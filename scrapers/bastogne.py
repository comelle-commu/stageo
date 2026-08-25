"""Bastogne - EN ATTENTE, volontairement non implémenté cette session.

Confirmée iMio (robots.txt redirige vers static.imio.be, Crawl-delay 120 -
voir docs/elargissement-provinces-2026-08-24.md), au même titre que Namur,
Mons, Nivelles, Ottignies-LLN, Arlon, Bastogne, Ciney. La page stages/
plaines elle-même n'a pas encore été localisée/vérifiée cette session (temps
consacré en priorité à Mons et Arlon, une commune par province suffisant
pour une première passe de couverture géographique) - à faire dans un
prochain tour, même méthode que Mons/Arlon (page unique, texte libre,
find_plone_content()).

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "iMio confirmée (voir docs/elargissement-provinces-2026-08-24.md) mais "
    "page stages/plaines pas encore localisée/vérifiée cette session"
)


def scrape() -> list:
    return []


if __name__ == "__main__":
    print(f"Bastogne : {STATUT} - {RAISON}")
