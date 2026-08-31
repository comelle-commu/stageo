"""Diagnostic ponctuel : consulte les statistiques d'engagement Brevo
(livré, ouvert, cliqué...) pour les emails transactionnels déjà envoyés
(alertes personnalisées, relances, confirmations) - pour savoir si les
familles inscrites ouvrent réellement ce qu'on leur envoie, pas juste si
l'envoi a réussi côté API.

Utilise l'API "Email Event Report" de Brevo (GET /v3/smtp/statistics/
events), qui journalise chaque évènement (delivered, opened, clicks...)
par destinataire - contrairement à /v3/smtp/email (l'envoi lui-même), qui
ne dit que si Brevo a accepté le message.

Usage :
  venv/bin/python3 email_stats.py                          # tous les évènements récents (30 jours)
  venv/bin/python3 email_stats.py --email x@example.com     # restreint à un destinataire
  venv/bin/python3 email_stats.py --days 14
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter, defaultdict

import requests

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")


def fetch_events(email: str | None, days: int) -> list[dict]:
    params = {"limit": 500, "offset": 0, "days": days, "sort": "desc"}
    if email:
        params["email"] = email
    resp = requests.get(
        "https://api.brevo.com/v3/smtp/statistics/events",
        headers={"api-key": BREVO_API_KEY, "Accept": "application/json"},
        params=params,
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("events", [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=None, help="Ne montrer que les évènements pour ce destinataire")
    parser.add_argument("--days", type=int, default=30, help="Fenêtre en jours (défaut 30)")
    args = parser.parse_args()

    if not BREVO_API_KEY:
        print("BREVO_API_KEY manquant - impossible d'interroger les statistiques.")
        return 1

    events = fetch_events(args.email, args.days)
    print(f"{len(events)} évènement(s) sur les {args.days} derniers jours"
          f"{' pour ' + args.email if args.email else ''}.\n")

    by_recipient: dict[str, Counter] = defaultdict(Counter)
    for ev in events:
        by_recipient[ev.get("email", "?")][ev.get("event", "?")] += 1

    for recipient, counts in sorted(by_recipient.items()):
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        print(f"{recipient}: {summary}")

    print("\n--- Détail chronologique ---")
    for ev in events:
        print(f"{ev.get('date')}  {ev.get('email'):35s}  {ev.get('event'):12s}  sujet: {ev.get('subject', '')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
