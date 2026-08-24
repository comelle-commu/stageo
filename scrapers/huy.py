"""Scraper Huy (Plone/iMio) - page "hub" qui renvoie vers des sous-pages par
période de vacances plutôt que d'afficher le programme directement.

Parcours réel (différent de l'hypothèse de départ "hub -> beaucoup de
sous-pages d'activités") : la page d'accueil ATL de Huy pointe vers une page
"Les stages" (elle-même un hub par période : Détente, Printemps, Été,
Automne, Hiver), qui pointe à son tour vers une sous-page par période
listant plusieurs organisateurs (commune + associations/asbl). Le contenu
communal officiel ("Le Repaire des P'tits Loups" pour l'été, "Toboggan" pour
les autres périodes) est facilement identifiable par son en-tête en
majuscules ; les nombreuses offres associatives qui suivent (clubs sportifs,
asbl...) ont un format trop hétérogène pour être extraites de façon fiable
cette session - seul le programme communal est extrait ici (comme pour les
autres communes), le reste de l'annuaire associatif reste consultable
manuellement via `lien_source`.

Portée volontairement limitée cette session à la page "Congé d'été"
(période actuellement pertinente) - étendre aux 4 autres pages de période
est mécanique (même code, seule l'URL et le nom du programme officiel
changent) mais coûte 120s de Crawl-delay iMio par page supplémentaire.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, find_plone_content, respectful_get

STAGES_HUB_URL = "https://www.huy.be/vivre-a/jeunesse/les-stages/accueil"
COMMUNE = "Huy"

MOIS = "janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _find_ete_url() -> str:
    resp = respectful_get(STAGES_HUB_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)
    # "ete" en sous-chaîne matcherait aussi "...d-ete-nte..." (Carnaval/
    # Détente) - on exige le texte exact "d'été" plutôt qu'une sous-chaîne
    # de l'URL (bug rencontré et corrigé : le lien Détente était choisi en
    # premier car son URL contient "detente" -> "ete").
    for a in main.find_all("a", href=True):
        if "d'été" in a.get_text(" ", strip=True).lower():
            return a["href"]
    raise RuntimeError("Lien 'Stages - Congé d'été' introuvable sur le hub Huy")


def scrape() -> list[Activite]:
    ete_url = _find_ete_url()
    resp = respectful_get(ete_url)
    soup = BeautifulSoup(resp.text, "lxml")
    main = find_plone_content(soup)
    text = _clean(main.get_text())

    # Bloc borné par le prochain organisateur de la page ("LA MAISON DE
    # L'ENFANT") - une frontière générique (ex. prochaine séquence en
    # majuscules) s'est révélée peu fiable : "PLAINE COMMUNALE" entre
    # parenthèses juste après le titre est lui-même tout en majuscules et
    # coupait le bloc immédiatement.
    m = re.search(r"LE REPAIRE DES P.TITS LOUPS.*?(?=LA MAISON DE L)", text, re.S)
    if not m:
        raise RuntimeError("Bloc 'Le Repaire des P'tits Loups' introuvable - la page a peut-être changé")
    block = m.group(0)

    dates_m = re.search(
        rf"Du\s+(\d{{1,2}}\s+(?:{MOIS}))\s+au\s+(\d{{1,2}}\s+(?:{MOIS}))", block, re.I
    )
    dates = f"du {dates_m.group(1)} au {dates_m.group(2)} 2026" if dates_m else "Non extrait automatiquement"

    age_m = re.search(r"Enfants de\s*([\d,]+)\s*à\s*([\d,]+)\s*ans", block)
    age_min, age_max = (
        (float(x.replace(",", ".")) for x in age_m.groups()) if age_m else (None, None)
    )
    if age_m:
        age_min, age_max = (float(x.replace(",", ".")) for x in age_m.groups())

    prix_m = re.search(r"Co[uû]t\s*:\s*(.+?)(?:\*|\.(?:\s|$))", block)
    prix = prix_m.group(1).strip() if prix_m else "Non extrait automatiquement"

    lieu_m = re.search(r"Dans les locaux de\s*(.+?)\.", block)
    lieu = lieu_m.group(1).strip() if lieu_m else "Non extrait automatiquement"

    insc_m = re.search(r"Inscriptions? via\s*:\s*(\S+?)(?=Infos|$)", block)
    infos_m = re.search(r"Infos\s*:\s*(.+)$", block)
    modalites = "Capacité limitée - inscription en ligne"
    if insc_m:
        modalites += f" : {insc_m.group(1)}"
    if infos_m:
        modalites += f" - {infos_m.group(1).strip()}"

    activite = Activite(
        commune=COMMUNE,
        nom_activite="Le Repaire des P'tits Loups (plaine communale)",
        dates=dates,
        age_min=age_min,
        age_max=age_max,
        prix=prix,
        lieu=lieu,
        modalites_inscription=modalites,
        disponibilite="Non communiqué sur cette page",
        lien_source=ete_url,
    )
    return [activite]


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
