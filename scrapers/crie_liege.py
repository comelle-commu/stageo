"""CRIE de Liège (Education-Environnement asbl) - EN ATTENTE.

Page dédiée (education-environnement.be/stage.php) légalement GO (robots.txt
lisible, page légale sans mot-clé anti-scraping), mais le programme
lui-même n'est pas encore publié : la page dit explicitement "Les dates de
nos prochains stages ne sont pas encore disponibles" et invite à
s'inscrire à la newsletter à la place. Rien à extraire pour l'instant -
à réessayer plus tard dans la saison.

Note pour plus tard : le réseau des CRIE compte 11 centres en Wallonie
(voir crie.be), chacun avec son propre site - à traiter un par un comme
les communes, pas de portail centralisé trouvé.

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "education-environnement.be (CRIE de Liège, légalement GO) affiche "
    "explicitement que le programme des prochains stages n'est pas encore "
    "publié - à réessayer plus tard dans la saison"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : le CRIE de Liège n'a pas encore publié son programme."""
    return []


if __name__ == "__main__":
    print(f"CRIE de Liège : {STATUT} - {RAISON}")
