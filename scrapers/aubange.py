"""Scraper Aubange (province de Luxembourg, Vercel/WordPress) - Plaines et
stages communaux.

Contrairement à Ans/Herstal/Ville de Bruxelles, la commune ne publie PAS
de programme détaillé (pas de nom de stage, pas de dates exactes par
site) : la seule information publique est un "projet d'accueil" général
(voir https://www.aubange.be/services-communaux/service-jeunesse/, PDF
"MAJ-projet-CDV-2026-1.pdf") qui donne le public cible, les tarifs et un
calendrier en texte libre ("2ème semaine des vacances de détente", "2
semaines des vacances de printemps") SANS dates calendaires. Les
inscriptions et le détail réel passent par une plateforme tierce
(APPSCHOOL), qui nécessite un compte - pas accessible en scraping.

Décision volontaire : pas d'extraction automatique depuis la page (rien
d'assez structuré à extraire de façon fiable d'une période à l'autre) -
deux activités génériques codées en dur, une par période confirmée par la
commune ELLE-MÊME comme organisée (le projet d'accueil précise
explicitement "sauf [la période] d'hiver" et ne mentionne pas l'automne -
on ne les invente donc pas). Les dates de ces deux périodes sont celles
du calendrier scolaire officiel FWB (même source que VACATION_WEEKS dans
activites.html) : "2ème semaine des vacances de détente" = la semaine du
1er au 7 mars 2027 (la 1ère est celle du 22 au 28 février) ; "2 semaines
des vacances de printemps" = les deux semaines, du 26 avril au 9 mai 2027.
L'été 2026 (les "3 premières semaines") n'est pas repris : déjà terminé
à la date d'écriture de ce scraper (30/08/2026).

À REVOIR régulièrement : la commune publie vraisemblablement un flyer
détaillé par période plus près de la date (comme observé pour l'été 2025,
voir cms.aubange.be/wp-content/uploads/2025/05/) - remplacer ces deux
entrées génériques par un vrai scraper dès qu'un tel flyer structuré
apparaît pour l'automne/hiver/détente/printemps 2026-2027.
"""
from __future__ import annotations

from common import Activite, classify_type

PAGE_URL = "https://www.aubange.be/services-communaux/service-jeunesse/"
COMMUNE = "Aubange"

PRIX = (
    "50€/semaine (résident·es ou agent·es communaux·ales) - 100€/semaine "
    "(non-résident·es) - garderie du soir en supplément (+10€ jusqu'à "
    "17h30, +20€ jusqu'à 18h30)"
)
MODALITES = (
    "Inscription via la plateforme APPSCHOOL (voir le lien sur la page "
    "source) - informations et dates précises à confirmer auprès du "
    "Service Jeunesse (jeunesse@aubange.be, 063/37.20.50)."
)

PERIODES = [
    ("2ème semaine des vacances de détente 2027", "Du 1 mars 2027 au 7 mars 2027"),
    ("Vacances de printemps 2027", "Du 26 avril 2027 au 9 mai 2027"),
]


def scrape() -> list[Activite]:
    nom = "Plaines et stages communaux"
    return [
        Activite(
            commune=COMMUNE,
            nom_activite=f"{nom} - {label}",
            type_activite=classify_type(nom),
            dates=dates,
            age_min=2.5,
            age_max=12.0,
            prix=PRIX,
            lieu="Aubange (lieu précis selon la période - voir Service Jeunesse)",
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
