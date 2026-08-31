"""Scraper "Jeunesse à Bruxelles asbl" - Plaines de vacances de la Ville de
Bruxelles (3-12 ans), seule source du jeu de données à couvrir les 3-6 ans
dans la région bruxelloise (voir docs, aucune autre source connue ne
descend sous 5-6 ans autour de Bruxelles).

La page listing (URL) ne contient aucune date/âge structuré en HTML - elle
renvoie vers un PDF "programme" (un par saison groupée, ex. "AUT-HIV-26-27"
pour Automne+Hiver). Pas de robots.txt sur ce domaine (404) - on applique
donc le délai de courtoisie par défaut (voir common.DEFAULT_MIN_DELAY).

Structure du PDF (texte natif, pas un scan) : pour chaque saison, une page
d'intro donne le thème (ex. "Les Petits Scientifiques"), puis 1-2 pages
listent les "plaines" par paire de colonnes - une colonne "I" (maternelle,
3-6 ans) et une colonne "II" (primaire, 6-12 ans), parfois un site combiné
"I et II" (3-12 ans, ex. Centre d'accueil Haren). Extraction via
page.extract_text() (pas extract_tables() - ce n'est pas un vrai tableau)
avec une astuce de découpe : dans ce PDF, aucun nom de site ne contient la
lettre "I" isolée comme mot - couper juste après un "I" suivi d'un espace
puis de "Plaine"/"Centre" sépare donc fiablement les deux moitiés d'une
ligne à deux colonnes ("Plaine X I Plaine Y II" -> ["Plaine X I", "Plaine
Y II"]) sans avoir à reconstruire la géométrie de la page.

`commune` = code postal (1000/1020/1120/1130 - Bruxelles/Laeken/Neder-Over-
Heembeek/Haren) plutôt qu'un nom : ce sont tous des quartiers de la Ville
de Bruxelles, pas des communes séparées au sens INSEE/Trouvéo, et le code
postal résout directement dans COMMUNE_COORDS (voir data/commune_coords.json)
pour la recherche par proximité et les alertes - même logique que pour un
parent qui tape son code postal dans criteres.html.

Restriction d'accès IMPORTANTE (voir page 26 du PDF) : réservé aux enfants
domicilié·es ou scolarisé·es sur le territoire de la Ville de Bruxelles
(ces 4 codes postaux), ou dont un parent est membre du personnel communal -
pas ouvert à "toute la région bruxelloise" malgré la proximité géographique.
Précisé explicitement dans `modalites_inscription` pour ne pas induire en
erreur une famille d'une autre commune bruxelloise (ex. Uccle, 1180) qui
tomberait dessus via la recherche par rayon.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, classify_type, fetch_pdf_bytes, is_pdf, respectful_get

# GELÉ le 31/08/2026 : www.jeunesseabruxelles.be sert une chaîne de
# certificats SSL incomplète (SSLCertVerificationError "unable to get local
# issuer certificate"), reproduit sur les runners GitHub Actions même en
# retentant explicitement avec le magasin CA du système (pas juste un
# décalage de version côté certifi - un vrai problème serveur, que même curl
# refuserait). Pas de contournement côté client sans désactiver la
# vérification du certificat, ce qu'on ne fait jamais. run_all.py appelle
# donc ce module comme EN_ATTENTE (aucune requête réseau) plutôt que SCRAPERS
# - les 21 activités importées le 30/08/2026 restent en base mais ne se
# rafraîchiront plus tant que jeunesseabruxelles.be n'a pas corrigé son
# certificat côté serveur. `scrape()` reste intact ci-dessous : à
# remettre dans SCRAPERS (voir run_all.py) dès que le site est réparé,
# sans rien réécrire.
RAISON = (
    "www.jeunesseabruxelles.be sert une chaîne de certificats SSL "
    "incomplète (SSLCertVerificationError, confirmé même avec le magasin CA "
    "du système - problème serveur, pas un souci de configuration côté "
    "scraper) - à réessayer une fois leur certificat corrigé."
)

LISTING_URL = "https://www.jeunesseabruxelles.be/site/activites-de-vacances/plaines/"
ORGANISATEUR = "Jeunesse à Bruxelles"

PERIOD_RE = re.compile(r"^(Automne|Hiver|Détente|Printemps|Été|Ete)$")
DATERANGE_RE = re.compile(r"^Du\s+\w+\s+(\d{1,2}\s+\w+\s+\d{4})\s+au\s+\w+\s+(\d{1,2}\s+\w+\s+\d{4})")
DEADLINE_RE = re.compile(r"^ATTENTION\s*:\s*(.+)", re.I)
SITE_LINE_RE = re.compile(r"^(Plaine\b.+|Centre d.accueil\b.+)$")
AGE_RE = re.compile(r"Enfants de\s+([\d,]+)\s*à\s*([\d,]+)\s*ans")
POSTAL_RE = re.compile(r"(\d{4})\s+([A-ZÉ][\wÀ-ÿ\-]*(?:\s+[A-ZÉ][\wÀ-ÿ\-]*)?)")
THEME_RE = re.compile(r"^([^:.\n]{4,60})[:\.]")

TARIF = (
    "30€/semaine (24€ si semaine de 4 jours) - tarif préférentiel 10€/8€ pour "
    "les habitant·es de la Ville de Bruxelles (1000/1020/1120/1130) ou membres "
    "du personnel communal - tarif social 5€/4€ sous conditions de revenus"
)
ELIGIBILITE = (
    "Réservé aux enfants domicilié·es ou scolarisé·es sur le territoire de la "
    "Ville de Bruxelles (1000 Bruxelles, 1020 Laeken, 1120 Neder-Over-Heembeek, "
    "1130 Haren), ou dont un parent est membre du personnel communal - voir "
    "conditions complètes sur jeunesseabruxelles.be."
)


def _split_on_i_boundary(line: str) -> list[str]:
    """Coupe après un "I" isolé (pas suivi de "et") quand il précède
    "Plaine"/"Centre" - voir la note en tête de fichier."""
    parts = re.split(r"(?<=\bI\b)(?!\s+et)\s+(?=Plaine|Centre)", line)
    return [p.strip() for p in parts if p.strip()]


def _find_pdf_url() -> str:
    resp = respectful_get(LISTING_URL)
    soup = BeautifulSoup(resp.text, "lxml")
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True).lower()
        if "programme" in text and "plaine" in text and a["href"].lower().endswith(".pdf"):
            return a["href"]
    raise RuntimeError(f"Aucun lien vers le programme PDF des plaines trouvé sur {LISTING_URL}")


def _parse_pdf(pdf_bytes: bytes) -> list[Activite]:
    import io

    import pdfplumber

    activites: list[Activite] = []
    current_period: str | None = None
    current_daterange: str | None = None
    current_deadline: str | None = None
    theme_by_period: dict[str, str] = {}

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            # "Plaines / <Saison> / Modalités pratiques en fin de section" se
            # répète en en-tête de CHAQUE page de la section (pas seulement
            # la page d'intro) - une page ne porte le paragraphe de thème que
            # si elle n'a ni date ni site listé (sinon "Modalités..." est
            # immédiatement suivi de la date, ou pire de la 1ère "Plaine ...",
            # qui serait alors prise à tort pour un thème).
            has_daterange = any(DATERANGE_RE.match(l) for l in lines)
            has_site_line = any(SITE_LINE_RE.match(l) for l in lines)
            page_period = next((l for l in lines if PERIOD_RE.match(l)), None)
            if page_period and not has_daterange and not has_site_line and page_period not in theme_by_period:
                try:
                    modalites_idx = lines.index("Modalités pratiques en fin de section")
                except ValueError:
                    modalites_idx = -1
                if 0 <= modalites_idx < len(lines) - 1:
                    theme_line = lines[modalites_idx + 1]
                    theme_match = THEME_RE.match(theme_line)
                    theme_by_period[page_period] = theme_match.group(1).strip() if theme_match else theme_line[:60]

            i = 0
            while i < len(lines):
                line = lines[i]

                if PERIOD_RE.match(line):
                    current_period = line

                m = DATERANGE_RE.match(line)
                if m:
                    current_daterange = f"Du {m.group(1)} au {m.group(2)}"

                m2 = DEADLINE_RE.match(line)
                if m2:
                    current_deadline = m2.group(1)

                if SITE_LINE_RE.match(line) and current_period and current_daterange:
                    site_names = _split_on_i_boundary(line)
                    age_line = lines[i + 1] if i + 1 < len(lines) else ""
                    ages = AGE_RE.findall(age_line)

                    block: list[str] = []
                    j = i + 2
                    while j < len(lines) and not SITE_LINE_RE.match(lines[j]) and not lines[j].isdigit() and not lines[j].startswith("BUS"):
                        block.append(lines[j])
                        j += 1
                    postals = POSTAL_RE.findall(" ".join(block))

                    n = max(len(site_names), len(ages), 1)
                    for k in range(n):
                        name = site_names[k] if k < len(site_names) else (site_names[0] if site_names else "Plaine")
                        age = ages[k] if k < len(ages) else (ages[0] if ages else None)
                        postal = postals[k] if k < len(postals) else (postals[0] if postals else None)
                        if age is None or postal is None:
                            continue  # donnee incomplete - on ecarte plutot que d'inventer

                        code_postal, ville = postal
                        theme = theme_by_period.get(current_period) or f"Plaines de {current_period}"
                        activites.append(
                            Activite(
                                commune=code_postal,
                                organisateur=ORGANISATEUR,
                                nom_activite=f"{theme} - {name}",
                                type_activite=classify_type(theme),
                                dates=current_daterange,
                                age_min=float(age[0].replace(",", ".")),
                                age_max=float(age[1].replace(",", ".")),
                                prix=TARIF,
                                lieu=f"{name}, {code_postal} {ville}",
                                modalites_inscription=(
                                    f"Inscription en ligne sur jeunesseabruxelles.be"
                                    + (f" - {current_deadline}" if current_deadline else "")
                                    + f". {ELIGIBILITE}"
                                ),
                                disponibilite="Non communiqué sur cette page",
                                lien_source=LISTING_URL,
                            )
                        )
                    i = j
                else:
                    i += 1

    return activites


def scrape() -> list[Activite]:
    pdf_url = _find_pdf_url()
    pdf_bytes = fetch_pdf_bytes(pdf_url)
    if not is_pdf(pdf_bytes):
        raise RuntimeError(f"{pdf_url} ne sert pas un vrai PDF (voir common.fetch_pdf_bytes)")
    return _parse_pdf(pdf_bytes)


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
