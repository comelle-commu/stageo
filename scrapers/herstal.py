"""Scraper Herstal (Plone/iMio) - Stages (renvoie vers un PDF pour le programme).

La page HTML elle-même ne contient aucune donnée d'activité (confirmé lors
de l'investigation d'élargissement) - elle liste des documents PDF
téléchargeables. Le PDF "Stages congé été [année].pdf" est un vrai PDF texte
(pas un scan) contenant un tableau bien structuré : une ligne d'en-tête "Du
X au Y [mois]" par semaine, suivie d'une ligne par stage (âge, thème,
organisme, contact, lieu, horaire, prix, garderie). Extrait via
`common.extract_pdf_tables` (pdfplumber).

Piège rencontré sur ce PDF : un tableau peut continuer sur la page suivante
sans répéter sa ligne d'en-tête de semaine - il faut donc traiter toutes les
lignes de tous les tableaux comme un flux continu, sans réinitialiser la
semaine en cours à chaque nouveau tableau/page.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_pdf_tables, fetch_pdf_bytes, find_plone_content, is_pdf, respectful_get

PAGE_URL = "https://www.herstal.be/vivre-a-herstal/stages"
COMMUNE = "Herstal"

AGE_RE = re.compile(r"([\d,]+)\s*-\s*([\d,]+)\s*ans", re.I)
WEEK_HEADER_RE = re.compile(r"^Du\s+\d", re.I)


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def _clean(cell) -> str:
    return re.sub(r"\s+", " ", (cell or "")).strip()


def _find_pdf_url() -> str:
    resp = respectful_get(PAGE_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)
    for a in main.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if "stage" in text.lower() and "conge" in a["href"].lower().replace("é", "e"):
            return a["href"] if a["href"].startswith("http") else f"https://www.herstal.be{a['href']}"
    # repli : premier lien .pdf contenant "stage" dans le texte
    for a in main.find_all("a", href=True):
        if ".pdf" in a["href"].lower() and "stage" in a.get_text(" ", strip=True).lower():
            return a["href"] if a["href"].startswith("http") else f"https://www.herstal.be{a['href']}"
    raise RuntimeError("Aucun lien PDF de stages trouvé sur la page Herstal")


def scrape() -> list[Activite]:
    pdf_url = _find_pdf_url()
    pdf_bytes = fetch_pdf_bytes(pdf_url)
    if not is_pdf(pdf_bytes):
        raise RuntimeError(f"{pdf_url} ne sert pas un vrai PDF (voir common.fetch_pdf_bytes)")

    tables = extract_pdf_tables(pdf_bytes)
    year_match = re.search(r"(20\d{2})", pdf_url)
    year = year_match.group(1) if year_match else ""

    activites: list[Activite] = []
    current_week: str | None = None

    for table in tables:
        for row in table:
            cells = [_clean(c) for c in row]
            if not any(cells):
                continue

            if cells[0] and WEEK_HEADER_RE.match(cells[0]):
                current_week = f"{cells[0]} {year}".strip()
                continue

            if cells[1].lower() == "age":  # ligne d'en-tête de colonnes
                continue

            age_match = AGE_RE.search(cells[1]) if len(cells) > 1 else None
            if not age_match or not current_week:
                continue  # ligne qu'on ne sait pas interpréter - on ne devine pas

            age_min, age_max = (_to_float(x) for x in age_match.groups())
            theme = cells[2] if len(cells) > 2 else ""
            organisme = cells[3] if len(cells) > 3 else ""
            contact = cells[4] if len(cells) > 4 else ""
            lieu = cells[5] if len(cells) > 5 else "Non précisé"
            horaire = cells[6] if len(cells) > 6 else ""
            prix = cells[7] if len(cells) > 7 else "Non précisé"
            garderie = cells[8] if len(cells) > 8 else ""
            site = cells[9] if len(cells) > 9 else ""

            modalites = f"Inscription directement auprès de l'organisme ({organisme})"
            if contact:
                modalites += f" - {contact}"
            if site:
                modalites += f" - {site}"
            if horaire:
                modalites += f" - horaire : {horaire}"
            if garderie:
                modalites += f" - garderie : {garderie}"

            activites.append(
                Activite(
                    commune=COMMUNE,
                    nom_activite=f"{theme} ({organisme})" if organisme else theme,
                    type_activite=classify_type(theme),
                    dates=current_week,
                    age_min=age_min,
                    age_max=age_max,
                    prix=prix or "Non précisé",
                    lieu=lieu,
                    modalites_inscription=modalites,
                    disponibilite="Non communiqué sur ce PDF",
                    lien_source=pdf_url,
                )
            )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
