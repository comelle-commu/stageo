"""Scraper La Ferme des Enfants de Liège (Centre nature de Liège ASBL) -
stages nature/animaux à la ferme pédagogique de Liège (Vieille-voie-de-
Tongres 48, 4000 Liège).

La liste des stages est publique via l'API WooCommerce Store standard
(`/wp-json/wc/store/v1/products?category=stage`), qui couvre à elle seule
toutes les sous-catégories saisonnières (automne, hiver, printemps, été,
détente) - pas besoin de les interroger une par une. Mais les VRAIES dates
de chaque stage ("19/10/2026 - 23/10/2026") ne sont PAS dans cette API :
elles ne sont rendues que dans le HTML de la page produit elle-même, dans
un bloc Divi (constructeur de page) au format "<h3>Dates</h3>texte" - même
schéma pour "Age" et "Lieu". D'où l'appel API (liste + prix + stock) suivi
d'un fetch HTML par produit (dates/âge/lieu).

Légal : robots.txt = "User-agent: *, Crawl-delay: 10", aucun Disallow ->
géré via l'entrée dédiée dans common.CRAWL_DELAYS (10s > DEFAULT_MIN_DELAY
de 2s, donc il faut la déclarer explicitement pour la respecter - même
convention que www.capsciences.be).

Tous les stages tournent autour des animaux/de la nature (soins aux
animaux quotidiens dans chaque programme) - classify_type() sur le seul
titre ne le détecterait pas de façon fiable (titres poétiques comme
"Traces de vie et jeux de lumière"), donc type_activite est fixé
directement à "Sciences & nature" plutôt que déduit du texte.
"""
from __future__ import annotations

import re
from html import unescape

from common import Activite, respectful_get

API_URL = "https://www.lafermedesenfantsdeliege.be/wp-json/wc/store/v1/products?category=stage&per_page=50"
ORGANISATEUR = "La Ferme des Enfants de Liège"
COMMUNE = "Liège"
LIEU_DEFAUT = "La Ferme des enfants de Liège, Vieille-voie-de-Tongres 48, 4000 Liège"

DATES_RE = re.compile(r"<h3>Dates</h3>\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})")
AGE_RE = re.compile(r"<h3>Age</h3>\s*(?:<p>)?(?:<span[^>]*>)?\s*De\s+(\d+)\s*(?:ans?)?\s*à\s+(\d+)\s*an", re.I)
LIEU_RE = re.compile(r"<h3>Lieu</h3>\s*([^<]+)</div>")


def _format_prix(prices: dict) -> str:
    minor = int(prices.get("currency_minor_unit", 2))
    price_range = prices.get("price_range") or {}
    min_amount = price_range.get("min_amount") or prices.get("price")
    max_amount = price_range.get("max_amount")
    if not min_amount:
        return "Non communiqué sur cette page"
    min_eur = int(min_amount) / (10**minor)
    if not max_amount or max_amount == min_amount:
        return f"{min_eur:.0f}€"
    max_eur = int(max_amount) / (10**minor)
    return f"{min_eur:.0f}€ - {max_eur:.0f}€"


def _parse_product_page(html: str) -> tuple[str, float | None, float | None, str]:
    m = DATES_RE.search(html)
    dates = f"du {m.group(1)} au {m.group(2)}" if m else "Non précisées"

    age_min = age_max = None
    m = AGE_RE.search(html)
    if m:
        age_min, age_max = float(m.group(1)), float(m.group(2))

    m = LIEU_RE.search(html)
    lieu = unescape(m.group(1).strip()) if m else LIEU_DEFAUT

    return dates, age_min, age_max, lieu


def scrape() -> list[Activite]:
    resp = respectful_get(API_URL)
    products = resp.json()

    activites = []
    for p in products:
        page_resp = respectful_get(p["permalink"])
        dates, age_min, age_max, lieu = _parse_product_page(page_resp.text)

        activites.append(
            Activite(
                commune=COMMUNE,
                organisateur=ORGANISATEUR,
                nom_activite=unescape(p["name"]),
                type_activite="Sciences & nature",
                dates=dates,
                age_min=age_min,
                age_max=age_max,
                prix=_format_prix(p.get("prices", {})),
                lieu=lieu,
                modalites_inscription="Inscription en ligne sur lafermedesenfantsdeliege.be",
                disponibilite="Places disponibles" if p.get("is_in_stock", True) else "Complet",
                lien_source=p["permalink"],
            )
        )
    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités", flush=True)
    for a in result[:3]:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
