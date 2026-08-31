"""Scraper HESL (Hannut Education Sports et Loisirs asbl) - stages à
Hannut, publiés via le plugin WordPress "Events Manager".

La page d'accueil liste, dans son menu (`li.page_item`), UNE page par
semaine de stage organisée depuis 2021 (~90 liens au 31/08/2026) - aucune
page "catalogue" unique à scraper. Pré-filtre sur le libellé du lien
(contient l'année en cours ou la suivante) pour éviter de télécharger des
dizaines de pages manifestement passées ; le filtrage définitif se fait
ensuite sur la vraie date lue dans le <h2> de chaque page ("Durant la
semaine du 19 octobre 2026 - 25 octobre 2026") - bien plus fiable que le
libellé du menu, qui omet parfois l'année ou le jour exact.

Sur chaque page retenue, une table par activité (nom + lien + liste
d'âges + prix) - l'échelle d'âge est une liste d'entiers ("6 ans", "7
ans"...) plutôt qu'un intervalle "X à Y ans" comme ailleurs : on prend
juste le min/max de la liste.
"""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

PAGE_URL = "https://hesl.org/"
ORGANISATEUR = "Hannut Education Sports et Loisirs (HESL) asbl"
COMMUNE = "Hannut"

MOIS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12, "decembre": 12,
}
_MOIS_RE = "|".join(MOIS.keys())
LAST_DATE_RE = re.compile(rf"(\d{{1,2}})\s+({_MOIS_RE})\s+(\d{{4}})", re.IGNORECASE)
AGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*ans", re.IGNORECASE)


def _end_date(text: str) -> date | None:
    matches = LAST_DATE_RE.findall(text or "")
    if not matches:
        return None
    d, mois, y = matches[-1]
    try:
        return date(int(y), MOIS[mois.lower()], int(d))
    except ValueError:
        return None


def _candidate_links() -> list[tuple[str, str]]:
    resp = respectful_get(PAGE_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    today = date.today()
    years = {str(today.year), str(today.year + 1)}
    out = []
    for a in soup.select("li.page_item > a"):
        label = a.get_text(strip=True)
        href = a.get("href")
        if href and any(y in label for y in years):
            out.append((label, href))
    return out


def _scrape_week_page(href: str) -> list[Activite]:
    resp = respectful_get(href)
    soup = BeautifulSoup(resp.text, "lxml")
    article = soup.find("article")
    if not article:
        return []

    h2 = article.find("h2")
    date_range_text = h2.get_text(strip=True) if h2 else ""
    end = _end_date(date_range_text)
    if end is None or end < date.today():
        return []  # page passee ou date illisible - on prefere ignorer plutot que deviner

    activites = []
    for table in article.find_all("table"):
        link = table.find("a")
        if not link:
            continue
        nom = link.get_text(strip=True)
        if not nom:
            continue
        lien = link.get("href") or href

        ages = [float(m.replace(",", ".")) for m in AGE_RE.findall(table.get_text(" "))]
        age_min = min(ages) if ages else None
        age_max = max(ages) if ages else None

        price_cell = table.find("td", class_=re.compile(r"^dispo"))
        prix = price_cell.get_text(strip=True) if price_cell else "Non communiqué sur cette page"

        activites.append(
            Activite(
                commune=COMMUNE,
                organisateur=ORGANISATEUR,
                nom_activite=nom,
                type_activite=classify_type(nom, ORGANISATEUR),
                dates=date_range_text or "Non communiqué sur cette page",
                age_min=age_min,
                age_max=age_max,
                prix=prix,
                lieu="Hannut (lieu précis selon l'activité - voir HESL)",
                modalites_inscription=f"Inscription en ligne : {lien}",
                disponibilite="Non communiqué sur cette page",
                lien_source=lien,
            )
        )
    return activites


def scrape() -> list[Activite]:
    activites: list[Activite] = []
    for _label, href in _candidate_links():
        activites.extend(_scrape_week_page(href))
    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
