# Identité visuelle : nouveau logo + photo hero (25/08/2026)

## Nouveau logo

Remplace l'ancien wordmark CSS ("Trouv" + "é" + icône pin) par le vrai
logo fourni par l'utilisateur (`trouveo-logo.png`) : lettrage manuscrit
bleu marine + mascotte boussole souriante.

- Fond blanc d'origine rendu transparent (seuil sur la luminosité des
  pixels - le fond était un blanc quasi uniforme, sans dégradé complexe).
  Vérifié sans halo visible sur fond crème (le fond réel du site).
- Recadré aux limites du dessin puis redimensionné à 900px de large
  (assez net en Retina aux tailles d'affichage réelles : ~30px de haut
  dans la nav, ~framecla,p(52-78)px dans le bandeau au-dessus du titre).
- Utilisé aux 3 emplacements où l'ancien wordmark apparaissait :
  `index.html` (nav + bandeau hero) et `activites.html` (nav).
- `trouveo-icon.png` (l'ancienne mascotte "pin", plus référencée nulle
  part) supprimé du dépôt.

## Photo hero (remplace les cercles décoratifs)

Les cercles SVG abstraits (`.collage`) ne représentaient rien de concret
- remplacés par une vraie photo d'enfants en pleine activité de groupe
  (jeu de parachute coloré, extérieur, plusieurs enfants).

- **Source** : [Pexels](https://www.pexels.com/photo/children-playing-at-a-park-8033864/),
  photographe RDNE Stock project.
- **Licence** : [Pexels License](https://www.pexels.com/license/) - usage
  commercial gratuit, aucune attribution légalement requise (créditée ici
  quand même par transparence).
- Redimensionnée à 1600px de large, compressée en JPEG qualité 82
  (~340 Ko) - suffisant pour un affichage hero, sans peser inutilement
  sur le temps de chargement.
- Affichée avec `object-fit:cover` dans un cadre arrondi (`.hero-photo`)
  qui reprend le même rayon/ombre que le reste de la charte (cartes,
  boutons).

## Si tu veux changer la photo plus tard

Remplace simplement `hero-photo.jpg` à la racine du dépôt par une autre
image (même nom de fichier, ou change la référence dans `index.html`).
Pense à vérifier la licence de la nouvelle image avant de la commiter -
Pexels, Unsplash et Pixabay proposent toutes des photos gratuites pour
usage commercial.
