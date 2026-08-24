"""Scraper Verviers (Plone/iMio) - Plaines de vacances.

Page unique, HTML statique, structure très proche d'Ans (même thème Plone :
<main id="main-container">), mais présentée en <h3> par plaine plutôt qu'en
<li> par semaine - et effectivement plus complète qu'Ans sur deux points
annoncés par l'investigation : dates ET âges donnés par plaine. Écart par
rapport à l'attendu : AUCUN prix n'est indiqué sur cette page (contrairement
à Ans) - voir champ `prix` en sortie.

Deux formats de titre <h3> coexistent sur la page :
- "Plaine des Hougnes - du 23 au 27 février 2026"       (dates dans le titre, pas d'âge)
- "Plaine des Tourelles (4 - 9 ans)"                     (âge dans le titre, dates données une fois au-dessus pour tout le groupe)
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from common import Activite, extract_disponibilite, find_plone_content, respectful_get

URL = "https://www.verviers.be/atl/plaines-de-vacances/plaines-2026"
COMMUNE = "Verviers"

DATE_IN_TITLE_RE = re.compile(r"^(?P<nom>.+?)\s*-\s*(?P<dates>du\s+.+)$", re.I)
AGE_IN_TITLE_RE = re.compile(r"^(?P<nom>.+?)\s*\((?P<age_min>[\d,]+)\s*-\s*(?P<age_max>[\d,]+)\s*ans\)$", re.I)
GROUP_DATES_RE = re.compile(r"^du\s+\S.+\d{4}$", re.I)


def _clean_text(tag) -> str:
    return re.sub(r"\s+", " ", tag.get_text()).strip()


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


def scrape() -> list[Activite]:
    resp = respectful_get(URL)
    soup = BeautifulSoup(resp.text, "lxml")
    content = find_plone_content(soup)

    full_text = _clean_text(content)
    disponibilite = extract_disponibilite(full_text) or "Non communiqué sur cette page"

    contact_match = re.search(r"Courriel\s*([\w.+-]+@[\w.-]+)", full_text, re.I)
    contact = contact_match.group(1) if contact_match else None
    phones = [p.strip() for p in re.findall(r"Téléphone\s*(\+?[\d.]{8,})", full_text)]
    modalites = "Inscription via le Portail parents (lien e-guichet sur cette page)"
    if contact or phones:
        modalites += " - contact : " + " / ".join(filter(None, [contact] + phones))

    activites: list[Activite] = []
    group_dates: str | None = None  # dates partagées par le groupe de <h3> en cours (ex. plaines d'été)

    for tag in content.find_all(["h2", "h3", "p"]):
        text = _clean_text(tag)
        if not text:
            continue

        if tag.name in ("h2", "p") and GROUP_DATES_RE.match(text):
            group_dates = text
            continue

        if tag.name != "h3":
            continue

        m_date = DATE_IN_TITLE_RE.match(text)
        m_age = AGE_IN_TITLE_RE.match(text)

        if m_date:
            nom, dates = m_date.group("nom").strip(), m_date.group("dates").strip()
            age_min = age_max = None
        elif m_age:
            nom = m_age.group("nom").strip()
            age_min, age_max = _to_float(m_age.group("age_min")), _to_float(m_age.group("age_max"))
            dates = group_dates or "Non extrait automatiquement"
        else:
            continue  # <h3> qui n'est pas un titre de plaine (ex. "Contact", "Adresse"...)

        activites.append(
            Activite(
                commune=COMMUNE,
                nom_activite=nom,
                dates=dates,
                age_min=age_min,
                age_max=age_max,
                prix="Non communiqué sur cette page",
                lieu=f"Verviers - {nom}",
                modalites_inscription=modalites,
                disponibilite=disponibilite,
                lien_source=URL,
            )
        )

    return activites


if __name__ == "__main__":
    import json
    from dataclasses import asdict

    for a in scrape():
        print(json.dumps(asdict(a), ensure_ascii=False, indent=2))
