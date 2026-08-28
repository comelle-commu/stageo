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

Ajoutées lors du 2e passage (28/08/2026, section F) :

- **Sport Fun Activ'** ✅ (via `iclub.py`, plateforme MyiClub `www7.iclub.be`
  ClubID=712) - 40 activités sur 4 implantations distinctes, chacune
  rattachée à sa vraie commune : Sprimont (Dolembreux), Trooz (Fraipont),
  Seraing, Esneux. Découverte importante : iClub est lui-même une
  plateforme de réservation MUTUALISÉE entre plusieurs clubs, comme le
  widget Omnia pour les communes - la structure HTML (`register.asp?
  ClubID=...`) déjà supportée par `iclub.py` a fonctionné sans adaptation,
  seul le format d'âge "X an(s) et Y mois" a nécessité un nouveau regex.
- **La Ferme des Enfants de Liège** ✅ `ferme_des_enfants.py` - 14
  activités (toutes saisons confondues, dont Toussaint x2 + Noël x1
  encore à venir). Donnée en deux temps : liste/prix/stock via l'API
  publique WooCommerce Store, dates/âge/lieu réels seulement dans le HTML
  de chaque page produit (bloc constructeur Divi).

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
| Sport Fun Activ' (sportfunactiv.be) | ✅ Construit | Le lien externe menait à `www7.iclub.be` ClubID=712 (plateforme MyiClub) - ajouté à `CLUBS` dans `iclub.py`, 40 activités sur 4 communes (Sprimont, Trooz, Seraing, Esneux) |
| Théâtre Le Moderne (lemoderne.be) | Confirmé impasse (28/08/2026) | Page "Stages" entièrement lue : ne liste que la "Saison 25-26" (dernière date 09-13/08/2026, déjà passée). Rien publié pour Toussaint/Noël 2026 au 28/08 - à revérifier plus tard, pas de PDF/actualité alternative trouvée |
| La Ferme des Enfants (lafermedesenfantsdeliege.be) | ✅ Construit | Catalogue WooCommerce, voir section A - `ferme_des_enfants.py` |
| Liège Parkour School | À approfondir | Stages réels (Parkour/Multisports, 114-115€) mais dates encore affichées sur juillet-août 2026, pas Toussaint |
| Sportforfun (sportforfun.be) | À surveiller | Plateforme de stages avec lieux listés, affiche "Aucune activité pour le moment" - à réessayer plus tard |
| iClub / CSM asbl (www16.iclub.be) | Confirmé impasse (28/08/2026) | `www16.iclub.be` redirige maintenant vers `iclubsport.biz`, le site vitrine du LOGICIEL iClub lui-même (plus une page club). Le lien historique `covid.iclub.be/register.asp?ClubID=99` redirige en cascade vers `www2.iclub.be` puis `notinproduction2.asp` - le club CSM asbl semble avoir été décommissionné/migré vers un ClubID inconnu sur cette plateforme. Pas de nouvel ID à deviner sans plus d'info (voir avertissement dans `iclub.py`) |
| Asbl PARI, École du cirque Polichinelle, Stage 100% Ado | Non vérifiés | Noms croisés dans un article de blog (todayinliege.be), jamais recherchés individuellement |

## G. Piste explorée et abandonnée : agenda.enwallonie.be en recherche directe

Voir section dédiée dans `README.md` ("Agenda Omnia") - l'API `@@omnia-api`
est authentifiée (Keycloak), et la recherche Plone classique (`@@search`)
renvoie toujours 0 résultat quel que soit le paramétrage essayé. Le
carrousel de la page d'accueil (méthode retenue, voir `agenda_omnia.py`)
fonctionne sans aucune authentification.

## Prochaines étapes recommandées, par ordre de rentabilité

1. Vérifier les ~23 communes de la section D (jamais checkées) - probablement le plus gros gisement restant, mais coûteux en temps (une vérification à la fois).
2. **Liège Parkour School** et **Sportforfun** (section F) - dates pas encore alignées sur Toussaint/Noël 2026, à réessayer.
3. Rechercher individuellement **Asbl PARI**, **École du cirque Polichinelle**, **Stage 100% Ado** (section F, jamais vérifiés).
4. Republier ce document mis à jour à chaque session de ratissage, pour ne pas reperdre le fil.

*(Malmedy, Verlaine, Dalhem, Wanze, Le Moderne, iClub/CSM : confirmées
comme impasses le 28/08/2026, voir sections C2/F - retirées de cette
liste. Sport Fun Activ' et La Ferme des Enfants : construits le
28/08/2026, voir section A.)*
