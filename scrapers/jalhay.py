"""Scraper Jalhay (WordPress, pas iMio) - page unique "La Plaine Jalhay-
Sart" qui liste TOUTES les périodes de l'année (Détente, Printemps, Été,
Automne), chaque semaine sous forme "Semaine <ID> [:|–] du D au D / Thème
: NOM / description / Lieu : ... / Prix : ... / Paiement : ...".

Nombre de places limité par tranche d'âge (3-6 ans et 6-12 ans) mentionné
une fois en préambule, pas répété par semaine - âge fixé à 3-12 ans pour
toutes les activités de cette page (aucune semaine n'exclut l'une des
deux tranches).

Le nom du thème est en MAJUSCULES suivi d'un emoji sur la plupart des
semaines, mais pas toutes (ex. "LOONEY TUNES" enchaîne directement sur sa
description sans emoji ni ponctuation) - extraction par tokenisation
(mots en majuscules accumulés jusqu'au premier mot en casse normale)
plutôt que par une regex sur l'emoji, plus robuste à cette incohérence.
"""
from __future__ import annotations

import re
from html import unescape

from common import Activite, classify_type, respectful_get

URL = "https://www.jalhay.be/administration/services-communaux/atl/plaine/"
COMMUNE = "Jalhay"

BLOCK_RE = re.compile(r"(?=Semaine\s+\w+\d*\s*[:–-]+\s*du\s+\d{2}/\d{2}/\d{4})")
HEADER_RE = re.compile(r"Semaine\s+(\w+\d*)\s*[:–-]+\s*du\s+(\d{2}/\d{2}/\d{4})\s+au\s+(\d{2}/\d{2}/\d{4})")
THEME_RE = re.compile(r"Th[eè]me\s*:\s*(.{0,80})")
LIEU_RE = re.compile(r"Lieu\s*:\s*(.+?)(?=Prix\s*:)")
PRIX_RE = re.compile(r"Prix\s*:\s*(.+?)(?=Paiement\s*:|$)")


def _extract_theme(after_theme: str) -> str | None:
    words = []
    for tok in after_theme.split():
        core = re.sub(r"[^\w&']", "", tok, flags=re.UNICODE)
        if not core:
            continue
        if core.upper() != core:
            break
        words.append(core)
        if len(words) > 8:
            break
    return " ".join(words) if words else None


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    text = re.sub(r"<[^>]+>", " ", resp.text)
    text = unescape(re.sub(r"\s+", " ", text))

    activites: list[Activite] = []
    for block in BLOCK_RE.split(text)[1:]:
        header_m = HEADER_RE.search(block)
        if not header_m:
            continue
        semaine_id, j1, j2 = header_m.groups()
        dates = f"du {j1} au {j2}"

        theme_m = THEME_RE.search(block)
        theme = _extract_theme(theme_m.group(1)) if theme_m else None
        nom = f"Plaine de Jalhay-Sart - {theme}" if theme else f"Plaine de Jalhay-Sart - Semaine {semaine_id}"

        lieu_m = LIEU_RE.search(block)
        lieu = lieu_m.group(1).strip(" .") if lieu_m else ""
        lieu = lieu or "Non précisé sur cette page"

        prix_m = PRIX_RE.search(block)
        prix = prix_m.group(1).strip() if prix_m else "Non extrait automatiquement (voir page source)"

        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=nom,
                type_activite=classify_type(nom),
                dates=dates,
                age_min=3.0,
                age_max=12.0,
                prix=prix,
                lieu=lieu,
                modalites_inscription="Formulaire d'inscription en ligne (ouvert sur une période limitée avant chaque saison) - voir page source",
                disponibilite="Non communiqué sur cette page",
                lien_source=URL,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
