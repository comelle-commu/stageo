"""Scraper Neupré (Nuxt.js, rendu cote serveur) - Plaines de vacances (page vitrine).

Page unique. Malgré l'apparence de SPA JavaScript, le contenu est déjà
présent dans le HTML retourné par une simple requête HTTP (SSR) - pas besoin
de navigateur headless (vérifié pendant l'investigation réseau).

La page est structurée en Q&A ("Quand ?", "Lieu ?", "Quel est le montant à
payer ?", ...) suivies de paragraphes/listes de réponse. L'inscription se
fait sur APSCHOOL (lien extrait) ; cette page vitrine reste elle-même
librement consultable.

Une ligne par groupe d'âge (5 groupes nommés sur la page). Les tranches
d'âge par groupe ne sont pas données en chiffres sur la page (seulement en
niveau scolaire belge) : elles sont dérivées via une table de correspondance
approximative, signalée comme telle dans le champ correspondant.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, respectful_get

URL = "https://www.neupre.be/neupre/information/plaines-de-vacances"
COMMUNE = "Neupre"

AGE_GLOBAL_RE = re.compile(r"de\s*([\d,]+)\s*à\s*([\d,]+)\s*ans", re.I)

# Correspondance approximative niveau scolaire belge -> tranche d'âge.
# Non fournie par la page elle-même (qui ne donne que la tranche globale
# 2,5-12 ans) : dérivée ici pour être exploitable, à vérifier/affiner.
NIVEAU_AGE_MAP = {
    "classe d'accueil": (2.5, 3.0),
    "1ère et 2ème maternelle": (3.0, 5.0),
    "3ème maternelle et 1ère primaire": (5.0, 6.0),
    "2ème et 3ème primaire": (7.0, 8.0),
    "4ème, 5ème et 6ème primaire": (9.0, 11.0),
}


def _clean_text(tag) -> str:
    """get_text() SANS separator pour un élément à enfants purement inline
    (p, li, strong...) : le HTML source contient déjà les espaces naturels,
    et get_text(" ") coupe parfois des mots en deux aux frontières de balise
    (voir seraing.py pour un exemple concret)."""
    return re.sub(r"\s+", " ", tag.get_text()).strip()


def _block_text(tag) -> str:
    """Pour un conteneur à enfants block-level (ul, div...) : BeautifulSoup
    n'insère aucun séparateur entre deux <li>/<p> voisins, donc get_text()
    seul les recolle ("...Printemps" + "les cinq..." -> "Printempsles cinq").
    On force un espace entre chaque enfant direct."""
    return " ".join(_clean_text(child) for child in tag.find_all(recursive=False) if _clean_text(child))


def _find_section(paragraphs, question: str):
    """Retourne le texte des <li>/<p> qui suivent un <p> dont le texte == question,
    jusqu'au <p> suivant qui ressemble à une nouvelle question (se termine par '?')."""
    for p in paragraphs:
        if _clean_text(p).rstrip("﻿") == question:
            texts = []
            for sib in p.find_next_siblings():
                if sib.name == "p":
                    sib_text = _clean_text(sib)
                    if sib_text.endswith("?"):
                        break
                    if sib_text:
                        texts.append(sib_text)
                elif sib.name in ("ul", "ol"):
                    texts.append(_block_text(sib))
                if len(texts) >= 6:  # garde-fou
                    break
            return texts
    return []


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    content_divs = soup.find_all("div", class_="lgc-html")
    content = max(content_divs, key=lambda d: len(d.get_text())) if content_divs else soup

    full_text = _block_text(content)
    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    age_match = AGE_GLOBAL_RE.search(full_text)
    age_min_global, age_max_global = (
        (float(x.replace(",", ".")) for x in age_match.groups()) if age_match else (None, None)
    )
    if age_match:
        age_min_global, age_max_global = (float(x.replace(",", ".")) for x in age_match.groups())

    groupes = []  # (nom, description_niveau)
    for li in content.find_all("li"):
        txt = _clean_text(li)
        m = re.match(r"([A-ZÉÈ' ]{3,})\s*-\s*Enfants?\s+de\s+(.+)", txt)
        if m:
            groupes.append((m.group(1).strip().title(), m.group(2).strip()))

    paragraphs = content.find_all("p")
    lieu_parts = _find_section(paragraphs, "Lieu ?")
    lieu = " ".join(lieu_parts) if lieu_parts else "Non extrait automatiquement"

    montant_parts = _find_section(paragraphs, "Quel est le montant à payer ?")
    prix = " ; ".join(montant_parts) if montant_parts else "Non extrait automatiquement"

    quand_parts = _find_section(paragraphs, "Quand ?")
    dates = (
        " ".join(quand_parts)
        + " (dates calendaires exactes non données sur cette page - voir brochure PDF jointe)"
        if quand_parts
        else "Non extrait automatiquement"
    )

    apschool_link_match = re.search(r"https://plateforme\.apschool\.be/\S+", full_text)
    apschool_link = apschool_link_match.group(0) if apschool_link_match else None
    modalites = "Compte APSCHOOL requis" + (f" ({apschool_link})" if apschool_link else "")

    activites: list[Activite] = []
    for nom_groupe, niveau_desc in groupes:
        age_min, age_max = NIVEAU_AGE_MAP.get(niveau_desc.lower(), (None, None))
        note_age = "" if age_min is not None else " [tranche d'âge du groupe non déterminée]"
        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=f"Plaines de vacances Neupre - {nom_groupe} (Enfants de {niveau_desc}){note_age}",
                type_activite=classify_type(nom_groupe),
                dates=dates,
                age_min=age_min if age_min is not None else age_min_global,
                age_max=age_max if age_max is not None else age_max_global,
                prix=prix,
                lieu=lieu,
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
