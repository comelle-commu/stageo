-- Stagéo — deux formules de mise en avant (voir partenaires.html) :
-- "Basique" (position prioritaire + encadré orange) et "Complet" (+ badge
-- "Le choix de Trouvéo" + descriptif détaillé). organismes_premium doit
-- déjà exister (migration 20260831b) - celle-ci ajoute juste la colonne qui
-- distingue les deux formules.
alter table public.organismes_premium
    add column if not exists mise_en_avant_complete boolean not null default false;

comment on column public.organismes_premium.mise_en_avant_complete is
    'false (défaut) = formule Basique (position + encadré orange seulement). true = formule Complet (+ badge "Le choix de Trouvéo" + description_longue affichés). Indépendant de `verifie` (badge "Organisme vérifié"), même si les deux sont vendus ensemble dans la formule Complet.';
