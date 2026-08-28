# Scrapers Stagéo — sites communaux (MVP)

Scraper fonctionnel, limité à la zone de test (province de Liège) :
**Ans**, **Seraing**, **Neupré**, **Verviers**, **Herstal**, **Huy**,
**Sprimont**. Floreffe, Waremme, Hannut, Oupeye et Aywaille sont
volontairement en attente (voir plus bas, chacun avec sa raison précise).
Contexte complet des vérifications légales/techniques :
`docs/investigation-technique-sites-communaux-2026-08-24.md` (Ans/Neupré/
Seraing),
`docs/investigation-technique-elargissement-communes-2026-08-24.md`
(passage à l'échelle iMio/Plone, Verviers), et
`docs/scraper-cas-difficiles-2026-08-24.md` (extraction PDF, pages hub :
Herstal/Waremme/Huy/Sprimont/Hannut).

## Installation

```bash
cd scrapers
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/playwright install chromium
```

## Lancer le scraper

```bash
./venv/bin/python3 run_all.py
```

Écrit `output/activites.json`, `output/activites.csv` et
`output/timings.txt`. Chaque module peut aussi être lancé seul pour du
debug (`./venv/bin/python3 ans.py`, etc.) — il affiche alors ses résultats
en JSON sur stdout sans rien écrire sur disque.

Si `scrapers/.env` est configuré (voir `docs/supabase-backend-2026-08-24.md`),
`run_all.py` upsert aussi automatiquement le résultat dans la table
`activites` sur Supabase, en plus des fichiers, puis journalise le run dans
`scrape_runs` et compare le nombre d'activités récupérées au dernier run
sain (voir "Contrôle qualité" plus bas). Sans `.env`, l'import et le
contrôle qualité sont simplement ignorés (message clair, pas d'erreur).
Vérification a posteriori : `./venv/bin/python3 verify_supabase.py`.

`run_all.py` retourne un code de sortie non nul si l'import Supabase échoue
ou si le contrôle qualité détecte une chute anormale — c'est ce code qui
fait apparaître un run rouge dans GitHub Actions (voir plus bas).

## Exécution automatique (GitHub Actions)

`.github/workflows/scrape.yml` relance `run_all.py` automatiquement chaque
semaine (voir `docs/automatisation-github-actions-2026-08-24.md` pour le
détail complet). En bref :

- **Secrets à configurer une fois** (Settings → Secrets and variables →
  Actions → New repository secret, sur le dépôt GitHub) :
  `SUPABASE_URL` et `SUPABASE_SECRET_KEY` (mêmes valeurs que dans
  `scrapers/.env` en local), plus `BREVO_API_KEY`, `BREVO_LIST_ID` et
  `BREVO_SENDER_EMAIL` pour l'email hebdomadaire (voir
  `docs/email-hebdomadaire-2026-08-25.md`).
- **Historique des runs** : onglet **Actions** du dépôt GitHub → workflow
  "Scraper Stagéo" → chaque ligne = un run passé, ✅ ou ❌, avec les logs et
  les fichiers de sortie téléchargeables en pièce jointe.
- **Lancer un run manuellement** : onglet Actions → "Scraper Stagéo” →
  bouton "Run workflow" (pas besoin d'attendre le cron).

### Ajuster la fréquence du scraper

Une seule ligne à changer dans `.github/workflows/scrape.yml`, la valeur de
`cron:` sous `schedule:`. Format standard (minute heure jour-du-mois mois
jour-de-la-semaine, en UTC) :

```yaml
schedule:
  - cron: "0 6 * * 1" # hebdomadaire, tous les lundis 06h00 UTC (par défaut)
```

En période préparatoire aux vacances, pour resserrer la fréquence :

```yaml
schedule:
  - cron: "0 6 * * 1,4" # tous les 3-4 jours (lundi ET jeudi)
  # ou : - cron: "0 6 */2 * *"  # tous les 2 jours
```

Puis relâcher à une fois par semaine une fois la période passée, en
remettant la ligne d'origine. Aucun autre changement nécessaire — le reste
du workflow (secrets, étapes, contrôle qualité) ne dépend pas de la
fréquence. Un simple commit sur cette ligne suffit ; le nouveau cron
s'applique au prochain déclenchement programmé.

## Schéma de sortie

Une ligne par activité : `commune, nom_activite, type_activite, dates,
age_min, age_max, prix, lieu, modalites_inscription, disponibilite,
lien_source, date_verification`.

`age_min`/`age_max` sont numériques quand l'info est disponible (sinon
`null`). Tous les autres champs sont du texte libre — voir les limites
ci-dessous, notamment pour `disponibilite`.

`type_activite` est assigné par `common.classify_type()` — un des 5
`TYPE_ACTIVITE_CHOICES` (`Sport`, `Art & créativité`, `Sciences & nature`,
`Langues`, `Multi-activités`). Best-effort par mots-clés sur le nom de
l'activité (avec priorité à l'organisateur quand il est structurellement
fiable : ADEPS → Sport, Cap Sciences → Sciences & nature, tout organisme
contenant "Club" → Sport). Un intitulé générique ou multi-thèmes retombe
honnêtement sur `Multi-activités` plutôt qu'un choix forcé. Piège rencontré
en l'écrivant : un match par simple sous-chaîne sur "créa" faisait aussi
matcher "RÉCRÉA'kids" (activité générique) — corrigé avec des regex à
limites de mots (`\b`).

## Architecture : un parseur par plateforme, un socle commun pour iMio/Plone

Contrairement à l'hypothèse de départ, **Ans et Seraing n'utilisent pas la
même plateforme** (Ans = Plone/iMio, Seraing = WordPress) — vérifié en
récupérant le HTML réel des deux sites. En revanche, l'investigation
d'élargissement (10 communes supplémentaires testées) a montré qu'**iMio/
Plone équipe 9 communes sur 13 examinées en province de Liège (69 %)**, avec
un `robots.txt` identique au bit près sur tout le réseau — ce qui justifie
un socle mutualisé pour cette famille de sites (voir
`docs/investigation-technique-elargissement-communes-2026-08-24.md`).

| Commune | Plateforme | Rendu | Module |
|---|---|---|---|
| Ans | Plone (iMio) | HTML statique | `ans.py` |
| Verviers | Plone (iMio) | HTML statique | `verviers.py` |
| Herstal | Plone (iMio) | Page HTML sans données + **PDF** (tableau propre, export Word) | `herstal.py` |
| Huy | Plone (iMio) | Page "hub" → sous-page HTML par période | `huy.py` |
| Sprimont | Plone (iMio, thème Sunburst) | HTML statique (planning daté en image, non extrait) | `sprimont.py` |
| Seraing | WordPress | HTML statique | `seraing.py` |
| Neupré | Nuxt.js | **SSR** — HTML déjà complet dans la réponse HTTP brute, malgré l'apparence de SPA JS (vérifié : pas besoin de navigateur headless) | `neupre.py` |
| Grâce-Hollogne | Plone (iMio) | Page HTML sommaire + **PDF texte natif** (dates/prix/adresses par centre, bien plus complet que la page) | `grace_hollogne.py` |
| Chaudfontaine | WordPress | HTML statique, très structuré (accordéons `<details>` un par stage) | `chaudfontaine.py` |
| Mons | Plone (iMio) | HTML statique, prose | `mons.py` |
| Arlon | Plone (iMio) | HTML statique, prose | `arlon.py` |
| Bastogne | Plone (iMio) | HTML statique, blocs structurés (titre + horaire/lieu par bloc) | `bastogne.py` |
| Ciney | Plone (iMio) | HTML statique, prose (organisé avec Ocarina Dinant) | `ciney.py` |
| La Louvière | Plone (iMio, sous-domaine `atl.`) | HTML statique, page permanente sans dates chiffrées | `lalouviere.py` |
| Ottignies-LLN | Plone (iMio, domaine réel `olln.be`) | HTML statique, prose | `ottignieslln.py` |
| Ferme de Roloux (organisme privé, Fexhe-le-Haut-Clocher) | Constructeur onlc.be | HTML statique, pas d'obstacle JS | `ferme_de_roloux.py` |
| Let's Sport (organisme privé, ~15 sites Liège/Luxembourg) | Site sur-mesure | HTML statique, structuré (classes CSS explicites) | `letssport.py` |
| Côté Campagne (organisme privé, Awans) | Constructeur générique | **SPA JS pur** - liens réels cachés derrière `onclick`, nécessite `fetch_rendered_html()` (Playwright) | `cote_campagne.py` |
| Village des Benjamins (organisme privé, Grâce-Hollogne) | Vue.js | **SPA JS pur** - rien en HTML brut, nécessite `fetch_rendered_html()` (Playwright) | `village_des_benjamins.py` |
| Dimension Sport (organisme privé, ~8 sites province de Liège) | Site sur-mesure | HTML statique, mais tableau dense avec balisage imbriqué/mal fermé → parsing hybride BeautifulSoup + regex par cellule | `dimension_sport.py` |
| Coordination ATL (plateforme multi-communes : Dinant, Fernelmont, Gesves, Incourt, Ohey, Wavre - Namur & Brabant wallon) | WordPress + TablePress | HTML statique, colonnes variables selon la commune (mapping par mot-clé d'en-tête) | `coordination_atl.py` |
| ADSL Stages (organisme privé, ~40 localités Hainaut/Luxembourg/Namur/BW) | Site sur-mesure | HTML statique, une carte par stage avec tout (âge/lieu/dates/prix) déjà dessus - pagination par "région" (liste figée d'IDs) | `adsl_stages.py` |
| Forest (commune bruxelloise) | Drupal | HTML statique, texte en prose (pas de balisage sémantique par activité) - une ligne "plaine" bornée sur l'ensemble des périodes citées + une ligne par stage nommé | `forest.py` |
| Uccle (commune bruxelloise) | Drupal | HTML statique, texte en prose, une seule offre ("plaine de jeux") avec 4 profils de prix selon la résidence | `uccle.py` |
| Besace ASBL (Liège, 2,5-6 ans) | Wix | HTML très fragmenté (DOM Wix), extraction sur texte à plat scopé à la section "Prochains stages" | `besace.py` |
| Jeunesse Ardente (annuaire Ville de Liège, multi-organisateurs) | WordPress sur-mesure | HTML statique, DOM propre par carte (`div.areas`) - agrège ~15 petites structures (écoles de sport, ASBL culturelles...) après filtrage des organisateurs déjà couverts ailleurs (ADEPS, Let's Sport) pour éviter les doublons | `jeunesse_ardente.py` |
| Agenda Omnia (18 communes iMio de la province de Liège) | iMio, widget "Agenda"/Omnia partagé | HTML statique (carrousel serveur en page d'accueil), filtré sur catégorie "Stages et cours" + type "Activité" - voir section dédiée plus bas | `agenda_omnia.py` |
| Stavelot (iMio, sans widget Omnia) | Brochure PDF (mise en page libre, pas de tableau exploitable) | Extraction sur le texte de chaque page individuelle, gabarit "organisateur / dates / titre / âge / prix" repéré empiriquement - voir section dédiée plus bas | `stavelot.py` |
| Faimes (iMio, sans widget Omnia) | Brochure PDF (texte natif, propre) | Une page couvre toute l'année scolaire, format répété "Semaine du D au D + thème(s) petits/grands" | `faimes.py` |
| La Ferme des Enfants de Liège (organisme privé, Liège) | WordPress/WooCommerce | Liste + prix/stock via l'API publique WooCommerce Store (`/wp-json/wc/store/v1/products`), mais les vraies dates ne sont que dans le HTML de la page produit (bloc constructeur Divi "Dates/Age/Lieu") - un appel API + un fetch HTML par stage | `ferme_des_enfants.py` |

### Sites 100% JavaScript : `common.fetch_rendered_html()`

Ajouté le 26/08/2026 pour Côté Campagne et Village des Benjamins - deux
sites qui ne rendent RIEN en HTML brut (SPA Vue.js, ou liens réels cachés
derrière un gestionnaire `onclick` plutôt qu'un `href` exploitable).
`respectful_get()` + BeautifulSoup ne suffisent pas dans ce cas : la
fonction lance un navigateur Chromium headless (Playwright), respecte le
même Crawl-delay par domaine que `respectful_get()` (même dictionnaire de
throttling), et retourne le HTML une fois le JS exécuté (et, si besoin, un
clic effectué via `click_selector`).

Coût réel : un navigateur headless est nettement plus lourd qu'une simple
requête HTTP - à réserver aux sites qui l'exigent vraiment. Nécessite
`playwright install --with-deps chromium` (voir `.github/workflows/scrape.yml`)
en plus de `pip install -r requirements.txt`.

`common.py` porte la logique partagée : requêtes HTTP respectueuses,
détection de disponibilité en texte libre, écriture JSON/CSV, **et depuis
cette session le socle iMio/Plone** :

- `IMIO_DOMAINS` / `IMIO_CRAWL_DELAY` : la liste des domaines iMio confirmés
  (10 à ce jour) et leur Crawl-delay commun (120s), utilisés automatiquement
  par `respectful_get()`.
- `check_legal(domain)` : vérification légale réutilisable pour onboarder
  une nouvelle commune sans tout relire à la main - fetch le `robots.txt` et
  la page légale (`/gdpr-view` par défaut sur iMio), compare le robots.txt à
  la signature iMio connue, et cherche des mots-clés anti-scraping dans le
  texte **visible** de la page légale (script/style retirés avant recherche,
  pour éviter les faux positifs type classe CSS `fa-robot`). Coûte 2
  requêtes HTTP - à appeler une fois à la main pour une nouvelle commune,
  jamais en boucle ni depuis `scrape()`.
- `find_plone_content(soup)` : repérage générique de la zone de contenu
  (`<main id="main-container">`, avec repli sur l'ancien thème Plone
  Sunburst). Confirmé mutualisable : présent et non-vide sur les 9 sites
  iMio inspectés (Ans et Verviers via un vrai parseur, les 7 autres lors du
  passage en revue structurel). Utilisé par `ans.py` et `verviers.py`.

**Ce qui n'est PAS mutualisé** (documenté en détail dans le rapport
d'élargissement) : l'extraction fine des dates/âges/prix à l'intérieur de
cette zone. Même entre deux sites iMio, la donnée est parfois en HTML
direct (Ans, Verviers), parfois renvoyée vers un PDF joint (Herstal,
probablement Waremme), parfois en page "hub" (Huy, Sprimont), parfois en
image intégrée (Oupeye) - un parseur par commune reste nécessaire pour
cette partie.

## Respect des règles de crawl

- **User-Agent identifiable** envoyé sur chaque requête, avec contact
  (`TrouveoScraperBot/0.1 (+contact: murieldelepont@gmail.com; ...)`).
  ⚠️ Piège rencontré : un accent dans le User-Agent (`Stagéo`, nom du
  projet avant son renommage en Trouvéo) a fait planter le WAF du site
  d'Ans en 403 côté `requests` (alors que `curl -A` passait avec la même
  chaîne). Leçon : header HTTP = ASCII pur, toujours.
- **Crawl-delay** du robots.txt respecté par domaine (`CRAWL_DELAYS` dans
  `common.py` — 120s pour Ans, valeur reprise du robots.txt partagé iMio).
  Sans objet sur ce run (une requête par domaine, pas de requêtes répétées),
  mais le mécanisme est en place pour un futur run multi-pages.
- Pas de boucle sur un grand nombre de pages : une URL connue à l'avance
  par commune, une requête chacune.

## Communes EN ATTENTE : pas ignorées silencieusement

Les modules `floreffe.py`, `waremme.py`, `hannut.py`, `oupeye.py`,
`aywaille.py`, `fleron.py`, `esneux.py`, `vise.py`, `jeunesses_musicales.py`,
`crie_liege.py`, `funhelangues.py` et `cote_campagne.py` **ne font aucune
requête réseau** et exposent une constante `RAISON` expliquant pourquoi.
`run_all.py` les affiche explicitement comme `EN_ATTENTE` dans le résumé
plutôt que de les omettre. Détail de chaque raison (403 robots.txt, PDF
sans structure exploitable, page pas encore publiée, image nécessitant de
l'OCR, plateforme tierce non vérifiée légalement) :
`docs/scraper-cas-difficiles-2026-08-24.md` pour les cinq premiers ;
raisons données directement dans chaque fichier pour les suivants — page
vide (Fléron), contenu chargé en JS/AJAX (Esneux, Jeunesses Musicales),
robots.txt interdisant explicitement ClaudeBot (Visé), programme pas
encore publié pour la saison (CRIE de Liège, FunheLangues), ou liens
cachés derrière du JavaScript nécessitant un navigateur headless non
encore intégré au pipeline (Côté Campagne).

## Verviers : plus simple qu'Ans, mais avec un écart par rapport à l'attendu

Comme annoncé par l'investigation d'élargissement, `verviers.py` a été le
parseur le plus rapide à écrire (structure `<h3>` propre, dates ET âges
donnés inline par plaine, contact directement dans le texte) - le socle
`find_plone_content()` a fonctionné du premier coup, sans adaptation.

**Écart avec ce qui était attendu :** l'investigation notait "dates + âges
inline par site" comme un point fort de Verviers par rapport à Ans, ce qui
est confirmé - mais **aucun prix n'est indiqué nulle part sur la page**
(contrairement à Ans, qui donne 2,50 €/semaine). Le champ `prix` est donc
`"Non communiqué sur cette page"` pour les 5 lignes Verviers. Le
tarif existe probablement dans un des deux PDF joints ("Règlement d'ordre
intérieur", "Projet pédagogique") ou sur le portail d'inscription lui-même,
non explorés cette session.

## Ratissage province de Liège : état des lieux et prochaines étapes

Suivi complet (communes couvertes, en attente de publication, à
construire, jamais vérifiées, ASBL candidates) dans
`docs/ratissage-province-liege-2026-08-28.md` - à consulter/mettre à jour
avant toute nouvelle session de recherche de sources sur cette province,
pour ne pas repartir de zéro.

## Agenda Omnia : un widget partagé découvert en ratissant la province de Liège

En cherchant à couvrir plus systématiquement la province de Liège (84
communes, dont ~30 déjà couvertes directement), l'investigation de Geer a
révélé qu'une bonne partie du réseau iMio embarque, sur sa page d'accueil,
un carrousel d'actualités ("Omnia") entièrement rendu côté serveur : chaque
élément porte une catégorie ("Stages et cours", "Fête et folklore"...) et un
type ("Activité" vs "Événementiel"). Piste alternative explorée d'abord :
une API de recherche filtrée sur `agenda.enwallonie.be` (le CDN d'images
partagé de ce widget) - abandonnée après investigation : le endpoint
`/@@omnia-api` de chaque commune redirige vers une authentification
Keycloak (pas public), et la recherche classique Plone (`@@search`) renvoie
0 résultat quel que soit le paramétrage essayé. Le carrousel de la page
d'accueil, lui, fonctionne sans aucune authentification ni JS.

Sur 19 communes de la province testées pour la présence de ce widget, 18 en
disposent réellement (`agenda_omnia.py`) - mais au 27/08/2026, **seule Geer
a des stages déjà publiés et correctement catégorisés** (8, tous pour la
Toussaint). Les autres communes de la liste sont conservées quand même :
le run hebdomadaire les réextraira automatiquement dès qu'elles publieront,
sans changement de code (même logique que Forest/Uccle).

Piège rencontré : le carrousel liste TOUTE l'actualité communale, pas
seulement les stages - un simple filtre sur la catégorie affichée ne
suffisait pas : Oupeye ("Table de conversation") et Ferrières ("Espace
Public Numérique") sont tagués "Stages et cours" mais sont en réalité des
événements adultes, révélés par leur `Event type` réel ("Événementiel")
une fois la fiche détail consultée - d'où le double filtre catégorie + type.

## Stavelot / Faimes : la vraie donnée était dans un PDF lié depuis une actualité, pas la page "stages" elle-même

Les deux pages web dédiées ("Plaines de jeux" à Stavelot, "Plaine de jeux
du Cortil" à Faimes) ne contiennent quasiment rien - la donnée utile est
en réalité dans une brochure PDF liée depuis une **actualité séparée**
(`decouvrez-la-brochure-extrascolaire-2026-2027` pour Faimes, un article
"Coordination Accueil Temps Libre" pour Stavelot). Leçon pour le
ratissage : quand la page "stages" habituelle est vide, chercher aussi du
côté des actualités récentes de la commune avant de conclure qu'il n'y a
rien.

Les deux PDF sont du texte natif (pas d'image scannée) mais avec des mises
en page très différentes de Herstal (le seul autre PDF déjà géré dans ce
dossier, qui a un vrai tableau propre) :

- **Stavelot** : un flyer à deux colonnes par activité (« Qui/Où/Quand »
  d'un côté, « Informations complémentaires » de l'autre) -
  `extract_tables()` ne renvoie que des fragments de cellules décoratives
  inexploitables. Extraction sur `extract_text()` **page par page**, avec
  un gabarit répété (organisateur, puis "Du D au D <mois>", puis le titre)
  repéré empiriquement. Limite assumée : sur une page qui fusionne deux
  activités en colonnes (1 page sur 12 dans le run testé), seule la
  première est extraite plutôt que de risquer d'associer les mauvais
  champs entre elles.
- **Faimes** : une seule page de texte propre couvre toute l'année
  scolaire (Toussaint, Noël, Détente, Printemps), format répété "Semaine
  du D au D <mois> <année> :" suivi du ou des thèmes ("pour les petits" /
  "pour les grands" / unique pour les deux tranches). Piège rencontré : le
  bloc de texte capturé entre deux "Semaine du" embarquait parfois le
  titre de la section suivante ("STAGE DE DETENTE") faute de séparateur -
  filtré explicitement.

## Forest / Uccle : pages communales mises à jour uniquement à l'approche de la période

Contrairement aux organismes privés (ADEPS, Cap Sciences, Dimension Sport...)
qui publient tout leur calendrier annuel à l'avance, les pages "plaine de
vacances" de Forest et Uccle ne semblent republiées qu'à l'approche de
chaque période (Forest l'indique explicitement : inscriptions ouvertes
"trois semaines avant la période des vacances"). Au 27/08/2026, les deux
pages ne couvrent encore que l'été 2026 (déjà passé, inscriptions closes) -
zéro ligne visible sur le site tant que ces dates ne sont pas dans le futur
(`isPast()` les masque par défaut côté `/activites`). Les regex sont
volontairement génériques (aucun mois/saison en dur) : dès que chaque
commune publiera sa page pour la Toussaint, le prochain run hebdomadaire
réextraira les nouvelles dates automatiquement, sans changement de code -
mais la structure n'a pas pu être vérifiée à l'avance sur du contenu
Toussaint réel, seulement sur l'été. À rouvrir l'œil dessus au premier run
de septembre.

## Limites connues de cette version (best-effort, pas de perfection)

- **`disponibilite`** : extraction par mots-clés simples
  (`complet`/`clôturé`/`places disponibles`/`liste d'attente`/`places
  limitées`) sur le texte de la page. Aucune des 3 communes de cet
  échantillon n'affiche de statut de ce type sur la page scrapée (Ans/
  Seraing/Neupré renvoient toutes vers un système d'inscription externe où
  la disponibilité réelle vit ailleurs) — donc `"Non communiqué sur cette
  page"` pour les 20 lignes de ce run. ⚠️ Faux positif rencontré et corrigé
  pendant le développement : Neupré affiche *"L'inscription est
  OBLIGATOIRE PAR SEMAINE **COMPLETE**"* (= semaine entière, pas "plus de
  places") — exclu explicitement du pattern. Les futurs sites qui
  affichent un vrai statut en texte libre (ex. Floreffe/Uccle vus dans
  l'investigation : `"ADOS : COMPLET"`) sont le vrai test de cette
  extraction — à surveiller de près une fois Floreffe débloqué.
- **Neupré — tranches d'âge par groupe** : la page ne donne les groupes
  qu'en niveau scolaire belge ("2ème et 3ème primaire"), pas en âge
  numérique (seule la tranche globale 2,5-12 ans est chiffrée). Les âges
  par groupe dans `NIVEAU_AGE_MAP` (`neupre.py`) sont donc **dérivés**, pas
  lus directement sur la page — à vérifier/affiner si besoin.
- **Neupré — dates** : pas de dates calendaires exactes sur cette page
  ("les cinq premières semaines des congés d'été" plutôt que des dates) ;
  le champ `dates` le signale explicitement plutôt que d'inventer des
  dates. La brochure PDF jointe sur la page (non traitée cette session)
  les contient probablement.
- **Ans — âge** : non précisé du tout sur la page scrapée (probablement
  dans le règlement PDF joint, non traité cette session) → `age_min`/
  `age_max` à `null`.
- **Ans — autres périodes de vacances** : la page mentionne aussi Automne,
  Hiver, Détente et Printemps, mais sans dates calendaires précises → non
  extraites (seule la période d'été, avec des dates exactes semaine par
  semaine, donne lieu à des lignes).
- **Encodage** : `www.neupre.be` ne déclare pas de charset dans son
  `Content-Type`, ce qui faisait tomber `requests` sur de l'ISO-8859-1 par
  défaut (mojibake sur tous les accents). Corrigé dans `common.py` via
  `resp.apparent_encoding` quand le charset est absent — à garder en tête
  pour les futurs sites.
- **Fusion de mots/paragraphes via BeautifulSoup `get_text()`** : deux
  bugs symétriques rencontrés et documentés dans le code (`seraing.py`,
  `neupre.py`) — `get_text(" ")` coupe parfois un mot en deux à une
  frontière de balise inline (`"pour l<strong>es suivants</strong>"` →
  `"pour l es suivants"`), tandis que `get_text()` sans séparateur recolle
  deux paragraphes voisins sans espace. Solution utilisée : pas de
  séparateur pour du texte à enfants inline, séparateur explicite entre
  enfants directs pour un conteneur à enfants block-level. À réappliquer
  pour tout nouveau parseur plutôt que de redécouvrir le problème.

## Résultats du run (référence)

Voir `output/timings.txt` après exécution. Dernier run mesuré (session du
24/08/2026) :

| Commune | Activités extraites | Durée |
|---|---|---|
| Ans | 6 | ~1,6 s |
| Seraing | 9 | ~1,1 s |
| Neupré | 5 | ~1,1 s |
| Verviers | 5 | ~0,9 s |
| Herstal | 57 | ~126,0 s (2 requêtes, dont le PDF → Crawl-delay iMio 120s) |
| Huy | 1 | ~122,1 s (2 requêtes : hub + sous-page → Crawl-delay iMio 120s) |
| Sprimont | 1 | ~1,8 s |
| Floreffe / Waremme / Hannut / Oupeye / Aywaille | — | EN_ATTENTE |

**Total : 84 activités extraites, 82 upsertées dans Supabase** (2 doublons
littéraux dans le PDF source Herstal, dédupliqués côté client — voir
`docs/scraper-cas-difficiles-2026-08-24.md`) en un peu plus de 4 minutes,
l'essentiel du temps venant du Crawl-delay iMio de 120s appliqué aux
communes nécessitant 2 requêtes (page + PDF, ou hub + sous-page). Le temps
d'exécution reste dominé par la politesse envers les serveurs, pas par le
traitement lui-même (extraction quasi instantanée une fois les pages
téléchargées).
