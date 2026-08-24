# Stagéo — Backend Supabase (24/08/2026)

## Contexte

Suite au socle mutualisé et à la validation sur 4 communes
(`docs/scraper-socle-mutualise-verviers-2026-08-24.md`), cette session
remplace les fichiers `activites.json`/`activites.csv` par un vrai backend
interrogeable : une table `activites` sur Supabase, alimentée par
`run_all.py`. L'interface web n'est **pas** construite cette session
(volontairement) — objectif : une base fiable d'abord.

## Schéma de base

`supabase/migrations/20260824_create_activites.sql` — table `activites` :

| Colonne | Type | Notes |
|---|---|---|
| `id` | `bigint identity` | clé primaire auto-incrémentée |
| `commune` | `text` | ex. "Ans" |
| `commune_slug` | `text` | normalisé, ex. "ans" — pour les filtres côté site plus tard |
| `plateforme_source` | `text` | Plone / WordPress / Nuxt — trace technique pour le débug |
| `nom_activite`, `dates`, `prix`, `lieu`, `modalites_inscription`, `disponibilite`, `lien_source` | `text` | reprennent le schéma de sortie du scraper tel quel |
| `age_min`, `age_max` | `numeric` | nullable |
| `date_verification` | `date` | |
| `created_at` | `timestamptz` | ajouté par défaut (audit), non demandé explicitement mais gratuit et utile |

**Dédoublonnage** : contrainte `unique (commune_slug, nom_activite, dates)`
— une même activité (même commune + même nom + mêmes dates) est mise à
jour, pas dupliquée, à chaque run.

**RLS activé** dès maintenant (avant même l'interface web) : une policy
`for select to anon, authenticated using (true)` autorise la lecture
publique — nécessaire pour le futur site — mais aucune policy d'écriture
n'est créée, donc la clé publique (`SUPABASE_PUBLISHABLE_KEY`, destinée à
être exposée côté client plus tard) ne peut pas écrire. Seule la clé
secrète (utilisée par le scraper, qui contourne RLS par nature sur
Supabase) peut insérer/mettre à jour. Choix fait maintenant plutôt que d'y
repenser une fois le site branché.

### ⚠️ Écart par rapport au plan : la table n'a pas pu être créée par le code

Les credentials fournis pour cette session
(`SUPABASE_PUBLISHABLE_KEY`/`SUPABASE_SECRET_KEY`, les clés API "Data API"
au nouveau format `sb_publishable_.../sb_secret_...`) permettent de
lire/écrire des **lignes** via l'API REST (PostgREST), mais **pas
d'exécuter du DDL** (`CREATE TABLE`) — ça demande soit un accès direct à la
base Postgres (mot de passe DB, non fourni — choix délibéré pour ne pas
faire circuler un secret de plus), soit de passer par le SQL Editor du
dashboard. La migration a donc été collée manuellement dans le SQL Editor
par l'utilisateur (fichier `supabase/migrations/20260824_create_activites.sql`
tenu comme source de vérité versionnée, à réappliquer telle quelle sur un
futur environnement - staging, autre projet Supabase, etc.).

## Script d'import

`scrapers/supabase_client.py` — écrit/lit via l'API REST PostgREST
directement (`requests`, pas de SDK `supabase-py`, pour rester léger) :
- `upsert_activites(activites)` : POST avec `Prefer:
  resolution=merge-duplicates` et `on_conflict=commune_slug,nom_activite,dates`
  → upsert sur la contrainte unique définie en base.
- `fetch_all()` : lecture simple de toute la table.

Credentials lus depuis `scrapers/.env` (gitignoré — jamais committé,
contient les clés `sb_secret_...`). `run_all.py` importe automatiquement
vers Supabase après avoir écrit les fichiers JSON/CSV **si** `.env` est
présent et complet ; sinon il l'indique clairement et continue sans planter
(pas de dépendance dure à Supabase pour que le scraper reste utilisable
seul).

## Vérification

Run complet (`venv/bin/python3 run_all.py`) sur les 4 communes actives
(Ans, Seraing, Neupré, Verviers) :

```
Total activités : 25
  Ans          6 activités    0.83s  [OK]
  Seraing      9 activités    1.11s  [OK]
  Neupre       5 activités    1.21s  [OK]
  Verviers     5 activités    1.32s  [OK]
  Floreffe     0 activités    0.00s  [EN_ATTENTE]

--- Import Supabase ---
  25 lignes upsertées dans `activites` en 0.78s
```

Lecture de vérification (`venv/bin/python3 verify_supabase.py`) — 25
lignes confirmées côté Supabase, réparties comme attendu (Ans 6, Seraing 9,
Neupré 5, Verviers 5).

**Test de dédoublonnage** : run relancé une seconde fois immédiatement
après → toujours 25 lignes en base (pas 50). L'upsert sur
`(commune_slug, nom_activite, dates)` fonctionne comme prévu.

## Prochaine étape suggérée

Base fiable et vérifiée. Prochaine session naturelle : construire
l'interface web qui lit `activites` (via la clé publique, lecture seule
grâce à la policy RLS déjà en place), ou continuer à élargir le scraper
aux cas plus durs identifiés précédemment (Herstal/Waremme → PDF,
Huy/Sprimont → page hub, Oupeye → image, Aywaille → plateforme tierce)
avant d'agrandir l'interface.
