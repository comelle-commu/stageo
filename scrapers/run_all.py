"""Orchestrateur : lance le scraper de chaque commune, chronomètre, agrège,
et écrit les sorties JSON/CSV dans output/.

Usage: venv/bin/python3 run_all.py
"""
from __future__ import annotations

import time
from pathlib import Path

import ans
import floreffe
import neupre
import seraing
import verviers
from common import write_outputs

SCRAPERS = [
    ("Ans", ans),
    ("Seraing", seraing),
    ("Neupre", neupre),
    ("Verviers", verviers),
]

OUT_DIR = Path(__file__).parent / "output"


def main() -> None:
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

    print(f"--- Floreffe ---")
    print(f"  EN_ATTENTE - {floreffe.RAISON}")
    timings.append(("Floreffe", 0, 0.0, "EN_ATTENTE"))

    json_path, csv_path = write_outputs(all_activites, OUT_DIR)

    print(f"\n=== Résumé ===")
    print(f"Total activités : {len(all_activites)}")
    for nom, n, elapsed, statut in timings:
        print(f"  {nom:10s} {n:3d} activités  {elapsed:6.2f}s  [{statut}]")
    print(f"\nSorties : {json_path} / {csv_path}")

    timing_path = OUT_DIR / "timings.txt"
    with timing_path.open("w", encoding="utf-8") as f:
        f.write("commune,activites,duree_secondes,statut\n")
        for nom, n, elapsed, statut in timings:
            f.write(f"{nom},{n},{elapsed:.2f},{statut}\n")


if __name__ == "__main__":
    main()
