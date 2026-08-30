"""Scraper Royal Hockey Club Verviers (RHCV, WordPress) - Stages de hockey
"Bélier Hockey School", terrains situés à Heusy (Drève de Maison-Bois,
4800 Verviers - juste à côté de la sortie 7 de l'E42, "Heusy").

Page unique (voir PAGE_URL), un <h2> par stage suivi de 3 <p> (dates,
âges, lien d'inscription) puis un <hr> avant le stage suivant - structure
HTML propre et stable (pas de texte libre à deviner comme pour Aubange).
Seul le tout premier <h2> de la page ("Du hockey, du plaisir...") n'est
pas un stage - repéré en vérifiant que le <p> suivant commence bien par
"Du " (toutes les dates de stage suivent ce format).

`lien_source` pointe vers le lien "S'inscrire" propre à CHAQUE stage
(formulaire Google dédié) plutôt que vers la page générale - plus utile
pour un parent qui clique depuis Trouvéo.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

PAGE_URL = "https://www.rhcv.be/nos-stages/"
COMMUNE = "Heusy"
ORGANISATEUR = "Royal Hockey Club Verviers"

DATE_RE = re.compile(r"^Du\s", re.I)
AGE_RANGE_RE = re.compile(r"(\d{1,2})\s*à\s*(\d{1,2})\s*ans", re.I)
AGE_MIN_ONLY_RE = re.compile(r"[àa]\s*partir\s*de\s*(\d{1,2})\s*ans", re.I)
INSCRIPTION_RE = re.compile(r"S.inscrire\s*:\s*(\S+)", re.I)


def _clean_title(title: str) -> str:
    # Retire les emojis en tete de titre (garde le texte, ex.
    # "🍂 Stage d'Automne (Toussaint)" -> "Stage d'Automne (Toussaint)").
    return re.sub(r"^[^\wÀ-ÿ]+", "", title).strip()


def scrape() -> list[Activite]:
    resp = respectful_get(PAGE_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = soup.find("main") or soup

    activites: list[Activite] = []
    for h2 in main.find_all("h2"):
        date_p = h2.find_next_sibling("p")
        if date_p is None:
            continue
        dates = date_p.get_text(" ", strip=True)
        if not DATE_RE.match(dates):
            continue  # pas un bloc de stage (ex. le tout premier h2, intro)

        nom = _clean_title(h2.get_text(" ", strip=True))

        age_p = date_p.find_next_sibling("p")
        age_text = age_p.get_text(" ", strip=True) if age_p else ""
        range_match = AGE_RANGE_RE.search(age_text)
        if range_match:
            age_min, age_max = float(range_match.group(1)), float(range_match.group(2))
        else:
            min_match = AGE_MIN_ONLY_RE.search(age_text)
            age_min = float(min_match.group(1)) if min_match else None
            age_max = None

        inscription_p = age_p.find_next_sibling("p") if age_p else None
        # Le lien reel est dans le href du <a> - le texte visible n'est pas
        # toujours l'URL elle-meme (ex. "Bélier&Brebis Hockey Camp - Aout
        # 2026" comme libelle, voir le stage "Béliers/Brebis Hockey Camp").
        link_tag = inscription_p.find("a", href=True) if inscription_p else None
        if link_tag:
            lien = link_tag["href"]
        else:
            inscription_text = inscription_p.get_text(" ", strip=True) if inscription_p else ""
            link_match = INSCRIPTION_RE.search(inscription_text)
            lien = link_match.group(1) if link_match else PAGE_URL

        activites.append(
            Activite(
                commune=COMMUNE,
                organisateur=ORGANISATEUR,
                nom_activite=nom,
                type_activite=classify_type(nom, ORGANISATEUR),
                dates=dates,
                age_min=age_min,
                age_max=age_max,
                prix="Non communiqué sur cette page (voir lien d'inscription pour le tarif exact)",
                lieu="RHCV, Drève de Maison-Bois 18, 4800 Verviers (Heusy)",
                modalites_inscription=f"Inscription en ligne : {lien}",
                disponibilite="Non communiqué sur cette page",
                lien_source=lien if lien.startswith("http") else PAGE_URL,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
