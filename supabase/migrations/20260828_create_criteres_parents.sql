-- Critères de recherche laissés par un parent pour affiner les futures
-- alertes (V1 : on récolte les critères, pas encore d'envoi automatique
-- basé dessus - voir docs/ pour le plan). Une ligne par email : une
-- nouvelle soumission met à jour la précédente plutôt que d'en créer une
-- deuxième (même logique que `updateEnabled` côté Brevo pour la liste
-- d'attente simple).
create table if not exists criteres_parents (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  email text not null unique,
  -- [{"age": 6}, {"age": 9.5}] - un objet par enfant, jamais juste un
  -- tableau de nombres : laisse la place à d'autres attributs par enfant
  -- plus tard (ex. besoins spécifiques) sans migration supplémentaire.
  enfants jsonb not null,
  commune text not null,
  rayon_km integer not null default 15,
  -- Sous-ensemble de TYPE_ACTIVITE_CHOICES (voir scrapers/common.py) -
  -- tableau vide = pas de préférence, toutes les catégories conviennent.
  types_activites text[] not null default '{}'
);

alter table criteres_parents enable row level security;
-- Aucune policy publique : la fonction Cloudflare écrit avec la clé
-- secrète (contourne RLS) - même logique que `activites`/`contact_requests`.
