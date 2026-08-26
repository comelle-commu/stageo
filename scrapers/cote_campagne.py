"""Scraper Côté Campagne (ferme pédagogique, Awans) - Stages été.

Site en JavaScript pur (le lien réel des stages est caché derrière un
gestionnaire `onclick`, pas un href exploitable) - nécessite
common.fetch_rendered_html() (Playwright) plutôt que respectful_get().
Voir docs sur l'ajout de cette dépendance au pipeline (25/08/2026).

Structure de la page : deux groupes de semaines ("Ferme et poney club"
sur 2 semaines en juillet, "Ferme/Poney club/Equitation" sur 3 semaines
en août), puis 3 "formules" avec âge et prix propres. L'équitation n'est
proposée que sur les 3 semaines d'août (pas en juillet) - une Activite
par formule, avec la liste de semaines qui la concernent réellement.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, fetch_rendered_html

URL = "https://www.cotecampagne.com/stages-a"
HOMEPAGE_URL = "https://www.cotecampagne.com/"
ORGANISATEUR = "Côté Campagne"
COMMUNE = "Awans"

WEEK_RE = re.compile(r"Du\s+(\d{1,2})\s+au\s+(\d{1,2})\s+(\w+)", re.I)
YEAR_RE = re.compile(r"ETE\s+(\d{4})", re.I)
HORAIRE_RE = re.compile(r"Horaires\s*:\s*de\s+(\d{1,2})h\s+à\s+(\d{1,2})h", re.I)
PRICE_BLOCK_RE = re.compile(r"Prix\s*:(.+?)(?:Réductions|Inscriptions)", re.I)


def _weeks_between(text: str, start_marker: str, end_marker: str, year: str) -> list[str]:
    segment = text.split(start_marker, 1)[1].split(end_marker, 1)[0] if end_marker in text.split(start_marker, 1)[1] else text.split(start_marker, 1)[1]
    return [f"du {d1} au {d2} {mois} {year}" for d1, d2, mois in WEEK_RE.findall(segment)]


def scrape() -> list[Activite]:
    html = fetch_rendered_html(HOMEPAGE_URL, click_selector='a[href*="stages"]')
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    full_text = re.sub(r"\s+", " ", soup.find("body").get_text(" ")).strip()

    year_match = YEAR_RE.search(full_text)
    year = year_match.group(1) if year_match else "2026"

    juillet_weeks = _weeks_between(full_text, "Ferme et poney club:", "Ferme/Poney club", year)
    aout_weeks = _weeks_between(full_text, "Ferme/Poney club/Equitation:", "Les 3 formules", year)
    toutes_semaines = juillet_weeks + aout_weeks

    horaire_match = HORAIRE_RE.search(full_text)
    horaires = f", de {horaire_match.group(1)}h à {horaire_match.group(2)}h (garderie 8h-9h et 16h-17h)" if horaire_match else ""

    price_block = PRICE_BLOCK_RE.search(full_text)
    price_text = price_block.group(1) if price_block else ""
    ferme_price = re.search(r"Ferme\s*:\s*(\d+)\s*€", price_text)
    poney_price = re.search(r"Poney club\s*:\s*(\d+)\s*€", price_text)
    equitation_price = re.search(r"Equitation\s*:\s*(\d+)\s*€", price_text)

    lieu = "Côté Campagne, Awans"
    modalites = "Inscription UNIQUEMENT par SMS au 0472/41.03.29 (nom, prénom, date de naissance, formule et semaine choisies)"
    reduction = "Réduction de 5 €/enfant à partir de deux enfants inscrits."

    formules = [
        ("Ferme", toutes_semaines, "de 3 à 12 ans", 3.0, 12.0, ferme_price),
        ("Poney Club", toutes_semaines, "de 4 à 7 ans", 4.0, 7.0, poney_price),
        ("Equitation", aout_weeks, "à partir de 7 ans", 7.0, None, equitation_price),
    ]

    activites: list[Activite] = []
    for nom_formule, semaines, age_desc, age_min, age_max, price_match in formules:
        if not semaines:
            continue
        prix = f"{price_match.group(1)} € par semaine" if price_match else "Non communiqué sur cette page"
        if nom_formule == "Equitation" and price_match:
            prix += " (+7 € d'assurance si non affilié LEWB)"
        prix += f". {reduction}"
        nom_activite = f"Stage {nom_formule} - Côté Campagne ({age_desc})"
        activites.append(
            Activite(
                commune=COMMUNE,
                organisateur=ORGANISATEUR,
                nom_activite=nom_activite,
                type_activite=classify_type(nom_activite, ORGANISATEUR),
                dates=f"Été {year} : {', '.join(semaines)}{horaires}",
                age_min=age_min,
                age_max=age_max,
                prix=prix,
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
