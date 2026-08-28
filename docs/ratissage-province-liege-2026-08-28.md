# Ratissage province de Liège (28/08/2026)

Contexte : la fondatrice a son carnet d'adresses de prospection concentré
sur la province de Liège - objectif de couverture la plus complète possible
sur cette province en particulier, pas seulement "encore quelques sources".
Ce document consolide tout ce qui a été vérifié pendant cette session pour
reprendre efficacement la prochaine fois, plutôt que de repartir de zéro.

## A. Couvertes avec de vraies données aujourd'hui

Communes/localités avec un scraper actif ET des activités réellement
extraites (voir `README.md` pour le détail technique de chacune) : Ans,
Awans (Côté Campagne, cassé dans ce bac à sable réseau uniquement),
Chaudfontaine, Engis, Fexhe-le-Haut-Clocher, Grâce-Hollogne, Héron,
Herstal, Herve, Huy, Liège (+ Jeunesse Ardente : 30 activités/14
organismes, + Besace ASBL : 1 activité), Marchin, Nandrin, Neupré, Olne,
Saint-Georges-sur-Meuse, Seraing, Spa, Sprimont, Verviers, Waremme,
Welkenraedt, Henri-Chapelle/Herbesthal/Heusy/Tiège/La Calamine (Dimension
Sport), Geer (Agenda Omnia : 8 activités Toussaint), **Stavelot (13
activités, Toussaint + Noël, brochure PDF)**, **Faimes (9 activités,
Toussaint/Noël/Détente/Printemps, brochure PDF)** - ces deux dernières
ajoutées après la rédaction initiale de ce document, voir section C mise
à jour.

## B. Enregistrées dans `agenda_omnia.py` mais 0 activité pour l'instant

Ces 17 communes ont le widget "Agenda" partagé (voir README) mais n'ont
rien publié pour la Toussaint au 28/08/2026. **Aucune action requise** :
le run hebdomadaire les réextraira automatiquement dès publication.

Ferrières, Blegny, Trooz, Villers-le-Bouillet, Amay, Dison, Flémalle,
Juprelle, Pepinster, Remicourt, Saint-Nicolas, Theux, Thimister-Clermont,
Wasseiges, Oupeye, Hamoir.

## C. Page trouvée, PAS de widget Omnia

### C1. Construits (28/08/2026)

- **Stavelot** ✅ `stavelot.py` — 13 activités (Toussaint + Noël). La page
  web "Plaines de jeux" elle-même était vide ; la vraie donnée était dans
  un PDF lié depuis une actualité séparée ("Coordination Accueil Temps
  Libre"). Voir README pour le détail de l'extraction (flyer 2 colonnes,
  pas de tableau propre).
- **Faimes** ✅ `faimes.py` — 9 activités (Toussaint x2, Noël, Détente,
  Printemps x2). Même leçon : la page "Plaine de jeux du Cortil" ne parle
  que de l'infrastructure physique - la vraie donnée est dans le PDF lié
  depuis l'actualité "Découvrez la brochure extrascolaire 2026-2027".

### C2. Confirmées comme impasses (28/08/2026)

La piste "chercher dans les actualités récentes" (qui a fonctionné pour
Stavelot/Faimes) a été retentée systématiquement sur ces 4 communes -
aucune n'a de brochure PDF récente. À ne pas retenter sans nouvelle
information (ex. un article publié après le 28/08).

- **Malmedy** — `https://www.malmedy.be/vivre-a-malmedy/enfance/plaines-de-jeux` — juste une liste de localités avec plaine "extérieure"/"couverte", aucune date. Rien trouvé dans `/actualites` non plus.
- **Verlaine** — `https://www.verlaine.be/loisirs/stages-enfants` — texte périmé (mentionne juillet-août **2021**). Une actualité "Stages - Congés été 2026" existe mais son contenu réel est vide (seuls des PDF de navigation hors-sujet, guide des aînés etc., apparaissent sur la page).
- **Dalhem** — `https://www.dalhem.be/loisirs/stages-de-vacances` — page quasiment vide (18 caractères de contenu : juste le titre). Rien de neuf dans `/actualites`.
- **Wanze** — a une "Brochure Sports et Loisirs" décrite en détail sur sa page dédiée, mais s'avère être un répertoire de clubs à l'année (enfants/ados/adultes), pas des stages de vacances datés - et aucun lien PDF n'est même présent sur cette page.
- **Wanze** — `https://www.wanze.be/commune/education/stages` — texte de présentation générale du dispositif, aucune date/activité listée.

## D. Jamais vérifiées (ni robots.txt, ni contenu)

Anthisnes, Aubel, Bassenge, Berloz, Beyne-Heusay, Burdinne, Clavier,
Crisnée, Donceel, Jalhay, Lontzen, Modave, Oreye, Ouffet, Plombières,
Soumagne, Tinlot, Trois-Ponts, Comblain-au-Pont (erreur proxy au moment du
check, à réessayer), Limbourg (timeout), Lincent (timeout), Lierneux
(statut 202, à réessayer), Stoumont (timeout).

## E. Hors périmètre : communes germanophones

Eupen, Kelmis (La Calamine - déjà couverte via Dimension Sport, à
vérifier si son contenu est bien francophone), Raeren, Büllingen,
Bütgenbach, Amblève, Burg-Reuland, Sankt-Vith, Waimes dépendent de la
**Communauté germanophone**, pas de la FWB - calendrier scolaire différent
de celui utilisé pour le filtre par semaine de vacances. Volontairement
non ratissées.

## F. ASBL/organismes trouvés via recherche Google (28/08/2026), statut par item

| Nom | Statut | Détail |
|---|---|---|
| Sport-Adeps (activites.sport-adeps.be) | Déjà couvert | C'est la source réelle de `adeps.py` (361 activités) - pas une nouvelle source |
| Latitude Jeunes | Déjà couvert | Apparaît déjà via `jeunesse_ardente.py` |
| Réseau IDée | Exclu | robots.txt interdit ClaudeBot |
| filous.be | Exclu | robots.txt interdit ClaudeBot |
| SportFinder (sport-finder.com) | Exclu | 403 sur toutes les requêtes, même robots.txt |
| IFAPME, Le Forem, Culture.be | Hors sujet | "Stage" = stage professionnel/formation, pas activité enfant |
| B3 (Province de Liège) | Écarté | Un seul événement ponctuel trouvé ("Stage vidéo"), pas un programme récurrent |
| Sport Fun Activ' (sportfunactiv.be) | À approfondir | ASBL réelle (2,5-12 ans, sport/cirque/magie) mais sa page "Nos stages" renvoie vers un outil de réservation externe sans dates visibles directement dessus - trouver ce lien externe |
| Théâtre Le Moderne (lemoderne.be) | À approfondir | Petit atelier théâtre à partir de 5 ans, page stages trouvée mais dates pas encore lues jusqu'au bout |
| La Ferme des Enfants (lafermedesenfantsdeliege.be) | À approfondir | Page "Les stages" est un index de catégories (dont "Stages d'automne") sans dates directes - suivre le lien de la sous-catégorie Toussaint |
| Liège Parkour School | À approfondir | Stages réels (Parkour/Multisports, 114-115€) mais dates encore affichées sur juillet-août 2026, pas Toussaint |
| Sportforfun (sportforfun.be) | À surveiller | Plateforme de stages avec lieux listés, affiche "Aucune activité pour le moment" - à réessayer plus tard |
| iClub / CSM asbl (www16.iclub.be) | Confirmé NOUVEAU (pas de doublon) | `iclub.py` ne couvre actuellement que 2 clubs, tous deux à Uccle (Royal Léopold Club, Royal Racing Club de Bruxelles) - CSM asbl (Embourg, Chaudfontaine, Crisnée, Grâce-Hollogne, Herstal, Liège) est un tenant distinct. Mais `www16.iclub.be` redirige vers `iclubsport.biz` (ClubID=99 sur l'ancien domaine `covid.iclub.be`) et il y a aussi un lien vers `iclubsport.academy` - domaines différents du pattern `<sous-domaine>.iclub.be` utilisé par `iclub.py`, structure de page à revérifier avant d'ajouter à `CLUBS` |
| Asbl PARI, École du cirque Polichinelle, Stage 100% Ado | Non vérifiés | Noms croisés dans un article de blog (todayinliege.be), jamais recherchés individuellement |

## G. Piste explorée et abandonnée : agenda.enwallonie.be en recherche directe

Voir section dédiée dans `README.md` ("Agenda Omnia") - l'API `@@omnia-api`
est authentifiée (Keycloak), et la recherche Plone classique (`@@search`)
renvoie toujours 0 résultat quel que soit le paramétrage essayé. Le
carrousel de la page d'accueil (méthode retenue, voir `agenda_omnia.py`)
fonctionne sans aucune authentification.

## Prochaines étapes recommandées, par ordre de rentabilité

1. Suivre les liens externes de **Sport Fun Activ'** et finir la lecture de **Le Moderne** et **La Ferme des Enfants** (section F) - proches d'être exploitables.
2. Construire **iClub/CSM** (confirmé nouveau, pas de doublon) une fois la structure de `iclubsport.biz`/`iclubsport.academy` vérifiée.
3. Vérifier les ~23 communes de la section D (jamais checkées) - probablement le plus gros gisement restant, mais coûteux en temps (une vérification à la fois).
4. Republier ce document mis à jour à chaque session de ratissage, pour ne pas reperdre le fil.

*(Malmedy, Verlaine, Dalhem, Wanze : confirmées comme impasses le
28/08/2026, voir section C2 - retirées de cette liste.)*
