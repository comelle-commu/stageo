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
    url = (
        f"{SUPABASE_URL}/rest/v1/activites?select=*"
        f"&premiere_apparition=gt.{since_iso}"
        "&order=premiere_apparition.asc"
    )
    resp = requests.get(url, headers=_digest_headers("count=none"), timeout=30)
    resp.raise_for_status()
    return resp.json()


def _group_key(row: dict) -> str:
    return row.get("organisateur") or row.get("commune") or "Non précisé"


def build_email_html(rows: list[dict]) -> tuple[str, str]:
    """Retourne (subject, html)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[_group_key(row)].append(row)

    subject = f"{len(rows)} nouvelle{'s' if len(rows) != 1 else ''} activité{'s' if len(rows) != 1 else ''} repérée{'s' if len(rows) != 1 else ''} par Trouvéo"

    sections = []
    for source in sorted(groups.keys(), key=lambda k: -len(groups[k])):
        items = groups[source]
        rows_html = []
        for r in items[:MAX_ITEMS_PER_SOURCE]:
            nom = (r.get("nom_activite") or "").strip()
            dates = (r.get("dates") or "").strip()
            lieu = (r.get("lieu") or "").strip()
            rows_html.append(
                f'<tr><td style="padding:8px 0;border-top:1px solid #EEF3F1;">'
                f'<div style="font-weight:600;color:#015380;font-size:14.5px;">{_esc(nom)}</div>'
                f'<div style="color:#5C7A8C;font-size:13px;margin-top:2px;">{_esc(dates)}'
                f'{" · " + _esc(lieu) if lieu else ""}</div></td></tr>'
            )
        remaining = len(items) - MAX_ITEMS_PER_SOURCE
        if remaining > 0:
            rows_html.append(
                f'<tr><td style="padding:8px 0;border-top:1px solid #EEF3F1;color:#5C7A8C;font-size:13px;">'
                f"… et {remaining} autre{'s' if remaining != 1 else ''} chez {_esc(source)}.</td></tr>"
            )
        sections.append(
            f'<div style="margin-bottom:24px;">'
            f'<div style="font-size:12px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;color:#017089;margin-bottom:6px;">{_esc(source)} ({len(items)})</div>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{"".join(rows_html)}</table>'
            f"</div>"
        )

    html = f"""
<div style="font-family:'Work Sans',Arial,sans-serif;max-width:560px;margin:0 auto;background:#FFFDF8;padding:32px 24px;color:#015380;">
  <div style="font-family:Georgia,serif;font-weight:700;font-size:22px;margin-bottom:6px;">Trouvéo</div>
  <p style="color:#5C7A8C;font-size:15px;line-height:1.6;margin:0 0 24px;">
    {len(rows)} nouvelle{'s' if len(rows) != 1 else ''} activité{'s' if len(rows) != 1 else ''} détectée{'s' if len(rows) != 1 else ''} cette semaine :
  </p>
  {"".join(sections)}
  <div style="margin-top:28px;text-align:center;">
    <a href="{SITE_URL}/activites" style="display:inline-block;background:#0197AF;color:#fff;text-decoration:none;font-weight:700;font-size:14px;padding:13px 26px;border-radius:100px;">Voir toutes les activités →</a>
  </div>
  <p style="color:#93A9B5;font-size:12px;margin-top:32px;text-align:center;">
    Trouvéo est encore en bêta - cet email liste automatiquement ce que notre outil a repéré, sans filtre par âge ou par commune pour l'instant.
  </p>
</div>
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
