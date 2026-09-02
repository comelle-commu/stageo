"""Scraper Le Point d'Eau (La Louvière) - piscine privée, stages "natation +"
mêlant apprentissage de la natation le matin et une activité complémentaire
l'après-midi (athlétisme, multisports, padel/tennis, bibliothèque...).

Site WordPress (thème sur-mesure), robots.txt standard sans restriction
(Disallow limité à /wp-admin/). HTML statique, pas d'obstacle JS.

Piège rencontré : plusieurs cartes de stage contiennent un <p hidden> imbriqué
à l'intérieur du <h3> ou du <p> de description - contenu volontairement
masqué sur le site public (thème/activité "à définir", pas encore annoncé
officiellement), qui casse au passage la structure HTML (un <p> ne peut pas
être un enfant valide d'un <h3> ; BeautifulSoup ferme alors le <h3> plus tôt
que prévu). On retire explicitement tout élément portant l'attribut `hidden`
avant toute extraction de texte - à la fois pour ne publier que ce qu'un
visiteur voit réellement (même principe que common.check_legal(), qui ne
cherche que dans le texte VISIBLE d'une page), et pour que le titre extrait
reste propre malgré le balisage cassé.

Les stages dont le thème de l'après-midi n'est pas encore choisi ("Natation
et à définir", sans prix ni horaires visibles) sont explicitement exclus :
rien de réservable à afficher, cohérent avec la philosophie du dossier
(voir Ans/Forest/Uccle - on n'invente jamais une info absente).
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, respectful_get

URL = "https://www.pointdeau.be/stages/"
COMMUNE = "La Louviere"

MOIS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

TITLE_RE = re.compile(
    r"^(\d{1,2})\s*-\s*(\d{1,2})\s+([a-zéû]+)\s+(\d{4})\s*:\s*(.+)$", re.I
)
AGE_RE = re.compile(r"\(\s*(?:enfants?|adultes?)\s+de\s+(\d+)\s+à\s+(\d+)\s+ans?\s*\)", re.I)
# "Prix​​: 130€..." observé sur le site (espace(s) de largeur nulle entre
# "Prix" et le montant) - \s ne les reconnaît pas tous, donc on saute tout
# ce qui n'est ni chiffre ni "€" plutôt que de s'appuyer sur \s*.
PRICE_RE = re.compile(r"Prix[^\d€\n]*([\d,.]+\s*€[^\n]*)", re.I)
HORAIRES_RE = re.compile(r"Horaires?\s*:?\s*([^\n]+)", re.I)


def _strip_hidden(soup: BeautifulSoup) -> None:
    for el in soup.find_all(attrs={"hidden": True}):
        el.decompose()


def _parse_card(li) -> Activite | None:
    h3 = li.find("h3")
    if h3 is None:
        return None
    title_full = h3.get_text(" ", strip=True)
    if "à définir" in title_full.lower() or "a definir" in title_full.lower():
        return None

    m = TITLE_RE.match(title_full)
    if not m:
        return None
    d1, d2, mois_txt, annee, reste = m.groups()
    mois_num = MOIS.get(mois_txt.lower())
    if mois_num is None:
        return None

    age_match = AGE_RE.search(reste)
    age_min, age_max = (float(age_match.group(1)), float(age_match.group(2))) if age_match else (None, None)
    nom_partie = AGE_RE.sub("", reste).strip(" -–")
    nom = f"Le Point d'Eau - {nom_partie}"
    dates = f"du {int(d1):02d}/{mois_num:02d}/{annee} au {int(d2):02d}/{mois_num:02d}/{annee}"

    p = li.find("p")
    body = p.get_text("\n", strip=True) if p else ""

    price_match = PRICE_RE.search(body)
    prix = price_match.group(1).strip(" .;") if price_match else "Non communiqué sur cette page"

    horaires_match = HORAIRES_RE.search(body)
    horaires = f" ({horaires_match.group(1).strip()})" if horaires_match else ""

    link = li.select_one("a.lien-cart")
    href = link.get("href") if link else None
    lien_source = href or URL
    modalites = (
        f"Préinscription en ligne (formulaire) : {href}"
        if href
        else "Inscription pas encore ouverte - consulter la page stages du Point d'Eau"
    )

    return Activite(
        commune=COMMUNE,
        organisateur="Le Point d'Eau",
        nom_activite=nom,
        type_activite=classify_type(nom_partie),
        dates=dates + horaires,
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu="Le Point d'Eau, Rue Sylvain Guyaux 121, 7100 La Louvière",
        modalites_inscription=modalites,
        disponibilite="Non communiqué sur cette page",
        lien_source=lien_source,
    )


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    _strip_hidden(soup)

    container = soup.select_one(".divAquademy ul")
    if container is None:
        return []

    activites: list[Activite] = []
    for li in container.find_all("li", recursive=False):
        a = _parse_card(li)
        if a is not None:
            activites.append(a)
    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
