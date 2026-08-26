"""Scraper Dimension Sport (ASBL, stages sportifs pour enfants dans
plusieurs localités de la province de Liège : Battice, Heusy, Welkenraedt,
Herve, Tiège, Henri-Chapelle, Herbesthal, La Calamine, Liège...).

robots.txt introuvable (404) sur www.dimension-sport.be -> aucune
restriction déclarée, crawl générique autorisé par défaut. Page HTML
statique (pas de JS nécessaire), mais tableau assez dense : une page par
période de vacances (paramètre `mois`, qui désigne une période, pas un
mois calendaire réel), colonnes = semaines, lignes = lieux, chaque cellule
peut contenir plusieururs stages séparés par des <hr>, avec un balisage
HTML imbriqué et parfois mal fermé - d'où un parsing hybride (BeautifulSoup
pour la structure lignes/colonnes, regex sur le HTML brut de chaque
cellule pour les stages individuels, plus robuste ici que de suivre l'arbre
DOM noeud par noeud).

Le prix n'est PAS sur cette page (seulement sur la fiche détail
individuelle, `stages-detail.php?no=...`) - non récupéré ici pour limiter
le nombre de requêtes, même logique que letssport.py.
"""
from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

BASE_URL = "https://www.dimension-sport.be"
ORGANISATEUR = "Dimension Sport"

# Codes "mois" tels qu'utilisés par le site pour désigner chaque période de
# vacances (vus dans le menu "Stages" de chaque page) : Carnaval=2,
# Printemps 1re semaine=4, 2e semaine=5, Juillet=7, Août=8, Toussaint=11,
# Noël=12, Nouvel an (année suivante)=1.
MOIS_CODES = [2, 4, 5, 7, 8, 11, 12, 1]

# Un stage = un <a href="stages-detail.php?no=ID&mois=M&reserve=0|1">.
# reserve=1 -> COMPLET (nom barré) ; reserve=0 -> disponible. `&(?:amp;)?`
# car BeautifulSoup ré-échappe `&` en `&amp;` quand on ressérialise un tag
# avec str(td) - le HTML brut original n'a que `&`.
_STAGE_RE = re.compile(
    r'<a\s+href="stages-detail\.php\?no=(\d+)&(?:amp;)?mois=\d+&(?:amp;)?reserve=([01])"[^>]*>(.*?)</a>',
    re.S,
)
# Prend le DERNIER "X-Y ans" trouvé entre un stage et le suivant : certaines
# cellules répètent un sous-titre thématique ("Wally l'Apprenti Sorcier")
# avant l'âge réel, donc chercher le premier motif chiffré donnerait parfois
# un faux résultat si le sous-titre contenait lui-même un nombre.
_AGE_RE = re.compile(r"(\d{1,2}(?:[.,]\d+)?)\s*-\s*(\d{1,2}(?:[.,]\d+)?)\s*ans?", re.I)
_DATE_RANGE_RE = re.compile(r"(\d{2}/\d{2})\s*au\s*(\d{2}/\d{2})", re.S)
_NAV_YEAR_RE = re.compile(r'stages-dispo-lieu\.php\?mois=(\d+)"><span>[^<]*?(\d{4})</span>')


def _clean_name(name_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", name_html)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip(" \"'")


def _year_for_mois(page_html: str) -> dict[int, int]:
    """Le code `mois` ne dit pas l'année (ex. mois=1 = "Nouvel an 2027") -
    on la lit dans le menu de navigation, présent sur chaque page."""
    return {int(mois): int(year) for mois, year in _NAV_YEAR_RE.findall(page_html)}


def _disponibilite(reserve: str, tail_html: str) -> str:
    if reserve == "1":
        return "Complet (liste d'attente possible)"
    if "PLUS QUE QUELQUES PLACES" in tail_html.upper():
        return "Places limitées"
    return "Places disponibles"


def scrape() -> list[Activite]:
    activites: list[Activite] = []

    for mois in MOIS_CODES:
        url = f"{BASE_URL}/stages-dispo-lieu.php?mois={mois}"
        resp = respectful_get(url)
        year_map = _year_for_mois(resp.text)
        year = year_map.get(mois)

        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table", class_="pi-table")
        if table is None or table.find("thead") is None or table.find("tbody") is None:
            continue

        header_cells = table.find("thead").find_all("th")[1:]  # le premier th = "Lieu"
        column_dates: list[str | None] = []
        for th in header_cells:
            header_text = th.get_text(" ", strip=True)
            m = _DATE_RANGE_RE.search(header_text)
            if not m:
                column_dates.append(None)
                continue
            start, end = m.group(1), m.group(2)
            jours_note = " (3 jours)" if "3 jours" in header_text else ""
            column_dates.append(f"Du {start}/{year} au {end}/{year}{jours_note}" if year else f"Du {start} au {end}{jours_note}")

        for row in table.find("tbody").find_all("tr", recursive=False):
            cells = row.find_all("td", recursive=False)
            if not cells:
                continue
            lieu = cells[0].get_text(" ", strip=True)
            if not lieu:
                continue

            for idx, td in enumerate(cells[1:]):
                if idx >= len(column_dates) or column_dates[idx] is None:
                    continue
                dates = column_dates[idx]
                cell_html = str(td)

                matches = list(_STAGE_RE.finditer(cell_html))
                for i, m in enumerate(matches):
                    stage_id, reserve, name_html = m.groups()
                    tail_end = matches[i + 1].start() if i + 1 < len(matches) else len(cell_html)
                    tail_html = cell_html[m.end():tail_end]

                    nom_activite = _clean_name(name_html)
                    if not nom_activite:
                        continue

                    age_matches = _AGE_RE.findall(tail_html)
                    age_min, age_max = (None, None)
                    if age_matches:
                        a_min, a_max = age_matches[-1]
                        age_min, age_max = float(a_min.replace(",", ".")), float(a_max.replace(",", "."))

                    activites.append(
                        Activite(
                            commune=lieu,
                            organisateur=ORGANISATEUR,
                            nom_activite=nom_activite,
                            type_activite=classify_type(nom_activite, ORGANISATEUR),
                            dates=dates,
                            age_min=age_min,
                            age_max=age_max,
                            prix="Non communiqué sur cette page (voir lien source pour le détail)",
                            lieu=lieu,
                            modalites_inscription="Inscription en ligne (voir lien source) ; liste d'attente possible si complet.",
                            disponibilite=_disponibilite(reserve, tail_html),
                            lien_source=f"{BASE_URL}/stages-detail.php?no={stage_id}&mois={mois}&reserve={reserve}",
                        )
                    )

    return activites


if __name__ == "__main__":
    results = scrape()
    print(f"{len(results)} activités extraites")
    for a in results[:10]:
        print(a)
