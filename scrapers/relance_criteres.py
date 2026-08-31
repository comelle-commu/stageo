"""Relance "vous n'avez pas encore précisé vos critères" - pour les
contacts de la liste d'attente Brevo qui n'ont jamais rempli le
formulaire /criteres.html (aucune ligne dans `criteres_parents`).

Contexte : l'email envoyé juste après l'inscription (automation Brevo,
externe à ce dépôt - voir docs/brevo-signup-2026-08-24.md) ne suffit pas
à lui seul - une partie des inscrits ouvrent l'email, sont interrompus,
et n'y reviennent jamais (~60% d'abandon observé le 31/08/2026 : 18
contacts Brevo pour 7 critères remplis). Ce script referme cet écart
avec UNE relance, envoyée une fois par contact (jamais répétée - voir
`relances_criteres_envoyees`), quelques jours après l'inscription pour
laisser le temps de le faire naturellement avant de relancer.

Lancé après criteres_alertes.py dans le workflow GitHub Actions (voir
.github/workflows/scrape.yml) - indépendant du scrape (n'a besoin que de
Brevo + Supabase), mais placé au même endroit par cohérence avec les
deux autres jobs d'email.

Usage :
  venv/bin/python3 relance_criteres.py            # envoi réel
  venv/bin/python3 relance_criteres.py --dry-run  # affiche les candidat·es, n'envoie rien et ne touche pas relances_criteres_envoyees

Variable d'environnement RELANCE_TEST_EMAIL (optionnelle) : si définie,
ne considère que ce contact - même mécanisme que ALERTES_TEST_EMAIL dans
criteres_alertes.py, pour tester sans risquer d'écrire aux vrais inscrits.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

import supabase_client
from supabase_client import SUPABASE_URL, _headers

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_LIST_ID = os.environ.get("BREVO_LIST_ID", "")
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Trouvéo")
TEST_EMAIL = os.environ.get("RELANCE_TEST_EMAIL", "").strip().lower()
SITE_URL = "https://trouveo.be"

# Délai avant la relance : assez court pour rester dans l'intention
# initiale de l'inscrit·e, assez long pour ne pas relancer quelqu'un qui
# était simplement en train de remplir le formulaire au moment du run.
DELAY_DAYS = 2


def is_configured() -> bool:
    return bool(BREVO_API_KEY and BREVO_LIST_ID and BREVO_SENDER_EMAIL)


def fetch_brevo_contacts() -> list[dict]:
    """Tous les contacts de la liste d'attente, avec email/date
    d'inscription/statut désabonné - pagination par blocs de 50 (max
    autorisé par l'API Brevo sur cet endpoint)."""
    headers = {"api-key": BREVO_API_KEY, "Accept": "application/json"}
    page_size = 50
    offset = 0
    contacts: list[dict] = []
    while True:
        url = (
            f"https://api.brevo.com/v3/contacts/lists/{BREVO_LIST_ID}/contacts"
            f"?limit={page_size}&offset={offset}"
        )
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        page = resp.json().get("contacts", [])
        contacts.extend(page)
        if len(page) < page_size:
            return contacts
        offset += page_size


def fetch_criteres_emails() -> set[str]:
    url = f"{SUPABASE_URL}/rest/v1/criteres_parents?select=email"
    resp = requests.get(url, headers=_headers("count=none"), timeout=30)
    resp.raise_for_status()
    return {row["email"].strip().lower() for row in resp.json()}


def fetch_already_reminded() -> set[str]:
    url = f"{SUPABASE_URL}/rest/v1/relances_criteres_envoyees?select=email"
    resp = requests.get(url, headers=_headers("count=none"), timeout=30)
    resp.raise_for_status()
    return {row["email"].strip().lower() for row in resp.json()}


def log_reminded(email: str) -> None:
    url = f"{SUPABASE_URL}/rest/v1/relances_criteres_envoyees"
    resp = requests.post(
        url,
        headers=_headers("resolution=merge-duplicates,return=minimal"),
        json=[{"email": email}],
        timeout=15,
    )
    resp.raise_for_status()


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_email_html(criteres_link: str) -> tuple[str, str]:
    subject = "Il manque juste vos critères pour activer vos alertes"
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Grandstander:wght@700;800&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;background:#FFFDF8;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FFFDF8;">
<tr><td align="center" style="padding:36px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;font-family:'Work Sans',Arial,sans-serif;">

  <tr><td style="padding-bottom:22px;">
    <span style="font-family:'Grandstander',Arial,sans-serif;font-weight:800;font-size:22px;color:#015380;">Trouvéo</span>
  </td></tr>

  <tr><td style="padding-bottom:24px;">
    <span style="font-family:'Grandstander',Arial,sans-serif;font-weight:700;font-size:21px;color:#015380;line-height:1.3;">
      Il manque juste vos critères pour activer vos alertes
    </span>
  </td></tr>

  <tr><td style="padding-bottom:26px;color:#5C7A8C;font-size:14.5px;line-height:1.6;">
    Vous vous êtes inscrit·e sur Trouvéo, mais il manque une étape : l'âge de votre enfant, sa commune
    et ses activités préférées - trente secondes pour que nous puissions commencer à vous prévenir
    dès qu'un stage correspond vraiment à sa famille.
  </td></tr>

  <tr><td align="center" style="padding:0 0 8px;">
    <a href="{criteres_link}" style="display:inline-block;background:#0197AF;color:#ffffff;text-decoration:none;
      font-family:'Work Sans',Arial,sans-serif;font-weight:700;font-size:14px;padding:14px 28px;border-radius:100px;">
      Préciser mes critères →
    </a>
  </td></tr>

  <tr><td style="border-top:1px solid rgba(1,83,128,0.12);padding-top:18px;margin-top:22px;">
    <p style="color:#93A9B5;font-size:12px;line-height:1.6;margin:0;text-align:center;">
      Vous recevez cet email car vous vous êtes inscrit·e sur Trouvéo. Pas intéressé·e ? Ignorez simplement ce message.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>
""".strip()
    return subject, html


def send_transactional(to_email: str, subject: str, html: str) -> None:
    resp = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
        json={
            "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html,
        },
        timeout=20,
    )
    resp.raise_for_status()


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not supabase_client.is_configured():
        print("Supabase non configuré (scrapers/.env) - relances ignorées.")
        return 0
    # Contrairement à brevo_digest.py, même le dry-run a besoin de
    # BREVO_API_KEY/BREVO_LIST_ID : la liste des candidat·es dépend de qui
    # est réellement dans la liste d'attente Brevo, pas seulement de
    # Supabase - impossible à prévisualiser sans ça.
    if not is_configured():
        print(
            "Brevo non configuré pour les relances (BREVO_API_KEY / BREVO_LIST_ID / "
            "BREVO_SENDER_EMAIL manquants) - relances ignorées."
        )
        return 0

    contacts = fetch_brevo_contacts()
    criteres_emails = fetch_criteres_emails()
    already_reminded = fetch_already_reminded()
    cutoff = datetime.now(timezone.utc) - timedelta(days=DELAY_DAYS)

    candidates = []
    for c in contacts:
        email = (c.get("email") or "").strip().lower()
        if not email or c.get("emailBlacklisted"):
            continue  # désabonné·e - ne jamais relancer malgré la promesse "désinscription en un clic"
        if email in criteres_emails or email in already_reminded:
            continue
        created_at = c.get("createdAt")
        if not created_at:
            continue
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if created > cutoff:
            continue  # inscrit·e trop récemment - on lui laisse le temps de remplir naturellement
        candidates.append(email)

    if TEST_EMAIL:
        candidates = [e for e in candidates if e == TEST_EMAIL]
        print(f"[test] restreint à {TEST_EMAIL} ({len(candidates)} candidat trouvé).")

    print(
        f"{len(contacts)} contact(s) Brevo, {len(criteres_emails)} critère(s) déjà rempli(s), "
        f"{len(candidates)} candidat(e)s à relancer."
    )

    sent = 0
    for email in candidates:
        criteres_link = f"{SITE_URL}/criteres.html?email={quote(email)}"
        subject, html = build_email_html(criteres_link)
        print(f"{'[dry-run] ' if dry_run else ''}Relance pour {email}")
        if dry_run:
            continue
        try:
            send_transactional(email, subject, html)
        except requests.HTTPError as exc:
            print(f"Erreur d'envoi pour {email}: {exc}")
            continue
        log_reminded(email)
        sent += 1

    if dry_run:
        print("[dry-run] aucun email envoyé, relances_criteres_envoyees non modifiée.")
    else:
        print(f"{sent} relance(s) envoyée(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
