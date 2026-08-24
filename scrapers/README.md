# Scrapers Stagéo — sites communaux (MVP)

Premier scraper fonctionnel, limité à la zone de test (province de Liège) :
**Ans**, **Seraing**, **Neupré**. Floreffe est volontairement laissé de côté
(voir plus bas). Contexte complet des vérifications légales/techniques :
`docs/investigation-technique-sites-communaux-2026-08-24.md`.

## Installation

```bash
cd scrapers
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Lancer le scraper

```bash
./venv/bin/python3 run_all.py
```

Écrit `output/activites.json`, `output/activites.csv` et
`output/timings.txt`. Chaque module peut aussi être lancé seul pour du
debug (`./venv/bin/python3 ans.py`, etc.) — il affiche alors ses résultats
en JSON sur stdout sans rien écrire sur disque.

## Schéma de sortie

Une ligne par activité : `commune, nom_activite, dates, age_min, age_max,
prix, lieu, modalites_inscription, disponibilite, lien_source,
date_verification`.

`age_min`/`age_max` sont numériques quand l'info est disponible (sinon
`null`). Tous les autres champs sont du texte libre — voir les limites
ci-dessous, notamment pour `disponibilite`.

## Architecture : un parseur par plateforme

Contrairement à l'hypothèse de départ, **Ans et Seraing n'utilisent pas la
même plateforme** (Ans = Plone/iMio, Seraing = WordPress) — vérifié en
récupérant le HTML réel des deux sites. Les 3 communes de cette session
utilisent donc 3 plateformes différentes, d'où 3 parseurs séparés :

| Commune | Plateforme | Rendu | Module |
|---|---|---|---|
| Ans | Plone (iMio) | HTML statique | `ans.py` |
| Seraing | WordPress | HTML statique | `seraing.py` |
| Neupré | Nuxt.js | **SSR** — HTML déjà complet dans la réponse HTTP brute, malgré l'apparence de SPA JS (vérifié : pas besoin de navigateur headless) | `neupre.py` |

`common.py` porte la logique partagée : requêtes HTTP respectueuses,
détection de disponibilité en texte libre, écriture JSON/CSV.

## Respect des règles de crawl

- **User-Agent identifiable** envoyé sur chaque requête, avec contact
  (`StageoScraperBot/0.1 (+contact: murieldelepont@gmail.com; ...)`).
  ⚠️ Piège rencontré : un accent dans le User-Agent (`Stagéo`) a fait
  planter le WAF du site d'Ans en 403 côté `requests` (alors que `curl -A`
  passait avec la même chaîne). Leçon : header HTTP = ASCII pur, toujours.
- **Crawl-delay** du robots.txt respecté par domaine (`CRAWL_DELAYS` dans
  `common.py` — 120s pour Ans, valeur reprise du robots.txt partagé iMio).
  Sans objet sur ce run (une requête par domaine, pas de requêtes répétées),
  mais le mécanisme est en place pour un futur run multi-pages.
- Pas de boucle sur un grand nombre de pages : une URL connue à l'avance
  par commune, une requête chacune.

## Floreffe : EN ATTENTE, pas ignoré silencieusement

`floreffe.py` existe mais **ne fait aucune requête réseau**. Le
`robots.txt` de floreffe.be renvoie un 403 Forbidden reproductible (curl et
navigateur complet, même résultat) — impossible de confirmer une politique
de crawl. `run_all.py` l'affiche explicitement comme `EN_ATTENTE` dans le
résumé plutôt que de l'omettre. À débloquer : contact direct avec la
commune, ou nouvelle vérification du robots.txt à une date ultérieure.

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
24/08/2026, une requête par commune, pas de charge réseau significative) :

| Commune | Activités extraites | Durée |
|---|---|---|
| Ans | 6 | ~1,1 s |
| Seraing | 9 | ~1,1 s |
| Neupré | 5 | ~1,4 s |
| Floreffe | — | EN_ATTENTE |

**Total : 20 activités en ~3,6 s** pour 3 pages. À ce rythme (une requête
HTTP simple par commune, pas de rendu JS nécessaire même pour le site en
apparence le plus "moderne"), élargir à une dizaine de communes
supplémentaires resterait de l'ordre de quelques secondes au total — le
goulot d'étranglement pour passer à l'échelle sera l'écriture d'un nouveau
parseur par plateforme, pas le temps d'exécution.
