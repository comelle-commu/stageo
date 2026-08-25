"""Fléron - EN ATTENTE, volontairement non implémenté cette session.

La page dédiée aux plaines/stages (atl.fleron.be, service "Accueil Temps
Libre", plateforme iMio/Plone - robots.txt et /gdpr-view confirmés
conformes, comme le reste du réseau iMio) répond 200 mais est
actuellement VIDE : "Il n'y a aucun élément dans ce dossier pour
l'instant." Le contenu n'est simplement pas encore publié pour la période
en cours - à réessayer plus tard dans la saison plutôt qu'un problème
technique ou légal.

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "atl.fleron.be (iMio, légalement GO) répond 200 mais la page est vide "
    "('Il n'y a aucun élément dans ce dossier pour l'instant') - contenu "
    "pas encore publié, à réessayer plus tard dans la saison"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : Fléron est en attente de publication du contenu."""
    return []


if __name__ == "__main__":
    print(f"Fléron : {STATUT} - {RAISON}")
