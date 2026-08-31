"""Scraper StageVacances (stagevacances.be) - répertoire national de stages
géré par la Ligue des familles (en collaboration avec Parentia), sur lequel
n'importe quel organisme (ASBL, club, centre culturel...) peut publier ses
propres stages. Trouvé en creusant `pour-nos-enfants.be` (piste notée dans
docs/paysage-organismes-2026-08-24.md) : un stage de tennis y référençait un
lien `lecfs.be`, ce qui a mené à `cfs.py`, et une recherche complémentaire a
révélé ce répertoire plus large.

Le site vitrine (`www.stagevacances.be`) est un SPA Nuxt qui ne rend AUCUNE
donnée réelle en HTML brut (juste un shell générique, `<title>Stagevacances
</title>` identique sur toutes les pages) - toute la liste des stages est
chargée côté client depuis une API publique séparée, `api.stagevacances.be`
(backend Cockpit CMS), sans authentification ni session. `GET /camps` (pas
de pagination, `populate=1` sans effet observé) renvoie la totalité des
stages jamais publiés sur la plateforme (~2300 au 31/08/2026, toute la
Belgique, tous organismes confondus, plusieurs années) : le filtrage utile
se fait donc entièrement côté client ici, pas via des paramètres d'URL.

Champs bruts de chaque enregistrement : `location` (très hétérogène - tantôt
un simple code postal, tantôt "code postal + commune", tantôt une adresse
complète), `period_from`/`period_until` (epoch Unix), `organisator` (le plus
souvent juste un `_id` Mongo SANS nom résolu - aucun endpoint public trouvé
du type `/organisators` ou `/users` pour le résoudre ; `/themes` existe mais
pas d'équivalent `/age_group(s)` malgré plusieurs variantes de nom testées),
`base_prices` (un ou plusieurs tarifs nommés), `moderation` ("Published" une
fois l'organisme validé côté Ligue des familles).

Trois filtres nécessaires pour arriver à une liste honnête (voir `scrape()`) :
1. **Localisation** : `location` ne contient quasiment jamais un nom de
   commune Wallon exploitable tel quel - un code postal 4 chiffres commençant
   par "4" y figure presque toujours en revanche (tout le "4xxx" belge est en
   province de Liège). `POSTAL_COMMUNE` (~55 codes, ceux effectivement vus
   dans le jeu de données) résout ce code vers sa commune officielle -
   construit à la main à partir de recherches individuelles (pas de mapping
   fiable trouvé dans le dépôt ni via l'API elle-même), donc volontairement
   incomplet : un code absent du dict est ignoré plutôt que deviné.
2. **Fraîcheur** : la plupart des ~500 enregistrements en "4xxx" sont des
   stages PASSÉS (jusqu'à 2022) mais restés `moderation=Published` (champ
   `keep_published: true` vu sur plusieurs) - sans doute un choix de
   l'organisme de garder sa fiche visible à l'année plutôt qu'un bug. On ne
   garde que `period_until` dans le futur. Un garde-fou supplémentaire
   (`_MAX_PERIOD_DAYS`) écarte aussi les fiches "bannière" dont la période
   est absurdement large (des années entières, ex. un encart publicitaire
   Réseau IDée repéré avec `period_from`=avril 2023 et `period_until`=2029)
   plutôt qu'un vrai calendrier de stage.
3. **Organisme** : `ORGANISATEURS` associe chaque `organisator._id` déjà
   identifié à un vrai nom lisible (déduit du texte de description - aucun
   nom n'est jamais fourni structuré). `ORGANISATEURS_EXCLUS` retire les
   organismes déjà couverts ailleurs sur Trouvéo (La Ferme des enfants de
   Liège, via `ferme_des_enfants.py`) pour éviter un doublon. Un organisme
   pas encore dans `ORGANISATEURS` n'est PAS perdu silencieusement : un nom
   de repli lisible est dérivé du domaine de son `info_url` (voir
   `_organisateur_name()`), à affiner manuellement dans `ORGANISATEURS` la
   prochaine fois qu'on retombe dessus (même logique d'onboarding
   progressif que `CLUBS` dans iclub.py).

`age_group` n'a pas pu être résolu (aucun endpoint public trouvé) : l'âge
est extrait en best-effort depuis le texte de la description ("de X à Y
ans", "X-Y ans", "pour les X-Y ans") ou, à défaut, depuis le nom de fichier
des images jointes (convention "STAGE visu 3-5 ans" observée chez le Centre
Culturel de Theux) - `None` si rien de tout ça n'est trouvé, jamais deviné.

Légal : robots.txt de www.stagevacances.be lisible et ouvert (`Disallow:`
vide, seuls quelques chemins techniques Nuxt/Jekyll cités ailleurs sur
d'autres sites n'existent même pas ici) ; robots.txt de api.stagevacances.be
absent (404, comme les sous-domaines iClub - aucune restriction déclarée).
Page "Disclaimer" (`/disclaimer`) lue en entier : aucune clause sur le
scraping/l'extraction automatisée (juste la politique RGPD standard sur les
données des utilisateurs inscrits, hors sujet ici)."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from common import Activite, classify_type, respectful_get

API_URL = "https://api.stagevacances.be/camps"
SITE_BASE = "https://www.stagevacances.be/stages/"

# Code postal (4 chiffres, commençant par "4" = province de Liège en
# Belgique) -> commune officielle. Seulement les ~55 codes réellement vus
# dans `location` au 31/08/2026 (voir docstring) - un code absent est
# ignoré plutôt que deviné.
POSTAL_COMMUNE = {
    "4000": "Liège", "4020": "Liège", "4030": "Liège", "4032": "Liège",
    "4040": "Herstal", "4042": "Herstal",
    "4052": "Chaudfontaine", "4053": "Chaudfontaine",
    "4100": "Seraing", "4102": "Seraing",
    "4130": "Esneux", "4140": "Sprimont", "4163": "Anthisnes", "4171": "Comblain-au-Pont",
    "4190": "Ferrières", "4250": "Geer", "4263": "Braives", "4280": "Hannut", "4287": "Lincent",
    "4300": "Waremme", "4340": "Awans", "4347": "Fexhe-le-Haut-Clocher", "4350": "Remicourt",
    "4400": "Flémalle", "4430": "Ans", "4431": "Ans", "4450": "Juprelle", "4460": "Grâce-Hollogne",
    "4500": "Huy", "4530": "Villers-le-Bouillet", "4537": "Verlaine", "4540": "Amay",
    "4557": "Tinlot", "4560": "Clavier", "4577": "Modave", "4590": "Ouffet",
    "4600": "Visé", "4607": "Dalhem", "4651": "Herve", "4683": "Oupeye",
    "4800": "Verviers", "4802": "Verviers", "4834": "Limbourg", "4840": "Welkenraedt",
    "4850": "Plombières", "4860": "Pepinster", "4877": "Olne", "4890": "Thimister-Clermont",
    "4900": "Spa", "4910": "Theux", "4950": "Waimes", "4960": "Malmedy", "4980": "Trois-Ponts",
    "4987": "Stoumont",
}
POSTAL_RE = re.compile(r"\b(4\d{3})\b")

# organisator._id -> nom lisible, déduit à la main du texte de description
# (voir docstring - aucun endpoint public ne résout ce champ). À compléter
# au fil des sessions, comme CLUBS dans iclub.py.
ORGANISATEURS = {
    "626a6d7e47d7a92a93774a36": "Centre Culturel de Theux",
    "6a104ca0c7904232f50e4bf3": "Académie Tennis Padel Waremmien (ATPW)",
}
# organisator._id -> raison de l'exclusion (déjà couvert ailleurs sur
# Trouvéo, ou fiche non exploitable comme donnée de stage - voir docstring).
ORGANISATEURS_EXCLUS = {
    "63c5a7fb4c1dd062190175ff": "La Ferme des enfants de Liège - déjà couverte par ferme_des_enfants.py",
    "643e450da1039805c100d5e2": "Réseau IDée - bannière promotionnelle générique, pas un vrai calendrier de stage",
}

_MAX_PERIOD_DAYS = 60  # au-delà, la fiche est presque certainement une bannière/placeholder, pas un vrai stage daté

AGE_RANGE_RE = re.compile(r"(\d{1,2})\s*[-–à]\s*(\d{1,2})\s*ans", re.I)


def _epoch_to_date(ts) -> date | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
    except (ValueError, OSError, OverflowError):
        return None


MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
    7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def _format_dates(d1: date, d2: date) -> str:
    if d1.month == d2.month and d1.year == d2.year:
        return f"du {d1.day} au {d2.day} {MOIS_FR[d2.month]} {d2.year}"
    return f"du {d1.day} {MOIS_FR[d1.month]} {d1.year} au {d2.day} {MOIS_FR[d2.month]} {d2.year}"


def _commune_from_location(location: str) -> str | None:
    m = POSTAL_RE.search(location or "")
    if not m:
        return None
    return POSTAL_COMMUNE.get(m.group(1))


def _clean_html(text: str) -> str:
    import html as html_module

    return html_module.unescape(re.sub(r"<[^>]+>", " ", text or ""))


def _extract_age(description: str, images: list[dict]) -> tuple[float | None, float | None]:
    m = AGE_RANGE_RE.search(_clean_html(description))
    if not m:
        for img in images:
            title = (img.get("meta") or {}).get("title") or ""
            m = AGE_RANGE_RE.search(title)
            if m:
                break
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))


def _format_prix(base_prices: list[dict]) -> str:
    parts = []
    for bp in base_prices or []:
        value = (bp.get("value") or "").strip()
        try:
            amount = float(value.replace(",", "."))
        except ValueError:
            continue
        if amount <= 0:
            continue
        amount_str = f"{amount:.0f}" if amount == int(amount) else f"{amount:.2f}"
        name = bp.get("name", "").strip()
        parts.append(f"{amount_str}€ ({name})" if name else f"{amount_str}€")
    return " / ".join(parts) if parts else "Non communiqué sur cette page"


def _organisateur_name(organisator: dict, info_url: str) -> str:
    org_id = (organisator or {}).get("_id")
    display = (organisator or {}).get("display")
    if display:
        return display
    if org_id and org_id in ORGANISATEURS:
        return ORGANISATEURS[org_id]
    # Repli lisible plutôt que de perdre silencieusement un organisme non
    # encore identifié manuellement (voir docstring) - à affiner dans
    # ORGANISATEURS la prochaine fois qu'on retombe sur ce même _id.
    if info_url:
        host = urlparse(info_url if "://" in info_url else f"https://{info_url}").netloc or info_url
        return f"Organisme StageVacances ({host})"
    return "Organisme StageVacances (non identifié)"


def scrape() -> list[Activite]:
    resp = respectful_get(API_URL)
    camps = resp.json()

    today = date.today()
    activites: list[Activite] = []

    for camp in camps:
        if camp.get("moderation") != "Published":
            continue

        commune = _commune_from_location(camp.get("location", ""))
        if commune is None:
            continue

        org_id = (camp.get("organisator") or {}).get("_id")
        if org_id in ORGANISATEURS_EXCLUS:
            continue

        debut = _epoch_to_date(camp.get("period_from"))
        fin = _epoch_to_date(camp.get("period_until"))
        if fin is None or fin < today:
            continue
        if debut is not None and (fin - debut).days > _MAX_PERIOD_DAYS:
            continue  # période absurdement large -> bannière/placeholder, pas un vrai stage (voir docstring)

        nom = _clean_html(camp.get("name") or "").strip()
        if not nom:
            continue

        organisateur = _organisateur_name(camp.get("organisator") or {}, camp.get("info_url") or "")
        age_min, age_max = _extract_age(camp.get("description") or "", camp.get("images") or [])

        registration = (camp.get("registration") or camp.get("info_url") or "").strip()
        slug = camp.get("slug") or ""
        lien = f"{SITE_BASE}{slug}" if slug else registration

        activites.append(
            Activite(
                commune=commune,
                organisateur=organisateur,
                nom_activite=nom,
                type_activite=classify_type(nom, organisateur),
                dates=_format_dates(debut, fin) if debut else "Non communiqué sur cette page",
                age_min=age_min,
                age_max=age_max,
                prix=_format_prix(camp.get("base_prices") or []),
                lieu=f"{organisateur} ({commune})",
                modalites_inscription=registration or "Non communiqué sur cette page",
                disponibilite="Non communiqué sur cette page",
                lien_source=lien or API_URL,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    result = scrape()
    print(f"{len(result)} activités", flush=True)
    for a in result:
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
