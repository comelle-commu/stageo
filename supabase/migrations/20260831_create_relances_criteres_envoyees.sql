-- Anti-doublon pour la relance "vous n'avez pas encore précisé vos
-- critères" (voir scrapers/relance_criteres.py) : une ligne = "cet email
-- a déjà reçu la relance", pour n'envoyer qu'UNE seule fois même si le
-- job tourne plusieurs fois - contrairement à alertes_envoyees (une ligne
-- par activité), ici une ligne par email suffit : la relance ne se répète
-- jamais, qu'elle ait fonctionné ou non.

create table if not exists public.relances_criteres_envoyees (
    email    text primary key,
    sent_at  timestamptz not null default now()
);

comment on table public.relances_criteres_envoyees is
    'Emails ayant déjà reçu la relance "critères non remplis" (voir scrapers/relance_criteres.py) - évite de relancer deux fois la même personne.';

-- Pas de policy publique : table technique interne, lue/écrite uniquement
-- par le job de relance via la clé secrète (même logique qu'alertes_envoyees).
alter table public.relances_criteres_envoyees enable row level security;
