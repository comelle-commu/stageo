-- Stagéo — table `organismes_premium` : statut "mise en avant" / "organisme
-- vérifié" d'un organisme, décidé le 31/08/2026 (voir
-- docs/partenariats-premium-2026-08-31.md et partenaires.html, section
-- "Ce que nous vous proposons").
--
-- Clé = `source_key`, la même notion que scrapers/supabase_client.py
-- (`source_key = activite.organisateur or activite.commune`) : une ligne par
-- organisme/commune, pas par activité individuelle - le statut s'applique
-- automatiquement à toutes les activités de cet organisme, y compris les
-- nouvelles ajoutées par le scrape hebdomadaire suivant, sans qu'il faille
-- re-flaguer chaque ligne à la main. Exemples de source_key valides :
-- "Ans", "Neupré" (scrapers communaux, = le nom de commune tel qu'utilisé
-- dans PLATEFORME_SOURCE), "ADEPS", "Les Ateliers 04" (organismes, = le
-- champ `organisateur`).
create table if not exists public.organismes_premium (
    source_key         text primary key,
    nom_affichage       text,             -- optionnel, nom lisible si source_key n'est pas assez clair tel quel
    mis_en_avant_jusquau date,            -- position prioritaire + badge "Le choix de Trouvéo" tant que non expiré
    description_longue text,              -- descriptif enrichi affiché sur les fiches (mise en avant)
    verifie             boolean not null default false, -- badge "Organisme vérifié"
    logo_url            text,             -- affiché à côté du nom si verifie = true
    lien_inscription    text,             -- lien "S'inscrire" direct si verifie = true
    updated_at          timestamptz not null default now()
);

comment on table public.organismes_premium is
    'Statut mise en avant / organisme vérifié par organisme (source_key = organisateur ou commune, même convention que supabase_client.PLATEFORME_SOURCE) - voir docs/partenariats-premium-2026-08-31.md. Mis à jour manuellement, pas par les scrapers.';
comment on column public.organismes_premium.mis_en_avant_jusquau is
    'Date d''expiration plutôt qu''un simple booléen : s''éteint tout seul si un renouvellement n''a pas été payé, plutôt que de rester actif indéfiniment par oubli.';

-- RLS : lu directement par activites.html (clé anon) pour l'affichage
-- (position prioritaire, badges) - mais jamais écrit depuis le navigateur.
-- Écriture réservée à la clé secrète (Supabase Table editor ou script),
-- comme pour `activites`.
alter table public.organismes_premium enable row level security;

create policy "Lecture publique du statut premium"
    on public.organismes_premium
    for select
    to anon, authenticated
    using (true);
