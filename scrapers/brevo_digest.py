"""Email hebdomadaire "nouvelles activités" vers la liste d'attente Brevo.

Lancé après run_all.py dans le workflow GitHub Actions (voir
.github/workflows/scrape.yml). Logique :

1. Lire la date du dernier envoi réussi dans `digest_log` (table Supabase).
2. Si aucun envoi précédent : on initialise la référence à maintenant SANS
   rien envoyer - sinon le premier run enverrait un email listant les 700+
   activités déjà en base comme si elles venaient d'apparaître cette
   semaine, ce qui n'aurait aucun sens pour l'abonné.
3. Sinon : chercher les activités dont `premiere_apparition` est postérieure
   à ce dernier envoi. S'il y en a, construire un email et l'envoyer à la
   liste Brevo entière via l'API Campagnes (POST /v3/emailCampaigns puis
   POST /v3/emailCampaigns/{id}/sendNow) - PAS l'API transactionnelle, qui
   n'a pas la gestion native du désabonnement/liste.

Usage :
  venv/bin/python3 brevo_digest.py            # envoi réel
  venv/bin/python3 brevo_digest.py --dry-run   # construit l'email, l'écrit
                                                # dans output/, n'envoie rien
                                                # et ne touche pas digest_log
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

import supabase_client
from supabase_client import SUPABASE_SECRET_KEY, SUPABASE_URL, _headers

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_LIST_ID = os.environ.get("BREVO_LIST_ID", "")
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Trouvéo")
SITE_URL = "https://stageo.netlify.app"

DIGEST_TABLE = "digest_log"
MAX_ITEMS_PER_SOURCE = 5  # au-delà, on résume ("... et N autres") pour ne pas produire un email interminable


def _digest_headers(prefer: str) -> dict:
    return _headers(prefer)


def is_configured() -> bool:
    return bool(BREVO_API_KEY and BREVO_LIST_ID and BREVO_SENDER_EMAIL)


def _last_sent_at() -> str | None:
    url = f"{SUPABASE_URL}/rest/v1/{DIGEST_TABLE}?select=sent_at&order=sent_at.desc&limit=1"
    resp = requests.get(url, headers=_digest_headers("count=none"), timeout=15)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0]["sent_at"] if rows else None


def _log_digest(nb_nouvelles: int, statut: str, details: str, brevo_campaign_id: int | None = None) -> None:
    url = f"{SUPABASE_URL}/rest/v1/{DIGEST_TABLE}"
    payload = {
        "nb_nouvelles": nb_nouvelles,
        "statut": statut,
        "details": details,
    }
    if brevo_campaign_id is not None:
        payload["brevo_campaign_id"] = brevo_campaign_id
    resp = requests.post(url, headers=_digest_headers("return=minimal"), json=[payload], timeout=15)
    resp.raise_for_status()


def _fetch_new_activites(since_iso: str) -> list[dict]:
    # quote() est indispensable ici : un "+" (fuseau horaire, ex.
    # "+00:00") non encodé dans une query string est interprété comme un
    # espace par PostgREST -> "invalid input syntax for type timestamp".
    url = (
        f"{SUPABASE_URL}/rest/v1/activites?select=*"
        f"&premiere_apparition=gt.{quote(since_iso, safe='')}"
        "&order=premiere_apparition.asc"
    )
    resp = requests.get(url, headers=_digest_headers("count=none"), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _group_key(row: dict) -> str:
    return row.get("organisateur") or row.get("commune") or "Non précisé"


def build_email_html(rows: list[dict]) -> tuple[str, str]:
    """Retourne (subject, html). Reprend la charte graphique du site
    (fonds crème, cartes blanches arrondies, badges pilule teal, police
    Grandstander/Work Sans) plutôt qu'un email texte générique - voir
    index.html / activites.html pour les mêmes tokens de couleur."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[_group_key(row)].append(row)

    subject = f"{len(rows)} nouvelle{'s' if len(rows) != 1 else ''} activité{'s' if len(rows) != 1 else ''} repérée{'s' if len(rows) != 1 else ''} par Trouvéo"

    sections = []
    for source in sorted(groups.keys(), key=lambda k: -len(groups[k])):
        items = groups[source]
        cards_html = []
        for r in items[:MAX_ITEMS_PER_SOURCE]:
            nom = (r.get("nom_activite") or "").strip()
            dates = (r.get("dates") or "").strip()
            lieu = (r.get("lieu") or "").strip()
            cards_html.append(
                '<tr><td style="padding:0 0 10px;">'
                '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                'style="background:#FFFFFF;border:1px solid rgba(1,83,128,0.12);border-radius:14px;">'
                '<tr><td style="padding:14px 16px;">'
                f'<div style="font-family:\'Grandstander\',Arial,sans-serif;font-weight:700;'
                f'color:#015380;font-size:15px;line-height:1.35;margin-bottom:4px;">{_esc(nom)}</div>'
                f'<div style="color:#5C7A8C;font-size:13px;line-height:1.5;">{_esc(dates)}'
                f'{" &middot; " + _esc(lieu) if lieu else ""}</div>'
                "</td></tr></table></td></tr>"
            )
        remaining = len(items) - MAX_ITEMS_PER_SOURCE
        if remaining > 0:
            cards_html.append(
                '<tr><td style="padding:2px 4px 10px;color:#5C7A8C;font-size:13px;">'
                f"…et {remaining} autre{'s' if remaining != 1 else ''} chez {_esc(source)}.</td></tr>"
            )
        sections.append(
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">'
            "<tr><td style=\"padding-bottom:10px;\">"
            '<span style="display:inline-block;font-size:11.5px;font-weight:700;letter-spacing:.03em;'
            'text-transform:uppercase;color:#017089;background:#E7F4EE;padding:5px 12px;border-radius:100px;">'
            f"{_esc(source)} &middot; {len(items)}</span>"
            "</td></tr>"
            f"{''.join(cards_html)}"
            "</table>"
        )

    n_txt = f"{len(rows)} nouvelle{'s' if len(rows) != 1 else ''} activité{'s' if len(rows) != 1 else ''}"

    # <meta charset> explicite indispensable : sans elle, certains clients
    # mail/navigateurs devinent un mauvais encodage pour ce fragment et les
    # accents s'affichent en mojibake ("TrouvÃ©o") - repere en previsualisant
    # digest_preview.html avant le premier envoi reel.
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

  <tr><td style="padding-bottom:8px;">
    <span style="display:inline-block;font-size:12px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;
      color:#017089;background:#FFFFFF;padding:7px 14px;border-radius:100px;border:1px solid rgba(1,83,128,0.12);">
      Nouveautés de la semaine
    </span>
  </td></tr>

  <tr><td style="padding-bottom:24px;">
    <span style="font-family:'Grandstander',Arial,sans-serif;font-weight:700;font-size:21px;color:#015380;line-height:1.3;">
      {n_txt} repérée{'s' if len(rows) != 1 else ''} cette semaine
    </span>
  </td></tr>

  <tr><td>{"".join(sections)}</td></tr>

  <tr><td align="center" style="padding:14px 0 28px;">
    <a href="{SITE_URL}/activites" style="display:inline-block;background:#0197AF;color:#ffffff;text-decoration:none;
      font-family:'Work Sans',Arial,sans-serif;font-weight:700;font-size:14px;padding:14px 28px;border-radius:100px;">
      Voir toutes les activités →
    </a>
  </td></tr>

  <tr><td style="border-top:1px solid rgba(1,83,128,0.12);padding-top:18px;">
    <p style="color:#93A9B5;font-size:12px;line-height:1.6;margin:0;text-align:center;">
      Trouvéo est encore en bêta - cet email liste automatiquement ce que notre outil a repéré,
      sans filtre par âge ou par commune pour l'instant.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>
""".strip()
    return subject, html


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def send_campaign(subject: str, html: str) -> int:
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    create_resp = requests.post(
        "https://api.brevo.com/v3/emailCampaigns",
        headers=headers,
        json={
            "name": f"Digest hebdo - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "subject": subject,
            "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
            "htmlContent": html,
            "recipients": {"listIds": [int(BREVO_LIST_ID)]},
        },
        timeout=20,
    )
    create_resp.raise_for_status()
    campaign_id = create_resp.json()["id"]

    send_resp = requests.post(
        f"https://api.brevo.com/v3/emailCampaigns/{campaign_id}/sendNow",
        headers=headers,
        timeout=20,
    )
    send_resp.raise_for_status()
    return campaign_id


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not supabase_client.is_configured():
        print("Supabase non configuré (scrapers/.env) - digest ignoré.")
        return 0
    # En --dry-run, on ne touche jamais Brevo : pas besoin des credentials
    # pour prévisualiser le contenu de l'email.
    if not dry_run and not is_configured():
        print(
            "Brevo non configuré pour le digest (BREVO_API_KEY / BREVO_LIST_ID / "
            "BREVO_SENDER_EMAIL manquants) - digest ignoré."
        )
        return 0

    last_sent = _last_sent_at()

    if last_sent is None:
        print("Aucun envoi précédent - initialisation de la référence, aucun email envoyé.")
        if not dry_run:
            _log_digest(0, "INIT", "Premiere execution : reference initialisee, aucun email envoye.")
        return 0

    print(f"Dernier envoi : {last_sent}")
    new_rows = _fetch_new_activites(last_sent)
    print(f"{len(new_rows)} nouvelle(s) activité(s) depuis le dernier envoi.")

    if not new_rows:
        if not dry_run:
            _log_digest(0, "VIDE", "Aucune nouvelle activite depuis le dernier envoi.")
        return 0

    subject, html = build_email_html(new_rows)

    if dry_run:
        out_dir = Path(__file__).parent / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "digest_preview.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"[dry-run] Sujet : {subject}")
        print(f"[dry-run] Aperçu HTML écrit dans {out_path} - aucun email envoyé, digest_log non modifié.")
        return 0

    try:
        campaign_id = send_campaign(subject, html)
    except requests.HTTPError as exc:
        details = f"Erreur Brevo : {exc} - {exc.response.text if exc.response is not None else ''}"
        print(details)
        _log_digest(len(new_rows), "ERREUR", details)
        return 1

    print(f"Campagne Brevo #{campaign_id} envoyée ({len(new_rows)} activités).")
    _log_digest(len(new_rows), "OK", f"Campagne Brevo #{campaign_id}", brevo_campaign_id=campaign_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
