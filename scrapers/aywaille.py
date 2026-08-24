"""Aywaille - EN ATTENTE, exclu explicitement cette session (consigne).

La page communale renvoie explicitement vers une plateforme tierce
("ActivKids") où les organisateurs encodent eux-mêmes leurs activités - rien
à scraper côté aywaille.be lui-même (voir
docs/investigation-technique-elargissement-communes-2026-08-24.md).
Nécessiterait sa propre vérification légale (robots.txt / CGU d'ActivKids),
comme pour APSCHOOL en son temps - non fait cette session.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "Renvoie vers la plateforme tierce ActivKids (rien à scraper sur "
    "aywaille.be lui-même) - nécessiterait sa propre vérification légale, "
    "non faite cette session."
)


def scrape() -> list:
    """Ne fait aucune requête réseau : source réelle chez un tiers non vérifié légalement."""
    return []


if __name__ == "__main__":
    print(f"Aywaille : {STATUT} - {RAISON}")
