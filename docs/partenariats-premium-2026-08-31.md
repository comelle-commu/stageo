# Partenariats "mis en avant" — pas encore construit (31/08/2026)

## Contexte

Une ASBL de Namur (médiation culturelle pour enfants/ados à partir de
collections d'archéologie/beaux-arts) a contacté Muriel spontanément pour
être référencée sur Trouvéo. C'est la première demande entrante (jusqu'ici
toutes les sources ont été trouvées et ajoutées par nous). L'occasion de
clarifier deux choses qui n'existaient encore qu'à l'état d'idée sur
`partenaires.html` (formulaire "être recontacté·e" collectant déjà des
leads intéressés par un "badge organisme vérifié" / mise en avant / encart
publicitaire, jamais activé ni tarifé) : comment onboarder un partenaire
qui envoie ses infos directement (pas trouvé par scraping), et comment
monétiser une mise en avant.

**Rien de ce qui suit n'est construit.** Décrit ici pour ne pas repartir de
zéro à la prochaine occasion (un autre organisme qui écrit, ou Muriel qui
veut activer l'offre) - à construire seulement quand il y a un vrai
partenaire prêt à payer, pas en spéculatif.

## Onboarding d'un partenaire qui envoie ses infos directement

Pas de nouvel outil nécessaire, juste un processus en 3 étapes :

1. **Vérifier** ce que le partenaire envoie (dates, âges, tarifs, lieu,
   modalités d'inscription - les mêmes champs que le schéma `Activite`
   existant).
2. **Récapitulatif** envoyé au partenaire ("voici ce qu'on publierait, ça
   vous va ?") avant toute mise en ligne - promesse déjà faite sur
   `partenaires.html` ("nous validons votre fiche ensemble avant
   publication").
3. **Publication** une fois l'accord reçu : soit ajout manuel direct en
   base (comme pour l'import initial de Jeunesse à Bruxelles), soit
   construction d'un vrai scraper si leur programme est publié en ligne et
   se renouvelle chaque saison (évite de tout refaire à la main).

## Offre "mise en avant" (à activer/tarifer le jour venu)

Trois morceaux techniques, chacun simple isolément :

1. **En tête des résultats** : un champ "mis en avant" utilisé comme
   premier critère du tri dans `activites.html` (`visible.sort(...)`,
   actuellement : commune exacte > type préféré > proximité de date).
2. **Descriptif plus détaillé** : un champ texte optionnel en plus des
   champs existants, affiché sur la carte quand rempli.
3. **Badge "Partenaire"** (renommé depuis "Le choix de Trouvéo" le
   31/08/2026 - risquait de sonner comme une recommandation éditoriale
   plutôt qu'un badge payant assumé) : badge visuel sur la carte, même
   principe que le badge "Édition passée" déjà en place.

Le statut "mis en avant" lui-même : prévoir une **date d'expiration**
(`premium_jusqu_au`) plutôt qu'un simple booléen - s'éteint tout seul à
l'échéance plutôt que de rester actif indéfiniment si un renouvellement
n'a pas été payé. Muriel indique manuellement quand quelqu'un paie et pour
combien de temps ; pas de vrai système de facturation tant que c'est une
poignée de partenaires.

## Relance automatique du partenaire pour le programme suivant

Idée soulevée en discutant du problème de fraîcheur des données pour un
partenaire sans scraper (mise à jour manuelle sinon) : réutiliser presque
telle quelle la mécanique de `scrapers/relance_criteres.py` :

- **Déclencheur** : un organisme "mis en avant" n'a plus aucune activité à
  venir en base (`is_upcoming()`/`extract_end_date()`, déjà écrites pour
  `criteres_alertes.py`).
- **Envoi** : email transactionnel Brevo à l'adresse de contact de
  l'organisme ("vos stages actuels touchent à leur fin, envoyez-nous le
  prochain programme").
- **Anti-spam** : table de suivi façon `relances_criteres_envoyees` - une
  seule relance par "creux", pas une par run tant que sans réponse.
- **Exécution** : un step de plus dans le job hebdomadaire déjà en place
  (`.github/workflows/scrape.yml`), rien de nouveau à orchestrer.

## Prochaine étape

Rien à faire tant qu'il n'y a pas de partenaire payant réel. Répondre à
l'ASBL namuroise en suivant le processus d'onboarding ci-dessus ; lui
proposer la mise en avant seulement si/quand l'offre existe vraiment.
