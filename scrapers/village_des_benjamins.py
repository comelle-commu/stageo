"""Scraper Village des Benjamins (ASBL, Grâce-Hollogne) - Stages vacances scolaires.

Application Vue.js pure (rien en HTML brut, "Désolé, ce site nécessite
JavaScript") - nécessite common.fetch_rendered_html() (Playwright).

Pas de dates calendaires ni de prix donnés pour les stages eux-mêmes sur
la page statique : seule la structure (4 groupes d'âge, thématiques par
période) est stable. Les vraies dates/tarifs de chaque période circulent
uniquement via le fil "Actualités" (billets datés, format libre, non
structuré) et la zone de réservation qui nécessite un compte - non
extraits ici, signalé explicitement plutôt que deviné (même logique que
La Louvière, voir lalouviere.py).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, fetch_rendered_html

URL = "https://village-des-benjamins.be/"
ORGANISATEUR = "Village des Benjamins"
COMMUNE = "Grace-Hollogne"

GROUPE_RE = re.compile(r"Les\s+([\wéèàû-]+)\s+de\s+(\d+(?:[.,]\d+)?)\s*à\s*(\d+(?:[.,]\d+)?)\s*ans", re.I)


def scrape() -> list[Activite]:
    html = fetch_rendered_html(URL)
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    full_text = re.sub(r"\s+", " ", soup.find("body").get_text(" ")).strip()

    dates = (
        "Stages organisés à chaque période de vacances scolaires, thème différent à chaque fois "
        "- dates et tarifs publiés environ un mois avant chaque période (voir réservation en ligne)"
    )
    lieu = "Rue Ernest Renan 30, 4460 Grâce-Hollogne"
    modalites = "Réservation en ligne (compte requis) un mois avant chaque période de vacances, ou par téléphone au 04/234.42.96"

    activites: list[Activite] = []
    for nom_groupe, age_min_txt, age_max_txt, in GROUPE_RE.findall(full_text):
        nom_activite = f"Stages vacances scolaires - {nom_groupe.capitalize()}"
        activites.append(
            Activite(
                commune=COMMUNE,
                organisateur=ORGANISATEUR,
                nom_activite=nom_activite,
                type_activite=classify_type(nom_activite, ORGANISATEUR),
                dates=dates,
                age_min=float(age_min_txt.replace(",", ".")),
                age_max=float(age_max_txt.replace(",", ".")),
                prix="Non communiqué sur cette page (voir réservation en ligne)",
                lieu=lieu,
                modalites_inscription=modalites,
                disponibilite="Non communiqué sur cette page",
                lien_source=URL,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
