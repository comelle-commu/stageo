"""Scraper Ottignies-Louvain-la-Neuve (Plone/iMio) - Plaines de vacances (CLA).

Domaine réel : olln.be (pas ottignies-louvain-la-neuve.be, enregistré dans
IMIO_DOMAINS mais visiblement un ancien domaine - olln.be a été vérifié et
ajouté séparément dans common.IMIO_DOMAINS). Page en prose, une seule
période décrite en détail (grandes vacances) avec dates, lieu, âge et
tarifs dégressifs par enfant.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, find_plone_content, respectful_get

URL = (
    "https://www.olln.be/fr/vivre-a-olln/famille-enfance-et-jeunesse/"
    "stages-plaines/plaines-de-vacances-comm-cla/organisation-des-plaines-de-vacances"
)
COMMUNE = "Ottignies-Louvain-la-Neuve"

AGE_RE = re.compile(r"de\s+(\d+(?:[.,]\d+)?)\s*à\s*(\d+(?:[.,]\d+)?)\s*ans", re.I)
LIEU_RE = re.compile(r"Lieu\s*:\s*(.+?)\s*Encadrement", re.I)
HORAIRE_RE = re.compile(r"Horaires des activités\s*:\s*de\s+(\d{1,2})h(\d{2})?\s*à\s*(\d{1,2})h(\d{2})?", re.I)
PERIODE_RE = re.compile(
    r"Période d.activités\s*:\s*du\s+\w+\s+(\d{1,2})\s+(\w+)\s+au\s+\w+\s+(\d{1,2})\s+(\w+)\s+(\d{4})",
    re.I,
)
PRIX1_RE = re.compile(r"(\d+)\s*€/jour pour le 1er enfant", re.I)
PRIX2_RE = re.compile(r"(\d+)\s*€/jour pour le 2[eè]me enfant", re.I)
PRIX_HORS_RE = re.compile(r"(\d+)\s*€/jour pour les enfants non domicilié", re.I)


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    content = find_plone_content(soup)
    full_text = content.get_text(" ", strip=True)

    age_match = AGE_RE.search(full_text)
    age_min = float(age_match.group(1).replace(",", ".")) if age_match else None
    age_max = float(age_match.group(2).replace(",", ".")) if age_match else None

    lieu_match = LIEU_RE.search(full_text)
    lieu = lieu_match.group(1).strip() if lieu_match else "Non précisé sur cette page"

    horaire_match = HORAIRE_RE.search(full_text)
    horaire = f", de {horaire_match.group(1)}h à {horaire_match.group(3)}h" if horaire_match else ""

    periode_match = PERIODE_RE.search(full_text)
    dates = (
        f"Du {periode_match.group(1)} {periode_match.group(2)} au {periode_match.group(3)} {periode_match.group(4)} {periode_match.group(5)}{horaire}"
        if periode_match
        else "Non extrait automatiquement"
    )

    p1, p2, phors = PRIX1_RE.search(full_text), PRIX2_RE.search(full_text), PRIX_HORS_RE.search(full_text)
    prix_parts = []
    if p1:
        prix_parts.append(f"{p1.group(1)} €/jour (1er enfant ottintois)")
    if p2:
        prix_parts.append(f"{p2.group(1)} €/jour (2e enfant ottintois et suivants)")
    if phors:
        prix_parts.append(f"{phors.group(1)} €/jour (enfant non domicilié à Ottignies-LLN)")
    prix = " ; ".join(prix_parts) if prix_parts else "Non communiqué sur cette page"

    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    return [
        Activite(
            commune=COMMUNE,
            nom_activite="Plaines de vacances communales du CLA (grandes vacances)",
            type_activite=classify_type("Plaines de vacances communales du CLA"),
            dates=dates,
            age_min=age_min,
            age_max=age_max,
            prix=prix,
            lieu=lieu,
            modalites_inscription="Inscription en ligne ou auprès du Service Enseignement (numéro de registre national requis)",
            disponibilite=disponibilite,
            lien_source=URL,
        )
    ]


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
