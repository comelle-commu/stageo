"""Côté Campagne (ferme pédagogique, Awans) - EN ATTENTE.

Contenu légalement accessible (pas de robots.txt = pas de restriction
déclarée) et riche une fois atteint (stages été 2026, 3 formules, prix,
horaires) - mais le site (constructeur "1&1 MyWebsite" ou équivalent)
cache ses vrais liens derrière du JavaScript ("xr_nn()"/"xr_mo()") : le
lien affiché dans le HTML brut ("stages-a") n'est pas l'URL réelle, elle
n'est résolue qu'à l'exécution du JS dans un navigateur. `respectful_get()`
(requests + BeautifulSoup, sans JS) ne peut donc pas l'atteindre.

Techniquement faisable avec un navigateur headless (Playwright, déjà
utilisé pour les tests de ce projet - voir CLAUDE.md), mais ce serait le
premier scraper de ce type : ajouterait Playwright comme dépendance du
pipeline de scraping (installation de Chromium dans le workflow GitHub
Actions, temps d'exécution plus long). Décision d'investir ou non dans
cette dépendance à valider avec l'utilisateur avant de l'ajouter pour un
seul site.

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "cotecampagne.com (légalement GO, pas de robots.txt) cache ses liens "
    "réels derrière du JavaScript - nécessiterait Playwright (navigateur "
    "headless), pas encore utilisé dans le pipeline de scraping ; à discuter "
    "avant d'ajouter cette dépendance pour un seul site"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : nécessite un navigateur headless non encore intégré au pipeline."""
    return []


if __name__ == "__main__":
    print(f"Côté Campagne : {STATUT} - {RAISON}")
