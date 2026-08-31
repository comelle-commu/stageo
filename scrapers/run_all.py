"""Orchestrateur : lance le scraper de chaque commune, chronomètre, agrège,
écrit les sorties JSON/CSV dans output/, ET upsert dans Supabase si
scrapers/.env est configuré (voir docs/supabase-backend-2026-08-24.md).

Usage: venv/bin/python3 run_all.py
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import adeps
import adsl_stages
import agenda_omnia
import ans
import arlon
import ateliers04
import aubange
import aubel
import aywaille
import bastogne
import besace
import capsciences
import cfs
import chaudfontaine
import ciney
import coordination_atl
import cote_campagne
import crie_liege
import dimension_sport
import esneux
import faimes
import ferme_de_roloux
import ferme_des_enfants
import fleron
import floreffe
import forest
import funhelangues
import grace_hollogne
import hannut
import herstal
import hesl
import huy
import iclub
import jalhay
import jeunesse_a_bruxelles
import jeunesse_ardente
import jeunesses_musicales
import lalouviere
import letssport
import mestempslibres
import mons
import namur
import neupre
import nivelles
import oupeye
import ottignieslln
import pari
import reform
import seraing
import sprimont
import rhcv
import stavelot
import tccb
import supabase_client
import uccle
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
    ("Aubange", aubange),
    ("Aubel", aubel),
    ("Jalhay", jalhay),
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
    ("Forest", forest),
    ("Uccle", uccle),
    ("Besace ASBL", besace),
    ("Jeunesse Ardente", jeunesse_ardente),
    ("Agenda Omnia (multi-communes)", agenda_omnia),
    ("Stavelot", stavelot),
    ("Royal Hockey Club Verviers", rhcv),
    ("TC Cheval Blanc", tccb),
    ("Faimes", faimes),
    ("La Ferme des Enfants de Liège", ferme_des_enfants),
    ("Mes Temps Libres (Anthisnes, Comblain-au-Pont)", mestempslibres),
    ("PARI asbl", pari),
    ("Les Ateliers 04", ateliers04),
    ("HESL (Hannut)", hesl),
    ("ReForm asbl (multi-régions)", reform),
    ("Le CFS asbl (Awans, Huy, Verlaine)", cfs),
]

# Modules "en attente" : n'effectuent aucune requête réseau (voir chaque
# fichier pour la raison), mais apparaissent explicitement dans le résumé
# plutôt que d'être silencieusement absents.
EN_ATTENTE = [
    ("Jeunesse à Bruxelles", jeunesse_a_bruxelles),
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
    """Lance chaque scraper EN PARALLÈLE (un thread par scraper - le goulot
    est le réseau, pas le CPU), retourne (toutes les activités, timings).

    Le respect du Crawl-delay par domaine (voir common.respectful_get)
    reste garanti même en parallèle : chaque domaine a son propre verrou,
    donc deux scrapers visitant des domaines différents avancent en même
    temps, mais deux requêtes vers LE MÊME domaine restent strictement
    séquentielles avec le délai imposé - identique au comportement
    séquentiel d'avant, juste sans attendre bêtement qu'un scraper lent
    finisse avant de commencer le suivant.

    Passage au parallélisme le 31/08/2026 après diagnostic d'un run
    programmé qui n'aboutissait plus : Aubel (7 fetches vers aubel.be,
    120s de Crawl-delay chacun) et Agenda Omnia (jusqu'à 18 communes,
    plusieurs fetches par commune) consommaient à eux deux plus de 27
    minutes en série, sans qu'aucun des deux ne soit en tort - juste
    l'exécution séquentielle qui forçait tous les autres scrapers,
    strictement indépendants, à attendre leur tour pour rien."""
    all_activites = []
    timings = []

    def _run_one(nom: str, module) -> tuple[str, list, float, Optional[Exception]]:
        start = time.monotonic()
        try:
            activites = module.scrape()
            elapsed = time.monotonic() - start
            return nom, activites, elapsed, None
        except Exception as exc:  # noqa: BLE001 - on veut que les autres communes tournent quand même
            elapsed = time.monotonic() - start
            return nom, [], elapsed, exc

    results: dict[str, tuple[int, float, str]] = {}

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(_run_one, nom, module): nom for nom, module in SCRAPERS}
        for future in as_completed(futures):
            nom, activites, elapsed, exc = future.result()
            print(f"--- {nom} ---")
            if exc is None:
                print(f"  {len(activites)} activités extraites en {elapsed:.2f}s")
                statut = "OK"
            else:
                print(f"  ERREUR après {elapsed:.2f}s : {exc}")
                statut = f"ERREUR: {exc}"
            results[nom] = (len(activites), elapsed, statut)
            all_activites.extend(activites)

    # Résumé final dans l'ordre de SCRAPERS (pas l'ordre d'arrivée, qui
    # varie d'un run à l'autre) - plus facile à comparer entre deux runs.
    for nom, _module in SCRAPERS:
        n, elapsed, statut = results[nom]
        timings.append((nom, n, elapsed, statut))

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
