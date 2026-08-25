"""Jeunesses Musicales - EN ATTENTE, volontairement non implémenté cette session.

La page "Stages de vacances" (jeunessesmusicales.be/stages/) est légalement
GO (robots.txt lisible, crawl-delay 10s, page légale sans mot-clé
anti-scraping), mais elle ne contient AUCUN programme en HTML statique :
la sélection "trouvez un stage près de chez vous" est une carte
interactive (plugin WordPress "WP Google Maps Pro"), dont les marqueurs
sont chargés via l'API privée du plugin (pas de JSON exposé trouvé dans le
HTML brut). Extraire les stages nécessiterait soit un navigateur headless
pour déclencher les appels JS de la carte, soit une rétro-ingénierie de
l'endpoint AJAX du plugin - non fait cette session.

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "jeunessesmusicales.be/stages/ (légalement GO) liste ses stages via une "
    "carte interactive (plugin WP Google Maps Pro) - aucune donnée exposée "
    "en HTML statique, nécessiterait un navigateur headless ou une "
    "rétro-ingénierie de l'API du plugin, non fait cette session"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : les stages sont derrière une carte JS non extraite."""
    return []


if __name__ == "__main__":
    print(f"Jeunesses Musicales : {STATUT} - {RAISON}")
