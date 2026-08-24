# Stagéo — Élargissement à 10 communes : capacité de mise à l'échelle (24/08/2026)

## Objectif

Avant de construire quoi que ce soit de plus, vérifier si iMio/Plone (la
plateforme d'Ans) est assez répandue en province de Liège pour justifier un
**parseur mutualisé**, plutôt que de continuer commune par commune comme pour
Ans/Seraing/Neupré (voir `scrapers/README.md`).

## Méthodologie

10 nouvelles communes de la province de Liège, tailles variées (2 grandes
villes, plusieurs communes moyennes, 2-3 rurales), en dehors d'Ans, Neupré et
Seraing déjà traitées. Pour chacune : une requête HTTP sur la page
"stages/plaines" trouvée via recherche web, une requête sur son robots.txt,
inspection du HTML retourné (balise `<meta name="generator">`, empreintes de
plateforme, structure du contenu). **Aucun scraping réel** — une poignée de
requêtes ponctuelles par commune, comme la dernière fois. Toutes les traces
HTML/robots.txt de cette exploration ont été jetées après analyse (pas de
valeur à les garder dans le dépôt).

## Résultats par commune

| Commune | Taille | Plateforme identifiée | robots.txt | CGU anti-scraping | GO/NO-GO | Structure ≈ Ans |
|---|---|---|---|---|---|---|
| **Liège** | Grande ville (~200k hab.) | Plone (iMio) — `<meta generator="Plone">` confirmé | iMio partagé, Crawl-delay 120s | Non (spot-check `/gdpr-view`) | **GO** | **Non** — page très courte, renvoie vers le service Jeunesse/e-guichet sans dates/prix inline ; les vraies offres (Céméa, Ferme des Enfants, Ocarina...) sont chez des opérateurs tiers |
| **Verviers** | Grande ville (~55k hab.) | Plone (iMio) confirmé | iMio partagé, Crawl-delay 120s | Non | **GO** | **Oui, et même mieux qu'Ans** — dates "du X au Y" et âges par site directement inline (ex. "Plaine Geron (2,5-5 ans)"), liste `<li>` structurée |
| **Herstal** | Moyenne (~40k hab.) | Plone (iMio) confirmé (URLs en `@@download`, typiques Plone) | iMio partagé, Crawl-delay 120s | Non | **GO** | **Non** — page HTML sans dates/âges/prix détectés, renvoie vers un PDF ("Stages d'été [année].pdf") pour le détail ; PDF non vérifié cette session (lien trouvé périmé) |
| **Huy** | Moyenne (~21k hab.) | Plone (iMio) confirmé | iMio partagé, Crawl-delay 120s | Non | **GO** | **À vérifier** — page "hub" (5,7k caractères) listant plusieurs programmes (Toboggan, Repaire des p'tits loups) avec semaine/âge/prix détectés dans le texte, mais pas encore isolés par activité |
| **Waremme** | Moyenne (~15k hab., chef-lieu Hesbaye) | Plone (iMio) confirmé | iMio partagé, Crawl-delay 120s | Non | **GO** | **À vérifier** — page d'intro courte, tranches d'âge mentionnées, détail probablement dans un PDF joint (`stages-printemps-2025.pdf` repéré) |
| **Visé** | Moyenne (~18k hab.) | **Nuxt.js** (vendor "enpoche.be", identifié via les métadonnées `og:url: vise.enpoche.be`) — **même famille technique que Neupré** | Pas de robots.txt réel (soft-fallback SPA, comme Neupré) | Non trouvée (mêmes chemins génériques testés que Neupré, tous retombent sur le shell SPA) | **GO** (par analogie avec Neupré, déjà scrapé avec succès) | À vérifier (page non inspectée en détail cette session) |
| **Aywaille** | Petite/rurale (~11k hab.) | Plone (iMio) confirmé | iMio partagé, Crawl-delay 120s | Non | **GO techniquement, mais NO-GO pratique** | **Non** — la page communale renvoie explicitement vers une plateforme tierce ("ActivKids") où les organisateurs encodent eux-mêmes leurs activités ; rien à scraper côté aywaille.be lui-même |
| **Sprimont** | Petite/rurale (~14k hab.) | Plone (iMio) confirmé | iMio partagé, Crawl-delay 120s | Non | **GO** | **À vérifier** — page longue (style règlement/ROI), semaine et âge détectés mais pas de prix inline détecté, structure prose plutôt que liste |
| **Oupeye** | Moyenne (~24k hab.) | Plone (iMio) confirmé | iMio partagé, Crawl-delay 120s | Non | **GO** | **Non probablement** — la page pointe vers une image intégrée (`@@images/...png`) pour le programme, pas du texte ; inscription via APSCHOOL (comme Neupré) |
| **Hannut** | Petite/moyenne (~15k hab.) | **WordPress** confirmé (`generator: WordPress 6.8.8`, `/wp-content/`) | Permissif (seuls agenda/calendrier dynamiques exclus, pas de Crawl-delay) | Non (spot-check `/mentions-legales`) | **GO** | À vérifier — URL de page spécifique trouvée via recherche web périmée (404), plateforme confirmée via la page d'accueil uniquement |

## Chiffre clé

**Sur les 13 communes examinées au total (3 déjà scrapées + 10 nouvelles),
9 tournent sur iMio/Plone, soit 69 %.**

- Déjà scrapées : Ans (Plone), Seraing (WordPress), Neupré (Nuxt/enpoche.be)
  → 1/3 sur Plone.
- Nouvelles : Liège, Verviers, Herstal, Huy, Waremme, Aywaille, Sprimont,
  Oupeye (Plone) + Visé (Nuxt/enpoche.be) + Hannut (WordPress) → 8/10 sur
  Plone.
- **Total Plone/iMio : 9/13.**

Fait notable en bonus : **Visé tourne sur la même plateforme Nuxt/"enpoche.be"
que Neupré** — une deuxième famille de mutualisation possible en dehors
d'iMio, à garder en tête.

**Robots.txt identique au bit près** sur les 8 nouveaux sites Plone testés
(194 lignes, `Crawl-delay: 120`, mêmes chemins dynamiques exclus) — confirmé
par diff direct entre plusieurs paires (Liège/Herstal, Liège/Oupeye). C'est
le même fichier géré centralement par iMio pour tout son réseau
d'hébergement, pas une coïncidence commune par commune.

## Nuance importante : "même plateforme" ≠ "même parseur suffit"

La plateforme technique (Plone/iMio) est très homogène — robots.txt
identique, structure de page (`<main id="content">`, `@@site-logo`,
`/gdpr-view` pour les mentions légales) et gabarit visuel identiques partout.
**Mais la façon dont chaque commune publie ses données d'activité varie
nettement, même au sein du même CMS :**

1. **Contenu directement en HTML** (comme Ans, et Verviers en encore mieux
   structuré) — extractible avec la même logique de parsing qu'`ans.py`.
2. **Contenu renvoyé vers un PDF joint** (Herstal, probablement Waremme) —
   même plateforme web, mais il faut ajouter une étape d'extraction PDF
   (non testée cette session : à vérifier si ce sont des PDF texte ou des
   scans avant de s'engager dessus).
3. **Contenu en page "hub"** listant plusieurs programmes avec du texte
   plus libre/long (Huy, Sprimont) — la même logique regex qu'Ans devrait
   fonctionner mais demandera plus de réglages par page.
4. **Contenu en image intégrée** (Oupeye) — non extractible par du texte,
   PDF/image à traiter différemment (OCR ou abandon).
5. **Renvoi vers une plateforme tierce** (Aywaille → ActivKids) — la
   commune elle-même n'a rien à scraper ; c'est un cas "NO-GO local" malgré
   un feu vert robots.txt/CGU, avec une piste alternative (la plateforme
   ActivKids elle-même, non investiguée).

## Recommandation

**Oui, ça vaut le coup d'investir dans un socle iMio/Plone mutualisé
maintenant** — mais mutualisé sur la partie qui est réellement identique
(pas sur l'extraction des données elle-même) :

- **Ce qui est mutualisable tout de suite, avec un ROI immédiat** : le
  respect du `Crawl-delay: 120` partagé (déjà fait dans `common.py`), la
  logique de requête HTTP respectueuse, la détection de la zone de contenu
  (`<main id="content">`), la vérification légale (CGU/robots.txt — déjà
  faite une fois pour tout le réseau iMio grâce au fichier identique), et
  une fonction générique de repérage "y a-t-il un PDF joint / une image
  jointe / du texte structuré ?" pour orienter vers la bonne stratégie
  d'extraction.
- **Ce qui reste du cas par cas** : l'extraction fine des dates/âges/prix,
  parce que même deux communes Plone voisines (Ans vs Verviers vs Huy)
  présentent l'info avec des variations de structure et de complétude
  significatives. Un "parseur iMio générique unique" qui prétendrait tout
  extraire automatiquement serait fragile ; un **socle commun + un petit
  adaptateur par commune** est plus réaliste, mais l'adaptateur sera
  nettement plus rapide à écrire pour un site Plone déjà connu que pour une
  plateforme totalement nouvelle (WordPress, Nuxt...).
- **Prochaine étape concrète suggérée** : étendre `common.py` avec les
  briques génériques ci-dessus, puis prioriser Verviers (structure quasi
  identique à Ans, meilleure même) comme 4e commune scrapée pour valider le
  socle mutualisé sur un vrai cas, avant de se pencher sur les cas PDF
  (Herstal/Waremme) qui demandent une brique supplémentaire (extraction PDF)
  non encore développée.

En résumé : **iMio/Plone est bien le socle technique dominant en province de
Liège** (69 % de l'échantillon) et mérite un investissement de
mutualisation — mais celle-ci portera sur l'infrastructure de scraping
(requêtes, légal, repérage de zone), pas sur un parseur "magique" universel
qui lirait toutes les pages d'activités sans adaptation.
