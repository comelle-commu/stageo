# Ratissage province de Luxembourg (31/08/2026)

## Contexte

Première session dédiée à la province de Luxembourg (la plus rurale et la
moins peuplée des provinces wallonnes, ~44 communes) - contrairement à
Liège, qui avait déjà eu deux sessions de ratissage
(`docs/ratissage-province-liege-2026-08-28.md`,
`docs/ratissage-liege-supplement-2026-08-31.md`), rien n'avait encore été
fait ici au-delà des deux communes ajoutées lors de l'élargissement
initial (`docs/elargissement-provinces-2026-08-24.md`). Objectif : la
couverture la plus honnête possible, sans forcer des scrapers sur des
pages qui n'ont rien de fiable à donner - le rendement attendu est
volontairement plus faible qu'à Liège ou en Brabant wallon.

**Résultat : 5 nouveaux scrapers construits et testés** (Virton,
Meix-devant-Virton, Hotton, La Roche-en-Ardenne, Vaux-sur-Sûre), plus la
confirmation que 3 communes étaient déjà couvertes (Arlon, Bastogne,
Aubange) et que 6 autres le sont indirectement via `adsl_stages.py` (voir
section B). `SCRAPERS` passe de 46 à 51 entrées actives.

## A. Déjà couvertes avant cette session (confirmé, pas de doublon créé)

- **Arlon** (`arlon.py`) - iMio, page unique en prose (printemps + été).
- **Bastogne** (`bastogne.py`) - iMio, programmes CPAS structurés.
- **Aubange** (`aubange.py`) - plateforme "LetsGoCity"/Nuxt (voir section
  D), 2 activités génériques codées en dur (détente + printemps
  2026-2027 uniquement - le projet d'accueil communal exclut
  explicitement l'hiver et ne mentionne pas l'automne).

## B. Déjà couvertes indirectement via ADSL Stages

`adsl_stages.py` (organisme privé, déjà scrapé pour Liège/Namur/Hainaut/
Brabant wallon) filtre par région ADSL - 6 de ces régions sont en province
de Luxembourg et étaient déjà dans `REGIONS` avant cette session : **Arlon**
(id 70), **Bertrix** (30), **Etalle** (41), **Habay-la-Neuve** (75),
**Libramont** (78), **Rouvroy** (76). Confirmé en lisant `adsl_stages.py` -
aucune de ces communes n'a donc été retravaillée avec un scraper communal
dédié (Bertrix et Etalle en particulier : leurs propres sites communaux ont
été vérifiés - voir section D - et n'apportaient rien de plus).

## C. Construits cette session (5 scrapers)

### Virton — `virton.py` (iMio)

Page unique en prose (même style qu'Arlon/Mons) : "Des semaines de plaines
sont organisées aux congés de printemps, d'été et d'automne... du 4 au 8
mai 2026, du 20 juillet au 7 août 2026 (3 semaines), **du 19 au 23 octobre
2026**." Tarif dégressif par enfant (12,70€/7,40€/5,30€), âge 2,5-12 ans,
lieu unique (école communale de Chenois-Latour). 3 activités extraites.

### Meix-devant-Virton — `meix_devant_virton.py` (iMio)

Petite commune de Gaume (~2500 hab.) à la page la plus riche trouvée cette
session : un calendrier scolaire complet (dates exactes de chaque congé
2026-2027) séparé d'une liste "Ce qui est proposé aux enfants" organisée
par congé (nom du stage, âge, durée, lieu, parfois "en attente de
confirmation"). Le scraper relie les deux parties par le nom du congé.
10 activités extraites (ASBL "Les petits cornichons", EVA² couture, Club
d'Escrime gaumais, ASBL Crépuscule équitation...) sur 4 congés (automne,
hiver, détente, printemps - l'été est exclu, pas de date de fin donnée
pour cette période sur la page).

### Hotton, La Roche-en-Ardenne, Vaux-sur-Sûre — activités génériques par congé

Trois communes avec une page vitrine qui confirme explicitement
l'organisation de plaines à **chaque** congé scolaire (dont l'automne),
mais sans donner de date calendaire précise par édition - même situation
que Aubange (déjà dans le dépôt avant cette session). Plutôt que de
forcer un parseur sur une structure prose qui n'existe pas, chaque module
code en dur une activité par congé FWB 2026-2027 confirmé comme organisé
(tarif/âge/lieu/contact réels tirés de la page) :

- **Hotton** (`hotton.py`) - plateforme "LetsGoCity"/Nuxt (voir section
  D). 5 périodes annoncées, agréées ONE ; 4 reprises (l'été mi-juillet/
  mi-août est déjà passé). "Une semaine" par congé, sans préciser
  laquelle des deux quand le congé en compte deux - la plage complète du
  congé est donnée avec une note explicite plutôt qu'un choix arbitraire.
- **La Roche-en-Ardenne** (`la_roche_en_ardenne.py`) - site propre (pas
  iMio, `Crawl-delay: 10`). Le "Projet d'accueil stages plaines 2026-2027"
  (PDF) confirme "2 semaines" par congé, ce qui correspond exactement aux
  deux semaines FWB de chaque congé - pas d'ambiguïté ici contrairement à
  Hotton.
- **Vaux-sur-Sûre** (`vaux_sur_sure.py`) - iMio. Page confirmant "chaque
  congé scolaire", tranche d'âge plus large (2,5-15 ans). Un calendrier
  PDF existe mais c'est une affiche graphique (grille jour par jour) sans
  légende exploitable en texte natif - non utilisé, voir docstring du
  module.

## D. Couverture iMio de la province

Méthode : suivre la redirection du `robots.txt` de chaque commune (même
méthode que le ratissage Liège) - toutes les communes iMio redirigent vers
`static.imio.be/robots.txt` (`Crawl-delay: 120`, déjà géré par
`common.IMIO_DOMAINS`). Les **44 communes de la province** ont été testées
(liste complète, y compris Arlon/Bastogne/Aubange déjà connues) : **28 sont
iMio**, dont Arlon et Bastogne déjà connues avant cette session - soit
**26 nouvelles confirmations** :

Attert, Martelange, Bertogne, Gouvy, Houffalize, Sainte-Ode,
Vaux-sur-Sûre✅, Erezee, Nassogne, Rendeux, Bouillon, Daverdisse,
Herbeumont, Neufchateau, Paliseul, Tellin, Vresse-sur-Semois, Wellin,
Florenville, Habay, Meix-devant-Virton✅, Musson, Rouvroy, Saint-Leger,
Tintigny, Virton✅ (✅ = scraper dédié construit cette session).

Toutes ajoutées à `common.IMIO_DOMAINS` (Crawl-delay correct dès qu'une
future session les scrape), même celles sans scraper actif pour l'instant.

### Widget "Agenda Omnia" (swiper) - 12 communes enregistrées dans `agenda_omnia.py`

Comme pour Liège, plusieurs communes iMio embarquent le carrousel
"Agenda"/swiper partagé sur leur page d'accueil. Sur les 26 communes iMio
testées, **12 ont le widget** (au moins un `swiper-slide` présent) :
Attert, Martelange, Bertogne, Sainte-Ode, Erezee, Nassogne, Herbeumont,
Neufchateau, Tellin, Wellin, Musson, Rouvroy. **Aucune n'a de stage
catégorisé "Stages et cours" au 31/08/2026** - toutes enregistrées quand
même dans `agenda_omnia.COMMUNES`, le run hebdomadaire les réextraira
automatiquement dès publication (même logique que pour Liège). Piège
vérifié et déjà correctement géré par le filtre existant : Neufchâteau a
un item catégorisé "Stages et cours" mais dont la fiche détail donne
`Event type: Événementiel` (formation au permis de conduire, pas une
activité enfant) - exclu par le filtre `event_type.startswith("Activité")`
déjà en place, sans changement de code nécessaire.

Les 14 autres communes iMio n'ont pas le widget (Gouvy, Houffalize,
Rendeux, Bouillon, Daverdisse, Paliseul, Vresse-sur-Semois, Florenville,
Habay, Saint-Leger, Tintigny - 0 slide - Virton/Meix-devant-Virton/
Vaux-sur-Sûre ont bien le widget mais un scraper dédié plus précis a été
préféré, voir section C) - volontairement absentes d'`agenda_omnia.py`,
rien à en tirer par cette méthode.

## E. Plateforme "LetsGoCity"/Nuxt - deuxième famille technique après iMio

Découverte notable de cette session : plusieurs communes de la province
tournent sur une plateforme partagée différente d'iMio, un SSR Nuxt.js
identifiable par ses assets `/_nuxt/*.js` et sa police maison
`"letsgocity"` - **même famille technique que Neupré/Visé (Liège)**, déjà
documentée dans
`docs/investigation-technique-elargissement-communes-2026-08-24.md`, mais
un vendor différent ("enpoche.be" pour Neupré/Visé vs "LetsGoCity" ici -
même comportement `soft-404` du `/robots.txt`, donc même traitement légal
: absence de fichier réel = pas de restriction technique déclarée).
Confirmée sur **Aubange** (déjà scrapée), **Hotton** (scrapée cette
session), **Messancy, Fauvillers, Manhay, Tenneville, Bertrix, Etalle**.

Seules les pages "information" statiques (`/‹commune›/information/‹slug›`)
sont rendues côté serveur ; la page d'accueil et les "actualités" sont du
pur client-side (texte vide en HTML brut) - **non vérifiables dans ce bac
à sable réseau** (Playwright bloqué ici, comme documenté pour Burdinne/
Plombières côté Liège) : à revérifier sur GitHub Actions.

## F. Investigué et écarté (impasses documentées, par commune/piste)

| Commune/piste | Raison |
|---|---|
| **Messancy** (LetsGoCity) | Pages "information" réelles trouvées (`vacances-d-ete`, `vacances-de-printemps`) mais toutes deux déjà passées au 31/08/2026 ; la page automne dédiée n'existe pas encore (slug testé = shell vide) ; l'actualité "Stages d'automne" existe mais est en pur client-side (JS bloqué dans ce bac à sable) - à revérifier sur GitHub Actions |
| **Fauvillers** (LetsGoCity) | Seule page "information" trouvée = "ONE & Baby-Service" (info générale petite enfance, hors sujet) ; aucune page stages/plaines localisée |
| **Manhay** (LetsGoCity) | Page "Plaines d'été" trouvée mais ne décrit QUE l'été (texte : "Retrouvez le récapitulatif..."), aucun lien PDF exploitable trouvé, rien sur l'automne |
| **Tenneville** (LetsGoCity) | Page "Plaines de vacances" trouvée mais explicitement limitée à l'été ("Durant les vacances d'été... 3 semaines"), aucune mention d'un autre congé |
| **Bertrix**, **Etalle** (LetsGoCity) | Aucune page "information" stages trouvée sous leur préfixe ; déjà couvertes via ADSL Stages (section B) - pas approfondi davantage |
| **Durbuy** | WordPress, robots.txt ouvert ; recherche superficielle seulement (mention vague de "stages juillet/août"), pas de page dédiée avec dates identifiée cette session - à revérifier |
| **Saint-Hubert** | WordPress, robots.txt ouvert ; seule page trouvée = "Activités - Accueil extrascolaires" (garderie avant/après école, pas des stages) ; plaines communales confirmées par recherche mais UNIQUEMENT à Noël/Carnaval/Pâques/juillet - rien pour l'automne |
| **Libin** | Page dédiée `/stages` trouvée mais explicitement obsolète ("STAGES 2018", dernière mise à jour visible 2018-2019) - abandonnée, pas mise à jour depuis des années |
| **Rendeux** (iMio) | Page "Plaines et stages" = simple répertoire d'organisateurs (contacts), pas de programme daté ; le seul PDF calendrier lié date de l'année scolaire **2022-2023** (obsolète) |
| **Bouillon** (iMio) | Actualité "Plaines communales à Bouillon" bloquée par un mur de connexion e-guichet (même symptôme que Namur, `docs/elargissement-provinces-2026-08-24.md`) ; autre actualité trouvée explicitement "il n'y aura pas de plaines communales" pour la période testée |
| **Florenville** (iMio) | Plaines communales confirmées mais UNIQUEMENT printemps/hiver/été (2,5-8 ans) - aucune mention d'automne trouvée dans les événements listés |
| **Léglise** (iMio) | `robots.txt` contradictoire et ambigu (`Allow: /` immédiatement suivi de `Disallow: /`) - traité par prudence comme restriction floue, non scrapé sans clarification |
| **Chiny** | Site entièrement hors ligne (redirige vers `offline.html`, "307 Temporary Redirect" reproductible) - impasse technique, à revérifier plus tard |
| **Martelange** (iMio) | "Calendrier des stages" trouvé mais daté **2025-2026** (Toussaint 2025, déjà passée) ; pas encore de version 2026-2027 publiée |
| **Habay**, **Saint-Léger**, **Tintigny** | iMio confirmé, widget Omnia absent, aucune page stages/plaines datée trouvée en recherche superficielle - déjà couvertes en partie via ADSL (Habay-la-Neuve) ou non approfondies faute de temps |
| **my.one.be** | Déjà exclu (CGU interdisent explicitement le scraping) - confirmé dans `docs/investigation-technique-2026-08-24.md`, non ré-investigué |

## G. Piste forte pour la prochaine session : Marche-en-Famenne

`enfance-jeunesse.marche.be` (sous-domaine dédié, robots.txt ouvert,
`Allow: /`) est une **vraie plateforme de réservation structurée** (cartes
avec nom/âge/dates/prix, comme ADSL Stages) qui liste déjà les clubs et
activités à l'année de Marche-en-Famenne. Le texte de la page annonce
explicitement : **"Stages et plaines d'automne - Offres visibles à partir
du 9 septembre. Inscriptions à partir du 14 septembre."** Rien d'exploitable
au 31/08/2026 (page pas encore publiée), mais c'est un signal de date de
publication concret et proche - la piste la plus prometteuse pour la
prochaine session plutôt qu'une commune "peut-être un jour publiée".

## Bilan chiffré

- **5 nouveaux scrapers** construits et testés : Virton, Meix-devant-Virton,
  Hotton, La Roche-en-Ardenne, Vaux-sur-Sûre.
- **24 activités réelles** extraites au total pour cette session (3 Virton
  + 10 Meix-devant-Virton + 4 Hotton + 3 La Roche-en-Ardenne + 4
  Vaux-sur-Sûre), couvrant l'automne 2026 et souvent au-delà (hiver/
  détente/printemps 2027).
- **`SCRAPERS` passe de 46 à 51 entrées actives** dans `run_all.py`.
- **28 communes iMio confirmées** dans la province sur les 44 testées
  (l'intégralité de la province) - 26 nouvelles confirmations ajoutées à
  `common.IMIO_DOMAINS` ; **12 d'entre elles** ont le widget Agenda Omnia
  (enregistrées dans `agenda_omnia.py`, 0 activité pour l'instant).
- **3 communes déjà couvertes** avant cette session (Arlon, Bastogne,
  Aubange) et **6 autres couvertes indirectement** via `adsl_stages.py`
  (Arlon, Bertrix, Etalle, Habay-la-Neuve, Libramont, Rouvroy).
- **~15 pistes investiguées et honnêtement écartées** cette session (voir
  section F), la plupart pour absence de programme d'automne publié,
  page obsolète, ou blocage technique (JS, e-guichet, site hors ligne).

## Prochaines étapes recommandées

1. **Marche-en-Famenne** (`enfance-jeunesse.marche.be`) - revenir dès le
   9-14 septembre 2026, date de publication annoncée par la plateforme
   elle-même (voir section G).
2. **Messancy** - revérifier sur GitHub Actions (Playwright complet) : la
   page "information" automne existe probablement déjà mais son
   actualité correspondante est en JS pur, bloqué dans ce bac à sable.
3. Revérifier début septembre les communes iMio sans widget Omnia et sans
   page trouvée cette session (Habay, Saint-Léger, Tintigny, Gouvy,
   Houffalize, Daverdisse, Paliseul, Vresse-sur-Semois) - plusieurs
   communes publient leur programme d'automne courant septembre, comme
   observé côté Liège.
4. **Martelange** - recalendrier "2026-2027" à surveiller (le
   "2025-2026" actuel deviendra obsolète, mais la structure de page est
   déjà connue et directement réutilisable).
5. **Durbuy**, **Saint-Hubert** - recherche superficielle seulement cette
   session faute de temps, à approfondir.
6. Republier ce document mis à jour à chaque session de ratissage sur
   cette province, comme fait pour Liège.
