# Élargissement géographique : Namur, Hainaut, Brabant wallon, Luxembourg — 25/08/2026

## Contexte

Demande explicite : avoir "un peu d'activités partout en Wallonie et à
Bruxelles" pour disposer de quelque chose de fonctionnel à proposer, plutôt
que de continuer à approfondir une seule plateforme (PromoSport) ou une
seule zone (Liège/Bruxelles).

Constat de départ : les scrapers communaux existants (Ans, Seraing,
Neupré, Verviers, Herstal, Huy, Sprimont) couvrent uniquement la province
de Liège. Mais **le socle iMio construit pour ces communes n'est pas
spécifique à Liège** — c'est une plateforme utilisée par des communes dans
toute la Wallonie. Plutôt que d'investir dans une nouvelle source technique,
le plus rapide pour élargir la couverture géographique était de vérifier
quelles grandes communes des autres provinces utilisent aussi iMio.

## Communes vérifiées iMio (8/8 confirmées)

Méthode : suivre la redirection du `robots.txt` de chaque commune - toutes
les communes iMio redirigent vers `static.imio.be/robots.txt`
(`Crawl-delay: 120` identique partout, déjà géré par
`common.IMIO_DOMAINS`).

| Commune | Province | Statut |
|---|---|---|
| **Mons** | Hainaut | ✅ Scraper construit (`mons.py`) |
| **Arlon** | Luxembourg | ✅ Scraper construit (`arlon.py`) |
| Namur | Namur | 🟡 iMio confirmée, page pas encore trouvée (voir ci-dessous) |
| Nivelles | Brabant wallon | 🟡 iMio confirmée, article introuvable (404) |
| La Louvière | Hainaut | 🟡 iMio confirmée, page pas encore vérifiée |
| Ottignies-Louvain-la-Neuve | Brabant wallon | 🟡 iMio confirmée, page pas encore vérifiée |
| Bastogne | Luxembourg | 🟡 iMio confirmée, page pas encore vérifiée |
| Ciney | Namur | 🟡 iMio confirmée, page pas encore vérifiée |

Tournai (Hainaut) a aussi été testée : robots.txt **403 Forbidden**
(comme Floreffe) - pas encore de scraper possible sans clarification.

## Mons — ✅ construit

Page unique en prose (comme Ans), décrivant les plaines d'été 2026 :
4 semaines, 3 lieux (Cuesmes, Obourg, Havré), tarif par jour, âge 2,5-12
ans. `disponibilite` détecte correctement "CLÔTURÉ" (les pré-inscriptions
2026 étaient closes au 31/05, donc c'est un résultat honnête, pas un bug).

## Arlon — ✅ construit

Page unique listant 2 périodes (Printemps, Été), même structure répétée
par bloc. Point à noter : **le site source lui-même contient une typo**
(le bloc "Été" mentionne "2025" alors que le contexte dit "cet été 2026")
- reproduit tel quel plutôt que "corrigé" silencieusement, pour rester
fidèle à ce qui est réellement publié.

## Namur — 🟡 en attente (friction technique, pas légale)

iMio confirmée, mais les pages individuelles de plaines trouvées par
recherche (ex. la page de la plaine du Parc Astrid à Jambes) redirigent
vers une page de login e-guichet ("Les cookies ne sont pas activés")
plutôt que d'afficher le contenu. Namur semble structurer l'info
différemment des autres communes (une sous-page par lieu plutôt qu'une
page de synthèse) - la bonne URL publique n'a pas été retrouvée cette
session.

## Nivelles — 🟡 en attente

Un article "Plaine de vacances communale - Été 2026 : Inscriptions" trouvé
par recherche, mais son URL renvoie 404 en accès direct (avec ou sans le
paramètre de tracking `?u=...` présent dans le lien indexé) - probablement
expiré ou déplacé.

## La Louvière, Ottignies-LLN, Bastogne, Ciney — 🟡 en attente

Confirmées iMio (robots.txt), mais la page stages/plaines elle-même n'a pas
encore été localisée/vérifiée cette session - le temps a été priorisé sur
une commune par province manquante (Mons pour le Hainaut, Arlon pour le
Luxembourg) plutôt que l'exhaustivité. Prochaine étape naturelle : même
méthode que Mons/Arlon (recherche de la page "plaines"/"stages", vérif
`find_plone_content()`).

## Impact sur la couverture géographique

Avant cet ajout, la répartition par lieu montrait déjà une couverture
correcte grâce à ADEPS et Cap Sciences (qui listent des activités dans tout
le pays), mais aucune commune hors Liège. Avec Mons et Arlon :

- **Liège** : Ans, Seraing, Neupré, Verviers, Herstal, Huy, Sprimont (+ ADEPS/Cap Sciences/iClub ponctuellement)
- **Hainaut** : Mons (commune) + ADEPS (Froidchapelle, Loverval, Seneffe, Péronnes)
- **Namur** : ADEPS (Jambes) - pas encore de commune dédiée
- **Luxembourg** : Arlon (commune) + ADEPS (Neufchâteau, Vielsalm)
- **Brabant wallon** : Cap Sciences (Nivelles, Louvain-la-Neuve) + ADEPS - pas encore de commune dédiée
- **Bruxelles** : Cap Sciences (Auderghem, Ixelles, Etterbeek, Anderlecht...) + iClub (Uccle)

Les 4 communes encore en attente (surtout Namur et Nivelles, provinces
avec le moins de communes propres) sont la suite logique la plus rentable
si on veut renforcer encore la couverture.
