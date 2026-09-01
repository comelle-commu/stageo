-- Stagéo — trois ajouts additifs pour le plan d'exécution du 01/09/2026
-- (voir la note stratégique "Trouvéo, plan d'exécution") : tracking
-- propriétaire minimal, mécanique "Boost" par activité (distincte de
-- `organismes_premium` qui reste la mécanique "Partenaire", par organisme),
-- et un carnet de prospection très léger. Migration purement additive :
-- aucune table existante n'est modifiée en profondeur, aucune colonne
-- supprimée - reversible en droppant les objets créés ici, un par un.

-- ---------------------------------------------------------------------
-- 1. `events` : tracking propriétaire minimal (SEARCH_PERFORMED,
--    ACTIVITY_VIEWED, OUTBOUND_REGISTRATION_CLICK, ALERT_CREATED,
--    BOOST_CTA_CLICKED, BOOST_PURCHASED - voir functions/api/event.js).
--    Volontairement plat (jsonb) plutôt que dénormalisé : le volume est
--    encore faible, une table à 5 colonnes + jsonb suffit largement et
--    évite une migration à chaque nouvelle propriété d'événement.
--    Aucune donnée personnelle : pas d'email, pas d'IP, session_id
--    anonyme généré côté navigateur (voir assets/tracking.js).
create table if not exists public.events (
    id           bigint generated always as identity primary key,
    event_name   text not null check (event_name in (
        'SEARCH_PERFORMED',
        'ACTIVITY_VIEWED',
        'OUTBOUND_REGISTRATION_CLICK',
        'ALERT_CREATED',
        'BOOST_CTA_CLICKED',
        'BOOST_PURCHASED'
    )),
    session_id   text not null,           -- identifiant anonyme (sessionStorage), pas lié à un email
    activite_id  bigint references public.activites(id) on delete set null,
    organizer_id text,                     -- source_key (organisateur ou commune), même convention que organismes_premium
    properties   jsonb not null default '{}'::jsonb,
    created_at   timestamptz not null default now()
);

comment on table public.events is
    'Tracking propriétaire minimal (voir docs plan d''exécution 01/09/2026) - aucune donnée personnelle, session_id anonyme uniquement. Écrit exclusivement via functions/api/event.js (clé secrète), jamais accessible en écriture depuis le navigateur.';
comment on column public.events.session_id is
    'Identifiant aléatoire généré côté navigateur (sessionStorage) - jamais un email, jamais une IP, jamais un identifiant permanent.';

alter table public.events enable row level security;
-- Aucune policy publique (ni lecture ni écriture) : même logique que
-- `contact_requests` - la fonction Cloudflare écrit avec la clé secrète
-- (contourne RLS), le dashboard interne lit aussi avec la clé secrète,
-- côté serveur uniquement (voir functions/api/admin-stats.js).

create index if not exists events_name_created_idx on public.events (event_name, created_at);
create index if not exists events_activite_idx on public.events (activite_id) where activite_id is not null;
create index if not exists events_organizer_idx on public.events (organizer_id) where organizer_id is not null;

-- Purge recommandée (pas automatisée pour l'instant - à lancer à la main,
-- ou à ajouter en step optionnel de .github/workflows/scrape.yml le jour
-- où le volume le justifie) : détail au-delà de 12 mois, garder seulement
-- des agrégats plus anciens si besoin.
--   delete from public.events where created_at < now() - interval '12 months';


-- ---------------------------------------------------------------------
-- 2. `activites_boost` : mise en avant ponctuelle d'UNE activité (29€ /
--    4 semaines), distincte d'`organismes_premium` qui reste la mécanique
--    "Partenaire" (annuelle, tout l'organisme). Même esprit que
--    `organismes_premium.mis_en_avant_jusquau` (date d'expiration plutôt
--    qu'un booléen, s'éteint tout seul) mais à la maille activité, pas
--    organisme - le Boost cible un seul stage précis, pas tout le
--    catalogue d'un organisateur.
create table if not exists public.activites_boost (
    id           bigint generated always as identity primary key,
    activite_id  bigint not null references public.activites(id) on delete cascade,
    boost_jusquau date not null,
    created_at   timestamptz not null default now(),
    unique (activite_id)  -- une seule ligne de boost active par activité ; un nouvel achat met à jour la même ligne (on_conflict)
);

comment on table public.activites_boost is
    'Boost ponctuel par activité (29€/4 semaines) - voir partenaires.html "Booster une activité". Distinct de organismes_premium (Partenaire, par organisme). Alimentée à la main (Table editor) tant que le paiement reste manuel, voir docs plan d''exécution §3.';

alter table public.activites_boost enable row level security;

create policy "Lecture publique du statut boost"
    on public.activites_boost
    for select
    to anon, authenticated
    using (true);
-- Écriture réservée à la clé secrète (Table editor), comme organismes_premium.


-- ---------------------------------------------------------------------
-- 3. `organizer_prospects` : carnet de prospection très léger pour les
--    30 premiers organisateurs (voir docs plan d'exécution §12/§17) - pas
--    un CRM, juste de quoi ne pas perdre le fil entre deux relances.
create table if not exists public.organizer_prospects (
    id               bigint generated always as identity primary key,
    organizer_name   text not null,
    email            text,
    status           text not null default 'a_contacter' check (status in (
        'a_contacter', 'contacte', 'interesse', 'boost', 'partenaire', 'pas_interesse'
    )),
    first_contact_at timestamptz,
    last_contact_at  timestamptz,
    next_action_at   date,
    notes            text,
    created_at       timestamptz not null default now()
);

comment on table public.organizer_prospects is
    'Carnet de prospection des premiers organisateurs (voir docs plan d''exécution §12) - alimenté et suivi à la main via Table editor, pas de CRM.';

alter table public.organizer_prospects enable row level security;
-- Aucune policy publique : lu/écrit uniquement via Table editor (clé
-- secrète), jamais depuis le navigateur - données de prospection, pas
-- destinées à être publiques.


-- ---------------------------------------------------------------------
-- 4. `contact_requests.offre` : distingue quel CTA a été cliqué (Boost /
--    Partenaire / générique) sur partenaires.html, pour trier le suivi
--    manuel sans devoir relire chaque message. Colonne additive,
--    reversible (drop column if exists).
alter table public.contact_requests
    add column if not exists offre text;

comment on column public.contact_requests.offre is
    'Offre concernée si la demande vient d''un CTA précis ("boost", "partenaire") - null pour les demandes génériques (formulaire "être recontacté").';
