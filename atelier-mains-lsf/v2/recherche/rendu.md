# Dossier « rendu » — rendu toon d'une main 3D, constant sous tous les angles

Atelier des mains LSF, palier v2. Dossier de recherche (pas de code livré), 15 octobre 2026.
Images, scripts et sources téléchargées : `/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/v2/recherche/rendu/`.

Question posée : comment rendre une main 3D en aplat + ombre franche + contour noir + ongles clairs (l'identité graphique actuelle), **sans que la qualité baisse selon l'angle ou la pose**, avec Three.js r128 vendu localement (`vendor/package/build/three.min.js` + `OrbitControls.js` seulement : pas d'EffectComposer, pas d'OutlinePass, pas de FXAA dans le paquet).

---

## 0. Résumé en dix lignes

1. Tout ce qui est **peint sur une texture** (traits de jointures, plis de la paume, ombre du dessin, trait d'ongle) se dégrade dès que la surface n'est plus vue de face : raccourci de projection (mesuré ×1,9 entre les deux bras du « U » d'un ongle), mipmaps qui délavent, déformeur qui écarte ou écrase le trait. C'est la cause n° 1 des « ongles pas naturels » et des « doigts qui ne représentent pas un doigt » sous un angle.
2. Tout ce qui est **calculé en 3D ou en espace écran** (coque inversée à largeur constante, arêtes par profondeur et identité, lignes attachées au maillage rendues en rubans d'épaisseur fixe) reste identique sous tous les angles. C'est ce que font Guilty Gear Xrd (lignes par sommet et coque), Spider-Verse (lignes = géométrie décollée de la surface) et tous les shaders toon de référence (MToon, Genshin-like).
3. Le rendu actuel n'a **pas** d'ombre franche : `s = 0,8 + 0,26·N·L` est une rampe douce saturée, le dessin, lui, a UNE marche à 0,82. Il faut une vraie fonction à deux paliers (1,0 / 0,82) avec une lisière antialiasée par `fwidth`.
4. La coque actuelle est épaisse **en unités du modèle** : juste à la distance de travail, fausse au zoom et à l'export ; la formule de largeur constante à l'écran (extrusion en espace clip × w) est connue, triviale et validée ici sur le maillage posé.
5. Le maillage actuel (marching cubes, pas 5 px ≈ 1,1 mm, + reliefs sculptés de 0,5 à 1 mm) est **trop rugueux** pour toute ligne tirée de la courbure ou des normales (le « détecteur de plis » éteint, les « griffures » du dos, et dans mes essais : la coque qui perce dans les sillons). Un rendu toon propre exige une surface lisse (subdivision ou lissage fort) et des normales lissées.
6. Les **traits intérieurs** d'un illustrateur sur une main sont peu nombreux et toujours aux mêmes endroits : plis des jointures (dos : IPP et IPD en deux petits arcs « = », MCP seulement poing fermé), U de l'ongle ouvert vers le bout, plis de flexion côté paume (1 à l'IPD, 2 à l'IPP, 1 à la racine), trois grands plis de la paume, pli du thénar, poignet. **Jamais** sur le fût des doigts, jamais sur les tendons (ils se lisent par l'ombre), pas de hachures.
7. Ces traits doivent être des **courbes attachées au maillage** (position barycentrique sur la peau au repos, suivies par le skinning), rendues en rubans de largeur constante à l'écran, avec une visibilité pilotée par l'angle de l'articulation (pli dorsal visible fléchi, effacé tendu ; pli palmaire inversement) et par N·V (filet en rasant), jamais par une texture.
8. L'ongle doit être une **zone géométrique** (attribut de sommet ou maillage à part, plaque bombée de rayon 7–9 mm, relief 0,3–0,5 mm) ; son contour vient de la passe d'identité en espace écran (largeur constante, validé), sa couleur claire et sa frange libre ×1,35 plus claire viennent de sa propre paramétrisation, pas d'une texture.
9. Pipeline v2 en quatre passes dans Three.js r128 : G-pass (normales + identité + profondeur) → toon 2 marches → coque inversée reculée en profondeur → arêtes écran + rubans. Tout tient dans `ShaderMaterial` + `WebGLRenderTarget` + `DepthTexture`, déjà utilisés par le code actuel.
10. Mesuré sur le maillage posé actuel (sans aucune texture) : contour médian 6 px à dpr 2 identique dans les 12 vues (face, dos, ¾, rasant), contour d'ongle propre à tout angle, part d'ombre 0,11–0,23 proche du dessin (0,16–0,18). Ce qui reste faux vient du maillage, pas du rendu.

---

## 1. Ce qui fait qu'un rendu reste bon à tout angle

| Élément du dessin | Mauvaise implémentation (se dégrade) | Bonne implémentation (constante) | Pourquoi |
|---|---|---|---|
| Contour extérieur | Trait peint dans la texture ; coque en unités du modèle | Coque inversée extrudée en **espace clip** (× w, / taille d'écran) ou détection d'arête en espace écran | la largeur ne dépend plus ni de la distance, ni de l'inclinaison de la surface |
| Traits intérieurs (jointures, plis) | Peints sur la texture UV | Courbes 3D attachées au maillage, rendues en rubans d'épaisseur fixe à l'écran ; ou arêtes calculées (profondeur / identité) | un trait peint subit le raccourci de la projection (cos de l'angle d'incidence) et le filtrage des mipmaps |
| Trait d'ongle | Distance signée dans une texture + largeur compensée | Frontière d'une **zone d'identité** (ongle / peau) détectée en espace écran | la frontière est un lieu géométrique, la largeur du trait est fixée en pixels |
| Ombre | Rampe douce ; ombre peinte dans la texture | Marche sur N·L avec normales **lissées**, seuil décalé par sommet là où l'illustrateur ombre toujours | une ombre peinte ne suit pas la lumière quand la main tourne ; une rampe douce n'est pas un aplat |
| Relief fin (tendons, vallées) | Sculpté dans un maillage grossier | Surface lisse (subdivision) ; lu par l'ombre, pas par un trait | sur un maillage à facettes, toute dérivée (normale, courbure, profondeur) est bruitée |
| Couleur | Texture projetée (dessin recoloré) | Couleur unie + zones (ongle, frange) par attribut | une texture projetée depuis une vue de face n'existe pas sur la tranche |

Références de fond :
- Hertzmann, *Introduction to 3D Non-Photorealistic Rendering: Silhouettes and Outlines* (1999) : deux familles, espace image (post-traitement d'un rendu, limité à la précision de l'image) et espace objet (arêtes exactes du maillage) ; les hybrides (Northrup & Markosian 2000) gardent la précision objet et la cohérence de visibilité de l'image. https://mrl.cs.nyu.edu/publications/npr-course1999/hertzmann-intro3d.pdf
- Cole et al., *Where Do People Draw Lines?* (SIGGRAPH 2008) : 29 artistes, 12 modèles, 208 dessins ; **75 % des traits sont à moins de 1 mm d'un trait d'un autre artiste**, surtout sur les contours d'occultation ; les traits hors contours coïncident avec les forts gradients d'intensité de l'image (les « apparent ridges » de Judd 2007 sont le meilleur prédicteur) ; **14 % des traits ne sont expliqués par aucune propriété locale**. https://gfx.cs.princeton.edu/pubs/cole_2008_wdp/index.php — synthèse Hertzmann 2020 : https://aaronhertzmann.com/2020/04/21/ar-vs-cs.html
- Judd, Durand, Adelson, *Apparent Ridges for Line Drawing* (2007) : maxima de la variation de la normale **vue depuis la caméra** (dépend du point de vue) ; DeCarlo et al. 2003, *Suggestive Contours* : lieux qui deviendraient contour pour un léger changement de point de vue. https://people.csail.mit.edu/tjudd/apparentLines.pdf

Ce que ça veut dire pour nous : les lignes qu'un œil attend sont (a) les contours d'occultation (silhouette, doigt devant doigt, pouce devant paume) — exacts, calculables en espace écran ; (b) quelques lignes de forme (plis), qui ne sortent proprement d'une courbure que sur un maillage lisse ; (c) une part irréductible de convention (les « = » des jointures, le U de l'ongle) que seul un trait **posé à la main sur le modèle** donne : d'où les lignes attachées.

---

## 2. Techniques de contour

### 2.1 Coque inversée (inverted hull / back-face)

Principe : on dessine une seconde fois le maillage, faces arrière seulement, sommets poussés le long de la normale, en noir. C'est la méthode de Guilty Gear Xrd (« une seconde couche de polygones plus sombres générée dans le shader et élargie dans la direction des normales ; la largeur varie selon l'endroit, jusqu'à être effacée ; la couleur de sommet pilote ces propriétés » — GDC 2015, Motomura, https://www.ggxrd.com/Motomura_Junya_GuiltyGearXrd.pdf ; résumés https://www.blendernation.com/2015/07/26/junya-c-motomura-behind-the-scenes-of-guilty-gear-xrd/ et https://polycount.com/discussion/121144/convincing-3d-that-looks-like-2d-wow/p8), de MToon (spécification VRM, copie locale `rendu/docs/mtoon_spec.md`) et des shaders « Genshin-like » (`rendu/docs/genshin_outline.gdshader`).

**Largeur constante à l'écran** — formule (ameye.dev *5 ways to draw an outline*, https://ameye.dev/notes/rendering-outlines/ ; heyheythere *Ink outlines that stay the same width near or far*, https://heyheythere.itch.io/toon-look/devlog/1692292/ink-outlines-that-stay-the-same-width-near-or-far ; Genshin-like, code local) :

```glsl
vec4 clip = projectionMatrix * mv;                    // mv = modelViewMatrix * position
vec3 n = normalize(normalMatrix * normal); n.z = 0.;  // on aplatit la composante vue : sinon les bouts (doigts, nez) poussent des « griffes »
vec2 cn = normalize((projectionMatrix * vec4(n, 0.)).xy);
clip.xy += cn * largeur_px * clip.w * 2.0 / resolution;   // × w annule la division perspective ; ×2 car le clip va de −1 à 1
```
Le ×w est ce qui rend la largeur indépendante de la profondeur ; la division par la résolution (x et y séparément) corrige le rapport d'aspect. MToon exprime la même chose en « ratio de la hauteur d'écran » (`outlineWidthMode: screenCoordinates`, facteur multiplié par `vViewPosition.z / projectionMatrix[1].y`, `rendu/docs/mtoon.vert`).

**Pièges documentés et comment on les règle :**

| Piège | Source | Remède |
|---|---|---|
| Normales séparées aux arêtes dures → trous dans la coque | toon-rp wiki https://github.com/Delt06/toon-rp/wiki/Inverted-Hull-Outline ; Toony Colors Pro | normales **lissées** stockées dans un attribut à part (UV2, tangente, couleur) et utilisées seulement par la coque ; notre peau est fermée et lisse : la normale lissée suffit |
| Pointes qui s'allongent (bouts des doigts) | Genshin-like, commentaire du shader | `n.z = 0` avant l'extrusion (extrusion en xy écran seulement) |
| Coque qui perce la surface dans les creux (sillons, plis) | **mesuré ici**, `rendu/coque_variantes.png` | reculer la coque en profondeur avant projection (`mv.z -= bias`) ; 0,25 u ≈ 2,7 mm efface toutes les « griffures » du dos sans toucher la silhouette. Le code actuel fait la même chose a posteriori, en jetant les fragments de coque à moins de `HPUSH` (1,8 × trait) devant la peau |
| Largeur qui « se perd » en rasant (une partie de l'extrusion part vers la caméra) | Video Poetics *Pixel-perfect outline* https://www.videopoetics.com/tutorials/pixel-perfect-outline-shaders-unity/ | même `n.z = 0` ; résidu négligeable |
| Coque trop large sur de petits objets (bouts de doigts vus de face) | MToon : « applications might want to render thinner as the camera goes away » | plafond : largeur × clamp(taille_apparente / taille_ref) ; pour nous, largeur fixe en px et plancher 1,25 px |

### 2.2 Détection d'arêtes en espace écran (profondeur, normales, identité)

Références : ameye.dev *Edge detection outlines* (https://ameye.dev/notes/edge-detection-outlines/), tutoriel URP (https://emmyvoita.github.io/posts/Unity-URP-Screen-Space-Outlines/), Vertex Fragment Sobel (https://www.vertexfragment.com/ramblings/unity-postprocessing-sobel-outline/), Three.js `SobelOperatorShader.js` (copie locale `rendu/three/`, noyaux 3×3 `Gx = [-1 -2 -1; 0 0 0; 1 2 1]`, lit le canal R d'une image grise).

| Tampon | Ce qu'il détecte | Ce qu'il rate / artefacts | Règle |
|---|---|---|---|
| **Profondeur** | occultations : silhouette, doigt devant doigt, pouce devant paume | une surface très inclinée produit un faux saut (le test « d − d0 > seuil » lit la pente) | seuil × (1 + k·(1 − |N·V|)) (ameye), ou test **symétrique** : `(d+ − d0) − (d0 − d−) > seuil` (une pente continue donne les deux écarts égaux) — validé ici |
| **Normales** | plis, arêtes vives, vallées entre doigts | sur un maillage à facettes, chaque facette devient un trait (« griffures ») ; les vallées douces (tendons) n'ont pas 50° d'écart | n'utiliser qu'avec un maillage lisse ; seuil `dot(n, n0) < 0,3` (≈ 72°) ; coupler avec « pas de saut de profondeur » pour ne pas doubler le contour |
| **Identité** (une couleur par partie / par ongle) | frontière entre deux parties qui se recouvrent, contour de l'ongle | si l'identité est **interpolée** entre sommets (varying), les triangles « mixtes » créent des traits partout (mesuré ici, `demo_essai1`) ; si on trace toute frontière, on souligne la racine des doigts tendus | identité **plate par triangle** (géométrie non indexée, comme le `idm` actuel) ; frontière tracée seulement si (a) saut de profondeur (recouvrement) ou (b) frontière d'ongle |
| Luminance / couleur | — | ne distingue pas un changement de couleur d'un changement de forme (GameDev.net) | ne pas utiliser |

Roberts cross (4 échantillons, en croix sur les diagonales) suffit et coûte moins que Sobel (9) ; pour une épaisseur de trait > 1 px on **échantillonne sur un anneau** de rayon r px (8 ou 12 directions, ce que fait déjà `edgeMat` avec 12) plutôt que de flouter après coup. Three.js `OutlinePass` (copie locale) n'est pas un traceur d'encre : masque des objets sélectionnés, flou gaussien `edgeThickness`, « glow », sous-échantillonnage ×2 — inadapté.

### 2.3 Arêtes d'objet par angle dièdre, et lignes de forme (Blender Freestyle)

Freestyle (manuel Blender, types d'arêtes d'un *Line Set* ; commit d'origine du *Crease Angle*, https://projects.blender.org/archive/blender-archive/src/commit/7d377478c394931f1226fbbacf96e095daf18c5d/release/scripts/ui/properties_render.py) :

| Type | Définition | Pertinence main |
|---|---|---|
| Silhouette | la normale bascule entre « vers » et « loin de » la caméra | = notre coque / arête de profondeur |
| Crease | angle dièdre entre les deux faces < *Crease Angle* (défaut **134,43°**, soit un pli de plus de 45,6°) | une main n'a pas d'arêtes dures : inutile sauf au bord libre de l'ongle |
| Border | arête de maillage ouvert | aucun (peau fermée) |
| Suggestive contour / Ridge & Valley | courbure (rayon de sphère de lissage, epsilon de dérivée Kr) | ce que ferait un illustrateur aux vallées entre doigts repliés — **seulement sur surface lisse** |
| Material boundary | changement de matière | = contour de l'ongle |

Épaisseur « absolue » en pixels, indépendante de la résolution. Freestyle tourne hors temps réel ; on en retient la taxonomie et le crease angle comme seuil.

### 2.4 Lignes = géométrie (Spider-Verse, Mitchells)

Sony Pictures Imageworks (befores & afters, https://beforesandafters.com/2023/06/28/this-was-the-first-cg-animated-movie-ive-ever-heard-of-that-actually-had-a-dedicated-inking-team/ ; VFX Voice, https://vfxvoice.com/imageworks-artists-break-the-mold-to-create-an-alternate-spider-verse/ ; SideFX, https://www.sidefx.com/community/spider-man-into-the-spider-verse/) : les lignes de forme et d'expression sont **dessinées sur le modèle 3D** dans Houdini, converties en **courbes géométriques** qui suivent le personnage (« not textures but actual geometry that moves with the character »), avec poids et effilement par ligne, **légèrement décollées de la surface** (Kismet, *Across the Spider-Verse* : « offset it from the surface, which is a big part of what makes the linework look better »), exportées en polylignes et dont l'épaisseur peut être modulée par la lumière au rendu. Une solution purement 2D (redessiner chaque image) a été écartée parce qu'elle ne tient pas en stéréo ; « les lignes du nez, des oreilles et des **mains** sont assez prévisibles pour être automatisées ».

→ C'est exactement le mécanisme qu'il nous faut pour les « = » des jointures, le U de l'ongle et les plis de la paume : des courbes attachées, pas des pixels.

### 2.5 Ce que font les autres productions citées

- **Guilty Gear Xrd** (GDC 2015) : un seul projecteur ; seuil d'ombre comparé à N·L, **décalé par un canal de couleur de sommet** (l'artiste noircit « toujours » certaines zones) ; **normales éditées** pour supprimer les ombres parasites ; très peu de normal maps : « les propriétés de sommet s'interpolent linéairement, donc ne dépendent pas de la résolution de texture » ; contour = coque inversée, épaisseur et effacement par couleur de sommet ; traits intérieurs dans l'alpha de la texture ILM, **tracés seulement horizontaux ou verticaux dans l'UV** pour rester nets à basse résolution (https://discussions.unity.com/t/guilty-gear-xrd-shader-test/650399) ; ombres colorées par multiplication avec une texture « SSS ». Leçon : vertex > texture ; la seule texture de traits est contrainte par l'UV, ce que nous ne pouvons pas faire sur une peau skinnée librement.
- **Wind Waker** : éclairage par sommet remplacé par une **courbe de teinte lue dans une texture** (en pratique deux tons avec une très légère transition), puis teinte des ombres (https://www.resetera.com/threads/video-how-the-wind-waker-defined-cel-shading.166993/ ; réimplémentation https://github.com/janhohenheim/bevy_wind_waker_shader : « only two colors, the edge is not entirely hard but has an ever-so-slight gradient »).
- **Arcane** (Fortiche) : 3D + **textures peintes** (ombres et lumières peintes dans les textures), compositing lourd, caméras contrôlées plan par plan (https://www.redsharknews.com/why-netflixs-arcane-looks-so-good-how-fortiche-ramped-up-the-animation-pipeline). C'est l'approche actuelle de l'atelier (dessins projetés) poussée au bout — elle marche parce que **chaque plan est cadré** ; elle ne tient pas pour un outil où l'utilisateur tourne la main librement.
- **Genshin / MToon** (VRM) : `shading = linearstep(−1 + toony, 1 − toony, N·L + shift)` avec `shadingToonyFactor` par défaut **0,9** (transition sur N·L ∈ [−0,1 ; 0,1]) et `shadingShiftFactor` (défaut 0) décalable par texture ; couleur d'ombre `shadeColorFactor` distincte de la base ; contour `screenCoordinates` ; rim paramétrique `pow(1 − N·V + lift, p)` (spec locale). Les reconstructions Genshin ajoutent : pas de coque sur le visage (ovale sombre), coque colorée depuis l'albédo assombri (`outline_darken 0,28`, `outline_width 1,25` px, `depth_bias 0,015`).
- **Three.js MeshToonMaterial (r128)** : `coord = N·L·0,5 + 0,5` ; sans `gradientMap`, `coord < 0,7 ? 0,7 : 1,0` (c'est-à-dire seuil N·L = 0,4 et ombre à 70 %) ; avec `gradientMap`, lecture d'une texture 1D, qui doit être en `NearestFilter` pour des marches nettes (extrait de `three.min.js`, doc locale `rendu/docs/MeshToonMaterial.html`). Utilisable, mais sans antialiasing de la lisière et sans décalage de seuil par sommet : on écrit la nôtre.

---

## 3. Rampe de toon et ombre franche

### 3.1 Ce que le dessin impose (mesuré dans CLAUDE.md)

| Grandeur | Valeur | Source |
|---|---|---|
| Ton de l'ombre | **0,82** × aplat (identique sur les deux dessins) | mesure texBack / texFront |
| Part de la main dans l'ombre, main au repos | **0,16 – 0,18** | mesure sur les deux mains (luminance 101 / 101) |
| Aplat | `#00a19a` (0, 161, 154) | logo INJS |
| Ongle | `#96DCD6` (150, 220, 214) | `hand3d.json nail.col` |
| Frange libre de l'ongle | ≈ **1,35** × plus claire que la tablette | photo de l'utilisateur |
| Trait de contour | 6 px de dessin (≈ 1,3 mm sur la main réelle) | `outw` |
| Traits intérieurs / ongle | 2,4 px (≈ 0,5 mm) | `nail.lw` |
| Lumière | (−0,45 ; 0,55 ; 1) normalisé, **fixe dans le repère caméra** (haut-gauche-devant) | `LIGHT`, script.js |

(Échelle : SC = 50 px de dessin par unité ; `push` = 1,8 × 6,6 / 50 = 0,24 u = 2,6 mm ⇒ **1 u ≈ 11 mm, 1 px de dessin ≈ 0,22 mm**.)

### 3.2 La rampe actuelle n'est pas une marche

`s = clamp(0,8 + 0,26 · max(N·L, 0), 0, 1)` : une rampe linéaire de 0,80 (N·L = 0) à 1,0 (N·L ≥ 0,77). Sur un doigt (cylindre) cela donne un dégradé continu sur 40° de tour, visible sur tous les rendus de contrôle (`v2/out/*radial*`), alors que le dessin pose une plage à 0,82 bordée net. Mesuré sur « V (2) » de face : 33 % des pixels de peau sous 0,9 × l'aplat, contre 16–18 % dans le dessin.

### 3.3 Règle v2

```glsl
float nl  = dot(normalize(vN_lissée), L);           // L en repère caméra, fixe
float t   = seuil + biais_sommet;                    // seuil ≈ 0,30 ; biais ∈ [−0,25 ; +0,25] par attribut
float f   = max(feather, fwidth(nl));                // feather ≈ 0,03 : lisière nette mais antialiasée à toute échelle
float lit = smoothstep(t - f, t + f, nl);
color = base * mix(0.82, 1.0, lit);
```
- **Deux marches, pas trois** : le dessin n'en a que deux ; une troisième (lumière spéculaire) casserait l'identité. Pas de rim.
- **Seuil** : à choisir pour retrouver 16–18 % d'ombre main au repos face et dos (la démo à 0,42 donne 0,23 / 0,11 ; viser ≈ 0,30–0,35). C'est un réglage à mesurer, pas à estimer.
- **Biais par sommet** (Guilty Gear) : +0,2 (plus d'ombre) dans le creux de la paume, les commissures, sous la base du pouce, le sillon entre deux doigts repliés ; −0,2 (plus de lumière) sur la tablette de l'ongle et le dos des phalanges. Peint une fois sur le maillage au repos, suit le skinning.
- **Normales de l'éclairage = normales lissées** (pas les normales géométriques du maillage) : sur une main, toute facette visible dans l'ombre se lit comme une tache (c'est ce que Guilty Gear appelle « édition de normales »). Sur un maillage de subdivision, les normales limites sont lisses par construction.
- **Ombre de contact** (doigt replié contre la paume, dessous du pouce) : l'illustrateur en pose une. Techniquement c'est une occultation ambiante en espace écran, binaire et élargie. Le code actuel l'a essayée (`pit`, `cavA`) et obtenu des taches déchirées — parce que le maillage est rugueux et que le test était un seuil brut. À retenter en v2 **après** la surface lisse, avec un test lissé (moyenne sur un anneau) ; pas dans le premier palier.

---

## 4. Où un illustrateur pose les traits sur une main (et où il n'en met pas)

Synthèse des tutoriels (Pencil Kings https://www.pencilkings.com/how-to-draw-hands/, MediBang https://medibangpaint.com/en/use/2023/04/how-to-write-by-hand/, Mammoth Memory https://mammothmemory.net/art/techniques/painting-and-drawing-techniques/how-to-draw-hands.html, Drawmora https://drawmora.com/how-to-draw-hands/, RapidFireArt https://rapidfireart.com/2015/09/15/how-to-draw-hands-part-2-beyond-structure/), des deux dessins de l'utilisateur (`references/`) et de ses photos (`scratchpad/photos/`, `wf2/photos_user/`).

| Endroit | Trait | Forme / règle | Quand il apparaît | Quand il disparaît |
|---|---|---|---|---|
| Dos, IPP et IPD | « = » : deux (parfois trois) petits arcs parallèles, concaves vers le bout, centrés sur le dos du doigt, **largeur ≈ 0,4–0,6 de la largeur du doigt** (dessin de l'utilisateur) | arcs, jamais droits ; le trait s'affine aux deux bouts | toujours un filet au repos (le dessin les montre) ; **s'épaissit et se creuse** en flexion | se réduit à rien en hyperextension |
| Dos, MCP (jointures) | pas de trait au repos (« les jointures détendues ne sont pas proéminentes », Pencil Kings) ; en poing : une courbe par jointure + ombre | le relief se lit par l'**ombre**, le trait seulement au creux entre deux jointures | poing, flexion MCP > 60° | main plate |
| Ongle | **U** ouvert vers le bout : les deux côtés et la base (repli proximal) ; pas de trait au bord libre (ou un filet plus clair) | bras du U pleins sur 0,3–0,5 de la hauteur de l'ongle puis s'affinent (mesuré sur les 5 ongles du dessin) | toujours | jamais, mais réduit à un filet quand l'ongle est vu de chant (N·V < 0,6) |
| Paume, doigts | 1 pli à l'IPD, **2** à l'IPP, 1 (ou 2) à la racine ; arcs concaves vers la paume ; largeur ≈ toute la largeur du doigt | fins au repos | **s'épaississent** en flexion (la peau se plisse) | en extension forcée, s'effacent |
| Paume | les trois grands plis (distal, proximal, thénar) + plis du poignet ; aucun autre | longs, continus, s'affinent aux extrémités | toujours | s'ouvrent (plus fins) main hyper-étendue |
| Commissures | un court trait à la palmure quand deux doigts s'écartent ; une ligne de contact quand ils se touchent | | | |
| Pouce | pli de l'IP (dos) ; pli du thénar (paume) ; **contour** quand le pouce passe devant la paume | | | |
| Tranche / fût du doigt | **rien** | | | |
| Tendons du dos | **rien** (ombre seulement) ; au plus une ombre entre deux tendons sur une main tendue | | | |
| Poignet | 1–2 plis côté paume | | | |

Règle de poids (Drawmora) : trait plus épais sur le côté ombre et là où la forme se détourne ; fin pour les rides et les détails d'ongle. Pour nous : contour 1,0 ; contact doigt/doigt 0,7 ; plis des jointures 0,4–0,6 selon la flexion ; U de l'ongle 0,4 ; plis de paume 0,4.

Ce que montrent les photos de l'utilisateur, à reproduire par l'ombre et non par le trait : la pulpe qui s'aplatit à l'appui ; la frange libre de l'ongle plus claire ; les tendons comme des bombés doux ; en poing (2357, 2364), **aucun jour** entre les bouts des doigts et la paume ; en « quatre » (2370), ombre portée du pouce sur la paume.

---

## 5. L'ongle

### 5.1 Chiffres

| Grandeur | Valeur | Source |
|---|---|---|
| Rayon de courbure transverse, hommes : pouce / index / majeur / annulaire / auriculaire | **11,4 / 8,9 / 8,8 / 7,3 / 5,8 mm** | Jung et al., *Fingernail Configuration*, Arch Plast Surg 2015 (300 volontaires) https://pubmed.ncbi.nlm.nih.gov/26618124 |
| Idem, femmes | 9,6 / 7,4 / 7,3 / 6,8 / 5,2 mm | idem |
| Valeur « générale » citée ailleurs | 13,2 mm (h) / 10,4 mm (f) | Murdan 2011 https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-2494.2011.00663.x |
| Largeur de l'ongle / largeur du doigt | **0,70–0,80** (main de l'utilisateur) ; 0,52–0,57 dans son dessin ; 0,55 dans le rendu actuel | CLAUDE.md (piste N) |
| Rapport largeur / longueur | non trouvé en clair (le tableau de Jung 2015 n'est pas accessible d'ici) ; **estimation** : 0,9–1,1 sur l'index–annulaire, 1,1–1,3 sur le pouce (plus large que long), 0,8–0,9 sur l'auriculaire | à vérifier dans le dossier anatomie / sur les photos (`photo_dos_B_ongles_zoom.jpg`) |
| Courbure longitudinale | faible mais réelle (plaque courbe dans les deux axes, plus marquée aux orteils) | De Berker 2007 https://onlinelibrary.wiley.com/doi/10.1111/j.1467-2494.2007.00372.x |
| Relief de la plaque sur la peau (repli latéral) | ≈ 0,3–0,5 mm — **estimation** (pas de mesure publiée trouvée) | — |
| Frange libre | plus claire (×1,35 sur la photo), de 1 à 3 mm | photo utilisateur |
| Lunule | visible surtout au pouce ; optique (blanche vue à travers la plaque) | StatPearls https://www.ncbi.nlm.nih.gov/sites/books/NBK534769/ |

### 5.2 Rendu v2 de l'ongle (sans texture)

1. **Zone géométrique** : les sommets de la tablette portent un attribut `nail = 1` (ou l'ongle est un sous-maillage) ; frontière nette par triangle. Elle suit le skinning comme le reste.
2. **Volume** : la tablette est bombée transversalement (rayon selon le tableau ci-dessus, ramené à l'échelle de la main modélisée), en relief de 0,3–0,5 mm sur la peau, avec un repli latéral et proximal (petit sillon de 0,2 mm) : c'est ce sillon qui donne la lisière d'ombre et le contour, sans rien peindre.
3. **Couleur** : aplat `#96DCD6` ; **même marche d'ombre que la peau** (0,82) : le bombé fait apparaître naturellement un croissant d'ombre le long du bord opposé à la lumière, ce que le code actuel peint à la main dans `texNailE.b`. Biais de seuil −0,1 sur la tablette (plus souvent éclairée) pour qu'elle ne bascule pas entièrement dans l'ombre vue de biais.
4. **Frange libre** : bande de la tablette au-delà du lit (paramètre `s` le long de l'ongle, s > 0,8), mix 0,45 vers le blanc (valeur actuelle, lisible). Calculée par la paramétrisation de l'ongle (attribut `s`), pas par une texture.
5. **Trait** : la frontière ongle/peau de la passe d'identité donne le U et la base ; la frange libre **n'a pas de trait noir** (le dessin non plus) : on masque la frontière où `s > 0,8` (attribut), ou on la remplace par le filet clair. Largeur du trait = celle des traits intérieurs (2,4 px de dessin ⇒ ≈ 0,4 × contour), constante à l'écran, plafonnée comme aujourd'hui (5/3 du trait) quand l'ongle est vu de chant pour ne pas manger la lamelle.
6. **Validé sur le maillage posé** : avec l'ongle en attribut de sommet et le trait par identité, le contour d'ongle est propre en dos ¾, en rasant et de face sur les doigts repliés (`rendu/zoom_actuel_vs_demo.png`, `rendu/cmp_V_2_actuel_vs_demo.png`). Les « bras du U inégaux » (rapport 1,9 puis 1,25 après correction) disparaissent par construction : le trait est posé en pixels d'écran sur une frontière 3D.

---

## 6. Évaluation de la version actuelle (v8 / v18) : pourquoi elle se dégrade en biais

Mécanismes en place (CLAUDE.md, `source/script.js`) : textures = les deux dessins projetés (UV = position dans le dessin), trait d'ongle en distance signée dans une texture + compensation de largeur, passe « identité » (une couleur par triangle, profondeur) pour les traits de recouvrement, coque inversée en unités du modèle avec rejet a posteriori (`HPUSH`), rampe douce, détecteur de plis éteint, reliefs sculptés (tendons, vallées, jointures, thénar) dans `mesh.dz`.

| Cause | Mesure | Effet visible | Ce que la v2 change |
|---|---|---|---|
| **Traits peints dans la texture** (« = » des jointures, plis de la paume) | raccourci de projection : 0,60 px de dessin par px d'écran d'un côté du doigt, 0,36 de l'autre (CLAUDE.md) ⇒ un trait 2 × plus gros d'un côté ; en vue rasante (`v2/out/V_2_radial.png`, `capture_zoom.png`) les « = » deviennent des « /// » obliques, étirés par le déformeur en arc | « les doigts se déforment avec le mouvement », « la configuration des ongles n'est pas naturelle » | lignes attachées, rendues en rubans d'épaisseur fixe ; aucune texture |
| **Ombre peinte du dessin** (bord de l'échancrure du pouce, croissant d'ongle) | tache rectangulaire sous la base du pouce en profil, étirée ×4–5 (CLAUDE.md, défaut connu 7) | ombres qui ne suivent pas la lumière ni la pose | ombre calculée (marche sur N·L lissé) |
| **Rampe douce** `0,8 + 0,26·N·L` | 33 % de pixels d'ombre en V (2) face contre 16–18 % dans le dessin ; dégradé continu sur le fût des doigts | la main n'est plus un aplat, elle « luit » | 2 marches + biais par sommet |
| **Coque en unités du modèle** | largeur médiane 8 px (dpr 2) à la distance 52 dans les 20 vues mesurées (`rendu_mesure.py`), mais proportionnelle au zoom et à la résolution d'export | trait qui grossit au zoom, « fin et dédoublé » de près (CLAUDE.md), cran sur les facettes | extrusion en espace clip (largeur en px) + recul en profondeur |
| **Maillage rugueux** (marching cubes pas 5 px = 1,1 mm, Taubin, + reliefs sculptés 0,5–1 mm) | le détecteur de plis « ne produit que des griffures » ; dans mes essais, la coque perce dans chaque sillon du dos (`rendu/coque_variantes.png`, colonne de gauche) | tout trait dérivé de la géométrie est bruité ; silhouette en dents de scie en vue dos | surface lisse (subdivision Catmull-Clark d'une cage quad, ou SDF à pas ≤ 0,5 mm fortement lissé) ; reliefs portés par la **forme**, lus par l'ombre |
| **Trait d'ongle en texture** (distance signée 8 bits, 1/12 px) | crénelage du bord intérieur ; 3 passes de correction (largeur à l'écran, plafond, extinction à la base) pour un rapport de bras 1,08–1,5 | ongle « autocollant », bras du U inégaux, tiret noir + tiret blanc de chant | frontière géométrique + identité |
| **Peau unique front/dos fondue sur la tranche** | la tranche (profil) « est déduite, pas dessinée » (défaut 2) | profil sans traits ni ombre cohérente | la tranche n'a besoin d'aucun dessin : couleur unie + ombre calculée |

**Ce qui est bon et à garder** : l'idée de la passe d'identité (une couleur plate par triangle, profondeur linéarisée, seuils de recouvrement 0,12 / 0,3 / 0,7 u), le trait de contact unique entre deux doigts, la règle « deux échantillons sur douze » contre les échardes, le plafond du trait d'ongle en rasant, la lumière fixe en repère caméra, le rayon de trait constant à l'écran, et le vert / l'ombre 0,82 / l'ongle `#96DCD6`.

### 6.1 Rendu de contrôle : le pipeline v2 sur le maillage posé actuel

Script `rendu/demo_v2.py` (lancé par `run_rendu.py`) : il prend le maillage **posé** par l'application (V (2), Poing (A), Index (1) × face / dos / dos ¾ / rasant), jette toutes les textures et le rend avec : G-pass (normales vue + identité plate + ongle en attribut de sommet lu une fois dans `texNail` au repos) → toon 2 marches (seuil 0,42, feather 0,05, ombre 0,82) → coque en espace clip (3,5 px css, reculée de 0,25 u) → arêtes écran (anneau r = 1,6 px, 8 directions ; profondeur par test symétrique, seuil 0,3 u × (1 + 1,2·(1 − |N·V|)) ; identité gated par un saut de profondeur de 0,35 × seuil ; normales éteintes).

Résultats (`rendu/cmp_*_actuel_vs_demo.png`, `rendu/zoom_actuel_vs_demo.png`, `rendu/coque_variantes.png`) :

| Mesure | Actuel | Démo v2 |
|---|---|---|
| Largeur médiane du trait (px, dpr 2), 12 vues | 8,0 partout (coque en unités, distance fixe) | **6,0 partout** (3 px css demandés + antialias), p90 6,3–10 |
| Part d'ombre V (2) face / dos ; Poing dos ¾ | 0,33 / 0,11 / 0,15 | 0,23 / 0,11 / 0,14 (seuil 0,42 ; à abaisser vers 0,30) |
| Contour d'ongle dos ¾, rasant, face replié | U peint, bras inégaux, lamelle « tiret » | trait propre et constant, lamelle lisible |
| Traits de recouvrement (doigt devant doigt, pouce devant paume) | passe identité (bon) | identiques, sans réglage par pose |
| Dos de la main | aplat vide + traits de texture étirés | aplat vide (mais honnête) ; **griffures** si la coque n'est pas reculée (essai 2) ou si l'identité est interpolée (essai 1) |

Trois leçons chiffrées qui ne seraient pas sorties des articles :
1. l'identité **doit** être plate par triangle, et une frontière d'identité ne se trace qu'avec un saut de profondeur (sinon : trait à la racine de chaque doigt tendu) ;
2. la coque inversée doit être **reculée** (0,25 u ≈ 2,7 mm suffit) ; sinon, sur un maillage avec sillons, elle perce partout — c'est ce que `HPUSH` réparait après coup ;
3. un seuil de profondeur de 0,12 u (1,3 mm) est en dessous de la rugosité du maillage ; 0,3 u (3,3 mm, un cinquième de l'épaisseur d'un doigt) est le bon ordre de grandeur pour « une partie passe devant une autre ».

---

## 7. Pipeline v2 proposé (Three.js r128, sans texture peinte)

Contraintes vérifiées dans `three.min.js` r128 : `WebGLRenderTarget` + `DepthTexture` (extension `WEBGL_depth_texture`, déjà utilisée), `OES_standard_derivatives` (`extensions: {derivatives: true}` sur `ShaderMaterial`), **pas de MRT en WebGL1** (une passe = une cible), `WebGLMultisampleRenderTarget` seulement en WebGL2, `MeshToonMaterial` + `gradientMap` disponibles mais trop limités (pas d'AA de lisière, pas de biais). Rien d'autre n'est vendu : on écrit quatre `ShaderMaterial`, ce que fait déjà le code.

### 7.1 Données attachées au maillage (fabriquées une fois au repos par rig3d.py)

| Attribut | Type | Rôle |
|---|---|---|
| `position`, `normal` (lissée) | vec3 | skinning ; `normal` recalculée après pose ou transformée par le skinning (pas de normale par facette) |
| `part` plate (géométrie non indexée pour la G-pass, ou attribut constant par triangle) | float | identité : paume 1, pouce 2, index 3 … auriculaire 6, ongle = +0,5/8 |
| `nail` | float 0/1 + `s` (0 base → 1 bord libre) | tablette, frange libre, masque du trait |
| `shadeBias` | float [−0,25 ; 0,25] | décalage du seuil d'ombre (creux de paume +, commissures +, tablette −) |
| `hullW` | float [0 ; 1] | modulation de la largeur de coque (0 dans les palmures profondes, 1 ailleurs) |
| Courbes de traits | polylignes (points barycentriques : triangle + poids), par trait : `poids`, `profil d'effilement`, `articulation pilote`, `signe` (dorsal : visible en flexion ; palmaire : visible en flexion aussi mais s'ouvre en extension) | lignes attachées : « = » des jointures, U de l'ongle (si l'on préfère au trait d'identité), plis de paume, pli du thénar, poignet |

### 7.2 Passes

```
1. G-pass  → RT_G (RGBA8 : normale vue ×0,5+0,5 en RGB, identité plate en A) + DepthTexture
2. Couleur → écran : toon 2 marches (base / ongle / frange), fwidth AA, biais par sommet
3. Coque   → écran, BackSide, extrusion clip × w (largeur px), n.z = 0, recul mv.z −= 0,25 u, largeur × hullW,
             plancher 1,25 px, couleur #111
4. Traits  → écran, autoClear = false, transparent :
   4a. quad plein écran : arêtes de profondeur (test symétrique, seuil 0,3 u × (1 + 1,2(1 − |n.z|))),
       frontières d'identité gated (saut ≥ 0,35 × seuil) sauf frontière d'ongle (toujours, hors frange),
       anneau de rayon r px, 12 directions, règle « 2 échantillons »
   4b. rubans : chaque polyligne skinnée est extrudée en espace clip (comme la coque) en quad-strip de largeur
       w(t) = poids × profil(t) × visibilité(angle articulation) × clamp(N·V, 0,3, 1), depth test contre
       DepthTexture avec biais 0,05 u (décollé de la surface, Spider-Verse), couleur #111
5. Export : rendu à pixelRatio 2–3 puis réduction (antialiasing des traits et des lisières) — remplace le MSAA
   indisponible sur cible hors écran en WebGL1
```

### 7.3 Paramètres de départ (à régler par mesure, pas à l'œil)

| Paramètre | Valeur | Justification |
|---|---|---|
| Contour (coque) | 3,0–3,5 px css (6–7 px à dpr 2), i.e. **0,6 % de la largeur de la main à l'écran** (6 px / 992 px du dessin) | identité graphique ; démo : 6 px médian constant |
| Traits intérieurs / ongle | 0,4 × contour (2,4 / 6) ; plancher 1,25 px | dessin |
| Recul de la coque | 0,25 u (2,7 mm) | `coque_variantes.png` |
| Seuil de profondeur (recouvrement) | 0,3 u, × (1 + 1,2(1 − |N·V|)) | démo ; équivalent aux 0,3 / 0,12 actuels |
| Seuil d'ombre | N·L = 0,30 ± biais ; feather max(0,03, fwidth) | viser 16–18 % d'ombre au repos |
| Ton d'ombre | 0,82 | dessin |
| Lumière | (−0,45 ; 0,55 ; 1) caméra, fixe ; identique main gauche (pas de nflip) | continuité avec l'actuel, planches cohérentes |
| Ongle | base #96DCD6 ; frange mix 0,45 vers blanc pour s > 0,8 ; biais −0,1 | actuel + photo |
| Visibilité des « = » dorsaux | w = 0,15 + 0,85 · smoothstep(10°, 60°, flexion IPP/IPD) | dessin (filet au repos) + photos (plis marqués fléchis) |
| Visibilité des plis palmaires des doigts | w = 0,4 + 0,6 · smoothstep(0°, 70°, flexion) | photos |
| Plis de la MCP dorsale | w = smoothstep(50°, 90°, flexion MCP) | « jointures détendues peu visibles » |
| Rasant | w × clamp(N·V, 0,3, 1) | plafond actuel 5/3 (même idée) |
| Arêtes par normales | **éteintes** tant que la surface n'est pas de subdivision ; ensuite dot < 0,3 et sans saut de profondeur | essais, CLAUDE.md |

### 7.4 Coût

44 000 sommets × 4 passes (G, couleur, coque, rubans de quelques centaines de segments) + un quad plein écran : identique à aujourd'hui (3 passes + quad). Le skinning CPU reste le poste dominant (13 ms). Pour plusieurs mains et un référent, la G-pass peut être rendue une seule fois pour toute la scène (identités distinctes par main : part + 8 × index de main).

---

## 8. Ce que ça implique pour la v2 (recommandations classées)

**A. Non négociable (sinon la qualité baissera encore selon l'angle)**
1. **Aucune texture peinte** sur la main : ni couleur, ni trait, ni ombre. Couleur unie + attributs de sommet + lignes attachées. Le dessin de l'utilisateur reste la référence de **forme** (silhouette, proportions, position des traits), plus un support de pixels.
2. **Surface lisse** : cage quad à topologie de main (boucles d'arêtes autour des articulations et de l'ongle) + Catmull-Clark 2 niveaux, ou SDF à pas ≤ 0,5 mm lissé ; normales lissées. Pas de relief sculpté à pas de 1 mm.
3. **Contour = coque inversée en espace clip**, largeur en pixels, `n.z = 0`, recul 0,25 u, modulée par `hullW` ; plancher 1,25 px.
4. **Traits de recouvrement = passe d'identité plate** + profondeur, gated par un saut ≥ 0,1 u ; test symétrique de profondeur ; 12 directions, 2 échantillons.
5. **Ombre = deux marches** (1,0 / 0,82), lisière `fwidth`, lumière fixe caméra, normales lissées, biais par sommet.
6. **Ongle = géométrie** : attribut + plaque bombée (rayon 7–9 mm aux doigts, 11 mm au pouce), frange par paramètre `s`, trait par frontière d'identité, pas de trait sur la frange.

**B. Fortement recommandé (c'est ce qui donne « la main d'un illustrateur »)**
7. **Lignes attachées** pour les « = » dorsaux, les plis palmaires, les trois plis de la paume, le thénar, le poignet ; rubans de largeur constante, décollés de 0,05 u, visibilité pilotée par les angles des articulations et par N·V ; effilement aux extrémités.
8. Poids de trait hiérarchisés : contour 1 ; contact 0,7 ; plis 0,4–0,6 ; ongle 0,4.
9. Régler le seuil d'ombre et les largeurs **par mesure** sur les planches de contrôle (part d'ombre 16–18 %, largeur médiane constante ± 10 % sur 12 vues, 0 fragment noir isolé < 20 px dans les fenêtres de jointures), comme la v8 le faisait.
10. Export en sur-échantillonnage ×2–3 puis réduction (le seul antialiasing fiable hors écran en WebGL1).

**C. Plus tard, une fois la surface lisse**
11. Arêtes par normales / vallées (dot < 0,3) pour les sillons entre doigts repliés, si les rubans attachés ne suffisent pas.
12. Ombre de contact en espace écran (anneau, test lissé) pour le creux du poing et sous le pouce.
13. Arêtes « apparent ridges » (Judd 2007) pour les plis que l'illustrateur ajouterait en pose extrême — expérimental.

**D. À ne pas refaire**
- Trait d'ongle en distance signée dans une texture (trois passes de rustines pour un rapport de bras encore 1,25–1,5).
- Détecteur de plis sur le maillage à facettes.
- Coque en unités du modèle sans recul (rejet a posteriori par comparaison de profondeur : fragile, 5 règles spéciales).
- Rampe douce `0,8 + 0,26·N·L`.
- Ombres ou croissants peints.

---

## 9. Incertitudes et limites de ce dossier

- Les pages hors GitHub / raw.githubusercontent n'étaient pas lisibles d'ici (DNS bloqué pour ameye.dev, roystan.net, docs.blender.org, polycount, PubMed, ACM…) : les citations correspondantes viennent des résumés de recherche et des documents disponibles (slides GG Xrd via résumés, spec MToon et shader three-vrm complets, shader Genshin-like complet, OutlinePass et SobelOperatorShader r128 complets, manuel Freestyle via résumés et commit d'origine). Les formules reproduites (extrusion clip, linearstep MToon, Sobel) sont vérifiées sur du code.
- Les rapports largeur/longueur d'ongle de Jung 2015 n'ont pas pu être lus (tableau non accessible) ; estimation donnée, à mesurer sur `photo_dos_B_ongles_zoom.jpg` dans le dossier anatomie.
- Le relief de la plaque d'ongle (0,3–0,5 mm) et le recul de coque (0,25 u) sont des estimations / mesures sur notre maillage, pas des valeurs publiées.
- Les valeurs de seuil (ombre 0,30, profondeur 0,3 u) sont des points de départ mesurés sur le maillage actuel ; elles devront être remesurées sur la surface v2.
- Unsplash : le serveur MCP refuse (courriel non confirmé) et `images.unsplash.com` est bloqué en curl ; les références photo utilisées sont celles de l'utilisateur (2354, 2357, 2364, 2370, `photo_dos_B_ongles_zoom`, `photo_dos_V2_zoom`).
- La démo tourne sur le maillage v8 : elle prouve la constance du rendu sous les angles, pas la beauté finale (dos vide, facettes) — celle-ci dépend du maillage v2 (dossier anatomie) et des lignes attachées.

---

## 10. Fichiers produits

- `rendu/demo_v2.py` — pipeline v2 appliqué en page au maillage posé (paramètres en ligne de commande : `hullPx edgePx thr feather shade dThr dGraze nThr idGate hullBias recomputeNormals tag out`).
- `rendu/demo_final_coque_reculee/` — 12 rendus v2 + `planche_*.png`.
- `rendu/demo_essai1_normales_id/`, `rendu/demo_essai2_coque_sans_recul/` — essais intermédiaires (griffures : identité interpolée, puis coque qui perce).
- `rendu/cmp_V_2_actuel_vs_demo.png`, `rendu/cmp_Poing_A_actuel_vs_demo.png`, `rendu/cmp_Index_1_actuel_vs_demo.png` — actuel | v2, 4 vues.
- `rendu/zoom_actuel_vs_demo.png` — ongles dos ¾, index en rasant, poing de face, doigts repliés.
- `rendu/coque_variantes.png` — coque sans recul / sans coque / coque reculée de 0,25 u.
- `rendu/rendu_mesure.py`, `rendu/mesure_demo.py` — largeur des traits (transformée de distance sur le squelette des pixels noirs).
- `rendu/docs/` — spec MToon, `mtoon.vert` / `mtoon.frag` (three-vrm), `genshin_outline.gdshader`, doc `MeshToonMaterial` r128. `rendu/three/` — `OutlinePass.js`, `SobelOperatorShader.js`, `ToonShader.js`, `LuminosityShader.js` r128.

## 11. Sources

- Motomura J., *GUILTY GEAR Xrd's Art Style: The X Factor Between 2D and 3D*, GDC 2015 — https://www.ggxrd.com/Motomura_Junya_GuiltyGearXrd.pdf ; résumés : https://www.blendernation.com/2015/07/26/junya-c-motomura-behind-the-scenes-of-guilty-gear-xrd/ , https://polycount.com/discussion/121144/convincing-3d-that-looks-like-2d-wow/p8 , https://discussions.unity.com/t/guilty-gear-xrd-shader-test/650399 , https://miketon.posthaven.com/maya-cgfx-shader-inspired-by-guilty-gear-xrd-gdc-presentation
- VRM MToon 1.0 spec — https://github.com/vrm-c/vrm-specification/blob/master/specification/VRMC_materials_mtoon-1.0/README.md ; three-vrm MToon shaders — https://github.com/pixiv/three-vrm/tree/dev/packages/three-vrm-materials-mtoon/src/shaders
- Genshin-like shader (Godot) — https://github.com/Tamicktom/genshin-like-shader
- ameye.dev, *5 ways to draw an outline* — https://ameye.dev/notes/rendering-outlines/ ; *Edge detection outlines* — https://ameye.dev/notes/edge-detection-outlines/
- heyheythere, *Ink outlines that stay the same width near or far* — https://heyheythere.itch.io/toon-look/devlog/1692292/ink-outlines-that-stay-the-same-width-near-or-far
- Video Poetics, *Pixel-Perfect Outline Shaders* — https://www.videopoetics.com/tutorials/pixel-perfect-outline-shaders-unity/
- torchinsky, *Cel-shading: some tricks* — https://torchinsky.me/cel-shading/
- Delt06 toon-rp, *Inverted Hull Outline* — https://github.com/Delt06/toon-rp/wiki/Inverted-Hull-Outline
- Emmy Voita, *Screen Space Outlines (URP)* — https://emmyvoita.github.io/posts/Unity-URP-Screen-Space-Outlines/ ; Vertex Fragment, *Sobel Outline* — https://www.vertexfragment.com/ramblings/unity-postprocessing-sobel-outline/ ; GameDev.net *Screen-Space Outline* — https://gamedev.net/shaderlab/40-screen-space-outline/
- bgolus, *The Quest for Very Wide Outlines* (JFA) — https://bgolus.medium.com/the-quest-for-very-wide-outlines-ba82ed442cd9
- Three.js r128 : `OutlinePass.js`, `SobelOperatorShader.js`, `ToonShader.js`, `MeshToonMaterial` — https://github.com/mrdoob/three.js/tree/r128
- Blender Freestyle, Line Set — https://docs.blender.org/manual/en/latest/render/freestyle/view_layer/line_set.html ; crease angle 134,43° — https://projects.blender.org/archive/blender-archive/src/commit/7d377478c394931f1226fbbacf96e095daf18c5d/release/scripts/ui/properties_render.py ; https://artisticrender.com/a-guide-to-blender-freestyle-rendering-with-eevee-and-cycles/
- Hertzmann A., *Introduction to 3D NPR: Silhouettes and Outlines* (1999) — https://mrl.cs.nyu.edu/publications/npr-course1999/hertzmann-intro3d.pdf ; Hertzmann & Zorin 2000 — https://cs.nyu.edu/~dzorin/papers/hertzmann2000iss.pdf
- Cole et al., *Where Do People Draw Lines?* (2008) — https://gfx.cs.princeton.edu/pubs/cole_2008_wdp/index.php ; Hertzmann 2020 — https://aaronhertzmann.com/2020/04/21/ar-vs-cs.html
- Judd, Durand, Adelson, *Apparent Ridges* (2007) — https://people.csail.mit.edu/tjudd/apparentLines.pdf ; DeCarlo et al., *Suggestive Contours* (2003) — https://users.cs.northwestern.edu/~ago820/cs395/Papers/W03_NPR/Decarlo_2003.pdf
- Spider-Verse : https://beforesandafters.com/2023/06/28/this-was-the-first-cg-animated-movie-ive-ever-heard-of-that-actually-had-a-dedicated-inking-team/ , https://beforesandafters.com/2024/01/10/giving-spider-man-across-the-spider-verse-that-crucial-hand-made-quality/ , https://vfxvoice.com/imageworks-artists-break-the-mold-to-create-an-alternate-spider-verse/ , https://www.sidefx.com/community/spider-man-into-the-spider-verse/ , https://www.cartoonbrew.com/feature-film/if-its-not-broke-break-it-sony-imageworks-renegade-approach-to-spider-man-into-the-spider-verse-167321.html
- Arcane : https://www.redsharknews.com/why-netflixs-arcane-looks-so-good-how-fortiche-ramped-up-the-animation-pipeline , https://riotupdates.com/arcane/production/
- Wind Waker : https://www.resetera.com/threads/video-how-the-wind-waker-defined-cel-shading.166993/ , https://github.com/janhohenheim/bevy_wind_waker_shader , https://panthavma.com/articles/shading/toonshading/ , https://roystan.net/articles/toon-shader/
- Dessin de mains : https://www.pencilkings.com/how-to-draw-hands/ , https://medibangpaint.com/en/use/2023/04/how-to-write-by-hand/ , https://mammothmemory.net/art/techniques/painting-and-drawing-techniques/how-to-draw-hands.html , https://drawmora.com/how-to-draw-hands/ , https://rapidfireart.com/2015/09/15/how-to-draw-hands-part-2-beyond-structure/ , https://www.animeoutline.com/how-to-draw-hand-poses-step-by-step/
- Ongles : Jung et al. 2015 — https://pubmed.ncbi.nlm.nih.gov/26618124 (PMC4659990) ; Murdan 2011 — https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-2494.2011.00663.x ; De Berker 2007 — https://onlinelibrary.wiley.com/doi/10.1111/j.1467-2494.2007.00372.x ; StatPearls — https://www.ncbi.nlm.nih.gov/sites/books/NBK534769/
- Normales lissées pour la coque : https://flatkit.dustyroom.com/stylized-surface/ , https://jeanmoreno.com/unity/toonycolorspro/doc/
