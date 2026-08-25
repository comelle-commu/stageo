"""Scraper Chaudfontaine (WordPress) - Stages & activites.

Page unique, tres bien structuree : chaque stage est un accordion
`<details><summary>` (titre + tranche d'age + dates dans le `<summary>`,
lieu/horaires/prix/inscription dans le corps, un champ par ligne separee
par `<br>`). Regroupes sous des `<h2>` de saison ("Stages d'automne 2026",
"Stages d'hiver 2026", ...) - le nom de la saison est ajoute au nom de
l'activite pour donner le contexte (l'annee n'apparait que dans le titre
de saison, pas dans les dates jour/mois elles-memes).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

URL = "https://www.chaudfontaine.be/mes-services/enfance-education-jeunesse/education/stages-activites/"
COMMUNE = "Chaudfontaine"

TITRE_AGE_RE = re.compile(r"^(.*?)\s*\((\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*ans\)\s*(.*)$")
CHAMP_RE = re.compile(r"^([A-Za-zÀ-ÿ' ]{2,20}?)\s*:\s*(.+)$")


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", txt).strip()


def _fields_from(content_div) -> dict[str, str]:
    for br in content_div.find_all("br"):
        br.replace_with("\n")
    fields: dict[str, str] = {}
    for line in content_div.get_text("").split("\n"):
        m = CHAMP_RE.match(_clean(line))
        if m:
            fields[m.group(1).strip().lower()] = m.group(2).strip()
    return fields


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    article = soup.find("article")
    if article is None:
        return []

    activites: list[Activite] = []
    saison = ""
    for el in article.find_all(["h2", "details"]):
        if el.name == "h2":
            saison = _clean(el.get_text(" "))
            continue

        summary = el.find("summary")
        if summary is None:
            continue
        summary_txt = _clean(summary.get_text(" "))
        m = TITRE_AGE_RE.match(summary_txt)
        if not m:
            continue
        titre, age_min_txt, age_max_txt, dates_txt = m.groups()

        content_div = el.find("div", class_="gb-accordion-text") or el
        fields = _fields_from(content_div)

        annee_match = re.search(r"\d{4}", saison)
        dates = _clean(dates_txt) or "Non extrait automatiquement"
        if annee_match:
            dates += f" ({annee_match.group(0)})"
        if fields.get("horaires"):
            dates += f", {fields['horaires']}"

        inscription = fields.get("inscription", "")
        info = fields.get("info", "")
        modalites = inscription or "Non extrait automatiquement"
        if info:
            modalites += f" (info : {info})"

        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=f"{titre.strip()} — {saison}" if saison else titre.strip(),
                type_activite=classify_type(titre),
                dates=dates,
                age_min=float(age_min_txt.replace(",", ".")),
                age_max=float(age_max_txt.replace(",", ".")),
                prix=fields.get("prix", "Non communiqué sur cette page"),
                lieu=fields.get("lieu", "Non extrait automatiquement"),
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
