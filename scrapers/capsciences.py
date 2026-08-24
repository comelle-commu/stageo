"""Scraper Cap Sciences (capsciences.be) - stages de vacances (multi-thèmes,
souvent co-organisés avec des partenaires comme Action Sport/PromoSport,
republiés sous la marque Cap Sciences).

WordPress + plugin "WP Grid Builder" (grille filtrable), mais la liste
complète est déjà présente dans le HTML statique (vérifié : 200 fiches en un
seul GET, pas de pagination/chargement JS supplémentaire nécessaire - voir
docs/investigation-technique-organismes-2026-08-24.md). robots.txt déclare
Crawl-delay: 10 (voir common.CRAWL_DELAYS) - à respecter.

Le prix n'est indiqué ni sur cette page ni sur les fiches individuelles
testées -> `prix` reste "Non communiqué sur cette page", comme pour les
sites communaux où l'info n'est pas publiée en clair.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import Activite, respectful_get

URL = "https://www.capsciences.be/stages-de-vacances/"
BASE_URL = "https://www.capsciences.be"
ORGANISATEUR = "Cap Sciences"

AGE_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*ans", re.I)
DATE_RE = re.compile(r"(\d{2})/(\d{2})\s*-\s*(\d{2})/(\d{2})/(\d{2})")


def _parse_age(text: str) -> tuple[float | None, float | None]:
    m = AGE_RE.search(text)
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))


def _parse_dates(text: str) -> str:
    m = DATE_RE.search(text)
    if not m:
        return text.strip() or "Non précisées"
    d1, m1, d2, m2, yy = m.groups()
    year = f"20{yy}"
    return f"du {d1}/{m1}/{year} au {d2}/{m2}/{year}"


def _parse_card(card) -> Activite | None:
    cells = card.select("span.tc")
    if len(cells) < 6:
        return None

    lieu = cells[1].get_text(strip=True)
    age_text = cells[2].get_text(strip=True)
    date_text = cells[3].get_text(strip=True)
    theme = cells[4].get_text(strip=True)
    activite_sport = cells[5].get_text(strip=True)

    nom = theme
    if activite_sport and activite_sport != "/":
        nom = f"{theme} - {activite_sport}"

    format_label = None
    if len(cells) >= 7:
        tooltip = cells[6].select_one(".tooltiptext")
        format_label = tooltip.get_text(strip=True) if tooltip else None
    if format_label:
        nom = f"{nom} ({format_label})"

    age_min, age_max = _parse_age(age_text)
    href = card.get("href", "")
    lien_source = urljoin(BASE_URL, href.split("?")[0])

    complet = "complet" in (card.get("class") or [])
    disponibilite = "Complet" if complet else "Places disponibles"

    return Activite(
        # `lieu` ici est déjà un nom de commune belge simple (Auderghem,
        # Ixelles, Nivelles...) sur cette source - contrairement à l'ADEPS,
        # on peut donc le réutiliser directement comme `commune`.
        commune=lieu,
        organisateur=ORGANISATEUR,
        nom_activite=nom,
        dates=_parse_dates(date_text),
        age_min=age_min,
        age_max=age_max,
        prix="Non communiqué sur cette page",
        lieu=lieu,
        modalites_inscription="Inscription en ligne via la fiche du stage (lien source)",
        disponibilite=disponibilite,
        lien_source=lien_source,
    )


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    container = soup.select_one(".grid_products_container")
    if container is None:
        return []

    activites: list[Activite] = []
    seen_links: set[str] = set()
    for card in container.select("a.product"):
        href = card.get("href", "")
        if href in seen_links:
            continue
        seen_links.add(href)
        a = _parse_card(card)
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
