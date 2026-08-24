"""Scraper ADEPS (activites.sport-adeps.be) - catalogue officiel des stages
sportifs de la Fédération Wallonie-Bruxelles.

Drupal, HTML rendu côté serveur, paginé (~20 stages/page, ~19 pages -> voir
docs/investigation-technique-organismes-2026-08-24.md pour la vérification).
Contrairement aux scrapers communaux, une activité ADEPS n'est pas rattachée
à une commune belge unique (elle peut se dérouler n'importe où, y compris à
l'étranger pour certains stages ADEPS) -> `commune` reste "" et le lieu
complet va dans `lieu` ; `organisateur` porte la source ("ADEPS").
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import Activite, respectful_get

BASE_URL = "https://activites.sport-adeps.be"
CATALOGUE_URL = f"{BASE_URL}/catalogue/stages"
ORGANISATEUR = "ADEPS"

MAX_PAGES_SAFETY = 60  # garde-fou si le pager change de forme un jour

AGE_RANGE_RE = re.compile(r"de\s+(\d+)\s*(?:ans)?\s+à\s+(\d+)\s*ans", re.I)
AGE_FROM_RE = re.compile(r"(?:à\s+partir\s+de|dès)\s+(\d+)\s*ans", re.I)
AGE_UP_TO_RE = re.compile(r"jusqu'?à\s+(\d+)\s*ans", re.I)


def _labelled_text(node, label: str) -> str:
    """Un champ ADEPS = <i/> + <div class="label">Label:</div> + texte brut
    en frère. get_text(" ") les joint proprement (séparateur espace, pas de
    mots collés) ; on retire juste le label lui-même ensuite."""
    if node is None:
        return ""
    text = node.get_text(" ", strip=True)
    return text.replace(label, "", 1).strip(" :")


def _parse_age(text: str) -> tuple[float | None, float | None]:
    m = AGE_RANGE_RE.search(text)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = AGE_FROM_RE.search(text)
    if m:
        return float(m.group(1)), None
    m = AGE_UP_TO_RE.search(text)
    if m:
        return None, float(m.group(1))
    return None, None


def _last_page_number(soup: BeautifulSoup) -> int:
    last_link = soup.select_one(".pager__item--last a")
    if not last_link or not last_link.get("href"):
        return 0
    m = re.search(r"page=(\d+)", last_link["href"])
    return int(m.group(1)) if m else 0


def _parse_row(article) -> Activite | None:
    title_link = article.select_one("h2.title a")
    if not title_link:
        return None
    nom = title_link.get_text(strip=True)
    lien_source = urljoin(BASE_URL, title_link.get("href", ""))

    stay = _labelled_text(article.select_one(".field-stay"), "Séjour:")
    if stay:
        nom = f"{nom} ({stay})"

    price_value = article.select_one(".price_value")
    price_info = article.select_one(".price_info")
    if price_value:
        prix = price_value.get_text(strip=True)
        if price_info and price_info.get_text(strip=True):
            prix = f"{prix} ({price_info.get_text(strip=True)})"
    else:
        prix = "Non communiqué sur cette page"

    age_text = _labelled_text(article.select_one(".field-ages"), "Âge:")
    age_min, age_max = _parse_age(age_text)

    lieu = _labelled_text(article.select_one(".field-center"), "Centre:") or (
        "Non précisé sur cette page"
    )

    date_paragraphs = article.select(".field-date p")
    dates = " ".join(p.get_text(strip=True) for p in date_paragraphs) or "Non précisées"

    # Le badge "no_availableseats" n'est présent QUE quand le stage est
    # complet (vérifié : 12/20 lignes avec badge sur la page 1, 8 sans -
    # absence de badge = places disponibles, jamais l'inverse).
    complet = article.select_one(".badge.no_availableseats") is not None
    disponibilite = "Complet" if complet else "Places disponibles"

    return Activite(
        commune="",
        organisateur=ORGANISATEUR,
        nom_activite=nom,
        dates=dates,
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu=lieu,
        modalites_inscription=(
            "Inscription en ligne via le catalogue Adeps "
            "(compte 'Mon Adeps' requis, voir am-sport.cfwb.be)"
        ),
        disponibilite=disponibilite,
        lien_source=lien_source,
    )


def scrape() -> list[Activite]:
    resp = respectful_get(CATALOGUE_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    last_page = min(_last_page_number(soup), MAX_PAGES_SAFETY)

    activites: list[Activite] = []
    for row in soup.select(".views-row"):
        article = row.select_one("article")
        if article is None:
            continue
        a = _parse_row(article)
        if a is not None:
            activites.append(a)

    for page_num in range(1, last_page + 1):
        resp = respectful_get(f"{CATALOGUE_URL}?page={page_num}")
        soup = BeautifulSoup(resp.text, "lxml")
        for row in soup.select(".views-row"):
            article = row.select_one("article")
            if article is None:
                continue
            a = _parse_row(article)
            if a is not None:
                activites.append(a)

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités", flush=True)
    for a in result[:3]:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
