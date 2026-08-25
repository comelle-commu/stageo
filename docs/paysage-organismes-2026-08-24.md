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

**Statut final (scraper construit — `scrapers/iclub.py`)** :
- `robots.txt` → **404** sur tous les sous-domaines testés (`www.`,
  `www2.`, `www4.`, `www6.iclub.be`) : aucune restriction déclarée, aucun
  `Crawl-delay` → minimum de courtoisie par défaut appliqué.
- Techno : ASP classique (IIS 10), rendu **100% côté serveur** - confirmé
  sur plusieurs clubs, structure HTML identique partout (classes CSS
  `.TitreFormule`, `.location-formule`, `.periode-formule`,
  `.age-formule`, `.prix-formule`, `.text-success`/`.text-danger` pour la
  disponibilité). Chaque stage est un lien `<a class="pull-left">` avec un
  `EvenementID` unique - utilisé comme `lien_source`.
- Piège rencontré (déjà connu, déjà géré) : pas de charset déclaré dans le
  `Content-Type` → mojibake sur les accents sans la correction
  `apparent_encoding` déjà présente dans `common.respectful_get()` (même
  cas que Neupré).
- **Correction importante** sur l'hypothèse initiale : `ClubID` **n'est
  PAS un identifiant global** - chaque combinaison (sous-domaine, ClubID)
  est un club distinct, sans registre public pour les énumérer. Impossible
  de "deviner" une liste de clubs par force brute (et pas souhaitable non
  plus, éthiquement, vu le volume de requêtes que ça représenterait). Testé
  concrètement : `ClubID=51`/`53` sur `www2`, `203` sur `www6`, `572` sur
  `www4` répondent tous `200` mais **sans aucun stage actuellement publié**
  (club sans stage ouvert en ce moment, ou mauvais paramètres - pas
  distingué, pas grave : on les revisitera plus tard plutôt que de deviner).
- **2 clubs confirmés et intégrés** (stages réels extraits, testés de bout
  en bout) : **Royal Léopold Club** (Uccle, `ClubID=10` sur `www2`, 16
  stages) et **Royal Racing Club de Bruxelles** (Uccle, `ClubID=27` sur
  `www`, 65 stages) - 81 activités au total.

**Conclusion sur le potentiel "socle mutualisé"** : partiellement confirmé.
La **structure d'extraction est bien 100% réutilisable** d'un club à
l'autre (un seul parseur, `scrapers/iclub.py`, fonctionne déjà pour 2 clubs
sans aucune adaptation) - contrairement à un scraper communal, où chaque
site a sa propre mise en page. En revanche, **il n'existe pas de raccourci
pour découvrir tous les clubs d'un coup** comme le permettait le robots.txt
identique iMio : chaque club doit être identifié individuellement (recherche
web, lien depuis son propre site) et ajouté à la liste `CLUBS` dans
`iclub.py` - exactement le même travail d'onboarding que pour les communes,
juste avec un parseur déjà prêt à chaque fois.

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

1. ~~`iclub.be`~~ — **fait** (voir ci-dessus, `scrapers/iclub.py`, 2 clubs
   intégrés). Prochaine sous-étape possible : trouver d'autres clubs
   (recherche web au cas par cas) pour enrichir `CLUBS`.
2. **`mya-sport.be` (PromoSport)** — reste en attente d'inspection réseau
   Playwright (déjà identifié comme nécessaire dans la doc précédente).
3. **Annuaires** (`pour-nos-enfants.be` notamment, en évitant
   `stagespourenfants.be` qui semble mal maintenu) — à vérifier si les
   fiches listées contiennent déjà assez d'info structurée pour éviter de
   visiter chaque organisateur individuellement, ou si ce ne sont que des
   liens de renvoi (moins utile dans ce cas).

Dis-moi par laquelle tu veux que je continue.
