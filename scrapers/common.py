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
    "TrouveoScraperBot/0.1 (+contact: murieldelepont@gmail.com; "
    "projet Trouveo, scraping leger de pages vitrines communales)"
)

# Crawl-delay (en secondes) déclaré dans le robots.txt de chaque domaine.
# Voir docs/investigation-technique-sites-communaux-2026-08-24.md et
# docs/investigation-technique-elargissement-communes-2026-08-24.md.
#
# Tous les sites iMio/Plone partagent EXACTEMENT le même robots.txt (194
# lignes, Crawl-delay 120) - confirmé par diff direct entre plusieurs paires
# de domaines (Liège/Herstal, Liège/Oupeye) pendant l'investigation
# d'élargissement. IMIO_CRAWL_DELAY centralise cette valeur ; IMIO_DOMAINS
# liste les domaines confirmés iMio à ce jour (robots.txt identique
# vérifié, ou plateforme identifiée via <meta generator="Plone"> + structure
# @@site-logo/@@download typique). Domaines absents du dict = pas de
# Crawl-delay déclaré -> on applique quand même un minimum poli.
IMIO_CRAWL_DELAY = 120
IMIO_DOMAINS = {
    "www.ans-ville.be",
    "www.eghezee.be",
    "www.liege.be",
    "www.verviers.be",
    "www.herstal.be",
    "www.huy.be",
    "www.waremme.be",
    "www.aywaille.be",
    "www.sprimont.be",
    "www.oupeye.be",
    # Confirmées iMio le 25/08/2026 via redirection de leur robots.txt vers
    # static.imio.be (voir docs/elargissement-provinces-2026-08-24.md) -
    # Namur, Hainaut, Brabant wallon et Luxembourg, pas seulement Liège.
    # Scraper écrit seulement pour Mons et Arlon pour l'instant ; les
    # autres restent enregistrées ici (Crawl-delay correct dès qu'on les
    # scrape) même sans scraper actif.
    "www.namur.be",
    "www.mons.be",
    "www.lalouviere.be",
    "www.ottignies-louvain-la-neuve.be",
    "www.nivelles.be",
    "www.arlon.be",
    "www.bastogne.be",
    "www.ciney.be",
}
CRAWL_DELAYS = {domain: IMIO_CRAWL_DELAY for domain in IMIO_DOMAINS}
# Organismes hors socle communal (voir
# docs/investigation-technique-organismes-2026-08-24.md) : Crawl-delay
# propre à chaque domaine, déclaré explicitement dans son robots.txt.
CRAWL_DELAYS["www.capsciences.be"] = 10
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


# --- Vérification légale réutilisable (robots.txt + CGU) -------------------
#
# Référence : le robots.txt iMio confirmé (194 lignes, Crawl-delay 120,
# disallow limité aux chemins dynamiques - recherche, login, calendrier...).
# Un nouveau domaine qui matche cette empreinte peut être considéré comme
# faisant partie du même réseau sans tout relire à la main.
_IMIO_ROBOTS_SIGNATURE_LINES = {"User-agent: *", "Crawl-delay: 120"}

# Mots-clés à chercher dans le texte VISIBLE d'une page légale (CGU/mentions
# légales/gdpr-view). Piège rencontré et déjà corrigé une fois : chercher
# sur le HTML brut remonte des faux positifs (classe CSS "fa-robot" de
# Font Awesome, "décision automatisée" du RGPD qui n'a rien à voir) -> on
# ne cherche que dans le texte visible, après avoir retiré <script>/<style>.
_CGU_WARNING_KEYWORDS = [
    "scraping",
    "extraction automatis",
    "robot",
    "crawl",
    "moissonnage",
]


@dataclass
class LegalCheck:
    domain: str
    robots_status: Optional[int]
    robots_matches_imio_signature: bool
    crawl_delay: Optional[int]
    legal_page_url: Optional[str]
    legal_page_status: Optional[int]
    warnings: list[tuple[str, str]]  # (mot-clé, contexte) trouvés dans le texte visible
    notes: list[str]

    @property
    def verdict(self) -> str:
        if self.warnings:
            return "À VÉRIFIER MANUELLEMENT (mot-clé suspect trouvé)"
        if self.robots_status == 200:
            return "GO"
        return "À VÉRIFIER MANUELLEMENT (robots.txt non lisible)"


def check_legal(domain: str, legal_path: str = "/gdpr-view") -> LegalCheck:
    """Vérification légale d'un nouveau domaine : robots.txt + page légale.

    Coûte 2 requêtes HTTP - à appeler UNE FOIS manuellement en onboardant une
    nouvelle commune (ex. dans un terminal Python), jamais depuis scrape()
    ni dans une boucle. Les sites iMio utilisent tous /gdpr-view pour leurs
    mentions légales (confirmé sur Ans, Eghezée, Liège, Herstal, Sprimont) ;
    passer un autre `legal_path` pour une plateforme différente (WordPress,
    Nuxt...).
    """
    from bs4 import BeautifulSoup  # import local : common.py reste utilisable sans bs4 pour le reste

    notes: list[str] = []
    warnings: list[tuple[str, str]] = []

    robots_status = None
    matches_signature = False
    crawl_delay = None
    try:
        r = requests.get(f"https://{domain}/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=15)
        robots_status = r.status_code
        if r.status_code == 200:
            lines = {line.strip() for line in r.text.splitlines()}
            matches_signature = _IMIO_ROBOTS_SIGNATURE_LINES.issubset(lines)
            m = re.search(r"Crawl-delay:\s*(\d+)", r.text, re.I)
            crawl_delay = int(m.group(1)) if m else None
            if not matches_signature:
                notes.append("robots.txt lisible mais ne matche pas la signature iMio connue - à relire à la main")
    except requests.RequestException as exc:
        notes.append(f"robots.txt inaccessible : {exc}")

    legal_url = f"https://{domain}{legal_path}"
    legal_status = None
    try:
        r = requests.get(legal_url, headers={"User-Agent": USER_AGENT}, timeout=15)
        legal_status = r.status_code
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup.find_all(["script", "style"]):
                tag.decompose()
            visible_text = soup.get_text(" ")
            for kw in _CGU_WARNING_KEYWORDS:
                for m in re.finditer(kw, visible_text, re.I):
                    start, end = m.span()
                    context = re.sub(r"\s+", " ", visible_text[max(0, start - 80):end + 80]).strip()
                    warnings.append((kw, context))
    except requests.RequestException as exc:
        notes.append(f"page légale inaccessible : {exc}")

    return LegalCheck(
        domain=domain,
        robots_status=robots_status,
        robots_matches_imio_signature=matches_signature,
        crawl_delay=crawl_delay,
        legal_page_url=legal_url,
        legal_page_status=legal_status,
        warnings=warnings,
        notes=notes,
    )


# --- Extraction PDF (texte natif uniquement, pas d'OCR) --------------------
#
# Plusieurs communes iMio renvoient vers un PDF pour le programme détaillé
# (Herstal confirmé, Waremme probable - voir
# docs/investigation-technique-elargissement-communes-2026-08-24.md).
# Choix délibéré : pas d'OCR à ce stade -> un PDF scanné (image) donnera un
# texte vide ou un tableau vide, pas une erreur - à l'appelant de vérifier.
def fetch_pdf_bytes(url: str) -> bytes:
    """Télécharge un PDF via respectful_get (donc avec le même crawl-delay
    que les pages HTML). ATTENTION : une URL qui *ressemble* à un .pdf n'en
    est pas forcément un - vu en pratique sur Ans, où le lien "Règlement
    d'ordre intérieur ... .pdf" sert en réalité un fichier .docx
    (Content-Type: application/vnd.openxmlformats...). Vérifier le
    Content-Type ou la signature des bytes (%PDF-) avant de traiter le
    résultat comme un PDF."""
    resp = respectful_get(url)
    return resp.content


def is_pdf(content: bytes) -> bool:
    return content[:5] == b"%PDF-"


def extract_pdf_tables(pdf_bytes: bytes) -> list[list[list[Optional[str]]]]:
    """Extraction de tableaux via pdfplumber (texte natif). Retourne une
    liste de tableaux (un par tableau détecté, toutes pages confondues),
    chaque tableau étant une liste de lignes (liste de cellules). Une
    lecture attentive reste nécessaire : un tableau peut continuer sur la
    page suivante sans répéter sa ligne d'en-tête (vu sur le PDF Herstal)."""
    import io

    import pdfplumber

    tables: list[list[list[Optional[str]]]] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables.extend(page.extract_tables())
    return tables


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extraction de texte brut (pypdf) - pour repérer des mots-clés
    (prix, âge...) dans un PDF qui n'est pas un tableau (règlement,
    brochure...)."""
    import io

    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


# --- Repérage de zone de contenu (Plone/iMio) -------------------------------
#
# Mutualisable avec un niveau de confiance raisonnable : `<main>` (souvent
# id="main-container") a été vérifié présent sur 9 sites iMio différents
# (Ans et Verviers inspectés en détail pour construire un vrai parseur ;
# Liège, Herstal, Huy, Waremme, Aywaille, Sprimont, Oupeye confirmés lors du
# passage en revue structurel - <main> systématiquement trouvé, contenu non
# vide). Un repli sur l'ancien thème Plone "Sunburst" (#content-core, vu sur
# Eghezée lors de l'investigation initiale mais jamais scrapé pour de vrai)
# est ajouté par prudence, non garanti.
#
# Ce qui N'EST PAS mutualisable pour l'instant (voir
# docs/investigation-technique-elargissement-communes-2026-08-24.md) : la
# façon dont chaque commune publie ses données À L'INTÉRIEUR de cette zone
# varie (HTML direct, PDF joint, page hub, image intégrée) - cette fonction
# ne fait que trouver la bonne zone à lire, pas l'extraction elle-même.
def find_plone_content(soup) -> object:
    """Retourne l'élément BeautifulSoup contenant le contenu principal d'une
    page Plone/iMio, avec repli si la structure diffère de celle observée."""
    return (
        soup.find("main", id="main-container")
        or soup.find("main")
        or soup.find(id="content-core")
        or soup.find(id="content")
        or soup
    )


@dataclass
class Activite:
    # `commune` = la commune belge concernee quand elle est identifiable
    # (deductible du lieu pour un organisme, ou la commune elle-meme pour un
    # scraper communal). Laisser "" (pas None - voir supabase_client.to_row)
    # quand ce n'est pas deductible (ex. stage ADEPS a l'etranger) : la
    # vraie localisation reste dans `lieu` dans tous les cas.
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
    # Nom de l'organisme source pour les scrapers non-communaux (ADEPS, Cap
    # Sciences...). None pour les scrapers communaux (source = la commune
    # elle-meme, deja dans `commune`).
    organisateur: Optional[str] = None


FIELDNAMES = [
    "commune",
    "organisateur",
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
