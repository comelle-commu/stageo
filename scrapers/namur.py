"""Namur - EN ATTENTE, volontairement non implémenté cette session.

Confirmée iMio (robots.txt redirige vers static.imio.be, Crawl-delay 120 -
voir docs/elargissement-provinces-2026-08-24.md). Mais les pages
individuelles de plaines trouvées par recherche (ex. "plaines-ete-jambes-
parc-astrid") redirigent vers une page de login e-guichet ("Les cookies ne
sont pas activés") plutôt que d'afficher le contenu directement - la vraie
page publique n'a pas été retrouvée cette session. Namur a une structure
inhabituelle (une sous-page par lieu plutôt qu'une page de synthèse comme
Ans/Mons/Arlon) - à explorer plus en détail avant de coder un scraper.

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "iMio confirmée mais pages individuelles de plaines redirigent vers "
    "une page de login e-guichet - URL publique correcte non retrouvée, "
    "voir docs/elargissement-provinces-2026-08-24.md"
)


def scrape() -> list:
    return []


if __name__ == "__main__":
    print(f"Namur : {STATUT} - {RAISON}")
