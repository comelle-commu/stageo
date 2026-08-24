"""Vérification simple : lit toute la table `activites` sur Supabase et
l'affiche, pour confirmer visuellement que l'import a fonctionné.

Usage: venv/bin/python3 verify_supabase.py
"""
from __future__ import annotations

import supabase_client


def main() -> None:
    rows = supabase_client.fetch_all()
    print(f"{len(rows)} lignes dans `activites` (Supabase)\n")

    par_commune: dict[str, int] = {}
    for row in rows:
        par_commune[row["commune"]] = par_commune.get(row["commune"], 0) + 1

    for commune, n in sorted(par_commune.items()):
        print(f"  {commune:10s} {n} activités")

    print()
    for row in rows:
        age = ""
        if row.get("age_min") is not None or row.get("age_max") is not None:
            age = f" [{row.get('age_min')}-{row.get('age_max')} ans]"
        print(f"#{row['id']:>3} {row['commune']:10s} {row['plateforme_source']:10s} {row['nom_activite']}{age}")


if __name__ == "__main__":
    main()
