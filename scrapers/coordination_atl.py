"""Scraper coordination-atl.be (plateforme "Coordination ATL", regroupe
plusieurs communes de Namur et du Brabant wallon sur un seul site WordPress
- une page par commune, `/en-vacances-<slug>/`).

robots.txt standard WordPress, `Disallow: /wp-admin/` uniquement -> crawl
générique autorisé. Chaque page de commune contient (quand elle est
publiée) un tableau TablePress en HTML statique, mais les colonnes varient
légèrement d'une commune à l'autre (ex. "Lieu" chez Wavre, "Prix" chez
Fernelmont, "Lieu d'animation" chez Ohey) - le mapping de colonnes se fait
donc par mot-clé sur l'en-tête plutôt que par position fixe. Certaines
communes du réseau (Dinant, Incourt, Gesves au 26/08/2026) n'ont pas encore
de tableau publié pour la période en cours : on les scrape quand même à
chaque run (sans erreur), au cas où le tableau apparaîtrait plus tard dans
la saison.

Les dates ne sont PAS toujours accompagnées d'une année dans le tableau
source ("06-10/07", "du 06 au 10 juillet") - on suppose l'année en cours
(date.today().year), comme le fait la commune elle-même en n'affichant que
la période active. Pas d'année à supposer différemment sans information
supplémentaire de la source.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, respectful_get

BASE_URL = "https://www.coordination-atl.be"

# (nom de commune, slug utilisé dans l'URL /en-vacances-<slug>/) - "Gesves"
# suit un schéma différent ("en-vacances-a-gesves") des cinq autres.
COMMUNES = [
    ("Dinant", "dinant"),
    ("Fernelmont", "fernelmont"),
    ("Gesves", "a-gesves"),
    ("Incourt", "incourt"),
    ("Ohey", "ohey"),
    ("Wavre", "wavre"),
]

_AGE_RE = re.compile(r"(\d{1,2}(?:[.,]\d+)?)\s*(?:-|à|a)\s*(\d{1,2}(?:[.,]\d+)?)\s*ans?", re.I)

# Mots-clés (sans accents, minuscules) cherchés dans le texte de chaque
# <th> pour retrouver la bonne colonne quel que soit son libellé exact.
_HEADER_KEYWORDS = {
    "dates": "dates",
    "age": "ages",
    "anim": "animation",
    "organisat": "organisateur",
    "lieu": "lieu",
    "prix": "prix",
    "info": "infos",
}


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _header_map(header_row) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, th in enumerate(header_row.find_all(["th", "td"])):
        label = _strip_accents(th.get_text(" ", strip=True).lower())
        for kw, key in _HEADER_KEYWORDS.items():
            if kw in label and key not in mapping:
                mapping[key] = idx
    return mapping


def _cell_text(cells, idx: Optional[int]) -> str:
    if idx is None or idx >= len(cells):
        return ""
    return cells[idx].get_text(", ", strip=True)


def _organisateur_text(cells, idx: Optional[int]) -> str:
    """Comme _cell_text(), mais ignore les <a> imbriqués (souvent juste le
    site web de l'organisateur en doublon du nom déjà présent en texte,
    ex. "Ocarina<br/><a>ocarina.be</a>" chez Fernelmont - inutile de le
    répéter dans le nom de l'activité)."""
    if idx is None or idx >= len(cells):
        return ""
    cell = cells[idx]
    parts = [str(node).strip() for node in cell.find_all(string=True, recursive=True) if node.find_parent("a") is None]
    return re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()


def _with_year(dates_text: str, year: int) -> str:
    """Ajoute l'année en cours seulement si la source n'en a pas déjà mis
    une elle-même (vu chez Ohey : "du 06 au 10 juillet 2026")."""
    if not dates_text:
        return f"Non précisées ({year})"
    if re.search(r"\b20\d{2}\b", dates_text):
        return dates_text
    return f"{dates_text} {year}"


def _scrape_commune(commune: str, slug: str) -> list[Activite]:
    url = f"{BASE_URL}/en-vacances-{slug}/"
    resp = respectful_get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", class_=re.compile(r"\btablepress\b"))
    if table is None:
        return []

    header_row = table.find("thead")
    header_row = header_row.find("tr") if header_row else table.find("tr")
    if header_row is None:
        return []
    cols = _header_map(header_row)

    body = table.find("tbody") or table
    activites: list[Activite] = []
    year = date.today().year

    for row in body.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        dates_text = _cell_text(cells, cols.get("dates"))
        ages_text = _cell_text(cells, cols.get("ages"))
        animation_text = _cell_text(cells, cols.get("animation"))
        organisateur_text = _organisateur_text(cells, cols.get("organisateur"))
        lieu_text = _cell_text(cells, cols.get("lieu"))
        prix_text = _cell_text(cells, cols.get("prix"))
        infos_text = _cell_text(cells, cols.get("infos"))

        if not animation_text and not dates_text:
            continue

        nom_activite = animation_text or "Stage"
        if organisateur_text:
            nom_activite = f"{nom_activite} — {organisateur_text}"

        age_min, age_max = None, None
        m = _AGE_RE.search(ages_text)
        if m:
            age_min, age_max = float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))

        lien = None
        infos_cell_idx = cols.get("infos")
        if infos_cell_idx is not None and infos_cell_idx < len(cells):
            a = cells[infos_cell_idx].find("a", href=True)
            if a:
                lien = a["href"]
        lien_source = lien or url

        full_text = " ".join([dates_text, animation_text, infos_text])
        disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

        activites.append(
            Activite(
                commune=commune,
                nom_activite=nom_activite,
                type_activite=classify_type(nom_activite),
                dates=_with_year(dates_text, year),
                age_min=age_min,
                age_max=age_max,
                prix=prix_text or "Non communiqué sur cette page",
                lieu=lieu_text or "Voir infos",
                modalites_inscription=infos_text or "Voir lien source pour les inscriptions",
                disponibilite=disponibilite,
                lien_source=lien_source,
            )
        )

    return activites


def scrape() -> list[Activite]:
    activites: list[Activite] = []
    for commune, slug in COMMUNES:
        try:
            activites.extend(_scrape_commune(commune, slug))
        except Exception as exc:  # noqa: BLE001 - une commune en panne ne doit pas bloquer les autres
            print(f"  [coordination-atl] {commune} ignorée (erreur : {exc})")
    return activites


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} activités extraites")
    for a in results[:10]:
        print(a)
