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
6. **Une planche de classe, pas seulement une main.** Un référent de face à qui appartiennent les mains (l'emplacement
   sur le corps est un paramètre du signe en LSF), **les deux mains**, un mouvement en **plusieurs étapes clés**
   dont chacune a sa propre configuration de doigts, une **flèche** (demi-cercle, zigzag, vague, boucle…) et un **fond**.

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
- Squelette : paume, métacarpien du pouce (`CMC`), 3 phalanges par doigt. La base du doigt pivote à la tête du métacarpien, sous le pli de la racine (`DEEP8`, voir piste P). Articulations au milieu de l'épaisseur (`jz`).
- **Déformeur en arc** aux articulations charnières (MCP, IPP, IPD des doigts ; MCP et IP du pouce), dans `skinMesh` (script.js), données `mesh.arc` (rig3d.py) : dans la zone d'une articulation, la section d'abscisse `tau` tourne de `tau·θ` autour d'un centre qui glisse, chaque fibre de peau devient un arc de cercle et rejoint exactement l'os rigide aux bords de la zone (pas de repli, de fente noire ni de creux au pli). Demi-largeur de zone `h` : grande côté paume (`h ≥ 1,15·d·tan(θmax/2)`, le pli ne se replie jamais), petite côté dos (jointure nette). Chaque chaîne (pouce, doigt) ajoute son déplacement ; parts des doigts lissées dans les palmures. Seule la base du pouce (trapézo-métacarpienne) reste en quaternions duaux. Les anciens poids `bi`/`bw` sont encore exportés mais plus utilisés par la peau.
- Une seule matière : dessin paume devant, dessin dos derrière, fondus sur la tranche.
- Passe « identité » : une partie nette par triangle ; palmures et éminence = paume.
- Quaternions duaux (base du pouce, `dqApply`) : signe aligné sur l'os principal du sommet (essai C ; boneDQ1 ramène w ≥ 0, donc court chemin garanti).
- **Racines sans « col »** (essai A) : le volume du dessin a, à la racine de chaque doigt et du pouce, une gorge puis un bourrelet. Profil corrigé exporté en déplacement `mesh.dz`, appliqué progressivement dès que la pose quitte « Dessin » (`rootBlend`, part `gR`) : dessin au repos exact au pixel près. Au pouce : côté dos seulement (MCP sans cran) ; côté paume, combler la gorge contre l'éminence effaçait l'écart de profondeur qui fait le contour du pouce posé devant la paume (trait effiloché).
- **Coque gardée** (`hullMatProto`) : hors pose « Dessin », main entière, un fragment de coque est jeté s'il est à moins de `HPUSH`(1,8) × épaisseur du trait devant la peau qu'il recouvre (profondeur de la passe identité), ET que les deux parties ne sont pas deux doigts différents (même partie, paume sous un doigt, pouce et paume/éminence) : les fentes en dents de scie et « confettis » des plis (pli de l'éminence et de la MCP du pouce, IP) disparaissent. Le vrai contour garde son poids : silhouette (aucune peau derrière), doigt sur doigt, pouce et doigt, et pouce posé devant la paume, qui en est toujours loin (écart ≥ 2 × HPUSH mesuré). Pas d'exception près du fond : elle laissait des éclats à l'embouchure des plis, et le contour n'y prend pas de cran.
- **Ongles** (essai D, repris) : forme dessinée (enveloppe convexe, recoupée à `NAILM`=10 px de la tranche) en distance signée dans `texNail` (R) ; le shader trace l'aplat + le trait fin (`NAILLW`=2,4 px), nets à tout grossissement. Le trait est un « U » comme dans le dessin : il s'amincit jusqu'à rien au bord libre (`texNailE`), pas d'anneau noir « autocollant ». La texture dos reste celle d'avant (ses mipmaps lues en biais changeaient la vue paume au repos) ; la peau repeinte (sous l'ongle, son trait, bouts de trait étirés en taches) passe par `texNail` G/B, appliquée sur le dos franc au repos et partout hors pose (plus de points noirs sous l'ongle vus de côté). Bombé + repli de peau (`NDOME`, `NFOLD`) dans `mesh.dz` (hors pose seulement), éteint sur 12 px vers la tranche (pas de cran de silhouette au bord de l'ongle).
- **Ongles « pas propres et nets » (piste N)** — grief de l'utilisateur sur sa capture de « V (2) » en dos ¾. Mesuré avant
  de toucher : la largeur de l'ongle n'était PAS en cause (texNail 0,55 × la largeur du doigt, son dessin 0,52-0,57,
  sa vraie main 0,70-0,80 : le rendu est plus étroit que le réel, pas plus large ; `NAILM` gardé). Ni les traits
  intérieurs, ni la coque, ni les mipmaps du dos (isolés un à un : 0 pixel changé près de l'ongle). Quatre causes, toutes
  dans le trait et l'aplat eux-mêmes :
  1. **Le trait était large de 2,4 px DE DESSIN sur la peau**, donc à l'écran il suivait le raccourci de la texture
     (projection plane sur un bout de doigt arrondi) : à l'angle de la capture, 0,60 px de dessin par pixel d'écran
     d'un côté, 0,36 de l'autre → bras du « U » de 4 et 7-8 px (×3 : 9 et 17 px, rapport 1,9). Le trait est maintenant
     de largeur constante À L'ÉCRAN (`nailPx` = 2,4 px ramenés à la distance de la cible, comme le rayon des traits
     intérieurs ; × `vAw`, pixels de dessin par pixel d'écran calculé AU SOMMET — pas `fwidth(sd)`, bruité par la
     quantification 8 bits de la distance signée, qui crénelait le bord intérieur). Mesuré ×3 : 18 et 16 px (1,12).
  2. **Rampe du « U » trop courte** (cos .3 → .65, 23° d'arc ≈ 6 px) : le trait plein s'arrêtait net au coin de
     l'ongle, lu de biais comme un crochet ou un second trait. Rampe .1 → .7 : les bras s'affinent vers le haut, comme
     la plume de son dessin (bras dessinés pleins jusqu'à 0,3-0,5 de la hauteur de l'ongle, mesuré sur les cinq ongles).
  3. **Bombé illisible** : `NDOME` = .08 en S n'inclinait la normale que de 6° de plus qu'au repos et l'ombre générale
     (saturée dès N·L > .77) ne variait que de 3 à 5 % sur l'ongle. Tablette en ARC (`NARC` = 1,8 × demi-largeur,
     flèche 0,30 × demi-largeur ≈ 1,4 mm, pente 34° au bord) ET ombre franche PEINTE dans `texNailE` B : croissant
     le long du bord, du côté où le dessin pose ses ombres (texBack : dernière phalange ombrée côté n < 0 sur les
     quatre doigts, 22-29 % contre 0 %), au ton de l'ombre du dessin (0,82), hors pose seulement. Écarté : seuil sur
     N·L du maillage — il lisait le bruit des facettes (pas de 5 px) et donnait une tache déchiquetée.
  4. **Bord libre** (`texNailE` G) : aplat plus clair (mix 0,45 vers le blanc) de la largeur du trait, sur la part du
     bord qui regarde le bout (sur sa photo la frange libre est ≈ 1,35 × plus claire que la tablette).
  Couture UV exacte/arrondie repoussée de 6 à 14 px du bord de l'ongle (le saut de ½ px tombait dans le trait élargi).
  **`cas_0` identique au pixel près ; `cas_1` : 917 pixels changés, tous à moins de 13 px d'un ongle. Balayage
  inchangé (1685 / 7627 / 19495 / 7452 / 0,0 % / 13,3 %).**
  Deuxième passe (shader seul, `hand3d.json` inchangé), après contrôle adverse :
  - **Le croissant n'était pas franc** : la rampe peinte (0,3 × sa largeur) + flou 1,5 px, interpolés par la texture,
    donnaient une lisière en dégradé de ≈ 10 px de dessin (index de « V (2) » ×3 : 194 → 155 sur 34 px d'écran, 28 %
    de l'ongle). Le shader seuille maintenant `texNailE.b` à mi-hauteur, adouci sur ~1,5 px d'écran (comme la distance
    signée de l'ongle) : lisière 186 → 150 en 4 px d'écran (≈ 1,3 px de dessin), « entre-deux » 1-2 pas de 2 px contre
    7-10. Raccourcir la rampe dans la texture aurait laissé un dégradé qui grossit avec le zoom. Ton peint 0,85 (et non
    0,82) : au bord de l'arc l'ombre générale retire déjà 4 % (194 → 186), l'écran lit ≈ 0,82, le ton du dessin.
  - **Ongles vus de chant** (bouts repliés vus de la paume : annulaire et pouce de « V (2) » face, « Index (1) »,
    « Poing serré ») : la mince lamelle visible était mangée par le trait constant à l'écran (jusqu'à 8 px de dessin en
    biais) et par le bord libre blanc de même largeur — « tiret noir + tiret blanc ». Plafond du trait et du bord libre
    à 5/3 × le trait du dessin (4 px) : au-delà de 53° (N.z < 0,6) le trait suit de nouveau le raccourci, la lamelle
    redevient un ongle (filet + frange claire). 4 px et pas 3,6 : à 3,6 le bras éloigné du « U » de l'index en dos ¾ ×3
    retombait à 7-8 px d'écran contre 10-11 (rapport 1,43, le dédoublement revenait) ; à 4 px le rapport reste ≤ 1,25.
    Plancher gardé : jamais sous ~1,25 px d'écran (de loin, caméra à 100-160, le trait reste continu).
  **`cas_0` identique ; `cas_1` : les mêmes 917 pixels (rien ne change à la pose du dessin, npose = 0).**
  Troisième passe (`rig3d.py` seul, canal B de `texNailE` ; shader inchangé), après second contrôle adverse :
  - **Tache grise sur les ongles de chant** : le plafond du trait avait rendu la lamelle lisible, mais le croissant y
    restait — une tache (102,150,146) sur l'aplat pâle (120,176,171), ≈ 10 % de la lamelle (327 px sur l'annulaire
    de « V (2) » ×3). Mesuré sur les UV des sommets d'ongle tournés vers la caméra : la lamelle est la BASE de l'ongle,
    25 % (annulaire) à 45 % (majeur) de sa hauteur, et le croissant courait le long du côté jusque dans le coin de la
    base. Il s'éteint maintenant vers la base (nul sous 0,3 de la hauteur, plein dès 0,6) : à la base l'ongle est plat
    (sous le repli, lunule), le bombé et son ombre sont distaux. Lamelles de « V (2) », « Index (1) », « Poing serré »,
    « L » : aplat pâle + filet, 0 pixel du ton du croissant ; index en dos ¾ ×3 : profil à mi-hauteur inchangé
    (tablette 84 px, croissant 40, 1 px d'entre-deux), bras du U 1,08-1,25, près du bout croissant 44 px, près de la
    base 1 px.
  - **Écarté : une porte par l'inclinaison dans le shader** (croissant × smoothstep(|N.z|)). Mesuré au fragment
    (shader de débogage) : la lamelle est à |N.z| 0,23-0,45 (médiane 0,33), et dans la vue « dessous ¾ » les pixels
    du croissant commencent à 0,36 (médiane 0,44) — l'ombre est précisément là où le bombé est le plus incliné, toute
    porte par la normale mange le croissant des vues de biais avant d'effacer la lamelle. (Les normales lues sur
    l'attribut `normal` au sommet donnaient 0,07-0,14 : ne pas s'y fier pour juger ce que voit le shader.)
  **`cas_0` identique ; `cas_1` : les mêmes 917 pixels ; `hand3d.json` ne change que par `texNailE` B (5306 texels).**
- **Colonne du pouce (piste T)** : les CENTRES d'articulation du pouce ne sont plus les plis dessinés.
  Mesuré sur le dessin : métacarpien 193,6 px, P1 100,5 px, P2 + pulpe 128,4 px → 1 : 0,52 : 0,66, alors que
  l'anatomie donne 1 : 0,67 : 0,55 (46 / 31 / 21 mm + ~4,5 mm de pulpe). Le pli IP dessiné est ≈ 25 px trop
  proximal : le pouce pliait trop tôt et traînait un boudin. `IP8` (rig3d.py) glisse le centre de l'IP à
  (790, 465) le long de l'axe du pouce → 123,5 / 104,2 px, soit P1:P2 = 1 : 0,84 (anatomie 1 : 0,84). La CMC
  (652, 748 : trapèze, au poignet, base de l'éminence) et la MCP (718, 566 : au niveau de l'apex de la
  commissure) sont vérifiées et gardées. Le dessin ne bouge pas : silhouette, textures, découpage et profils
  restent calés sur `CP`, la chaîne corrigée n'est exportée que dans `mesh.chain.pouce` (lue par script.js
  pour les articulations, ARCJ et `AX.pouce`) → repos exact au pixel près.
- **Base du pouce à deux axes (Hollister 1992, Imaeda 1994)** : la trapézo-métacarpienne n'a plus de centre de
  rotation unique. Axe de flexion/extension (« rapprocher ») FIXE dans le TRAPÈZE, par `CMC` ; axe
  d'abduction/adduction palmaire (« avancer ») FIXE dans la BASE DU 1er MÉTACARPIEN, décalé de `TOFF` = 0,30 le
  long de l'os : les deux axes ne se croisent pas, la base du pouce glisse. Ils ne sont pas perpendiculaires
  aux os (`TFT` = 20°, `TAT` = 15°), donc flexion et abduction entraînent déjà ≈ 25° de pronation ; l'axe de
  flexion penche en plus de `FEV` = 15° vers la paume, donc en se rapprochant des doigts le pouce passe DEVANT
  la paume au lieu de glisser dans son plan (colonne du pouce antérieure). La pronation explicite (`PRONA`)
  suit l'OPPOSITION, pas « avancer » : elle démarre avec l'abduction palmaire et ne culmine qu'une fois le
  pouce ramené vers les doigts (42° en abduction radiale → 99° en opposition). À (0, 0) : aucune pronation.
- **Vis sans fin de la trapézo-métacarpienne, et un solveur qui ne recule plus (piste V)**. Grief de l'utilisateur :
  « la main n'est toujours pas naturelle, il y a des incohérences quand on bouge les doigts et surtout le pouce ».
  Mesuré, pas supposé — balayage du pouce sur toute sa course par le chemin RÉEL de l'application (curseur →
  `constrain` → `solve`), pénétration relevée à chaque pose :
  1. On demandait « rapprocher 40 » et on obtenait **21,4**, avec « avancer » ramené de 10 à **6,1** et la base
     de 20 à **10,7**. Une commande en déplaçait trois, et le pouce ne traversait jamais la paume.
     Cause : `solve` commençait par une interpolation GLOBALE en arrière pour sortir de la pénétration, ce qui
     ramenait aussi les articulations que l'utilisateur n'avait pas touchées. Il part maintenant de la pose de
     départ et pousse chaque articulation vers sa cible aussi loin que le contact le permet, **celles qui dégagent
     de la place d'abord** (mesuré : une évaluation de pénétration par articulation), puis un second tour pour
     celles qu'un voisin bloquait. C'est l'ordre que `settle` appliquait à la main depuis toujours (écarter le
     pouce, fermer les doigts, ramener le pouce) ; déduit ici, il vaut pour TOUTES les poses.
  2. Le pouce butait sur la paume parce qu'il restait dans son plan. À la trapézo-métacarpienne, flexion/adduction,
     abduction et rotation axiale sont COUPLÉES (Hollister 1992 ; les études in vivo parlent de « screw-home ») :
     ce ne sont pas trois commandes indépendantes. `AVC` = 0,7 : rapprocher le pouce des doigts le fait sortir du
     plan de la paume, donc il passe DEVANT elle au lieu de dedans. La valeur n'est pas choisie à l'œil — le
     balayage donne : au-delà du plan (avancer < 15°) le rapprochement bute vers 21°, et il atteint 40° dès que
     l'abduction palmaire dépasse 20° ; 0,7 suit exactement cette frontière.
  Résultat mesuré : 9 poses de pouce sur 10 atteignent EXACTEMENT la valeur demandée, pénétration nulle (la 10e,
  pouce ramené sur un poing déjà fermé, est arrêtée par un vrai contact). Sur la planche de contrôle, `Poing serré`
  passe de `pou:44/14/55/-20` (bout en hyperextension, pouce plaqué à plat) à `pou:45/35/40/25`, la valeur même du
  preset, et les quatre doigts de `Index (1)` se replient enfin à égalité (l'annulaire restait à 75°).
  **Repos face et dos inchangés au pixel près.**
- **LE DOS DE LA MAIN (piste W)** — c'était une plaque lisse, mesuré sur les rendus de contrôle : aucun relief,
  donc ni ombre ni trait. Le détecteur de plis lui-même n'y trouvait rien, parce qu'il n'y avait réellement rien
  à trouver. Sur une vraie main (photos 2357, 2364, 2366, 2370) le dos montre trois choses, qui vont par paires :
  les **tendons extenseurs** (quatre cordes du poignet aux jointures), les **vallées** entre ces cordes, et les
  **sillons** entre deux doigts repliés. Tendons et vallées suivent l'EXTENSION ; sillons et jointures suivent la
  FLEXION. Le dos n'est donc jamais plat, mais il ne montre jamais les deux reliefs à la fois — c'est ce qui
  sépare une main d'un gant. Tout passe par `knAdd` (le mécanisme du relief des jointures) et par `rootBlend`,
  donc à la pose du dessin l'amplitude est nulle et le repos reste exact au pixel près.
  Deux choses apprises en le réglant :
  1. **Une côte haute et étroite ne passe pas.** Le maillage (pas de 5 px) ne sait pas la lisser, et chaque facette
     se lit comme un trait : le dos se couvrait de griffures. Pente ≈ 2 × hauteur / largeur, à garder basse — un
     tendon est un renflement DOUX, qu'on voit par l'ombre et pas par un trait. `TEND`=0,11 `VALL`=0,075
     `SILL`=0,15, largeurs 0,40 à 0,46 × l'écartement des métacarpiens.
  2. **Deux reliefs par sommet ne suffisaient plus.** `KNI`/`KNW` ne gardaient que les DEUX plus forts : avec
     quatorze bosses bien séparées ça allait, mais les champs du dos se recouvrent, et la frontière où le
     classement bascule rend le déplacement DISCONTINU — encore des facettes. `KNB` = 4 repousse la discontinuité
     sur le quatrième relief, bien plus faible, et elle cesse de se voir. L'amplitude est aussi SIGNÉE désormais
     (le signe voyage avec le pilote, le précalcul ne voit que la valeur absolue) : on peut creuser, pas seulement
     bomber.
- **Détecteur de plis : ÉTEINT** (`CRV` = 1e4, `window.__atelier.setCrv` pour le rallumer). Mesuré sur cinq vues,
  détecteur contre détecteur éteint : sur `Poing serré` et `Pince` il ne change RIEN de visible (198 et 175 pixels
  sur 350 000, invisibles à l'œil, vérifié en gros plan côte à côte) ; sur le dos de la main il ne produit que des
  griffures, en lisant chaque facette du relief comme un trait. Il avait été écrit pour faire lire les creux ; le
  relief du dos le fait mieux, par l'ombre. Le code reste en place, la passe le saute quand le seuil dépasse 100.
- **Éminence thénar (tissus)** : c'est le volume qui change le PLUS sur la paume quand on signe, et il était
  absolument fixe — la peau suivait la base du pouce, mais le muscle dessous ne gonflait jamais. Les trois muscles
  de la base du pouce (court abducteur, court fléchisseur, opposant) sont d'autant plus contractés que le pouce
  s'OPPOSE, pas qu'il s'avance seul ni qu'il se rapproche seul. On réutilise donc la mesure d'opposition qui pilote
  déjà la pronation, et le même mécanisme que le relief des jointures (`knAdd`), mais côté PAUME et sur toute la
  longueur du métacarpien : `THEN` = 0,17 × cette longueur. À (0,0) la mesure vaut 0, donc le dessin au repos ne
  bouge pas d'un pixel (vérifié). Le pas de quantification de `KNW` suit désormais la plus forte amplitude : le
  thénar dépasse une jointure et aurait été écrêté à 0,25.
  **Commissure pouce–index : vérifiée, rien à faire.** Je l'avais annoncée comme « une simple échancrure qui ne
  s'ouvre pas » ; c'était faux. Rendue à trois abductions (0°, 22°, 45°) en paume, dos et biais, la palmure
  s'ouvre bien en nappe continue et sa courbe reste lisse — la peau étant UNE surface fermée, le tissu s'étire
  tout seul. Ne pas y ajouter de déformeur : il n'y a pas de problème à résoudre.
- **Le creux du pouce — le DOS de la première commissure** (« le pouce est un réel problème avec son creux »).
  Pouce replié sous ou en travers de la paume (V (2), Quatre (4), B, Index (1), Poing serré), le bord radial de la
  main vue de DOS faisait un « S » : concavité profonde sous la tête du 2e métacarpien, bosse à la base du pouce,
  poignet. Sur sa main (photos dos, pouce caché dessous ; V de dos), ce bord est une ligne droite qui prolonge le
  bord radial de l'index jusqu'au poignet. Mesuré (profil x(y) de la peau posée, vue dos, tête du 2e métacarpien →
  poignet) : flèche de 20,9 mm en Quatre, 18,4 en V (2), 19,3 en B, 15,6 en Index (1). Ce n'était ni le relief
  (`setKnk(0)` : 21,8), ni la pronation (`setPron(0)` : 26,0, pire), ni les axes de la CMC : c'était les POIDS.
  `thenarW8` (rig3d.py) est un poids 2D, le même pour la paume et pour le dos ; côté paume c'est l'éminence thénar
  et c'est juste, mais côté dos la peau de la commissure et celle qui recouvre le 2e MÉTACARPIEN portaient 0,5 à
  0,94 de part du métacarpien du pouce (le sommet qui faisait la silhouette venait de (615, 505) px, au-dessus de
  l'index, avec 0,48) : « rapprocher 40 » balayait tout le dos de la commissure de 11 à 27 mm vers le centre.
  Deux corrections, toutes deux des poids (repos exact au pixel près, vérifié) :
  1. côté dos seulement, part du pouce annulée en deçà de la ligne bord radial de la tête du 2e métacarpien
     (648 px) → trapèze (652 px) ; la commissure dorsale se plie sur `XW` px juste au-delà, sous la main. La face
     paume (éminence, palmure palmaire et ses plis dessinés) suit le pouce ; la tranche passe de l'une à l'autre sur
     40 px centrés sur z = 0 (`ZA, ZB`) ;
  2. rampe axiale de la part du métacarpien `SAX` = .30 au lieu de .78 : la peau suit l'os dès le tiers du
     métacarpien, sinon la base du pouce restait dehors en bosse (saillie 7,7 → 4,3 mm, saturée à .30 ; le reste
     est le contour dessiné du poignet, qui ne peut pas tourner autour du trapèze).
  **Le pli lui-même (seconde passe).** Un premier réglage `XW` = 60 constant (rampe z 0 → −15) donnait le bord droit
  mais, en vue « Profil », une tache d'ombre RECTANGULAIRE sous la base du pouce et 35 à 44 arêtes à dièdre > 60°
  dans la fenêtre de la commissure (1 avant). Mesuré :
  - la tache est la TEXTURE, pas la lumière : texture du dos remplacée par un aplat, elle disparaît ; ses pixels
    viennent de UV x 645..683, y 452..542, c'est-à-dire de l'ombre peinte de ~20 px le long du bord de l'échancrure
    (luminance 136 contre 161). Le pli est une nappe qui relie le bord du dos, immobile, au pouce passé sous la
    paume (113 à 160 px plus loin, 95 à 170 px plus bas) : cette nappe est faite de 27 à 44 px de peau au repos,
    étirée ×4 à 5, et c'est l'ombre dessinée du bord qu'elle affiche à plat. On ne peut pas l'éviter sans toucher
    aux UV (donc au repos) : on la concentre sous le pouce, où une ombre est naturelle ;
  - les dièdres de 60 à 175° (triangles retournés) étaient au FOND de l'échancrure (x − xl 33..41, y 527..552,
    z −7..−29) : tube serré (rayon ~10 px) où la rampe faisait encore varier la part de 0,78 à 0,98, soit 30 px
    d'écart de déplacement sur 10 px de peau. Le fond doit être un PLATEAU à part 1 : `XW` ≤ 30 à ce niveau.
    Mesuré : 30 px → 1 / 6 / 10 / 0 arêtes (V (2) / Quatre / B / Index (1)) ; 36 px → 11 / 23 / 16 / 0 ; 44 px
    (rampe z ±20) → 11 / 20 / 16 / 6 ; 60 px (rampe z 0..−15) → 38 / 44 / 39 / 35.
    Un palier intermédiaire (part 0,7 au fond, le reste sur la base ulnaire du pouce) a été essayé et rejeté :
    la peau du pouce lui-même, coupée de 5 à 15 %, se retourne (44 à 57 arêtes sur son bord ulnaire, y 437..460).
  D'où `XW_Y`, largeur du pli fonction de y : 95 px en haut de l'échancrure (y 440, le bord libre n'est qu'à 5 px
  de xl et le pouce à 95 : l'ombre du bord reste serrée), 30 au fond (y 515..550), 60 sur le dos du 1er métacarpien
  (y 600), puis 34 / 20 (y 660 / 690) : plus la rampe est étroite près du trapèze, moins la base du pouce ressort
  (bosse convexe du bord 4,5 → 2,8 mm). Résultat (V (2) / Quatre / B / Index (1)) : flèche concave sur l'image
  0,7 / 0,2 / 0,2 / 0,7 mm (première passe 0,1..0,2, original 13..18) ; arêtes > 60° : 1 / 6 / 10 / 0 (première
  passe 38 / 44 / 39 / 35) ; la tache est devenue une ombre sous la base du pouce, bord supérieur sur le pouce, sans
  le côté rectiligne du bas ; plus de traits parasites au pli. Pénétration des 15 presets inchangée (≤ 0,42).
  Balayage (172 poses) : replis 1 685 → 1 789, froissements 7 627 → 8 025, pincés 19 495 → 21 395, gonflés
  7 452 → 16 869 (première passe 12 419 ; 16 217 avec un pli de 36 px au fond), os 0,0 %, épaisseur 13,3 %. Les « gonflés » SONT la nappe du pli : son
  aire est fixée par la pose (le pouce passe 2 à 3,7 cm sous la paume) et par les 27..44 px de peau disponibles
  entre le bord droit et le pouce ; les ramener sous 9 000 demanderait ≥ 47 px de pli au fond de l'échancrure,
  c'est-à-dire remettre la rampe sur le tube du fond et retrouver les retournements. Le compromis choisi est le pli
  sans retournement : un triangle étiré est invisible (c'est la nappe), un triangle retourné fait un trait.
  Pouce dehors (L, Y, Main ouverte (5)) : la palmure dorsale, qui ne suit plus le métacarpien, se tend en membrane
  et prend une ombre douce — comme sur sa photo paume ouverte ; l'éminence thénar vue de paume (B) reste une masse
  lisse.
- **Fléchisseur profond commun** : `dip ≥ 0,45 (pip − 55)`. On ne tient pas l'articulation du milieu pliée à fond
  avec le bout parfaitement tendu ; ce doigt-là se lisait comme une pièce mécanique. (La borne haute
  `dip ≤ 25 + 0,65 pip` existait déjà : le couplage est maintenant dans les deux sens.)
- **Fantômes et lecture** : ils interpolaient les angles SANS butée ni solveur, donc entre deux poses valides les
  images intermédiaires pouvaient montrer le pouce dans la paume ou deux doigts qui se traversent.
  `lerpPoseSafe` passe par `constrain` puis `solve` (≈ 3 ms, contre 13 ms de peau par image : à ce prix-là aucune
  image n'a d'excuse), avec un petit cache pour les fantômes, dont la pose ne change pas à chaque rafraîchissement.
- **Rides et plis qui suivent la flexion (piste R)** : les traits du dessin ne sont plus figés.
  `rig3d.py` range les plis dans `texCrease`. Un pli ou une ride est un trait FIN plus sombre que l'aplat voisin,
  l'ombre franche est une plage LARGE : une fermeture morphologique de rayon `CRR` = 5 px efface les traits et garde
  l'ombre, donc `a = 1 - luminance dessinée / luminance fermée` isole le SEUL trait (0 sur l'aplat comme dans
  l'ombre ; plancher `CRA0` = 0,07, sinon le grain JPEG du dessin paume se creuserait et la paume se salirait).
  Canaux : R = trait de la paume, G = le même dilaté (pli élargi), B = aplat du dos (teinte du vert × clarté, comme
  la peau des ongles), A = masque large des rides du dos. Ongle, trait d'ongle et taches exclus du dos.
  `script.js` envoie au shader, par sommet, l'effacement `crf` du trait : x côté paume (< 0 : pli creusé et élargi),
  y côté dos (> 0 : ride effacée) ; `vS` choisit le côté. Côté paume le trait est gris, un multiplicateur
  `(1 - a(1-e))/(1-a)` suffit ; côté dos il est NOIR, donc on le remplace par l'aplat voisin (`mix`, qui va aussi
  dans l'autre sens en hyperextension : la ride se marque). Les deux valent exactement l'identité à e = 0.
  Le champ `crf` vient de deux articulations par sommet (bosse gaussienne le long de l'os, refermée sur les côtés,
  plus large et biaisée vers le proximal côté paume) ; poids calculés une fois au chargement, le rafraîchissement
  n'est qu'une somme de deux produits (attribut Int8 normalisé, non ré-envoyé quand tous les angles sont nuls).
  Amplitude : le dos s'étire de 0,29 %/° à la MCP, 0,35 à l'IPP, 0,20 à l'IPD (≈30 % en tout) ; la réserve de peau
  plissée d'une jointure étant à la mesure de ce qu'elle doit rendre, l'effacement est la part de course parcourue
  (`CRMX` = 95/110/85°, ×1,1 : le dos est lisse un peu avant la butée, comme sur les photos 2374 et 2375).
  Le pli thénar suit « rapprocher » et « avancer » du pouce ; les plis palmaires transversaux suivent les MCP.
  **Au repos tous les angles valent 0, donc e = 0 et le multiplicateur vaut exactement 1 : `cas_0` et `cas_1` sont
  identiques au pixel près.** Écarté : écarter les rides en décalant les UV (l'ongle glissait) — inutile, la peau
  porte sa texture et l'étirement du déformeur en arc écarte DÉJÀ les rides dessinées ; filtrer la texture dans le
  shader (min/max) — halo sur le bord de l'ombre franche, et un trait noir ne peut pas s'éclaircir en multipliant.
- **Proportions et convergence des quatre doigts (piste P)** : comme pour le pouce, les CENTRES d'articulation
  des doigts ne sont pas les plis dessinés. Trois corrections, toutes dans `mesh.chain` (le dessin ne bouge pas :
  silhouette, textures, découpage et profils restent calés sur `CP`, donc `cas_0` et `cas_1` sont identiques au
  pixel près aux rendus de référence — vérifié pixel à pixel).
  1. **IPD glissée vers le bout** (`PHAL8`, rig3d.py). Mesuré sur le dessin : moyenne:distale = 1 : 1,30 (index),
     1,10 (majeur), 1,31 (annulaire), 1,70 (auriculaire), alors que l'anatomie donne 1 : 0,88 / 0,81 / 0,86 / 1,09
     (P2 contre P3 + ~4 mm de pulpe). Relevé aussi sur la photo 2354 (paume à plat), index : pli IPP → pli IPD
     418 px, pli IPD → bout 410 px, soit 1 : 0,98 — le pli distal DESSINÉ est bien trop proximal. On garde
     IPP → bout tel qu'il est dessiné et on le repartage P2 : (P3 + pulpe), doigt par doigt : l'IPD avance de
     18,6 / 15,8 / 20,9 / 16,8 px. Elle glisse le long de la polyligne du dessin, donc la phalange distale garde
     EXACTEMENT sa direction et l'IPP ne dévie que de 1,2° au plus.
  2. **MCP enfoncée doigt par doigt** (`DEEP8`). Le pli digital palmaire est au TIERS PROXIMAL de la phalange
     proximale, donc pli → IPP = ⅔ de P1 et le centre de la MCP est ½ de cette distance plus bas :
     `DEEP8 = ½ · |CP[0] → CP[1]|` → 53,8 / 62,0 / 53,4 / 43,3 px au lieu des 38,5 / 41,2 / 38,9 / 38,2 px de
     l'ancienne règle « ½ largeur de doigt » (la même pour les quatre, alors que les quatre doigts n'ont pas la
     même longueur). Du coup `vis()` (collisions) cache exactement ⅓ de la phalange proximale.
     Résultat mesuré, P1 : P2 : (P3 + pulpe) — index 1 : 0,632 : 0,559 (cible 1 : 0,563 : 0,497), majeur
     1 : 0,623 : 0,507 (1 : 0,590 : 0,480), annulaire 1 : 0,670 : 0,576 (1 : 0,621 : 0,534), auriculaire
     1 : 0,576 : 0,630 (1 : 0,554 : 0,606) ; avant la piste P l'écart sur la distale allait jusqu'à 0,25.
  3. **Convergence `CONV` remise dans le bon sens** (script.js). Poing fermé, les bouts des quatre doigts
     s'écartaient de 310 px alors que les MCP ne s'écartent que de 263 px : les doigts DIVERGEAIENT au lieu de
     pointer vers le scaphoïde. `CONV` = 6 / 2 / −2 / −7 (au lieu de −16 / 3 / 10 / 14) ramène l'écartement des
     bouts à 236 px (239 aux 3/4), le poing se ferme en entier sans pénétration (`cas_3` : 90/105/70 au lieu de
     89/103/69) et le jour entre les bouts et la paume se referme en grande partie.
  Vérifié aussi : les axes de flexion des doigts sont repris sur la chaîne corrigée (`segu` dans rig3d.py,
  `AX[k]` dans script.js), l'arc transversal des têtes métacarpiennes est bien là dans `jz` (majeur le plus
  dorsal à −2,4 px, auriculaire le plus palmaire à +1,6), aucune phalange ne s'allonge ni ne se raccourcit en
  pliant (mesure sur 9 poses : os rigides à 100,00 %, peau du bout à 0,03 % près), et le temps de `refresh`
  est inchangé (≈ 12 ms minimum en rendu logiciel).
- **Relief des jointures et tranche de la main (piste D)** : le déformeur en arc donne, à une articulation pliée, un
  cylindre parfait ; une vraie main y montre la tête de l'os qui saille côté dos (quatre bosses des têtes
  métacarpiennes dans le poing, marches entre phalanges repliées : photos 2357, 2364, 2374).
  `script.js` ajoute donc, AVANT l'arc (le déplacement est ensuite porté par lui, comme `mesh.dz`), un relief local
  centré sur chaque articulation, du côté DOS seulement : gaussienne le long de l'os, refermée de côté, hauteur
  `KNK` = 0,22 × demi-largeur du segment (× 1,45 à la MCP, dont la tête est plus large et plus saillante ; × 1,05 à
  l'IPP ; × 0,55 à l'IPD). Direction : −f0 de l'articulation (le côté extenseur), donc exactement −z pour les doigts et oblique pour
  le pouce. Hauteur proportionnelle à la part de course parcourue, donc **nulle au repos : `cas_0` et `cas_1`
  restent exacts au pixel près.** Les deux articulations qui commandent le plus chaque sommet sont retenues au
  chargement, le rafraîchissement n'est qu'une somme de deux produits (+1,3 ms sur `skinMesh`, médiane 13,4 ms).
  `x0`/`y0` de `skinMesh` sont désormais lus dans `pa` et plus dans `MREST`, pour que ce déplacement de base compte
  sur les trois axes. Amplitude réglée AU BALAYAGE (ci-dessous) et aux rendus : à 0,14 elle ne faisait pas lire
  une jointure dans le poing (piste X), à 0,27 la peau du dos commençait à se froisser ; 0,22 est le compromis.
- **Tranche de la main** (même piste) : l'épaisseur n'est pas dessinée, elle est déduite, et elle sortait trop
  uniforme. `rig3d.py` ajoute à `mesh.dz` une dilatation de l'intervalle [−arrière, avant] : éminence hypothénar
  (`TH_HYP` = 0,30 côté paume, 0,40 × côté dos, tache large centrée sur (330, 668)) et doigts (`TH_FIN` = 0,09 ;
  un vrai doigt fait ≈ 16 mm d'épaisseur pour 18 de large, le volume n'en donnait que 0,81 × la largeur).
  Comme tout `mesh.dz`, cela n'entre qu'une fois la pose quittée : le repos vu de face ne bouge pas.
- **Poids du trait intérieur constant** (même piste) : le rayon du détecteur de la passe identité était figé en
  pixels d'écran, si bien qu'en gros plan le trait intérieur n'était qu'un filet gris à côté du gros trait noir de
  la coque (trait « fin et dédoublé » entre deux doigts repliés). Il suit maintenant l'épaisseur RÉELLE du contour
  (`0,4 × HULL/SC ×` pixels par unité, plafonné à 5,5) et se fond avec elle. Interpolé par `rootBlend` (`gR`) comme
  `mesh.dz`, donc « Dessin » reste exact au pixel près. `EDMAX` = 2,6 : au-delà de cette marche de profondeur, la
  partie d'en face n'est pas « derrière » mais au fond d'une crevasse (creux du poing) et on n'y trace rien.
- **Balayage anti-déformation** (`tests/balayage.py`) : parcourt ≈ 170 poses (chaque articulation seule à plusieurs
  angles, combinaisons dans un même doigt, poses extrêmes, les 12 configurations de `PRESETS`) et mesure sur le
  maillage, par rapport au repos : arêtes repliées (dièdre signé < −140°), arêtes froissées (dièdre changé de plus
  de 100°), triangles pincés (< 12 % de leur aire) ou gonflés (> 320 %), variation de longueur des phalanges,
  variation d'épaisseur des anneaux de peau loin des articulations. Sort le tableau des pires poses et, avec
  `--images N`, les rend en PNG. `--knk 0` éteint le relief des jointures (comparaison A/B).
  Le relevé de référence est gardé dans `tests/out/balayage.txt`.
  **Relevé de référence (172 poses, version intégrée pistes N + creux du pouce + Z)** : replis 1 713,
  froissements 8 067, pincés 21 465, gonflés 17 920, allongement d'os max 0,0 %, variation d'épaisseur max 15,0 %.
  Les « gonflés » sont pour l'essentiel la NAPPE du pli dorsal de la première commissure (27 à 44 px de peau au
  repos étirés ×4 à 5 sous la main quand le pouce passe dessous — invisibles en tant que triangles, voir « Le
  creux du pouce ») ; les 15,0 % d'épaisseur sont l'auriculaire replié seul (plus de sillon dorsal en face, voir
  piste Z). Avant ces trois pistes (relief 0,22 + élargissement 0,11) : 1 685 / 7 627 / 19 495 / 7 452 / 0,0 % /
  13,3 %.
  (Avant la piste X, relief à 0,14 sans élargissement : 1 120 / 5 194 / 18 258 / 3 720 / 0,0 % / 12,0 % ; sans
  aucun relief : 1 153 / 5 195 / 18 255 / 2 959 / 0,0 % / 8,8 %.) À 0,14 le relief ne créait ni repli ni
  froissement de plus ; à 0,22, avec l'élargissement latéral, il en crée — c'est le prix d'une jointure qui
  SORT, et la peau étirée sur une jointure est ce qu'une vraie main fait. Ce qui n'est pas négociable tient :
  **l'os ne s'allonge jamais, dans aucune des 170 poses, et le repos reste exact au pixel près.**
  Les pires poses sont toujours les flexions complètes (`tous.100/115/85`, `PRESET Poing serré`) et, pour une seule
  articulation, la MCP du majeur et celle de l'auriculaire : c'est là que les palmures travaillent le plus.
- Essayé et écarté sur la piste D : **bourrelets palmaires** (deux lobes de part et d'autre du pli, pour que la
  chair chassée par la flexion remplisse le creux du poing) — même à 3 × l'amplitude ils ne comblent pas le tunnel
  que laisse un doigt plié à 90/105/70, et le balayage les condamne (replis 1 153 → 1 631, froissements 5 195 →
  7 269 pour 170 poses) ; **ombre franche automatique au fond des crevasses** (compte des voisins plus proches de
  l'œil dans la passe identité) — le compteur n'atteint jamais le seuil, aucun effet visible, retiré ; **second
  point de contrôle du trait intérieur** (refaire le test à FAR × rayon pour écarter les échardes) — cela amincit
  et coupe aussi les vrais traits entre deux doigts repliés, retiré.
- Essayé et écarté à l'intégration : partage linéaire des palmures entre deux doigts (essai C) par-dessus le déformeur en arc (fente/pointe entre annulaire et majeur, poing d'un seul doigt) ; trait épais tiré de la passe identité pour le pouce devant la paume (taches sur le contour dos).
- Les photos de la main de l'utilisateur (profil, poing, pince, O…) ont servi de référence de volumes ; elles ne sont pas dans le dépôt.

## LE POING SERRÉ (piste X) — « tu vois bien que c'est pas réaliste »

Grief de l'utilisateur, photos de son vrai poing à l'appui (2357, 2374, 2375) : *« le poing serré ne correspond
pas et les doigts sont toujours atroces »*. Quatre mesures, et trois d'entre elles ont démenti mon premier
diagnostic — à garder en tête avant de refaire la même erreur :

1. **Les proportions n'étaient PAS en cause.** J'avais annoncé un poing « colonne haute et étroite » contre son
   « bloc compact ». Mesuré : hauteur / largeur du poing = 1,59 en comptant l'avant-bras DESSINÉ (220 px de
   poignet qui font partie de son dessin), **1,19 du pli du poignet au sommet des jointures** — une vraie main
   donne 1,18 à 1,29. De même le doigt replié vu côté paume : jointure + P2 + rayon du bout = 2,2 × la largeur
   du doigt chez lui comme chez moi. Il n'y avait rien à corriger là, et allonger P1 de 6 % n'aurait rien changé.
2. **Le poing n'est pas creux.** Les quatre bouts touchent la paume à 0,1–0,2 mm près (mesuré sommet à sommet,
   `scipy.cKDTree`). Le « trou » vu de profil est le tunnel connu (défaut 0), pas un défaut de fermeture.
3. **Ce qui n'allait pas, c'était la LISIBILITÉ.** Deux choses, mesurées :
   - **Aucun relief de jointure.** `KNK` = 0,14 donnait 1,8 mm de saillie à la tête du métacarpien, là où une
     vraie jointure sort de 4 à 5 mm. Les quatre doigts repliés se lisaient comme quatre tuyaux lisses, sans
     arête pour accrocher l'ombre franche. `KNK` = 0,22 et des gaussiennes RESSERRÉES le long de l'os (une
     jointure est un dôme court, pas un renflement qui court sur la phalange) : les quatre têtes sortent.
   - **Les doigts ne se touchaient pas.** Le dessin de référence est une main OUVERTE : à la racine, deux
     doigts voisins sont séparés par ~2 mm d'air (1,96 unité entre deux centres de MCP pour 1,78 de
     demi-largeurs cumulées). L'adduction ne referme rien — elle tourne AUTOUR du centre de la MCP, qui est
     justement là où la fente est. Résultat : quatre fentes CLAIRES, chacune doublée du contour noir, et le
     poing se lisait comme quatre bananes posées sur une paume. Sur une vraie main les jointures se touchent et
     ce qu'on voit entre elles est une OMBRE. D'où `KNL` = 0,11 : chaque jointure (MCP et IPP) s'élargit des
     deux côtés avec sa flexion, sur une gaussienne LONGUE le long de l'os (2,0 et 1,6 × la demi-largeur) pour
     fermer la fente sur toute la longueur du doigt et pas seulement au droit de la jointure.
     L'os le dit aussi : la tête du métacarpien est la partie la plus large de l'os, et elle ne sort qu'en flexion.
4. **Le pouce était faux, et c'était ça « le poing serré ne correspond pas ».** Il se couchait À PLAT EN TRAVERS
   de la paume : bout à x = −1,73, c'est-à-dire **au-delà du majeur**, dépassant du poing comme une palette.
   Sur sa photo 2357, le pouce s'enroule sur le FLANC RADIAL de l'index, MCP et IP bien pliées.
   - La cible de `thumbReach` était un point INTÉRIEUR à la masse des doigts (milieu de l'IPP de l'index et de
     l'IPD du majeur) : inatteignable, donc le solveur s'arrêtait au contact, n'importe où. Elle vise maintenant
     un point qui est vraiment à la SURFACE : milieu de P2 de l'index, décalé de 1,05 × demi-largeur côté radial.
   - Balayage de 1 232 poses de pouce contre cette cible : le preset passe de `TH(45,35,40,25)` à
     `TH(20,0,50,65)`, l'écart à la cible de **5,52 à 1,0 unité**, sans une seule unité de pénétration en plus
     (0,77, qui est celle des quatre doigts eux-mêmes).
   - **v18 : `TH(24,10,35,60)`, le pouce EN TRAVERS des P2.** La critique finale (lot 3) a relu la photo 2357 :
     le pouce ne longe pas le flanc de l'index, il se couche SUR les P2 de l'index et du majeur, ongle vers le
     haut, bout vers le majeur. Nouveau balayage (`exp/sweep2.py`, cible devant les P2, av ≤ 58, av + rap ≤ 92) :
     meilleur `[24, 10, 35, 60]`, écart 0,92, pénétration 0,18 brute, 0,29 après `solve` (plafond 0,5), le solveur
     le garde tel quel. Vue de face : le pouce barre l'index et le majeur comme sur la photo ; de profil il
     ressort au même endroit qu'avant. L'ancien `[20, 0, 46, 65]` laissait le pouce À CÔTÉ du poing.

**Contour dans un creux de contact.** `HULL_FS` gardait la coque dès que deux parties étaient deux doigts
différents (`real`), quel que soit l'écart de profondeur. Deux doigts repliés qui SE TOUCHENT ont un écart nul :
la coque des deux se superposait au point de contact et le test basculait d'un pixel à l'autre. `real` exige
désormais un vrai écart (`d > 0,5 × push`) : un contour « doigt sur doigt » veut dire qu'un doigt passe DEVANT
l'autre. Le trait de contact est l'affaire de la passe identité, qui en trace UN, propre (son seuil entre deux
doigts est déjà de 0,02). Reste les lambeaux au FOND des crevasses (défaut 5) : là, l'écart de profondeur est
réel (on voit la paume tout au fond), le contour est légitime, et il est déchiré parce que le fond est rasant.
Invisible à l'échelle d'usage, visible en très gros plan.

**Coût mesuré au balayage** (170 poses) : replis 1 120 → 1 685, froissements 5 194 → 7 627, pincés 18 258 →
19 495, gonflés 3 720 → 7 452, **allongement d'os toujours 0,0 %**, variation d'épaisseur 12,0 → 13,3 %.
Les 13,3 % SONT l'élargissement voulu (1 mm par côté sur 9 mm de demi-largeur). Le reste vient du relief plus
haut : c'est de la peau étirée sur une jointure, ce qu'une vraie jointure fait. Une leçon au passage : le champ
latéral s'allume sur `0,55 × rd` ; avec `rd` = demi-largeur, la rampe faisait un demi-millimètre et étirait les
triangles (8 400 gonflés) — `rd` = 2,2 × demi-largeur donne le même volume sur une rampe longue (7 452).

**`cas_0` et `cas_1` restent identiques au pixel près** après chacune de ces corrections (vérifié à chaque étape).

## LES DOIGTS REPLIÉS À CÔTÉ DES DOIGTS TENDUS (piste Z) — « les doigts sont déformés »

Grief de l'utilisateur, capture de « V (2) » vue de dos aux trois quarts et photo de sa main dans la même
configuration : l'annulaire et l'auriculaire repliés se lisaient comme deux boudins ronds séparés, cernés d'un
gros trait, avec un creux sombre entre eux et le dos de la main ; sur sa photo ils sont serrés l'un contre
l'autre, rangés sous le majeur, en UNE masse continue avec le dos de la main. Trois lots de corrections ; chacun
a démenti un diagnostic du précédent, à garder en tête.

1. **La cause était dans `CONV`, pas dans la peau.** Mesuré sur la peau posée (`scipy.cKDTree`, station par station
   le long de la phalange proximale) : dans le poing, les P1 voisines restaient PARALLÈLES (axes à 1,97 / 1,91 / 1,74
   unité à la MCP et 2,01 / 1,96 / 1,63 à l'IPP) et, le doigt s'amincissant vers l'IPP, l'écart de peau y atteignait
   4,0 mm (index–majeur), 4,2 mm (majeur–annulaire) et 2,0 mm (annulaire–auriculaire) ; en V (2), annulaire–auriculaire
   1,1 à 2,0 mm sur toute la P1. `CONV` tourne le doigt autour de Z : à 90° de flexion c'est l'axe même de la P1,
   donc il oriente P2/P3 (les bouts convergent, comme mesuré à la piste P) mais ne déplace pas la P1 d'un millimètre,
   et `ab` non plus (vérifié à chaud : `ab` = −8 sur l'auriculaire ne change rien). Le relief latéral `KNL` fermait
   la fente à la jointure seulement. L'anatomie dit autre chose : les axes de flexion des MCP sont OBLIQUES, et en
   pliant chaque P1 penche vers l'axe de la main (le majeur). D'où `LEAN` (script.js) : l'axe de flexion de la MCP
   est incliné autour de l'os, comme `tAxis` pour le pouce ; à 90° la P1 pointe vers Z·cos β + lat·sin β, le déport
   vaut hauteur × sin β, nul au repos. Réglé pour le CONTACT et pas pour l'écart nul (la peau est de la chair, pas de
   l'os) : β = −6,5° / 0 / 6,5° / 12° → écarts de peau le long de la P1 (stations ¼ à 1, mm) : V (2)
   annulaire–auriculaire 0,41 / 0,05 / 0,17 ; poing index–majeur 1,3 / 1,4 / 0,6, majeur–annulaire 0,2 / 1,1 / 0,8,
   annulaire–auriculaire 0,2 / 0,2 / 0,1 ; les squelettes ne se chevauchent nulle part (terme 3 de `penetration` = 0
   dans tous les presets). Prix connu : l'obliquité agit dès 20–30° de flexion, donc les poses « molles » bougent aussi
   (Repos : auriculaire 3,2 mm en moyenne, index 1,4 ; C et O : 2 à 4 mm ; Pince : index 2,5 mm) — pas un défaut
   visible, c'est l'anatomie, mais à savoir en comparant deux rendus.
2. **Le budget du solveur était un escalier, puis une pose rangée au plafond.** Le vérificateur du lot 1 a vu la
   pénétration des presets repliés passer de 0,08 à 0,48 et la marionnette perdre de la liberté (V (2), écarter
   l'auriculaire à −8° donnait −2 ; poing, ouvrir l'index à 80° donnait 85,9). Mesuré terme par terme
   (`r2/pen_decomp.py`) : tout vient du terme 1, les BOUTS de l'annulaire et de l'auriculaire posés sur la paume.
   Trois causes, trois corrections :
   - **`palmH` lisait la cellule la plus proche** d'une grille au pas de 8 px, à hauteurs ENTIÈRES : la paume était un
     escalier à marches de 1 px, le budget du solveur est 0,5 px. Écarter l'auriculaire de 2° déplace son bout de
     2 px, change de cellule (hf 51 → 52) et la pénétration saute de 0,00 à 0,92 ; l'annulaire du poing était bloqué à
     `ab` = −3,3 (à −3,0 : +0,61). La liberté de la version précédente (0,42 px de marge) était le hasard de la cellule
     où le bout s'était arrêté. Lecture bilinéaire : la hauteur est continue, le solveur s'arrête là où la chair le veut.
   - **`penetration()` rend le contact le plus profond, pas la somme.** Un bout posé sur la paume consommait le budget de
     la main entière : plus rien pour le pouce ni pour un autre doigt. Deux contacts sont deux contacts.
   - **Une articulation bloquée s'assied à la MOITIÉ du budget (`PEN_SEAT` = 0,25), le geste garde l'autre moitié
     (`PEN_MAX` = 0,5) ; et un bout posé sur la paume GLISSE.** Avec un seul seuil, la pose résolue (l'auriculaire demandé
     à 90° s'arrête à ≈ 76°, bout sur l'hypothénar) était rangée exactement AU PLAFOND, et le geste suivant sur ce doigt
     n'avait plus aucune marge : écarter l'auriculaire de V (2) à −8° donnait −3,5 (son bout monte de 0,6 px sur le bord
     arrondi de l'hypothénar). Quand une articulation d'un doigt (ab, IPP, IPD) est bloquée par ce contact, `solve`
     relâche la MCP du même doigt de ce qu'il faut (≤ `SLIDE` = 4°, le plus petit relâchement trouvé par dichotomie)
     pour que la commande passe entière — c'est ce qu'une main fait : le bout reste posé et glisse. Jamais le pouce
     (ses couplages sont dans `constrain`), jamais plus que `SLIDE`. Mesuré (`verif/probe_solve.py`) : V (2) auriculaire
     ab −8 → −8 (MCP 76,3 → 75,9), annulaire 1,8 → 1,8 (avant : −3,3 bloqué) ; poing, index 80 → 80 ; Y −15 → −15 ;
     Quatre (4), auriculaire fermé avec `ab` 2,3 → 2,3 (avant 8,8, la MCP cède 3,7°). Pénétration des 15 presets :
     ≤ 0,18 (avant 0,08 à 0,42 au hasard des cellules), différence d'angle 0,2° (0,06 mm de peau).
3. **Les pouces « validés » étaient les presets bruts, jamais thumbReach.** Tracé pas à pas (`r2/reach_trace.py`) :
   dans la version précédente, CHAQUE pas de `thumbReach` était rejeté (pénétration 0,77 > 0,5) parce que
   `constrain()` ramenait l'ab de l'annulaire de −3,3 à −3,0 et que ce 0,3° faisait sauter son bout d'une cellule.
   Grille continue, la montée reprenait et trouvait son optimum : V (2) 24,5/35/55/−8 (IP en hyperextension, coût
   1,75 contre 3,05 au preset), Poing serré 11/1,5/39/80 (0,60 contre 1,29), Index (1) 31/18/46/58 — ce que le
   vérificateur a vu au lot 1 et qui n'était PAS dû aux P1 déplacées. Les cibles `REACH` de V (2), Index (1) et
   Poing serré sont retirées : leur pouce est celui du preset (Poing serré validé sur la photo 2357). Mesuré sur les
   15 presets : V (2) 40/35/40/40, Index (1) 40/23,9/40/40, Poing serré 20/0/46/65 identiques à la version
   précédente ; O 33/18/25/27 → 30 et Pince 25,5/27,5/5/15,5 → 8/14 (cibles sur le bout de l'index, qui penche).
4. **Les échardes : le sillon dorsal, puis la coque vue en rasant** (`SILL` = 0,15 → 0 ; coque hors « doigt sur doigt »
   à 2 × push). Diagnostic coloré (passe identité en rouge, coque en bleu puis par CATÉGORIE selon ce qu'elle recouvre,
   `r2/echardes_diag.py`, `r2/hull_cat.py`) : le « trait noir double » entre les deux jointures repliées de V (2) était
   la coque de l'auriculaire posée sur la bande de DOS qui plonge entre les deux jointures, à 2,5 px du trait de contact
   de la passe identité — le sillon sculpté creusait là une rigole dont la coque lisait le fond comme un second contour.
   Le sillon était un creux SCULPTÉ là où, les P1 ne se touchant pas, rien ne faisait d'ombre ; maintenant qu'elles se
   touchent, la jointure fait son propre creux et la passe identité y trace UN trait. Sillon éteint, le « bouquet » qui
   restait au bas de la jointure était la coque des crêtes (même partie, ou paume derrière un doigt) vue en rasant
   par-dessus le fond de la vallée, à 1 à 2 push derrière : elle ne perce que par lambeaux d'un ou deux pixels entre
   les facettes de la peau. Sur le DOS de la main (`rnz` < −0,3, le « dos franc » du nuanceur de peau, passé à la coque
   par l'attribut `rnz`), hors « doigt sur doigt », la coque exige donc 2 × push ; le vrai contour de ces cas-là est
   toujours bien plus loin (un doigt replié devant la paume : 16 mm d'épaisseur). Côté PAUME le seuil reste push :
   mesuré sur 15 presets × 5 vues (pixels de trait perdus image par image), à 2 push partout c'est le bord inférieur
   du pouce sur le THÉNAR qui s'effaçait (V (2) de face 322 px, Quatre (4) 286 — un pli de la paume, même partie, à 1 à
   2 push), et l'excepter par partie ne suffisait pas (209 / 226 : le thénar est « paume ») ; le côté, lui, sépare
   exactement les creux rasants du dos des plis de la paume ; ce qui disparaît encore ailleurs est le bord de coque
   d'un bout de doigt posé sur la paume, dans la bande de 1 à 2 push au ras du contact (Y de face, 115 px ; le trait de
   la passe identité y reste). Mesuré (fenêtre des jointures du vérificateur, dos34, fragments noirs < 120 px /
   pixels dedans, sur les images mêmes des composites) : V (2) 50 / 326 → 18 / 213 (dont UN trait de 117 px à la base
   du majeur, compté parce que juste sous le seuil, et les lambeaux d'une coque « doigt sur doigt » légitime à plus de
   2 push), Index (1) 41 / 161 → 7 / 7, Poing serré 41 / 78 → 13 / 17 ; les jointures du poing se lisent toujours
   (`KNK`, `KNL` inchangés).
   Essayé et écarté, à chiffres égaux ou pires : coque « consciente des jointures » (46 → 59), test corrigé de la
   pente (46 → 69), `EDMAX` 1,0 ou 0,5 (traits tronqués) ; **zone de contact entre deux doigts dans `sep()`** (le côté
   qui trace décidé par l'identité quand |dn − d0| < 0,12 / 0,3 / 0,6 au lieu de 0,02) : 18 → 22 / 19 / 17 fragments en
   V (2), 7 → 10 / 8 / 5 en Index (1) — dans le bruit de mesure (± 3 d'un rendu à l'autre), donc pas touché ; ce qui
   reste en V (2) n'est pas un trait qui clignote mais la coque. La règle « deux échantillons sur douze » (hors pose
   seulement) est GARDÉE, mesurée à sillon nul : V (2) 23 contre 43 avec un seul, Index (1) 24 contre 40, Poing serré
   25 contre 28 ; à trois, les traits se tronquent (V (2) 29).
5. La coque « doigt sur doigt » exige un écart ≥ push (2,6 mm), comme la paume sous un doigt : au contact, c'est la
   passe identité qui trace le trait (seuil 0,02 entre deux doigts).

**`cas_0` et `cas_1` identiques au pixel près** (vérifié : écart max 0). `cas_3` (poing) et `cas_4` (pince) changent :
P1 pressées (annulaire `ab` −3,3 → 0, auriculaire 74,6 → 76,3°), pouces identiques ; `cas_5` (Repos) bouge de 2 à 3 mm
latéralement (obliquité, point 1). Main gauche vérifiée (miroir de la droite). **Balayage (172 poses)** : replis
1 685 → 1 613, froissements 7 627 → 7 666, pincés 19 495 → 19 549, gonflés 7 452 → 8 483, os max 0,0 %, épaisseur
max 13,3 → 15,0 % (lot 1 : 1 819 / 7 911 / 19 629 / 8 281 / 14,6 %). Les 15,0 % sont l'auriculaire SEUL replié à
90/105 (12,5 % avant) : vérifié sur la peau posée, il ne touche pas l'annulaire tendu (12,6 mm d'écart, aucun sommet à
moins de 1,1 mm, dans les deux versions) — c'est l'anneau de peau de sa P1 mesuré dans un plan fixe alors que la P1
tourne désormais autour d'un axe oblique de 12°, pas un doigt plus gros ni une collision. La règle « sillon = min des
deux flexions » du lot 1 est retirée (sans effet à `SILL` = 0).

## Chiffres (leçons de mathématiques)

`PRESETS` contenait déjà « Index (1) » et « V (2) ». Ajoutés : **« Trois (3) »** (pouce + index + majeur),
**« Quatre (4) »** (les quatre doigts, pouce replié en travers de la paume) et **« Main ouverte (5) »**.
Au-delà de 5, les formes varient d'un usage à l'autre : elles ne sont PAS devinées — à poser à la main et à
ranger dans la bibliothèque. Attention : une clé d'objet qui est un entier (`'3'`) est remontée EN TÊTE par
`Object.keys`, donc les boutons apparaissaient avant « Dessin » ; d'où les noms « Trois (3) », etc.

## La planche : référent, deux mains, étapes, flèches, fond (v9)

État (`S`, dans `script.js`) :

```js
S = {
  mode:'pose'|'mouvement',
  mains:'D'|'G'|'DG',      // mains à l'écran      act:'D'|'G'  // main que le panneau manipule
  pose:{D:pose, G:pose},   // mode pose fixe
  cles:[{D:pose,G:pose}…], // mode mouvement : 2 à 5 ÉTAPES CLÉS   cur:index de celle qu'on pose
  etapes:0–3,              // fantômes intermédiaires par intervalle
  fl:{style,sens,double,col}, fond:{type,col,cadre}, ref:{style,t,h,x,visage,reperes}
}
```

- **Deux mains.** La gauche est la droite *dans un miroir* : `mirror(pose)` retourne `pos.x` et le quaternion
  (`x,-y,-z,w`), et l'instance porte `root.scale.x = -1`. Chaque main pleine est créée à la demande (`handOf`),
  ses fantômes aussi (`ghostOf`) : tant qu'on n'affiche qu'une main sans mouvement, rien d'autre n'existe.
  Budget de fantômes : 8 par main, 5 dès qu'il y a deux mains (`MAXG`).
  Conventions d'axes : la droite est en **x négatif**, la gauche en x positif — face au signeur, sa main droite
  est à notre gauche ; vu de dos (« signeur ») l'axe s'inverse tout seul et la droite revient à droite.
- **Étapes clés.** `S.cles` remplace l'ancien couple début/fin. Chaque étape porte une pose COMPLÈTE par main :
  changer de configuration de doigts en cours de mouvement est donc natif. Les fantômes (`ghostList`) sont les
  autres étapes clés (opacité .34) plus `S.etapes` interpolations par intervalle (.17). « Jouer » parcourt
  toute la suite.
- **Deux calques plats** (`#bgL` derrière la 3D, `#fgL` devant) dessinés au canvas 2D. Une flèche de dictionnaire
  LSF est un SYMBOLE, pas un objet de la scène : elle doit rester lisible quel que soit l'angle de la caméra,
  donc elle est tracée à plat. L'export recompose fond → référent → rendu 3D → flèches sur un seul canvas,
  puis recadre sur l'alpha.
- **Référent** : buste de face, proportions données en **longueurs de main** (`HL`, mesurée sur la géométrie au
  repos ; 1 main ≈ 18,5 cm, épaules 2,3 mains, buste 3,7 mains), donc la silhouette reste juste à n'importe quel
  zoom. Ancré au creux du cou, réglable en taille / hauteur / latéral. Option « repères d'emplacement »
  (front, menton, épaules, poitrine, taille) : ce sont les lieux d'articulation du signe.
  **Un personnage, pas un mannequin** (demande de l'utilisateur : « simple, clair, comme un personnage, pas un
  truc de forme géométrique »). La première version était une pile de formes : calotte de cheveux en demi-dôme
  (un casque), cou en tube, tronc en trapèze coupé droit, aucun bras (une cape). Ce qui fait lire un personnage,
  dans l'ordre du papier découpé (`drawRef`) : des BRAS le long du corps, du moignon d'épaule au coude, bout
  arrondi (les avant-bras viennent vers nous — c'est pourquoi les mains flottent devant la poitrine), un cou qui
  part des trapèzes, des OREILLES à moitié cachées par la tête, un tee-shirt (encolure ronde, flancs qui rentrent
  sous l'aisselle, ourlet arrondi), et surtout des CHEVEUX qui ont une forme : une masse qui déborde un peu du
  crâne, des pattes devant les oreilles et une FRANGE à trois festons. Piège : un bras dont le contour dépasse la
  ligne d'épaule (`E`) fait des épaulettes de footballeur — l'épaule du bras reste à `E`. En style « trait », les
  cheveux sont remplis de la couleur du papier pour couvrir le trait du crâne dessous.
- **Flèches** : `arrowPts(A,B,style,sens)` en coordonnées écran — droite, arc, demi-cercle (vrai demi-cercle de
  rayon L/2), vague, zigzag, boucle ; pointe simple ou aller-retour ; quatre couleurs. Les icônes du panneau
  sont générées par la même fonction, donc elles ne peuvent pas mentir. Au-delà de deux étapes, chaque étape
  reçoit une pastille numérotée.
- **Cadrage** (`contentBox` / `fitView` / `fitIfNeeded`) : la vue de départ montre une main plein cadre ; dès qu'on
  ajoute un buste (3,7 mains de haut), une deuxième main ou des étapes écartées, le contenu sort du cadre.
  On recadre **seulement quand il déborde** (ou de force quand on allume le référent, et on restaure la vue
  précédente quand on l'éteint), jamais au milieu d'un geste. Bouton « Cadrer » sur le plateau.
- **Format d'échange v8** : `{version:8, mode, mains, act, pose, cles, cur, etapes, fleche, fl, decor:{fond,ref}, verrous, vue}`.
  `snapshot()` garde À LA FOIS la pose fixe et les étapes : le mode ne dit pas lequel des deux travaux on veut
  conserver, et perdre quatre étapes clés parce qu'on avait repassé la main en « pose fixe » avant d'enregistrer
  serait brutal. `load()` relit les versions 6 et 7 (une main, début/fin) et les convertit.

### Pièges rencontrés sur cette version (relus par une revue multi-axes, puis corrigés)

- **Main en miroir : la normale est DÉJÀ bonne.** `scale.x = -1` : `normalMatrix` est l'inverse transposée de
  modelView ; pour une réflexion (matrice orthogonale de déterminant −1) c'est la matrice elle-même, donc la
  normale est réfléchie comme la position et reste sortante. Une version antérieure croyait l'inverse et mettait
  l'uniforme `nflip` à −1 pour la main gauche : mesuré sur la planche à deux mains, 98 % des pixels de la gauche
  tombaient dans le ton d'ombre (luminance moyenne 81 contre 95 pour la droite). À +1 les deux mains ont la même
  part d'ombre (0,16 / 0,18, luminance 101 / 101). `nflip` reste dans le nuanceur, à +1 ; `mkHand` n'y touche plus.
- **Un seul `gR` pour tout l'écran.** La passe des traits intérieurs est UNIQUE : prendre le maximum des deux mains
  ouvrait le détecteur de plis et épaississait les traits de la main restée au repos, donc « Dessin = dessin exact
  au pixel près » tombait dès qu'on affichait les deux. La passe identité écrit désormais `gR` dans son canal BLEU
  (`idMatProto`, une matière par main) et `edgeMat` le lit par pixel.
- **Boucle de lecture et état partagé.** « Jouer » capturait la longueur de `S.cles` au départ : supprimer une
  étape ou charger une configuration pendant la lecture levait une exception DANS le rappel d'animation, donc ni
  l'image suivante ni le `setTimeout` final n'étaient atteints et `playing` restait à true pour toujours — l'atelier
  gelé, rechargement obligatoire. La boucle relit l'état à chaque image et un `try/catch` rend la main.
- **Ne jamais déplacer ce que l'utilisateur a placé.** `ensureSide` écartait les deux mains en poussant la pose
  EXISTANTE ; en mode mouvement cela rallongeait la course d'une étape sans qu'il l'ait demandé. Seule la main
  nouvellement créée est décalée.
- **Un réglage par intervalle ne doit pas déborder.** `segFl()` retombe sur `S.fl` quand un intervalle n'a pas de
  style propre : écrire dans `S.fl` changeait donc aussi les intervalles qu'on n'avait pas touchés. `flSet` fige
  d'abord le style courant sur tous les intervalles, puis ne modifie que celui qui est visé.
- **Rogner une liste de fantômes, oui ; rogner des étapes clés, non.** Une pastille numérotée sans main dessous ne
  veut rien dire : `ghostList` garde toutes les étapes clés et distribue ce qui reste de budget en tourniquet sur
  les intervalles, pour que le mouvement reste régulier au lieu de ralentir au début et de sauter à la fin.
- **Rendu à la demande : tout ce qui change l'image doit le dire.** `setHL` n'écrivait que des uniformes, donc le
  surlignage au survol ne s'affichait plus (et pouvait s'allumer périmé à la première image suivante). Il appelle
  `repaint()`, et il lit `HAND[S.act]` au lieu de `act()` : `act()` CRÉE la main manquante, donc un simple survol
  pouvait construire un maillage de 44 000 sommets.
- **`for (const k in ensembleD'Étape)`** suppose que toutes les clés sont des côtés de main : depuis les flèches par
  intervalle, un ensemble porte aussi `fl`. On énumère `['D','G']`.
- **Un JSON importé vient de l'extérieur.** Une couleur qui serait un nombre, un style de flèche inconnu, un
  `verrous` qui serait une chaîne : `Object.assign` les laissait passer, et c'est `refresh()` qui levait ensuite
  une exception à CHAQUE clic, pour toujours. `load()` filtre maintenant chaque champ (`vHex`, `vNum`, `vIn`,
  `vBool`, `vFl`), vide les poses incomplètes plutôt que de les laisser « présentes et vides », et n'écrit dans
  `S` qu'une fois TOUT validé : un import refusé ne laisse plus l'atelier à moitié écrasé (il basculait sur
  « les deux mains » au prochain rafraîchissement alors que le message disait « JSON illisible »). Vérifié sur
  sept JSON tordus : l'atelier répond encore après chacun.
- **« Recadrer au plus juste » était inerte dès qu'un fond était choisi** : on peignait le fond EN PREMIER, donc
  tous les pixels étaient opaques et la boîte trouvée était l'image entière. On compose désormais le CONTENU seul
  (référent, 3D, flèches), on mesure son alpha (`alphaBox`, marge égale sur les deux axes), puis on peint le fond
  à la taille de SORTIE — son dégradé et son cadre suivent l'image finale.
- **Export sans filet.** Pas de garde de réentrance ni de `try/finally` : un double clic laissait le plateau au
  `pixelRatio` de l'export (flou à l'écran) et `showModal()` sur une boîte déjà ouverte bloquait le message sur
  « Rendu en cours… ». Le bouton se désactive, tout est dans un `try/finally`, et l'URL d'objet du PNG est
  révoquée (sinon un PNG de 0,5 à 3 Mo restait en mémoire par export).
- **Un point DERRIÈRE l'œil** ne se projette pas en NaN mais en coordonnées retournées : le référent se serait
  dessiné à l'envers et une flèche serait partie à l'autre bout de l'image dès qu'on entre dans la main.
  `devant(v)` teste le z en repère caméra avant de tracer.
- **Plan éloigné à 500.** Un buste à 170 % plus des étapes très écartées peuvent demander davantage, et tout ce
  qui dépasse serait simplement coupé : `fitView` repousse `camera.far` au besoin.
- **Trait de l'ongle en pixels du DESSIN.** De loin ou vu en biais, les 2,4 px de dessin tombaient sous le pixel
  d'écran : le trait se brisait en pointillé et l'ongle devenait une tache claire sans bord. Il garde maintenant au
  moins ~1,25 px d'écran (`max(nailLW, 1.25*fwidth(sd))`), multiplié par le profil en « U » pour que le bord libre
  reste ouvert. Au zoom des rendus de contrôle, `fwidth` < 1,9 : la pose du dessin est inchangée.
  (Depuis la piste N, la largeur est constante à l'écran à tout angle : `nailPx` × `vAw`, voir « Ongles ».)

## Lot 3 — critique finale et corrections (v18)

Trois critiques indépendants (anatomie contre ses photos, artefacts de rendu, régressions et usage) ont relu la
version intégrée. Ce qu'ils ont trouvé de bloquant, et ce qui a été fait :

- **Main gauche à 98 % dans l'ombre** : `nflip = −1` était une erreur de raisonnement (voir le piège corrigé plus
  haut) ; supprimé. Mesuré après : luminance 101 / 101, part d'ombre 0,16 / 0,18 pour les deux mains.
- **Flèches absentes avec trois étapes et le référent** : `drawArrows` sautait tout segment plus court que 7 fois
  la largeur du trait ; à l'échelle du référent, les étapes insérées par défaut sont à un quart d'intervalle et
  tombaient sous ce seuil. Seuil ramené à 3 fois le trait.
- **Deux mains qui se chevauchent avec des étapes** : `ensureSide` écartait la main en miroir d'une distance fixe
  (18) ; avec des étapes, la main droite balaie une plage en x (`span`) et la gauche tombait dedans. L'écart
  tient compte de la plage : `18 + span`.
- **« Cadre » rectangulaire sur le flanc du majeur en vue Profil** (« Index (1) », « L », « Y ») : diagnostiqué à
  tort comme la crête du bombé d'ongle (`NDOME` .17 → .11, `NFOLD` 1.6 → 1.2, `NARC` 1.8 → 2.6 : réglages
  gardés, ils adoucissent le bombé, mais le cadre restait). Isolé en cachant tour à tour la coque, la passe
  identité et le trait d'ongle, puis en coupant le maillage posé (`exp/cadre/`) : c'est **le creux du poing**,
  l'espace fermé par P1, P2, P3 du majeur replié et la paume (1,6 × 1 unité, 1,5 de profondeur), dans lequel on
  regarde de profil ; son rebord est un vrai contour (la coque le trace) et la passe identité ajoutait l'arête
  paroi / fond : un rectangle à double trait. Règle « en retrait » (`rec`) dans `edgeMat` : un pixel qui a une
  surface nettement plus proche (> 1,1 unité) à moins de 0,4 unité est une paroi ou un fond, aucun trait
  intérieur n'en part. Le double trait disparaît ; le rebord reste (défaut connu 0). Une ombre de creux (`pit`,
  `cavA`) a été essayée et laissée éteinte : voir le commentaire du nuanceur.
- **Pouce du poing à côté du poing** : preset `[24, 10, 35, 60]` (piste X, point 4, v18).

Non traité, documenté : les doigts repliés lus comme des tubes séparés côté paume, « Pince » qui ne ferme pas
tout à fait, « O » trop fermé, « Poing (A) » au pouce peu levé, P2 du pouce qui se soulève en « B » et « 4 »,
anneaux de trait en vue Dessus, trait lourd à l'export à l'échelle de la planche.

**Contrôles après le lot** : `cas_0` identique au pixel près, `cas_1` inchangé hors zone des ongles (917 px) ;
aucune erreur JS sur référent, deux mains, étapes, flèches, fond, export ; 15 presets × 4 vues comparés avant /
après : seules les vues du poing changent au-delà de quelques centaines de pixels (le pouce), le reste est des
traits intérieurs retirés dans des creux.

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
  S'y ajoute un **détecteur de plis** (`CRV`, `CRMAX`) : le dessin ne porte que les traits d'une main à PLAT, donc
  rien ne dessine la vallée entre deux doigts repliés qui se touchent. On la lit dans la profondeur — en traversant
  un creux, les DEUX voisins remontent vers l'œil (on prend le plus petit des deux écarts, sinon un bord d'occlusion
  suffirait à déclencher) ; rapporté au pas en unités du modèle c'est la tangente du versant, donc le seuil ne
  dépend ni de la distance ni du zoom. Sur une surface bombée le signe s'inverse : aucun trait parasite sur le
  corps d'un doigt. Comme `mesh.dz`, il n'entre qu'une fois la pose du dessin quittée (`gR`), donc le repos reste
  exact au pixel près. Mesuré : il ajoute des traits sur 54 des 60 vues de contrôle (presets × face/dos/profil/¾),
  surtout dans les crevasses pouce–doigts et entre doigts repliés. **Il ne montre rien sur le dos du poing** : à
  cet endroit la surface est réellement lisse et convexe, le manque est géométrique (pas de relief d'articulation
  ni de sillon inter-doigts côté dos), pas un problème de trait.
- **Marionnette** : la direction écran de chaque articulation est mesurée en la poussant de 3°. Résolution par moindres carrés (`grabAxes` / `onDrag`). Couplage naturel `GRAB` (bout tiré → MCP .85, IPP 1, IPD .7).
- **Configurations de départ** (`PRESETS`) : Dessin, Repos, B, A, Poing serré, 1, V, L, Y, C, O, Pince. Pour O, Pince et Poing serré, `thumbReach` amène le pouce sur sa cible.
- **Bibliothèque** : capacité `db` de claude.ai (`window.claude.use('db')`, collection `configurations`). Hors claude.ai elle est indisponible, et l'échange JSON prend le relais. **Export PNG** : capacité `downloads`, sinon image dans une boîte de dialogue.
- **Débogage** : `window.__atelier` expose `renderer, S, refresh, main, HAND, handOf, act, camera, PRESETS,
  applyPreset, editable, curSet, mirror, penetration, constrain, solve, setPron, setCrv, setCrmax, drawOverlays,
  load, snapshot`. **La pose modifiable n'est plus `S.pose` mais `editable()`** (elle dépend de la main active et
  de l'étape clé en cours) : les scripts de contrôle passent par là.

## Construire et vérifier

```bash
pip install numpy scipy pillow playwright && playwright install chromium
python3 build.py --rig --preview   # régénère la géométrie (≈10 s) + contrôle du recalage
python3 tests/rendu.py             # rendus de contrôle → tests/out/planche.png
python3 tests/balayage.py          # balayage anti-déformation (≈170 poses) → tableau des pires poses
```
**Toujours regarder la planche** avant de livrer : repos face et dos = dessins exacts, majeur levé (doigts serrés, pouce cerné d'un trait), poing serré, pince, gros plan des ongles.

## Défauts connus (à traiter en priorité)
0. *(mesuré et démenti en partie — voir « LE POING SERRÉ (piste X) » : les proportions du doigt replié sont
   justes, le poing n'est pas creux, les bouts touchent la paume. Ce qui reste est le tunnel ci-dessous.)*
   **Creux du poing vu de profil** (`poing_cote`) : à pleine flexion, la boucle phalange 1 / 2 / 3 d'un doigt
   enferme un tunnel, et par ce tunnel on aperçoit les doigts voisins, cernés de traits — cela se lit comme un trou
   rectangulaire. Mesuré : pour l'index replié seul, le tunnel libre fait ≈ 78 × 31 px, alors qu'une vraie main n'en
   laisse qu'une dizaine. Cause : les phalanges moyenne et distale sont trop longues (voir la mesure des doigts) et
   le doigt est trop mince en profil. Le relief des jointures et la correction de tranche l'ont réduit, pas supprimé ;
   il faudra rapprocher les longueurs de 1 : 0,56 : 0,50 pour le fermer.
   *v18 (lot 3)* : remesuré en coupe sur « Index (1) » : 1,6 × 1 unité, 1,5 de profondeur, bords droits (P1, P2,
   P3 sont des tubes droits). Le double trait est parti (règle `rec`), le rebord noir reste : c'est un contour
   légitime autour d'un vrai trou. Pistes : P1 plus charnue (une vraie P1 masque le creux vu de côté), ou une
   ombre de creux lissée (`cavA`, essayée brute : taches déchirées ailleurs).
1. Stries légères sur l'ongle du pouce en pince : le dessin dos colle l'ongle du pouce au contour.
2. La tranche de la main (profil) est déduite, pas dessinée (corrigée en partie, piste D).
3. Quelques traits parasites possibles à la jointure pouce/paume selon l'angle.
4. Le glisser est un peu lent sur machine modeste : `penetration` est appelée plusieurs dizaines de fois par mouvement.
5. Poing vu de profil en très gros plan : il reste un petit jour entre les bouts des doigts et la paume, par lequel
   on voit les doigts du fond ; la passe « identité » y empile des traits épais. La piste P l'a beaucoup réduit
   (les bouts atteignent la paume, la boucle du doigt se referme) mais pas supprimé. Sur la vraie main (photo 2364)
   il n'y a pas de jour du tout.
6. Ongles, croissant d'ombre (piste N) : le croissant se termine côté bord libre par une coupe à ≈ 40° plutôt
   qu'en pointe le long du bord ; à ×6 il se lit comme un éclat sombre dans le coin haut de l'ongle (vérificateur
   du lot 2). Piste : faire décroître sa LARGEUR avec la hauteur (rampe longue sur `ax`) au lieu de le couper.
   Et sur le majeur de « V (2) » en dos ¾ ×3, le rapport des deux bras du U atteint encore 1,5 (index : 1,08-1,25).
7. Vue « Profil », pouce replié : une ombre plus foncée subsiste sous la base du pouce — c'est l'ombre PEINTE du
   dessin du dos le long de l'échancrure, étirée sur la nappe du pli (mesuré : disparaît avec une texture unie).
   Plus de bord rectiligne ni de traits parasites, mais pas « sans tache » ; inévitable sans toucher aux UV.
8. Échardes au contact de deux doigts repliés : divisées par deux à trois (V (2) dos ¾ 50 → 19 fragments,
   Index (1) 41 → 23) mais pas nulles ; un trait doublé pré-existant sur le flanc ulnaire de l'auriculaire reste.

## Publication
La version en ligne est un artifact claude.ai privé, publié depuis Claude. Pour le mettre à jour, republier `dist/atelier-mains-lsf.html` (sans doctype : claude.ai l'ajoute) avec les capacités `db`, `user`, `downloads`.

## v2 (palier « atelier de conception », octobre 2026) — lire `v2/PLAN.md` d'abord

Nouvelle application dans `v2/`, publiée comme `dist/atelier-v2.html` ; la v1 (`source/`, `build.py`, `tests/`,
`dist/atelier-mains-lsf*.html`) n'est PAS modifiée et reste la référence de ce qui précède dans ce fichier.

- **Contrat** : `v2/PLAN.md` (assets M1 → moteur M2 → éditeur M3, personnage M4, intégration M5) ; un journal par
  chantier (`v2/hand`, `v2/engine`, `v2/plate`, `v2/personnage`, `v2/integration` : `JOURNAL.md`), chaque réglage avec
  sa mesure. Lire le journal du chantier avant d'y toucher.
- **Main** : `v2/hand/hand_v2.glb` est une main DROITE (doigts +Y, paume +Z vers la caméra, pouce +X) ; la gauche est
  le miroir x → −x à l'exécution, orientation [x, −y, −z, w], MÊME lumière (fixe dans le repère caméra : l'ombre ne se
  reflète pas). Vérifié : pouce à droite en vue paume pour la D, IoU G / D retournée = 1,000.
- **Construire** : `python3 v2/build.py` → un fichier de ≈ 5 Mo (three.js r128 et GLTFLoader vendus, GLB en base64 dans
  `window.ATELIER_HAND_ASSETS`, polices OFL en base64), `node --check` de chaque script, refus de toute balise externe.
- **Cache des mains** (plate.js) : rendu par le moteur dans un cache d'images ; estimation du coût en ms par mégapixel ;
  un rendu prévu > 50 ms ne se fait jamais pendant un geste et un seul par image au repos ; une main sans image reçoit
  d'abord un aperçu ; à dpr ≥ 1,75 l'écran est rendu sans sur-échantillonnage (÷ 2,6), l'export avec.
- **Reprise v1** : `convertitV1` porte la caméra de la v1 (`vue: {pos, cible}`) dans l'orientation de la main
  (q2 = Qcam⁻¹ · q1) — sans cela une configuration enregistrée « vue signeur » se rouvrait de face. La collection db
  « configurations » de la v1 est lue (jamais écrite) ; la v2 écrit dans « projets ».
- **Expression par étape** : le visage est un paramètre du signe qui change en cours de signe ; gabarit F = un référent
  par étape, chacun son expression.
- **Vérifier** : `v2/tests/integration_*.py` sur la page construite ; toujours regarder
  `v2/tests/out/livraison_v2.png` (gabarit A à deux vraies mains, V (2) v1 / v2 face et dos ¾, poing, pince, ongles,
  D et G côte à côte, gabarit F) avant de livrer.
- **Architecture v2** : l'arbre des dossiers (hand, engine, plate, personnage, integration, tests, build.py) est dans
  `README.md` § « v2 → Architecture » et dans `v2/PLAN.md` § « Architecture » ; chaque dossier a son `JOURNAL.md`.
- **Bibliothèque db v2** : une ligne fait au plus 256 Kio sérialisés (contrat db 0.2.76) ; mesuré en OCTETS (Blob), seuil
  250 000 ; au-delà, les photos partent par la capacité `assets` (id `/_blob/<id>` dans la ligne, relu en data: à
  l'ouverture), sinon la planche est enregistrée sans elles avec un message. `invalid_argument` = ligne refusée (taille),
  jamais un problème de droits (db n'a pas de code « droits »).
- **Publication v2** : republier `dist/atelier-v2.html` avec les capacités `db`, `user`, `downloads`, `assets`.
- **Ce qui reste (v2)** : voir `v2/PLAN.md` § « État d'avancement → Reste » — critique multi-regards puis publication,
  temps à remesurer sur GPU (tous mesurés en rendu logiciel), validations de l'utilisateur (expressions, chiffres 6–10,
  presets « à valider »), défauts résiduels du moteur listés dans `v2/engine/JOURNAL.md` et `v2/integration/JOURNAL.md`.
