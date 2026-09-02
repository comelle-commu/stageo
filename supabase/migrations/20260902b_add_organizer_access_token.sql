-- Espace organisateur ("mon espace") par lien magique - remplace le
-- couple login/mot de passe évoqué initialement : un jeton secret unique
-- par organisme, envoyé par email (voir functions/api/admin-invite-organizer.js),
-- qui donne accès à un espace où l'organisme voit ses activités et peut
-- Booster/devenir Partenaire directement (identité déjà prouvée par la
-- possession du jeton, plus besoin de deviner via une correspondance
-- d'email - voir functions/api/create-checkout-session.js).
--
-- Réutilise organisateurs_contact plutôt qu'une nouvelle table : c'est
-- déjà "un organisme (source_key) <-> un email de contact", exactement
-- ce dont ce jeton a besoin en plus.
alter table public.organisateurs_contact
    add column if not exists access_token text unique;

comment on column public.organisateurs_contact.access_token is
    'Jeton secret longue durée ("espace organisateur") - généré par functions/api/admin-invite-organizer.js, vérifié par functions/api/organisateur-espace.js. Un organisateur qui le possède est considéré identifié, sans mot de passe.';
