"""FunheLangues (stages d'immersion linguistique) - EN ATTENTE.

Site Wix (funhelangues.be/stages-vacances-scolaires), robots.txt lisible
et permissif (crawl-delay 10s, pas de mot-clé anti-scraping détecté), mais
la page affiche actuellement "Pas d'événements pour le moment" pour les
stages enfants comme pour les stages ados - aucun programme daté à
extraire. À noter aussi : Wix charge généralement son calendrier
d'événements en JavaScript, donc même une fois des stages publiés,
`respectful_get()` seul pourrait ne pas suffire à les récupérer (à
vérifier le jour où du contenu sera disponible).

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "funhelangues.be (légalement GO) affiche 'Pas d'événements pour le "
    "moment' pour ses stages - rien à extraire actuellement ; site Wix, "
    "à vérifier si le futur calendrier est en JS pur le jour où du contenu "
    "sera publié"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : aucun stage publié pour l'instant."""
    return []


if __name__ == "__main__":
    print(f"FunheLangues : {STATUT} - {RAISON}")
