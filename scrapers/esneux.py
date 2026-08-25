"""Esneux - EN ATTENTE, volontairement non implémenté cette session.

La page "Stages et activités" (esneux.be, CMS "wwwedit") est légalement
GO (robots.txt lisible, crawl-delay 10s, /gdpr-view sans mot-clé
anti-scraping), mais la liste des activités elle-même est chargée en
JavaScript/AJAX après le chargement de la page - le HTML brut renvoyé par
une simple requête ne contient que la coquille ("Loading..." et le menu),
pas les activités. Contrairement à Neupré (Nuxt SSR, contenu déjà présent
dans le HTML brut), ce site nécessiterait un navigateur headless
(Playwright) pour récupérer le contenu réellement affiché - non fait
cette session.

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "esneux.be (légalement GO) charge la liste des stages en JavaScript/AJAX "
    "après coup - le HTML brut ne contient que la coquille de page, pas les "
    "activités ; nécessiterait un navigateur headless (Playwright), non fait "
    "cette session"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : Esneux nécessite un rendu JS non implémenté."""
    return []


if __name__ == "__main__":
    print(f"Esneux : {STATUT} - {RAISON}")
