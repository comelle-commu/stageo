"""Scraper Meix-devant-Virton (Plone/iMio, province de Luxembourg) -
programme des vacances scolaires (petite commune de Gaume, ~2500 hab.).

Trouvé pendant le ratissage de la province de Luxembourg (31/08/2026).
Page structurée en DEUX parties bien distinctes, toutes deux nécessaires :
1. Un calendrier scolaire complet (Rentrée -> vacances d'été de l'année
   suivante) donnant les dates EXACTES de chaque congé ("Vacances
   d'automne (Toussaint) Du lundi 19 octobre 2026 au dimanche 1er
   novembre 2026"...).
2. Une liste "Ce qui est proposé aux enfants durant les vacances
   scolaires", organisée par congé ("Congé d'automne", "Vacances
   d'hiver"...), qui énumère les activités réelles (stage/plaine, âge,
   durée, lieu) SANS répéter les dates exactes - d'où le besoin de relier
   les deux parties par le nom du congé.

Seuls les 4 congés à date de FIN certaine sont repris (automne, hiver,
détente, printemps) - "Vacances d'été" n'a qu'une date de DÉBUT sur cette
page ("Les vacances d'été débutent le Samedi 3 juillet 2027"), pas de
date de fin exploitable, donc volontairement exclu plutôt que deviné.

Certaines activités sont explicitement marquées "En attente de
confirmation" par la commune elle-même (ex. le stage d'escrime en congé
de détente) - signalé tel quel dans `dates` plutôt qu'ignoré ou présenté
comme confirmé.

Légal : robots.txt iMio standard (signature confirmée, Crawl-delay 120),
page /gdpr-view lisible, aucun mot-clé anti-scraping trouvé.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, find_plone_content, respectful_get

URL = "https://www.meix-devant-virton.be/loisirs/enfance-et-jeunesse/vacances-scolaires"
COMMUNE = "Meix-devant-Virton"

# Label dans la section "Ce qui est proposé" -> label correspondant dans le
# calendrier scolaire en haut de page (formulation légèrement différente
# des deux côtés - vérifié à la main sur la page).
LABEL_TO_CALENDRIER = {
    "Congé d'automne": "Vacances d'automne (Toussaint)",
    "Vacances d'hiver": "Vacances d'hiver (Noël)",
    "Congé de détente": "Vacances de détente (Carnaval)",
    "Vacances de printemps": "Vacances de printemps (Pâques)",
}
ACTIVITES_LABELS = list(LABEL_TO_CALENDRIER) + ["Vacances d'été"]  # "été" gardé pour le split, exclu ensuite (voir docstring)

CALENDRIER_RE = re.compile(
    r"(Vacances d'automne \(Toussaint\)|Vacances d'hiver \(Noël\)|"
    r"Vacances de détente \(Carnaval\)|Vacances de printemps \(Pâques\))"
    r"\s*Du\s+lundi\s+(\d{1,2})\s+(\w+)\s+(\d{4})\s+au\s+dimanche\s+(\d{1,2})(?:\s*er)?\s+(\w+)\s+(\d{4})",
    re.I,
)
ACTIVITE_RE = re.compile(r"((?:Un|Une)\s+[^()]+?)\s*\(([^)]+)\)")
AGE_RANGE_RE = re.compile(r"(\d+(?:,\d+)?)\s*-\s*(\d+)\s*ans", re.I)
AGE_MIN_ONLY_RE = re.compile(r"(?:à partir de|dès)\s*(\d+(?:,\d+)?)\s*ans", re.I)


def _clean(txt: str) -> str:
    return re.sub(r"\s+", " ", txt).strip()


def _parse_calendrier(full_text: str) -> dict[str, str]:
    """label calendrier -> "du D mois AAAA au D mois AAAA" (dates exactes)."""
    dates: dict[str, str] = {}
    for m in CALENDRIER_RE.finditer(full_text):
        label, d1, mois1, an1, d2, mois2, an2 = m.groups()
        dates[label] = f"du {d1} {mois1} {an1} au {d2} {mois2} {an2}"
    return dates


def _parse_age(age_text: str) -> tuple[float | None, float | None]:
    m = AGE_RANGE_RE.search(age_text)
    if m:
        return float(m.group(1).replace(",", ".")), float(m.group(2))
    m = AGE_MIN_ONLY_RE.search(age_text)
    if m:
        return float(m.group(1).replace(",", ".")), None
    return None, None


_DECIMAL_COMMA_RE = re.compile(r"(\d),(\d)")


def _parse_details(details: str) -> tuple[str | None, str | None, str | None]:
    """"1 semaine, 2,5-12 ans, Meix-devant-Virton" -> (duree, age_text, lieu).
    Champs variables d'une activité à l'autre (pas toujours les 3) - on
    classe chaque partie séparée par une virgule selon son contenu plutôt
    que sur une position fixe. La virgule décimale ("2,5 ans") est protégée
    avant la découpe (sinon "2,5-12 ans" se scinde en deux morceaux "2" et
    "5-12 ans" - piège rencontré en pratique sur cette page)."""
    protected = _DECIMAL_COMMA_RE.sub(r"\1٫\2", details)
    duree = age_text = lieu = None
    for part in (p.strip().replace("٫", ",") for p in protected.split(",")):
        if "semaine" in part.lower():
            duree = part
        elif "ans" in part.lower():
            age_text = part
        elif part:
            lieu = f"{lieu}, {part}" if lieu else part
    return duree, age_text, lieu


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)
    full_text = _clean(main.get_text(" "))

    calendrier = _parse_calendrier(full_text)
    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    idx = full_text.find("Ce qui est proposé")
    section = full_text[idx:] if idx != -1 else ""

    split_pattern = "(" + "|".join(re.escape(l) for l in ACTIVITES_LABELS) + ")"
    parts = re.split(split_pattern, section)

    activites: list[Activite] = []
    for i in range(1, len(parts), 2):
        label = parts[i]
        if label not in LABEL_TO_CALENDRIER:
            continue  # "Vacances d'été" volontairement exclue (voir docstring)
        body = parts[i + 1] if i + 1 < len(parts) else ""
        dates_exactes = calendrier.get(LABEL_TO_CALENDRIER[label], "Dates non trouvées sur cette page")

        for m in ACTIVITE_RE.finditer(body):
            nom_brut, details = m.groups()
            nom = _clean(nom_brut)
            a_confirmer = "en attente de confirmation" in body[max(0, m.start() - 40):m.start()].lower()

            duree, age_text, lieu = _parse_details(details)
            age_min, age_max = _parse_age(age_text or "")

            dates = dates_exactes
            if duree:
                dates += f" ({duree})"
            if a_confirmer:
                dates += " - EN ATTENTE DE CONFIRMATION (source : commune)"

            activites.append(
                Activite(
                    commune=COMMUNE,
                    nom_activite=f"{nom} - {label}",
                    type_activite=classify_type(nom),
                    dates=dates,
                    age_min=age_min,
                    age_max=age_max,
                    prix="Non communiqué sur cette page",
                    lieu=lieu or COMMUNE,
                    modalites_inscription="Voir Service Accueil Temps Libre (lien source)",
                    disponibilite=disponibilite,
                    lien_source=URL,
                )
            )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités")
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
