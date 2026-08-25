"""Scraper Ciney (Plone/iMio) - Plaines de vacances (organisées avec Ocarina Dinant).

Page unique en prose, deux lieux distincts (Ciney/Les Forges et Leignon)
avec des dates et un tarif résident/non-résident propres à chacun.
L'organisateur réel est Ocarina (Province de Namur), mais la page est
publiée par la commune elle-même -> `commune` reste "Ciney" (convention
des scrapers communaux, voir common.Activite).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, extract_disponibilite, find_plone_content, respectful_get

URL = "https://www.ciney.be/vivre-a-ciney/enfance/plaines-de-vacances"
COMMUNE = "Ciney"

LIEU_RE = re.compile(
    r"Du\s+(\d{1,2})(?:\s+(\w+))?\s+au\s+(\d{1,2})\s+(\w+)\s+(\d{4})\s*\(([^)]+)\)\s*à\s*([A-ZÉÈÀ']+)",
    re.I,
)
AGE_RE = re.compile(r"[aâ]g[ée]s?\s+de\s+(\d+(?:[.,]\d+)?)\s*à\s*(\d+(?:[.,]\d+)?)\s*ans", re.I)
PRICE_RE = re.compile(r"Enfant cinacien\s+(\d+)\s*€/semaine\s*-\s*Enfant non cinacien\s+(\d+)\s*€/semaine", re.I)
HORAIRE_RE = re.compile(r"[Aa]nimation dès\s+(\d{1,2})h\d*\s+jusqu.à\s+(\d{1,2})h\d*\s+et accueil gratuit dès\s+(\d{1,2})h\d*\s+et jusqu.à\s+(\d{1,2})h\d*", re.I)
INSCRIPTION_RE = re.compile(r"INSCRIPTION dès le\s+(\d{1,2}\s+\w+\s+\d{4})\s+sur\s+(?:le\s+)?(\S+)", re.I)


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    content = find_plone_content(soup)
    full_text = content.get_text(" ", strip=True)

    age_match = AGE_RE.search(full_text)
    age_min = float(age_match.group(1).replace(",", ".")) if age_match else None
    age_max = float(age_match.group(2).replace(",", ".")) if age_match else None

    price_match = PRICE_RE.search(full_text)
    prix_resident, prix_non_resident = (price_match.groups() if price_match else (None, None))

    horaire_match = HORAIRE_RE.search(full_text)
    horaire = (
        f", de {horaire_match.group(1)}h à {horaire_match.group(2)}h (accueil gratuit de {horaire_match.group(3)}h à {horaire_match.group(4)}h)"
        if horaire_match
        else ""
    )

    inscription_match = INSCRIPTION_RE.search(full_text)
    modalites = (
        f"Inscription dès le {inscription_match.group(1)} sur {inscription_match.group(2)}"
        if inscription_match
        else "Inscription via Ocarina (www.ocarina.be)"
    )

    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    activites: list[Activite] = []
    for d1, mois1, d2, mois2, annee, lieu_detail, ville in LIEU_RE.findall(full_text):
        mois1 = mois1 or mois2
        dates = f"Du {d1} {mois1} au {d2} {mois2} {annee}{horaire}"
        prix = (
            f"{prix_resident} €/semaine (enfant cinacien) — {prix_non_resident} €/semaine (non cinacien)"
            if price_match
            else "Non communiqué sur cette page"
        )
        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=f"Plaines de vacances Ciney — {ville.title()}",
                dates=dates,
                age_min=age_min,
                age_max=age_max,
                prix=prix,
                lieu=f"{lieu_detail}, {ville.title()}",
                modalites_inscription=modalites,
                disponibilite=disponibilite,
                lien_source=URL,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
