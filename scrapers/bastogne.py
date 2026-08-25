"""Scraper Bastogne (Plone/iMio) - Centres de vacances (CPAS).

Page structurée en blocs `<li>` (nom + tranche scolaire) suivis de
`<p>` Horaire / Accueil / Lieu - un parseur structurel (pas du regex sur
texte aplati) est plus fiable ici vu le nombre de blocs répétés.

Pas d'année indiquée nulle part sur la page pour les dates elles-mêmes
(seul un "© 2026" de pied de page traîne dans le HTML) - le champ `dates`
le signale explicitement plutôt que de deviner une année.

Les tranches d'âge sont données en niveau scolaire ("de la prématernelle
à la 6e primaire"), jamais en âge chiffré -> age_min/age_max restent
`None` (mêmes limites que Neupré, voir neupre.py).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, find_plone_content, respectful_get

URL = (
    "https://www.bastogne.be/cpas/famille-enfance-et-jeunesse/enfance/"
    "plaines-et-stages-conges-scolaires/projet-daccueil-centres-de-vacances"
)
COMMUNE = "Bastogne"

PROG_TITLE_RE = re.compile(r"^(.+?)\s*-\s*Service Famille et Enfance du CPAS\s*\(de la (.+?)\)", re.I)
HORAIRE_RE = re.compile(r"du\s+\w+\s+(\d{1,2})\s+au\s+\w+\s+(\d{1,2})\s+(\w+)\s*,\s*de\s+(\d{1,2})h\s*à\s*(\d{1,2})h", re.I)
ACCUEIL_RE = re.compile(r"Accueil à partir de\s+(\d{1,2})h\s*et jusque\s+(\d{1,2})h(\d{2})?", re.I)
LIEU_RE = re.compile(r"Lieu\s*:\s*(.+)", re.I)

TARIF_RESIDENT_RE = re.compile(
    r"domicili[ée]s dans la commune de Bastogne\s*:\s*semaine complète\s*:\s*(\d+)\s*€\s*\(1er enfant\),\s*(\d+)\s*€\s*\(2e enfant\)\s*et\s*(\d+)\s*€\s*\(3e enfant\)",
    re.I,
)
TARIF_EXTERNE_RE = re.compile(
    r"domicili[ée]s hors de la commune de Bastogne\s*:\s*semaine complète\s*:\s*(\d+)\s*€\s*\(1er enfant\),\s*(\d+)\s*€\s*\(2e enfant\)\s*et\s*(\d+)\s*€\s*\(3e enfant\)",
    re.I,
)


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", txt).strip()


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    content = find_plone_content(soup)
    full_text = content.get_text(" ", strip=True)

    resident_match = TARIF_RESIDENT_RE.search(full_text)
    externe_match = TARIF_EXTERNE_RE.search(full_text)
    prix = "Non communiqué sur cette page"
    if resident_match and externe_match:
        prix = (
            f"Semaine complète, domicilié Bastogne : {resident_match.group(1)}€ (1er enfant), "
            f"{resident_match.group(2)}€ (2e), {resident_match.group(3)}€ (3e) — "
            f"hors commune : {externe_match.group(1)}€/{externe_match.group(2)}€/{externe_match.group(3)}€"
        )

    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    text_div = content.find(class_="text") or content
    activites: list[Activite] = []
    current = None  # dict en cours de construction

    for el in text_div.find_all(["h2", "ul", "p"], recursive=True):
        if el.name == "ul":
            li = el.find("li")
            if not li:
                continue
            m = PROG_TITLE_RE.match(_clean(li.get_text(" ")))
            if not m:
                continue
            if current:
                activites.append(current)
            current = {
                "nom": m.group(1).strip(),
                "niveau": m.group(2).strip(),
                "horaire": None,
                "accueil": None,
                "lieu": None,
            }
        elif el.name == "p" and current is not None:
            txt = _clean(el.get_text(" "))
            h = HORAIRE_RE.search(txt)
            if h:
                current["horaire"] = f"du {h.group(1)} au {h.group(2)} {h.group(3)}, de {h.group(4)}h à {h.group(5)}h"
                continue
            a = ACCUEIL_RE.search(txt)
            if a:
                current["accueil"] = f"accueil de {a.group(1)}h à {a.group(2)}h{a.group(3) or ''}"
                continue
            l = LIEU_RE.search(txt)
            if l:
                current["lieu"] = l.group(1).strip()

    if current:
        activites.append(current)

    result: list[Activite] = []
    for prog in activites:
        dates = prog["horaire"] or "Non extrait automatiquement"
        dates += " (année non précisée sur la page)"
        if prog["accueil"]:
            dates += f" — {prog['accueil']}"
        result.append(
            Activite(
                commune=COMMUNE,
                nom_activite=f"{prog['nom']} — CPAS Bastogne (de la {prog['niveau']})",
                type_activite=classify_type(prog["nom"]),
                dates=dates,
                age_min=None,
                age_max=None,
                prix=prix,
                lieu=prog["lieu"] or "Non précisé sur cette page",
                modalites_inscription="Inscription via www.bastogne.be/cpas/famille-enfance-et-jeunesse",
                disponibilite=disponibilite,
                lien_source=URL,
            )
        )

    return result


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
