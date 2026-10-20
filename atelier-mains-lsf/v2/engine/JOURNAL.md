# Chantier M2 — LE MOTEUR 3D (engine.js, shaders.js) : journal

Tenu au fur et à mesure (tout sur disque). Contrat : PLAN.md « M2 → M3 ». Assets : v2/hand/hand_v2.glb + hand_v2.json (M1).

## 19 octobre 2026 — démarrage

Lu : PLAN.md, les trois journaux (M1, M3, M4), rendu.md (§ 3, 5, 6, 7 et demo_v2.py), mobilite.md (§ 1–6), outil.md
(§ 4, 8), CLAUDE.md, le moteur v1 (source/script.js : constrain, cmcPose, solve, penetration, grabAxes, PRESETS).

Décisions de départ (à revoir si la mesure les dément) :
- three.js r128 vendu dans `v2/engine/vendor/three.min.js` (PROVENANCE.txt) ; GLTFLoader pris dans `v2/hand/vendor/`.
- Skinning sur le CPU en quaternions duaux (comme dqApply v1, conseil M1), correctifs (morph targets) ajoutés AVANT,
  dans l'espace de liaison, poids clamp(θ/θref, 0, 1) ; normales transformées par la rotation du DQ mélangé.
- Convention de l'écartement `ab` : par rapport à l'AXE DU MAJEUR (3e rayon, +Y), comme la v1 (« 0 = parallèle au
  majeur », SPREAD) et comme les butées de mobilite.md § 5 reprises dans hand_v2.json (`abd`). Le GLB est lié en
  léger éventail (index +4°, annulaire −5,5°, auriculaire −14°) : le moteur tourne la P1 de (ab − éventail de
  liaison). Les poses du JSON (écrites dans le repère de liaison par M1) sont converties à la lecture (ab + éventail).
- `prono` > 0 = pronation de la main droite = rotation de −prono autour de +Y (pouce vers la caméra en vue paume).

## Premiers contrôles (19 octobre)

- Chargement (GLTFLoader.parse sur l'ArrayBuffer) : 26 610 sommets, 20 os ; centres des os du GLB = centres du JSON à
  6·10⁻⁵ cm près ; éventail de liaison mesuré sur le GLB : index +4,0°, majeur 0, annulaire −5,5°, auriculaire −14,0°
  (ce que M1 annonçait). WebGL2 dans Chromium swiftshader : l'identité de la G-pass est PLATE par triangle (`flat`).
- Parties par poids dominant (paume 6 298 sommets dont les palmures, pouce 2 825, index 4 513, majeur 4 293,
  annulaire 4 269, auriculaire 4 412) ; aucune arête ne relie directement deux doigts (0 couture à rendre à la paume).
- Correctifs : 8 morphs relus, 4 469 à 5 534 sommets déplacés chacun (accesseurs creux de M1 densifiés par GLTFLoader :
  le moteur ne garde que les sommets non nuls).
- **Skinning du moteur (JS, quaternions duaux + correctifs) contre celui de M1 (build_hand.py, numpy)**, deux poses
  (poing partiel + poignet 30/−10 + arc 0,7 ; hyperextension + poignet −40/15) : écart max 0,0018 mm et 0,0004 mm
  (`v2/tests/engine_skin_m1.py`). Le moteur pose la main exactement comme M1 l'a contrôlée. (Premier essai : 14 mm
  d'écart sur la 2e pose — c'était l'arc AUTOMATIQUE du moteur, 0,6 × 45/90 = 0,3, absent chez M1 ; à arc égal : 0.)
- Rayons des capsules mesurés sur la peau (centile 90, cm) : P1 index latéral 1,04 / palmaire 0,95 / dorsal 0,75 ;
  pulpe de l'index 0,84 / 0,75 / 0,63 ; pouce P1 1,15 / 1,04 / 0,85.
- Fumée (`engine_fumee.png`) : la main se rend, droite et gauche ; DÉFAUT vu : les rubans des plis absents sur la
  droite, présents sur la gauche → le ruban est une bande dont le sens dépend de la courbe, culling des faces :
  `side: DoubleSide`. Temps : 124 à 293 ms pour 420 × 520 (sur-échantillonné ×2), 517 ms au premier (compilation).

## Contacts : capsules réglées sur la peau (19 octobre)

Le solveur a besoin d'une pénétration rapide (il l'évalue des centaines de fois par geste) ; la vérité est la peau
(mesure de M1, `build_hand.penetration` : sommet sous la surface de l'autre partie, normales opposées). Comparaison
capsules / peau sur 8 poses (`v2/tests/engine_contacts.py`), en mm, pire paire :

| étape | index/majeur (O) | bout/paume (poing serré) | annulaire/auriculaire (repos) | thumb |
|---|---|---|---|---|
| rayon unique moyen | — | 7,3 / 3,0 | 2,5 / 1,6 | 11,6 / 8,0 |
| bout de capsule ramené d'un rayon (le « bout » de M1 est SUR la peau) | 3,3 / 3,1 | 1,3 / 3,0 | 2,5 / 1,6 | 10,2 / 8,0 |
| profil POLAIRE de section (16 secteurs, centile 90) | 3,1 / 3,1 | 1,3 / 3,0 | 1,4 / 1,6 | 10,6 / 8,0 |
| + deux profils le long de l'os (proximal / distal) | 3,3 / 3,1 | 1,3 / 3,0 | 1,6 / 1,6 | 10,6 / 8,0 |
| + marge paume 1,6 mm (la pulpe s'écrase) | 3,3 / 3,1 | **2,9 / 3,0** | **1,6 / 1,6** | 10,6 / 8,0 |

Entre doigts : écart ≤ 0,4 mm sur toutes les poses (index/majeur 2,6 / 2,2 ; 3,0 / 2,9 ; majeur/annulaire 2,6 / 2,3 ;
pince 1,9 / 1,7). Le pouce reste SURESTIMÉ par les capsules (il s'arrête un peu avant la peau : prudent). Seul cas non
vu : « B » à l'ancienne (annulaire +6, auriculaire +9) écrase 4,6 mm de chair au fond de la commissure palmaire
annulaire–auriculaire (coussinet de la base de P1, hors des capsules) ; invisible au rendu.
Coût : penetration() = 0,033 ms ; les 81 presets se résolvent en 177 ms au chargement.

## Solveur et presets (19 octobre)

- **Écartement en flexion autour de l'éventail neutre.** R2 (mobilite.md : la plage d'écartement se referme avec la
  flexion de la MCP, × max(0,1 ; 1 − 0,9·θ/90)) refermait d'abord vers 0, c'est-à-dire « parallèle au majeur » : poing
  fermé, l'auriculaire était tourné de 14° vers l'annulaire, le contact majeur–annulaire montait à 3,2 mm et l'annulaire
  restait bloqué à MCP 75°. La plage se referme maintenant autour de l'éventail de liaison du doigt (index +4°,
  annulaire −5,5°, auriculaire −14° : chaque doigt reste dans l'axe de son rayon, comme le poing réglé par M1). Les
  doigts repliés des presets (`PLI(k)`) portent cet éventail.
- **Budget par chaîne.** Chaque contact a son budget (v1 : « deux contacts sont deux contacts ») : une chaîne n'est jugée
  que sur les contacts qui la concernent. Mesuré : avec la pénétration globale, fermer l'auriculaire après les trois
  autres doigts butait à MCP 1,4° — l'arc automatique (piloté par sa MCP) déplace le 4e rayon et le contact
  majeur–annulaire, déjà au plafond, passait de 3,07 à 3,24 mm à mi-chemin.
- **Trois étapes dans solve** : (0) tout ensemble jusqu'au premier contact (quatre doigts qui se ferment se partagent la
  place — fermés un par un, l'index prenait tout et le majeur restait à 73°) ; (1) chaîne par chaîne, toutes ses
  articulations ensemble (fermer la MCP APRÈS l'IPP était impossible : bout déjà sur la paume) ; (2) articulation par
  articulation (v1), avec le glissement de la MCP ≤ 4° quand un bout posé bloque.
- `settle` (presets) s'assied à 2,6 mm (siège) au lieu de 1,5 : une configuration de référence va jusqu'au contact.
- Pouces posés réglés par `reach` (descente sur les angles du pouce et, pour les pinces, de l'index) puis recopiés
  dans les intentions : O, Pince, Pince ronde (F), Pince fermée, becs d'oiseau, becs de canard et d'oie fermés,
  Majeur pouce / H, D (écart pulpe–bouts 0,1 mm), poing serré (pouce en travers des P2 : écart 0,3 mm), V (2), Index (1).

## Rendu : réglages mesurés (19 octobre)

- **Seuil d'ombre** balayé sur « Repos » (part d'ombre de la peau, paume / dos) : 0,30 → 14,1 / 10,8 % ; 0,36 → 16,5 /
  13,8 ; 0,40 → 18,2 / 16,2 ; 0,44 → 20,1 / 19,3. Retenu **0,41 → 18,7 / 17,1 %** (cible 16–24, dessin 16–18).
- **Coque = silhouette seule.** La coque pleine cernait chaque doigt replié d'un trait de contour (les « boudins cernés »
  de la piste Z v1). Elle est maintenant jetée là où la G-pass voit de la peau : les recouvrements intérieurs passent
  par les arêtes au poids 0,7 (rendu.md § 4). Bonus : plus de griffures de coque dans les sillons.
- **Porte d'identité paume / doigt 0,35 → 1,0 × seuil** : à 0,35 la passe d'arêtes hachurait le fond des commissures
  (flanc du doigt contre la palmure : une dizaine d'échardes par commissure en mode débogage). Le pouce devant la paume
  et les doigts repliés devant la paume restent cernés (vérifié en gros plan : Quatre (4), poing).
- **Pas de trait intérieur à moins de r du fond** : la coque y trace la silhouette ; sinon un « écho » du contour
  (surface rasante) laissait ≈ 15 échardes par vue le long des flancs.
- **Coupe de l'avant-bras** à y = −2,0 cm (repère de liaison) : le bouchon oblique du GLB faisait une ellipse cernée au
  bas de chaque vue. Coupé net, le trait des flancs s'arrête ouvert ; par l'ouverture, l'intérieur (faces arrière) est
  peint dans l'ombre × 0,86 sans aucun trait (identité 8). Vue « de dessous » : l'intérieur des tubes des doigts reste
  visible par l'ouverture (vue de toute façon peu utile pour un signe).
- **Couche des traits nettoyée** : arêtes, bande d'ongle et rubans des plis rendus dans une cible à part (MAX des
  alphas) puis composés en ne gardant un pixel que s'il a ≥ 3 × plancher voisins de trait sur 25 (fenêtre 5 × 5 de la
  cible : 7,5 avec le sur-échantillonnage ×2 de render(), 3,75 dans la marionnette) : un trait réel en a ≈ 5 × le
  plancher, une miette ou le bout d'un filet nettement moins. (D'abord 8 fixe : dans la marionnette, sans
  sur-échantillonnage, les plis de la paume tombaient en tirets.)
- Bande d'ongle : seulement près de l'ongle (masque interpolé > 0,05–0,25), éteinte vue par la tranche (N·V < 0,12–0,3),
  largeur calculée en mm de peau par pixel AU SOMMET (comme `vAw` en v1) plutôt que par fwidth.

## Fin du chantier (19 octobre, soir) — corrections après les mesures

### Pénétration des presets sur la PEAU : 3,62 → 2,82 mm
Premier relevé complet (`tests/engine_presets.py`, peau posée mesurée par `build_hand.penetration` de M1) : 6 presets
sur 82 au-dessus de 3 mm — Lettre R 3,62 (pouce/annulaire), C 3,23 (index/majeur), Majeur pouce et H 3,14, Bec de canard
rond 3,07, Cornes 3,01. Deux causes mesurées :
- les capsules SOUS-estiment deux familles de contacts : le pouce contre un doigt (R : 2,6 mm de capsules pour 3,62 de
  peau) et deux doigts À DEMI fléchis côte à côte (C : 2,59 → 3,23). Entre deux doigts repliés c'est l'inverse (Cornes :
  3,65 de capsules pour 3,01 de peau) ;
- l'arc automatique, piloté par l'opposition du pouce, enfonce le contact majeur/annulaire quand `settle` place le
  pouce en dernier (budget par chaîne : le pouce n'est jugé que sur SES contacts) — Cornes finissait à 3,65 mm de
  capsules, au-dessus du plafond de 3,0.
Correction : `degager()` après `settle`, pour les presets seulement — plafond PAR FAMILLE (pouce/doigt 2,0 mm ; deux
doigts à MCP < 60° 2,0 ; bout sur la paume 2,6 ; doigts repliés 3,0), pas de 1° sur l'articulation du contact le plus en
excès qui le dégage le mieux, un pas refusé s'il enfonce un AUTRE contact au-delà de ce qu'il était ou de son plafond.
Essai écarté : un plafond unique de 2,0 mm — le dégagement écartait l'annulaire replié vers l'auriculaire (L, Index (1),
becs… : 4,99 mm sur la peau, invisibles aux capsules) et ouvrait le majeur du poing à MCP 72°.
Résultat : **82 presets, peau max 2,82 mm (Cône, index/majeur)**, capsules ≤ 2,97 ; R 2,36, C 2,13, Majeur pouce 2,03,
Bec rond 2,13, Cornes 2,21, Poing serré 2,17, O 2,44, Pince 1,39, V (2) 2,19. Planches `engine_presets_1..5.png`
(paume ¾ et dos ¾ de chaque preset, regardées : aucun changement de lecture des configurations).

### Marionnette : 816 → 117–128 ms par image de geste (rendu logiciel)
- Mesure corrigée d'abord : `chrono()` lisait un pixel APRÈS le rendu mais pas avant, il comptait donc aussi l'image
  complète mise en file par `poser()` juste avant (360 ms au lieu de 125, mesuré passe par passe). Il vide la file avant
  de lancer le chronomètre. (Les 816 ms du relevé précédent tombaient en plus pendant un calcul des presets en tâche de
  fond.)
- Profil par passe (442 × 520, swiftshader) avec le MSAA du canvas : G 50, coque 59, toon 120, rubans 6, arêtes 26 ms ;
  sans MSAA : toon 49, coque 22. Le coût suit les pixels. Pendant un geste : image rendue dans une cible réduite à
  **0,7 ×** (moitié des pixels), sans MSAA, puis agrandie sur le canvas (`RENDU.rapideK`, `dessinerGeste`) ; l'image
  complète (MSAA, couche des traits nettoyée) revient au relâchement.
- Relevé final (`engine_marionnette.py`, médiane sur 20) : **geste 117 à 128 ms** (min 86, max 150), **image complète
  252 à 287 ms**, en rendu LOGICIEL ; sur GPU compter 3 à 10 × moins (outil.md § 4.2), soit ≈ 15–40 ms par image de geste.
  Image de geste contre image complète : `engine_marionnette_geste.png` (plus douce, trait un peu crénelé, même lecture).
- Tous les gestes vérifiés sur la vraie page (`test.html`) : bout tiré (MCP 24 / IPP 28 / IPD 20), milieu (MCP + IPP),
  Maj (une articulation), clic droit (verrou), double clic (tendu), Alt (quatre doigts), pouce (vis sans fin respectée),
  paume (rotation), Échap (options.onFin), pénétration 0,00 mm après les gestes, 0 erreur JS.

### Bord de la manche (contour constant à toutes les vues : ±10,8 % → ±5,5 %)
Les vues « dos ¾ » montraient le bas du contour PLUS FIN (Pince 4,26 px pour 4,77 de médiane : −10,8 %). Mesure par
bande horizontale de l'image : 2,0 à 2,8 px dans la bande du bas, 4,0 à 4,5 partout ailleurs — c'est le bord de la
coupe de l'avant-bras, vu par son ouverture : la coque est jetée sous la coupe, il n'y restait qu'un filet (et une
petite pointe au milieu). Ajout d'une bande « bord de la manche » (shaders.js 3b) : les segments de l'anneau de coupe
(163, un par triangle traversé, interpolés sur la peau posée), extrudés de px vers l'EXTÉRIEUR de l'anneau à l'écran,
là où la G-pass ne voit pas de peau. Deux pièges vus en image : (1) extrudée le long de la normale de la peau, la bande
LONGEAIT le bord au lieu de le traverser (2 px au lieu de 4,5) — perpendiculaire au bord à l'écran, tournée à l'opposé du
centre de l'anneau ; (2) vue par la tranche (vue paume), l'anneau aplati donnait une frange en dents de scie — la bande
n'existe que si l'on voit DANS la manche (dz > 0,12, largeur amenée de 0 à 1 entre 0,12 et 0,35) ; vue de face, la
coupe reste ouverte comme avant.
Relevé final (`engine_planches.py`, 8 poses × 12 vues, 30 px/cm, contour attendu 4,56 px) : médianes 4,76 à 4,98 px,
**écart max à la médiane 0,9 % (Poing serré) à 5,5 % (Main ouverte, Pince)** — exigence ±10 %.

### Fragments noirs isolés aux articulations : 234 → 133 (sur 96 vues)
- `Pipeline.nettoyerTraits` (render() seulement) : la couche des traits est relue sur le processeur, une composante
  d'arête ou de bande d'ongle (les rubans des plis, marques voulues, restent) de moins de 20 px de l'image finale (× ss²)
  qui ne rejoint ni le fond (donc la silhouette) ni le bord de la tuile est retirée. 234 → 147. Coût mesuré : 0 à 50 ms
  sur ≈ 400 ms (dans le bruit de la mesure).
- Bande d'ongle sous le plancher : quand le plafond en mm (ongle vu de biais) la rendait plus fine que 1,25 px, elle se
  brisait en pointillé noir entre la frange claire et la tablette (vues de profil et en plongée) ; elle garde maintenant
  le plancher et s'éclaircit (alpha = largeur / plancher), comme les rubans. 147 → 133.
- Essais écartés, mesurés : porte N·V de la bande d'ongle plus haute (0,22–0,42) : 147 → 133 aussi, mais l'ongle vu de
  chant perdait son filet (leçon v1 : « la lamelle redevient un ongle ») ; masque de frange lissé sur le maillage puis
  seuillé net (pour effacer l'escalier du bord de la frange en gros plan ×3) : la frange disparaissait par endroits et
  la bande d'ongle remontait sur le bord libre en dents noires, 133 → 174 — retiré.
- Ce qui reste (133, dont 88 de 1 à 4 px ; par vue : plongée paume 41, profil radial 19, dessus 19, aucune vue « dos ¾
  radial ») : des bouts d'ARÊTES — un trait de contact entre deux doigts qui se touchent et qui clignote en tirets (dos
  plongée), un second filet parallèle au contour au bout d'un doigt vu en plongée, de petites fourches au contact du
  pouce (O, Index (1)) — et les coins du « U » d'ongle vus par le bout du doigt. Avec les plis : 1 149 marques, ce sont les
  rubans courts des plis (voulus). **L'exigence « 0 » n'est pas atteinte** ; historique du même relevé : 2 876 au
  premier rendu, 988, 230, 147, 133.

### Mesures finales (toutes regardées en image)
| mesure | valeur | exigence |
|---|---|---|
| skinning JS contre M1 (2 poses) | écart max 0,0018 / 0,0004 mm | identique |
| contour, 8 poses × 12 vues (30 px/cm) | médianes 4,76–4,98 px pour 4,56 attendus ; écart max 0,9–5,5 % | ±10 % |
| ombre au repos (paume / dos) | 18,8 / 17,1 % | 16–24 % |
| fragments noirs < 20 px aux articulations | 133 sur 96 vues (Repos 35, Main ouverte 9, B 14, Poing 7, Index 20, V 15, O 19, Pince 14) | 0 — non atteint |
| render() 470 × 660 (ss ×2), médiane sur 20 | 435 à 475 ms (logiciel) ; planches médiane 347–373 ms | mesuré |
| marionnette, image de geste / complète | 117–128 / 252–287 ms (logiciel, 442 × 520) | mesuré |
| pénétration des 82 presets, sur la peau | max 2,82 mm (capsules ≤ 2,97) | ≤ 3 mm |
| presets avec note « à valider par l'utilisateur » | 20 sur 82 | — |
| intégration planche (plate/index.html, bouchon remplacé) | gabarit A : 2 mains, 2 rendus ; D : 4 mains, 3 rendus ; marionnette en place ; 0 erreur | — |

### Photos de l'utilisateur, côte à côte au même angle (`engine_photos.png`)
Poing 2357 : pouce en travers des P2 de l'index et du majeur, quatre P2 en rangée — comme la photo ; le rendu montre un
peu plus de jour entre les doigts repliés (traits de contact entre chaque P2, la photo n'a que des ombres). V 2359 :
annulaire et auriculaire tenus par le pouce, même lecture. O 2367 : l'anneau pouce/index se lit, le jour est un peu plus
petit que sur la photo. Pince annulaire 2368 / 2369 : index et majeur tendus, anneau pouce–annulaire visible aux deux
angles. Quatre 2370 : pouce replié en travers de la paume, même lecture. Pouce levé 2374 : pouce dressé sur le poing, vu
de ¾ ; la manche ouverte se voit par son ouverture (bord désormais au poids du contour).

### Pour M3 (intégration dans plate.js)
- `#puppet` (ou l'hôte passé à `puppet`) doit couvrir le cadre de l'objet, e.w·zoom × e.h·zoom, sans marge ni bordure :
  la marionnette prend la taille de l'hôte ; un hôte sans taille propre reçoit 420 px de haut (options.hauteur /
  options.largeur). La barre d'outils est posée SOUS le cadre (top: 100 %) : prévoir la place ou un hôte qui ne coupe pas.
- plate.js appelle `puppet(host, e, onChange)` SANS 4e argument : la marionnette n'a donc ni bouton « Terminer » ni
  sortie au clavier à elle, et Entrée pendant la marionnette passe au raccourci de la planche (« Entrée sur une main =
  marionnette »), qui la RELANCE. À brancher par M3 : `puppet(host, e, onChange, {onFin: finMarionnette})` — Échap /
  Entrée sont alors pris en capture sur window et arrêtés là (la planche ne les voit plus). `onChange(pose, {orientation,
  dx, dy})` n'est appelé qu'au relâchement.
- plate.js passe `largeurTrait` 1,2 par défaut, le moteur 0,8 % de HL (≈ 1,5 mm sur la main réelle, v1) : à trancher.
- `render({w, h})` remplit w × h selon `bounds` (le paramètre `scale` du contrat est ignoré : l'échelle vient de w et h).
- `presets` compte maintenant 82 entrées (15 de la v1, alphabet A–Z, chiffres 0–10, formes de base) ; `presetsInfo[nom]`
  donne l'intention, la note « à valider » et la pénétration : plate.js affiche toutes les clés en boutons — une liste
  par famille serait plus lisible (voir test.html).
- `mirrorOrientation(q)` existe ; la main gauche est le miroir x → −x (normales déjà justes : pas de « nflip »).

### Ce qui reste
- Fragments noirs : 133 bouts d'arêtes et coins d'ongle sur 96 vues (voir plus haut) ; la piste est la stabilité de la
  passe d'arêtes au seuil (contact entre doigts qui clignote en tirets), pas un filtre de plus.
- Bord de la frange en ESCALIER en gros plan ×3 (masque par sommet, pas de maillage 0,6 mm) ; invisible à 30 px/cm.
- Tunnel du poing vu de profil (défaut 0 de la v1) : rebord légitime autour d'un vrai creux.
- Vue « de dessous » : l'intérieur des tubes des doigts se voit par l'ouverture de la manche.
- « B » à l'ancienne : 4,6 mm de chair écrasée au fond de la commissure annulaire–auriculaire (hors capsules, invisible).
- Les capsules du pouce surestiment la peau dans la plupart des poses (prudent) mais la sous-estiment pouce sur doigt
  replié (R) : couvert pour les presets par `degager`, pas pour un geste libre (plafond du solveur 3,0 mm de capsules).
- Temps : mesurés en rendu logiciel seulement ; à remesurer sur la machine de l'utilisateur.

## Correction après relecture adverse (19 octobre, nuit)

La relecture (scripts et images dans le brouillon `rev/`) a relevé 3 défauts bloquants, 6 importants, 5 mineurs. Chaque
correction ci-dessous porte sa mesure ; le relevé complet refait à la fin est en bas de cette section.

### B1. Grands rendus par tuiles (exports ×2, ×3, A4, A3) — CORRIGÉ
- Reproduit : V (2) dos ¾ à 2600 px, traînée noire à y ≈ 2313 px de x 800 à 1950 (la couture verticale des tuiles).
  Cause trouvée : PAS la bande « bord de la manche ». `nettoyerTraits` ne refaisait sa texture que si le NOMBRE de
  pixels changeait ; les tuiles 3997 × 1401 et 1401 × 3997 en ont autant, la seconde relisait la couche des traits de
  la première avec le mauvais pas de ligne. Texture refaite dès que la largeur ou la hauteur change.
- Marche de 1 à 2 px du contour à la couture : chaque tuile était recadrée PUIS réduite (×½), le filtre de réduction
  voyait le bord de la tuile. Marge et pas des tuiles en multiples de ss (chaque tuile tombe sur un pixel entier), la
  tuile est réduite AVEC sa marge puis découpée (clip) ; la marge couvre aussi le nettoyage des miettes (aMin / 2 px).
- Mesuré (`tests/engine_tuiles.py`) : à la vraie taille, rendu en 4 tuiles de 4096 contre une seule tuile de 8192
  (limite de swiftshader) : **0 pixel différent** sur Repos paume 2200 × 2600 et V (2) dos ¾ 2600 × 2600, 0 encre
  hors de la main ; gros plans des coutures (`engine_tuiles_coutures.png`) : contour continu. Tuiles forcées petites
  (520 px) : les écarts restants sont du bruit de rastérisation d'un sous-cadre (rangées de 1 px au bord net et
  horizontal de la coupe, arêtes au seuil), répartis sans lien avec les coutures (densité dans la bande des coutures
  / ailleurs 0,48 sur 39 vues : MOINS d'écarts sur les coutures qu'ailleurs ; chiffres dans le relevé final).

### B3. Vues « dessus » et « dessous » — CORRIGÉ
- **Dessous (poignet vers l'œil)** : on voyait par l'ouverture de la manche l'intérieur creux des doigts et de la paume
  (faces arrière peintes dans l'ombre). Un BOUCHON ferme maintenant la coupe : éventail (centre de l'anneau, extrémités
  des 163 segments de l'anneau de coupe, posés à chaque pose), identité 8 (aucune arête), peint dans le ton CLAIR de la
  peau. Contre l'avant-bras éclairé il se fond : en dos ¾ l'ellipse sombre « entrée de gant » a disparu, la coupe se lit
  comme la fin d'un dessin ; vue de dessous, l'avant-bras est un moignon plein. Il remplace les deux passes des faces
  arrière (la moitié du coût géométrique quand l'ouverture regardait l'œil).
- **Dessus (bouts vers l'œil)** : doubles anneaux noirs et échardes autour des bouts. Débogage en couleurs : c'étaient
  des ARÊTES de profondeur (rouge), pas la bande d'ongle — le doigt vu par le bout montre un anneau de flanc rasant (le
  doigt s'affine vers le bout) dont la pente dépasse tout seuil. Deux vetos dans la passe d'arêtes, pour une MÊME
  partie seulement : (1) continuité — la marche de profondeur est expliquée par les pentes que donnent les normales des
  deux pixels (n.z plafonné à 0,08) ; (2) enveloppe — le pixel proche tourne déjà dans la direction de l'échantillon et
  le pixel lointain est un flanc rasant tourné vers l'extérieur (n.z < 0,2) : la suite du même volume. Balayage du seuil
  de l'enveloppe : 0,35 cassait les traits des jointures du poing vu de face (crêtes à n.z 0,2–0,35), 0,12 laissait
  revenir le second anneau ; 0,2.
- Trait de contact entre deux doigts : les profondeurs sont maintenant comparées juste de part et d'autre de la
  FRONTIÈRE (3 pas le long de l'échantillon) et non à r px ; deux cylindres qui se touchent se voyaient chacun
  « derrière » l'autre à r px et les deux côtés traçaient (trait doublé, second trait en tirets). Décision continue
  (fondu de porteDoigts à 2 × porteDoigts) et compte d'échantillons en fondu de 1 à 3 au lieu d'un seuil sec :
  plus de bande hachurée le long des contacts (main plate en dos ¾, vérifié en gros plan ×6). porteDoigts 0,3 → 2,5 mm.
- Images : `engine_dessus_dessous.png` (relevé final).

### I1. Poing complet — CORRIGÉ
- Cause : `settle` assied une articulation bloquée au siège (2,6 mm de capsules) ; le contact index/majeur des P1 qui
  convergent (axes de MCP obliques) atteignait 2,67 mm de capsules dès MCP 78,8° du majeur. Mesuré sur la PEAU (M1) :
  majeur 78,8° → 2,17 mm ; 84° → 2,42 ; 90° → 3,00. Les capsules surestiment ce contact de 0,17 à 0,64 mm.
- Trois corrections du solveur : (1) profondeurs EFFECTIVES par famille (`margeFamille`) : deux doigts repliés côte à
  côte (MCP ≥ 70°) jugés 0,3 mm plus bas ; (2) REMPLISSAGE : les chaînes qui se ferment ensemble avancent de la même
  fraction de leur course jusqu'à ce que l'une bute (fermées une à une, la première prenait la place) ; (3) un doigt
  arrêté par le FLANC d'un voisin qui se ferme avec lui va jusqu'au budget du geste (3,0 mm) au lieu du siège (1,5 mm) :
  ce contact grandit continûment pendant toute la fermeture, c'est de la chair qui se range. Ajout : ENROULEMENT, la MCP
  qui bute par le bout laisse l'IPP / IPD s'ouvrir (≤ 50 / 40°) pour passer par-dessus l'obstacle.
- Mesuré (`m2c/r6.py`, copie du script de la relecture) : fermer les quatre doigts depuis la main ouverte 76/90/90/88
  → **90/90/90/90** ; depuis Repos, Dessin, L : 90/90/90/90 (auriculaire 88–90) ; presets Poing (A), Poing serré, S,
  Pouce levé : 90/78/90/88 → **90/88/90/88** ; Y : 83/90/83 → 90/88/90 ; Cornes 0/90/90/0.
- Pas changé, et c'est voulu : depuis Main plate (B) et Quatre (4), le pouce est COUCHÉ EN TRAVERS de la paume
  (B : av 24,5 / rap 35 ; 4 : 30 / 42 / 45 / 30) ; à MCP 90 le majeur entrerait de 4,7 mm (B) et 6,2 mm (4) dans le
  pouce. Les doigts s'arrêtent sur lui (74/55/90/86 et 90/72/58/83), comme une vraie main : CLAUDE.md, exigence 4,
  « le pouce reste libre tant qu'on ne le bouge pas » — la marionnette ne le pousse pas ; écarter le pouce d'abord (ou
  appliquer le preset) donne le poing entier (settle : 90/90/90/89).

### I5. Clé — CORRIGÉ
Prise latérale : pulpe du pouce pressée contre le flanc radial de la P2 de l'index courbé. Nouvelle cible
`flanc:index_p2` (milieu de la P2, + rayon latéral côté pouce) ; reach sur une grille de 5 courbures de l'index × 5
départs du pouce : meilleur index 70 / 75 / 35, pouce av 12,5, rap 13,5, MCP 21, IP 23,5, écart pulpe–flanc 0,2 mm
(l'ancien TH(5, 0, 0, 0) laissait le pouce à plus de 3 cm de l'index). Ajouté à la table REACH de engine_presets.py.

### I2. Tunnel du poing vu de profil — CORRIGÉ (rendu)
Le jour que la boucle P1 / P2 / P3 de l'index laisse dans le poing (≈ 1,9 × 1,25 cm à 40 px/cm ; M1 l'avait réduit
de 126 à 52 mm² par ses correctifs, pas fermé) était cerné d'un cadre noir (arête : la boucle passe devant le majeur)
et hérissé de trois épines. Nouvelle passe « creux » (shaders.js 4c) : un pixel de peau est au fond d'un creux FERMÉ si
dans au moins 7 directions sur 8 une surface plus proche de plus de 5 mm se trouve à moins de 1,2 cm ; ce fond est
peint dans l'ombre (× 0,86) et aucune arête ne le cerne. L'anneau d'un O (2 à 3 cm de jour) n'est pas fermé à cette
distance et reste dessiné (vérifié : O de profil inchangé). Les épines étaient des RUBANS de plis (débogage en vert) :
plis digito-palmaires (au pied des doigts, MCP à 90°) et plis IPP vus en rasant sur la paroi du tunnel. Un pli palmaire
de doigt plié à fond est au fond du repli : il s'efface de 70 à 90° à la MCP, de 80 à 100° à l'IPP / IPD ; un ruban
s'efface maintenant de N·V 0,12 à 0,3 (avant 0,02 à 0,15 : vu en rasant il s'étirait en épine). Reste une épine
(pli du thénar vu par la tranche), au lieu du cadre et de trois épines.

### I6. Dos de la main « gant de caoutchouc » — CORRIGÉ (relief porté par l'ombre)
La géométrie des correctifs de M1 fait bien sortir les têtes métacarpiennes (3,5 mm à 90°), mais une pente de ≈ 19°
ne fait pas basculer le toon à deux tons (N·L 0,68 pour un seuil de 0,41). Comme la piste W de la v1 (validée par
l'utilisateur), le dos porte maintenant deux reliefs qui ne vont jamais ensemble : SILLONS entre les têtes quand les MCP
se plient, VALLÉES entre les tendons extenseurs quand elles s'étendent. Ils passent par le SEUIL d'ombre (comme le
biais des ongles) : poids calculés une fois dans le repère de liaison (sommets du dos de la paume, distance à la ligne
médiane entre deux rayons, au droit des têtes ou le long des diaphyses), pilotés à chaque pose par les deux MCP voisines.
Réglé en image : sillon 0,45 (une ombre franche entre deux jointures du poing, vues dos et dos ¾) ; vallée balayée 0,22
(invisible), 0,35, 0,5 (rayures) → 0,35.

### B2. Fragments noirs et échardes — mesure ÉTENDUE, fragments à 0
- **Mesure** (`tests/engine_traits.py`, utilisée par engine_planches.py et engine_relecture.py) : sur l'image ENTIÈRE
  (plus seulement à 0,9 cm des articulations ; bouts des doigts compris), rubans des plis éteints, 13 vues (les 12 +
  « dessous ») :
  - fragments : composante d'encre (luminance < 95 hors tons d'ombre, ou < 60) de moins de 20 px contenant un pixel
    noir, en voisinage 8 ; l'ancienne mesure (voisinage 4 de `ndimage.label`, fenêtres des articulations) est gardée
    à côté pour comparaison ;
  - échardes rattachées : branche du squelette de l'encre NOIRE qui part d'un bout libre et rejoint, après 2 à 6 px
    visibles, un trait qui TRAVERSE le nœud (deux branches de plus de 8 px à plus de 120° l'une de l'autre), plus mince
    que lui (≤ 0,6 × son épaisseur). Calibrée en regardant chaque détection en gros plan ×4 : sur l'encre grise (< 95)
    elle comptait les barbules des jonctions en T et en Y (25 sur 45, vérifié) ; la pointe d'un V et le bout effilé
    d'un trait ne sont pas des échardes. Elle compte encore quelques coudes de trait (limite connue de la mesure).
- **Corrections à la source** (shaders.js 4a) : contact entre doigts jugé à la frontière (un seul trait, plus de second
  trait en tirets) ; décision continue au contact (plus de hachures) ; veto de continuité et d'enveloppe (plus d'anneaux
  doublés ni de poils autour des bouts vus de face) ; pas de coupure à r du fond (le trait d'un doigt vu derrière un
  autre rejoint le contour au lieu de s'interrompre en tirets ; essai écarté : un fondu de r à 2r, qui laissait des
  miettes en coin — 25 → 31) ; creux fermés sans cadre (4c) ; plis enfouis effacés.
- **Nettoyage final** (engine.js `nettoyerImage`, render() seulement) : à la résolution de SORTIE, avec la définition
  même de la mesure — encre = pixel opaque de luminance < 95 hors tons d'ombre de la peau (calculés depuis style.peau),
  ou < 60 ; voisinage 4 (le plus strict des deux comptes) ; seulement là où passe le masque d'encre (coque, bord de la
  manche, arêtes, bande d'ongle — jamais les rubans des plis ni l'aplat) ; une composante de moins de 20 px qui
  contient un pixel noir est repeinte, avec sa lisière, de la couleur de la peau voisine (pixel opaque hors masque le
  plus proche : l'aplat et l'ombre sont des tons unis). Deux passes, comme les deux comptes de la mesure (noir < 60,
  puis < 70 : les « filets gris ») ; chacune avec EXACTEMENT la connexité de son compte. Ce que cela retire, regardé en
  image (`m2c/t_retire.py`, 4 poses × 4 vues) : des points et tirets de 1 à 5 px, coins d'ongle vus par le bout, pixels
  d'escalier diagonaux ; rien de lisible. Essais écartés : (1) connexité par la couverture du masque (> 10 %) — un coin
  de « U » d'ongle relié à la bande par une lisière à 30 % restait « attaché », alors que sur l'aplat clair de l'ongle
  (luminance 195) il se lit isolé ; (2) une seule passe à « noir < 70 » — la lisière grise (ton 68, à 13 du ton d'ombre
  × 0,86) reliait des tirets en un trait de 26 px que la mesure voit en morceaux : main plate vue de bout, 4 fragments
  restaient ; (3) repeindre avec une couche « sans traits » composée exprès : une passe et une relecture de plus
  (75 ms à 470 × 660 en rendu logiciel) pour la même image.
- La couche des traits (nettoyerTraits, cible ×2) retire aussi désormais les composantes de moins de 20 px de l'image
  finale qui touchent la silhouette (bouts de trait de 2 à 6 px plantés dans le contour) : 22 → 17 échardes sur 4 poses
  × 13 vues, rien de lisible retiré.

### I3. Marionnette dans la planche — CORRIGÉ (M2 et M3)
- M2 : la barre (vues, poignet, inclinaison, pronation, arc) va dans `options.barreHote` si la planche en donne un,
  sinon sous le cadre ; `options.boutonFin: false` (la planche a son bouton) ; un hôte sans taille est signalé
  (console.warn) ; le pointeur est lu en coordonnées LOCALES (offsetX / offsetY : l'hôte peut être tourné ou
  retourné comme l'objet) ; le surlignage au survol suit les POIDS de peau (attribut interpolé) et non l'identité
  plate par triangle (bord lisse) ; la coque déborde d'un pixel sous la peau (plus de liseré clair d'un pixel entre le
  contour et la peau dans l'image complète de la marionnette, MSAA du canvas contre G-pass sans).
- M3 (plate.js, plate.css — retouches minimales, notées dans plate/JOURNAL.md) : #puppet sans marge ni bordure ni
  fond, overflow visible, posé par placeOverlays EXACTEMENT sur le cadre de l'objet (transformCSS, e.w·zoom × e.h·zoom) ;
  la main en marionnette n'est plus peinte par la planche dessous ; la barre de la marionnette s'insère dans la barre
  contextuelle (#ctx), visible en mode marionnette au-dessus de l'objet ; appel puppet(host, e, onChange, {onFin,
  barreHote, boutonFin:false}) — Échap / Entrée terminent.
- Mesuré (`tests/engine_integration_planche.py`) : cadre du canevas = cadre de l'objet à **0 px** près
  (128, 462, 227 × 267 px), 4 curseurs dans la barre visible, curseur pronation 0 → 40 appliqué à l'élément, geste du
  bout de l'index → pose changée, Échap → mode planche, 0 erreur JS. Image `engine_integration_marionnette_geste.png`.

### I4. Tests reproductibles depuis le dépôt — CORRIGÉ
`tests/glb.py` (lecteur glTF binaire numpy, accesseurs creux compris) est dans le dépôt ; engine_contacts.py,
engine_skin_m1.py et engine_presets.py l'importent de là. Photos de l'utilisateur : hors du dépôt (ce sont les siennes),
dossier donné par ATELIER_PHOTOS (défaut : le brouillon) ; engine_photos.py s'arrête proprement avec un message si
elles manquent.

### Mineurs
- **Couleur illisible** : `couleurValide` avant setStyle (#rgb, #rrggbb, rgb()/hsl(), noms CSS) ; {peau: 'pas une
  couleur'} → peau médiane (0, 161, 154), le vert INJS (engine_relecture.json).
- **Contrat de style** tranché dans PLAN.md : largeurTrait en % de HL (19 cm), défaut 0,8 ; ongle #96DCD6 ; plate.js
  aligné (il passait 1,2 et #d6f2ee) ; `scale` facultatif et ignoré (documenté).
- **IPD / IPP** : préférence souple du geste — IPD ramenée dans [0,6 ; 0,77] × IPP quand l'IPP dépasse 20°, sur le(s)
  doigt(s) bougé(s), jamais avec Maj ni IPD verrouillée. Mesuré : IPP 90 / IPD 0 → constrain 15,8 (bornes v1), geste
  54,0 (0,6 ×) ; Maj 15,8 (inchangé). constrain garde les bornes larges de la v1 (les presets et les valeurs saisies
  franchissent légitimement ce couplage).
- **Chiffres 6 à 10** : retirés des presets (CLAUDE.md : « au-delà de 5 … ne sont PAS devinées »), gardés comme
  propositions sourcées dans `AtelierHand.presetsAValider`, montrées à part dans test.html (« À valider ») ; la planche
  ne les propose plus en boutons. 82 → 77 presets.
- **Bord de la manche** aussi quand l'avant-bras FUIT (vues « dessus ») : le bout de l'avant-bras vu de derrière restait
  sans contour sous la paume.

### Relevé final après correction (toutes les mesures refaites d'un trait, images regardées)
Lancé par `m2c/final.sh` (brouillon) : engine_planches, engine_marionnette, engine_tuiles, engine_presets,
engine_relecture, engine_integration_planche, engine_photos, engine_fumee, engine_essai, engine_contacts,
engine_skin_m1 — tous en code 0, 0 erreur JS. « avant » = relevé de fin de chantier plus haut, ou ancien moteur
remesuré avec la NOUVELLE mesure quand la mesure a changé.

| mesure | avant | après | exigence |
|---|---|---|---|
| fragments noirs < 20 px, image entière, 8 poses × 13 vues (mesure étendue) | 109 (ancien moteur) | **0** | 0 |
| fragments < 20 px aux articulations (ancienne mesure, fenêtres) | 133 sur 96 vues | **0** (filets gris compris : 0) | 0 |
| échardes rattachées (2–6 px, ≤ 0,6 × le trait), 104 vues | 44 (ancien moteur) | 29 | — (voir « Ce qui reste ») |
| vues « dessus » / « dessous », 5 poses : fragments / échardes | anneaux doublés, gant creux | 0 / 7 sur 10 vues | — |
| tuiles : 4 × 4096 contre 1 × 8192, Repos paume 2200 × 2600 et V (2) dos ¾ 2600² | traînée + marche | **0 pixel différent** | identique |
| tuiles forcées à 520 px, 3 poses × 13 vues : densité d'écarts bande des coutures / ailleurs | — | 0,48 (1 740 px en tout, plus grande tache 161 px, hors couture) | ≤ 1 |
| encre hors de la main, 13 vues × (2400, 3000 px) | traînée | **0** | 0 |
| poing, presets (Poing (A), Poing serré, S, Pouce levé, A) : MCP | majeur 78° | 90/88/90/88 | poing complet |
| poing obtenu par `solve` depuis Main ouverte / Repos / Dessin / L | majeur 76–78° | 90/90/90/90 ; peau 3,00 mm (index/majeur), capsules 3,21 | ≤ 3 mm peau |
| Clé : écart pulpe du pouce – flanc de l'index (P2) | pouce loin | 0,024 cm | contact |
| pénétration sur la peau, presets | 82 presets, max 2,82 mm | 77 presets, max 2,96 mm | ≤ 3 mm |
| contour, 8 poses × 13 vues (30 px/cm) | écart max 0,9–5,5 % | médianes 4,74–4,95 px, écart max 1,4–6,7 % | ±10 % |
| ombre au repos (paume / dos) | 18,8 / 17,1 % | 18,7 / 17,2 % | 16–24 % |
| couleur illisible `{peau:'pas une couleur'}` → peau médiane | blanc | (0, 161, 154) | vert INJS |
| IPP 90 / IPD 0 : constrain / geste / Maj | 15,8 / 15,8 / 15,8 | 15,8 / 54,0 / 15,8 | couplage souple |
| marionnette dans la planche : cadre du canevas – cadre de l'objet | décalé, barre invisible | 0 px ; barre visible, 4 curseurs ; Échap → planche | — |
| skinning JS contre M1 (2 poses) | 0,0018 / 0,0004 mm | 0,0018 / 0,0004 mm | identique |
| render() 470 × 660 (ss ×2), médiane sur 20 | 435–475 ms | 615 ms | mesuré (logiciel) |
| planches, médiane | 347–373 ms | 464 ms | mesuré (logiciel) |
| marionnette, image de geste / complète (442 × 520) | 117–128 / 252–287 ms | 90 / 234 ms | ≤ 200 ms (geste) |

Images regardées pour ce relevé : `tests/out/engine_relecture_1_tuiles.png` (2600 px en 4 tuiles, bas de l'image
propre), `engine_tuiles_coutures.png` (coutures ×3 : contour continu), `engine_relecture_2_dessus_dessous.png`
(dessus : un seul trait autour des bouts ; dessous : le bouchon ferme l'avant-bras, plus de gant creux),
`engine_relecture_3_poing.png`, `engine_relecture_4_tunnel.png` (creux peint dans l'ombre, sans cadre),
`engine_relecture_5_dos.png`, `engine_relecture_6_cle.png`, `engine_relecture_7_styles.png`,
`engine_relecture_avant_apres.png`, `engine_defauts_1..4.png`, `engine_planche_ensemble.png`,
`engine_presets_1..4.png`, `engine_integration_marionnette_geste.png`, `engine_photos.png`.

### Ce qui reste (après correction)
- **29 échardes** sur 104 vues (44 avant). Regardées en gros plan : des coudes de trait que la mesure compte encore
  (limite connue), et quelques barbules au bout d'un pli sur le bord (Pince 10, Poing serré 6). Rien de détaché :
  les fragments isolés sont à 0.
- **Tunnel du poing de profil** : le creux est peint dans l'ombre et le cadre a disparu ; reste l'arête du pli thénar
  qui pointe dans l'ouverture (un trait court, visible au gros plan de `engine_relecture_4_tunnel.png`).
- **Creux fermés** calculés à demi-résolution : leur bord peut se lire en marches de 2 px en gros plan (ex. Pince,
  paume ¾) ; invisible à 30 px/cm.
- **Coût du rendu** : +30 % sur render() (615 ms contre 435–475) — passe des creux, bouchon, nettoyage final. Tous
  les temps sont en rendu LOGICIEL (swiftshader) ; à remesurer sur la machine de l'utilisateur.
- **Poing par geste** depuis « Main plate (B) » ou « Quatre (4) » : le solveur s'arrête sur le pouce couché en travers
  de la paume (74/55/90/86 et 90/72/58/83). C'est un vrai obstacle : forcer le majeur à 90° le ferait entrer de 4,7 et
  6,2 mm dans le pouce. Il faut d'abord dégager le pouce (comme une vraie main).
- Poing par geste depuis la main ouverte : 3,00 mm de peau au pire contact (index/majeur ; 3,21 en capsules, qui
  surestiment ce contact) — à la limite ; les presets restent ≤ 2,96 mm.
- **Faux positif de la mesure sur la peau** (build_hand.penetration, M1), relevé en vérifiant ce poing : elle annonce
  5,56 mm annulaire/auriculaire. Mesuré : UN seul sommet (12108, flanc de l'auriculaire), à 7,74 mm de la peau de
  l'annulaire, juste sous la fenêtre de 8 mm de la mesure, jugé « dedans » par le signe du triangle le plus proche ;
  la valeur saute de 0 à 5,51 mm entre MCP de l'auriculaire 89,0 et 89,5° (le bout bouge de 0,1 mm : impossible pour
  un vrai contact). Test de parité (rayons dans 6 directions contre la peau fermée, `m2c/t_parite.py`) : les points
  pris de 0,2 à 4,5 mm au-dessus de ce sommet sont HORS du volume dans les 6 directions (et un point pris 0,3 mm
  dessous est dedans dans les 6 : le test marche). Contact réel annulaire/auriculaire : nul. Mesure de M1 laissée
  telle quelle (les 77 presets n'en sont pas touchés : max 2,96 mm, paire majeur/annulaire ou index/majeur).
- Bord de la frange d'ongle en escalier au gros plan ×3 (masque par sommet) ; invisible à 30 px/cm.
- Chiffres 6 à 10 : propositions dans `presetsAValider`, à valider par l'utilisateur avant d'en faire des presets.

## 20 octobre 2026 — LE TRAIT DE CONTACT ENTRE DEUX DOIGTS (grief : « des doigts qui se fondent dans la main »)

Grief de l'utilisateur, capture de la v2 publiée (« L » vu de dos) : *« La main manque de précision. Il y a des doigts
qui se fondent dans la main, tu ne vois même plus les traits de chaque doigt. On a perdu beaucoup en précision. »*
Rendus de contrôle (L, V (2), Index (1), Poing serré, Main ouverte (5), Quatre (4) × paume / dos / profil) : vus de DOS,
les trois doigts repliés de L, d'Index (1) et de V (2) n'ont aucun trait entre eux — un gant. En v1, un trait de contact
séparait toujours deux doigts différents (passe identité, seuil 0,02 entre deux doigts).

### Diagnostic (mesuré, pas supposé)
- **Ce n'était pas d'abord la porte de profondeur.** Passe identité lue sur la G-pass (`K/diag_id.py`, brouillon) : vu de
  dos ou de dos ¾, TOUT ce qu'on voit d'un doigt replié — tête du métacarpien, palmure dorsale, base de la P1 — porte
  l'identité PAUME (les poids de peau y sont dominés par mc2–mc5 ; seuls quelques pixels de P1 dépassent au sommet des
  bosses). Aucune frontière doigt / doigt n'existait donc là, quel que soit le seuil. En v1 il n'y avait pas d'os
  métacarpien : la peau de la jointure appartenait à la P1.
- Fenêtre de mesure entre deux jointures voisines (disque de 0,4 × l'écart des deux MCP, remonté de 0,45 cm au-dessus de
  leur milieu, hors de la bande du contour ; `tests/engine_contact.py`) : **0 pixel noir** à 30 px/cm dans les 16 vallées
  de L, Index (1), V (2) et Poing serré vues de dos et de dos ¾ (1 et 14 sur deux d'entre elles : lisière de l'encoche) ;
  à ×3, 0 en vue de dos, 22 à 72 en dos ¾ (bouts de lisière, épaisseur ≈ 3 px au lieu de 9,6).
- Là où deux doigts différents se touchaient vraiment (B, doigts repliés vus de la paume), l'ancienne règle faisait
  tracer UN côté choisi par la profondeur juste de part et d'autre de la frontière (porte 2,5 mm) : le long d'un contact
  dont l'écart frôlait la porte, le trait sautait d'un côté à l'autre (B paume ×3 : contact majeur–annulaire hachuré et
  cassé ; Pince dos ¾ : cinq échardes sur un seul contact).

### Ce qui a été fait
1. **Jointures à l'identité de leur doigt** (engine.js decoder « JOINTURES », shaders.js G-pass). Chaque sommet reçoit au
   chargement, dans le repère de liaison, une coordonnée latérale CONTINUE entre les rayons (u = 0 sur l'axe de l'index …
   3 sur celui de l'auriculaire ; k + ½ = ligne médiane entre deux rayons), sa position le long du rayon (t, 1 = centre
   de la MCP) et un poids « dos ». Le nuanceur donne au fragment de peau dorsale (paume, et base des P1 à t < 1,35)
   l'identité du doigt k = arrondi(u) au-delà d'un seuil en t piloté par la flexion de la MCP (30 → 75°) — du doigt OU
   d'un voisin (la vallée existe dès qu'une des deux têtes sort : sans cela, dans sa capture de « L », rien ne séparait
   la jointure du majeur replié de la base de l'index tendu). La frontière entre deux jointures est l'isoligne u = k + ½
   d'un champ lisse : le fond de la vallée, sans l'escalier des triangles. Main à plat (MCP < 30°) : rien ne change.
   Mesuré au repos : 1 637 des 1 659 sommets dorsaux des P1 sont à |u − k| < ½ de leur rayon (les 22 autres au bord
   cubital de l'auriculaire) — la frontière ne coupe aucune P1.
   Pièges rencontrés en le réglant, chacun vu en image :
   - coordonnée écrite pour la paume seulement : les zéros des sommets « doigt » voisins, interpolés dans les triangles
     mixtes, perçaient la jointure de trous de paume (tirets : Y de profil, O en dos ¾) → calculée pour tous les sommets ;
   - frontière P1 (maillage) / jointure voisine en escalier (dents de 2 à 6 px à ×3) → la base dorsale des P1 suit
     l'isoligne elle aussi ;
   - palmure au fond de la commissure (n.z −0,2 à +0,2, 189 sommets) restée « paume » : blanc de 4 à 6 px (×3) entre le
     trait et l'encoche du contour → la palmure compte comme dos jusqu'à n.z 0,2 ;
   - la jointure est la même peau continue que la paume voisine : le veto de « continuité » de la marche de profondeur
     (réservé à une même identité) et la porte paume / doigt la hachuraient en rasant → étendus aux pixels de jointure,
     marqués dans le reste de l'alpha d'identité (≥ 0,1 / 8 : le décodage floor(a·8 + ½) rend la même identité) ;
   - fin du trait : coupée carrée, puis fendue en deux pointes ou hérissée de dents (essais de pente 1,5 / 0,6 / 0,3 à
     ×9) → l'alpha d'identité porte aussi un « effilement » sur les 0,06 derniers de t, et l'anneau du contact s'y
     resserre jusqu'à ¼ : une pointe de plume (`K/tip_eff.png`).
2. **Trait de contact CENTRÉ** entre deux doigts différents, pouce compris (shaders.js 4a) : chaque côté compte, sur un
   anneau de rContact = ½ r (12 directions — 24 ne changent rien de visible, comparé à ×9), les échantillons d'un AUTRE
   doigt, et trace sa moitié. Les deux moitiés sont symétriques par construction : le trait est continu, d'épaisseur
   constante, et sa place ne dépend plus de la profondeur ni de l'ordre des identités. Garde-fous, tous vus en image :
   - anti-lamelle : l'autre doigt doit être épais (pas moi à 2 × rC) et je ne suis pas moi-même une lamelle (à l'opposé,
     pas ce même autre doigt) ;
   - occlusion en FONDU : un doigt nettement devant l'autre (écart de profondeur 0,2 → 0,6 cm) trace son bord d'un seul
     côté, sans le test symétrique de la marche (comme l'ancienne règle « doigt sur doigt ») ; l'autre moitié s'efface.
     Seuil sec à 0,6 : trois échardes sur un contact de B vu en plongée (écart 4 à 8 mm) ; sans occlusion du tout : le
     bord de l'annulaire devant l'auriculaire (Pince de profil, bande plus étroite que l'anneau) se cassait en tirets ;
   - jour étroit : un échantillon tombé dans 1 à 2 px de fond entre deux doigts collés compte si l'autre doigt est juste
     au-delà (B dos ¾ : le trait se pinçait à 2,1 px pour 3,2 à la transition jour / contact ; 2,9 après) ;
   - essayé et retiré : atténuer le trait près de la paume (pour la fin des vallées) — inutile depuis l'effilement, et il
     coupait le contact de Pince de profil au voisinage des dents de paume du maillage.
   La porte paume / doigt (racine des doigts tendus) est INCHANGÉE (1,0 × seuil).

### Relevé (main figée : la même copie de hand_v2.glb pour l'avant et l'après, l'autre chantier la remplaçait en cours)
| mesure | avant | après |
|---|---|---|
| vallées entre jointures, 30 px/cm (L, Index (1), V (2), Poing serré ; dos, dos ¾) : pixels noirs | 0 (1 et 14 de lisière) | 61 à 145 par vallée |
| épaisseur de ce trait, 30 / 90 px/cm (attendu 3,19 / 9,58) | — | 2,7–3,6 / 7,4–10,0 px |
| contacts de B (dos, dos ¾, paume), 30 px/cm : épaisseur | 2,3–4,1 px | 2,2–4,1 px |
| 12 presets × 4 vues (paume, dos, profil, dos ¾), 30 px/cm : fragments isolés / échardes | 0 / 18 | 0 / 14 |
| contour médian, 12 × 4 vues | 4,83 px | 4,81 px |
| engine_planches (8 poses × 13 vues) : fragments / échardes | 0 / 31 | 0 / 44 |
| engine_planches : contour médian par pose | 4,73–4,92 px | 4,73–4,92 px (écarts ≤ 0,03) |
| render() 470 × 660, médiane sur 20 (logiciel, deux tours alternés) | 774–790 / 882–957 ms | 816–861 / 890–967 ms (+1 à +11 %) |
| erreurs JS | 0 | 0 |

Relevé final des tests du dépôt, moteur final, sur la main livrée ensuite par l'autre chantier (hand_v2.glb a8077…) :
`engine_planches.py` fragments 0, échardes 38 sur 104 vues, contour médian 4,74 à 4,90 px par pose (écart max 6,9 %,
exigence ± 10 %), ombre au repos 18,4 / 16,7 %, 0 erreur JS ; `engine_fumee.py` code 0 ; `engine_tuiles.py` (fait en
cours de chantier) 0 encre hors de la main ; `engine_contact.py` (nouveau) : vallées 65 à 176 pixels noirs à 30 px/cm,
épaisseur 2,5 à 3,9 px, 0 erreur JS, planche `tests/out/engine_contact_avant_apres.png`.

Les échardes de plus d'engine_planches (31 → 44, toutes rattachées, 2 à 5 px) sont pour l'essentiel des barbules sur des
traits de contact qui N'EXISTAIENT PAS avant : poing et index vus en plongée ou par le bout (avant : aucun trait entre
les P2 repliées ; après : un trait continu, avec une ou deux barbules), plus de petits « T » là où deux doigts ne se
touchent que sur 2 à 4 px (V (2) vu du dessus). En face : Pince dos ¾ 5 → 1, B paume / profil 1 → 0, Poing serré et
Index (1) de face 1 → 0.

Images regardées : `tests/out/engine_contact_avant_apres.png` (sa capture de « L » : trois traits là où il n'y en avait
aucun ; poing de dos : quatre jointures séparées par trois traits qui s'effilent ; dos ¾ : le trait suit le recouvrement
des têtes ; B paume ×3 : contact continu au lieu d'hachuré ; Pince de profil ×3), les planches 12 × 4 avant / après
(brouillon `K/vue48_0.png`, `K/vue48_1.png`), les gros plans de chaque écharde nouvelle (`K/ech4_crops.png`,
`K/ech5.png`, `K/ech6.png`) et les débogages identité / arêtes (`K/dbg*.png`).

### Ce qui reste
- Barbules de 2 à 5 px sur certains des nouveaux traits de contact vus en plongée ou par le bout (poing, index) et petits
  « T » de contact très court (V (2) vu du dessus) : 44 échardes sur 104 vues contre 31.
- Au sommet des vallées, là où la frontière rejoint le contour au flanc de l'encoche, 2 à 3 dents de < 1 px à 30 px/cm
  (visibles à ×5).
- Les doigts tendus mais écartés (Quatre (4), Main ouverte (5)) n'ont pas de contact : rien à tracer ; les hachures du
  profil de la main ouverte au pied des doigts (lamelles d'identité vues par la tranche) sont antérieures et inchangées.
- (Vérifié) main gauche : mêmes traits en miroir — poing de dos, 2 pixels différents (> 60) entre D et G retournée sur
  400 × 520 ; L de dos, 228, tous dans l'ombre (lumière fixe dans le repère caméra, voulu) ; `K/gauche.png`.
