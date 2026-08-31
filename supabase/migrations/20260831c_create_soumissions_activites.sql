-- Stagéo — table `soumissions_activites` : les organismes soumettent
-- eux-mêmes une activité (formulaire soumettre-activite.html), en attente
-- de relecture avant publication - voir docs/partenariats-premium-2026-08-31.md
-- et partenaires.html ("nous validons votre fiche ensemble avant
-- publication"). Pas d'auto-publication : une soumission n'apparaît sur le
-- site qu'une fois `statut` passé à 'approuvee' (à la main, dans le Table
-- editor Supabase) ET reprise par scrapers/import_soumissions.py (même
-- run hebdomadaire que le reste - voir .github/workflows/scrape.yml).
create table if not exists public.soumissions_activites (
    id                    bigint generated always as identity primary key,
    organisateur          text not null,
    commune               text not null default '',
    nom_activite          text not null,
    type_activite         text not null,
    dates                 text not null,
    age_min               numeric,
    age_max               numeric,
    prix                  text not null default '',
    lieu                  text not null default '',
    modalites_inscription text not null default '',
    lien_source           text not null default '',
    description_longue    text,
    contact_email         text not null,

    -- 'en_attente' (défaut) / 'approuvee' / 'rejetee' - changé à la main
    -- dans le Table editor Supabase après relecture.
    statut                text not null default 'en_attente',
    -- Rempli par import_soumissions.py au moment où la soumission approuvée
    -- est effectivement copiée dans `activites` - évite de la réimporter
    -- au run suivant.
    importee_le           timestamptz,
    created_at            timestamptz not null default now()
);

comment on table public.soumissions_activites is
    'Activités soumises directement par les organismes (soumettre-activite.html), en attente de relecture manuelle avant publication - voir docs/partenariats-premium-2026-08-31.md.';
comment on column public.soumissions_activites.statut is
    'en_attente (défaut) / approuvee / rejetee - changé à la main après relecture dans le Table editor Supabase.';

-- RLS : écrite uniquement par functions/api/soumettre-activite.js (clé
-- secrète, côté serveur) - jamais par le navigateur. Lue uniquement par
-- Muriel (Table editor, contourne RLS) et scrapers/import_soumissions.py
-- (clé secrète). Pas de policy publique du tout : contrairement à
-- `organismes_premium`, rien ici n'est destiné à être lu par le site
-- public avant d'avoir été copié dans `activites`.
alter table public.soumissions_activites enable row level security;
