"""Scraper Ferme de Roloux (ASBL "Petite Ferme de Roloux", Fexhe-le-Haut-Clocher).

Site vitrine simple (constructeur onlc.be), HTML statique classique, pas
d'obstacle JS contrairement a Cote Campagne (voir cote_campagne.py, mis en
attente pour cette raison). robots.txt permissif (aucun Disallow declare).

Organisateur prive, pas une commune -> `organisateur` porte la source,
`commune` est deduite du lieu connu (Fexhe-le-Haut-Clocher) - meme
convention que ADEPS/Cap Sciences (voir common.Activite).

Pas de dates calendaires exactes sur cette page ("vacances d'automne"
seulement) - signale explicitement plutot que d'inventer, meme logique
que Neupre (voir neupre.py).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

URL = "https://fermederoloux.onlc.be/10-Les-stages.html"
ORGANISATEUR = "Ferme de Roloux"
COMMUNE = "Fexhe-le-Haut-Clocher"

AGE_RE = re.compile(r"entre\s+(\d+)\s+ans(\s+et\s+demi)?\s+et\s+(\d+)\s+ans", re.I)
PRICE_RE = re.compile(r"Prix\s*:\s*(\d+)\s*€\s*ou\s*(\d+)\s*€\s*deuxième enfant\s*ou\s*(\d+)\s*€\s*à partir du troisième", re.I)
HORAIRE_RE = re.compile(r"Horaire de\s+(\d+)h\s+à\s+(\d+)h\s+avec accueil d[eé]s\s+(\d+)h\s+et jusqu.à\s+(\d+)h", re.I)


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    full_text = re.sub(r"\s+", " ", soup.find("body").get_text(" ")).strip()

    age_match = AGE_RE.search(full_text)
    age_min = float(age_match.group(1)) + (0.5 if age_match.group(2) else 0) if age_match else None
    age_max = float(age_match.group(3)) if age_match else None

    price_match = PRICE_RE.search(full_text)
    prix = (
        f"{price_match.group(1)} € (1er enfant), {price_match.group(2)} € (2e enfant), "
        f"{price_match.group(3)} € (à partir du 3e enfant)"
        if price_match
        else "Non communiqué sur cette page"
    )

    horaire_match = HORAIRE_RE.search(full_text)
    dates = "Vacances d'automne 2026 (dates exactes non précisées sur cette page)"
    if horaire_match:
        dates += f", de {horaire_match.group(1)}h à {horaire_match.group(2)}h (accueil de {horaire_match.group(3)}h à {horaire_match.group(4)}h)"

    nom_activite = "Stage à la ferme - Vacances d'automne (thème Marie Wabbes)"

    return [
        Activite(
            commune=COMMUNE,
            organisateur=ORGANISATEUR,
            nom_activite=nom_activite,
            type_activite=classify_type(nom_activite, ORGANISATEUR),
            dates=dates,
            age_min=age_min,
            age_max=age_max,
            prix=prix,
            lieu="Petite Ferme de Roloux, Fexhe-le-Haut-Clocher",
            modalites_inscription="Inscription par email uniquement, à partir du 24 août 19h (nom, prénom, date de naissance de l'enfant)",
            disponibilite="Non communiqué sur cette page",
            lien_source=URL,
        )
    ]


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
