# Email hebdomadaire "nouvelles activités" (25/08/2026)

## Contexte

Le produit promet "on vous prévient avant que la place ne parte", mais
jusqu'ici rien ne prévenait personne : les données étaient récoltées et
visibles sur `/activites`, mais personne n'était activement notifié. Cette
étape ajoute un email automatique hebdomadaire vers la liste d'attente
Brevo, listant les activités détectées depuis le dernier envoi.

**Ce n'est pas encore personnalisé** (pas de filtre par âge/commune - le
formulaire d'inscription ne capture que l'email) : tout le monde sur la
liste reçoit le même email. C'est une première brique fonctionnelle, pas
le produit final.

## Comment ça marche

`scrapers/brevo_digest.py`, lancé juste après `run_all.py` dans
`.github/workflows/scrape.yml` (donc chaque lundi, après le scraping) :

1. Lit la date du dernier email envoyé (table `digest_log`).
2. **Premier lancement** : aucune date précédente -> initialise la
   référence à maintenant et **n'envoie rien**. Sans ça, le premier envoi
   listerait les 700+ activités déjà en base comme si elles venaient
   d'apparaître cette semaine - aucun sens pour l'abonné.
3. Ensuite : cherche les activités dont `premiere_apparition` est
   postérieure au dernier envoi. Si la liste est vide, rien n'est envoyé
   (mais c'est journalisé). Sinon, un email est construit et envoyé.

## Pourquoi l'API Campagnes Brevo, pas l'API transactionnelle

Deux façons d'envoyer un email avec Brevo : l'API transactionnelle
(`/v3/smtp/email`, pensée pour un email individuel - confirmation de
commande, etc.) et l'API Campagnes (`/v3/emailCampaigns`, pensée pour
diffuser à une liste entière). On utilise la seconde : gestion native du
lien de désabonnement (obligatoire légalement), pas besoin de boucler
manuellement sur chaque contact de la liste.

Flux en 2 appels :
1. `POST /v3/emailCampaigns` (crée la campagne en brouillon, cible
   `recipients.listIds: [BREVO_LIST_ID]`).
2. `POST /v3/emailCampaigns/{id}/sendNow` (déclenche l'envoi immédiat).

## Variables d'environnement supplémentaires

En plus de `SUPABASE_URL`/`SUPABASE_SECRET_KEY` déjà configurées :

| Variable | Valeur |
|---|---|
| `BREVO_API_KEY` | La même clé déjà utilisée par `netlify/functions/brevo-signup.js` |
| `BREVO_LIST_ID` | `13` (même liste "Stagéo - liste d'attente") |
| `BREVO_SENDER_EMAIL` | **À fournir** - une adresse déjà validée dans Brevo (Senders & IP → Senders), sinon la création de campagne échoue |

**À ajouter en tant que secrets GitHub** (Settings → Secrets and
variables → Actions → New repository secret) - ce sont des secrets
séparés de ceux déjà configurés pour Netlify, même si les valeurs
`BREVO_API_KEY`/`BREVO_LIST_ID` sont identiques (les deux plateformes ne
partagent pas leurs variables d'environnement entre elles).

## Tester sans envoyer de vrai email

```
venv/bin/python3 brevo_digest.py --dry-run
```

Construit l'email et l'écrit dans `scrapers/output/digest_preview.html`
(à ouvrir dans un navigateur pour prévisualiser) - n'appelle jamais Brevo,
ne touche jamais `digest_log`. Utile pour vérifier le rendu avant le
premier vrai envoi.

## Suivi des envois

Table `digest_log` (migration
`supabase/migrations/20260825_create_digest_log.sql`) : une ligne par
exécution, avec le statut (`INIT` / `VIDE` / `OK` / `ERREUR`), le nombre
d'activités incluses, et l'ID de la campagne Brevo créée le cas échéant.
Pas de lecture publique (contrairement à `activites`) - c'est un journal
technique interne.

## Limite connue : pas de personnalisation

Tout le monde reçoit le même email, quel que soit l'âge de l'enfant ou la
commune. Prochaine étape naturelle si on veut vraiment tenir la promesse
"prévenu·e dès qu'une place correspond à votre enfant" : capturer ces
préférences dans le formulaire d'inscription, puis filtrer l'email (ou
segmenter la liste Brevo) en fonction. Pas fait dans cette passe.
