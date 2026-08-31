"""Scraper Virton (Plone/iMio, province de Luxembourg) - Plaines communales.

Trouvé pendant le ratissage de la province de Luxembourg (31/08/2026) :
page unique en prose (comme Arlon/Mons), qui liste TOUTES les semaines de
plaines de l'année en une seule phrase ("Des semaines de plaines sont
organisées aux congés de printemps, d'été et d'automne... : du 4 au 8 mai
2026, du 20 juillet au 7 août 2026 (3 semaines), du 19 au 23 octobre
2026"). Un seul lieu (école communale de Chenois-Latour), un seul tarif
dégressif (1er/2e/3e enfant) et un seul âge (2,5-12 ans) s'appliquent à
toutes ces semaines - inutile de les traiter comme des "activités"
distinctes nommées, une entrée par semaine avec les mêmes infos communes
suffit (comme Arlon).

Légal : robots.txt iMio standard (signature confirmée, Crawl-delay 120),
page /gdpr-view lisible, aucun mot-clé anti-scraping trouvé.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, find_plone_content, respectful_get

URL = "https://www.virton.be/vivre-a-virton/activites-et-accueil-des-enfants/plaines-communales"
COMMUNE = "Virton"
LIEU = "École communale de Chenois-Latour, Virton"

DATE_RE = re.compile(
    r"du\s+(\d{1,2})(?:\s+(\w+))?\s+au\s+(\d{1,2})\s+(\w+)\s+(\d{4})(?:\s*\(([^)]+)\))?",
    re.I,
)

TARIF_RE = re.compile(
    r"Premier enfant\s*:\s*([\d,]+)\s*€\s*Deuxième enfant\s*:\s*([\d,]+)\s*€\s*"
    r"Troisième enfant et suivants\s*:\s*([\d,]+)\s*€",
    re.I,
)


def _format_periode(m: re.Match) -> str:
    d1, mois1, d2, mois2, annee, note = m.groups()
    base = f"du {d1} {mois1} au {d2} {mois2} {annee}" if mois1 else f"du {d1} au {d2} {mois2} {annee}"
    return f"{base} ({note})" if note else base


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)
    full_text = re.sub(r"\s+", " ", main.get_text(" ")).strip()

    tarif_match = TARIF_RE.search(full_text)
    prix = "Non communiqué sur cette page"
    if tarif_match:
        prix = (
            f"Par jour, semaine complète (règlement-redevance 2026-2031) : "
            f"{tarif_match.group(1)}€ (1er enfant), {tarif_match.group(2)}€ (2e enfant), "
            f"{tarif_match.group(3)}€ (3e enfant et suivants)"
        )

    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    activites: list[Activite] = []
    for m in DATE_RE.finditer(full_text):
        periode = _format_periode(m)
        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=f"Plaine communale de Virton - semaine {periode}",
                type_activite=classify_type("Plaine communale"),
                dates=periode,
                age_min=2.5,
                age_max=12.0,
                prix=prix,
                lieu=LIEU,
                modalites_inscription="Inscription via le Portail Parent de la Ville de Virton (voir lien source)",
                disponibilite=disponibilite,
                lien_source=URL,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités")
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
