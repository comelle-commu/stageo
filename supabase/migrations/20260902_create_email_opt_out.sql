-- Désinscription email : source unique de vérité pour "cette adresse ne
-- veut plus recevoir d'emails Trouvéo", consultée par criteres_alertes.py,
-- relance_criteres.py et relance_organisateurs.py avant tout envoi.
--
-- Alimentée uniquement par functions/api/desinscription.js (lien "un clic"
-- présent dans chaque email transactionnel) via la clé secrète - jamais
-- lue ni écrite par le navigateur, donc pas de policy anon.

create table if not exists public.email_opt_out (
  email text primary key,
  created_at timestamptz not null default now()
);

alter table public.email_opt_out enable row level security;
