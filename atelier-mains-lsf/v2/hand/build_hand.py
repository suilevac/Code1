#!/usr/bin/env python3
"""Atelier des mains LSF — v2, chantier M1 : construction de la main (assets).

    python3 build_hand.py            reconstruit tout (hand_v2.glb, hand_v2.json, checks/)
    python3 build_hand.py --jusqu N  s'arrête après l'étape N (les étapes suivantes relisent work/)
    python3 build_hand.py --depuis N relance à partir de l'étape N (relit work/ pour les précédentes)

Matière première (CC0) : maillage MakeHuman hm08 `base.obj`, squelette `default.mhskel` (centres articulaires =
centroïdes des cubes-repères `joint-*`), poids `default_weights.mhw`. Dessin de l'utilisateur : `references/paume.jpg`.
Repère du contrat (PLAN.md § M1 → M2) : doigts +Y, paume +Z, pouce +X, poignet (centre articulaire radio-carpien,
à mi-épaisseur) à l'origine, unités = cm. Vu de la caméra « Paume (face) » en +Z, le pouce est à droite — c'est le
dessin paume de l'utilisateur, superposable tel quel.

Étapes : 1 extraction · 2 squelette · 3 retaille · 4 surface (Catmull-Clark ×2) · 5 régions · 6 plis · 7 JSON · 8 GLB
· 9 contrôles (Cycles) · 10 test three.js. Chaque étape écrit ses chiffres dans JOURNAL.md (tableaux) et ses images
dans checks/.
"""
import os, sys, json, struct, math, time, argparse
import numpy as np
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))                # dépôt atelier-mains-lsf
SCRATCH = '/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad'
MH = os.environ.get('MH_DIR', SCRATCH + '/v2/recherche/modeles/makehuman')   # base.obj, default.mhskel, default_weights.mhw
WORK = os.path.join(HERE, 'work'); CHECKS = os.path.join(HERE, 'checks')
os.makedirs(WORK, exist_ok=True); os.makedirs(CHECKS, exist_ok=True)

# ----------------------------------------------------------------------------------------------------------------
# Constantes de conception (chaque valeur porte la mesure qui l'a fixée)
# ----------------------------------------------------------------------------------------------------------------
HL = 19.0            # cm, pli du poignet → bout du majeur : la main de l'utilisateur (anatomie.md § 1)
PAUME_L = 9.06       # cm, bord ulnaire → commissure du pouce, mesuré sur sa photo IMG_2354 (anatomie.md § 1)
CUT_D = -3.6         # cm le long de l'axe de l'avant-bras : sélectionne la boucle d'arêtes dont le plan moyen est à
                     # -2,71 cm du centre du poignet (mesuré : la boucle choisie par -3,4 et -3,8 est la même, d de
                     # -3,09 à -2,43) : « ~3 cm d'avant-bras », coupe rendue plane en projetant la boucle sur son plan moyen
# Dessin paume (992 × 1084 px) : axe du majeur x = 505 (chaîne CP du rig v1, vertical : 505, 505, 507, 507) ; pli du
# poignet dessiné (double trait) à y = 792 ; bout du majeur y = 18. Échelle anisotrope : en Y, HL = 190 mm sur 774 px ;
# en X, la paume (bord ulnaire x = 284 → apex de la 1re commissure x ≈ 690, mesurés sur le masque) = 90,6 mm.
DESSIN = dict(x0=505.0, y_pli=792.0, y_bout=18.0)
SY = HL / (DESSIN['y_pli'] - DESSIN['y_bout'])     # 0,02455 cm/px
# Chaînes corrigées du rig v1 (source/hand3d.json mesh.chain : MCP enfoncée DEEP8, IPD glissée PHAL8, pouce IP8) :
CHAINE_DESSIN = {   # px, [MCP, IPP, IPD, bout] ; pouce [CMC, MCP, IP, bout]
    'index':       [[603.0, 421.0], [630.0, 262.0], [647.05, 161.55], [657.0, 72.0]],
    'majeur':      [[505.0, 414.0], [505.0, 228.0], [507.0, 112.22], [507.0, 18.0]],
    'annulaire':   [[409.5, 420.5], [381.0, 263.0], [363.04, 157.29], [350.0, 66.0]],
    'auriculaire': [[340.0, 473.0], [256.0, 374.0], [206.97, 317.57], [158.0, 252.0]],
    'pouce':       [[652.0, 748.0], [718.0, 566.0], [790.0, 465.0], [872.0, 402.0]],
}
# Os de Buryanov & Kotiuk 2010 × 1,03 (main de 185 → 190 mm), mm ; P3 inclut le tissu mou du bout (anatomie.md § 2.1)
BURYANOV_MC = {'index': 70.1, 'majeur': 66.5, 'annulaire': 59.7, 'auriculaire': 55.3}   # mm, MC II–V × 1,03
BURYANOV = {'index': (41.0, 23.1, 16.3 + 3.8), 'majeur': (45.9, 27.1, 17.9 + 4.0), 'annulaire': (42.6, 26.5, 17.8 + 4.0),
            'auriculaire': (33.7, 18.6, 16.5 + 3.5), 'pouce': (47.6, 32.5, 22.4 + 5.7)}
# Largeurs (radio-ulnaire) et épaisseurs (dorso-palmaire) de conception, mm, tables 4.1–4.2 d'anatomie.md :
# stations [MCP, P1 milieu, IPP, P2 milieu, IPD, pulpe] ; le bout s'arrondit sur ≈ 8 mm (rayon 0,45 × largeur)
LARGEUR = {'index': (20.5, 20.0, 20.5, 18.0, 17.0, 16.5), 'majeur': (21.5, 21.0, 21.0, 18.5, 17.5, 17.0),
           'annulaire': (20.0, 19.5, 19.5, 17.0, 16.5, 16.0), 'auriculaire': (17.5, 17.0, 17.0, 15.0, 14.5, 14.0),
           'pouce': (23.5, 23.0, 22.0, 22.0, 22.0, 21.0)}      # pouce : [MCP, P1, P1 distal, IP, P2, pulpe]
EPAISSEUR = {'index': (17.5, 17.0, 17.5, 15.0, 14.5, 13.0), 'majeur': (18.5, 18.0, 18.0, 15.5, 15.0, 13.5),
             'annulaire': (17.0, 16.5, 17.0, 14.0, 14.0, 12.5), 'auriculaire': (15.0, 14.5, 15.0, 12.5, 12.0, 11.0),
             'pouce': (20.0, 19.0, 18.5, 17.0, 17.0, 16.0)}
PAUME_EP = {'poignet': 40.0, 'carpe': 36.0, 'mcp': 30.0}   # mm, anatomie.md § 1 et § 4.3 (poignet 40 ± 3, têtes MC 30 ± 3)
# Profondeur des centres articulaires depuis la peau du dos, en fraction de l'épaisseur locale (anatomie.md § 3 :
# centre dans la tête de l'os proximal, décalé vers la paume ; os de P1 1,4 × plus large que haut sous ≈ 2,5 mm de
# peau dorsale : 2,5 + 4,5 = 7 mm sur 17 = 0,41, tête décalée vers la paume → 0,45 ; tête MC : 5 mm de peau + tendons,
# tête de 13 mm → 11,5 / 30 = 0,38)
PROF = {'mcp': 0.40, 'ipp': 0.45, 'ipd': 0.45, 'cmc': 0.50, 'mcp_pouce': 0.45, 'ip_pouce': 0.45}
# Arc des têtes métacarpiennes (anatomie.md § 3) : Y relatif au majeur, et voûte transversale (flèche 5–8 mm, auriculaire
# le plus palmaire) : Z relatif au majeur
ARC_MCP_Y = {'index': -0.2, 'majeur': 0.0, 'annulaire': -0.4, 'auriculaire': -1.0}
ARC_MCP_Z = {'index': 0.10, 'majeur': 0.0, 'annulaire': 0.12, 'auriculaire': 0.40}
# Obliquité des axes de flexion des MCP (convergence vers le scaphoïde) : v1 `LEAN`, réglé sur le contact des P1 dans
# le poing (CLAUDE.md piste Z) ; > 0 = l'axe tourne autour de l'os de façon que le doigt fléchi dévie vers le majeur
LEAN = {'index': -6.5, 'majeur': 0.0, 'annulaire': 6.5, 'auriculaire': 12.0}
DOIGTS = ['index', 'majeur', 'annulaire', 'auriculaire']
# Bases des métacarpiens II–V (XY, cm) : rangée distale du carpe (MH : cubes hand-2 / hand-3 à y = 2,85 et 3,37 cm) ;
# écart de 1,2 cm entre bases (la base d'un métacarpien est plus étroite que sa tête : 21 mm d'écart aux têtes)
BASE_MC = {'index': (1.3, 2.9), 'majeur': (0.1, 3.1), 'annulaire': (-1.1, 3.0), 'auriculaire': (-2.3, 2.6)}
# Correspondance os MakeHuman → os du contrat
MH2OS = {'wrist.L': 'poignet', 'lowerarm01.L': 'poignet', 'lowerarm02.L': 'poignet',
         'finger1-1.L': 'mc1', 'finger1-2.L': 'pouce_p1', 'finger1-3.L': 'pouce_p2',
         'metacarpal1.L': 'mc2', 'metacarpal2.L': 'mc3', 'metacarpal3.L': 'mc4', 'metacarpal4.L': 'mc5'}
for _i, _d in enumerate(DOIGTS):
    for _j in (1, 2, 3): MH2OS['finger%d-%d.L' % (_i + 2, _j)] = '%s_p%d' % (_d, _j)
OS = ['poignet', 'mc1', 'pouce_p1', 'pouce_p2', 'mc2', 'index_p1', 'index_p2', 'index_p3', 'mc3', 'majeur_p1', 'majeur_p2',
      'majeur_p3', 'mc4', 'annulaire_p1', 'annulaire_p2', 'annulaire_p3', 'mc5', 'auriculaire_p1', 'auriculaire_p2',
      'auriculaire_p3']
PARENT = {'poignet': None, 'mc1': 'poignet', 'pouce_p1': 'mc1', 'pouce_p2': 'pouce_p1'}
for _i, _d in enumerate(DOIGTS):
    PARENT['mc%d' % (_i + 2)] = 'poignet'; PARENT[_d + '_p1'] = 'mc%d' % (_i + 2)
    PARENT[_d + '_p2'] = _d + '_p1'; PARENT[_d + '_p3'] = _d + '_p2'
CHAINES = {'pouce': ['mc1', 'pouce_p1', 'pouce_p2']}
for _i, _d in enumerate(DOIGTS): CHAINES[_d] = ['mc%d' % (_i + 2), _d + '_p1', _d + '_p2', _d + '_p3']
OSI = {b: i for i, b in enumerate(OS)}
REGION = {'peau': 0, 'plaque': 1, 'frange': 2, 'repli': 3, 'palmure': 4}

JOURNAL = []          # lignes ajoutées au journal par les étapes
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); JOURNAL.append(s)
def nz(v): v = np.asarray(v, float); return v / (np.linalg.norm(v) + 1e-12)
def px2cm(p, sx):
    """point du dessin paume (px) → (X, Y) cm du repère du contrat"""
    p = np.asarray(p, float); return np.array([(p[0] - DESSIN['x0']) * sx, (DESSIN['y_pli'] - p[1]) * SY])

# ----------------------------------------------------------------------------------------------------------------
# Lecture de MakeHuman
# ----------------------------------------------------------------------------------------------------------------
def lire_mh():
    V, F, G, cur = [], [], [], None
    for l in open(os.path.join(MH, 'base.obj')):
        if l.startswith('v '): V.append(list(map(float, l.split()[1:4])))
        elif l.startswith('g '): cur = l[2:].strip()
        elif l.startswith('f '): F.append([int(t.split('/')[0]) - 1 for t in l.split()[1:]]); G.append(cur)
    V = np.array(V) * 10.0                      # décimètres MakeHuman → cm
    body = [f for f, g in zip(F, G) if g == 'body']
    sk = json.load(open(os.path.join(MH, 'default.mhskel')))
    J = {k: V[v].mean(0) for k, v in sk['joints'].items()}     # centroïde du cube-repère = centre articulaire
    W = json.load(open(os.path.join(MH, 'default_weights.mhw')))['weights']
    return V, body, sk, J, W

def masque_paume():
    """masque de la silhouette du dessin paume (peau + trait), et apex des commissures"""
    from PIL import Image
    from scipy import ndimage
    im = np.array(Image.open(os.path.join(ROOT, 'references', 'paume.jpg')).convert('RGB')).astype(float)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]; L = 0.299 * r + 0.587 * g + 0.114 * b
    sat = (r - b) / 85.0
    m = (sat > 0.22) | (L < 127)
    m = ndimage.binary_fill_holes(m); m = ndimage.binary_opening(m, iterations=2)
    lab, n = ndimage.label(m); sizes = ndimage.sum(m, lab, range(1, n + 1)); m = lab == (1 + np.argmax(sizes))
    return m

# ----------------------------------------------------------------------------------------------------------------
# Étape 1 — extraction de la main gauche MakeHuman + ~3 cm d'avant-bras, coupe plane par boucle d'arêtes, repère
# ----------------------------------------------------------------------------------------------------------------
def etape1():
    log('\n## 1. Extraction')
    V, body, sk, J, Wmh = lire_mh()
    W = J['wrist.L____head']; M2 = J['finger2-1.L____head']; M3 = J['finger3-1.L____head']; M5 = J['finger5-1.L____head']
    FA = J['lowerarm02.L____head']
    uy = nz(M3 - W)                                   # +Y : poignet → MCP du majeur
    n = nz(np.cross(M2 - W, M5 - W)); n = nz(n - (n @ uy) * uy)
    if (J['finger1-2.L____head'] - W) @ n < 0: n = -n  # +Z vers la paume : la MCP du pouce est palmaire
    ux = np.cross(uy, n)                              # main gauche MH : le pouce tombe en -X ; miroir plus bas
    R = np.stack([ux, uy, n])
    ufa = nz(W - FA); d = (V - W) @ ufa                # abscisse le long de l'axe de l'avant-bras (0 au poignet)
    # boucle d'arêtes : faces à cheval sur le plan d = CUT_D, arêtes de ces faces entièrement du côté distal
    strad = [i for i, f in enumerate(body) if V[f][:, 0].mean() > 30 and d[f].min() < CUT_D < d[f].max()]
    loop = set()
    for i in strad:
        f = body[i]
        for j in range(4):
            a, b = f[j], f[(j + 1) % 4]
            if d[a] > CUT_D and d[b] > CUT_D: loop.add(tuple(sorted((a, b))))
    deg = defaultdict(int)
    for a, b in loop: deg[a] += 1; deg[b] += 1
    assert all(v == 2 for v in deg.values()), 'la boucle de coupe n’est pas une boucle simple'
    adj = defaultdict(list)
    for i, f in enumerate(body):
        for j in range(4): adj[tuple(sorted((f[j], f[(j + 1) % 4])))].append(i)
    tipc = J['finger3-3.L____tail']; vi = int(np.argmin(np.linalg.norm(V[:13380] - tipc, axis=1)))
    start = [i for i, f in enumerate(body) if vi in f][0]
    seen = {start}; st = [start]; sset = set(strad)
    while st:
        i = st.pop(); f = body[i]
        for j in range(4):
            e = tuple(sorted((f[j], f[(j + 1) % 4])))
            if e in loop: continue
            for nb in adj[e]:
                if nb not in seen and nb not in sset: seen.add(nb); st.append(nb)
    hf = sorted(seen); hv = sorted(set(v for i in hf for v in body[i]))
    remap = {v: i for i, v in enumerate(hv)}
    Fq = [[remap[v] for v in body[i]] for i in hf]
    lv = sorted(set(x for e in loop for x in e))
    dmean = float(d[lv].mean())
    Vc = V[hv].copy()
    # coupe PLANE : les sommets de la boucle glissent le long de l'axe de l'avant-bras jusqu'au plan moyen
    for v in lv: Vc[remap[v]] += (dmean - d[v]) * ufa
    log('- boucle de coupe : %d arêtes / %d sommets, tous de degré 2 ; plan moyen à %.2f cm du poignet (écart avant '
        'aplatissement %.2f..%.2f cm)' % (len(loop), len(lv), dmean, d[lv].min() - dmean, d[lv].max() - dmean))
    # repère du contrat : (x, y, z) = ((v − W)·R), puis miroir x → −x pour mettre le pouce en +X (voir en-tête)
    Vf = (Vc - W) @ R.T; Vf[:, 0] *= -1; Fq = [f[::-1] for f in Fq]
    # origine Z à mi-épaisseur du poignet (le cube-repère wrist de MH est à la peau du dos : peau du poignet à
    # z = 0,17..2,40 cm, mesuré) ; origine X au milieu de la largeur du poignet
    # Le cube-repère « wrist » de MH est à la peau du DOS du poignet (peau mesurée à z = 0,17..2,40 cm de lui) et
    # la ligne des cubes poignet → MCP n'est pas parallèle au plan médian de la paume (dos à +0,17 au poignet,
    # −1,5 aux têtes MC) : on redresse le repère sur le plan médian de la paume proprement dite (x ∈ [−3,5 ; 1,5],
    # hors éminence thénar) par une rotation autour de X, et on met l'origine à mi-épaisseur du poignet.
    def plan_median(Vq):
        ys = np.arange(-2.5, 9.6, 1.0); pts = []
        for y in ys:
            m = (np.abs(Vq[:, 1] - y) < 0.5) & (Vq[:, 0] > -3.5) & (Vq[:, 0] < 1.5)
            if m.sum() > 6: pts.append((y, 0.5 * (Vq[m, 2].min() + Vq[m, 2].max())))
        pts = np.array(pts); a, b = np.polyfit(pts[:, 0], pts[:, 1], 1); return a, b
    a, b = plan_median(Vf); th = math.atan(a)
    Rx = np.array([[1, 0, 0], [0, math.cos(th), -math.sin(th)], [0, math.sin(th), math.cos(th)]])
    Vf = Vf @ Rx.T                                   # rotation autour de X : le plan médian devient horizontal
    a2, b2 = plan_median(Vf)
    m0 = np.abs(Vf[:, 1]) < 0.25
    z0 = 0.5 * (Vf[m0, 2].min() + Vf[m0, 2].max()); x0 = 0.5 * (Vf[m0, 0].min() + Vf[m0, 0].max())
    Vf[:, 0] -= x0; Vf[:, 2] -= z0
    log('- redressement : plan médian de la paume incliné de %.1f° sur la ligne des cubes (z = %.3f·y + %.2f) → rotation '
        'autour de X ; résidu %.2f° ; recentrage à y = 0 : x0 = %.2f, z0 = %.2f cm (épaisseur MH du poignet %.2f cm, '
        'largeur %.2f cm)' % (math.degrees(th), a, b, math.degrees(math.atan(a2)), x0, z0, Vf[m0, 2].max() - Vf[m0, 2].min(), Vf[m0, 0].max() - Vf[m0, 0].min()))
    # bouchon du poignet : un n-gone (Catmull-Clark le subdivise en éventail de quads) orienté vers l'extérieur
    loopv = [remap[v] for v in lv]
    # ordonner la boucle en suivant les arêtes
    nb = defaultdict(list)
    for a, b in loop: nb[remap[a]].append(remap[b]); nb[remap[b]].append(remap[a])
    ring = [loopv[0]]; prev = None
    while len(ring) < len(loopv):
        cur = ring[-1]; nxt = [x for x in nb[cur] if x != prev and x != ring[0] or (x == ring[0] and len(ring) == len(loopv))]
        nxt = [x for x in nb[cur] if x != prev]; prev = cur; ring.append(nxt[0])
    ring = ring[:len(loopv)]
    c = Vf[ring].mean(0); nrm = sum(np.cross(Vf[ring[i]] - c, Vf[ring[(i + 1) % len(ring)]] - c) for i in range(len(ring)))
    if nrm @ np.array([0, -1, 0.]) < 0: ring = ring[::-1]       # normale du bouchon vers −Y (vers l'avant-bras)
    Fq.append(ring)
    # cubes-repères MH dans le repère (miroir compris)
    def tf(p): q = (p - W) @ R.T; q[0] = -q[0]; q = Rx @ q; q[0] -= x0; q[2] -= z0; return q
    jts = {k: tf(J[k]) for k in J if k.endswith('.L____head') or k.endswith('.L____tail')}
    # axes de flexion MH : normale du plan de rotation (3 repères) de chaque os
    axes_mh = {}
    for b, info in sk['bones'].items():
        if b not in MH2OS or b.startswith('lowerarm') or b == 'wrist.L': continue
        p = [tf(J[q]) for q in sk['planes'][info['rotation_plane']]]
        nrm = nz(np.cross(p[1] - p[0], p[2] - p[0]))
        axes_mh[b] = nrm.tolist()
    # poids MH : report sur les 20 os du contrat
    hset = set(hv); Wm = np.zeros((len(hv), len(OS)))
    for bone, lst in Wmh.items():
        if bone not in MH2OS:
            if any(vi in hset for vi, _ in lst): log('  (poids ignorés de %s)' % bone)
            continue
        col = OSI[MH2OS[bone]]
        for vi, val in lst:
            if vi in hset: Wm[remap[vi], col] += val
    Wm /= Wm.sum(1, keepdims=True)
    np.savez(os.path.join(WORK, 's1_extraction.npz'), V=Vf, F=np.array(Fq, dtype=object), ring=np.array(ring),
             W=Wm, orig=np.array(hv), jts=json.dumps({k: v.tolist() for k, v in jts.items()}), axes_mh=json.dumps(axes_mh))
    log('- main extraite : %d sommets, %d faces (%d quads + 1 bouchon de %d côtés) ; boîte x %.1f..%.1f, y %.1f..%.1f, '
        'z %.1f..%.1f cm' % (len(Vf), len(Fq), len(Fq) - 1, len(ring), *np.array([Vf.min(0), Vf.max(0)]).T.ravel()))
    log('- longueur MH poignet → bout du majeur : %.2f cm (cible %.1f)' % (jts['finger3-3.L____tail'][1], HL))
    # image de contrôle
    from rendu import render, view, sheet
    segs = []
    for b, info in sk['bones'].items():
        if b in MH2OS and not b.startswith('lowerarm'):
            segs.append((jts[info['head']], jts[info['tail']], (220, 30, 30)))
    ims, labs = [], []
    for nm in ['paume', 'dos', 'profil_radial', 'dessus']:
        im, _ = render(Vf, Fq, view(nm), size=520, segs=segs, wire=True); ims.append(im); labs.append('étape 1 : MH brut, ' + nm)
    sheet(ims, labs).save(os.path.join(CHECKS, 'e1_extraction.png'))
    return Vf, Fq, Wm, jts, axes_mh

def charger(etape):
    d = np.load(os.path.join(WORK, 's%d_%s.npz' % (etape, {1: 'extraction', 3: 'retaille', 4: 'surface'}[etape])), allow_pickle=True)
    return d

# ----------------------------------------------------------------------------------------------------------------
# Étape 2 — squelette cible : 20 os, centres corrigés (anatomie.md § 3), axes locaux
# ----------------------------------------------------------------------------------------------------------------
def etape2(V, F, Wm, jts, axes_mh):
    log('\n## 2. Squelette')
    mask = masque_paume()
    # apex de la 1re commissure (pouce–index) : point le plus bas du bord supérieur du masque entre x = 600 et 760
    ytop = np.array([np.where(mask[:, x])[0].min() if mask[:, x].any() else 0 for x in range(mask.shape[1])])
    xa = 600 + int(np.argmax(ytop[600:760])); ya = int(ytop[xa])
    y_ref = 520; xs = np.where(mask[y_ref])[0]; x_uln = int(xs.min())
    sx = PAUME_L / (xa - x_uln)
    log('- dessin : 1re commissure à (%d, %d) px, bord ulnaire x = %d à y = %d → échelle X %.5f cm/px (paume %.1f mm) ; '
        'échelle Y %.5f cm/px (HL %.0f mm sur %d px)' % (xa, ya, x_uln, y_ref, sx, PAUME_L * 10, SY, HL * 10, DESSIN['y_pli'] - DESSIN['y_bout']))
    # --- longueurs cibles : total MCP → bout du dessin (ses proportions) réparti selon Buryanov (anatomie) ---
    tab = []; L = {}
    for k in DOIGTS + ['pouce']:
        ch = [px2cm(p, sx) for p in CHAINE_DESSIN[k]]
        segd = [np.linalg.norm(ch[i + 1] - ch[i]) for i in range(3)]
        bur = np.array(BURYANOV[k]) / 10.0
        if k == 'pouce':
            L[k] = bur.tolist()          # pouce : Buryanov (son pouce photographié fait 72 mm de la commissure au bout ; le dessin 53)
        else:
            tot = sum(segd); L[k] = (bur / bur.sum() * tot).tolist()
        tab.append((k, segd, bur.tolist(), L[k]))
    # auriculaire : son bout atteint le pli IPD de l'annulaire (anatomie.md § 9, photo) : avec la MCP sur l'arc
    # anatomique (−10 mm sous celle du majeur) la longueur voulue vaut Y(IPD annulaire) − Y(MCP auriculaire)
    mcp = {k: px2cm(CHAINE_DESSIN[k][0], sx) for k in DOIGTS}
    mcp['auriculaire'][1] = mcp['majeur'][1] + ARC_MCP_Y['auriculaire']
    y_ipd_ann = mcp['annulaire'][1] + L['annulaire'][0] + L['annulaire'][1]
    tot5 = y_ipd_ann - mcp['auriculaire'][1]; bur5 = np.array(BURYANOV['auriculaire']) / 10
    L['auriculaire'] = (bur5 / bur5.sum() * tot5).tolist()
    tab[3] = ('auriculaire', tab[3][1], tab[3][2], L['auriculaire'])
    log('- longueurs d’os (cm) : dessin (chaîne v1) | Buryanov × 1,03 | retenu')
    log('  | doigt | P1 dessin | P2 | P3+pulpe | P1 Bur. | P2 | P3+p | P1 retenu | P2 | P3+p | total retenu |')
    log('  |---|---|---|---|---|---|---|---|---|---|---|')
    for k, sd, b, r in tab:
        log('  | %s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f |' % ((k,) + tuple(sd) + tuple(b) + tuple(r) + (sum(r),)))
    log('  (auriculaire : total = Y du pli IPD de l’annulaire (%.2f) − Y de sa MCP (%.2f) = %.2f, Buryanov %.2f : son '
        'auriculaire est long ; index %.2f ≈ annulaire %.2f : les siens)' % (y_ipd_ann, mcp['auriculaire'][1], tot5, bur5.sum(), sum(L['index']), sum(L['annulaire'])))
    # --- épaisseur locale MH autour de chaque articulation → z des centres (fraction PROF depuis le dos) ---
    def peau_z(c, r=0.45):
        m = np.linalg.norm(V[:, :2] - c[:2], axis=1) < r
        return V[m, 2].min(), V[m, 2].max()
    centres = {}; axes = {}
    centres['poignet'] = np.zeros(3)
    for k in DOIGTS:
        mh = ['finger%d-%d.L____head' % (DOIGTS.index(k) + 2, j) for j in (1, 2, 3)]
        zd, zp = peau_z(jts[mh[0]]); zmcp = zd + PROF['mcp'] * (zp - zd) + ARC_MCP_Z[k]
        c0 = np.array([mcp[k][0], mcp[k][1] + (ARC_MCP_Y[k] if k != 'auriculaire' else 0) * 0 , zmcp])
        # (l'arc en Y des quatre MCP est déjà celui du dessin, sauf l'auriculaire, remis sur l'arc plus haut)
        zd1, zp1 = peau_z(jts[mh[1]]); zd2, zp2 = peau_z(jts[mh[2]])
        # les phalanges sont dans le prolongement de +Y ; le centre IPP/IPD à PROF de l'épaisseur locale MH,
        # ramené sur l'axe de la P1 (pente dorsale douce : z décroît de la MCP au bout comme dans le maillage MH)
        z1 = zd1 + PROF['ipp'] * (zp1 - zd1); z2 = zd2 + PROF['ipd'] * (zp2 - zd2)
        # ces z MH sont ceux d'une main aux doigts légèrement fléchis (bouts à z ≈ +1,3) : on garde la pente mais on
        # la ramène à une main à plat (IPP, IPD, bout alignés sur une droite partant de la MCP, pente ≤ 3°)
        pente = min(0.05, (z2 - zmcp) / (L[k][0] + L[k][1]))
        c1 = c0 + np.array([0, L[k][0], pente * L[k][0]]); c2 = c1 + np.array([0, L[k][1], pente * L[k][1]])
        c3 = c2 + np.array([0, L[k][2], pente * L[k][2]])
        i = DOIGTS.index(k) + 2
        centres[k + '_p1'] = c0; centres[k + '_p2'] = c1; centres[k + '_p3'] = c2; centres[k + '_bout'] = c3
        # base du métacarpien (articulation carpo-métacarpienne) : rangée distale du carpe, ≈ 2,5–3 cm du poignet
        # (MH : cubes « hand-2/3 » à y = 2,85 et 3,37 cm), écartement réduit (base du métacarpien plus étroite que la tête)
        centres['mc%d' % i] = np.array([BASE_MC[k][0], BASE_MC[k][1], c0[2] + 0.15])
        log('  %s : MCP (%.2f, %.2f, %.2f) [MH z %.2f, peau %.2f..%.2f] ; IPP z %.2f, IPD z %.2f, bout z %.2f' %
            (k, *c0, jts[mh[0]][2], zd, zp, c1[2], c2[2], c3[2]))
    # --- pouce : CMC à la base de l'éminence (trapèze), directions MH gardées, longueurs Buryanov ---
    cmc_xy = px2cm(CHAINE_DESSIN['pouce'][0], sx)
    zd, zp = peau_z(jts['finger1-1.L____head'], 0.6); zc = zd + PROF['cmc'] * (zp - zd)
    c0 = np.array([cmc_xy[0], cmc_xy[1], zc])
    u_mc = nz(jts['finger1-1.L____tail'] - jts['finger1-1.L____head'])
    u_p1 = nz(jts['finger1-2.L____tail'] - jts['finger1-2.L____head'])
    u_p2 = nz(jts['finger1-3.L____tail'] - jts['finger1-3.L____head'])
    c1 = c0 + u_mc * L['pouce'][0]; c2 = c1 + u_p1 * L['pouce'][1]; c3 = c2 + u_p2 * L['pouce'][2]
    centres['mc1'] = c0; centres['pouce_p1'] = c1; centres['pouce_p2'] = c2; centres['pouce_bout'] = c3
    ang = lambda u: math.degrees(math.atan2(u[0], u[1]))
    u_mc2 = nz(centres['index_p1'] - centres['mc2'])
    log('  pouce : CMC (%.2f, %.2f, %.2f) ; MC I à %.0f° de +Y dans le plan XY (MC II à %.0f° → %.0f° entre les deux ; '
        'anatomie.md : ≈ 30° au repos), élévation palmaire %.0f° ; P1 à %.0f°, P2 à %.0f° ; bout (%.2f, %.2f, %.2f)' %
        (*c0, ang(u_mc), ang(u_mc2), ang(u_mc) - ang(u_mc2), math.degrees(math.asin(u_mc[2])), ang(u_p1), ang(u_p2), *c3))
    # --- axes locaux : +Y le long de l'os, +Z vers la paume, +X = Y × Z (axe de flexion, vers le pouce) ---
    def frame(y, zref):
        y = nz(y); z = nz(zref - (zref @ y) * y); x = np.cross(y, z); return np.stack([x, y, z], 1)   # colonnes
    axes['poignet'] = np.eye(3)
    for k in DOIGTS:
        i = DOIGTS.index(k) + 2
        axes['mc%d' % i] = frame(centres[k + '_p1'] - centres['mc%d' % i], np.array([0, 0, 1.]))
        for j, nxt in ((1, k + '_p2'), (2, k + '_p3'), (3, k + '_bout')):
            b = '%s_p%d' % (k, j); nxtc = centres[nxt] if nxt in centres else centres[k + '_bout']
            fr = frame(nxtc - centres[b], np.array([0, 0, 1.]))
            if j == 1:   # obliquité de l'axe de flexion de la MCP : rotation de LEAN autour de l'os
                a = math.radians(LEAN[k]); c, s = math.cos(a), math.sin(a)
                Ry = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])      # rotation autour de Y local
                fr = fr @ Ry
            axes[b] = fr
    # pouce : +Z = côté pulpe = axe MH de flexion × direction (signe : vers (−X, +Z), le pouce est proné ≈ 60°)
    for b, mhb, nxt in (('mc1', 'finger1-1.L', 'pouce_p1'), ('pouce_p1', 'finger1-2.L', 'pouce_p2'), ('pouce_p2', 'finger1-3.L', 'pouce_bout')):
        y = nz(centres[nxt] - centres[b]); n = np.array(axes_mh[mhb]); n = nz(n - (n @ y) * y)
        z = np.cross(n, y)
        if z @ np.array([-1, 0, 1.]) < 0: z = -z
        axes[b] = frame(y, z)
    # table récapitulative
    log('- centres (cm) et longueurs centre → centre :')
    log('  | os | parent | centre | longueur (cm) | cible Buryanov×1,03 |')
    log('  |---|---|---|---|---|')
    long = {}
    for b in OS:
        if b == 'poignet':
            long[b] = float(np.linalg.norm(centres['mc3'] - centres['poignet']))
            log('  | poignet | — | (0, 0, 0) | %.2f (→ base du mc3) | — |' % long[b]); continue
        k = [kk for kk, ch in CHAINES.items() if b in ch][0]; ch = CHAINES[k]; j = ch.index(b)
        nxt = centres[ch[j + 1]] if j + 1 < len(ch) else centres[k + '_bout']
        long[b] = float(np.linalg.norm(nxt - centres[b]))
        cible = '(MC II–V : %.2f, de la base)' % (BURYANOV_MC[k] / 10) if (b.startswith('mc') and b != 'mc1') else '%.2f' % (BURYANOV[k][j - (0 if k == 'pouce' else 1)] / 10)
        log('  | %s | %s | (%.2f, %.2f, %.2f) | %.2f | %s |' % (b, PARENT[b] or '—', *centres[b], long[b], cible))
    sq = {'centres': {b: centres[b].tolist() for b in centres}, 'axes': {b: axes[b].tolist() for b in axes}, 'longueurs': long,
          'sx': sx, 'commissure1': [xa, ya], 'x_ulnaire': x_uln, 'L': L, 'mcp_xy': {k: mcp[k].tolist() for k in mcp}}
    json.dump(sq, open(os.path.join(WORK, 's2_squelette.json'), 'w'), indent=1)
    # vérification de l'obliquité : fléchir chaque P1 de 90° autour de son X local et regarder où va le bout
    log('- contrôle LEAN : bout du doigt après 90° de flexion de la MCP (X du bout, + vers le pouce) :')
    for k in DOIGTS:
        b = k + '_p1'; fr = axes[b]; x = fr[:, 0]; c = centres[b]; tip = centres[k + '_bout']
        a = math.radians(90); K = np.array([[0, -x[2], x[1]], [x[2], 0, -x[0]], [-x[1], x[0], 0]])
        Rm = np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K
        t2 = c + Rm @ (tip - c)
        log('  %s : bout (%.2f, %.2f, %.2f) → (%.2f, %.2f, %.2f) : déport latéral %+.2f cm' % (k, *tip, *t2, t2[0] - tip[0]))
    # image : squelette cible sur la main MH brute (face) et sur le dessin
    from rendu import render, view, sheet, overlay_dessin
    segs = [(centres['poignet'], centres['mc%d' % i], (230, 40, 40)) for i in range(1, 6)]
    for b in OS[1:]:
        k = [kk for kk, ch in CHAINES.items() if b in ch][0]; ch = CHAINES[k]; j = ch.index(b)
        nxt = centres[ch[j + 1]] if j + 1 < len(ch) else centres[k + '_bout']
        segs.append((centres[b], nxt, (230, 40, 40)))
    pts = [(centres[b], (40, 40, 230)) for b in OS]
    im1, _ = render(V, F, view('paume'), size=560, segs=segs, points=pts)
    im2 = overlay_dessin(mask, sx, segs, pts, size=560)
    sheet([im1, im2], ['étape 2 : squelette cible sur la main MH brute (paume)', 'squelette cible sur le dessin (échelle anisotrope)']).save(os.path.join(CHECKS, 'e2_squelette.png'))
    return sq

# ----------------------------------------------------------------------------------------------------------------
def ecrire_journal(titre):
    p = os.path.join(HERE, 'JOURNAL.md')
    with open(p, 'a') as f: f.write('\n'.join(JOURNAL) + '\n')
    JOURNAL.clear()

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--jusqu', type=int, default=99); ap.add_argument('--depuis', type=int, default=1)
    args = ap.parse_args()
    sys.path.insert(0, HERE)
    t0 = time.time()
    if args.depuis <= 1:
        V, F, Wm, jts, axes_mh = etape1()
    else:
        d = charger(1); V = d['V']; F = [list(map(int, f)) for f in d['F']]; Wm = d['W']
        jts = {k: np.array(v) for k, v in json.loads(str(d['jts'])).items()}; axes_mh = json.loads(str(d['axes_mh']))
    if args.jusqu >= 2 and args.depuis <= 2: sq = etape2(V, F, Wm, jts, axes_mh)
    else: sq = json.load(open(os.path.join(WORK, 's2_squelette.json')))
    if args.jusqu >= 3:
        import etapes_suite
        etapes_suite.lancer(args, V, F, Wm, jts, axes_mh, sq, globals())
    log('\n(temps total %.0f s)' % (time.time() - t0))
    ecrire_journal('')
