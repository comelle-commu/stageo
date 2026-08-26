"""Scraper ADSL Stages (organisme privé, stages pour enfants dans une
quarantaine de localités - Hainaut, Luxembourg, Namur et Brabant wallon
principalement).

robots.txt quasi vide (juste un commentaire, aucune règle) -> crawl
générique autorisé. Page HTML statique, une carte par stage avec tout ce
qu'il faut déjà dessus (âge, commune, lieu, dates, prix) - pas besoin de
visiter les pages détail individuelles, contrairement à Let's Sport ou
Dimension Sport.

Le site liste ses stages par "région" (en fait une commune ou un
sous-programme comme "Charleroi Extrascolaire") via `?search[region]=ID`,
paginé (9 cartes/page). Les IDs de région sont listés en dur ci-dessous
(extraits une fois depuis la page /stages, même logique que SITES dans
letssport.py) plutôt que redécouverts à chaque run - liste volontairement
figée, à mettre à jour manuellement si ADSL ajoute une localité. "Espagne"
(région étrangère) est explicitement exclue du périmètre Wallonie/Bruxelles
du projet.

Chaque région peut avoir plusieurs pages (jusqu'à 4 vues en pratique pour
Arlon) - on pagine jusqu'à une page vide, avec un plafond de sécurité par
région pour rester dans l'esprit "poignée de requêtes" du projet plutôt
qu'une boucle non bornée.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

BASE_URL = "https://inscriptions.adslstages.be"
ORGANISATEUR = "ADSL Stages"
MAX_PAGES_PER_REGION = 8

# (id de région ADSL, nom affiché) - extraits le 26/08/2026 depuis la liste
# de filtres de https://inscriptions.adslstages.be/stages. "Espagne"
# (id=83) volontairement absente (hors Wallonie/Bruxelles).
REGIONS = [
    (70, "Arlon"), (1, "Ath"), (93, "Beaumont"), (103, "Beloeil"), (30, "Bertrix"),
    (72, "Champion"), (94, "Champion Parascolaire"), (2, "Charleroi"), (101, "Charleroi Extrascolaire"),
    (23, "Dinant"), (5, "Eghezée"), (26, "Enghien"), (6, "Erpent"),
    (27, "Estaimpuis"), (108, "Estaimpuis Extrascolaire"), (41, "Etalle"),
    (38, "Floreffe"), (109, "Floreffe Extrascolaire"), (106, "Florennes"),
    (74, "Forchies"), (99, "Forchies Extrascolaire"), (88, "Gedinne"),
    (9, "Gembloux"), (10, "Gosselies"), (75, "Habay-la-Neuve"), (77, "Jambes"),
    (12, "Jurbise"), (78, "Libramont"), (92, "Lonzée"), (96, "Mettet"),
    (98, "Mettet Extrascolaire"), (14, "Mons"), (100, "Mons Extrascolaire"),
    (15, "Mouscron"), (16, "Namur"), (17, "Nivelles"), (80, "Quevaucamps"),
    (76, "Rouvroy"), (81, "Saint-Ghislain"), (19, "Tournai"), (21, "Waterloo"),
]

_AGE_RE = re.compile(r"(\d{1,2}(?:[.,]\d+)?)\s*-\s*(\d{1,2}(?:[.,]\d+)?)\s*ans?", re.I)


def _text(el) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _parse_card(card) -> Optional[Activite]:
    href = card.get("href")
    if not href:
        return None
    lien_source = urljoin(BASE_URL, href)

    age_text = _text(card.select_one(".card-header span"))
    nom_activite = _text(card.select_one(".card-header h3"))
    if not nom_activite:
        return None

    items = card.select(".card-body .card-item")
    commune = _text(items[0].find("h4")) if len(items) > 0 else ""
    lieu = _text(items[0].find("p")) if len(items) > 0 else ""
    date_label = _text(items[1].find("h4")) if len(items) > 1 else ""
    date_text = _text(items[1].find("p")) if len(items) > 1 else ""
    prix_montant = _text(items[2].find("h4")) if len(items) > 2 else ""
    prix_unite = _text(items[2].find("p")) if len(items) > 2 else ""

    age_min, age_max = None, None
    m = _AGE_RE.search(age_text)
    if m:
        age_min, age_max = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))

    dates = f"{date_text} ({date_label})" if date_label and date_label not in date_text else (date_text or date_label or "Non précisées")
    prix = f"{prix_montant} {prix_unite}".strip() if prix_montant else "Non communiqué sur cette page"

    return Activite(
        commune=commune,
        organisateur=ORGANISATEUR,
        nom_activite=nom_activite,
        type_activite=classify_type(nom_activite, ORGANISATEUR),
        dates=dates,
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu=lieu or commune,
        modalites_inscription="Inscription en ligne (voir lien source)",
        disponibilite="Non communiqué sur cette page",
        lien_source=lien_source,
    )


def _scrape_region(region_id: int, region_name: str) -> list[Activite]:
    activites: list[Activite] = []
    for page in range(1, MAX_PAGES_PER_REGION + 1):
        url = f"{BASE_URL}/stages?search%5Bregion%5D={region_id}"
        if page > 1:
            url += f"&page={page}"
        resp = respectful_get(url)
        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select("a.card-link")
        if not cards:
            break
        for card in cards:
            activite = _parse_card(card)
            if activite is not None:
                activites.append(activite)
        if len(cards) < 9:  # taille de page habituelle -> probablement la dernière
            break
    return activites


def scrape() -> list[Activite]:
    activites: list[Activite] = []
    seen_ids: set[str] = set()

    for region_id, region_name in REGIONS:
        try:
            for activite in _scrape_region(region_id, region_name):
                stage_id = activite.lien_source.rstrip("/").rsplit("/", 1)[-1]
                if stage_id in seen_ids:
                    continue  # un même stage peut apparaître dans plusieurs "régions" proches
                seen_ids.add(stage_id)
                activites.append(activite)
        except Exception as exc:  # noqa: BLE001 - une localité en panne ne doit pas bloquer les autres
            print(f"  [ADSL Stages] {region_name} ignorée (erreur : {exc})")

    return activites


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} activités extraites")
    for a in results[:10]:
        print(a)
