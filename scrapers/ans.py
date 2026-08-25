"""Scraper Ans (Plone/iMio) - CCJV (Centres communaux de jeux de vacances).

Page unique, HTML statique. Extrait une ligne par semaine de vacances d'été
listée sur la page (seule période avec des dates calendaires précises ; les
autres périodes - Automne, Hiver, Détente, Printemps - sont mentionnées sans
dates exactes sur cette page et ne sont donc pas extraites ici).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, find_plone_content, respectful_get

URL = (
    "https://www.ans-ville.be/que-faire/stages-plaines-activites/"
    "centres-communaux-de-jeux-de-vacances-ccjv/ccjv"
)
COMMUNE = "Ans"

WEEK_RE = re.compile(
    r"Semaine\s*(\d+)\s*:\s*du\s*(\d{2}/\d{2}/\d{2})\s*au\s*(\d{2}/\d{2}/\d{2})"
    r"(?:\s*\(([^)]*)\))?",
    re.I,
)
PRICE_RE = re.compile(
    r"fixés?\s+à\s+([\d.,]+\s*€[^.(]*)(?:\(([^)]*)\))?", re.I
)


def _to_iso_year(yy: str) -> str:
    return f"20{yy}" if len(yy) == 2 else yy


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)

    full_text = main.get_text(" ", strip=True)
    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    price_match = PRICE_RE.search(full_text)
    if price_match:
        base = price_match.group(1).strip(" .;")
        extra = f" ({price_match.group(2).strip()})" if price_match.group(2) else ""
        prix = f"{base}{extra}"
    else:
        prix = "Non extrait automatiquement (voir page source)"

    theme_match = re.search(r'THEME\s*:\s*"([^"]+)"', full_text)
    theme = theme_match.group(1).strip() if theme_match else None

    activites: list[Activite] = []
    for li in main.find_all("li"):
        m = WEEK_RE.search(li.get_text(" ", strip=True))
        if not m:
            continue
        num, d1, d2, note = m.groups()
        d1_full = d1[:-2] + _to_iso_year(d1[-2:])
        d2_full = d2[:-2] + _to_iso_year(d2[-2:])
        dates = f"du {d1_full} au {d2_full}" + (f" ({note})" if note else "")
        nom = f"CCJV Ans - Vacances d'été 2026 - Semaine {num}"
        if theme:
            nom += f' (thème : "{theme}")'
        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=nom,
                type_activite=classify_type(nom),
                dates=dates,
                age_min=None,
                age_max=None,
                prix=prix,
                lieu="Site communiqué au 1er jour d'inscription (non précisé sur cette page)",
                modalites_inscription=(
                    "Compte Itsme + création de compte sur l'e-guichet "
                    "(https://ans.guichet-citoyen.be/), onglet « Portail parent »"
                ),
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
