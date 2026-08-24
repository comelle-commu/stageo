# Stagéo — Automatisation GitHub Actions + contrôle qualité (24/08/2026)

## Contexte

Suite au backend Supabase fonctionnel et à l'élargissement du scraper à 7
communes (82 activités — `docs/scraper-cas-difficiles-2026-08-24.md`),
cette session automatise l'exécution régulière via GitHub Actions et pose
les bases de la détection de nouvelles activités pour de futures alertes.

## Tâche 1 — Colonne `premiere_apparition`

Migration : `supabase/migrations/20260825_add_premiere_apparition_and_scrape_runs.sql`
(à exécuter dans le SQL Editor Supabase, comme la première table — les
clés API fournies ne permettent toujours pas le DDL, voir
`docs/supabase-backend-2026-08-24.md` pour le contexte).

`premiere_apparition` (`timestamptz`, `not null`, défaut `now()`) est
ajoutée à `activites`. **Aucun changement de code n'était nécessaire** pour
garantir qu'elle n'est jamais mise à jour par les upserts suivants : le
scraper (`supabase_client.to_row()`) n'envoie jamais ce champ dans le
payload, et PostgREST, avec `Prefer: resolution=merge-duplicates`, ne
touche que les colonnes réellement présentes dans le payload lors d'un
conflit — une colonne absente du payload reste donc intacte. C'est le même
principe qui protège déjà `created_at` depuis le début.

**Détail important pour les 82 lignes déjà en base** : la migration
n'utilise volontairement pas `now()` pour les remplir rétroactivement (ça
aurait fait croire que les 82 activités existantes venaient toutes
d'apparaître au moment de la migration). Elle backfille plutôt depuis
`created_at`, qui capture déjà leur date d'insertion réelle — le calcul
"apparue il y a X jours" est donc correct dès le premier jour.

## Tâche 2 — Workflow GitHub Actions

`.github/workflows/scrape.yml` :
- **Déclencheurs** : `schedule` (cron hebdomadaire, lundi 06h00 UTC) +
  `workflow_dispatch` (bouton "Run workflow" manuel dans l'onglet Actions,
  pratique pour tester sans attendre le cron).
- **Étapes** : checkout → installe Python 3.11 → `pip install -r
  scrapers/requirements.txt` → lance `python run_all.py` (le même script
  qu'en local) depuis le dossier `scrapers/`, avec `SUPABASE_URL` et
  `SUPABASE_SECRET_KEY` injectés comme variables d'environnement depuis les
  secrets GitHub Actions (jamais en clair dans le fichier).
- **Bonus** : la sortie (`activites.json`, `.csv`, `timings.txt`) est
  conservée comme artefact du run pendant 30 jours (`if: always()` — même
  si le run échoue, pour pouvoir inspecter ce qui a été récupéré avant le
  problème).
- `timeout-minutes: 15` : marge large, un run complet prend actuellement
  ~4 minutes (Herstal et Huy consomment chacun 120s de Crawl-delay iMio).

### Ajouter les secrets dans GitHub (à faire une fois, manuellement)

1. Sur GitHub, ouvrir le dépôt `comelle-commu/stageo`.
2. **Settings** (onglet en haut du dépôt) → dans le menu de gauche,
   **Secrets and variables** → **Actions**.
3. Onglet **Secrets** (pas *Variables* — les secrets sont chiffrés et
   jamais affichés en clair, contrairement aux variables) → bouton **New
   repository secret**.
4. Créer deux secrets :
   - Nom `SUPABASE_URL`, valeur : l'URL du projet
     (`https://oitmxxrurvutazuqsjbl.supabase.co`).
   - Nom `SUPABASE_SECRET_KEY`, valeur : la clé secrète du projet
     (`sb_secret_...`, la même que dans `scrapers/.env` en local — jamais
     la clé `publishable`, qui n'a pas les droits d'écriture nécessaires).
5. Une fois enregistrés, ces secrets sont utilisables par n'importe quel
   workflow du dépôt via `${{ secrets.NOM_DU_SECRET }}` (déjà en place dans
   `scrape.yml`) — leur valeur n'apparaît jamais dans les logs, même en cas
   d'erreur (GitHub la masque automatiquement si elle apparaît en sortie).

### Voir l'historique des exécutions

Onglet **Actions** en haut du dépôt GitHub → cliquer sur le workflow
**"Scraper Stagéo"** dans la liste à gauche → chaque ligne est une
exécution passée, avec sa date, sa durée, et un indicateur ✅ (vert,
réussi) ou ❌ (rouge, échoué). Cliquer sur une ligne pour voir le détail
étape par étape (les mêmes logs que ceux affichés en local), et
télécharger l'artefact `scrape-output` (bas de la page du run) pour
récupérer les fichiers JSON/CSV de ce run précis.

Pour déclencher un run manuellement sans attendre le lundi : onglet
Actions → "Scraper Stagéo" → bouton **Run workflow** (en haut à droite de
la liste des runs) → **Run workflow** à nouveau pour confirmer.

## Tâche 3 — Contrôle qualité (chute anormale)

Nouvelle table `scrape_runs` (même migration que `premiere_apparition`) :
journalise chaque run (`ran_at`, `total_activites`, `statut`, `details`).

`supabase_client.log_run_and_check_quality(total_activites)` :
1. Récupère le `total_activites` du **dernier run marqué `OK`** (pas
   simplement le run précédent — voir plus bas pourquoi).
2. Si absent (tout premier run après la migration), utilise **82** comme
   référence de départ (demandé explicitement).
3. Calcule la baisse : `(référence - total_actuel) / référence`.
4. Si ≥ 50%, statut `ALERTE_BAISSE` ; sinon `OK`. Le run est journalisé
   dans `scrape_runs` dans tous les cas (pour garder l'historique complet,
   y compris les échecs).
5. `run_all.py` retourne alors un code de sortie non nul → le step GitHub
   Actions échoue → **le run apparaît rouge dans l'onglet Actions**,
   visible sans avoir à ouvrir les logs.

**Choix de conception à noter** : la comparaison se fait contre le dernier
run **sain**, pas contre le run immédiatement précédent au sens strict. Si
elle comparait au run précédent tout court, une panne qui dure plusieurs
semaines finirait par sembler "stable" (chaque run en échec devenant la
nouvelle référence basse pour le suivant, la baisse par rapport à ce
nouveau plancher restant sous 50%) — l'alerte ne se déclencherait qu'une
fois puis se tairait, alors que le problème persiste. En comparant toujours
au dernier `OK`, l'alerte reste active tant que le problème n'est pas
réglé.

L'import Supabase lui-même (upsert) continue de s'exécuter même si le
contrôle qualité déclenche une alerte — un run dégradé ne supprime jamais
de données existantes (l'upsert n'ajoute/ne met à jour que ce qu'il a
trouvé), donc laisser passer l'écriture ne peut pas appauvrir la base ; ce
qui doit être visible immédiatement, c'est le statut rouge du workflow, pas
un blocage de l'écriture.

## Tâche 4 — Ajuster la fréquence

Voir la section dédiée dans `scrapers/README.md` ("Ajuster la fréquence du
scraper") — en résumé : une seule ligne à changer
(`cron: "0 6 * * 1"` dans `.github/workflows/scrape.yml`), avec des
exemples prêts à copier-coller pour "tous les 2 jours" et "tous les 3
jours" en période préparatoire aux vacances.

## Point de vigilance connu sur les cron GitHub Actions

Deux comportements standards de GitHub à connaître, pas spécifiques à ce
projet :
- Un cron programmé peut être retardé de quelques minutes en cas de forte
  charge sur l'infrastructure GitHub (pas de garantie de déclenchement à la
  seconde près) — sans impact réel ici (le scraper n'a pas besoin de
  précision horaire).
- GitHub **désactive automatiquement** les workflows programmés d'un dépôt
  resté inactif (aucun commit) pendant 60 jours. Un commit sur le dépôt (ou
  une réactivation manuelle dans l'onglet Actions) suffit à le relancer. À
  garder en tête si le projet passe plusieurs mois sans y toucher.

## Prochaine étape suggérée

`premiere_apparition` et l'historique `scrape_runs` posent les bases
techniques pour de vraies alertes ("3 nouvelles activités à Ans cette
semaine") — la logique de détection elle-même (comparer les
`premiere_apparition` récentes, décider du canal d'envoi — email, autre)
reste à construire, volontairement hors scope cette session.
