-- Deux usages regroupés dans une seule table (volume attendu faible au
-- départ, pas besoin de deux tables séparées pour l'instant) :
--  - "organisme" : quelqu'un signale un organisme/une commune pas encore
--    sur Trouvéo (URL de leur site, éventuellement son email pour le tenir
--    au courant).
--  - "premium" : un organisme ou un commerce local demande à être
--    recontacté au sujet d'une mise en avant payante (partenaire officiel,
--    encart publicitaire).
create table if not exists contact_requests (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  type text not null check (type in ('organisme', 'premium')),
  email text,
  url text,
  message text
);

alter table contact_requests enable row level security;
-- Aucune policy publique : la fonction Cloudflare écrit avec la clé secrète
-- (contourne RLS), personne ne peut lire/écrire directement depuis le
-- navigateur - même logique que la table `activites`.
