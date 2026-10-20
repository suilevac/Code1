/* shaders.js — les nuanceurs du rendu toon de la main v2 (Atelier des mains LSF, chantier M2).
   Pipeline en quatre passes (dossier rendu.md § 7, prototype rendu/demo_v2.py) :
     1. G-pass   : normale vue (RGB) + identité de partie (A) + profondeur (DepthTexture) → cible hors écran
     2. couleur  : aplat + UNE ombre franche (deux marches 1,0 / 0,82), ongles par attribut (distance signée)
     3. coque    : faces arrière extrudées en espace CLIP (largeur constante à l'écran), reculées en profondeur
     4. traits   : quad plein écran (arêtes de profondeur et d'identité lues dans la G-pass) + rubans des plis
   Tout est écrit en GLSL ES 1.0 « compatible » : three.js r128 compile un ShaderMaterial en GLSL ES 3.0 quand le
   contexte est WebGL2 (il ajoute `#define varying in/out`, `texture2D → texture`) ; on profite alors de `flat` pour une
   identité NETTE PAR TRIANGLE (sommet provoquant), sinon (WebGL1) on retombe sur la règle « triangle mixte ignoré » du
   prototype (identité interpolée qui n'est pas un entier → pas d'identité).
   Chaque réglage numérique vit dans engine.js (uniformes), avec la mesure qui l'a fixé. */
(function(){
'use strict';
// identité plate : `flat` en GLSL ES 3.0, interpolée (et testée) en 1.0
const FLAT = `
#if __VERSION__ >= 300
#define PLAT flat
#else
#define PLAT
#endif
`;
const S = {};

/* ---------- 1. G-pass : normale vue + identité ---------- */
// aPart : 0 paume (avec avant-bras, thénar et palmures), 1 pouce, 2 index, 3 majeur, 4 annulaire, 5 auriculaire.
// Alpha = (aPart + 1) / 8 : 0 reste « vide » (fond). 8 bits suffisent, la valeur est exacte.
S.gVertex = FLAT + `
attribute float aPart;
attribute float aY;
attribute vec3 aRayon;
varying vec3 vN;
varying float vY;
varying vec3 vRayon;
PLAT varying float vPart;
void main(){
  vN = normalize(normalMatrix * normal);
  vPart = aPart; vY = aY; vRayon = aRayon;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;
S.gFragment = FLAT + `
uniform float coupeY;
uniform vec4 tJointure;    // par doigt : abscisse le long du rayon au-delà de laquelle la jointure prend son identité
uniform vec3 finJointure;  // (pente, descente max, longueur d'effilement) de la limite basse de la zone (en t)
varying vec3 vN;
varying float vY;
varying vec3 vRayon;       // (u latéral continu entre les rayons, t le long du rayon, poids « dos ») — engine.js, JOINTURES
varying float vMmPx;
PLAT varying float vPart;
void main(){
#ifdef BOUCHON
  // bouchon de la coupe de l'avant-bras : identité 8, aucune arête n'en part (engine.js, Pipeline)
  gl_FragColor = vec4(normalize(vN) * 0.5 + 0.5, 1.0);
  return;
#endif
  if (vY < coupeY) discard;
  float p = vPart;
#if __VERSION__ < 300
  // WebGL1 : un triangle « mixte » (deux parties) a une identité interpolée non entière ; on la marque 7 (inconnue)
  if (abs(p - floor(p + 0.5)) > 0.02) p = 6.0; else p = floor(p + 0.5);
#endif
  // JOINTURES : la peau dorsale de la paume au droit d'une MCP pliée (tête du métacarpien, palmure dorsale, base de la
  // P1) prend l'identité du doigt k = arrondi(u). u est interpolé (lisse) : la frontière entre deux jointures voisines
  // est l'isoligne u = k + ½, le fond de la vallée entre les deux têtes — et non l'escalier des triangles (identité plate)
  float reste = 0.0;
  // (la base dorsale des P1, t < 1,35, suit la même règle : là, la frontière entre la P1 du doigt k et la jointure de
  // k + 1 était l'escalier des triangles de la P1 — dents de 2 à 6 px à ×3 —, elle devient l'isoligne. Mesuré au repos :
  // les sommets dorsaux des P1 sont à |u − k| < ½ de leur rayon, l'identité de leur intérieur ne change pas)
  if ((p < 0.5 || (p > 1.5 && vRayon.y < 1.35)) && vRayon.z > 0.5) {
    float k = clamp(floor(vRayon.x + 0.5), 0.0, 3.0);
    float tj = k < 0.5 ? tJointure.x : k < 1.5 ? tJointure.y : k < 2.5 ? tJointure.z : tJointure.w;
    // limite basse légèrement bombée (plus basse au centre de la tête qu'à la ligne médiane) ; sur les finJointure.z
    // derniers de t avant cette limite, la part « effilement » descend de 1 à 0 : le trait de contact (4a) s'y amincit
    // jusqu'à une pointe, comme un trait de plume, au lieu de finir carré
    float w = abs(vRayon.x - k), tb = max(tj + finJointure.x * (w - 0.5), tj - finJointure.y);
    if (vRayon.y > tb) { p = 2.0 + k; reste = 0.1 + 0.3 * (1.0 - clamp((vRayon.y - tb) / finJointure.z, 0.0, 1.0)); }
  }
  vec3 n = normalize(vN);
  // intérieur (vu par l'ouverture de la manche) : identité 8, sur laquelle la passe d'arêtes ne trace rien (un aplat
  // sombre, bordé par le seul trait de l'ouverture)
  if (!gl_FrontFacing) { gl_FragColor = vec4(-n * 0.5 + 0.5, 1.0); return; }
  // alpha = (identité + 1 + reste) / 8 : le décodage floor(a·8 + ½) rend la même identité (reste < ½). Le reste marque
  // les pixels de JOINTURE (≥ 0,1 ; 3 pas de 8 bits au-dessus de 0) et porte l'effilement de la fin de la vallée (0,1 →
  // 0,4, 10 pas) ; ailleurs il est nul et l'alpha est celui d'avant au bit près
  gl_FragColor = vec4(n * 0.5 + 0.5, (p + 1.0 + reste) / 8.0);
}`;

/* ---------- passe de sélection (marionnette) : os dominant + partie ---------- */
S.pickVertex = FLAT + `
attribute float aPart;
attribute float aOs;
attribute float aY;
varying float vY;
PLAT varying float vPart;
PLAT varying float vOs;
void main(){
  vPart = aPart; vOs = aOs; vY = aY;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;
S.pickFragment = FLAT + `
uniform float coupeY;
varying float vY;
PLAT varying float vPart;
PLAT varying float vOs;
void main(){ if (vY < coupeY) discard; gl_FragColor = vec4((floor(vOs + 0.5) + 1.0) / 32.0, (floor(vPart + 0.5) + 1.0) / 8.0, 0.0, 1.0); }`;

/* ---------- 2. couleur : toon deux marches + ongles ---------- */
// La lumière est FIXE dans le repère caméra (−0,45 ; 0,55 ; 1), comme la v1 : la main gauche (miroir, scale.x = −1)
// reçoit la même lumière, normalMatrix réfléchit déjà la normale (CLAUDE.md, piège « nflip »).
S.toonVertex = FLAT + `
attribute float aPart;
attribute float aBiais;
attribute float aOngle;
attribute vec2 aMasque;
attribute float aY;
attribute float aSurvol;
varying float vSurvol;
varying vec3 vN;
varying vec3 vV;
varying float vBiais;
varying float vOngle;
varying vec2 vMasque;
varying float vY;
varying float vMmPx;
uniform vec2 res;
uniform float ortho;
PLAT varying float vPart;
void main(){
  vN = normalize(normalMatrix * normal);
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vV = -mv.xyz;
  vBiais = aBiais; vOngle = aOngle; vMasque = aMasque; vPart = aPart; vY = aY; vSurvol = aSurvol;
  // millimètres de peau par pixel, calculés AU SOMMET (lisses d'un sommet à l'autre) : le raccourci de la surface
  // (|n.z|, plafonné à 0,3) × la taille d'un pixel. fwidth(sd) au fragment change d'un bloc 2 × 2 à l'autre et
  // pointillait le trait au repli de l'ongle (v1 avait fait le même constat : « vAw »)
  float cmPx = 2.0 * (ortho > 0.5 ? 1.0 : -mv.z) / (projectionMatrix[0][0] * res.x);
  vMmPx = 10.0 * cmPx / max(abs(vN.z), 0.3);
  gl_Position = projectionMatrix * mv;
}`;
S.toonFragment = FLAT + `
uniform vec3 L;            // lumière, repère caméra, normalisée
uniform float seuil;       // N·L où bascule l'ombre franche
uniform float lisiere;     // demi-largeur minimale de la lisière (en N·L), sinon fwidth
uniform float tonOmbre;    // 0,82 : ton de l'ombre du dessin
uniform float ombreOn;     // 1 = ombre franche, 0 = aplat seul (style.ombre = false)
uniform vec3 peau;
uniform vec3 ongle;
uniform vec3 trait;
uniform float frange;      // mélange vers le blanc de la frange libre (0,45 : ×1,35 plus claire, photo)
uniform float onglePx;     // largeur du trait d'ongle, px de la cible
uniform float plancherPx;  // plancher de tout trait (1,25 px de l'image finale, × sur-échantillonnage)
uniform float ongleMaxMm;  // plafond du trait d'ongle en mm de peau (ongle vu de chant : la lamelle reste lisible)
uniform float ortho;
uniform float hlPart;      // partie survolée (marionnette), −10 = aucune
uniform float debug;       // 1 = chaque passe dans sa couleur (diagnostic des traits, tests)
uniform float bandeOn;     // 1 = trait d'ongle peint ici ; 0 = il passe par la couche des traits (nettoyée)
uniform float coupeY;      // coupe de l'avant-bras (repère de liaison, cm)
uniform sampler2D tCreux;  // creux fermés (passe 4c)
uniform float creuxOn;
uniform float cmPx;        // cm par pixel de la cible (orthographique)
uniform vec2 res;
varying vec3 vN;
varying vec3 vV;
varying float vBiais;
varying float vOngle;
varying vec2 vMasque;
varying float vY;
varying float vMmPx;
varying float vSurvol;
PLAT varying float vPart;
void main(){
#ifdef BOUCHON
  // bouchon : le ton CLAIR de la peau, sans ombre ni trait — il se fond avec l'avant-bras éclairé (la coupe se lit comme
  // la fin d'un dessin, pas comme l'ouverture d'un gant) ; dans la couche des traits il n'écrit que sa profondeur
#ifdef COUCHE_TRAITS
  gl_FragColor = vec4(0.0);
#else
  gl_FragColor = vec4(peau, 1.0);
#endif
  return;
#endif
  if (vY < coupeY) discard;
  vec3 n = normalize(vN);
  if (!gl_FrontFacing) {   // intérieur de la manche : le ton d'ombre, un cran plus sombre (une manche vue par son ouverture)
    gl_FragColor = vec4(peau * tonOmbre * 0.86, 1.0);
    return;
  }
  vec3 v = ortho > 0.5 ? vec3(0.0, 0.0, 1.0) : normalize(vV);
  float nl = dot(n, L);
  float t = seuil + vBiais;
  float f = max(lisiere, fwidth(nl));
  float lit = smoothstep(t - f, t + f, nl);
  // ongle : la distance signée (mm, > 0 dedans) est continue et lisse → un bord net à tout grossissement
  float sd = vOngle;
  float fw = max(fwidth(sd), 1e-4);
  float dedans = smoothstep(-0.5 * fw, 0.5 * fw, sd);
  // frange libre : vMasque.y est une DISTANCE continue au bord frange / tablette (cm, > 0 sur la frange ; engine.js,
  // « FRANGE LIBRE »), seuillée sur un pixel comme la distance signée de l'ongle → bord net et lisse à tout grossissement
  // (avec le masque 0/1 de M1, le bord suivait les triangles : escalier de ≈ 130 px sur une main de 4 600 px)
  float ffw = max(fwidth(vMasque.y), 1e-5);
  float fr = smoothstep(-0.5 * ffw, 0.5 * ffw, vMasque.y);
  vec3 base = mix(peau, ongle, dedans);
  base = mix(base, mix(base, vec3(1.0), frange), dedans * fr);
  // fond d'un creux fermé (4c) : dans l'ombre, un cran plus sombre (le jour n'y entre pas)
  // (passe calculée à demi-résolution, lue filtrée : le bord du creux s'adoucit sur un pixel au lieu de faire des marches)
  // … et LISSÉE sur un disque de 2 mm (13 lectures, moyenne puis seuil à mi-hauteur) : la décision « 7 directions sur 8 »
  // fait des dents et des lambeaux de quelques pixels qui, aux grands rendus (export A3, gros plans de 1 800 px), se
  // lisaient comme des plaques d'ombre déchirées en escalier (relecture M5) ; le seuil d'une moyenne arrondit le bord et
  // efface ce qui est plus étroit que le disque, comme une ombre portée dessinée
  float creux = 0.0;
  if (creuxOn > 0.5) {
    vec2 uv0 = gl_FragCoord.xy / res;
    float rb = (ortho > 0.5 ? 0.2 / cmPx : 3.0) / res.x;
    float sm = texture2D(tCreux, uv0).r;
    for (int i = 0; i < 6; i++) {
      float a = float(i) * 1.0471976;
      vec2 o = vec2(cos(a), sin(a) * res.x / res.y) * rb;
      sm += texture2D(tCreux, uv0 + o).r + texture2D(tCreux, uv0 + 0.5 * o).r;
    }
    creux = smoothstep(0.4, 0.6, sm / 13.0);
  }
  lit *= 1.0 - creux;
  vec3 c = base * mix(mix(1.0, tonOmbre, ombreOn), 1.0, lit) * mix(1.0, 0.86, creux);
  // trait d'ongle : bande centrée sur le bord (sd = 0), largeur constante À L'ÉCRAN (fwidth de sd = mm par pixel),
  // plafonnée en mm quand l'ongle est vu de chant (sinon le trait mange la lamelle), jamais sur la frange libre
  float ndv = abs(dot(n, v));
  float wpx = max(onglePx * mix(0.6, 1.0, smoothstep(0.15, 0.6, ndv)), plancherPx);
  float fv = vMmPx;
  float demiMm = min(0.5 * wpx * fv, ongleMaxMm);
  // sous le plancher (plafond en mm atteint, ongle vu de biais), la bande garde le plancher et s'éclaircit au lieu de se
  // briser en pointillé noir (mesuré : en vue de profil et en plongée, un filet de 1 à 2 px de cible entre la frange et
  // la tablette donnait 1 à 4 points noirs par ongle — 104 des 147 « fragments » de la planche des 96 vues)
  float aB = clamp(2.0 * demiMm / (fv * plancherPx), 0.0, 1.0);
  demiMm = max(demiMm, 0.5 * plancherPx * fv);
  float bande = aB * (1.0 - smoothstep(demiMm - 0.5 * fv, demiMm + 0.5 * fv, abs(sd)));
  // pas de trait sur la frange : il s'éteint sur les 0,4 mm qui la précèdent (l'ancien masque interpolé s'éteignait sur
  // un triangle, ≈ 0,6 mm ; 0,4 mm garde le « U » ouvert au bord libre sans couper ses bras plus tôt). Vu de dessus ou
  // en plongée, le bras du « U » longe alors le contour jusqu'au coin de la frange : la mesure des échardes en compte
  // 3 sur 104 vues (regardé ×6 : un filet d'ongle, pas un éclat ; 0,8 mm ne change rien au compte)
  bande *= 1.0 - smoothstep(-0.04, 0.0, vMasque.y);
  // le zéro de la distance signée n'est un bord d'ongle que près de l'ongle (masque interpolé ≈ 0,5 sur le bord) :
  // ailleurs le champ peut frôler 0 sur un flanc et laisser des points noirs de 1 à 3 px
  bande *= smoothstep(0.05, 0.25, vMasque.x);
  // ongle vu par la tranche (N·V < 0,3) : la bande se brisait en points de 1 à 3 px au ras de la silhouette (12 à 20 par
  // vue de ¾) ; là, c'est le contour qui dessine le bord
  bande *= smoothstep(0.12, 0.3, ndv);
  c = mix(c, debug > 0.5 ? vec3(0.8, 0.1, 0.8) : trait, bande * bandeOn);
#ifdef COUCHE_TRAITS
  // passe « couche des traits » : seule la bande d'ongle, en alpha ; la profondeur s'écrit partout (occlusion)
  gl_FragColor = vec4(bande, 0.0, bande, bande);
  return;
#endif
  if (hlPart > -5.0) c = mix(c, vec3(1.0), 0.16 * smoothstep(0.4, 0.6, vSurvol));
  gl_FragColor = vec4(c, 1.0);
}`;

/* ---------- 3. coque inversée : contour de largeur constante à l'écran ---------- */
// Extrusion en espace clip (× w : indépendante de la profondeur ; / résolution : en pixels), normale aplatie dans le
// plan de l'écran (n.z = 0 : pas de « griffe » au bout des doigts), coque RECULÉE de `recul` cm (rendu.md § 2.1 :
// 0,25 u ≈ 2,7 mm efface les griffures des sillons sans toucher la silhouette).
S.hullVertex = `
uniform float px;
uniform vec2 res;
uniform float recul;
attribute float aY;
varying float vY;
void main(){
  vY = aY;
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  mv.z -= recul;
  vec4 clip = projectionMatrix * mv;
  vec3 n = normalize(normalMatrix * normal);
  n.z = 0.0;
  vec2 cn = (projectionMatrix * vec4(n, 0.0)).xy;
  float l = length(cn);
  vec2 dir = l > 1e-6 ? cn / l : vec2(0.0);
  clip.xy += dir * px * clip.w * 2.0 / res;
  gl_Position = clip;
}`;
// La coque ne trace que la SILHOUETTE (là où la G-pass ne voit aucune peau) : un recouvrement intérieur (doigt devant la
// paume, pouce devant les doigts) est l'affaire de la passe d'arêtes, au poids 0,7 (rendu.md § 4 : contour 1, contact
// 0,7). Mesuré sur le poing vu de face : la coque pleine cernait chaque doigt replié d'un trait de contour (les « boudins
// cernés » reprochés à la v1, piste Z) ; et elle ne peut plus percer dans les sillons (« griffures »).
S.hullFragment = `
uniform vec3 trait;
uniform float debug;
uniform float masque;      // 1 = masque d'encre (render() : nettoyage final de l'image)
uniform sampler2D tG;
uniform vec2 res;
uniform float coupeY;
varying float vY;
void main(){
  if (vY < coupeY) discard;
  // jetée sous la peau, mais elle DÉBORDE d'un pixel sous son bord : la peau (passe couleur, dessinée après, devant)
  // la recouvre ; dans la marionnette (multi-échantillonnage du canvas, G-pass sans), le pixel du bord n'était couvert
  // qu'en partie par la peau et ni par la coque, d'où un liseré clair d'un pixel entre le contour et la peau (relecture)
  vec2 uv = gl_FragCoord.xy / res, t1 = 1.0 / res;
  if (texture2D(tG, uv).a > 0.01 && texture2D(tG, uv + vec2(t1.x, 0.0)).a > 0.01 && texture2D(tG, uv - vec2(t1.x, 0.0)).a > 0.01 &&
      texture2D(tG, uv + vec2(0.0, t1.y)).a > 0.01 && texture2D(tG, uv - vec2(0.0, t1.y)).a > 0.01) discard;
  gl_FragColor = masque > 0.5 ? vec4(1.0) : vec4(debug > 0.5 ? vec3(0.1, 0.2, 0.9) : trait, 1.0);
}`;

/* ---------- 3b. bord de la manche : la coque de l'anneau de coupe ---------- */
// Quand l'ouverture de l'avant-bras regarde la caméra, le bord de la coupe EST la silhouette, mais la coque (jetée sous
// la coupe) n'y laissait qu'un filet : mesuré à 30 px/cm, 2,0 à 2,8 px au bas des vues « dos ¾ » contre 4,0 à 4,5 px
// partout ailleurs (contour attendu 4,56 px). Une bande de px pixels extrudée depuis l'anneau de coupe vers l'extérieur,
// là où la G-pass ne voit pas de peau.
S.bordVertex = `
attribute float aCote;
attribute vec3 aAutre;
uniform float px;
uniform vec2 res;
uniform vec3 centreBord;
uniform float fBord;
uniform vec3 axeBord;      // axe de l'avant-bras posé, vers l'extérieur (repère du modèle)
uniform float fAxe;        // 1 = coupe vue par la tranche (face, paume, dos, profils) : bande tirée le long de l'axe
void main(){
  mat4 pm = projectionMatrix * modelViewMatrix;
  vec4 clip = pm * vec4(position, 1.0), c1 = pm * vec4(aAutre, 1.0), cc = pm * vec4(centreBord, 1.0);
  vec2 s0 = clip.xy / clip.w * res, s1 = c1.xy / c1.w * res, sc = cc.xy / cc.w * res;
  vec2 tg = s1 - s0;
  float l = length(tg);
  tg = l > 1e-6 ? tg / l : vec2(1.0, 0.0);
  // perpendiculaire au BORD à l'écran, tournée vers l'extérieur de l'anneau (la normale de la peau, projetée, longe le
  // bord au lieu de le traverser : mesuré, une bande de 2 px au lieu de 4,5) ; chaque segment déborde de 0,15 px × sa
  // largeur aux deux bouts pour couvrir les coins entre segments
  vec2 pp = vec2(-tg.y, tg.x);
  if (dot(pp, s0 - sc) < 0.0) pp = -pp;
  // coupe vue PAR LA TRANCHE (relecture M5 : « la coupe de l'avant-bras reste ouverte et sans trait en vue de face ou de
  // paume ; sur les planches à référent les mains se terminent par un bord droit sans contour et se lisent comme des
  // gants posés ») : l'anneau s'aplatit en un segment ; chaque morceau est alors tiré le long de l'AXE de l'avant-bras
  // projeté (vers le bas de la coupe), et leur réunion est une bande de la largeur du contour SOUS la coupe, qui rejoint
  // le contour des flancs (la perpendiculaire de chaque morceau, elle, partait dans tous les sens : frange en dents de
  // scie, d'où l'ancienne coupe ouverte). Relais avec l'anneau vu par l'ouverture de |dz| 0,12 à 0,35.
  vec2 ax = (pm * vec4(axeBord, 0.0)).xy * res;
  float la = length(ax);
  if (la > 1e-6 && fAxe > 0.0) pp = normalize(mix(pp, ax / la, fAxe));
  // (morceaux prolongés de ½ contour aux deux bouts en vue par la tranche : la bande rejoint les flancs sans encoche)
  vec2 d = aCote * pp - (0.15 + 0.5 * fAxe) * tg;
  clip.xy += d * max(fBord, fAxe) * px * clip.w * 2.0 / res;
  gl_Position = clip;
}`;
S.bordFragment = `
uniform vec3 trait;
uniform float debug;
uniform float masque;
uniform sampler2D tG;
uniform vec2 res;
void main(){
  if (texture2D(tG, gl_FragCoord.xy / res).a > 0.01) discard;
  gl_FragColor = masque > 0.5 ? vec4(1.0) : vec4(debug > 0.5 ? vec3(0.9, 0.5, 0.1) : trait, 1.0);
}`;

/* ---------- 4a. arêtes en espace écran ---------- */
// Lit la G-pass. Un pixel de la main devient trait si, sur un anneau de rayon r px (12 directions), AU MOINS DEUX
// échantillons (règle v1 contre les échardes) voient :
//  - un saut de profondeur vers l'arrière que la pente locale n'explique pas (test SYMÉTRIQUE : sur une surface inclinée
//    continue, d − d0 ≈ d0 − dq ; au bord d'une occlusion le côté opposé reste continu), seuil × (1 + k(1 − |n.z|)) ;
//  - une autre partie (identité) derrière : saut ≥ porte × seuil entre la paume et un doigt (sinon la racine des doigts
//    tendus serait soulignée) ;
//  - TRAIT DE CONTACT entre deux doigts différents (pouce compris) : SANS porte de profondeur, centré sur la frontière
//    d'identité et tracé par les deux côtés sur un anneau de rContact ≈ ½ r (voir plus bas).
// Le fond (alpha 0) est ignoré : la silhouette est l'affaire de la coque.
S.edgeVertex = `
varying vec2 vUv;
void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;
S.edgeFragment = `
uniform sampler2D tG;
uniform sampler2D tD;
uniform vec2 texel;
uniform float r;
uniform float dThr;
uniform float dGraze;
uniform float porte;
uniform float porteDoigts;
uniform float rContact;    // px de la cible : demi-anneau du trait de contact entre deux doigts (≈ ½ r)
uniform float ortho;
uniform float cn;
uniform float cf;
uniform float cmPx;        // cm par pixel de la cible (orthographique) ; en perspective : à la profondeur 1
uniform float continuite;  // 1 = veto des sauts de profondeur expliqués par les normales (voir plus bas)
uniform sampler2D tCreux;
uniform float creuxOn;
uniform float presFond;    // 1 = aucun trait intérieur à moins de r du fond
uniform float fonduFond;   // 1 = trait intérieur fondu entre r et 2r du fond
uniform float enveloppe;   // n.z sous lequel un flanc lointain tourné vers l'extérieur prolonge le volume proche
uniform vec3 trait;
uniform float debug;
varying vec2 vUv;
float lin(float d){
  if (ortho > 0.5) return cn + d * (cf - cn);
  float z = d * 2.0 - 1.0;
  return 2.0 * cn * cf / (cf + cn - z * (cf - cn));
}
void main(){
  vec4 g0 = texture2D(tG, vUv);
  if (g0.a < 0.01) discard;
  float d0 = lin(texture2D(tD, vUv).r);
  vec3 n0 = g0.rgb * 2.0 - 1.0;
  float thr = dThr * (1.0 + dGraze * (1.0 - abs(n0.z)));
  float id0 = floor(g0.a * 8.0 + 0.5);
  if (id0 > 7.5) discard;                 // intérieur de la manche : aucun trait dessus
  float cnt = 0.0;
  float cpx = ortho > 0.5 ? cmPx : cmPx * d0;
  for (int i = 0; i < 12; i++) {
    float a = float(i) * 0.5235988;
    vec2 o = vec2(cos(a), sin(a)) * r * texel;
    vec4 g = texture2D(tG, vUv + o);
    // à moins de r du fond, c'est la coque qui trace la silhouette : un trait intérieur ici n'est que l'écho du contour
    // (surface rasante au bord : la pente fait un faux saut) — mesuré : ≈ 15 « échardes » < 20 px par vue sur les flancs
    if (g.a < 0.01) { if (presFond > 0.5) discard; continue; }
    if (creuxOn > 0.5 && texture2D(tCreux, vUv + o).r > 0.5) continue;   // le bord d'un creux fermé n'est pas cerné (4c)
    float d = lin(texture2D(tD, vUv + o).r);
    vec4 gq = texture2D(tG, vUv - o);
    float dq = gq.a < 0.01 ? d0 : lin(texture2D(tD, vUv - o).r);
    float e = 0.0;
    float id = floor(g.a * 8.0 + 0.5);
    // l'un des deux pixels est une JOINTURE (reste de l'alpha ≥ 0,1, G-pass)
    bool jointure = g0.a * 8.0 - id0 > 0.05 || g.a * 8.0 - id > 0.05;
    if (d - d0 > thr && (d - d0) - (d0 - dq) > 0.7 * thr) {
      e = 1.0;
      // CONTINUITÉ (relecture adverse : doubles anneaux noirs autour des bouts des doigts vus de face, « vue dessus ») :
      // dans une MÊME partie, une marche de profondeur que les NORMALES des deux pixels expliquent n'est pas une
      // occlusion mais une surface qui tourne (le dôme de la pulpe qui rejoint le flanc rasant du doigt vu par le bout ;
      // l'« écho » du contour sur un flanc). Pente de la profondeur le long de o d'après une normale vue n :
      // (n.x·o.x + n.y·o.y) / n.z ; une surface continue a sa marche entre les deux pentes (valeurs moyennes), une
      // occlusion la dépasse. n.z plafonné à 0,08 (pente 12,5 : un flanc vu à 5° du rasant).
      // … et entre une JOINTURE et ce qui l'entoure (reste de l'alpha ≥ 0,1, voir la G-pass) : c'est la même peau,
      // continue, dont seule l'identité a changé — sans cela le veto tombait et la peau des têtes vue en rasant se
      // hachurait de tirets (O en dos ¾, Y de profil)
      if (continuite > 0.5 && (id == id0 || id > 7.5 || jointure)) {
        vec3 n1 = g.rgb * 2.0 - 1.0;
        vec2 u = vec2(cos(a), sin(a)), oc = u * r * cpx;
        float s0 = dot(n0.xy, oc) / max(n0.z, 0.08), s1 = dot(n1.xy, oc) / max(n1.z, 0.08);
        if (d - d0 < max(s0, s1) + 0.5 * thr) e = 0.0;
        // ENVELOPPE : le pixel proche tourne déjà dans la direction o (bord convexe) et le pixel lointain est une
        // surface RASANTE tournée vers l'extérieur le long de o — c'est la suite du même volume vu par la tranche (le
        // flanc d'un doigt vu par le bout, n.z ≈ 0, dont la pente dépasse ce que 8 bits de normale savent dire), pas
        // un objet derrière ; un fond quelconque n'a ce signe que par hasard
        if (dot(n0.xy, u) > 0.2 && n1.z < enveloppe && dot(n1.xy, u) > 0.6) e = 0.0;
      }
    }
    if (id != id0 && id < 6.5 && id0 < 6.5) {
      // deux doigts (pouce compris) : ni la marche de profondeur ni la porte ne décident — c'est le trait de contact
      // centré, compté à part (cntC) ; paume / doigt : porte de profondeur (la racine d'un doigt tendu reste sans trait)
      if (id0 > 1.5 && id > 1.5) e = 0.0;   // (identités lues + 1 : paume 1, pouce 2, doigts 3 à 6)
      // jointure / paume : la même peau continue (seule l'identité change) — ni porte ni trait ; une vraie occlusion y
      // reste tracée par la marche de profondeur (plus haut, si les normales ne l'expliquent pas)
      else if (jointure) {}
      else if (d - d0 > porte * thr) e = 1.0;
    }
    cnt += e;
  }
  // TRAIT DE CONTACT entre deux doigts différents (pouce compris), rétabli comme en v1 (CLAUDE.md, passe identité : un
  // trait sépare TOUJOURS deux doigts, même collés, même sans marche de profondeur). Grief de l'utilisateur (20 octobre,
  // « L » vu de dos : « des doigts qui se fondent dans la main, tu ne vois même plus les traits de chaque doigt »).
  // L'ancienne règle faisait tracer UN côté, choisi par la profondeur juste de part et d'autre de la frontière (porte
  // 2,5 mm, fondu jusqu'à 5 mm) : là où l'écart de profondeur passait la porte le long d'un contact, le trait sautait
  // d'un côté de la frontière à l'autre (un cran de r px). Ici le trait est CENTRÉ sur la frontière : chaque côté
  // compte les échantillons d'une autre identité de doigt sur un anneau de rContact (≈ ½ r) et trace sa moitié ; les
  // deux moitiés sont symétriques par construction, donc le trait est continu, d'épaisseur constante (≈ celle de
  // l'ancien trait d'un seul côté sur r : bande où le compte dépasse 1 à 3 sur 12, ≈ 0,84 × l'anneau de chaque côté),
  // et sa place ne dépend ni de la profondeur ni de l'ordre des identités. Le fond est ignoré (la coque fait la
  // silhouette), le fond d'un creux fermé aussi (4c).
  float cntC = 0.0, cntP = 0.0;
  // effilement du pixel (G-pass : reste de l'alpha d'identité, 0 hors de la fin d'une vallée) : l'anneau se resserre
  // jusqu'à 0,25 × rContact, le trait s'amincit vers sa pointe
  float rC = rContact * mix(0.25, 1.0, 1.0 - clamp((g0.a * 8.0 - id0 - 0.12) / 0.26, 0.0, 1.0));
  // 12 directions : 24 ne changent rien de visible (pointe du trait comparée à ×9, jointures du poing en dos ¾ à ×3)
  if (id0 > 1.5) for (int i = 0; i < 12; i++) {
    float a = float(i) * 0.5235988;
    vec2 o = vec2(cos(a), sin(a)) * rC * texel;
    vec4 g = texture2D(tG, vUv + o);
    if (g.a < 0.01) {
      // JOUR ÉTROIT entre deux doigts collés (B en dos ¾ : 1 à 2 px de fond entre majeur et annulaire sur une partie du
      // contact) : la coque n'y noircit que le jour lui-même ; si l'autre doigt est juste au-delà (à 2 × rC), le jour
      // fait partie du contact et le trait garde son épaisseur (sinon il se pinçait à 2,1 px pour 3,2 à la transition)
      float idj = floor(texture2D(tG, vUv + 2.0 * o).a * 8.0 + 0.5);
      if (idj != id0 && idj > 1.5 && idj < 6.5) cntC += 1.0;
      continue;
    }
    if (creuxOn > 0.5 && texture2D(tCreux, vUv + o).r > 0.5) continue;
    float id = floor(g.a * 8.0 + 0.5);
    if (id != id0 && id > 1.5 && id < 6.5) {
      // ANTI-LAMELLE (vues de profil et en rasant : la jointure du majeur qui dépasse de 1 à 2 px derrière celle de
      // l'index, l'entre-deux des racines vu par la tranche — le trait centré soulignait ces lamelles en tirets : 4 → 11
      // échardes sur 12 presets × 4 vues). L'échantillon ne compte que si l'autre doigt est ÉPAIS (à 2 × rC ce n'est
      // toujours pas moi) et si je ne suis pas moi-même une lamelle (à l'opposé, ce n'est pas ce même autre doigt).
      // Deux doigts qui se touchent vraiment ont, de part et d'autre de la frontière, bien plus de 2 × rC (≈ 1 mm) ;
      // une lamelle est laissée à la marche de profondeur (plus haut), comme avant.
      float id2 = floor(texture2D(tG, vUv + 2.0 * o).a * 8.0 + 0.5);
      float idq = floor(texture2D(tG, vUv - o).a * 8.0 + 0.5);
      if (id2 != id0 && idq != id) cntC += 1.0;
    }
    else if (id < 1.5) cntP += 1.0;
  }
  // FIN DU TRAIT : là où le contact rejoint la paume (bas de la vallée entre deux jointures, où un coin de paume s'ouvre
  // entre elles ; fond d'une commissure), chaque moitié du trait longeait son bord du coin et la fin se fendait en deux
  // pointes (« queue de poisson », vue ×3). Le trait s'éteint avec la part de l'anneau qui voit la paume : une seule
  // pointe, effilée sur ≈ rContact
  float aC = smoothstep(1.0, 3.0, cntC) * clamp(1.0 - cntP / 4.0, 0.0, 1.0);
  // au moins deux échantillons sur douze (règle v1 contre les échardes), mais en fondu de 1 à 3 : le bord de la bande
  // de trait, où le compte hésite d'un pixel à l'autre, s'adoucit au lieu de hachurer
  if (cnt < 1.0 && aC < 0.01) discard;
  float aCnt = max(smoothstep(1.0, 3.0, cnt), aC);
  // FONDU près de la silhouette : à moins de r du fond le trait intérieur est jeté (la coque trace le contour) ; entre
  // r et 2r il entre PROGRESSIVEMENT (distance au fond estimée sur 4 anneaux de 8 directions, au quart de r). Avec la
  // seule coupure à r, un doigt vu de biais derrière un autre, dont il ne reste qu'une lamelle de l'ordre de r entre le
  // trait de recouvrement et le contour, faisait un second filet EN TIRETS parallèle au contour (la lamelle passe d'un
  // pixel à l'autre au-dessus et au-dessous de r) — relecture adverse, « second filet parallèle au contour »
  float fondu = 1.0;
  if (fonduFond > 0.5) for (int k = 1; k <= 4; k++) {
    float rk = r * (1.0 + 0.25 * float(k));
    float vu = 0.0;
    for (int j = 0; j < 8; j++) { float b = float(j) * 0.7853982 + 0.3926991; vu += step(texture2D(tG, vUv + vec2(cos(b), sin(b)) * rk * texel).a, 0.01); }
    if (vu > 0.5) { fondu = min(fondu, 0.25 * float(k) - 0.125); }
  }
  fondu *= aCnt;
#ifdef COUCHE_TRAITS
  gl_FragColor = vec4(fondu, 0.0, 0.0, fondu);
#else
  gl_FragColor = vec4(debug > 0.5 ? vec3(0.9, 0.1, 0.1) : trait, fondu);
#endif
}`;

/* ---------- 4b. rubans des plis : courbes attachées au maillage ---------- */
// Chaque point d'un pli est une position barycentrique sur un triangle de la peau (hand_v2.json « plis »), recalculée
// après le skinning ; le ruban est extrudé en espace clip perpendiculairement à la courbe À L'ÉCRAN (largeur constante),
// décollé de la surface de `decolle` cm (Spider-Verse, rendu.md § 2.4) et testé en profondeur contre la peau.
// aW (calculé sur le CPU) = poids du type × visibilité articulaire × effilement aux bouts ; N·V éteint le ruban vu de dos
// et l'amincit en rasant.
S.rubanVertex = `
attribute vec3 aPrec;
attribute vec3 aSuiv;
attribute float aCote;
attribute float aW;
uniform vec2 res;
uniform float px;
uniform float plancher;
uniform float decolle;
uniform float ortho;
varying float vA;
void main(){
  vec3 nv = normalize(normalMatrix * normal);
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vec3 vdir = ortho > 0.5 ? vec3(0.0, 0.0, 1.0) : normalize(-mv.xyz);
  float ndv = dot(nv, vdir);
  mv.xyz += nv * decolle;
  vec4 c = projectionMatrix * mv;
  vec4 cp = projectionMatrix * modelViewMatrix * vec4(aPrec, 1.0);
  vec4 cs = projectionMatrix * modelViewMatrix * vec4(aSuiv, 1.0);
  vec2 sp = cp.xy / cp.w * res, ss = cs.xy / cs.w * res;
  vec2 tg = ss - sp;
  float lt = length(tg);
  // COUDE à l'écran (relecture M5 : « un pli thénar se termine en crochet ») : là où la peau tourne le dos à l'œil, la
  // projection d'un pli se replie en crochet ; un pli dessiné ne fait jamais demi-tour. Angle entre (point − précédent)
  // et (suivant − point), voisins à ± 2 points : plein jusqu'à 50°, éteint au-delà de 75° (cos 0,64 → 0,26). Les
  // courbes voulues (thénar, poignet) tournent de moins de 25° sur cette longueur aux tailles d'usage.
  vec4 c0 = c; vec2 sc = c0.xy / c0.w * res;
  vec2 a1 = sc - sp, a2 = ss - sc; float l1 = length(a1), l2 = length(a2);
  float coude = (l1 > 0.5 && l2 > 0.5) ? dot(a1 / l1, a2 / l2) : 1.0;
  tg = lt > 1e-6 ? tg / lt : vec2(1.0, 0.0);
  vec2 perp = vec2(-tg.y, tg.x);
  // vu en rasant (N·V < 0,3), un ruban s'étire en épine (relecture adverse : « trois échardes » dans le tunnel du poing,
  // les plis palmaires de l'index replié vus par la tranche) : il s'efface de 0,12 à 0,3 (avant : 0,02 à 0,15)
  float vis = smoothstep(0.12, 0.3, ndv);
  float w = px * aW * clamp(ndv / 0.45, 0.45, 1.0);
  // sous le plancher, le trait s'éclaircit (alpha) au lieu de se briser en pointillé
  vA = vis * clamp(w / plancher, 0.0, 1.0) * step(0.001, aW) * smoothstep(0.26, 0.64, coude);
  w = max(w, plancher);
  c.xy += perp * aCote * 0.5 * w * 2.0 / res * c.w;
  gl_Position = c;
}`;
S.rubanFragment = `
uniform vec3 trait;
uniform float debug;
uniform sampler2D tCreux;
uniform float creuxOn;
uniform vec2 res;
uniform sampler2D tG;
uniform sampler2D tD;
uniform float ortho;
uniform float cn;
uniform float cf;
uniform float rOcc;        // px de la cible : rayon de la réserve autour d'une partie posée DEVANT le pli
uniform float dOcc;        // cm : écart de profondeur à partir duquel une autre partie est « devant »
varying float vA;
float lin(float d){
  if (ortho > 0.5) return cn + d * (cf - cn);
  float z = d * 2.0 - 1.0;
  return 2.0 * cn * cf / (cf + cn - z * (cf - cn));
}
void main(){
  if (vA < 0.02) discard;
  vec2 uv = gl_FragCoord.xy / res;
  if (creuxOn > 0.5 && texture2D(tCreux, uv).r > 0.5) discard;   // pas de pli au fond d'un creux
  // RÉSERVE autour d'un occultant (relecture M5 : « les traits de plis de la paume traversent le pouce posé devant
  // elle ») : le pli était bien caché SOUS le pouce (test de profondeur), mais il courait jusqu'au contour du pouce des
  // deux côtés, aligné : l'œil lit un trait qui traverse le pouce (« X » de griffures en V (2) face). Comme un
  // dessinateur, on arrête le pli avant le bord d'une AUTRE partie posée devant lui (plus proche de dOcc) : 32
  // échantillons sur quatre anneaux (¼ à 1 × rOcc) ; la même partie (pli qui passe derrière son propre relief) et le
  // fond (silhouette, déjà réservée par la coque) ne comptent pas.
  float res0 = 1.0;
  if (rOcc > 0.5) {
    vec4 g0 = texture2D(tG, uv);
    float id0 = floor(g0.a * 8.0 + 0.5);
    float d0 = lin(texture2D(tD, uv).r);
    for (int i = 0; i < 8; i++) {
      float a = float(i) * 0.7853982 + 0.3926991;
      vec2 dir = vec2(cos(a), sin(a)) * rOcc / res;
      for (int k = 1; k <= 4; k++) {
        vec2 q = uv + dir * (0.25 * float(k));
        vec4 g = texture2D(tG, q);
        float id = floor(g.a * 8.0 + 0.5);
        if (g.a < 0.01 || id > 7.5 || abs(id - id0) < 0.5) continue;
        // occultant à ¼ ou ½ rOcc : éteint ; à ¾ : 1/3 ; à rOcc : 2/3 (le pli s'effile vers le bord au lieu de finir net)
        if (lin(texture2D(tD, q).r) < d0 - dOcc) res0 = min(res0, max(0.0, float(k) - 2.0) / 3.0);
      }
    }
  }
  if (res0 < 0.01) discard;
#ifdef COUCHE_TRAITS
  gl_FragColor = vec4(0.0, 1.0, 0.0, vA * res0);
#else
  gl_FragColor = vec4(debug > 0.5 ? vec3(0.1, 0.7, 0.1) : trait, vA * res0);
#endif
}`;

/* ---------- 4c. creux fermés (tunnel du poing vu de profil) ---------- */
// Un pixel de peau est au FOND D'UN CREUX si, dans au moins 7 des 8 directions, on rencontre à moins de rCreux une
// surface nettement plus proche (de plus de dCreux) : on regarde par un petit trou fermé de tous côtés. Cas type : le
// tunnel que la boucle P1 / P2 / P3 de l'index replié laisse dans le poing vu de profil (défaut 0 de la v1, relecture
// adverse : « petit cadre noir avec trois échardes ») ; une vraie main n'y montre qu'une ombre. Le fond du creux est
// peint dans l'ombre (passe couleur) et aucun trait ne le cerne (passe d'arêtes) : on lit un creux, pas un cadre. Un
// trou plus large que 2 × rCreux (l'anneau d'un O, 2 à 3 cm) n'est pas fermé à cette distance et reste dessiné.
S.creuxFragment = `
uniform sampler2D tG;
uniform sampler2D tD;
uniform vec2 texel;
uniform float ortho;
uniform float cn;
uniform float cf;
uniform float cmPx;
uniform float rCreux;
uniform float dCreux;
uniform float nCreux;      // nombre de directions fermées exigé (sur 8), moins ½
varying vec2 vUv;
float lin(float d){
  if (ortho > 0.5) return cn + d * (cf - cn);
  float z = d * 2.0 - 1.0;
  return 2.0 * cn * cf / (cf + cn - z * (cf - cn));
}
void main(){
  vec4 g0 = texture2D(tG, vUv);
  float id0 = floor(g0.a * 8.0 + 0.5);
  if (g0.a < 0.01 || id0 > 7.5) { gl_FragColor = vec4(0.0); return; }
  float d0 = lin(texture2D(tD, vUv).r);
  float rpx = rCreux / (ortho > 0.5 ? cmPx : cmPx * d0);
  float fermes = 0.0;
  // pas d'échantillonnage borné en pixels (≤ 24 px de cible, 3 à 8 pas) : avec 3 pas fixes, une main de 1 800 px
  // (rpx ≈ 190 px de cible à ss 2) était sondée tous les 63 px, et des cloisons étroites passaient entre deux sondes — la
  // décision changeait avec la taille de l'image (relecture M5 : plaques d'ombre déchirées aux grands rendus). Mesuré :
  // à 10 px / 12 pas, le rendu de 2 600 px passait de 12 à 52 s (logiciel) ; 24 px / 8 pas garde la même image du poing
  float pas = clamp(ceil(rpx / 24.0), 3.0, 8.0);
  // « plus proche » se juge contre le PLAN TANGENT du pixel, pas contre sa profondeur : une paume vue de ¾ (pente 35°)
  // remonte de 0,84 cm vers l'œil sur 1,2 cm — avec un seuil de 0,5 cm elle « fermait » à elle seule 3 à 4 directions,
  // et sous la rangée des bouts du poing (paume ¾) le creux s'allumait en plaques (relecture M5). Pente tirée de la
  // normale de la G-pass (repère vue), n.z plafonné à 0,35 (au-delà de 70° de pente on ne prédit plus rien de sûr)
  vec3 n0 = texture2D(tG, vUv).rgb * 2.0 - 1.0;
  vec2 pente = n0.xy / max(n0.z, 0.35);
  float cmp = ortho > 0.5 ? cmPx : cmPx * d0;
  for (int i = 0; i < 8; i++) {
    float a = float(i) * 0.7853982;
    vec2 u = vec2(cos(a), sin(a));
    float f = 0.0;
    for (int k = 1; k <= 8; k++) {
      if (float(k) > pas) break;
      float t = rpx * (float(k) / pas);
      vec2 uv = vUv + u * t * texel;
      vec4 g = texture2D(tG, uv);
      float dPlan = d0 + dot(pente, u) * t * cmp;
      if (g.a > 0.01 && lin(texture2D(tD, uv).r) < dPlan - dCreux) f = 1.0;
    }
    fermes += f;
  }
  float c = step(nCreux, fermes);
  gl_FragColor = vec4(c, 0.0, 0.0, 1.0);
}`;

/* ---------- 5. composition de la couche des traits (arêtes, ongles, plis) : NETTOYAGE des miettes ---------- */
// Les traits intérieurs sont rendus dans une cible à part (alpha), puis posés sur l'image : un pixel de trait n'est gardé
// que s'il a assez de voisins de trait (fenêtre 5 × 5 de la cible) : seuil = 3 × le plancher en px de cible (7,5 avec le
// sur-échantillonnage ×2 de render(), 3,75 dans la marionnette non sur-échantillonnée) ; un trait au plancher en a ≈ 5 ×
// le plancher, une miette ou le bout isolé d'un filet nettement moins. Mesuré avant : 988 « fragments noirs < 20 px » aux jointures sur 96 vues,
// 80 % de 1 à 3 px (bout d'une bande d'ongle vue en biais, filet d'arête au seuil, bord d'une frange).
S.compoVertex = S.edgeVertex;
S.compoFragment = `
uniform sampler2D tL;
uniform vec2 texel;
uniform vec3 trait;
uniform float debug;
uniform float voisinsMin;
uniform float masque;
varying vec2 vUv;
void main(){
  vec4 l = texture2D(tL, vUv);
  if (l.a < 0.02) discard;
  float n = 0.0;
  for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) n += step(0.02, texture2D(tL, vUv + vec2(float(i), float(j)) * texel).a);
  if (n < voisinsMin) discard;
  // masque d'encre : arêtes et bande d'ongle seulement (les rubans des plis sont des marques voulues, jamais nettoyées)
  if (masque > 0.5) { float m = max(l.r, l.b); if (m < 0.02) discard; gl_FragColor = vec4(1.0, 1.0, 1.0, m); return; }
  vec3 c = debug > 0.5 ? (l.r > 0.5 && l.b > 0.5 ? vec3(0.8, 0.1, 0.8) : l.r > 0.5 ? vec3(0.9, 0.1, 0.1) : vec3(0.1, 0.7, 0.1)) : trait;
  gl_FragColor = vec4(c, l.a);
}`;

window.AtelierShaders = S;
})();
