# Atelier des mains LSF

Outil web pour poser une main 3D comme une marionnette et exporter des images de configurations de la **Langue des Signes Française** (ex. le signe « cent » : la main glisse du chiffre des centaines vers les zéros). Les PNG exportés servent ensuite dans Canva pour des supports de classe (INJS de Metz).

Auteur et utilisateur : Cavélius, enseignant LSF natif (CODA) à l'INJS de Metz. Il juge l'anatomie à l'œil : **c'est lui la référence, pas les valeurs par défaut.**

---

## Exigences de l'utilisateur (non négociables)

1. **Garder exactement SA main.** Les deux dessins de `references/` (paume = face élève, dos = vue signeur) sont la source. Seule la couleur change : **vert INJS `#00a19a`** (relevé sur le logo du site lsfdico.injs-metz.fr). Pas de main générique, pas de proportions inventées.
2. **Vraie 3D, toutes orientations.** Tourner la main entière dans tous les sens, vues face / dos / profil / dessus.
3. **Mode marionnette.** On attrape un doigt et on tire : tout le doigt suit depuis sa base. Le clic droit bloque une articulation (cadenas). Maj + glisser fait bouger une seule articulation.
4. **Anatomie humaine stricte.** Aucune pose impossible, aucun doigt qui traverse la paume ou un autre doigt. Fermer tous les doigts donne un poing, et le pouce reste libre tant qu'on ne le bouge pas.
5. **Rendu naturel.** Pas de « boudins » (segments posés bout à bout), pas d'ongles déformés, pas de doigt qui s'allonge, pas de formes géométriques qui apparaissent.

## Approches déjà essayées et REJETÉES (ne pas y revenir)

| Version | Approche | Pourquoi rejetée |
|---|---|---|
| v1 | Main 3D maison en primitives (sphères/cylindres) | Ce n'était pas sa main |
| v2 | Découpe 2D du dessin en pièces qui pivotent | Plate, flexion en « boudins », vue dos illisible |
| v3 | Modèle 3D générique (WebXR hand, MIT) restylé | Pas sa main ; la peau s'étire, les ongles se déforment |
| v5 | Phalanges rigides séparées, texturées | Mieux, mais « boudins » aux articulations et pouce qui se disloque |

## Architecture actuelle (v8, en cours)

**v8 = UNE peau fermée pour toute la main** (remplace les tubes de doigts + nappe de paume de la v7, qui donnaient trous, boules et « boudins » à la base des doigts) :
- `rig3d.py` (section v8) : silhouette intérieure exacte du dessin paume gonflée en volume (doigts : coupe en ellipse DF/DB × demi-largeur locale ; paume : nappes `hf`/`hb`), surface extraite par *marching cubes* (pas 5 px, ≈ 44 000 sommets) puis lissage de Taubin.
- Squelette : paume, métacarpien du pouce (`CMC`), 3 phalanges par doigt. La base du doigt pivote à la tête du métacarpien, ½ largeur de doigt sous le pli de la racine (`DEEP8`). Articulations au milieu de l'épaisseur (`jz`).
- **Déformeur en arc** aux articulations charnières (MCP, IPP, IPD des doigts ; MCP et IP du pouce), dans `skinMesh` (script.js), données `mesh.arc` (rig3d.py) : dans la zone d'une articulation, la section d'abscisse `tau` tourne de `tau·θ` autour d'un centre qui glisse, chaque fibre de peau devient un arc de cercle et rejoint exactement l'os rigide aux bords de la zone (pas de repli, de fente noire ni de creux au pli). Demi-largeur de zone `h` : grande côté paume (`h ≥ 1,15·d·tan(θmax/2)`, le pli ne se replie jamais), petite côté dos (jointure nette). Chaque chaîne (pouce, doigt) ajoute son déplacement ; parts des doigts lissées dans les palmures. Seule la base du pouce (trapézo-métacarpienne) reste en quaternions duaux. Les anciens poids `bi`/`bw` sont encore exportés mais plus utilisés par la peau.
- Une seule matière : dessin paume devant, dessin dos derrière, fondus sur la tranche.
- Passe « identité » : une partie nette par triangle ; palmures et éminence = paume.
- Quaternions duaux (base du pouce, `dqApply`) : signe aligné sur l'os principal du sommet (essai C ; boneDQ1 ramène w ≥ 0, donc court chemin garanti).
- **Racines sans « col »** (essai A) : le volume du dessin a, à la racine de chaque doigt et du pouce, une gorge puis un bourrelet. Profil corrigé exporté en déplacement `mesh.dz`, appliqué progressivement dès que la pose quitte « Dessin » (`rootBlend`, part `gR`) : dessin au repos exact au pixel près. Au pouce : côté dos seulement (MCP sans cran) ; côté paume, combler la gorge contre l'éminence effaçait l'écart de profondeur qui fait le contour du pouce posé devant la paume (trait effiloché).
- **Coque gardée** (`hullMatProto`) : hors pose « Dessin », main entière, un fragment de coque est jeté s'il est à moins de `HPUSH`(1,8) × épaisseur du trait devant la peau qu'il recouvre (profondeur de la passe identité), loin de la silhouette, ET que la peau recouverte est la même partie ou la paume sous un doigt : les fentes en dents de scie des plis disparaissent, le vrai contour (pouce sur paume/éminence, doigt sur doigt, pouce et doigt, silhouette) garde son poids.
- **Ongles** (essai D, repris) : forme dessinée (enveloppe convexe, recoupée à `NAILM`=10 px de la tranche) en distance signée dans `texNail` (R) ; le shader trace l'aplat + le trait fin (`NAILLW`=2,4 px), nets à tout grossissement. Le trait est un « U » comme dans le dessin : il s'amincit jusqu'à rien au bord libre (`texNailE`), pas d'anneau noir « autocollant ». La texture dos reste celle d'avant (ses mipmaps lues en biais changeaient la vue paume au repos) ; la peau repeinte (sous l'ongle, son trait, bouts de trait étirés en taches) passe par `texNail` G/B, appliquée sur le dos franc au repos et partout hors pose (plus de points noirs sous l'ongle vus de côté). Bombé + repli de peau (`NDOME`, `NFOLD`) dans `mesh.dz` (hors pose seulement), éteint sur 12 px vers la tranche (pas de cran de silhouette au bord de l'ongle).
- Essayé et écarté à l'intégration : partage linéaire des palmures entre deux doigts (essai C) par-dessus le déformeur en arc (fente/pointe entre annulaire et majeur, poing d'un seul doigt) ; trait épais tiré de la passe identité pour le pouce devant la paume (taches sur le contour dos).
- Les photos de la main de l'utilisateur (profil, poing, pince, O…) ont servi de référence de volumes ; elles ne sont pas dans le dépôt.

## Architecture précédente (v7)

```
references/   paume.jpg, dos.png      ← les deux dessins de l'utilisateur
source/
  rig3d.py      Python (numpy, scipy, Pillow) : dessins → géométrie + textures → hand3d.json
  hand3d.json   données générées (≈800 Ko, embarquées dans la page)
  head.html     interface (onglets Doigts / Main / Mouvement / Biblio)
  style.css     jetons de couleur clair/sombre, mise en page
  script.js     moteur 3D (Three.js r128) : squelette, peau, anatomie, collisions, rendu, interface
build.py        assemble dist/atelier-mains-lsf.html (fichier unique autonome)
tests/rendu.py  rendus de contrôle via Playwright (WebGL logiciel)
dist/           page construite (+ .local.html ouvrable directement dans un navigateur)
```

### rig3d.py (pipeline géométrie)
- **Recoloration** : peau → vert INJS proportionnel à la luminance, ongles → vert clair, traits noirs conservés en alpha.
- **Recalage** du dessin dos sur le dessin paume par **thin-plate spline**. Les points de contrôle sont les articulations, les bords des doigts et des repères de la paume. Le trait de contour est ensuite retiré des textures, car il est redessiné en 3D.
- **Squelette** : les chaînes d'articulations sont saisies à la main en pixels (`CP` pour la paume, `CD` pour le dos). Doigts : [MCP, IPP, IPD, bout]. Pouce : [MCP, IP, bout].
- **Profils des doigts** : largeurs gauche/droite mesurées sur la silhouette intérieure, échantillonnage serré, bout arrondi.
- **Paume** : nappe de hauteur (épaisseur avant `hf`, arrière `hb`), avec éminence thénar, creux de la paume, poignet plus épais. Hauteurs stockées ×8 (`zscale`) pour éviter les paliers.
- **Collision** : grille d'épaisseur de paume (`hgrid`).
- **Poids de peau** de la paume vers la base de chaque doigt (`fw`).

### script.js (moteur)
- **Doigts = UNE peau continue par doigt** portée par des os rigides. Chaque anneau de peau suit un os ; près d'une articulation il se partage entre les deux os par **mélange de quaternions duaux** (pas de pincement ni d'allongement). La coupe est plus ronde côté pulpe (`DF=.92`) et plus plate côté ongle (`DB=.7`, `DB_TIP=.58`).
- **Textures** projetées depuis le dessin (UV = position dans le dessin), jamais étirées. Les flancs et le bout prennent leur couleur légèrement en retrait du bord dessiné pour éviter les traînées.
- **Paume** : peau déformée par le pouce (poids thénar `PW`) et par la base des doigts (`fw`) → relief des jointures dans le poing.
- **Anatomie** (`constrain`) :
  - **pivot de la base enfoncé dans la paume** (`DEEP` = 0,8 × largeur du doigt) : la vraie tête du métacarpien est sous le pli distal de la paume, pas au pli de la racine du doigt du dessin. Sans ça, la 1re phalange est trop courte et le poing ne se ferme pas. Le repos est inchangé ;
  - passage d'une configuration à l'autre (`settle`) : pouce écarté d'abord, puis doigts, puis pouce → résultat indépendant de la pose précédente ;
  - limites des doigts : MCP −20…90°, IPP 0…105°, IPD −10…80° et couplée à l'IPP (`dip ≤ 25 + 0.65·pip`, tendon commun) ;
  - l'écartement se referme quand la MCP plie ;
  - convergence des doigts en flexion (`CONV`) ;
  - asservissement entre voisins (`ENSLAVE`) ;
  - pouce : trapézo-métacarpienne au poignet (`CMC_IMG`) avec avancer / rapprocher + pronation (`PRON=-1`). Sa MCP ne plie loin que pouce avancé, et son bout ne pointe jamais vers le poignet.
- **Collisions** (`penetration` / `solve`) : doigt contre paume (tissus mous : `SOFT=12` px d'appui permis), pouce contre doigts, doigts voisins, doigt contre lui-même, posture du pouce. Le solveur s'arrête au contact sans jamais traverser.
- **Rendu** : aplat + une ombre franche (style du dessin), contour noir par coque inversée. Une passe « identité » trace les traits intérieurs quand une partie passe devant une autre (pouce devant la paume, doigt devant doigt).
- **Marionnette** : la direction écran de chaque articulation est mesurée en la poussant de 3°. Résolution par moindres carrés (`grabAxes` / `onDrag`). Couplage naturel `GRAB` (bout tiré → MCP .85, IPP 1, IPD .7).
- **Configurations de départ** (`PRESETS`) : Dessin, Repos, B, A, Poing serré, 1, V, L, Y, C, O, Pince. Pour O, Pince et Poing serré, `thumbReach` amène le pouce sur sa cible.
- **Bibliothèque** : capacité `db` de claude.ai (`window.claude.use('db')`, collection `configurations`). Hors claude.ai elle est indisponible, et l'échange JSON prend le relais. **Export PNG** : capacité `downloads`, sinon image dans une boîte de dialogue.
- **Débogage** : `window.__atelier` expose `renderer, S, refresh, main, camera, PRESETS, applyPreset, penetration, constrain, solve, setPron`.

## Construire et vérifier

```bash
pip install numpy scipy pillow playwright && playwright install chromium
python3 build.py --rig --preview   # régénère la géométrie (≈10 s) + contrôle du recalage
python3 tests/rendu.py             # rendus de contrôle → tests/out/planche.png
```
**Toujours regarder la planche** avant de livrer : repos face et dos = dessins exacts, majeur levé (doigts serrés, pouce cerné d'un trait), poing serré, pince, gros plan des ongles.

## Défauts connus (à traiter en priorité)
1. Stries légères sur l'ongle du pouce en pince : le dessin dos colle l'ongle du pouce au contour.
2. La tranche de la main (profil) est déduite, pas dessinée.
3. Quelques traits parasites possibles à la jointure pouce/paume selon l'angle.
4. Le glisser est un peu lent sur machine modeste : `penetration` est appelée plusieurs dizaines de fois par mouvement.

## Publication
La version en ligne est un artifact claude.ai privé, publié depuis Claude. Pour le mettre à jour, republier `dist/atelier-mains-lsf.html` (sans doctype : claude.ai l'ajoute) avec les capacités `db`, `user`, `downloads`.
