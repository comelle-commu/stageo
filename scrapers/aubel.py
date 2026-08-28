"""Scraper Aubel (Plone/iMio) - contrairement à Malmedy/Verlaine/Dalhem/
Wanze (impasses confirmées, voir docs/ratissage-province-liege-2026-08-28.md
section C2), Aubel a une page "Stages de vacances" à jour avec dates ET
âges directement dessus, groupés par période sous forme
"<p><strong>Du 19 au 23 octobre 2026</strong></p><ul><li>Titre (de X à Y
ans) - <a>Informations</a></li>...</ul>".

Le lieu n'est en revanche PAS sur cette page hub - seulement sur la page
"évènement" individuelle liée par "Informations" (bloc standard Plone
"Quand / Où / Catégories d'événements"), d'où un fetch supplémentaire par
stage (coûteux avec le Crawl-delay iMio de 120s, mais c'est la seule
source pour ce champ).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, find_plone_content, respectful_get

HUB_URL = (
    "https://www.aubel.be/fr/ma-commune/enfance/accueil-temps-libre-atl-2-5-ans-12-ans/"
    "stages/copy_of_stages-de-vacances"
)
COMMUNE = "Aubel"

MOIS = "janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"
DATE_RANGE_RE = re.compile(rf"Du\s+(\d{{1,2}})\s+au\s+(\d{{1,2}})\s+({MOIS})\s+(\d{{4}})", re.I)
AGE_RE = re.compile(r"\(de\s+(\d+)\s*à\s+(\d+)\s*ans\)", re.I)
LIEU_RE = re.compile(r"Où\s+(.+?)\s+Catégories d.événements", re.S)


def _fetch_lieu(url: str) -> str:
    resp = respectful_get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)
    text = re.sub(r"\s+", " ", main.get_text(" ", strip=True))
    m = LIEU_RE.search(text)
    return m.group(1).strip() if m else "Non précisé sur cette page"


def scrape() -> list[Activite]:
    resp = respectful_get(HUB_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)

    activites: list[Activite] = []
    current_dates = None
    for el in main.find_all(["p", "ul"]):
        if el.name == "p":
            m = DATE_RANGE_RE.search(el.get_text(" ", strip=True))
            if m:
                current_dates = f"du {m.group(1)} {m.group(3)} au {m.group(2)} {m.group(3)} {m.group(4)}"
            continue

        if current_dates is None:
            continue

        for li in el.find_all("li"):
            a = li.find("a")
            if a is None or "href" not in a.attrs:
                continue
            full_text = li.get_text(" ", strip=True)
            age_m = AGE_RE.search(full_text)
            age_min, age_max = (float(age_m.group(1)), float(age_m.group(2))) if age_m else (None, None)
            nom = full_text[: age_m.start()].strip(" -") if age_m else re.sub(r"-?\s*Informations\.?$", "", full_text).strip(" -")

            activites.append(
                Activite(
                    commune=COMMUNE,
                    nom_activite=nom,
                    type_activite=classify_type(nom),
                    dates=current_dates,
                    age_min=age_min,
                    age_max=age_max,
                    prix="Non communiqué sur cette page",
                    lieu=_fetch_lieu(a["href"]),
                    modalites_inscription="Voir la page évènement liée pour les modalités d'inscription",
                    disponibilite="Non communiqué sur cette page",
                    lien_source=a["href"],
                )
            )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
