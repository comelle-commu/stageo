# Stagéo — Formulaire d'inscription branché sur Brevo (24/08/2026)

## Contexte

La landing page (`stageo-landing.html`, servie sur `https://stageo.netlify.app/`)
affichait un message de confirmation simulé sans rien envoyer nulle part.
Cette session la branche sur une vraie liste Brevo. Le fichier source n'était
tracké dans aucun dépôt accessible à cette session — récupéré depuis le site
live et ajouté à `comelle-commu/stageo` (voir "Point de vigilance" en bas).

## Tâche 1 — Créer la liste dans Brevo (à faire toi-même)

Je n'ai pas accès à ton compte Brevo — voici les étapes exactes.

1. Connecte-toi sur [app.brevo.com](https://app.brevo.com).
2. Menu de gauche → **Contacts** → onglet **Lists**.
3. Bouton **Create a list** (ou **+ Create a new list**) → nom :
   `Stagéo - liste d'attente` → **Create**.
4. Ouvre la liste créée : son **ID numérique** apparaît dans l'URL, ex.
   `https://app.brevo.com/contact/list-details/7` → l'ID est `7`. Note-le,
   il servira de variable d'environnement (`BREVO_LIST_ID`).
5. Récupère la clé API : icône profil (en haut à droite) → **SMTP & API**
   → onglet **API Keys** → **Generate a new API key** → donne-lui un nom
   (ex. "Stagéo landing") → copie la clé générée (elle ne sera plus
   affichée en entier ensuite, à conserver précieusement).

⚠️ Cette clé API donne un accès complet à ton compte Brevo (tous les
contacts, l'envoi d'emails...). Contrairement à Supabase, Brevo n'a pas de
notion de clé "publique" à droits restreints — c'est justement pour ça
qu'on ne la met jamais dans le HTML/JS (voir Tâche 2).

## Tâche 2 — Formulaire branché via une fonction Netlify (relais sécurisé)

**Brevo nécessite bien un relais côté serveur** — confirmé en tâche 1 : une
seule clé API, tous droits, donc invivable à exposer dans le navigateur
(n'importe qui peut faire "Afficher le code source"). Solution retenue,
la plus simple vu que le site est déjà hébergé sur Netlify : une **fonction
Netlify** (`netlify/functions/brevo-signup.js`), zéro hébergement
supplémentaire à gérer.

```
Navigateur (fetch JSON)  →  Fonction Netlify (clé API en variable d'env.)  →  API Brevo
```

### Ce qui a changé dans `stageo-landing.html`

- Les deux formulaires (`signupForm`, `signupForm2`) envoient maintenant un
  `fetch('/.netlify/functions/brevo-signup', ...)` avec l'email en JSON, au
  lieu de juste basculer l'affichage.
- **Message de confirmation existant conservé à l'identique** — toujours
  affiché (`#confirmMsg` / `#confirmMsg2`) uniquement après une réponse de
  succès de la fonction.
- **Nouveau message d'erreur** (`#errorMsg` / `#errorMsg2`, texte rouge/rose
  sous le formulaire) affiché si : l'email ne passe pas une validation basique
  côté client, ou si la fonction Netlify renvoie une erreur (Brevo injoignable,
  configuration manquante, etc.). Le formulaire reste utilisable pour
  réessayer (contrairement au succès, qui le masque définitivement).
- Bouton désactivé + texte "Envoi..." pendant la requête, pour éviter les
  double-clics.

### La fonction Netlify (`netlify/functions/brevo-signup.js`)

Reçoit `{ email }` en POST, valide le format, puis appelle
`POST https://api.brevo.com/v3/contacts` avec `listIds: [BREVO_LIST_ID]` et
`updateEnabled: true` (une personne qui s'inscrit deux fois - les deux
formulaires de la page, ou un rechargement - ne voit pas d'erreur, Brevo met
juste à jour le contact existant plutôt que de refuser le doublon).

### Variables d'environnement à configurer sur Netlify

Site Netlify → **Site configuration** → **Environment variables** →
**Add a variable**, deux fois :

| Nom | Valeur |
|---|---|
| `BREVO_API_KEY` | la clé API générée en Tâche 1 |
| `BREVO_LIST_ID` | l'ID numérique de la liste, ex. `7` |

Sans ces deux variables, la fonction répond une erreur 500 claire
("Configuration serveur incomplète") plutôt que d'échouer silencieusement.

## Tâche 3 — Email de bienvenue automatique (à faire dans Brevo, pas dans le code)

1. Dans Brevo, menu de gauche → **Automations** (parfois appelé
   "Marketing Automation").
2. **Create a workflow** → pars d'un modèle vide ("Create from scratch")
   plutôt qu'un template pré-rempli.
3. Déclencheur (**Entry point**) → choisis **"A contact is added to a
   list"** (ou "Contact enters a list") → sélectionne
   `Stagéo - liste d'attente`.
4. Ajoute une étape **"Send an email"** juste après le déclencheur.
5. Rédige l'email : objet du type *"Bienvenue dans la liste d'attente
   Stagéo !"*, corps reprenant l'idée *"Bienvenue dans la liste d'attente
   Stagéo, on vous prévient dès l'ouverture."* (à enrichir avec ton ton de
   marque si tu veux, ce n'est qu'un point de départ).
6. Vérifie l'expéditeur (**From**) — utilise une adresse déjà validée dans
   Brevo (Senders & IP → Senders), sinon Brevo demandera de la valider
   avant d'activer le workflow.
7. **Active** le workflow (bouton en haut, souvent "Activate"/"Start
   workflow").

Une fois actif, toute nouvelle adresse ajoutée à la liste (donc toute
inscription réussie depuis la landing page) reçoit cet email automatiquement
— aucun code supplémentaire nécessaire, c'est entièrement gèré côté Brevo.

## Où consulter la liste des inscrits

Brevo → **Contacts** → **Lists** → clique sur **"Stagéo - liste d'attente"**
→ la table affiche chaque email inscrit, avec sa date d'ajout. Exportable en
CSV depuis cette même page (bouton **Export**) si besoin de la récupérer
ailleurs.

## Point de vigilance : le déploiement Netlify

Ce fichier n'a été retrouvé nulle part dans un dépôt Git accessible à cette
session — récupéré directement depuis `https://stageo.netlify.app/` (voir
commit associé). **Comment ce site Netlify est-il actuellement connecté à
son code source ?** Deux cas possibles, avec une action différente selon
lequel s'applique :

- **Le site Netlify est lié à un dépôt GitHub** (le plus probable, vu le
  script `data-netlify-site-id` détecté sur la page) : si ce dépôt n'est
  pas `comelle-commu/stageo`, il faut soit y répliquer ces changements soit
  reconnecter le site Netlify pour qu'il pointe vers `comelle-commu/stageo`
  (Site configuration → Build & deploy → Link a different repository).
- **Le site a été déployé par glisser-déposer** (pas de dépôt Git derrière) :
  il faudra redéployer manuellement le contenu de ce dépôt (dossier racine,
  qui contient maintenant `stageo-landing.html`, `netlify.toml` et
  `netlify/functions/`) via le dashboard Netlify ou la CLI (`netlify deploy`).

Sans savoir laquelle de ces deux situations s'applique, je ne peux pas
garantir que les changements de cette session sont déjà live sur
`stageo.netlify.app` — à vérifier après déploiement.
