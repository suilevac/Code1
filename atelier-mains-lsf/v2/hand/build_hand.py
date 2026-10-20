#!/usr/bin/env python3
"""Atelier des mains LSF — palier v2, chantier M1 : LA MAIN (assets).

    python3 build_hand.py              reconstruit tout : hand_v2.glb, hand_v2.json, checks/, tableaux du JOURNAL.md
    python3 build_hand.py --depuis N   relance à partir de l'étape N (relit work/ pour les précédentes)
    python3 build_hand.py --jusqu N    s'arrête après l'étape N
    python3 build_hand.py --sans-cycles  saute les rendus Cycles (les plus longs) et le test three.js

Matière première (CC0, MakeHuman hm08, dossier MH_DIR) : maillage `base.obj`, squelette `default.mhskel` (centres
articulaires = centroïdes des cubes-repères `joint-*` du maillage), poids `default_weights.mhw`.
Dessin de l'utilisateur : `references/paume.jpg` (silhouette, plis) ; chaînes corrigées du rig v1 (`source/hand3d.json`,
`mesh.chain`) ; tables d'anatomie.md (os de Buryanov, largeurs/épaisseurs 4.1–4.2, ongles 7.1) et de mobilite.md § 5.

Repère du contrat (PLAN.md § M1 → M2) : doigts +Y, paume +Z, pouce +X, centre du poignet à l'origine, centimètres.
ATTENTION : avec ces trois axes (repère direct), la main est anatomiquement une main DROITE vue paume vers la caméra
+Z — c'est exactement le dessin `paume.jpg` (pouce à droite, paume vers nous). On respecte les axes à la lettre
(ce sont eux que le moteur consomme) ; le maillage MakeHuman gauche est donc passé au miroir x → −x, et l'autre main
s'obtient par le miroir x → −x à l'exécution, comme en v1. Le JSON le note (`cote_anatomique`).

Étapes : 1 extraction · 2 squelette · 3 retaille · 4 surface (Catmull-Clark ×2) · 5 poids · 6 régions (ongles…)
· 7 plis · 8 butées et poses → JSON · 9 export GLB (bpy) · 10 contrôles (Cycles, three.js). Chaque étape écrit ses
chiffres (tableaux) dans la section automatique de JOURNAL.md et ses images dans checks/.
"""
import os, sys, json, math, time, argparse
import numpy as np
from collections import defaultdict

ICI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, ICI)
from noyau import *                                         # noqa
RACINE = os.path.abspath(os.path.join(ICI, '..', '..'))     # dépôt atelier-mains-lsf
SCRATCH = '/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad'
MH = os.environ.get('MH_DIR', SCRATCH + '/v2/recherche/modeles/makehuman')
WORK = os.path.join(ICI, 'work'); CHECKS = os.path.join(ICI, 'checks')
os.makedirs(WORK, exist_ok=True); os.makedirs(CHECKS, exist_ok=True)

# =================================================================================================================
# Constantes (chaque valeur porte la mesure ou la source qui l'a fixée)
# =================================================================================================================
HL = 19.0          # cm, pli du poignet → bout du majeur : la main de l'utilisateur (anatomie.md § 1, photo IMG_2354)
PAUME_L = 9.06     # cm, bord ulnaire → commissure du pouce, mesuré sur sa photo IMG_2354 (anatomie.md § 1, PLAN.md)
CUT_D = -3.6       # cm le long de l'axe de l'avant-bras MH : sélectionne la boucle d'arêtes MH dont le plan moyen est
                   # à −2,7 cm du centre du poignet (−3,4 et −3,8 donnent la même boucle) : « ~3 cm d'avant-bras »
DOIGTS = ['index', 'majeur', 'annulaire', 'auriculaire']
OS = ['poignet', 'mc1', 'pouce_p1', 'pouce_p2', 'mc2', 'index_p1', 'index_p2', 'index_p3', 'mc3', 'majeur_p1',
      'majeur_p2', 'majeur_p3', 'mc4', 'annulaire_p1', 'annulaire_p2', 'annulaire_p3', 'mc5', 'auriculaire_p1',
      'auriculaire_p2', 'auriculaire_p3']
OSI = {b: i for i, b in enumerate(OS)}
PARENT = {'poignet': None, 'mc1': 'poignet', 'pouce_p1': 'mc1', 'pouce_p2': 'pouce_p1'}
CHAINES = {'pouce': ['mc1', 'pouce_p1', 'pouce_p2']}
for _i, _d in enumerate(DOIGTS):
    _m = 'mc%d' % (_i + 2); PARENT[_m] = 'poignet'; PARENT[_d + '_p1'] = _m
    PARENT[_d + '_p2'] = _d + '_p1'; PARENT[_d + '_p3'] = _d + '_p2'
    CHAINES[_d] = [_m, _d + '_p1', _d + '_p2', _d + '_p3']
CHAINE_DE = {b: k for k, ch in CHAINES.items() for b in ch}
# Os MakeHuman (main gauche, suffixe .L) → os du contrat. Les deux os d'avant-bras MH (torsion) vont au « poignet » :
# le poignet du contrat est la racine (avant-bras + carpe), voir l'étape 5 pour la séparation avant-bras / main.
MH2OS = {'wrist.L': 'poignet', 'lowerarm01.L': 'poignet', 'lowerarm02.L': 'poignet',
         'finger1-1.L': 'mc1', 'finger1-2.L': 'pouce_p1', 'finger1-3.L': 'pouce_p2',
         'metacarpal1.L': 'mc2', 'metacarpal2.L': 'mc3', 'metacarpal3.L': 'mc4', 'metacarpal4.L': 'mc5'}
for _i, _d in enumerate(DOIGTS):
    for _j in (1, 2, 3): MH2OS['finger%d-%d.L' % (_i + 2, _j)] = '%s_p%d' % (_d, _j)
OS2MH = {v: k for k, v in MH2OS.items() if not k.startswith('lowerarm')}
REGION = {'peau': 0, 'plaque': 1, 'frange': 2, 'repli': 3, 'palmure': 4}

# =================================================================================================================
# Journal : section automatique de JOURNAL.md (entre deux marqueurs), réécrite à chaque reconstruction
# =================================================================================================================
LIGNES = {}
_etape = ['0']
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LIGNES.setdefault(_etape[0], []).append(s)
def ecrire_journal():
    p = os.path.join(ICI, 'JOURNAL.md')
    txt = open(p).read() if os.path.exists(p) else '# Chantier M1 — journal\n'
    A, B = '<!-- MESURES AUTOMATIQUES : DÉBUT (build_hand.py réécrit cette section) -->', '<!-- MESURES AUTOMATIQUES : FIN -->'
    # on garde les mesures des étapes non relancées
    anc = {}
    if A in txt and B in txt:
        corps = txt.split(A)[1].split(B)[0]
        cur = None
        for l in corps.split('\n'):
            if l.startswith('<!-- étape '): cur = l[len('<!-- étape '):].split(' ')[0]; anc[cur] = []; continue
            if cur is not None: anc[cur].append(l)
    for k, v in LIGNES.items(): anc[k] = v
    sec = A + '\n' + '\n'.join('<!-- étape %s -->\n' % k + '\n'.join(l for l in anc[k] if l is not None).strip('\n') + '\n'
                                 for k in sorted(anc, key=lambda s: int(s) if s.isdigit() else 99)) + B
    if A in txt and B in txt: txt = txt.split(A)[0] + sec + txt.split(B)[1]
    else: txt = txt.rstrip('\n') + '\n\n' + sec + '\n'
    open(p, 'w').write(txt)

def sauver(nom, **kw):
    np.savez_compressed(os.path.join(WORK, nom + '.npz'), **{k: (np.array(v, dtype=object) if isinstance(v, list) else v) for k, v in kw.items()})
def charger(nom):
    d = np.load(os.path.join(WORK, nom + '.npz'), allow_pickle=True)
    return {k: d[k] for k in d.files}
def faces_de(a): return [list(map(int, f)) for f in a]

# =================================================================================================================
# Étape 1 — extraction de la main gauche MakeHuman + ~3 cm d'avant-bras : coupe plane par boucle d'arêtes, repère
# =================================================================================================================
def lire_mh():
    V, F, G, cur = [], [], [], None
    for l in open(os.path.join(MH, 'base.obj')):
        if l.startswith('v '): V.append(list(map(float, l.split()[1:4])))
        elif l.startswith('g '): cur = l[2:].strip()
        elif l.startswith('f '): F.append([int(t.split('/')[0]) - 1 for t in l.split()[1:]]); G.append(cur)
    V = np.array(V) * 10.0                      # décimètres MakeHuman → cm
    body = [f for f, g in zip(F, G) if g == 'body']
    sk = json.load(open(os.path.join(MH, 'default.mhskel')))
    J = {k: V[v].mean(0) for k, v in sk['joints'].items()}     # centroïde du cube-repère = centre articulaire MH
    W = json.load(open(os.path.join(MH, 'default_weights.mhw')))['weights']
    return V, body, sk, J, W

def etape1():
    _etape[0] = '1'; log('### 1. Extraction (MakeHuman hm08, CC0)')
    from raster import Vue, vues, planche
    V, body, sk, J, Wmh = lire_mh()
    W0 = J['wrist.L____head']; FA = J['lowerarm02.L____head']
    ufa = nz(W0 - FA); d = (V - W0) @ ufa                     # abscisse le long de l'avant-bras (0 au poignet)
    # --- boucle de coupe : arêtes des faces à cheval sur d = CUT_D, entièrement du côté de la main ---
    strad = [i for i, f in enumerate(body) if V[f][:, 0].mean() > 30 and d[f].min() < CUT_D < d[f].max()]
    loop = set()
    for i in strad:
        f = body[i]
        for j in range(len(f)):
            a, b = f[j], f[(j + 1) % len(f)]
            if d[a] > CUT_D and d[b] > CUT_D: loop.add(tuple(sorted((a, b))))
    deg = defaultdict(int)
    for a, b in loop: deg[a] += 1; deg[b] += 1
    assert all(v == 2 for v in deg.values()), 'la boucle de coupe n’est pas une boucle simple'
    E = aretes(body)
    tip = J['finger3-3.L____tail']; vi = int(np.argmin(np.linalg.norm(V[:13380] - tip, axis=1)))
    start = [i for i, f in enumerate(body) if vi in f][0]
    seen = {start}; st = [start]; sset = set(strad)
    while st:                                                  # remplissage depuis le bout du majeur sans franchir la boucle
        i = st.pop(); f = body[i]
        for j in range(len(f)):
            e = tuple(sorted((f[j], f[(j + 1) % len(f)])))
            if e in loop: continue
            for nb in E[e]:
                if nb not in seen and nb not in sset: seen.add(nb); st.append(nb)
    hf = sorted(seen); hv = sorted(set(v for i in hf for v in body[i]))
    remap = {v: i for i, v in enumerate(hv)}
    Fq = [[remap[v] for v in body[i]] for i in hf]
    lv = sorted(set(x for e in loop for x in e)); dmean = float(d[lv].mean())
    Vc = V[hv].copy()
    for v in lv: Vc[remap[v]] += (dmean - d[v]) * ufa         # coupe PLANE : la boucle glisse jusqu'à son plan moyen
    log('- boucle de coupe : %d arêtes, %d sommets tous de degré 2 ; plan moyen à %.2f cm du centre du poignet le long '
        'de l’avant-bras (écart avant aplatissement %.2f..%.2f cm)' % (len(loop), len(lv), dmean, d[lv].min() - dmean, d[lv].max() - dmean))
    # --- repère approché : Y poignet → tête du 3e métacarpien, Z normale au plan (MCP II, MCP V, poignet) ---
    M2 = J['finger2-1.L____head']; M3 = J['finger3-1.L____head']; M5 = J['finger5-1.L____head']
    uy = nz(M3 - W0); n = nz(np.cross(M2 - W0, M5 - W0)); n = nz(n - (n @ uy) * uy)
    if (J['finger1-2.L____head'] - W0) @ n < 0: n = -n         # +Z vers la paume : la MCP du pouce est palmaire
    R0 = np.stack([np.cross(uy, n), uy, n])
    def vers_contrat(P, Rx=np.eye(3), o=np.zeros(3)):
        q = (np.asarray(P) - W0) @ R0.T; q = q * np.array([-1, 1, 1])  # miroir x → −x : pouce en +X (voir l'en-tête)
        return q @ Rx.T - o
    Vf = vers_contrat(Vc); Fq = [f[::-1] for f in Fq]          # le miroir retourne l'orientation des faces
    # --- redressement sur le plan médian de la PAUME (le cube « wrist » MH est sur la peau du dos du poignet, la
    # ligne des cubes n'est donc pas dans le plan de la paume) : tangage (autour de X), roulis (autour de Y) et lacet
    # (autour de Z), trois passes ---
    def mi_epaisseur(P, ys, xs=(-2.5, 1.5), lar=0.3):
        out = []
        for y in ys:
            m = (np.abs(P[:, 1] - y) < lar) & (P[:, 0] > xs[0]) & (P[:, 0] < xs[1])
            if m.sum() > 6: out.append((y, 0.5 * (P[m, 2].min() + P[m, 2].max())))
        return np.array(out)
    T0, _ = triangles(Fq); Pe, _, _ = echantillons(Vf, T0, 300000)
    Rx = np.eye(3); o = np.zeros(3)
    for it in range(3):
        P = Pe @ Rx.T - o
        a, b = np.polyfit(*mi_epaisseur(P, np.arange(0.5, 8.6, 0.5)).T, 1)        # z = a·y + b (tangage)
        Rx = rot_axe([1, 0, 0], -math.atan(a)) @ Rx
        P = Pe @ Rx.T - o
        cols = []
        for x in np.arange(-3.0, 2.01, 0.5):                                       # z = c·x (roulis), paume centrale
            m = (np.abs(P[:, 0] - x) < 0.2) & (P[:, 1] > 4) & (P[:, 1] < 8)
            if m.sum() > 6: cols.append((x, 0.5 * (P[m, 2].min() + P[m, 2].max())))
        c, _ = np.polyfit(*np.array(cols).T, 1); Rx = rot_axe([0, 1, 0], math.atan(c)) @ Rx
        m3 = vers_contrat(M3, Rx); Rx = rot_axe([0, 0, 1], math.atan2(m3[0], m3[1])) @ Rx   # lacet : MCP III sur +Y
        P = Pe @ Rx.T
        m0 = np.abs(P[:, 1]) < 0.25
        o = np.array([0.5 * (P[m0, 0].min() + P[m0, 0].max()), 0.0, 0.5 * (P[m0, 2].min() + P[m0, 2].max())])
    P = Pe @ Rx.T - o
    a2, _ = np.polyfit(*mi_epaisseur(P, np.arange(0.5, 8.6, 0.5)).T, 1)
    ang = np.degrees(np.arccos(np.clip((np.trace(Rx) - 1) / 2, -1, 1)))
    Vf = Vf @ Rx.T - o
    m0 = np.abs(P[:, 1]) < 0.25
    log('- redressement sur le plan médian de la paume (3 passes) : rotation totale %.1f° ; pente résiduelle du plan '
        'médian %.2f° ; origine = milieu de la section du poignet au cube MH « wrist » (largeur %.2f cm, épaisseur %.2f cm)'
        % (ang, math.degrees(math.atan(a2)), np.ptp(P[m0, 0]), np.ptp(P[m0, 2])))
    # --- bouchon du poignet : un n-gone orienté vers −Y (ses arêtes seront vives à la subdivision) ---
    nb = defaultdict(list)
    for a, b in loop: nb[remap[a]].append(remap[b]); nb[remap[b]].append(remap[a])
    ring = [remap[lv[0]]]; prev = None
    while len(ring) < len(lv):
        cur = ring[-1]; nxt = [x for x in nb[cur] if x != prev and x not in ring[-2:]]
        prev = cur; ring.append(nxt[0])
    c = Vf[ring].mean(0); nrm = sum(np.cross(Vf[ring[i]] - c, Vf[ring[(i + 1) % len(ring)]] - c) for i in range(len(ring)))
    if nrm @ (c - Vf.mean(0)) < 0: ring = ring[::-1]
    Fq.append(ring)
    # --- repères MH dans le repère du contrat ---
    jts = {k: vers_contrat(J[k], Rx, o) for k in J if k.endswith('.L____head') or k.endswith('.L____tail')}
    plans = {}
    for b, info in sk['bones'].items():
        if b in MH2OS and not b.startswith('lowerarm'):
            plans[b] = [vers_contrat(J[q], Rx, o).tolist() for q in sk['planes'][info['rotation_plane']]]
    # --- poids MH reportés sur les 20 os du contrat ---
    hset = set(hv); Wm = np.zeros((len(hv), len(OS)))
    for bone, lst in Wmh.items():
        if bone not in MH2OS: continue
        col = OSI[MH2OS[bone]]
        for v, val in lst:
            if v in hset: Wm[remap[v], col] += val
    ignores = [b for b, l in Wmh.items() if b not in MH2OS and any(v in hset for v, _ in l)]
    Wm /= np.maximum(Wm.sum(1, keepdims=True), 1e-9)
    # orientation des faces : normales sortantes ?
    T1, _ = triangles(Fq); nn = np.cross(Vf[T1[:, 1]] - Vf[T1[:, 0]], Vf[T1[:, 2]] - Vf[T1[:, 0]])
    vol = float((nn * Vf[T1].mean(1)).sum() / 6)
    log('- main extraite : %d sommets, %d faces (%d quads + 1 bouchon de %d côtés), volume %.0f cm³ (> 0 : faces '
        'orientées vers l’extérieur) ; boîte x %.1f..%.1f, y %.1f..%.1f, z %.1f..%.1f cm' %
        (len(Vf), len(Fq), len(Fq) - 1, len(ring), vol, *np.array([Vf.min(0), Vf.max(0)]).T.ravel()))
    log('- os MH sans équivalent ignorés : %s ; longueur MH poignet → bout du majeur : %.2f cm (cible %.1f)' %
        (', '.join(ignores) or 'aucun', jts['finger3-3.L____tail'][1], HL))
    sauver('s1', V=Vf, F=Fq, ring=np.array(ring), W=Wm, orig=np.array(hv), jts=json.dumps({k: v.tolist() for k, v in jts.items()}),
           plans=json.dumps(plans))
    # --- image ---
    VW = vues(); ims, labs = [], []
    T, _ = triangles(Fq)
    for nm in ['paume', 'dos', 'profil_radial', 'dessus']:
        v = Vue(Vf, T, VW[nm], 560); im = v.image(fil=True)
        from PIL import ImageDraw
        dr = ImageDraw.Draw(im)
        for b in OS2MH.values():
            h, t = v.proj(jts[b + '____head']), v.proj(jts[b + '____tail'])
            dr.line([tuple(h), tuple(t)], fill=(220, 30, 30), width=2)
        ims.append(im); labs.append('MH brut — ' + nm)
    planche(ims, labs, cols=4, titre='Étape 1 — main MakeHuman extraite (coupe plane, bouchon), repère du contrat ; '
            'segments rouges : os MH (cubes-repères)').save(os.path.join(CHECKS, 'e1_extraction.png'))
    return dict(V=Vf, F=Fq, ring=ring, W=Wm, jts=jts, plans=plans)

def lire_s1():
    d = charger('s1')
    return dict(V=d['V'], F=faces_de(d['F']), ring=list(map(int, d['ring'])), W=d['W'],
                jts={k: np.array(v) for k, v in json.loads(str(d['jts'])).items()}, plans=json.loads(str(d['plans'])))


# =================================================================================================================
# Le dessin de l'utilisateur (references/paume.jpg) et les chaînes corrigées du rig v1
# =================================================================================================================
DESSIN = dict(x0=505.0, y_pli=792.0, y_bout=18.0)   # px : axe du majeur (chaîne v1 : x = 505, 505, 507, 507), pli du
                                                      # poignet dessiné (y = 792), bout du majeur (y = 18)
SY = HL / (DESSIN['y_pli'] - DESSIN['y_bout'])        # 0,02455 cm/px : HL = 190 mm sur 774 px
# plis DESSINÉS (rig3d.py, CP) : [pli de la racine, pli IPP, pli IPD, bout] — sert à la règle de l'auriculaire
CP_DESSIN = {'annulaire': [[400, 368], [381, 263], [366, 178], [350, 66]]}
TRAIT_DESSIN = 2.85    # px : demi-épaisseur du trait de contour (médiane mesurée 5,7 px) : le « contour du dessin »
                       # est le MILIEU du trait, c'est-à-dire la peau du dessin dilatée de 2,85 px

def masques_dessin():
    """masque de la peau du dessin (sans le trait), puis masque « milieu du trait » (peau dilatée de TRAIT_DESSIN)"""
    from PIL import Image
    from scipy import ndimage
    im = np.array(Image.open(os.path.join(RACINE, 'references', 'paume.jpg')).convert('RGB')).astype(float)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]; L = 0.299 * r + 0.587 * g + 0.114 * b
    peau = ((r - b) / 85.0 > 0.22) & (L > 110)          # peau = teinte chaude claire ; plis et trait = sombres
    peau = ndimage.binary_fill_holes(peau)
    lab, n = ndimage.label(peau); sz = ndimage.sum(peau, lab, range(1, n + 1)); peau = lab == 1 + int(np.argmax(sz))
    peau = ndimage.binary_opening(peau, iterations=1)
    milieu = ndimage.distance_transform_edt(~peau) <= TRAIT_DESSIN
    return peau, milieu, im

def chaines_v1():
    """chaînes corrigées du rig v1 (source/hand3d.json → mesh.chain : MCP enfoncée DEEP8, IPD glissée PHAL8, IP du
    pouce IP8, CMC au trapèze) : [MCP, IPP, IPD, bout] ; pouce [CMC, MCP, IP, bout], en px du dessin paume"""
    d = json.load(open(os.path.join(RACINE, 'source', 'hand3d.json')))
    return {k: np.array(v, float) for k, v in d['mesh']['chain'].items()}

# =================================================================================================================
# Étape 2 — squelette cible : 20 os, centres corrigés (anatomie.md § 3), axes locaux
# =================================================================================================================
# Os de Buryanov & Kotiuk 2010 × 1,03 (main de 185 → 190 mm), mm ; P3 inclut le tissu mou du bout (anatomie.md § 2.1)
BURYANOV = {'index': (41.0, 23.1, 16.3 + 3.8), 'majeur': (45.9, 27.1, 17.9 + 4.0), 'annulaire': (42.6, 26.5, 17.8 + 4.0),
            'auriculaire': (33.7, 18.6, 16.5 + 3.5), 'pouce': (47.6, 32.5, 22.4 + 5.7)}     # pouce : MC I, P1, P2 + pulpe
BURYANOV_MC = {'index': 70.1, 'majeur': 66.5, 'annulaire': 59.7, 'auriculaire': 55.3}  # MC II–V × 1,03
EP_PAUME_MCP = 3.0     # cm, épaisseur de la paume aux têtes métacarpiennes (anatomie.md § 1 et 4.3 : 30 ± 3 mm)
PROF_MCP = 0.38        # centre de la tête MC depuis la peau du dos, en fraction de cette épaisseur : 5 mm de peau
                       # et de tendons + demi-tête de 6,5 mm = 11,5 / 30 (tête en came, centre décalé vers la paume)
Z_MCP = -EP_PAUME_MCP / 2 + PROF_MCP * EP_PAUME_MCP     # −0,36 cm (plan médian de la paume en z = 0)
# Arc des têtes métacarpiennes (anatomie.md § 3) : en Y, relatif au majeur (index −2 mm, annulaire −4, auriculaire
# −10 à −14) ; en Z, voûte transversale concave côté paume, flèche ≈ 5 mm sur la corde II–V (5–8 mm au repos)
ARC_Y = {'index': -0.2, 'majeur': 0.0, 'annulaire': -0.4, 'auriculaire': -1.1}
ARC_Z = {'index': 0.25, 'majeur': 0.0, 'annulaire': 0.20, 'auriculaire': 0.80}
# Éventail au repos (doigts tendus, « le long de +Y ») : les axes rayonnent depuis le carpe, 4–6° entre voisins,
# l'auriculaire un peu plus ouvert (anatomie.md § 3, « Éventail » ; photo 2354 : 7° / 6° / 32° en main étalée)
EVENTAIL = {'index': 4.0, 'majeur': 0.0, 'annulaire': -5.5, 'auriculaire': -14.0}   # auriculaire à −10° : palmure
# annulaire–auriculaire repliée en pli vif (angle entre faces 86°, mesuré) ; à −14° elle reste une selle douce
# Bases des métacarpiens II–V (x, cm) : la rangée distale du carpe est plus étroite que la ligne des têtes
# (≈ 3,3 cm de la base de MC II à celle de MC V contre 5,9 cm entre têtes)
BASE_MC_X = {'index': 1.25, 'majeur': 0.15, 'annulaire': -0.95, 'auriculaire': -2.0}
# Obliquité des axes de flexion (convergence vers le scaphoïde, mobilite.md R1 : « axes de flexion des MCP ET des IP
# obliques ») : rotation de l'axe de flexion autour de l'os.
# Grief du 20 octobre 2026 (« L » vu de dos : « j'ai jamais vu des doigts aussi inclinés », jointures en vague) : la v1
# mettait TOUTE la convergence dans la MCP (`LEAN` −6,5 / 0 / +6,5 / +12°). Mesuré dans le moteur (presets résolus, repère
# de la main, arc automatique 0,6 compris) : P1 repliées à 90° inclinées de −6,5 / 0 / +8,0 / +4,9° — vues de dos en
# plongée, l'inclinaison s'amplifie (×1/sin de la plongée : ×2,9 à 20°) et chaque jointure penche vers le majeur. Sur SES
# photos (V de dos, poing 2357), les P1 repliées restent PARALLÈLES sous le majeur ; ce sont les P2–P3 qui convergent vers
# la base du thénar. D'où : MCP presque droites, la convergence passe dans les IP.
#   LEAN (MCP)    : P1 à 90° (moteur, arc 0,6) inclinées de −3,0 / 0 / +3,0 / +3,2° (cible : « quelques degrés ») ;
#                   l'auriculaire garde +10° d'axe parce que l'arc métacarpien du moteur (mc5 : supination 20°·arc, arc
#                   0,6 dès que l'auriculaire se replie) le renverse de −6,8° ; l'annulaire +1,5 (mc4 : flexion 12°·arc
#                   l'incline de +1,5°)
#   LEAN_IP (IPP et IPD) : −4 / 0 / +4 / +8° : bouts du poing ramenés à 0,88 de l'écart des MCP (v1, piste P : 0,90)
# Le contact entre P1 voisines, que la v1 obtenait en inclinant les P1, vient de la chair des flancs (correctif de la
# MCP, `elargit`, comme `KNL` en v1).
LEAN = {'index': -3.0, 'majeur': 0.0, 'annulaire': 1.5, 'auriculaire': 10.0}
LEAN_IP = {'index': -4.0, 'majeur': 0.0, 'annulaire': 4.0, 'auriculaire': 8.0}
# Pouce : trapézo-métacarpienne à la base de l'éminence thénar (dessin : (652, 748) px → (3,28 ; 1,08) cm ; anatomie
# § 3 : trapèze dans la rangée distale du carpe) ; MC I à 30° de MC II (anatomie.md § 3, repos relâché), sorti de 20°
# du plan de la paume (colonne du pouce antérieure) ; P1 et P2 dans le prolongement, un peu plus écartés (dessin)
CMC_POUCE = np.array([3.2, 1.4, 0.3])
POUCE_ANGLES = {'mc1': (None, 20.0), 'pouce_p1': (30.0, 12.0), 'pouce_p2': (34.0, 6.0)}   # (dans le plan°, élévation°)
POUCE_MC_MCII = 30.0
# Pronation de repos de P1–P2 du pouce (20 octobre 2026). MakeHuman donne 75° (normale de son ongle ; 0 = pulpe vers
# +Z, 90 = pulpe vers l'index, ongle ⟂ paume). Mesuré sur SON dessin (pose « dessin », silhouette de face, milieu du
# trait) : le pouce vu de face y fait 21,2 mm à mi-P1, 21,9 à l'IP, 19,8 / 18,1 sur P2 ; le maillage à 75° n'en montrait
# que 19,6 / 18,2 / 17,9 / 17,1 — il montrait son FLANC (épaisseur 17,5 mm), donc il paraissait aussi mince que l'index
# alors qu'une IP de 21,9 mm ne se voit que de face (largeur 22 mm). Ses photos disent la même chose : pouce écarté vu
# côté paume = 1,3 à 1,5 × la largeur de P2 de l'index (IMG_2354 : P1 79 / IP 72,5 / P2 67 px contre 52,5 ; IMG_2361 :
# 76 / 72 / 59,5 contre ≈ 47). Balayage : −20° → 21,4 / 20,0 / 19,2 / 18,5 mm (P1 aux 3/10 : 22,5 contre 21,9, plus
# large que son dessin) ; −35° → jusqu'à +3,1 mm de trop ; −18° retenu (≈ 57°) : jamais plus large que son dessin. La
# pronation COUPLÉE du moteur (34° en opposition) la remonte ensuite pouce opposé. C'est la PEAU de P1–P2 (et l'ongle) qui
# tourne autour de l'os (repères géométriques AG, étape 2) ; les repères de liaison (axes de la MCP et de l'IP que lit le
# moteur) et mc1 (trapézo-métacarpienne validée en v1) ne bougent pas : la MCP et l'IP du pouce fléchissent sur un axe
# oblique de 18° par rapport à l'ongle (vers l'index), et les presets du pouce réglés par `reach` restent justes.
# (Essayé d'abord : tourner aussi les axes — la pince, le F et les becs s'ouvraient d'≈ 1 cm dans le moteur.)
PRONATION_POUCE_DELTA = -18.0

def px2cm(p, sx):
    p = np.asarray(p, float); return np.array([(p[0] - DESSIN['x0']) * sx, (DESSIN['y_pli'] - p[1]) * SY])

def repere(y, zref):
    """repère local (colonnes X, Y, Z) : Y le long de l'os, Z vers zref (paume / pulpe), X = Y × Z (axe de flexion)"""
    y = nz(y); z = nz(zref - (zref @ y) * y); x = np.cross(y, z); return np.stack([x, y, z], 1)

def ongles_mh(s1):
    """plaques d'ongle de la topologie hm08 (faces), par doigt. Index : région bordée par le sillon (arêtes concaves
    > 6°) — 8 quads ; majeur, annulaire, auriculaire : MÊME topologie que l'index, décalée de 192·k (1er bloc de
    sommets du doigt) et 39·k (2e bloc), vérifié face par face ; pouce : topologie propre, 6 quads repérés au rendu
    (sillon en U, checks/e1_ongles.png)."""
    d = charger('s1'); orig = d['orig']; V, F = s1['V'], s1['F']
    pos = {tuple(sorted(orig[f])): i for i, f in enumerate(F)}
    IDX = [(9648, 8747, 8739, 9647), (8738, 8747, 9648, 9646), (8742, 8746, 8747, 8738), (8746, 8741, 8739, 8747),
           (8736, 8740, 9490, 9492), (8746, 8742, 9491, 9492), (9492, 9490, 8741, 8746), (9492, 9491, 8743, 8736)]
    out = {}
    for k, nom in enumerate(DOIGTS):
        m = lambda v: v + 192 * k if v < 9340 else v + 39 * k
        out[nom] = [pos[tuple(sorted(m(v) for v in f))] for f in IDX]
    # pouce : faces dorsales de la P2 MH entourées par le sillon : graine au centre du dos de la pulpe, remplissage
    # sans franchir les arêtes concaves > 5°, limité au dos (angle < 60°) et à 0,30–0,93 de la phalange
    j = s1['jts']; h = j['finger1-3.L____head']; t = j['finger1-3.L____tail']; u = nz(t - h); L = np.linalg.norm(t - h)
    fn = nz(np.array([np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]]) for f in F])); fc = np.array([V[f].mean(0) for f in F])
    p = np.array(s1['plans']['finger1-3.L']); dors = nz(np.cross(nz(np.cross(p[1] - p[0], p[2] - p[0])), u))
    sd = (fc - h) @ u; r = fc - h - np.outer(sd, u)
    dors = nz(dors - (dors @ u) * u)
    # sens : le dos du pouce est du côté opposé à la paume (la pulpe regarde l'index)
    if dors @ np.array([-1.0, 0, 0]) > 0: dors = -dors
    cand = set(np.where((sd > 0.30 * L) & (sd < 0.93 * L) & ((nz(r) @ dors) > 0.5))[0].tolist())
    E = aretes(F); conc = set()
    for e, l in E.items():
        if len(l) == 2 and np.degrees(np.arccos(np.clip(fn[l[0]] @ fn[l[1]], -1, 1))) > 5 and (fc[l[1]] - fc[l[0]]) @ fn[l[0]] > 0: conc.add(e)
    seed = max(cand, key=lambda i: (nz(r[i]) @ dors) - abs(sd[i] / L - 0.62))
    comp = {seed}; st = [seed]
    while st:
        i = st.pop(); f = F[i]
        for q in range(len(f)):
            e = tuple(sorted((f[q], f[(q + 1) % len(f)])))
            if e in conc: continue
            for nb in E[e]:
                if nb in cand and nb not in comp: comp.add(nb); st.append(nb)
    out['pouce'] = sorted(comp)
    return out

def etape2(s1):
    _etape[0] = '2'; log('### 2. Squelette (20 os, centres articulaires corrigés)')
    from raster import Vue, vues, planche
    from PIL import Image, ImageDraw
    V, F, jts = s1['V'], s1['F'], s1['jts']
    peau, milieu, im = masques_dessin()
    # échelle X du dessin : bord ulnaire → apex de la 1re commissure (milieu du trait) = 90,6 mm
    top = np.array([np.where(milieu[:, x])[0].min() if milieu[:, x].any() else 0 for x in range(milieu.shape[1])])
    xa = 600 + int(np.argmax(top[600:760])); ya = int(top[xa])
    xs = np.where(milieu[ya])[0]; x_uln = int(xs.min())
    sx = PAUME_L / (xa - x_uln)
    log('- dessin : apex de la 1re commissure (%d, %d) px, bord ulnaire x = %d px à la même hauteur → échelle X %.5f cm/px '
        '(paume %.1f mm) ; échelle Y %.5f cm/px (HL %.0f mm sur %d px) ; anisotropie %.3f' %
        (xa, ya, x_uln, sx, PAUME_L * 10, SY, HL * 10, DESSIN['y_pli'] - DESSIN['y_bout'], SY / sx))
    ch = chaines_v1()
    # --- longueurs : longueur totale MCP → bout du DESSIN (ses proportions), répartie selon Buryanov ---
    L, tot_d, seg_d = {}, {}, {}
    for k in DOIGTS:
        c = [px2cm(p, sx) for p in ch[k]]; seg_d[k] = [float(np.linalg.norm(c[i + 1] - c[i])) for i in range(3)]
        tot_d[k] = sum(seg_d[k]); b = np.array(BURYANOV[k]) / 10; L[k] = (b / b.sum() * tot_d[k]).tolist()
    mcp = {}
    ym = px2cm(ch['majeur'][0], sx)[1]
    for k in DOIGTS:
        x = px2cm(ch[k][0], sx)[0]; mcp[k] = np.array([x, ym + ARC_Y[k], Z_MCP + ARC_Z[k]])
    # auriculaire : son bout atteint le pli IPD de l'annulaire (anatomie.md § 9, photos) — doigts serrés, donc le long
    # de +Y : entre le centre de l'IPD de l'annulaire et son pli IPD dessiné (le pli est quelques mm en amont)
    y_ipd_c = mcp['annulaire'][1] + L['annulaire'][0] + L['annulaire'][1]
    y_ipd_p = px2cm(CP_DESSIN['annulaire'][2], sx)[1]
    tot5 = 0.5 * (y_ipd_c + y_ipd_p) - mcp['auriculaire'][1]; b5 = np.array(BURYANOV['auriculaire']) / 10
    L['auriculaire'] = (b5 / b5.sum() * tot5).tolist()
    L['pouce'] = (np.array(BURYANOV['pouce']) / 10).tolist()
    log('- longueurs centre → centre (cm) : dessin (chaîne v1 corrigée) | Buryanov × 1,03 | RETENU (total du dessin, '
        'partage de Buryanov ; pouce : Buryanov)')
    log('')
    log('| doigt | P1 dessin | P2 dessin | P3+pulpe dessin | total dessin | P1 Bur. | P2 Bur. | P3+p Bur. | total Bur. | P1 retenu | P2 retenu | P3+p retenu | total retenu |')
    log('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for k in DOIGTS + ['pouce']:
        if k == 'pouce':
            c = [px2cm(p, sx) for p in ch['pouce']]; sd = [float(np.linalg.norm(c[i + 1] - c[i])) for i in range(3)]
        else: sd = seg_d[k]
        b = np.array(BURYANOV[k]) / 10
        log('| %s | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | %.2f | **%.2f** | **%.2f** | **%.2f** | **%.2f** |' %
            ((k,) + tuple(sd) + (sum(sd),) + tuple(b) + (b.sum(),) + tuple(L[k]) + (sum(L[k]),)))
    log('')
    log('  (pouce : colonnes « dessin » = MC I, P1, P2 + pulpe projetés ; auriculaire : total = mi-chemin entre le '
        'centre de l’IPD de l’annulaire (y = %.2f) et son pli IPD dessiné (y = %.2f) − y de sa MCP (%.2f) = %.2f ; '
        'dessin %.2f, Buryanov %.2f)' % (y_ipd_c, y_ipd_p, mcp['auriculaire'][1], tot5, tot_d['auriculaire'], b5.sum()))
    # --- centres ---
    C = {'poignet': np.zeros(3)}; bout = {}
    for k in DOIGTS:
        a = math.radians(EVENTAIL[k]); u = np.array([math.sin(a), math.cos(a), 0.0])
        p = mcp[k].copy(); C[k + '_p1'] = p
        C[k + '_p2'] = p + u * L[k][0]; C[k + '_p3'] = C[k + '_p2'] + u * L[k][1]; bout[k] = C[k + '_p3'] + u * L[k][2]
        i = DOIGTS.index(k) + 2; lm = BURYANOV_MC[k] / 10
        dx = BASE_MC_X[k] - p[0]; C['mc%d' % i] = np.array([BASE_MC_X[k], p[1] - math.sqrt(lm ** 2 - dx ** 2), p[2]])
    # pouce : MC I à POUCE_MC_MCII de MC II en 3D avec l'élévation voulue
    u2 = nz(C['index_p1'] - C['mc2']); a2 = math.atan2(u2[0], u2[1]); el = math.radians(POUCE_ANGLES['mc1'][1])
    da = math.acos(min(1.0, math.cos(math.radians(POUCE_MC_MCII)) / math.cos(el)))
    a1 = a2 + da
    u1 = np.array([math.sin(a1) * math.cos(el), math.cos(a1) * math.cos(el), math.sin(el)])
    C['mc1'] = CMC_POUCE.copy(); C['pouce_p1'] = C['mc1'] + u1 * L['pouce'][0]
    dirs = {'mc1': u1}
    for b, nxt, Lb in (('pouce_p1', 'pouce_p2', L['pouce'][1]), ('pouce_p2', None, L['pouce'][2])):
        a, e = map(math.radians, POUCE_ANGLES[b]); dirs[b] = np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])
        q = C[b] + dirs[b] * Lb
        if nxt: C[nxt] = q
        else: bout['pouce'] = q
    # --- axes locaux ---
    A = {'poignet': np.eye(3)}
    for k in DOIGTS:
        i = DOIGTS.index(k) + 2
        A['mc%d' % i] = repere(C[k + '_p1'] - C['mc%d' % i], np.array([0, 0, 1.0]))
        for jj, b in enumerate(CHAINES[k][1:]):
            nxt = C[CHAINES[k][jj + 2]] if jj < 2 else bout[k]
            fr = repere(nxt - C[b], np.array([0, 0, 1.0]))
            # obliquité de l'axe de flexion : LEAN à la MCP, LEAN_IP à l'IPP et à l'IPD (rotation autour de l'os)
            fr = rot_axe(fr[:, 1], math.radians(LEAN[k] if jj == 0 else LEAN_IP[k])) @ fr
            A[b] = fr
    # pouce : Z = pulpe. Pronation reprise de MakeHuman : normale de la plaque d'ongle MH (dos), transportée par la
    # plus petite rotation de la direction MH de chaque os vers la direction cible
    ong = ongles_mh(s1)
    fnrm = nz(np.array([np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]]) for f in F]))
    n_ongle = nz(fnrm[ong['pouce']].sum(0))
    for b, mhb, nxt in (('mc1', 'finger1-1.L', 'pouce_p1'), ('pouce_p1', 'finger1-2.L', 'pouce_p2'), ('pouce_p2', 'finger1-3.L', None)):
        dmh = nz(jts[mhb + '____tail'] - jts[mhb + '____head']); y = nz((C[nxt] if nxt else bout['pouce']) - C[b])
        pulpe = rot_min(dmh, y) @ (-n_ongle)
        A[b] = repere(y, pulpe)
    pron_ = lambda F: math.degrees(math.atan2(-(F[:, 2] @ np.array([1.0, 0, 0])), F[:, 2] @ np.array([0, 0, 1.0])))
    pron_mh = pron_(A['pouce_p2'])
    # repères GÉOMÉTRIQUES (AG) : ceux de la peau à la retaille, des ongles, des coupes ; = A partout sauf P1–P2 du pouce,
    # tournés de PRONATION_POUCE_DELTA autour de l'os. Les repères de liaison A (axes de la MCP et de l'IP lus par le
    # moteur) restent ceux de MakeHuman : les presets du pouce réglés par `reach` (O, pince, F, becs…) gardent leur
    # cinématique (essayé : tourner aussi A ouvrait la pince et le F de 1 cm — le moteur les avait réglés sur ces axes).
    AG = {b: A[b].copy() for b in A}
    if PRONATION_POUCE_DELTA:
        for b in ('pouce_p1', 'pouce_p2'):
            Rp = rot_axe(A[b][:, 1], math.radians(abs(PRONATION_POUCE_DELTA))); Rm = rot_axe(A[b][:, 1], -math.radians(abs(PRONATION_POUCE_DELTA)))
            plus = pron_(Rp @ A[b]) > pron_(Rm @ A[b])
            AG[b] = (Rp if plus == (PRONATION_POUCE_DELTA > 0) else Rm) @ A[b]
    pron = pron_(AG['pouce_p2'])
    # --- tableau ---
    long = {}
    for b in OS:
        if b == 'poignet': long[b] = float(np.linalg.norm(C['mc3'])); continue
        k = CHAINE_DE[b]; chn = CHAINES[k]; jj = chn.index(b)
        nxt = C[chn[jj + 1]] if jj + 1 < len(chn) else bout[k]; long[b] = float(np.linalg.norm(nxt - C[b]))
    log('- centres articulaires retenus (cm, repère du contrat) et longueurs :')
    log('')
    log('| os | parent | centre (x, y, z) | longueur | cible | X local (axe de flexion) | Z local |')
    log('|---|---|---|---|---|---|---|')
    for b in OS:
        k = CHAINE_DE.get(b); 
        if b == 'poignet': cible = '—'
        elif b.startswith('mc') and b != 'mc1': cible = 'MC Bur. %.2f' % (BURYANOV_MC[k] / 10)
        else:
            jj = CHAINES[k].index(b) - (0 if k == 'pouce' else 1); cible = '%.2f' % L[k][jj]
        log('| %s | %s | (%.2f, %.2f, %.2f) | %.2f | %s | (%.2f, %.2f, %.2f) | (%.2f, %.2f, %.2f) |' %
            (b, PARENT[b] or '—', *C[b], long[b], cible, *A[b][:, 0], *A[b][:, 2]))
    log('')
    ang = lambda u: math.degrees(math.atan2(u[0], u[1]))
    log('- bouts : ' + ', '.join('%s (%.2f, %.2f, %.2f)' % (k, *bout[k]) for k in DOIGTS + ['pouce']) +
        ' ; majeur à y = %.2f (HL %.1f) ; index %.2f / annulaire %.2f (son index = son annulaire)' % (bout['majeur'][1], HL, bout['index'][1], bout['annulaire'][1]))
    log('- arc des têtes : MCP y index %+.1f, annulaire %+.1f, auriculaire %+.1f mm sous le majeur ; voûte : flèche du '
        'majeur sur la corde II–V %.1f mm' % (10 * (C['index_p1'][1] - C['majeur_p1'][1]), 10 * (C['annulaire_p1'][1] - C['majeur_p1'][1]),
        10 * (C['auriculaire_p1'][1] - C['majeur_p1'][1]),
        10 * ((C['index_p1'][2] + (C['majeur_p1'][0] - C['index_p1'][0]) / (C['auriculaire_p1'][0] - C['index_p1'][0]) * (C['auriculaire_p1'][2] - C['index_p1'][2])) - C['majeur_p1'][2])))
    u1 = nz(C['pouce_p1'] - C['mc1'])
    log('- pouce : CMC (%.2f, %.2f, %.2f) ; MC I à %.1f° de MC II en 3D (dans le plan de la paume %.1f° contre %.1f°, '
        'élévation palmaire %.0f°) ; pronation de la pulpe %.0f° (0 = pulpe vers +Z, 90 = pulpe vers l’index ; reprise de '
        'MH : normale de son ongle) ; ongles MH repérés : %s faces' % (*C['mc1'], math.degrees(math.acos(u1 @ u2)), ang(u1), ang(u2),
        math.degrees(math.asin(u1[2])), pron, '/'.join(str(len(ong[k])) for k in ['pouce'] + DOIGTS)))
    if PRONATION_POUCE_DELTA:
        log('- pronation de repos de P1–P2 du pouce : %.0f° chez MakeHuman, %+.0f° → %.0f° (voir PRONATION_POUCE_DELTA : '
            'largeurs du pouce vu de face sur SON dessin)' % (pron_mh, PRONATION_POUCE_DELTA, pron))
    # contrôle de l'obliquité : angle latéral des P1 et des P2 dans un poing (MCP 90, IPP 105, IPD 70, arc 0,6 comme le
    # moteur), dans le repère de la main ; écart des bouts / écart des MCP
    sq_ = dict(C=C, A=A, bout=bout); pz = dict({k: {'mcp': 90, 'pip': 105, 'dip': 70} for k in DOIGTS}, arc=0.6); Mz = cinematique(sq_, pz)
    lat1 = {k: math.degrees(math.atan2(*(Mz[OSI[k + '_p1']][:3, :3] @ A[k + '_p1'][:, 1])[[0, 2]])) for k in DOIGTS}
    tz = {k: (Mz[OSI[k + '_p3']] @ np.r_[bout[k], 1])[0] for k in DOIGTS}; mz = {k: (Mz[OSI[k + '_p1']] @ np.r_[C[k + '_p1'], 1])[0] for k in DOIGTS}
    log('- obliquité (LEAN %s ; LEAN_IP %s) : poing (MCP 90 / IPP 105 / IPD 70, arc 0,6) — P1 inclinées de %s par rapport à la '
        'normale de la paume (+ vers le pouce) ; écart des bouts index–auriculaire %.1f mm pour %.1f mm entre MCP (rapport %.2f)'
        % ('/'.join('%+.1f' % LEAN[k] for k in DOIGTS), '/'.join('%+.1f' % LEAN_IP[k] for k in DOIGTS),
           ' / '.join('%s %+.1f°' % (k, lat1[k]) for k in DOIGTS), 10 * (tz['index'] - tz['auriculaire']), 10 * (mz['index'] - mz['auriculaire']),
           (tz['index'] - tz['auriculaire']) / (mz['index'] - mz['auriculaire'])))
    # (ancienne mesure, gardée)
    txt = []
    for k in DOIGTS:
        b = k + '_p1'; c = C[b]; R = rot_axe(A[b][:, 0], math.radians(90)); t2 = c + R @ (bout[k] - c)
        txt.append('%s %+.2f cm' % (k, t2[0] - bout[k][0]))
    log('- obliquité (LEAN) : déport latéral du bout après 90° de flexion de la MCP (+ vers le pouce) : ' + ', '.join(txt))
    sq = dict(C={b: C[b].tolist() for b in C}, A={b: A[b].tolist() for b in A}, AG={b: AG[b].tolist() for b in AG}, bout={k: bout[k].tolist() for k in bout},
              L=L, long=long, sx=sx, commissure=[xa, ya], x_uln=x_uln, ongles_mh={k: list(map(int, v)) for k, v in ong.items()})
    json.dump(sq, open(os.path.join(WORK, 's2.json'), 'w'), indent=1)
    # --- images : squelette cible sur la main MH brute (paume, profil) et sur le dessin ---
    segs = []
    for b in OS[1:]:
        k = CHAINE_DE[b]; chn = CHAINES[k]; jj = chn.index(b)
        segs.append((C[PARENT[b]] if b.startswith('mc') else C[b], C[b])) if b.startswith('mc') else None
        nxt = C[chn[jj + 1]] if jj + 1 < len(chn) else bout[k]; segs.append((C[b], nxt))
    T, _ = triangles(F); VW = vues(); ims, labs = [], []
    for nm in ('paume', 'profil_radial'):
        v = Vue(V, T, VW[nm], 640, centre=np.array([1.0, 8.0, 0.0]), echelle=640 * 0.44 / 11.0)
        img = v.image(couleur=(150, 200, 196)); dr = ImageDraw.Draw(img)
        for a, b in segs: dr.line([tuple(v.proj(a)), tuple(v.proj(b))], fill=(220, 30, 30), width=3)
        for b in OS:
            x, y = v.proj(C[b]); dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(30, 30, 220))
        ims.append(img); labs.append('squelette cible sur MH brut — ' + nm)
    # sur le dessin (pixels → cm anisotropes)
    H, Wd = peau.shape; S = 640 / 24.0
    def P2(x, y): return ((x + 12.0 - 1.0) * S, 640 - (y + 2.5) * S)
    img = Image.new('RGB', (640, 640), 'white'); ar = np.array(img)
    ys_, xs_ = np.nonzero(milieu); X = (xs_ - DESSIN['x0']) * sx; Y = (DESSIN['y_pli'] - ys_) * SY
    px = np.clip(((X + 11.0) * S).astype(int), 0, 639); py = np.clip((640 - (Y + 2.5) * S).astype(int), 0, 639)
    ar[py, px] = (215, 215, 215); img = Image.fromarray(ar); dr = ImageDraw.Draw(img)
    for a, b in segs: dr.line([P2(a[0], a[1]), P2(b[0], b[1])], fill=(220, 30, 30), width=3)
    for b in OS:
        x, y = P2(*C[b][:2]); dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(30, 30, 220))
    for k in ch:
        for p in ch[k]:
            x, y = P2(*px2cm(p, sx)); dr.rectangle([x - 3, y - 3, x + 3, y + 3], outline=(0, 140, 0))
    ims.append(img); labs.append('sur le dessin (gris) ; carrés verts : chaîne v1')
    planche(ims, labs, cols=3, titre='Étape 2 — squelette cible (centres corrigés : arc des têtes, MC I à 30°, '
            'trapèze à la base du thénar)').save(os.path.join(CHECKS, 'e2_squelette.png'))
    return lire_s2()

def lire_s2():
    sq = json.load(open(os.path.join(WORK, 's2.json')))
    sq['C'] = {k: np.array(v) for k, v in sq['C'].items()}; sq['A'] = {k: np.array(v) for k, v in sq['A'].items()}
    sq['AG'] = {k: np.array(v) for k, v in sq.get('AG', sq['A']).items()}
    sq['bout'] = {k: np.array(v) for k, v in sq['bout'].items()}
    return sq



# =================================================================================================================
# Cinématique directe : pose v2 (degrés) → matrices de skinning (monde posé · liaison⁻¹), pour les contrôles.
# La convention (axes, signes, ordre) est écrite dans hand_v2.json → "convention_pose" pour le moteur (M2).
# =================================================================================================================
def mat4(R, t):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t; return M

def rot_local(axes):
    """produit de rotations intrinsèques [(axe 'x'|'y'|'z', degrés), …] dans le repère local de l'os"""
    R = np.eye(3)
    for ax, deg in axes:
        if deg: R = R @ rot_axe({'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}[ax], math.radians(deg))
    return R

def rotations_pose(pose):
    """pose v2 → rotation locale (3×3, dans le repère de liaison de l'os) de chaque os.
    Doigts : P1 = abduction autour de Z local (ab > 0 : vers le pouce, +X), puis flexion autour de X (oblique, LEAN),
    puis rotation axiale autour de Y ; P2, P3 : flexion autour de X. Pouce : MC I = « rapprocher » (rap > 0 : vers
    l'index, flexion-adduction) autour de X local (≈ normale à la paume), puis « avancer » (av > 0 : abduction palmaire,
    vers +Z) autour de Z local ; P1 = MCP (flexion autour de X) + abdMcp (autour de Z) ; P2 = IP (autour de X).
    Arc métacarpien (arc 0–1) : MC IV fléchi de 12°·arc, MC V de 25°·arc et supiné de 20°·arc (mobilite.md R11)."""
    g = lambda d, k: float((d or {}).get(k, 0) or 0)
    R = {b: np.eye(3) for b in OS}
    for k in DOIGTS:
        d = pose.get(k, {})
        R[k + '_p1'] = rot_local([('z', -g(d, 'ab')), ('x', g(d, 'mcp')), ('y', g(d, 'rot'))])
        R[k + '_p2'] = rot_local([('x', g(d, 'pip'))]); R[k + '_p3'] = rot_local([('x', g(d, 'dip'))])
    p = pose.get('pouce', {})
    R['mc1'] = rot_local([('x', g(p, 'rap')), ('z', -g(p, 'av'))])
    R['pouce_p1'] = rot_local([('x', g(p, 'mcp')), ('z', -g(p, 'abdMcp'))])
    R['pouce_p2'] = rot_local([('x', g(p, 'ip'))])
    arc = float(pose.get('arc', 0) or 0)
    R['mc4'] = rot_local([('x', 12 * arc)]); R['mc5'] = rot_local([('x', 25 * arc), ('y', -20 * arc)])
    return R

def cinematique(sq, pose):
    """matrices de skinning 4×4 (monde posé · liaison⁻¹) des 20 os. Le poignet (racine) porte l'avant-bras : la flexion
    (pose.poignet.flex > 0 : vers la paume) et l'inclinaison (dev > 0 : radiale, vers le pouce) font tourner les cinq
    rayons autour de l'origine ; la pronation (prono > 0) fait tourner toute la main ET l'avant-bras autour de Y."""
    C, A = sq['C'], sq['A']; Rl = rotations_pose(pose)
    lie = {b: mat4(A[b], C[b]) for b in OS}
    pw = pose.get('poignet', {}) or {}
    Rw = rot_axe([1, 0, 0], math.radians(float(pw.get('flex', 0) or 0))) @ rot_axe([0, 0, 1], math.radians(-float(pw.get('dev', 0) or 0)))
    Rp = rot_axe([0, 1, 0], math.radians(float(pose.get('prono', 0) or 0)))
    G = {'poignet': mat4(Rp, np.zeros(3))}
    Gm = mat4(Rp @ Rw, np.zeros(3))                       # repère des rayons (main) : poignet + flexion/inclinaison
    for b in OS[1:]:
        par = PARENT[b]
        base = Gm if par == 'poignet' else G[par] @ np.linalg.inv(lie[par])
        G[b] = base @ lie[b] @ mat4(Rl[b], np.zeros(3)) if par == 'poignet' else G[par] @ np.linalg.inv(lie[par]) @ lie[b] @ mat4(Rl[b], np.zeros(3))
    return np.array([G[b] @ np.linalg.inv(lie[b]) for b in OS])

def poids4(W):
    """poids (n, 20) → 4 plus forts (indices, poids normalisés)"""
    J = np.argsort(-W, 1)[:, :4]; w = np.take_along_axis(W, J, 1); w /= np.maximum(w.sum(1, keepdims=True), 1e-12)
    return J, w

def poser(V, W, sq, pose, mode='dqs'):
    J, w = poids4(W); M = cinematique(sq, pose)
    return dqs(V, J, w, M) if mode == 'dqs' else lbs(V, J, w, M)

# =================================================================================================================
# Étape 3 — retaille aux proportions de l'utilisateur
#   3a. déformation pilotée par les os : chaque sommet suit ses os MH pondérés ; pour chaque os, passage du repère MH
#       au repère cible, étirement le long de la chaîne (abscisse MH → abscisse cible, linéaire par morceaux entre
#       centres articulaires) et mise à l'échelle radiale PAR STATION (largeur / épaisseur des tables 4.1–4.2)
#   3b. ajustement de la silhouette de face sur le contour du dessin (milieu du trait) par un champ 2D lissé
# =================================================================================================================
# largeurs (radio-ulnaires) et épaisseurs (dorso-palmaires), cm, anatomie.md tables 4.1–4.2 (main de 190 mm) aux
# stations [P1 milieu, IPP, P2 milieu, IPD, pulpe] ; pouce : [P1 milieu (23 / 19), MCP… voir STATIONS_POUCE]
LARGEUR = {'index': (2.00, 2.05, 1.80, 1.70, 1.65), 'majeur': (2.10, 2.10, 1.85, 1.75, 1.70),
           'annulaire': (1.95, 1.95, 1.70, 1.65, 1.60), 'auriculaire': (1.70, 1.70, 1.50, 1.45, 1.40),
           'pouce': (2.30, 2.25, 2.20, 2.20, 2.10)}
EPAISSEUR = {'index': (1.70, 1.75, 1.50, 1.45, 1.30), 'majeur': (1.80, 1.80, 1.55, 1.50, 1.35),
             'annulaire': (1.65, 1.70, 1.40, 1.40, 1.25), 'auriculaire': (1.45, 1.50, 1.25, 1.20, 1.10),
             'pouce': (1.90, 1.85, 1.75, 1.70, 1.60)}
# pouce : stations [P1 milieu, P1 aux 3/4, IP, P2 milieu (pulpe proximale), pulpe] (table 4.1 : P1 23, IP 22,
# pulpe 21 ; table 4.2 : P1 19, IP 17, P3 16)
LARGEUR_TABLE = {k: tuple(v) for k, v in LARGEUR.items()}; EPAISSEUR_TABLE = {k: tuple(v) for k, v in EPAISSEUR.items()}
# --- LARGEURS DES DOIGTS : SON DESSIN, pas les tables (grief du 20 octobre 2026 : « on a perdu en précision par rapport à
# avant », la v1 étant construite sur ses dessins). Mesuré (pose « dessin », silhouette de face sur la grille du dessin,
# 0,25 mm) : avec les tables 4.1, les quatre doigts sortaient 1 à 4 mm PLUS LARGES que son dessin (index +3,3 à +4,0 mm
# sur P1–IPP, majeur +2,6 à +3,2, annulaire +1,9 à +2,7, auriculaire +0,4 à +1,5), alors que la paume y colle à 1–2 mm
# près : rapportés à la paume, des doigts 10 à 20 % trop gros. Sa photo IMG_2354 (paume à plat), en rapport à la largeur
# de la paume (apex de la 1re commissure → bord ulnaire, 283 px) : index P1 57,5 / P2 52,5 / P3 48,5 px → 18,4 / 16,8 /
# 15,5 mm, c'est-à-dire la largeur de son dessin au MILIEU DU TRAIT (18,2 / 16,0 / 14,9), la convention même de
# l'ajustement de la paume (3b) et de l'échelle X (PAUME_L). D'où : largeur de chaque station = son dessin au milieu du
# trait, le long de la chaîne v1 corrigée (mesh.chain : celle qu'il a validée) ; épaisseur = largeur × le rapport e/l des
# tables 4.1–4.2 (0,76–0,87 : le dessin ne donne pas l'épaisseur). Le pouce garde les tables : vu dans la pose « dessin »
# (projeté comme sur le dessin) il est déjà 0 à 3,7 mm PLUS ÉTROIT que son dessin, jamais plus large.
F_P1_DESSIN = 0.6      # station « P1 milieu » prise aux 6/10 de MCP → IPP sur le dessin : à 0,5 la corde touche la
                       # palmure dessinée de l'index et du majeur (+0,6 mm), pas le doigt

def largeurs_du_dessin():
    """largeurs (cm) de SON dessin paume au milieu du trait, aux 5 stations des tables, pour les quatre doigts"""
    peau, milieu, _ = masques_dessin()
    top = np.array([np.where(milieu[:, x])[0].min() if milieu[:, x].any() else 0 for x in range(milieu.shape[1])])
    xa = 600 + int(np.argmax(top[600:760])); ya = int(top[xa]); x_uln = int(np.where(milieu[ya])[0].min())
    sx = PAUME_L / (xa - x_uln); ds = Dessin(sx); ch = chaines_v1(); out = {}
    def corde(c, n, rmax=2.0, pas=0.0125):
        ts = np.arange(-rmax, rmax + pas / 2, pas); P = c[None, :] + ts[:, None] * n[None, :]
        ix, iy = ds.pix(P); v = ds.D[iy, ix]; i0 = len(ts) // 2
        a = b = i0
        while a > 0 and v[a - 1]: a -= 1
        while b < len(v) - 1 and v[b + 1]: b += 1
        return (b - a + 1) * pas
    perp = lambda u: np.array([-u[1], u[0]])
    for k in DOIGTS:
        p = [px2cm(q, sx) for q in ch[k]]; u = [nz(p[i + 1] - p[i]) for i in range(3)]
        st = [(p[0] + F_P1_DESSIN * (p[1] - p[0]), u[0]), (p[1], nz(u[0] + u[1])), (0.5 * (p[1] + p[2]), u[1]),
              (p[2], nz(u[1] + u[2])), (p[2] + 0.45 * (p[3] - p[2]), u[2])]
        w = [corde(c, perp(d)) for c, d in st]
        w[0] = min(w[0], w[1] + 0.05)    # auriculaire : aux 6/10 de sa P1 courte la corde prend encore la palmure (18,5
        out[k] = tuple(round(x, 4) for x in w)   # mm contre 17,2 à l'IPP) ; une P1 n'est pas plus large que sa tête
    return out

PROF_DOIGT = 0.45      # centre IPP / IPD dans l'épaisseur, depuis le dos (anatomie.md § 3 : tête de P1 de 9 mm sous
                       # ≈ 2,5 mm de peau dorsale → 7 mm sur 17,5 = 0,41, tête décalée vers la paume → 0,45)
K_PAUME = (1.10, 1.05)  # échelle radiale (x, z) des métacarpiens : paume MH 7,9 cm de large aux têtes contre 8,8–9,0
                        # (anatomie § 1) ; épaisseur 2,85 contre 3,0
K_POIGNET = (1.25, 1.15)  # poignet MH 4,74 × 3,39 cm contre 5,9–6,1 cm sur le dessin et 4,0 cm d'épaisseur (§ 1)
K_THENAR = (1.08, 1.08)   # radial autour du 1er métacarpien

def profils_mh(V, T, W, cadres, chaines_s):
    """profils de section MH le long de chaque chaîne de doigt, mesurés sur la surface LISSE (limite de Catmull-Clark,
    sinon la retaille viserait la cage et la surface finale serait 2 à 5 % trop mince — mesuré au premier essai) :
    pour chaque abscisse s (pas 1 mm), étendue latérale (x) et dorso-palmaire (z) des points de surface dont l'os
    dominant est un os libre de la chaîne"""
    P, tri, ba = echantillons(V, T, 500000, rng=3)
    Wp = (W[T[tri, 0]] * ba[:, 0:1] + W[T[tri, 1]] * ba[:, 1:2] + W[T[tri, 2]] * ba[:, 2:3])
    out = {}
    for k, osk in chaines_s.items():
        libres = [b for b in osk if not b.startswith('mc')]
        cols = [OSI[b] for b in libres]
        dom = np.argmax(Wp[:, cols], 1); m = Wp[:, cols].sum(1) > 0.6
        Pm = P[m]; dm = dom[m]; s_all = np.zeros(m.sum()); x_all = np.zeros(m.sum()); z_all = np.zeros(m.sum())
        for i, b in enumerate(libres):
            q = (Pm[dm == i] - cadres[b]['o']) @ cadres[b]['F']
            s_all[dm == i] = cadres[b]['S'] + q[:, 1]; x_all[dm == i] = q[:, 0]; z_all[dm == i] = q[:, 2]
        ss = np.arange(np.floor(s_all.min() * 10) / 10, s_all.max() + 0.05, 0.1)
        prof = np.full((len(ss), 4), np.nan)
        for i, q in enumerate(ss):
            mm = (np.abs(s_all - q) < 0.08) & (np.abs(x_all) < 1.6) & (np.abs(z_all) < 1.6)
            if mm.sum() > 25:
                prof[i] = [np.percentile(x_all[mm], 0.5), np.percentile(x_all[mm], 99.5), np.percentile(z_all[mm], 0.5), np.percentile(z_all[mm], 99.5)]
        ok = ~np.isnan(prof[:, 0]); ss, prof = ss[ok], prof[ok]
        ker = np.ones(5) / 5
        pr = np.array([np.convolve(np.pad(prof[:, c], 2, mode='edge'), ker, 'valid') for c in range(4)]).T
        out[k] = (ss, pr)
    return out

STATIONS = {'doigt': ('P1 milieu', 'IPP', 'P2 milieu', 'IPD', 'pulpe'), 'pouce': ('P1 milieu', 'P1 3/4', 'IP', 'P2 1/3', 'pulpe')}
def stations_cible(k, St):
    """abscisses (le long de la chaîne cible) des stations des tables 4.1–4.2"""
    if k == 'pouce':
        s0, L1, L2 = St[1], St[2] - St[1], St[3] - St[2]
        return np.array([s0 + 0.5 * L1, s0 + 0.8 * L1, s0 + L1, s0 + L1 + 0.35 * L2, s0 + L1 + 0.55 * L2])
    s0, L1, L2, L3 = St[1], St[2] - St[1], St[3] - St[2], St[4] - St[3]
    return np.array([s0 + 0.5 * L1, s0 + L1, s0 + L1 + 0.5 * L2, s0 + L1 + L2, s0 + L1 + L2 + 0.45 * L3])

def preparer_retaille(s1, sq, op):
    """repères MH et cibles de chaque os, abscisses de chaîne, profils MH mesurés sur la surface lisse"""
    V, F, W, jts = s1['V'], s1['F'], s1['W'], s1['jts']
    C, A, bout, L = sq['C'], sq['A'], sq['bout'], sq['L']
    fnrm = nz(np.array([np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]]) for f in F]))
    ong = sq['ongles_mh']
    cad, cib = {}, {}
    cad['poignet'] = dict(o=np.zeros(3), F=np.eye(3), S=0.0); cib['poignet'] = dict(o=np.zeros(3), F=np.eye(3), S=0.0)
    S_T, S_MH, roulis = {}, {}, {}
    for i, k in enumerate(DOIGTS):
        mhm = 'metacarpal%d.L' % (i + 1); mf = ['finger%d-%d.L' % (i + 2, q) for q in (1, 2, 3)]
        pts = [jts[mhm + '____head'], jts[mf[0] + '____head'], jts[mf[1] + '____head'], jts[mf[2] + '____head'], jts[mf[2] + '____tail']]
        # roulis du doigt MH : normale de SA plaque d'ongle (topologie hm08) → l'ongle cible regarde exactement −Z
        n_o = nz(fnrm[ong[k]].sum(0)); d3 = nz(pts[4] - pts[3]); a = nz(-n_o - (-n_o @ d3) * d3)
        zref = nz(np.array([0, 0, 1.0]) - d3 * d3[2])
        roulis[k] = math.degrees(math.atan2(np.cross(zref, a) @ d3, zref @ a))
        Smh = np.cumsum([0] + [np.linalg.norm(pts[q + 1] - pts[q]) for q in range(4)])
        tg = [C['mc%d' % (i + 2)], C[k + '_p1'], C[k + '_p2'], C[k + '_p3'], bout[k]]
        St = np.cumsum([0] + [np.linalg.norm(tg[q + 1] - tg[q]) for q in range(4)])
        S_MH[k], S_T[k] = Smh, St
        for q, b in enumerate(CHAINES[k]):
            cad[b] = dict(o=pts[q], F=repere(pts[q + 1] - pts[q], np.array([0, 0, 1.0]) if q == 0 else -n_o), S=Smh[q])
            cib[b] = dict(o=tg[q], F=repere(tg[q + 1] - tg[q], np.array([0, 0, 1.0])), S=St[q])
    # pouce : ancré à la MCP — le cube CMC de MakeHuman est 1,8 cm trop distal, dans le thénar (MC I MH = 2,64 cm contre
    # 4,76) : le 1er métacarpien MH est prolongé vers le carpe à sa longueur cible, sans étirement du thénar
    tp = [jts['finger1-2.L____head'], jts['finger1-3.L____head'], jts['finger1-3.L____tail']]
    d1 = nz(jts['finger1-1.L____tail'] - jts['finger1-1.L____head'])
    pts = [tp[0] - d1 * L['pouce'][0]] + tp
    n_o = nz(fnrm[ong['pouce']].sum(0))
    Smh = np.cumsum([0] + [np.linalg.norm(pts[q + 1] - pts[q]) for q in range(3)])
    tg = [C['mc1'], C['pouce_p1'], C['pouce_p2'], bout['pouce']]
    St = np.cumsum([0] + [np.linalg.norm(tg[q + 1] - tg[q]) for q in range(3)])
    S_MH['pouce'], S_T['pouce'] = Smh, St
    for q, b in enumerate(CHAINES['pouce']):
        cad[b] = dict(o=pts[q], F=repere(pts[q + 1] - pts[q], -n_o), S=Smh[q]); cib[b] = dict(o=tg[q], F=sq['AG'][b], S=St[q])
    S, F2 = op['S'], op['F2']; T2, _ = triangles(F2)
    prof = profils_mh(S @ V, T2, S @ W, cad, {k: CHAINES[k] for k in DOIGTS + ['pouce']})
    return dict(cad=cad, cib=cib, S_T=S_T, S_MH=S_MH, prof=prof, roulis=roulis)

def axe_chaine(R, k, s):
    """abscisse MH le long de la chaîne k → abscisse cible : linéaire par morceaux entre centres articulaires (MH →
    cible), pente 1 avant la base, pente du dernier segment au-delà du bout"""
    a, b = R['S_MH'][k], R['S_T'][k]; y = np.interp(s, a, b)
    y = np.where(s < a[0], b[0] + (s - a[0]), y)
    return np.where(s > a[-1], b[-1] + (s - a[-1]) * (b[-1] - b[-2]) / (a[-1] - a[-2]), y)

def sections(R, corr=None):
    """facteurs radiaux par station : largeur (table) / largeur MH, épaisseur (table) / épaisseur MH ; au-delà de la
    pulpe, rapport constant (la forme du bout MH, en goutte, est gardée et mise à l'échelle). `corr` : correction
    multiplicative mesurée sur la surface obtenue (une passe de rétroaction)"""
    sec = {}
    for k in DOIGTS + ['pouce']:
        ssm, pr = R['prof'][k]; sT = stations_cible(k, R['S_T'][k])
        wT, tT = np.array(LARGEUR[k]), np.array(EPAISSEUR[k])
        if corr is not None: wT = wT * corr[k][0]; tT = tT * corr[k][1]
        sp = axe_chaine(R, k, ssm)
        Wmh = pr[:, 1] - pr[:, 0]; Tmh = pr[:, 3] - pr[:, 2]
        kx = np.interp(sp, sT, wT) / Wmh; kz = np.interp(sp, sT, tT) / Tmh
        ip = min(int(np.searchsorted(sp, sT[-1])), len(ssm) - 1); kx[ip:] = kx[ip]; kz[ip:] = kz[ip]
        sec[k] = dict(s=ssm, cx=(pr[:, 0] + pr[:, 1]) / 2, cz=(pr[:, 2] + pr[:, 3]) / 2, kx=kx, kz=kz, sT=sT, tT=tT)
    return sec

def retaille_os(V, W, R, sec):
    """3a : v' = Σ_b w_b · T_b(v) ; T_b = repère MH de l'os → abscisse de chaîne cible, section mise à l'échelle par
    station, repère cible de l'os"""
    cad, cib = R['cad'], R['cib']
    def transforme(b, P):
        c, t = cad[b], cib[b]; q = (P - c['o']) @ c['F']
        if b == 'poignet': return q * np.array([K_POIGNET[0], 1.0, K_POIGNET[1]])
        k = CHAINE_DE[b]; s = c['S'] + q[:, 1]; y2 = axe_chaine(R, k, s) - t['S']
        kk = K_THENAR if k == 'pouce' else K_PAUME
        if b.startswith('mc'):
            x2, z2 = q[:, 0] * kk[0], q[:, 2] * kk[1]
        else:
            se = sec[k]
            cx = np.interp(s, se['s'], se['cx']); cz = np.interp(s, se['s'], se['cz'])
            kx = np.interp(s, se['s'], se['kx']); kz = np.interp(s, se['s'], se['kz'])
            # axe cible au centre articulaire : dos à −PROF·T, paume à (1 − PROF)·T → centre de section à (0,5 − PROF)·T
            czT = (0.5 - PROF_DOIGT) * np.interp(axe_chaine(R, k, s), se['sT'], se['tT'])
            xf, zf = (q[:, 0] - cx) * kx, (q[:, 2] - cz) * kz + czT
            # près de la MCP (premier tiers de P1), passage progressif du régime « paume » au régime « doigt »
            s_mcp = R['S_MH'][k][1]; Lp1 = R['S_MH'][k][2] - s_mcp
            be = np.clip((s - s_mcp) / (0.35 * Lp1), 0, 1); be = be * be * (3 - 2 * be)
            x2 = be * xf + (1 - be) * q[:, 0] * kk[0]; z2 = be * zf + (1 - be) * q[:, 2] * kk[1]
        return t['o'] + np.stack([x2, y2, z2], 1) @ t['F'].T
    Wc = np.where(W > 0.02, W, 0); Wc /= Wc.sum(1, keepdims=True)
    V2 = np.zeros_like(V)
    for b in OS:
        m = Wc[:, OSI[b]] > 0
        if m.any(): V2[m] += Wc[m, OSI[b]][:, None] * transforme(b, V[m])
    return V2

def mesurer_sections(Vf, T2, sq):
    """largeur et épaisseur mesurées (coupe plane ⟂ à l'os, boucle qui entoure l'axe) aux stations des tables"""
    C, A, bout = sq['C'], sq['A'], sq['bout']; out = {}
    for k in DOIGTS + ['pouce']:
        ch = CHAINES[k]
        St = np.cumsum([0] + [np.linalg.norm((C[ch[q + 1]] if q + 1 < len(ch) else bout[k]) - C[ch[q]]) for q in range(len(ch))])
        res = []
        for st in stations_cible(k, St):
            q = int(np.searchsorted(St, st, side='right') - 1); b = ch[q]
            nxt = C[ch[q + 1]] if q + 1 < len(ch) else bout[k]; u = nz(nxt - C[b]); o = C[b] + (st - St[q]) * u
            Fr = sq['AG'][b] if k == 'pouce' else repere(u, np.array([0, 0, 1.0]))
            P = coupe(Vf, T2, o, u); qq = (P - o) @ Fr
            res.append((float(np.ptp(qq[:, 0])), float(np.ptp(qq[:, 2])), float(qq[:, 2].min()), float(qq[:, 2].max())))
        out[k] = res
    return out

class Dessin:
    """le dessin paume sur une grille en cm (repère du contrat) : masque « milieu du trait », distance signée"""
    def __init__(self, sx, res=0.025, X0=-9.5, X1=11.5, Y0=-2.6, Y1=20.5):
        from scipy import ndimage
        peau, milieu, self.im = masques_dessin()
        self.res, self.X0, self.X1, self.Y0, self.Y1, self.sx = res, X0, X1, Y0, Y1, sx
        self.gw = int(round((X1 - X0) / res)); self.gh = int(round((Y1 - Y0) / res))
        gx = X0 + (np.arange(self.gw) + 0.5) * res; gy = Y1 - (np.arange(self.gh) + 0.5) * res
        PX = np.clip(np.round(DESSIN['x0'] + gx / sx).astype(int), 0, milieu.shape[1] - 1)
        PY = np.clip(np.round(DESSIN['y_pli'] - gy / SY).astype(int), 0, milieu.shape[0] - 1)
        self.D = milieu[PY[:, None], PX[None, :]]
        self.PX, self.PY = PX, PY
        self.sdf = (ndimage.distance_transform_edt(~self.D) - ndimage.distance_transform_edt(self.D)) * res   # > 0 dehors
        gy_, gx_ = np.gradient(self.sdf); self.gx, self.gy = gx_, -gy_
    def vue(self, Vp, T):
        from raster import Vue
        return Vue(Vp, T, np.eye(3), self.gw, centre=np.array([(self.X0 + self.X1) / 2, (self.Y0 + self.Y1) / 2, 0]), echelle=1 / self.res, hauteur=self.gh)
    def pix(self, P):
        return (np.clip(np.round((P[:, 0] - self.X0) / self.res - 0.5).astype(int), 0, self.gw - 1),
                np.clip(np.round((self.Y1 - P[:, 1]) / self.res - 0.5).astype(int), 0, self.gh - 1))

def iou(M, D): return float((M & D).sum() / max(1, (M | D).sum()))

LARGEUR_DESSIN = largeurs_du_dessin()
for _k in DOIGTS:
    LARGEUR[_k] = LARGEUR_DESSIN[_k]
    EPAISSEUR[_k] = tuple(round(w * e / l, 4) for w, e, l in zip(LARGEUR_DESSIN[_k], EPAISSEUR_TABLE[_k], LARGEUR_TABLE[_k]))

def optimiser_pose_dessin(Vf, T2, W2, sq, ds, pose, pas=(4, 2, 1), params=None, mode='dqs'):
    """descente par coordonnées sur quelques angles pour que la silhouette de face recouvre le mieux le dessin (IoU)"""
    params = params or [('index', 'ab'), ('majeur', 'ab'), ('annulaire', 'ab'), ('auriculaire', 'ab'),
                        ('pouce', 'rap'), ('pouce', 'av'), ('pouce', 'mcp'), ('pouce', 'ip')]
    ev = lambda p: iou(ds.vue(poser(Vf, W2, sq, p, mode), T2).masque, ds.D)
    best = ev(pose); n = 1
    for st in pas:
        for _ in range(4):
            am = False
            for k, p in params:
                for sg in (1, -1):
                    pz = json.loads(json.dumps(pose)); pz.setdefault(k, {}); pz[k][p] = round(pz[k].get(p, 0) + sg * st, 3)
                    v = ev(pz); n += 1
                    if v > best + 1e-5: best, pose, am = v, pz, True
            if not am: break
    return pose, best, n

def libre(Vb, sq):
    """part « libre » d'un sommet (doigt au-delà de la palmure, pouce au-delà de sa MCP) : 0 sur la paume, 1 sur un
    doigt — la silhouette de la paume suit le dessin, les doigts gardent leurs largeurs anatomiques"""
    C = sq['C']; lib = np.zeros(len(Vb))
    for k in DOIGTS:
        u = nz(sq['bout'][k] - C[k + '_p1']); s = (Vb - C[k + '_p1']) @ u; r = np.linalg.norm(Vb - C[k + '_p1'] - np.outer(s, u), axis=1)
        t = np.clip((s - 0.6) / 0.9, 0, 1); lib = np.maximum(lib, np.where(r < 1.4, t * t * (3 - 2 * t), 0))
    u = nz(C['pouce_p2'] - C['pouce_p1']); s = (Vb - C['pouce_p1']) @ u; r = np.linalg.norm(Vb - C['pouce_p1'] - np.outer(s, u), axis=1)
    t = np.clip((s + 0.3) / 0.8, 0, 1); lib = np.maximum(lib, np.where(r < 1.6, t * t * (3 - 2 * t), 0))
    return lib

def ajuster_silhouette(V, F, op, W2, sq, ds, pose, iters=4, lam=1.0):
    """3b : champ 2D lissé. Sommets de contour de la surface lisse posée (« dessin ») → déplacement vers le contour du
    dessin le long du gradient de la distance signée ; on résout pour les sommets GROSSIERS (moindres carrés sur
    l'opérateur de subdivision) avec un terme de lissage laplacien et les parties libres (doigts, pouce) tenues fixes."""
    import scipy.sparse as sp, scipy.sparse.linalg as spl
    from scipy import ndimage
    S = op['S']; T2, _ = triangles(op['F2'])
    nbr = voisins(F, len(V)); rows, cols, vals = [], [], []
    for i, nb in enumerate(nbr):
        rows.append(i); cols.append(i); vals.append(1.0)
        for j in nb: rows.append(i); cols.append(j); vals.append(-1.0 / len(nb))
    Lc = sp.csr_matrix((vals, (rows, cols)), shape=(len(V), len(V)))
    Vc = V.copy(); hist = []
    for it in range(iters + 1):
        Vf = S @ Vc; Vp = poser(Vf, W2, sq, pose); v = ds.vue(Vp, T2); M = v.masque
        lib = libre(Vf, sq); N = normales(Vp, T2)
        bord = M & ~ndimage.binary_erosion(M, iterations=2)
        ix, iy = ds.pix(Vp)
        # contour de la PAUME seulement : ni les doigts libres, ni la peau qui suit surtout une phalange (la base de
        # l'auriculaire, écarté de 33° dans le dessin, sinon le bord de la paume prend un épaulement au repos)
        wf = W2[:, [OSI[b] for b in OS if b.endswith(('_p1', '_p2', '_p3'))]].sum(1)
        cont = bord[iy, ix] & (np.abs(N[:, 2]) < 0.4) & (Vp[:, 1] > -2.2) & (lib < 0.05) & (wf < 0.3)
        cpoids = np.clip(1 - wf / 0.3, 0, 1)        # pondération douce (une coupure franche laissait un cran au repos)
        d = ds.sdf[iy, ix]; g = nz(np.stack([ds.gx[iy, ix], ds.gy[iy, ix]], 1))
        hist.append((int(cont.sum()), float(10 * np.abs(d[cont]).mean()), float(10 * np.abs(d[cont]).max()), iou(M, ds.D)))
        if it == iters: break
        # déplacement voulu dans la pose « dessin » → ramené au repos par la rotation mélangée du sommet (le thénar
        # tourne avec le 1er métacarpien dans cette pose)
        J4, w4 = poids4(W2); Mk = cinematique(sq, pose)
        Rv = np.einsum('nk,nkij->nij', w4, Mk[J4][:, :, :3, :3])
        d3 = np.c_[-d[:, None] * g, np.zeros(len(d))]
        delta = np.einsum('nji,nj->ni', Rv, d3)[:, :2]
        ic = np.where(cont)[0]; ifx = np.where(lib > 0.2)[0]
        Sc = sp.diags(cpoids[ic]) @ S[ic]; Sf = sp.diags(lib[ifx]) @ S[ifx]
        A = sp.vstack([Sc, Sf, lam * Lc]).tocsr()
        for c in range(2):
            b = np.r_[delta[ic, c] * cpoids[ic], np.zeros(Sf.shape[0]), np.zeros(len(V))]
            Vc[:, c] += spl.lsqr(A, b, atol=1e-10, btol=1e-10, iter_lim=5000)[0]
    return Vc, hist

def etape3(s1, sq, op):
    _etape[0] = '3'; log('### 3. Retaille aux proportions de l’utilisateur')
    from raster import Vue, vues, planche
    from PIL import Image, ImageDraw
    V, F, W = s1['V'], s1['F'], s1['W']; S = op['S']; T2, _ = triangles(op['F2']); W2 = S @ W
    R = preparer_retaille(s1, sq, op)
    log('- roulis des doigts MH (normale de la plaque d’ongle contre −Z) corrigé à la retaille : ' +
        ', '.join('%s %+.1f°' % (k, R['roulis'][k]) for k in DOIGTS))
    log('- largeurs cibles des doigts = SON dessin au milieu du trait (mm, stations P1 / IPP / P2 / IPD / pulpe ; entre '
        'parenthèses les tables 4.1 de la version précédente) : ' + ' ; '.join('%s %s (%s)' % (k, ' / '.join('%.1f' % (10 * w) for w in LARGEUR[k]),
        ' / '.join('%.1f' % (10 * w) for w in LARGEUR_TABLE[k])) for k in DOIGTS) + ' ; épaisseurs = largeur × e/l des tables 4.2')
    # 3a avec une passe de rétroaction sur les stations
    sec = sections(R); V3 = retaille_os(V, W, R, sec)
    m0 = mesurer_sections(S @ V3, T2, sq)
    corr = {}
    for k in DOIGTS + ['pouce']:
        mw = np.array([a[0] for a in m0[k]]); mt = np.array([a[1] for a in m0[k]])
        corr[k] = (np.array(LARGEUR[k]) / mw, np.array(EPAISSEUR[k]) / mt)
    sec = sections(R, corr); V3 = retaille_os(V, W, R, sec)
    m1 = mesurer_sections(S @ V3, T2, sq)
    e0 = max(abs(m0[k][i][0] - LARGEUR[k][i]) for k in m0 for i in range(5)) * 10
    e1 = max(abs(m1[k][i][0] - LARGEUR[k][i]) for k in m1 for i in range(5)) * 10
    log('- 3a : écart de largeur max aux stations après une passe %.1f mm, après rétroaction %.1f mm' % (e0, e1))
    # 3b : pose « dessin » (angles optimisés sur la silhouette) puis champ 2D sur le contour de la paume
    ds = Dessin(sq['sx']); ds_g = Dessin(sq['sx'], res=0.04)     # grille grossière pour la recherche de pose (2,5× plus rapide)
    pose0 = {'index': {'ab': 4.0}, 'annulaire': {'ab': -3.8}, 'auriculaire': {'ab': -26.8}, 'pouce': {}}  # directions
    pose, sc, n = optimiser_pose_dessin(S @ V3, T2, W2, sq, ds_g, pose0)                                  # de la chaîne v1
    log('- pose « dessin » (angles des doigts et du pouce, descente par coordonnées sur l’IoU de la silhouette de '
        'face, %d évaluations) : %s ; IoU %.4f' % (n, json.dumps(pose), sc))
    V3b, hist = ajuster_silhouette(V3, F, op, W2, sq, ds, pose)
    log('- 3b, champ 2D lissé sur le contour de la paume (milieu du trait du dessin), par itération : ' +
        ' ; '.join('%d sommets de contour, écart moyen %.2f mm, max %.2f mm, IoU %.4f' % h for h in hist))
    # « sans casser le volume » : là où le champ élargit la section (divergence > 0), l'épaisseur suit pour moitié
    nbr = voisins(F, len(V)); D = V3b - V3; div = np.zeros(len(V))
    for i, nb in enumerate(nbr):
        if len(nb) < 2: continue
        dp = V3[nb, :2] - V3[i, :2]; dd = D[nb, :2] - D[i, :2]
        G, *_ = np.linalg.lstsq(dp, dd, rcond=None); div[i] = np.trace(G)
    div = lisser(div, nbr, iters=10)
    fz = 1 + 0.5 * np.clip(div, -0.2, 0.2)
    i_mx = int(np.argmax(np.abs(div)))
    log('- divergence du champ : médiane %.3f, max |div| %.3f au sommet (%.1f, %.1f, %.1f) cm' % (np.median(div), np.abs(div).max(), *V3[i_mx]))
    V3b[:, 2] = V3b[:, 2] * fz
    log('- épaisseur suivant la divergence du champ (moitié) : facteur z %.3f..%.3f' % (fz.min(), fz.max()))
    # pose dessin réoptimisée sur la forme finale
    pose, sc, n = optimiser_pose_dessin(S @ V3b, T2, W2, sq, ds_g, pose, pas=(2, 1))
    Vp = poser(S @ V3b, W2, sq, pose); v = ds.vue(Vp, T2); M = v.masque
    # écarts : contour du maillage → contour du dessin, par zone
    from scipy import ndimage
    bord = M & ~ndimage.binary_erosion(M); yy, xx = np.nonzero(bord)
    dd = np.abs(ds.sdf[yy, xx]) * 10
    # zone de chaque pixel de bord : sommet le plus proche
    from scipy.spatial import cKDTree
    kd = cKDTree(Vp[:, :2]); P = np.stack([ds.X0 + (xx + 0.5) * ds.res, ds.Y1 - (yy + 0.5) * ds.res], 1)
    _, vi = kd.query(P); lb = libre(S @ V3b, sq)[vi]; okp = P[:, 1] > -2.2
    zone_p = okp & (lb < 0.05); zone_d = okp & (lb > 0.5)
    log('- superposition finale (pose « dessin ») : IoU %.4f ; contour de la paume (hors doigts et pouce libres) : écart '
        'moyen %.2f mm, médian %.2f, 95e centile %.2f, MAX %.2f mm ; doigts et pouce (largeurs anatomiques imposées, '
        'longueurs retenues) : moyen %.2f mm, max %.2f mm' % (iou(M, ds.D), dd[zone_p].mean(), np.median(dd[zone_p]),
        np.percentile(dd[zone_p], 95), dd[zone_p].max(), dd[zone_d].mean(), dd[zone_d].max()))
    # image : contour du dessin en rouge, maillage projeté en vert
    img = np.zeros((ds.gh, ds.gw, 3), np.uint8) + 255
    img[M] = (190, 230, 200)
    bD = ds.D & ~ndimage.binary_erosion(ds.D, iterations=2)
    bM = M & ~ndimage.binary_erosion(M, iterations=2)
    img[bM] = (0, 150, 0); img[bD] = (220, 30, 30)
    i_max = np.argmax(np.where(zone_p, dd, -1)); im1 = Image.fromarray(img); dr = ImageDraw.Draw(im1)
    dr.ellipse([xx[i_max] - 9, yy[i_max] - 9, xx[i_max] + 9, yy[i_max] + 9], outline=(0, 0, 255), width=3)
    from raster import police
    dr.text((10, 10), 'rouge : contour du dessin (milieu du trait) ; vert : maillage posé « dessin »', fill=(0, 0, 0), font=police(16))
    dr.text((10, 32), 'paume : écart max %.1f mm (cercle bleu), moyen %.2f mm ; doigts : moyen %.1f mm' % (dd[zone_p].max(), dd[zone_p].mean(), dd[zone_d].mean()), fill=(0, 0, 0), font=police(16))
    # mise en page (relecture : l'ancienne planche laissait trois cases vides) : les trois états en colonne à gauche,
    # la superposition au dessin à droite, à la même hauteur
    VW = vues(); ims, labs = [], []
    for Vx, lab in ((S @ V, 'MakeHuman brut (lisse)'), (S @ V3, '3a : retaille par les os'), (S @ V3b, '3b : + silhouette du dessin')):
        vv = Vue(Vx, T2, VW['paume'], 380, centre=np.array([1.0, 8.0, 0]), echelle=380 * 0.45 / 11.5); ims.append(vv.image()); labs.append(lab)
    pl = planche(ims, labs, cols=1, titre='Étape 3 — retaille (repos, vue paume)')
    im1 = im1.resize((int(im1.width * pl.height / im1.height), pl.height))
    out = Image.new('RGB', (pl.width + im1.width + 10, pl.height), 'white'); out.paste(pl, (0, 0)); out.paste(im1, (pl.width + 10, 0))
    out.save(os.path.join(CHECKS, 'e3_retaille.png'))
    sauver('s3', V=V3b, V3a=V3, pose=json.dumps(pose))
    return dict(V=V3b, pose_dessin=pose)

def lire_s3():
    d = charger('s3'); return dict(V=d['V'], pose_dessin=json.loads(str(d['pose'])))


# =================================================================================================================
# Étape 4 — surface : Catmull-Clark ×2 (opérateur creux, poids interpolés par le même opérateur), normales lissées,
# contrôles de forme (pincements, sections en trapèze arrondi, bouts en goutte, creux de la paume, éminences)
# =================================================================================================================
def sstep(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)

def normale_quads(V, F):
    F = np.asarray(F); return nz(np.cross(V[F[:, 2]] - V[F[:, 0]], V[F[:, 3]] - V[F[:, 1]]))

def diedres(V, F, vives=()):
    """angle (degrés) entre normales des deux faces de chaque arête intérieure (hors arêtes vives)"""
    Fn = normale_quads(V, F); E = aretes(F); out = []
    for e, l in E.items():
        if len(l) == 2 and e not in vives: out.append(np.degrees(np.arccos(np.clip(Fn[l[0]] @ Fn[l[1]], -1, 1))))
    return np.array(out)

def forme_section(Vf, T2, o, u, Fr):
    """coupe ⟂ à l'os : largeur à 25 % et 75 % de l'épaisseur depuis le dos (trapèze : dos plus étroit que la paume)"""
    P = coupe(Vf, T2, o, u); q = (P - o) @ Fr
    z0, z1 = q[:, 2].min(), q[:, 2].max(); out = []
    for f in (0.25, 0.75):
        zc = z0 + f * (z1 - z0); m = np.abs(q[:, 2] - zc) < 0.06 * (z1 - z0)
        out.append(float(np.ptp(q[m, 0])) if m.sum() > 1 else float('nan'))
    return q, out

def profil_sagittal(Vf, T2, o, u, Fr):
    """coupe par le plan (axe de l'os, Z local) : renvoie (s, z) de la boucle (s le long de l'os, z vers la paume)"""
    P = coupe(Vf, T2, o, Fr[:, 0], rmax=3.0); q = (P - o) @ Fr
    return q[:, 1], q[:, 2]

def creux_paume(Vf, T2):
    """profondeur du creux de la paume (cm) à y = 4,5 / 5,5 / 6,5 : min(crête thénar, crête hypothénar) − fond"""
    res = []
    for y in (4.5, 5.5, 6.5):
        P = coupe(Vf, T2, np.array([0, y, 0]), np.array([0, 1.0, 0]), rmax=6); pal = P[P[:, 2] > 0]
        xs = np.linspace(-3.5, 3.5, 57)
        zp = np.array([pal[np.abs(pal[:, 0] - x) < 0.12, 2].max() if (np.abs(pal[:, 0] - x) < 0.12).any() else np.nan for x in xs])
        th = np.nanmax(zp[xs > 0.8]); hy = np.nanmax(zp[xs < -1.2]); cr = np.nanmin(zp[(xs > -1.5) & (xs < 1.2)])
        res.append((y, th, hy, cr, min(th, hy) - cr))
    return res

def modeler(Vf, T2, sq, op):
    """retouches de forme sur la surface lisse, chacune mesurée :
    (a) creux de la paume ramené à ≈ 4 mm (anatomie.md § 4.3 : 3–5 mm main ouverte au repos ; la main MH, aux doigts
        à demi fléchis, a une paume en coupe de 8 à 10 mm) ;
    (b) sections des doigts en TRAPÈZE ARRONDI (anatomie.md § 5.1 : dos plat, flancs convergents vers le dos, pulpe
        bombée) : la coupe MH est un ovale (largeur à 25 % de l'épaisseur côté dos / à 75 % côté paume ≈ 0,93–0,99)."""
    C, A, bout = sq['C'], sq['A'], sq['bout']
    N = normales(Vf, T2)
    # (a) creux de la paume
    r0 = creux_paume(Vf, T2); d0 = max(r[4] for r in r0)
    # bosse gaussienne LARGE, appliquée à la moitié palmaire (poids lisse en z, sans masque de normale : un masque
    # dur dessinait un anneau dans la paume, vu au premier essai)
    x0, y0, sgx, sgy = -0.45, 5.4, 1.5, 1.9
    g_ = np.exp(-0.5 * (((Vf[:, 0] - x0) / sgx) ** 2 + ((Vf[:, 1] - y0) / sgy) ** 2))
    bosse = g_ * sstep((Vf[:, 2] + 0.3) / 1.2)
    V2 = Vf.copy(); amp = 0.0
    for it in range(4):                      # amplitude réglée sur la mesure (cible 4,5 mm au plus profond)
        amp = amp + (max(r[4] for r in creux_paume(V2, T2)) - 0.45)
        V2 = Vf.copy(); V2[:, 2] += amp * bosse
    r1 = creux_paume(V2, T2)
    log('- (a) creux de la paume : %s mm → %s mm (bosse palmaire gaussienne de %.1f mm au centre, σ %.1f × %.1f cm)' %
        (' / '.join('%.1f' % (10 * r[4]) for r in r0), ' / '.join('%.1f' % (10 * r[4]) for r in r1), 10 * amp, sgx, sgy))
    Vf = V2
    # (b) trapèze : dans le repère de chaque phalange (Z vers la paume), x' = x·(1 + τ·u) (u = −1 au dos, +1 à la
    # paume) et les épaules du dos remontées (dos plus plat), sur la partie LIBRE du doigt, nul vers le bout (la
    # goutte de P3 et l'ongle sont modelés à part)
    TAU, PHI = 0.07, 0.10
    out = Vf.copy(); avant = {}; apres = {}
    for k in DOIGTS:
        u = nz(bout[k] - C[k + '_p1']); Fr = repere(u, np.array([0, 0, 1.0])); o = C[k + '_p1']
        q = (Vf - o) @ Fr; s_ = q[:, 1]; L = np.linalg.norm(bout[k] - o)
        St = [0, np.linalg.norm(C[k + '_p2'] - o), np.linalg.norm(C[k + '_p3'] - o), L]
        se = np.array(stations_cible(k, np.r_[0, 1, np.array(St) + 1])) - 1    # stations le long du doigt
        W_ = np.interp(s_, se, LARGEUR[k]); T_ = np.interp(s_, se, EPAISSEUR[k])
        hw = W_ / 2; cz = (0.5 - PROF_DOIGT) * T_
        ra = np.sqrt((q[:, 0] / (hw * 1.15)) ** 2 + ((q[:, 2] - cz) / (T_ / 2 * 1.15)) ** 2)
        lib = sstep((s_ - 1.2) / 0.8) * (1 - sstep((s_ - (St[2] + 0.45 * (L - St[2]))) / 0.5)) * sstep((1.25 - ra) / 0.35)
        uu = np.clip((q[:, 2] - cz) / (T_ / 2), -1, 1); xn = np.clip(q[:, 0] / hw, -1, 1)
        dx = q[:, 0] * TAU * uu
        dz = -PHI * (T_ / 2) * 4 * xn ** 2 * (1 - xn ** 2) * np.clip(-uu, 0, 1)
        out += lib[:, None] * (np.outer(dx, Fr[:, 0]) + np.outer(dz, Fr[:, 2]))
    # (c) palmures : les plis vifs laissés par le rapprochement des doigts (annulaire–auriculaire surtout) sont
    # lissés localement (Taubin λ/μ, sans rétrécissement), seulement autour des arêtes à > 35°
    F2 = op['F2']; nbr = voisins(F2, len(out)); Fn = normale_quads(out, F2); E = aretes(F2)
    vif = np.zeros(len(out), bool)
    for e, l in E.items():
        if len(l) == 2 and e not in op['vives'] and Fn[l[0]] @ Fn[l[1]] < math.cos(math.radians(35)): vif[list(e)] = True
    zone = vif & (out[:, 1] > 8.5) & (out[:, 1] < 11.5) & (out[:, 2] > -0.3)   # commissures (côté paume et bord)
    for _ in range(3):
        z2 = zone.copy()
        for i in np.where(zone)[0]: z2[nbr[i]] = True
        zone = z2
    for _ in range(10):
        out = lisser(out, nbr, 1, 0.5, zone); out = lisser(out, nbr, 1, -0.53, zone)
    log('- (c) palmures : lissage de Taubin local sur %d sommets autour des plis vifs des commissures' % zone.sum())
    log('- (b) sections en trapèze arrondi sur les parties libres des doigts : τ = %.2f (flancs : dos −%d %%, paume '
        '+%d %%), épaules du dos relevées de %.0f %% de la demi-épaisseur (effet mesuré dans le tableau ci-dessous, '
        'colonne dos/paume)' % (TAU, 100 * TAU, 100 * TAU, 100 * PHI))
    return out

def etape4(s1, sq, op, s3):
    _etape[0] = '4'; log('### 4. Surface (Catmull-Clark ×2)')
    from raster import Vue, vues, planche
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from PIL import Image
    S, F2 = op['S'], op['F2']; Vf = S @ s3['V']; T2, _ = triangles(F2); C, A, bout = sq['C'], sq['A'], sq['bout']
    Vf = modeler(Vf, T2, sq, op)
    di = diedres(Vf, F2, op['vives'])
    Q = np.array(F2); e1 = np.linalg.norm(Vf[Q[:, 1]] - Vf[Q[:, 0]], axis=1); e2 = np.linalg.norm(Vf[Q[:, 2]] - Vf[Q[:, 1]], axis=1)
    log('- %d sommets, %d quads → %d triangles à l’export (contrat : 20–25 k sommets) ; arête médiane %.2f mm (min %.2f, '
        'max %.2f)' % (len(Vf), len(F2), 2 * len(F2), 10 * np.median(np.r_[e1, e2]), 10 * min(e1.min(), e2.min()), 10 * max(e1.max(), e2.max())))
    log('- pincements / plis de la surface au repos : angle entre faces voisines médian %.1f°, 99,9e centile %.1f°, '
        'max %.1f° ; arêtes > 30° : %d, > 60° : %d (hors bord vif du poignet)' % (np.median(di), np.percentile(di, 99.9), di.max(), (di > 30).sum(), (di > 60).sum()))
    # sections
    ms = mesurer_sections(Vf, T2, sq)
    log(''); log('| doigt | station | largeur (mm) | cible (doigts : SON dessin, milieu du trait ; pouce : table 4.1) | épaisseur (mm) | cible (e/l des tables 4.2) | e/l | dos/paume (largeur à 25 % / 75 % de l’épaisseur) |')
    log('|---|---|---|---|---|---|---|---|')
    secs = {}
    for k in DOIGTS + ['pouce']:
        ch = CHAINES[k]
        St = np.cumsum([0] + [np.linalg.norm((C[ch[q + 1]] if q + 1 < len(ch) else bout[k]) - C[ch[q]]) for q in range(len(ch))])
        noms = STATIONS['pouce' if k == 'pouce' else 'doigt']; secs[k] = []
        for i, st in enumerate(stations_cible(k, St)):
            q = int(np.searchsorted(St, st, side='right') - 1); b = ch[q]
            nxt = C[ch[q + 1]] if q + 1 < len(ch) else bout[k]; u = nz(nxt - C[b]); o = C[b] + (st - St[q]) * u
            Fr = sq['AG'][b] if k == 'pouce' else repere(u, np.array([0, 0, 1.0]))
            qq, (w25, w75) = forme_section(Vf, T2, o, u, Fr); secs[k].append(qq)
            w, t = ms[k][i][0], ms[k][i][1]
            log('| %s | %s | %.1f | %.1f | %.1f | %.1f | %.2f | %.2f |' % (k, noms[i], 10 * w, 10 * LARGEUR[k][i], 10 * t, 10 * EPAISSEUR[k][i], t / w, w25 / w75))
    log('')
    # bouts en goutte : profil sagittal de P3
    txt = []
    prof3 = {}
    for k in DOIGTS + ['pouce']:
        b = CHAINES[k][-1]; u = nz(bout[k] - C[b]); Fr = sq['AG'][b] if k == 'pouce' else repere(u, np.array([0, 0, 1.0]))
        sv, zv = profil_sagittal(Vf, T2, C[b], u, Fr); prof3[k] = (sv, zv)
        L3 = np.linalg.norm(bout[k] - C[b]); m = (sv > 0.25 * L3) & (sv < 0.85 * L3)
        dz = zv[m & (zv < 0)]; ds_ = sv[m & (zv < 0)]
        # dos : écart à une droite (ajustée) sur la moitié distale ; pulpe : flèche palmaire max sous l'axe
        a_, b_ = np.polyfit(ds_, dz, 1); dev = np.abs(dz - (a_ * ds_ + b_)).max()
        pz = zv[m & (zv > 0)].max(); dd = -dz.min()
        txt.append('%s : dos rectiligne à %.2f mm près, pulpe %.1f mm sous l’axe contre dos %.1f mm au-dessus (rapport %.2f), bout à %.1f mm au-delà de l’axe' %
                   (k, 10 * dev, 10 * pz, 10 * dd, pz / dd, 10 * (sv.max() - L3)))
    log('- bouts en goutte (profil sagittal de la dernière phalange) : ' + ' ; '.join(txt))
    # creux de la paume et éminences : profil palmaire z(x) à travers la paume
    T_ = T2; res = []
    for y in (4.5, 5.5, 6.5):
        P = coupe(Vf, T_, np.array([0, y, 0]), np.array([0, 1.0, 0]), rmax=6)
        pal = P[P[:, 2] > 0]
        xs = np.linspace(-3.5, 3.5, 57); zp = np.array([pal[np.abs(pal[:, 0] - x) < 0.12, 2].max() if (np.abs(pal[:, 0] - x) < 0.12).any() else np.nan for x in xs])
        th = np.nanmax(zp[xs > 0.8]); hy = np.nanmax(zp[xs < -1.2]); cr = np.nanmin(zp[(xs > -1.5) & (xs < 1.2)])
        res.append((y, th, hy, cr, min(th, hy) - cr))
    log('- creux de la paume (profil palmaire à travers la paume) : ' + ' ; '.join('y = %.1f cm : thénar z = %.2f, hypothénar %.2f, creux %.2f → profondeur %.1f mm' % (r[0], r[1], r[2], r[3], 10 * r[4]) for r in res)
        + ' (anatomie.md § 4.3 : 3–5 mm au repos)')
    yy = np.abs(Vf[:, 1] - 8.6) < 0.3
    log('- épaisseur de la paume aux têtes métacarpiennes (y ≈ 8,6 cm, x ∈ [−2 ; 1]) : %.1f mm (anatomie : 30 ± 3) ; au poignet '
        '(y = 0) : %.1f mm × %.1f mm de large (40 × 60–66)' % (10 * np.ptp(Vf[yy & (Vf[:, 0] > -2) & (Vf[:, 0] < 1), 2]),
        10 * np.ptp(Vf[np.abs(Vf[:, 1]) < 0.15, 2]), 10 * np.ptp(Vf[np.abs(Vf[:, 1]) < 0.15, 0])))
    # images
    VW = vues(); ims, labs = [], []
    for nm in ('paume', 'dos', 'profil_radial', 'profil_ulnaire', 'dessus', 'dos_34'):
        v = Vue(Vf, T2, VW[nm], 560, centre=np.array([1.0, 8.5, 0.5]), echelle=560 * 0.45 / 11.5); ims.append(v.image()); labs.append(nm)
    pl = planche(ims, labs, cols=3, titre='Étape 4 — surface lisse (Catmull-Clark ×2, %d sommets), repos' % len(Vf))
    fig, axs = plt.subplots(2, 5, figsize=(16, 6.6))
    for i, k in enumerate(DOIGTS + ['pouce']):
        ax = axs[0, i]
        for qq, c in zip(secs[k], plt.cm.viridis(np.linspace(0, 1, 5))):
            ang = np.arctan2(qq[:, 2], qq[:, 0]); o_ = np.argsort(ang); ax.plot(10 * qq[o_, 0], -10 * qq[o_, 2], '-', color=c, lw=1.4)
        ax.set_aspect('equal'); ax.set_title('%s : sections (dos en haut)' % k, fontsize=9); ax.grid(alpha=.3)
        ax = axs[1, i]; sv, zv = prof3[k]; L3_ = np.linalg.norm(bout[k] - C[CHAINES[k][-1]])
        mm = (sv > -0.4) & (sv < L3_ + 0.3) & (np.abs(zv) < 1.4)                    # la seule dernière phalange
        ax.plot(10 * sv[mm], -10 * zv[mm], '.', ms=2, color='k'); ax.axvline(0, color='r', lw=.8); ax.axvline(10 * L3_, color='r', lw=.8)
        ax.set_aspect('equal'); ax.set_title('%s : profil de P3 (dos en haut)' % k, fontsize=9); ax.grid(alpha=.3)
    fig.tight_layout(); p_ = os.path.join(WORK, 'e4_sections.png'); fig.savefig(p_, dpi=80); plt.close(fig)
    im2 = Image.open(p_)
    out = Image.new('RGB', (max(pl.width, im2.width), pl.height + im2.height), 'white'); out.paste(pl, (0, 0)); out.paste(im2, (0, pl.height))
    out.save(os.path.join(CHECKS, 'e4_surface.png'))
    sauver('s4', V=Vf)
    return dict(V=Vf)

def lire_s4(): return dict(V=charger('s4')['V'])


# =================================================================================================================
# Étape 5 — poids : repris de default_weights.mhw (interpolés par l'opérateur de subdivision), puis NETTOYÉS :
# avant-bras / main séparés au pli du poignet, partage de chaque chaîne recentré sur NOS centres articulaires,
# palmures lissées, ≤ 4 os par sommet, normalisés
# =================================================================================================================
Y_AB = (-1.2, 0.8)     # cm : zone de passage avant-bras (os « poignet ») → main (métacarpiens) ; pli du poignet en
                       # y ≈ 0 (origine) ; 2 cm de peau pour la flexion du poignet (75° : arc de ≈ 2,5 cm côté dos)
# demi-largeurs des zones de mélange entre os voisins, autour du CENTRE articulaire (cm) : ≈ 0,4–0,5 × le rayon du
# doigt aux IP (une zone plus large fait « mollir » la phalange, plus étroite plie la peau en accordéon) ; MCP plus
# large (tête du métacarpien, jointure et coussinet palmaire)
H_MELANGE = {'mcp': 0.70, 'ipp': 0.45, 'ipd': 0.35, 'mcp_pouce': 0.60, 'ip_pouce': 0.40}
# pli de la 1re commissure : voir (3b) de poids_propres — ESSAYÉ ET ÉCARTÉ (20 octobre 2026), None = éteint ; réglage
# essayé : dict(c=0.4, w=0.7, wp=1.0, y0=4.5)
COMMISSURE = None

def poids_propres(V, F2, Wmh, sq):
    C, bout = sq['C'], sq['bout']; n = len(V); W = Wmh.copy(); rap = {}
    # (1) avant-bras / main : l'os « poignet » (racine = avant-bras) ne garde que la peau en deçà du pli
    y = V[:, 1]; p = 1 - sstep((y - Y_AB[0]) / (Y_AB[1] - Y_AB[0]))
    rap['poignet_paume_avant'] = float(W[y > Y_AB[1], OSI['poignet']].max())
    Wh = W.copy(); Wh[:, OSI['poignet']] = 0; sh = Wh.sum(1)
    # secours (avant-bras pur dans MH) : métacarpien le plus proche (gaussienne de la distance à l'os)
    fb = np.zeros_like(W)
    for i in range(1, 6):
        b = 'mc%d' % i; a = C[b]; e = C['pouce_p1' if i == 1 else DOIGTS[i - 2] + '_p1']
        t = np.clip(((V - a) @ (e - a)) / ((e - a) @ (e - a)), 0, 1); d = np.linalg.norm(V - a - t[:, None] * (e - a), axis=1)
        fb[:, OSI[b]] = np.exp(-(d / 1.2) ** 2)
    fb /= fb.sum(1, keepdims=True)
    Wh = np.where(sh[:, None] > 1e-4, Wh / np.maximum(sh[:, None], 1e-12), fb)
    W = (1 - p)[:, None] * Wh; W[:, OSI['poignet']] = p
    # (1b) le 1er métacarpien ne porte que le THÉNAR : MakeHuman lui donne de la peau jusqu'au poignet et au milieu
    # de la paume (son cube CMC est 1,8 cm trop distal) ; en deçà du trapèze ou à plus de 2,4 cm de l'axe du MC I, sa
    # part passe aux autres os du sommet (ou au métacarpien le plus proche) — sinon « rapprocher » le pouce déchirait
    # la peau du poignet (sommet (1,0 ; 0,5 ; 1,7) : 0,75 de MC I, déplacé de 1,5 cm, pli en Z au rendu)
    # Rampe RADIALE LARGE (relecture adverse : la carte de poids de mc1 était un triangle à bord net, de 2,4 à 1,6 cm de
    # l'axe) : de 3,0 à 1,2 cm de l'axe. Mesuré en DQS sur la peau palmaire (changement de dièdre pose − repos, 99e
    # centile / arêtes > 30°) : opposition 29,8° / 82 → 26,1° / 70 ; rapprocher 45 + avancer 32 : 28,7° / 80 → 23,9° / 62 ;
    # poing 36,2° / 113 → 33,9° / 98 ; arc métacarpien inchangé. Écartés : rampe axiale allongée vers le poignet (−0,35)
    # — la peau du carpe suit alors le pouce, 13 à 30 arêtes de plus au poignet ; lissage laplacien des poids des
    # métacarpiens sur la paume (40 passes) — rien de mieux, l'arc seul ne plisse pas le centre de la paume (0 arête
    # du centre change de plus de 20° en opposition : le « X » vu au rendu est le relief MakeHuman de la paume)
    R_MC1 = (1.2, 3.0)
    a, e = C['mc1'], C['pouce_p1']; L1 = np.linalg.norm(e - a); u1 = (e - a) / L1
    t = (V - a) @ u1 / L1; rp = np.linalg.norm(V - a - np.outer(t * L1, u1), axis=1)
    msk = sstep((t + 0.15) / 0.35) * sstep((R_MC1[1] - rp) / (R_MC1[1] - R_MC1[0]))
    # le poids retiré va aux autres os de la MAIN, jamais à l'os « poignet » (avant-bras) : un sommet qui ne portait que
    # mc1 et l'avant-bras passait sinon à 1,0 sur l'avant-bras, entre des voisins à 0,35 (marche de poids au dos radial
    # du poignet : 5 triangles retournés dès 15° d'extension, trait sombre au rendu du repos — mesuré)
    j1 = OSI['mc1']; ret = W[:, j1] * (1 - msk); W[:, j1] *= msk
    autres = W.copy(); autres[:, j1] = 0; autres[:, OSI['poignet']] = 0; sa = autres.sum(1, keepdims=True)
    fb2 = fb.copy(); fb2[:, j1] = 0; fb2 /= fb2.sum(1, keepdims=True)
    W += ret[:, None] * np.where(sa > 1e-4, autres / np.maximum(sa, 1e-12), fb2)
    rap['mc1_retire'] = float(ret.max())
    # (1c) même règle pour les 4e et 5e métacarpiens, seuls mobiles de la paume (arc métacarpien, R11 : jusqu'à 25°) :
    # la peau en deçà de leur base (carpe, hamatum) reste au 3e métacarpien, immobile — sinon l'arc creusait une
    # fossette au bord ulnaire du poignet (vue au premier rendu Cycles du poing)
    rap['mc45_retire'] = 0.0
    for b, nxt in (('mc4', 'annulaire_p1'), ('mc5', 'auriculaire_p1')):
        a, e = C[b], C[nxt]; Lb = np.linalg.norm(e - a); ub = (e - a) / Lb
        t = (V - a) @ ub / Lb; msk = sstep((t + 0.10) / 0.30)
        jb = OSI[b]; ret = W[:, jb] * (1 - msk); W[:, jb] *= msk; W[:, OSI['mc3']] += ret
        rap['mc45_retire'] = max(rap['mc45_retire'], float(ret.max()))
    # (2) partage de chaque chaîne recentré sur les centres articulaires cibles
    def g(s, c, h): return sstep((s - c + h) / (2 * h))
    for k in DOIGTS:
        cols = [OSI[b] for b in CHAINES[k]]; om = W[:, cols].sum(1)
        u = nz(bout[k] - C[k + '_p1']); s = (V - C[k + '_p1']) @ u
        L1 = np.linalg.norm(C[k + '_p2'] - C[k + '_p1']); L2 = np.linalg.norm(C[k + '_p3'] - C[k + '_p2'])
        g1, g2, g3 = g(s, 0, H_MELANGE['mcp']), g(s, L1, H_MELANGE['ipp']), g(s, L1 + L2, H_MELANGE['ipd'])
        W[:, cols] = om[:, None] * np.stack([1 - g1, g1 - g2, g2 - g3, g3], 1)
    cols = [OSI[b] for b in CHAINES['pouce']]; om = W[:, cols].sum(1)
    u1 = nz(C['pouce_p2'] - C['pouce_p1']); u2 = nz(bout['pouce'] - C['pouce_p2'])
    g1 = g((V - C['pouce_p1']) @ u1, 0, H_MELANGE['mcp_pouce']); g2 = g((V - C['pouce_p2']) @ u2, 0, H_MELANGE['ip_pouce'])
    W[:, cols] = om[:, None] * np.stack([1 - g1, g1 * (1 - g2), g1 * g2], 1)
    # (3) palmures : là où deux chaînes de doigts se partagent la peau, lissage laplacien (8 passes) sur 2 anneaux
    nbr = voisins(F2, n)
    ch = np.stack([W[:, [OSI[b] for b in CHAINES[k] if not b.startswith('mc')]].sum(1) for k in DOIGTS + ['pouce']], 1)
    srt = np.sort(ch, 1); web = srt[:, -2] > 0.06
    for _ in range(2):
        web2 = web.copy()
        for i in np.where(web)[0]: web2[nbr[i]] = True
        web = web2
    W = lisser(W, nbr, iters=8, lam=0.5, masque=web)
    rap['palmure_sommets'] = int(web.sum())
    # (3b) PLI DE LA 1re COMMISSURE — ESSAYÉ ET ÉCARTÉ (20 octobre 2026 ; `COMMISSURE = None`). Grief « L » vu de dos : « le
    # pouce fait 40 cm de large ». Largeur perpendiculaire à P1 du pouce, vue de dos (banc d'essai sur les poids) : 39,6 mm à
    # la MCP, 27,9 au quart de P1 (photo 2361 à la même ouverture, 53° : ≈ 27 et ≈ 25 mm). Idée : contraster la part du
    # pouce dans la palmure autour de 0,4 (part' = s((part − 0,4)/w + 0,5)) pour que l'étirement se fasse sur une bande
    # étroite. Mesuré : quart de P1 27,9 → 25,2 mm (« 5 » 27,6 → 26,0), MCP 39,6 → 39,8 (inchangé) ; mais au rendu Cycles
    # (`checks/e11_commissure_avant_apres.jpg`) le bord libre de la palmure devient une DROITE de la tête de MC II au pouce
    # (le coin s'agrandit au lieu de se creuser) et un pli horizontal marque le bord radial en V. Écarté. Essayés aussi,
    # sans gain à la MCP : recette v1 côté dos (part annulée en deçà de la ligne tête de MC II → trapèze, pli XW(y)) :
    # bord radial concave 0,4 → 1,7 mm ; part de MC I renforcée dès sa base ; apex de la commissure tiré vers le pouce
    # (0,9 → MCP 45,8 mm) ou laissé à la main (0,1 → 42,0). La largeur à la MCP vient de la GÉOMÉTRIE : l'apex de la
    # commissure de SON dessin est 1,4 cm au-delà de la MCP du pouce, et une peau à poids fixes ne glisse pas le long du
    # pouce quand il s'écarte (il faudrait un correctif piloté par « rapprocher » < 0 : 9e morph, hors contrat).
    rap['commissure_sommets'], rap['commissure_dmax'] = 0, 0.0
    if COMMISSURE:
        ccols = [OSI[b] for b in CHAINES['pouce']]; th = W[:, ccols].sum(1)
        idx_ = W[:, [OSI[b] for b in CHAINES['index'][1:]]].sum(1)
        zc = sstep((V[:, 0] - 2.4) / 0.5) * sstep((V[:, 1] - COMMISSURE['y0']) / 0.6) * sstep((9.0 - V[:, 1]) / 0.6) * (idx_ < 0.3)
        # contraste plus doux côté paume (largeur w → wp de z = 0,3 à 1,1 cm) : avec 0,8 partout, l'apex PALMAIRE de la
        # commissure (4,5 ; 6,6 ; 1,3) se repliait au repos (1 triangle retourné, pouce av 25 / rap 10)
        wv = COMMISSURE['w'] + (COMMISSURE['wp'] - COMMISSURE['w']) * sstep((V[:, 2] - 0.3) / 0.8)
        th2 = th + zc * (sstep((th - COMMISSURE['c']) / wv + 0.5) - th)
        Wt = np.where(th[:, None] > 1e-4, W[:, ccols] / np.maximum(th[:, None], 1e-12), np.array([0.5, 0.5, 0.0]))
        Wo = W.copy(); Wo[:, ccols] = 0; so = Wo.sum(1, keepdims=True); fb3 = np.zeros(W.shape[1]); fb3[OSI['mc2']] = 1
        Wo = np.where(so > 1e-4, Wo / np.maximum(so, 1e-12), fb3)
        W = Wo * (1 - th2)[:, None]; W[:, ccols] = Wt * th2[:, None]
        rap['commissure_sommets'] = int((np.abs(th2 - th) > 0.02).sum()); rap['commissure_dmax'] = float(np.abs(th2 - th).max())
    # (4) ≤ 4 os, normalisés
    J = np.argsort(-W, 1)[:, :4]; w4 = np.take_along_axis(W, J, 1); w4[w4 < 1e-3] = 0; w4 /= w4.sum(1, keepdims=True)
    Wf = np.zeros_like(W); np.put_along_axis(Wf, J, w4, 1)
    rap['perte_top4_max'] = float((W - Wf).clip(0).sum(1).max())
    return Wf, rap

def etape5(s1, sq, op, s4):
    _etape[0] = '5'; log('### 5. Poids (default_weights.mhw nettoyés)')
    from raster import Vue, vues, planche
    S, F2 = op['S'], op['F2']; V = s4['V']; T2, _ = triangles(F2)
    Wmh = S @ s1['W']
    W, rap = poids_propres(V, F2, Wmh, sq)
    nb = (W > 0).sum(1)
    log('- poids MH interpolés par l’opérateur de subdivision (positifs, somme 1) : %s os par sommet (histogramme 1→%d : %s)'
        % ('1 à %d' % ((Wmh > 1e-6).sum(1).max()), (Wmh > 1e-6).sum(1).max(), np.bincount((Wmh > 1e-6).sum(1)).tolist()[1:]))
    log('- avant-bras / main : poids de l’os « poignet » sur la paume (y > %.1f cm) : %.2f dans MH → %.2f ; zone de passage '
        'y ∈ [%.1f ; %.1f] cm' % (Y_AB[1], rap['poignet_paume_avant'], W[V[:, 1] > Y_AB[1], OSI['poignet']].max(), *Y_AB))
    log('- partage des chaînes recentré sur les centres cibles (demi-largeurs de mélange : MCP %.2f, IPP %.2f, IPD %.2f, '
        'MCP du pouce %.2f, IP %.2f cm) ; palmures lissées sur %d sommets' % (H_MELANGE['mcp'], H_MELANGE['ipp'], H_MELANGE['ipd'],
        H_MELANGE['mcp_pouce'], H_MELANGE['ip_pouce'], rap['palmure_sommets']))
    log('- résultat : os par sommet %s (1, 2, 3, 4) ; somme des poids %.6f..%.6f ; poids retiré par la coupe à 4 os : max %.3f'
        % (np.bincount(nb, minlength=5)[1:].tolist(), W.sum(1).min(), W.sum(1).max(), rap['perte_top4_max']))
    log('- 1er métacarpien limité au thénar (au-delà du trapèze ; rampe radiale de 3,0 à 1,2 cm de son axe) : jusqu’à %.2f de poids '
        'rendu aux os voisins ; 4e et 5e métacarpiens limités à la paume au-delà de leur base : jusqu’à %.2f rendu au 3e'
        % (rap['mc1_retire'], rap['mc45_retire']))
    if COMMISSURE: log('- pli de la 1re commissure (part du pouce contrastée autour de %.2f, largeur %.2f côté dos → %.2f côté paume, dès y = %.1f cm) : '
        '%d sommets, part changée de %.2f au plus' % (COMMISSURE['c'], COMMISSURE['w'], COMMISSURE['wp'], COMMISSURE['y0'], rap['commissure_sommets'], rap['commissure_dmax']))
    # image : os dominant (couleur) + poids d'un os en dégradé
    rng = np.random.default_rng(5); pal = (rng.random((20, 3)) * 200 + 40).astype(float)
    pal[OSI['poignet']] = (120, 120, 120)
    col = W @ pal
    VW = vues(); ims, labs = [], []
    for nm in ('paume', 'dos', 'profil_radial'):
        v = Vue(V, T2, VW[nm], 520, centre=np.array([1.0, 8.5, 0.5]), echelle=520 * 0.45 / 11.5); ims.append(v.image(couleurs=col, ambiant=0.55)); labs.append('mélange des os — ' + nm)
    for b in ('index_p2', 'mc1', 'poignet'):
        c2 = np.outer(W[:, OSI[b]], [230, 40, 40]) + np.outer(1 - W[:, OSI[b]], [235, 235, 235])
        v = Vue(V, T2, VW['paume' if b != 'poignet' else 'dos'], 520, centre=np.array([1.0, 8.5, 0.5]), echelle=520 * 0.45 / 11.5)
        ims.append(v.image(couleurs=c2, ambiant=0.6)); labs.append('poids de %s (rouge = 1)' % b)
    planche(ims, labs, cols=3, titre='Étape 5 — poids nettoyés (≤ 4 os, normalisés)').save(os.path.join(CHECKS, 'e5_poids.png'))
    sauver('s5', W=W)
    return dict(W=W)

def lire_s5(): return dict(W=charger('s5')['W'])


# =================================================================================================================
# Étape 6 — régions (attribut _REGION) et VRAIE forme des ongles
#   0 peau, 1 plaque d'ongle, 2 frange libre, 3 repli (proximal et latéraux), 4 palmure ; attribut _ONGLE = distance
#   signée au bord de la plaque (mm, > 0 dedans), pour un trait d'ongle net à tout grossissement
# =================================================================================================================
# Ongles (anatomie.md § 7.1, Jung 2015, hommes) : rayon de courbure transversale (cm), rapport largeur/longueur
ONGLE_R = {'pouce': 1.14, 'index': 0.89, 'majeur': 0.88, 'annulaire': 0.73, 'auriculaire': 0.58}
ONGLE_WL = {'pouce': 1.04, 'index': 1.0, 'majeur': 1.0, 'annulaire': 1.0, 'auriculaire': 1.0}   # SES ongles : « presque
# aussi larges que longs (W/L ≈ 1,0) » (photo, anatomie.md § 7.1) ; Jung : 0,93–0,95 ; pouce 1,04
# largeur de la plaque / largeur du doigt à l'IPD, mesurée sur SES ongles (anatomie.md § 7.1, dernière colonne) :
# index 0,70, majeur 0,74, annulaire 0,72, auriculaire 0,70, pouce 0,70–0,75 → 0,72. (Une valeur unique de 0,73 donnait
# à l'auriculaire une plaque de 10,6 mm, soit un arc de 132° sur son rayon de 5,8 mm contre 115° chez Jung.)
ONGLE_RAPPORT = {'pouce': 0.72, 'index': 0.70, 'majeur': 0.74, 'annulaire': 0.72, 'auriculaire': 0.70}
ONGLE_RELIEF = 0.042   # cm : décalage de la plaque au-dessus de la peau de référence ; le calage du cylindre (centre
                       # pondéré ×2) et la cuticule en retirent une part, le redressement de la plaque en ajoute au bout (anatomie.md
                       # § 7 : 0,3–0,5 mm ; à 0,035 relief mesuré 0,17–0,23 mm, à 0,050 : 0,35–0,60 mm)
ONGLE_INCL = 14.0      # ° : pente maximale de la plaque par rapport à l'axe de P3 (anatomie.md § 7.2 : 10–15° vers la paume) :
                       # là où le dos du bout plonge plus vite, la plaque file droit et s'en décolle (bord libre) ; ONGLE_SUIT
                       # = part de ce redressement (1 = droite pure : bord libre décollé de 1,6 mm à l'index, trop)
ONGLE_SUIT = 0.6
ONGLE_FRANGE = 0.12    # cm : bord libre (utilisateur : 1–1,5 mm, ongles coupés court)
PENTE_HYPO = 0.70      # l'hyponychium (début du bord libre) est là où le dos de P3 plonge vers le bout à plus de 35°
                       # (pente 0,70) : mesuré sur le profil de l'index, le dos passe de 0,33 à 1,4 entre 1,83 et 2,02 cm
REPLI_L = 0.15         # cm : largeur de la bande « repli » (sillons latéraux, cuticule) autour de la plaque

def ongle_cadre(k, sq):
    C, A, bout = sq['C'], sq['A'], sq['bout']; b = CHAINES[k][-1]
    u = nz(bout[k] - C[b]); Fr = sq['AG'][b] if k == 'pouce' else repere(u, np.array([0, 0, 1.0]))
    return b, C[b], Fr, float(np.linalg.norm(bout[k] - C[b]))

def ongle_geometrie(k, sq, s_d=None):
    """paramètres de la plaque d'un doigt (repère de sa dernière phalange : x latéral, s le long, z vers la paume) ;
    s_d = abscisse du bord libre (réglée sur le profil du dos à l'étape 6)"""
    b, o, Fr, L3 = ongle_cadre(k, sq)
    w_ipd = LARGEUR[k][2] if k == 'pouce' else LARGEUR[k][3]
    W_n = ONGLE_RAPPORT[k] * w_ipd; L_n = min(W_n / ONGLE_WL[k], 0.66 * L3)
    s_d = L3 - 0.06 if s_d is None else s_d; s_p = s_d - L_n
    return dict(b=b, o=o, Fr=Fr, L3=L3, W=W_n, L=L_n, s_p=s_p, s_d=s_d, R=ONGLE_R[k], hw=W_n / 2)

def sdf_ongle(x, s, g, p=4.0):
    """distance signée approchée (cm, > 0 dedans) au contour de la plaque dans le plan (x, s) : « squircle »
    |x/a|⁴ + |s/b|⁴ = 1 (rectangle à coins arrondis, anatomie.md § 7.2), un peu plus large distalement ; LISSE (C²),
    contrairement au min() de trois distances de la version précédente, dont les coins faisaient des crans"""
    sc = 0.5 * (g['s_p'] + g['s_d']); b = 0.5 * (g['s_d'] - g['s_p'])
    t = np.clip((s - g['s_p']) / (g['s_d'] - g['s_p']), -0.5, 1.5); a = g['hw'] * (0.94 + 0.06 * t)
    X = np.abs(x) / a + 1e-9; S = np.abs(s - sc) / b + 1e-9
    Fv = (X ** p + S ** p) ** (1 / p)
    gx = Fv ** (1 - p) * X ** (p - 1) / a; gs = Fv ** (1 - p) * S ** (p - 1) / b
    return (1 - Fv) / np.maximum(np.sqrt(gx ** 2 + gs ** 2), 1.0 / np.maximum(a, b))

def etape6(s1, sq, op, s4, s5):
    """Ongles par un CHAMP DE DÉPLACEMENT LISSE. La version précédente déplaçait les sommets par morceaux (coupure
    nette à z = −1 mm sur les flancs, bande du bord exclue au-delà du bord libre, sillon de 0,2 mm de large) : 262
    arêtes à plus de 60° et 8 triangles retournés au bout des doigts (mesurés sur le maillage de l'étape 6 ; le chiffre
    « 1 arête > 60° » de l'ancien journal était celui de l'étape 4). Ici, par doigt :
      1. peau de référence = la peau de l'étape 4, le creux de la plaque MakeHuman (0,8 mm sous la peau) comblé par
         interpolation biharmonique ;
      2. plaque cible = cylindre de rayon R (Jung) sur toute la largeur, calé tranche par tranche sur la référence
         relevée de ONGLE_RELIEF : la plaque suit la convexité du dos de P3 (anatomie.md § 7.2) ;
      3. contraintes : plaque (à plus de 0,45 mm du bord), peau de l'anneau (au-delà de 1,5 mm du bord) ramenée vers
         la référence, bout du doigt et bord du domaine immobiles ; entre les deux, interpolation biharmonique (‖LΔ‖²
         minimal) : le raccord est lisse, sans pli ni triangle retourné."""
    _etape[0] = '6'; log('### 6. Régions et ongles')
    from raster import Vue, vues, planche
    S, F2 = op['S'], op['F2']; V = s4['V'].copy(); W = s5['W'].copy(); T2, _ = triangles(F2); n = len(V)
    N = normales(V, T2); nbr = voisins(F2, n); Lp = laplacien(nbr, n); mere = op['mere']
    reg = np.zeros(n); dongle = np.full(n, -3.0); tab = []; s_d_k = {}; Fa = np.array(F2); ong_mes = {}
    for k in DOIGTS + ['pouce']:
        b = CHAINES[k][-1]; bp = CHAINES[k][-2]
        _, o, Fr, L3 = ongle_cadre(k, sq); g0 = ongle_geometrie(k, sq)
        q = (V - o) @ Fr; nzl = N @ Fr[:, 2]
        wk = W[:, OSI[b]] + W[:, OSI[bp]]
        # plaque MakeHuman (topologie hm08, étape 2) + 3 anneaux (son sillon) : exclus de la référence
        mh = np.zeros(n, bool); mh[np.unique(Fa[np.isin(mere, sq['ongles_mh'][k])])] = True
        q_mh = q[mh]; mh_dim = (np.ptp(q_mh[:, 0]), np.ptp(q_mh[:, 1]))
        for _ in range(3):
            m2 = mh.copy()
            for i in np.where(mh)[0]: m2[nbr[i]] = True
            mh = m2
        zone = (wk > 0.25) & (q[:, 1] > -0.3) & (q[:, 1] < L3 + 0.6) & (nzl < 0.6)
        zr = np.where(zone, biharmonique(Lp, zone, zone & ~mh, q[:, 2]), q[:, 2])        # 1. référence
        # ligne médiane du dos (référence), lissée → bord libre à l'hyponychium (PENTE_HYPO) + la frange
        cm = zone & (np.abs(q[:, 0]) < 0.10) & (nzl < -0.2) & (q[:, 2] < 0)
        o_ = np.argsort(q[cm, 1]); sg = np.linspace(q[cm, 1].min(), q[cm, 1].max(), 120); zg = np.interp(sg, q[cm, 1][o_], zr[cm][o_])
        for _ in range(20): zg[1:-1] = 0.5 * zg[1:-1] + 0.25 * (zg[:-2] + zg[2:])
        ok = (sg > 0.6 * L3) & (np.gradient(zg, sg) > PENTE_HYPO)
        s_h = float(sg[np.argmax(ok)]) if ok.any() else L3 - 0.15
        g = ongle_geometrie(k, sq, min(s_h + ONGLE_FRANGE, L3 - 0.02)); s_p, s_d = g['s_p'], g['s_d']; s_d_k[k] = s_d
        d = sdf_ongle(q[:, 0], q[:, 1], g)
        dorsal = sstep((-nzl - 0.20) / 0.35) * (q[:, 2] < 0.15)
        # 2. plaque cible : cylindre de rayon R calé tranche par tranche (moindres carrés, centre pondéré ×2)
        R = g['R']; xx = np.clip(np.abs(q[:, 0]), 0, 0.97 * R); sag = R - np.sqrt(R * R - xx * xx)
        u_ = np.abs(q[:, 0]) / g['hw']; v_ = (q[:, 1] - 0.5 * (s_p + s_d)) / (0.5 * g['L'])
        prox = sstep((-v_ - u_) / 0.3 + 0.5)                     # 1 près du bord proximal : la cuticule recouvre
        rel = ONGLE_RELIEF * (1 - 0.6 * prox)                    # presque la plaque (relief ramené à 0,14 mm)
        dsl = (u_ < 1) & (nzl < -0.2) & (q[:, 2] < 0) & zone
        sg2 = np.linspace(s_p - 0.3, s_d + 0.1, 60); zc2 = np.full(len(sg2), np.nan)
        for i_, s_ in enumerate(sg2):
            m_ = dsl & (np.abs(q[:, 1] - s_) < 0.05)
            if m_.sum() >= 4:
                w_ = np.where(u_[m_] < 0.6, 2.0, 1.0); zc2[i_] = np.sum(w_ * (zr[m_] - rel[m_] - sag[m_])) / w_.sum()
        okz = ~np.isnan(zc2); zc2 = np.interp(sg2, sg2[okz], zc2[okz])
        for _ in range(15): zc2[1:-1] = 0.5 * zc2[1:-1] + 0.25 * (zc2[:-2] + zc2[2:])
        # plaque redressée : pente plafonnée à ONGLE_INCL depuis son tiers proximal (la plaque est rigide et droite ; le
        # dos de P3 se courbe vers le bout) — mesuré à l'index sans redressement : 18,4° (hors des 10–15°)
        s_a = s_p + 0.35 * g['L']; z_a = np.interp(s_a, sg2, zc2)
        ligne = z_a + math.tan(math.radians(ONGLE_INCL)) * (sg2 - s_a)
        zc2 = zc2 + ONGLE_SUIT * np.minimum(0, ligne - zc2) * (sg2 > s_a)
        zt = np.interp(q[:, 1], sg2, zc2) + sag
        zt -= 0.010 * sstep((q[:, 1] - (s_d - ONGLE_FRANGE)) / ONGLE_FRANGE)       # frange : relevée de 0,1 mm
        # 3. contraintes et interpolation biharmonique du déplacement (le long du Z local de P3)
        omega = (wk > 0.25) & (q[:, 1] > s_p - 0.8) & (q[:, 1] < L3 + 0.7) & (np.abs(q[:, 0]) < g['hw'] + 0.7) & (nzl < 0.55)
        coeur = omega & (d > 0.045) & (dorsal > 0.5) & (q[:, 1] < s_d - 0.02)
        anneau = omega & (d < -0.15) & (d > -0.32) & (dorsal > 0.3) & (q[:, 1] < s_d - 0.05)
        bout_ = omega & (q[:, 1] > s_d + 0.10) & (d < -0.06)
        bordo = np.zeros(n, bool)
        for i in np.where(omega)[0]:
            if (~omega[nbr[i]]).any(): bordo[i] = True
        val = np.zeros(n); val[coeur] = (zt - q[:, 2])[coeur]
        beta = sstep((d + 0.32) / 0.15); val[anneau] = (beta * (zr - q[:, 2]))[anneau]
        fixe = coeur | anneau | bout_ | bordo; val[bout_ | bordo] = 0
        dz = biharmonique(Lp, omega, fixe, val)
        V = V + np.outer(dz, Fr[:, 2])
        # régions, distance signée (mm) au bord de la plaque
        pl = (d >= 0) & (dorsal > 0.5) & omega
        fr_ = pl & (q[:, 1] > s_d - ONGLE_FRANGE - 0.10 * g['W'] * np.clip(q[:, 0] / g['hw'], -1, 1) ** 2)
        reg[pl] = REGION['plaque']; reg[fr_] = REGION['frange']
        rep = omega & (d < 0) & (d > -REPLI_L) & (dorsal > 0.5) & (q[:, 1] < s_d)
        reg[rep] = REGION['repli']
        # distance signée de l'ongle : minimum de deux champs LISSES (contour de la plaque, orientation dorsale de la peau),
        # pour que le trait d'ongle ne saute pas en escalier au bord libre là où le masque dorsal coupait (vu au rendu Cycles
        # des bouts, profil et bout)
        dorsal_l = sstep((-nzl - 0.20) / 0.35)                  # sans la coupure nette en z (elle faisait des dents)
        d_ong = np.minimum(d, 0.25 * (dorsal_l - 0.5))
        dongle[omega] = np.maximum(dongle[omega], np.clip(10 * d_ong[omega], -3, 3))
        # ongle rigide : rampe vers un poids 1 sur la dernière phalange (plaque + 1,5 mm), sans marche de poids
        r = (sstep((d + 0.30) / 0.15) * sstep((dorsal - 0.2) / 0.3) * omega)[:, None]
        oh = np.zeros_like(W); oh[:, OSI[b]] = 1; W = (1 - r) * W + r * oh
        # --- mesures sur la forme obtenue ---
        q2 = (V - o) @ Fr
        mid = pl & (np.abs(q2[:, 1] - (s_p + 0.5 * g['L'])) < 0.06)
        xa, za = q2[mid, 0], q2[mid, 2]
        cx, cz_, c0 = np.linalg.lstsq(np.c_[2 * xa, 2 * za, np.ones(mid.sum())], xa ** 2 + za ** 2, rcond=None)[0]
        Rm = math.sqrt(c0 + cx * cx + cz_ * cz_)
        cl = pl & (np.abs(q2[:, 0]) < 0.10); sl = np.polyfit(q2[cl, 1], q2[cl, 2], 1)[0]
        haut = float(np.mean(zr[pl] - q2[pl, 2]))                               # plaque au-dessus de la référence
        lat = (u_ > 0.6) & (np.abs(v_) < 0.6)
        e_in = pl & (d < 0.08) & lat
        marche = float(np.mean(zr[e_in] - q2[e_in, 2])) if e_in.any() else float('nan')   # relief au bord latéral
        a_ = pl & (np.abs(q2[:, 0]) < 0.2) & (np.abs(q2[:, 1] - (s_d - 0.05)) < 0.06)
        b_ = (np.abs(q2[:, 0]) < 0.2) & (np.abs(q2[:, 1] - (s_d - 0.05)) < 0.06) & (q2[:, 2] < 0.2)
        bord_libre = float(np.mean(zr[a_] - q2[a_, 2])) if a_.any() else float('nan')    # plaque au-dessus de la peau sous le bord libre
        w_ipd = LARGEUR[k][2] if k == 'pouce' else LARGEUR[k][3]
        tab.append((k, 10 * mh_dim[0], 10 * mh_dim[1], 10 * g['W'], g['W'] / w_ipd, 10 * g['L'], g['L'] / L3, 10 * R, 10 * Rm,
                    math.degrees(math.atan(sl)), 10 * haut, -10 * marche, 10 * bord_libre, 10 * float(np.abs(dz).max()), int(pl.sum())))
        ong_mes[k] = {'os': b, 'largeur': round(g['W'], 3), 'longueur': round(g['L'], 3), 'rayon_transversal': R, 'rayon_mesure': round(Rm, 3),
                      'inclinaison_mesuree': round(math.degrees(math.atan(sl)), 1), 'relief_mesure': round(haut, 3), 'frange': ONGLE_FRANGE,
                      'repli_proximal_s': round(s_p, 3), 'bord_libre_s': round(s_d, 3)}
    # --- palmures : peau partagée par deux rayons ---
    chf = np.stack([W[:, [OSI[b] for b in CHAINES[k] if not b.startswith('mc')]].sum(1) for k in DOIGTS], 1)
    srt = np.sort(chf, 1)
    web = (srt[:, -2] > 0.12) & (reg == 0)
    w1 = (W[:, OSI['mc1']] + W[:, OSI['pouce_p1']] > 0.2) & (W[:, OSI['mc2']] + W[:, OSI['index_p1']] > 0.2) & (V[:, 1] > 4.0) & (reg == 0)
    reg[web | w1] = REGION['palmure']
    log('- la plaque MakeHuman (topologie hm08, repérée à l’étape 2 ; EN CREUX de 0,8 mm) est remplacée par un champ de '
        'déplacement LISSE : peau de référence (creux MH comblé par interpolation biharmonique), plaque = cylindre de rayon '
        'R calé sur la référence + %.2f mm (cuticule : %.2f mm), raccord biharmonique sur 1,5 mm ; bord libre à '
        'l’hyponychium (dos qui plonge à plus de %.0f°) + %.1f mm de frange ; ongle rigide (rampe de poids vers 1,0 sur P3)'
        % (10 * ONGLE_RELIEF, 4 * ONGLE_RELIEF, math.degrees(math.atan(PENTE_HYPO)), 10 * ONGLE_FRANGE))
    log(''); log('| doigt | plaque MH l × L (mm) | largeur (mm) | / doigt à l’IPD | longueur (mm) | / P3 | R cible (mm) | R mesuré | '
                 'inclinaison de la plaque / axe de P3 (°) | relief moyen sur la peau de référence (mm) | repli latéral au-dessus du bord de la plaque (mm) | '
                 'bord libre décollé de la peau (mm) | déplacement max (mm) | sommets de plaque |')
    log('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for t in tab: log('| %s | %.1f × %.1f | %.1f | %.2f | %.1f | %.2f | %.1f | %.1f | %.1f | %.2f | %.2f | %.2f | %.2f | %d |' % t)
    log('')
    # --- dièdres et triangles retournés APRÈS les ongles, sur les triangles exportés (diagonale courte) ---
    Tc = tri_courts(V, F2); e, a = diedres_tri(V, Tc); viv = op['vives']
    hors = np.array([tuple(x) not in viv for x in e]) & (V[e[:, 0], 1] > -2.6)
    Tc4 = tri_courts(s4['V'], F2); e4, a4 = diedres_tri(s4['V'], Tc4); h4 = np.array([tuple(x) not in viv for x in e4]) & (s4['V'][e4[:, 0], 1] > -2.6)
    ret = triangles_retournes(V, Tc)
    big = e[hors & (a > 60)]
    log('- surface APRÈS les ongles (triangles exportés, diagonale la plus courte ; hors bord vif du bouchon du poignet) : '
        'arêtes > 30° : %d, > 45° : %d, > 60° : %d, > 90° : %d, max %.1f° ; triangles retournés : %d (étape 4 : > 60° : %d, '
        'max %.1f°) ; arêtes > 60° restantes : %s' % ((a[hors] > 30).sum(), (a[hors] > 45).sum(), (a[hors] > 60).sum(), (a[hors] > 90).sum(),
        a[hors].max(), len(ret), (a4[h4] > 60).sum(), a4[h4].max(), ', '.join('(%.1f, %.1f, %.1f)' % tuple(V[i]) for i in big[:, 0]) or 'aucune'))
    cnt = np.bincount(reg.astype(int), minlength=5)
    log('- régions : peau %d, plaque %d, frange %d, repli %d, palmure %d sommets' % tuple(cnt))
    # --- images : gros plans de chaque bout (dos, bout, deux profils, ¾), doigt isolé, régions puis géométrie seule ---
    pal = {0: (0, 161, 154), 1: (215, 238, 233), 2: (255, 255, 255), 3: (70, 130, 200), 4: (230, 160, 40)}
    col = np.array([pal[int(r)] for r in reg], float)
    for nom_f, couleurs, titre in (('e6_ongles.png', col, 'Étape 6 — ongles, doigt isolé (blanc : plaque et bord libre ; bleu : replis)'),
                                   ('e6_bouts_geo.png', None, 'Étape 6 — bouts des doigts, géométrie seule (%d triangle(s) retourné(s), %d arête(s) > 60° '
                                    'sur toute la main)' % (len(ret), (a[hors] > 60).sum()))):
        ims, labs = [], []
        for k in DOIGTS + ['pouce']:
            _, o, Fr, L3 = ongle_cadre(k, sq); c = o + Fr @ np.array([0, 0.62 * L3, -0.2])
            ch = CHAINES[k]; wk = W[:, OSI[ch[-1]]] + W[:, OSI[ch[-2]]]; Tk = Tc[(wk[Tc] > 0.5).all(1)]
            X_, S_, Z_ = Fr[:, 0], Fr[:, 1], Fr[:, 2]
            def Rv(ey, ez):
                ey = nz(ey - (ey @ ez) * ez); return np.stack([np.cross(ey, ez), ey, ez])
            for nom, R_ in (('dos', Rv(S_, -Z_)), ('bout', Rv(-Z_, S_)), ('profil +x', Rv(-Z_, X_)), ('profil −x', Rv(-Z_, -X_)), ('¾ dos', Rv(S_, nz(-Z_ + 0.8 * X_)))):
                v = Vue(V, Tk, R_, 300, centre=c, echelle=300 / 2.5)
                ims.append(v.image(couleurs=couleurs, couleur=(150, 200, 196), lumiere=(0.3, 0.5, 1.0))); labs.append('%s — %s' % (k, nom))
        planche(ims, labs, cols=5, titre=titre).save(os.path.join(CHECKS, nom_f))
    VW = vues(); ims = []
    for nm in ('paume', 'dos', 'dessus'):
        v = Vue(V, T2, VW[nm], 520, centre=np.array([1.0, 8.5, 0.5]), echelle=520 * 0.45 / 11.5); ims.append(v.image(couleurs=col))
    planche(ims, ['régions — paume', 'régions — dos', 'régions — dessus'], cols=3).save(os.path.join(CHECKS, 'e6_regions.png'))
    sauver('s6', V=V, W=W, reg=reg, dongle=dongle, s_d=json.dumps(s_d_k), ongles=json.dumps(ong_mes))
    return dict(V=V, W=W, reg=reg, dongle=dongle, s_d=s_d_k, ongles=ong_mes)

def lire_s6():
    d = charger('s6'); return dict(V=d['V'], W=d['W'], reg=d['reg'], dongle=d['dongle'], s_d=json.loads(str(d['s_d'])),
                                   ongles=json.loads(str(d['ongles'])) if 'ongles' in d else {})


# =================================================================================================================
# Étape 7 — courbes de plis (barycentriques sur les triangles). Doigts : pli digital proximal à mi-P1, moyen 2–3 mm
# avant l'IPP (anatomie.md § 5.8) ; pli DISTAL par la règle de SA photo 2354 (index : pli IPP → pli IPD 418 px, pli IPD
# → bout 410 px, rapport 0,98 ; CLAUDE.md piste P) : le pli distal est à mi-chemin du pli moyen et du bout, soit 3 à
# 4 mm avant l'IPD (0,8 mm à l'auriculaire, dont P3 est aussi long que P2) — les « 7–8 mm » d'anatomie.md (Clin Orthop
# 1993) donnaient un rapport 1,47 contre 0,98 sur sa main, l'erreur déjà corrigée en v1 ; « = » dorsaux sur l'IPP et
# l'IPD ; paume, poignet et pouce : SES plis, relevés sur le dessin paume (milieu du trait) et projetés sur la
# main posée « dessin » (le pli se retrouve ensuite sur la main au repos par ses coordonnées barycentriques)
# =================================================================================================================
# plis relevés sur references/paume.jpg (px), dans le sens où on les lit ; relevé à l'œil sur l'image squelettisée
# (checks/e7_plis.png les montre superposés au dessin)
PLIS_DESSIN = {
    'paume_distal':   ([(318, 537), (360, 523), (405, 509), (455, 485), (500, 455), (530, 425), (548, 402)], 'flex(annulaire_p1, auriculaire_p1)'),
    'paume_proximal': ([(640, 452), (600, 470), (560, 491), (520, 516), (480, 545), (440, 578), (412, 604), (390, 624)], 'flex(index_p1, majeur_p1)'),
    'paume_thenar':   ([(628, 462), (598, 480), (568, 506), (545, 545), (527, 595), (518, 650), (520, 705), (531, 752)], 'rap(mc1), av(mc1)'),
    'pouce_base_1':   ([(615, 490), (640, 503), (660, 515), (676, 525)], 'rap(mc1), flex(pouce_p1)'),
    'pouce_base_2':   ([(606, 546), (630, 534), (655, 528), (680, 526)], 'rap(mc1), flex(pouce_p1)'),
    'pouce_mcp':      ([(706, 514), (718, 532), (730, 548), (740, 560)], 'flex(pouce_p1)'),
    'pouce_ip_1':     ([(747, 456), (762, 466), (778, 477)], 'flex(pouce_p2)'),
    'pouce_ip_2':     ([(752, 475), (767, 485), (790, 496)], 'flex(pouce_p2)'),
    'poignet_distal': ([(376, 788), (410, 794), (445, 796), (480, 787), (515, 778), (560, 773), (600, 772), (640, 770)], 'flex(poignet)'),
    'poignet_proximal': ([(390, 816), (425, 821), (460, 822), (495, 812), (540, 804), (575, 799), (600, 795)], 'flex(poignet)'),
}

def localiser(V, T, P, kd=None, cent=None):
    """triangle et coordonnées barycentriques du point de la surface le plus proche de chaque point P"""
    from scipy.spatial import cKDTree
    if kd is None: cent = V[T].mean(1); kd = cKDTree(cent)
    _, cand = kd.query(P, k=16)
    out_t = np.zeros(len(P), int); out_b = np.zeros((len(P), 3)); best = np.full(len(P), np.inf)
    for j in range(cand.shape[1]):
        t = cand[:, j]; a, b, c = V[T[t, 0]], V[T[t, 1]], V[T[t, 2]]
        n = np.cross(b - a, c - a); nn = np.linalg.norm(n, axis=1, keepdims=True); n = n / np.maximum(nn, 1e-12)
        p = P - ((P - a) * n).sum(1, keepdims=True) * n
        v0, v1, v2 = b - a, c - a, p - a
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01; den = np.where(np.abs(den) < 1e-18, 1e-18, den)
        bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den; bu = 1 - bv - bw
        B = np.clip(np.stack([bu, bv, bw], 1), 0, None); B /= B.sum(1, keepdims=True)
        q = B[:, 0:1] * a + B[:, 1:2] * b + B[:, 2:3] * c; d = np.linalg.norm(q - P, axis=1)
        m = d < best; best[m] = d[m]; out_t[m] = t[m]; out_b[m] = B[m]
    return out_t, out_b, best

def arc_section(V, T, o, u, Fr, cote, demi_angle, pas=0.05):
    """arc de la section ⟂ à l'os (centre o, axe u) du côté 'dos' ou 'paume', ±demi_angle autour du milieu, ordonné"""
    P = coupe(V, T, o, u)
    if len(P) == 0: return np.zeros((0, 3))
    q = (P - o) @ Fr; zc = 0.5 * (q[:, 2].min() + q[:, 2].max())
    ang = np.degrees(np.arctan2(q[:, 0], (zc - q[:, 2]) if cote == 'dos' else (q[:, 2] - zc)))
    m = np.abs(ang) <= demi_angle; P, ang = P[m], ang[m]
    o_ = np.argsort(ang); P = P[o_]
    # rééchantillonnage régulier
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if d[-1] < 2 * pas: return P
    t = np.arange(0, d[-1] + 1e-9, pas)
    return np.stack([np.interp(t, d, P[:, c]) for c in range(3)], 1)

def etape7(s1, sq, op, s3, s6):
    _etape[0] = '7'; log('### 7. Plis')
    from raster import Vue, vues, planche
    from PIL import Image, ImageDraw
    from scipy.spatial import cKDTree
    S, F2 = op['S'], op['F2']; V = s6['V']; W = s6['W']; C, A, bout = sq['C'], sq['A'], sq['bout']
    T2 = tri_courts(V, F2)       # les triangles EXPORTÉS : les plis tombent exactement sur la surface du GLB
    cent = V[T2].mean(1); kd = cKDTree(cent)
    plis = []
    def ajouter(nom, typ, P, visible, groupe=None, regle=None):
        t, b, d = localiser(V, T2, P, kd, cent)
        plis.append(dict(nom=nom, type=typ, groupe=groupe or nom, visible=visible, regle=regle, P=P, t=t, b=b, err=float(d.max())))
    # --- doigts : plis palmaires et « = » dorsaux, positions anatomiques ---
    for k in DOIGTS:
        o1, o2, o3 = C[k + '_p1'], C[k + '_p2'], C[k + '_p3']; u = nz(bout[k] - o1); Fr = repere(u, np.array([0, 0, 1.0]))
        L1 = np.linalg.norm(o2 - o1); L2 = np.linalg.norm(o3 - o2)
        defs = [('digital_proximal', o1 + u * 0.5 * L1, 'paume', 60, 'flex(%s_p1)' % k, 'pli palmaire à mi-P1'),
                ('moyen_a', o2 - u * 0.30, 'paume', 62, 'flex(%s_p2)' % k, 'pli moyen, 3 mm avant l’IPP'),
                ('moyen_b', o2 - u * 0.17, 'paume', 58, 'flex(%s_p2)' % k, 'second pli moyen, 1,7 mm avant l’IPP'),
                ('distal', o1 + u * 0.5 * ((L1 - 0.30) + np.linalg.norm(bout[k] - o1)), 'paume', 55, 'flex(%s_p3)' % k,
                 'pli distal : règle de sa photo 2354, pli IPD → bout = pli IPP → pli IPD')]
        for nm, o, cote, da, vis, regle in defs:
            ajouter('%s_%s' % (k, nm), 'pli', arc_section(V, T2, o, u, Fr, cote, da), vis, '%s_%s' % (k, nm.split('_')[0]), regle)
        for art, oc, os_ in (('ipp', o2, k + '_p2'), ('ipd', o3, k + '_p3')):
            for lettre, off, da in (('a', -0.10, 48), ('b', 0.08, 44)):
                ajouter('%s_%s_dos_%s' % (art, k, lettre), '=', arc_section(V, T2, oc + u * off, u, Fr, 'dos', da),
                        'ext(%s)' % os_, '%s_%s_dos' % (art, k), '« = » dorsal sur l’%s, effacé par la flexion' % art.upper())
    # pouce : « = » dorsal sur l'IP
    o3 = C['pouce_p2']; u = nz(bout['pouce'] - o3); Fr = sq['AG']['pouce_p2']
    for lettre, off, da in (('a', -0.10, 48), ('b', 0.08, 44)):
        ajouter('ip_pouce_dos_%s' % lettre, '=', arc_section(V, T2, o3 + u * off, u, Fr, 'dos', da), 'ext(pouce_p2)', 'ip_pouce_dos')
    # --- paume, pouce, poignet : relevés sur le dessin, projetés sur la main posée « dessin » (vue paume, +Z) ---
    pose = s3['pose_dessin']; Vp = poser(V, W, sq, pose)
    ordre = np.argsort(-Vp[T2].mean(1)[:, 2])
    from matplotlib.path import Path as MPath
    tri2 = Vp[T2][:, :, :2]; zt = Vp[T2].mean(1)[:, 2]
    kd2 = cKDTree(tri2.mean(1))
    sx = sq['sx']
    for nom, (pts, vis) in PLIS_DESSIN.items():
        pts = np.array(pts, float); xy = np.stack([(pts[:, 0] - DESSIN['x0']) * sx, (DESSIN['y_pli'] - pts[:, 1]) * SY], 1)
        d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]; tt = np.arange(0, d[-1] + 1e-9, 0.05)
        xy = np.stack([np.interp(tt, d, xy[:, 0]), np.interp(tt, d, xy[:, 1])], 1)
        P3 = []
        for p in xy:
            _, cand = kd2.query(p, k=40)
            best = None
            for t in cand:
                a, b, c = tri2[t]
                den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(den) < 1e-14: continue
                l0 = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / den
                l1 = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / den; l2 = 1 - l0 - l1
                if min(l0, l1, l2) >= -1e-6:
                    z = l0 * Vp[T2[t, 0], 2] + l1 * Vp[T2[t, 1], 2] + l2 * Vp[T2[t, 2], 2]
                    if best is None or z > best[0]: best = (z, t, np.array([l0, l1, l2]))
            if best is not None:
                _, t, bb = best; P3.append(bb @ V[T2[t]])        # même triangle, mêmes barycentriques, AU REPOS
        if len(P3) >= 2: ajouter(nom, 'pli', np.array(P3), vis, nom.rsplit('_', 1)[0] if nom[-1].isdigit() else nom, 'relevé sur son dessin')
    # --- bilan ---
    log('- %d courbes de plis (%d points), points à %.3f mm au plus de la surface : %s' % (len(plis), sum(len(p['P']) for p in plis),
        10 * max(p['err'] for p in plis), ', '.join('%s (%d)' % (p['nom'], len(p['P'])) for p in plis if not p['nom'].startswith(('ipp_', 'ipd_')))))
    # contrôles de position (anatomiques) : pli → centre articulaire le long de l'os
    txt = []
    for k in DOIGTS:
        u = nz(bout[k] - C[k + '_p1'])
        f = lambda nm: float(np.mean((next(p for p in plis if p['nom'] == '%s_%s' % (k, nm))['P'] - C[k + '_p1']) @ u))
        L1 = np.linalg.norm(C[k + '_p2'] - C[k + '_p1']); L12 = L1 + np.linalg.norm(C[k + '_p3'] - C[k + '_p2'])
        Lt = float(np.linalg.norm(bout[k] - C[k + '_p1']))
        txt.append('%s : proximal à %.2f de P1, moyen %.1f mm avant l’IPP, distal %.1f mm avant l’IPD (pli IPD → bout / pli IPP → pli IPD = %.2f ; sa photo 0,98)'
                   % (k, f('digital_proximal') / L1, 10 * (L1 - f('moyen_a')), 10 * (L12 - f('distal')), (Lt - f('distal')) / (f('distal') - f('moyen_a'))))
    log('- positions mesurées sur la surface : ' + ' ; '.join(txt))
    # image : plis sur la main au repos (paume, dos) et sur le dessin
    VW = vues(); ims = []
    for nm in ('paume', 'dos'):
        v = Vue(V, T2, VW[nm], 640, centre=np.array([1.0, 8.5, 0.5]), echelle=640 * 0.45 / 11.5); img = v.image(couleur=(150, 205, 200)); dr = ImageDraw.Draw(img)
        for p in plis:
            vis_ = (p['P'] - V[T2[p['t']]].mean(1)) @ VW[nm][2] > -1   # tous ; la profondeur est testée ci-dessous
            q = v.proj(p['P']); zq = p['P'] @ VW[nm][2]
            ix = np.clip(q[:, 0].astype(int), 0, 639); iy = np.clip(q[:, 1].astype(int), 0, 639)
            ok = zq >= v.zbuf[iy, ix] - 0.05
            col = (200, 30, 30) if p['type'] == 'pli' else (30, 30, 200)
            for i in range(len(q) - 1):
                if ok[i] and ok[i + 1]: dr.line([tuple(q[i]), tuple(q[i + 1])], fill=col, width=2)
        ims.append(img)
    # sur le dessin
    im = Image.open(os.path.join(RACINE, 'references', 'paume.jpg')).convert('RGB'); dr = ImageDraw.Draw(im)
    for nom, (pts, vis) in PLIS_DESSIN.items():
        dr.line([tuple(p) for p in pts], fill=(220, 0, 0), width=3)
    im = im.resize((int(im.width * 640 / im.height), 640)); ims.append(im)
    planche(ims, ['plis au repos — paume (rouge : palmaires, bleu : « = » dorsaux)', 'plis au repos — dos', 'relevé sur son dessin (rouge)'],
            cols=3, titre='Étape 7 — courbes de plis').save(os.path.join(CHECKS, 'e7_plis.png'))
    sauver('s7', plis=json.dumps([dict(nom=p['nom'], type=p['type'], groupe=p['groupe'], visible=p['visible'], regle=p['regle'],
                                       P=p['P'].tolist()) for p in plis]))
    return dict(plis=plis)

def lire_s7():
    d = charger('s7'); pl = json.loads(str(d['plis']))
    for p in pl: p['P'] = np.array(p['P'])
    return dict(plis=pl)


# =================================================================================================================
# Étape 8 — butées (mobilite.md § 5.1.2, actif / passif), couplages, poses « repos », « dessin », poses de contrôle
# =================================================================================================================
def butees():
    B = {}
    abd = {'index': (-12, 30), 'majeur': (-18, 18), 'annulaire': (-22, 15), 'auriculaire': (-45, 15)}
    for k in DOIGTS:
        fl = (-30, 100) if k == 'auriculaire' else (-25, 95)
        B[k + '_p1'] = {'flex': list(fl), 'flex_passif': [-45, 110], 'abd': list(abd[k]),
                        'abd_passif': [abd[k][0] - 8, abd[k][1] + 8], 'rot': [0, 0], 'rot_passif': [-15, 15]}
        B[k + '_p2'] = {'flex': [0, 110], 'flex_passif': [-10, 120]}
        B[k + '_p3'] = {'flex': [-20, 85], 'flex_passif': [-30, 95]}
    B['mc1'] = {'av': [0, 55], 'av_passif': [-5, 60], 'rap': [-30, 45], 'rap_passif': [-35, 50]}
    B['pouce_p1'] = {'flex': [-20, 65], 'flex_passif': [-40, 90], 'abd': [-5, 15], 'abd_passif': [-25, 25]}
    B['pouce_p2'] = {'flex': [-25, 85], 'flex_passif': [-45, 95]}
    B['poignet'] = {'flex': [-70, 75], 'flex_passif': [-85, 90], 'dev': [-35, 20], 'dev_passif': [-45, 25],
                    'prono': [-80, 80], 'prono_passif': [-90, 90]}
    B['mc4'] = {'arc': [0, 1], 'note': 'flexion = 12°·arc'}; B['mc5'] = {'arc': [0, 1], 'note': 'flexion = 25°·arc, supination = 20°·arc'}
    return B

COUPLAGES = {
    'abduction_flexion': 'ab_max(θ) = ab_max(0) · max(0,1 ; 1 − 0,9·θ/90), θ = flexion de la MCP (mobilite.md R2)',
    'ipd_ipp': 'IPD ≤ 25 + 0,65·IPP et IPD ≥ 0,45·(IPP − 55) ; doigt relâché : IPD ≈ 0,65·IPP (R4) ; '
               'relâché à IPD ≤ 60 + 0,65·IPP seulement par contact (appui)',
    'ipd_seule': 'IPD fléchie avec IPP tendue : ≤ 40–60° (ligament de Landsmeer, R5)',
    'asservissement': 'écart de flexion des MCP voisines : index–majeur 90°, majeur–annulaire 85°, annulaire–auriculaire 75° '
                      '(v1 ENSLAVE) — PRÉFÉRENCE, jamais bloquant (R7)',
    'marionnette': 'doigt tiré par le bout : MCP : IPP : IPD = 0,85 : 1 : 0,7 (v1 GRAB, R14)',
    'pouce_mcp': 'MCP du pouce ≤ 30 + 0,8·av + 0,4·rap : PRÉFÉRENCE (R10), pas une butée',
    'pouce_vis': 'trapézo-métacarpienne : rapprocher fait sortir le pouce du plan, av ≥ 0,7·max(0, rap) (v1 AVC 0,7), axes inclinés TFT 20°, '
                 'TAT 15°, FEV 15°, pronation couplée à l’opposition (PRONA 34°) — modèle v1 validé (R8), à garder',
    'arc': 'arc = max(flexion MCP auriculaire / 90, opposition du pouce) par défaut (R11)',
    'convergence': 'axes de flexion obliques (R1), rotation autour de l’os : MCP (X des P1) index −3°, majeur 0, annulaire '
                   '+1,5°, auriculaire +10° (dont 6,8° compensent la supination de mc5 par l’arc) → P1 repliées à 90° quasi '
                   'parallèles (−3 / 0 / +3 / +3,2° avec arc 0,6) ; IPP et IPD (X des P2 et P3) −4 / 0 / +4 / +8° → les '
                   'P2–P3 convergent vers la base du thénar (bouts du poing à 0,88 de l’écart des MCP)',
}

CONVENTION_POSE = {
    'unites': 'degrés',
    'doigts': 'P1 : R = Rz(−ab) · Rx(mcp) · Ry(rot) dans le repère de liaison de l’os (ab > 0 : vers le pouce, +X ; '
              'mcp > 0 : flexion vers la paume, autour de l’axe X OBLIQUE ; rot > 0 : autour de Y) ; P2 : Rx(pip) ; P3 : Rx(dip) (X des P2 et P3 obliques aussi : voir couplages.convergence)',
    'pouce': 'mc1 : R = Rx(rap) · Rz(−av) (rap > 0 : vers l’index, flexion-adduction, axe X ≈ normale à la paume ; '
             'av > 0 : abduction palmaire, le pouce sort vers +Z) ; pouce_p1 : Rx(mcp) · Rz(−abdMcp) ; pouce_p2 : Rx(ip). '
             'Z local du pouce = pulpe des AXES (pronation de repos 75°, reprise de MakeHuman ; la PEAU de P1–P2 est tournée de −18° autour de l’os : pulpe visible à 57°, axes de la MCP et de l’IP obliques de 18° par rapport à l’ongle) : le moteur ajoute la pronation couplée',
    'poignet': 'l’os « poignet » (racine) porte l’avant-bras : flexion (flex > 0 : vers la paume, autour de X) et '
               'inclinaison (dev > 0 : radiale, vers le pouce, autour de −Z) font tourner mc1–mc5 autour de l’origine ; '
               'prono (autour de Y) fait tourner toute la main avec l’avant-bras',
    'arc': 'mc4 : Rx(12·arc) ; mc5 : Rx(25·arc) · Ry(−20·arc)',
    'skinning': 'matrice de skinning = monde posé · liaison⁻¹ ; quaternions duaux recommandés (contrôles faits en LBS et DQS)',
}

def doigt(m, p, d, a=0.0): return {'mcp': m, 'pip': p, 'dip': d, 'ab': a}
POSE_REPOS = {'poignet': {'flex': -15, 'dev': 0}, 'prono': 0, 'arc': 0.1,
              'pouce': {'av': 30, 'rap': 10, 'mcp': 10, 'ip': 10, 'abdMcp': 0},
              'index': doigt(21, 27, 13), 'majeur': doigt(24, 29, 14), 'annulaire': doigt(26, 31, 16), 'auriculaire': doigt(29, 33, 17)}
# Poses de contrôle RÉGLÉES (relecture adverse : l'ancien poing s'interpénétrait de 4,5 à 5,9 mm, le pouce allait jusqu'à
# l'annulaire et laissait un tunnel de 195 mm² vu de profil ; l'ancien V : pouce dans l'annulaire de 5,9 à 7,9 mm).
# Réglées par `python3 build_hand.py --regler-poses` (descente par coordonnées, DQS) : pénétration doigt/doigt,
# pouce/doigts et bouts/paume ≤ CONTACT_MOU (mobilite.md § 5 P2.1 : enfoncement de chair admis 1,5–3 mm), bouts posés sur
# la paume, pouce couché EN TRAVERS de la face dorsale des P2 (poing : index et majeur, photo 2357 ; V : annulaire et
# auriculaire, photo 2359), dans les butées actives, R2 (abduction ≤ 10 % de sa course à 90° de flexion), couplage IPD–IPP
# et vis sans fin du pouce (av ≥ 0,7·rap) ; aucune rotation axiale (R6 : ≈ 0 en flexion).
POSES_CONTROLE = {
    'poing': {'pouce': {'rap': 20.0, 'av': 24.35, 'mcp': 40.75, 'ip': 38.25, 'abdMcp': -5.0},
              'index': {'mcp': 95.0, 'pip': 105.25, 'dip': 72.5, 'ab': -1.2}, 'majeur': {'mcp': 84.0, 'pip': 102.0, 'dip': 66.5, 'ab': 1.8},
              'annulaire': {'mcp': 84.25, 'pip': 104.0, 'dip': 65.0, 'ab': -2.2}, 'auriculaire': {'mcp': 90.0, 'pip': 100.0, 'dip': 63.5, 'ab': 0.0},
              'arc': 0.6},
    'V': {'pouce': {'rap': 40.75, 'av': 28.525, 'mcp': 43.75, 'ip': 28.5, 'abdMcp': -5.0}, 'index': doigt(0, 0, 0, 12), 'majeur': doigt(0, 0, 0, -12),
          'annulaire': {'mcp': 91.75, 'pip': 106.0, 'dip': 51.5, 'ab': -2.2}, 'auriculaire': {'mcp': 88.0, 'pip': 104.0, 'dip': 58.25, 'ab': -5.4},
          'arc': 0.6},
}
# 20 octobre 2026 (largeurs de SON dessin, obliquité passée des MCP aux IP) : ces angles sont GARDÉS. `--regler-poses`
# relancé sur la nouvelle main tombait sur des poses moins naturelles (poing : IPP du majeur à 90°, sa butée basse de
# réglage, IP du pouce à 63° ; tunnel vu de profil 111 mm²) ; les angles validés donnent sur la nouvelle main : poing
# 2,5 mm de pénétration (bout de l'index sur la paume), tunnel 74 mm² ; V 3,2 mm avec arc 0,4 → arc 0,6 (celui que le
# moteur prend dès que l'auriculaire est replié : ARC_AUTO 0,6 × 88/90) : 2,4 mm (annulaire_bout/paume).
# « L » (grief du 20 octobre 2026), dans la convention de CE fichier (ab par rapport à la liaison) : pouce en abduction
# radiale à angle droit (moteur : TH(0, −28, 0, 0), mobilite.md 4.2), trois doigts repliés comme le PLI du moteur
POSE_L = {'pouce': {'av': 0, 'rap': -28, 'mcp': 0, 'ip': 0}, 'index': doigt(0, 0, 0), 'majeur': doigt(90, 105, 70),
          'annulaire': doigt(90, 105, 70), 'auriculaire': doigt(90, 105, 70), 'arc': 0.6}
POSES_CONTROLE_AVANT = {     # pour la comparaison du journal (version livrée avant la relecture)
    'poing': {'pouce': {'rap': 38, 'av': 22, 'mcp': 40, 'ip': 45}, 'index': doigt(90, 100, 65), 'majeur': doigt(90, 102, 65),
              'annulaire': doigt(90, 104, 65), 'auriculaire': doigt(90, 106, 65), 'arc': 0.6},
    'V': {'pouce': {'rap': 40, 'av': 18, 'mcp': 40, 'ip': 30}, 'index': doigt(0, 0, 0, 12), 'majeur': doigt(0, 0, 0, -12),
          'annulaire': doigt(88, 100, 62), 'auriculaire': doigt(88, 104, 62), 'arc': 0.4},
}
# poses d'essai du pouce (relecture adverse) : « rapprocher » à fond AVEC sa vis sans fin (av = 0,7 × 45), et l'opposition
# vers l'auriculaire avec l'arc métacarpien complet ; « rapprocher 45 / avancer 0 » est hors couplage (le pouce entre dans
# le 2e métacarpien) : mesuré pour mémoire seulement
POSES_ESSAI = {'rapprocher': {'pouce': {'rap': 45, 'av': 31.5}},
               'opposition': {'pouce': {'av': 50, 'rap': 45, 'mcp': 30, 'ip': 30}, 'auriculaire': doigt(60, 60, 30), 'arc': 1},
               'arc': {'arc': 1}, 'rapprocher_sans_vis': {'pouce': {'rap': 45, 'av': 0}}}
CONTACT_MOU = 0.25     # cm : plafond d'enfoncement de chair entre deux doigts, doigt et pouce, bout et paume (P2.1 : 1,5–3 mm)

# --- contacts : pénétration entre parties de la main posée ---
def groupes_contact(W):
    """sommets portés à plus de 85 % par les phalanges d'un doigt (ou du pouce), à plus de 90 % par les métacarpiens II–V
    (paume) : la peau commune (palmures, base des doigts) n'appartient à aucun groupe — elle n'est pas un contact"""
    w = lambda bs: W[:, [OSI[b] for b in bs]].sum(1); g = {}
    for k in DOIGTS:
        g[k] = np.where(w([k + '_p1', k + '_p2', k + '_p3']) > 0.85)[0]; g[k + '_bout'] = np.where(w([k + '_p2', k + '_p3']) > 0.85)[0]
    g['pouce'] = np.where(w(['pouce_p1', 'pouce_p2']) > 0.85)[0]; g['paume'] = np.where(w(['mc2', 'mc3', 'mc4', 'mc5']) > 0.9)[0]
    return g
PAIRES_CONTACT = [('index', 'majeur'), ('majeur', 'annulaire'), ('annulaire', 'auriculaire'), ('index', 'annulaire'), ('majeur', 'auriculaire'),
                  ('pouce', 'index'), ('pouce', 'majeur'), ('pouce', 'annulaire'), ('pouce', 'auriculaire'),
                  ('index_bout', 'paume'), ('majeur_bout', 'paume'), ('annulaire_bout', 'paume'), ('auriculaire_bout', 'paume'), ('pouce', 'paume')]

def penetration(Vp, T, g, paires=PAIRES_CONTACT, rapide=False):
    """profondeur max (cm) de chaque paire, dans les deux sens : sommet de A sous la surface de B (point le plus proche
    sur ses triangles, normale lissée de B), normales opposées, écart orienté le long de la normale (−s > 0,7·distance :
    un sommet vraiment DEDANS, pas un voisin de côté). rapide = sommet le plus proche au lieu du triangle (réglage)"""
    from scipy.spatial import cKDTree
    N = normales(Vp, T); out = {}
    for A, B in paires:
        best = 0.0
        for X, Y in ((g[A], g[B]), (g[B], g[A])):
            if len(X) == 0 or len(Y) == 0: continue
            P = Vp[X]
            if rapide:
                dd, j = cKDTree(Vp[Y]).query(P); nn = N[Y[j]]; s = ((P - Vp[Y[j]]) * nn).sum(1)
                ins = (s < 0) & (dd < 0.6) & ((N[X] * nn).sum(1) < 0) & (-s > 0.7 * dd)
                if ins.any(): best = max(best, float((-s[ins]).max()))
                continue
            tb = T[np.isin(T, Y).all(1)]
            _, jj = cKDTree(Vp[tb].mean(1)).query(P, k=6); dep = np.zeros(len(X))
            for c in range(jj.shape[1]):
                t = tb[jj[:, c]]; a, b_, cc = Vp[t[:, 0]], Vp[t[:, 1]], Vp[t[:, 2]]
                n = nz(np.cross(b_ - a, cc - a)); q = P - ((P - a) * n).sum(1, keepdims=True) * n
                v0, v1, v2 = b_ - a, cc - a, q - a
                d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
                den = np.where(np.abs(d00 * d11 - d01 ** 2) < 1e-18, 1e-18, d00 * d11 - d01 ** 2)
                bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den
                B3 = np.clip(np.stack([1 - bv - bw, bv, bw], 1), 0, None); B3 /= B3.sum(1, keepdims=True)
                qq = B3[:, :1] * a + B3[:, 1:2] * b_ + B3[:, 2:3] * cc
                nn = B3[:, :1] * N[t[:, 0]] + B3[:, 1:2] * N[t[:, 1]] + B3[:, 2:3] * N[t[:, 2]]
                s = ((P - qq) * nn).sum(1); dist = np.linalg.norm(P - qq, axis=1)
                ins = (s < 0) & (dist < 0.8) & ((N[X] * nn).sum(1) < 0.2) & (-s > 0.7 * dist)
                dep = np.maximum(dep, np.where(ins, -s, 0))
            best = max(best, float(dep.max()))
        out[(A, B)] = best
    return out

def tunnel_profil(Vp, T, M, sq, res=0.02):
    """jour du poing vu de profil côté pouce (caméra orthographique en +X) : aire (mm²) du plus grand creux où le premier
    point vu est derrière la face ULNAIRE de l'index posé (on voit à travers la boucle de l'index) et qui est ENTOURÉ de
    surface proche ; renvoie aussi ses dimensions (mm)"""
    from raster import Vue, vues
    from scipy import ndimage
    R = vues()['profil_radial']; v = Vue(Vp, T, R, int(16.0 / res), centre=Vp.mean(0), echelle=1 / res)
    b = 'index_p2'; c = (M[OSI[b]] @ np.r_[0.5 * (sq['C'][b] + sq['C']['index_p3']), 1])[:3]
    x_uln = c[0] - 0.5 * LARGEUR['index'][2]
    proche = v.masque & (np.where(v.masque, v.zbuf, np.inf) >= x_uln - 0.05)
    creux = ndimage.binary_fill_holes(proche) & ~proche; lab, n = ndimage.label(creux)
    if n == 0: return 0.0, (0.0, 0.0)
    aires = ndimage.sum(creux, lab, range(1, n + 1)) * (10 * res) ** 2; i = int(np.argmax(aires)); ys, xs = np.nonzero(lab == i + 1)
    return float(aires[i]), (10 * res * float(np.ptp(xs)), 10 * res * float(np.ptp(ys)))

# --- morph targets correctifs des jointures ---
# Grief de l'utilisateur (« l'articulation n'est pas harmonieuse ») et relecture adverse : en flexion, la jointure ne
# saillait pas (rayon dorsal sur la bissectrice, index MCP à 90° : repos 9,6 mm, DQS 9,5, LBS 6,9) et la peau dorsale des
# MCP se froissait. Une vraie jointure sort de 4 à 5 mm (CLAUDE.md piste X ; v1 KNK : 0,22 × demi-largeur × 1,45 à la MCP,
# × 1,05 à l'IPP). Pour chaque MCP (90°) et IPP (100°) : pose DQS de cette seule articulation, puis dans la pose
# (a) dôme dorsal centré sur la bissectrice (gaussienne angulaire σφ, plateau latéral), amplitude calée pour que le rayon
#     sur la bissectrice dépasse celui du repos de SAILLIE ;
# (b) côté paume, coussinets de part et d'autre du pli (gaussienne σ 40° autour de la bissectrice palmaire), plafonnés
#     au plan bissecteur du pli (ils s'y rejoignent sans se traverser) : la chair comprimée remplit les coins de la boucle
#     du doigt (le « tunnel » du poing, défaut 0 de la v1) ; le pli lui-même reste marqué (−0,6 mm, σ 10°) ;
# (c) lissage de Taubin de la zone du dôme (rides de la peau dorsale, vues en LBS comme en DQS) ;
# le tout ramené au repos par la rotation DQS de chaque sommet (Δ_repos = Rᵀ·Δ_pose). Le moteur applique Σ wᵢ·Δᵢ AVANT le
# skinning, wᵢ = clamp(θ / θref, 0, 1).
# Coussinets (mesuré sur le poing réglé, DQS, cavité vue de profil côté pouce / arêtes devenues > 60° / triangles
# retournés) : sans coussinet 125 mm² / 475 / 21 ; MCP 3,0 mm 99 / 504 / 22 ; 4,5 mm 83 / 509 / 22 ; 6,0 mm 67 / 512 / 22.
# Le jour est dans le COIN DE LA MCP (paume sous la tête métacarpienne / face palmaire de P1) : c'est là que la chair
# doit le remplir. Coussinets de 4 mm NON plafonnés au plan du pli : 77 mm² mais 1 373 arêtes / 240 triangles retournés
# (la peau se recoupe) — d'où le plafond. Saillie dorsale : v1 KNK ≈ 3,2 mm à la MCP ; ici 4,0 (CLAUDE.md : 4–5 mm).
# Forme du dôme (mesurée sur le haut de la silhouette du poing vu de dos, hauteur des bosses sur les vallées / largeur à
# mi-hauteur) : DQS seul 3,5 / 12 mm (index) ; dôme gaussien étroit (σφ 38°, σ latéral 0,5 × demi-largeur, 4 mm) 6,3 / 12,
# 5,7 / 9, 3,8 / 6 mm : des PICS ; dôme en plateau (plein sur ± 0,6 demi-largeur, rampe 1,0 ; σφ 60°) à 3,5 mm : 6,5 / 14,
# 5,4 / 12, 3,4 / 8,5 mm — des têtes arrondies, larges comme la tête d'un métacarpien (13 mm d'os + la chair). Saillie
# retenue 3,5 mm à la MCP (v1 : 3,2 ; CLAUDE.md : 4–5 ; à 4 mm les têtes redevenaient pointues), 2,5 mm à l'IPP.
CORRECTIFS = {'mcp': dict(ref=90.0, saillie=0.35, sig_phi=60.0, plateau=(0.6, 1.0), coussin=0.60, os='_p1', elargit=0.12),
              'pip': dict(ref=100.0, saillie=0.25, sig_phi=60.0, plateau=(0.6, 1.0), coussin=0.25, os='_p2')}

def rayon_rayon(Vp, T, c, dirn, cand):
    """distance de c à la peau le long de dirn (premier triangle touché parmi cand, Möller–Trumbore)"""
    tt = T[cand]; a, b, cc = Vp[tt[:, 0]], Vp[tt[:, 1]], Vp[tt[:, 2]]
    e1, e2 = b - a, cc - a; pv = np.cross(dirn, e2); det = (e1 * pv).sum(1); ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0); tv = c - a; u = (tv * pv).sum(1) * inv
    qv = np.cross(tv, e1); v = (qv @ dirn) * inv; t = (e2 * qv).sum(1) * inv
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
    return float(t[hit].min()) if hit.any() else float('nan')

def correctif_jointure(V, W, sq, T, nbr, k, ang, A_dos, cfg):
    b = k + cfg['os']; J4, w4 = poids4(W); M = cinematique(sq, {k: {ang: cfg['ref']}})
    Vp, Rv = dqs_rt(V, J4, w4, M)
    par = PARENT[b]; C, A = sq['C'], sq['A']; c = (M[OSI[b]] @ np.r_[C[b], 1])[:3]
    Ap = M[OSI[par]][:3, :3] @ A[par]; Ad = M[OSI[b]][:3, :3] @ A[b]
    X = nz(Ap[:, 0] + Ad[:, 0]); nd = nz(-Ap[:, 2] - Ad[:, 2])
    r = Vp - c; lat = r @ X; rp = r - np.outer(lat, X); rad = np.linalg.norm(rp, axis=1); ur = rp / np.maximum(rad[:, None], 1e-9)
    phi = np.degrees(np.arccos(np.clip(ur @ nd, -1, 1)))
    wch = W[:, [OSI[x] for x in CHAINES[k]]].sum(1); hw = 0.5 * (LARGEUR[k][0] if ang == 'mcp' else LARGEUR[k][1])
    # décroissance LISSE en distance à l'axe et en latéral (une coupure nette à 2 cm laissait un pli sur P2, vu au rendu)
    # côté paume, la peau est plus loin du centre (MCP : 18–19 mm, centre à 38 % de l'épaisseur depuis le dos) : fenêtre
    # radiale propre, sinon les coussinets de la MCP s'éteignaient avant d'atteindre la peau (tunnel inchangé, mesuré)
    r_out, w_r = (2.1, 0.7) if ang == 'mcp' else (1.6, 0.6)
    rp_out, wp_r = (3.0, 0.9) if ang == 'mcp' else (2.0, 0.6)
    base = sstep((wch - 0.5) / 0.4) * sstep((2.2 * hw - np.abs(lat)) / (0.6 * hw))
    porte = base * sstep((r_out - rad) / w_r); porte_p = base * sstep((rp_out - rad) / wp_r)
    # profil LATÉRAL en plateau : la tête du métacarpien est aussi large que le doigt, son dessus est arrondi ; une
    # gaussienne latérale étroite faisait une CRÊTE le long du doigt (pics sur la silhouette du poing vu de dos, au rendu)
    if cfg.get('plateau'):
        a_, b_ = cfg['plateau'][0] * hw, cfg['plateau'][1] * hw; g_lat = sstep((a_ + b_ - np.abs(lat)) / b_)
    else: g_lat = np.exp(-0.5 * (lat / (cfg['kx'] * hw)) ** 2)
    g_d = np.exp(-0.5 * (phi / cfg['sig_phi']) ** 2) * g_lat * porte
    lat_p = np.exp(-0.5 * (lat / (0.7 * hw)) ** 2) * porte_p
    g_p = np.exp(-0.5 * ((180 - phi) / 40.0) ** 2) * lat_p; g_c = np.exp(-0.5 * ((180 - phi) / 10.0) ** 2) * lat_p
    D = (A_dos * g_d + cfg['coussin'] * g_p - 0.06 * g_c)[:, None] * ur
    if cfg.get('elargit'):
        # chair des flancs de P1 chassée sur les côtés par la flexion (v1 piste X, `KNL`, validé par l'utilisateur) : avec SES
        # largeurs (dessin, plus minces que les tables) et des axes de flexion presque droits (LEAN réduit, 20 octobre 2026),
        # deux P1 voisines repliées à 90° gardaient 2,4 à 3,8 mm d'air (index–majeur) et 1,5 à 3,0 (majeur–annulaire) entre
        # leurs flancs ; le poing se lit alors comme des tuyaux séparés. Le flanc de P1 s'élargit de `elargit` cm de chaque
        # côté, sur toute la longueur de P1 et jusqu'à l'IPP (plateau le long de l'os), nul sur le dos et la pulpe.
        Y1 = Ad[:, 1]; X1 = Ad[:, 0]; L1 = float(np.linalg.norm(C[CHAINES[k][2]] - C[b]))
        s1 = r @ Y1; l1 = r @ X1; z1 = r @ Ad[:, 2]
        # flancs côté dos et à mi-épaisseur seulement, à partir de 3,5 mm de la MCP : sur la face palmaire de la base de
        # P1 (pli digito-palmaire, qui se referme en flexion) l'élargissement faisait 12 arêtes vives au repos sur
        # l'auriculaire (mesuré : repos DQS + correctifs 15 arêtes > 60° contre 3)
        g_s = sstep((s1 - 0.35) / 0.5) * sstep((L1 + 0.5 - s1) / 0.5)
        g_z = np.where(z1 < 0, np.exp(-0.5 * (z1 / (0.9 * hw)) ** 2), np.exp(-0.5 * (z1 / (0.4 * hw)) ** 2))
        g_f = sstep((np.abs(l1) - 0.25 * hw) / (0.55 * hw)) * sstep((2.0 * hw - np.abs(l1)) / (0.6 * hw)) * g_z
        D = D + (cfg['elargit'] * g_s * g_f * np.sign(l1) * sstep((wch - 0.5) / 0.4))[:, None] * X1[None, :]
    # les deux coussinets se RENCONTRENT au plan bissecteur palmaire du pli sans le traverser (sinon la peau se
    # recoupe : 240 triangles retournés dans le poing avec des coussinets de 4 mm non plafonnés, mesuré) : chaque sommet
    # palmaire reste à 0,3 mm au moins de son côté du plan (axe de la jointure, bissectrice)
    mpl = nz(np.cross(X, nd)); cote = np.sign(r @ mpl); cote[cote == 0] = 1
    pal = (g_p > 0.02) & ((ur @ nd) < 0)
    dist0 = cote * (r @ mpl); dd_ = cote * (D @ mpl)
    f = np.where(pal & (dd_ < 0), np.clip((dist0 - 0.03) / np.maximum(-dd_, 1e-9), 0, 1), 1.0)
    D = D * f[:, None]
    Vt = Vp + D; zone = g_d > 0.05; Vs = Vt.copy()
    for _ in range(8): Vs = lisser(Vs, nbr, 1, 0.5, zone); Vs = lisser(Vs, nbr, 1, -0.53, zone)
    D = D + (Vs - Vt) * np.clip(g_d / 0.3, 0, 1)[:, None]
    cand = np.where(np.linalg.norm(V[T].mean(1) - C[b], axis=1) < 2.5)[0]; candp = np.where(np.linalg.norm(Vp[T].mean(1) - c, axis=1) < 2.5)[0]
    m = dict(r_repos=rayon_rayon(V, T, C[b], -A[par][:, 2], cand), r_dqs=rayon_rayon(Vp, T, c, nd, candp), r_corr=rayon_rayon(Vp + D, T, c, nd, candp),
             r_lbs=rayon_rayon(lbs(V, J4, w4, M), T, c, nd, candp), dmax=float(np.linalg.norm(D, axis=1).max()))
    return np.einsum('nji,nj->ni', Rv, D), m

def correctifs(V, W, sq, T, nbr):
    """les 8 morph targets des jointures (MCP et IPP des quatre doigts, amplitude du dôme calée en 3 passes sur la saillie
    voulue) et le 9e, la palmure de la 1re commissure (`commissure_abd`)"""
    out, mes = {}, {}
    for ang, cfg in CORRECTIFS.items():
        for k in DOIGTS:
            A_ = cfg['saillie']
            for _ in range(3):
                Db, m = correctif_jointure(V, W, sq, T, nbr, k, ang, A_, cfg)
                A_ = float(np.clip(A_ * cfg['saillie'] / max(m['r_corr'] - m['r_repos'], 0.05), 0.1, 0.9))
            out['%s_%s' % (ang, k)] = Db.astype(np.float32); m['A'] = A_; mes['%s_%s' % (ang, k)] = m
    if COMMISSURE_ABD:
        out[COMMISSURE_ABD['nom']], mes[COMMISSURE_ABD['nom']] = correctif_commissure(V, W, sq, T, nbr)
    return out, mes

# --- 9e correctif : la PALMURE de la 1re commissure quand le pouce s'écarte (20 octobre 2026, feu vert de l'orchestrateur) ---
# « L » vu de dos : 39,6 mm de silhouette à la MCP du pouce (perpendiculaire à P1) contre ≈ 27 sur sa photo 2361 à la même
# ouverture. L'apex de la commissure de SON dessin est 1,4 cm au-delà de la MCP ; quand le pouce s'écarte, la vraie peau
# de la palmure glisse vers la MCP, une peau à poids fixes ne glisse pas (cinq familles de poids essayées, voir l'étape 5).
# Correctif calculé DANS la pose « L » (pouce seul, rap = ref) : la peau de la palmure (part du pouce entre 0 et 1, autour
# de l'apex, faces dorsale ET palmaire) est ramenée vers la MCP du pouce, dans le plan de la paume, d'`amplitude` à
# l'apex (gaussienne σ autour de lui), puis lissée (Taubin) et ramenée au repos par Rᵀ. Poids moteur : clamp(rap / ref,
# 0, 1) avec ref < 0, soit clamp(−rap / 28, 0, 1) : 0 pour tout pouce ramené (rap ≥ 0 : repos, dessin, V, Quatre, B,
# poing, O, pinces…), 1 dans « L » (rap −28, mobilite.md 4.2), 0,43 dans « Main ouverte (5) » (rap −12).
# Pilote : « rapprocher » < 0 (abduction RADIALE, dans le plan de la paume), pas « avancer » : sur ses photos 2354 et 2361
# le pouce est écarté DANS le plan (palmure tendue) ; « avancer » est aussi grand pouce replié (V : av 35, B : av 20), où
# la palmure est relâchée — le correctif y serait faux.
# Réglage (banc d'essai sur la main livrée, « L » de dos, largeur perpendiculaire à P1 du pouce à la MCP / au quart de
# P1, replis dans la commissure) : sans correctif 39,6 / 27,9 mm. Protection par la PART du pouce (peau à part ≥ 0,97
# immobile) : 1,0 cm → 31,7 / 24,5 ; 1,2 → 29,8 / 22,4, mais un CROCHET au bord libre là où la palmure rejoint le pouce
# (la peau du pouce immobile, la palmure voisine tirée de 1,2 cm) — rampe de part plus douce, champ lissé (20, 40
# passes) : le crochet reste. Protection par la DISTANCE à l'axe du pouce posé (0 à moins de 0,9 cm, plein à 1,8 cm) et
# champ lissé : bord libre en V arrondi qui rejoint le pouce sans crochet ; amplitude 1,4 cm (σ 1,2, 10 passes) → 29,6 /
# 21,4 mm, mais 31,6 mm dans le MOTEUR (sa cinématique du pouce, TOFF et pronation couplée, élargit de 2 mm : 41,2 sans
# correctif) ; 1,6 → 28,4 ; **1,7 (σ 1,3, 12 passes) → 27,5 / 19,5 mm** (moteur : voir JOURNAL) ; (1,5 avec la rampe
# 1,1–2,2 : 3 arêtes vives ; 1,3 / 1,0–2,0 : angle encore visible). 0 arête > 60° et 0 triangle retourné dans la
# commissure en L, en 5 et au repos.
COMMISSURE_ABD = dict(nom='commissure_abd', angle='pouce.rap', ref=-28.0, amplitude=1.7, sigma=1.3, axe=(0.9, 1.8), lisse=12)

def correctif_commissure(V, W, sq, T, nbr, cfg=None):
    cfg = cfg or COMMISSURE_ABD
    J4, w4 = poids4(W); M = cinematique(sq, {'pouce': {'rap': cfg['ref'], 'av': 0}})
    Vp, Rv = dqs_rt(V, J4, w4, M)
    th = W[:, [OSI[b] for b in CHAINES['pouce']]].sum(1)
    ap = px2cm(sq['commissure'], sq['sx'])
    sel = (np.hypot(V[:, 0] - ap[0], V[:, 1] - ap[1]) < 0.6) & (th > 0.25) & (th < 0.75)
    apex = Vp[sel].mean(0); c = (M[OSI['pouce_p1']] @ np.r_[sq['C']['pouce_p1'], 1])[:3]
    d = c - apex; d[2] = 0; dist = float(np.linalg.norm(d)); d /= dist
    g = np.exp(-0.5 * (np.linalg.norm(Vp - apex, axis=1) / cfg['sigma']) ** 2)
    g *= sstep((cfg.get('haut', 0.97) - th) / cfg.get('garde', 0.2)) * sstep((th - 0.03) / 0.15)
    if cfg.get('axe'):        # protection par la distance à l'axe du pouce posé (MC I distal → bout) au lieu de la part du pouce
        a_ = (M[OSI['mc1']] @ np.r_[sq['C']['mc1'] + 0.4 * (sq['C']['pouce_p1'] - sq['C']['mc1']), 1])[:3]
        b_ = (M[OSI['pouce_p2']] @ np.r_[sq['bout']['pouce'], 1])[:3]; ab = b_ - a_
        tt = np.clip((Vp - a_) @ ab / (ab @ ab), 0, 1); r_ = np.linalg.norm(Vp - a_ - np.outer(tt, ab), axis=1)
        R0, R1 = cfg['axe']; g = np.exp(-0.5 * (np.linalg.norm(Vp - apex, axis=1) / cfg['sigma']) ** 2) * sstep((r_ - R0) / (R1 - R0)) * sstep((th - 0.03) / 0.15)
    if cfg.get('lisse'): g = lisser(g[:, None], nbr, iters=cfg['lisse'], lam=0.5)[:, 0]   # champ du poids lissé sur la peau (pas de crochet au bord libre)
    D = (cfg['amplitude'] * g)[:, None] * d[None, :]
    zone = g > 0.02; Vt = Vp + D; Vs = Vt.copy()
    for _ in range(6): Vs = lisser(Vs, nbr, 1, 0.5, zone); Vs = lisser(Vs, nbr, 1, -0.53, zone)
    D = D + (Vs - Vt) * np.clip(g / 0.3, 0, 1)[:, None]
    mes = dict(apex_mcp_cm=dist, sommets=int((np.linalg.norm(D, axis=1) > 1e-4).sum()), dmax=float(np.linalg.norm(D, axis=1).max()))
    return np.einsum('nji,nj->ni', Rv, D).astype(np.float32), mes

def poids_correctif(nom, pose):
    """poids moteur d'un correctif : clamp(valeur / ref, 0, 1) (ref < 0 pour la commissure : rap négatif)"""
    if nom == COMMISSURE_ABD['nom']:
        k, ch = COMMISSURE_ABD['angle'].split('.'); return float(np.clip(((pose.get(k, {}) or {}).get(ch, 0) or 0) / COMMISSURE_ABD['ref'], 0, 1))
    ang, k = nom.split('_'); return float(np.clip(((pose.get(k, {}) or {}).get(ang, 0) or 0) / CORRECTIFS[ang]['ref'], 0, 1))

def deplacement_correctifs(cor, pose):
    """Σ wᵢ·Δᵢ (espace de liaison) pour une pose : wᵢ = clamp(θ / θref, 0, 1)"""
    D = 0
    for ang, cfg in CORRECTIFS.items():
        for k in DOIGTS:
            D = D + float(np.clip((pose.get(k, {}) or {}).get(ang, 0) / cfg['ref'], 0, 1)) * cor['%s_%s' % (ang, k)]
    if COMMISSURE_ABD['nom'] in cor: D = D + poids_correctif(COMMISSURE_ABD['nom'], pose) * cor[COMMISSURE_ABD['nom']]
    return D

def poser_v2(V, W, sq, pose, cor=None, mode='dqs'):
    """pose comme le moteur M2 : correctifs (espace de liaison) puis skinning"""
    return poser(V + (deplacement_correctifs(cor, pose) if cor is not None else 0), W, sq, pose, mode)

# --- réglage des poses de contrôle (option --regler-poses) ---
def _contraindre(p):
    ABD = {'index': (-12, 30), 'majeur': (-18, 18), 'annulaire': (-22, 15), 'auriculaire': (-45, 15)}
    for k in DOIGTS:                                     # R2 : l'abduction se ferme avec la flexion de la MCP
        d = p.get(k)
        if d:
            f = max(0.1, 1 - 0.9 * d.get('mcp', 0) / 90); d['ab'] = float(np.clip(d.get('ab', 0), ABD[k][0] * f, ABD[k][1] * f))
    t = p.get('pouce')
    if t is not None: t['av'] = max(t.get('av', 0), 0.7 * max(0, t.get('rap', 0)))      # vis sans fin (v1 AVC)
    for k in DOIGTS:
        d = p.get(k)
        if d: d['dip'] = float(np.clip(d.get('dip', 0), 0.45 * (d.get('pip', 0) - 55), 25 + 0.65 * d.get('pip', 0)))
    return p

def _cout_pose(V, W, sq, T, g, p, cible, cor=None):
    Vp = poser_v2(V, W, sq, p, cor); pen = penetration(Vp, T, g, rapide=True); M = cinematique(sq, p)
    c = sum(400 * max(0, v - 0.20) ** 2 + 5 * v ** 2 for v in pen.values())
    from scipy.spatial import cKDTree
    kd = cKDTree(Vp[g['paume']])
    for k in cible['bouts_paume']:
        tip = (M[OSI[CHAINES[k][-1]]] @ np.r_[sq['bout'][k], 1])[:3]; c += 30 * max(0, kd.query(tip)[0] - 0.65) ** 2
    d1, d2 = cible['pouce_sur']
    def axe(b, f):
        ch = CHAINES[CHAINE_DE[b]]; i = ch.index(b); nxt = sq['C'][ch[i + 1]] if i + 1 < len(ch) else sq['bout'][CHAINE_DE[b]]
        R = M[OSI[b]]; return (R @ np.r_[sq['C'][b] + f * (nxt - sq['C'][b]), 1])[:3], R[:3, :3] @ sq['A'][b]
    pa, Ra = axe(d1 + '_p2', 0.5); pb, Rb = axe(d2 + '_p2', 0.55)
    Ta = pa - Ra[:, 2] * (0.5 * EPAISSEUR[d1][2] + 0.85); Tb = pb - Rb[:, 2] * (0.5 * EPAISSEUR[d2][2] + 0.80)
    ip, _ = axe('pouce_p2', 0.0); tp = (M[OSI['pouce_p2']] @ np.r_[sq['bout']['pouce'], 1])[:3]
    c += 20 * (np.sum((tp - Tb) ** 2) + 0.5 * np.sum((ip - Ta) ** 2))
    for k, dd in cible['ref'].items():
        if isinstance(dd, dict):
            for q, v in dd.items(): c += 0.002 * (p.get(k, {}).get(q, 0) - v) ** 2
    return c

def regler_poses(V, W, sq, T, cor=None):
    import copy
    ABD = {'index': (-12, 30), 'majeur': (-18, 18), 'annulaire': (-22, 15), 'auriculaire': (-45, 15)}
    g = groupes_contact(W); res = {}
    for nom, p0 in POSES_CONTROLE_AVANT.items():
        plies = DOIGTS if nom == 'poing' else ['annulaire', 'auriculaire']
        cible = dict(bouts_paume=plies, pouce_sur=('index', 'majeur') if nom == 'poing' else ('annulaire', 'auriculaire'), ref=p0)
        params = [('pouce', 'av', 0, 55), ('pouce', 'rap', -30, 45), ('pouce', 'mcp', -20, 65), ('pouce', 'ip', -25, 85), ('pouce', 'abdMcp', -5, 15)]
        for k in plies:
            f = max(0.1, 1 - 0.9 * p0[k]['mcp'] / 90)
            params += [(k, 'ab', ABD[k][0] * f, ABD[k][1] * f), (k, 'pip', 90, 110), (k, 'dip', 50, 80), (k, 'mcp', 82, 95)]
        p = _contraindre(copy.deepcopy(p0)); best = _cout_pose(V, W, sq, T, g, p, cible, cor)
        for st in (6, 3, 1.5, 0.75):
            for _ in range(3):
                am = False
                for k, q, lo, hi in params:
                    for sg in (1, -1):
                        pz = copy.deepcopy(p); v = float(np.clip(pz[k].get(q, 0) + sg * st, lo, hi))
                        if v == pz[k].get(q, 0): continue
                        pz[k][q] = v; pz = _contraindre(pz); c = _cout_pose(V, W, sq, T, g, pz, cible, cor)
                        if c < best - 1e-6: best, p, am = c, pz, True
                if not am: break
        res[nom] = p; print(nom, json.dumps(p))
    return res

def etape8(s1, sq, op, s3, s6, regler=False):
    _etape[0] = '8'; log('### 8. Butées, poses, contacts et correctifs des jointures')
    F2 = op['F2']; T2, _ = triangles(F2); V = s6['V']; W = s6['W']; Tc = tri_courts(V, F2); nbr = voisins(F2, len(V))
    ds = Dessin(sq['sx'], res=0.04)
    pose, sc, n = optimiser_pose_dessin(V, T2, W, sq, ds, s3['pose_dessin'], pas=(2, 1))
    ds2 = Dessin(sq['sx']); sc2 = iou(ds2.vue(poser(V, W, sq, pose), T2).masque, ds2.D)
    pose_dessin = {'poignet': {'flex': 0, 'dev': 0}, 'prono': 0, 'arc': 0}
    for k, v in pose.items(): pose_dessin[k] = {kk: float(vv) for kk, vv in v.items()}
    for k in DOIGTS: pose_dessin.setdefault(k, {}); [pose_dessin[k].setdefault(q, 0.0) for q in ('mcp', 'pip', 'dip', 'ab')]
    pose_dessin.setdefault('pouce', {}); [pose_dessin['pouce'].setdefault(q, 0.0) for q in ('av', 'rap', 'mcp', 'ip', 'abdMcp')]
    log('- pose « dessin » réajustée sur la main finale (poids et ongles compris) : IoU de la silhouette de face avec son '
        'dessin %.4f (grille 0,25 mm) ; angles %s' % (sc2, json.dumps(pose)))
    # superposition finale (main livrée, pose « dessin ») : contour du dessin en rouge, maillage projeté en vert
    from scipy import ndimage
    from PIL import Image, ImageDraw
    from raster import police
    Vp = poser(V, W, sq, pose); Mk = ds2.vue(Vp, T2).masque
    bM = Mk & ~ndimage.binary_erosion(Mk); yy, xx = np.nonzero(bM); dd = np.abs(ds2.sdf[yy, xx]) * 10
    from scipy.spatial import cKDTree
    _, vi = cKDTree(Vp[:, :2]).query(np.stack([ds2.X0 + (xx + 0.5) * ds2.res, ds2.Y1 - (yy + 0.5) * ds2.res], 1))
    lb = libre(V, sq)[vi]; okp = (ds2.Y1 - (yy + 0.5) * ds2.res) > -2.2; zp = okp & (lb < 0.05); zd = okp & (lb > 0.5)
    img = np.zeros((ds2.gh, ds2.gw, 3), np.uint8) + 255; img[Mk] = (190, 230, 200)
    img[Mk & ~ndimage.binary_erosion(Mk, iterations=2)] = (0, 150, 0); img[ds2.D & ~ndimage.binary_erosion(ds2.D, iterations=2)] = (220, 30, 30)
    im1 = Image.fromarray(img); dr = ImageDraw.Draw(im1); i_ = int(np.argmax(np.where(zp, dd, -1)))
    dr.ellipse([xx[i_] - 10, yy[i_] - 10, xx[i_] + 10, yy[i_] + 10], outline=(0, 0, 255), width=3)
    im1 = im1.resize((im1.width * 3 // 4, im1.height * 3 // 4)); out = Image.new('RGB', (im1.width, im1.height + 70), 'white')
    out.paste(im1, (0, 70)); dr = ImageDraw.Draw(out)
    dr.text((8, 4), 'Main livrée, pose « dessin » — rouge : contour de son dessin (milieu du trait) ; vert : maillage', fill='black', font=police(14))
    dr.text((8, 24), 'IoU %.4f ; paume : écart moyen %.2f mm, max %.1f mm (cercle bleu)' % (sc2, dd[zp].mean(), dd[zp].max()), fill='black', font=police(14))
    dr.text((8, 44), 'doigts (largeurs anatomiques imposées) : moyen %.1f mm, max %.1f mm' % (dd[zd].mean(), dd[zd].max()), fill='black', font=police(14))
    out.save(os.path.join(CHECKS, 'e8_dessin.png'))
    log('- superposition de la main LIVRÉE (pose « dessin ») : contour de la paume écart moyen %.2f mm, médian %.2f, max %.1f mm ; '
        'doigts et pouce : moyen %.1f mm, max %.1f mm (checks/e8_dessin.png)' % (dd[zp].mean(), np.median(dd[zp]), dd[zp].max(), dd[zd].mean(), dd[zd].max()))
    # --- correctifs des jointures ---
    cor, mes = correctifs(V, W, sq, Tc, nbr)
    log(''); log('| jointure | angle de référence | rayon dorsal au repos (mm) | LBS (mm) | DQS (mm) | DQS + correctif (mm) | saillie (mm) | déplacement max (mm) |')
    log('|---|---|---|---|---|---|---|---|')
    for nm, m in mes.items():
        if nm == COMMISSURE_ABD['nom']: continue
        ang, k = nm.split('_'); log('| %s %s | %.0f° | %.1f | %.1f | %.1f | %.1f | %+.1f | %.1f |' % (ang.upper(), k, CORRECTIFS[ang]['ref'], 10 * m['r_repos'],
            10 * m['r_lbs'], 10 * m['r_dqs'], 10 * m['r_corr'], 10 * (m['r_corr'] - m['r_repos']), 10 * m['dmax']))
    log('')
    log('- correctifs : rayon dorsal mesuré sur la bissectrice de la jointure (centre articulaire → peau) ; saillie = rayon '
        'posé avec correctif − rayon au repos ; cible %.1f mm à la MCP, %.1f mm à l’IPP ; coussinets palmaires %.1f / %.1f mm'
        % (10 * CORRECTIFS['mcp']['saillie'], 10 * CORRECTIFS['pip']['saillie'], 10 * CORRECTIFS['mcp']['coussin'], 10 * CORRECTIFS['pip']['coussin']))
    if COMMISSURE_ABD['nom'] in mes:
        m = mes[COMMISSURE_ABD['nom']]
        log('- 9e correctif « %s » (palmure de la 1re commissure, poids clamp(%s / %g, 0, 1)) : calculé dans la pose pouce rap = %g ; '
            'apex de la commissure à %.1f mm de la MCP du pouce, ramené vers elle de %.1f mm au plus, %d sommets'
            % (COMMISSURE_ABD['nom'], COMMISSURE_ABD['angle'], COMMISSURE_ABD['ref'], COMMISSURE_ABD['ref'], 10 * m['apex_mcp_cm'], 10 * m['dmax'], m['sommets']))
    poses_c = POSES_CONTROLE
    if regler:
        poses_c = regler_poses(V, W, sq, Tc, cor); log('- poses de contrôle RE-RÉGLÉES (--regler-poses) : %s' % json.dumps(poses_c))
    # --- contacts : pénétrations (DQS + correctifs, comme le moteur ; LBS pour mémoire), tunnel du poing ---
    g = groupes_contact(W)
    def resume(pen): 
        top = sorted(pen.items(), key=lambda x: -x[1]); return ', '.join('%s/%s %.1f' % (a, b, 10 * v) for (a, b), v in top if v > 0.03) or 'aucune'
    log(''); log('| pose | pénétration max DQS + correctifs (mm) | paires > 0,3 mm (mm) | LBS sans correctif : max (mm) |')
    log('|---|---|---|---|')
    tous = [('repos', POSE_REPOS), ('dessin', pose_dessin)] + [(k, v) for k, v in poses_c.items()] + \
           [('%s (avant relecture)' % k, v) for k, v in POSES_CONTROLE_AVANT.items()] + [(k, v) for k, v in POSES_ESSAI.items()]
    pens = {}
    for nom, p in tous:
        pd = penetration(poser_v2(V, W, sq, p, cor), Tc, g); pl = penetration(poser(V, W, sq, p, 'lbs'), Tc, g)
        pens[nom] = max(pd.values()); log('| %s | %.1f | %s | %.1f |' % (nom, 10 * max(pd.values()), resume(pd), 10 * max(pl.values())))
    log('')
    for nom, p in (('poing', poses_c['poing']), ('poing (avant relecture)', POSES_CONTROLE_AVANT['poing'])):
        M = cinematique(sq, p)
        a1, d1 = tunnel_profil(poser(V, W, sq, p, 'lbs'), Tc, M, sq); a2, d2 = tunnel_profil(poser(V, W, sq, p, 'dqs'), Tc, M, sq)
        a3, d3 = tunnel_profil(poser_v2(V, W, sq, p, cor), Tc, M, sq)
        log('- tunnel du %s vu de profil côté pouce (jour à travers la boucle de l’index) : LBS %.0f mm² (%.1f × %.1f mm), DQS %.0f mm², '
            'DQS + correctifs %.0f mm² (%.1f × %.1f mm)' % (nom, a1, *d1, a2, a3, *d3))
    B = butees()
    def verif(p):
        bad = []
        for k in DOIGTS:
            d = p.get(k, {}); b1, b2, b3 = B[k + '_p1'], B[k + '_p2'], B[k + '_p3']
            f = max(0.1, 1 - 0.9 * d.get('mcp', 0) / 90)
            if not (b1['flex'][0] <= d.get('mcp', 0) <= b1['flex'][1]): bad.append(k + '.mcp')
            if not (b1['abd'][0] * f - 1e-6 <= d.get('ab', 0) <= b1['abd'][1] * f + 1e-6): bad.append(k + '.ab (R2)')
            if not (b2['flex'][0] <= d.get('pip', 0) <= b2['flex'][1]): bad.append(k + '.pip')
            if not (b3['flex'][0] <= d.get('dip', 0) <= b3['flex'][1]): bad.append(k + '.dip')
            pip, dip = d.get('pip', 0), d.get('dip', 0)
            if dip > 25 + 0.65 * pip + 1e-6 or dip < 0.45 * (pip - 55) - 1e-6: bad.append(k + '.couplage')
        t = p.get('pouce', {})
        for q, bb in (('av', B['mc1']['av']), ('rap', B['mc1']['rap']), ('mcp', B['pouce_p1']['flex']), ('ip', B['pouce_p2']['flex'])):
            if not (bb[0] <= t.get(q, 0) <= bb[1]): bad.append('pouce.' + q)
        if t and t.get('av', 0) < 0.7 * max(0, t.get('rap', 0)) - 1e-6: bad.append('pouce.vis (av < 0,7·rap)')
        return bad
    for nom, p in [('repos', POSE_REPOS), ('dessin', pose_dessin)] + list(poses_c.items()) + list(POSES_ESSAI.items()):
        log('- pose « %s » : %s' % (nom, 'dans les butées actives et les couplages (R2, IPD–IPP, vis sans fin)' if not verif(p) else 'HORS butées : ' + ', '.join(verif(p))))
    sauver('s8', **cor)
    return dict(butees=B, repos=POSE_REPOS, dessin=pose_dessin, controle=poses_c, essai=POSES_ESSAI, iou_dessin=sc2,
                correctifs=cor, correctifs_mes=mes, pen=pens)

# =================================================================================================================
# Étape 9 — export GLB (bpy, glTF 2.0 binaire skinné) puis relecture et vérification ; hand_v2.json
# =================================================================================================================
def lire_glb(chemin):
    """lecture minimale d'un .glb (numpy) : nœuds, peau, primitive du maillage (attributs, indices)"""
    import struct
    b = open(chemin, 'rb').read(); assert b[:4] == b'glTF'
    n0 = struct.unpack('<I', b[12:16])[0]; js = json.loads(b[20:20 + n0]); off = 20 + n0
    n1 = struct.unpack('<I', b[off:off + 4])[0]; blob = b[off + 8:off + 8 + n1]
    CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
    NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    def acc(i):
        a = js['accessors'][i]; dt = np.dtype(CT[a['componentType']]); nc = NC[a['type']]
        if 'bufferView' in a:
            bv = js['bufferViews'][a['bufferView']]
            st = bv.get('byteStride', dt.itemsize * nc); o = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
            raw = np.frombuffer(blob, np.uint8, count=st * (a['count'] - 1) + dt.itemsize * nc, offset=o)
            arr = np.lib.stride_tricks.as_strided(raw, (a['count'], st), (st, 1))[:, :dt.itemsize * nc].copy().view(dt).reshape(a['count'], nc)
        else: arr = np.zeros((a['count'], nc), dt)
        if 'sparse' in a:            # accesseur creux (morph targets) : valeurs aux seuls indices listés
            sp_ = a['sparse']; n_ = sp_['count']; ib = js['bufferViews'][sp_['indices']['bufferView']]; vb = js['bufferViews'][sp_['values']['bufferView']]
            ix = np.frombuffer(blob, CT[sp_['indices']['componentType']], count=n_, offset=ib.get('byteOffset', 0) + sp_['indices'].get('byteOffset', 0))
            vals = np.frombuffer(blob, dt, count=n_ * nc, offset=vb.get('byteOffset', 0) + sp_['values'].get('byteOffset', 0)).reshape(n_, nc)
            arr = arr.copy(); arr[ix.astype(np.int64)] = vals
        if a.get('normalized'): arr = arr.astype(float) / np.iinfo(dt).max
        return arr
    return js, acc

def matrice_noeud(nd):
    if 'matrix' in nd: return np.array(nd['matrix']).reshape(4, 4).T
    M = np.eye(4); t = nd.get('translation', [0, 0, 0]); q = nd.get('rotation', [0, 0, 0, 1]); s_ = nd.get('scale', [1, 1, 1])
    M[:3, :3] = quat_mat(q) @ np.diag(s_); M[:3, 3] = t; return M

def etape9(s1, sq, op, s6, s7, s8):
    _etape[0] = '9'; log('### 9. Export GLB et hand_v2.json')
    import cycles_bpy
    from scipy.spatial import cKDTree
    F2 = op['F2']; V = s6['V']; W = s6['W']; C, A, bout = sq['C'], sq['A'], sq['bout']
    longs = {b: float(sq['long'][b]) for b in OS}
    chem = os.path.join(ICI, 'hand_v2.glb')
    reg = s6['reg']
    masques = np.stack([np.isin(reg, (1, 2)), reg == 2, reg == 3, reg == 4], 1).astype(np.float32)
    Tc = tri_courts(V, F2)        # triangulation exportée = celle des mesures (diagonale la plus courte de chaque quad)
    err = cycles_bpy.exporter_glb(chem, V, Tc, W, OS, PARENT, C, A, longs, {'_REGION': reg, '_ONGLE': s6['dongle']},
                                  couleurs={'_MASQUES': masques}, morphs=s8['correctifs'])
    log('- export bpy (export_yup = False : les axes du contrat passent tels quels) ; repères des os dans Blender = repères '
        'voulus à %.1e près' % err)
    # --- relecture ---
    js, acc = lire_glb(chem)
    meshes = js['meshes']; prim = meshes[0]['primitives']
    assert len(meshes) == 1 and len(prim) == 1, 'une seule primitive attendue'
    pr = prim[0]; att = pr['attributes']
    P = acc(att['POSITION']); N = acc(att['NORMAL']); I = acc(pr['indices']).reshape(-1, 3).astype(np.int64)
    J = acc(att['JOINTS_0']).astype(int); Wt = acc(att['WEIGHTS_0']).astype(float)
    sk = js['skins'][0]; jn = [js['nodes'][j]['name'] for j in sk['joints']]
    ibm = acc(sk['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
    # matrices monde des nœuds
    par = {}
    for i, nd in enumerate(js['nodes']):
        for c in nd.get('children', []): par[c] = i
    def monde(i):
        M = matrice_noeud(js['nodes'][i])
        while i in par: i = par[i]; M = matrice_noeud(js['nodes'][i]) @ M
        return M
    e_rep = 0.0; e_ibm = 0.0
    for k_, j in enumerate(sk['joints']):
        b = jn[k_]; Mw = monde(j)
        e_rep = max(e_rep, float(np.abs(Mw[:3, :3] - A[b]).max()), float(np.abs(Mw[:3, 3] - C[b]).max()))
        e_ibm = max(e_ibm, float(np.abs(Mw @ ibm[k_] - np.eye(4)).max()))
    mo = [i for i, nd in enumerate(js['nodes']) if 'mesh' in nd][0]; Mm = monde(mo)
    # morph targets relus : noms, déplacements = correctifs du pipeline
    cibles = pr.get('targets', []); noms_c = meshes[0].get('extras', {}).get('targetNames', [])
    e_m = max((float(np.abs(acc(tg['POSITION']) - s8['correctifs'][nm]).max()) for tg, nm in zip(cibles, noms_c)), default=float('nan'))
    # correspondance sommets GLB ↔ maillage du pipeline
    kd = cKDTree(V); dd, perm = kd.query(P)
    nom_os = {i: n_ for i, n_ in enumerate(jn)}
    Wg = np.zeros((len(P), 20)); [np.add.at(Wg, (np.arange(len(P)), [OS.index(nom_os[j]) for j in J[:, c]]), Wt[:, c]) for c in range(4)]
    e_w = float(np.abs(Wg - W[perm]).max())
    extra = sorted(k for k in att if k.startswith('_'))
    reg = acc(att['_REGION'])[:, 0] if '_REGION' in att else None
    log('- relu : %d sommets (pipeline %d, appariés à %.1e cm près, permutation %s), %d triangles (100 %% triangles), '
        '%d os %s ; attributs %s ; matrice du nœud du maillage = identité à %.1e près' %
        (len(P), len(V), dd.max(), 'identité' if np.all(perm == np.arange(len(V))) else 'non triviale', len(I), len(jn),
         'nommés comme le contrat' if sorted(jn) == sorted(OS) else 'NOMS DIFFÉRENTS', ', '.join(sorted(att)), np.abs(Mm - np.eye(4)).max()))
    log('- os relus : repère monde de chaque nœud = (axes, centre) voulus à %.1e près ; liaison⁻¹ × monde = identité à %.1e '
        'près ; poids relus = poids du pipeline à %.1e près (≤ 4 os, somme %.4f..%.4f)' % (e_rep, e_ibm, e_w, Wt.sum(1).min(), Wt.sum(1).max()))
    log('- morph targets relus : %d (%s), attributs %s ; déplacements = correctifs du pipeline à %.1e cm près'
        % (len(cibles), ', '.join(noms_c), '/'.join(sorted(cibles[0].keys())) if cibles else '—', e_m))
    # surface du GLB livré, au repos, sur SES triangles (relecture adverse : le chiffre doit porter sur le fichier livré)
    Pf = P.astype(float); ed, an = diedres_tri(Pf, I); ret = triangles_retournes(Pf, I)
    viv = op['vives']                                     # bord vif du bouchon du poignet (arêtes vives de la subdivision)
    hors = np.array([(int(perm[a_]), int(perm[b_])) not in viv and (int(perm[b_]), int(perm[a_])) not in viv for a_, b_ in ed]) & (Pf[ed[:, 0], 1] > -2.6)
    same = set(map(tuple, np.sort(perm[I], 1).tolist())) == set(map(tuple, np.sort(Tc, 1).tolist()))
    log('- surface du GLB au repos (ses %d triangles%s) : arêtes > 30° : %d, > 60° : %d, > 90° : %d, max %.1f° (hors bord vif du '
        'bouchon du poignet) ; triangles retournés : %d' % (len(I), ', identiques à ceux des mesures' if same else ', triangulation DIFFÉRENTE',
        (an[hors] > 30).sum(), (an[hors] > 60).sum(), (an[hors] > 90).sum(), an[hors].max(), len(ret)))
    # --- plis : barycentriques sur les triangles DU GLB ---
    cent = P[I].mean(1); kdt = cKDTree(cent); plis = []; emax = 0.0
    for p in s7['plis']:
        t, bb, d = localiser(P.astype(float), I, p['P'], kdt, cent); emax = max(emax, float(d.max()))
        e = {'nom': p['nom'], 'type': p['type'], 'groupe': p['groupe'], 'visible': p['visible'],
             'points': [[int(tt), round(float(b0), 5), round(float(b1), 5), round(float(b2), 5)] for tt, (b0, b1, b2) in zip(t, bb)]}
        if p.get('regle'): e['regle'] = p['regle']
        plis.append(e)
    log('- plis convertis en barycentriques sur les triangles du GLB : %d courbes, écart max point ↔ surface %.4f mm' % (len(plis), 10 * emax))
    # --- JSON ---
    os_json = {}
    for b in OS:
        k = CHAINE_DE.get(b); e = {'parent': PARENT[b], 'centre': [round(float(v), 4) for v in C[b]], 'longueur': round(longs[b], 4),
                                   'axes': {'x': [round(float(v), 5) for v in A[b][:, 0]], 'y': [round(float(v), 5) for v in A[b][:, 1]],
                                            'z': [round(float(v), 5) for v in A[b][:, 2]]}}
        if b == 'poignet': e['rayon'] = 2.0
        elif b.startswith('mc'): e['rayon'] = 1.0 if b == 'mc1' else 0.75
        else:
            ch = CHAINES[k]; jj = ch.index(b) - (0 if k == 'pouce' else 1)
            i0 = {0: 0, 1: 2, 2: 4}[jj] if k != 'pouce' else {1: 0, 2: 3}[ch.index(b)]
            e['rayon'] = round(0.25 * (LARGEUR[k][i0] + EPAISSEUR[k][i0]), 3)
            e['largeur'] = LARGEUR[k][i0]; e['epaisseur'] = EPAISSEUR[k][i0]
        if b == CHAINES.get(k, [None])[-1]: e['bout'] = [round(float(v), 4) for v in bout[k]]
        os_json[b] = e
    ongles = s6['ongles']
    correctifs_json = []
    for nm in s8['correctifs']:
        if nm == COMMISSURE_ABD['nom']:
            m = s8['correctifs_mes'][nm]; k_, ch_ = COMMISSURE_ABD['angle'].split('.')
            correctifs_json.append({'nom': nm, 'os': 'pouce_p1', 'angle': COMMISSURE_ABD['angle'], 'reference': COMMISSURE_ABD['ref'],
                                    'poids': 'clamp(%s / %g, 0, 1) = clamp(−%s.%s / %g, 0, 1) : 0 pour tout pouce ramené (rap ≥ 0), 1 dans « L » '
                                             '(rap −28), 0,43 dans « Main ouverte (5) » (rap −12)' % (COMMISSURE_ABD['angle'], COMMISSURE_ABD['ref'], k_, ch_, -COMMISSURE_ABD['ref']),
                                    'role': 'palmure de la 1re commissure (faces dorsale et palmaire) ramenée vers la MCP du pouce quand le pouce '
                                            's’écarte (abduction radiale) : la peau glisse le long du pouce comme sur ses photos 2354 et 2361',
                                    'deplacement_max_mm': round(10 * m['dmax'], 1)})
            continue
        ang, k = nm.split('_'); cfg = CORRECTIFS[ang]; m = s8['correctifs_mes'][nm]
        correctifs_json.append({'nom': nm, 'os': k + cfg['os'], 'angle': '%s.%s' % (k, ang), 'reference': cfg['ref'],
                                'poids': 'clamp(%s.%s / %g, 0, 1)' % (k, ang, cfg['ref']),
                                'saillie_dorsale_mm': round(10 * (m['r_corr'] - m['r_repos']), 1), 'coussin_palmaire_mm': round(10 * cfg['coussin'], 1)})
    meta = {
        'version': 1, 'unites': 'cm', 'HL': HL,
        'cote_anatomique': 'droite — avec les axes du contrat (doigts +Y, paume +Z, pouce +X) le maillage est une main '
                           'droite vue paume vers +Z, comme le dessin paume.jpg ; l’autre main = miroir x → −x',
        'cote_note_plan': 'PLAN.md écrit « main gauche » : dans un repère direct (déterminant des repères des os = +1), une main '
                          'paume vers +Z, doigts vers +Y, pouce vers +X est forcément une main DROITE (une gauche aurait le pouce '
                          'en −X). Correction proposée au PLAN : « main droite skinnée (la gauche = miroir x → −x) ». Le moteur lit '
                          'cote_anatomique.',
        'source': 'MakeHuman hm08 (CC0 1.0) : base.obj, default.mhskel, default_weights.mhw — retaillé par build_hand.py',
        'repere': {'origine': 'centre du poignet', 'x': 'pouce', 'y': 'doigts', 'z': 'paume'},
        'maillage': {'sommets': int(len(P)), 'triangles': int(len(I)), 'attributs': sorted(att),
                     'attributs_threejs': 'GLTFLoader r128 met en minuscules les attributs personnalisés : geometry.attributes._region, '
                                          '._ongle, ._masques (les noms glTF restent _REGION, _ONGLE, _MASQUES)',
                     'skinning': '≤ 4 os par sommet, normalisés (JOINTS_0 / WEIGHTS_0)',
                     'morph_targets': '%d correctifs (8 des jointures + « commissure_abd ») (POSITION + NORMAL, noms dans '
                                      'mesh.extras.targetNames → morphTargetDictionary), voir « correctifs »' % len(s8['correctifs'])},
        'correctifs': {'principe': 'déplacement de la peau, dans l’espace de LIAISON, à ajouter AVANT le skinning avec le poids '
                                   'clamp(angle / reference, 0, 1) (champ « angle » = « doigt.champ » de la pose ; reference NÉGATIVE pour '
                                   '« commissure_abd » : rap < 0) : à l’angle de référence, en DQS, la tête de l’os saille côté dos, la chair '
                                   'palmaire remplit le coin de la boucle du doigt, les rides dorsales sont lissées ; la palmure du pouce suit '
                                   'son abduction',
                       'skinning': 'calculés pour les quaternions duaux (DQS) ; en LBS l’effet est proche mais la jointure reste écrasée',
                       'limite_threejs_r128': 'le shader intégré n’applique que 8 morphs (4 avec morphNormals) : 9 correctifs ici '
                                              '(au plus 8 actifs dans un poing : commissure_abd y vaut 0) ; appliquer les morphs côté CPU '
                                              '(le moteur le fait), ou garder morphNormals éteint',
                       'liste': correctifs_json},
        'regions': {'attribut': '_REGION', 'codes': {'0': 'peau', '1': 'plaque d’ongle', '2': 'frange libre de l’ongle',
                    '3': 'repli d’ongle', '4': 'palmure'},
                    'lecture': '_REGION est un CODE par sommet : ne pas l’interpoler entre régions (entre peau 0 et palmure 4, '
                               'une interpolation passe par 1–3) ; pour des bords nets, utiliser _MASQUES et _ONGLE',
                    '_MASQUES': 'VEC4 par sommet, masques 0/1 qui s’interpolent proprement : (ongle = plaque + frange, frange, repli, palmure)',
                    '_ONGLE': 'distance signée au bord de la plaque d’ongle, mm (> 0 dedans, bornée à ±3) : seuil 0 = trait net à tout grossissement',
                    'ongles': ongles},
        'os': os_json, 'butees': s8['butees'], 'couplages': COUPLAGES, 'convention_pose': CONVENTION_POSE,
        'plis_convention': 'points = [triangle du GLB (indice dans l’ordre des indices), b0, b1, b2] ; type « = » : double '
                           'trait dorsal (deux courbes du même groupe) ; visible : « ext(os) » = s’efface quand l’os fléchit '
                           '(de 20° à 80°), « flex(os…) » = se creuse avec la flexion, toujours tracé',
        'plis': plis,
        'repos': s8['repos'], 'dessin': s8['dessin'], 'poses_controle': s8['controle'], 'poses_essai': s8['essai'],
        'contacts': {'regle': 'enfoncement de chair admis ≤ %.1f mm entre doigts, doigt et pouce, bout et paume (mobilite.md § 5 P2.1 : '
                              '1,5–3 mm) ; mesuré en DQS + correctifs' % (10 * CONTACT_MOU),
                     'penetration_max_mm': {k: round(10 * v, 1) for k, v in s8['pen'].items()}},
        'conseils_moteur': [
            'skinning en quaternions duaux, PUIS correctifs (morph targets) : en LBS la jointure de l’index s’écrase de 3 mm à 90°, '
            'en DQS elle reste ronde sans saillir (checks/e8_correctifs.jpg)',
            'vis sans fin du pouce : av ≥ 0,7·max(0, rap) (v1 AVC) — « rapprocher 45 » avec « avancer 0 » fait entrer le pouce dans '
            'le 2e métacarpien (pose hors couplage, mesurée dans poses_essai)',
            'ongle rigide : plaque, frange, replis et un anneau autour ont un poids 1,0 sur la dernière phalange',
            'trait d’ongle : seuil 0 de _ONGLE (distance signée en mm), net à tout grossissement ; _REGION à lire sans interpolation',
            'attributs personnalisés vus par three.js r128 : _region, _ongle, _masques (minuscules, GLTFLoader)',
            'main gauche : miroir x → −x à la racine (scale.x = −1) ; les normales sont alors déjà bonnes (leçon v1 « nflip »)',
            'avant-bras : l’os racine « poignet » porte les 2,7 cm d’avant-bras ; fléchir le poignet = tourner mc1–mc5 autour de l’origine',
        ],
        'mesures': {'iou_silhouette_dessin': round(s8['iou_dessin'], 4)},
        'dessin_echelle': {'image': 'references/paume.jpg', 'x0_px': DESSIN['x0'], 'y_pli_px': DESSIN['y_pli'],
                           'cm_par_px_x': round(float(sq['sx']), 6), 'cm_par_px_y': round(SY, 6),
                           'note': 'x_cm = (px − x0)·sx, y_cm = (y_pli − py)·sy : la pose « dessin » vue de +Z se superpose au dessin'},
    }
    json.dump(meta, open(os.path.join(ICI, 'hand_v2.json'), 'w'), ensure_ascii=False, indent=1)
    log('- hand_v2.glb : %.0f Ko ; hand_v2.json : %.0f Ko' % (os.path.getsize(chem) / 1024, os.path.getsize(os.path.join(ICI, 'hand_v2.json')) / 1024))
    return dict(P=P, I=I, perm=perm)


# =================================================================================================================
# Étape 10 — contrôles : rendus Cycles (bpy) au repos et dans deux poses (poing, V ; os tournés, skinning LBS), et test
# de chargement du GLB dans three.js r128 (Playwright, voir test_three.py)
# =================================================================================================================
def etape10(s1, sq, op, s6, s8, sans_cycles=False):
    """contrôles : déformation de la surface pose par pose (LBS, DQS, DQS + correctifs), rendus Cycles (bpy) faits en
    DQS + correctifs comme le moteur M2 (relecture adverse : les rendus LBS cachaient ce que M2 montrera), gros plans des
    bouts, des jointures et du tunnel du poing, puis chargement du GLB dans three.js r128"""
    _etape[0] = '10'; log('### 10. Contrôles')
    from raster import vues, planche, police
    from PIL import Image, ImageDraw
    F2 = op['F2']; V = s6['V']; W = s6['W']; dong = s6['dongle']; Tc = tri_courts(V, F2); cor = s8['correctifs']
    C = sq['C']; bout = sq['bout']
    # --- déformation : arêtes dont l'angle entre faces passe au-delà de 60° (pli vif nouveau) et triangles retournés ---
    Pp = paires_triangles(Tc); e, a0 = diedres_tri(V, Tc, Pp)
    poses = [('repos', s8['repos']), ('dessin', s8['dessin'])] + list(s8['controle'].items()) + list(s8['essai'].items())
    log(''); log('| pose | LBS : arêtes devenues > 60° / triangles retournés | DQS | DQS + correctifs |'); log('|---|---|---|---|')
    for nom, p in poses:
        cells = []
        for mode, cc in (('lbs', None), ('dqs', None), ('dqs', cor)):
            Vp = poser_v2(V, W, sq, p, cc, mode); _, a = diedres_tri(Vp, Tc, Pp)
            cells.append('%d / %d' % (((a > 60) & (a0 <= 60)).sum(), len(triangles_retournes(Vp, Tc))))
        log('| %s | %s |' % (nom, ' | '.join(cells)))
    log('')
    log('- lecture : les arêtes nouvelles > 60° d’une pose fléchie sont surtout les plis PALMAIRES (la peau se replie au pli de '
        'flexion, c’est un vrai pli) ; un triangle retourné est une peau qui se traverse : ils sont au fond de ces plis')
    # poing : distance des bouts à la peau de la paume
    pg = s8['controle']['poing']; Vp = poser_v2(V, W, sq, pg, cor); M = cinematique(sq, pg)
    from scipy.spatial import cKDTree
    paume = (W[:, [OSI[b] for b in ('mc2', 'mc3', 'mc4', 'mc5')]].sum(1) > 0.9) & (V[:, 2] > 0.5)
    kd = cKDTree(Vp[paume]); tips = {k: (M[OSI[CHAINES[k][-1]]] @ np.r_[bout[k], 1])[:3] for k in DOIGTS}
    log('- poing (DQS + correctifs) : distance de l’extrémité de l’axe de chaque doigt à la peau de la paume : ' +
        ', '.join('%s %.1f mm' % (k, 10 * kd.query(tips[k])[0]) for k in DOIGTS) + ' (demi-épaisseur de la pulpe 5,5–6,8 mm : le bout appuie)')
    if sans_cycles: return
    import cycles_bpy
    VW = vues(); noms_v = [('paume', 'face (paume)'), ('dos', 'dos'), ('profil_radial', 'profil (pouce)'), ('dessus', 'dessus (bouts)'), ('dos_34', '¾ dos')]
    def cadre(Vx, R):
        P = Vx @ R.T; c = Vx.mean(0); ext = max(np.ptp(P[:, 0]), np.ptp(P[:, 1]))
        return R.T @ np.array([P[:, 0].min() + np.ptp(P[:, 0]) / 2, P[:, 1].min() + np.ptp(P[:, 1]) / 2, c @ R[2]]), 0.56 * ext
    t0 = time.time(); nren = 0
    # 1. planche générale : liaison, repos, poing, V — DQS + correctifs
    scenes = [('main ouverte (liaison)', V), ('repos', poser_v2(V, W, sq, s8['repos'], cor)),
              ('poing', poser_v2(V, W, sq, s8['controle']['poing'], cor)), ('V', poser_v2(V, W, sq, s8['controle']['V'], cor))]
    ims, labs = [], []
    for i, (titre, Vx) in enumerate(scenes):
        vl = [(VW[nm],) + cadre(Vx, VW[nm]) for nm, _ in noms_v]
        ch = cycles_bpy.rendus([(Vx, Tc, dong)], vl, taille=460, echantillons=24, chemin_tmp=os.path.join(WORK, 'cyc_%02d_%%d.png' % i))
        ims += [Image.open(p).convert('RGB') for p in ch]; labs += ['%s — %s' % (titre, v[1]) for v in noms_v]; nren += len(ch)
    planche(ims, labs, cols=5, titre='Contrôle Cycles — skinning DQS + morph targets correctifs (comme le moteur M2), ongles en clair').save(
        os.path.join(CHECKS, 'e10_cycles.jpg'), quality=90)
    # 2. pouce : rapprocher (avec sa vis sans fin), opposition, arc métacarpien ; et le cas hors couplage
    ims, labs = [], []
    Pp2 = Pp
    for i, (nom, p) in enumerate(s8['essai'].items()):
        Vx = poser_v2(V, W, sq, p, cor); _, a = diedres_tri(Vx, Tc, Pp2); nv = int(((a > 60) & (a0 <= 60)).sum())
        R34 = VW['paume_34']; vl = [(VW['paume'], np.array([1.5, 6.5, 1.5]), 6.0), (R34, np.array([1.5, 6.5, 1.5]), 6.0)]
        ch = cycles_bpy.rendus([(Vx, Tc, dong)], vl, taille=400, echantillons=20, chemin_tmp=os.path.join(WORK, 'cyc_p%d_%%d.png' % i))
        ims += [Image.open(q).convert('RGB') for q in ch]; nren += len(ch)
        labs += ['%s — paume (%d arêtes > 60°, %d retournés)' % (nom, nv, len(triangles_retournes(Vx, Tc))), '%s — paume ¾' % nom]
    planche(ims, labs, cols=4, titre='Pouce et arc métacarpien (DQS + correctifs) : « rapprocher » avec sa vis sans fin (av = 0,7·rap), '
            'opposition, arc = 1 ; « rapprocher_sans_vis » est hors couplage').save(os.path.join(CHECKS, 'e10_pouce.jpg'), quality=90)
    # 3. jointures du poing et tunnel : LBS / DQS / DQS + correctifs ; ancien poing pour comparaison
    d_ = nz(np.array([0.25, 0.75, -1.0])); up = nz(np.array([0, 1.0, 0]) - d_ * d_[1]); R1 = np.stack([np.cross(up, d_), up, d_])
    ctr = np.mean([C[k + '_p1'] for k in DOIGTS], 0) + np.array([0, -0.5, 0.5])
    vl = [(R1, ctr, 5.5), (VW['profil_radial'], np.array([1.0, 7.5, 2.0]), 6.0), (VW['paume'], np.array([0.5, 7.0, 2.0]), 6.5)]
    ims, labs = [], []
    for i, (titre, Vx) in enumerate((('ancien poing, LBS (livraison précédente)', poser(V, W, sq, POSES_CONTROLE_AVANT['poing'], 'lbs')),
                                     ('poing réglé, DQS sans correctif', poser(V, W, sq, pg, 'dqs')),
                                     ('poing réglé, DQS + correctifs (M2)', poser_v2(V, W, sq, pg, cor)))):
        ch = cycles_bpy.rendus([(Vx, Tc, dong)], vl, taille=420, echantillons=24, chemin_tmp=os.path.join(WORK, 'cyc_c%d_%%d.png' % i))
        ims += [Image.open(q).convert('RGB') for q in ch]; nren += len(ch)
        labs += ['%s — jointures (dos ¾)' % titre, '%s — profil (pouce)' % titre, '%s — face' % titre]
    planche(ims, labs, cols=3, titre='Jointures et tunnel du poing — morph targets correctifs (saillie dorsale, coussinets palmaires, '
            'rides lissées)').save(os.path.join(CHECKS, 'e8_correctifs.jpg'), quality=90)
    # 4. bouts des doigts au repos (liaison), un doigt après l'autre : dos, bout, deux profils
    ims, labs = [], []
    for i, k in enumerate(DOIGTS + ['pouce']):
        _, o, Fr, L3 = ongle_cadre(k, sq); c = o + Fr @ np.array([0, 0.62 * L3, -0.2]); X_, S_, Z_ = Fr[:, 0], Fr[:, 1], Fr[:, 2]
        def Rv(ey, ez):
            ey = nz(ey - (ey @ ez) * ez); return np.stack([np.cross(ey, ez), ey, ez])
        vl = [(Rv(S_, -Z_), c, 1.2), (Rv(-Z_, S_), c, 1.2), (Rv(-Z_, X_), c, 1.3), (Rv(-Z_, -X_), c, 1.3)]
        ch = cycles_bpy.rendus([(V, Tc, dong)], vl, taille=300, echantillons=20, chemin_tmp=os.path.join(WORK, 'cyc_b%d_%%d.png' % i))
        ims += [Image.open(q).convert('RGB') for q in ch]; nren += len(ch)
        labs += ['%s — dos' % k, '%s — bout' % k, '%s — profil +x' % k, '%s — profil −x' % k]
    planche(ims, labs, cols=4, titre='Bouts des doigts au repos (Cycles) — plaque, sillons latéraux, repli proximal, bord libre').save(
        os.path.join(CHECKS, 'e10_bouts.jpg'), quality=90)
    # 5. gros plans : V de dos (ongles en pose), index de profil
    gp = cycles_bpy.rendus([(scenes[3][1], Tc, dong)], [(VW['dos'], np.array([0.2, 14.5, 0]), 4.0)], taille=560, echantillons=32,
                           chemin_tmp=os.path.join(WORK, 'cyc_gp1_%d.png'))
    gp += cycles_bpy.rendus([(V, Tc, dong)], [(VW['dos'], np.array([0.5, 16.0, 0]), 3.6), (VW['profil_radial'], np.array([2.6, 16.2, 0]), 2.2)],
                            taille=560, echantillons=32, chemin_tmp=os.path.join(WORK, 'cyc_gp2_%d.png'))
    nren += len(gp)
    planche([Image.open(p).convert('RGB') for p in gp], ['V : ongles de l’index et du majeur (dos)', 'bouts et ongles au repos (dos)', 'bout de l’index (profil)'],
            cols=3, titre='Contrôle Cycles — gros plans').save(os.path.join(CHECKS, 'e10_gros_plans.jpg'), quality=90)
    # 6. signes du grief du 20 octobre 2026 (« L » vu de dos) : repos, poing, V, L × face / dos / profil, et gros plans des
    #    jointures de dos (de face et en plongée de 35°, là où l'obliquité des P1 se voyait le plus)
    ims, labs = [], []
    Rpl = VW['dos'] @ rot_axe([1, 0, 0], math.radians(-35))
    sig = [('repos', s8['repos']), ('poing', s8['controle']['poing']), ('V', s8['controle']['V']), ('L', POSE_L)]
    for i, (nom, p) in enumerate(sig):
        Vx = poser_v2(V, W, sq, p, cor)
        vl = [(VW[nm],) + cadre(Vx, VW[nm]) for nm in ('paume', 'dos', 'profil_radial')]
        ch = cycles_bpy.rendus([(Vx, Tc, dong)], vl, taille=420, echantillons=24, chemin_tmp=os.path.join(WORK, 'cyc_s%d_%%d.png' % i))
        ims += [Image.open(q).convert('RGB') for q in ch]; nren += len(ch); labs += ['%s — %s' % (nom, v) for v in ('face (paume)', 'dos', 'profil (pouce)')]
    planche(ims, labs, cols=3, titre='Signes (DQS + correctifs) : repos, poing, V, L — largeurs de SON dessin, P1 repliées quasi parallèles, '
            'pouce à 56° de pronation de repos').save(os.path.join(CHECKS, 'e10_signes.jpg'), quality=90)
    ims, labs = [], []
    for i, (nom, p) in enumerate(sig[1:]):
        Vx = poser_v2(V, W, sq, p, cor); M = cinematique(sq, p)
        ctr = np.mean([(M[OSI[k + '_p1']] @ np.r_[C[k + '_p1'], 1])[:3] for k in DOIGTS], 0)
        ch = cycles_bpy.rendus([(Vx, Tc, dong)], [(VW['dos'], ctr, 4.2), (Rpl, ctr, 4.2)], taille=480, echantillons=28,
                               chemin_tmp=os.path.join(WORK, 'cyc_j%d_%%d.png' % i))
        ims += [Image.open(q).convert('RGB') for q in ch]; nren += len(ch); labs += ['%s — jointures, dos' % nom, '%s — jointures, dos en plongée 35°' % nom]
    planche(ims, labs, cols=2, titre='Jointures vues de dos (DQS + correctifs) : P1 repliées (photos : parallèles sous le majeur)').save(
        os.path.join(CHECKS, 'e10_jointures_dos.jpg'), quality=90)
    log('- %d rendus Cycles (CPU, 20 à 32 échantillons) en %.0f s : e10_cycles.jpg, e10_pouce.jpg, e8_correctifs.jpg, e10_bouts.jpg, '
        'e10_gros_plans.jpg, e10_signes.jpg, e10_jointures_dos.jpg' % (nren, time.time() - t0))

# =================================================================================================================
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--depuis', type=int, default=1); ap.add_argument('--jusqu', type=int, default=99)
    ap.add_argument('--sans-cycles', action='store_true')
    ap.add_argument('--regler-poses', action='store_true', help='relance la recherche des poses de contrôle (≈ 5 min)')
    args = ap.parse_args(); t0 = time.time()
    s1 = etape1() if args.depuis <= 1 else lire_s1()
    if args.jusqu >= 2: sq = etape2(s1) if args.depuis <= 2 else lire_s2()
    ring = s1['ring']; viv = set(tuple(sorted((ring[i], ring[(i + 1) % len(ring)]))) for i in range(len(ring)))
    S_, F2_, v2_, mere_ = cc2_operateur(s1['F'], len(s1['V']), viv)          # Catmull-Clark ×2, arêtes vives au bord
    op = dict(S=S_, F2=F2_, vives=v2_, mere=mere_)                          # du bouchon du poignet
    if args.jusqu >= 3: s3 = etape3(s1, sq, op) if args.depuis <= 3 else lire_s3()
    if args.jusqu >= 4: s4 = etape4(s1, sq, op, s3) if args.depuis <= 4 else lire_s4()
    if args.jusqu >= 5: s5 = etape5(s1, sq, op, s4) if args.depuis <= 5 else lire_s5()
    if args.jusqu >= 6: s6 = etape6(s1, sq, op, s4, s5) if args.depuis <= 6 else lire_s6()
    if args.jusqu >= 7: s7 = etape7(s1, sq, op, s3, s6) if args.depuis <= 7 else lire_s7()
    if args.jusqu >= 8: s8 = etape8(s1, sq, op, s3, s6, regler=args.regler_poses)
    if args.jusqu >= 9: s9 = etape9(s1, sq, op, s6, s7, s8)
    if args.jusqu >= 10:
        etape10(s1, sq, op, s6, s8, args.sans_cycles)
        if not args.sans_cycles:      # chargement dans three.js r128 (Chromium swiftshader, Playwright)
            import subprocess
            r = subprocess.run([sys.executable, os.path.join(SCRATCH, 'run_rendu.py'), os.path.join(ICI, 'test_three.py')],
                               cwd=RACINE, capture_output=True, text=True, timeout=600)
            try:
                rap = json.load(open(os.path.join(WORK, 'three.json')))
                log('- three.js r%s (GLTFLoader) : %d SkinnedMesh, %d os (noms du contrat : %s), %d sommets, %d triangles, '
                    'attributs %s ; régions (sommets) %s ; index_p1.rotateX(90°) : bout de l’index (%.2f, %.2f, %.2f) → '
                    '(%.2f, %.2f, %.2f) cm — checks/e10_three.png' % (rap['revision'], rap['skinnedMesh'], rap['os'],
                    'oui' if rap['noms_conformes'] else 'NON', rap['sommets'], rap['triangles'], ', '.join(rap['attributs']),
                    rap['regions'], *rap['bout_index_repos'], *rap['bout_index_flechi']))
            except Exception as e:
                log('- test three.js : ÉCHEC (%s) %s' % (e, r.stderr[-500:]))
    ecrire_journal()
    print('temps %.0f s' % (time.time() - t0))
