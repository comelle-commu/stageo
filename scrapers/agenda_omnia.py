"""Widget agenda communal partagé ("Omnia", iMio) - plusieurs communes de la
province de Liège à la fois.

Découvert en creusant Geer pendant le ratissage de la province de Liège :
de nombreuses communes iMio embarquent, sur leur page d'accueil, un carrousel
d'actualités/agenda ("swiper") entièrement rendu côté serveur (pas de JS
nécessaire) - chaque élément porte sa propre catégorie ("Stages et cours",
"Fête et folklore", "Balade et découverte"...) et un type d'événement
("Activité" vs "Événementiel"). En filtrant sur category="Stages et cours"
ET event_type commençant par "Activité", on obtient un flux fiable
d'activités enfants, sans dépendre d'une page dédiée par commune (qui,
elle, n'est souvent pas encore publiée pour la période à venir - cf. Forest/
Uccle).

Piège rencontré et corrigé : le carrousel liste TOUTE l'actualité communale,
pas seulement les stages - un simple filtre sur la catégorie affichée
suffisait presque, mais certains items mal catégorisés (ex. Oupeye "Table de
conversation", Ferrières "Espace Public Numérique", tous deux tagués
"Stages et cours" par erreur ou par extension) se sont avérés être du type
"Événementiel" une fois la fiche détaillée consultée - d'où le double filtre.

Chaque lien détaillé nécessite de conserver le paramètre `?u=<uid>` de
l'URL d'origine (mécanisme Plone resolveuid) - sans lui, la page renvoie
une 404 malgré un slug d'URL a priori correct.

État au 27/08/2026 : sur ~19 communes testées disposant du widget, seule
Geer a des stages déjà publiés et correctement catégorisés (8). Les autres
communes de la liste sont conservées quand même (voir Forest/Uccle) : le
run hebdomadaire les réextraira automatiquement dès qu'elles publieront.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, extract_disponibilite, respectful_get

# (nom_commune, domaine) - communes iMio confirmées disposant du widget
# "swiper" en page d'accueil (vérifié le 27/08/2026). Communes iMio SANS ce
# widget (Ans, Herstal, Malmedy, Verlaine, Dalhem, Wanze, Faimes, Stavelot...)
# volontairement absentes d'ici - rien à en tirer par cette méthode.
COMMUNES = [
    ("Geer", "www.geer.be"),
    ("Ferrieres", "www.ferrieres.be"),
    ("Blegny", "www.blegny.be"),
    ("Trooz", "www.trooz.be"),
    ("Villers-le-Bouillet", "www.villers-le-bouillet.be"),
    ("Amay", "www.amay.be"),
    ("Dison", "www.dison.be"),
    ("Flemalle", "www.flemalle.be"),
    ("Juprelle", "www.juprelle.be"),
    ("Pepinster", "www.pepinster.be"),
    ("Remicourt", "www.remicourt.be"),
    ("Saint-Nicolas", "www.saint-nicolas.be"),
    ("Theux", "www.theux.be"),
    ("Thimister-Clermont", "www.thimister-clermont.be"),
    ("Wasseiges", "www.wasseiges.be"),
    ("Oupeye", "www.oupeye.be"),
    ("Hamoir", "www.hamoir.be"),
    ("Awans", "www.awans.be"),
]

DATE_RANGE_RE = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}\s*-\s*(\d{2}/\d{2}/\d{4})\s+\d{2}:\d{2}"
)
AGE_RE = re.compile(r"(?:à\s+partir\s+de\s*)?([\d,]+)\s*ans?(?:\s*(?:à|-)\s*(\d{1,2})\s*ans)?", re.I)
PRIX_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*€")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_between(text: str, start_marker: str, end_markers: list[str]) -> str:
    if start_marker not in text:
        return ""
    tail = text.split(start_marker, 1)[1]
    end_pos = len(tail)
    for marker in end_markers:
        idx = tail.find(marker)
        if idx != -1:
            end_pos = min(end_pos, idx)
    return tail[:end_pos].strip(" :")


def _scrape_commune(commune: str, domain: str) -> list[Activite]:
    resp = respectful_get(f"https://{domain}/")
    soup = BeautifulSoup(resp.text, "lxml")

    seen_links: set[str] = set()
    candidats: list[tuple[str, str]] = []  # (titre, href)
    for slide in soup.find_all("div", class_="swiper-slide"):
        cat = slide.find("div", class_="swiper_category")
        if not cat or "Stages et cours" not in cat.get_text():
            continue
        title_div = slide.find("div", class_="swiper_title")
        link = slide.find("a", href=True)
        if not title_div or not link or link["href"] in seen_links:
            continue
        seen_links.add(link["href"])
        candidats.append((_clean(title_div.get_text(" ")), link["href"]))

    activites: list[Activite] = []
    for titre, href in candidats:
        detail_resp = respectful_get(href)
        detail_soup = BeautifulSoup(detail_resp.text, "lxml")
        main = detail_soup.find("main", id="main-container") or detail_soup.find("main")
        if not main:
            continue
        full_text = _clean(main.get_text(" "))

        event_type = _extract_between(full_text, "Event type:", [])
        # Filtre clé : le carrousel tague parfois par erreur des événements
        # adultes en "Stages et cours" - seul "Activité (extrascolaire,
        # sport, atelier...)" correspond réellement à notre périmètre,
        # "Événementiel" (festivité, conférence...) est écarté.
        if not event_type.startswith("Activité"):
            continue

        date_match = DATE_RANGE_RE.search(full_text)
        dates = f"du {date_match.group(1)} au {date_match.group(2)}" if date_match else "Non extrait automatiquement"

        description = _extract_between(full_text, "Description:", ["Infos pratiques", "Address:", "Event type:"])

        age_match = AGE_RE.search(full_text)
        age_min, age_max = None, None
        if age_match:
            age_min = float(age_match.group(1).replace(",", "."))
            age_max = float(age_match.group(2)) if age_match.group(2) else None

        prix_match = PRIX_RE.search(full_text)
        prix = f"{prix_match.group(1)}€" if prix_match else "Non extrait automatiquement"

        lieu = _extract_between(full_text, "Address:", ["Téléphone", "Site web", "Event type:"]) or "Non précisé"

        disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

        activites.append(
            Activite(
                commune=commune,
                nom_activite=titre,
                type_activite=classify_type(titre + " " + description),
                dates=dates,
                age_min=age_min,
                age_max=age_max,
                prix=prix,
                lieu=lieu,
                modalites_inscription="Voir la fiche (lien source)",
                disponibilite=disponibilite,
                lien_source=href,
            )
        )

    return activites


def scrape() -> list[Activite]:
    activites: list[Activite] = []
    for commune, domain in COMMUNES:
        try:
            activites.extend(_scrape_commune(commune, domain))
        except Exception as exc:  # noqa: BLE001 - une commune en échec ne doit pas bloquer les autres
            print(f"  [agenda_omnia] {commune} : erreur ignorée - {exc}")
    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"# {len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
