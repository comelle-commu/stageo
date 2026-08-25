-- Ajoute le type d'activite (Sport / Art & creativite / Sciences & nature /
-- Langues / Multi-activites), pour permettre un filtre par type sur
-- /activites. Valeur par defaut "Multi-activites" pour les lignes
-- existantes - elles seront recalculees correctement au prochain run du
-- scraper (upsert), qui assigne desormais explicitement ce champ via
-- common.classify_type().
alter table activites
  add column if not exists type_activite text not null default 'Multi-activités';
