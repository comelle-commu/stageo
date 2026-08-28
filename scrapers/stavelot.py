"""Scraper Stavelot (iMio) - Coordination Accueil Temps Libre, brochure PDF.

Contrairement à Herstal (PDF avec un vrai tableau propre), la brochure de
Stavelot est un flyer en mise en page libre à deux colonnes ("Qui/Où/Quand"
d'un côté, "Informations complémentaires" de l'autre) - pdfplumber.
extract_tables() ne renvoie que des fragments de cellules décoratives
inexploitables (icônes de police, bordures). L'extraction se fait donc sur
le TEXTE de chaque page individuellement (extract_text(), pas les tables),
avec un gabarit repéré empiriquement : une page "une activité" commence par
l'organisateur, puis "Du D au D <mois>", puis le nom de l'activité en
toutes lettres.

Piège rencontré : l'ordre de lecture du texte extrait entrelace les deux
colonnes visuelles (ex. "Qui :" et "Informations complémentaires :" se
suivent alors qu'ils sont côte à côte sur la page, pas l'un sous l'autre) -
le lieu précis en particulier est difficile à isoler proprement ; extraction
best-effort (ville seule, via "à <Ville>" après "Où :") plutôt qu'une
adresse complète.

Une page (44 dans ce run) contient DEUX activités fusionnées en colonnes
(deux organisateurs, deux titres, plusieurs dates) - plutôt que de risquer
d'associer les mauvais champs entre elles, seule la première activité de
cette page est extraite (perte assumée d'une ligne plutôt qu'une donnée
fausse - voir "pas besoin de perfection" dans la philosophie du projet).

Brochure couvrant septembre à décembre 2026 (Toussaint ET vacances de
Noël) - fichier renommé chaque trimestre par la commune, à re-vérifier
sur https://www.stavelot.be/actualites/coordination-accueil-temps-libre-...
si l'URL en dur ci-dessous renvoie un jour une 404.
"""
from __future__ import annotations

import io
import re

import pdfplumber
from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, fetch_pdf_bytes, is_pdf, respectful_get

PAGE_URL = "https://www.stavelot.be/actualites/coordination-accueil-temps-libre-septembre-decembre-2026-brochure-des-stages-animations"
COMMUNE = "Stavelot"
YEAR = 2026

DATE_RE = re.compile(r"Du\s+(\d{1,2})\s+au\s+(\d{1,2})\s+(\w+)", re.I)
AGE_RANGE_RE = re.compile(r"[Ee]nfants?\s+de\s+([\d,]+)\s*(?:à|-)\s*(\d{1,2})\s*ans")
AGE_MIN_ONLY_RE = re.compile(r"[Ee]nfants?\s+d[eè]s\s+(\d{1,2})\s*ans")
PRIX_RE = re.compile(r"(\d+)\s*€\s*\n?\s*Co[ûu]t\s*:", re.I)
# Sur les fiches à deux activités fusionnées (colonnes entrelacées), "à"
# peut parfois être suivi d'un mot-clé de la fiche voisine plutôt que d'un
# vrai nom de ville - "Où", "Qui" et "Quand" (les labels de colonne
# eux-mêmes) sont les faux positifs rencontrés en pratique, exclus ici.
VILLE_RE = re.compile(r"\bà\s+(?!(?:Où|Qui|Quand)\b)([A-ZÉÈÀ][\wÉÈÀéèàâêîôûäëïöü'-]+)")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _find_brochure_url() -> str:
    resp = respectful_get(PAGE_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith(".pdf"):
            return a["href"] if a["href"].startswith("http") else "https://www.stavelot.be" + a["href"]
    raise RuntimeError("Aucun lien PDF trouvé sur la page brochure Stavelot")


def _parse_activity_page(text: str) -> Activite | None:
    date_match = DATE_RE.search(text)
    if not date_match:
        return None

    organisateur_raw = text[: date_match.start()]
    # Dédoublonne les lignes consécutives identiques (répétitions vues dans
    # la source, ex. "Accueil extrascolaire" cité deux fois de suite).
    lines = [l.strip() for l in organisateur_raw.split("\n") if l.strip()]
    dedup_lines = [l for i, l in enumerate(lines) if i == 0 or l != lines[i - 1]]
    organisateur = _clean(" ".join(dedup_lines))[:120] or "Non précisé"

    # Piège : text[date_match.end():] commence par le saut de ligne qui suit
    # "...octobre" - un .split("\n", 1)[0] sans strip() préalable renvoyait
    # une chaîne vide (avant ce premier \n) au lieu du titre réel. Autre
    # piège : certaines fiches ont un qualificatif ("MIDI") ou une deuxième
    # période ("ET du 26 au 30 octobre") sur la ligne juste après la date -
    # on saute ces lignes-là pour tomber sur le vrai titre.
    _SKIP_LINE_RE = re.compile(r"^(MIDI|ET\s+du\s+\d|Du\s+\d)", re.I)
    after_date_lines = [l.strip() for l in text[date_match.end():].split("\n") if l.strip()]
    title_lines = [l for l in after_date_lines if not _SKIP_LINE_RE.match(l)]
    nom_activite = _clean(title_lines[0]) if title_lines else "Activité (nom non extrait)"

    age_match = AGE_RANGE_RE.search(text)
    age_min_only_match = AGE_MIN_ONLY_RE.search(text)
    if age_match:
        age_min = float(age_match.group(1).replace(",", "."))
        age_max = float(age_match.group(2))
    elif age_min_only_match:
        age_min = float(age_min_only_match.group(1))
        age_max = None
    else:
        age_min = age_max = None

    prix_match = PRIX_RE.search(text)
    prix = f"{prix_match.group(1)}€" if prix_match else "Non extrait automatiquement"

    # Le nom du lieu précis (avant "Où :") est trop entrelacé avec la
    # colonne "Informations complémentaires" voisine pour être isolé de
    # façon fiable (essayé et abandonné - voir docstring) : on se contente
    # de la ville, systématiquement présente sous la forme "à <Ville>".
    ville_match = VILLE_RE.search(text)
    lieu = ville_match.group(1) if ville_match else "Stavelot (voir brochure)"

    disponibilite = extract_disponibilite(text) or "Non communiqué sur cette page"

    return Activite(
        commune=COMMUNE,
        organisateur=organisateur,
        nom_activite=nom_activite,
        type_activite=classify_type(nom_activite, organisateur),
        dates=f"du {date_match.group(1)} au {date_match.group(2)} {date_match.group(3)} {YEAR}",
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu=lieu,
        modalites_inscription="Voir la brochure PDF (lien source)",
        disponibilite=disponibilite,
        lien_source=PAGE_URL,
    )


def scrape() -> list[Activite]:
    brochure_url = _find_brochure_url()
    pdf_bytes = fetch_pdf_bytes(brochure_url)
    if not is_pdf(pdf_bytes):
        return []

    activites: list[Activite] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if not DATE_RE.search(text[:200]):
                continue  # page d'index/sommaire/couverture, pas une fiche activité
            activite = _parse_activity_page(text)
            if activite:
                activites.append(activite)

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"# {len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
