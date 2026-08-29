-- Anti-doublon pour les alertes personnalisées (voir scrapers/criteres_alertes.py) :
-- une ligne = "cette activité a déjà été signalée à cet email", pour ne
-- jamais renvoyer deux fois la même activité à la même famille même si le
-- job tourne plusieurs fois (ex. après un scrape supplémentaire en pleine
-- période de vacances).

create table if not exists public.alertes_envoyees (
    id           bigint generated always as identity primary key,
    email        text not null,
    activite_id  bigint not null references public.activites (id) on delete cascade,
    sent_at      timestamptz not null default now(),

    constraint alertes_envoyees_dedup unique (email, activite_id)
);

comment on table public.alertes_envoyees is
    'Historique des activités déjà signalées par email à chaque parent (voir scrapers/criteres_alertes.py) - évite les doublons entre deux runs du job d''alertes.';

-- Pas de policy publique : table technique interne, lue/écrite uniquement
-- par le job d'alertes via la clé secrète (même logique que digest_log).
alter table public.alertes_envoyees enable row level security;
