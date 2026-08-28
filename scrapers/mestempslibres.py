"""Scraper "Mes Temps Libres" (mestempslibres.be) - plateforme WordPress
mutualisée pour 3 communes de la province de Liège (Anthisnes, Comblain-
au-Pont, Esneux), trouvée en explorant les screenshots de recherche
Google de la fondatrice. Chaque commune a une page dédiée
(`/stages-plaines/<commune>/`) qui pointe vers un dépliant PDF au nom
variable d'une année à l'autre ("Depliant-stages-Anthisnes-Automne-
Hiver-2025.pdf") - découverte dynamique du lien nécessaire (comme
stavelot.py/faimes.py), MAIS le lien lui-même est caché derrière une
double couche d'encodage (attribut HTML url-encodé contenant du JSON
lui-même échappé en `\\/`) : `_find_pdf_url()` fait `unquote()` puis
cherche `"link":"...pdf"` dans le texte décodé.

Esneux n'est PAS traité ici : sa page redirige explicitement vers son
propre site (déjà couvert par `esneux.py`), pas de contenu propre sur
cette plateforme.

Au 28/08/2026, seule la page Anthisnes a un PDF (celui de la saison
"Automne-Hiver 2025", pas encore remplacé par l'édition 2026 - le run
hebdomadaire le réextraira automatiquement dès republication, comme pour
les communes "Agenda Omnia" en attente). Comblain-au-Pont n'a
actuellement aucun PDF lié (page vide) - `_find_pdf_url()` retourne None
et la commune est silencieusement ignorée ce run-ci, sans erreur.

Format du PDF (validé sur l'édition Anthisnes 2025, un bloc par stage) :
"STAGE N : DU <jour> <j1> [<mois1>] AU <jour> <j2> <mois2> <année>"
puis une ligne "<titre> ! <âge> – <âge> ans", une description libre,
le nom de l'organisme, "Prix : ..." et "Lieu : ...". mois1 est parfois
absent quand les deux dates tombent dans le même mois ("DU LUNDI 22 AU
MARDI 23 DÉCEMBRE 2025") - géré par un lookahead qui empêche de capturer
"AU" comme mois par erreur.
"""
from __future__ import annotations

import re
import urllib.parse

from common import Activite, classify_type, respectful_get

BASE_URL = "https://mestempslibres.be"
# slug -> nom de commune tel qu'affiché ailleurs sur le site
COMMUNES = {"anthisnes": "Anthisnes", "comblain-au-pont": "Comblain-au-Pont"}

STAGE_BLOCK_RE = re.compile(r"(?=STAGE\s+\d+\s*:)")
DATE_RE = re.compile(
    r"DU\s+\w+\s+(\d{1,2})(?:\s+(?!AU\b)(\w+))?\s+AU\s+\w+\s+(\d{1,2})\s+(\w+)\s+(\d{4})",
    re.I,
)
AGE_RE = re.compile(r"([\d.,]+)\s*[–-]\s*([\d.,]+)\s*ans", re.I)
ORG_RE = re.compile(r"\n([^\n]{3,80})\nPrix\s*:", re.I)
PRIX_RE = re.compile(r"Prix\s*:\s*([^\n]+)", re.I)
LIEU_RE = re.compile(r"Lieu\s*:\s*([^\n]+)", re.I)


def _find_pdf_url(commune_slug: str) -> str | None:
    resp = respectful_get(f"{BASE_URL}/stages-plaines/{commune_slug}/")
    decoded = urllib.parse.unquote(resp.text)
    m = re.search(r'"link":"([^"]+\.pdf)"', decoded)
    return m.group(1).replace("\\/", "/") if m else None


def _extract_pdf_text(pdf_url: str) -> str:
    from common import fetch_pdf_bytes, extract_pdf_text

    return extract_pdf_text(fetch_pdf_bytes(pdf_url))


def _parse_block(block: str, commune: str, pdf_url: str) -> Activite | None:
    date_m = DATE_RE.search(block)
    if not date_m:
        return None
    j1, mois1, j2, mois2, annee = date_m.groups()
    mois1 = mois1 or mois2
    dates = f"du {j1} {mois1.lower()} au {j2} {mois2.lower()} {annee}"

    lines = [l.strip() for l in block.split("\n") if l.strip()]
    if len(lines) < 2:
        return None
    titre_line = lines[1]
    age_m = AGE_RE.search(titre_line)
    age_min, age_max = (
        (float(age_m.group(1).replace(",", ".")), float(age_m.group(2).replace(",", ".")))
        if age_m
        else (None, None)
    )
    nom = (titre_line[: age_m.start()] if age_m else titre_line).strip(" !")

    org_m = ORG_RE.search(block)
    organisateur = org_m.group(1).strip() if org_m else None

    prix_m = PRIX_RE.search(block)
    prix = prix_m.group(1).strip() if prix_m else "Non extrait automatiquement (voir PDF source)"

    lieu_m = LIEU_RE.search(block)
    lieu = lieu_m.group(1).strip() if lieu_m else "Non précisé sur cette page"

    return Activite(
        commune=commune,
        organisateur=organisateur,
        nom_activite=nom,
        type_activite=classify_type(nom, organisateur),
        dates=dates,
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu=lieu,
        modalites_inscription="Voir le dépliant PDF source pour les modalités d'inscription",
        disponibilite="Non communiqué sur cette page",
        lien_source=pdf_url,
    )


def scrape() -> list[Activite]:
    activites: list[Activite] = []
    for slug, commune in COMMUNES.items():
        pdf_url = _find_pdf_url(slug)
        if pdf_url is None:
            continue
        text = _extract_pdf_text(pdf_url)
        blocks = STAGE_BLOCK_RE.split(text)[1:]
        for block in blocks:
            activite = _parse_block(block, commune, pdf_url)
            if activite is not None:
                activites.append(activite)
    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
