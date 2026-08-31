# Ratissage province de Liège — supplément (31/08/2026)

## Contexte

Demande explicite de la fondatrice : « J'aimerais avoir 10-12 organismes en
plus en province de Liège ». Cette session reprend le travail des deux
précédentes (`docs/ratissage-province-liege-2026-08-28.md`,
`docs/paysage-organismes-2026-08-24.md`,
`docs/investigation-technique-organismes-2026-08-24.md`) — déjà lues avant
de commencer, pour ne pas retomber sur les mêmes pistes déjà tranchées
(Réseau IDée, filous.be, SportFinder, iClub/CSM historique, Le Moderne,
Soumagne, Malmedy/Verlaine/Dalhem/Wanze, les ~20 communes jamais vérifiées
maintenant closes...).

**Résultat honnête : 4 nouveaux organismes construits et testés** (3
modules de scraper, un couvrant 2 organismes via une plateforme partagée),
en dessous de la fourchette 10-12 demandée. La province de Liège avait déjà
été ratissée en profondeur lors des deux sessions précédentes — la plupart
des pistes évidentes (clubs de tennis/équitation, écoles de cirque/danse,
centres nature, communes jamais vérifiées) sont soit déjà couvertes, soit
sans programme Toussaint 2026 encore publié, soit hors périmètre
géographique. Voir section "Rejetés" pour le détail de chaque piste
écartée honnêtement plutôt que forcée.

## A. Ajoutés cette session (4 organismes, 3 modules)

### 1. Le CFS asbl — `scrapers/cfs.py` (16 activités : Awans, Huy, Verlaine)

Piste de départ : `lecfs.be`, déjà repérée mais jamais vérifiée dans
`docs/paysage-organismes-2026-08-24.md` ("Le CFS — Brabant wallon,
Bruxelles, Liège"). Sa page catalogue (`/stages/activites/`) n'affiche
qu'un intitulé/tranche d'âge/région générique par carte — mais chaque carte
ouvre un modal dont le bouton "Inscription" pointe vers
`www12.iclub.be/myiclub3_CFS_register.asp?ClubID=559` : **Le CFS utilise la
même plateforme MyiClub que Sport Fun Activ'/Royal Léopold/RRC Bruxelles**
déjà intégrée via `iclub.py`, mais dans une variante UI différente
(formulaire JS + API JSON dédiée `AjaxGetCFS.asp`, pas la page HTML
`register.asp?action=Search` directement parseable des 3 autres clubs) —
d'où un module séparé.

L'API JSON publique (`GET AjaxGetCFS.asp?Action=Resultat&ClubID=559&
Categorie=4&Page=N`, sans session ni auth) donne accès à tous les
évènements "Vacances scolaires" du club, toutes régions confondues (349
évènements au total). Sur les 33 lieux distincts observés, seuls 3 sont en
province de Liège : **Awans, Verlaine, Huy** (Hall Omnisports / École
d'Agriculture) — les ~30 autres (Brabant wallon, Bruxelles) sont
volontairement exclus du filtre (`LIEUX_LIEGE`), hors périmètre de ce
ratissage.

Légal : `robots.txt` de `www12.iclub.be` absent (404, comme les autres
sous-domaines iClub déjà vérifiés) — aucune restriction déclarée.
`robots.txt` de `lecfs.be` lisible et ouvert (Jekyll standard) ; ses
"Conditions générales" ne contiennent aucune clause anti-scraping.

### 2 & 3. StageVacances (Ligue des familles) — `scrapers/stagevacances.py`

Répertoire national multi-organismes découvert en creusant
`pour-nos-enfants.be`. Le site vitrine (`stagevacances.be`, SPA Nuxt) ne
rend aucune donnée réelle en HTML brut, mais son API publique
(`api.stagevacances.be/camps`, backend Cockpit CMS, sans auth) renvoie la
totalité des fiches jamais publiées sur la plateforme — ~2300 au
31/08/2026, toutes régions/années confondues.

Après un filtrage nécessairement strict pour rester honnête :
- **Localisation** : `location` est presque toujours un simple code postal
  (parfois avec adresse complète) — jamais un nom de commune directement
  exploitable. Construit à la main une table `POSTAL_COMMUNE` (~55 codes
  "4xxx" effectivement vus dans le jeu de données → leur commune officielle
  de la province de Liège, vérifiée individuellement par recherche — voir
  le code pour le détail, aucun mapping public fiable trouvé).
- **Fraîcheur** : la quasi-totalité des ~500 fiches "4xxx" sont en fait des
  stages **passés** (jusqu'à 2022) restés `moderation=Published`
  (`keep_published: true` côté organisme — un choix délibéré, pas un bug).
  Seul `period_until` dans le futur est retenu, plus un garde-fou
  (`_MAX_PERIOD_DAYS=60`) qui écarte les fiches "bannière publicitaire" à
  période absurdement large (une bannière Réseau IDée trouvée avec une
  "période" de 2023 à 2029, clairement pas un vrai stage daté — cohérent
  avec l'exclusion déjà connue de Réseau IDée, robots.txt bloque ClaudeBot
  sur son propre site).
- **Organisme** : `organisator` ne fournit quasiment jamais de nom
  structuré (juste un `_id` Mongo) — aucun endpoint public trouvé pour le
  résoudre (`/organisators`, `/users`... tous 404 ; seul `/themes` existe).
  Noms déduits à la main du texte de description pour les organismes
  identifiés (`ORGANISATEURS`, à enrichir à chaque session comme `CLUBS`
  dans `iclub.py`) ; un organisme pas encore identifié n'est **pas perdu
  silencieusement** — un nom de repli lisible est dérivé du domaine de son
  `info_url` plutôt que d'inventer ou d'ignorer.

Après ce filtrage honnête, il ne reste que **5 activités réelles pour
Toussaint 2026** (le reste écarté ci-dessus) — mais **2 organismes tout à
fait nouveaux** :
- **Centre Culturel de Theux** (3 stages : Histoires enchantées 3-5 ans,
  Promenons-nous dans les bois 6-9 ans, Rap & création musicale 9-14 ans —
  du 19 au 23 et du 26 au 30 octobre 2026, 55-90€, inscription
  `centreculturel@theux.be` / `www.cctheux.be`).
- **Académie Tennis Padel Waremmien (ATPW)** (stage tennis/padel, 2
  semaines de Toussaint, `atpwaremmien@gmail.com`).

La Ferme des Enfants de Liège apparaît aussi dans le flux (déjà couverte
par `ferme_des_enfants.py`) — exclue explicitement pour éviter un doublon
(`ORGANISATEURS_EXCLUS`).

Légal : `robots.txt` de `www.stagevacances.be` ouvert (`Disallow:` vide),
celui de `api.stagevacances.be` absent (404). "Disclaimer" lu en entier :
aucune clause sur le scraping (juste du RGPD standard sur les comptes
utilisateurs).

**Ce module continuera à détecter automatiquement tout nouvel organisme**
qui publierait sur la plateforme en province de Liège, sans changement de
code (même logique que `agenda_omnia.py` pour les communes iMio) — le
volume actuel modeste (5 activités) n'est donc probablement qu'un point de
départ, pas un plafond.

### 4. Le Fagotin — `scrapers/fagotin.py` (5 activités, Stoumont)

Parc animalier/nature (Route de l'Amblève, Stoumont) trouvé en recherchant
spécifiquement les organismes nature de la province. Page WordPress
statique très propre : 5 stages réels et datés pour l'Automne 2026 (2
semaines, tranches d'âge 3-5/6-10/11-15 ans, thèmes différents chaque
semaine), chacun avec son propre lien de réservation individuel
(`bookwhen.com/fr/fagotin`). Structure `h5.wp-block-heading` "Titre |
X-Y ans" groupée sous des `h2` de semaine — parcours à état, même logique
que `aubel.py`.

Légal : `robots.txt` WordPress standard (seul `/wp-admin/` interdit) ;
"Conditions générales" lues en entier, aucune clause anti-scraping.

## B. Rejetés — investigués et honnêtement écartés

| Piste | Raison du rejet |
|---|---|
| École de Cirque Polichinelle (`ecoledecirquepolichinelle.be`) | **Site en maintenance** — page d'accueil unique "Le site... est actuellement en maintenance", aucune donnée accessible |
| CSM asbl (`csmasbl.be`) | **Domaine inatteignable depuis ce bac à sable réseau** (502/DNS timeout reproductible sur plusieurs tentatives, `www12.iclub.be`-like symptôme mais pas iClub) — piste réelle et prometteuse (stages sportifs 2,5-17 ans, ~30 ans d'existence, plusieurs centres Liège/Chaudfontaine/Fléron), à revérifier sur GitHub Actions plutôt qu'abandonnée |
| `liege-stages.be` | Domaine inatteignable depuis ce bac à sable (DNS ne résout pas du tout, `getaddrinfo ENOTFOUND`) — à revérifier sur GitHub Actions |
| Royal Tennis Club de Liège (`rtcl1885.be`, iClub `www8` ClubID=693) | Bannière explicite sur la page : **"Les stages ne sont pas en ligne mais vous pouvez inscrire votre enfant aux valves comme chaque année"** — inscription physique uniquement, pas de donnée en ligne |
| Cravache (manège, Loncin/Ans) | Page "Stages" purement descriptive (horaire-type, tarif), **aucune date concrète** publiée |
| Jonckeu Equestrian (Theux) | Page stages au texte encore daté "Programme de la saison **2022**" ; page "Calendrier 2026" ne liste que des concours (mars), rien sur les stages Toussaint |
| Royal Fayenbois Tennis Club (Jupille) | Page stages titrée **"STAGES PÂQUES & ÉTÉ"** uniquement — pas de programme Toussaint/Noël |
| ARGAYON (iClub `www` ClubID=88) | 5 stages trouvés mais tous datés d'**août 2026, déjà passés** au 31/08 ; rien pour Toussaint |
| A-corde La (école de musique, Grâce-Hollogne) | Dernier stage publié 3-13 août 2026 (déjà passé) ; page événements Squarespace confirmée à jour mais rien de plus récent |
| Art&Fact asbl (ULiège) | Programme "Stages en ville" seulement jusqu'à avril 2026, "Stages été" jusqu'à août 2026 — rien pour Toussaint au 31/08 |
| Nature et Loisirs asbl | Toutes les activités (dont le stage Toussaint "Pas si horrible nature", dates réelles 19-23/10) se déroulent à la **Maison du bois d'Hautmont, Braine-le-Château — Brabant wallon**, hors périmètre Liège |
| MaxJump Liège (trampoline) | Seul stage publié : "Stage d'Été Août 2026" (17-21/08), déjà passé ; rien pour Toussaint |
| MeltingSport | Stages **organisés sur Bruxelles**, hors périmètre Liège |
| CISAG (trampoline) | Adresse "Gymnase Montlouis... Oullins" — **commune française** (banlieue de Lyon), faux positif de recherche |
| Stu'Dance 26 (danse, Huy) | Seuls des stages d'été (juillet/août 2026, déjà passés) trouvés ; rien de daté pour Toussaint |
| ASenDANSE (Stages Kids) | École de danse **au parc de la Woluwe — Bruxelles**, hors périmètre Liège malgré un nom qui pouvait laisser penser à Liège |
| Vivons Sport asbl (Verviers/capoeira) | Cours hebdomadaires à l'année seulement, aucun stage Toussaint daté trouvé |
| Latitude Jeunes (site officiel, hors Jeunesse Ardente) | Tableau "Stages 2026 – région Liège" entièrement lu : toutes les entrées sont à **Liège-ville et Chênée** (déjà représentées via `jeunesse_ardente.py`, qui liste déjà Latitude Jeunes) — aucune commune de la province non couverte trouvée dans ce tableau, pas de doublon créé |
| Province de Liège (Musée de la Vie wallonne, "Mystère au musée") | **Inscription uniquement par téléphone** (04/279.20.16) — aucune donnée structurée en ligne, comme documenté pour "Sport chez nous" en 24/08 |
| Animation & Créativité (service Ville de Liège) | Page descriptive uniquement, aucune date Toussaint 2026 trouvée sur le texte visible |
| Burdinne, Plombières | Confirmé à nouveau : SPA Nuxt.js pur, rien en HTML brut ; Playwright échoue systématiquement dans ce bac à sable réseau (`net::ERR_CONNECTION_RESET` reproductible même avec proxy explicite) — à revérifier sur GitHub Actions comme noté le 28/08 |
| Modave (`modave.be`) | **Toujours compromis** au 31/08/2026 (revérifié : "POMPA4D", `modave-amp.pages.dev`, `blog.marzipants.co.uk` toujours présents) — ne pas scraper tant que non assaini |
| Tinlot | Page "vacances-scolaire" ne contient que les conditions administratives (compte, tarifs, pénalités) — aucun programme daté publié pour Toussaint au 31/08 |

## Correction apportée à la documentation précédente

**Waimes n'est pas une commune de la Communauté germanophone** — vérifié
cette session : Waimes appartient à la Communauté française (facilités
linguistiques pour la minorité germanophone, comme Malmedy), contrairement
à ce que listait la section E de `docs/ratissage-province-liege-2026-08-28.md`.
Le code postal 4950 (Waimes) est donc inclus dans `POSTAL_COMMUNE` de
`stagevacances.py` plutôt qu'exclu — à corriger de la même façon si un
autre scraper venait à toucher cette commune.

## Bilan chiffré

- **4 nouveaux organismes** avec données réelles extraites et testées :
  Le CFS asbl, Centre Culturel de Theux, Académie Tennis Padel Waremmien,
  Le Fagotin.
- **3 nouveaux modules** de scraper (`cfs.py`, `stagevacances.py`,
  `fagotin.py`) — `stagevacances.py` couvre 2 organismes et continuera
  d'en détecter automatiquement d'autres sans changement de code.
- **26 nouvelles activités** au total (16 CFS + 3 Theux + 2 ATPW + 5
  Fagotin), toutes pour la Toussaint 2026, dates/âges/prix réels.
- **`SCRAPERS` passe de 43 à 46 entrées actives** dans `run_all.py`.
- **~20 pistes investiguées et honnêtement rejetées** cette session (voir
  section B), la plupart pour absence de programme Toussaint 2026 publié
  ou localisation hors province de Liège.
- **2 candidats network-bloqués dans ce bac à sable** (CSM asbl,
  liege-stages.be) — ni construits ni rejetés, à revérifier sur GitHub
  Actions (réseau moins restreint) avant de conclure.

## Prochaines étapes recommandées

1. **CSM asbl** et **liege-stages.be** : revérifier sur un run GitHub
   Actions (réseau complet) — deux pistes réelles bloquées uniquement par
   les limites réseau de ce bac à sable, pas par une raison de fond.
2. **Burdinne / Plombières** : toujours à vérifier en Playwright complet
   sur GitHub Actions (SPA Nuxt.js non observable ici, cf. 28/08).
3. Revérifier début septembre les communes qui republient leur programme à
   cette période (Berloz, Clavier, Oreye, Ouffet, Tinlot, Donceel, Crisnée,
   Stoumont, Bassenge, Trois-Ponts, Limbourg — voir section D3 du
   28/08/2026), ainsi que **Modave** (site à assainir) et **Jonckeu
   Equestrian**/**Cravache** (calendriers pas encore mis à jour).
4. Surveiller `stagevacances.py` au fil des semaines : de nouveaux
   organismes s'y ajoutent en continu (plateforme ouverte à tout
   organisme), potentiellement plus productif à terme que la recherche
   manuelle organisme par organisme.
