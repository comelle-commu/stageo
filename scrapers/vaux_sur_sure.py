"""Scraper Vaux-sur-Sûre (Plone/iMio, province de Luxembourg) - Plaines
communales.

Trouvé pendant le ratissage de la province de Luxembourg (31/08/2026).
La page ("Les plaines communales") confirme explicitement que le
dispositif tourne "durant CHAQUE congé scolaire", pour les enfants de 2,5
à 15 ans (tranche plus large que la plupart des communes voisines), avec
réduction dès le 2e enfant - mais reste un texte de présentation générale
(comme Hotton), sans dates par activité nommée.

Un "calendrier des plaines 2026" est bien lié en PDF
(`2026-plaines-et-stages.pdf`), mais c'est une affiche calendrier
pleine page (grille de cases jour par jour avec légende couleur) sans le
mot "automne" ni "octobre" retrouvé dans le texte natif extrait
(`pdfplumber`/`pypdf` ne lisent que les nombres du quadrillage, pas la
légende qui les associe aux congés - mise en page trop graphique pour une
extraction fiable sans OCR, hors périmètre du projet) : non exploité,
seule la page HTML sert de source ici.

Une activité générique par congé FWB 2026-2027 (même source que
VACATION_WEEKS dans activites.html), la page elle-même confirmant que
TOUS les congés sont couverts (pas d'exclusion comme à Aubange) - plage
complète du congé donnée, la commune ne précisant pas si un congé donné
dure une ou deux semaines.

Légal : robots.txt iMio standard (signature confirmée, Crawl-delay 120),
page /gdpr-view lisible, aucun mot-clé anti-scraping trouvé.
"""
from __future__ import annotations

from common import Activite, classify_type

PAGE_URL = "https://www.vaux-sur-sure.be/ma-commune/services-communaux/extrascolaire/plaines-communales"
COMMUNE = "Vaux-sur-Sûre"

MODALITES = (
    "Inscription auprès de la Coordination ATL - Maud Jacques, +32 61 26 09 91, "
    "Chaussée de Neufchâteau 36, 6640 Vaux-sur-Sûre (voir page source pour le détail)"
)

# (label, dates) - la page confirme "chaque congé scolaire" sans détailler
# la durée par congé : plage complète du congé FWB 2026-2027 donnée avec
# une note (voir docstring).
PERIODES = [
    ("Congé d'automne (Toussaint) 2026", "entre le 19 octobre et le 1 novembre 2026 (durée exacte non précisée sur cette page)"),
    ("Vacances de Noël (Hiver) 2026", "entre le 21 décembre 2026 et le 3 janvier 2027 (durée exacte non précisée sur cette page)"),
    ("Congé de détente (Carnaval) 2027", "entre le 22 février et le 7 mars 2027 (durée exacte non précisée sur cette page)"),
    ("Vacances de printemps (Pâques) 2027", "entre le 26 avril et le 9 mai 2027 (durée exacte non précisée sur cette page)"),
]


def scrape() -> list[Activite]:
    nom = "Plaine communale - Vaux-sur-Sûre"
    return [
        Activite(
            commune=COMMUNE,
            nom_activite=f"{nom} ({label})",
            type_activite=classify_type(nom),
            dates=dates,
            age_min=2.5,
            age_max=15.0,
            prix="Non communiqué sur cette page - réduction à partir du 2e enfant inscrit",
            lieu=COMMUNE,
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
