"""Hannut - EN ATTENTE, volontairement non implémenté cette session.

L'investigation d'élargissement notait une URL périmée. Vérification cette
session : la ville de Hannut republie un article WordPress par période de
vacances (ex. `hannut.be/stages-automne-2025/`, publié le 16/09/2025 pour
les vacances d'octobre 2025), qui renvoie lui-même vers un PDF
("communication-des-offres-de-stages-automneAAAA.pdf"). Le motif d'URL est
donc prévisible (`stages-{periode}-{annee}`), mais **l'article pour la
période actuellement pertinente n'existe pas encore** :
`hannut.be/stages-automne-2026/` -> 404 au 24/08/2026 (probablement publié
mi-septembre 2026, à en juger par le calendrier de l'édition 2025). Ce
n'est donc pas un blocage légal/technique comme Floreffe, mais un problème
de calendrier : rien à scraper pour l'instant.

Note pour plus tard : le PDF 2025 équivalent (4.2 MB, 8 pages) contient de
nombreux petits tableaux détectés par pdfplumber (17 sur la page 1) plutôt
qu'un grand tableau propre comme Herstal - probablement une compilation de
flyers/inserts par organisme plutôt qu'un export tabulaire unique. À
revérifier une fois l'édition 2026 publiée, la structure pourrait différer.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "Article 'stages-automne-2026' pas encore publié sur hannut.be (404 au "
    "24/08/2026 ; l'édition 2025 avait été publiée le 16/09) - rien à "
    "scraper pour la période actuelle, pas un blocage légal/technique. "
    "Voir docs/scraper-cas-difficiles-2026-08-24.md"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : rien n'est encore publié pour la période actuelle."""
    return []


if __name__ == "__main__":
    print(f"Hannut : {STATUT} - {RAISON}")
