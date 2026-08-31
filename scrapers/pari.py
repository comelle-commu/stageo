"""Scraper PARI asbl (Pédagogie Active Recherche Initiative, Liège et
environs) - stages via l'API REST WordPress (pariasbl.org/wp-json/wp/v2).

Pas de scraping HTML classique ici : chaque stage est un post du type
personnalisé "stage", dont le titre WordPress n'est qu'un code interne
("E7B") - le vrai nom affiché ("Stage résidentiel: VTT"), l'âge, le lieu
("implantation") et la semaine sont chacun une TAXONOMIE WordPress
distincte, exposée sur des endpoints REST séparés (/age, /implantation,
/semaine, /themes_activite) qu'il faut résoudre par id. Bien plus fiable
qu'un parsing HTML/CSS sur ce site (page générée par Elementor Loop +
JetSmartFilters, classes CSS peu stables) - voir le nom de la semaine
directement lisible ("17/08/2026 AU 21/08/2026") côté API, pas de date à
reconstruire depuis du texte libre.

Chaque "implantation" est un nom de lieu-dit/quartier, pas une commune :
IMPLANTATION_COMMUNES ne mappe QUE celles identifiées avec certitude (voir
recherche PARI asbl, quartiers de Liège + Fontin confirmé Sprimont) - les
autres (Belleflamme, Mehagne, Montfort, chalets ardennais...) gardent leur
nom de lieu tel quel comme `commune` : la recherche par rayon les exclura
silencieusement (within_radius() dans criteres_alertes.py, non
géocodable) plutôt que de risquer un mauvais rattachement de commune.

Au 31/08/2026, seuls 3 stages sont publiés côté API et tous les trois sont
déjà terminés (aucun stage à venir tant que PARI ne publie pas Toussaint/
Noël 2026) - is_upcoming() dans criteres_alertes.py et isPast() côté site
les filtrent déjà normalement, donc ce scraper tourne "à vide" jusqu'à la
prochaine publication, sans qu'aucune modification ne soit nécessaire à ce
moment-là.
"""
from __future__ import annotations

import re

from common import Activite, classify_type, respectful_get

API_BASE = "https://pariasbl.org/wp-json/wp/v2"
PAGE_URL = "https://pariasbl.org/stages"
ORGANISATEUR = "PARI asbl"
PRIX = "55€ par enfant (45€ pour les semaines avec jour férié)"

IMPLANTATION_COMMUNES = {
    "Cointe": "Liège",
    "Laveu": "Liège",
    "Naniot": "Liège",
    "Rabosée": "Liège",
    "Thier à Liège": "Liège",
    "Jupille": "Liège",
    "Saint-Léonard": "Liège",
    "Vieille-Montagne": "Liège",  # École Vieille-Montagne, quartier Saint-Léonard
    "Fontin": "Sprimont",
}

AGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*[–-]\s*(\d+(?:[.,]\d+)?)")


def _parse_age(label: str) -> tuple[float | None, float | None]:
    m = AGE_RE.search(label or "")
    if not m:
        return None, None
    return float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))


def _taxonomy_map(slug: str) -> dict[int, str]:
    # Pagination indispensable : plusieurs taxonomies (ex. themes_activite,
    # un thème par stage organisé depuis la création de l'ASBL) dépassent
    # largement 100 termes - une page unique tronquait silencieusement le
    # dict et faisait disparaître des stages pourtant bien présents côté
    # /stage (thème introuvable -> exclu par le `continue` de scrape()).
    page = 1
    terms: dict[int, str] = {}
    while True:
        resp = respectful_get(f"{API_BASE}/{slug}?per_page=100&page={page}")
        batch = resp.json()
        if not batch:
            break
        terms.update({t["id"]: t["name"] for t in batch})
        if len(batch) < 100:
            break
        page += 1
    return terms


def scrape() -> list[Activite]:
    resp = respectful_get(f"{API_BASE}/stage?per_page=100")
    posts = resp.json()
    if not posts:
        return []

    ages = _taxonomy_map("age")
    implantations = _taxonomy_map("implantation")
    semaines = _taxonomy_map("semaine")
    themes = _taxonomy_map("themes_activite")

    activites: list[Activite] = []
    for post in posts:
        theme_ids = post.get("themes_activite") or []
        nom = themes.get(theme_ids[0]) if theme_ids else None
        if not nom:
            continue  # pas de theme resolu -> rien d'exploitable a afficher

        age_min, age_max = _parse_age(ages.get((post.get("age") or [None])[0], ""))

        impl_ids = post.get("implantation") or []
        impl_name = implantations.get(impl_ids[0], "") if impl_ids else ""
        commune = IMPLANTATION_COMMUNES.get(impl_name, impl_name or "Non communiqué sur cette page")

        semaine_ids = post.get("semaine") or []
        dates = semaines.get(semaine_ids[0]) if semaine_ids else "Non communiqué sur cette page"

        lien = post.get("link") or PAGE_URL
        activites.append(
            Activite(
                commune=commune,
                organisateur=ORGANISATEUR,
                nom_activite=nom,
                type_activite=classify_type(nom, ORGANISATEUR),
                dates=dates,
                age_min=age_min,
                age_max=age_max,
                prix=PRIX,
                lieu=impl_name or "Non communiqué sur cette page",
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
