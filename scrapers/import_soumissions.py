"""Reprend les soumissions d'activités approuvées (soumettre-activite.html,
table `soumissions_activites`) et les publie dans `activites` - voir
docs/partenariats-premium-2026-08-31.md.

Aucune auto-publication : une soumission n'est reprise ici que si son
`statut` a été passé à 'approuvee' à la main (Table editor Supabase, après
relecture) ET qu'elle n'a jamais été importée (`importee_le` vide). Une
fois importée, `importee_le` est rempli pour ne jamais la réimporter au run
suivant - contrairement aux scrapers, ce n'est pas une source qui se
resoumet elle-même chaque semaine.

Lancé après run_all.py dans .github/workflows/scrape.yml (même run
hebdomadaire), mais peut aussi tourner seul :
    venv/bin/python3 import_soumissions.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

import requests

from common import Activite
from supabase_client import SUPABASE_SECRET_KEY, SUPABASE_URL, is_configured, upsert_activites

TABLE = "soumissions_activites"


def _headers(prefer: str) -> dict:
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def fetch_approuvees() -> list[dict]:
    url = (
        f"{SUPABASE_URL}/rest/v1/{TABLE}"
        "?select=*&statut=eq.approuvee&importee_le=is.null&order=created_at.asc"
    )
    resp = requests.get(url, headers=_headers("count=none"), timeout=15)
    resp.raise_for_status()
    return resp.json()


def _to_activite(row: dict) -> Activite:
    return Activite(
        commune=row.get("commune") or "",
        organisateur=row["organisateur"],
        nom_activite=row["nom_activite"],
        type_activite=row["type_activite"],
        dates=row["dates"],
        age_min=row.get("age_min"),
        age_max=row.get("age_max"),
        prix=row.get("prix") or "Non communiqué",
        lieu=row.get("lieu") or "Non communiqué",
        modalites_inscription=row.get("modalites_inscription") or f"Contact : {row['contact_email']}",
        disponibilite="Non communiqué",
        lien_source=row.get("lien_source") or "",
    )


def _mark_importee(ids: list[int]) -> None:
    if not ids:
        return
    # Horodatage calculé côté client (pas "now()" - PostgREST prend une
    # valeur JSON littérale, pas une expression SQL à évaluer côté base).
    now_iso = datetime.now(timezone.utc).isoformat()
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=in.({','.join(str(i) for i in ids)})"
    resp = requests.patch(
        url,
        headers=_headers("return=minimal"),
        json={"importee_le": now_iso},
        timeout=15,
    )
    resp.raise_for_status()


def main() -> int:
    if not is_configured():
        print("Supabase : scrapers/.env absent ou incomplet -> import des soumissions ignoré.")
        return 0

    rows = fetch_approuvees()
    if not rows:
        print("Aucune soumission approuvée en attente d'import.")
        return 0

    activites = [_to_activite(r) for r in rows]
    upserted = upsert_activites(activites)
    _mark_importee([r["id"] for r in rows])

    print(f"{len(upserted)} activité(s) importée(s) depuis soumissions_activites :")
    for r in rows:
        print(f"  - {r['nom_activite']} ({r['organisateur']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
