"""Scraper Le CFS asbl (organisme privé de stages, Brabant wallon/Bruxelles/
Liège) - trouvé en creusant `lecfs.be` (déjà repéré comme piste non vérifiée
dans docs/paysage-organismes-2026-08-24.md). La page catalogue
(`/stages/activites/`) elle-même n'affiche qu'un intitulé/tranche d'âge/
région générique par carte (pas de date) - mais chaque carte ouvre un modal
dont le bouton "Inscription" pointe vers `www12.iclub.be/myiclub3_CFS_
register.asp?ClubID=559` : Le CFS utilise donc la MÊME plateforme MyiClub
que Sport Fun Activ'/Royal Léopold Club/RRC Bruxelles déjà intégrée via
`iclub.py` - mais sous une variante différente de l'UI (formulaire de
filtre + JS qui interroge une API JSON dédiée, plutôt que la page HTML
`register.asp?action=Search` directement exploitable en BeautifulSoup des
3 autres clubs). D'où un module séparé plutôt qu'une entrée `CLUBS` dans
`iclub.py`.

Endpoint réel identifié en lisant le JS de la page de filtre
(`requestFilters()`/`ajaxUpdate()` dans myiclub3_CFS_register.asp) :
`GET AjaxGetCFS.asp?Action=Resultat&ClubID=559&Categorie=4&Page=N` - JSON
public, sans cookie de session ni authentification (contrairement à
`myiclub3_CFS.asp`, le POST classique du formulaire, qui exige une session
déjà initialisée - piste abandonnée au profit de cette API JSON plus
simple, une fois trouvée). `Categorie=4` = "Vacances scolaires" (les autres
catégories du même club sont des cours à l'année/parascolaire, hors
périmètre). Pagination confirmée : 15 résultats/page, page vide = fin.

Chaque évènement peut être organisé sur PLUSIEURS implantations à la fois
(champs `DescriptionLieuN`/`TarifN`/`MaxPlaceN`/`GrN` numérotés 1 à 10, prix
et places parfois différents par lieu) - une Activite par (évènement, lieu)
comme pour Sport Fun Activ' dans iclub.py. Sur 349 évènements "Vacances
scolaires" au total (toutes régions confondues), seuls 3 lieux sont en
province de Liège (LIEUX_LIEGE ci-dessous) - les ~30 autres (Brabant wallon,
Bruxelles) sont hors périmètre de ce ratissage et volontairement exclus
plutôt que de les deviner/rattacher à une mauvaise commune.

Légal : robots.txt absent (404) sur www12.iclub.be, comme les autres
sous-domaines iClub déjà vérifiés (voir iclub.py) - aucune restriction
déclarée. robots.txt de lecfs.be (le site vitrine, pas la plateforme
d'inscription elle-même) lisible et ouvert (seuls quelques dossiers
techniques Jekyll interdits, rien sur `/stages/`) ; ses "Conditions
générales" (`/stages/conditions_generales/`) ne contiennent aucune clause
sur le scraping/l'extraction automatisée.
"""
from __future__ import annotations

import html
from datetime import date, datetime

from common import Activite, classify_type, respectful_get

API_BASE = "https://www12.iclub.be/AjaxGetCFS.asp"
CLUB_ID = 559
CATEGORIE_VACANCES = 4
ORGANISATEUR = "Le CFS"

# Nom exact du champ DescriptionLieuN (tel que renvoyé par l'API) -> commune
# officielle. Seuls les 3 lieux confirmés en province de Liège sur les 33
# lieux distincts observés au 31/08/2026 (les autres sont en Brabant wallon/
# Bruxelles/Namur, hors périmètre de ce ratissage - voir docstring).
LIEUX_LIEGE = {
    "AWANS - Hall Omnisports": "Awans",
    "VERLAINE - Hall Omnisports": "Verlaine",
    "HUY - Ecole d'Agriculture (Athénée Royal Agri SG)": "Huy",
}

MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def _parse_us_date(text: str) -> date | None:
    try:
        return datetime.strptime(text, "%m/%d/%Y").date()
    except (ValueError, TypeError):
        return None


def _format_dates(d1: date, d2: date) -> str:
    if d1.month == d2.month and d1.year == d2.year:
        return f"du {d1.day} au {d2.day} {MOIS_FR[d2.month]} {d2.year}"
    return f"du {d1.day} {MOIS_FR[d1.month]} {d1.year} au {d2.day} {MOIS_FR[d2.month]} {d2.year}"


def _fetch_page(page: int) -> list[dict]:
    url = f"{API_BASE}?Action=Resultat&ClubID={CLUB_ID}&Categorie={CATEGORIE_VACANCES}&Page={page}"
    resp = respectful_get(url)
    return resp.json()


def _disponibilite(max_place: int, actuel: int) -> str:
    # 999 observé systématiquement comme valeur "pas de plafond réel" sur les
    # évènements testés (voir docstring) - pas assez fiable pour être traité
    # comme une vraie capacité chiffrée.
    if not max_place or max_place >= 900:
        return "Non communiqué sur cette page"
    return "Complet" if actuel >= max_place else "Places disponibles"


def scrape() -> list[Activite]:
    today = date.today()
    activites: list[Activite] = []

    page = 1
    while True:
        items = _fetch_page(page)
        if not items:
            break
        for item in items:
            debut = _parse_us_date(item.get("DateDebut", ""))
            fin = _parse_us_date(item.get("DateFin", ""))
            if fin is not None and fin < today:
                continue  # periode passee - on prefere ignorer plutot que d'afficher du perime

            nom = html.unescape(item.get("Titre") or "").strip()
            if not nom:
                continue
            age_min = item.get("AgeDebut")
            age_max = item.get("AgeFin")
            evenement_id = item.get("EvenementID")

            for i in range(1, 11):
                lieu_desc = item.get(f"DescriptionLieu{i}")
                if lieu_desc not in LIEUX_LIEGE:
                    continue
                lieu_id = item.get(f"EvenementLieuID{i}")
                tarif = item.get("Tarif" if i == 1 else f"Tarif{i}")
                max_place = item.get(f"MaxPlace{i}") or 0
                gr = item.get(f"Gr{i}") or 0

                lien = (
                    f"https://www12.iclub.be/register.asp?action=dispatch&ClubID={CLUB_ID}"
                    f"&EvenementID={evenement_id}&EvenementLieuID={lieu_id}"
                )
                activites.append(
                    Activite(
                        commune=LIEUX_LIEGE[lieu_desc],
                        organisateur=ORGANISATEUR,
                        nom_activite=nom,
                        type_activite=classify_type(nom, ORGANISATEUR),
                        dates=_format_dates(debut, fin) if debut and fin else "Non communiqué sur cette page",
                        age_min=float(age_min) if age_min is not None else None,
                        age_max=float(age_max) if age_max is not None else None,
                        prix=f"{tarif}€" if tarif else "Non communiqué sur cette page",
                        lieu=lieu_desc,
                        modalites_inscription=f"Inscription en ligne via la plateforme MyiClub du CFS : {lien}",
                        disponibilite=_disponibilite(max_place, gr),
                        lien_source=lien,
                    )
                )

        page += 1

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
