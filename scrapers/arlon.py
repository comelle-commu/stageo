"""Scraper Arlon (Plone/iMio) - plaines de vacances (page unique, 2 périodes
actuellement listées : printemps et été), texte libre comme Ans/Mons.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, extract_disponibilite, find_plone_content, respectful_get

URL = "https://www.arlon.be/loisirs/activites/plaines"
COMMUNE = "Arlon"

# Un bloc = "Des plaines de <periode> pour tous !" jusqu'au bloc suivant (ou fin).
BLOCK_RE = re.compile(r"Des plaines d[e']\s*(\S+)\s+pour tous\s*!(.*?)(?=Des plaines d[e']|\Z)", re.I | re.S)
DATES_RE = re.compile(r"Dates et horaires\s*:\s*(du .+?)(?:\.|Tarif)", re.I)
AGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*ans?\s*à\s*(\d+(?:[.,]\d+)?)\s*ans", re.I)
PRICE_RE = re.compile(r"Tarif\s*:\s*([^.]+\.)", re.I)
LIEU_RE = re.compile(r"Deux implantations\s*:\s*(.+?)Infos pratiques", re.I)


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)
    full_text = main.get_text(" ", strip=True)

    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    activites: list[Activite] = []
    for m in BLOCK_RE.finditer(full_text):
        periode, body = m.groups()

        dates_match = DATES_RE.search(body)
        dates = dates_match.group(1).strip() if dates_match else "Non précisées"

        age_match = AGE_RE.search(body)
        age_min = float(age_match.group(1).replace(",", ".")) if age_match else None
        age_max = float(age_match.group(2).replace(",", ".")) if age_match else None

        price_match = PRICE_RE.search(body)
        prix = price_match.group(1).strip() if price_match else "Non extrait automatiquement (voir page source)"

        lieu_match = LIEU_RE.search(body)
        lieu = lieu_match.group(1).strip(" :") if lieu_match else "Non précisé sur cette page"

        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=f"Plaines de vacances Arlon - {periode.capitalize()}",
                dates=dates,
                age_min=age_min,
                age_max=age_max,
                prix=prix,
                lieu=lieu,
                modalites_inscription="Inscription auprès du Service Jeunesse (+32 63 41 25 15)",
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
