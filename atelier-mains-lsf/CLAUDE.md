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
  `KNK` = 0,14 × demi-largeur du segment (× 1,35 à la MCP, dont la tête est plus large et plus saillante ; × 0,7 à
  l'IPD). Direction : −f0 de l'articulation (le côté extenseur), donc exactement −z pour les doigts et oblique pour
  le pouce. Hauteur proportionnelle à la part de course parcourue, donc **nulle au repos : `cas_0` et `cas_1`
  restent exacts au pixel près.** Les deux articulations qui commandent le plus chaque sommet sont retenues au
  chargement, le rafraîchissement n'est qu'une somme de deux produits (+1,3 ms sur `skinMesh`, médiane 13,4 ms).
  `x0`/`y0` de `skinMesh` sont désormais lus dans `pa` et plus dans `MREST`, pour que ce déplacement de base compte
  sur les trois axes. Amplitude réglée AU BALAYAGE (ci-dessous) : à 0,21 et plus la peau du dos se froissait.
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
  **Relevé de référence (170 poses, relief à 0,14)** : replis 1 120, froissements 5 194, pincés 18 258, gonflés
  3 720, allongement d'os max 0,0 %, variation d'épaisseur max 12,0 %. Sans le relief : 1 153 / 5 195 / 18 255 /
  2 959 / 0,0 % / 8,8 %. Le relief ne crée donc NI repli NI froissement NI pincement de plus ; il étire seulement la
  peau du dos, ce qu'une jointure fait vraiment. **L'os ne s'allonge jamais, dans aucune des 170 poses.**
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

- **Main en miroir ⇒ normales à l'envers.** `scale.x = -1` : Three.js retourne bien le sens des faces, mais
  `normalMatrix` est l'inverse TRANSPOSÉE, donc elle retourne aussi la normale. Sans correction la main gauche
  recevait la lumière à l'envers (aplat uniforme, sans modelé) et la repeinte de peau sous l'ongle se déclenchait
  sur la face cachée. Uniforme `nflip` dans le nuanceur de peau, mis à −1 par `mkHand` pour une main gauche.
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
0. **Creux du poing vu de profil** (`poing_cote`) : à pleine flexion, la boucle phalange 1 / 2 / 3 d'un doigt
   enferme un tunnel, et par ce tunnel on aperçoit les doigts voisins, cernés de traits — cela se lit comme un trou
   rectangulaire. Mesuré : pour l'index replié seul, le tunnel libre fait ≈ 78 × 31 px, alors qu'une vraie main n'en
   laisse qu'une dizaine. Cause : les phalanges moyenne et distale sont trop longues (voir la mesure des doigts) et
   le doigt est trop mince en profil. Le relief des jointures et la correction de tranche l'ont réduit, pas supprimé ;
   il faudra rapprocher les longueurs de 1 : 0,56 : 0,50 pour le fermer.
1. Stries légères sur l'ongle du pouce en pince : le dessin dos colle l'ongle du pouce au contour.
2. La tranche de la main (profil) est déduite, pas dessinée (corrigée en partie, piste D).
3. Quelques traits parasites possibles à la jointure pouce/paume selon l'angle.
4. Le glisser est un peu lent sur machine modeste : `penetration` est appelée plusieurs dizaines de fois par mouvement.
5. Poing vu de profil en très gros plan : il reste un petit jour entre les bouts des doigts et la paume, par lequel
   on voit les doigts du fond ; la passe « identité » y empile des traits épais. La piste P l'a beaucoup réduit
   (les bouts atteignent la paume, la boucle du doigt se referme) mais pas supprimé. Sur la vraie main (photo 2364)
   il n'y a pas de jour du tout.

## Publication
La version en ligne est un artifact claude.ai privé, publié depuis Claude. Pour le mettre à jour, republier `dist/atelier-mains-lsf.html` (sans doctype : claude.ai l'ajoute) avec les capacités `db`, `user`, `downloads`.
