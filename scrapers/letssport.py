"""Scraper Let's Sport (organisme privé, stages sportifs/thématiques - ~15
sites en province de Liège et Luxembourg).

HTML statique et bien structuré (classes CSS explicites : `.activite-titre`
= plage de dates, `.activite-date` = thème + âge + lieu, `.activite-button`
= liens détails/inscription) - un parseur structurel par site, mais un
seul site suffit (`stages/stages-<slug>.html`), listés en dur ci-dessous
(extraits une fois depuis la page hub `stages.html`).

Le prix n'est PAS sur la page de liste, seulement sur chaque page
"détails" individuelle (une par activité) - non récupéré ici pour
limiter le nombre de requêtes (potentiellement des dizaines par site) ;
`lien_source` pointe directement vers la page détails de l'activité pour
que le prix reste à un clic.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, respectful_get

BASE_URL = "https://www.letssport.be"
ORGANISATEUR = "Let's Sport"

SITES = {
    "Ans": "ans",
    "Braives": "braives",
    "Engis": "engis",
    "Grace-Hollogne": "grace-hollogne",
    "Heron": "heron",
    "Herve": "herve",
    "Huy": "huy",
    "Liege": "liege",
    "Marche-en-Famenne": "marche-en-famenne",
    "Marchin": "marchin",
    "Nandrin": "nandrin",
    "Saint-Georges-sur-Meuse": "saint-georges-sur-meuse",
    "Seraing": "seraing",
    "Verviers": "verviers",
    "Waremme": "waremme",
}

DATES_RE = re.compile(r"Du\s+(\d{1,2}\s+\w+\s+\d{4})\s+au\s+(\d{1,2}\s+\w+\s+\d{4})", re.I)
THEME_AGE_RE = re.compile(r"^(.+?)\s*\(([\d,]+)\s*-\s*([\d,]+)\s*ans\)\s*$", re.I)


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", txt).strip()


def _scrape_site(commune: str, slug: str) -> list[Activite]:
    url = f"{BASE_URL}/stages/stages-{slug}.html"
    resp = respectful_get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    content = soup.find("div", class_="activite-content")
    if content is None:
        return []

    activites: list[Activite] = []
    dates_courantes = "Non extrait automatiquement"
    for p in content.find_all("p", recursive=False):
        classes = p.get("class") or []
        if "activite-titre" in classes:
            m = DATES_RE.search(_clean(p.get_text(" ")))
            if m:
                dates_courantes = f"Du {m.group(1)} au {m.group(2)}"
        elif "activite-date" in classes:
            b = p.find("b")
            titre_age = _clean(b.get_text(" ")) if b else ""
            m = THEME_AGE_RE.match(titre_age)
            theme, age_min, age_max = (m.group(1), m.group(2), m.group(3)) if m else (titre_age, None, None)
            spans = p.find_all("span")
            lieu = _clean(spans[0].get_text(" ")) if spans else "Non précisé"
            disponibilite = extract_disponibilite(_clean(p.get_text(" "))) or "Non communiqué sur cette page"

            lien = url
            bouton = p.find_next_sibling("p", class_="activite-button")
            if bouton:
                a = bouton.find("a")
                if a and a.get("href"):
                    lien = f"{BASE_URL}/{a['href'].lstrip('/')}"

            nom_activite = f"{theme} - Let's Sport {commune}"
            activites.append(
                Activite(
                    commune=commune,
                    organisateur=ORGANISATEUR,
                    nom_activite=nom_activite,
                    type_activite=classify_type(theme, ORGANISATEUR),
                    dates=dates_courantes,
                    age_min=float(age_min.replace(",", ".")) if age_min else None,
                    age_max=float(age_max.replace(",", ".")) if age_max else None,
                    prix="Non communiqué sur cette page (voir lien source pour le détail)",
                    lieu=lieu,
                    modalites_inscription="Inscription en ligne jusqu'au jeudi précédant le stage (voir lien source)",
                    disponibilite=disponibilite,
                    lien_source=lien,
                )
            )

    return activites


def scrape() -> list[Activite]:
    # Un site sur 15 tombant en erreur (timeout, reset réseau ponctuel) ne
    # doit pas faire perdre les 14 autres - contrairement aux autres
    # scrapers (une seule page chacun), celui-ci fait plusieurs requêtes
    # indépendantes et gagne à isoler les erreurs par site.
    activites: list[Activite] = []
    for commune, slug in SITES.items():
        try:
            activites.extend(_scrape_site(commune, slug))
        except Exception as exc:  # noqa: BLE001
            print(f"  [Let's Sport] {commune} ignoré (erreur : {exc})")
    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
