# Chantier M5 — intégration et page finale : journal

Tenu au fur et à mesure (tout sur disque). Contrat : v2/PLAN.md. Page : `python3 v2/build.py` → `dist/atelier-v2.html`
(artifact, sans doctype) et `dist/atelier-v2.local.html` (page complète). Tests : `v2/tests/integration_*.py`, lancés par
`python3 <scratchpad>/run_rendu.py v2/tests/integration_<nom>.py` sur la page CONSTRUITE (file://, rendu logiciel).

## 19 octobre 2026 — démarrage
Lu : PLAN.md, les journaux M1 (hand), M2 (engine), M3 (plate), M4 (personnage), CLAUDE.md (v1, « Publication »),
outil.md § 4 et § 7, personnage.md § 4.5 (« expression réglable par étape clé »).

### 1. v2/build.py
- Un fichier : plate.css, fonts.js, three.min.js r128 et GLTFLoader.js (vendus, sha256 dans PROVENANCE.txt), shaders.js,
  `window.ATELIER_HAND_ASSETS = {glb: base64, json}` (engine.js l'initialise au chargement — prévu par M2), engine.js,
  personnage.js, puis le corps de plate/index.html et plate.js. Le bouchon stub_hand.js n'est PAS embarqué.
- Contrôles du script : `node --check` sur les 8 scripts, refus de « </script » et « <!-- » dans le code embarqué,
  aucune balise `src=` / `href=` externe restante, taille < 12 Mo.
- Mesuré : **5,10 Mo** (5 347 301 octets ; GLB 3 066 104 octets → 4,09 Mo en base64), syntaxe OK, page prête
  (`AtelierHand.ready`) en **1,0 à 1,1 s** après le chargement (rendu logiciel), 77 presets, personnage chargé, 0 erreur JS.
- Fumée (gabarit A, deux vraies mains + référent) regardée : main D à gauche de l'image, pouce vers le milieu (vue paume
  = pouce à droite pour une droite, comme paume.jpg), G en miroir.

### 2. Cache des mains avec le vrai coût de rendu (outil.md § 4.4)
Mesuré AVANT toute retouche (`tests/integration_cache.py`, dpr 2, rendu logiciel → `out/integration_cache_avant.json`) :
UN rendu d'écran coûte **2 059 ms** (main de gabarit D à dpr 2 : 1 418 × 1 670 px, sur-échantillonnée ×2 dans le
moteur) ; gabarit D : plus longue image 1 200 ms ; **après un zoom à la molette : 3 983 ms de gel** ; redimensionner au
coin (×1,6) : 0 rendu pendant le geste (règle ×1,5 + une main par image), 1 après ; déplacer : 0 rendu.
Retouches de plate.js (rendCache / rendSales / trouveCache) :
- estimation AVANT de rendre : ms par mégapixel (w·h·ss²), moyenne glissante, départ pessimiste 400 ;
- un rendu prévu > 50 ms (RENDU_LENT, outil.md § 4.4) ne se fait jamais pendant un geste, et un seul par image au repos ;
- une main qui n'a encore rien à montrer reçoit d'abord un APERÇU (taille réduite pour ≤ 50 ms prévus, ss 1), l'image
  juste suit à l'image suivante et remplace l'aperçu ;
- à l'écran, dpr ≥ 1,75 : rendu sans sur-échantillonnage du moteur (ss 1). Mesuré sur V (2) 600 × 840 : 330 ms contre
  870 (÷ 2,6) ; gros plan ×2 regardé : crénelage du contour à peine plus marqué, invisible à dpr 2. L'export garde ss 2.
Après : gel après le zoom **3 983 → 1 000 à 1 133 ms** (deux relevés) ; gabarit D 1 200 → 800 ms (dont l'aperçu de la 1re main) ; coin et
déplacement inchangés (0 rendu pendant), 0 erreur JS. Le rendu d'UNE main reste un bloc synchrone (WebGL sur le fil
principal) : sur GPU, compter 3 à 10 × moins (outil.md § 4.2), soit ≈ 110 à 380 ms une fois le geste fini.

### 3. Latéralité, orientation, miroir 3D (`tests/integration_lateralite.py`, page construite, vrai moteur)
- Main D, orientation identité (vue paume), « L » : pouce à DROITE (portée de l'encre depuis le milieu du poignet : 365 px
  à droite contre 139 à gauche) — main droite comme paume.jpg, GLB sans miroir. G : à gauche (139 / 366). D tournée de
  180° autour de Y (dos) : à gauche (139 / 366).
- Miroir 3D : silhouette de G = silhouette de D retournée, IoU **1,0000** (paume) et **1,0000** (dos ¾ avec l'orientation
  réfléchie [x, −y, −z, w]). Lumière fixe dans le repère caméra : sur l'index tendu, **98,5 %** des pixels d'ombre sont à
  droite de l'axe du doigt POUR LES DEUX mains (un miroir d'image l'aurait mis à gauche sur la G).
  (Première mesure fausse, notée : « ombre à droite du centre de la main » donnait 26 / 85 % — l'ombre des doigts repliés
  de L, d'un seul côté, dominait ; la mesure sur un doigt seul est la bonne.)
- Planche : la main D posée en dos ¾ = le rendu direct du moteur (IoU 1,0000). « Convertir en main gauche » : côté G,
  orientation réfléchie, flipH faux, nom « Main G », silhouette = D retournée (IoU 1,0000). « Miroir ⇄ » pose flipH
  (miroir d'image, l'ombre change de côté : c'est le rôle documenté de ce bouton). 0 erreur JS.

### 4. Reprise de la v1 (`tests/integration_v1.py`, `out/integration_v1.png`, `out/integration_v1.json`)
- **Vue caméra de la v1.** La v1 faisait tourner la CAMÉRA autour de la main (`vue: {pos, cible}` dans le JSON v8) ; la
  v2 garde une caméra fixe de face. `convertitV1` ignorait la vue : une configuration enregistrée vue « signeur » se
  rouvrait de face. Maintenant q2 = Qcam⁻¹ · q1 (Qcam = lookAt(pos → cible), haut +Y) ; avec deux mains, le côté à
  l'écran suit la position de chaque main vue par cette caméra. Même repère de main dans les deux versions (doigts +Y,
  paume +Z, pouce +X pour la droite, gauche = miroir [x, −y, −z, w]).
- Poses v1 converties par le moteur (`AtelierHand.depuisV1`, repli sur l'ancienne lecture si absent).
- Mesuré sur 4 configurations ENREGISTRÉES PAR LA V1 (dist/atelier-mains-lsf.local.html, `snapshot()`), rouvertes en v2,
  IoU des silhouettes (70 % du haut, avant-bras exclu) contre la capture v1 du même angle / contre la v2 retournée :
  V (2) face 0,734 / 0,573 ; V (2) signeur 0,740 / 0,573 ; V (2) dos ¾ 0,811 / 0,481 ; Poing serré ¾ 0,862 / 0,653.
  Regardé : même angle, même côté de pouce dans les quatre cas (la v1 est la main dessinée, la v2 la main 3D : les
  silhouettes ne peuvent pas coïncider).
- JSON v6 (gauche, pose fixe) → 1 main G ; v7 (mouvement) → 1 main D à 2 étapes ; v8 deux mains, 3 étapes, référent,
  fond → personnage + 2 mains à 3 étapes, flèches par intervalle reprises (« arc » → « courbe », zigzag), fond #fff8e0.
- **Bibliothèque db** : la collection « configurations » de la v1 (même artifact republié = même base) est listée en
  lecture seule (« Configurations de la v1 », onglet Projet) ; « Ouvrir » la convertit en planche, « Enregistrer » écrit
  dans « projets ». Fausse capability (window.claude.use) : 2 lignes v1 affichées, ouverture → 1 main, nom repris ;
  écritures : 1 `add` dans « projets », **0 dans « configurations »**.
- **Capability downloads** : export PNG → `downloads.save({filename: 'planche.png', data: Blob image/png 73 717 o})`,
  projet → `'V vu de dos.atelier.json'` (application/json). API conforme aux définitions du contrat 0.2.76 (db.d.ts,
  downloads.d.ts relus). Hors claude.ai, la page reste sur ses replis (boîte d'image, téléchargement) — inchangé.

### 5. Référent : une expression PAR ÉTAPE (gabarit F)
personnage.md § 4.5 : « l'expression doit être réglable par étape clé, pas globale : en LSF elle change en cours de
signe ». Le personnage de la v2 est un objet de la planche ; une étape = une case. Nouveau gabarit **F · Étapes avec
référent** : bandeau du mot, 3 cases, dans chacune un référent (son expression se règle dans Propriétés), sa main D
posée à l'ancre des mains (+0,3 HL sous le creux du cou, 0,45 HL vers la gauche de l'image = la droite du signeur, main de
1,6 HL comme au gabarit A), flèches entre les cases. 3 cases et pas 4 : à 4, le buste tombait sous 160 px à l'écran
(repli en style B, personnage.md § 4.6). Regardé (`m5/fumee.png` du brouillon) ; chiffré dans le parcours complet.

### 6. Configurations rangées par famille (panneau Propriétés d'une main)
Le moteur donne 77 configurations ; plate.js les affichait en UNE liste de 77 boutons (le journal M2 le signalait). Rangées
comme dans engine/test.html : « Atelier v1 » (les 15, ouverte), « Alphabet », « Chiffres », « Formes de base » (repliées),
la note « à valider » du moteur en infobulle, `data-preset` = nom complet (tests). Chiffres 6–10 toujours hors planche.

### 7. Parcours complet (`tests/integration_parcours.py`, page construite, vrais gestes) — 20 contrôles verts, 0 erreur JS
Captures `out/integration_parcours_01..05.png`, planche `out/integration_parcours_planche.png` (regardée), export
`out/integration_parcours_export_x2.png` (regardé en gros plan : deux vraies mains, référent, fond photo, trait net).
| étape | mesure | temps (logiciel) |
|---|---|---|
| ouvrir la page | AtelierHand.ready | 1,04 s |
| outil Main D + clic | 1 main, rendue | 1,26 s |
| bouton « V (2) » | annulaire 90°, index tendu | 0,53 s |
| marionnette : tirer le bout de l'index (10 pas) | MCP 0 → 26°, IPP 0 → 31° ; plus longue image 317 ms (p95 67) | 2,42 s |
| Ctrl+D, « → main gauche », Maj+H | copie G, pose gardée, flipH | — |
| gabarit A, « cent », presets Index (1) / O | 5 objets (2 textes, référent, 2 mains) | 0,89 s |
| définition tapée, « cent » surligné | surlignage [21, 25] = « cent » | — |
| image collée (Ctrl+V d'un fichier) → fond | fond image, 0 objet image | — |
| export ×2 | 3 840 × 2 160, 513 Ko, JSON v9 de 5 objets dans le chunk iTXt | 1,59 s |
| export ×1 transparent | coins alpha 0, 1 032 020 px opaques | 0,69 s |
| projet .json (téléchargement) | « cent.atelier.json », 34 Ko, 5 objets, fond image + 1 asset | — |
| rechargement + Ouvrir… le fichier | identique (types, positions, poses, textes) | 1,34 s + 0,46 s |
| Suppr puis Ctrl+Z | 5 → 4 → 5 | — |
Non-régression (plate/index.html avec le bouchon, après les retouches de plate.js) : plate_scenario, plate_projet,
plate_edition, plate_correctifs (34/34) tous verts, 0 erreur ; engine_integration_planche : cadre 0 px, A 2 mains, D 4.

### 8. Planche de livraison (`tests/integration_livraison.py` → `tests/out/livraison_v2.png`, 2 400 × 3 566) — regardée
1. Gabarit A « cent » exporté ×1 par la page construite : bannière, définition surlignée, référent, main droite
   « Index (1) » et main gauche « O » — les deux mains sont du vrai moteur, posées sur le buste à l'ancre des mains.
2. « V (2) » enregistrée par la v1 et rouverte en v2 : face et dos ¾ au même angle (même lecture, pouce sur l'annulaire
   replié ; v2 : volume anatomique, ongles clairs, pas de texture peinte).
3. Poing serré v1 / v2 de ¾ (pouce en travers des P2 dans les deux) ; pince v2.
4. Ongles en gros plan (Main plate (B), dos, rendu 1 800 px) : plaques claires, frange plus claire, repli de peau, aucun
   ongle déformé. Le contour y est épais (0,8 % de HL = 14 px à cette taille) : c'est le trait de la planche, constant
   en proportion de la main.
5. Main droite et main gauche côte à côte (paume « Main ouverte (5) », dos ¾ « L ») : miroirs 3D exacts ; même lumière,
   donc l'ombre ne se reflète pas (la G de dos ¾ a son ombre franche sur le dos, la D sur la tranche).
6. Gabarit F « content ? » : trois référents, neutre → sourcils levés → sourire, chacun avec sa main.
Jugement : la planche se lit sans légende ; rien d'arraché ni de détaché. Ce qui se voit et reste (connu de M2) : la
coupe de l'avant-bras est nette et ouverte (pas de trait en travers), la pince v2 se lit « pince + doigts tendus » au ¾.
0 erreur JS pendant la génération.

## Relevé final (page reconstruite après toutes les retouches : 5,10 Mo)
integration_cache, integration_lateralite, integration_v1, integration_parcours : code 0, 0 erreur JS ;
integration_livraison : livraison_v2.png regardée ; plate_* (bouchon) et engine_integration_planche verts.
Cache (dpr 2, logiciel) : gabarit D plus longue image 817 ms (avant 1 200), après zoom 1 000 ms (avant 3 983), coin et
déplacement 0 rendu pendant le geste. v1 intacte (git status vide sur source/, build.py, tests/, dist/atelier-mains-lsf*).
Aucun TODO dans plate.js, build.py, tests/integration_*.py.

## Ce qui reste (voir PLAN.md « État d'avancement »)
Critique multi-regards puis publication (capacités db, user, downloads) ; temps à remesurer sur GPU ; validations de
l'utilisateur (expressions, chiffres 6–10, presets « à valider ») ; images de la bibliothèque par la capability assets.

## 19 octobre 2026 (soir) — correction après relecture adverse (scripts et images de la relecture : brouillon `r5/`)
Relecture : 4 défauts importants, 5 mineurs, aucun bloquant. Travail dans le brouillon `r5fix/` (scripts de gros plans
`gp.py`, `creux2.py`, `pouce2.py`, mesure `frange_mesure.py`) ; « avant » = copie de la relecture (`r5/cp`), même GLB.

### I-1. Bibliothèque db : limite de 256 Kio — CORRIGÉ (plate.js, enregistreDb)
- Cause : seuil en CARACTÈRES (900 000) alors que le contrat db 0.2.76 refuse toute ligne de plus de 256 Kio SÉRIALISÉE
  (db.d.ts : « DOCUMENT BODIES … at most 256 KiB serialized ») ; le code `invalid_argument` était traduit par « Tu n'as
  pas les droits d'écriture » (db n'a AUCUN code de droits : « deliberately NO permission-denied »).
- Correction : taille mesurée en OCTETS (`new Blob([JSON.stringify(ligne)]).size`), seuil 250 000 (marge de 12 144
  octets) ; au-delà, chaque image part par la capacité `assets` (`assets.upload`, une fois par image et par visite),
  la ligne ne garde que `/_blob/<id>` ; à l'ouverture d'un projet de la bibliothèque, ces images sont relues en data:
  (le document de la planche reste autoporteur : export, .json, brouillon). Sans `assets` (capacité refusée ou personne
  qui ne peut pas modifier), la planche est enregistrée SANS ses images, avec le message qui le dit. Messages par code :
  invalid_argument → « Projet refusé par la bibliothèque (trop lourd…) », quota_exceeded → « bibliothèque pleine »,
  resource_exhausted → « occupée ».
- Mesuré (`tests/integration_v1.py`, fausse capability qui applique la limite réelle de 262 144 octets, photo JPEG de
  301 124 octets collée sur la planche → projet de 502 791 octets) : AVEC assets, ligne de **764 octets**, 1 image
  envoyée, rouverte : image décodée 900 × 600, data:image/jpeg ; SANS assets, ligne de **506 octets**, 0 image, message
  « enregistré sans ses images (trop lourdes pour la bibliothèque : 256 Ko par projet ; garde le .json) » ; **0 refus**
  de la fausse db, aucun message de droits. Image `tests/out/integration_v1_db_photo.png` regardée (photo rouverte).
- Publication : la page doit maintenant être publiée avec `assets` en plus de `db`, `user`, `downloads` (README,
  CLAUDE.md, PLAN.md mis à jour).

### I-2. Grands rendus : frange d'ongle en escalier, plaques d'ombre déchirées, éclats — CORRIGÉ (engine.js, shaders.js)
- **Frange** : le bord frange / tablette était l'isoligne 0,5 d'un masque 0/1 PAR SOMMET (`_MASQUES`.y de M1),
  interpolé : il suit les milieux des arêtes (maillage ≈ 0,6 mm) et zigzague. M1 définit la frange analytiquement
  (build_hand.py, étape 6 : s > s_d − frange − 0,10·W·(x/hw)² dans le repère de la dernière phalange) : le moteur
  recalcule ce champ au chargement, CONTINU (cm), à partir de hand_v2.json (`regions.ongles` : bord_libre_s, largeur,
  frange ; `os` : centre, bout, axes) et le nuanceur le seuille sur un pixel (fwidth), comme la distance signée de
  l'ongle. Contrôle au chargement : signe du champ = masque de M1 sur **2 125 / 2 126** sommets d'ongle (le seul écart à
  0,002 mm du seuil). Mesuré sur le pouce de « V (2) » paume rendu à 4 600 px (bord ajusté par un polynôme de degré 3 :
  écart max / RMS) : **10,0 / 3,9 px → 1,3 / 0,5 px** (même rendu, moteur avant / après) ; le trait d'ongle s'éteint sur
  les 0,4 mm qui précèdent la frange (champ continu au lieu du masque interpolé).
- **Plaques d'ombre déchirées** (poing paume ¾, 1 800 px) : c'était la passe des CREUX FERMÉS (désactivée, elles
  disparaissaient). Deux causes : (1) 3 sondes fixes par direction — à 1 800 px (rayon 1,2 cm ≈ 110 px) une sonde tous
  les 37 px, la décision changeait avec la taille de l'image → pas ≤ 10 px de cible (3 à 12 sondes) ; (2) « plus
  proche » jugé contre la profondeur du pixel : une paume vue de ¾ (pente 35°) remonte de 0,84 cm sur 1,2 cm et fermait
  à elle seule 3 à 4 directions → jugé contre le PLAN TANGENT (pente tirée de la normale de la G-pass, n.z ≥ 0,35).
  Écarté : exiger 8 directions sur 8 (le tunnel du poing de profil perdait son ombre et ses traits revenaient) et
  lisser le masque sur 2 mm (bords flous). Le masque est quand même lu en moyenne de 13 points sur 2 mm puis seuillé à
  mi-hauteur (bord arrondi, plus de dents). Tunnel du poing de profil : toujours peint dans l'ombre (regardé,
  `r5fix/out/creux2_plan.png`).
- **Éclats noirs** (gribouillis sous l'annulaire, bouts d'arêtes au fond d'un pli) : le seuil des miettes (20 px) avait
  été réglé à 30 px/cm ; une miette est une AIRE → seuil × (s / 30)², de 1 (écran) à 16 (A3). À 1 800 px (≈ 80 px/cm) :
  seuil 142 px.
- **Triangle cerné de noir** (jour entre le pouce et l'index, poing paume ¾) : vrai jour à travers la main ; une
  composante transparente enclose de moins de 0,3 % de l'aire de la main est remplie du ton du trait (un creux sombre,
  comme au dessin) ; l'anneau d'un O ou l'espace entre deux doigts dépasse 3 % et reste du fond.
- Reste, regardé : une petite plaque d'ombre à bord droit sur la P2 de l'auriculaire replié (poing paume ¾ à 1 800 px) :
  ombre franche d'un repli de peau du maillage (présente moteur avant et après, avec ou sans creux ; invariante quand on
  change l'IPP ou l'IPD de l'auriculaire), lisible comme un pli à cette taille.
