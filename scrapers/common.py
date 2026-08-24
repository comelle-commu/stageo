"""Fonctions partagées par les scrapers Stagéo (un module par plateforme/commune).

Politique de respect (voir docs/investigation-technique-sites-communaux-2026-08-24.md) :
- Un User-Agent identifiable est envoyé sur chaque requête, avec un contact.
- Le Crawl-delay déclaré dans le robots.txt de chaque domaine est respecté
  entre deux requêtes vers ce même domaine (voir CRAWL_DELAYS ci-dessous).
- Aucune boucle sur des centaines de pages : un run = une poignée de requêtes,
  une par page connue à l'avance.
"""
from __future__ import annotations

import csv
import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import requests

# ASCII uniquement : un User-Agent avec un caractère accentué (ex. "Stagéo")
# a déclenché un 403 (WAF) côté serveur avec `requests`, alors que curl -A
# passait avec la même chaîne. Header HTTP -> rester en ASCII pur.
USER_AGENT = (
    "StageoScraperBot/0.1 (+contact: murieldelepont@gmail.com; "
    "projet Stageo, scraping leger de pages vitrines communales)"
)

# Crawl-delay (en secondes) déclaré dans le robots.txt de chaque domaine.
# Voir docs/investigation-technique-sites-communaux-2026-08-24.md pour le détail.
# Domaines absents du dict = pas de Crawl-delay déclaré (WordPress standard,
# aucune restriction notable) -> on applique quand même un minimum poli.
CRAWL_DELAYS = {
    "www.ans-ville.be": 120,
    "www.eghezee.be": 120,  # même plateforme iMio, non utilisé cette session
}
DEFAULT_MIN_DELAY = 2  # pause minimale de courtoisie entre requêtes, même sans Crawl-delay déclaré

_last_request_at: dict[str, float] = {}


def _domain_of(url: str) -> str:
    return re.sub(r"^https?://", "", url).split("/")[0]


def respectful_get(url: str, timeout: int = 20) -> requests.Response:
    """GET avec User-Agent identifiable et respect du Crawl-delay du domaine."""
    domain = _domain_of(url)
    min_delay = CRAWL_DELAYS.get(domain, DEFAULT_MIN_DELAY)
    last = _last_request_at.get(domain)
    if last is not None:
        elapsed = time.monotonic() - last
        wait = min_delay - elapsed
        if wait > 0:
            time.sleep(wait)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    _last_request_at[domain] = time.monotonic()
    resp.raise_for_status()
    # Certains sites communaux ne déclarent pas de charset dans leur
    # Content-Type (ex. neupre.be) ; requests retombe alors sur ISO-8859-1
    # par défaut HTTP alors que le contenu réel est en UTF-8 (mojibake sinon).
    if "charset" not in (resp.headers.get("content-type") or "").lower():
        resp.encoding = resp.apparent_encoding
    return resp


# Mots-clés simples pour repérer une mention de disponibilité en texte libre.
# Best-effort volontairement simple (voir consigne : pas besoin de perfection).
# Piège rencontré en pratique (page Neupré) : "L'inscription est OBLIGATOIRE
# PAR SEMAINE COMPLETE" utilise "complète" au sens de "semaine entière", pas
# "plus de places" -> exclu explicitement par lookbehind négatif sur "semaine".
_DISPO_PATTERNS = [
    (re.compile(r"(?<!semaine\s)\bcomplet(?:e|es|s)?\b", re.I), "COMPLET"),
    (re.compile(r"cl[ôo]tur[ée]e?s?", re.I), "CLÔTURÉ"),
    (re.compile(r"places?\s+(?:encore\s+)?dispo(?:s|nibles?)", re.I), "PLACES_DISPONIBLES"),
    (re.compile(r"liste\s+d[e']attente", re.I), "LISTE_ATTENTE"),
    (re.compile(r"places?\s+limit[ée]es?", re.I), "PLACES_LIMITÉES"),
]


def extract_disponibilite(text: str) -> Optional[str]:
    """Cherche un signal de disponibilité en texte libre. Retourne None si rien trouvé."""
    for pattern, label in _DISPO_PATTERNS:
        if pattern.search(text):
            return label
    return None


@dataclass
class Activite:
    commune: str
    nom_activite: str
    dates: str
    age_min: Optional[float]
    age_max: Optional[float]
    prix: str
    lieu: str
    modalites_inscription: str
    disponibilite: str
    lien_source: str
    date_verification: str = field(default_factory=lambda: date.today().isoformat())


FIELDNAMES = [
    "commune",
    "nom_activite",
    "dates",
    "age_min",
    "age_max",
    "prix",
    "lieu",
    "modalites_inscription",
    "disponibilite",
    "lien_source",
    "date_verification",
]


def write_outputs(activites: list[Activite], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "activites.json"
    csv_path = out_dir / "activites.csv"

    records = [asdict(a) for a in activites]
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)

    return json_path, csv_path
