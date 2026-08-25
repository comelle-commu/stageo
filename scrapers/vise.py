"""Visé - EN ATTENTE, refus délibéré (pas un blocage technique).

La ville de Visé centralise ses stages/plaines sur une plateforme dédiée,
visestages.be (hébergée derrière Cloudflare) - PAS sur www.vise.be
(Nuxt/enpoche.be, comme Neupré). Le robots.txt de visestages.be interdit
EXPLICITEMENT "ClaudeBot" ("User-agent: ClaudeBot / Disallow: /"), avec un
en-tête "Content-Signal: ai-train=no" - un refus ciblé et sans ambiguïté
envers les agents Claude, quel que soit le User-Agent HTTP réellement
envoyé. Ce scraper tournant via Claude Code, l'intention du site est
respectée à la lettre plutôt que contournée en changeant de User-Agent.
La page d'accueil elle-même renvoie d'ailleurs 403 (Cloudflare).

Ce module ne fait volontairement AUCUNE requête HTTP.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "visestages.be interdit explicitement ClaudeBot dans son robots.txt "
    "(Content-Signal: ai-train=no) - refus respecté, pas de scraping ; "
    "www.vise.be lui-même ne publie pas le programme (renvoie vers cette "
    "plateforme tierce)"
)


def scrape() -> list:
    """Ne fait aucune requête réseau : Visé a explicitement exclu ClaudeBot."""
    return []


if __name__ == "__main__":
    print(f"Visé : {STATUT} - {RAISON}")
