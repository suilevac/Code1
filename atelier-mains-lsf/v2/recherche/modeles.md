# Dossier « modeles » — Maillages de main 3D disponibles et faisabilité technique (palier v2)

Date : 2026-10-15. Tout ce qui suit a été **téléchargé, chargé et rendu depuis cette machine** (pas de chiffre recopié d'une fiche produit). Les fichiers, rendus et scripts sont dans `/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/v2/recherche/modeles/`.

Rappel du besoin (CLAUDE.md + jugement de l'utilisateur) : une main **à ses proportions**, volume vrai, **ongles modelés**, articulations propres, toute l'amplitude humaine, même qualité sous tous les angles, les deux mains, rendu aplat + ombre franche + contour, exportée en PNG depuis three.js.

---

## 1. Ce qui passe par le réseau depuis ici (mesuré)

| Hôte | curl | Conséquence |
|---|---|---|
| `raw.githubusercontent.com` | **200** | tout fichier d'un dépôt GitHub public se télécharge (y compris binaires de 40 Mo : testé) |
| `registry.npmjs.org` (métadonnées + tarballs `/-/x.tgz`) | **200** | paquets npm complets |
| `pypi.org` + `files.pythonhosted.org` | **200** | **`pip install --user` fonctionne** (testé, voir §5) |
| `github.com`, `api.github.com`, `codeload.github.com` | 403 | pas de clone, pas d'archive zip, pas d'API ; mais l'outil GitHub MCP `search_code` fonctionne (pas `get_file_contents` hors dépôt autorisé) |
| `cdn.jsdelivr.net`, `sketchfab.com`, `huggingface.co`, `images.unsplash.com`, `blender.org` (download/projects/studio), `polyhaven.com`, `quaternius.com`, `blendswap.com`, `opengameart.org` | 000 (DNS/tunnel refusé) | aucune bibliothèque de modèles « grand public » n'est joignable ; WebFetch lit les pages GitHub (listing de dossiers) mais pas ces sites |

Piège Python : `python3 -I` désactive le *user site* ; les paquets installés avec `--user` ne s'importent qu'avec `python3 -P` (chemin sûr, sans le répertoire du script).

---

## 2. Candidats examinés — tableau récapitulatif

Sommets/triangles mesurés avec trimesh après chargement ; « ongles » jugé sur rendu (Blender Cycles ou projection numpy, gros plan ×8 sur le bout de l'index).

| # | Candidat | Source (URL) | Licence (vérifiée dans le fichier) | Format | Sommets main (1 main) | Triangles | Ongles modelés | Topologie | Rig fourni | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **MakeHuman hm08 `base.obj`** | `https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/3dobjs/base.obj` | **CC0 1.0** (en-tête du fichier : « explicitly released as CC0 in september 2020 » ; LICENSE.md §C : « The base mesh and proxies … released under CC0 1.0 Universal ») | OBJ quads | **1 383** (main gauche isolée au poignet) ; 21 849 après Catmull-Clark ×2 | 2 720 (brut) / 43 520 (CC×2) | **OUI** — plaque d'ongle en creux, lit et repli visibles au gros plan (`makehuman/bpy_mh_planche.png`, rangée 2) | **100 % quads**, anneaux de **14 sommets** sur les doigts, 4-6 anneaux par phalange, arête médiane **3,4 mm** (min 0,3, max 19,9 mm à la paume) | **OUI, CC0** : `default.mhskel` (163 os dont wrist + 4 métacarpiens + 15 phalanges par main, centres définis par des cubes-repères dans le maillage) + `default_weights.mhw` (1 894 sommets pondérés pour la main gauche, poids max 1,0) + **targets** de main (`l-hand-fingers-length/diameter/distance`, `l-hand-scale`) | **MEILLEURE BASE** |
| 2 | Valve « Index » hand (`godot_openxr`) | `https://raw.githubusercontent.com/GodotVR/godot_openxr/master/demo/addons/godot-openxr/assets/valve_hand_models/left_hand.glb` | **BSD-3-Clause**, « Copyright (c), Valve Corporation » (fichier LICENSE à côté) | GLB skinné, 2 textures (PNG + JPEG), 40 Mo | **3 028** | 4 899 | non (main **gantée** : bracelet au poignet, matériau `glove.material`) | tris, doigts à 8-10 sommets par anneau | 26 joints OpenXR (Wrist, 5 × Metacarpal/Proximal/Intermediate/Distal/Tip, Palm) | gant VR, pas une main nue ; utile seulement comme référence de rig OpenXR |
| 3 | WebXR `generic-hand` (`@webxr-input-profiles/assets` 1.0.20) | `https://registry.npmjs.org/@webxr-input-profiles/assets/-/assets-1.0.20.tgz` → `dist/profiles/generic-hand/left.glb` | **MIT** (LICENSE.md du paquet, © 2019 Amazon ; README : « Assets are available under MIT license ») | GLB skinné | 1 360 | 2 314 | **non** (bouts arrondis lisses, gros plan = facettes nues) | tris, segments quasi cylindriques | 25 joints XRHand (nommage WebXR) | c'est le modèle de la **v3 rejetée** (« pas sa main ; la peau s'étire, les ongles se déforment ») |
| 4 | A-Frame `leftHandHigh.glb` (`aframevr/assets`) | `https://raw.githubusercontent.com/aframevr/assets/master/controllers/hands/leftHandHigh.glb` | **NON ÉTABLIE** : le GLB porte « Copyright © Unboring SLU 2020. All rights reserved. », aucun LICENSE dans le dépôt | GLB skinné, 7 animations | 1 425 (Low : 329) | 2 320 | non | tris | 16 os (Palm + 3 × 5) | **exclure** (licence) |
| 5 | Microsoft Rocketbox `Male_Adult_01.fbx` | `https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/master/Assets/Avatars/Adults/Male_Adult_01/Export/Male_Adult_01.fbx` | **MIT** (README : « The library of avatars is now released under MIT License ») | FBX binaire 7.4 (importé avec bpy) | **394** (sommets dominés par les os de la main gauche) sur 4 025 pour le corps « hipoly » | ≈ 700 | non | tris, doigts en boudins | Biped 3ds Max : `Bip01 L Hand` + 15 os de doigts | main de jeu vidéo 2010, trop pauvre |
| 6 | xeogl `hand.obj` | `https://raw.githubusercontent.com/xeolabs/xeogl/master/examples/models/obj/hand/hand.obj` | dépôt MIT mais **provenance du modèle inconnue** (export Blender 2.69, aucun crédit) | OBJ | 1 849 (avec avant-bras) | 3 371 | non | tris | non | exclure (provenance) |
| 7 | beat-pose `hand.obj` | `https://raw.githubusercontent.com/charliegerard/beat-pose/master/assets/models/hand.obj` | dépôt **GPL-3**, modèle Maya sans crédit | OBJ | 1 683 | 2 740 | non (bouts plats) | quads triangulés | non | exclure |
| 8 | gsgen `Hand_Anatomy_Practice.obj` | `https://raw.githubusercontent.com/gsgen3d/gsgen/main/objects/hand.obj` | **inconnue** (fichier nommé comme un modèle Sketchfab) | OBJ | 1 329 | 2 351 | non | quads | non | exclure |
| 9 | DEODR `hand.obj` | `https://raw.githubusercontent.com/martinResearch/DEODR/master/deodr/data/hand.obj` | BSD-2 (dépôt) | OBJ | 526 | 1 048 | non | très basse déf. | non | trop pauvre |
| 10 | scenepic `hand.obj` | `https://raw.githubusercontent.com/microsoft/scenepic/main/ci/assets/hand.obj` | MIT (dépôt) | OBJ | 520 | 1 036 | non | très basse déf. | non | trop pauvre |
| 11 | handAR `hand.obj` | `https://raw.githubusercontent.com/wbstx/handAR/master/model/hand.obj` | — | OBJ | **778** = topologie **MANO** | 1 538 | non | — | — | **exclure** (MANO, licence restrictive) |
| 12 | Blender Studio « Human Base Meshes » (2023, 17 maillages dont une main, quads, multirésolution) | `https://www.blender.org/download/demo-files/` (bundle Blender 3.6) | **CC0** (annonce 80.lv / CG Channel / notes de version 3.6) | .blend | n.c. | n.c. | annoncé « photoréaliste » | quads | non | **injoignable d'ici** (blender.org bloqué) ; à récupérer **sur le poste de l'utilisateur** si on veut une 2e base de plus haute définition |
| 13 | BlendSwap « Hands Rigged » 22269 | `https://blendswap.com/blend/22269` | CC0 (fiche) | .blend | n.c. | n.c. | non précisé, pas de pouce rigué | — | partiel | injoignable, et rig incomplet |
| 14 | MPFB2 (plugin Blender MakeHuman) | `https://static.makehumancommunity.org/mpfb.html` | même base hm08 CC0 | — | = #1 | | | | | pas une autre main : **même maillage** que #1 |
| 15 | MANO / SMPL / SMPL-X / NIMBLE / HTML | — | licences recherche non commerciales, redistribution interdite | — | 778 | — | non (MANO sans ongles) | — | — | **exclus** d'office |
| 16 | Ultraleap UnityPlugin (Apache 2.0 pour le code) | `https://github.com/ultraleap/UnityPlugin` | modèles FBX non indexés par la recherche GitHub ; licence des **assets** non confirmée | FBX | ? | | | | | non vérifiable d'ici |
| 17 | godot-xr-tools hands | `addons/godot-xr-tools/hands/About.md` | le README dit : « The Hand Mesh was made using the Makehuman Community Edition … modified inside Blender » → donc **dérivé de #1** | GLB (chemins non trouvés) | | | | | | confirme que MakeHuman est la base CC0 standard des mains libres |
| 18 | npm `three` 0.186.1 | registre | MIT | — | aucun modèle de main dans le paquet | | | | | — |
| 19 | npm `hand-model`, `three-hand-model`, `rigged-hand`, `low-poly-hand` | registre | — | — | **404** (n'existent pas) | | | | | — |
| 20 | Khronos glTF-Sample-Assets (`model-index.json`) | raw | diverses | — | **aucun modèle de main** | | | | | — |

Rendus à regarder : `makehuman/bpy_mh_planche.png` (Blender Cycles, subdivision ×2, 5 vues + 4 gros plans d'ongle), `makehuman/o_makehuman_raw.png`, `makehuman/o_makehuman_cc2.png`, `gh/o_valve.png`, `npm/o_webxr.png`, `gh/o_beatpose.png`, `gh/bpy_rocketbox_planche.png`, `gh/r_*.png` (les autres).

---

## 3. Le candidat retenu en détail : MakeHuman hm08 (CC0)

### 3.1 Fichiers récupérés (tous CC0, en-tête « (c) 2020/2021 Data Collection AB, Joel Palmius, Jonas Hauquier CC0 »)

| Fichier | Taille | Contenu utile |
|---|---|---|
| `base.obj` | 1,75 Mo | 19 158 sommets, 18 486 quads (corps 13 380 sommets + helpers) ; groupes `body`, `helper-*`, **`joint-*` (cubes-repères : centroïde = centre articulaire)** |
| `default.mhskel` | 118 ko | 163 os ; par main : `wrist`, `metacarpal1..4`, `finger1-1..3` (pouce), `finger2..5-1..3` ; chaque os = tête/queue = index de sommets du maillage + plan de rotation |
| `default_weights.mhw` | 898 ko | poids de peau par os (139 os pondérés) |
| `l-hand-fingers-length-incr/decr.target`, `l-hand-fingers-diameter-incr.target`, `l-hand-scale-incr.target` | 29-41 ko | déplacements par sommet (1 396 lignes) pour **allonger les doigts, les épaissir, agrandir la main** : premier levier de retaille |
| `modeling_modifiers.json` | — | liste les modificateurs de main : `fingers-distance`, `fingers-diameter`, `fingers-length`, `hand-scale`, `hand-trans` (gauche et droite) |

### 3.2 Chiffres mesurés sur la main gauche (unités MakeHuman = décimètres)

| Mesure | Valeur | Remarque |
|---|---|---|
| Sommets / quads de la main (coupe x > poignet − 2 mm) | 1 383 / 1 360 | la coupe de mon script est en dents de scie au poignet : à refaire proprement par boucle d'arêtes |
| Longueur poignet → bout du majeur | 1,768 dm = **17,7 cm** | main humaine adulte masculine ≈ 18,9-19,3 cm : la main MH est un peu courte |
| Index MCP → bout | 7,06 cm | |
| Index : P1 / P2 / P3+pulpe | 2,52 / 2,26 / 2,32 cm → **1 : 0,90 : 0,92** | anatomie ≈ 1 : 0,58 : 0,55 (40/23/17 mm + pulpe) → **les repères de la P1 sont trop courts** ; le dessin de l'utilisateur doit remplacer ces centres |
| Pouce : métacarpien / P1 / P2+pulpe | 2,64 / 3,59 / 2,33 cm → 1 : 1,36 : 0,88 | anatomie 1 : 0,67 : 0,55 ; le dessin de l'utilisateur (CLAUDE.md, piste T) donne 193,6 / 123,5 / 104,2 px = 1 : 0,64 : 0,54 → **il faut déplacer les centres articulaires** du pouce MH |
| Sommets par anneau de doigt | **14** (index, majeur) | 4-6 anneaux par phalange ; après CC×2 : 56 par anneau |
| Arêtes de la main | médiane 3,44 mm, min 0,34, max 19,9 | la paume est grossière (quads de 2 cm) : subdivision indispensable |
| Ongles | **modelés** (plaque + repli) sur les 5 doigts | visibles dès la subdivision ×1 ; au repos la plaque est en léger creux (lit), pas bombée : à rebomber par un déplacement |
| Poids de peau, main gauche | 1 894 sommets pondérés (doigts 114-251 sommets par os, métacarpiens 192-248, poignet 248) | permet immédiatement une pose par skinning classique (LBS ou DQS) |

### 3.3 Ce que donne le rendu
- Brut (1 383 sommets) : facetté mais la forme est juste (éminences, dos bombé, articulations marquées).
- Catmull-Clark ×2 (21 849 sommets, calcul < 1 s en numpy, `catmull.py`) : surface lisse et continue, doigts ronds, **ongles lisibles** (gros plans Blender). Deux subdivisions suffisent pour le rendu aplat ; une troisième (87 k sommets) ne serait utile que pour les très gros plans.
- Les 14 sommets par anneau sont suffisants après ×2 pour un contour propre sous tous les angles, ce que la v8 obtenait avec 44 000 sommets de marching cubes à 5 px.

---

## 4. L'autre voie : génération procédurale (SDF + marching cubes, comme `rig3d.py`)

### 4.1 Outils réellement installables ici (testés)

| Paquet | pip `--user` | Import | Utile pour |
|---|---|---|---|
| `trimesh` 5.1.1 | OK | OK | chargement OBJ/GLB/PLY/STL, normales, `subdivide_loop`, booléens simples, export GLB (**sans squelette**) |
| `pygltflib` 1.16.5 | OK | OK | lire/écrire GLB **avec skins/joints/poids** (c'est ce qu'il faut pour sortir une main skinnée pour three.js) |
| `pyvista` 0.49.1 | OK | OK | `contour` (marching cubes VTK), `smooth_taubin`, `decimate`, `subdivide` (loop/butterfly/linear) |
| `manifold3d` 3.5.4 | OK | OK | CSG exact + `level_set` (marching cubes d'une fonction), `smooth`, `refine` |
| `scikit-image` 0.26 | déjà là | OK | `marching_cubes` (déjà utilisé par rig3d.py) |
| `matplotlib` 3.11 | OK | OK | rendus de contrôle |
| **`bpy` 5.2.2 LTS** (Blender en module Python, roue cp313 manylinux ≈ 300 Mo) | **OK** | **OK** (sans écran) | **tout Blender par script** : import OBJ/FBX/GLB, Subdivision Surface, Shrinkwrap, Armature + poids automatiques, Lattice, Multires, **export glTF/GLB avec squelette et poids**, rendu Cycles CPU (une vue 700 px en 4 s) |
| `sdf` de PyPI | OK mais **ce n'est pas fogleman/sdf** (c'est « Scientific Data Format ») | — | le vrai `fogleman/sdf` (MIT) a été récupéré fichier par fichier depuis raw.githubusercontent dans `fogleman_sdf/` ; il n'apporte rien que numpy + skimage ne fassent déjà |
| `pymeshlab` 2025.7 | OK | **non** (`libOpenGL.so.0` manquant) | inutilisable ici |
| `open3d` | OK | **non** (`libEGL.so.1`) | inutilisable ici |
| `igl` | **pas de roue** cp313 | — | — |

### 4.2 Verdict sur la voie SDF
La v8 fait déjà ce que la voie SDF peut faire : silhouette gonflée + marching cubes + Taubin. Ses limites viennent de la *forme* donnée à la fonction (ellipses extrudées), pas de l'outil. Construire une **vraie** main par SDF (éminences thénar/hypothénar, bosses des MCP, pulpes, lit d'ongle avec repli, palmures) revient à modéliser à la main plusieurs dizaines de primitives avec des unions lisses, puis à re-déduire des poids de peau et des centres articulaires ; chaque retouche de forme change la topologie du maillage extrait (pas de correspondance sommet à sommet entre deux générations), ce qui rend impossible la stabilité des UV, des textures (`texNail`, dessin paume/dos) et des réglages fins d'articulation accumulés dans script.js. C'est la cause structurelle des « boudins », des ongles qui se déforment et de la qualité qui baisse selon l'angle : on repart de zéro à chaque itération.

Un maillage à topologie fixe (quads, anneaux réguliers, ongles dans la topologie) règle ces quatre points d'un coup : les anneaux se replient proprement aux articulations, l'ongle est une région de sommets qui suit rigidement la phalange distale, les UV sont stables, et les poids se règlent une fois.

---

## 5. Risques de chaque voie

| Voie | Risques | Parade |
|---|---|---|
| **A. MakeHuman retaillé** (recommandée) | (1) « Pas sa main » : la silhouette MH n'est pas la sienne (main 17,7 cm, doigts plus fins, P1 trop courte) | retaille **imposée par son dessin** : ajustement des sommets en 2D sur la silhouette paume/dos (déjà exacte dans `rig3d.py`), Shrinkwrap/lattice bpy ou déplacement laplacien ; les targets MH donnent les premiers 30 % |
| | (2) Centres articulaires MH approximatifs (pouce surtout) | remplacer par les centres mesurés (CP, IP8, chaîne pouce à deux axes de la piste T) |
| | (3) Coupe du poignet en dents de scie dans mon extraction | couper sur une boucle d'arêtes (bpy ou sélection des quads par poids `wrist.L`) et boucher |
| | (4) Ongles en creux au repos, bombé absent | déplacement normal (NDOME existant) sur la région d'ongle, maintenant définie par des quads et non par une texture |
| | (5) Peau de la paume grossière (quads 2 cm) | CC×2 avant skinning ; ou CC×1 + lissage dans le shader |
| | (6) Droite = miroir de la gauche : MH est symétrique, pas la main réelle | miroir du maillage + textures miroir (déjà le choix v8) ; mesurer sur ses photos si l'asymétrie se voit (non, en pratique) |
| **B. SDF procédurale** | topologie instable, pas d'ongles dans la géométrie, poids à recalculer à chaque génération, coût (44 k sommets à 5 px) | aucune bonne parade : c'est ce qui a produit v1→v8 |
| **C. Blender Studio Human Base Meshes** (CC0, plus haute définition) | injoignable d'ici, format .blend (lisible par bpy une fois le fichier là) | à télécharger par l'utilisateur sur blender.org si un jour la définition MH ne suffit plus ; **même méthode** de retaille s'applique |
| **D. Modèles VR (Valve, WebXR, A-Frame)** | gant ou peau lisse sans ongles ; licence A-Frame non établie ; c'est le choix v3 rejeté | ne servent que de référence pour le nommage des joints OpenXR |

---

## 6. Ce que ça implique pour la v2 (recommandations classées)

1. **Base = MakeHuman hm08, main gauche, quads, CC0** (`makehuman/mh_hand_left_quads.obj` + `default.mhskel` + `default_weights.mhw`). Pas de modèle VR, pas de MANO, pas de re-génération par SDF. Mentionner la CC0 dans le README (aucune attribution exigée, mais la mentionner est propre).
2. **Pipeline Python en trois étapes, exécutable ici** : (a) extraction propre de la main (boucle d'arêtes au poignet, bouchage) ; (b) **retaille sur le dessin de l'utilisateur** — sommets projetés sur la silhouette paume/dos déjà extraite par `rig3d.py`, longueurs de phalanges et centres articulaires = ceux mesurés (CP, IP8, pouce piste T), épaisseurs = ses photos de profil (IMG_2364) ; (c) Catmull-Clark ×2 (script `catmull.py`, < 1 s) puis re-pondération (poids MH transférés par plus proche sommet, ou poids automatiques bpy) et **export GLB skinné via `pygltflib` ou `bpy.ops.export_scene.gltf`**.
3. **Garder la topologie fixe pour toujours** : les UV (dessin paume/dos, `texNail`), les régions (ongles, palmures, éminences) et les poids deviennent des attributs de sommet stables ; toute retouche future est un déplacement, jamais une régénération.
4. **Ongles = sommets, plus texture seule** : la région d'ongle MH (plaque + repli) reçoit un bombé par déplacement normal et le trait « U » en contour de région, donc net sous tous les angles et insensible au raccourci de texture (les quatre causes de la piste N disparaissent).
5. **Skinning dans three.js par `SkinnedMesh` standard** (GLB chargé par `GLTFLoader`, 20 os par main : wrist, 4 métacarpiens, 15 phalanges) avec le déformeur en arc actuel réécrit comme correction de poids/« bulge » à l'articulation, ou en gardant `skinMesh` sur des anneaux réguliers (ce qui le simplifie : chaque anneau a une abscisse `tau` exacte). Les 4 métacarpiens donnent la voûte palmaire (poing, opposition) que la v8 n'a pas.
6. **Budget** : CC×2 = 21 849 sommets/main (43 520 triangles), moitié de la v8 (44 000 sommets) pour une surface plus lisse ; deux mains = 87 k triangles, trivial pour WebGL.
7. **Main droite = miroir** du même GLB (déjà le choix v8), mêmes poids, textures miroir.
8. **bpy est disponible ici** : l'utiliser pour les opérations lourdes (coupe propre, Shrinkwrap sur un volume cible, poids automatiques, export GLB) et pour des rendus de contrôle Cycles (4 s/vue) sans passer par Chromium.
9. **Si plus de définition est voulue plus tard** : Blender Studio Human Base Meshes (CC0) — à déposer par l'utilisateur dans le projet ; même pipeline.
10. **À ne pas refaire** : rechercher des mains sur Sketchfab/TurboSquid/Free3D depuis ici (injoignables, licences floues), ou espérer un paquet npm/pypi « hand » (inexistants : 404 vérifiés).

---

## 7. Incertitudes
- Les proportions détaillées de la main de l'utilisateur (longueurs de phalanges des quatre doigts, épaisseurs) ne sont pas dans ce dossier : elles relèvent du dossier anatomie/mesures ; ici seules les valeurs du pouce (CLAUDE.md) ont servi de comparaison.
- La qualité des poids MH aux palmures et à la base du pouce n'a pas été testée en pose (seulement comptée) ; il faudra probablement les retoucher (c'est prévu dans le pipeline).
- Blender Studio Human Base Meshes : « main » confirmée dans le bundle par les annonces, mais ni le nombre de sommets ni la présence d'ongles n'ont pu être vérifiés (site injoignable).
- Licence des assets Ultraleap et A-Frame : non établie → traités comme exclus.
- Rocketbox : un seul avatar testé (Male_Adult_01, 394 sommets de main) ; les autres sont de la même famille, le verdict ne changerait pas.

## 8. Sources
- MakeHuman dépôt : https://github.com/makehumancommunity/makehuman — LICENSE.md §C (assets CC0) : https://raw.githubusercontent.com/makehumancommunity/makehuman/master/LICENSE.md ; base.obj, default.mhskel, default_weights.mhw, targets `armslegs/`, `modifiers/modeling_modifiers.json` (chemins dans le tableau §2).
- Topologie hm08 (quads, « optimized for subdivision ») : https://static.makehumancommunity.org/makehuman/docs/professional_mesh_topology.html ; MPFB2 = même base : https://static.makehumancommunity.org/mpfb/faq/differences_between_mpfb2_and_makehuman.html
- godot-xr-tools, mains dérivées de MakeHuman : https://raw.githubusercontent.com/GodotVR/godot-xr-tools/master/addons/godot-xr-tools/hands/About.md
- Valve hand models (BSD-3) : https://github.com/GodotVR/godot_openxr/tree/master/demo/addons/godot-openxr/assets/valve_hand_models
- WebXR input profiles assets (MIT) : https://github.com/immersive-web/webxr-input-profiles/tree/main/packages/assets ; paquet npm `@webxr-input-profiles/assets` 1.0.20
- A-Frame assets : https://github.com/aframevr/assets (pas de LICENSE ; GLB © Unboring SLU)
- Microsoft Rocketbox (MIT) : https://github.com/microsoft/Microsoft-Rocketbox
- Blender Studio Human Base Meshes (CC0, Blender 3.6) : https://www.cgchannel.com/2023/06/download-blender-studios-free-human-base-meshes ; https://80.lv/articles/human-base-meshes-a-new-free-asset-pack-by-blender ; https://developer.blender.org/docs/release_notes/3.6/asset_bundles/
- BlendSwap Hands Rigged (CC0) : https://blendswap.com/blend/22269
- fogleman/sdf (MIT) : https://github.com/fogleman/sdf ; bpy sur PyPI : https://pypi.org/project/bpy/ ; pygltflib : https://pypi.org/project/pygltflib/ ; manifold3d : https://pypi.org/project/manifold3d/
- Normes anatomiques citées (phalanges 40/23/17 mm, pouce 46/31/21 mm) : valeurs déjà utilisées dans CLAUDE.md (piste T), à confirmer dans le dossier anatomie.
