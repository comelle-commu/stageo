"""Scraper Neptune Ans Natation - piscine privée (école de natation), stages
"natation + multisports" à Ans. Site WordPress, robots.txt standard sans
restriction (Disallow limité à /wp-admin/).

Piège rencontré : au moment du ratissage (02/09/2026), la page affiche
encore le cycle complet de l'année scolaire 2025-2026 (Toussaint 20/10/2025
-> été 10-14/08/2026) - donc entièrement DANS LE PASSÉ par rapport à
aujourd'hui, la page n'ayant apparemment pas encore été mise à jour pour
2026-2027. Comme pour Forest/Uccle (voir plus bas dans ce README), le
parseur reste volontairement générique (aucune saison/année en dur) : le
jour où Neptune publie ses dates 2026-2027, le prochain run hebdomadaire
les récupérera automatiquement, sans changement de code. À rouvrir l'œil
dessus.

Structure : une <ul> de <li> "Vacances de X : DD/MM/ au DD/MM/YYYY »
OUVERT » ✅" pour Toussaint/Carnaval (x2)/Pâques (x2), plus une <li>
"Vacances d'été :" contenant une sous-<ul> de 5 semaines sans préfixe
("DD/MM au DD/MM/YYYY"). On ne garde que les <li> "feuilles" (sans <ul>
imbriqué) pour éviter de dupliquer l'entrée sur le conteneur "Vacances
d'été :" lui-même.

Tarif non calculé précisément (dégressif selon nombre d'enfants ET selon
semaine de 4 ou 5 jours, sans lien clair entre les deux dans le texte
source) - description honnête plutôt qu'un chiffre inventé, même logique
que uccle.py (4 profils de prix selon la résidence).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

URL = "https://www.neptunenatation.be/services/stages/"
COMMUNE = "Ans"
ORGANISATEUR = "Neptune Ans Natation"

DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/?\s*au\s*(\d{1,2})/(\d{1,2})/(\d{4})")
STATUT_RE = re.compile(r"»\s*([A-ZÀ-Ü][A-ZÀ-Üa-zà-ü]*)\s*»", re.I)
PREFIX_RE = re.compile(r"^Vacances\s+d[e']\s*([^:]+):", re.I)
# Retire les emoji/pictogrammes décoratifs en fin de libellé ("Carnaval 🎉")
TRAILING_EMOJI_RE = re.compile(r"[^\w\sÀ-ÿ'-]+$")


def _clean_label(label: str) -> str:
    return TRAILING_EMOJI_RE.sub("", label).strip()


def _parse_li(li, ete_counter: list[int]) -> Activite | None:
    text = li.get_text(" ", strip=True)
    date_match = DATE_RE.search(text)
    if not date_match:
        return None
    d1, m1, d2, m2, annee = date_match.groups()
    dates = f"du {int(d1):02d}/{int(m1):02d}/{annee} au {int(d2):02d}/{int(m2):02d}/{annee}"

    prefix_match = PREFIX_RE.match(text)
    if prefix_match:
        label = _clean_label(prefix_match.group(1))
    else:
        ete_counter[0] += 1
        label = f"Vacances d'été - Semaine {ete_counter[0]}"

    statut_match = STATUT_RE.search(text)
    disponibilite = statut_match.group(1).strip().capitalize() if statut_match else "Non communiqué sur cette page"
    if disponibilite.lower() == "ouvert":
        disponibilite = "Places disponibles"

    nom = f"{ORGANISATEUR} - {label}"
    return Activite(
        commune=COMMUNE,
        organisateur=ORGANISATEUR,
        nom_activite=nom,
        type_activite=classify_type(nom, ORGANISATEUR),
        dates=dates,
        age_min=3.0,
        age_max=15.0,
        prix="90 à 100€/semaine pour 1 enfant selon le nombre de jours (4 ou 5) et le nombre d'enfants inscrits, tarif préférentiel membres/école Saint-Pierre - grille complète sur le site",
        lieu="Piscine d'Ans (Neptune Ans Natation)",
        modalites_inscription="Document d'inscription à télécharger sur le site puis à renvoyer par email à stages@neptunenatation.be",
        disponibilite=disponibilite,
        lien_source=URL,
    )


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")

    activites: list[Activite] = []
    ete_counter = [0]
    for li in soup.select("li"):
        if li.find("ul") is not None:
            continue  # conteneur (ex. "Vacances d'été :"), pas une entrée feuille
        a = _parse_li(li, ete_counter)
        if a is not None:
            activites.append(a)
    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
