"""Scraper Sprimont (Plone/iMio, ancien thème Sunburst - #content-core plutôt
que <main>) - "Kids Holidays".

La page principale est un texte de type règlement (horaires, lieux, grille
de prix détaillée) SANS dates calendaires - le planning daté concret est
publié comme une IMAGE (`stages-ete-2026.png`, 832 KB), pas du texte ou un
PDF. Comme pour Oupeye (laissé de côté cette session, cf. README), une
image nécessiterait de l'OCR, volontairement évité. Contrairement à Oupeye,
la page texte donne quand même de vraies infos exploitables (âge, prix,
horaires, lieux) -> une ligne est produite avec ces infos, `dates` signalant
explicitement que le planning détaillé est une image non extraite.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, find_plone_content, respectful_get

URL = "https://www.sprimont.be/loisirs/stages/stages-sur-la-commune-de-sprimont/stages-de-la-commune-kids-holidays"
PLANNING_IMAGE_URL = (
    "https://www.sprimont.be/loisirs/stages/stages-sur-la-commune-de-sprimont/stages/stages-ete-2026.png"
)
COMMUNE = "Sprimont"

AGE_RE = re.compile(r"enfants de\s*([\d,]+)\s*à\s*([\d,]+)\s*ans", re.I)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    content = find_plone_content(soup)
    text = _clean(content.get_text())

    title = soup.find("title")
    title_text = title.get_text() if title else ""
    age_m = AGE_RE.search(title_text) or AGE_RE.search(text)
    age_min = age_max = None
    if age_m:
        age_min, age_max = (float(x.replace(",", ".")) for x in age_m.groups())

    prix_m = re.search(
        r"Prix\s*:\s*(.+?ann[ée]e|.+?famille\.)", text, re.I
    ) or re.search(r"(Pour une semaine de 5 jours.+?famille\.)", text)
    prix = prix_m.group(1).strip() if prix_m else "Non extrait automatiquement"

    lieu_m = re.search(r"Lieu\s*:\s*(.+?)Prix\s*:", text, re.I)
    lieu = lieu_m.group(1).strip() if lieu_m else "Non extrait automatiquement"

    horaire_m = re.search(r"Horaire\s*:\s*(.+?);", text, re.I)
    horaire = horaire_m.group(1).strip() if horaire_m else ""

    modalites = "Service Accueil Extrascolaire de Sprimont"
    if horaire:
        modalites += f" - horaire : {horaire}"

    activite = Activite(
        commune=COMMUNE,
        nom_activite="Kids Holidays (plaine communale non résidentielle)",
        dates=(
            "Dates exactes publiées uniquement sous forme d'image "
            f"({PLANNING_IMAGE_URL}) - non extraites cette session (pas d'OCR)"
        ),
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu=lieu,
        modalites_inscription=modalites,
        disponibilite="Non communiqué en texte sur cette page",
        lien_source=URL,
    )
    return [activite]


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
