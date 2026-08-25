"""Scraper Grace-Hollogne (Plone/iMio) - Plaines de vacances.

La page vitrine (`URL_PAGE`) ne donne que les 4 centres et leur tranche
d'age (lien Google Forms par centre). Les vraies infos utiles (dates,
prix, adresses par centre) sont dans le PDF joint ("depliant" texte natif,
pas un scan) -> `URL_PDF` est la source principale de ce parseur, comme
pour Herstal.

Piege rencontre dans le PDF : le centre Defuisseaux (2,5-3 ans) est
imprime "21/2" au lieu de "2 1/2" (fusion sans espace dans le texte
natif) -> cas particulier gere dans `_parse_age()`.
"""
from __future__ import annotations

import re

from common import Activite, classify_type, fetch_pdf_bytes, extract_pdf_text, is_pdf

URL_PAGE = "https://www.grace-hollogne.be/loisirs/sports/plaines-de-vacances-2026"
URL_PDF = "https://www.grace-hollogne.be/loisirs/sports/finalplainev4.pdf"
COMMUNE = "Grace-Hollogne"

CENTRE_RE = re.compile(
    r"Le centre\s+(.+?)\s*-\s*Ecole\s+([^\n]+?)\s*\n\s*(Rue[^\n]+)\s*\n\s*"
    r"sera r[ée]serv[ée] aux enfants [aâ]g[ée]s de\s+([\d/]+)\s*[àa]\s+(\d+)\s*ans",
    re.I,
)
DATES_RE = re.compile(
    r"ENTRE LE (\w+) (\d{1,2}) (\w+) (\d{4}) ET\s*\n?\s*"
    r"LE (\w+) (\d{1,2}) (\w+) (\d{4}) INCLUS\s*\n?\s*DE (\d{1,2})H A (\d{1,2})H",
    re.I,
)
PRIX_JOUR_RE = re.compile(r"(\d+)\s*€\s*par jour et par enfant", re.I)
PRIX_EXCURSION_RE = re.compile(r"participation suppl[ée]mentaire de\s*(\d+)\s*€", re.I)


def _parse_age(token: str) -> float:
    # "21/2" = artefact d'extraction PDF pour "2 1/2" (espace perdue) - vu
    # uniquement sur le centre Defuisseaux, jamais ailleurs sur ce document.
    if token == "21/2":
        return 2.5
    if "/" in token:
        whole, frac = token.split("/") if token.count("/") == 1 else (token, "1")
        num, den = frac, "1"
        return float(whole) if whole else 0.0
    return float(token.replace(",", "."))


def scrape() -> list[Activite]:
    pdf_bytes = fetch_pdf_bytes(URL_PDF)
    if not is_pdf(pdf_bytes):
        return []
    text = extract_pdf_text(pdf_bytes)

    dates = "Non communiqué sur cette page"
    m = DATES_RE.search(text)
    if m:
        _, d1, mois1, y1, _, d2, mois2, y2, h1, h2 = m.groups()
        dates = f"Du {d1} {mois1.lower()} {y1} au {d2} {mois2.lower()} {y2} inclus, de {h1}h à {h2}h"

    prix_jour = PRIX_JOUR_RE.search(text)
    prix_excursion = PRIX_EXCURSION_RE.search(text)
    prix = "Non communiqué sur cette page"
    if prix_jour:
        prix = f"{prix_jour.group(1)} €/jour/enfant (collation, dîner, collation)"
        if prix_excursion:
            prix += f" + {prix_excursion.group(1)} € supplémentaires par excursion"

    # "dossier complet" (obligatoire pour l'inscription) apparaît sur cette
    # page mais ne signifie PAS "plus de places" - piège du même type que
    # "semaine complète" sur Neupré. extract_disponibilite() n'est donc pas
    # utilisé ici pour éviter un faux positif COMPLET.
    disponibilite = "Non communiqué sur cette page"

    modalites = (
        "Inscription en ligne par centre (formulaire dédié, voir "
        f"{URL_PAGE}) + dossier complet obligatoire (fiche médicale, "
        "règlement d'ordre intérieur signé)"
    )

    activites: list[Activite] = []
    for nom_centre, ecole, adresse, age_min_tok, age_max_tok in CENTRE_RE.findall(text):
        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=f"Plaines de vacances Grâce-Hollogne - Centre {nom_centre.strip()}",
                type_activite=classify_type("Plaines de vacances Grâce-Hollogne"),
                dates=dates,
                age_min=_parse_age(age_min_tok),
                age_max=float(age_max_tok),
                prix=prix,
                lieu=f"Ecole {ecole.strip()}, {adresse.strip()}",
                modalites_inscription=modalites,
                disponibilite=disponibilite,
                lien_source=URL_PDF,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
