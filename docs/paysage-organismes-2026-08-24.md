# Paysage des organismes de stages en Wallonie/Bruxelles — 24/08/2026

## Contexte

Recherche demandée pour élargir la couverture au-delà des communes et des
2 premiers organismes déjà traités (ADEPS, Cap Sciences — voir
`docs/investigation-technique-organismes-2026-08-24.md`). Ceci est une
**recherche exploratoire** (web search), pas encore une vérification
technique/légale complète comme pour ADEPS/Cap Sciences — chaque piste
listée ici devra passer par le même processus (robots.txt, CGU, structure
réelle de page) avant qu'un scraper soit construit.

## Piste prioritaire : `iclub.be` — potentiel "socle mutualisé" comme iMio

Découverte importante : **`iclub.be` est une plateforme d'inscription
partagée par de nombreux clubs sportifs différents**, chacun avec son
propre `ClubID` sur un sous-domaine (`www2.iclub.be`, `www4.`, `www6.`,
`www15.`, `www16.`...). URL type :
`https://wwwN.iclub.be/register.asp?ClubID=X&action=Search&CategorieEvenement=Stages&LG=FR`.

Clubs identifiés dessus jusqu'ici : Royal Racing Club de Bruxelles, Royal
Léopold Club, Les Copains du Sport, Ville de Bruxelles (Vacances
Sportives), et d'autres non encore identifiés (les `ClubID` ne sont pas
forcément séquentiels/publics).

**Vérification technique de premier niveau faite** :
- `www2.iclub.be/robots.txt` → **404** (fichier inexistant) : aucune
  restriction déclarée, mais aussi aucun `Crawl-delay` à respecter
  explicitement → appliquer notre minimum de courtoisie par défaut.
- Techno : ASP classique + ASP.NET (IIS 10), page HTML avec CSS
  Bootstrap-like.
- **Testé concrètement sur un club** (`ClubID=10`, Royal Léopold Club,
  `register.asp?ClubID=10&action=Search&CategorieEvenement=Stages&LG=FR`) :
  un simple `curl` (sans JS) **renvoie déjà des dates réelles dans le HTML**
  (`10/08/2026`, `24/08/2026`, etc.) → rendu côté serveur confirmé, pas
  besoin de Playwright pour ce club au moins. Le prix n'est en revanche pas
  trouvé sous un format numérique simple sur cette page - à creuser (peut-
  être affiché après sélection d'un stage précis).
- **Reste à faire** avant de construire un scraper : confirmer que la
  structure HTML est identique (mêmes classes CSS) sur 2-3 autres `ClubID`
  différents (ex. `ClubID=203` Ville de Bruxelles, `ClubID=53` déjà croisé
  plus tôt), et trouver comment obtenir la liste des `ClubID` valides sans
  deviner un par un (annuaire iClub, ou liens trouvés via recherche comme
  ici).

**Pourquoi c'est la piste à creuser en premier** : si le motif se répète
(même structure de page, juste le `ClubID` qui change), **un seul scraper
paramétrable par `ClubID` pourrait couvrir des dizaines de clubs d'un
coup** — exactement le même effet de levier qu'avait eu la découverte du
socle iMio pour les communes.

## Autres pistes identifiées (non vérifiées techniquement/légalement)

### Annuaires / comparateurs (potentiel raccourci, mais à vérifier sérieusement)

| Site | Remarque |
|---|---|
| `stagespourenfants.be` | Annuaire multi-organisateurs par province. ⚠️ Signal de qualité douteux : son `robots.txt` référence un tout autre domaine (`voyage.be`) - probablement un template mal configuré, jamais mis à jour. À vérifier avec prudence avant d'y investir du temps. |
| `pour-nos-enfants.be` | Annuaire avec des pages dédiées par province (Hainaut, Namur, Luxembourg, Brabant wallon) - pas encore vérifié techniquement. |
| `happykids.be`, `centre-de-vacance.be` | Mentionnés comme annuaires similaires, pas encore explorés. |

### Organismes individuels repérés (à trier/prioriser)

**Multi-provinces / grande échelle :**
- **PromoSport** (`promo-sport.be`) — déjà en cours d'investigation (voir
  doc précédente), données réelles sur `mya-sport.be` (Next.js, à
  inspecter en Playwright).
- **ActionSport** (`actionsport.be`) — cité comme partenaire dans les
  stages Cap Sciences, mais a aussi l'air d'exister en organisme propre
  ("plus de 30 centres") — relation exacte avec Cap Sciences/PromoSport à
  clarifier (risque de doublons si les 3 sources sont scrapées un jour).
- **ADSL Stages** (`inscriptions.adslstages.be`) — spécialiste stages 3-18
  ans, semble avoir sa propre plateforme d'inscription dédiée.

**Brabant wallon / Bruxelles :**
- **Les Copains du Sport** (`lescopainsdusport.be`) — Genappe, Jodoigne,
  Perwez, Wavre, Watermael-Boitsfort, Kraainem. Passe peut-être par
  iclub.be (à confirmer).
- **Le CFS** (`lecfs.be`) — Brabant wallon, Bruxelles, Liège.
- **Smash Academy** (Uccle) — tennis, foot, judo, laser game, 3-17 ans.
- **Bubble** (`bubbleevent.be`) — stages créatifs, 2-7 ans.
- **Plaine de Plaisirs** (`stage-vacances.be`) — Uccle, multi-activités.
- **Jeunesse à Bruxelles** (`jeunesseabruxelles.be`) — stages et séjours.
- **Ville de Bruxelles** (`bruxelles.be/stages-et-vacances-sportives`) —
  organisme public, probablement structuré comme un site communal (même
  logique de scraping que Ans/Seraing potentiellement).

**Namur / Hainaut / Luxembourg (moins couvert jusqu'ici) :**
- **Funny Sports** (Namur) — tennis, danse, escalade, hockey, natation,
  3-12 ans.
- **AtArt asbl** — Namur et Charleroi, stages sportifs ET artistiques,
  centre de vacances agréé FWB.
- Organisateurs plus locaux non encore nommés en Hainaut/Luxembourg,
  probablement listés sur les annuaires ci-dessus.

## Recommandation

Trois pistes concrètes, par ordre de priorité suggéré :

1. **`iclub.be`** — vérification technique complète (Playwright si besoin,
   robots.txt confirmé absent donc pas de blocage légal évident) pour
   confirmer si un seul scraper paramétrable peut couvrir plusieurs clubs
   d'un coup. Plus gros potentiel de levier.
2. **`mya-sport.be` (PromoSport)** — reste en attente d'inspection réseau
   Playwright (déjà identifié comme nécessaire dans la doc précédente).
3. **Annuaires** (`pour-nos-enfants.be` notamment, en évitant
   `stagespourenfants.be` qui semble mal maintenu) — à vérifier si les
   fiches listées contiennent déjà assez d'info structurée pour éviter de
   visiter chaque organisateur individuellement, ou si ce ne sont que des
   liens de renvoi (moins utile dans ce cas).

Dis-moi par laquelle tu veux que je continue.
