"""Écriture/lecture de la table `activites` sur Supabase, via l'API REST
(PostgREST) — pas de dépendance au SDK supabase-py, juste `requests`.

Credentials lus depuis scrapers/.env (jamais committé — voir .gitignore) ou
depuis l'environnement si déjà exporté. Schéma de la table :
supabase/migrations/20260824_create_activites.sql (à exécuter une fois dans
le SQL Editor Supabase avant le premier import — voir
docs/supabase-backend-2026-08-24.md).
"""
from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from common import Activite


def _load_dotenv() -> None:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
TABLE = "activites"

# Un scraper = une plateforme connue (voir scrapers/README.md) -> pas besoin
# de le redétecter à l'exécution, on le sait déjà pour chaque commune.
PLATEFORME_SOURCE = {
    "Ans": "Plone",
    "Seraing": "WordPress",
    "Neupre": "Nuxt",
    "Verviers": "Plone",
}


def slugify(commune: str) -> str:
    """ex. "Neupre" -> "neupre". Volontairement simple (accents déjà absents
    des noms de commune utilisés dans le code - voir neupre.py)."""
    return commune.strip().lower().replace(" ", "-")


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SECRET_KEY)


def _headers(prefer: str) -> dict:
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def to_row(activite: "Activite") -> dict:
    row = asdict(activite)
    row["commune_slug"] = slugify(activite.commune)
    row["plateforme_source"] = PLATEFORME_SOURCE.get(activite.commune, "Inconnue")
    return row


def upsert_activites(activites: list["Activite"]) -> list[dict]:
    """Upsert (insert ou update) sur la clé (commune_slug, nom_activite,
    dates) définie par la contrainte unique `activites_dedup_key` - relancer
    le scraper plusieurs fois ne duplique pas les lignes déjà présentes."""
    if not activites:
        return []
    if not is_configured():
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SECRET_KEY manquants - voir scrapers/.env "
            "(non committé, à créer à partir des credentials du projet Supabase)."
        )
    rows = [to_row(a) for a in activites]
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?on_conflict=commune_slug,nom_activite,dates"
    resp = requests.post(
        url,
        headers=_headers("resolution=merge-duplicates,return=representation"),
        json=rows,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_all() -> list[dict]:
    """Lecture simple de toute la table, pour vérification."""
    if not is_configured():
        raise RuntimeError("SUPABASE_URL / SUPABASE_SECRET_KEY manquants - voir scrapers/.env")
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?select=*&order=commune_slug,nom_activite"
    resp = requests.get(url, headers=_headers("count=exact"), timeout=30)
    resp.raise_for_status()
    return resp.json()
