# Stagéo — Investigation technique (24/08/2026)

## ⚠️ Limite de cette session

L'environnement d'exécution cloud utilisé pour cette session bloque tout accès
réseau sortant vers des domaines externes (proxy d'égression : `my.one.be`,
`wikipedia.org`, `odwb.be`, `neupre.be`, etc. tous rejetés — y compris pour
un navigateur headless Playwright). Seul l'outil de recherche web indexée a
fonctionné. Il n'a donc **pas été possible d'ouvrir un vrai navigateur sur
my.one.be ou APSCHOOL pour inspecter les requêtes réseau en direct** comme
prévu initialement.

Les constats ci-dessous viennent de recherches web (pages publiques indexées,
PDF de communes, articles ONE/pro.one.be) et non d'une inspection live du
trafic réseau. **Ils doivent être re-vérifiés avec un accès réseau réel**
(nouvel environnement avec accès internet complet, ou session locale) avant
de coder quoi que ce soit dessus. C'est la première étape à refaire.

---

## Tâche 1 — my.one.be

**Fonctionnement observé (via doc/articles publics) :**
- Recherche par sujet ("Plaines et stages" entre autres), puis un champ
  "Localisation" (code postal / adresse), résultats affichés sur carte +
  liste à gauche, avec filtres additionnels ("Filtrer les résultats").
- Fiche détail par activité : adresse, horaires, contact, personne de
  contact.
- Les données proviennent de **pro.one.be** (portail professionnel) : les
  organisateurs y encodent leurs activités (plaines et stages, sous forme
  résidentielle "séjours" ou non-résidentielle "plaines"), publication sur
  my.one.be depuis février (année non précisée dans les sources trouvées).
  Les deux portails partagent la même donnée centrale ("feeding three
  portals" selon le guide pro.one.be).

**Ce qui reste à vérifier en live (non confirmé) :**
- Si my.one.be charge les résultats via un **appel JSON/XHR** en arrière-plan
  (très probable vu l'UX carte+liste+filtres dynamiques, mais aucune preuve
  technique trouvée — aucune mention d'Algolia/Elasticsearch/API publique
  dans les sources indexées).
- L'URL exacte de cette API, son schéma de réponse (places restantes ?
  contact direct ? âge exact ou tranche ?).
- Si l'API nécessite une clé/session ou est librement interrogeable.
- Le contenu du `robots.txt` et des CGU de my.one.be (à lire avant tout
  scraping, même léger).

**Conclusion Tâche 1 :** hypothèse raisonnable qu'une API JSON existe
derrière le formulaire de recherche, mais **non confirmée** — nécessite une
vraie session de navigation avec inspection réseau (DevTools ou Playwright)
avant de décider de l'approche technique.

---

## Tâche 2 — APSCHOOL

**Structure d'URL confirmée et répétée sur plusieurs communes** (trouvé pour
au moins 4 communes différentes) :

```
https://plateforme.apschool.be/authentication/extrascolaireInscription/accueil/{ID}
https://plateforme.apschool.be/authentication/plaineinscription/accueil/{ID}
https://portail.apschool.be/authentication/plaineinscription/accueil/{ID}
```

Exemples trouvés :
- Neupré → `.../extrascolaireInscription/accueil/211`
- Chaumont-Gistoux → `.../plaineinscription/accueil/39`
- Une autre commune (non identifiée) → `.../extrascolaireInscription/accueil/181`
- Saint-Ghislain → `portail.apschool.be/.../plaineinscription/accueil/129`

C'est une **bonne nouvelle structurelle** : la plateforme est bien
multi-tenant avec un identifiant numérique de commune/organisme dans l'URL,
ce qui rendrait un scraper générique réutilisable *si* le contenu est
accessible publiquement. Deux nuances à vérifier en live :
- Deux sous-domaines coexistent (`plateforme.` et `portail.apschool.be`) —
  pas un seul point d'entrée.
- Deux types de parcours (`extrascolaireInscription` vs `plaineinscription`)
  qui ne couvrent peut-être pas exactement les mêmes données.

**Accès public vs compte parent — non confirmé avec certitude :**
Le chemin `/authentication/...` suggère une porte d'authentification dès
l'entrée. Les guides d'utilisation trouvés (Oupeye, Saint-Stanislas,
Remicourt) décrivent le parcours **après connexion** : création de compte,
saisie des données de l'enfant, des parents, des données médicales, avant
même d'arriver au catalogue des stages. Rien dans les sources indexées ne
confirme un catalogue consultable *sans* compte. Cela pointe plutôt vers un
mur d'authentification pour voir les places disponibles — mais à vérifier
en ouvrant réellement une de ces URLs sans se connecter.

**Conclusion Tâche 2 :** structure d'URL prévisible et couvrant plusieurs
communes (bon signe pour la couverture), mais **accès public au catalogue
probablement bloqué par compte** (mauvais signe pour l'automatisation sans
créer de comptes — ce qui est exclu par la contrainte du projet). À
confirmer en ouvrant une URL de commune en navigation privée, sans se
connecter.

---

## Tâche 3 — Open data (ODWB / opendata.brussels.be)

**odwb.be :**
- Aucun jeu de données trouvé avec places disponibles / dates en temps réel
  pour les plaines ou stages.
- Un jeu de données pertinent en tant que **répertoire d'organisateurs**,
  pas de disponibilités : *"Les associations de jeunesse de la Fédération
  Wallonie-Bruxelles"* (centres de jeunes, coordinations, opérateurs de
  formation, mouvements de jeunesse) —
  https://www.odwb.be/explore/dataset/les-associations-de-jeunesse-de-la-federation-wallonie-bruxelles/
  Utile potentiellement pour constituer une liste de cibles à couvrir, pas
  pour alimenter des alertes de places.

**opendata.brussels.be :**
- *"Maisons des Enfants"* (accueil 6-12 ans après l'école et pendant les
  vacances, Ville de Bruxelles) — dataset de localisation, pas de
  places/dates en temps réel.
- Rien trouvé de plus proche d'un catalogue de plaines/stages avec
  disponibilités.

**Conclusion Tâche 3 :** pas de source open data "prête à l'emploi" pour les
disponibilités en temps réel. Les jeux de données trouvés sont utiles en
appoint (répertoires d'organisateurs / lieux), pas comme source principale.

---

## Synthèse — ce qui est automatisable

| Piste | Statut | Effort estimé |
|---|---|---|
| ODWB — répertoire d'associations de jeunesse | **Facile** : dataset ouvert, structuré, exportable (CSV/JSON via l'explorateur ODWB) | Faible — bon pour constituer une liste de cibles/organisateurs, pas pour les disponibilités |
| opendata.brussels.be — Maisons des Enfants | **Facile** mais périmètre limité (localisation, pas dispo) | Faible |
| my.one.be | **Effort modéré, à confirmer** — si une API JSON existe bien derrière la recherche (probable mais non vérifié), ce serait la source la plus riche (âge, dates, lieu, contact). Sinon scraping HTML classique, plus fragile | Modéré, conditionné à une vraie inspection réseau |
| APSCHOOL (Neupré, Chaumont-Gistoux, autres communes) | **Probablement bloqué** sans compte — structure d'URL prévisible (bon pour la couverture multi-communes) mais catalogue vraisemblablement caché derrière l'authentification (mauvais pour l'automatisation sans compte, ce qui est exclu) | Bloqué / à confirmer en priorité |
| Sites communaux "faits maison" (hors ONE/APSCHOOL) | Inconnu | Non exploré cette session |

## Prochaine étape recommandée

Avant d'écrire le moindre script définitif :
1. **Refaire cette investigation avec un vrai accès réseau** (nouvel
   environnement cloud avec accès internet complet choisi à la création, ou
   session locale Claude Code) pour :
   - Confirmer/infirmer l'API JSON de my.one.be (DevTools → onglet Réseau
     pendant une recherche) et documenter son schéma exact.
   - Ouvrir une URL APSCHOOL de commune **sans se connecter** pour confirmer
     si le catalogue est visible ou non avant authentification.
   - Lire les CGU / robots.txt de my.one.be avant toute automatisation.
2. Selon ces résultats, décider ensemble par quelle source commencer (my.one.be
   semble le meilleur candidat si l'API existe ; APSCHOOL nécessitera
   probablement un partenariat/accord avec les communes plutôt qu'un scraper,
   vu le mur de connexion).
