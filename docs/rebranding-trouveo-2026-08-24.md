# Renommage du projet : Stagéo → Trouvéo (24/08/2026)

## Ce qui a été fait automatiquement

- **Landing page** (`index.html`) : nouvelle identité visuelle et
  nouvelle copie fournies par toi, intégrées avec la logique
  d'inscription Brevo déjà en place (voir
  `docs/brevo-signup-2026-08-24.md`). Nom affiché, titre de page,
  wordmark, footer et adresse de contact (`hello@trouveo.be`) : tous
  sous "Trouvéo".
- **Icône** : `stageo-icon.png` supprimé, remplacé par
  `trouveo-icon.png`.
- **Scraper** (`scrapers/common.py`, `scrapers/README.md`) : le
  User-Agent envoyé aux sites communaux passe de
  `StageoScraperBot/0.1 (...)` à `TrouveoScraperBot/0.1 (...)`. C'est
  la seule partie du scraper visible depuis l'extérieur (identifiant
  transmis à chaque requête HTTP) — le reste (noms de fichiers, slugs
  de communes, table Supabase `activites`) est un détail technique
  interne, sans rapport avec le nom de marque, donc inchangé.
- Commentaire de code obsolète corrigé dans
  `netlify/functions/brevo-signup.js` (référençait encore l'ancien
  nom de fichier `stageo-landing.html`, déjà renommé en `index.html`
  lors d'une étape précédente).

## Ce qui reste sous le nom "Stagéo" — et pourquoi je ne l'ai pas changé moi-même

Trois éléments techniques portent encore l'ancien nom. Aucun n'est
visible par un visiteur du site, mais chacun nécessite une action
que je ne peux pas — ou ne dois pas — faire à ta place :

### 1. Le dépôt GitHub `comelle-commu/stageo`

Le renommer changerait son URL (`github.com/comelle-commu/stageo` →
`.../trouveo`). GitHub redirige automatiquement l'ancienne URL vers
la nouvelle pendant un certain temps, donc ce n'est pas bloquant en
soi — mais c'est une action que je préfère te laisser déclencher
toi-même plutôt que de la faire sans confirmation explicite, l'accès
de cette session étant justement configuré sur le nom actuel du
dépôt.

**Pour le faire toi-même** : sur GitHub, dans le dépôt → **Settings**
(onglet tout en haut) → en haut de la page **General** → champ
**Repository name** → remplace `stageo` par `trouveo` → **Rename**.

### 2. Le domaine `stageo.netlify.app`

Netlify permet de changer gratuitement le sous-domaine
`*.netlify.app` du site (pas besoin d'acheter un nom de domaine pour
ça). Je n'ai pas d'accès à ton compte Netlify pour le faire.

**Pour le faire toi-même** : site Netlify → **Site configuration** →
**General** → **Site details** → **Change site name** → remplace
`stageo` par `trouveo` (si disponible) → le site sera alors accessible
sur `trouveo.netlify.app`.

Si tu veux un vrai nom de domaine (`trouveo.be` par exemple) plutôt
que le sous-domaine Netlify gratuit, c'est un achat chez un
registrar (ex. DNS Belgium pour un `.be`, ou directement depuis
Netlify → **Domain management** → **Add a domain**) — une démarche
qui implique un paiement, donc à faire toi-même également.

### 3. Historique des docs (`docs/*.md`)

Les documents précédents (`brevo-signup-2026-08-24.md`,
`automatisation-github-actions-2026-08-24.md`, etc.) mentionnent
`stageo-landing.html`, `stageo-icon.png` et `stageo.netlify.app` —
ce sont des faits historiques exacts au moment où ils ont été écrits
(noms de fichiers réellement utilisés, URL réellement testée). Je ne
les ai pas réécrits pour ne pas fausser le journal des événements ;
si tu renommes le dépôt et/ou le site, ces mentions resteront
correctes en tant qu'historique, simplement plus à jour avec le nom
actuel des choses.
