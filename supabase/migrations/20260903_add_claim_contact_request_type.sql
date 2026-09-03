-- Ajoute "claim" à contact_requests.type : quelqu'un tente de revendiquer
-- l'accès à une activité (bouton "C'est votre activité ? Gérez-la" sur
-- activites.html) mais son email ne correspond à aucun contact/domaine déjà
-- connu pour cette activité - voir functions/api/organisateur-claim.js.
-- Contrairement à "organisme"/"premium", toujours accompagnée d'une
-- notification email immédiate (voir la fonction) : une personne qui
-- attend un accès ne doit pas poireauter jusqu'à ce que Muriel pense à
-- consulter la table.
alter table public.contact_requests drop constraint if exists contact_requests_type_check;
alter table public.contact_requests add constraint contact_requests_type_check
    check (type in ('organisme', 'premium', 'claim'));
