-- Stagéo — table `activites` : sortie du scraper (Ans, Seraing, Neupré,
-- Verviers pour l'instant), une ligne par activité (plaine/stage) trouvée.
-- Voir scrapers/README.md et docs/ pour le contexte complet.

create table if not exists public.activites (
    id                    bigint generated always as identity primary key,
    commune               text not null,
    commune_slug          text not null,               -- ex. "ans", "verviers" - pour les filtres côté site plus tard
    plateforme_source     text not null,                -- Plone / WordPress / Nuxt - trace technique pour le débug
    nom_activite          text not null,
    dates                 text not null,
    age_min               numeric,
    age_max               numeric,
    prix                  text not null,
    lieu                  text not null,
    modalites_inscription text not null,
    disponibilite         text not null,
    lien_source           text not null,
    date_verification     date not null,
    created_at            timestamptz not null default now(),

    -- Dédoublonnage : une même activité (même commune + même nom + mêmes
    -- dates) est mise à jour plutôt que dupliquée à chaque run du scraper.
    constraint activites_dedup_key unique (commune_slug, nom_activite, dates)
);

comment on table public.activites is
    'Activités (plaines/stages) extraites des sites communaux par les scrapers. Une ligne = une activité pour une commune/période donnée.';
comment on column public.activites.commune_slug is
    'Identifiant normalisé de la commune (minuscule, sans accent/espace) pour les filtres côté site.';
comment on column public.activites.plateforme_source is
    'Plateforme technique du site source (Plone, WordPress, Nuxt...) - utile pour le débug scraper, pas destiné à l''affichage.';

-- RLS : le scraper écrit avec la clé secrète (service role, qui contourne
-- RLS) ; la clé publique (anon, utilisée plus tard par le site web) ne doit
-- pouvoir que LIRE, jamais écrire. Activé dès maintenant même si
-- l'interface web n'est pas encore construite cette session, pour ne pas
-- avoir à y repenser plus tard.
alter table public.activites enable row level security;

create policy "Lecture publique des activités"
    on public.activites
    for select
    to anon, authenticated
    using (true);

-- Index utiles pour les futurs filtres côté site (commune, tranche d'âge).
create index if not exists activites_commune_slug_idx on public.activites (commune_slug);
create index if not exists activites_age_idx on public.activites (age_min, age_max);
