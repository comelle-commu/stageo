"""Scraper La Louvière (Plone/iMio) - Centres de Vacances.

Domaine réel : atl.lalouviere.be (sous-domaine ATL, comme Fléron), ajouté
séparément dans common.IMIO_DOMAINS. Page de présentation générale (pas de
dates calendaires précises - "vacances d'automne, de détente, de printemps
et d'été", lieux variables) : contrairement à Ans/Mons/Ciney, il n'y a pas
de dates chiffrées à extraire, seulement une description permanente du
dispositif. Le champ `dates` le signale explicitement plutôt que d'inventer
des dates, même logique que Neupré (voir neupre.py).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, find_plone_content, respectful_get

URL = "https://atl.lalouviere.be/vacances-scolaires/centres-de-vacances"
COMMUNE = "La Louviere"

AGE_RE = re.compile(
    r"[Ee]nfants de\s+(\d+(?:[.,]\d+)?)\s*ans?\s*à\s*(\d+(?:[.,]\d+)?)\s*ans",
    re.I,
)
PRIX_RE = re.compile(r"Prix\s*:\s*([^G]+?)(?:Garderie|$)", re.I)
GARDERIE_RE = re.compile(r"Garderie\s*:\s*(.+?)(?=Inscriptions\s*:)", re.I)


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    content = find_plone_content(soup)
    full_text = content.get_text(" ", strip=True)

    age_match = AGE_RE.search(full_text)
    age_min = float(age_match.group(1).replace(",", ".")) if age_match else 2.5
    age_max = float(age_match.group(2).replace(",", ".")) if age_match else None

    prix_match = PRIX_RE.search(full_text)
    prix = prix_match.group(1).strip() if prix_match else "Non communiqué sur cette page"
    garderie_match = GARDERIE_RE.search(full_text)
    if garderie_match:
        prix += f" ; garderie {garderie_match.group(1).strip()}"

    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    return [
        Activite(
            commune=COMMUNE,
            nom_activite="Centres de Vacances de La Louvière (automne, détente, printemps, été)",
            type_activite=classify_type("Centres de Vacances de La Louvière"),
            dates=(
                "Dates précises non données sur cette page - se déroulent chaque période de "
                "vacances scolaires (automne, détente/Carnaval, printemps/Pâques, été), voir "
                "le programme des stages en cours sur le site"
            ),
            age_min=age_min,
            age_max=age_max,
            prix=prix,
            lieu="Écoles de l'entité louviéroise, lieu variable selon la période",
            modalites_inscription="Inscription en ligne exclusivement, via l'e-Guichet de la Ville de La Louvière",
            disponibilite=disponibilite,
            lien_source=URL,
        )
    ]


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
