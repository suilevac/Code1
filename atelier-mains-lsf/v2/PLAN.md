# Atelier des mains LSF — palier v2 : plan et contrats

Ce dossier `v2/` est une NOUVELLE application, construite à côté de la v1 (`source/`, `dist/atelier-mains-lsf.html`),
qui ne touche à rien de la v1. Elle sera publiée comme `dist/atelier-v2.html` et remplacera la v1 quand elle la dépasse.

## Ce que l'utilisateur a demandé (ses mots, 15 octobre 2026)

« La main n'est pas encore réaliste, la configuration des ongles n'est pas naturelle, elle se déforme quand les doigts
bougent. Les doigts, leurs formes et leurs contours se déforment avec le mouvement et ne représentent pas un doigt.
L'articulation n'est pas harmonieuse. Le bout des doigts doit être réaliste. Je veux une plus grande mobilité des doigts
avec tous les mouvements que l'être humain peut reproduire, en gardant les détails d'une main qui ne baisse pas en
qualité selon le mouvement et l'angle. Seule la couleur doit être non humaine, le reste oui. Même qualité main gauche et
main droite. Copier la main et la coller où je veux, comme dans Canva, la déplacer, la retourner, la modifier ensuite.
Insérer des images de mon ordinateur en fond. Une bannière avec le mot et une colonne avec les définitions, changer les
couleurs, surligner. Le personnage est affreux : retire-lui les bras, garde le tronc et la tête, inspire-toi de Piccolo.
Un outil de conception complet. »

Décision de cadrage (assumée, à lui dire) : la v2 garde SES proportions (longueurs d'os, largeurs mesurées sur ses deux
dessins et ses photos) mais le VOLUME est anatomique (maillage MakeHuman CC0 retaillé), et le rendu est calculé en 3D
(aplat vert INJS, ombre franche, contour noir, ongles clairs) sans texture peinte : la pose « Dessin » ne sera plus
identique au pixel près aux dessins — elle leur ressemblera, et toutes les autres poses seront enfin justes.

## Dossiers de recherche (lus avant d'agir)

`/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/v2/recherche/` :
`anatomie.md` (proportions, coupes, ongles), `mobilite.md` (amplitudes, couplages, besoins LSF), `rendu.md` (pipeline
toon v2, démo `rendu/demo_v2.py`), `modeles.md` (MakeHuman hm08, bpy, pipeline Python), `outil.md` (éditeur de planche),
`personnage.md` (direction A, SVG dans `personnage/svg/`).

## Architecture

```
v2/
  PLAN.md                 ce fichier
  build.py                assemble dist/atelier-v2.html (three.js r128 vendu + engine + plate + personnage + assets b64)
  hand/                   M1 — la main : pipeline Python (bpy, numpy) → assets
    build_hand.py         MakeHuman hm08 → coupe poignet → retaille (proportions utilisateur) → Catmull-Clark ×2 →
                          régions (ongles, palmures, éminences) → poids → export
    hand_v2.glb           main DROITE skinnée (la gauche = miroir x → −x à l'exécution)
    hand_v2.json          métadonnées : os, centres, axes, butées, courbes de plis (barycentriques), régions
    checks/               rendus de contrôle (Cycles + planches), overlays sur les dessins
  engine/                 M2 — moteur 3D (Three.js r128) : chargement, pose, squelette 26 DDL, skinning (DQ), toon 4 passes,
    engine.js             marionnette, contacts, presets ; API window.AtelierHand (ci-dessous)
    shaders.js
  plate/                  M3 — l'éditeur de planche : document, calques, sélection, texte, images, gabarits, export, projet
    plate.js  plate.css  index.html (page complète)
  personnage/             M4 — le référent : chemins SVG → Path2D, expressions, vue dos
    personnage.js
  tests/                  scripts Playwright (python3 run_rendu.py) et planches de contrôle
```

Règles communes :
- Ne JAMAIS modifier `source/`, `dist/atelier-mains-lsf*.html`, `build.py`, `tests/` de la v1. Pas de `git commit` : l'orchestrateur commet.
- Pas de CDN : three.js r128 est dans `/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/vendor/package` ;
  toute bibliothèque vendue vient de registry.npmjs.org et pèse < 100 Ko gzip ; polices OFL en base64.
- Commentaires et interface en français, ton de CLAUDE.md : chaque réglage porte la MESURE qui l'a fixé.
- Chaque livrable est vérifié par une image regardée (Read) et par un chiffre ; les planches de contrôle vont dans `v2/tests/out/`.
- Rendu hors écran : `python3 /tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/run_rendu.py <script.py>`
  (Chromium swiftshader, three.js local). bpy 5.2 (Blender module) est installable par pip pour M1.

## Contrat M1 → M2 : les assets de la main

`hand_v2.glb` : glTF 2.0 binaire, UNE SkinnedMesh (main DROITE — le trièdre doigts +Y / paume +Z / pouce +X est celui d'une droite, comme le dessin paume.jpg ; la gauche = miroir x → −x à l'exécution ; poignet inclus sur ~3 cm d'avant-bras), unités =
centimètres, repos = main ouverte à plat, doigts le long de +Y, paume vers +Z (la vue « Paume (face) » a la caméra en +Z),
pouce vers +X, poignet à l'origine. 20 os, nommés exactement :

```
poignet
  mc1 (pouce, CMC)  → pouce_p1 (MCP) → pouce_p2 (IP)
  mc2 (index)       → index_p1 (MCP) → index_p2 (IPP) → index_p3 (IPD)
  mc3 (majeur)      → majeur_p1 → majeur_p2 → majeur_p3
  mc4 (annulaire)   → annulaire_p1 → annulaire_p2 → annulaire_p3
  mc5 (auriculaire) → auriculaire_p1 → auriculaire_p2 → auriculaire_p3
```
Chaque os a son origine au CENTRE ARTICULAIRE (dans la tête de l'os proximal, décalé vers la paume : anatomie.md § 3),
axe local +Y le long de l'os, +X vers le pouce (axe de flexion), +Z vers la paume. Poids : ≤ 4 os par sommet, normalisés.
Attributs de sommet supplémentaires (glTF `_REGION` float ou `COLOR_0`) : 0 peau, 1 plaque d'ongle, 2 frange libre de
l'ongle, 3 repli d'ongle, 4 palmure. Maillage lisse (Catmull-Clark ×2 ≈ 27 k sommets, 8 morph targets correctifs des jointures), normales lissées, 100 % triangles à l'export.

`hand_v2.json` :
```
{ "version": 1, "unites": "cm", "HL": 19.0,
  "os": { "index_p1": { "parent": "mc2", "centre": [x,y,z], "longueur": 3.98, "rayon": 1.0 }, ... },
  "butees": { "index_p1": { "flex": [-25, 95], "flex_passif": [-45, 110], "abd": [-20, 20] }, ... },   // mobilite.md § 5
  "plis": [ { "nom": "ipp_index_dos", "type": "=", "points": [[face, b0, b1, b2], ...], "visible": "flex(index_p2)" }, ... ],
  "repos": { ... pose de repos (poignet 15, MCP 25, IPP 30, IPD 15, pouce 30) ... },
  "dessin": { ... pose qui ressemble le plus au dessin paume de l'utilisateur ... } }
```

## Contrat M2 → M3 : l'API de rendu d'une main

`engine.js` expose `window.AtelierHand` :
```
AtelierHand.ready : Promise<void>                       // assets chargés, shaders compilés
AtelierHand.render({pose, cote:'D'|'G', orientation:[qx,qy,qz,qw], w, h, scale, style}) → HTMLCanvasElement
      // image RGBA transparente de w×h px : la main posée, vue par une caméra orthographique de face (la rotation
      // est portée par `orientation`), rendue en aplat + ombre + contour + traits + ongles ; `style` = {peau, ongle,
      // trait, largeurTrait (en % de la hauteur), ombre:boolean}
AtelierHand.bounds({pose, cote, orientation}) → {w, h} en cm   // boîte de la main posée, pour dimensionner l'objet
AtelierHand.puppet(canvasHost, element, onChange)   // mode marionnette EN PLACE sur un élément de la planche
AtelierHand.presets : { nom → pose }                 // au moins les 15 de la v1 + l'alphabet et les chiffres LSF
AtelierHand.solve(poseDepart, poseCible) → pose      // contacts (pas d'interpénétration), butées, couplages
AtelierHand.mirror(pose) → pose
```
Format de pose v2 (degrés) :
```
{ poignet:{flex, dev}, prono, arc,
  pouce:{av, rap, mcp, ip, abdMcp},
  index:{mcp, pip, dip, ab, rot}, majeur:{...}, annulaire:{...}, auriculaire:{...} }
```
compatible avec la v1 (`F(mcp,pip,dip,ab)`, `TH(av,rap,mcp,ip)`) : les champs absents valent 0, `load()` lit les JSON v6–v8.

## Contrat M3 : le document (projet JSON v9)

```
{ "version": 9, "planche": { "w": 1920, "h": 1080, "fond": { "type": "uni|degrade|image|transparent", ... } },
  "theme": { "couleur": "#00a19a", "police": "Atkinson Hyperlegible", "corps": 48 },
  "elements": [   // ordre = calques, du fond vers le devant
    { "id", "type": "main", "x","y","w","h","rot","flipH","opacite", "cote":"D", "pose":{...}, "orientation":[...], "style":{...} },
    { "id", "type": "texte", "x","y","w","h","rot", "texte", "police","corps","gras","couleur","fond","align","surlignages":[{from,to,couleur}] },
    { "id", "type": "image", ..., "asset": "id ou data:" },
    { "id", "type": "personnage", ..., "expression":"neutre|sourire|sourcils_leves|sourcils_fronces", "vue":"face|dos", "style":"A|B" },
    { "id", "type": "fleche", ..., "de":[x,y], "a":[x,y], "style":"droite|demi|courbe", "double":false, "couleur" } ],
  "assets": { "id": "data:image/..." } }
```
Gabarits (un clic) : A bannière mot + colonne définitions (16:9), B carte mot/signe (carré), C fiche de vocabulaire (A4),
D planche 4 étapes, E bilingue. Export PNG ×1/×2/×3 (fond transparent possible), WebP en option, projet JSON autoporteur,
brouillon IndexedDB, bibliothèque `db` (capability claude.ai) comme la v1.

## Contrat M4 : le personnage

`personnage.js` expose `AtelierPersonnage.draw(ctx, {x, y, HLpx, vue, expression, style, couleurs})` (Path2D, trait
constant à l'écran = max(1,3 ; 0,028·HLpx)), `AtelierPersonnage.ancres(HLpx)` (creux du cou, menton, épaules, taille,
ancre des mains) et la direction A du dossier personnage (cape à épaulettes, oreilles pointues, antennes courtes,
crâne nu, pas de bras, pas de turban/taches/crocs), B comme style simple et repli sous 160 px.

## Jalons

M1 main (assets) et M3 éditeur et M4 personnage en parallèle → M2 moteur (dès qu'un premier GLB existe) → intégration
(`v2/build.py`, `dist/atelier-v2.html`) → critique multi-regards → publication. Chaque jalon laisse des fichiers sur
disque et une planche de contrôle ; l'orchestrateur commet après chaque jalon.
