"""Waremme - EN ATTENTE, volontairement non implémenté cette session.

Contrairement à l'hypothèse de départ (même structure que Herstal), le PDF
de Waremme ("Les stages 2026 Ete.pdf", 38 pages, 1.2 MB) n'est PAS un
tableau propre exporté depuis Word/Excel comme celui d'Herstal - c'est une
brochure en mise en page libre : chaque stage a un bloc "Heures / Âges /
Prix / Inscription / Lieu" positionné par coordonnées x/y plutôt que par de
vraies cellules de tableau. `pdfplumber.extract_tables()` ne détecte AUCUN
tableau sur ce PDF (contre 1 tableau propre de 43-58 lignes par page chez
Herstal). Une extraction positionnelle (regrouper les mots par colonne de
coordonnée x, puis par ligne de coordonnée y) serait nécessaire - piste
identifiée mais non développée cette session (effort nettement supérieur à
Herstal, à budgéter séparément).

Bonus contexte : la page précise explicitement que "la liste des opérateurs
[...] ne dépendent pas de la ville de Waremme, ils sont, seuls, responsables
du contenu des descriptifs" - une nuance proche du cas Aywaille/ActivKids
(offre tierce agrégée par la commune, pas organisée par elle), même si ici
c'est un PDF statique et non une plateforme tierce en ligne.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "PDF en mise en page libre (38 pages, pas de tableau détectable par "
    "pdfplumber, contrairement à Herstal) - nécessiterait une extraction "
    "positionnelle (x/y) non développée cette session. Voir "
    "docs/scraper-cas-difficiles-2026-08-24.md"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : Waremme est en attente d'un parseur dédié."""
    return []


if __name__ == "__main__":
    print(f"Waremme : {STATUT} - {RAISON}")
