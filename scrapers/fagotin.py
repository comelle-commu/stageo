"""Scraper Le Fagotin (parc animalier/nature, Stoumont) - trouvé via
recherche ciblée sur les organismes nature en province de Liège (voir
docs/ratissage-liege-supplement-2026-08-31.md). Page WordPress/Gutenberg
statique, un bloc `h5.wp-block-heading` par stage ("Titre | X-Y ans"), groupé
par semaine sous un `h2` "Semaine N" suivi d'un `h2` "Du D au D <mois>" -
même logique de parcours à état que aubel.py (accumulation de `current_*`
en avançant dans le document). Chaque stage a son propre lien de réservation
(`bookwhen.com/fr/fagotin?entry=...`), utilisé comme `lien_source`.

Légal : robots.txt WordPress standard (seul `/wp-admin/` interdit, rien sur
le contenu) ; conditions générales (`/conditions-generales/`) lues en
entier, aucune clause sur le scraping/l'extraction automatisée.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

PAGE_URL = "https://www.fagotin.be/stages-3/stage-automne-2026/"
COMMUNE = "Stoumont"
ORGANISATEUR = "Le Fagotin"
PRIX = "99€ la semaine (5 jours) / 25€ à la journée"

WEEK_HEADER_RE = re.compile(r"^Semaine\s+\d+", re.I)
DATE_RE = re.compile(r"^Du\s+\d{1,2}\s+au\s+\d{1,2}\s+\w+", re.I)
TITLE_AGE_RE = re.compile(r"^(.*?)\s*\|\s*(\d{1,2})\s*-\s*(\d{1,2})\s*ans\s*$")


def scrape() -> list[Activite]:
    resp = respectful_get(PAGE_URL)
    soup = BeautifulSoup(resp.text, "lxml")

    activites: list[Activite] = []
    current_dates: str | None = None

    # Parcours en ordre de document : h2 "Semaine N" (ignoré, juste un
    # repère visuel) -> h2 "Du D au D <mois>" (les vraies dates) -> une
    # poignée de h5 "Titre | age ans" jusqu'à la prochaine semaine.
    for el in soup.find_all(["h2", "h5"]):
        text = el.get_text(" ", strip=True)
        if el.name == "h2":
            if DATE_RE.match(text):
                current_dates = text[0].lower() + text[1:]  # "Du 19 au 23 octobre" -> "du 19 au 23 octobre"
            continue

        if current_dates is None:
            continue  # h5 avant la premiere date rencontree (ne devrait pas arriver) - ignore par prudence

        m = TITLE_AGE_RE.match(text)
        if not m:
            continue
        nom, age_min, age_max = m.group(1).strip(), float(m.group(2)), float(m.group(3))

        col = el.find_parent("div", class_="wp-block-column")
        link = col.find("a", href=True) if col else None
        lien = link["href"] if link else PAGE_URL

        activites.append(
            Activite(
                commune=COMMUNE,
                organisateur=ORGANISATEUR,
                nom_activite=nom,
                type_activite=classify_type(nom, ORGANISATEUR),
                dates=current_dates,
                age_min=age_min,
                age_max=age_max,
                prix=PRIX,
                lieu="Le Fagotin, Stoumont",
                modalites_inscription=f"Réservation en ligne : {lien}",
                disponibilite="Non communiqué sur cette page",
                lien_source=lien,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
