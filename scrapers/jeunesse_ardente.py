"""Scraper Jeunesse Ardente (WordPress, Liège) - annuaire de stages multi-organisateurs.

Contrairement aux autres sources de ce module, ce n'est pas UN organisme qui
publie ses propres stages, mais un annuaire communal (Ville de Liège) qui
agrège les offres de dizaines de petites structures locales (écoles de
sport, ASBL culturelles, clubs...) - exactement le type de source visé par
le ratissage de "petites structures" plutôt que les gros organismes déjà
connus. Chaque stage garde son organisateur d'origine dans `organisateur`.

Pagination WordPress classique (`/stages/page/N/`), ~6 pages pour ~56
résultats au 27/08/2026 - dans les clous de la politique "poignée de
requêtes" (un Crawl-delay non déclaré dans le robots.txt -> DEFAULT_MIN_DELAY
de common.py suffit).

DOM propre et stable (`div.areas` par carte, sous-blocs `area1`/`area2`/
`area3`) - extraction par sélecteurs CSS plutôt que par regex sur texte à
plat, contrairement à la plupart des autres scrapers de ce dossier.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, respectful_get

BASE_URL = "https://www.jeunesse-ardente.be/stages/"
COMMUNE = "Liege"
MAX_PAGES = 10  # garde-fou - la pagination réelle (~6 pages) s'arrête avant

# Organisateurs déjà couverts par leur propre scraper dédié (adeps.py,
# letssport.py) - présents aussi dans cet annuaire puisqu'il agrège TOUT.
# Sans ce filtre, leurs stages seraient dupliqués (deux lignes pour la même
# activité réelle, avec un lien_source différent donc pas dédupliqués par la
# contrainte unique Supabase). Comparaison insensible à la casse/accents
# simplifiée par un .lower() suffisant pour ces deux noms.
ORGANISATEURS_DEJA_COUVERTS = {"adeps", "let's sport"}

DATE_RE = re.compile(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})")
AGE_RE = re.compile(r"(?:[Aa]\s+partir\s+de\s*)?(\d{1,2})\s*ans(?:.*?(\d{1,2})\s*ans)?", re.S)
PRIX_RE = re.compile(r"([\d.,]+)\s*€")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _num_pages(soup: BeautifulSoup) -> int:
    numbers = [int(a.get_text(strip=True)) for a in soup.select("a") if a.get_text(strip=True).isdigit()]
    return max(numbers) if numbers else 1


def _parse_card(card) -> Activite | None:
    area1, area2, area3 = card.find("div", class_="area1"), card.find("div", class_="area2"), card.find("div", class_="area3")
    if not (area1 and area2 and area3):
        return None

    organisateur_p = area1.find("p")
    organisateur = _clean(organisateur_p.get_text(" ")).replace("Organisé par :", "").strip() if organisateur_p else "Non précisé"

    title_a = area2.find("h3")
    nom_activite = _clean(title_a.get_text(" ")) if title_a else "Stage (nom non extrait)"
    lien = title_a.find("a")["href"] if title_a and title_a.find("a") else BASE_URL

    dates_block = area2.find("div", class_=lambda c: c and "justify-content-md-end" in c)
    date_nums = DATE_RE.findall(dates_block.get_text(" ")) if dates_block else []
    if len(date_nums) >= 2:
        (j1, m1, a1), (j2, m2, a2) = date_nums[0], date_nums[-1]
        dates = f"du {j1}/{m1}/{a1} au {j2}/{m2}/{a2}"
    else:
        dates = "Non extrait automatiquement"

    # area2 contient DEUX div.col-12 (type/dates/titre, PUIS âge/prix) -
    # piège rencontré : `.find("div", class_="col-12")` prenait le premier
    # (type/dates), pas celui visé. Distingué via sa classe propre "text-m".
    age_price_block = area2.find("div", class_=lambda c: c and "text-m" in c)
    age_span = age_price_block.find("span", class_="bold") if age_price_block else None
    age_min, age_max = None, None
    if age_span:
        age_match = AGE_RE.search(age_span.get_text(" "))
        if age_match:
            age_min = float(age_match.group(1))
            # Pas de deuxième borne trouvée ("À partir de 16 ans", sans
            # plafond) -> age_max reste None, cohérent avec ageLabel() côté
            # front (affiche "à partir de X ans" seulement si age_max absent).
            age_max = float(age_match.group(2)) if age_match.group(2) else None

    prix_span = age_price_block.find("span", class_="text-l") if age_price_block else None
    prix_match = PRIX_RE.search(prix_span.get_text(" ")) if prix_span else None
    prix = f"{prix_match.group(1)}€" if prix_match else "Non extrait automatiquement"

    adresse_p = area3.find("p")
    lieu = _clean(adresse_p.get_text(" ")).replace("Adresse du stage :", "").strip() if adresse_p else "Non précisé"

    full_card_text = _clean(card.get_text(" "))
    disponibilite = extract_disponibilite(full_card_text) or "Non communiqué sur cette page"

    return Activite(
        commune=COMMUNE,
        organisateur=organisateur,
        nom_activite=nom_activite,
        type_activite=classify_type(nom_activite, organisateur),
        dates=dates,
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu=lieu,
        modalites_inscription="Voir la fiche du stage (lien source)",
        disponibilite=disponibilite,
        lien_source=lien,
    )


def scrape() -> list[Activite]:
    resp = respectful_get(BASE_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    total_pages = min(_num_pages(soup), MAX_PAGES)

    activites: list[Activite] = []
    seen_links: set[str] = set()

    for page_num in range(1, total_pages + 1):
        page_soup = soup if page_num == 1 else BeautifulSoup(respectful_get(f"{BASE_URL}page/{page_num}/").text, "lxml")
        for card in page_soup.find_all("div", class_="areas"):
            activite = _parse_card(card)
            if not activite or activite.lien_source in seen_links:
                continue
            if (activite.organisateur or "").lower() in ORGANISATEURS_DEJA_COUVERTS:
                continue
            seen_links.add(activite.lien_source)
            activites.append(activite)

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"# {len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
