"""Scraper Forest (commune bruxelloise, Drupal) - Plaine de vacances + stages.

Page unique, texte structuré en questions/paragraphes (pas de HTML
sémantique par activité, contrairement aux sites iMio). Deux offres
distinctes sur la même page :
- La "plaine de vacances" (2,5-12 ans), continue sur toute la période
  annoncée (une ligne, bornée par la première et la dernière date citées).
- Les "STAGES" nommés (une ligne par stage, avec sa propre tranche d'âge et
  ses propres dates communes aux trois).

⚠️ Au 27/08/2026, la page ne couvre que le "Congé d'été 2026" (déjà passé) -
la commune ne semble publier chaque période qu'à l'approche de celle-ci
(cf. texte de la page : "trois semaines avant la période des vacances").
Le scraper reste volontairement générique (pas de mot "été" en dur dans les
regex) : dès que la page sera mise à jour pour la Toussaint, le prochain run
hebdomadaire réextraira les nouvelles dates sans changement de code.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, respectful_get

URL = "https://forest.brussels/fr/themes/enfance-jeunesse-seniors/loisirsactivites/plaines-de-vacances-stages"
COMMUNE = "Forest"

# "du lundi 6/07 au vendredi 10/07 : 5 jours" / "du mercredi 22/07 au vendredi 24/07 : 3 jours"
PERIODE_RE = re.compile(
    r"du\s+\w+\s+(\d{1,2}/\d{1,2})\s+au\s+\w+\s+(\d{1,2}/\d{1,2})\s*:\s*\d+\s*jours?",
    re.I,
)
# "âgés de 2,5 ans (qui ont acquis ... scolarisés) à 12 ans" - le nombre de
# tête peut avoir une décimale (2,5), et un membre de phrase entier sépare
# souvent les deux bornes (piège rencontré : un \d{1,2}...à...\d{1,2} générique
# matchait d'abord la tranche d'âge du premier stage nommé plus bas sur la page).
AGE_GLOBAL_RE = re.compile(r"âgés?\s+de\s+([\d,]+)\s*ans\s*\([^)]*\)\s*à\s*(\d{1,2})\s*ans", re.I)
PRIX_JOUR_RE = re.compile(r"(\d+)\s*€\s*/\s*jour", re.I)
PRIX_SEMAINE_RE = re.compile(r"(\d+)\s*eur\w*\s*la\s+semaine", re.I)
# "Du lundi 17/08 au jeudi 20/08"
STAGE_DATES_RE = re.compile(r"Du\s+\w+\s+(\d{1,2}/\d{1,2})\s+au\s+\w+\s+(\d{1,2}/\d{1,2})", re.I)
# "stage pour les 4 à 5 ans « les Petits scientifiques »"
STAGE_RE = re.compile(
    r"stage\s+pour\s+les\s+(\d{1,2})\s*à\s*(\d{1,2})\s*ans\s*[«\"]\s*([^»\"]+?)\s*[»\"]",
    re.I,
)


def _year_hint(text: str) -> str:
    m = re.search(r"\b(20\d{2})\b", text)
    return m.group(1) if m else ""


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = soup.find("main") or soup
    full_text = re.sub(r"\s+", " ", main.get_text(" ")).strip()

    year = _year_hint(full_text)
    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    activites: list[Activite] = []

    # --- Plaine de vacances (une ligne, bornée sur l'ensemble des périodes) ---
    periodes = PERIODE_RE.findall(full_text)
    if periodes:
        premiere = periodes[0][0]
        derniere = periodes[-1][1]
        dates_plaine = f"du {premiere}{'/' + year if year else ''} au {derniere}{'/' + year if year else ''} (plusieurs semaines, voir programme complet)"
    else:
        dates_plaine = "Non extrait automatiquement"

    age_global = AGE_GLOBAL_RE.search(full_text)
    age_min_g, age_max_g = (
        (float(age_global.group(1).replace(",", ".")), float(age_global.group(2))) if age_global else (2.5, 12.0)
    )

    prix_jour_matches = PRIX_JOUR_RE.findall(full_text)
    prix_plaine = (
        " ; ".join(f"{p}€/jour" for p in dict.fromkeys(prix_jour_matches)) + " (+5€ sorties avec intervenant externe)"
        if prix_jour_matches
        else "Non extrait automatiquement"
    )

    activites.append(
        Activite(
            commune=COMMUNE,
            nom_activite="Plaine de vacances - École du Bempt",
            type_activite=classify_type("Plaine de vacances multi-activités"),
            dates=dates_plaine,
            age_min=age_min_g,
            age_max=age_max_g,
            prix=prix_plaine,
            lieu="École communale du Bempt, chaussée de Neerstalle 273, 1190 Forest",
            modalites_inscription="Inscription en ligne (voir page source)",
            disponibilite=disponibilite,
            lien_source=URL,
        )
    )

    # --- Stages nommés (une ligne par stage) ---
    # Cherché uniquement APRÈS le marqueur "STAGES" : sinon STAGE_DATES_RE
    # matche d'abord la toute première période de la plaine plus haut sur la
    # page (même forme "du <jour> D/M au <jour> D/M").
    stages_section = full_text.split("STAGES", 1)[-1] if "STAGES" in full_text else ""
    stage_dates_match = STAGE_DATES_RE.search(stages_section)
    dates_stages = (
        f"du {stage_dates_match.group(1)}{'/' + year if year else ''} au {stage_dates_match.group(2)}{'/' + year if year else ''}"
        if stage_dates_match
        else dates_plaine
    )
    prix_semaine_match = PRIX_SEMAINE_RE.search(stages_section)
    prix_stage = f"{prix_semaine_match.group(1)}€/semaine" if prix_semaine_match else "Non extrait automatiquement"

    for age_min, age_max, nom in STAGE_RE.findall(stages_section):
        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=f"Stage {nom.strip()}",
                type_activite=classify_type(nom.strip()),
                dates=dates_stages,
                age_min=float(age_min),
                age_max=float(age_max),
                prix=prix_stage,
                lieu="École communale du Bempt, chaussée de Neerstalle 273, 1190 Forest",
                modalites_inscription="Inscription en ligne (voir page source)",
                disponibilite=disponibilite,
                lien_source=URL,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
