# Stagéo — Socle iMio/Plone mutualisé + validation Verviers (24/08/2026)

## Contexte

Suite à l'investigation d'élargissement
(`docs/investigation-technique-elargissement-communes-2026-08-24.md`), qui a
montré qu'iMio/Plone équipe 9 communes sur 13 examinées (69 %) avec un
`robots.txt` identique au bit près sur tout le réseau, cette session
construit le socle mutualisable identifié puis le valide avec **Verviers**
comme 4e commune scrapée (après Ans, Seraing, Neupré — voir
`docs/investigation-technique-sites-communaux-2026-08-24.md` et
`scrapers/README.md`).

## Ce qui a été ajouté à `common.py`

1. **Crawl-delay centralisé** (`IMIO_DOMAINS`, `IMIO_CRAWL_DELAY`) : les 10
   domaines iMio confirmés à ce jour partagent tous le même Crawl-delay
   (120s), appliqué automatiquement par `respectful_get()`.
2. **`check_legal(domain)`** : vérification légale réutilisable pour
   onboarder une nouvelle commune iMio sans tout relire à la main - récupère
   le `robots.txt` et la page légale (`/gdpr-view` par défaut), compare le
   robots.txt à la signature iMio connue, et cherche des mots-clés
   anti-scraping (`scraping`, `robot`, `extraction automatis...`, `crawl`,
   `moissonnage`) **dans le texte visible uniquement** (script/style
   retirés avant recherche - leçon tirée du faux positif `fa-robot`
   rencontré lors de l'investigation précédente). Coûte 2 requêtes HTTP :
   pensé pour un appel manuel ponctuel par nouvelle commune, jamais en
   boucle. Testé en conditions réelles sur `www.verviers.be` :

   ```
   robots_status: 200        matches iMio signature: True
   crawl_delay: 120           legal_page_status: 200
   warnings: []               verdict: GO
   ```

3. **`find_plone_content(soup)`** : repérage générique de la zone de
   contenu (`<main id="main-container">`, avec repli sur l'ancien thème
   Plone Sunburst `#content-core`). Confirmé fonctionnel sur Ans **et**
   Verviers (deux parseurs réels, structures de page différentes à
   l'intérieur, même point d'entrée). `ans.py` a été mis à jour pour
   l'utiliser aussi, en remplacement de son ancien `soup.find("main")` local.

**Ce qui reste volontairement hors du socle commun** (documenté dans le code
et dans `scrapers/README.md`) : l'extraction fine des dates/âges/prix à
l'intérieur de la zone de contenu. Elle varie trop d'une commune iMio à
l'autre (HTML direct, PDF joint, page hub, image) pour être généralisée sans
plus de cas réels en main.

## Verviers : validation du socle

`verviers.py` extrait 5 activités (2 plaines de détente/printemps + 3
plaines d'été) directement depuis les balises `<h3>` de la page, groupées
sous les dates communes de la période été. Écrit et fonctionnel du premier
coup avec `find_plone_content()`, sans adaptation du socle.

**Écart par rapport à l'attendu** (l'investigation annonçait Verviers comme
mieux structuré qu'Ans) : confirmé pour les dates et les âges (donnés
inline, ce qu'Ans ne fait pas), mais **le prix n'est indiqué nulle part sur
la page** — contrairement à Ans qui donne un tarif clair. Le champ `prix`
sort donc à `"Non communiqué sur cette page"` pour les 5 lignes Verviers ;
le tarif est probablement dans un des PDF joints (règlement, projet
pédagogique), non explorés cette session.

## Run consolidé : 4 communes

```
--- Ans ---        6 activités   0.80s
--- Seraing ---     9 activités   1.03s
--- Neupre ---      5 activités   1.12s
--- Verviers ---    5 activités   0.95s
--- Floreffe ---    EN_ATTENTE (robots.txt en 403, non débloqué)

Total : 25 activités en ~3.9s
```

Ajouter Verviers n'a pratiquement rien coûté en temps d'exécution — le
socle iMio partagé (déjà valide pour Ans) a été réutilisé tel quel. Le
temps de développement (comprendre la structure `<h3>`, écrire le parseur)
reste le vrai coût, pas l'exécution.

## Extrait des nouvelles données (Verviers)

| Activité | Dates | Âge | Prix |
|---|---|---|---|
| Plaine des Hougnes | du 23 au 27 février 2026 | non précisé | non communiqué |
| Plaine des Tourelles (printemps) | du 4 au 8 mai 2026 | non précisé | non communiqué |
| Plaine des Tourelles (été) | du 6 juillet au 14 août 2026 | 4–9 ans | non communiqué |
| Plaine Geron | du 6 juillet au 14 août 2026 | 2,5–5 ans | non communiqué |
| Plaine Deru - Rouheid | du 6 juillet au 14 août 2026 | 6–12 ans | non communiqué |

Sortie complète (25 activités, 4 communes) : `scrapers/output/activites.json`
et `scrapers/output/activites.csv` après exécution de
`scrapers/run_all.py`.

## Prochaine étape suggérée

Le socle est validé sur un 2e site iMio réel. Les cas plus difficiles
identifiés par l'investigation d'élargissement (Herstal/Waremme → PDF,
Huy/Sprimont → page hub, Oupeye → image, Aywaille → plateforme tierce)
restent à traiter un par un — chacun demandera probablement une brique
technique supplémentaire (extraction PDF texte, notamment) avant de
justifier son propre effort de mutualisation.
