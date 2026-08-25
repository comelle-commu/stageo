"""Scraper iClub (plateforme MyiClub, ASP classique) - clubs sportifs privés
qui publient leurs stages sur cette plateforme mutualisée.

Contrairement à iMio (un seul domaine par commune, mais robots.txt/structure
identiques), chaque club iClub a sa PROPRE combinaison (sous-domaine,
ClubID) - pas d'annuaire public trouvé pour les découvrir automatiquement
(voir docs/paysage-organismes-2026-08-24.md). On les ajoute donc un par un
dans CLUBS au fur et à mesure qu'on les identifie (même logique que
l'onboarding commune par commune), mais la structure HTML de la page de
résultats elle-même est identique d'un club à l'autre une fois l'URL connue
- un seul parseur pour tous.

Légal : robots.txt absent (404) sur les sous-domaines testés -> aucune
restriction déclarée. Pas de CGU publique trouvée en ligne pour le Royal
Léopold Club (conditions transmises sur demande au secrétariat, rien sur le
réemploi/scraping). Pas de Crawl-delay déclaré -> DEFAULT_MIN_DELAY.

Page sans charset déclaré dans le Content-Type -> mojibake sur les accents
si on ne corrige pas l'encodage (même piège que Neupré) ; déjà géré par
common.respectful_get() (apparent_encoding).
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

# (nom_affiche, commune, sous-domaine, ClubID) - clubs confirmés (page de
# stages non vide, structure vérifiée) pour l'instant ; à compléter au fur
# et à mesure (voir docstring). ClubID n'est PAS le même identifiant d'un
# sous-domaine à l'autre (testé : ClubID=51/53 sur www2.iclub.be, et
# ClubID=203/572 sur www6/www4, ne renvoient actuellement aucun stage -
# soit d'autres clubs sans stage ouvert en ce moment, soit un souci de
# paramètres non investigué - à re-tester plus tard plutôt que deviner).
CLUBS = [
    {"nom": "Royal Léopold Club", "commune": "Uccle", "subdomain": "www2", "club_id": 10},
    {"nom": "Royal Racing Club de Bruxelles", "commune": "Uccle", "subdomain": "www", "club_id": 27},
]

DATE_RANGE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})")
AGE_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*an")


def _base_url(subdomain: str) -> str:
    return f"https://{subdomain}.iclub.be/"


def _parse_dates(text: str) -> str:
    m = DATE_RANGE_RE.search(text)
    if not m:
        return text.strip() or "Non précisées"
    return f"du {m.group(1)} au {m.group(2)}"


def _parse_age(text: str) -> tuple[float | None, float | None]:
    m = AGE_RE.search(text)
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))


def _parse_card(card, club: dict, base_url: str) -> Activite | None:
    title = card.select_one(".TitreFormule")
    if title is None:
        return None
    nom = title.get_text(strip=True)

    periode_text = card.select_one(".periode-formule")
    dates = _parse_dates(periode_text.get_text(" ", strip=True) if periode_text else "")

    age_text = card.select_one(".age-formule")
    age_min, age_max = _parse_age(age_text.get_text(" ", strip=True) if age_text else "")

    prix_el = card.select_one(".prix-formule")
    prix = prix_el.get_text(" ", strip=True) if prix_el else "Non communiqué sur cette page"

    complet = card.select_one(".text-danger") is not None
    disponibilite = "Complet" if complet else "Places disponibles"

    href = card.get("href", "")
    lien_source = urljoin(base_url, href)

    return Activite(
        commune=club["commune"],
        organisateur=club["nom"],
        nom_activite=nom,
        type_activite=classify_type(nom, club["nom"]),
        dates=dates,
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu=club["nom"],
        modalites_inscription=f"Inscription en ligne via la plateforme MyiClub du {club['nom']}",
        disponibilite=disponibilite,
        lien_source=lien_source,
    )


def _scrape_club(club: dict) -> list[Activite]:
    base_url = _base_url(club["subdomain"])
    url = (
        f"{base_url}register.asp?ClubID={club['club_id']}"
        "&action=Search&CategorieEvenement=Stages&LG=FR"
    )
    resp = respectful_get(url)
    soup = BeautifulSoup(resp.text, "lxml")

    activites = []
    for card in soup.select('a.pull-left[href*="action=details"]'):
        a = _parse_card(card, club, base_url)
        if a is not None:
            activites.append(a)
    return activites


def scrape() -> list[Activite]:
    activites: list[Activite] = []
    for club in CLUBS:
        activites.extend(_scrape_club(club))
    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités", flush=True)
    for a in result[:3]:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
