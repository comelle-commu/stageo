# Stagéo — Investigation technique : sites communaux individuels (24/08/2026)

## Contexte

my.one.be et APSCHOOL sont abandonnés comme sources de scraping — voir
`docs/investigation-technique-2026-08-24.md` (my.one.be : API confirmée mais
CGU interdisant explicitement le web scraping ; APSCHOOL : aucun catalogue
accessible sans compte, mur d'inscription dès la première page).

Nouvelle piste testée ici : un socle de **sites communaux individuels**
(pages "vitrine" décrivant les plaines/stages communaux), site par site,
sans passer par une plateforme centralisée. Échantillon de 6 communes,
formats variés :

| Commune | Domaine | Province | Plateforme technique |
|---|---|---|---|
| Ans | ans-ville.be | **Liège** (zone test) | Plone (iMio) |
| Neupré | neupre.be | **Liège** (zone test) | Nuxt.js (SSR) |
| Seraing | seraing.be | **Liège** (zone test) | WordPress |
| Floreffe | floreffe.be | Namur | WordPress |
| Eghezée | eghezee.be | Namur | Plone (iMio) |
| Uccle | uccle.be | Bruxelles | Drupal |

**Méthodologie** : consultation manuelle unique de chaque page (une requête
`curl`/navigateur par site, aucune boucle automatisée), lecture du
`robots.txt` de chaque domaine, recherche d'une page CGU/mentions
légales mentionnant l'extraction de contenu, et inspection du HTML retourné
pour déterminer si l'info est statique, réactive (JS) ou en PDF.

---

## 1. Ans — CCJV (Centres communaux de jeux de vacances)

**Page testée :** `https://www.ans-ville.be/que-faire/stages-plaines-activites/centres-communaux-de-jeux-de-vacances-ccjv/ccjv`

- **robots.txt** (`https://www.ans-ville.be/robots.txt`, redirige vers le
  fichier partagé `static.imio.be/robots.txt` — utilisé par toutes les
  communes wallonnes hébergées par l'intercommunale iMio, dont Ans et
  Eghezée dans cet échantillon) : `User-agent: *` avec **`Crawl-delay:
  120`** et une liste de chemins dynamiques interdits (`/search*`,
  `/*login_form*`, `/*folder_contents*`, etc.) — **aucune page de contenu
  n'est interdite**. Une longue liste de bots agressifs connus
  (ScraperBot-type, y compris `GPTBot`/`ChatGPT-User`) est explicitement
  bloquée par nom, mais un accès `User-agent: *` respectueux (avec un délai
  de 120s entre requêtes) est autorisé.
- **CGU / mentions légales** (`/gdpr-view`) : uniquement une déclaration
  RGPD classique (finalités de traitement, DPD, durée de conservation).
  Aucune mention de scraping, robots, ou extraction de contenu.
- **Format :** 100% HTML statique, texte en clair dans la page (pas de JS
  requis, pas de PDF nécessaire pour l'essentiel de l'info).
- **Contenu disponible :** dates précises par semaine (été 2026 : 6
  semaines détaillées jour par jour), horaires, prix (2,50€/semaine,
  1,25€ à partir du 2e enfant), conditions d'éligibilité (résidents/école
  ansoise prioritaires), procédure d'inscription (Itsme + e-guichet
  communal, hors scope scraping), documents PDF annexes (règlement, mode
  d'emploi) en bonus. **Pas de tranche d'âge précise dans le texte
  principal** (implicite "enfants" — probablement dans le règlement PDF).

**Verdict : GO** — scraping simple et éthique, à condition de respecter le
`Crawl-delay: 120` du robots.txt partagé iMio.

---

## 2. Floreffe — Stages de vacances / Plaine communale

**Page testée :** `https://www.floreffe.be/enfance-et-education/stages-de-vacances/`

- **robots.txt** (`https://www.floreffe.be/robots.txt`) : **retourne un
  403 Forbidden**, de manière reproductible (testé en `curl` et en
  navigateur réel, même résultat). Le reste du site (page de contenu,
  page d'accueil) répond normalement en 200. C'est très probablement une
  erreur de configuration serveur (règle Apache bloquant l'accès au
  fichier robots.txt lui-même) plutôt qu'un blocage intentionnel — mais le
  signal est **ambigu** : impossible de lire une politique de crawl
  explicite. Par convention (RFC 9309 / pratique Google), une erreur 4xx
  sur robots.txt est généralement interprétée comme "aucune restriction",
  mais ce n'est pas une garantie universelle.
- **CGU / mentions légales :** aucune page CGU trouvée ; seul document
  légal identifié est une politique de protection des données (RGPD) en
  PDF, sans mention de scraping.
- **Format :** 100% HTML statique (WordPress), texte en clair.
- **Contenu disponible :** exceptionnellement complet — dates précises
  (3 semaines de juillet 2026), tranche d'âge (2,5 à 15 ans), prix détaillé
  par rang d'enfant et par résidence (Floreffois/non-Floreffois),
  modalités d'inscription (téléphone uniquement, pas en ligne), contact
  direct, **et même un état des places par groupe d'âge en texte libre**
  ("M2 : places dispos en semaine 3", "ADOS : COMPLET", etc.) — exactement
  le type d'info "disponibilité" recherché, mais en texte libre à
  interpréter plutôt qu'en champ structuré.

**Verdict : GO avec réserve** — techniquement trivial (HTML statique), mais
le `robots.txt` inaccessible (403) empêche de confirmer une politique de
crawl explicite. Recommandé : soit contacter la commune avant automatisation
régulière, soit s'auto-imposer un rythme très conservateur (une requête
occasionnelle, pas de polling fréquent) en attendant clarification.

---

## 3. Neupré — Plaines de vacances (page vitrine, hors APSCHOOL)

**Page testée :** `https://www.neupre.be/neupre/information/plaines-de-vacances`

- **robots.txt** (`https://www.neupre.be/robots.txt`) : le fichier
  n'existe pas à proprement parler — le serveur répond `200 OK` avec le
  **shell HTML générique de l'application** (Nuxt.js) pour cette URL comme
  pour n'importe quelle URL inconnue (comportement de type "soft-404" côté
  SPA). Testé aussi pour `/mentions-legales`, `/cgu`, `/conditions-generales`,
  etc. : même page générique à chaque fois (fichiers diff identiques),
  donc **aucune page légale dédiée trouvée**, ni de robots.txt réel.
  Absence de robots.txt = pas de restriction technique déclarée, mais
  signal moins net qu'un robots.txt explicite autorisant le crawl.
- **CGU :** non trouvées (cf. ci-dessus).
- **Format :** la page a l'apparence d'une SPA JavaScript (Nuxt.js), mais
  le contenu est en réalité **rendu côté serveur (SSR)** — vérifié en
  comparant le rendu Playwright (navigateur complet) et une simple requête
  `curl` brute : le texte intégral ("PETITES CANAILLES", tranches d'âge,
  prix, etc.) est déjà présent dans le HTML retourné par `curl`, sans
  exécution JS. **Un scraper HTTP simple (sans navigateur headless)
  fonctionne donc**, contrairement à l'hypothèse initiale.
- **Contenu disponible :** groupes d'âge nommés (5 groupes, de la classe
  d'accueil à la 6e primaire), tranche d'âge globale (2,5 à 12 ans),
  éligibilité (résidents/école communale), lieu, horaires, prix
  (30€/enfant/semaine), renvoi vers APSCHOOL pour l'inscription elle-même.
  **Dates moins précises** que Ans/Floreffe/Eghezée/Seraing/Uccle : "les
  deux semaines des congés de Printemps" et "les cinq premières semaines
  des congés d'été" plutôt que des dates calendaires exactes — celles-ci
  sont probablement dans la brochure PDF jointe (non vérifiée en détail
  cette session).

**Verdict : GO** — plus simple que redouté (le SSR évite le besoin d'un
navigateur headless), mais contenu textuel moins précis sur les dates que
les autres communes de l'échantillon ; à compléter par le PDF brochure si
des dates exactes sont nécessaires.

---

## 4. Eghezée — Plaines et stages communaux d'été 2026

**Page testée :** `https://www.eghezee.be/votre-commune/services-communaux/enfance-jeunesse-atl/plaines-de-vacances/plaines-et-stages-communaux-26`

- **robots.txt :** identique au modèle partagé iMio décrit pour Ans
  (même plateforme Plone) — `Crawl-delay: 120`, pages de contenu
  autorisées, seuls les chemins dynamiques (recherche, calendrier, etc.)
  sont interdits.
- **CGU / mentions légales** (`/gdpr-view`) : même modèle RGPD générique
  qu'Ans, aucune mention de scraping.
- **Format :** 100% HTML statique (Plone/iMio), texte en clair.
- **Contenu disponible :** **le plus structuré des six sites testés.**
  Chaque stage a un intitulé, une tranche d'âge précise (2,5-4, 5-7,
  8-12 ans), un lieu, un prix par semaine, et un programme thématique
  semaine par semaine avec dates exactes (ex. "Semaine 1 : Bike académy",
  "Du 13 au 17 juillet 2026 pour les minimax de 5-7 ans"). Inscription via
  portail e-guichet (hors scope scraping), contact email/téléphone
  disponible.

**Verdict : GO** — meilleur candidat "texte libre" de l'échantillon en
termes de richesse et de structure de l'information.

---

## 5. Seraing — Plaines de vacances d'été

**Page testée :** `https://www.seraing.be/plaines-2026-inscriptions/`

- **robots.txt** (`https://www.seraing.be/robots.txt`) : minimal,
  standard WordPress — `Disallow: /wp-admin/` uniquement (avec exception
  pour `admin-ajax.php`), sitemap déclaré. Aucune restriction sur les
  pages de contenu, aucun `Crawl-delay` spécifié.
- **CGU / mentions légales :** aucune page dédiée trouvée aux emplacements
  usuels (`/mentions-legales`, `/cgu`, `/politique-de-confidentialite` →
  404). Site institutionnel simple, sans CGU distincte identifiée.
- **Format :** 100% HTML statique (WordPress), texte en clair.
- **Contenu disponible :** dates précises (6 juillet – 14 août 2026),
  tranche d'âge (2,5 à 12 ans), horaires (avec accueil élargi payant
  détaillé), prix (5€/2,50€ par enfant), fenêtres d'inscription
  différenciées par priorité résidentielle, contact du service ATL,
  renvoi vers `www.seraing.be/atl` pour l'inscription (compte eID/Itsme).

**Verdict : GO** — simple, propre, robots.txt permissif.

---

## 6. Uccle — Plaine de jeux communale

**Page testée :** `https://www.uccle.be/fr/actualites/vie-pratique/enseignement/plaine-de-jeux-communale`

- **robots.txt** (`https://www.uccle.be/robots.txt`) : robots.txt Drupal
  standard, ne désautorise que les chemins d'administration/utilisateur
  (`/user/login`, `/node/add/`, `/search/`, etc.). Pages de contenu
  public non concernées.
- **CGU / mentions légales** (`/fr/mentions-legales`) : page trouvée,
  aucune mention de scraping/extraction/robots dans le texte (recherche
  par mots-clés négative).
- **Format :** 100% HTML statique (Drupal), texte en clair.
- **Contenu disponible :** très complet — dates (6 juillet – 14 août
  2026), âge (2,5 à 13 ans), lieu précis, grille de prix à 4 niveaux selon
  résidence/scolarité, contact, documents PDF annexes (règlement, projets
  pédagogiques), **et un état de complétude par section en texte libre**
  ("En maternelle -> COMPLET", "En primaire : semaines 1 et 2 ->
  COMPLET") — même logique que Floreffe.

**Verdict : GO** — simple, propre, contenu riche incluant un signal de
disponibilité en texte libre.

---

## Synthèse

| Commune | robots.txt | CGU anti-scraping ? | Format | Verdict |
|---|---|---|---|---|
| Ans | ✅ Autorisé (Crawl-delay 120s) | Non (RGPD seulement) | HTML statique | **GO** |
| Floreffe | ⚠️ Inaccessible (403, probable bug serveur) | Non | HTML statique | **GO avec réserve** (clarifier le robots.txt avant automatisation régulière) |
| Neupré | ⚠️ Absent (soft-404 générique) | Non trouvée | HTML statique (SSR malgré apparence SPA) | **GO** (dates moins précises, PDF en complément) |
| Eghezée | ✅ Autorisé (Crawl-delay 120s) | Non (RGPD seulement) | HTML statique | **GO** — le plus structuré |
| Seraing | ✅ Autorisé, aucune restriction notable | Non trouvée | HTML statique | **GO** |
| Uccle | ✅ Autorisé (standard Drupal) | Non trouvée (vérifiée) | HTML statique | **GO** |

**Aucun cas de NO-GO** dans cet échantillon — contrairement à my.one.be
(interdiction explicite) et APSCHOOL (rien à scraper sans compte), les
sites communaux "faits maison" testés ici sont uniformément :
- **statiques** (aucun besoin de rendu JavaScript, même sur le site en
  apparence le plus "moderne" — Neupré/Nuxt fait du SSR),
- **sans PDF obligatoire** pour l'info essentielle (dates, âges, prix,
  contact) — les PDF ne sont que des compléments (règlements, brochures),
- **sans clause CGU interdisant l'extraction de contenu** — à la
  différence de my.one.be, aucun des six sites n'a de CGU dédiée
  mentionnant scraping/robots/extraction,
- **majoritairement permissifs au niveau robots.txt**, avec deux nuances à
  traiter au cas par cas : le `Crawl-delay: 120` partagé par les sites
  iMio (Ans, Eghezée, et presque certainement toutes les communes
  wallonnes hébergées par iMio) à respecter strictement, et le 403
  reproductible sur `floreffe.be/robots.txt` à clarifier avant automatisation.

## Recommandation

**Oui, ce socle de sites communaux individuels est une base légale et
technique plus solide que my.one.be/APSCHOOL pour un premier MVP**, avec
des nuances importantes :

1. **Sur la zone test (province de Liège)** : les 3 communes liégeoises de
   l'échantillon (Ans, Neupré, Seraing) sont **toutes en GO**, avec des
   robots.txt propres et du contenu HTML statique exploitable
   immédiatement. C'est un signal positif fort pour démarrer le MVP sur
   cette zone spécifiquement.
2. **Le vrai coût n'est pas technique mais éditorial** : contrairement à
   my.one.be (une API, un schéma, un scraper), ici il faut **un parseur
   par commune** (ou au minimum par plateforme : Plone/iMio, WordPress,
   Drupal, Nuxt — 4 familles identifiées sur 6 sites, ce qui limite un peu
   la duplication d'effort), car le texte est libre et la structure HTML
   varie. Le champ "disponibilité" n'existe nulle part sous forme
   structurée (contrairement à my.one.be) — il faudrait le déduire d'un
   texte libre ("COMPLET", "places dispos en semaine 3"), ce qui est plus
   fragile et demandera un peu de NLP/regex par site plutôt qu'un parsing
   générique.
3. **Passage à l'échelle** : la province de Liège compte 84 communes.
   Ce test sur 3 communes liégeoises + 3 hors zone est encourageant mais
   ne prouve pas l'uniformité à grande échelle — d'autres communes
   utilisent probablement d'autres plateformes (Wix, Joomla, sites
   "faits maison" sans CMS, PDF uniquement...) qu'il faudra tester avant
   de généraliser. La bonne nouvelle : sur cet échantillon, 4 plateformes
   différentes (Plone/iMio, WordPress, Drupal, Nuxt) ont toutes donné un
   résultat statique et exploitable, ce qui laisse penser que la
   proportion de sites réellement bloquants (JS pur sans SSR, PDF scanné,
   CGU restrictive) sera minoritaire — mais **à vérifier commune par
   commune avant d'industrialiser**, pas supposer.
4. **Prochaine étape concrète suggérée** : élargir l'échantillon à une
   dizaine de communes liégeoises supplémentaires (même méthodologie
   manuelle, pas de boucle automatisée) pour confirmer le taux de
   couverture réel avant d'investir dans un scraper multi-communes ; en
   parallèle, clarifier le cas Floreffe (contact direct ou nouvelle
   vérification du robots.txt) puisque Floreffe fait partie des communes
   à fort potentiel de contenu (état de complétude en texte libre).

**En résumé : ce socle suffit pour démarrer un MVP sur la zone de test
(province de Liège), à condition d'accepter un coût de maintenance par
commune (un parseur par plateforme, pas un scraper générique) et de
continuer à vérifier robots.txt/CGU au cas par cas à mesure que la
couverture s'élargit.**
