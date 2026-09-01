-- Stagéo — relance automatique d'un organisme dont toutes les activités
-- connues sont passées ("vos stages sont terminés, envoyez le prochain
-- programme") - voir scrapers/relance_organisateurs.py.
--
-- `organisateurs_contact` : email de contact par organisateur (source_key,
-- même convention que scrapers/supabase_client.PLATEFORME_SOURCE et
-- organismes_premium). Alimentée automatiquement à chaque soumission via
-- soumettre-activite.html (voir scrapers/import_soumissions.py), et à la
-- main pour un organisme qui a envoyé ses infos autrement (ex. par email -
-- voir docs, cas de la Société archéologique de Namur le 01/09/2026).
-- Sans ligne ici, pas de relance possible : la plupart des ~50 sources
-- scrapées n'ont jamais communiqué d'email de contact structuré.
create table if not exists public.organisateurs_contact (
    source_key    text primary key,
    contact_email text not null,
    updated_at    timestamptz not null default now()
);

comment on table public.organisateurs_contact is
    'Email de contact par organisateur (source_key = organisateur ou commune) - utilisé par relance_organisateurs.py pour savoir qui relancer. Alimentée automatiquement par import_soumissions.py, ou à la main.';

-- `relances_organisateurs_envoyees` : anti-doublon. `dernier_ajout_connu`
-- retient le plus récent `created_at` parmi les activités de cet
-- organisateur AU MOMENT de la relance - permet de renvoyer une nouvelle
-- relance si l'organisme a soumis une nouvelle activité entre-temps (elle
-- aussi finie par expirer) sans le harceler chaque semaine tant qu'il n'a
-- rien soumis de neuf.
create table if not exists public.relances_organisateurs_envoyees (
    source_key          text primary key,
    sent_at              timestamptz not null default now(),
    dernier_ajout_connu  timestamptz not null
);

comment on table public.relances_organisateurs_envoyees is
    'Anti-doublon pour relance_organisateurs.py - une relance par "creux" (toutes les activités de l''organisme passées), pas une par run tant qu''il n''a rien soumis de neuf depuis.';

-- RLS : pas de policy publique sur les deux tables - lues/écrites
-- uniquement par les scripts via la clé secrète (Table editor Supabase
-- pour Muriel), même logique que organismes_premium/soumissions_activites.
alter table public.organisateurs_contact enable row level security;
alter table public.relances_organisateurs_envoyees enable row level security;
