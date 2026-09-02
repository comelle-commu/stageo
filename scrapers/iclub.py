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
#
# "lieux" (optionnel) : certains clubs (ex. Sport Fun Activ') organisent
# leurs stages sur plusieurs implantations physiques, dans des communes
# différentes, listées dans le texte de la période elle-même ("Toussaint 26
# Dolembreux Semaine 1") plutôt que sur des pages séparées. Quand ce dict
# est présent, on l'utilise pour retrouver la vraie commune de chaque
# activité au lieu du "commune" par défaut du club.
CLUBS = [
    {"nom": "Royal Léopold Club", "commune": "Uccle", "subdomain": "www2", "club_id": 10},
    {"nom": "Royal Racing Club de Bruxelles", "commune": "Uccle", "subdomain": "www", "club_id": 27},
    {
        "nom": "Sport Fun Activ'",
        "commune": "Sprimont",
        "subdomain": "www7",
        "club_id": 712,
        "lieux": {
            "Dolembreux": "Sprimont",
            "Fraipont": "Trooz",
            "Seraing": "Seraing",
            "Esneux": "Esneux",
        },
    },
    # Piscine privée (ratissage piscines, 02/09/2026) - stages natation sur
    # deux bassins (Mini-Bassin + piscine Calypso), Av. Léopold Wiener 60,
    # Watermael-Boitsfort. robots.txt absent (404) sur www.iclub.be comme
    # sur les autres clubs de ce dossier - même statut légal déjà établi.
    {"nom": "Parc Sportif des 3 Tilleuls", "commune": "Watermael-Boitsfort", "subdomain": "www", "club_id": 28},
]

DATE_RANGE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})")
AGE_RE = re.compile(r"(\d+)\s*-\s*(\d+)\s*an")
# Format long observé chez Sport Fun Activ' : "2 an(s) et  4 mois - 4 an(s)
# et  0 mois" (les mois du club Léopold/Racing ne suivent pas ce format,
# donc pas de risque de régression sur eux).
AGE_MONTHS_RE = re.compile(
    r"(\d+)\s*an\(s\)(?:\s*et\s*(\d+)\s*mois)?\s*-\s*(\d+)\s*an\(s\)(?:\s*et\s*(\d+)\s*mois)?"
)
LOCATION_RE = re.compile(r"\d{2}\s+([A-ZÉÈÀÂÊÎÔÛ][\wÉÈÀÂÊÎÔÛéèàâêîôûäëïöü'-]*)\s+Semaine")


def _base_url(subdomain: str) -> str:
    return f"https://{subdomain}.iclub.be/"


def _parse_dates(text: str) -> str:
    m = DATE_RANGE_RE.search(text)
    if not m:
        return text.strip() or "Non précisées"
    return f"du {m.group(1)} au {m.group(2)}"


def _parse_age(text: str) -> tuple[float | None, float | None]:
    m = AGE_MONTHS_RE.search(text)
    if m:
        age_min = float(m.group(1)) + (float(m.group(2)) / 12 if m.group(2) else 0)
        age_max = float(m.group(3)) + (float(m.group(4)) / 12 if m.group(4) else 0)
        return age_min, age_max
    m = AGE_RE.search(text)
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))


def _parse_location(text: str, lieux: dict) -> tuple[str | None, str | None]:
    """Retourne (commune, nom_implantation) si le texte de période mentionne
    une des implantations connues du club, sinon (None, None)."""
    m = LOCATION_RE.search(text)
    if not m:
        return None, None
    lieu = m.group(1)
    commune = lieux.get(lieu)
    return (commune, lieu) if commune else (None, None)


def _parse_card(card, club: dict, base_url: str) -> Activite | None:
    title = card.select_one(".TitreFormule")
    if title is None:
        return None
    nom = title.get_text(strip=True)

    periode_text = card.select_one(".periode-formule")
    periode_raw = periode_text.get_text(" ", strip=True) if periode_text else ""
    dates = _parse_dates(periode_raw)

    age_text = card.select_one(".age-formule")
    age_min, age_max = _parse_age(age_text.get_text(" ", strip=True) if age_text else "")

    prix_el = card.select_one(".prix-formule")
    prix = prix_el.get_text(" ", strip=True) if prix_el else "Non communiqué sur cette page"

    complet = card.select_one(".text-danger") is not None
    disponibilite = "Complet" if complet else "Places disponibles"

    href = card.get("href", "")
    lien_source = urljoin(base_url, href)

    commune, implantation = _parse_location(periode_raw, club.get("lieux", {}))
    if commune is None:
        commune = club["commune"]
    lieu = f"{club['nom']} - {implantation}" if implantation else club["nom"]

    return Activite(
        commune=commune,
        organisateur=club["nom"],
        nom_activite=nom,
        type_activite=classify_type(nom, club["nom"]),
        dates=dates,
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu=lieu,
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
