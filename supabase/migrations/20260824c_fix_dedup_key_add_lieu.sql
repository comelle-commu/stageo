-- Trouvéo — corrige la clé de dédoublonnage pour inclure `lieu` ET
-- `lien_source`.
--
-- Bug découvert lors du premier import ADEPS (361 activités scrapées) :
-- l'ADEPS réutilise le même nom générique de stage (ex. "Zap Multisports")
-- pour la même semaine dans plusieurs centres différents (ex. Jambes,
-- Neufchâteau, Spa - 3 activités bien distinctes). L'ancienne clé
-- (commune_slug, nom_activite, dates) - correcte pour les scrapers
-- communaux, où une activité = un lieu implicite (la commune elle-même) -
-- les fusionnait à tort en une seule ligne : 154 activités ADEPS réelles
-- ont été silencieusement perdues au premier import avant que ce bug ne
-- soit repéré (361 scrapées -> seulement 207 conservées après
-- dédoublonnage).
--
-- `lieu` seul ne suffit pas non plus : l'ADEPS propose aussi le même
-- stage/semaine/lieu en plusieurs tranches d'âge distinctes (ex.
-- "Multisports" à Mons la même semaine pour 6-8 ans ET pour 9-12 ans,
-- deux pages/activités différentes). `lien_source` (l'URL de la fiche
-- individuelle) est en revanche garanti unique par activité sur ADEPS/Cap
-- Sciences - vérifié : plus aucune collision une fois ajouté à la clé.
-- Pas de risque pour les scrapers communaux où `lien_source` est parfois
-- partagé entre plusieurs activités d'une même page (ex. Ans) : `nom` et
-- `dates` les distinguent déjà, `lien_source` ne fait qu'affiner.
--
-- `lieu` est renseigné (NOT NULL) sur toutes les sources, y compris les
-- communes (jamais vide, même quand la valeur exacte n'est pas connue -
-- voir ex. Ans : "Site communiqué au 1er jour d'inscription...") - sûr à
-- ajouter à la clé partout, ça ne fait que la rendre plus précise.

alter table public.activites
    drop constraint if exists activites_dedup_key;

alter table public.activites
    add constraint activites_dedup_key unique (commune_slug, nom_activite, dates, lieu, lien_source);
