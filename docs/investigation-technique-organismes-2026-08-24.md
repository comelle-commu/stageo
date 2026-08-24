# Investigation technique — organismes (au-delà des communes) — 24/08/2026

## Contexte

Demande : élargir la couverture au-delà des sites communaux vers des
organismes qui publient aussi des stages/plaines — ADEPS, PromoSport,
Sport chez nous, Cap Sciences ont été cités comme exemples. Même
méthodologie que pour les communes : vérification technique (structure
de la page, rendu serveur ou JS) et légale (robots.txt, mentions
légales/CGU) avant tout scraping.

## Résultat en un coup d'œil

| Organisme | Verdict | Volume potentiel | Complexité technique |
|---|---|---|---|
| **ADEPS** | ✅ GO | Très élevé (361 stages sur une seule page catalogue) | Faible — HTML serveur classique |
| **Cap Sciences** | ✅ GO | Élevé (dizaines de stages, plusieurs villes) | Faible — HTML serveur classique |
| **PromoSport** | 🟡 À creuser | Élevé (5 provinces) | Incertaine — voir ci-dessous |
| **Sport chez nous** | ❌ NO-GO (pour l'instant) | Très faible (1 camp en texte libre) | N/A — pas assez de contenu structuré |

## ADEPS — ✅ GO

- **Source** : [`activites.sport-adeps.be/catalogue/stages`](https://activites.sport-adeps.be/catalogue/stages)
  — catalogue officiel de la Fédération Wallonie-Bruxelles.
- **Technique** : Drupal, page rendue côté serveur. Vérifié : **361
  stages déjà présents dans le HTML brut**, sans appel JS/API
  nécessaire — comparable en simplicité à Ans/Seraing.
- **Champs disponibles par stage** : nom, internat/externat, prix,
  repas/logement inclus ou non, **disponibilité explicite
  ("Complet")**, tranche d'âge, lieu/centre, dates, niveau requis.
  → C'est la première source qui donne une vraie disponibilité
  exploitable (contrairement aux 82 activités communales actuelles,
  toutes "non communiqué").
- **robots.txt** : Drupal standard, bloque uniquement `/admin/`,
  `/user/...`, `/search/`, etc. — **rien qui vise `/catalogue/`**.
  Pas de `Crawl-delay` déclaré → on s'imposera un délai prudent par
  défaut (ex. 3-5s), comme fait pour les sites non-iMio jusqu'ici.
- **Légal** : mentions légales/vie privée de la Fédération
  Wallonie-Bruxelles consultées → notice RGPD classique (cookies,
  finalités, droits d'accès), **aucune clause sur le scraping ou la
  réutilisation automatisée**.

## Cap Sciences — ✅ GO

- **Source** : [`capsciences.be/stages-de-vacances/`](https://www.capsciences.be/stages-de-vacances/)
- **Technique** : WordPress, page rendue côté serveur — tableau de
  stages déjà présent dans le HTML.
- **Champs disponibles** : nom/thème du stage, lieu, tranche d'âge,
  dates, format (temps plein/mi-temps), **disponibilité explicite
  ("Stage complet")**. Le prix n'apparaît pas sur cette page de liste
  (probablement sur la fiche de chaque stage — à confirmer si on
  construit le scraper).
- **robots.txt** : bloque nommément une liste de bots IA/SEO
  (`GPTBot`, `CCBot`, `AhrefsBot`, `SemrushBot`, etc.) mais **autorise
  explicitement `User-agent: *`** (donc notre bot identifié) avec un
  **`Crawl-delay: 10`** déclaré — à respecter scrupuleusement, comme
  le `Crawl-delay: 120` iMio.
- **Légal** : mentions légales consultées → uniquement mention RGPD
  sur les emails collectés, **rien sur la réutilisation du contenu**.
- **Point à noter** : les intitulés de stages référencent parfois
  "PromoSport" ou "Action Sport" (ex. `promosport-nivelles-...`,
  `action-sport-magicien-...`) — Cap Sciences semble republier une
  partie de l'offre de partenaires sous sa propre marque. Cela peut
  créer des doublons avec un futur scraper PromoSport séparé — à
  garder en tête pour la logique de dédoublonnage le jour où les deux
  sources existeront (probablement sur `nom_activite` + `dates`,
  comme déjà géré pour les doublons intra-source).

## PromoSport — 🟡 à creuser avant de trancher

- **Source publique** ([`promo-sport.be/stages/`](https://www.promo-sport.be/stages/))
  ne liste que les implantations (ville + lien) — **aucune donnée de
  stage** (dates/prix/âge/dispo) n'est sur cette page.
- Les inscriptions et le détail des stages renvoient vers une
  application séparée : **`mya-sport.be`** (app "MYA", propre à
  PromoSport d'après le nom de son app mobile `com.inno.promosport`).
- **Vérification technique faite** : `mya-sport.be` tourne sous
  **Next.js** (React Server Components). Un premier `curl` sur
  `mya-sport.be/fr/pr1/home?category=stages` renvoie un `200 OK` mais
  **aucune donnée de stage identifiable** dans le HTML/JSON streamé —
  soit l'identifiant de club utilisé dans l'URL (`pr1`) n'est pas le
  bon, soit les données réelles arrivent via un appel client
  post-hydratation (comme my.one.be en tout début d'investigation).
- **Conclusion** : impossible de trancher GO/NO-GO sans une vraie
  inspection réseau **Playwright** (comme fait pour my.one.be et
  APSCHOOL au tout début du projet) pour voir ce que le navigateur
  charge réellement une fois la page hydratée, et identifier le bon
  identifiant de club/organisation dans l'URL. Je ne l'ai pas fait
  dans cette passe pour rester dans un temps raisonnable — à faire en
  prochaine étape si on confirme l'intérêt pour PromoSport.

## Sport chez nous — ❌ NO-GO pour l'instant

- Site WordPress simple, robots.txt ouvert — **aucun obstacle
  technique ou légal**.
- Mais en pratique : la page "Stages sportifs" ne contient **qu'une
  seule annonce en texte libre** (pas un tableau structuré), et ne
  couvre que 3 communes (Waremme, Oreye, **Ans** — déjà couverte par
  notre scraper communal). Le volume ne justifie pas la mise en place
  d'un scraper dédié pour l'instant. À reconsidérer si le site évolue
  vers un vrai catalogue, ou si on veut être exhaustif sur Waremme/
  Oreye spécifiquement.

## Recommandation

1. **Construire les scrapers ADEPS et Cap Sciences maintenant** — les
   deux sont des GO clairs, techniquement simples (HTML serveur,
   pattern déjà maîtrisé), et à eux deux ils ajouteraient largement
   plus d'activités que les 82 actuelles (rien que ADEPS : 361 lignes
   dans son catalogue).
2. **Investiguer PromoSport (via mya-sport.be) avec Playwright** avant
   de décider — c'est potentiellement la source la plus large (5
   provinces) mais reste technique incertaine tant que l'inspection
   réseau n'est pas faite.
3. **Laisser Sport chez nous de côté** sauf si tu tiens spécifiquement
   à Waremme/Oreye.
