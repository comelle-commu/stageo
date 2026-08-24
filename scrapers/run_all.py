"""Orchestrateur : lance le scraper de chaque commune, chronomètre, agrège,
écrit les sorties JSON/CSV dans output/, ET upsert dans Supabase si
scrapers/.env est configuré (voir docs/supabase-backend-2026-08-24.md).

Usage: venv/bin/python3 run_all.py
"""
from __future__ import annotations

import time
from pathlib import Path

import ans
import aywaille
import floreffe
import hannut
import herstal
import huy
import neupre
import oupeye
import seraing
import sprimont
import supabase_client
import verviers
import waremme
from common import write_outputs

SCRAPERS = [
    ("Ans", ans),
    ("Seraing", seraing),
    ("Neupre", neupre),
    ("Verviers", verviers),
    ("Herstal", herstal),
    ("Huy", huy),
    ("Sprimont", sprimont),
]

# Modules "en attente" : n'effectuent aucune requête réseau (voir chaque
# fichier pour la raison), mais apparaissent explicitement dans le résumé
# plutôt que d'être silencieusement absents.
EN_ATTENTE = [floreffe, waremme, hannut, oupeye, aywaille]

OUT_DIR = Path(__file__).parent / "output"


def run_scrapers() -> tuple[list, list[tuple[str, int, float, str]]]:
    """Lance chaque scraper, retourne (toutes les activités, timings)."""
    all_activites = []
    timings = []

    for nom, module in SCRAPERS:
        print(f"--- {nom} ---")
        start = time.monotonic()
        try:
            activites = module.scrape()
            elapsed = time.monotonic() - start
            print(f"  {len(activites)} activités extraites en {elapsed:.2f}s")
            timings.append((nom, len(activites), elapsed, "OK"))
            all_activites.extend(activites)
        except Exception as exc:  # noqa: BLE001 - on veut que les autres communes tournent quand même
            elapsed = time.monotonic() - start
            print(f"  ERREUR après {elapsed:.2f}s : {exc}")
            timings.append((nom, 0, elapsed, f"ERREUR: {exc}"))

    for module in EN_ATTENTE:
        nom = module.__name__.capitalize()
        print(f"--- {nom} ---")
        print(f"  EN_ATTENTE - {module.RAISON}")
        timings.append((nom, 0, 0.0, "EN_ATTENTE"))

    return all_activites, timings


def main() -> None:
    all_activites, timings = run_scrapers()

    json_path, csv_path = write_outputs(all_activites, OUT_DIR)

    print(f"\n=== Résumé ===")
    print(f"Total activités : {len(all_activites)}")
    for nom, n, elapsed, statut in timings:
        print(f"  {nom:10s} {n:3d} activités  {elapsed:6.2f}s  [{statut}]")
    print(f"\nSorties fichiers : {json_path} / {csv_path}")

    timing_path = OUT_DIR / "timings.txt"
    with timing_path.open("w", encoding="utf-8") as f:
        f.write("commune,activites,duree_secondes,statut\n")
        for nom, n, elapsed, statut in timings:
            f.write(f"{nom},{n},{elapsed:.2f},{statut}\n")

    print()
    if not supabase_client.is_configured():
        print("Supabase : scrapers/.env absent ou incomplet -> import ignoré (fichiers JSON/CSV seuls).")
        return

    print("--- Import Supabase ---")
    start = time.monotonic()
    try:
        rows = supabase_client.upsert_activites(all_activites)
        elapsed = time.monotonic() - start
        print(f"  {len(rows)} lignes upsertées dans `activites` en {elapsed:.2f}s")
    except Exception as exc:  # noqa: BLE001
        elapsed = time.monotonic() - start
        print(f"  ERREUR après {elapsed:.2f}s : {exc}")


if __name__ == "__main__":
    main()
