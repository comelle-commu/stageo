"""Scraper Les Ateliers 04 (Liège) - stages créatifs (arts plastiques,
photo, cirque, écriture...) pour enfants, ados et adultes.

Contrairement à PARI (voir pari.py), pas d'API REST exploitable ici : le
custom post type "stages" existe bien (wp-json/wp/v2/stages) mais le champ
date affiché sur le site ("Du 26 au 30 octobre 2026") est un champ
Elementor "custom field" non exposé par l'API (acf: [] vide, aucune
taxonomie date). Scraping HTML classique de la page /stages/ à la place -
un widget "post-info" par carte porte soit un terme de taxonomie (span
elementor-post-info__item--type-terms, catégorie "Stage" OU âge - les deux
utilisent la même classe, distingués ici par un motif d'âge reconnu plutôt
que par position) soit le champ personnalisé (elementor-post-info__item--
type-custom, toujours la date en pratique sur cette page).

La page ne montre que 50 stages (limite de la boucle Elementor, pas de
pagination visible) - mélange passé/futur, filtré comme d'habitude en
aval (isPast()/is_upcoming()).

Les stages réservés aux adultes ("Adultes", "Adultes (Dès 16 ans)") sont
explicitement exclus : Trouvéo est un aggregateur d'activités enfants, pas
un outil généraliste - les inclure biaiserait les résultats de recherche
d'un parent. "Intergénérationnel"/"Tous" restent inclus sans borne d'âge
(comme les activités sans âge détecté ailleurs dans le jeu de données) :
ces stages accueillent explicitement les enfants, contrairement à
"Adultes".
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

PAGE_URL = "https://www.lesateliers04.be/stages/"
ORGANISATEUR = "Les Ateliers 04"
COMMUNE = "Liège"
LIEU = "Les Ateliers 04, Liège"

AGE_RANGE_RE = re.compile(r"(\d+)\s*(?:-|–|à)\s*(\d+)\s*ans", re.I)
AGE_MIN_ONLY_RE = re.compile(r"D[eè]s\s*(\d+)\s*ans", re.I)
ADULTES_RE = re.compile(r"^Adultes\b", re.I)


def _parse_age(label: str) -> tuple[float | None, float | None, bool]:
    """Retourne (age_min, age_max, exclure). `exclure` = True pour les
    stages explicitement réservés aux adultes."""
    label = (label or "").strip()
    if ADULTES_RE.match(label):
        return None, None, True
    m = AGE_RANGE_RE.search(label)
    if m:
        return float(m.group(1)), float(m.group(2)), False
    m = AGE_MIN_ONLY_RE.search(label)
    if m:
        return float(m.group(1)), None, False
    return None, None, False  # "Intergénérationnel", "Tous" - pas de borne


def scrape() -> list[Activite]:
    resp = respectful_get(PAGE_URL)
    soup = BeautifulSoup(resp.text, "lxml")

    activites: list[Activite] = []
    for item in soup.find_all("div", class_="e-loop-item"):
        link_a = item.find("a", recursive=False)
        lien = link_a["href"] if link_a and link_a.get("href") else PAGE_URL

        title_el = item.find(class_="elementor-widget-theme-post-title")
        nom = title_el.get_text(strip=True) if title_el else None
        if not nom:
            continue

        date_el = item.find("span", class_="elementor-post-info__item--type-custom")
        dates = date_el.get_text(strip=True) if date_el else "Non communiqué sur cette page"

        # Plusieurs widgets "type-terms" par carte (catégorie "Stage" +
        # âge) - on prend le premier texte qui ressemble à un âge plutôt
        # qu'une position fixe, plus robuste si l'ordre des widgets varie.
        age_label = ""
        for term_el in item.find_all(class_="elementor-post-info__terms-list-item"):
            text = term_el.get_text(strip=True)
            if AGE_RANGE_RE.search(text) or AGE_MIN_ONLY_RE.search(text) or ADULTES_RE.match(text) or text in ("Intergénérationnel", "Tous"):
                age_label = text
                break

        age_min, age_max, exclure = _parse_age(age_label)
        if exclure:
            continue

        activites.append(
            Activite(
                commune=COMMUNE,
                organisateur=ORGANISATEUR,
                nom_activite=nom,
                type_activite=classify_type(nom, ORGANISATEUR),
                dates=dates,
                age_min=age_min,
                age_max=age_max,
                prix="Non communiqué sur cette page (voir le lien du stage pour le tarif exact)",
                lieu=LIEU,
                modalites_inscription=f"Inscription en ligne : {lien}",
                disponibilite="Non communiqué sur cette page",
                lien_source=lien,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
