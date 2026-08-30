"""Alertes personnalisées "un stage correspond à votre enfant" — le
différenciant affiché en hero sur index.html.

Contrairement à brevo_digest.py (un email hebdomadaire générique envoyé à
toute la liste d'attente, sans filtre d'âge ni de commune), ce script
regarde chaque ligne de `criteres_parents` individuellement et n'envoie
que les activités qui correspondent VRAIMENT aux critères de cette
famille (âge de l'enfant, type d'activité, commune dans le rayon choisi)
- un email personnalisé par parent via l'API transactionnelle Brevo, pas
une campagne groupée.

Lancé après brevo_digest.py dans le workflow GitHub Actions (voir
.github/workflows/scrape.yml).

Anti-doublon : `alertes_envoyees` (email, activite_id) retient ce qui a
déjà été signalé à qui, pour ne jamais renvoyer la même activité deux fois
à la même famille même si le job tourne plusieurs fois.

Usage :
  venv/bin/python3 criteres_alertes.py            # envoi réel
  venv/bin/python3 criteres_alertes.py --dry-run  # affiche les matches, n'envoie rien et ne touche pas alertes_envoyees

Variable d'environnement ALERTES_TEST_EMAIL (optionnelle) : si définie, ne
traite que ce parent (ex. pour tester sans risquer d'envoyer aux vraies
familles inscrites) - voir l'input `test_email` du workflow_dispatch dans
.github/workflows/scrape.yml.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from urllib.parse import urlencode

import requests

import supabase_client
from supabase_client import SUPABASE_URL, _headers

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.environ.get("BREVO_SENDER_NAME", "Trouvéo")
TEST_EMAIL = os.environ.get("ALERTES_TEST_EMAIL", "").strip().lower()
SITE_URL = "https://trouveo.be"

COORDS_PATH = Path(__file__).parent / "data" / "commune_coords.json"
MAX_ITEMS_PER_EMAIL = 8  # au-delà, on résume - même logique que brevo_digest.py

# Pour exclure les stages déjà terminés des alertes (voir extract_end_date
# ci-dessous) - `dates` est un texte libre écrit par ~40 sites communaux
# différents, jamais une vraie colonne date structurée sur `activites`.
MOIS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12, "decembre": 12,
}
_MOIS_RE = "|".join(MOIS.keys())


def extract_end_date(dates_str: str) -> date | None:
    """Extrait la date de fin d'une activité à partir du texte libre
    `dates` (ex. "Du 19/10/2026 au 23/10/2026", "6 juillet au 14 août
    2026"). Retourne None si aucune date exploitable n'est trouvée (texte
    purement descriptif type "dates non précisées sur cette page") - ces
    activités sont alors exclues des alertes plutôt qu'incluses par
    défaut : mieux vaut rater une alerte que d'en envoyer une sur un stage
    déjà terminé.

    Cherche, dans cet ordre, le DERNIER motif trouvé (la date de fin est
    toujours mentionnée en dernier dans ces formulations "Du X au Y") :
    1. DD/MM/YYYY
    2. DD <mois en toutes lettres> YYYY
    3. DD/MM suivi plus loin d'une année entre parenthèses, ex.
       "du 19 au 21/10 (2026)" - format utilisé par plusieurs sites iMio.
    """
    if not dates_str:
        return None

    matches = re.findall(r"(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})", dates_str)
    if matches:
        d, m, y = matches[-1]
        try:
            return date(int(y), int(m), int(d))
        except ValueError:
            pass

    matches = re.findall(rf"(\d{{1,2}})\s+({_MOIS_RE})\s+(\d{{4}})", dates_str, re.IGNORECASE)
    if matches:
        d, mois, y = matches[-1]
        try:
            return date(int(y), MOIS[mois.lower()], int(d))
        except ValueError:
            pass

    paren = re.search(r"\((\d{4})\)", dates_str)
    if paren:
        year = int(paren.group(1))
        before = dates_str[: paren.start()]
        dm = re.findall(r"(\d{1,2})\s*/\s*(\d{1,2})\b", before)
        if dm:
            d, m = dm[-1]
            try:
                return date(year, int(m), int(d))
            except ValueError:
                pass

    return None


def is_upcoming(activite: dict, today: date) -> bool:
    end = extract_end_date(activite.get("dates", ""))
    return end is not None and end >= today


def is_configured() -> bool:
    return bool(BREVO_API_KEY and BREVO_SENDER_EMAIL)


def normalize_name(s: str) -> str:
    """Doit rester identique à normalizeName() dans activites.html : les
    deux lisent les mêmes clés dans commune_coords.json (généré une fois
    depuis le COMMUNE_COORDS du JS - voir data/commune_coords.json)."""
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return r * 2 * asin(sqrt(a))


def load_coords() -> dict:
    return json.loads(COORDS_PATH.read_text(encoding="utf-8"))


def fetch_criteres() -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/criteres_parents?select=*"
    resp = requests.get(url, headers=_headers("count=none"), timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_activites() -> list[dict]:
    # PostgREST plafonne a 1000 lignes par defaut sans pagination - avec
    # plus de 2000 activites en base, la moitie du catalogue etait ignoree
    # silencieusement par le moteur d'alertes (meme bug que cote site, voir
    # fetchAllActivites() dans activites.html). On boucle par pages de 1000
    # jusqu'a une page plus courte que PAGE_SIZE.
    page_size = 1000
    offset = 0
    rows: list[dict] = []
    while True:
        url = f"{SUPABASE_URL}/rest/v1/activites?select=*&limit={page_size}&offset={offset}"
        resp = requests.get(url, headers=_headers("count=none"), timeout=30)
        resp.raise_for_status()
        page = resp.json()
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


def fetch_already_sent() -> set[tuple[str, int]]:
    url = f"{SUPABASE_URL}/rest/v1/alertes_envoyees?select=email,activite_id"
    resp = requests.get(url, headers=_headers("count=none"), timeout=30)
    resp.raise_for_status()
    return {(row["email"], row["activite_id"]) for row in resp.json()}


def log_sent(pairs: list[tuple[str, int]]) -> None:
    if not pairs:
        return
    url = f"{SUPABASE_URL}/rest/v1/alertes_envoyees"
    payload = [{"email": email, "activite_id": activite_id} for email, activite_id in pairs]
    resp = requests.post(
        url,
        headers=_headers("resolution=merge-duplicates,return=minimal"),
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()


def enfant_matches(enfant: dict, activite: dict) -> bool:
    age = enfant.get("age")
    age_min, age_max = activite.get("age_min"), activite.get("age_max")
    # age_min/age_max nuls sur certaines lignes historiques (âge non
    # détecté par le scraper source) - on préfère notifier plutôt que
    # rejeter faute de donnée.
    if age is not None and age_min is not None and age_max is not None:
        if not (age_min <= age <= age_max):
            return False
    types = enfant.get("types_activites") or []
    if types and activite.get("type_activite") not in types:
        return False
    return True


def within_radius(parent_commune: str, rayon_km: float, activite_commune: str, coords: dict) -> bool:
    origin = coords.get(normalize_name(parent_commune))
    target = coords.get(normalize_name(activite_commune))
    if not origin or not target:
        # Commune non géocodable d'un côté ou de l'autre (ex. activité
        # d'organisme sans commune renseignée - ~36% des lignes en pratique,
        # voir colonne `commune` vide sur ADEPS/Cap Sciences/MyiClub) - on
        # exclut plutôt que d'inclure par défaut : ces familles reçoivent
        # déjà toutes les activités via le digest hebdomadaire générique
        # (brevo_digest.py), et une alerte "près de chez vous" qui inclut
        # des activités à 100km sans lieu connu détruirait la confiance
        # dans la fonctionnalité plus vite qu'elle ne raterait un vrai match.
        return False
    return haversine_km(origin[0], origin[1], target[0], target[1]) <= rayon_km


def find_matches(parent: dict, activites: list[dict], coords: dict, already_sent: set[tuple[str, int]]) -> list[dict]:
    matches = []
    for act in activites:
        if (parent["email"], act["id"]) in already_sent:
            continue
        if not within_radius(parent["commune"], parent.get("rayon_km") or 15, act["commune"], coords):
            continue
        if any(enfant_matches(e, act) for e in parent["enfants"]):
            matches.append(act)

    # Même logique de tri que côté site (voir exactCommuneKey/preferredTypes
    # dans activites.html) : la commune même du parent d'abord (ex.
    # recherche "Ans" -> les stages À Ans avant ceux des communes voisines
    # trouvées par rayon), puis les types d'activité demandés par au moins
    # un enfant, puis par date de fin croissante.
    own_commune = normalize_name(parent["commune"])
    preferred_types = {t for e in parent["enfants"] for t in (e.get("types_activites") or [])}
    matches.sort(key=lambda act: (
        0 if normalize_name(act["commune"]) == own_commune else 1,
        0 if act.get("type_activite") in preferred_types else 1,
        extract_end_date(act.get("dates", "")) or date.max,
    ))
    return matches


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Doit rester synchronisé avec AGE_BRACKETS dans activites.html - sert
# uniquement à construire le lien "Voir le détail" (voir build_detail_link).
AGE_BRACKETS = [
    ("0-3", 0, 3),
    ("3-6", 3, 6),
    ("6-9", 6, 9),
    ("9-12", 9, 12),
    ("12+", 12, float("inf")),
]


def build_detail_link(parent: dict) -> str:
    """Lien vers /activites pré-filtré avec les mêmes critères que ceux qui
    ont produit l'alerte - voir applyFiltersFromUrl() dans activites.html.
    Le paramètre `commune` réutilise directement la recherche par proximité
    déjà en place côté site (voir communesWithinRadius()).

    `types` (union des types de TOUS les enfants, dédupliquée) fait
    remonter en priorité les activités qui correspondent, sans jamais les
    exclure - contrairement à l'âge (filtre dur, un seul chip actif à la
    fois côté site), un type de préférence peut se cumuler entre enfants
    sans perdre de sens : "Ans, en priorité Sport ou Art" reste correct
    même pour une fratrie aux goûts différents.

    L'âge, lui, reste réservé à une famille à un seul enfant : un chip
    d'âge unique représenterait mal des enfants d'âges différents - mieux
    vaut alors laisser cette dimension non filtrée plutôt que de biaiser
    vers un seul enfant."""
    params = {"commune": parent["commune"]}
    enfants = parent.get("enfants") or []
    if len(enfants) == 1:
        age = enfants[0].get("age")
        if isinstance(age, (int, float)):
            for key, lo, hi in AGE_BRACKETS:
                if lo <= age < hi:
                    params["age"] = age
                    break
    all_types: list[str] = []
    for enfant in enfants:
        for t in enfant.get("types_activites") or []:
            if t not in all_types:
                all_types.append(t)
    if all_types:
        params["types"] = ",".join(all_types)
    return f"{SITE_URL}/activites?{urlencode(params)}"


def build_email_html(matches: list[dict], commune: str, detail_link: str) -> tuple[str, str]:
    n = len(matches)
    subject = f"{n} stage{'s' if n != 1 else ''} correspond{'ent' if n != 1 else ''} à votre recherche"

    cards = []
    for r in matches[:MAX_ITEMS_PER_EMAIL]:
        nom = (r.get("nom_activite") or "").strip()
        dates = (r.get("dates") or "").strip()
        lieu = (r.get("lieu") or "").strip()
        cards.append(
            '<tr><td style="padding:0 0 10px;">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            'style="background:#FFFFFF;border:1px solid rgba(1,83,128,0.12);border-radius:14px;">'
            '<tr><td style="padding:14px 16px;">'
            f'<div style="font-family:\'Grandstander\',Arial,sans-serif;font-weight:700;'
            f'color:#015380;font-size:15px;line-height:1.35;margin-bottom:4px;">{_esc(nom)}</div>'
            f'<div style="color:#5C7A8C;font-size:13px;line-height:1.5;">{_esc(dates)}'
            f'{" &middot; " + _esc(lieu) if lieu else ""}</div>'
            "</td></tr></table></td></tr>"
        )
    remaining = n - MAX_ITEMS_PER_EMAIL
    if remaining > 0:
        cards.append(
            '<tr><td style="padding:2px 4px 10px;color:#5C7A8C;font-size:13px;">'
            f"…et {remaining} autre{'s' if remaining != 1 else ''} correspondant à vos critères.</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Grandstander:wght@700;800&family=Work+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;background:#FFFDF8;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FFFDF8;">
<tr><td align="center" style="padding:36px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;font-family:'Work Sans',Arial,sans-serif;">

  <tr><td style="padding-bottom:22px;">
    <span style="font-family:'Grandstander',Arial,sans-serif;font-weight:800;font-size:22px;color:#015380;">Trouvéo</span>
  </td></tr>

  <tr><td style="padding-bottom:8px;">
    <span style="display:inline-block;font-size:12px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;
      color:#017089;background:#FFFFFF;padding:7px 14px;border-radius:100px;border:1px solid rgba(1,83,128,0.12);">
      Alerte personnalisée
    </span>
  </td></tr>

  <tr><td style="padding-bottom:24px;">
    <span style="font-family:'Grandstander',Arial,sans-serif;font-weight:700;font-size:21px;color:#015380;line-height:1.3;">
      {n} stage{'s' if n != 1 else ''} correspond{'ent' if n != 1 else ''} à vos critères près de {_esc(commune)}
    </span>
  </td></tr>

  <tr><td>{''.join(cards)}</td></tr>

  <tr><td align="center" style="padding:14px 0 28px;">
    <a href="{detail_link}" style="display:inline-block;background:#0197AF;color:#ffffff;text-decoration:none;
      font-family:'Work Sans',Arial,sans-serif;font-weight:700;font-size:14px;padding:14px 28px;border-radius:100px;">
      Voir le détail →
    </a>
  </td></tr>

  <tr><td style="border-top:1px solid rgba(1,83,128,0.12);padding-top:18px;">
    <p style="color:#93A9B5;font-size:12px;line-height:1.6;margin:0;text-align:center;">
      Vous recevez cet email car vous avez laissé vos critères de recherche sur Trouvéo.
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body>
</html>
""".strip()
    return subject, html


def send_transactional(to_email: str, subject: str, html: str) -> None:
    resp = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
        json={
            "sender": {"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html,
        },
        timeout=20,
    )
    resp.raise_for_status()


def main() -> int:
    dry_run = "--dry-run" in sys.argv

    if not supabase_client.is_configured():
        print("Supabase non configuré (scrapers/.env) - alertes ignorées.")
        return 0
    if not dry_run and not is_configured():
        print(
            "Brevo non configuré pour les alertes (BREVO_API_KEY / BREVO_SENDER_EMAIL "
            "manquants) - alertes ignorées."
        )
        return 0

    coords = load_coords()
    parents = fetch_criteres()
    activites = fetch_activites()
    already_sent = fetch_already_sent()

    today = datetime.now(timezone.utc).date()
    activites = [a for a in activites if is_upcoming(a, today)]

    if TEST_EMAIL:
        parents = [p for p in parents if p["email"].strip().lower() == TEST_EMAIL]
        print(f"[test] restreint à {TEST_EMAIL} ({len(parents)} profil trouvé).")

    print(f"{len(parents)} critère(s) à traiter, {len(activites)} activité(s) encore à venir.")

    total_emails = 0
    for parent in parents:
        matches = find_matches(parent, activites, coords, already_sent)
        if not matches:
            continue

        print(f"{parent['email']}: {len(matches)} nouveau(x) match(s).")
        if dry_run:
            continue

        subject, html = build_email_html(matches, parent["commune"], build_detail_link(parent))
        try:
            send_transactional(parent["email"], subject, html)
        except requests.HTTPError as exc:
            print(f"Erreur d'envoi pour {parent['email']}: {exc}")
            continue
        log_sent([(parent["email"], act["id"]) for act in matches])
        total_emails += 1

    if dry_run:
        print("[dry-run] aucun email envoyé, alertes_envoyees non modifiée.")
    else:
        print(f"{total_emails} email(s) d'alerte envoyé(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
