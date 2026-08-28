"""Scraper Faimes (iMio) - brochure PDF "Accueil extrascolaire", stages par
période de vacances scolaire 2026-2027.

Contrairement à la page web elle-même (juste une description de
l'infrastructure de la plaine de jeux, sans dates), la vraie donnée vit
dans un PDF texte natif lié depuis une actualité séparée
(`/actualites/decouvrez-la-brochure-extrascolaire-2026-2027`) - une seule
page du PDF (texte propre, pas de tableau) couvre TOUTES les périodes de
l'année scolaire (Toussaint x2 semaines, Noël, Détente, Printemps x2
semaines), avec un format répété "Semaine du D au D <mois> <année> :"
suivi du ou des thèmes.

Chaque semaine distingue parfois "les petits" (2,5-5 ans) des "grands"
(6-12 ans) avec un thème différent chacun (-> deux lignes), parfois un
thème unique "pour les petits et les grands" (-> une ligne, une seule
Activite couvrant 2,5-12 ans).
"""
from __future__ import annotations

import io
import re

import pdfplumber
from bs4 import BeautifulSoup

from common import Activite, classify_type, fetch_pdf_bytes, is_pdf, respectful_get

ARTICLE_URL = "https://www.faimes.be/actualites/decouvrez-la-brochure-extrascolaire-2026-2027"
COMMUNE = "Faimes"

WEEK_RE = re.compile(
    r"Semaine du\s+(\d{1,2})\s+au\s+(\d{1,2})\s+(\w+)\s+(\d{4})\s*:?\s*\n(.+?)(?=Semaine du|\Z)",
    re.S,
)
PETITS_GRANDS_UNIQUE_RE = re.compile(r"(.+?)\s*pour les petits et les grands", re.I)
PETITS_RE = re.compile(r"(.+?)\s*pour les petits\b", re.I)
GRANDS_RE = re.compile(r"(.+?)\s*pour les grands\b", re.I)

AGE_PETITS = (2.5, 5.0)
AGE_GRANDS = (6.0, 12.0)
AGE_TOUS = (2.5, 12.0)


def _find_pdf_url() -> str:
    resp = respectful_get(ARTICLE_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith(".pdf"):
            return a["href"] if a["href"].startswith("http") else "https://www.faimes.be" + a["href"]
    raise RuntimeError("Aucun lien PDF trouvé sur l'actualité brochure extrascolaire de Faimes")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" :“”\"")


_SECTION_HEADER_RE = re.compile(r"^STAGE D['E]")  # "STAGE D'AUTOMNE", "STAGE DE DETENTE"...


def _activites_from_week(dates: str, block_text: str) -> list[tuple[str, tuple[float, float]]]:
    """Retourne une liste de (titre, (age_min, age_max)) pour une semaine donnée."""
    # Le bloc capturé entre deux "Semaine du" inclut parfois le titre de
    # section suivant ("STAGE DE DETENTE"...) quand il n'y a pas de nouvelle
    # "Semaine du" juste après dans le texte source - filtré ici.
    lines = [l.strip() for l in block_text.split("\n") if l.strip() and not _SECTION_HEADER_RE.match(l.strip())]
    joined = " ".join(lines)

    unique_match = PETITS_GRANDS_UNIQUE_RE.search(joined)
    if unique_match:
        return [(_clean(unique_match.group(1)), AGE_TOUS)]

    result = []
    for line in lines:
        petits_match = PETITS_RE.search(line)
        grands_match = GRANDS_RE.search(line)
        if petits_match:
            result.append((_clean(petits_match.group(1)), AGE_PETITS))
        elif grands_match:
            result.append((_clean(grands_match.group(1)), AGE_GRANDS))
    if result:
        return result

    # Aucune mention petits/grands sur cette semaine (ex. "Le meilleur
    # pâtissier") - le thème vaut pour les deux tranches d'âge à la fois.
    return [(_clean(joined), AGE_TOUS)] if joined else []


def scrape() -> list[Activite]:
    pdf_url = _find_pdf_url()
    pdf_bytes = fetch_pdf_bytes(pdf_url)
    if not is_pdf(pdf_bytes):
        return []

    full_text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if "Semaine du" in page_text:
                full_text += page_text + "\n"

    activites: list[Activite] = []
    for j1, j2, mois, annee, block in WEEK_RE.findall(full_text):
        dates = f"du {j1} au {j2} {mois} {annee}"
        for titre, (age_min, age_max) in _activites_from_week(dates, block):
            if not titre:
                continue
            activites.append(
                Activite(
                    commune=COMMUNE,
                    nom_activite=titre,
                    type_activite=classify_type(titre),
                    dates=dates,
                    age_min=age_min,
                    age_max=age_max,
                    prix="70€ (5 jours) / 60€ (4 jours) pour les enfants de la commune ; 90€ / 80€ sinon",
                    lieu="Accueil extrascolaire Les Mains Colorées, Faimes",
                    modalites_inscription="Informations détaillées à suivre (voir brochure PDF)",
                    disponibilite="Non communiqué sur cette page",
                    lien_source=pdf_url,
                )
            )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"# {len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
