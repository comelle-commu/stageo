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

### ⚠️ Désactiver la restriction par IP (sinon la fonction Netlify sera bloquée)

Testé en tentant un appel `GET /v3/account` depuis cet environnement : Brevo
a renvoyé `401 unauthorized` avec le message *"We have detected you are
using an unrecognised IP address"*. Brevo propose par défaut (ou sur
certains comptes) de restreindre l'usage de la clé API à une liste d'IP
autorisées.

**Incompatible avec une fonction Netlify** : les fonctions Netlify tournent
sur une infrastructure serverless (AWS Lambda) à IP dynamique, impossible à
lister à l'avance. Sans corriger ça, `brevo-signup.js` échouera exactement
comme le test ci-dessus, une fois déployée.

**Correction** : profil Brevo → **Security** → **Authorised IPs** →
désactiver la restriction ("Restrict access by IP address" ou équivalent).
Pas de perte de sécurité réelle : la clé ne quitte de toute façon jamais le
serveur (variable d'environnement Netlify), c'est déjà la bonne protection.

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

## Connexion Netlify ↔ GitHub (résolu)

Confirmé : le site était déployé par glisser-déposer manuel, sans dépôt Git
derrière. Décision : connecter le site Netlify à `comelle-commu/stageo`
pour que les futurs déploiements (dont les fonctions) se fassent
automatiquement à chaque push. Checklist pour la connexion (Site
configuration → Build & deploy → Link repository, ou en recréant le site
depuis "Import from Git") :

- **Dossier à publier : la racine du dépôt** (`.`), pas un sous-dossier —
  `stageo-landing.html` est directement à la racine.
- **`netlify.toml` : déjà présent et correct**, committé à la racine :
  ```toml
  [build]
    publish = "."
    functions = "netlify/functions"
  ```
- **Build command : vide** (site statique, rien à compiler).
- **`stageo-icon.png`** : confirmé présent au même endroit que
  `stageo-landing.html` (racine) — manquait initialement (seul le HTML
  avait été récupéré depuis le site live, pas les assets), corrigé et
  committé.

## Variables d'environnement Brevo - état

| Variable | Valeur | Statut |
|---|---|---|
| `BREVO_LIST_ID` | `13` | Fourni par l'utilisateur, à confirmer une fois la restriction IP levée (vérification directe bloquée par Brevo - voir ci-dessus) |
| `BREVO_API_KEY` | (reçue, non stockée dans le dépôt) | Idem - à re-tester une fois "Authorised IPs" désactivé, puis à coller directement dans Netlify (jamais dans un fichier commité) |
