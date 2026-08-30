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
# de le redétecter à l'exécution, on le sait déjà pour chaque commune/
# organisme. Clé = `organisateur` pour les scrapers non-communaux (ADEPS,
# Cap Sciences...), sinon `commune` - voir to_row() ci-dessous.
PLATEFORME_SOURCE = {
    "Ans": "Plone",
    "Seraing": "WordPress",
    "Neupre": "Nuxt",
    "Verviers": "Plone",
    "Herstal": "Plone",
    "Huy": "Plone",
    "Sprimont": "Plone",
    "Mons": "Plone",
    "Arlon": "Plone",
    "ADEPS": "Drupal",
    "Cap Sciences": "WordPress",
    "Royal Léopold Club": "MyiClub",
    "Royal Racing Club de Bruxelles": "MyiClub",
    "Jeunesse à Bruxelles": "WordPress",
}


def slugify(commune: str) -> str:
    """ex. "Neupre" -> "neupre". Volontairement simple (accents déjà absents
    des noms de commune utilisés dans le code - voir neupre.py). Chaîne vide
    -> chaîne vide (cas des activités d'organisme sans commune déductible)."""
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
    source_key = activite.organisateur or activite.commune
    row["plateforme_source"] = PLATEFORME_SOURCE.get(source_key, "Inconnue")
    return row


def _dedupe_rows(rows: list[dict]) -> list[dict]:
    """PostgreSQL refuse un batch INSERT ... ON CONFLICT DO UPDATE qui
    toucherait deux fois la même ligne (erreur 500 "ON CONFLICT DO UPDATE
    command cannot affect row a second time") - rencontré en pratique avec
    le PDF Herstal, qui contient deux entrées strictement identiques
    (même thème/organisme/semaine, doublon dans le PDF source lui-même).
    On déduplique donc côté client sur la même clé que la contrainte
    unique en base avant l'envoi.

    `lieu` ET `lien_source` font partie de la clé (pas seulement
    commune_slug/nom/dates) : l'ADEPS réutilise le même nom de stage
    générique pour la même semaine dans plusieurs centres différents (ex.
    "Zap Multisports" à Jambes, à Neufchâteau ET à Spa la même semaine) ET
    dans plusieurs tranches d'âge au même endroit (ex. "Multisports" à Mons
    la même semaine pour 6-8 ans et pour 9-12 ans) - toutes des activités
    bien distinctes. Sans `lieu`/`lien_source` dans la clé, elles étaient
    fusionnées à tort - 154 puis 60 activités ADEPS perdues aux deux
    premiers imports avant que ce bug ne soit repéré. Voir
    supabase/migrations/20260824c_fix_dedup_key_add_lieu.sql."""
    seen: dict[tuple, dict] = {}
    for row in rows:
        key = (row["commune_slug"], row["nom_activite"], row["dates"], row["lieu"], row["lien_source"])
        seen[key] = row  # la dernière occurrence gagne (elles sont identiques en pratique)
    return list(seen.values())


def upsert_activites(activites: list["Activite"]) -> list[dict]:
    """Upsert (insert ou update) sur la clé (commune_slug, nom_activite,
    dates, lieu, lien_source) définie par la contrainte unique
    `activites_dedup_key` - relancer le scraper plusieurs fois ne duplique
    pas les lignes déjà présentes."""
    if not activites:
        return []
    if not is_configured():
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SECRET_KEY manquants - voir scrapers/.env "
            "(non committé, à créer à partir des credentials du projet Supabase)."
        )
    rows = _dedupe_rows([to_row(a) for a in activites])
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?on_conflict=commune_slug,nom_activite,dates,lieu,lien_source"
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


# --- Contrôle qualité (historique des runs) --------------------------------
#
# Référence de départ demandée explicitement : 82 activités (le total en
# base au moment où cette fonctionnalité a été ajoutée). Utilisée seulement
# tant qu'aucun run "OK" n'a encore été journalisé dans `scrape_runs`
# (premier run après la migration).
BOOTSTRAP_REFERENCE = 82
DROP_THRESHOLD = 0.5  # 50%
RUNS_TABLE = "scrape_runs"


def _fetch_last_ok_total() -> int:
    url = (
        f"{SUPABASE_URL}/rest/v1/{RUNS_TABLE}"
        "?select=total_activites&statut=eq.OK&order=ran_at.desc&limit=1"
    )
    resp = requests.get(url, headers=_headers("count=none"), timeout=15)
    resp.raise_for_status()
    rows = resp.json()
    return rows[0]["total_activites"] if rows else BOOTSTRAP_REFERENCE


def log_run_and_check_quality(total_activites: int) -> tuple[bool, str]:
    """Compare `total_activites` (nombre d'activités récupérées par CE run,
    avant dédoublonnage Supabase) au dernier run considéré sain (statut=OK),
    journalise ce run dans `scrape_runs`, et retourne (sain, message).

    Comparaison volontairement faite contre le dernier run OK plutôt que le
    run immédiatement précédent : sinon une panne durable (plusieurs runs en
    échec d'affilée) finirait par sembler "normale" puisque chaque run en
    échec deviendrait la nouvelle référence basse pour le suivant."""
    if not is_configured():
        raise RuntimeError("SUPABASE_URL / SUPABASE_SECRET_KEY manquants - voir scrapers/.env")

    reference = _fetch_last_ok_total()
    drop_ratio = (reference - total_activites) / reference if reference > 0 else 0.0
    healthy = drop_ratio < DROP_THRESHOLD
    statut = "OK" if healthy else "ALERTE_BAISSE"
    details = f"reference={reference} total={total_activites} baisse={drop_ratio:.0%}"

    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/{RUNS_TABLE}",
        headers=_headers("return=minimal"),
        json=[{"total_activites": total_activites, "statut": statut, "details": details}],
        timeout=15,
    )
    resp.raise_for_status()

    if healthy:
        message = f"{total_activites} activités (référence : {reference}) - OK"
    else:
        message = (
            f"ALERTE : {total_activites} activités récupérées contre {reference} "
            f"au dernier run sain (baisse de {drop_ratio:.0%}, seuil {DROP_THRESHOLD:.0%}) "
            "- un site a probablement changé de structure, le scraper ne lit peut-être plus rien."
        )
    return healthy, message
