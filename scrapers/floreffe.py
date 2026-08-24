"""Floreffe - EN ATTENTE, volontairement non implémenté cette session.

Le robots.txt de floreffe.be (https://www.floreffe.be/robots.txt) retourne
un 403 Forbidden de façon reproductible (testé en curl et en navigateur
complet, même résultat) - voir
docs/investigation-technique-sites-communaux-2026-08-24.md. Impossible de
lire une politique de crawl explicite pour ce domaine. Consigne : ne pas
scraper Floreffe tant que ce point n'est pas clarifié (contact direct avec
la commune, ou nouvelle vérification du robots.txt).

Ce module ne fait volontairement AUCUNE requête HTTP. Il existe pour que
Floreffe apparaisse explicitement comme "en attente" dans le run plutôt que
d'être silencieusement absent.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "robots.txt de floreffe.be inaccessible (403 Forbidden reproductible) - "
    "politique de crawl non confirmée, voir "
    "docs/investigation-technique-sites-communaux-2026-08-24.md"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : Floreffe est en attente de clarification."""
    return []


if __name__ == "__main__":
    print(f"Floreffe : {STATUT} - {RAISON}")
