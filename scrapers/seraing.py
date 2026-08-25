"""Scraper Seraing (WordPress) - Plaines de vacances d'été.

Page unique, HTML statique. Les infos clés (dates, sites, âges) sont
encadrées par des balises <strong> dans le premier paragraphe descriptif -
extraction structurelle plutôt que regex sur texte libre.
Une ligne par site de plaine (9 sites nommés sur la page).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, respectful_get

URL = "https://www.seraing.be/plaines-2026-inscriptions/"
COMMUNE = "Seraing"

AGE_RE = re.compile(r"de\s*([\d,]+)\s*à\s*([\d,]+)\s*ans", re.I)


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def _clean_text(tag) -> str:
    """get_text() SANS separator : les noeuds texte du HTML source
    contiennent déjà les espaces naturels entre mots. get_text(" ") force un
    espace à chaque frontière de balise, ce qui coupe des mots en deux
    lorsque le HTML source enchaîne un <strong> juste après une lettre
    (ex. vu sur cette page : "pour l<strong>es suivants</strong>" ->
    get_text(" ") donnerait "l es suivants" au lieu de "les suivants")."""
    return re.sub(r"\s+", " ", tag.get_text()).strip()


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    content = soup.find(class_="entry-content") or soup.find("article") or soup

    full_text = _clean_text(content)
    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    # Le paragraphe descriptif "Du X au Y, les plaines A, B, ... accueilleront
    # les enfants de M à N ans" est identifié via ses balises <strong>.
    paragraphs = content.find_all("p")
    date_range = None
    site_names: list[str] = []
    age_min = age_max = None
    for p in paragraphs:
        strongs = [_clean_text(s) for s in p.find_all("strong")]
        if not strongs:
            continue
        text = _clean_text(p)
        age_match = AGE_RE.search(text)
        if "les plaines" in text.lower() and age_match:
            date_range = strongs[0]
            age_min, age_max = (_to_float(x) for x in age_match.groups())
            # tout ce qui n'est ni la date (1er strong) ni la tranche d'âge
            # (dernier strong, "de X à Y ans") est un nom de site
            site_names = strongs[1:-1]
            break

    year_match = re.search(r"\b(20\d{2})\b", resp.url) or re.search(r"\b(20\d{2})\b", full_text)
    year = year_match.group(1) if year_match else ""
    dates = f"{date_range} {year}".strip() if date_range else "Non extrait automatiquement"

    price_match = re.search(
        r"tarif\s+est\s+fix[ée]\s+à\s+([^.]*premier enfant[^.]*)\.", full_text, re.I
    )
    prix = price_match.group(1).strip() if price_match else "Non extrait automatiquement"
    accueil_match = re.search(r"([\d,]+\s*€\s*la\s*demi-heure)", full_text, re.I)
    if accueil_match:
        prix += f" ; accueil élargi (7h-9h/16h-18h) : {accueil_match.group(1)}"

    modalites = (
        "Compte eID ou application Itsme sur www.seraing.be/atl "
        "(numero de registre national requis) ; ouverture des inscriptions "
        "par vagues selon priorité de résidence/travail (voir page source pour les dates exactes)"
    )

    if not site_names:
        # repli : une seule ligne "Seraing (ensemble des plaines)" si l'extraction structurelle échoue
        site_names = ["Ensemble des plaines communales"]

    activites = [
        Activite(
            commune=COMMUNE,
            nom_activite=f"Plaine de vacances - {site}",
            type_activite=classify_type(site),
            dates=dates,
            age_min=age_min,
            age_max=age_max,
            prix=prix,
            lieu=f"Seraing - site \"{site}\"",
            modalites_inscription=modalites,
            disponibilite=disponibilite,
            lien_source=URL,
        )
        for site in site_names
    ]
    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
