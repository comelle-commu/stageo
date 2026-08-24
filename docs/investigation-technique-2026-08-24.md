# Stagéo — Investigation technique (24/08/2026)

## Mise à jour — inspection réseau réelle effectuée

Cette session dispose d'un accès réseau sortant complet. L'accès a été
confirmé (`https://www.wikipedia.org` → HTTP 200) et une vraie inspection
réseau via un navigateur Playwright/Chromium a été menée sur my.one.be et
APSCHOOL. Les constats ci-dessous remplacent les hypothèses non vérifiées de
la version précédente de ce document pour les tâches 1 et 2.

**Note technique (pour rejouer cette investigation) :** le proxy de sortie de
cet environnement (`HTTPS_PROXY=http://127.0.0.1:35553`) fait un
MITM/re-terminaison TLS. Chromium récent envoie par défaut un ClientHello
TLS 1.3 volumineux (GREASE ECH + post-quantum key share), que ce proxy gère
mal (`net::ERR_CONNECTION_RESET` systématique, y compris sur des sites aussi
simples que example.com ou wikipedia.org, alors que curl/Python passaient
sans problème). Contournement qui fonctionne de manière fiable : lancer
Chromium avec l'argument `--ssl-version-max=tls1.2` (en plus de
`--proxy-server=http://127.0.0.1:35553 --ignore-certificate-errors`). À
retenir pour toute future session Playwright dans cet environnement.

---

## Tâche 1 — my.one.be

### API confirmée

En reproduisant le parcours réel (page d'accueil → lien "Trouver une plaine
ou un stage" = `/?theme=PLAINE` → saisie de "4430" dans le champ
Localisation → sélection de la suggestion "4430 - Ans" → la page navigue
vers `/search?theme=PLAINE&criteres=...`), le navigateur déclenche cet appel
réseau, qui est bien la source des données affichées :

```
GET https://my.one.be/gw/microservice-my/activite-vacances/plaine/search/zone
    ?latitudeOrigine={lat}&longitudeOrigine={lon}
    &latitudeMin={latMin}&latitudeMax={latMax}
    &longitudeMin={lonMin}&longitudeMax={lonMax}
```

- C'est une recherche **par zone géographique (bounding box)**, pas par
  rayon autour d'un code postal. Le front calcule la bbox à partir du niveau
  de zoom de la carte après géolocalisation de "4430 - Ans" (via un service
  d'autocomplétion d'adresse séparé, `/gw/microservice-my/adresse/...`, qui
  ressemble à un proxy vers l'API Google Places — utilise un `sessionToken`).
- **Aucune authentification requise.** Vérifié en rejouant l'URL exacte avec
  une requête Python `urllib` totalement anonyme (aucun cookie, aucun
  header d'auth, nouvelle session) depuis cet environnement : réponse
  `200 OK` avec le JSON complet, identique à ce que le navigateur reçoit.
- Le endpoint ne prend **pas** de paramètre "période de vacances" ou "âge" —
  il retourne toutes les activités dans la zone géographique, tous congés et
  tous âges confondus. Le filtrage par période ("prochaine période de
  vacances") et par âge se fait côté client (ou via des filtres UI
  supplémentaires sur la page de résultats, non testés en détail).

### Structure de la réponse (exemple réel, zone Ans/Liège, 4 résultats)

```json
[
  {
    "activiteId": "18745280",
    "denomination": "Plaines de vacances",
    "description": "<p>...html...</p>",
    "conge": "AUTOMNE",
    "publicCible": { "ageMinimal": 2.5, "ageMaximal": 10.0, "libelle": null },
    "horaire": { "heureDebut": "08:00:00", "heureFin": "17:30:00" },
    "periode": { "dateDebut": "2026-10-19", "dateFin": "2026-10-30" },
    "pouvoirOrganisateur": { "denomination": "CENTRE DE JEUNESSE - LIEGE", "id": "137966" },
    "pfp": { "pfpMin": 70, "pfpMax": 70 },
    "prestationsIncluses": ["ACCUEIL_MATIN", "ACCUEIL_SOIR", "COLLATIONS", "ACTIVITES"],
    "thematiques": ["LECTURE_ET_CONTES", "MUSIQUE_ET_CHANTS", "CUISINE", "..."],
    "adresse": {
      "pays": "BE", "localite": "Ans", "codePostal": "4430",
      "rue": "Rue du Président Wilson", "numeroRue": "5",
      "province": "LIEGE", "municipalite": "Ans",
      "localisation": { "latitude": 50.6526, "longitude": 5.538698 }
    },
    "distance": 1763.95,
    "inscriptionInformation": {
      "denominationContact": "Secrétariat / Michelle BONNET",
      "donneesContact": [
        { "contactType": "EMAIL", "value": "info@cjlg.be" },
        { "contactType": "PHONE", "value": "042471436" },
        { "contactType": "WEBSITE", "value": "www.cjlg.be" }
      ]
    },
    "dateDebutInscription": "2026-08-04",
    "disponibilite": "PLACES_DISPONIBLES",
    "couverturePFP": "SEMAINE"
  }
]
```

C'est un schéma **très riche** — exactement ce qu'un outil d'alerte de
places voudrait : dates précises, tranche d'âge, organisateur, contact
direct, et surtout un champ **`disponibilite`** (`PLACES_DISPONIBLES` dans
cet exemple) qui semble indiquer directement si des places restent. Aucune
pagination observée sur ce petit échantillon (4 résultats) ; à re-vérifier
sur une zone plus dense (ex. Bruxelles) avant de conclure sur l'absence de
pagination.

### ⚠️ Blocage contractuel — CGU de my.one.be

En lisant les CGU réelles (`/information/conditions`, rendu et lu via
navigateur — page 100% Angular, illisible en HTTP brut) :

> « En utilisant ce site, vous vous engagez à ne pas développer, prendre en
> charge ou utiliser des logiciels, des dispositifs, des scripts, des robots
> ou tout autre moyen ou processus visant à effectuer du **« web scraping »**
> du contenu ou à copier par ailleurs des profils et d'autres données des
> services. **Toute extraction et/ou réutilisation du contenu est
> interdite.** »

Et le `robots.txt` de my.one.be contient `Disallow: /*?` — soit toute URL
avec une chaîne de requête, ce qui couvre à la fois la page de résultats
(`/search?theme=...`) et l'API elle-même
(`/gw/.../zone?latitudeOrigine=...`).

**Conclusion Tâche 1 :** l'API JSON existe, est confirmée, ne nécessite
aucune authentification, et a un schéma de réponse très exploitable
(y compris un champ de disponibilité). **Techniquement**, un scraper serait
trivial à écrire. **Contractuellement**, les CGU interdisent explicitement
le scraping/l'extraction de contenu, et le `robots.txt` désautorise
explicitement les URL avec paramètres (donc l'API elle-même). C'est un
blocage clair, pas une zone grise — automatiser cette source sans
autorisation écrite de l'ONE serait une violation directe des CGU.

---

## Tâche 2 — APSCHOOL

### Confirmation en navigation privée (contexte navigateur neuf, sans cookies)

Les deux URLs communales ont été ouvertes dans un contexte Playwright neuf
(équivalent navigation privée — aucun cookie, aucune session préexistante) :

- `https://plateforme.apschool.be/authentication/extrascolaireInscription/accueil/211`
  (Neupré) → page "Welcome to the school's APSCHOOL platform — Commune de
  Neupré", texte : *"In order to have access to the various extracurricular
  activities offered, a registration is necessary."*, un seul bouton
  **"I register"**. Aucun catalogue, aucune liste d'activités visible.
- `https://plateforme.apschool.be/authentication/plaineinscription/accueil/39`
  (Chaumont-Gistoux) → page identique, "Commune de Chaumont-Gistoux".

Seul appel JSON observé sur ces pages (public, sans auth) :
`GET https://api.plateforme.apschool.be/plaine/nomEcole?ecoleId={id}` →
`{"nom": "Commune de Neupré"}` — juste le nom de la commune, aucune donnée
d'activité.

### Un cran plus loin : clic sur "I register"

En cliquant sur "I register" (toujours sans compte, navigation privée), la
page mène directement à un **formulaire d'inscription complet** :
identité de l'enfant, **numéro de registre national**, informations
médicales, données des parents, choix d'établissement/section/niveau
scolaire, contact d'urgence — avant même d'arriver à un quelconque choix de
plaine ou stage. Aucun catalogue d'activités n'est visible à aucune étape
sans avoir rempli ces données personnelles sensibles.

**Conclusion Tâche 2 :** confirmé de manière définitive et en direct — il
n'existe **aucun catalogue public consultable sans compte** sur APSCHOOL.
L'accès est verrouillé dès la première étape derrière un formulaire
d'inscription exigeant des données personnelles sensibles (dont le numéro
de registre national de l'enfant). Un scraper sans création de compte est
**techniquement impossible** ici (pas un problème de CGU comme pour
my.one.be — il n'y a simplement rien à scraper avant identification), et
créer des comptes automatiquement est de toute façon exclu par la
contrainte du projet.

---

## Tâche 3 — Open data (ODWB / opendata.brussels.be)

*(non re-testée cette session — résultats de la session précédente, issus de
recherche web indexée, inchangés)*

**odwb.be :**
- Aucun jeu de données trouvé avec places disponibles / dates en temps réel
  pour les plaines ou stages.
- Un jeu de données pertinent en tant que **répertoire d'organisateurs**,
  pas de disponibilités : *"Les associations de jeunesse de la Fédération
  Wallonie-Bruxelles"* —
  https://www.odwb.be/explore/dataset/les-associations-de-jeunesse-de-la-federation-wallonie-bruxelles/

**opendata.brussels.be :**
- *"Maisons des Enfants"* — dataset de localisation, pas de places/dates en
  temps réel.

**Conclusion Tâche 3 :** pas de source open data "prête à l'emploi" pour les
disponibilités en temps réel.

---

## Synthèse — ce qui est automatisable

| Piste | Statut | Détail |
|---|---|---|
| ODWB — répertoire d'associations de jeunesse | **Facile**, légal | Dataset ouvert exportable — bon pour une liste de cibles, pas pour les disponibilités |
| opendata.brussels.be — Maisons des Enfants | **Facile**, légal | Périmètre limité (localisation, pas dispo) |
| **my.one.be** | **Techniquement trivial, mais interdit contractuellement** | API JSON confirmée, sans auth, schéma riche (dates, âge, contact, dispo). **CGU interdisent explicitement le web scraping** + `robots.txt` désautorise les URL à paramètres (couvre l'API). Nécessite un accord/partenariat avec l'ONE avant tout usage automatisé. |
| **APSCHOOL** (Neupré, Chaumont-Gistoux, et probablement les autres communes sur la même structure d'URL) | **Bloqué techniquement**, confirmé en direct | Aucun catalogue accessible sans compte ; le formulaire d'inscription (avec numéro de registre national) est la première chose affichée. Pas de scraping possible sans créer de comptes, ce qui est exclu. |
| Sites communaux "faits maison" (hors ONE/APSCHOOL) | Inconnu | Non exploré cette session |

## Verdict

**Aucune des deux sources principales (my.one.be, APSCHOOL) n'est
exploitable par un scraper non autorisé dans l'état actuel :**

- **my.one.be** a la meilleure donnée (et de loin — schéma détaillé avec
  disponibilité en temps réel), mais l'utiliser sans autorisation
  violerait explicitement ses CGU. La voie viable ici n'est **pas
  technique mais relationnelle** : contacter l'ONE (ou pro.one.be, qui
  alimente la même donnée) pour discuter d'un accès API officiel ou d'un
  partenariat. Si un accord est obtenu, l'implémentation technique côté
  Stagéo serait rapide (API REST simple, JSON propre, pas d'auth à gérer
  côté client si l'ONE l'autorise telle quelle).
- **APSCHOOL** n'a tout simplement rien à offrir sans création de compte
  (et donc sans données personnelles d'enfants réels) — cette piste doit
  être abandonnée en l'état, ou remplacée par un partenariat direct avec
  les communes/organisateurs (ex. obtenir un export manuel ou un accès API
  dédié de leur part), pas par un scraper.

**Recommandation :** ne pas coder de scraper contre ces deux sources.
Prochaine étape utile : prise de contact avec l'ONE/pro.one.be pour évaluer
un partenariat de données (la richesse du schéma my.one.be vaut largement la
démarche), et en parallèle continuer à explorer des sources alternatives
(sites communaux indépendants, autres plateformes d'inscription que
APSCHOOL) qui n'ont pas ce double verrou technique + contractuel.
