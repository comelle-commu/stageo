"""Orchestrateur : lance le scraper de chaque commune, chronomètre, agrège,
écrit les sorties JSON/CSV dans output/, ET upsert dans Supabase si
scrapers/.env est configuré (voir docs/supabase-backend-2026-08-24.md).

Usage: venv/bin/python3 run_all.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import adeps
import adsl_stages
import ans
import arlon
import aywaille
import bastogne
import capsciences
import chaudfontaine
import ciney
import coordination_atl
import cote_campagne
import crie_liege
import dimension_sport
import esneux
import ferme_de_roloux
import fleron
import floreffe
import funhelangues
import grace_hollogne
import hannut
import herstal
import huy
import iclub
import jeunesses_musicales
import lalouviere
import letssport
import mons
import namur
import neupre
import nivelles
import oupeye
import ottignieslln
import seraing
import sprimont
import supabase_client
import verviers
import village_des_benjamins
import vise
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
    ("Grace-Hollogne", grace_hollogne),
    ("Chaudfontaine", chaudfontaine),
    ("Mons", mons),
    ("Arlon", arlon),
    ("Bastogne", bastogne),
    ("Ferme de Roloux", ferme_de_roloux),
    ("Côté Campagne", cote_campagne),
    ("Village des Benjamins", village_des_benjamins),
    ("Ciney", ciney),
    ("La Louviere", lalouviere),
    ("Ottignies-Louvain-la-Neuve", ottignieslln),
    ("ADEPS", adeps),
    ("Cap Sciences", capsciences),
    ("iClub", iclub),
    ("Let's Sport", letssport),
    ("Dimension Sport", dimension_sport),
    ("Coordination ATL", coordination_atl),
    ("ADSL Stages", adsl_stages),
]

# Modules "en attente" : n'effectuent aucune requête réseau (voir chaque
# fichier pour la raison), mais apparaissent explicitement dans le résumé
# plutôt que d'être silencieusement absents.
EN_ATTENTE = [
    ("Floreffe", floreffe),
    ("Waremme", waremme),
    ("Hannut", hannut),
    ("Oupeye", oupeye),
    ("Aywaille", aywaille),
    ("Fléron", fleron),
    ("Esneux", esneux),
    ("Visé", vise),
    ("Jeunesses Musicales", jeunesses_musicales),
    ("CRIE de Liège", crie_liege),
    ("FunheLangues", funhelangues),
    ("Namur", namur),
    ("Nivelles", nivelles),
]

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

    for nom, module in EN_ATTENTE:
        print(f"--- {nom} ---")
        print(f"  EN_ATTENTE - {module.RAISON}")
        timings.append((nom, 0, 0.0, "EN_ATTENTE"))

    return all_activites, timings


def main() -> int:
    """Retourne un code de sortie (0 = tout va bien, 1 = à examiner) - utilisé
    par le workflow GitHub Actions pour afficher un run rouge en cas de
    problème réel (erreur d'import, ou chute anormale du nombre d'activités)."""
    all_activites, timings = run_scrapers()
    exit_code = 0

    json_path, csv_path = write_outputs(all_activites, OUT_DIR)

    print(f"\n=== Résumé ===")
    print(f"Total activités : {len(all_activites)}")
    for nom, n, elapsed, statut in timings:
        print(f"  {nom:10s} {n:3d} activités  {elapsed:6.2f}s  [{statut}]")
        if statut.startswith("ERREUR"):
            exit_code = 1
    print(f"\nSorties fichiers : {json_path} / {csv_path}")

    timing_path = OUT_DIR / "timings.txt"
    with timing_path.open("w", encoding="utf-8") as f:
        f.write("commune,activites,duree_secondes,statut\n")
        for nom, n, elapsed, statut in timings:
            f.write(f"{nom},{n},{elapsed:.2f},{statut}\n")

    print()
    if not supabase_client.is_configured():
        print("Supabase : scrapers/.env absent ou incomplet -> import et contrôle qualité ignorés (fichiers JSON/CSV seuls).")
        return exit_code

    print("--- Import Supabase ---")
    start = time.monotonic()
    try:
        rows = supabase_client.upsert_activites(all_activites)
        elapsed = time.monotonic() - start
        print(f"  {len(rows)} lignes upsertées dans `activites` en {elapsed:.2f}s")
    except Exception as exc:  # noqa: BLE001
        elapsed = time.monotonic() - start
        print(f"  ERREUR après {elapsed:.2f}s : {exc}")
        exit_code = 1

    print("\n--- Contrôle qualité ---")
    try:
        healthy, message = supabase_client.log_run_and_check_quality(len(all_activites))
        print(f"  {message}")
        if not healthy:
            exit_code = 1
    except Exception as exc:  # noqa: BLE001
        print(f"  ERREUR pendant le contrôle qualité : {exc}")
        exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
