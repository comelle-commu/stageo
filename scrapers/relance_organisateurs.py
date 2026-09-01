"""Relance "vos stages sont terminés, envoyez-nous le prochain programme" -
pour les organismes dont on connaît un email de contact (table
organisateurs_contact, voir migration 20260901) et dont TOUTES les
activités actuellement en base sont passées.

Contexte : jusqu'ici, un organisme qui envoie son programme (par email ou
via soumettre-activite.html) n'était jamais relancé une fois ses stages
terminés - sans rappel, la fiche reste simplement à jour jusqu'à la
prochaine saison, mais rien ne les pousse à penser à nous renvoyer leurs
nouvelles dates. Voir docs/partenariats-premium-2026-08-31.md (idée notée
le 31/08/2026) et le cas de la Société archéologique de Namur
(01/09/2026) qui a motivé sa construction.

Un email de contact structuré n'existe que pour les organismes ayant
soumis directement (via soumettre-activite.html, ou ajoutés à la main
dans organisateurs_contact) - la grande majorité des ~50 sources scrapées
automatiquement n'en ont pas et ne sont donc jamais concernées par ce
script, ce qui est le comportement voulu (on ne connaît pas d'email à qui
écrire).

Anti-doublon : `relances_organisateurs_envoyees` retient, par organisateur,
la date du dernier ajout connu au moment de la relance - une nouvelle
relance n'est envoyée que si l'organisme a soumis une activité plus
récente depuis (qui a fini, elle aussi, par expirer), pas à chaque run
tant qu'il n'a rien renvoyé.

Lancé après import_soumissions.py dans le workflow GitHub Actions (voir
.github/workflows/scrape.yml) - a besoin des activités fraîchement
importées pour juger correctement qui a déjà soumis un programme récent.

Usage :
  venv/bin/python3 relance_organisateurs.py            # envoi réel
  venv/bin/python3 relance_organisateurs.py --dry-run  # affiche les candidat·es, n'envoie rien et ne touche pas relances_organisateurs_envoyees

Variable d'environnement RELANCE_ORG_TEST_EMAIL (optionnelle) : si
définie, ne considère que les organismes dont le contact_email correspond
- même mécanisme que RELANCE_TEST_EMAIL dans relance_criteres.py.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone

import requests

import supabase_client
from criteres_alertes import is_upcoming
from supabase_client import SUPABASE_URL, _headers

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Trouvéo")
TEST_EMAIL = os.environ.get("RELANCE_ORG_TEST_EMAIL", "").strip().lower()
SITE_URL = "https://trouveo.be"


def is_configured() -> bool:
    return bool(BREVO_API_KEY and BREVO_SENDER_EMAIL)


def fetch_contacts() -> dict[str, str]:
    """source_key -> contact_email."""
    url = f"{SUPABASE_URL}/rest/v1/organisateurs_contact?select=source_key,contact_email"
    resp = requests.get(url, headers=_headers("count=none"), timeout=15)
    resp.raise_for_status()
    return {r["source_key"]: r["contact_email"] for r in resp.json()}


def fetch_activites_par_organisateur(source_keys: list[str]) -> dict[str, list[dict]]:
    """Toutes les activités actuelles pour ces organisateurs (regroupées),
    en cherchant à la fois sur `organisateur` et `commune` - même
    ambiguïté que groupKey() côté site (un organisme sans champ
    `organisateur` distinct est identifié par sa commune)."""
    if not source_keys:
        return {}
    in_list = ",".join(f'"{k}"' for k in source_keys)
    result: dict[str, list[dict]] = {k: [] for k in source_keys}
    for column in ("organisateur", "commune"):
        url = f"{SUPABASE_URL}/rest/v1/activites?select=organisateur,commune,dates,created_at&{column}=in.({in_list})"
        resp = requests.get(url, headers=_headers("count=none"), timeout=30)
        resp.raise_for_status()
        for row in resp.json():
            key = row.get("organisateur") or row.get("commune")
            if key in result:
                result[key].append(row)
    return result


def fetch_already_relanced() -> dict[str, datetime]:
    url = f"{SUPABASE_URL}/rest/v1/relances_organisateurs_envoyees?select=source_key,dernier_ajout_connu"
    resp = requests.get(url, headers=_headers("count=none"), timeout=15)
    resp.raise_for_status()
    return {
        r["source_key"]: datetime.fromisoformat(r["dernier_ajout_connu"].replace("Z", "+00:00"))
        for r in resp.json()
    }


def log_relance(source_key: str, dernier_ajout_connu: datetime) -> None:
    url = f"{SUPABASE_URL}/rest/v1/relances_organisateurs_envoyees?on_conflict=source_key"
    resp = requests.post(
        url,
        headers=_headers("resolution=merge-duplicates,return=minimal"),
        json=[{
            "source_key": source_key,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "dernier_ajout_connu": dernier_ajout_connu.isoformat(),
        }],
        timeout=15,
    )
    resp.raise_for_status()


def build_email_html(source_key: str) -> tuple[str, str]:
    subject = "Vos stages sont terminés - et la suite ?"
    submit_link = f"{SITE_URL}/soumettre-activite.html"
    partenaires_link = f"{SITE_URL}/partenaires.html"
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
      Vos stages sont terminés - et la suite ?
    </span>
  </td></tr>

  <tr><td style="padding-bottom:26px;color:#5C7A8C;font-size:14.5px;line-height:1.6;">
    Les activités de {source_key} sur Trouvéo sont maintenant toutes passées. Si vous avez
    un prochain programme (vacances de Noël, Carnaval...), envoyez-le-nous - deux minutes suffisent.
  </td></tr>

  <tr><td align="center" style="padding:0 0 22px;">
    <a href="{submit_link}" style="display:inline-block;background:#0197AF;color:#ffffff;text-decoration:none;
      font-family:'Work Sans',Arial,sans-serif;font-weight:700;font-size:14px;padding:14px 28px;border-radius:100px;">
      Soumettre mon prochain stage →
    </a>
  </td></tr>

  <tr><td style="border-top:1px solid rgba(1,83,128,0.12);padding-top:18px;">
    <p style="color:#93A9B5;font-size:12px;line-height:1.6;margin:0;text-align:center;">
      Au passage : si vous voulez plus de visibilité, une mise en avant est possible
      (<a href="{partenaires_link}" style="color:#93A9B5;">en savoir plus</a>). Aucune obligation,
      l'inscription de base reste et restera toujours gratuite.
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
        print("Supabase non configuré (scrapers/.env) - relances organisateurs ignorées.")
        return 0
    if not is_configured():
        print("Brevo non configuré (BREVO_API_KEY / BREVO_SENDER_EMAIL manquants) - relances organisateurs ignorées.")
        return 0

    contacts = fetch_contacts()
    if not contacts:
        print("Aucun organisateur avec email de contact connu (organisateurs_contact vide) - rien à faire.")
        return 0

    activites_par_org = fetch_activites_par_organisateur(list(contacts.keys()))
    already = fetch_already_relanced()
    today = date.today()

    candidates: list[tuple[str, str, datetime]] = []  # (source_key, email, dernier_ajout_connu)
    for source_key, email in contacts.items():
        rows = activites_par_org.get(source_key, [])
        if not rows:
            continue  # jamais importé (ou pas encore) - rien à relancer
        if any(is_upcoming(r, today) for r in rows):
            continue  # au moins une activité encore à venir - pas de creux
        dernier_ajout = max(
            datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")) for r in rows
        )
        deja = already.get(source_key)
        if deja is not None and deja >= dernier_ajout:
            continue  # déjà relancé pour ce creux précis, rien de neuf depuis
        candidates.append((source_key, email, dernier_ajout))

    if TEST_EMAIL:
        candidates = [c for c in candidates if c[1].strip().lower() == TEST_EMAIL]
        print(f"[test] restreint à {TEST_EMAIL} ({len(candidates)} candidat trouvé).")

    print(f"{len(contacts)} organisateur(s) avec contact connu, {len(candidates)} candidat(e)s à relancer.")

    sent = 0
    for source_key, email, dernier_ajout in candidates:
        subject, html = build_email_html(source_key)
        print(f"{'[dry-run] ' if dry_run else ''}Relance pour {source_key} ({email})")
        if dry_run:
            continue
        try:
            send_transactional(email, subject, html)
        except requests.HTTPError as exc:
            print(f"Erreur d'envoi pour {source_key} ({email}): {exc}")
            continue
        log_relance(source_key, dernier_ajout)
        sent += 1

    if dry_run:
        print("[dry-run] aucun email envoyé, relances_organisateurs_envoyees non modifiée.")
    else:
        print(f"{sent} relance(s) envoyée(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
