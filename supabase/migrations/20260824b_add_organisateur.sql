-- Trouvéo — ajoute la colonne `organisateur`, nécessaire pour les scrapers
-- non-communaux (ADEPS, Cap Sciences...) : une activité de ces sources
-- n'est pas rattachée à une commune belge unique (elle peut se dérouler
-- dans n'importe quelle ville, parfois même à l'étranger pour l'ADEPS), au
-- contraire des scrapers communaux où `commune` = la source elle-même.
--
-- Convention : `commune` reste NOT NULL (contrainte déjà en place) et vaut
-- '' (chaîne vide, jamais NULL - la contrainte unique `activites_dedup_key`
-- ne dédoublonnerait pas correctement des NULL, qui ne sont jamais égaux
-- entre eux en SQL) quand la commune réelle n'est pas déductible du lieu.
-- `organisateur` reste NULL pour les scrapers communaux (la source est déjà
-- dans `commune`). Voir docs/organismes-adeps-capsciences-2026-08-24.md.

alter table public.activites
    add column if not exists organisateur text;

comment on column public.activites.organisateur is
    'Nom de l''organisme source pour les scrapers non-communaux (ADEPS, Cap Sciences...). NULL pour les scrapers communaux (source = commune, déjà dans la colonne commune).';

create index if not exists activites_organisateur_idx on public.activites (organisateur);
