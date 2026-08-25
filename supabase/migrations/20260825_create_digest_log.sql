-- Trouvéo — table `digest_log` : historique des emails hebdomadaires
-- envoyés à la liste d'attente Brevo (nouvelles activités détectées depuis
-- le dernier envoi). Voir scrapers/brevo_digest.py et
-- docs/email-hebdomadaire-2026-08-25.md.
--
-- Sert aussi de référence : le prochain envoi ne regarde que les
-- activités dont `premiere_apparition` est postérieure au `sent_at` le
-- plus récent ici.

create table if not exists public.digest_log (
    id            bigint generated always as identity primary key,
    sent_at       timestamptz not null default now(),
    nb_nouvelles  integer not null,
    statut        text not null,  -- INIT / VIDE / OK / ERREUR
    details       text,
    brevo_campaign_id bigint
);

comment on table public.digest_log is
    'Historique des envois de l''email hebdomadaire "nouvelles activités" à la liste d''attente Brevo.';

-- Pas de politique RLS publique : cette table est un journal technique
-- interne, écrit/lu uniquement via la clé secrète (service role, qui
-- contourne RLS) - contrairement à `activites`, elle n''a pas vocation à
-- être lue depuis le site public.
alter table public.digest_log enable row level security;
