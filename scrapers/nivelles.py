"""Nivelles - EN ATTENTE, volontairement non implémenté cette session.

Confirmée iMio (robots.txt redirige vers static.imio.be, Crawl-delay 120 -
voir docs/elargissement-provinces-2026-08-24.md). Un article "Plaine de
vacances communale - Été 2026 : Inscriptions" trouvé par recherche, mais
son URL renvoie 404 en direct (avec ou sans le paramètre de tracking "?u=")
- probablement expiré ou déplacé depuis l'indexation. URL correcte à
retrouver.

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "iMio confirmée mais l'article de plaine trouvé par recherche renvoie "
    "404 en direct (probablement expiré) - URL publique correcte non "
    "retrouvée, voir docs/elargissement-provinces-2026-08-24.md"
)


def scrape() -> list:
    return []


if __name__ == "__main__":
    print(f"Nivelles : {STATUT} - {RAISON}")
