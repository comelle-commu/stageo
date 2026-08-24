# Stagéo — Cas difficiles : PDF et pages hub (24/08/2026)

## Contexte

Suite au backend Supabase fonctionnel (4 communes, 25 activités —
`docs/supabase-backend-2026-08-24.md`), cette session élargit le scraper
aux cas plus difficiles identifiés par l'investigation d'élargissement :
extraction PDF (Herstal, Waremme), pages "hub" (Huy, Sprimont), et
vérification de l'URL Hannut. Oupeye et Aywaille restent volontairement de
côté (consigne explicite).

## Nouvelle capacité : extraction PDF dans `common.py`

`fetch_pdf_bytes()`, `is_pdf()`, `extract_pdf_tables()` (pdfplumber),
`extract_pdf_text()` (pypdf) — texte natif uniquement, pas d'OCR (un PDF
scanné donnera un texte/tableau vide, pas une erreur, à l'appelant de
vérifier). `fetch_pdf_bytes()` réutilise `respectful_get()`, donc le
Crawl-delay iMio s'applique aussi aux téléchargements de PDF.

**Piège rencontré et documenté dans le code** : une URL qui se termine en
`.pdf` n'est pas forcément un vrai PDF. Le lien "Règlement d'ordre
intérieur ... .pdf" sur la page Ans sert en réalité un fichier **.docx**
(`Content-Type: application/vnd.openxmlformats-officedocument...`) — le
`.pdf` fait juste partie du slug Plone, pas du format réel. `is_pdf()`
vérifie la signature `%PDF-` des bytes avant de traiter quoi que ce soit
comme un PDF.

## Tâche 1 — Herstal : GO, 57 activités

Le PDF `Stages congé été 2026.pdf` est un export Word propre (2 pages),
avec un vrai tableau détecté par `pdfplumber` : une ligne d'en-tête "Du X au
Y [mois]" par semaine, suivie d'une ligne par stage (âge, thème, organisme,
contact, lieu, horaire, prix, garderie). `herstal.py` traite toutes les
lignes de tous les tableaux comme un flux continu (**piège rencontré** : le
tableau continue sur la page 2 sans répéter sa ligne d'en-tête de semaine —
traiter chaque page indépendamment aurait perdu le rattachement à la bonne
semaine pour les premières lignes de la page 2).

**Résultat : 57 activités extraites**, la commune la plus riche du jeu de
données à ce jour — âge précis, prix, contact direct, horaires, garderie
pour chaque stage. Deux doublons littéraux détectés dans le PDF source lui-
même (même thème/organisme/semaine répété deux fois) — voir section
Supabase plus bas.

### Vérification secondaire : les PDF Ans/Verviers contiennent-ils l'info manquante ?

Consigne initiale : vérifier si les PDF déjà repérés sur Ans et Verviers
contiennent "le prix manquant". En pratique, le champ manquant diffère par
commune (Ans a déjà son prix en HTML, c'est l'**âge** qui manque ; Verviers
a déjà âge et dates, c'est le **prix** qui manque) — vérifié le champ
réellement absent pour chacune plutôt que de suivre l'énoncé au pied de la
lettre :

- **Ans** (`ROI CCJV 2025.docx`, en réalité un Word malgré l'URL `.pdf`) :
  **contient bien la tranche d'âge** — *"les enfants âgés de 2 ½ ans à 12
  ans"*. Confirmé présent, pas intégré au parseur cette session (consigne),
  mais vaut clairement le coup pour une prochaine passe : donnée propre et
  facile à extraire (`python-docx`, pas dans les dépendances actuelles).
- **Verviers** (règlement d'ordre intérieur + projet pédagogique, deux vrais
  PDF) : **aucune mention de prix dans les deux documents** (recherche de
  "prix", "tarif", "montant", "gratuit", "€" — aucun résultat). Le tarif
  n'est probablement communiqué qu'au moment de l'inscription en ligne, pas
  publié à l'avance. Pas de piste PDF à exploiter pour ce champ.

## Tâche 2 — Waremme : structure différente d'Herstal, EN_ATTENTE

Le PDF de Waremme (`Les stages 2026 Ete.pdf`, 38 pages, 1,2 Mo) n'est **pas**
un export tableau propre comme Herstal : `pdfplumber.extract_tables()` ne
détecte aucun tableau sur les pages testées. L'inspection des positions de
mots (`page.extract_words()`) montre une mise en page en colonnes alignées
par coordonnées x/y (brochure), pas de vraies bordures de cellule — le
signal est là (labels "Heures / Âges / Prix / Inscription / Lieu"
cohérents) mais nécessiterait un regroupement positionnel des mots, pas la
même extraction qu'Herstal. Effort nettement supérieur, non développé cette
session (voir `waremme.py` pour le détail et la piste à suivre plus tard).

Bonus contexte : la page précise explicitement que les opérateurs listés
"ne dépendent pas de la ville de Waremme" — nuance proche du cas
Aywaille/ActivKids (offre tierce agrégée), même si ici en PDF statique
plutôt qu'en plateforme tierce.

## Tâche 3 — Pages hub : Huy et Sprimont

**Huy** : la structure réelle diverge de l'hypothèse de départ ("hub →
beaucoup de sous-pages d'activités"). Le vrai parcours est : hub ATL →
"Les stages" (hub par période : Détente, Printemps, Été, Automne, Hiver) →
sous-page par période listant plusieurs organisateurs (commune + associatif).
`huy.py` suit ce chemin (2 requêtes, Crawl-delay 120s respecté entre les
deux) et extrait le programme communal officiel identifiable par son
en-tête ("Le Repaire des P'tits Loups" pour l'été) ; les nombreuses offres
associatives sur la même page (clubs sportifs, asbl...) restent hors
scope cette session — format trop hétérogène pour une extraction fiable,
laissé consultable via `lien_source`.

Portée volontairement limitée à la page "Congé d'été" (période actuellement
pertinente) — étendre aux 4 autres périodes est mécanique (même code, seule
l'URL et le nom du programme officiel — "Toboggan" pour les autres
périodes — changent) mais coûte 120s de Crawl-delay par page
supplémentaire.

**Deux bugs rencontrés et corrigés en cours de route** (voir commentaires
dans `huy.py`) :
1. Frontière de bloc mal calée : chercher "la prochaine séquence en
   majuscules" comme fin de bloc échouait car "PLAINE COMMUNALE" (entre
   parenthèses juste après le titre) est lui-même en majuscules — remplacé
   par une frontière explicite ("LA MAISON DE L'ENFANT", l'organisateur
   suivant sur la page).
2. Sélection du mauvais lien : chercher `"ete"` en sous-chaîne de l'URL
   matchait aussi `"conge-de-detente-carnaval"` (qui contient "ete" dans
   "d**ete**nte") — remplacé par une recherche du texte exact "d'été".

**Résultat : 1 activité** (Le Repaire des P'tits Loups, dates/âge/prix/lieu
tous extraits correctement).

**Sprimont** : ce n'est en réalité pas un hub multi-pages mais une seule
page de type règlement (thème Plone Sunburst, `#content-core` plutôt que
`<main>` — confirme le repli prévu dans `find_plone_content()`). Contient
âge, prix (grille détaillée), horaires et lieux, mais **aucune date
calendaire** : le planning daté concret est publié comme une **image**
(`stages-ete-2026.png`, 832 Ko) — même blocage qu'Oupeye (OCR). `sprimont.py`
extrait ce qui est disponible en texte et signale explicitement dans le
champ `dates` que le planning détaillé est une image non traitée.

**Résultat : 1 activité** (infos partielles, dates signalées comme
indisponibles en texte).

## Tâche 4 — Hannut : URL à jour introuvable, pas encore publiée

L'URL périmée notée par l'investigation s'explique : Hannut republie un
article WordPress par période (`hannut.be/stages-{periode}-{annee}/`,
confirmé avec `stages-automne-2025` publié le 16/09/2025). **L'article pour
la période actuellement pertinente n'existe pas encore** :
`stages-automne-2026` → 404 au 24/08/2026, probablement publié mi-septembre
2026 à en juger par le calendrier 2025. Ce n'est donc pas un blocage
légal/technique comme Floreffe, mais un problème de calendrier — rien à
scraper pour l'instant, documenté comme `EN_ATTENTE`.

## Ce qui reste EN_ATTENTE (documenté, pas ignoré)

| Commune | Raison |
|---|---|
| Floreffe | robots.txt en 403 reproductible, non clarifié |
| Waremme | PDF en mise en page libre, pas de tableau détectable |
| Hannut | page de la période actuelle pas encore publiée |
| Oupeye | programme en image intégrée (OCR requis) |
| Aywaille | renvoie vers la plateforme tierce ActivKids (vérification légale non faite) |

## Run complet et import Supabase

```
Total activités : 84
  Ans          6 activités    1.6s
  Seraing      9 activités    1.1s
  Neupre       5 activités    1.1s
  Verviers     5 activités    0.9s
  Herstal     57 activités  126.0s   (2 requêtes, Crawl-delay iMio 120s)
  Huy          1 activités  122.1s   (2 requêtes, Crawl-delay iMio 120s)
  Sprimont     1 activités    1.8s
  Floreffe / Waremme / Hannut / Oupeye / Aywaille : EN_ATTENTE
```

**Import Supabase — un problème réel rencontré et corrigé** : le premier
upsert a échoué avec une erreur 500 (`ON CONFLICT DO UPDATE command cannot
affect row a second time`). Cause : le PDF Herstal contient deux doublons
littéraux (même thème/organisme/semaine répété deux fois dans le document
source), et PostgreSQL refuse qu'un même batch `INSERT ... ON CONFLICT DO
UPDATE` touche deux fois la même clé de conflit. Corrigé en dédupliquant
côté client (`supabase_client._dedupe_rows()`) sur la même clé que la
contrainte unique en base avant l'envoi.

**Résultat final : 82 lignes upsertées** (84 activités extraites - 2
doublons du PDF source). Vérifié avec `verify_supabase.py` : 82 lignes
confirmées côté Supabase, réparties comme attendu (Ans 6, Seraing 9, Neupré
5, Verviers 5, Herstal 55, Huy 1, Sprimont 1). Un second import consécutif
confirme l'absence de doublons (toujours 82 lignes).

## Comparaison avec la session précédente

| | Avant cette session | Après cette session |
|---|---|---|
| Communes actives | 4 (Ans, Seraing, Neupré, Verviers) | **7** (+ Herstal, Huy, Sprimont) |
| Communes EN_ATTENTE documentées | 1 (Floreffe) | **5** (Floreffe, Waremme, Hannut, Oupeye, Aywaille) |
| Activités en base Supabase | 25 | **82** |

## Prochaine étape suggérée

- Intégrer l'âge trouvé dans le règlement Ans (2,5-12 ans) — gain rapide,
  nécessite `python-docx` (pas encore dans `requirements.txt`).
- Waremme : développer l'extraction positionnelle (x/y) si le volume de
  contenu (38 pages) justifie l'effort par rapport aux autres priorités.
- Étendre `huy.py` aux 4 autres périodes (Détente, Printemps, Automne,
  Hiver) — mécanique, juste coûteux en Crawl-delay.
- Revérifier Hannut après mi-septembre 2026 (calendrier de publication
  observé sur l'édition 2025).
- Décider si les offres associatives (Huy, Waremme) valent un effort de
  parsing dédié, ou si Stagéo se concentre sur l'offre communale officielle.
