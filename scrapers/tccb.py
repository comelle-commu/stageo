"""Scraper TC Cheval Blanc (Tennis Club du Cheval Blanc, Heusy) - Stages de
tennis.

Comme pour Aubange, pas de vrai scraping ici : le site (tcchevalblanc.be)
est une page unique où tout le contenu est déjà dans le HTML mais affiché
par sections via du JS (onclick="showSection(...)"), sans jamais publier
de calendrier de stages avec dates précises - seulement "Stages pendant
les vacances" en une ligne, dans la section École de Tennis.

⚠️ Point important, différent de toutes les autres sources du jeu de
données : la page précise explicitement que "Les cours et les stages de
tennis sont réservés aux membres du TCCB en ordre de cotisation" - ce
n'est PAS une activité ouverte à toute famille comme les autres. Le
warning est répété dans `nom_activite` (visible directement dans la
liste, pas seulement dans modalites_inscription) pour qu'un parent ne
clique pas en pensant pouvoir inscrire son enfant sans adhésion préalable.

Trois entrées (une par tranche d'âge de "formule" annoncée sur la page) -
pas de date exploitable, donc ces activités n'apparaîtront jamais dans une
alerte personnalisée (is_upcoming() les exclut faute de date parseable),
mais restent visibles en recherche libre sur /activites (comportement
existant pour toute activité à date illisible - voir isPast() côté site).
"""
from __future__ import annotations

from common import Activite, classify_type

COMMUNE = "Heusy"
ORGANISATEUR = "Tennis Club du Cheval Blanc"
PAGE_URL = "https://www.tcchevalblanc.be/"

DATES = "Non communiqué sur cette page (stages annoncés \"pendant les vacances scolaires\", dates précises à confirmer auprès du club)"
LIEU = "TC Cheval Blanc, Drève de Maison Bois 20, 4800 Verviers (Heusy)"
MODALITES = (
    "⚠️ Réservé aux membres du TCCB en ordre de cotisation (pas ouvert aux "
    "non-membres) - École de Tennis : Xavier Schmitz, 0495/46.42.56, "
    "courstccb@gmail.com"
)

FORMULES = [
    ("Mini-Tennis", 4.0, 6.0),
    ("École des Jeunes", 7.0, 12.0),
    ("Ados & Compétition", 13.0, 17.0),
]


def scrape() -> list[Activite]:
    nom_base = "[Réservé aux membres] Stages de tennis"
    return [
        Activite(
            commune=COMMUNE,
            organisateur=ORGANISATEUR,
            nom_activite=f"{nom_base} - {formule}",
            type_activite=classify_type(nom_base, ORGANISATEUR),
            dates=DATES,
            age_min=age_min,
            age_max=age_max,
            prix="Non communiqué sur cette page",
            lieu=LIEU,
            modalites_inscription=MODALITES,
            disponibilite="Non communiqué sur cette page",
            lien_source=PAGE_URL,
        )
        for formule, age_min, age_max in FORMULES
    ]


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
