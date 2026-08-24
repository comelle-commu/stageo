-- Stagéo — 2 ajouts pour préparer l'automatisation GitHub Actions et les
-- futures alertes de nouvelles activités :
--
-- 1) `activites.premiere_apparition` : horodatage de la première insertion
--    d'une activité, jamais mis à jour ensuite (contrairement à `dates` ou
--    `prix` qui peuvent changer d'un run à l'autre). Permet plus tard un
--    calcul du type "cette activité est apparue il y a 2 jours".
--
-- 2) `scrape_runs` : historique des exécutions du scraper (nombre
--    d'activités récupérées à chaque run), utilisé par le contrôle qualité
--    du workflow GitHub Actions (voir .github/workflows/scrape.yml) pour
--    détecter une chute anormale (site qui a changé de structure).

-- 1) premiere_apparition ------------------------------------------------
--
-- Ajoutée nullable d'abord, puis backfillée depuis `created_at` (qui,
-- pour les 82 lignes déjà en base, capture bien leur date d'insertion
-- réelle) plutôt que depuis `now()` - sinon les 82 activités existantes
-- auraient l'air d'être toutes apparues à l'instant de cette migration,
-- ce qui casserait le calcul "apparue il y a X jours" dès le premier jour.
alter table public.activites
    add column if not exists premiere_apparition timestamptz;

update public.activites
    set premiere_apparition = created_at
    where premiere_apparition is null;

alter table public.activites
    alter column premiere_apparition set not null,
    alter column premiere_apparition set default now();

comment on column public.activites.premiere_apparition is
    'Horodatage de la première insertion de cette activité - jamais mis à jour par les upserts suivants (le scraper n''envoie jamais ce champ, donc PostgREST ne le touche pas lors d''un conflit). Sert de base aux futures alertes "nouvelle activité".';

-- 2) scrape_runs ----------------------------------------------------------
--
-- Historique des runs, pour que le contrôle qualité du workflow GitHub
-- Actions compare "nombre d'activités récupérées cette semaine" au
-- dernier run considéré SAIN (statut = 'OK'), pas au run précédent
-- littéral - un run précédent lui-même en échec ne doit pas devenir la
-- nouvelle référence basse, sinon une panne durable finirait par sembler
-- "normale". Amorcée à 82 activités (référence de départ demandée).
create table if not exists public.scrape_runs (
    id               bigint generated always as identity primary key,
    ran_at           timestamptz not null default now(),
    total_activites  integer not null,
    statut           text not null check (statut in ('OK', 'ALERTE_BAISSE')),
    details          text
);

comment on table public.scrape_runs is
    'Historique des exécutions du scraper (voir .github/workflows/scrape.yml) - utilisé pour détecter une chute anormale du nombre d''activités récupérées d''un run à l''autre.';
