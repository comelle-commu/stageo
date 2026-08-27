"""Scraper Uccle (commune bruxelloise, Drupal) - Plaine de jeux communale.

Page unique, une seule offre ("Plaine de jeux communale", 2,5-13 ans) sur
toute la période annoncée - pas de stages nommés distincts comme à Forest.
Le prix varie selon 4 profils de résidence (repris tel quel en texte, pas
de tarif "moyen" inventé).

⚠️ Comme Forest, la page ne couvre au 27/08/2026 que l'été 2026 (déjà
terminé, inscriptions closes) - la commune republiera vraisemblablement la
même page pour la Toussaint. Regex volontairement génériques (pas de mot
"été"/"juillet" en dur) pour survivre à la mise à jour sans changement de code.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, respectful_get

URL = "https://www.uccle.be/fr/actualites/vie-pratique/enseignement/plaine-de-jeux-communale"
COMMUNE = "Uccle"

# "Du 6 juillet au 14 août 2026" (+ note de fermeture ponctuelle ignorée)
DATES_RE = re.compile(
    r"Du\s+(\d{1,2}\s+\w+)\s+au\s+(\d{1,2}\s+\w+\s+20\d{2})",
    re.I,
)
AGE_RE = re.compile(r"(\d{1,2})\s*ans?(\s*et\s+demi)?\s*à\s*(\d{1,2})\s*ans", re.I)
# Chaque profil ("Enfant ucclois...", "Autres enfants...") suivi de ": NN €".
# Ancré sur ces deux mots de tête plutôt qu'une longueur de caractères fixe -
# piège rencontré : une longueur max bornée coupait le premier profil
# ("Enfant ucclois bénéficiant d'un tarif réduit...", 60+ caractères) en
# plein milieu d'un mot pour rentrer dans la limite.
PRIX_RE = re.compile(r"((?:Enfant|Autres enfants)[^:;]{0,90}?)\s*:\s*(\d+)\s*€", re.I)
LIEU_RE = re.compile(r"Où\s*\?\s*(.+?)(?:Prix|$)", re.I)


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = soup.find("main") or soup
    full_text = re.sub(r"\s+", " ", main.get_text(" ")).strip()

    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    dates_match = DATES_RE.search(full_text)
    dates = f"du {dates_match.group(1)} au {dates_match.group(2)}" if dates_match else "Non extrait automatiquement"

    age_match = AGE_RE.search(full_text)
    if age_match:
        age_min = float(age_match.group(1)) + (0.5 if age_match.group(2) else 0)
        age_max = float(age_match.group(3))
    else:
        age_min, age_max = 2.5, 13.0

    lieu_match = LIEU_RE.search(full_text)
    lieu = lieu_match.group(1).strip() if lieu_match else "École de Calevoet, Uccle (voir page source)"

    prix_parts = [f"{profil.strip()} : {montant}€" for profil, montant in PRIX_RE.findall(full_text)]
    prix = " ; ".join(prix_parts) if prix_parts else "Non extrait automatiquement"

    return [
        Activite(
            commune=COMMUNE,
            nom_activite="Plaine de jeux communale",
            type_activite=classify_type("Plaine de jeux multi-activités"),
            dates=dates,
            age_min=age_min,
            age_max=age_max,
            prix=prix,
            lieu=lieu,
            modalites_inscription="Formulaire en ligne (voir page source) ou permanence au Service Éducation",
            disponibilite=disponibilite,
            lien_source=URL,
        )
    ]


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
