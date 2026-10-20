/* engine.js — moteur 3D de la main v2 (Atelier des mains LSF, chantier M2). Three.js r128.
   Expose window.AtelierHand (contrat « M2 → M3 » de v2/PLAN.md) :
     ready, init({glb, json}), charger(urlGlb, urlJson), render({pose, cote, orientation, w, h, scale, style}),
     bounds({pose, cote, orientation}), puppet(canvasHost, element, onChange, options), presets, solve(depart, cible),
     mirror(pose), mirrorOrientation(q), constrain(pose), penetration(pose), depuisV1(objet), versV1(pose, q, pos).
   Les assets sont ceux de M1 : v2/hand/hand_v2.glb (main DROITE skinnée, 20 os, 26 610 sommets, 8 correctifs) et
   v2/hand/hand_v2.json (os, butées, couplages, plis barycentriques, ongles, poses). La main gauche est la droite en
   miroir x → −x (même lumière : la normale réfléchie par normalMatrix est déjà la bonne, CLAUDE.md « nflip »).
   Unités : centimètres (comme le GLB). Angles des poses : degrés.
   Chaque réglage porte la MESURE qui l'a fixé ; le journal est v2/engine/JOURNAL.md. */
(function(){
'use strict';
const THREE = window.THREE;
const SH = window.AtelierShaders;

/* =====================================================================================================================
   1. Constantes (chaque valeur porte sa source ou sa mesure)
   ===================================================================================================================== */
const D2R = Math.PI / 180;
const HL = 19.0;                 // cm, pli du poignet → bout du majeur (hand_v2.json « HL », main de l'utilisateur)
const DOIGTS = ['index', 'majeur', 'annulaire', 'auriculaire'];
const OS = ['poignet', 'mc1', 'pouce_p1', 'pouce_p2', 'mc2', 'index_p1', 'index_p2', 'index_p3', 'mc3', 'majeur_p1',
  'majeur_p2', 'majeur_p3', 'mc4', 'annulaire_p1', 'annulaire_p2', 'annulaire_p3', 'mc5', 'auriculaire_p1',
  'auriculaire_p2', 'auriculaire_p3'];
const OSI = {}; OS.forEach((n, i) => OSI[n] = i);
// parties (identité de la G-pass) : 0 paume (+ avant-bras, thénar, palmures), 1 pouce, 2…5 doigts
const PARTIES = ['paume', 'pouce', 'index', 'majeur', 'annulaire', 'auriculaire'];
const PARTIE_OS = OS.map(n => n === 'pouce_p1' || n === 'pouce_p2' ? 1 :
  DOIGTS.findIndex(k => n.startsWith(k + '_')) >= 0 ? 2 + DOIGTS.findIndex(k => n.startsWith(k + '_')) : 0);

// --- pouce : la trapézo-métacarpienne de la v1 (Hollister 1992), modèle validé par l'utilisateur (mobilite.md R8) ---
// Les axes inclinés TFT / TAT / FEV sont déjà dans les repères de liaison du GLB (mesuré : l'axe X de mc1 est à 4,4° de
// l'axe E_FE de la v1). Restent à ajouter : la pronation COUPLÉE à l'opposition (PRONA = 34°, v1) et l'axe d'abduction
// décalé dans la base du métacarpien (TOFF = 0,30 unité v1 ≈ 3,3 mm) : les deux axes ne se croisent pas, la base glisse.
const PRONA = 34;
const TOFF = 0.33;               // cm
const AV_REF = 45, RAP_REF = 40; // normalisation v1 de la pronation couplée (LIMT.av[1], LIMT.rap[1])
const AVC = 0.7;                 // vis sans fin : av ≥ 0,7·rap (v1, réglé par balayage, mobilite.md R8)
const AV_RAP_MAX = 80;           // v1 : av + rap ≤ 80
// --- arc métacarpien (mobilite.md R11) : CMC4 12°·arc, CMC5 25°·arc + supination 20°·arc ---
// automatique : arc ≥ ARC_AUTO · max(flexion MCP de l'auriculaire / 90, opposition du pouce) ; 0,6 = l'arc des poses de
// contrôle réglées par M1 sur le contact (poing : MCP 90 → arc 0,6 ; V : MCP 88 → 0,4 réglé, 0,59 ici)
const ARC_AUTO = 0.6;
// --- butées (hand_v2.json « butees », reprises de mobilite.md § 5.1.2), lues au chargement ; défauts identiques ---
let BUT = null;
// --- couplages souples (préférences, jamais bloquants : mobilite.md R7, R10) ---
const ENSLAVE = [['index', 'majeur', 90], ['majeur', 'annulaire', 85], ['annulaire', 'auriculaire', 75]];
// --- marionnette : un doigt tiré par le bout se ferme MCP : IPP : IPD = 0,85 : 1 : 0,7 (v1 GRAB, mobilite.md R14) ---
const GRAB = {doigt: [{mcp: 1}, {mcp: .85, pip: 1}, {mcp: .85, pip: 1, dip: .7}],
  pouce: [{av: 1}, {av: .3, mcp: 1}, {av: .15, rap: .6, mcp: .5, ip: .8}]};

/* =====================================================================================================================
   2. Petites maths (quaternions [x, y, z, w], vecteurs [x, y, z])
   ===================================================================================================================== */
const clamp = (x, a, b) => x < a ? a : x > b ? b : x;
const sstep = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
const clone = o => JSON.parse(JSON.stringify(o));
const num = (x, d) => typeof x === 'number' && isFinite(x) ? x : (d || 0);
function qmul(a, b) {
  return [a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1], a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
    a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3], a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]];
}
const qconj = q => [-q[0], -q[1], -q[2], q[3]];
function qrot(q, v) {
  const x = q[0], y = q[1], z = q[2], w = q[3];
  const tx = 2 * (y * v[2] - z * v[1]), ty = 2 * (z * v[0] - x * v[2]), tz = 2 * (x * v[1] - y * v[0]);
  return [v[0] + w * tx + y * tz - z * ty, v[1] + w * ty + z * tx - x * tz, v[2] + w * tz + x * ty - y * tx];
}
function qaxis(ax, deg) { const h = deg * D2R / 2, s = Math.sin(h); return [ax[0] * s, ax[1] * s, ax[2] * s, Math.cos(h)]; }
const QX = d => qaxis([1, 0, 0], d), QY = d => qaxis([0, 1, 0], d), QZ = d => qaxis([0, 0, 1], d);
function qnorm(q) { const l = Math.hypot(q[0], q[1], q[2], q[3]) || 1; return [q[0] / l, q[1] / l, q[2] / l, q[3] / l]; }
const vadd = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const vsub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const vsc = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
const vdot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const vlen = a => Math.hypot(a[0], a[1], a[2]);
const vnorm = a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
const vcross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const vlerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
// distance entre deux segments [p1,q1] et [p2,q2] ; rend aussi les paramètres s, t (Ericson, Real-Time Collision Detection)
function segSeg(p1, q1, p2, q2) {
  const d1 = vsub(q1, p1), d2 = vsub(q2, p2), r = vsub(p1, p2), a = vdot(d1, d1), e = vdot(d2, d2), f = vdot(d2, r);
  let s, t; const c = vdot(d1, r), b = vdot(d1, d2), den = a * e - b * b;
  s = den > 1e-9 ? clamp((b * f - c * e) / den, 0, 1) : 0; t = (b * s + f) / e;
  if (t < 0) { t = 0; s = clamp(-c / a, 0, 1); } else if (t > 1) { t = 1; s = clamp((b - c) / a, 0, 1); }
  const P = vadd(p1, vsc(d1, s)), Q = vadd(p2, vsc(d2, t));
  return {d: vlen(vsub(P, Q)), s, t};
}

/* =====================================================================================================================
   3. Pose v2 : normalisation, conversion v1, miroir
   Format (degrés) : { poignet:{flex, dev}, prono, arc, pouce:{av, rap, mcp, ip, abdMcp},
                       index:{mcp, pip, dip, ab, rot}, majeur:{…}, annulaire:{…}, auriculaire:{…} }
   - ab : écartement par rapport à l'AXE DU MAJEUR (3e rayon) : 0 = parallèle au majeur, > 0 vers le pouce (v1, SPREAD) ;
   - flex du poignet > 0 vers la paume, dev > 0 radiale (vers le pouce) ; prono > 0 = pronation (main droite : rotation
     de −prono autour de +Y, le pouce vient vers la caméra en vue paume) ; arc ∈ [0, 1] (en plus de l'arc automatique) ;
   - champs absents = 0 ; un champ `note` (texte) est ignoré par le moteur.
   ===================================================================================================================== */
function normalise(p) {
  p = p && typeof p === 'object' ? p : {};
  const pg = p.poignet || {}, t = p.pouce || {};
  const o = {poignet: {flex: num(pg.flex), dev: num(pg.dev)}, prono: num(p.prono), arc: num(p.arc),
    pouce: {av: num(t.av), rap: num(t.rap), mcp: num(t.mcp), ip: num(t.ip), abdMcp: num(t.abdMcp)}};
  DOIGTS.forEach(k => { const f = p[k] || {}; o[k] = {mcp: num(f.mcp), pip: num(f.pip), dip: num(f.dip), ab: num(f.ab), rot: num(f.rot)}; });
  return o;
}
// clé de cache (arrondie au centième de degré : deux poses qui ne diffèrent que par le bruit de flottant se valent)
function cle(p) {
  const r = x => Math.round(x * 100);
  const a = [r(p.poignet.flex), r(p.poignet.dev), r(p.prono), r(p.arc * 100), r(p.pouce.av), r(p.pouce.rap), r(p.pouce.mcp),
    r(p.pouce.ip), r(p.pouce.abdMcp)];
  DOIGTS.forEach(k => { const f = p[k]; a.push(r(f.mcp), r(f.pip), r(f.dip), r(f.ab), r(f.rot)); });
  return a.join(',');
}
// v1 → v2 : {f:{pouce:{av,rap,mcp,ip}, index:{mcp,pip,dip,ab},…}, q, pos} (JSON v6–v8 de l'atelier v1, une pose) ;
// mêmes noms, mêmes signes, même référence de l'écartement (le majeur) : la conversion est une recopie.
function depuisV1(o) {
  if (!o || typeof o !== 'object') return {pose: normalise({}), orientation: [0, 0, 0, 1], pos: [0, 0, 0]};
  const f = o.f || o;
  const pose = normalise({pouce: f.pouce, index: f.index, majeur: f.majeur, annulaire: f.annulaire, auriculaire: f.auriculaire});
  const q = Array.isArray(o.q) && o.q.length === 4 ? qnorm(o.q.map(x => num(x))) : [0, 0, 0, 1];
  const pos = Array.isArray(o.pos) && o.pos.length === 3 ? o.pos.map(x => num(x)) : [0, 0, 0];
  return {pose, orientation: q, pos};
}
// v2 → v1 : ce que la v1 sait lire (poignet, pronation, arc, abdMcp et rotation axiale n'existent pas en v1 et sont perdus)
function versV1(pose, q, pos) {
  const p = normalise(pose), f = {pouce: {av: p.pouce.av, rap: p.pouce.rap, mcp: p.pouce.mcp, ip: p.pouce.ip}};
  DOIGTS.forEach(k => f[k] = {mcp: p[k].mcp, pip: p[k].pip, dip: p[k].dip, ab: p[k].ab});
  return {f, q: Array.isArray(q) ? q.slice() : [0, 0, 0, 1], pos: Array.isArray(pos) ? pos.slice() : [0, 0, 0]};
}
// main gauche : mêmes angles (la pose est symétrique par construction) ; c'est l'orientation qui se réfléchit
function mirror(pose) { return normalise(pose); }
function mirrorOrientation(q) { return Array.isArray(q) && q.length === 4 ? [q[0], -q[1], -q[2], q[3]] : [0, 0, 0, 1]; }

/* =====================================================================================================================
   4. Assets : GLB (GLTFLoader) + JSON → tableaux du moteur
   ===================================================================================================================== */
let A = null;                    // assets décodés (voir init)
let resoudrePret, rejeterPret;
const ready = new Promise((ok, ko) => { resoudrePret = ok; rejeterPret = ko; });
ready.catch(() => {});           // une erreur de chargement est rapportée par init(), pas en « unhandled rejection »

function versArrayBuffer(glb) {
  if (glb instanceof ArrayBuffer) return glb;
  if (ArrayBuffer.isView(glb)) return glb.buffer.slice(glb.byteOffset, glb.byteOffset + glb.byteLength);
  if (typeof glb === 'string') {   // base64, avec ou sans en-tête data:
    const b64 = glb.replace(/^data:[^,]*,/, ''), bin = atob(b64), u = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
    return u.buffer;
  }
  throw new Error('GLB : ArrayBuffer, Uint8Array ou base64 attendu');
}
function lireAttr(at, n, c) {      // BufferAttribute (éventuellement entrelacé ou normalisé) → Float32Array
  const out = new Float32Array(n * c), arr = at.array;
  const den = at.normalized ? (arr instanceof Uint8Array ? 255 : arr instanceof Uint16Array ? 65535 : 1) : 1;
  const g = ['getX', 'getY', 'getZ', 'getW'];
  for (let i = 0; i < n; i++) for (let j = 0; j < c; j++) out[i * c + j] = at[g[j]](i) / den;
  return out;
}

async function init(opts) {
  try {
    if (A) return ready;
    if (!THREE || !THREE.GLTFLoader) throw new Error('three.js r128 et GLTFLoader doivent être chargés avant engine.js');
    if (!SH) throw new Error('shaders.js doit être chargé avant engine.js');
    const buf = versArrayBuffer(opts.glb);
    const J = typeof opts.json === 'string' ? JSON.parse(opts.json) : opts.json;
    const gltf = await new Promise((ok, ko) => new THREE.GLTFLoader().parse(buf, '', ok, ko));
    let sk = null; gltf.scene.traverse(o => { if (o.isSkinnedMesh && !sk) sk = o; });
    if (!sk) throw new Error('aucune SkinnedMesh dans le GLB');
    A = decoder(sk, J);
    construireContacts();
    construirePlis();
    construirePresets();
    resoudrePret();
  } catch (e) { rejeterPret(e); throw e; }
  return ready;
}
async function charger(urlGlb, urlJson) {
  const [g, j] = await Promise.all([fetch(urlGlb).then(r => { if (!r.ok) throw new Error(urlGlb + ' : ' + r.status); return r.arrayBuffer(); }),
    fetch(urlJson).then(r => { if (!r.ok) throw new Error(urlJson + ' : ' + r.status); return r.json(); })]);
  return init({glb: g, json: j});
}

function decoder(sk, J) {
  const g = sk.geometry, n = g.attributes.position.count;
  const a = {n, json: J};
  a.rest = lireAttr(g.attributes.position, n, 3);
  a.restN = lireAttr(g.attributes.normal, n, 3);
  a.index = g.index ? Uint32Array.from(g.index.array) : Uint32Array.from({length: n}, (_, i) => i);
  a.y = new Float32Array(n); for (let i = 0; i < n; i++) a.y[i] = a.rest[3 * i + 1];
  // --- os : liaison monde = inverse(boneInverse) (matrice du maillage = identité, M1 étape 9) ---
  const bones = sk.skeleton.bones, carte = bones.map(b => OSI[b.name]);
  if (carte.some(x => x === undefined) || bones.length !== 20) throw new Error('os du GLB ≠ contrat (20 os nommés)');
  a.Qb = []; a.Cb = []; a.parent = [];
  const m = new THREE.Matrix4(), pp = new THREE.Vector3(), qq = new THREE.Quaternion(), ss = new THREE.Vector3();
  bones.forEach((b, i) => {
    m.copy(sk.skeleton.boneInverses[i]).invert().decompose(pp, qq, ss);
    const k = carte[i]; a.Qb[k] = [qq.x, qq.y, qq.z, qq.w]; a.Cb[k] = [pp.x, pp.y, pp.z];
  });
  OS.forEach((nm, k) => { const par = (J.os[nm] || {}).parent; a.parent[k] = par ? OSI[par] : -1; });
  // contrôle : centres du JSON = centres du GLB (M1 : 2,5·10⁻⁶ près)
  a.ecartJsonGlb = Math.max(...OS.map((nm, k) => vlen(vsub(a.Cb[k], J.os[nm].centre))));
  // liaison locale (repère du parent)
  a.Ql = []; a.Tl = [];
  OS.forEach((nm, k) => { const p = a.parent[k];
    if (p < 0) { a.Ql[k] = a.Qb[k].slice(); a.Tl[k] = a.Cb[k].slice(); return; }
    const ip = qconj(a.Qb[p]); a.Ql[k] = qmul(ip, a.Qb[k]); a.Tl[k] = qrot(ip, vsub(a.Cb[k], a.Cb[p])); });
  // éventail de liaison des doigts (angle de la P1 par rapport à +Y dans le plan de la paume, > 0 vers le pouce)
  a.eventail = {};
  DOIGTS.forEach(k => { const y = qrot(a.Qb[OSI[k + '_p1']], [0, 1, 0]); a.eventail[k] = Math.atan2(y[0], y[1]) / D2R; });
  // --- poids : ≤ 4 os, l'os dominant en premier (alignement de signe des quaternions duaux, comme dqApply v1) ---
  const si = g.attributes.skinIndex, sw = g.attributes.skinWeight;
  const Ji = lireAttr(si, n, 4), Wi = lireAttr(sw, n, 4);
  a.J = new Uint8Array(4 * n); a.W = new Float32Array(4 * n); a.os = new Float32Array(n); a.part = new Float32Array(n);
  const ordre = [0, 1, 2, 3];
  for (let i = 0; i < n; i++) {
    ordre.sort((x, y) => Wi[4 * i + y] - Wi[4 * i + x]);
    let s = 0; for (let j = 0; j < 4; j++) s += Wi[4 * i + ordre[j]];
    const parGroupe = [0, 0, 0, 0, 0, 0];
    for (let j = 0; j < 4; j++) {
      const b = carte[Math.round(Ji[4 * i + ordre[j]])], w = Wi[4 * i + ordre[j]] / (s || 1);
      a.J[4 * i + j] = b; a.W[4 * i + j] = w; parGroupe[PARTIE_OS[b]] += w;
    }
    a.os[i] = a.J[4 * i];
    let best = 0; for (let j = 1; j < 6; j++) if (parGroupe[j] > parGroupe[best]) best = j;
    a.part[i] = best;
  }
  // --- régions, ongles (attributs de M1 ; three.js met leur nom en minuscules) ---
  const at = g.attributes;
  a.region = at._region ? lireAttr(at._region, n, 1) : new Float32Array(n);
  a.ongle = at._ongle ? lireAttr(at._ongle, n, 1) : new Float32Array(n).fill(-3);
  const mq = at._masques ? lireAttr(at._masques, n, 4) : new Float32Array(4 * n);
  a.masque = new Float32Array(2 * n);
  for (let i = 0; i < n; i++) { a.masque[2 * i] = mq[4 * i]; a.masque[2 * i + 1] = mq[4 * i + 1];
    if (Math.round(a.region[i]) === 4) a.part[i] = 0; }   // palmure = paume (v1 : « palmures et éminence = paume »)
  // FRANGE LIBRE en distance CONTINUE (cm, > 0 sur la frange), à la place du masque 0/1 de M1. Relecture M5 : à
  // l'export A3 (main de 4 600 px) le bord frange / tablette du pouce était en ESCALIER sur ≈ 130 px — l'isoligne 0,5
  // d'un masque 0/1 interpolé suit les milieux des arêtes des triangles (pas de 0,6 mm) et zigzague. M1 définit la
  // frange analytiquement (build_hand.py, étape 6) : s > s_d − frange − 0,10·W·(x / hw)², dans le repère de la dernière
  // phalange (Y vers le bout, Z vers la paume ; pouce : axes de l'os) ; on recalcule ce champ ici, lisse par sommet —
  // l'isoligne d'un champ affine par triangle est une courbe continue, nette à tout grossissement (seuil au fragment, en
  // fwidth comme la distance signée de l'ongle). Contrôle au chargement : signe du champ = masque de M1 sur les sommets
  // d'ongle (`a.frangeEcart` désaccords ; mesuré 1 sur 2 126, à 0,002 mm du seuil).
  {
    const ON = (J.regions && J.regions.ongles) || {}, R = a.rest;
    const fr = new Float32Array(n).fill(-0.3); let ecart = 0, compte = 0;
    Object.keys(ON).forEach(k => { const g = ON[k], b = J.os[g.os]; if (!b || !b.bout) return;
      const C = b.centre, y = vnorm(vsub(b.bout, C));
      let X, Y, Z;
      if (k === 'pouce' && b.axes) { X = b.axes.x; Y = b.axes.y; Z = b.axes.z; }
      else { Y = y; const zr = [0, 0, 1], d = vdot(zr, Y); Z = vnorm([zr[0] - d * Y[0], zr[1] - d * Y[1], zr[2] - d * Y[2]]); X = vcross(Y, Z); }
      const W = g.largeur, hw = W / 2, sd = g.bord_libre_s, fl = g.frange != null ? g.frange : 0.12;
      for (let i = 0; i < n; i++) {
        const d = [R[3 * i] - C[0], R[3 * i + 1] - C[1], R[3 * i + 2] - C[2]];
        const qx = vdot(d, X), qs = vdot(d, Y), qz = vdot(d, Z);
        if (Math.abs(qx) > hw + 0.3 || qs < 0 || qs > sd + 0.5 || Math.abs(qz) > 1.5) continue;
        const u = Math.max(-1, Math.min(1, qx / hw));
        const f = Math.max(-0.3, Math.min(0.3, qs - (sd - fl - 0.10 * W * u * u)));
        fr[i] = f;
        if (mq[4 * i] > 0.5) { compte++; if ((f > 0) !== (mq[4 * i + 1] > 0.5)) ecart++; }
      }
    });
    if (compte) { for (let i = 0; i < n; i++) a.masque[2 * i + 1] = fr[i]; }
    a.frangeEcart = ecart; a.frangeCompte = compte;
  }
  // une couture directe entre deux doigts (sans paume entre eux) serait tracée comme un contact : on la mesure et on
  // la rend à la paume (sommets de la couture)
  let couture = 0;
  for (let t = 0; t < a.index.length; t += 3) {
    const v = [a.index[t], a.index[t + 1], a.index[t + 2]];
    for (let e = 0; e < 3; e++) { const p1 = a.part[v[e]], p2 = a.part[v[(e + 1) % 3]];
      if (p1 >= 1 && p2 >= 1 && p1 !== p2) { couture++; a.part[v[e]] = 0; a.part[v[(e + 1) % 3]] = 0; } }
  }
  a.couture = couture;
  // --- biais d'ombre par sommet (rendu.md § 3.3, Guilty Gear) : ongle −0,10 (plus souvent éclairé : il ne bascule pas
  //     entier dans l'ombre vu de biais), palmures +0,08 (le creux entre deux doigts) ---
  a.biais = new Float32Array(n);
  for (let i = 0; i < n; i++) { if (a.masque[2 * i] > 0.5) a.biais[i] = -0.10; else if (Math.round(a.region[i]) === 4) a.biais[i] = 0.08; }
  // --- RELIEF DU DOS porté par l'ombre (relecture adverse : « gant de caoutchouc » — le dos de la main était une plaque
  //     lisse dans toutes les vues dos ¾). Une vraie main montre, par paires (CLAUDE.md, piste W de la v1 validée par
  //     l'utilisateur) : les SILLONS entre les têtes métacarpiennes quand les MCP se plient (poing), les VALLÉES entre les
  //     tendons extenseurs quand elles s'étendent ; jamais les deux à la fois. La géométrie (correctifs de M1 : tête qui
  //     sort de 3,5 mm) ne fait pas basculer le toon à deux tons (pente ≈ 19°, N·L 0,68 contre un seuil de 0,41) ; le
  //     relief passe donc par le SEUIL d'ombre, comme le biais des ongles : chaque sommet du dos de la paume reçoit, dans
  //     le repère de liaison, son poids de sillon (près des têtes, à mi-chemin entre deux rayons) et de vallée (le long
  //     des diaphyses, entre deux rayons), pilotés à chaque pose par la flexion des deux MCP voisines (Pipeline.poser).
  a.sillon = []; a.vallee = [];
  {
    const MC = ['mc2', 'mc3', 'mc4', 'mc5'].map(k => OSI[k]), P1 = DOIGTS.map(k => OSI[k + '_p1']);
    const ax = MC.map((m, k) => ({b: a.Cb[m], h: a.Cb[P1[k]]}));
    for (let k = 0; k < 3; k++) { a.sillon.push(new Float32Array(n)); a.vallee.push(new Float32Array(n)); }
    for (let i = 0; i < n; i++) {
      if (a.part[i] !== 0 || a.restN[3 * i + 2] > -0.25 || a.masque[2 * i] > 0.1) continue;   // dos de la paume seulement
      const v = [a.rest[3 * i], a.rest[3 * i + 1], a.rest[3 * i + 2]];
      for (let k = 0; k < 3; k++) {
        // ligne médiane entre les rayons k et k+1 (base → tête), paramètre t le long de la diaphyse
        const b = vlerp(ax[k].b, ax[k + 1].b, 0.5), h = vlerp(ax[k].h, ax[k + 1].h, 0.5), d = vsub(h, b), L = vlen(d);
        const t = vdot(vsub(v, b), d) / (L * L), q = vadd(b, vsc(d, t)), lat = Math.hypot(v[0] - q[0], v[1] - q[1]);
        const ecart = vlen(vsub(ax[k + 1].h, ax[k].h));                 // écartement des têtes (≈ 2 cm)
        const w = Math.exp(-Math.pow(lat / (0.28 * ecart), 2));
        a.sillon[k][i] = w * sstep(0.72, 0.92, t) * (1 - sstep(1.08, 1.22, t));   // au droit des têtes
        a.vallee[k][i] = w * sstep(0.25, 0.45, t) * (1 - sstep(0.8, 0.95, t));    // le long des diaphyses
      }
    }
  }
  a.biaisBase = a.biais.slice();
  // --- JOINTURES À L'IDENTITÉ DE LEUR DOIGT (grief de l'utilisateur, 20 octobre : « des doigts qui se fondent dans la
  //     main, tu ne vois même plus les traits de chaque doigt », capture de « L » vue de dos). Mesuré (passe identité lue
  //     sur la G-pass, vues dos et dos ¾ de L, Index (1), V (2), Poing serré) : tout ce que l'on voit de dos d'un doigt
  //     replié — la tête du métacarpien, la palmure dorsale et la base de la P1 — porte l'identité PAUME (les poids de
  //     peau y sont dominés par mc2–mc5 ; 0 pixel de trait entre deux jointures à 30 px/cm comme à 90). Aucune frontière
  //     doigt / doigt n'existait donc à cet endroit, quel que soit le seuil : un gant. En v1, la peau de la jointure
  //     appartenait à la P1 (pas d'os métacarpien) et la passe identité y traçait toujours le trait de contact.
  //     Chaque sommet du DOS de la paume reçoit ici, dans le repère de liaison, une coordonnée latérale CONTINUE entre les
  //     rayons (u = 0 sur l'axe de l'index … 3 sur celui de l'auriculaire, k + ½ sur la ligne médiane entre deux rayons),
  //     sa position le long du rayon (t = 0 à la base du métacarpien, 1 au centre de la MCP), et un poids « dos ». La
  //     G-pass (shaders.js, 1) donne au fragment l'identité du doigt k = arrondi(u) quand la MCP de ce doigt est pliée
  //     (seuil en t passé par uniforme, Pipeline.poser) : la frontière entre deux jointures est l'isoligne u = k + ½ d'un
  //     champ lisse (pas l'escalier des triangles), c'est-à-dire le fond de la vallée entre deux têtes métacarpiennes.
  //     Mesuré au repos : 1 637 des 1 659 sommets dorsaux des P1 (t < 1,5) sont à moins de ½ de leur rayon (|u − k| < ½),
  //     les 22 autres au bord cubital de l'auriculaire (u 2,48–2,50 ou > 3,5) : la frontière ne coupe aucune P1.
  {
    const MC = ['mc2', 'mc3', 'mc4', 'mc5'].map(k => OSI[k]), P1 = DOIGTS.map(k => OSI[k + '_p1']);
    const ax = MC.map((m, k) => { const b = a.Cb[m], h = a.Cb[P1[k]], d = [h[0] - b[0], h[1] - b[1]], L = Math.hypot(d[0], d[1]); return {b, d, L}; });
    const ecart = [0, 1, 2].map(k => Math.hypot(a.Cb[P1[k + 1]][0] - a.Cb[P1[k]][0], a.Cb[P1[k + 1]][1] - a.Cb[P1[k]][1]));   // 2,25 / 2,22 / 1,74 cm
    a.rayon = new Float32Array(3 * n);
    for (let i = 0; i < n; i++) {
      // calculé pour TOUS les sommets (le nuanceur décide qui change d'identité : la paume, et la base dorsale des P1) ;
      // n'écrire que ceux de la paume laissait des zéros sur les sommets voisins des doigts, interpolés dans les triangles
      // mixtes : trous de paume dans la jointure, tirets de trait (Y de profil, O en dos ¾). Le pouce n'en a pas.
      if (a.part[i] === 1) continue;
      const x = a.rest[3 * i], y = a.rest[3 * i + 1];
      // e[k] : distance signée à l'axe du rayon k dans le plan de la paume, > 0 vers le cubital (−X) ; t[k] : abscisse
      const e = [], t = [];
      for (let k = 0; k < 4; k++) { const w = [x - ax[k].b[0], y - ax[k].b[1]];
        t.push((w[0] * ax[k].d[0] + w[1] * ax[k].d[1]) / (ax[k].L * ax[k].L)); e.push((w[0] * -ax[k].d[1] + w[1] * ax[k].d[0]) / ax[k].L); }
      let u = null;
      if (e[0] < 0) u = e[0] / ecart[0]; else if (e[3] > 0) u = 3 + e[3] / ecart[2];
      else for (let k = 0; k < 3; k++) if (e[k] >= 0 && e[k + 1] <= 0) { u = k + e[k] / (e[k] - e[k + 1]); break; }
      if (u === null) continue;
      const k0 = Math.max(0, Math.min(2, Math.floor(u))), f = Math.max(0, Math.min(1, u - k0)), tt = t[k0] * (1 - f) + t[k0 + 1] * f;
      // dos : n.z < −0,05 → 0, < −0,35 → 1 (isoligne ½ à n.z ≈ −0,2, comme le « dos franc » des sillons) ; au-delà d'une
      // demi-jointure hors des rayons extrêmes (bord radial de l'index, cubital de l'auriculaire : la commissure du pouce
      // et la tranche), rien — sinon la palmure dorsale du pouce aurait pris l'identité de l'index et tracé un trait
      // « pouce / index » le long de la commissure
      // La PALMURE (région 4) compte comme dos jusqu'à n.z 0,2 : au fond de la commissure ses normales regardent le
      // bout des doigts (mesuré : 189 sommets de palmure à moins de 0,1 de la ligne médiane, n.z −0,2 à +0,2) ; restée
      // « paume », elle laissait un blanc de 4 à 6 px (×3) entre le trait de la vallée et l'encoche du contour.
      const nz = a.restN[3 * i + 2], palmure = Math.round(a.region[i]) === 4;
      const dos = (u < -0.45 || u > 3.45) ? 0 : palmure ? sstep(0.35, 0.05, nz) : sstep(-0.05, -0.35, nz);
      a.rayon[3 * i] = u; a.rayon[3 * i + 1] = tt; a.rayon[3 * i + 2] = dos;
    }
  }
  // --- correctifs (morph targets, accesseurs creux → on ne garde que les sommets déplacés) ---
  a.morphs = [];
  const dict = sk.morphTargetDictionary || {}, mp = g.morphAttributes.position || [], mn = g.morphAttributes.normal || [];
  const liste = (J.correctifs && J.correctifs.liste) || [];
  liste.forEach(c => {
    const i = dict[c.nom]; if (i === undefined || !mp[i]) return;
    const dp = lireAttr(mp[i], n, 3), dn = mn[i] ? lireAttr(mn[i], n, 3) : new Float32Array(3 * n);
    const idx = [];
    for (let v = 0; v < n; v++) if (Math.abs(dp[3 * v]) + Math.abs(dp[3 * v + 1]) + Math.abs(dp[3 * v + 2]) + Math.abs(dn[3 * v]) + Math.abs(dn[3 * v + 1]) + Math.abs(dn[3 * v + 2]) > 1e-7) idx.push(v);
    const P = new Float32Array(3 * idx.length), N = new Float32Array(3 * idx.length);
    idx.forEach((v, j) => { for (let c3 = 0; c3 < 3; c3++) { P[3 * j + c3] = dp[3 * v + c3]; N[3 * j + c3] = dn[3 * v + c3]; } });
    const [doigt, champ] = c.angle.split('.');   // « index.mcp » → doigt, champ
    a.morphs.push({nom: c.nom, doigt, champ, ref: c.reference, idx: Uint32Array.from(idx), dp: P, dn: N});
  });
  // --- butées ---
  BUT = J.butees;
  a.bouts = {};
  OS.forEach(nm => { if (J.os[nm].bout) a.bouts[nm] = J.os[nm].bout; });
  return a;
}

/* =====================================================================================================================
   5. Butées et couplages
   ===================================================================================================================== */
function borne(os, champ, passif) {
  const b = BUT && BUT[os]; if (!b) return [-180, 180];
  return (passif && b[champ + '_passif']) || b[champ] || [-180, 180];
}
// constrain : butées DURES (actives par défaut, passives si opts.passif) et couplages anatomiques obligatoires :
// IPD–IPP (R4), écartement qui se ferme avec la flexion sans jamais atteindre 0 (R2), vis sans fin du pouce (R8).
function constrain(pose, opts) {
  const p = normalise(pose), ps = !!(opts && opts.passif);
  const pw = p.poignet;
  pw.flex = clamp(pw.flex, ...borne('poignet', 'flex', ps)); pw.dev = clamp(pw.dev, ...borne('poignet', 'dev', ps));
  p.prono = clamp(p.prono, ...borne('poignet', 'prono', ps)); p.arc = clamp(p.arc, 0, 1);
  DOIGTS.forEach(k => {
    const f = p[k];
    f.mcp = clamp(f.mcp, ...borne(k + '_p1', 'flex', ps));
    f.pip = clamp(f.pip, ...borne(k + '_p2', 'flex', ps));
    const bd = borne(k + '_p3', 'flex', ps);
    // fléchisseur profond commun (v1, mobilite.md R4) : IPD ≤ 25 + 0,65·IPP et IPD ≥ 0,45·(IPP − 55)
    f.dip = clamp(f.dip, Math.max(bd[0], 0.45 * (f.pip - 55)), Math.min(bd[1], 25 + 0.65 * f.pip));
    // R2 : l'écartement se referme avec la flexion de la MCP (collatéraux tendus), plage × max(0,1 ; 1 − 0,9·θ/90),
    // AUTOUR DE L'ÉVENTAIL NEUTRE du doigt (sa liaison : index +4°, annulaire −5,5°, auriculaire −14°, M1) et non autour
    // de l'axe du majeur : poing fermé, chaque doigt reste dans l'axe de son rayon. Mesuré : refermée vers 0 (parallèle
    // au majeur), la plage serrait les quatre P1 du poing l'une dans l'autre (auriculaire tourné de 14° vers
    // l'annulaire, contact majeur–annulaire 3,2 mm, annulaire bloqué à MCP 75°) ; M1 avait réglé son poing sur l'éventail.
    const ba = borne(k + '_p1', 'abd', ps), fr = Math.max(0.1, 1 - 0.9 * clamp(f.mcp, 0, 90) / 90), n0 = A ? A.eventail[k] : 0;
    f.ab = clamp(f.ab, n0 + (ba[0] - n0) * fr, n0 + (ba[1] - n0) * fr);
    // rotation axiale : jamais commandée au repos (R6), permise dans sa plage passive (±15°) quand on la demande (R croisé)
    f.rot = clamp(f.rot, ...borne(k + '_p1', 'rot', true));
  });
  const t = p.pouce;
  t.av = clamp(t.av, ...borne('mc1', 'av', ps)); t.rap = clamp(t.rap, ...borne('mc1', 'rap', ps));
  t.mcp = clamp(t.mcp, ...borne('pouce_p1', 'flex', ps)); t.ip = clamp(t.ip, ...borne('pouce_p2', 'flex', ps));
  t.abdMcp = clamp(t.abdMcp, ...borne('pouce_p1', 'abd', ps));
  // vis sans fin (v1 AVC) : on ne rapproche pas le pouce des doigts sans qu'il sorte du plan de la paume
  t.av = Math.max(t.av, AVC * Math.max(0, t.rap));
  if (t.av + t.rap > AV_RAP_MAX) { const e = (t.av + t.rap - AV_RAP_MAX) / 2; t.av -= e; t.rap -= e; }
  t.av = clamp(t.av, ...borne('mc1', 'av', true));
  return p;
}
// préférences SOUPLES (mobilite.md R7, R10) : appliquées au glisser de la marionnette, jamais aux valeurs saisies ou
// aux presets (7, 8, H, T LSF les franchissent). driver = doigt tiré ; verrous = {doigt: [base, milieu, bout]}.
function preferences(p, driver, verrous, opts) {
  const t = p.pouce;
  // IPD ↔ IPP (mobilite.md R4, relecture adverse) : en fermeture, l'IPD suit 0,6 à 0,77 × l'IPP (fléchisseur profond) ;
  // constrain n'impose que les bornes larges de la v1 (0,45·(IPP − 55) ≤ IPD ≤ 25 + 0,65·IPP : IPD 15,75° acceptée pour
  // IPP 90, 0,18 ×). Préférence SOUPLE du geste : jamais avec Maj (une seule articulation), jamais IPD verrouillée,
  // seulement sur le(s) doigt(s) que l'on bouge, et au-delà de 20° d'IPP (doigt quasi tendu : libre).
  const ks = opts && opts.doigts ? opts.doigts : (driver && driver !== 'pouce' ? [driver] : []);
  if (!(opts && opts.maj)) ks.forEach(k => {
    if (verrous && verrous[k] && verrous[k][2]) return;
    const f = p[k]; if (f.pip <= 20) return;
    f.dip = clamp(f.dip, 0.6 * f.pip, 0.77 * f.pip);
  });
  t.mcp = Math.min(t.mcp, Math.max(30 + 0.8 * t.av + 0.4 * Math.max(0, t.rap), Math.min(t.mcp, 0)));
  if (driver && driver !== 'pouce') {
    const ordre = [driver], vu = new Set(ordre);
    for (let i = 0; i < ordre.length; i++) {
      const a = ordre[i];
      ENSLAVE.forEach(([x, y, mx]) => {
        if (x !== a && y !== a) return; const b = x === a ? y : x; if (vu.has(b)) return;
        const d = p[a].mcp - p[b].mcp;
        if (Math.abs(d) > mx) {
          if (verrous && verrous[b] && verrous[b][0]) p[a].mcp = p[b].mcp + Math.sign(d) * mx;
          else { p[b].mcp = p[a].mcp - Math.sign(d) * mx; vu.add(b); ordre.push(b); }
        }
      });
    }
  }
  return p;
}
// ce qui est « forcé » dans une pose (les couplages souples franchis) : affiché par la marionnette, noté dans les presets
function diagnostic(pose) {
  const p = normalise(pose), out = [], t = p.pouce;
  const lim = 30 + 0.8 * t.av + 0.4 * Math.max(0, t.rap);
  if (t.mcp > lim + 0.5) out.push('MCP du pouce pliée (' + t.mcp.toFixed(0) + '°) au-delà de sa préférence (' + lim.toFixed(0) + '°) : posture forcée');
  ENSLAVE.forEach(([x, y, mx]) => { const d = Math.abs(p[x].mcp - p[y].mcp); if (d > mx + 0.5) out.push(x + '–' + y + ' : écart de flexion ' + d.toFixed(0) + '° > ' + mx + '° (asservissement) : posture forcée'); });
  return out;
}

/* =====================================================================================================================
   6. Cinématique directe : pose → repère monde posé de chaque os (quaternion Qw, centre Cw)
   Conventions de hand_v2.json « convention_pose » : P1 = Rz(−ab′)·Rx(mcp)·Ry(rot) dans le repère de liaison (X oblique :
   LEAN de la v1 déjà dans le GLB), P2 = Rx(pip), P3 = Rx(dip) ; mc1 = Rx(rap)·Rz(−av) (+ pronation couplée et axe
   d'abduction décalé, ci-dessous) ; pouce_p1 = Rx(mcp)·Rz(−abdMcp) ; pouce_p2 = Rx(ip) ; mc4 = Rx(12·arc),
   mc5 = Rx(25·arc)·Ry(−20·arc) ; poignet : Ry(−prono) porte l'avant-bras, Rx(flex)·Rz(−dev) tourne les cinq rayons autour
   de l'origine (ordre de build_hand.py cinematique).
   ===================================================================================================================== */
function opposition(t) { return clamp(t.av / AV_REF, 0, 1) * clamp(Math.max(0, t.rap) / RAP_REF, 0, 1); }
function arcEffectif(p) { return clamp(Math.max(p.arc, ARC_AUTO * Math.max(clamp(p.auriculaire.mcp / 90, 0, 1), opposition(p.pouce))), 0, 1); }
function pronationPouce(t) {     // v1 pronOf : elle suit l'OPPOSITION, pas « avancer » ; nulle à (0, 0)
  const a = clamp(t.av / AV_REF, 0, 1), r = clamp(Math.max(t.rap, 0) / RAP_REF, 0, 1);
  return -PRONA * (a * (0.35 + 0.65 * r) + 0.25 * r * (1 - a));
}
function rotationsLocales(p) {
  const R = new Array(20), T = new Array(20);
  for (let i = 0; i < 20; i++) { R[i] = [0, 0, 0, 1]; T[i] = null; }
  DOIGTS.forEach(k => {
    const f = p[k];
    R[OSI[k + '_p1']] = qmul(qmul(QZ(-(f.ab - A.eventail[k])), QX(f.mcp)), QY(f.rot));
    R[OSI[k + '_p2']] = QX(f.pip); R[OSI[k + '_p3']] = QX(f.dip);
  });
  const t = p.pouce;
  // trapézo-métacarpienne : flexion (rap) autour de X par le trapèze, abduction (av) autour de Z par la BASE du
  // métacarpien (décalée de TOFF le long de l'os), pronation couplée autour de l'os : x → Rf·Rb·Rp·x + Rf·o − Rf·Rb·o
  const Rf = QX(t.rap), Rb = QZ(-t.av), Rp = QY(pronationPouce(t)), o = [0, TOFF, 0];
  R[OSI.mc1] = qmul(qmul(Rf, Rb), Rp);
  T[OSI.mc1] = vsub(qrot(Rf, o), qrot(qmul(Rf, Rb), o));
  R[OSI.pouce_p1] = qmul(QX(t.mcp), QZ(-t.abdMcp));
  R[OSI.pouce_p2] = QX(t.ip);
  const arc = arcEffectif(p);
  R[OSI.mc4] = QX(12 * arc); R[OSI.mc5] = qmul(QX(25 * arc), QY(-20 * arc));
  return {R, T};
}
// fk(pose normalisée) → {Q: [20 quaternions monde], C: [20 centres monde]} dans le repère de la main (avant orientation)
function fk(p) {
  const {R, T} = rotationsLocales(p), Q = new Array(20), C = new Array(20);
  const qpr = QY(-p.prono);
  Q[0] = qmul(qpr, qmul(A.Ql[0], R[0])); C[0] = qrot(qpr, A.Tl[0]);
  const Qcarpe = qmul(Q[0], qmul(QX(p.poignet.flex), QZ(-p.poignet.dev)));   // repère des rayons (identité de liaison)
  for (let k = 1; k < 20; k++) {
    const par = A.parent[k], Qp = par === 0 ? Qcarpe : Q[par], Cp = C[par];
    const QpL = qmul(Qp, A.Ql[k]);
    Q[k] = qmul(QpL, R[k]);
    let c = vadd(Cp, qrot(Qp, A.Tl[k]));
    if (T[k]) c = vadd(c, qrot(QpL, T[k]));
    C[k] = c;
  }
  return {Q, C};
}
// point attaché à un os, donné dans le repère monde de LIAISON → position posée
function pointPose(F, k, pLiaison) { return vadd(F.C[k], qrot(qmul(F.Q[k], qconj(A.Qb[k])), vsub(pLiaison, A.Cb[k]))); }

/* =====================================================================================================================
   7. Peau : quaternions duaux sur le CPU (comme dqApply de la v1), correctifs ajoutés AVANT dans l'espace de liaison
   ===================================================================================================================== */
const _dq = new Float64Array(8 * 20);
function quaternionsDuaux(F) {
  for (let k = 0; k < 20; k++) {
    const q = qmul(F.Q[k], qconj(A.Qb[k]));               // liaison → posé
    const t = vsub(F.C[k], qrot(q, A.Cb[k]));
    const o = 8 * k;
    _dq[o] = q[0]; _dq[o + 1] = q[1]; _dq[o + 2] = q[2]; _dq[o + 3] = q[3];
    _dq[o + 4] = 0.5 * (t[0] * q[3] + t[1] * q[2] - t[2] * q[1]);
    _dq[o + 5] = 0.5 * (-t[0] * q[2] + t[1] * q[3] + t[2] * q[0]);
    _dq[o + 6] = 0.5 * (t[0] * q[1] - t[1] * q[0] + t[2] * q[3]);
    _dq[o + 7] = -0.5 * (t[0] * q[0] + t[1] * q[1] + t[2] * q[2]);
  }
}
let _mp = null, _mn = null;
// skin(pose normalisée, P, N) : écrit les positions et normales posées (repère de la main) dans P et N (Float32Array 3n)
function skin(p, P, N) {
  const n = A.n, rest = A.rest, restN = A.restN, J = A.J, W = A.W;
  if (!_mp) { _mp = new Float32Array(3 * n); _mn = new Float32Array(3 * n); }
  _mp.set(rest); _mn.set(restN);
  A.morphs.forEach(m => {
    const w = clamp(p[m.doigt][m.champ] / m.ref, 0, 1); if (w <= 0) return;
    const idx = m.idx, dp = m.dp, dn = m.dn;
    for (let j = 0; j < idx.length; j++) { const o = 3 * idx[j];
      _mp[o] += w * dp[3 * j]; _mp[o + 1] += w * dp[3 * j + 1]; _mp[o + 2] += w * dp[3 * j + 2];
      _mn[o] += w * dn[3 * j]; _mn[o + 1] += w * dn[3 * j + 1]; _mn[o + 2] += w * dn[3 * j + 2]; }
  });
  const F = fk(p); quaternionsDuaux(F);
  const dq = _dq;
  for (let i = 0; i < n; i++) {
    const i4 = 4 * i, b0 = 8 * J[i4];
    const r0x = dq[b0], r0y = dq[b0 + 1], r0z = dq[b0 + 2], r0w = dq[b0 + 3];
    let rx = 0, ry = 0, rz = 0, rw = 0, dx = 0, dy = 0, dz = 0, dw = 0;
    for (let j = 0; j < 4; j++) {
      const w = W[i4 + j]; if (w === 0) continue;
      const b = 8 * J[i4 + j];
      // signe aligné sur l'os dominant (court chemin)
      const s = (dq[b] * r0x + dq[b + 1] * r0y + dq[b + 2] * r0z + dq[b + 3] * r0w) < 0 ? -w : w;
      rx += s * dq[b]; ry += s * dq[b + 1]; rz += s * dq[b + 2]; rw += s * dq[b + 3];
      dx += s * dq[b + 4]; dy += s * dq[b + 5]; dz += s * dq[b + 6]; dw += s * dq[b + 7];
    }
    const l = 1 / Math.sqrt(rx * rx + ry * ry + rz * rz + rw * rw);
    rx *= l; ry *= l; rz *= l; rw *= l; dx *= l; dy *= l; dz *= l; dw *= l;
    // translation = 2·(rw·d − dw·r + r × d)
    const tx = 2 * (rw * dx - dw * rx + ry * dz - rz * dy), ty = 2 * (rw * dy - dw * ry + rz * dx - rx * dz),
      tz = 2 * (rw * dz - dw * rz + rx * dy - ry * dx);
    const o = 3 * i;
    let vx = _mp[o], vy = _mp[o + 1], vz = _mp[o + 2];
    let cx = 2 * (ry * vz - rz * vy), cy = 2 * (rz * vx - rx * vz), cz = 2 * (rx * vy - ry * vx);
    P[o] = vx + rw * cx + ry * cz - rz * cy + tx; P[o + 1] = vy + rw * cy + rz * cx - rx * cz + ty; P[o + 2] = vz + rw * cz + rx * cy - ry * cx + tz;
    vx = _mn[o]; vy = _mn[o + 1]; vz = _mn[o + 2];
    cx = 2 * (ry * vz - rz * vy); cy = 2 * (rz * vx - rx * vz); cz = 2 * (rx * vy - ry * vx);
    let nx = vx + rw * cx + ry * cz - rz * cy, ny = vy + rw * cy + rz * cx - rx * cz, nz = vz + rw * cz + rx * cy - ry * cx;
    const ln = 1 / (Math.sqrt(nx * nx + ny * ny + nz * nz) || 1);
    N[o] = nx * ln; N[o + 1] = ny * ln; N[o + 2] = nz * ln;
  }
  return F;
}

/* =====================================================================================================================
   8. Contacts : capsules des phalanges + surface de la paume ; penetration(pose) = contact le plus profond (cm)
   Les rayons sont MESURÉS sur la peau du GLB au chargement (centile 90 de la distance à l'axe, latéral et palmaire
   séparés : deux doigts côte à côte se touchent par leurs flancs, un bout se pose sur la paume par sa pulpe).
   ===================================================================================================================== */
// Budget du solveur (piste V de la v1, en cm) : une articulation BLOQUÉE s'assied à PEN_SEAT, un geste peut aller
// jusqu'à PEN_MAX ; c'est l'enfoncement de chair admis (mobilite.md P2.1 : 1,5–3 mm ; M1 : poing 2,2, V 2,5 mm).
const PEN_SEAT = 0.15, PEN_MAX = 0.30, SLIDE = 4;
// part de la P1 cachée dans la paume (exclue du contact entre doigts) : réglée sur la peau (JOURNAL, « contacts »)
let VIS_P1 = 0.2;
// bout contre paume : la pulpe s'écrase sur 1,5 à 1,7 mm de plus que la sphère de la capsule ne le dit (mesuré sur la
// peau : poing serré, Index (1) — annulaire et auriculaire sur l'hypothénar, 1,3 mm « capsules » contre 3,0 sur la peau)
const PAUME_MARGE = 0.16;
let SEGS = null, PAUME = null;
function construireContacts() {
  const a = A, J = a.json;
  SEGS = [];
  const ajoute = (chaine, g, os, fin, bout) => SEGS.push({chaine, g, os: OSI[os], fin: fin ? OSI[fin] : -1, bout: bout || null});
  DOIGTS.forEach(k => { ajoute(k, 0, k + '_p1', k + '_p2'); ajoute(k, 1, k + '_p2', k + '_p3'); ajoute(k, 2, k + '_p3', null, J.os[k + '_p3'].bout); });
  ajoute('pouce', 0, 'mc1', 'pouce_p1'); ajoute('pouce', 1, 'pouce_p1', 'pouce_p2'); ajoute('pouce', 2, 'pouce_p2', null, J.os.pouce_p2.bout);
  // rayons mesurés : sommets portés à ≥ 85 % par l'os du segment, hors ongle, entre 15 et 85 % de sa longueur
  SEGS.forEach(s => {
    const p0 = a.Cb[s.os], p1 = s.fin >= 0 ? a.Cb[s.fin] : s.bout, ax = vsub(p1, p0), L = vlen(ax), u = vsc(ax, 1 / L);
    const X = qrot(a.Qb[s.os], [1, 0, 0]), Z = qrot(a.Qb[s.os], [0, 0, 1]);
    // profil POLAIRE de la section (16 secteurs autour de l'os) : la section d'un doigt est un trapèze arrondi, plus
    // large côté paume (M1 étape 4b) ; une ellipse sous-estimait de 3,6 mm le contact des bases de P1 côté paume
    // (B : annulaire–auriculaire 1,0 mm « capsules » contre 4,6 mm sur la peau)
    // … et deux profils le long de l'os (moitié proximale, moitié distale) : un doigt s'affine vers le bout (pouce : 22 mm
    // à l'IP, 21 × 16 à la pulpe) ; un rayon constant arrêtait le pouce 1 cm avant la pulpe de l'index (pince : 2,8 mm
    // de « contact » capsules pour 0 sur la peau)
    const NB = 16, sect = [0, 1].map(() => Array.from({length: NB}, () => [])), lat = [], pal = [], dos = [];
    for (let i = 0; i < a.n; i++) {
      if (a.J[4 * i] !== s.os || a.W[4 * i] < 0.85 || a.masque[2 * i] > 0.5) continue;
      const v = [a.rest[3 * i] - p0[0], a.rest[3 * i + 1] - p0[1], a.rest[3 * i + 2] - p0[2]], t = vdot(v, u) / L;
      if (t < 0.1 || t > 0.9) continue;
      const x = vdot(v, X), z = vdot(v, Z);
      if (t >= 0.15 && t <= 0.85) { if (Math.abs(z) < 0.5 * Math.abs(x)) lat.push(Math.abs(x)); else if (z > 0) pal.push(z); else dos.push(-z); }
      const ph = Math.atan2(z, x), b = ((Math.round(ph / (2 * Math.PI) * NB) % NB) + NB) % NB;
      sect[t < 0.5 ? 0 : 1][b].push(Math.hypot(x, z));
    }
    const c90 = l => { if (!l.length) return 0.8; l.sort((x, y) => x - y); return l[Math.floor(0.9 * (l.length - 1))]; };
    s.L = L; s.rLat = c90(lat); s.rPal = c90(pal); s.rDos = c90(dos); s.r = (s.rLat + 0.5 * (s.rPal + s.rDos)) / 2;
    s.polaire = sect.map(sc => { const pr = sc.map(l => l.length ? c90(l) : 0); for (let b = 0; b < NB; b++) if (!pr[b]) pr[b] = s.r; return pr; });
    // le « bout » de M1 est SUR la peau, au bout du doigt : la capsule s'arrête un rayon (palmaire) avant, sinon la
    // sphère de la pulpe dépasse le doigt de 6 à 9 mm (mesuré : bout de l'annulaire sur la paume 7,3 mm « capsules »
    // contre 3,0 mm sur la peau)
    if (s.bout) s.bout = vsub(s.bout, vsc(u, Math.min(s.rPal, 0.45 * L)));
  });
  // surface de la paume : grille (pas 2,5 mm) de la face palmaire (hf) et dorsale (hb) des sommets portés à ≥ 90 % par
  // le poignet et les métacarpiens, dans le repère de LIAISON ; chaque case retient son métacarpien dominant (l'arc
  // déplace l'hypothénar). Deux grilles : celle des doigts (thénar compris), celle du pouce (sans le thénar, qui est
  // le pouce lui-même). Lecture BILINÉAIRE (v1 : la paume en escalier faisait sauter le solveur d'une case à l'autre).
  const PAS = 0.25, X0 = -5.5, Y0 = -1.5, NX = 44, NY = 50;
  const grille = sansThenar => {
    const hf = new Float32Array(NX * NY).fill(-1e9), hb = new Float32Array(NX * NY).fill(1e9), os = new Int8Array(NX * NY).fill(-1);
    const cpt = new Float32Array(NX * NY * 4);
    for (let i = 0; i < a.n; i++) {
      let wp = 0, w1 = 0; const cmpt = [0, 0, 0, 0];
      for (let j = 0; j < 4; j++) { const b = a.J[4 * i + j], w = a.W[4 * i + j];
        if (b === OSI.poignet || b === OSI.mc1 || b === OSI.mc2 || b === OSI.mc3 || b === OSI.mc4 || b === OSI.mc5) wp += w;
        if (b === OSI.mc1) w1 += w;
        const m = [OSI.mc2, OSI.mc3, OSI.mc4, OSI.mc5].indexOf(b); if (m >= 0) cmpt[m] += w; }
      if (wp < 0.9 || (sansThenar && w1 > 0.3)) continue;
      const x = a.rest[3 * i], y = a.rest[3 * i + 1], z = a.rest[3 * i + 2], nz = a.restN[3 * i + 2];
      const cx = Math.round((x - X0) / PAS), cy = Math.round((y - Y0) / PAS);
      if (cx < 0 || cy < 0 || cx >= NX || cy >= NY) continue;
      const c = cy * NX + cx;
      if (nz > 0.15) hf[c] = Math.max(hf[c], z); else if (nz < -0.15) hb[c] = Math.min(hb[c], z);
      for (let m = 0; m < 4; m++) cpt[4 * c + m] += cmpt[m];
    }
    for (let c = 0; c < NX * NY; c++) { let bm = -1, bv = 0; for (let m = 0; m < 4; m++) if (cpt[4 * c + m] > bv) { bv = cpt[4 * c + m]; bm = m; }
      os[c] = bm >= 0 ? [OSI.mc2, OSI.mc3, OSI.mc4, OSI.mc5][bm] : OSI.mc3; }
    // trous (cases sans sommet entre deux qui en ont) : moyenne des voisines, deux passes
    for (let pass = 0; pass < 2; pass++) {
      const f2 = hf.slice(), b2 = hb.slice();
      for (let cy = 1; cy < NY - 1; cy++) for (let cx = 1; cx < NX - 1; cx++) {
        const c = cy * NX + cx;
        if (hf[c] < -1e8) { let s = 0, k = 0; [[-1, 0], [1, 0], [0, -1], [0, 1]].forEach(([dx, dy]) => { const v = hf[c + dy * NX + dx]; if (v > -1e8) { s += v; k++; } }); if (k >= 3) f2[c] = s / k; }
        if (hb[c] > 1e8) { let s = 0, k = 0; [[-1, 0], [1, 0], [0, -1], [0, 1]].forEach(([dx, dy]) => { const v = hb[c + dy * NX + dx]; if (v < 1e8) { s += v; k++; } }); if (k >= 3) b2[c] = s / k; }
      }
      hf.set(f2); hb.set(b2);
    }
    return {hf, hb, os};
  };
  PAUME = {PAS, X0, Y0, NX, NY, doigts: grille(false), pouce: grille(true)};
}
// hauteurs (avant, arrière) de la paume au point (x, y) du repère de liaison, bilinéaire ; null hors de la paume
function hauteurPaume(G, x, y) {
  const P = PAUME, fx = (x - P.X0) / P.PAS, fy = (y - P.Y0) / P.PAS, cx = Math.floor(fx), cy = Math.floor(fy);
  if (cx < 0 || cy < 0 || cx >= P.NX - 1 || cy >= P.NY - 1) return null;
  const tx = fx - cx, ty = fy - cy, c = cy * P.NX + cx, idx = [c, c + 1, c + P.NX, c + P.NX + 1], wt = [(1 - tx) * (1 - ty), tx * (1 - ty), (1 - tx) * ty, tx * ty];
  let f = 0, b = 0, wf = 0, wb = 0;
  for (let j = 0; j < 4; j++) { const h = G.hf[idx[j]], k = G.hb[idx[j]];
    if (h > -1e8) { f += wt[j] * h; wf += wt[j]; } if (k < 1e8) { b += wt[j] * k; wb += wt[j]; } }
  if (wf < 0.5 || wb < 0.5) return null;   // bord de la paume : au moins la moitié des coins valides
  return [f / wf, b / wb, G.os[idx[wt.indexOf(Math.max(...wt))]]];
}
// rayon d'un segment dans une direction (monde) : ellipse latéral (X local) × palmaire (+Z) ou dorsal (−Z) ; une
// phalange n'est pas un cylindre (index P1 : 10,4 mm de côté, 9,5 côté paume, 7,5 côté dos)
function rayonVers(F, s, d, tSeg) {
  const l = qrot(qconj(F.Q[s.os]), d), x = l[0], z = l[2];
  if (Math.hypot(x, z) < 1e-9) return s.r;
  const NB = 16, f = ((Math.atan2(z, x) / (2 * Math.PI) * NB) % NB + NB) % NB, b0 = Math.floor(f), t = f - b0;
  const r = pr => pr[b0] * (1 - t) + pr[(b0 + 1) % NB] * t;
  const u = clamp(((tSeg === undefined ? 0.5 : tSeg) - 0.3) / 0.4, 0, 1);   // proximal (t ≤ 0,3) → distal (t ≥ 0,7)
  return r(s.polaire[0]) * (1 - u) + r(s.polaire[1]) * u;
}
function extremites(F, s) { return [F.C[s.os], s.fin >= 0 ? F.C[s.fin] : pointPose(F, s.os, s.bout)]; }
// penetration(pose) → profondeur (cm) du contact le plus profond ; detail = true rend aussi {paire, profondeur}
function penetration(pose, detail) {
  const p = pose && pose.pouce && typeof pose.prono === 'number' ? pose : normalise(pose);
  const F = fk(p), ex = SEGS.map(s => extremites(F, s));
  let mx = 0, paire = '';
  const paires = detail ? {} : null, chaines = detail ? {} : null;
  const add = (o, nom) => {
    if (o > mx) { mx = o; paire = nom; }
    if (paires && o > 0) { paires[nom] = Math.max(paires[nom] || 0, o);
      nom.split('/').forEach(x => { const k = x.split('_')[0]; if (k !== 'paume' && k !== 'lui-même' && k !== 'vers le poignet') chaines[k] = Math.max(chaines[k] || 0, o); }); }
  };
  // 1. paume : P2 et P3 des doigts (la P1 est attachée à la paume), P1 et P2 du pouce (sans le thénar)
  const versLiaison = (b, q) => vadd(qrot(qmul(A.Qb[b], qconj(F.Q[b])), vsub(q, F.C[b])), A.Cb[b]);
  SEGS.forEach((s, i) => {
    if (s.g === 0) return;
    const G = s.chaine === 'pouce' ? PAUME.pouce : PAUME.doigts, [a0, a1] = ex[i];
    [0.25, 0.6, 1].forEach(fr => {
      const q = vlerp(a0, a1, fr), r = s.rPal + PAUME_MARGE;
      let ql = versLiaison(OSI.mc3, q), h = hauteurPaume(G, ql[0], ql[1]);
      if (h && h[2] !== OSI.mc3) { ql = versLiaison(h[2], q); h = hauteurPaume(G, ql[0], ql[1]); }
      if (!h) return;
      const avant = h[0] + r - ql[2], arriere = ql[2] + r - h[1];
      if (avant > 0 && arriere > 0) add(Math.min(avant, arriere), s.chaine + (s.g === 2 ? '_bout' : '_p2') + '/paume');
    });
  });
  // 2. doigts entre eux (flancs) : P1 sans son tiers caché dans la paume, P2, P3 ; et le pouce contre chaque doigt
  const vis = (i) => { const s = SEGS[i], e = ex[i]; return s.g === 0 && s.chaine !== 'pouce' ? [vlerp(e[0], e[1], VIS_P1), e[1]] : e; };
  for (let i = 0; i < SEGS.length; i++) for (let j = i + 1; j < SEGS.length; j++) {
    const si = SEGS[i], sj = SEGS[j];
    if (si.chaine === sj.chaine) continue;
    const pouce = si.chaine === 'pouce' || sj.chaine === 'pouce';
    if (pouce && ((si.chaine === 'pouce' && si.g === 0) || (sj.chaine === 'pouce' && sj.g === 0))) continue;
    const [a0, a1] = vis(i), [b0, b1] = vis(j), r = segSeg(a0, a1, b0, b1);
    if (r.d > 3) continue;
    const Pa = vlerp(a0, a1, r.s), Pb = vlerp(b0, b1, r.t), d = vsub(Pb, Pa);
    // paramètre le long du segment ENTIER (la partie visible de P1 commence à VIS_P1)
    const ti = si.g === 0 && si.chaine !== 'pouce' ? VIS_P1 + (1 - VIS_P1) * r.s : r.s, tj = sj.g === 0 && sj.chaine !== 'pouce' ? VIS_P1 + (1 - VIS_P1) * r.t : r.t;
    const ri = rayonVers(F, si, d, ti), rj = rayonVers(F, sj, vsc(d, -1), tj);
    add(ri + rj - r.d, si.chaine + '/' + sj.chaine);
  }
  // 3. un doigt ne se replie pas dans lui-même (P3 contre P1)
  DOIGTS.forEach((k, n) => { const i3 = 3 * n + 2, i1 = 3 * n, [a0, a1] = ex[i3], [b0, b1] = vis(i1), r = segSeg(a0, a1, b0, b1);
    add(SEGS[i3].rPal + SEGS[i1].rPal - r.d, k + '/lui-même'); });
  // (pulpe contre pulpe dans P3/P1 : les deux côtés palmaires se font face)
  // 4. posture du pouce (v1) : jamais le bout tourné vers le poignet (direction de P2 dans le repère du 3e rayon)
  {
    const versMain = qmul(A.Qb[OSI.mc3], qconj(F.Q[OSI.mc3]));
    const dir = i => { const [a0, a1] = ex[i], d = qrot(versMain, vsub(a1, a0)), l = vlen(d) || 1; return d[1] / l; };
    const d2 = dir(14), d1 = dir(13);          // P2 (IP → bout) et P1 du pouce
    if (d2 < -0.45) add((-0.45 - d2) * 2, 'pouce/vers le poignet');
    if (d1 < -0.2) add((-0.2 - d1) * 2, 'pouce/vers le poignet');
  }
  if (!detail) return mx;
  // profondeurs EFFECTIVES (celles que juge le solveur) : capsule ± l'écart capsules → peau mesuré pour la famille du
  // contact (margeFamille) ; `paires` et `profondeur` restent celles des capsules
  const chainesEff = {}; let profEff = 0;
  for (const nom in paires) {
    const e = paires[nom] + margeFamille(nom, p); if (e > profEff) profEff = e;
    nom.split('/').forEach(x => { const k = x.split('_')[0]; if (k !== 'paume' && k !== 'lui-même' && k !== 'vers le poignet') chainesEff[k] = Math.max(chainesEff[k] || 0, e); });
  }
  return {profondeur: mx, paire, paires, chaines, chainesEff, profEff};
}
// Écart capsules → peau par famille de contacts (mesuré, v2/tests/engine_contacts.py et relecture adverse) : entre deux
// doigts REPLIÉS côte à côte (MCP ≥ 70°), les capsules SURESTIMENT la peau de 0,17 à 0,64 mm (poing, MCP 90 partout :
// capsules 3,21 mm / peau 3,00 ; Cornes 3,65 / 3,01 ; Lettre I 2,83 / 2,66 ; Y 2,60 / 2,28 ; Poing pouce dedans 2,97 /
// 2,65). Le solveur les juge donc MARGE_REPLIES plus bas. Sans cela le majeur du poing s'arrêtait à MCP 78,8° (siège
// 2,6 mm de capsules = 2,2 mm de peau seulement) : un doigt dépassait du poing.
const replies = (nom, p) => { const ks = nom.split('/').map(x => x.split('_')[0]); return ks.length === 2 && ks.every(k => DOIGTS.includes(k)) && ks.every(k => p[k].mcp >= 70); };
function margeFamille(nom, p) { return replies(nom, p) ? -MARGE_REPLIES : 0; }
// 0,3 mm et non 0,17 (le plus petit écart mesuré) : le poing PLI 90 / 105 / 70 sur les quatre doigts fait 3,21 mm de
// capsules (index / majeur) pour 3,00 mm de peau — à 0,2 mm il restait jugé à 3,01, juste au-dessus du budget du geste
// (3,0) : fermer les quatre doigts ensemble était alors refusé d'un bloc et le solveur repartait par morceaux. Le
// contrôle sur la peau des presets reste celui de M1 (≤ 3 mm, tests/engine_presets.py).
const MARGE_REPLIES = 0.03;

/* =====================================================================================================================
   9. Solveur : de la pose de départ vers la cible, chaque articulation poussée aussi loin que le contact le permet
   (piste V de la v1) : celles qui DÉGAGENT de la place d'abord, puis de la plus sollicitée à la moins, second tour
   pour celles qu'un voisin bloquait ; un bout posé sur la paume GLISSE (la MCP du même doigt cède ≤ SLIDE = 4°).
   ===================================================================================================================== */
const CHEMINS = [['poignet', 'flex'], ['poignet', 'dev'], [null, 'prono'], [null, 'arc'],
  ['pouce', 'av'], ['pouce', 'rap'], ['pouce', 'mcp'], ['pouce', 'ip'], ['pouce', 'abdMcp']];
DOIGTS.forEach(k => ['mcp', 'pip', 'dip', 'ab', 'rot'].forEach(c => CHEMINS.push([k, c])));
const lit = (p, c) => c[0] ? p[c[0]][c[1]] : p[c[1]];
const ecrit = (p, c, v) => { if (c[0]) p[c[0]][c[1]] = v; else p[c[1]] = v; };
// Chaque contact a son budget (v1 : « deux contacts sont deux contacts ») : bouger une chaîne n'est jugé que sur les
// contacts QUI LA CONCERNENT. Mesuré : avec la pénétration globale, fermer l'auriculaire après les trois autres doigts
// butait à MCP 1,4° — l'arc automatique (piloté par sa MCP) déplace le 4e rayon et le contact majeur–annulaire, déjà au
// plafond, passait de 3,07 à 3,24 mm à mi-chemin ; l'auriculaire, lui, ne touchait rien.
function penChaine(p, k) { const d = penetration(p, true); return k ? d.chainesEff[k] || 0 : d.profEff; }
const penEff = p => penetration(p, true).profEff;
function solve(depart, cible, opts) {
  const from = constrain(depart, opts), to = constrain(cible, opts);
  if (penEff(to) <= Math.max(penEff(from) + 0.005, PEN_MAX)) return to;
  let cur = clone(from);
  const chaineDe = c => (c[0] && c[0] !== 'poignet') ? c[0] : null;   // poignet, prono, arc : jugés sur toute la main
  // siège : là où s'assied une articulation bloquée (PEN_SEAT, la moitié du budget : la marionnette garde de la marge
  // pour le geste suivant) ; settle (presets) s'assied plus près du contact (opts.siege)
  const siege = opts && opts.siege ? opts.siege : PEN_SEAT;
  const budget = k => { const p0 = penChaine(from, k); return {ref: Math.max(p0 + 0.005, PEN_MAX), seat: Math.max(p0 + 0.005, siege)}; };
  const ch = [];
  CHEMINS.forEach(c => {
    const d = Math.abs(lit(to, c) - lit(from, c)); if (d < 0.5 && !(c[1] === 'arc' && d > 0.01)) return;
    const k = chaineDe(c), t1 = clone(from); ecrit(t1, c, lit(to, c)); ch.push([c, d, penChaine(t1, k) - penChaine(from, k)]);
  });
  // 0. tout ensemble d'abord, jusqu'au premier contact : quand quatre doigts se ferment à la fois, ils se partagent la
  //    place (fermés un par un, l'index prenait tout : majeur arrêté à MCP 73° dans le poing contre 84–90 sur les photos)
  {
    const p0 = penEff(from), lim = Math.max(p0 + 0.005, siege), tgt = clone(cur);
    const met = m => ch.forEach(([c]) => ecrit(tgt, c, lit(from, c) + (lit(to, c) - lit(from, c)) * m));
    let lo = 0, hi = 1;
    for (let i = 0; i < 7; i++) { const m = (lo + hi) / 2; met(m); if (penEff(tgt) <= lim) lo = m; else hi = m; }
    if (lo > 0) { met(lo); cur = clone(tgt); }
  }
  // 1. chaîne par chaîne (doigt, pouce, poignet…) : toutes ses articulations ENSEMBLE vers la cible, aussi loin que le
  //    contact le permet. Un doigt qui se ferme plie MCP, IPP et IPD en même temps : articulation par articulation, l'IPP
  //    d'abord recourbait le doigt et la MCP ne pouvait plus fermer le poing. Les chaînes qui DÉGAGENT de la place passent
  //    d'abord.
  const groupes = {};
  ch.forEach(c => { const k = chaineDe(c[0]) || '*'; (groupes[k] = groupes[k] || {k, chemins: [], gain: 0}).chemins.push(c[0]); });
  Object.values(groupes).forEach(g => { const t1 = clone(from); g.chemins.forEach(c => ecrit(t1, c, lit(to, c))); g.gain = penChaine(t1, g.k === '*' ? null : g.k) - penChaine(from, g.k === '*' ? null : g.k); });
  const avance = g => {
    const k = g.k === '*' ? null : g.k, {ref, seat} = budget(k);
    const v0 = g.chemins.map(c => lit(cur, c)), v1 = g.chemins.map(c => lit(to, c)), tgt = clone(cur);
    const met = m => g.chemins.forEach((c, i) => ecrit(tgt, c, v0[i] + (v1[i] - v0[i]) * m));
    met(1); if (penChaine(tgt, k) <= ref) { cur = clone(tgt); return; }
    const lim = Math.max(seat, penChaine(cur, k));
    let lo = 0, hi = 1;
    for (let i = 0; i < 7; i++) { const m = (lo + hi) / 2; met(m); if (penChaine(tgt, k) <= lim) lo = m; else hi = m; }
    met(lo); cur = clone(tgt);
  };
  // REMPLISSAGE : les chaînes qui se ferment ensemble avancent ENSEMBLE (même fraction de leur course) jusqu'à ce que
  // l'une bute ; elle s'arrête là, les autres continuent, et ainsi de suite. Fermées une à une (ordre du gain), la
  // première prenait toute la place : relecture adverse, fermer les quatre doigts depuis la main ouverte donnait
  // MCP 76 / 90 / 90 / 88, depuis B 74 / 55 / 90 / 86, depuis Quatre (4) 90 / 65 / 59 / 83.
  const remplir = gs => {
    const A = gs.map(g => { const k = g.k, b = budget(k); return {g, k, v0: g.chemins.map(c => lit(cur, c)), v1: g.chemins.map(c => lit(to, c)), m: 0, ref: b.ref, lim: Math.max(b.seat, penChaine(cur, k))}; });
    const tgt = clone(cur), met = (a, m) => a.g.chemins.forEach((c, i) => ecrit(tgt, c, a.v0[i] + (a.v1[i] - a.v0[i]) * m));
    let d;
    const pc = a => d.chainesEff[a.k] || 0;
    A.forEach(a => met(a, 1)); d = penetration(tgt, true);
    if (A.every(a => pc(a) <= a.ref)) { cur = clone(tgt); return; }
    let actifs = A.slice();
    for (let tour = 0; tour <= A.length && actifs.length; tour++) {
      const pose = t => actifs.forEach(a => met(a, a.m + (1 - a.m) * t)), ok = () => { d = penetration(tgt, true); return actifs.every(a => pc(a) <= a.lim); };
      pose(1); if (ok()) { actifs.forEach(a => a.m = 1); break; }
      let lo = 0, hi = 1;
      for (let i = 0; i < 7; i++) { const t = (lo + hi) / 2; pose(t); if (ok()) lo = t; else hi = t; }
      pose(hi); ok(); const bloques = actifs.filter(a => pc(a) > a.lim);
      // un doigt arrêté par le FLANC d'un voisin qui se ferme AVEC lui n'est pas assis au siège : ce contact grandit
      // continûment pendant toute la fermeture (les axes obliques des MCP font converger les P1), c'est de la chair qui
      // se range, pas un obstacle ; s'arrêter à 1,5 mm laissait le poing à MCP 71° depuis la main ouverte, 74 / 55 depuis
      // B (doigts serrés, déjà au contact) ; il va jusqu'au budget du geste (PEN_MAX)
      const ensemble = new Set(A.map(x => x.k));
      const flanc = nom => { const ks = nom.split('/').map(x => x.split('_')[0]); return ks.length === 2 && ks.every(k => DOIGTS.includes(k) && ensemble.has(k)); };
      const releves = bloques.filter(a => a.lim < a.ref && Object.keys(d.paires).some(nom => nom.split('/').some(x => x.split('_')[0] === a.k) && flanc(nom) && d.paires[nom] + margeFamille(nom, tgt) > a.lim));
      releves.forEach(a => a.lim = a.ref);
      actifs.forEach(a => { a.m = a.m + (1 - a.m) * lo; met(a, a.m); });
      if (!bloques.length) break;
      actifs = actifs.filter(a => !bloques.includes(a) || releves.includes(a));
    }
    A.forEach(a => met(a, a.m)); cur = clone(tgt);
  };
  const gs = Object.values(groupes).sort((a, b) => a.gain - b.gain);
  // d'abord, un par un : le poignet, la pronation, l'arc (jugés sur toute la main) et les chaînes qui DÉGAGENT de la place
  gs.filter(g => g.k === '*' || g.gain < -0.002).forEach(avance);
  const ens = gs.filter(g => !(g.k === '*' || g.gain < -0.002));
  if (ens.length === 1) avance(ens[0]); else if (ens.length) remplir(ens);
  // 2. puis chaque articulation seule (v1, piste V) : celles qui dégagent d'abord, de la plus sollicitée à la moins ;
  //    un bout posé sur la paume GLISSE (la MCP du même doigt cède ≤ SLIDE = 4°) ; second tour pour celles qu'un voisin
  //    bloquait. On ne recule jamais sur une articulation que l'on n'a pas demandé de bouger.
  ch.sort((a, b) => (a[2] - b[2]) || (b[1] - a[1]));
  const pousse = ([c]) => {
    if (Math.abs(lit(to, c) - lit(cur, c)) < 0.25) return true;
    const k = chaineDe(c), {ref, seat} = budget(k);
    const tgt = clone(cur); ecrit(tgt, c, lit(to, c));
    if (penChaine(tgt, k) <= ref) { cur = tgt; return true; }
    const lim = Math.max(seat, penChaine(cur, k));
    if (k && k !== 'pouce' && c[1] !== 'mcp' && !(opts && opts.fige && opts.fige[k + '.mcp'])) {
      const m0 = cur[k].mcp, sl = Math.min(SLIDE, m0 - borne(k + '_p1', 'flex')[0]);
      tgt[k].mcp = m0 - sl;
      if (sl > 0 && penChaine(tgt, k) <= lim) {
        let lo = 0, hi = 1;
        for (let i = 0; i < 6; i++) { const m = (lo + hi) / 2; tgt[k].mcp = m0 - sl * m; if (penChaine(tgt, k) <= lim) hi = m; else lo = m; }
        tgt[k].mcp = m0 - sl * hi; cur = tgt; return true;
      }
      tgt[k].mcp = m0;
    }
    // ENROULEMENT : la MCP d'un doigt qui se ferme bute par son bout (sur le pouce couché en travers de la paume, sur la
    // paume) ; une main referme alors la MCP et laisse l'IPP et l'IPD s'ouvrir un peu, le doigt s'enroule PAR-DESSUS
    // l'obstacle. On cherche la plus petite ouverture (IPP jusqu'à −50°, IPD jusqu'à −40°) qui laisse passer la MCP.
    // Relecture adverse : fermer les quatre doigts depuis B (pouce en travers de la paume) donnait MCP 74 / 55 / 90 / 86,
    // depuis Quatre (4) 90 / 65 / 59 / 83 — le majeur et l'annulaire arrêtés par le bout sur le pouce.
    if (k && DOIGTS.includes(k) && c[1] === 'mcp' && lit(to, c) > lit(cur, c) && !(opts && opts.fige && (opts.fige[k + '.pip'] || opts.fige[k + '.dip']))) {
      const p0 = cur[k].pip, d0 = cur[k].dip, ouvre = r => { tgt[k].pip = p0 - r * Math.min(p0, 50); tgt[k].dip = d0 - r * Math.min(d0, 40); };
      ecrit(tgt, c, lit(to, c)); ouvre(1);
      if (penChaine(constrain(tgt), k) <= lim) {
        let lo = 0, hi = 1;
        for (let i = 0; i < 6; i++) { const m = (lo + hi) / 2; ouvre(m); if (penChaine(constrain(tgt), k) <= lim) hi = m; else lo = m; }
        ouvre(hi); cur = constrain(tgt); return true;
      }
      tgt[k].pip = p0; tgt[k].dip = d0;
    }
    let lo = 0, hi = 1; const v0 = lit(cur, c), v1 = lit(to, c);
    for (let i = 0; i < 7; i++) { const m = (lo + hi) / 2; ecrit(tgt, c, v0 + (v1 - v0) * m); if (penChaine(tgt, k) <= lim) lo = m; else hi = m; }
    ecrit(cur, c, v0 + (v1 - v0) * lo); return lo > 0.995;
  };
  const reste = ch.filter(c => !pousse(c));
  reste.forEach(pousse);
  return cur;
}
// passage d'une configuration à une autre (v1 settle) : le pouce s'écarte, chaque doigt va à sa place, puis le pouce ;
// le résultat ne dépend pas de la pose précédente
// (siège 2,6 mm : une configuration de référence va jusqu'au contact ; le contrôle sur la peau reste ≤ 3 mm)
const SIEGE_PRESET = 0.26;
function settle(depart, cible) {
  let cur = constrain(depart); const to = constrain(cible), o = {siege: SIEGE_PRESET};
  { const t = clone(cur); t.pouce = {av: Math.max(cur.pouce.av, 20), rap: -10, mcp: 0, ip: 0, abdMcp: 0}; cur = solve(cur, t, o); }
  { const t = clone(cur); ['poignet', 'prono', 'arc'].forEach(k => t[k] = clone(to[k])); cur = solve(cur, t, o); }
  { const t = clone(cur); DOIGTS.forEach(k => t[k] = clone(to[k])); cur = solve(cur, t, o); }   // les quatre doigts ensemble
  { const t = clone(cur); t.pouce = clone(to.pouce); cur = solve(cur, t, o); }
  return cur;
}
// pulpe d'un doigt (point de contact, SUR la peau) : centre de la sphère du bout (capsule raccourcie d'un rayon),
// poussé côté paume (+Z local, « Z = pulpe » de M1) de 0,85 rayon palmaire
function pulpe(F, chaine) {
  const s = SEGS.find(x => x.chaine === chaine && x.g === 2), [, a1] = extremites(F, s);
  return vadd(a1, vsc(qrot(F.Q[s.os], [0, 0, 1]), 0.85 * s.rPal));
}
// reach(pose, cible) : amène la pulpe du pouce vers un point (fonction de la cinématique) en ne touchant qu'au pouce,
// sans dépasser le budget de contact (v1 thumbReach) — sert à régler les presets O, pince, F, D, becs
// champs : chemins [doigt, champ] que la descente peut bouger (défaut : les quatre du pouce ; pour une pince on y
// ajoute l'index : les deux pulpes vont l'une vers l'autre)
function reach(pose, cibleFn, champs) {
  let cur = constrain(pose); const ref = Math.max(penetration(cur) + 0.005, PEN_MAX);
  champs = (champs || ['av', 'rap', 'mcp', 'ip']).map(c => typeof c === 'string' ? ['pouce', c] : c);
  const cout = p => { const F = fk(p); return vlen(vsub(pulpe(F, 'pouce'), cibleFn(F))); };
  let best = cout(cur);
  for (const pas of [8, 4, 2, 1, 0.5]) for (let boucle = 0; boucle < 30; boucle++) {
    let bouge = false;
    for (const c of champs) for (const sg of [1, -1]) {
      const t = clone(cur); ecrit(t, c, lit(t, c) + sg * pas); const cc = constrain(t);
      if (Math.abs(lit(cc, c) - lit(cur, c)) < 1e-6) continue;
      const v = cout(cc); if (v < best - 1e-4 && penetration(cc) <= ref) { cur = cc; best = v; bouge = true; }
    }
    if (!bouge) break;
  }
  return {pose: cur, ecart: best};
}

/* =====================================================================================================================
   10. Plis : courbes barycentriques de hand_v2.json → rubans (rendu.md § 4 et § 7.2, 4b)
   ===================================================================================================================== */
let PLIS = null;
function construirePlis() {
  const J = A.json, idx = A.index;
  let total = 0;
  const angleDe = (fn, os, p) => {
    if (os === 'poignet') return p.poignet.flex;
    if (os === 'mc1') return fn === 'av' ? p.pouce.av : p.pouce.rap;
    if (os === 'pouce_p1') return p.pouce.mcp;
    if (os === 'pouce_p2') return p.pouce.ip;
    const [k, ph] = os.split('_'); return p[k][{p1: 'mcp', p2: 'pip', p3: 'dip'}[ph]];
  };
  const courbes = (J.plis || []).map(c => {
    const pts = c.points.map(([t, b0, b1, b2]) => [idx[3 * t], idx[3 * t + 1], idx[3 * t + 2], b0, b1, b2]);
    // abscisse curviligne au repos (effilement aux deux bouts)
    const pos = pts.map(q => [0, 1, 2].map(c3 => q[3] * A.rest[3 * q[0] + c3] + q[4] * A.rest[3 * q[1] + c3] + q[5] * A.rest[3 * q[2] + c3]));
    const s = [0]; for (let i = 1; i < pos.length; i++) s.push(s[i - 1] + vlen(vsub(pos[i], pos[i - 1])));
    const L = s[s.length - 1] || 1, tt = s.map(x => x / L);
    const termes = []; (c.visible || '').replace(/(\w+)\(([^)]*)\)/g, (_, fn, args) => { args.split(',').forEach(a => termes.push([fn, a.trim()])); });
    const dorsal = c.type === '=';
    // poids du type (fraction du contour, rendu.md § 4 « poids de trait hiérarchisés » : plis 0,4–0,6, contour 1)
    const g = c.groupe || c.nom;
    const poids = dorsal ? 0.42 : g.startsWith('paume_') ? 0.5 : g.startsWith('poignet') ? 0.4 : 0.45;
    // effilement : longs plis de la paume sur 12 % de leur longueur, plis courts des doigts sur 22 %
    const eff = L > 3 ? 0.12 : 0.22;
    const debut = total; total += pts.length;
    return {nom: c.nom, pts, tt, termes, dorsal, poids, eff, debut};
  });
  // visibilité pilotée par l'angle articulaire (hand_v2.json « plis_convention ») :
  //  « = » dorsal (ext) : plein tendu, effacé de 20° à 80° de flexion (la peau du dos s'étire : v1 piste R, photos
  //    2374/2375), un peu plus marqué en hyperextension ;
  //  pli palmaire (flex) : toujours tracé, fin au repos, creusé avec la flexion (0,45 → 1 de 0° à 70°) ;
  //  poignet : se creuse de −10° (extension) à 45° de flexion ; thénar et base du pouce : avec av / rap (0 → 45°).
  courbes.forEach(c => {
    c.vis = p => {
      if (c.dorsal) { let th = 0; c.termes.forEach(([fn, os]) => th = Math.max(th, angleDe(fn, os, p)));
        return (1 - sstep(20, 80, th)) * (1 + 0.4 * sstep(0, -25, th)); }
      let v = 0, cache = 1;
      c.termes.forEach(([fn, os]) => {
        const th = angleDe(fn, os, p);
        const x = os === 'poignet' ? sstep(-10, 45, th) : os === 'mc1' ? sstep(0, 45, th) : sstep(0, 70, th);
        v = Math.max(v, x);
        // un pli palmaire de doigt PLIÉ À FOND est au fond du repli (une vraie main ne le montre pas) : ce qui en
        // dépassait au bord du repli, vu en rasant, s'étirait en épines (relecture adverse : « trois échardes » dans le
        // tunnel du poing vu de profil : plis digitaux proximaux, au pied des doigts, sur la paroi du tunnel). Il s'efface
        // de 70 à 90° pour la MCP (le pli digito-palmaire est enfoui dès que la P1 se couche sur la paume), de 80 à 100°
        // pour l'IPP et l'IPD.
        if (/_p1$/.test(os) && !os.startsWith('pouce')) cache = Math.min(cache, 1 - sstep(70, 90, th));
        else if (/_p[23]$/.test(os) && !os.startsWith('pouce')) cache = Math.min(cache, 1 - sstep(80, 100, th));
      });
      return (0.45 + 0.55 * v) * cache;
    };
  });
  PLIS = {courbes, total};
}

/* =====================================================================================================================
   11. Rendu : un « pipeline » par renderer (le rendu hors écran de render(), et celui de la marionnette)
   ===================================================================================================================== */
// réglages du rendu (rendu.md § 7.3, à MESURER sur les planches : voir JOURNAL.md)
const RENDU = {
  // N·L où bascule l'ombre. Balayé sur « Repos », part d'ombre de la peau paume / dos (cible 16–24 %, dessin 16–18 %) :
  // 0,30 → 14,1 / 10,8 % ; 0,36 → 16,5 / 13,8 ; 0,40 → 18,2 / 16,2 ; 0,44 → 20,1 / 19,3. Retenu 0,41.
  seuil: 0.41,
  lisiere: 0.03,      // demi-lisière minimale en N·L (sinon fwidth)
  tonOmbre: 0.82,     // ton de l'ombre du dessin (texBack / texFront, CLAUDE.md)
  L: [-0.45, 0.55, 1],// lumière fixe en repère caméra (v1 LIGHT)
  frange: 0.45,       // frange libre : mélange vers le blanc (≈ ×1,35 plus claire, photo de l'utilisateur)
  recul: 0.27,        // cm : recul de la coque (0,25 u v1 ≈ 2,7 mm, rendu.md coque_variantes)
  dThr: 0.33,         // cm : saut de profondeur « une partie passe devant une autre » (0,3 u ≈ 3,3 mm, 1/5 d'un doigt)
  dGraze: 1.2,        // seuil × (1 + 1,2 (1 − |n.z|)) : une surface rasante ne fait pas un faux saut
  // frontière d'identité paume/doigt : tracée si saut ≥ porte × seuil. 0,35 (prototype) traçait des hachures au fond
  // des commissures (le flanc du doigt contre la palmure : ≈ 10 échardes rouges par commissure en mode débogage) ; à
  // 1,0 elles disparaissent et le pouce devant la paume (B, 4), les doigts repliés devant la paume (poing) restent cernés
  porte: 1.0,
  // cm : entre deux doigts, l'écart de profondeur JUSTE DE PART ET D'AUTRE de leur frontière (shaders.js, 4a) en deçà
  // duquel c'est un contact (le doigt d'identité la plus basse trace, un seul trait) ; au-delà, le plus proche trace.
  // 0,3 mm (v1 : 0,02 u) faisait basculer le trait d'un côté à l'autre le long d'un contact (deux doigts convergent :
  // l'écart y vaut quelques dixièmes de mm) — trait déchiqueté ; à 2,5 mm il reste d'un seul côté (relecture adverse)
  porteDoigts: 0.25,
  // TRAIT DE CONTACT entre deux doigts (pouce compris) : centré sur la frontière d'identité, tracé par les DEUX côtés
  // sur un anneau de contactK × r (shaders.js 4a), sans aucune porte de profondeur. À RÉGLER : voir JOURNAL.md.
  contactK: 0.5,
  // cm : écart de profondeur entre deux doigts au-delà duquel l'un passe DEVANT l'autre (son bord, tracé d'un seul côté
  // par la marche de profondeur) au lieu de le toucher (trait centré). À RÉGLER : voir JOURNAL.md.
  occlDoigts: 0.6,
  // jointures à l'identité de leur doigt (decoder, Pipeline.poser) : abscisse le long du rayon (1 = centre de la MCP) où
  // s'arrête, MCP pliée à fond, le trait de la vallée entre deux têtes métacarpiennes. À RÉGLER : voir JOURNAL.md.
  jointureT: 0.88,
  // fin EFFILÉE du trait de la vallée (shaders.js, 1) : la limite basse de la zone d'une jointure monte vers la ligne
  // médiane (pente en t par unité de u, descente max au centre de la tête) ; sous la fin du trait, un coin de paume
  // s'ouvre entre les deux jointures et le trait centré s'amincit jusqu'à rien. À RÉGLER : voir JOURNAL.md.
  jointurePente: 0.3, jointureDescente: 0.15, jointureEffile: 0.06,
  decolle: 0.04,      // cm : rubans décollés de la peau (Spider-Verse)
  // réserve des plis devant une autre partie (shaders.js 4b, relecture M5 : pli de la paume qui « traverse » le pouce) :
  // rayon 4 × le contour (éteint à moins de 2 × : un blanc d'un contour entre le pli et le trait du pouce, puis
  // effilé jusqu'à 4 ×), écart
  // de profondeur 3 mm (le pouce couché sur la paume en V (2) est à 10–15 mm devant ; un bout de doigt POSÉ sur la paume,
  // à moins de 3 mm, n'est pas « devant » : le trait de contact de la passe d'arêtes y fait déjà la limite)
  reserveOcc: 4.0, dOcc: 0.3,
  interne: 0.7,       // trait de recouvrement / contact = 0,7 × contour (rendu.md § 4, poids de trait)
  ongleT: 0.4,        // trait d'ongle = 0,4 × contour (2,4 / 6 px du dessin)
  ongleMaxMm: 0.45,   // demi-largeur max du trait d'ongle sur la peau (mm) : vu de chant, la lamelle reste lisible
  plancher: 1.25,     // px : plancher de tout trait (sinon il se brise en pointillé)
  marge: 0.8,         // cm autour de la boîte (couvre un contour jusqu'à 4 % de HL = 0,76 cm)
  ss: 2,              // sur-échantillonnage du rendu hors écran (puis réduction) : l'antialiasing fiable en WebGL1/2
  // coupe de l'avant-bras à 2,0 cm sous le centre du poignet (repère de liaison) : le bouchon du GLB (coupe oblique,
  // y −2,9 à −2,3) faisait une ellipse cernée au bas de chaque vue ; coupé net, le trait des flancs s'arrête ouvert
  // (comme dans un dessin de dictionnaire) et, vue par son ouverture, la manche montre son intérieur dans l'ombre
  coupeY: -2.0,
  largeurDefaut: 0.8, // % de HL quand le style n'en donne pas (≈ 1,5 mm sur la main réelle ; v1 : 6 px de dessin ≈ 1,3 mm)
  // nettoyage de la couche des traits : un pixel de trait garde ≥ 3 × plancher voisins sur 25 (shaders.js, 5) — à 8 fixe,
  // la marionnette (pas de sur-échantillonnage) hachait les plis de la paume en tirets
  voisinsK: 3,
  // marionnette pendant un geste : image réduite à 0,7 × la taille (moitié des pixels), sans multi-échantillonnage, puis
  // agrandie ; mesuré (442 × 520, swiftshader) : passes G 46 / coque 59 / toon 120 / arêtes 26 ms avec le MSAA du canvas
  // (toon 49, coque 22 sans) — le coût suit les pixels ; l'image complète revient au relâchement
  rapideK: 0.7,
  // render() : composante isolée de la couche des traits retirée sous 20 px de l'image finale (× ss² en pixels de cible ;
  // 0 = pas de nettoyage) ; voir Pipeline.nettoyerTraits
  nettoyage: 20,
  // côté maximal d'une tuile de rendu (px de cible) ; 0 = la limite du GPU (4096 au plus). Les tests le baissent pour
  // comparer un rendu par tuiles au rendu d'une seule tuile (v2/tests/engine_tuiles.py)
  tuileMax: 0,
  // veto des sauts de profondeur qu'expliquent les normales (shaders.js, 4a « continuité ») ; 0 pour comparer
  continuite: 1,
  // n.z sous lequel un flanc lointain, tourné vers l'extérieur, prolonge le volume proche (règle « enveloppe ») : balayé
  // sur Main plate (B) vue de bout, Poing serré et V (2) : 0,35 cassait les traits des jointures du poing vu de face
  // (crêtes à n.z 0,2–0,35), 0,12 laissait revenir le second anneau autour des bouts ; 0,2 garde l'un et ôte l'autre
  enveloppe: 0.2,
  // pas de trait intérieur à moins de r du fond (1) : la règle venait de l'« écho » du contour sur les flancs rasants,
  // que le veto de continuité ôte maintenant ; elle découpait en TIRETS le trait d'un doigt vu derrière un autre près de
  // la silhouette (la lamelle visible passe au-dessus et au-dessous de r). Mesuré sur 4 poses × 13 vues : 31 → 27
  // fragments sans elle ; le trait rejoint le contour au lieu de s'interrompre. fonduFond : essai écarté (miettes en coin)
  presFond: 0, fonduFond: 0,
  // nettoyage de la couche des traits (nettoyerTraits) : 0 = une composante de moins de aMin pixels est retirée même si
  // elle touche la silhouette (bouts de trait de 2 à 6 px plantés dans le contour : « échardes rattachées » de la
  // relecture adverse ; 22 → 17 sur 4 poses × 13 vues, rien de lisible retiré, vérifié en image)
  garderBord: 0,
  // creux fermés (shaders.js, 4c) : rayon de recherche (cm) et marche de profondeur (cm) ; le tunnel de l'index replié
  // du poing vu de profil mesure ≈ 1,9 × 1,25 cm (rendu à 40 px/cm) : fermé dans les 8 directions à 1,2 cm de son
  // centre ; l'anneau d'un O (2 à 3 cm de jour) ne l'est pas. 0 = passe éteinte.
  rCreux: 1.2, dCreux: 0.5,
  // relief du dos porté par l'ombre (decoder, « relief du dos ») : biais du seuil dans les sillons entre les têtes
  // métacarpiennes (× la flexion des deux MCP voisines, plein à 90°) et dans les vallées entre les tendons (× l'extension,
  // pleine à MCP ≤ 0, nulle dès 35°). Réglé en image sur le poing et la main plate en dos ¾ (planches engine_presets) :
  // 0,45 fait d'un sillon une ombre franche entre deux jointures (N·L du dos de face ≈ 0,8) ; vallées balayées sur la
  // main ouverte, la main plate et l'hyperextension, vues dos et dos ¾ : 0,22 invisible, 0,5 trois bandes sombres qui
  // se lisent comme des rayures, 0,35 deux ou trois ombres courtes entre les tendons (comme les photos 2366 / 2370)
  sillon: 0.45, vallee: 0.35
};
// couleur de style : validée AVANT setStyle — THREE.Color.setStyle ne lève pas d'exception sur une chaîne illisible, il
// avertit et laisse le BLANC (relecture adverse : {peau: 'pas une couleur'} donnait une main blanche) ; formes lues par
// three.js r128 : #rgb, #rrggbb, rgb()/rgba(), hsl()/hsla(), noms CSS
function couleurValide(x) {
  if (typeof x !== 'string') return false; const t = x.trim();
  return /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(t) || /^(rgb|hsl)a?\(\s*[-\d.%\s,]+\)$/i.test(t) || (THREE.Color.NAMES && THREE.Color.NAMES[t.toLowerCase()] !== undefined);
}
function couleur(hex, def) { const c = new THREE.Color(); c.setStyle(couleurValide(hex) ? hex.trim() : def); return c; }
function styleDe(st) {
  st = st || {};
  const lt = typeof st.largeurTrait === 'number' && isFinite(st.largeurTrait) ? Math.max(0, st.largeurTrait) : RENDU.largeurDefaut;
  return {peau: couleur(st.peau, '#00a19a'), ongle: couleur(st.ongle, '#96dcd6'), trait: couleur(st.trait, '#111111'),
    largeurTrait: lt, ombre: st.ombre !== false, plis: st.plis !== false};
}

function Pipeline(renderer) {
  const n = A.n, R = renderer;
  this.R = R;
  this.P = new Float32Array(3 * n); this.N = new Float32Array(3 * n); this.cle = null;
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(this.P, 3).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute('normal', new THREE.BufferAttribute(this.N, 3).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute('aPart', new THREE.BufferAttribute(A.part, 1));
  g.setAttribute('aOs', new THREE.BufferAttribute(A.os, 1));
  this.biais = A.biais.slice();
  g.setAttribute('aBiais', new THREE.BufferAttribute(this.biais, 1).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute('aOngle', new THREE.BufferAttribute(A.ongle, 1));
  g.setAttribute('aMasque', new THREE.BufferAttribute(A.masque, 2));
  g.setAttribute('aY', new THREE.BufferAttribute(A.y, 1));
  g.setAttribute('aRayon', new THREE.BufferAttribute(A.rayon, 3));   // jointures à l'identité de leur doigt (decoder)
  // part de la partie survolée (marionnette) par sommet, tirée des POIDS de peau : interpolée, sa frontière suit la peau
  // (avec l'identité plate par triangle, le surlignage avait un bord en dents de scie — relecture adverse)
  this.survolA = new Float32Array(n);
  g.setAttribute('aSurvol', new THREE.BufferAttribute(this.survolA, 1).setUsage(THREE.DynamicDrawUsage));
  g.setIndex(new THREE.BufferAttribute(A.index, 1));
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 8, 0), 40);
  this.geo = g;
  const L = new THREE.Vector3(...RENDU.L).normalize();
  const u = this.u = {
    L: {value: L}, seuil: {value: RENDU.seuil}, lisiere: {value: RENDU.lisiere}, tonOmbre: {value: RENDU.tonOmbre},
    ombreOn: {value: 1}, peau: {value: new THREE.Color()}, ongle: {value: new THREE.Color()}, trait: {value: new THREE.Color()},
    frange: {value: RENDU.frange}, onglePx: {value: 2}, plancherPx: {value: 1.25}, ongleMaxMm: {value: RENDU.ongleMaxMm},
    ortho: {value: 1}, hlPart: {value: -10}, px: {value: 6}, res: {value: new THREE.Vector2(1, 1)}, recul: {value: RENDU.recul},
    tG: {value: null}, tD: {value: null}, texel: {value: new THREE.Vector2(1, 1)}, r: {value: 3}, dThr: {value: RENDU.dThr},
    dGraze: {value: RENDU.dGraze}, porte: {value: RENDU.porte}, porteDoigts: {value: RENDU.porteDoigts}, cn: {value: 1}, cf: {value: 100},
    pxPli: {value: 3}, plancher: {value: 1.25}, decolle: {value: RENDU.decolle}, coupeY: {value: RENDU.coupeY}, debug: {value: 0}, bandeOn: {value: 0},
    tL: {value: null}, voisinsMin: {value: 7.5}, cmPx: {value: 0.01}, continuite: {value: 1}, enveloppe: {value: 0.15}, presFond: {value: 1}, fonduFond: {value: 0}, masque: {value: 0},
    tCreux: {value: null}, creuxOn: {value: 0}, rCreux: {value: 1.2}, dCreux: {value: 0.5}, nCreux: {value: 6.5}, rOcc: {value: 0}, dOcc: {value: 0.3},
    tJointure: {value: new THREE.Vector4(9, 9, 9, 9)}, occlDoigts: {value: 0.6}, finJointure: {value: new THREE.Vector3(0.3, 0.15, 0.06)}, rContact: {value: 2}
  };
  const mat = (vs, fs, extra) => new THREE.ShaderMaterial(Object.assign({uniforms: u, vertexShader: vs, fragmentShader: fs, extensions: {derivatives: true}}, extra || {}));
  this.mG = mat(SH.gVertex, SH.gFragment);
  this.mT = mat(SH.toonVertex, SH.toonFragment);
  this.mH = mat(SH.hullVertex, SH.hullFragment, {side: THREE.BackSide});
  this.mP = mat(SH.pickVertex, SH.pickFragment);
  // couche des traits : arêtes, bande d'ongle et rubans rendus dans une cible à part (MAX des alphas), puis composés
  // avec nettoyage des miettes (voir shaders.js, 5)
  const max = {transparent: true, blending: THREE.CustomBlending, blendEquation: THREE.MaxEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
    blendEquationAlpha: THREE.MaxEquation, blendSrcAlpha: THREE.OneFactor, blendDstAlpha: THREE.OneFactor};
  this.mE = mat(SH.edgeVertex, SH.edgeFragment, Object.assign({depthTest: false, depthWrite: false, defines: {COUCHE_TRAITS: 1}}, max));
  this.mO = mat(SH.toonVertex, SH.toonFragment, {defines: {COUCHE_TRAITS: 1}, blending: THREE.NoBlending});
  this.mC = mat(SH.compoVertex, SH.compoFragment, {depthTest: false, depthWrite: false, transparent: true});
  // mode RAPIDE (marionnette pendant un geste) : arêtes et rubans directement sur l'image, bande d'ongle dans la passe
  // de couleur, sans couche nettoyée (mesuré sous swiftshader : 685 ms par image en qualité complète)
  this.mEd = mat(SH.edgeVertex, SH.edgeFragment, {depthTest: false, depthWrite: false, transparent: true});
  const uR = Object.assign({}, u, {px: u.pxPli});
  this.mR = new THREE.ShaderMaterial(Object.assign({uniforms: uR, vertexShader: SH.rubanVertex, fragmentShader: SH.rubanFragment,
    depthWrite: false, depthTest: true, side: THREE.DoubleSide, defines: {COUCHE_TRAITS: 1}}, max));   // le sens du ruban dépend de la courbe
  this.mRd = new THREE.ShaderMaterial({uniforms: uR, vertexShader: SH.rubanVertex, fragmentShader: SH.rubanFragment,
    depthWrite: false, depthTest: true, side: THREE.DoubleSide, transparent: true});
  const scene = m => { const s = new THREE.Scene(), me = new THREE.Mesh(g, m); me.frustumCulled = false; me.matrixAutoUpdate = false; s.add(me); s.autoUpdate = true; return [s, me]; };
  [this.sG, this.meG] = scene(this.mG); [this.sT, this.meT] = scene(this.mT); [this.sH, this.meH] = scene(this.mH); [this.sP, this.meP] = scene(this.mP);
  [this.sO, this.meO] = scene(this.mO);
  // bord de la manche (shaders.js, 3b) : segments de l'anneau de coupe y = coupeY (repère de liaison), un par triangle
  // traversé, chacun extrudé en quadrilatère ; positions et normales interpolées sur la peau posée à chaque pose
  {
    const Y = A.y, I = A.index, c0 = RENDU.coupeY, pts = new Map(), seg = [];
    const pt = (i, j) => { const a = Math.min(i, j), b = Math.max(i, j), k = a * n + b;
      if (!pts.has(k)) pts.set(k, {i: a, j: b, t: (c0 - Y[a]) / (Y[b] - Y[a])}); return pts.get(k); };
    for (let f = 0; f < I.length; f += 3) {
      const v = [I[f], I[f + 1], I[f + 2]], x = [];
      for (let e = 0; e < 3; e++) { const a = v[e], b = v[(e + 1) % 3]; if ((Y[a] - c0) * (Y[b] - c0) < 0) x.push(pt(a, b)); }
      if (x.length === 2) seg.push(x);
    }
    const m = seg.length, gb = new THREE.BufferGeometry(), cote = new Float32Array(4 * m), idx = [];
    for (let s2 = 0; s2 < m; s2++) { cote[4 * s2 + 2] = cote[4 * s2 + 3] = 1; idx.push(4 * s2, 4 * s2 + 1, 4 * s2 + 3, 4 * s2, 4 * s2 + 3, 4 * s2 + 2); }
    this.bord = {seg, pos: new Float32Array(12 * m), autre: new Float32Array(12 * m), centre: new THREE.Vector3()};
    gb.setAttribute('position', new THREE.BufferAttribute(this.bord.pos, 3).setUsage(THREE.DynamicDrawUsage));
    gb.setAttribute('aAutre', new THREE.BufferAttribute(this.bord.autre, 3).setUsage(THREE.DynamicDrawUsage));
    gb.setAttribute('aCote', new THREE.BufferAttribute(cote, 1));
    gb.setIndex(idx); gb.boundingSphere = g.boundingSphere;
    this.mB = new THREE.ShaderMaterial({uniforms: Object.assign({}, u, {centreBord: {value: this.bord.centre}, fBord: {value: 1}, axeBord: {value: new THREE.Vector3(0, -1, 0)}, fAxe: {value: 0}}), vertexShader: SH.bordVertex,
      fragmentShader: SH.bordFragment, side: THREE.DoubleSide, depthTest: false, depthWrite: false});
    this.sB = new THREE.Scene(); this.meB = new THREE.Mesh(gb, this.mB); this.meB.frustumCulled = false; this.meB.matrixAutoUpdate = false; this.sB.add(this.meB);
    this.geoB = gb;
    // BOUCHON de la coupe : un éventail (centre de l'anneau, extrémités de chaque segment) qui FERME l'avant-bras. Relecture
    // adverse : vue « dessous » (poignet vers l'œil), on voyait par l'ouverture l'intérieur creux des doigts et de la paume
    // (les faces arrière, peintes dans l'ombre) — un gant vide ; vue « dos ¾ », l'ellipse sombre de l'ouverture se lisait
    // comme l'entrée d'un gant. Le bouchon est peint dans le ton CLAIR de la peau, sans trait (identité 8 de la G-pass) :
    // contre l'avant-bras éclairé il se fond, la coupe se lit comme la fin d'un dessin et non comme un trou ; seul le bord
    // de la manche (bande 3b) cerne la partie de l'anneau qui est silhouette. Il remplace les deux passes des faces arrière
    // (la moitié du coût géométrique quand l'ouverture regardait l'œil).
    const gc = new THREE.BufferGeometry(), nv = 3 * m;
    this.bouchon = {pos: new Float32Array(3 * nv), nor: new Float32Array(3 * nv)};
    gc.setAttribute('position', new THREE.BufferAttribute(this.bouchon.pos, 3).setUsage(THREE.DynamicDrawUsage));
    gc.setAttribute('normal', new THREE.BufferAttribute(this.bouchon.nor, 3).setUsage(THREE.DynamicDrawUsage));
    const remplir = (nom, c, v) => { const t = new Float32Array(c * nv); for (let i = 0; i < nv; i++) for (let j = 0; j < c; j++) t[c * i + j] = Array.isArray(v) ? v[j] : v; gc.setAttribute(nom, new THREE.BufferAttribute(t, c)); };
    remplir('aPart', 1, 0); remplir('aOs', 1, 0); remplir('aBiais', 1, 0); remplir('aOngle', 1, -3); remplir('aMasque', 2, [0, 0]); remplir('aY', 1, c0 + 1e-3); remplir('aRayon', 3, [0, 0, 0]);
    gc.boundingSphere = g.boundingSphere;
    this.geoC = gc;
    this.mGc = mat(SH.gVertex, SH.gFragment, {side: THREE.DoubleSide, defines: {BOUCHON: 1}});
    this.mTc = mat(SH.toonVertex, SH.toonFragment, {side: THREE.DoubleSide, defines: {BOUCHON: 1}});
    this.mOc = mat(SH.toonVertex, SH.toonFragment, {side: THREE.DoubleSide, defines: {BOUCHON: 1, COUCHE_TRAITS: 1}, blending: THREE.NoBlending});
    this.mPc = mat(SH.pickVertex, SH.pickFragment, {side: THREE.DoubleSide});
    const ajouteBouchon = (sc, m2) => { const me = new THREE.Mesh(gc, m2); me.frustumCulled = false; me.matrixAutoUpdate = false; sc.add(me); return me; };
    this.meGc = ajouteBouchon(this.sG, this.mGc); this.meTc = ajouteBouchon(this.sT, this.mTc); this.meOc = ajouteBouchon(this.sO, this.mOc); this.mePc = ajouteBouchon(this.sP, this.mPc);
  }
  // rubans des plis
  const np = PLIS.total, rp = this.rp = {
    pos: new Float32Array(6 * np), nor: new Float32Array(6 * np), prec: new Float32Array(6 * np), suiv: new Float32Array(6 * np),
    cote: new Float32Array(2 * np), w: new Float32Array(2 * np)};
  const ri = [];
  PLIS.courbes.forEach(c => {
    for (let i = 0; i < c.pts.length; i++) { const v = 2 * (c.debut + i); rp.cote[v] = -1; rp.cote[v + 1] = 1;
      if (i < c.pts.length - 1) ri.push(v, v + 1, v + 2, v + 1, v + 3, v + 2); }
  });
  const gr = new THREE.BufferGeometry();
  gr.setAttribute('position', new THREE.BufferAttribute(rp.pos, 3).setUsage(THREE.DynamicDrawUsage));
  gr.setAttribute('normal', new THREE.BufferAttribute(rp.nor, 3).setUsage(THREE.DynamicDrawUsage));
  gr.setAttribute('aPrec', new THREE.BufferAttribute(rp.prec, 3).setUsage(THREE.DynamicDrawUsage));
  gr.setAttribute('aSuiv', new THREE.BufferAttribute(rp.suiv, 3).setUsage(THREE.DynamicDrawUsage));
  gr.setAttribute('aCote', new THREE.BufferAttribute(rp.cote, 1));
  gr.setAttribute('aW', new THREE.BufferAttribute(rp.w, 1).setUsage(THREE.DynamicDrawUsage));
  gr.setIndex(ri);
  gr.boundingSphere = g.boundingSphere;
  this.geoR = gr;
  [this.sR, this.meR] = scene(this.mR); this.meR.geometry = gr;
  [this.sRd, this.meRd] = scene(this.mRd); this.meRd.geometry = gr;
  // quads plein écran : arêtes (dans la couche des traits), composition nettoyée (sur l'image)
  this.sE = new THREE.Scene(); const q = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mE); q.frustumCulled = false; this.sE.add(q);
  this.sC = new THREE.Scene(); const qc = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mC); qc.frustumCulled = false; this.sC.add(qc);
  this.sEd = new THREE.Scene(); const qd = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mEd); qd.frustumCulled = false; this.sEd.add(qd);
  // creux fermés (shaders.js, 4c) : un plein écran vers une cible à part, lue par la couleur, les arêtes et les rubans
  this.mK = mat(SH.edgeVertex, SH.creuxFragment, {depthTest: false, depthWrite: false, blending: THREE.NoBlending});
  this.sK = new THREE.Scene(); const qk2 = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mK); qk2.frustumCulled = false; this.sK.add(qk2);
  this.rtK = null;
  // copie de l'image réduite du geste vers le canvas (filtre linéaire ; RGBA prémultiplié recopié tel quel)
  this.mCopie = new THREE.ShaderMaterial({uniforms: {t: {value: null}}, depthTest: false, depthWrite: false, blending: THREE.NoBlending,
    vertexShader: 'varying vec2 vU; void main(){ vU = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: 'uniform sampler2D t; varying vec2 vU; void main(){ gl_FragColor = texture2D(t, vU); }'});
  this.sCopie = new THREE.Scene(); const qk = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.mCopie); qk.frustumCulled = false; this.sCopie.add(qk);
  this.rtRapide = null;
  this.rtL = null;
  this.camQ = new THREE.Camera();
  this.rt = null;
  this.rtPick = null;
}
Pipeline.prototype.survol = function (part) {
  this.u.hlPart.value = part; const S2 = this.survolA, n = A.n;
  for (let i = 0; i < n; i++) { let w = 0; if (part >= 0) for (let j = 0; j < 4; j++) if (PARTIE_OS[A.J[4 * i + j]] === part) w += A.W[4 * i + j]; S2[i] = w; }
  this.geo.attributes.aSurvol.needsUpdate = true;
};
// pose → peau (positions, normales) et rubans ; cache : la dernière pose
Pipeline.prototype.poser = function (p, pe) {
  const k0 = cle(p), k = k0 + '|' + RENDU.sillon + ',' + RENDU.vallee + ',' + RENDU.jointureT; if (k === this.cle) return this.F;
  if (pe && pe.k === k0) { this.P.set(pe.P); this.N.set(pe.N); this.F = pe.F; } else this.F = skin(p, this.P, this.N);
  this.cle = k;
  this.geo.attributes.position.needsUpdate = true; this.geo.attributes.normal.needsUpdate = true;
  // relief du dos : biais d'ombre des sillons (flexion des deux MCP voisines) et des vallées (extension)
  {
    const bz = this.biais, b0 = A.biaisBase, n = A.n; bz.set(b0);
    for (let k2 = 0; k2 < 3; k2++) {
      const ma = p[DOIGTS[k2]].mcp, mb = p[DOIGTS[k2 + 1]].mcp;
      const fs = RENDU.sillon * sstep(20, 90, Math.min(ma, mb)), fv = RENDU.vallee * (1 - sstep(0, 35, 0.5 * (ma + mb)));
      if (fs <= 0 && fv <= 0) continue;
      const S2 = A.sillon[k2], V2 = A.vallee[k2];
      for (let i = 0; i < n; i++) { const w = fs * S2[i] + fv * V2[i]; if (w > bz[i] - b0[i]) bz[i] = b0[i] + w; }
    }
    this.geo.attributes.aBiais.needsUpdate = true;
  }
  // jointures à l'identité de leur doigt (decoder, « JOINTURES ») : seuil en t (abscisse le long du rayon, 1 = centre de
  // la MCP) au-delà duquel la peau dorsale de la paume prend l'identité du doigt k, selon la flexion de sa MCP. Main à plat
  // (MCP < 30°) : aucun changement (9 = jamais) — le dos d'une main ouverte est lisse, sans trait entre les rayons. De 30
  // à 75° la zone descend de la base de la P1 (t 1,05) jusqu'à t = RENDU.jointureT : le trait de la vallée grandit avec
  // la jointure qui sort, sans apparaître d'un coup. La zone d'un doigt TENDU s'active aussi quand un VOISIN est plié :
  // la vallée existe dès qu'une des deux têtes sort (capture de « L » de l'utilisateur, vue de dos : sans cela, rien ne
  // séparait la jointure du majeur replié de la base de l'index tendu) ; elle prolonge la P1 du doigt tendu (même
  // identité), donc aucun trait de plus ailleurs.
  {
    const tj = this.u.tJointure.value, f = DOIGTS.map(k => sstep(30, 75, p[k].mcp)), v = [0, 0, 0, 0];
    for (let k = 0; k < 4; k++) { const g = Math.max(f[k], k > 0 ? f[k - 1] : 0, k < 3 ? f[k + 1] : 0); v[k] = g > 0 ? 1.05 + (RENDU.jointureT - 1.05) * g : 9; }
    tj.set(v[0], v[1], v[2], v[3]);
  }
  // rubans : position et normale barycentriques sur la peau posée ; voisins pour la tangente écran ; largeur
  const rp = this.rp, P = this.P, N = this.N;
  PLIS.courbes.forEach(c => {
    const vis = c.vis(p), m = c.pts.length, tmp = new Float32Array(3 * m);
    for (let i = 0; i < m; i++) {
      const q = c.pts[i], o = 3 * i;
      let nx = 0, ny = 0, nz = 0;
      for (let c3 = 0; c3 < 3; c3++) tmp[o + c3] = q[3] * P[3 * q[0] + c3] + q[4] * P[3 * q[1] + c3] + q[5] * P[3 * q[2] + c3];
      nx = q[3] * N[3 * q[0]] + q[4] * N[3 * q[1]] + q[5] * N[3 * q[2]]; ny = q[3] * N[3 * q[0] + 1] + q[4] * N[3 * q[1] + 1] + q[5] * N[3 * q[2] + 1];
      nz = q[3] * N[3 * q[0] + 2] + q[4] * N[3 * q[1] + 2] + q[5] * N[3 * q[2] + 2];
      const ln = 1 / (Math.hypot(nx, ny, nz) || 1), v = 2 * (c.debut + i);
      for (let s2 = 0; s2 < 2; s2++) { rp.nor[3 * (v + s2)] = nx * ln; rp.nor[3 * (v + s2) + 1] = ny * ln; rp.nor[3 * (v + s2) + 2] = nz * ln; }
      const t = c.tt[i], prof = sstep(0, c.eff, t) * sstep(1, 1 - c.eff, t);
      rp.w[v] = rp.w[v + 1] = c.poids * vis * prof;
    }
    for (let i = 0; i < m; i++) {
      // voisins à ± 2 points (≈ 1,2 mm de peau) : la tangente écran et le COUDE du ruban (shaders.js 4b) sont lus sur
      // quatre segments — sur un seul, un crochet de 10 à 15 px se répartit en coudes de 20° que rien ne distingue
      const v = 2 * (c.debut + i), ip = Math.max(0, i - 2), is = Math.min(m - 1, i + 2);
      for (let s2 = 0; s2 < 2; s2++) for (let c3 = 0; c3 < 3; c3++) {
        rp.pos[3 * (v + s2) + c3] = tmp[3 * i + c3]; rp.prec[3 * (v + s2) + c3] = tmp[3 * ip + c3]; rp.suiv[3 * (v + s2) + c3] = tmp[3 * is + c3];
      }
    }
  });
  ['position', 'normal', 'aPrec', 'aSuiv', 'aW'].forEach(a => this.geoR.attributes[a].needsUpdate = true);
  // bord de la manche : extrémités des segments et centre de l'anneau
  const B = this.bord, ptB = q => [0, 1, 2].map(c3 => P[3 * q.i + c3] + (P[3 * q.j + c3] - P[3 * q.i + c3]) * q.t);
  let cx = 0, cy = 0, cz = 0;
  B.seg.forEach((sg, s2) => {
    const a = ptB(sg[0]), b = ptB(sg[1]);
    cx += a[0] + b[0]; cy += a[1] + b[1]; cz += a[2] + b[2];
    [[a, b], [b, a]].forEach(([x, y], e) => { for (const v of [4 * s2 + e, 4 * s2 + e + 2]) for (let c3 = 0; c3 < 3; c3++) { B.pos[3 * v + c3] = x[c3]; B.autre[3 * v + c3] = y[c3]; } });
  });
  const nb = 2 * Math.max(1, B.seg.length); B.centre.set(cx / nb, cy / nb, cz / nb);
  this.geoB.attributes.position.needsUpdate = true; this.geoB.attributes.aAutre.needsUpdate = true;
  // bouchon : un triangle (centre, a, b) par segment ; normale = axe de l'avant-bras posé, vers l'extérieur (−Y du poignet)
  const C = this.bouchon, nz = this.F ? qrot(this.F.Q[0], [0, -1, 0]) : [0, -1, 0], ctr = [B.centre.x, B.centre.y, B.centre.z];
  B.seg.forEach((sg, s2) => {
    const a = ptB(sg[0]), b = ptB(sg[1]);
    [ctr, a, b].forEach((pt, j) => { const o = 3 * (3 * s2 + j); C.pos[o] = pt[0]; C.pos[o + 1] = pt[1]; C.pos[o + 2] = pt[2]; C.nor[o] = nz[0]; C.nor[o + 1] = nz[1]; C.nor[o + 2] = nz[2]; });
  });
  this.geoC.attributes.position.needsUpdate = true; this.geoC.attributes.normal.needsUpdate = true;
  return this.F;
};
Pipeline.prototype.matrice = function (M) {
  [this.meG, this.meT, this.meH, this.meP, this.meR, this.meRd, this.meO, this.meB, this.meGc, this.meTc, this.meOc, this.mePc].forEach(me => { me.matrix.copy(M); me.matrixWorldNeedsUpdate = true; });
  // orientation de l'ouverture de l'avant-bras par rapport à l'œil (dz > 0 : on voit DANS la manche)
  const F = this.F; let dz = 1;
  if (F) { const d = qrot(F.Q[0], [0, -1, 0]), e = M.elements; dz = e[2] * d[0] + e[6] * d[1] + e[10] * d[2]; }
  // bord de la manche : seulement quand on voit DANS la manche ; vue par la tranche (dz ≈ 0, vues paume / dos / profil) la
  // coupe reste ouverte, comme dans un dessin de dictionnaire — l'anneau aplati y donnait une frange en dents de scie
  // (vu sur la vue paume) ; largeur amenée de 0 à 1 entre dz 0,12 et 0,35 (vues « dos ¾ » : dz = sin 20° = 0,34)
  // … et, depuis le bouchon, aussi quand l'avant-bras FUIT (dz < 0, vues « dessus ») : l'anneau est alors la silhouette du
  // bout de l'avant-bras vu de derrière, qui restait sans contour sous la paume
  // depuis la relecture M5, la bande sert AUSSI quand la coupe est vue par la tranche (fAxe, shaders.js 3b) : toujours
  // visible ; l'axe de l'avant-bras posé lui est passé dans le repère du modèle
  this.meB.visible = true; this.mB.uniforms.fBord.value = sstep(0.12, 0.35, Math.abs(dz));
  this.mB.uniforms.fAxe.value = 1 - sstep(0.12, 0.35, Math.abs(dz));
  if (F) { const d = qrot(F.Q[0], [0, -1, 0]); this.mB.uniforms.axeBord.value.set(d[0], d[1], d[2]); }
};
Pipeline.prototype.cible = function (W, H) {
  if (!this.rt) {
    this.rt = new THREE.WebGLRenderTarget(W, H, {minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, depthBuffer: true});
    this.rt.depthTexture = new THREE.DepthTexture(W, H); this.rt.depthTexture.type = THREE.UnsignedIntType;
  } else if (this.rt.width !== W || this.rt.height !== H) this.rt.setSize(W, H);
  return this.rt;
};
// st : style résolu (styleDe) ; px : {contour, interne, ongle, plis, plancher} en pixels de la CIBLE ; cam : caméra
Pipeline.prototype.dessiner = function (cam, W, H, st, px, sortie, rapide, nettoyer) {
  const R = this.R, u = this.u;
  // réglages relus à chaque image (les tests les font varier : JOURNAL.md, balayages)
  u.seuil.value = RENDU.seuil; u.lisiere.value = RENDU.lisiere; u.tonOmbre.value = RENDU.tonOmbre; u.frange.value = RENDU.frange;
  u.ongleMaxMm.value = RENDU.ongleMaxMm; u.recul.value = RENDU.recul; u.dThr.value = RENDU.dThr; u.dGraze.value = RENDU.dGraze;
  u.porte.value = RENDU.porte; u.porteDoigts.value = RENDU.porteDoigts; u.decolle.value = RENDU.decolle; u.coupeY.value = RENDU.coupeY; u.debug.value = RENDU.debug || 0;
  u.peau.value.copy(st.peau); u.ongle.value.copy(st.ongle); u.trait.value.copy(st.trait); u.ombreOn.value = st.ombre ? 1 : 0;
  u.res.value.set(W, H); u.texel.value.set(1 / W, 1 / H);
  u.ortho.value = cam.isOrthographicCamera ? 1 : 0; u.cn.value = cam.near; u.cf.value = cam.far;
  // taille d'un pixel de la cible en cm (orthographique : la largeur du cadre ENTIER sur sa largeur en pixels, tuiles
  // comprises) ; en perspective, à la profondeur 1 (le nuanceur multiplie par la profondeur)
  u.cmPx.value = cam.isOrthographicCamera ? (cam.right - cam.left) / cam.zoom / (cam.view && cam.view.enabled ? cam.view.fullWidth : W)
    : 2 * Math.tan(cam.fov * D2R / 2) / H;
  u.continuite.value = RENDU.continuite; u.enveloppe.value = RENDU.enveloppe; u.presFond.value = RENDU.presFond; u.fonduFond.value = RENDU.fonduFond;
  u.px.value = px.contour; u.onglePx.value = px.ongle; u.plancherPx.value = px.plancher; u.plancher.value = px.plancher;
  u.r.value = px.interne / 0.85; u.pxPli.value = px.plis;
  u.rContact.value = RENDU.contactK * u.r.value; u.occlDoigts.value = RENDU.occlDoigts;
  u.finJointure.value.set(RENDU.jointurePente, RENDU.jointureDescente, RENDU.jointureEffile);
  u.rOcc.value = (RENDU.reserveOcc || 0) * px.contour; u.dOcc.value = RENDU.dOcc;
  const rt = this.cible(W, H);
  if (!this.rtL) this.rtL = new THREE.WebGLRenderTarget(W, H, {minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, depthBuffer: true});
  else if (this.rtL.width !== W || this.rtL.height !== H) this.rtL.setSize(W, H);
  u.tG.value = rt.texture; u.tD.value = rt.depthTexture; u.tL.value = this.rtL.texture; u.voisinsMin.value = RENDU.voisinsK * px.plancher;
  const ac = R.autoClear; R.autoClear = false;
  R.setRenderTarget(rt); R.setClearColor(0x000000, 0); R.clear(true, true, true); R.render(this.sG, cam);
  // creux fermés : pas pendant un geste de la marionnette (image rapide), partout ailleurs
  u.rCreux.value = RENDU.rCreux; u.dCreux.value = RENDU.dCreux; u.nCreux.value = RENDU.nCreux != null ? RENDU.nCreux : 6.5;
  u.creuxOn.value = rapide || !(RENDU.rCreux > 0) ? 0 : 1;
  if (u.creuxOn.value) {
    // à DEMI-RÉSOLUTION (3 pas par direction au lieu de 5) : c'est une région de l'ordre du cm, pas un trait ; mesuré à
    // 470 × 660 (rendu logiciel) : 240 → ≈ 40 ms
    const Wk = Math.max(1, Math.ceil(W / 2)), Hk = Math.max(1, Math.ceil(H / 2));
    if (!this.rtK) this.rtK = new THREE.WebGLRenderTarget(Wk, Hk, {minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false});
    else if (this.rtK.width !== Wk || this.rtK.height !== Hk) this.rtK.setSize(Wk, Hk);
    R.setRenderTarget(this.rtK); R.setClearColor(0x000000, 0); R.clear(true, false, false); R.render(this.sK, this.camQ);
    u.tCreux.value = this.rtK.texture;
  }
  if (rapide) {
    u.bandeOn.value = px.contour > 0 ? 1 : 0;
    R.setRenderTarget(sortie || null); R.setClearColor(0x000000, 0); R.clear(true, true, true);
    if (px.contour > 0) R.render(this.sH, cam);
    if (px.contour > 0 && this.meB.visible) R.render(this.sB, cam);
    R.render(this.sT, cam);
    if (px.contour > 0 && st.plis) R.render(this.sRd, cam);
    if (px.contour > 0) R.render(this.sEd, this.camQ);
    u.bandeOn.value = 0; R.autoClear = ac; return;
  }
  if (px.contour > 0) {      // couche des traits : bande d'ongle (avec sa profondeur), rubans, arêtes
    R.setRenderTarget(this.rtL); R.setClearColor(0x000000, 0); R.clear(true, true, true);
    R.render(this.sO, cam);
    if (st.plis) R.render(this.sR, cam);
    R.render(this.sE, this.camQ);
    if (nettoyer) this.nettoyerTraits(W, H, nettoyer);
  }
  this.dernier = {cam, contour: px.contour > 0};
  this.composer('complet', sortie);
  R.autoClear = ac;
};
// dernière étape de dessiner(), refaite sans recalculer la G-pass ni la couche des traits : 'complet' (l'image),
// 'base' (aplat et ombre seuls : ce qu'il y a SOUS les traits), 'masque' (encre de la coque, du bord de la manche, des
// arêtes et de la bande d'ongle, en blanc : render() s'en sert pour nettoyer l'image finale)
Pipeline.prototype.composer = function (mode, sortie) {
  const R = this.R, u = this.u, cam = this.dernier.cam, trace = this.dernier.contour && mode !== 'base', ac = R.autoClear;
  R.autoClear = false;
  R.setRenderTarget(sortie || null); R.setClearColor(0x000000, 0); R.clear(true, true, true);
  u.masque.value = mode === 'masque' ? 1 : 0;
  if (trace) R.render(this.sH, cam);
  if (trace && this.meB.visible) R.render(this.sB, cam);
  if (mode !== 'masque') R.render(this.sT, cam);
  if (trace) R.render(this.sC, this.camQ);
  u.masque.value = 0; R.autoClear = ac;
};
// Nettoyage de la couche des traits sur le processeur (render() seulement) : une composante d'arête ou de bande d'ongle
// (canaux R et B ; les rubans des plis, canal G, sont des marques voulues et restent) de moins de aMin pixels de cible,
// qui ne rejoint ni le fond (donc pas la silhouette et son contour) ni le bord de la tuile, est retirée. Ce que le filtre
// 5 × 5 du GPU laisse passer (shaders.js, 5) : les bouts d'un « U » d'ongle vu par le bout du doigt (deux tirets aux coins
// de l'ongle), une bande d'ongle vue de chant qui se brise en pointillé, un bout d'arête au seuil — mesuré sur 8 poses ×
// 12 vues à 30 px/cm : 234 fragments noirs < 20 px près des articulations, dont 148 de 1 à 4 px.
Pipeline.prototype.nettoyerTraits = function (W, H, aMin) {
  const R = this.R, n = W * H;
  // la texture est refaite dès que la LARGEUR ou la HAUTEUR change, pas seulement le nombre de pixels : deux tuiles de
  // 3997 × 1401 et 1401 × 3997 ont le même nombre de pixels, et la seconde relisait les données de la première avec le
  // mauvais pas de ligne — une traînée noire horizontale traversait les exports ≥ 2048 px (relecture adverse, V (2) dos ¾
  // à 2600 px : traînée de x 800 à 1950 px à la hauteur de la coupe de l'avant-bras)
  if (!this.bufL || this.bufW !== W || this.bufH !== H) {
    this.bufL = new Uint8Array(4 * n); this.bufG = new Uint8Array(4 * n); this.labL = new Uint8Array(n); this.fileL = new Int32Array(n);
    if (this.texL) this.texL.dispose();
    this.texL = new THREE.DataTexture(this.bufL, W, H, THREE.RGBAFormat); this.texL.minFilter = this.texL.magFilter = THREE.NearestFilter;
    this.bufW = W; this.bufH = H;
  }
  const L = this.bufL, G = this.bufG, lab = this.labL, file = this.fileL;
  R.readRenderTargetPixels(this.rtL, 0, 0, W, H, L);
  R.readRenderTargetPixels(this.rt, 0, 0, W, H, G);
  lab.fill(0);
  const encre = q => L[4 * q] > 5 || L[4 * q + 2] > 5;
  let retires = 0;
  for (let p0 = 0; p0 < n; p0++) {
    if (lab[p0] || !encre(p0)) continue;
    let tete = 0, queue = 0, libre = false; file[queue++] = p0; lab[p0] = 1;
    while (tete < queue) {
      const p = file[tete++], x = p % W, y = (p - x) / W;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= W || yy >= H) { libre = true; continue; }
        const q = yy * W + xx;
        if (G[4 * q + 3] === 0 && RENDU.garderBord) libre = true;   // le fond à ≤ 2 px : le trait rejoint la silhouette
        if (dx >= -1 && dx <= 1 && dy >= -1 && dy <= 1 && !lab[q] && encre(q)) { lab[q] = 1; file[queue++] = q; }
      }
    }
    if (queue < aMin && !libre) { for (let i = 0; i < queue; i++) { const q = file[i]; L[4 * q] = 0; L[4 * q + 2] = 0; L[4 * q + 3] = L[4 * q + 1]; } retires++; }
  }
  this.texL.needsUpdate = true; this.u.tL.value = this.texL; this.retires = retires;
};
// image d'un geste (marionnette) : rendu « rapide » dans une cible réduite de k, puis copie agrandie sur le canvas
Pipeline.prototype.dessinerGeste = function (cam, W, H, st, pxDe, k) {
  const Wr = Math.max(16, Math.round(W * k)), Hr = Math.max(16, Math.round(H * k));
  if (!this.rtRapide) this.rtRapide = new THREE.WebGLRenderTarget(Wr, Hr, {minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: true});
  else if (this.rtRapide.width !== Wr || this.rtRapide.height !== Hr) this.rtRapide.setSize(Wr, Hr);
  this.dessiner(cam, Wr, Hr, st, pxDe(Wr / W), this.rtRapide, true);
  const R = this.R, ac = R.autoClear; R.autoClear = false;
  this.mCopie.uniforms.t.value = this.rtRapide.texture;
  R.setRenderTarget(null); R.setClearColor(0x000000, 0); R.clear(true, true, true); R.render(this.sCopie, this.camQ);
  R.autoClear = ac;
};
// passe de sélection (marionnette) : os dominant et partie sous chaque pixel
Pipeline.prototype.selection = function (cam, W, H) {
  if (!this.rtPick) this.rtPick = new THREE.WebGLRenderTarget(W, H, {minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, depthBuffer: true});
  else if (this.rtPick.width !== W || this.rtPick.height !== H) this.rtPick.setSize(W, H);
  const R = this.R, ac = R.autoClear; R.autoClear = false;
  R.setRenderTarget(this.rtPick); R.setClearColor(0x000000, 0); R.clear(true, true, true); R.render(this.sP, cam);
  R.setRenderTarget(null); R.autoClear = ac;
  this.pickW = W; this.pickH = H;
};
Pipeline.prototype.lirePixel = function (x, y) {
  const b = new Uint8Array(4); if (!this.rtPick) return null;
  this.R.readRenderTargetPixels(this.rtPick, Math.round(x), Math.round(this.pickH - 1 - y), 1, 1, b);
  if (b[3] === 0) return null;
  return {os: Math.round(b[0] / 255 * 32) - 1, partie: Math.round(b[1] / 255 * 8) - 1};
};

// matrice objet : orientation (quaternion) · miroir (main gauche : x → −x)
function matriceObjet(q, cote) {
  const qq = qnorm(Array.isArray(q) && q.length === 4 ? q.map(x => num(x)) : [0, 0, 0, 1]);
  const M = new THREE.Matrix4().makeRotationFromQuaternion(new THREE.Quaternion(qq[0], qq[1], qq[2], qq[3]));
  if (cote === 'G') M.multiply(new THREE.Matrix4().makeScale(-1, 1, 1));
  return M;
}
// boîte (cm) de la peau posée vue par la caméra (axes x droite, y haut, z vers la caméra)
function boite(P, M) {
  const e = M.elements, YL = A.y, cy = RENDU.coupeY; let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9, z0 = 1e9, z1 = -1e9;
  for (let i = 0; i < P.length; i += 3) {
    if (YL[i / 3] < cy) continue;
    const x = P[i], y = P[i + 1], z = P[i + 2];
    const X = e[0] * x + e[4] * y + e[8] * z, Y = e[1] * x + e[5] * y + e[9] * z, Z = e[2] * x + e[6] * y + e[10] * z;
    if (X < x0) x0 = X; if (X > x1) x1 = X; if (Y < y0) y0 = Y; if (Y > y1) y1 = Y; if (Z < z0) z0 = Z; if (Z > z1) z1 = Z;
  }
  return {x0, x1, y0, y1, z0, z1};
}

// --- le rendu hors écran de render() : un renderer, un pipeline, peaux mises en cache par pose ---
let OFF = null;
function horsEcran() {
  if (OFF) return OFF;
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 16;
  const R = new THREE.WebGLRenderer({canvas, antialias: false, alpha: true, premultipliedAlpha: true, preserveDrawingBuffer: true});
  R.setPixelRatio(1);
  const gl = R.getContext();
  const maxRB = Math.min(gl.getParameter(gl.MAX_RENDERBUFFER_SIZE), gl.getParameter(gl.MAX_VIEWPORT_DIMS)[0], R.capabilities.maxTextureSize);
  OFF = {R, canvas, pipe: new Pipeline(R), tuile: Math.min(4096, maxRB), webgl2: R.capabilities.isWebGL2};
  return OFF;
}
// peau mise en cache par pose (les deux ou trois dernières) : bounds() puis render() de la même main ne posent qu'une fois
const CACHE_PEAU = [];
function peauDe(p) {
  const k = cle(p), e = CACHE_PEAU.find(x => x.k === k);
  if (e) return e;
  const P = new Float32Array(3 * A.n), N = new Float32Array(3 * A.n), F = skin(p, P, N), o = {k, P, N, F};
  CACHE_PEAU.unshift(o); if (CACHE_PEAU.length > 3) CACHE_PEAU.pop();
  return o;
}
function boiteMain(o) {
  const p = constrain(o && o.pose, {passif: true}), M = matriceObjet(o && o.orientation, o && o.cote);
  const pe = peauDe(p), b = boite(pe.P, M), m = RENDU.marge;
  return {p, M, pe, b, x0: b.x0 - m, x1: b.x1 + m, y0: b.y0 - m, y1: b.y1 + m};
}
function bounds(o) {
  if (!A) return {w: 10, h: 19};
  const B = boiteMain(o || {});
  return {w: B.x1 - B.x0, h: B.y1 - B.y0};
}
// largeurs de trait (px de l'image finale) pour s px/cm
function largeurs(st, s) {
  const c = st.largeurTrait > 0 ? Math.max(RENDU.plancher, st.largeurTrait / 100 * HL * s) : 0;
  return {contour: c, interne: c > 0 ? Math.max(RENDU.plancher, RENDU.interne * c) : 0, ongle: c > 0 ? Math.max(RENDU.plancher, RENDU.ongleT * c) : 0,
    plis: c, plancher: RENDU.plancher};
}
const fois = (px, k) => ({contour: px.contour * k, interne: px.interne * k, ongle: px.ongle * k, plis: px.plis * k, plancher: px.plancher * k});
// projection utilisée par render() (tests : fenêtres des jointures, recadrages) → pixels de l'image finale
function projection(o) {
  const w = Math.round(num(o.w, 256)), h = Math.round(num(o.h, 256)), B = boiteMain(o), bw = B.x1 - B.x0, bh = B.y1 - B.y0;
  const s = Math.min(w / bw, h / bh), cx = (B.x0 + B.x1) / 2, cy = (B.y0 + B.y1) / 2, e = B.M.elements;
  const px = q => { const X = e[0] * q[0] + e[4] * q[1] + e[8] * q[2], Y = e[1] * q[0] + e[5] * q[1] + e[9] * q[2]; return [(X - cx) * s + w / 2, h / 2 - (Y - cy) * s]; };
  const F = fk(B.p), joints = {};
  OS.forEach((n, k) => joints[n] = px(F.C[k]));
  Object.keys(A.bouts).forEach(n => joints[n + '_bout'] = px(pointPose(F, OSI[n], A.bouts[n])));
  return {s, w, h, joints, contourPx: largeurs(styleDe(o.style), s).contour};
}
// NETTOYAGE FINAL de l'image (render() seulement), à la résolution de SORTIE : une composante d'encre (coque, bord de la
// manche, arêtes, bande d'ongle — pas les rubans des plis, marques voulues) de moins de aMin pixels, qui contient au moins
// un pixel noir, est repeinte avec la peau voisine (avec sa lisière antialiasée). C'est exactement ce que l'œil lit
// comme une miette : un point, un tiret, un coin de « U » d'ongle isolé (relecture adverse : 133 fragments noirs < 20 px
// sur 96 vues après le nettoyage de la couche des traits, qui travaillait AVANT le filtre de composition et la réduction
// — un trait de 80 px de cible coupé par le filtre 5 × 5 ou aminci par la réduction ×½ donnait encore des miettes).
// JOURS ENCLOS : une petite composante transparente (alpha < 128) qui ne touche pas le bord de l'image est un jour à
// travers la main (entre le pouce et l'index du poing vu de ¾ paume : triangle blanc de ≈ 40 px cerné de noir à 1 800 px,
// relecture M5). Un jour aussi petit, entouré de trait, se dessine comme un creux sombre : il est rempli du ton du
// trait. Aire maximale : 0,3 % de l'aire opaque de la main (le triangle mesuré : 0,05 %) — l'anneau d'un O ou l'espace
// entre deux doigts écartés dépasse 3 % et reste du vrai fond.
function boucherJours(ctx, w, h, st) {
  const I = ctx.getImageData(0, 0, w, h), D = I.data, n = w * h;
  let opaques = 0; for (let p = 0; p < n; p++) if (D[4 * p + 3] >= 128) opaques++;
  const aMax = 0.003 * opaques, lab = new Uint8Array(n), file = new Int32Array(n), V4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const tr = [Math.round(st.trait.r * 255), Math.round(st.trait.g * 255), Math.round(st.trait.b * 255)];
  let bouches = 0, px = 0;
  for (let p0 = 0; p0 < n; p0++) {
    if (lab[p0] || D[4 * p0 + 3] >= 128) continue;
    let tete = 0, queue = 0, bord = false; file[queue++] = p0; lab[p0] = 1;
    while (tete < queue) {
      const p = file[tete++], x = p % w, y = (p - x) / w;
      if (x === 0 || y === 0 || x === w - 1 || y === h - 1) bord = true;
      for (const [dx, dy] of V4) {
        const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
        const q = yy * w + xx; if (!lab[q] && D[4 * q + 3] < 128) { lab[q] = 1; file[queue++] = q; }
      }
    }
    if (bord || queue > aMax) continue;
    bouches++; px += queue;
    for (let i = 0; i < queue; i++) { const q = 4 * file[i]; D[q] = tr[0]; D[q + 1] = tr[1]; D[q + 2] = tr[2]; D[q + 3] = 255; }
  }
  if (bouches) ctx.putImageData(I, 0, 0);
  return {jours: bouches, px};
}
function nettoyerImage(ctx, ctxM, w, h, aMin, st) {
  const I = ctx.getImageData(0, 0, w, h), M = ctxM.getImageData(0, 0, w, h).data, D = I.data, n = w * h;
  // couleur de remplacement d'un pixel de miette : celle du pixel OPAQUE HORS MASQUE le plus proche (anneaux de rayon 1 à
  // 4) — l'aplat et l'ombre sont des tons unis, la peau sous la miette est celle d'à côté. (Une couche « sans traits »
  // composée exprès coûtait une passe et une relecture de plus : 75 ms à 470 × 660 en rendu logiciel.)
  const S0 = new Uint8ClampedArray(D);   // l'image avant nettoyage (les voisins lus ne doivent pas être déjà repeints)
  const peauDe = (x, y) => {
    for (let r = 1; r <= 4; r++) for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
      if (Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
      const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
      const q = 4 * (yy * w + xx); if (M[q + 3] === 0 && S0[q + 3] === 255) return q;
    }
    return -1;
  };
  // ENCRE VISIBLE, à la mesure des planches (tests/engine_planches.py, engine_traits.py) : pixel opaque de luminance
  // < 95 qui n'est pas un ton d'ombre de la peau (à 16 près), ou plus sombre que le seuil « noir » ; seulement là où le
  // masque d'encre passe (jamais l'aplat ni l'ombre). DEUX passes, comme les deux comptes de la mesure : noir < 60, puis
  // noir < 70 (les miettes GRISES, « filets gris compris » de la relecture : 150). La connexité de chaque passe est
  // EXACTEMENT celle de son compte — un seuil plus large reliait des tirets par leur lisière grise (ton 68, à 13 du ton
  // d'ombre × 0,86) en un trait de 26 px que la mesure, elle, voit en morceaux de 2 à 12 px (mesuré : main plate vue de
  // bout, 4 fragments restaient). Voisinage 4 : un pixel noir qui ne touche un trait que par un coin est une miette pour
  // la mesure (ndimage.label) — il part, ce qui n'ôte qu'un pixel d'escalier au bord du trait.
  const om = [st.peau.r * RENDU.tonOmbre * 255, st.peau.g * RENDU.tonOmbre * 255, st.peau.b * RENDU.tonOmbre * 255];
  const loin = (q, k) => Math.hypot(D[q] - om[0] * k, D[q + 1] - om[1] * k, D[q + 2] - om[2] * k) > 16;
  const encre = new Uint8Array(n), lab = new Int32Array(n), file = new Int32Array(n), V4 = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  let retirees = 0;
  for (const noirMax of [60, 70]) {
    encre.fill(0); lab.fill(0);
    for (let p = 0; p < n; p++) {
      const q = 4 * p; if (M[q + 3] <= 26 || D[q + 3] < 128) continue;
      const lf = (D[q] + D[q + 1] + D[q + 2]) / 3;
      if (lf < noirMax) encre[p] = 2; else if (lf < 95 && loin(q, 1) && loin(q, 0.86)) encre[p] = 1;
    }
    let num = 0;
    for (let p0 = 0; p0 < n; p0++) {
      if (lab[p0] || !encre[p0]) continue;
      num++; let tete = 0, queue = 0, noir = false; file[queue++] = p0; lab[p0] = num;
      while (tete < queue) {
        const p = file[tete++], x = p % w, y = (p - x) / w;
        if (encre[p] === 2) noir = true;
        for (const [dx, dy] of V4) {
          const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
          const q = yy * w + xx; if (!lab[q] && encre[q]) { lab[q] = num; file[queue++] = q; }
        }
      }
      if (queue >= aMin || !noir) continue;   // trait véritable, ou lisière grise seule
      retirees++;
      for (let i = 0; i < queue; i++) {
        const p = file[i], x = p % w, y = (p - x) / w;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          const xx = x + dx, yy = y + dy; if (xx < 0 || yy < 0 || xx >= w || yy >= h) continue;
          const q = 4 * (yy * w + xx); if ((dx || dy) && (M[q + 3] === 0 || encre[yy * w + xx])) continue;   // lisière seulement, pas un AUTRE trait
          const v = peauDe(xx, yy); if (v < 0) continue;
          D[q] = S0[v]; D[q + 1] = S0[v + 1]; D[q + 2] = S0[v + 2]; D[q + 3] = S0[v + 3];
        }
      }
    }
  }
  if (retirees) ctx.putImageData(I, 0, 0);
  return retirees;
}
function render(o) {
  o = o || {};
  const w = Math.max(2, Math.round(num(o.w, 256))), h = Math.max(2, Math.round(num(o.h, 256)));
  const out = document.createElement('canvas'); out.width = w; out.height = h;
  if (!A) return out;
  const t0 = performance.now();
  const st = styleDe(o.style), B = boiteMain(o), bw = B.x1 - B.x0, bh = B.y1 - B.y0;
  const s = Math.min(w / bw, h / bh), cx = (B.x0 + B.x1) / 2, cy = (B.y0 + B.y1) / 2;
  const off = horsEcran(), R = off.R, pipe = off.pipe;
  // peau : celle du cache (copie dans le pipeline seulement si la pose change)
  pipe.poser(B.p, B.pe);
  pipe.matrice(B.M);
  const ss = clamp(Math.round(num(o.ss, RENDU.ss)), 1, 4), W = w * ss, H = h * ss;
  const px = fois(largeurs(st, s), ss);
  const zc = B.b.z1 + 20, near = 1, far = (B.b.z1 - B.b.z0) + 40;
  const hw = w / (2 * s), hh = h / (2 * s);
  const cam = new THREE.OrthographicCamera(cx - hw, cx + hw, cy + hh, cy - hh, near, far);
  cam.position.set(0, 0, zc); cam.updateMatrixWorld();
  // lu sur le processeur par le nettoyage et le bouchage des jours (3 lectures) : contexte prévu pour (sinon Chrome avertit)
  const ctx = out.getContext('2d', {willReadFrequently: true}); ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
  // seuil des miettes PROPORTIONNEL à l'échelle : 20 px a été mesuré et vérifié à 30 px/cm (planches de contrôle,
  // tailles d'écran) ; une miette est une AIRE, elle grandit comme s². Relecture M5 : à 1 800 px (≈ 80 px/cm) les mêmes
  // éclats d'arête (fond d'un pli au poing paume ¾, gribouillis sous l'annulaire) faisaient 60 à 140 px et passaient le
  // filtre — « des formes qui apparaissent » aux grands rendus seulement. Facteur (s / 30)², de 1 (écran) à 16 (A3).
  const kMiettes = clamp((s / 30) * (s / 30), 1, 16);
  const T = RENDU.tuileMax > 0 ? Math.min(off.tuile, RENDU.tuileMax) : off.tuile, aMin = RENDU.nettoyage * kMiettes * ss * ss;
  // nettoyage final (voir nettoyerImage) : on garde aussi, réduit de la même façon, le masque d'encre ; composé tuile par
  // tuile comme l'image
  const net = RENDU.nettoyage > 0 && px.contour > 0;
  const toile = () => { const c = document.createElement('canvas'); c.width = w; c.height = h; const x = c.getContext('2d'); x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high'; return x; };
  const ctxM = net ? toile() : null;
  const copie = (cible, mode, sx, sy, sw, sh, dx, dy, dw, dh, clip) => {
    if (mode !== 'complet') pipe.composer(mode, null);
    if (clip) { cible.save(); cible.beginPath(); cible.rect(...clip); cible.clip(); }
    cible.drawImage(off.canvas, sx, sy, sw, sh, dx, dy, dw, dh);
    if (clip) cible.restore();
  };
  if (W <= T && H <= T) {
    R.setSize(W, H, false); cam.updateProjectionMatrix();
    pipe.dessiner(cam, W, H, st, px, null, false, aMin);
    copie(ctx, 'complet', 0, 0, W, H, 0, 0, w, h);
    const tc0 = performance.now();
    if (net) copie(ctxM, 'masque', 0, 0, W, H, 0, 0, w, h);
    out.tCouches = performance.now() - tc0;
    out.tuiles = 1;
  } else {
    // grande image (exports ×2, ×3, A4, A3) : tuiles avec recouvrement. La marge couvre ce que chaque passe lit autour
    // d'un pixel : la coque (contour), l'anneau des arêtes (r = interne / 0,85), la fenêtre 5 × 5 de la composition et
    // le nettoyage des miettes (une miette de aMin pixels de cible, en trait de 2 px, s'étend sur aMin / 2 pixels : elle
    // est jugée en entier dans la tuile qui la garde). Marge et pas sont des MULTIPLES de ss : chaque tuile tombe sur un
    // pixel entier de l'image finale, et elle est réduite AVEC sa marge puis découpée (clip) — le filtre de réduction voit
    // les mêmes voisins qu'en une seule tuile ; recadrée avant réduction, la tuile décalait le contour de 1 à 2 px à la
    // couture (relecture adverse : marche à y ≈ 1947 px sur Repos 2200 × 2600). Vérifié par v2/tests/engine_tuiles.py.
    // (miette : aMin pixels d'un trait de l'épaisseur d'un trait intérieur, au moins 2 px ; depuis que aMin suit l'échelle
    // — relecture M5 —, aMin / 2 faisait des marges de 640 px à 3 000 px et 16 tuiles au lieu de 4)
    const marge = ss * Math.ceil((px.contour + px.interne * 2 + 8 + aMin / Math.max(2, px.interne) + RENDU.rCreux * s * ss) / ss), pas = ss * Math.floor((T - 2 * marge) / ss);
    let nb = 0; out.coutures = {x: [], y: []};
    for (let k = pas; k < W; k += pas) out.coutures.x.push(k / ss);
    for (let k = pas; k < H; k += pas) out.coutures.y.push(k / ss);
    for (let y = 0; y < H; y += pas) for (let x = 0; x < W; x += pas) {
      const x0 = Math.max(0, x - marge), y0 = Math.max(0, y - marge), tw = Math.min(W, x + pas + marge) - x0, th = Math.min(H, y + pas + marge) - y0;
      R.setSize(tw, th, false); cam.setViewOffset(W, H, x0, y0, tw, th); cam.updateProjectionMatrix();
      pipe.dessiner(cam, tw, th, st, px, null, false, aMin);
      const cw = Math.min(pas, W - x), ch = Math.min(pas, H - y), clip = [x / ss, y / ss, cw / ss, ch / ss];
      copie(ctx, 'complet', 0, 0, tw, th, x0 / ss, y0 / ss, tw / ss, th / ss, clip);
      if (net) copie(ctxM, 'masque', 0, 0, tw, th, x0 / ss, y0 / ss, tw / ss, th / ss, clip);
      nb++;
    }
    cam.clearViewOffset();
    out.tuiles = nb;
  }
  const tn0 = performance.now();
  if (net) out.miettes = nettoyerImage(ctx, ctxM, w, h, RENDU.nettoyage * kMiettes, st);
  out.seuilMiettes = RENDU.nettoyage * kMiettes;
  if (px.contour > 0 && RENDU.boucherJours !== 0) out.jours = boucherJours(ctx, w, h, st);
  out.tNettoyage = performance.now() - tn0;
  if (net && RENDU.garderCouches) out.coucheMasque = ctxM.canvas;   // tests : le masque d'encre du nettoyage
  out.dureeRendu = performance.now() - t0;
  return out;
}

/* =====================================================================================================================
   12. Marionnette : puppet(canvasHost, element, onChange, options) — EN PLACE sur l'objet main de la planche
   Un canvas WebGL remplit `canvasHost` (que la planche pose sur le cadre de l'objet) ; la caméra est orthographique et
   cadrée comme render() (même boîte, même échelle) : la main 3D se superpose exactement à l'image de la planche.
   Gestes (v1, CLAUDE.md « Mode marionnette », mobilite.md R14) :
   - tirer le BOUT d'un doigt → tout le doigt se replie (MCP : IPP : IPD = 0,85 : 1 : 0,7) ; le MILIEU → MCP + IPP ;
     la BASE → pivot + écartement ; glisser de côté = écarter / serrer ;
   - Maj = une seule articulation ; clic droit = verrou (cadenas) ; double clic = doigt tendu (paume : main ouverte) ;
   - Alt = les quatre doigts ensemble (plier, éventail) ;
   - pouce : la base (P1) déplace la trapézo-métacarpienne (avancer / rapprocher, vis sans fin), le bout le replie ;
   - paume : tourner la main ; Maj + paume : la déplacer ;
   - poignet, pronation, arc : curseurs sous le cadre ; vues face / dos / profil / dessus ;
   - la pose est écrite dans l'élément et rendue par onChange au RELÂCHEMENT (une entrée d'historique par geste) ;
     Échap / Entrée appellent options.onFin.
   Options : onFin (fin du mode), barreHote (élément où poser la barre — sinon sous le cadre), boutonFin (false : pas de
   bouton « Terminer », la planche a le sien), hauteur / largeur (cadre de repli d'un hôte sans taille), camera
   ('perspective'), antialias. L'hôte peut être transformé en CSS (rotation, miroir de l'objet) : le pointeur est lu en
   coordonnées locales.
   Chaque déplacement : constrain (butées, couplages) + préférences souples + solve depuis la dernière pose valide.
   ===================================================================================================================== */
const NOMS_SEG = {doigt: ['base', 'milieu', 'bout'], pouce: ['base', 'milieu', 'bout']};
const LIBELLE = {index: 'Index', majeur: 'Majeur', annulaire: 'Annulaire', auriculaire: 'Auriculaire', pouce: 'Pouce'};
// articulations bloquées par le verrou de chaque segment (clic droit)
const VERROU = {doigt: [['mcp', 'ab'], ['pip'], ['dip']], pouce: [['av', 'rap', 'mcp'], [], ['ip']]};
const EVENTAIL = {index: 1, majeur: 0.15, annulaire: -0.6, auriculaire: -1.2};   // Alt + glisser de côté (v1 FAN)
function segmentDeOs(nom) {
  if (nom === 'pouce_p1') return {k: 'pouce', g: 0};
  if (nom === 'pouce_p2') return {k: 'pouce', g: 2};
  const m = /^(index|majeur|annulaire|auriculaire)_p([123])$/.exec(nom);
  return m ? {k: m[1], g: +m[2] - 1} : {k: null};
}
function puppet(host, element, onChange, options) {
  if (!A) throw new Error('AtelierHand.puppet : attendre AtelierHand.ready');
  options = options || {};
  const el = element || {};
  let pose = constrain(el.pose, {passif: true}), q = qnorm(Array.isArray(el.orientation) && el.orientation.length === 4 ? el.orientation.map(x => num(x)) : [0, 0, 0, 1]);
  const cote = el.cote === 'G' ? 'G' : 'D', st = styleDe(el.style);
  const verrous = {}; ['pouce', ...DOIGTS].forEach(k => verrous[k] = [false, false, false]);
  // --- DOM ---
  host.innerHTML = '';
  const boite = document.createElement('div');
  boite.style.cssText = 'position:relative;width:100%;height:100%;touch-action:none;user-select:none';
  const cv = document.createElement('canvas'); cv.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;display:block;cursor:grab';
  const ov = document.createElement('canvas'); ov.style.cssText = 'position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none';
  const bulle = document.createElement('div');
  bulle.style.cssText = 'position:absolute;pointer-events:none;background:rgba(20,32,31,.86);color:#fff;font:12px/1.3 system-ui,sans-serif;padding:3px 7px;border-radius:6px;white-space:nowrap;transform:translate(12px,12px);display:none;z-index:3';
  const barre = document.createElement('div');
  // barre (vues, poignet, inclinaison, pronation, arc, Terminer) : dans options.barreHote si la planche en donne un (sa
  // barre contextuelle, hors de l'objet transformé) ; sinon SOUS le cadre. Relecture adverse : posée en top:100 % dans un
  // hôte en overflow:auto, elle était coupée — le poignet et la pronation étaient inaccessibles depuis la planche.
  const barreDehors = options.barreHote && options.barreHote.appendChild;
  barre.style.cssText = (barreDehors ? 'position:relative;' : 'position:absolute;left:0;top:100%;margin-top:6px;') +
    'display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center;background:rgba(255,255,255,.96);border:1px solid #9cc;border-radius:8px;padding:6px 8px;font:12px system-ui,sans-serif;color:#14201f;z-index:3;min-width:260px';
  boite.append(cv, ov, bulle); if (barreDehors) { options.barreHote.innerHTML = ''; options.barreHote.appendChild(barre); } else boite.appendChild(barre);
  host.appendChild(boite);
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const R = new THREE.WebGLRenderer({canvas: cv, antialias: options.antialias !== false, alpha: true, premultipliedAlpha: true});
  R.setPixelRatio(dpr);
  const pipe = new Pipeline(R);
  const ctrl = {durees: [], arrete: false};
  // --- cadrage : la boîte de la main au DÉBUT (l'échelle ne bouge pas pendant un geste ; elle suit l'élément au
  //     relâchement, quand la planche a redimensionné l'objet) ---
  let cam = null, echelle = 1, cw = 1, ch = 1, decal = [0, 0], selSale = true;
  // taille du cadre : celle de l'hôte (la planche le pose sur l'objet) ; un hôte sans taille propre (panneau qui suit
  // son contenu, comme le #puppet du bouchon de M3) reçoit un cadre de options.largeur × options.hauteur, ou 420 px de
  // haut aux proportions de la main
  if ((host.clientWidth || 0) < 48 || (host.clientHeight || 0) < 48) {
    // hôte sans taille propre : la marionnette ne peut pas se poser sur l'objet ; on le dit (la planche doit donner à
    // l'hôte le cadre de l'objet, e.w·zoom × e.h·zoom) et on prend un cadre de repli
    console.warn('AtelierHand.puppet : hôte sans taille (' + host.clientWidth + ' × ' + host.clientHeight + ' px) — cadre de repli ; donner à l\'hôte la taille de l\'objet');
    const b0 = boiteMain({pose, orientation: q, cote}), hh = num(options.hauteur, 420), ww = num(options.largeur, Math.round(hh * (b0.x1 - b0.x0) / (b0.y1 - b0.y0)));
    boite.style.width = ww + 'px'; boite.style.height = hh + 'px';
  }
  function cadrer() {
    cw = Math.max(16, boite.clientWidth || host.clientWidth || 360); ch = Math.max(16, boite.clientHeight || host.clientHeight || 420);
    const B = boiteMain({pose, orientation: q, cote}), bw = B.x1 - B.x0, bh = B.y1 - B.y0;
    echelle = Math.min(cw / bw, ch / bh);
    const cx = (B.x0 + B.x1) / 2, cy = (B.y0 + B.y1) / 2, hw = cw / (2 * echelle), hh = ch / (2 * echelle);
    const zc = B.b.z1 + 40, far = (B.b.z1 - B.b.z0) + 80;
    if (options.camera === 'perspective') {
      const d = 60, fov = 2 * Math.atan(hh / d) / D2R;
      cam = new THREE.PerspectiveCamera(fov, cw / ch, 1, d + 60); cam.position.set(cx, cy, d + B.b.z1);
    } else { cam = new THREE.OrthographicCamera(cx - hw, cx + hw, cy + hh, cy - hh, 1, far); cam.position.set(0, 0, zc); }
    cam.updateMatrixWorld(); cam.updateProjectionMatrix();
    R.setSize(cw, ch, false);
    ov.width = Math.round(cw * dpr); ov.height = Math.round(ch * dpr);
    selSale = true;
  }
  const M = () => { const m = matriceObjet(q, cote); if (decal[0] || decal[1]) m.premultiply(new THREE.Matrix4().makeTranslation(decal[0], decal[1], 0)); return m; };
  // projection d'un point de la main (cm, repère de la main) en pixels CSS du canvas
  const _v = new THREE.Vector3();
  function ecran(pt, Mx) {
    _v.set(pt[0], pt[1], pt[2]).applyMatrix4(Mx || M()).project(cam);
    return [(_v.x + 1) / 2 * cw, (1 - _v.y) / 2 * ch];
  }
  function dessiner(complet) {
    if (ctrl.arrete) return;
    const t0 = performance.now();
    pipe.poser(pose); pipe.matrice(M());
    const W = Math.round(cw * dpr), H = Math.round(ch * dpr);
    if (geste && !complet && RENDU.rapideK < 1) pipe.dessinerGeste(cam, W, H, st, k => largeurs(st, echelle * dpr * k), RENDU.rapideK);
    else pipe.dessiner(cam, W, H, st, largeurs(st, echelle * dpr), null, !!geste && !complet);
    selSale = true;
    dessinerSurcouche();
    ctrl.durees.push(performance.now() - t0); if (ctrl.durees.length > 200) ctrl.durees.shift();
  }
  let demande = false;
  const redessiner = () => { if (demande) return; demande = true; requestAnimationFrame(() => { demande = false; dessiner(); }); };
  // surcouche 2D : cadenas des articulations verrouillées
  function dessinerSurcouche() {
    const x = ov.getContext('2d'); x.setTransform(dpr, 0, 0, dpr, 0, 0); x.clearRect(0, 0, cw, ch);
    const F = pipe.F || fk(pose), Mx = M();
    for (const k in verrous) verrous[k].forEach((v, g) => {
      if (!v) return;
      const os = k === 'pouce' ? ['pouce_p1', 'pouce_p1', 'pouce_p2'][g] : k + '_p' + (g + 1);
      const [sx, sy] = ecran(F.C[OSI[os]], Mx);
      x.fillStyle = 'rgba(20,32,31,.9)'; x.strokeStyle = '#fff'; x.lineWidth = 1.5;
      x.beginPath(); x.arc(sx, sy - 4, 4, Math.PI, 0); x.stroke();            // anse
      x.fillRect(sx - 5.5, sy - 4, 11, 9); x.strokeRect(sx - 5.5, sy - 4, 11, 9);
    });
  }
  // --- sélection : passe d'identité (os dominant) sous le pointeur ---
  // coordonnées du pointeur DANS le cadre (px CSS non transformés) : offsetX / offsetY tiennent compte de la rotation,
  // du miroir et de l'échelle CSS que la planche donne à l'hôte (il est posé sur l'objet, transformé comme lui) ;
  // clientX − rect.left ne vaut que pour un hôte droit
  function loc(ev) {
    if (ev.target === cv && typeof ev.offsetX === 'number') return [ev.offsetX, ev.offsetY];
    const r = cv.getBoundingClientRect(); return [(ev.clientX - r.left) * cw / (r.width || cw), (ev.clientY - r.top) * ch / (r.height || ch)];
  }
  function sous(ev) {
    const [x, y] = loc(ev);
    if (selSale) { pipe.poser(pose); pipe.matrice(M()); pipe.selection(cam, Math.round(cw * dpr), Math.round(ch * dpr)); selSale = false; }
    const px = pipe.lirePixel(x * dpr, y * dpr);
    if (!px || px.os < 0 || px.os > 19) return null;
    const s = segmentDeOs(OS[px.os]);
    return Object.assign(s, {x, y});
  }
  const libelle = s => !s ? '' : s.k === null ? 'Main · tourner (Maj : déplacer)' :
    LIBELLE[s.k] + ' · ' + NOMS_SEG[s.k === 'pouce' ? 'pouce' : 'doigt'][s.g] + (verrous[s.k][s.g] ? ' · verrouillé' : '');
  function montrerBulle(s, ev, extra) {
    if (!s && !extra) { bulle.style.display = 'none'; return; }
    const [bx, by] = loc(ev);
    bulle.textContent = extra || libelle(s); bulle.style.display = 'block';
    bulle.style.left = bx + 'px'; bulle.style.top = by + 'px';
  }
  // --- axes du geste (v1 grabAxes) : direction écran de l'extrémité du segment pour +3° de chaque groupe ---
  const bloque = (k, champ) => { const t = k === 'pouce' ? 'pouce' : 'doigt'; return VERROU[t].some((l, g) => l.includes(champ) && verrous[k][g]); };
  function finSegment(F, k, g) {
    if (k === 'pouce') return g === 0 ? F.C[OSI.pouce_p2] : pointPose(F, OSI.pouce_p2, A.bouts.pouce_p2);
    return g < 2 ? F.C[OSI[k + '_p' + (g + 2)]] : pointPose(F, OSI[k + '_p3'], A.bouts[k + '_p3']);
  }
  function axesGeste(p0, s, maj, groupe) {
    const k = s.k, t = k === 'pouce' ? 'pouce' : 'doigt', axes = [];
    groupe = groupe && k !== 'pouce';
    let jeu = GRAB[t][s.g];
    if (maj) jeu = t === 'pouce' ? (s.g === 0 ? {mcp: 1} : {ip: 1}) : [{mcp: 1}, {pip: 1}, {dip: 1}][s.g];
    const ks = groupe ? DOIGTS.filter(f => f === k || !verrous[f].some(Boolean)) : [k];
    const js = Object.keys(jeu).filter(n => maj || !bloque(k, n));
    if (js.length) axes.push({flex: true, set: (p, c) => ks.forEach(f => js.forEach(n => p[f][n] = p0[f][n] + c * jeu[n]))});
    if (!maj && !verrous[k][0]) {
      if (t === 'pouce') axes.push({set: (p, c) => p.pouce.rap = p0.pouce.rap + c});
      else if (groupe) { const sg = Math.sign(EVENTAIL[k]) || 1; axes.push({set: (p, c) => ks.forEach(f => p[f].ab = p0[f].ab + c * EVENTAIL[f] * sg)}); }
      else axes.push({set: (p, c) => p[k].ab = p0[k].ab + c});
    }
    const Mx = M(), F0 = fk(p0), e0 = ecran(finSegment(F0, k, s.g), Mx), b0 = ecran(F0.C[OSI[k === 'pouce' ? 'pouce_p1' : k + '_p1']], Mx);
    axes.forEach(a => {
      const p = clone(p0); a.set(p, 3); const F1 = fk(normalise(p)), w1 = finSegment(F1, k, s.g), e1 = ecran(w1, Mx);
      a.dir = [(e1[0] - e0[0]) / 3, (e1[1] - e0[1]) / 3];
      if (a.flex) {   // un bout qui vient vers l'œil ne bouge pas à l'écran : on lui donne la direction de sa base
        const w0 = finSegment(F0, k, s.g), dz = (new THREE.Vector3(w1[0] - w0[0], w1[1] - w0[1], w1[2] - w0[2]).transformDirection(Mx).z) * echelle / 3;
        const ub = [b0[0] - e0[0], b0[1] - e0[1]], l = Math.hypot(ub[0], ub[1]);
        if (l > 1) { a.dir[0] += ub[0] / l * Math.abs(dz) * 0.6; a.dir[1] += ub[1] / l * Math.abs(dz) * 0.6; }
      }
    });
    return axes;
  }
  // --- gestes ---
  let geste = null;
  function surDown(ev) {
    if (ev.button === 2) return;
    const s = sous(ev);
    if (!s) return;
    ev.preventDefault(); cv.setPointerCapture(ev.pointerId);
    const [lx, ly] = loc(ev);
    geste = {s, x0: lx, y0: ly, p0: clone(pose), q0: q.slice(), ok: clone(pose), maj: ev.shiftKey, alt: ev.altKey, d0: decal.slice()};
    if (s.k !== null) geste.axes = axesGeste(clone(pose), s, ev.shiftKey, ev.altKey);
    cv.style.cursor = 'grabbing';
  }
  let attente = null;
  function surMove(ev) {
    if (!geste) { const s = sous(ev); const part = s ? (s.k === null ? 0 : PARTIES.indexOf(s.k)) : -10;
      if (pipe.u.hlPart.value !== part) { pipe.survol(part); redessiner(); }
      montrerBulle(s, ev); cv.style.cursor = s ? 'grab' : 'default'; return; }
    attente = ev;
    requestAnimationFrame(() => { if (!attente || !geste) return; const e = attente; attente = null; glisser(e); });
  }
  function glisser(ev) {
    const [lx, ly] = loc(ev), dx = lx - geste.x0, dy = ly - geste.y0, s = geste.s;
    if (s.k === null) {
      if (geste.maj) decal = [geste.d0[0] + dx / echelle, geste.d0[1] - dy / echelle];
      else q = qnorm(qmul(qmul(QY(dx * 0.45), QX(dy * 0.45)), geste.q0));
    } else {
      const p = clone(geste.p0), Ax = geste.axes;
      if (Ax.length === 1) { const d = Ax[0].dir, l = d[0] * d[0] + d[1] * d[1]; Ax[0].set(p, l > 0.01 ? (d[0] * dx + d[1] * dy) / l : 0); }
      else if (Ax.length === 2) {
        const a = Ax[0].dir, b = Ax[1].dir, lam = 0.02, aa = a[0] * a[0] + a[1] * a[1] + lam, bb = b[0] * b[0] + b[1] * b[1] + lam,
          ab = a[0] * b[0] + a[1] * b[1], am = a[0] * dx + a[1] * dy, bm = b[0] * dx + b[1] * dy, det = aa * bb - ab * ab;
        Ax[0].set(p, (bb * am - ab * bm) / det); Ax[1].set(p, (aa * bm - ab * am) / det);
      }
      let c = constrain(p);
      c = preferences(c, geste.alt ? null : s.k, verrous, {maj: geste.maj, doigts: s.k === 'pouce' ? [] : geste.alt ? DOIGTS.filter(f => f === s.k || !verrous[f].some(Boolean)) : [s.k]});
      c = constrain(c);
      pose = solve(geste.ok, c); geste.ok = clone(pose);
    }
    montrerBulle(s, ev, s.k === null ? null : libelle(s) + avertissement());
    dessiner();
  }
  const avertissement = () => { const d = diagnostic(pose); return d.length ? ' · posture forcée' : ''; };
  function surUp(ev) {
    if (!geste) return;
    const g = geste; geste = null; cv.style.cursor = 'grab';
    dessiner(true);      // fin du geste : l'image de qualité complète
    try { cv.releasePointerCapture(ev.pointerId); } catch (e) {}
    const [lx, ly] = loc(ev), bouge = Math.hypot(lx - g.x0, ly - g.y0) > 1;
    if (!bouge) return;
    publier(g.s.k === null && g.maj);
  }
  function publier(deplace) {
    const extra = {orientation: q.slice()};
    el.pose = clone(pose); el.orientation = q.slice();
    if (deplace && (decal[0] || decal[1])) {
      // déplacement : en unités de la planche (le cadre de l'objet mesure el.w × el.h pour cw × ch pixels)
      const kx = num(el.w, cw) / cw, ky = num(el.h, ch) / ch;
      const dx = decal[0] * echelle * kx, dy = -decal[1] * echelle * ky;
      if (typeof el.x === 'number') el.x += dx; if (typeof el.y === 'number') el.y += dy;
      extra.dx = dx; extra.dy = dy; decal = [0, 0];
    }
    if (typeof onChange === 'function') onChange(clone(pose), extra);
    requestAnimationFrame(() => { if (!ctrl.arrete) { cadrer(); dessiner(); } });
  }
  function surMenu(ev) {
    ev.preventDefault(); const s = sous(ev); if (!s || s.k === null) return;
    verrous[s.k][s.g] = !verrous[s.k][s.g]; montrerBulle(s, ev); dessinerSurcouche();
  }
  function surDouble(ev) {
    const s = sous(ev); if (!s) return; const t = clone(pose);
    if (s.k === null) { DOIGTS.forEach(k => Object.assign(t[k], {mcp: 0, pip: 0, dip: 0})); Object.assign(t.pouce, {mcp: 0, ip: 0}); }
    else if (s.k === 'pouce') Object.assign(t.pouce, {mcp: 0, ip: 0});
    else (ev.altKey ? DOIGTS : [s.k]).forEach(k => Object.assign(t[k], {mcp: 0, pip: 0, dip: 0}));
    pose = solve(pose, t); dessiner(); publier(false);
  }
  function surQuitte() { if (!geste) { montrerBulle(null); if (pipe.u.hlPart.value !== -10) { pipe.survol(-10); redessiner(); } } }
  function surTouche(ev) {
    // écouté en CAPTURE sur window et arrêté ici : sinon le raccourci « Entrée = marionnette » de la planche (écouté sur
    // document, donc AVANT window en remontée) relançait la marionnette au moment même où elle se fermait
    if (ev.key === 'Escape' || ev.key === 'Enter') { if (typeof options.onFin === 'function') { ev.preventDefault(); ev.stopPropagation(); options.onFin(); } }
  }
  cv.addEventListener('pointerdown', surDown); cv.addEventListener('pointermove', surMove); cv.addEventListener('pointerup', surUp);
  cv.addEventListener('pointercancel', surUp); cv.addEventListener('contextmenu', surMenu); cv.addEventListener('dblclick', surDouble);
  cv.addEventListener('pointerleave', surQuitte); window.addEventListener('keydown', surTouche, true);
  // --- barre : vues, poignet, pronation, arc, terminer ---
  const VUES_M = {face: [0, 0, 0, 1], dos: QY(180), profil: QY(-90), dessus: QX(90)};
  const bouton = (txt, titre, f) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = txt; b.title = titre;
    b.style.cssText = 'font:12px system-ui,sans-serif;padding:2px 7px;border:1px solid #9cc;border-radius:6px;background:#fff;cursor:pointer'; b.onclick = f; return b; };
  const vues = document.createElement('span');
  Object.keys(VUES_M).forEach(n => vues.appendChild(bouton(n, 'Vue ' + n, () => { q = VUES_M[n].slice(); cadrer(); dessiner(); publier(false); })));
  barre.appendChild(vues);
  const curseurs = {};
  const curseur = (lab, lire, ecrire, mn, mx, pas) => {
    const l = document.createElement('label'); l.style.cssText = 'display:inline-flex;align-items:center;gap:4px';
    const i = document.createElement('input'); i.type = 'range'; i.min = mn; i.max = mx; i.step = pas || 1; i.value = lire(); i.style.width = '86px';
    i.oninput = () => { const t = clone(pose); ecrire(t, +i.value); pose = solve(pose, t); i.value = lire(); dessiner(); };
    i.onchange = () => publier(false);
    l.append(lab, i); barre.appendChild(l); curseurs[lab] = {i, lire};
  };
  const bp = (o, c, ps) => borne(o, c, ps);
  curseur('poignet', () => pose.poignet.flex, (t, v) => t.poignet.flex = v, ...bp('poignet', 'flex'));
  curseur('inclinaison', () => pose.poignet.dev, (t, v) => t.poignet.dev = v, ...bp('poignet', 'dev'));
  curseur('pronation', () => pose.prono, (t, v) => t.prono = v, ...bp('poignet', 'prono'));
  curseur('arc', () => pose.arc, (t, v) => t.arc = v, 0, 1, 0.05);
  if (typeof options.onFin === 'function' && options.boutonFin !== false) barre.appendChild(bouton('Terminer', 'Terminer (Échap / Entrée)', () => options.onFin()));
  // suit la taille du cadre (la planche redimensionne l'objet après chaque geste)
  let ro = null;
  if (window.ResizeObserver) { ro = new ResizeObserver(() => { if (!geste && !ctrl.arrete) { cadrer(); dessiner(); } }); ro.observe(host); }
  cadrer(); dessiner();
  return Object.assign(ctrl, {
    stop() {
      ctrl.arrete = true;
      cv.removeEventListener('pointerdown', surDown); cv.removeEventListener('pointermove', surMove); cv.removeEventListener('pointerup', surUp);
      cv.removeEventListener('pointercancel', surUp); cv.removeEventListener('contextmenu', surMenu); cv.removeEventListener('dblclick', surDouble);
      cv.removeEventListener('pointerleave', surQuitte); window.removeEventListener('keydown', surTouche, true);
      if (ro) ro.disconnect();
      try { R.dispose(); R.forceContextLoss(); } catch (e) {}
      host.innerHTML = ''; if (barre.parentNode) barre.parentNode.removeChild(barre);
    },
    pose: () => clone(pose), orientation: () => q.slice(), verrous: () => clone(verrous),
    vue: n => { if (VUES_M[n]) { q = VUES_M[n].slice(); cadrer(); dessiner(); } },
    poser: p => { pose = constrain(p, {passif: true}); Object.values(curseurs).forEach(c => c.i.value = c.lire()); cadrer(); dessiner(); },
    rafraichir: () => dessiner(),
    _rendu: () => ({R, pipe}),   // pour les tests (profil des passes)
    // temps d'un rafraîchissement COMPLET (peau + rendu, achèvement forcé par la lecture d'un pixel : sous swiftshader
    // gl.finish ne bloque pas, outil.md § 4.2)
    // (le travail déjà en file — l'image précédente — est vidé AVANT de lancer le chronomètre : sinon on le compte aussi,
    // mesuré 360 ms au lieu de 125 pour une image de geste précédée d'une image complète)
    chrono: (rapide) => { const g0 = geste, b = new Uint8Array(4), gl = R.getContext(); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, b);
      if (rapide) geste = geste || {}; const t0 = performance.now(); pipe.cle = null; dessiner();
      gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, b); geste = g0;
      return performance.now() - t0; },
    // pour les tests : coordonnées écran (px CSS du canvas) d'un point d'un segment ('index', 2 = bout)
    ecranDe: (k, g) => { const F = fk(pose); return ecran(finSegment(F, k, g)); },
    centreDe: (k, g) => { const F = fk(pose), os = k === 'pouce' ? ['pouce_p1', 'pouce_p1', 'pouce_p2'][g] : k + '_p' + (g + 1), fin = finSegment(F, k, g);
      return ecran(vlerp(F.C[OSI[os]], fin, 0.55)); }
  });
}
/* =====================================================================================================================
   13. Presets : les 15 de la v1 (convertis : mêmes noms, mêmes signes, écartement par rapport au majeur), l'alphabet
   LSF A–Z, les chiffres 0–10 et les formes de base de mobilite.md § 4.4. Les valeurs écrites ici sont l'INTENTION ;
   au chargement chaque preset passe par settle (pouce écarté, doigts, pouce : comme la v1) puis solve, et c'est la
   pose résolue que l'API expose (aucun preset ne traverse : pénétration mesurée sur la peau, JOURNAL.md).
   Les pouces qui se POSENT quelque part (O, pince, D, becs…) ont été réglés par `reach` (pulpe du pouce sur la cible,
   v2/tests/engine_presets.py) puis recopiés ici. Quand les sources divergent sur une forme LSF, le preset porte une
   `note` « à valider par l'utilisateur » (c'est lui la référence, CLAUDE.md) ; le moteur ignore ce champ texte.
   ===================================================================================================================== */
const Fd = (mcp, pip, dip, ab, rot) => ({mcp, pip, dip, ab: ab || 0, rot: rot || 0});
const TH = (av, rap, mcp, ip, abdMcp) => ({av, rap, mcp, ip, abdMcp: abdMcp || 0});
const H = (pouce, i, m, a, au, extra) => Object.assign({poignet: {flex: 0, dev: 0}, prono: 0, arc: 0, pouce, index: i, majeur: m, annulaire: a, auriculaire: au}, extra || {});
const OUV = Fd(0, 0, 0, 0);
// doigt replié du poing (photos 2357 / 2364 : MCP 90, IPP 100–105, IPD 60–70), écartement = l'ÉVENTAIL NEUTRE du doigt
// (sa liaison) : poing fermé, chaque doigt reste dans l'axe de son rayon (voir R2 dans constrain) ; la v1 écrivait 0
// (« parallèle au majeur ») parce que sa main dessinée n'avait pas d'éventail de liaison
const EV0 = {index: 4, majeur: 0, annulaire: -5.5, auriculaire: -14};
const PLI = k => Fd(90, 105, 70, EV0[k]);
// doigts tendus serrés : la v1 serrait index −6, annulaire +6, auriculaire +9 (bouts qui convergent) ; le solveur
// arrête chaque doigt au contact du voisin (siège 1,5 mm), la valeur écrite est l'intention « serré »
const SER = {index: Fd(0, 0, 0, -6), majeur: Fd(0, 0, 0, 0), annulaire: Fd(0, 0, 0, 6), auriculaire: Fd(0, 0, 0, 9)};
const ECARTE = {index: Fd(0, 0, 0, 14), majeur: Fd(0, 0, 0, 0), annulaire: Fd(0, 0, 0, -10), auriculaire: Fd(0, 0, 0, -32)}; // photo 2354 : écarts 7 / 6 / 32° … max (5)
const tous = f => [f, f, f, f];
const PRESETS_INTENTION = {
  // ---------- les 15 de la v1 ----------
  'Dessin': null,          // = hand_v2.json « dessin » (pose ajustée par M1 sur la silhouette de son dessin, IoU 0,94)
  'Repos': H(TH(25, 10, 10, 15), Fd(18, 28, 14, 5), Fd(22, 33, 16, 0), Fd(27, 38, 18, -3), Fd(32, 42, 20, -8), {poignet: {flex: -15, dev: 0}}),
  'Main plate (B)': H(TH(20, 35, 30, 10), SER.index, SER.majeur, SER.annulaire, SER.auriculaire),
  'Poing (A)': H(TH(5, 35, 10, 5), PLI('index'), PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),
  // relecture M5 : avec TH(27, 23,6, 28,5, 29) (cible = pulpe entre les P2 de l'index et du majeur) le pouce montait en
  // diagonale vers le bout de l'index. Photo 2357 : la P2 du pouce est COUCHÉE sur la P2 de l'index, la pulpe sur celle
  // du majeur. Recherche sur grille (av 15–50, rap 15–60, MCP 15–60, IP 10–70 ; 5 600 poses, puis affinage) du coût
  // |pulpe − dos de P2 du majeur| + |IP du pouce − dos de P2 de l'index| (+ rayon du pouce) : 1,97 → 0,90 cm, pénétration
  // inchangée (2,92 mm de capsules) ; vue côté pouce : même lecture que la photo
  'Poing serré': H(TH(29, 30, 29, 28.5),
    PLI('index'), PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),
  'Index (1)': H(TH(34.5, 36, 31.5, 31),   // reach : pouce posé sur les P2 du majeur et de l'annulaire
    OUV, PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),
  'V (2)': H(TH(35, 45, 38.5, 12.5),   // reach : pouce sur les P2 repliés ; écart index–majeur 38° (photo 2359 : 35–40°)
    Fd(0, 0, 0, 18), Fd(0, 0, 0, -20), PLI('annulaire'), PLI('auriculaire')),   // photo 2359 : 35–40° d'écart (v1 : ±8, trop serré)
  'Trois (3)': H(TH(14, 2, 0, 0), Fd(0, 0, 0, -6), Fd(0, 0, 0, 0), PLI('annulaire'), PLI('auriculaire')),
  // photo 2370 : quatre doigts tendus ÉCARTÉS (la v1 les serrait), pouce replié en travers de la paume vers la base de
  // l'annulaire (mobilite.md § 4.3)
  'Quatre (4)': H(TH(30, 42, 45, 30), Fd(0, 0, 0, 12), Fd(0, 0, 0, 0), Fd(0, 0, 0, -10), Fd(0, 0, 0, -30)),   // annulaire–auriculaire 20° (photo : ≈ 30)
  'Main ouverte (5)': H(TH(8, -12, 0, 0), ECARTE.index, ECARTE.majeur, ECARTE.annulaire, ECARTE.auriculaire),
  'L': H(TH(0, -28, 0, 0), OUV, PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),                 // mobilite.md 4.2 : rap −25 à −30 (angle droit)
  'Y': H(TH(0, -28, 0, 0), PLI('index'), PLI('majeur'), PLI('annulaire'), Fd(0, 0, 0, -30)),
  'C': H(TH(45, 5, 10, 10), Fd(35, 45, 30, -6), Fd(35, 45, 30, 0), Fd(35, 45, 30, 6), Fd(35, 45, 30, 9), {arc: 0.4}),
  'O': H(TH(37, 15.5, 33.5, 16), Fd(62, 62, 25, -2),   // reach : pulpe du pouce sur la pulpe de l'index (photo 2367)
    Fd(58, 62, 42, 0), Fd(60, 64, 42, 2), Fd(62, 66, 44, 4), {arc: 0.6}),
  'Pince': H(TH(45, 9, 47.5, 16), Fd(66, 63, 15, 0),   // reach : pulpe contre pulpe
    SER.majeur, SER.annulaire, SER.auriculaire),
  // ---------- formes de base (mobilite.md § 4.4) ----------
  'Main plate': H(TH(0, 0, 0, 0), SER.index, SER.majeur, SER.annulaire, SER.auriculaire),
  'Main plate hyperétendue': H(TH(0, 0, 0, -10), Fd(-20, 0, 0, -6), Fd(-20, 0, 0, 0), Fd(-20, 0, 0, 6), Fd(-25, 0, 0, 9), {poignet: {flex: -45, dev: 0}}),
  'Moufle': H(TH(15, -15, 0, 0), SER.index, SER.majeur, SER.annulaire, SER.auriculaire),
  'Angle droit': H(TH(0, 0, 0, 0), Fd(90, 0, 0, -6), Fd(90, 0, 0, 0), Fd(90, 0, 0, 6), Fd(90, 0, 0, 9)),
  'Bec de canard fermé': H(TH(29.4, 42, 6, -15), Fd(87, 5, 0, -4), Fd(84, 5, 0, 0),   // reach : pulpe du pouce sous les bouts
    Fd(80, 5, 0, 4), Fd(80, 5, 0, 6)),
  'Bec de canard ouvert': H(TH(45, 10, 0, 0), Fd(65, 10, 5, -4), Fd(65, 10, 5, 0), Fd(65, 10, 5, 4), Fd(65, 10, 5, 6)),
  'Bec de canard rond': H(TH(45, 20, 20, 25), Fd(50, 50, 35, -4), Fd(50, 50, 35, 0), Fd(50, 50, 35, 4), Fd(50, 50, 35, 6), {arc: 0.6}),
  'Cône': H(TH(45, 30, 20, 20), Fd(60, 50, 30, -8), Fd(60, 50, 30, 0), Fd(60, 50, 30, 8), Fd(60, 50, 30, 12), {arc: 1}),
  'Bec d’oie fermé': H(TH(31, 42, 5, -11), Fd(90, 0, 0, -4), Fd(89, 0, 0, 0),   // reach
    PLI('annulaire'), PLI('auriculaire')),
  'Bec d’oie ouvert': H(TH(45, 10, 0, 0), Fd(60, 20, 10, -4), Fd(60, 20, 10, 0), PLI('annulaire'), PLI('auriculaire')),
  'Bec d’oiseau fermé': H(TH(24.5, 28.5, 16.5, -7), Fd(60, 40, 37, 0),   // reach : IP du pouce en légère hyperextension (appui, R5)
    PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),
  'Bec d’oiseau ouvert': H(TH(40, 10, 0, 0), Fd(50, 20, 10, 0), PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),
  'Bec d’oiseau rond': H(TH(37, 18.5, 28.5, 16.5), Fd(64, 58, 22, 0),   // reach
    PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),
  'Pince fermée': H(TH(20.5, 25, 15, -3), Fd(55, 55, 28, 0),   // reach
    OUV, Fd(0, 0, 0, -6), Fd(0, 0, 0, -16)),
  'Pince ouverte': H(TH(40, 10, 5, 5), Fd(30, 20, 5, 0), OUV, Fd(0, 0, 0, -6), Fd(0, 0, 0, -16)),
  'Pince ronde (F)': H(TH(37, 12, 44, 3.5), Fd(61, 66, 20, 0),   // reach
    OUV, Fd(0, 0, 0, -10), Fd(0, 0, 0, -24)),
  'Index plié': H(TH(40, 35, 40, 40), Fd(10, 90, 65, 0), PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),
  'Majeur': H(TH(40, 35, 40, 40), PLI('index'), OUV, PLI('annulaire'), PLI('auriculaire')),
  'Majeur pouce': H(TH(32, 30, 25, 18), Fd(0, 0, 0, 10), Fd(58, 68.5, 18.5, 0),   // reach : pulpe contre pulpe
    Fd(0, 0, 0, -8), Fd(0, 0, 0, -22)),
  'Pouce levé': H(TH(0, -28, 0, -10), PLI('index'), PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),            // photos 2374 / 2375
  'U pouce': H(TH(0, -25, 0, 0), Fd(0, 0, 0, -3), Fd(0, 0, 0, 0), PLI('annulaire'), PLI('auriculaire')),
  // prise en CLÉ (latérale) : l'index courbé, la pulpe du pouce pressée contre le flanc radial de sa P2. Relecture
  // adverse : l'ancien TH(5, 0, 0, 0) laissait le pouce ouvert en L, à plus de 3 cm de l'index. Réglé par reach (cible
  // 'flanc:index_p2', grille de 5 × 5 départs) : écart pulpe–flanc 0,2 mm, index 70 / 75 / 35
  'Clé': H(TH(12.5, 13.5, 21, 23.5), Fd(70, 75, 35, 4), PLI('majeur'), PLI('annulaire'), PLI('auriculaire')),
  'Griffe': H(TH(40, 0, 20, 40), Fd(30, 80, 55, 12), Fd(30, 80, 55, 0), Fd(30, 80, 55, -8), Fd(30, 80, 55, -20)),
  'Cornes': H(TH(40, 35, 40, 40), Fd(0, 0, 0, 10), PLI('majeur'), PLI('annulaire'), Fd(0, 0, 0, -35)),
  'Cornes et pouce': H(TH(0, -25, 0, 0), Fd(0, 0, 0, 10), PLI('majeur'), PLI('annulaire'), Fd(0, 0, 0, -35)),
  'V plié': H(TH(40, 35, 40, 40), Fd(40, 60, 40, 8), Fd(40, 60, 40, -8), PLI('annulaire'), PLI('auriculaire')),
  'V serré (U)': H(TH(40, 35, 40, 40), Fd(0, 0, 0, -3), Fd(0, 0, 0, 0), PLI('annulaire'), PLI('auriculaire')),
  'V écarté': H(TH(40, 35, 40, 40), Fd(0, 0, 0, 18), Fd(0, 0, 0, -18), PLI('annulaire'), PLI('auriculaire')),
  // forme relevée sur les photos 2368 / 2369 de l'utilisateur : index et majeur tendus, pouce en anneau avec l'annulaire
  'Pince annulaire': H(TH(42, 38, 25, 20), Fd(0, 0, 0, 16), Fd(0, 0, 0, -14), Fd(52, 62, 22, -5.5), Fd(72, 88, 48, -14), {arc: 0.7}),
  'Poing pouce dedans': H(TH(10, 40, 40, 20), Fd(85, 85, 40, 0), Fd(85, 85, 40, 0), Fd(85, 85, 40, 0), Fd(85, 90, 45, 0)),
};
// les lettres et les chiffres : la plupart sont des formes ci-dessus (même pose, autre nom)
const ALIAS = {
  'Lettre A': ['Poing (A)'], 'Lettre B': ['Main plate (B)'], 'Lettre C': ['C'],
  'Lettre D': [H(TH(32, 42, 39, 28), OUV, Fd(61, 81, 40, 0), Fd(61, 60, 40, -5.5), Fd(90, 85, 40, -11)),   // reach : bouts des trois doigts sur la pulpe du pouce (écart 0,1 mm)
    'D : index tendu, majeur, annulaire et auriculaire repliés, leurs bouts contre la pulpe du pouce — à valider par l’utilisateur'],
  'Lettre E': [H(TH(10, 40, 50, 30), Fd(65, 90, 60, -4), Fd(65, 90, 60, 0), Fd(65, 90, 60, 4), Fd(65, 90, 60, 6)),
    'E en griffe : bouts des doigts contre le dos du pouce replié à plat (sources : Wikipedia FR/EN) — à valider par l’utilisateur'],
  'Lettre F': ['Pince ronde (F)'],
  'Lettre G': [H(TH(0, 0, 0, 0), OUV, PLI('majeur'), PLI('annulaire'), PLI('auriculaire')), 'G : index et pouce tendus parallèles ; pointés vers le haut ou à l’horizontale selon les sources (orientation de la main) — à valider par l’utilisateur'],
  'Lettre H': [H(TH(32, 30, 25, 18), Fd(0, 0, 0, 10), Fd(58, 68.5, 18.5, 0), Fd(0, 0, 0, -8), Fd(0, 0, 0, -22)),
    'H : forme « majeur–pouce » (Wikipedia EN, Wikisign) ; d’autres tableaux montrent index et majeur tendus à l’horizontale — à trancher par l’utilisateur'],
  'Lettre I': [H(TH(25, 35, 35, 50), PLI('index'), PLI('majeur'), PLI('annulaire'), Fd(0, 0, 0, -10))],
  'Lettre J': [H(TH(0, -28, 0, 0), PLI('index'), PLI('majeur'), PLI('annulaire'), Fd(0, 0, 0, -30)), 'J : forme de Y qui pivote (mouvement : flèche) — à valider par l’utilisateur'],
  'Lettre K': [H(TH(45, 10, 0, 0), Fd(0, 0, 0, 8), Fd(0, 0, 0, -8), PLI('annulaire'), PLI('auriculaire')), 'K : V, pouce tendu posé à la base du majeur ; certains tableaux le confondent avec R — à valider par l’utilisateur'],
  'Lettre L': ['L'],
  'Lettre M': [H(TH(10, 40, 30, 10), Fd(80, 40, 10, 0), Fd(80, 40, 10, 0), Fd(80, 40, 10, 0), PLI('auriculaire')), 'M : trois doigts repliés SUR le pouce, main de côté (orientation) — à valider par l’utilisateur'],
  'Lettre N': [H(TH(10, 40, 30, 10), Fd(80, 40, 10, 0), Fd(80, 40, 10, 0), PLI('annulaire'), PLI('auriculaire')), 'N : comme M avec deux doigts — à valider par l’utilisateur'],
  'Lettre O': ['O'],
  'Lettre P': [H(TH(45, 10, 0, 0), Fd(0, 0, 0, 8), Fd(0, 0, 0, -8), PLI('annulaire'), PLI('auriculaire'), {poignet: {flex: 60, dev: 0}}), 'P : K orienté vers le bas (« hochement ») — à valider par l’utilisateur'],
  'Lettre Q': [H(TH(0, 0, 0, 0), OUV, PLI('majeur'), PLI('annulaire'), PLI('auriculaire'), {poignet: {flex: 60, dev: 0}}), 'Q : G orienté vers le bas — à valider par l’utilisateur'],
  'Lettre R': [H(TH(25, 35, 35, 50), Fd(15, 0, 0, 2), Fd(5, 0, 0, 10, 10), PLI('annulaire'), PLI('auriculaire')),
    'R : index et majeur CROISÉS (le majeur passe devant l’index) ; le solveur ne superpose pas deux doigts : le majeur vient au contact, tourné de 10° (rotation axiale passive) — à valider par l’utilisateur'],
  'Lettre S': ['Poing serré'],
  'Lettre T': [H(TH(20, 35, 45, 20), Fd(45, 60, 30, 0), OUV, Fd(0, 0, 0, -6), Fd(0, 0, 0, -16)),
    'T : variante LSF retenue = pouce replié contre l’intérieur de l’index courbé ; plusieurs tableaux montrent le pouce glissé entre index et majeur (T de l’ASL) — à trancher par l’utilisateur'],
  'Lettre U': ['V serré (U)'], 'Lettre V': ['V (2)'],
  'Lettre W': [H(TH(15, 35, 30, 40), Fd(0, 0, 0, 10), Fd(0, 0, 0, 0), Fd(0, 0, 0, -10), PLI('auriculaire'))],
  'Lettre X': [H(TH(40, 35, 40, 40), Fd(30, 80, 60, 0), PLI('majeur'), PLI('annulaire'), PLI('auriculaire')), 'X : index en crochet (tableaux français) ; Wikipedia EN : index ET majeur courbés — à valider par l’utilisateur'],
  'Lettre Y': ['Y'], 'Lettre Z': ['Index (1)', 'Z : index tendu qui trace un Z (mouvement : flèche)'],
  'Chiffre 0': ['O'], 'Chiffre 1': ['Index (1)'], 'Chiffre 2': ['V (2)'], 'Chiffre 3': ['Trois (3)', '3 = pouce + index + majeur (famille « pouce compte », choix de la v1) ; variante index + majeur + annulaire'],
  'Chiffre 4': ['Quatre (4)'], 'Chiffre 5': ['Main ouverte (5)'],
};
// Chiffres AU-DELÀ DE 5 : CLAUDE.md (« Chiffres ») — « les formes varient d'un usage à l'autre : elles ne sont PAS
// devinées, à poser à la main et à ranger dans la bibliothèque ». Relecture adverse : ils apparaissaient comme presets.
// Ils ne sont plus dans `presets` (ni donc dans les boutons de la planche) ; ces propositions, sourcées, restent dans
// `presetsAValider` pour que l'utilisateur les juge (test.html les montre à part, sous ce titre).
const A_VALIDER = {
  'Chiffre 6': [H(TH(0, -28, 0, 0), PLI('index'), PLI('majeur'), PLI('annulaire'), Fd(0, 0, 0, -30)), '6 = pouce + auriculaire (Y) ; variantes : 5 + 1 à deux mains — à valider par l’utilisateur'],
  'Chiffre 7': [H(TH(0, -20, 0, 0), PLI('index'), PLI('majeur'), OUV, Fd(0, 0, 0, -10)), '7 = pouce + annulaire + auriculaire (asservissement forcé, posture réelle) ; variantes pouce + index, pouce + annulaire — à valider par l’utilisateur'],
  'Chiffre 8': [H(TH(0, -20, 0, 0), PLI('index'), Fd(0, 0, 0, 0), Fd(0, 0, 0, -8), Fd(0, 0, 0, -22)), '8 = pouce + majeur + annulaire + auriculaire ; variantes pouce + majeur, pouce + index + majeur — à valider par l’utilisateur'],
  'Chiffre 9': [H(TH(28, 40, 45, 20), SER.index, SER.majeur, SER.annulaire, SER.auriculaire), '9 : les sources divergent (quatre doigts pouce replié, index crochu…) — à poser par l’utilisateur'],
  'Chiffre 10': ['Main ouverte (5)', '10 : deux mains « 5 » ou un mouvement (poing qui s’ouvre) : placer deux mains sur la planche — à valider par l’utilisateur'],
};
// cibles du pouce (réglage par reach dans v2/tests/engine_presets.py) — documentation : quelle pulpe va où
const CIBLES = {
  'pulpe:index': F => pulpe(F, 'index'),
  'pulpe:majeur': F => pulpe(F, 'majeur'),
  'pulpe:annulaire': F => pulpe(F, 'annulaire'),
  'pulpes:bec': F => vsc(vadd(pulpe(F, 'index'), pulpe(F, 'majeur')), 0.5),
  'pulpes:D': F => vsc(vadd(vadd(pulpe(F, 'majeur'), pulpe(F, 'annulaire')), pulpe(F, 'auriculaire')), 1 / 3),
  // pouce couché EN TRAVERS des P2 (photo 2357) : milieu des P2 des deux doigts, côté dos de la P2 (face avant du poing)
  'P2:index+majeur': F => surP2(F, 'index', 'majeur'),
  'P2:majeur+annulaire': F => surP2(F, 'majeur', 'annulaire'),
  'P2:annulaire+auriculaire': F => surP2(F, 'annulaire', 'auriculaire'),
  // Clé (prise latérale) : pulpe du pouce contre le flanc RADIAL de la P2 de l'index courbé (+X local, vers le pouce,
  // à un rayon latéral de l'axe)
  'flanc:index_p2': F => { const s = SEGS.find(x => x.chaine === 'index' && x.g === 1), [p0, p1] = extremites(F, s);
    return vadd(vlerp(p0, p1, 0.55), vsc(qrot(F.Q[s.os], [1, 0, 0]), s.rLat)); },
  // T (variante LSF) : pulpe du pouce contre la face PALMAIRE de la P2 de l'index courbé
  'P2:index': F => { const s = SEGS.find(x => x.chaine === 'index' && x.g === 1), [p0, p1] = extremites(F, s);
    return vadd(vlerp(p0, p1, 0.5), vsc(qrot(F.Q[s.os], [0, 0, 1]), s.rPal)); }
};
function surP2(F, a, b) {
  const m = k => { const s = SEGS.find(x => x.chaine === k && x.g === 1), [p0, p1] = extremites(F, s);
    return vadd(vlerp(p0, p1, 0.5), vsc(qrot(F.Q[s.os], [0, 0, -1]), s.rDos + 0.9)); };
  return vsc(vadd(m(a), m(b)), 0.5);
}
// Dégagement final des presets. Le solveur juge les contacts sur les CAPSULES ; mesurée sur la PEAU (M1,
// tests/engine_presets.py), la pénétration les DÉPASSE dans deux familles de contacts : le pouce contre un doigt
// (R, pouce sur l'annulaire replié : 2,6 mm de capsules → 3,62 sur la peau ; Majeur pouce 2,93 → 3,14) et deux doigts
// À DEMI fléchis côte à côte (C : 2,59 → 3,23 ; Bec de canard rond 2,60 → 3,07). Entre deux doigts REPLIÉS c'est
// l'inverse (Cornes : 3,65 → 3,01 ; Lettre I : 3,26 → 2,95), et l'arc automatique, piloté par l'opposition du pouce,
// enfonce ce contact-là quand le pouce se place en dernier. Un plafond par famille, donc : 2,0 mm pour les deux
// premières, 3,0 pour les doigts repliés, 2,6 pour un bout posé sur la paume (le siège). Essai écarté : un plafond
// unique de 2,0 mm — le dégagement écartait l'annulaire replié vers l'auriculaire (L, Index (1) : 4,99 mm sur la peau,
// invisibles aux capsules) et ouvrait le majeur du poing (MCP 72°). D'où aussi la règle : un pas n'est gardé que s'il
// n'enfonce AUCUN autre contact au-delà de ce qu'il était ou de son plafond.
function plafondPaire(nom, p) {
  const ks = nom.split('/').map(x => x.split('_')[0]);
  if (ks.includes('pouce')) return 0.20;
  if (ks.includes('paume')) return 0.26;
  // deux doigts côte à côte : le défaut des capsules diminue avec la flexion (peau − capsules : C à MCP 35° +0,64 mm,
  // bec rond à 50° +0,47, Lettre E à 65° +0,12, repliés à 90° −0,2 à −0,6) — plafond 2,0 mm jusqu'à MCP 55°, 3,0 dès 75°
  // (correction : E, MCP 65°, finissait à 3,10 mm de peau sous l'ancien seuil sec « < 60° → 2,0, sinon 3,0 »)
  if (ks.length === 2 && ks.every(k => DOIGTS.includes(k))) return 0.20 + 0.10 * sstep(55, 75, Math.min(p[ks[0]].mcp, p[ks[1]].mcp));
  return 0.30;
}
function degager(pose) {
  let cur = constrain(pose);
  const exces = (d, p) => { let pire = null, e = 0;
    for (const nom in d.paires) { const x = d.paires[nom] - plafondPaire(nom, p); if (x > e) { e = x; pire = nom; } }
    return [pire, e]; };
  for (let it = 0; it < 150; it++) {
    const d = penetration(cur, true), [pire, e] = exces(d, cur); if (!pire) break;
    const ks = [...new Set(pire.split('/').map(x => x.split('_')[0]).filter(k => k === 'pouce' || DOIGTS.includes(k)))];
    let best = null, bv = d.paires[pire] - 1e-4;
    for (const k of ks) for (const c of (k === 'pouce' ? ['av', 'rap', 'mcp', 'ip'] : ['mcp', 'pip', 'dip', 'ab'])) for (const sg of [1, -1]) {
      const t = clone(cur); t[k][c] += sg; const tc = constrain(t);
      if (Math.abs(tc[k][c] - cur[k][c]) < 1e-6) continue;
      const dn = penetration(tc, true), v = dn.paires[pire] || 0;
      if (v >= bv) continue;
      let ok = true;
      for (const nom in dn.paires) if (nom !== pire && dn.paires[nom] > Math.max(d.paires[nom] || 0, plafondPaire(nom, tc)) + 0.002) { ok = false; break; }
      if (ok) { bv = v; best = tc; }
    }
    if (!best) break;
    cur = best;
  }
  return cur;
}
let PRESETS = {}, PRESETS_INFO = {}, PRESETS_A_VALIDER = {};
function construirePresets() {
  const t0 = performance.now(), J = A.json, base = {};
  const dessin = normalise(J.dessin);  // M1 l'a écrite dans le repère de liaison : écartement + éventail
  DOIGTS.forEach(k => dessin[k].ab += A.eventail[k]);
  for (const nom in PRESETS_INTENTION) base[nom] = nom === 'Dessin' ? dessin : PRESETS_INTENTION[nom];
  for (const nom in ALIAS) { const [v, note] = ALIAS[nom]; base[nom] = typeof v === 'string' ? clone(base[v]) : v; if (note) base[nom].note = note; }
  const aValider = {};
  for (const nom in A_VALIDER) { const [v, note] = A_VALIDER[nom]; aValider[nom] = typeof v === 'string' ? clone(base[v]) : v; aValider[nom].note = note; }
  const ouvert = normalise({pouce: {av: 20, rap: -10}});
  for (const nom in base) {
    const b = base[nom], note = b.note || null;
    const r = nom === 'Dessin' ? constrain(b) : degager(settle(ouvert, b));
    if (note) r.note = note;
    PRESETS[nom] = r;
    PRESETS_INFO[nom] = {intention: normalise(b), note, penetration: penetration(r)};
  }
  for (const nom in aValider) { const b = aValider[nom], r = degager(settle(ouvert, b)); r.note = b.note; PRESETS_A_VALIDER[nom] = r; }
  A.dureePresets = performance.now() - t0;
}

/* =====================================================================================================================
   15. API
   ===================================================================================================================== */
const API = {
  ready, init, charger, render, bounds, puppet, solve, settle, mirror, mirrorOrientation, constrain, penetration, normalise,
  depuisV1, versV1, diagnostic, reach, HL,
  get presets() { return PRESETS; },
  get presetsInfo() { return PRESETS_INFO; },
  get presetsAValider() { return PRESETS_A_VALIDER; },
  // pour les tests et les outils (rien de ceci n'est nécessaire à la planche)
  _interne: {fk: p => fk(normalise(p)), skin: (p, P, N) => skin(normalise(p), P, N), assets: () => A, segs: () => SEGS, paume: () => PAUME,
    plis: () => PLIS, RENDU, OS, PARTIES, pulpe: (p, ch) => pulpe(fk(normalise(p)), ch), horsEcran: () => horsEcran(), boiteMain,
    preferences, arcEffectif, pronationPouce, CIBLES, PRESETS_INTENTION, settle, projection}
};
window.AtelierHand = API;
// assets injectés par la page autonome (v2/build.py) : window.ATELIER_HAND_ASSETS = {glb: base64, json: objet}
if (window.ATELIER_HAND_ASSETS) init(window.ATELIER_HAND_ASSETS).catch(e => console.error('AtelierHand :', e));
})();
