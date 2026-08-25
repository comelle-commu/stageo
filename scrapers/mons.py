"""Scraper Mons (Plone/iMio) - plaines de vacances communales, page d'été.

Page unique en prose (comme Ans) : une liste de semaines ("Quand ?") et une
liste de lieux ("Où ?") décrites en texte libre, pas de tableau structuré.
Une activité par semaine, avec les 3 lieux combinés (la page ne distingue
pas quelle semaine a lieu à quel endroit précisément).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, find_plone_content, respectful_get

URL = (
    "https://www.mons.be/fr/vivre-a-mons/education-extrascolaire/extrascolaire/"
    "plaines-de-vacances-communales-1/les-plaines-de-vacances-ete"
)
COMMUNE = "Mons"

WEEK_RE = re.compile(
    r"Du\s+\w+\s+(\d{1,2})(?:\s+(\w+))?\s+au\s+\w+\s+(\d{1,2})\s+(\w+)"
    r"(?:\s*\(([^)]*)\))?",
    re.I,
)
AGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*à\s*(\d+(?:[.,]\d+)?)\s*ans", re.I)
PRICE_RE = re.compile(r"([\d.,]+\s*€\s*par\s*jour)", re.I)
YEAR_RE = re.compile(r"\b(20\d{2})\b")


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)
    full_text = main.get_text(" ", strip=True)

    year_match = YEAR_RE.search(full_text)
    year = year_match.group(1) if year_match else "2026"

    age_match = AGE_RE.search(full_text)
    age_min = float(age_match.group(1).replace(",", ".")) if age_match else None
    age_max = float(age_match.group(2).replace(",", ".")) if age_match else None

    prices = PRICE_RE.findall(full_text)
    prix = " / ".join(prices) if prices else "Non extrait automatiquement (voir page source)"

    lieu_match = re.search(r"Où\s*\?\s*(.+?)Les activités se déroulent", full_text)
    lieu = lieu_match.group(1).strip(" ;") if lieu_match else "Non précisé sur cette page"

    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    activites: list[Activite] = []
    for m in WEEK_RE.finditer(full_text):
        d1, month1, d2, month2, note = m.groups()
        month1 = month1 or month2
        dates = f"du {d1} {month1} {year} au {d2} {month2} {year}"
        if note:
            dates += f" ({note})"
        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=f"Plaines de vacances Mons - Été {year} - Semaine du {d1} {month1}",
                type_activite=classify_type("Plaines de vacances Mons"),
                dates=dates,
                age_min=age_min,
                age_max=age_max,
                prix=prix,
                lieu=lieu,
                modalites_inscription="Pré-inscription en ligne obligatoire (formulaire sur la page source)",
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
