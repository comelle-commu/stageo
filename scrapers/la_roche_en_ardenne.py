"""Scraper La Roche-en-Ardenne (province de Luxembourg) - Stages/plaines de
l'ATL (Accueil Temps Libre).

Trouvé pendant le ratissage de la province de Luxembourg (31/08/2026),
page ATL (`la-roche-en-ardenne.be/pages/vie_communale/atl.php`, PAS iMio -
plateforme propre) et son "Projet d'accueil stages plaines 2026-2027"
(PDF joint) tous deux vérifiés manuellement : le texte donne un
engagement clair et récent ("Stages : 2 semaines au congé d'automne,
détente, printemps ; Plaines d'été : 4 semaines durant le congé d'été"),
avec tarif/horaire précis, mais SANS dates calendaires (document
réglementaire type ROI, pas un programme daté - comme le PDF
équivalent de Bastogne). Le PDF ne mentionne d'ailleurs jamais "octobre"
ni aucun mois explicitement.

Contrairement à Hotton, "2 semaines" ici couvre exactement les DEUX
semaines de chaque congé FWB (pas d'ambiguïté sur "quelle semaine") -
la plage complète du congé officiel 2026-2027 (même source que
VACATION_WEEKS dans activites.html) est donc utilisée avec confiance,
sans note d'incertitude. L'été n'est pas repris (4 semaines à une date
non précisée, ni fenêtre officielle FWB claire à cette distance).

Légal : robots.txt propre (`User-agent: * / Crawl-delay: 10`, pas de
Disallow), page /mentions-legales lisible (contenu quasi vide - juste la
navigation - mais aucune clause anti-scraping nulle part sur le domaine).
"""
from __future__ import annotations

from common import Activite, classify_type

PAGE_URL = "https://www.la-roche-en-ardenne.be/pages/vie_communale/atl.php"
COMMUNE = "La Roche-en-Ardenne"
LIEU = "Local ATL, Rue de la Piscine 1, La Roche-en-Ardenne"

PRIX = "10€/jour (potage + 1 collation inclus) - accueil 7h-9h et 16h30-17h30 : 0,035€/minute"
MODALITES = (
    "Inscription via formulaire en ligne (lien Forms sur le site communal) - "
    "ATL : Françoise Legros, 0477/85.06.15, francoise.legros@laroche.be"
)

# (label, dates) - "2 semaines" par congé = les deux semaines officielles
# FWB du congé correspondant (voir docstring), pas d'ambiguïté ici.
PERIODES = [
    ("Congé d'automne (Toussaint) 2026", "du 19 octobre au 1 novembre 2026 (2 semaines)"),
    ("Congé de détente (Carnaval) 2027", "du 22 février au 7 mars 2027 (2 semaines)"),
    ("Vacances de printemps (Pâques) 2027", "du 26 avril au 9 mai 2027 (2 semaines)"),
]


def scrape() -> list[Activite]:
    nom = "Stage/plaine ATL - La Roche-en-Ardenne"
    return [
        Activite(
            commune=COMMUNE,
            nom_activite=f"{nom} ({label})",
            type_activite=classify_type(nom),
            dates=dates,
            age_min=2.5,
            age_max=12.0,
            prix=PRIX,
            lieu=LIEU,
            modalites_inscription=MODALITES,
            disponibilite="Non communiqué sur cette page",
            lien_source=PAGE_URL,
        )
        for label, dates in PERIODES
    ]


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
