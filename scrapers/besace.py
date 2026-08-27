"""Scraper Besace ASBL (Wix, Liège) - petits stages pour 2,5-6 ans.

Toute petite structure associative (un seul lieu, École Saint-Christophe à
Liège), à l'opposé des gros organismes déjà bien référencés (ADEPS...) -
exactement le type de source visé par le "ratissage" de petites structures.

Page unique en Wix (DOM très fragmenté, un <div>/<span> par mot ou presque -
non exploitable élément par élément) : extraction sur le texte à plat
(get_text), section "Prochains stages" repérée par regex, chaque entrée au
format "Du D au D mois AAAA <Titre> / <Lieu>". Le prix et la tranche d'âge
sont globaux (une seule mention sur toute la page, pas par stage).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, respectful_get

URL = "https://www.besace.be/stages-a-liege"
COMMUNE = "Liege"
ORGANISATEUR = "Besace ASBL"

AGE_RE = re.compile(r"([\d,]+)\s*à\s*(\d{1,2})\s*ans", re.I)
PRIX_SEMAINE_RE = re.compile(r"(\d+)\s*€\s*la\s+semaine", re.I)
PRIX_MATINEES_RE = re.compile(r"(\d+)\s*€\s*les\s+\d+\s*matin[ée]es", re.I)
MOIS = (
    "janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre"
)
# "Du 19 au 23 octobre 2026 Frissons, bonbons et petits fripons / École Libre Saint-Christophe - Liège"
STAGE_RE = re.compile(
    rf"Du\s+(\d{{1,2}})\s+au\s+(\d{{1,2}})\s+({MOIS})\s+(\d{{4}})\s+(.+?)\s*/\s*(.+?)(?=\s*Du\s+\d{{1,2}}\s+au|\s*Inscription\s+à\s+la\s+newsletter|$)",
    re.I,
)


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    full_text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()

    age_match = AGE_RE.search(full_text)
    age_min, age_max = (
        (float(age_match.group(1).replace(",", ".")), float(age_match.group(2))) if age_match else (2.5, 6.0)
    )

    prix_parts = []
    m = PRIX_SEMAINE_RE.search(full_text)
    if m:
        prix_parts.append(f"{m.group(1)}€ la semaine")
    m = PRIX_MATINEES_RE.search(full_text)
    if m:
        prix_parts.append(f"{m.group(1)}€ les 5 matinées")
    prix = " ; ".join(prix_parts) if prix_parts else "Non extrait automatiquement"

    # "Prochains stages" introduit la liste à venir - sans ce marqueur, on
    # retomberait sur "Stages d'été" plus haut sur la page (déjà passés).
    section = full_text.split("Prochains stages", 1)
    search_zone = section[1] if len(section) > 1 else full_text
    # Disponibilité cherchée dans cette même zone uniquement : le reste de la
    # page parle du stage d'été (déjà passé) et de sa propre disponibilité
    # ("complet"), sans rapport avec les prochains stages listés ici.
    disponibilite = extract_disponibilite(search_zone) or "Non communiqué sur cette page"

    activites: list[Activite] = []
    for j1, j2, mois, annee, titre, lieu in STAGE_RE.findall(search_zone):
        activites.append(
            Activite(
                commune=COMMUNE,
                organisateur=ORGANISATEUR,
                nom_activite=titre.strip().rstrip("/").strip(),
                type_activite=classify_type(titre.strip()),
                dates=f"du {j1} au {j2} {mois} {annee}",
                age_min=age_min,
                age_max=age_max,
                prix=prix,
                lieu=lieu.strip(),
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
