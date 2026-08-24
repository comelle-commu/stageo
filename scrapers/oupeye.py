"""Oupeye - EN ATTENTE, exclu explicitement cette session (consigne).

Le programme des stages est publié comme une image intégrée
(`@@images/image-....png`) sur la page communale, pas comme texte ou PDF -
nécessiterait de l'OCR, volontairement évité à ce stade (voir
docs/investigation-technique-elargissement-communes-2026-08-24.md).
Inscription via APSCHOOL, comme Neupré.
"""
from __future__ import annotations

STATUT = "EN_ATTENTE"
RAISON = (
    "Programme publié en image intégrée (pas de texte/PDF) - nécessiterait "
    "de l'OCR, explicitement laissé de côté cette session."
)


def scrape() -> list:
    """Ne fait aucune requête réseau : image, pas de texte/PDF exploitable sans OCR."""
    return []


if __name__ == "__main__":
    print(f"Oupeye : {STATUT} - {RAISON}")
