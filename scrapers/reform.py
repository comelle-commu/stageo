"""Scraper ReForm asbl - stages de vacances, plusieurs antennes régionales
en Wallonie et à Bruxelles (Liège/Verviers, Hainaut, Namur, Bruxelles,
Brabant wallon) - une seule page (/nos-activites/en-vacances/) liste
TOUTES les périodes et TOUTES les antennes à la suite.

Page construite avec l'éditeur visuel Divi : pas de classes CSS par champ
(contrairement à PARI/Ateliers04/HESL), mais chaque stage forme malgré
tout un bloc HTML sémantique cohérent et stable (`div.et_pb_text_inner`) :
- <h1> = nom de l'antenne ("ReForm Liège", "ReForm Hainaut"...) - casse
  incohérente sur le site lui-même ("ReForm BRUXELLES" vs "ReForm
  Bruxelles") - normalisée ici (REGIONS) pour ne pas fragmenter les
  données entre deux organisateurs qui n'en sont qu'un seul.
- premier <p> = dates ("Du 19 au 23 octobre 2026")
- <h2> = nom du stage
- <h3> = lignes de métadonnées ("Age : ...", "Lieu : ...", "Infos : ...")

Un bloc sans à la fois <h1> ET <h2> (ex. le titre général de page "Stages
vacances scolaires", ou les titres de période "Congé d'automne (Toussaint)
2026") n'est pas un stage - ignoré.

`commune` est déduite du texte "Lieu" (ex. "Local ReForm (Avenue Hanlet 31
à Heusy)" -> "Heusy") : certains lieux-dits (ex. "Champion", section de
Namur) ne seront pas géocodables dans commune_coords.json - la recherche
par rayon les exclut alors silencieusement plutôt que de risquer un
mauvais rattachement (même logique que pari.py).
"""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

PAGE_URL = "https://reform.be/nos-activites/en-vacances/"

REGIONS = {
    "bruxelles": "Bruxelles",
    "hainaut": "Hainaut",
    "liège": "Liège",
    "liege": "Liège",
    "namur": "Namur",
    "brabant wallon": "Brabant wallon",
}

MOIS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12, "decembre": 12,
}
_MOIS_RE = "|".join(MOIS.keys())
LAST_DATE_RE = re.compile(rf"(\d{{1,2}})\s+({_MOIS_RE})\s+(\d{{4}})", re.IGNORECASE)
AGE_RANGE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*[-–]\s*(\d+(?:[.,]\d+)?)")
COMMUNE_FROM_LIEU_RE = re.compile(r"\bà\s+([A-ZÉÈÀÂ][A-Za-zÀ-ÿ\-\s]*?)\)?\s*$")


def _end_date(text: str) -> date | None:
    matches = LAST_DATE_RE.findall(text or "")
    if not matches:
        return None
    d, mois, y = matches[-1]
    try:
        return date(int(y), MOIS[mois.lower()], int(d))
    except ValueError:
        return None


def _normalize_organisateur(h1_text: str) -> str | None:
    if not h1_text.lower().startswith("reform"):
        return None
    region_key = h1_text[len("reform"):].strip().lower()
    region = REGIONS.get(region_key, h1_text[len("ReForm"):].strip())
    return f"ReForm {region}"


def scrape() -> list[Activite]:
    resp = respectful_get(PAGE_URL)
    soup = BeautifulSoup(resp.text, "lxml")

    activites: list[Activite] = []
    for block in soup.find_all("div", class_="et_pb_text_inner"):
        h1 = block.find("h1")
        h2 = block.find("h2")
        if not h1 or not h2:
            continue
        organisateur = _normalize_organisateur(h1.get_text(strip=True))
        nom = h2.get_text(strip=True)
        if not organisateur or not nom:
            continue

        date_p = block.find("p")
        dates_text = date_p.get_text(strip=True) if date_p else ""
        end = _end_date(dates_text)
        if end is None or end < date.today():
            continue  # periode passee ou date illisible - on ignore plutot que deviner

        age_min = age_max = None
        lieu = "Non communiqué sur cette page"
        infos = ""
        for h3 in block.find_all("h3"):
            text = h3.get_text(" ", strip=True)
            label = text.split(":", 1)[0].strip().lower()
            value = text.split(":", 1)[1].strip() if ":" in text else ""
            if label == "age":
                m = AGE_RANGE_RE.search(text)
                if m:
                    age_min = float(m.group(1).replace(",", "."))
                    age_max = float(m.group(2).replace(",", "."))
            elif label == "lieu" and value:
                lieu = value
            elif label == "infos" and value:
                infos = value

        commune_match = COMMUNE_FROM_LIEU_RE.search(lieu)
        commune = commune_match.group(1).strip() if commune_match else ""

        activites.append(
            Activite(
                commune=commune,
                organisateur=organisateur,
                nom_activite=nom,
                type_activite=classify_type(nom, organisateur),
                dates=dates_text,
                age_min=age_min,
                age_max=age_max,
                prix="Non communiqué sur cette page",
                lieu=lieu,
                modalites_inscription=infos or f"Voir {PAGE_URL}",
                disponibilite="Non communiqué sur cette page",
                lien_source=PAGE_URL,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
