"""Scraper Hotton (province de Luxembourg) - Plaines de vacances communales.

Page vitrine ("hub") vérifiée manuellement le 31/08/2026 : décrit le
dispositif de façon générique et récurrente ("La commune organise des
plaines de vacances durant différentes périodes des congés scolaires...
5 périodes : cinq semaines mi-juillet/mi-août, UNE semaine aux vacances
d'automne, UNE semaine aux vacances de Noël, UNE semaine au congé de
détente, UNE semaine aux vacances de printemps") sans jamais donner de
date calendaire précise par édition - contrairement à Virton ou
Meix-devant-Virton, rien à parser automatiquement d'une page à l'autre.

Même logique que `aubange.py` : plutôt que d'inventer une structure qui
n'existe pas sur la page, quatre activités génériques sont codées en dur,
une par période EXPLICITEMENT confirmée comme organisée par la commune
elle-même (l'été n'est pas repris : déjà passé à la date d'écriture de ce
scraper). Les dates utilisées sont celles du calendrier scolaire officiel
FWB 2026-2027 (même source que VACATION_WEEKS dans activites.html) -
Hotton ne précisant qu'"une semaine" par congé (jamais laquelle des deux
quand le congé en compte deux), la plage complète du congé est donnée
avec une note explicite plutôt que de deviner la bonne semaine.

Légal : robots.txt de hotton.be répond 200 mais avec le shell HTML
générique de l'application (comportement "soft-404" de SPA, comme
Neupré/Visé déjà documenté dans
docs/investigation-technique-sites-communaux-2026-08-24.md) - absence de
robots.txt réel = pas de restriction technique déclarée. Page
/mentions-legales vérifiée : même shell générique vide, aucune clause
trouvée nulle part sur le domaine.
"""
from __future__ import annotations

from common import Activite, classify_type

PAGE_URL = "https://www.hotton.be/hotton/information/plaines-et-stages-de-vacances"
COMMUNE = "Hotton"
LIEU = "École communale de Hampteau, Hotton"

PRIX = "10€/jour/enfant (2,5 à 12 ans) - 8€/jour/enfant à partir du 2ème enfant d'une même famille"
MODALITES = (
    "Inscription via le lien 'Emma' sur la page d'accueil du site (onglet "
    "'plaine') - infos : +32 84 36 03 23, plaines@hotton.be"
)

# (label, dates) - une activité par période EXPLICITEMENT listée comme
# organisée sur la page (voir docstring). Dates = plage complète du congé
# FWB 2026-2027 (Hotton ne précise qu'"une semaine" sur les deux quand le
# congé en compte deux - la note le signale plutôt que de deviner).
PERIODES = [
    ("Congé d'automne (Toussaint) 2026", "1 semaine entre le 19 octobre et le 1 novembre 2026 (semaine exacte non précisée sur cette page)"),
    ("Vacances de Noël (Hiver) 2026", "1 semaine entre le 21 décembre 2026 et le 3 janvier 2027 (semaine exacte non précisée sur cette page)"),
    ("Congé de détente (Carnaval) 2027", "1 semaine entre le 22 février et le 7 mars 2027 (semaine exacte non précisée sur cette page)"),
    ("Vacances de printemps (Pâques) 2027", "1 semaine entre le 26 avril et le 9 mai 2027 (semaine exacte non précisée sur cette page)"),
]


def scrape() -> list[Activite]:
    nom = "Plaine de vacances - Hotton"
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
