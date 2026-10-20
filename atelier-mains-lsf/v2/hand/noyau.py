"""Outils géométriques du chantier M1 (numpy seul) : Catmull-Clark avec arêtes vives et attributs interpolés,
triangulation, normales, rotations, quaternions, skinning (LBS / quaternions duaux), échantillonnage de surface."""
import numpy as np
from collections import defaultdict

def nz(v):
    v = np.asarray(v, float); n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-12)

def rot_axe(axe, ang):
    """matrice de rotation d'angle ang (radians) autour de l'axe unitaire axe (Rodrigues)"""
    a = nz(axe); x, y, z = a; c, s = np.cos(ang), np.sin(ang); C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])

def rot_min(a, b):
    """plus petite rotation qui amène la direction a sur la direction b"""
    a, b = nz(a), nz(b); v = np.cross(a, b); s = np.linalg.norm(v); c = float(a @ b)
    if s < 1e-10:
        if c > 0: return np.eye(3)
        p = nz(np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0])); return rot_axe(p, np.pi)
    return rot_axe(v / s, np.arctan2(s, c))

def mat_quat(R):
    """matrice 3×3 → quaternion (x, y, z, w), w ≥ 0"""
    R = np.asarray(R, float); t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1) * 2; w = s / 4; x = (R[2, 1] - R[1, 2]) / s; y = (R[0, 2] - R[2, 0]) / s; z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = np.sqrt(1 + R[0, 0] - R[1, 1] - R[2, 2]) * 2; w = (R[2, 1] - R[1, 2]) / s; x = s / 4; y = (R[0, 1] + R[1, 0]) / s; z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = np.sqrt(1 + R[1, 1] - R[0, 0] - R[2, 2]) * 2; w = (R[0, 2] - R[2, 0]) / s; x = (R[0, 1] + R[1, 0]) / s; y = s / 4; z = (R[1, 2] + R[2, 1]) / s
    else:
        s = np.sqrt(1 + R[2, 2] - R[0, 0] - R[1, 1]) * 2; w = (R[1, 0] - R[0, 1]) / s; x = (R[0, 2] + R[2, 0]) / s; y = (R[1, 2] + R[2, 1]) / s; z = s / 4
    q = np.array([x, y, z, w]); q /= np.linalg.norm(q)
    return q if q[3] >= 0 else -q

def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

# ------------------------------------------------------------------------------------------------------------
def triangles(F):
    """faces (listes de sommets) → triangles (éventail) ; renvoie aussi l'indice de la face d'origine"""
    T, src = [], []
    for i, f in enumerate(F):
        for k in range(1, len(f) - 1): T.append((f[0], f[k], f[k + 1])); src.append(i)
    return np.array(T, np.int64), np.array(src, np.int64)

def triangles_quads(F):
    """quads → 2 triangles, coupés selon la diagonale la plus courte n'est pas fait ici (topologie fixe) : (0,1,2),(0,2,3)"""
    return triangles(F)

def normales(V, T):
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    N = np.zeros_like(V)
    for k in range(3): np.add.at(N, T[:, k], n)
    return nz(N)

def aretes(F):
    """dictionnaire arête triée → liste des faces"""
    E = defaultdict(list)
    for i, f in enumerate(F):
        for j in range(len(f)): E[tuple(sorted((f[j], f[(j + 1) % len(f)])))].append(i)
    return E

def catmull_clark(V, F, attrs=None, vives=None):
    """Une itération de Catmull-Clark.
    V (n,3), F liste de faces (n-gones), attrs : dict nom → tableau (n, ...) interpolé LINÉAIREMENT avec les mêmes
    moyennes que les positions dans leur version « topologique » (point de face = moyenne, point d'arête = moyenne des
    2 extrémités, sommet = sommet) — c'est ce qu'il faut pour des poids ou des étiquettes (pas de lissage qui
    déborderait d'une région) ; vives : ensemble d'arêtes (triées) à garder vives (règles de pli : point d'arête =
    milieu, sommet sur 2 arêtes vives = (6v + a + b)/8, ≥ 3 vives = coin fixe).
    Renvoie V2, F2 (quads), attrs2, vives2, et pour chaque nouvelle face l'indice de sa face mère."""
    V = np.asarray(V, float); n = len(V); attrs = attrs or {}; vives = set(vives or ())
    E = aretes(F); el = list(E.keys()); eid = {e: i for i, e in enumerate(el)}
    fp = np.array([V[f].mean(0) for f in F])
    ep = np.zeros((len(el), 3))
    for i, e in enumerate(el):
        fs = E[e]
        if len(fs) == 2 and e not in vives: ep[i] = (V[e[0]] + V[e[1]] + fp[fs[0]] + fp[fs[1]]) / 4
        else: ep[i] = (V[e[0]] + V[e[1]]) / 2
    # nouveaux sommets
    vf = defaultdict(list); ve = defaultdict(list)
    for i, f in enumerate(F):
        for v in f: vf[v].append(i)
    for e in el: ve[e[0]].append(e); ve[e[1]].append(e)
    Vn = V.copy()
    for v in range(n):
        es = ve[v]
        if not es: continue
        sharp = [e for e in es if e in vives or len(E[e]) != 2]
        if len(sharp) == 2:
            a = sharp[0][0] if sharp[0][1] == v else sharp[0][1]; b = sharp[1][0] if sharp[1][1] == v else sharp[1][1]
            Vn[v] = (6 * V[v] + V[a] + V[b]) / 8
        elif len(sharp) > 2: Vn[v] = V[v]
        else:
            k = len(es); Fm = fp[vf[v]].mean(0); Rm = np.mean([(V[e[0]] + V[e[1]]) / 2 for e in es], 0)
            Vn[v] = (Fm + 2 * Rm + (k - 3) * V[v]) / k
    V2 = np.vstack([Vn, ep, fp])
    off_e = n; off_f = n + len(el)
    F2, mere = [], []
    for i, f in enumerate(F):
        m = len(f)
        for j in range(m):
            a = f[j]; e_prev = eid[tuple(sorted((f[j - 1], f[j])))]; e_next = eid[tuple(sorted((f[j], f[(j + 1) % m])))]
            F2.append([a, off_e + e_next, off_f + i, off_e + e_prev]); mere.append(i)
    A2 = {}
    for k, A in attrs.items():
        A = np.asarray(A, float)
        Ae = np.array([(A[e[0]] + A[e[1]]) / 2 for e in el]); Af = np.array([A[f].mean(0) for f in F])
        A2[k] = np.concatenate([A, Ae, Af], 0)
    viv2 = set()
    for e in vives:
        m = off_e + eid[e]; viv2.add(tuple(sorted((e[0], m)))); viv2.add(tuple(sorted((e[1], m))))
    return V2, F2, A2, viv2, np.array(mere)

def echantillons(V, T, n, rng=0, poids=None):
    """n points tirés uniformément sur la surface ; renvoie (P, tri, bary)"""
    rng = np.random.default_rng(rng)
    A = V[T[:, 0]]; B = V[T[:, 1]]; C = V[T[:, 2]]
    ar = np.linalg.norm(np.cross(B - A, C - A), axis=1) / 2
    if poids is not None: ar = ar * poids
    idx = rng.choice(len(T), n, p=ar / ar.sum())
    u = rng.random(n); v = rng.random(n); m = u + v > 1; u[m] = 1 - u[m]; v[m] = 1 - v[m]
    P = A[idx] + u[:, None] * (B[idx] - A[idx]) + v[:, None] * (C[idx] - A[idx])
    return P, idx, np.stack([1 - u - v, u, v], 1)

def voisins(F, n):
    nb = [set() for _ in range(n)]
    for f in F:
        for j in range(len(f)):
            a, b = f[j], f[(j + 1) % len(f)]; nb[a].add(b); nb[b].add(a)
    return [np.array(sorted(s)) for s in nb]

def lisser(A, nb, iters=1, lam=0.5, masque=None):
    """lissage laplacien d'un attribut de sommet (uniforme), limité aux sommets du masque"""
    A = np.array(A, float)
    for _ in range(iters):
        M = np.array([A[s].mean(0) if len(s) else A[i] for i, s in enumerate(nb)])
        if masque is None: A = A + lam * (M - A)
        else: A[masque] = A[masque] + lam * (M[masque] - A[masque])
    return A

# ------------------------------------------------------------------------------------------------------------
# Skinning : chaque os a une matrice de liaison (repère monde au repos, 4×4) et une matrice posée ; un sommet suit
# Σ w_b · M_b · B_b⁻¹ (LBS) ou le mélange de quaternions duaux (DQS, sans perte de volume aux articulations)
def lbs(V, J, Wt, M):
    """V (n,3), J (n,4) indices d'os, Wt (n,4) poids, M (nb,4,4) matrices posée·liaison⁻¹"""
    Vh = np.c_[V, np.ones(len(V))]
    out = np.zeros((len(V), 3))
    for k in range(J.shape[1]):
        Mk = M[J[:, k]]                                   # (n,4,4)
        out += Wt[:, k:k + 1] * np.einsum('nij,nj->ni', Mk, Vh)[:, :3]
    return out

def dq_de_mat(M):
    q = mat_quat(M[:3, :3]); t = M[:3, 3]
    x, y, z, w = q; tx, ty, tz = t
    d = 0.5 * np.array([tx * w + ty * z - tz * y, -tx * z + ty * w + tz * x, tx * y - ty * x + tz * w, -tx * x - ty * y - tz * z])
    return q, d

def dqs(V, J, Wt, M):
    """skinning par quaternions duaux (Kavan 2007), signe aligné sur l'os de plus fort poids"""
    Q = np.array([dq_de_mat(m)[0] for m in M]); D = np.array([dq_de_mat(m)[1] for m in M])
    q0 = Q[J[:, 0]]
    br = np.zeros((len(V), 4)); bd = np.zeros((len(V), 4))
    for k in range(J.shape[1]):
        q = Q[J[:, k]]; d = D[J[:, k]]; s = np.sign((q * q0).sum(1)); s[s == 0] = 1
        br += (Wt[:, k] * s)[:, None] * q; bd += (Wt[:, k] * s)[:, None] * d
    nr = np.linalg.norm(br, axis=1, keepdims=True); br /= nr; bd /= nr
    x, y, z, w = br.T
    # rotation
    R = np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
                  np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                  np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], 1)
    dx, dy, dz, dw = bd.T
    t = 2 * np.stack([-dw * x + dx * w - dy * z + dz * y, -dw * y + dx * z + dy * w - dz * x, -dw * z - dx * y + dy * x + dz * w], -1)
    return np.einsum('nij,nj->ni', R, V) + t

def cc_operateur(F, n, vives=None):
    """Catmull-Clark sous forme d'opérateur LINÉAIRE creux S (n2 × n) : V2 = S @ V (mêmes règles que catmull_clark,
    arêtes vives comprises). Sert à subdiviser positions, poids et attributs d'un coup, et à résoudre des moindres
    carrés « sur la surface lisse » en n'ayant que les sommets grossiers comme inconnues."""
    import scipy.sparse as sp
    vives = set(vives or ())
    E = aretes(F); el = list(E.keys()); eid = {e: i for i, e in enumerate(el)}
    rows, cols, vals = [], [], []
    ne = len(el); nf = len(F); off_e = n; off_f = n + ne
    # points de face
    for i, f in enumerate(F):
        for v in f: rows.append(off_f + i); cols.append(v); vals.append(1.0 / len(f))
    # points d'arête
    for i, e in enumerate(el):
        fs = E[e]
        if len(fs) == 2 and e not in vives:
            for v in e: rows.append(off_e + i); cols.append(v); vals.append(0.25)
            for fi in fs:
                f = F[fi]
                for v in f: rows.append(off_e + i); cols.append(v); vals.append(0.25 / len(f))
        else:
            for v in e: rows.append(off_e + i); cols.append(v); vals.append(0.5)
    vf = defaultdict(list); ve = defaultdict(list)
    for i, f in enumerate(F):
        for v in f: vf[v].append(i)
    for e in el: ve[e[0]].append(e); ve[e[1]].append(e)
    for v in range(n):
        es = ve[v]
        if not es: rows.append(v); cols.append(v); vals.append(1.0); continue
        sharp = [e for e in es if e in vives or len(E[e]) != 2]
        if len(sharp) == 2:
            a = sharp[0][0] if sharp[0][1] == v else sharp[0][1]; b = sharp[1][0] if sharp[1][1] == v else sharp[1][1]
            rows += [v, v, v]; cols += [v, a, b]; vals += [0.75, 0.125, 0.125]
        elif len(sharp) > 2: rows.append(v); cols.append(v); vals.append(1.0)
        else:
            k = len(es)
            # (F + 2R + (k−3)V)/k ; F = moyenne des points de face, R = moyenne des milieux d'arêtes
            for fi in vf[v]:
                f = F[fi]
                for u in f: rows.append(v); cols.append(u); vals.append(1.0 / k / len(vf[v]) / len(f))
            for e in es:
                for u in e: rows.append(v); cols.append(u); vals.append(2.0 / k / len(es) * 0.5)
            rows.append(v); cols.append(v); vals.append((k - 3.0) / k)
    S = sp.csr_matrix((vals, (rows, cols)), shape=(n + ne + nf, n))
    F2, mere = [], []
    for i, f in enumerate(F):
        m = len(f)
        for j in range(m):
            a = f[j]; e_prev = eid[tuple(sorted((f[j - 1], f[j])))]; e_next = eid[tuple(sorted((f[j], f[(j + 1) % m])))]
            F2.append([a, off_e + e_next, off_f + i, off_e + e_prev]); mere.append(i)
    viv2 = set()
    for e in vives:
        m = off_e + eid[e]; viv2.add(tuple(sorted((e[0], m)))); viv2.add(tuple(sorted((e[1], m))))
    return S, F2, viv2, np.array(mere)

def cc2_operateur(F, n, vives=None):
    """deux niveaux de Catmull-Clark : S = S2·S1, faces, arêtes vives, et face grossière mère de chaque face fine"""
    S1, F1, v1, m1 = cc_operateur(F, n, vives)
    S2, F2, v2, m2 = cc_operateur(F1, S1.shape[0], v1)
    return (S2 @ S1).tocsr(), F2, v2, m1[m2]

def coupe(V, T, o, n, ref=None, rmax=2.5):
    """section du maillage (V, T) par le plan (o, n) : renvoie la boucle (composante connexe de segments) qui entoure
    le point o (ou la plus proche de ref), sous forme de points (m,3). Les extrémités de segments sont repérées par
    l'arête du maillage coupée, ce qui recolle exactement les segments voisins."""
    d = (V - o) @ n
    s = np.sign(d[T]); s[s == 0] = 1
    tri = np.where(~((s[:, 0] == s[:, 1]) & (s[:, 1] == s[:, 2])))[0]
    if len(tri) == 0: return np.zeros((0, 3))
    pts, keys, segs = [], {}, []
    def pt(a, b):
        k = (a, b) if a < b else (b, a)
        if k not in keys:
            t = d[k[0]] / (d[k[0]] - d[k[1]]); keys[k] = len(pts); pts.append(V[k[0]] + t * (V[k[1]] - V[k[0]]))
        return keys[k]
    for i in tri:
        a, b, c = T[i]; e = []
        for u, v in ((a, b), (b, c), (c, a)):
            if (d[u] >= 0) != (d[v] >= 0): e.append(pt(u, v))
        if len(e) == 2: segs.append(e)
    pts = np.array(pts)
    # composantes connexes
    par = list(range(len(pts)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for a, b in segs: par[f(a)] = f(b)
    lab = np.array([f(i) for i in range(len(pts))])
    best, bd = None, 1e9
    for l in np.unique(lab):
        P = pts[lab == l]
        if len(P) < 6: continue
        c = P.mean(0); dist = np.linalg.norm(c - (o if ref is None else ref))
        if np.linalg.norm(P - o, axis=1).min() > rmax: continue
        if dist < bd: bd, best = dist, P
    return best if best is not None else np.zeros((0, 3))

# ------------------------------------------------------------------------------------------------------------
# Ajouts de la passe de correction (relecture adverse du 19 octobre 2026)
def tri_courts(V, F):
    """quads → 2 triangles par la diagonale la plus COURTE (la triangulation exportée dans le GLB : les mesures de
    dièdres et de triangles retournés sont faites sur ces triangles-là, pas sur un éventail arbitraire)"""
    F = np.asarray(F); a, b, c, d = F.T
    m = np.linalg.norm(V[a] - V[c], axis=1) <= np.linalg.norm(V[b] - V[d], axis=1)
    T1 = np.where(m[:, None], np.stack([a, b, c], 1), np.stack([b, c, d], 1))
    T2 = np.where(m[:, None], np.stack([a, c, d], 1), np.stack([b, d, a], 1))
    return np.concatenate([T1, T2]).astype(np.int64)

def paires_triangles(T):
    """arêtes intérieures (n, 2) et leurs deux triangles (n, 2)"""
    E = defaultdict(list)
    for f, (a, b, c) in enumerate(T):
        for u, v in ((a, b), (b, c), (c, a)): E[(min(u, v), max(u, v))].append(f)
    ks = [k for k, v in E.items() if len(v) == 2]
    return np.array(ks, np.int64), np.array([E[k] for k in ks], np.int64)

def normales_faces(V, T):
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]); return nz(n)

def diedres_tri(V, T, P=None):
    """angle (degrés) entre les normales des deux triangles de chaque arête intérieure"""
    e, f = paires_triangles(T) if P is None else P; n = normales_faces(V, T)
    return e, np.degrees(np.arccos(np.clip((n[f[:, 0]] * n[f[:, 1]]).sum(1), -1, 1)))

def triangles_retournes(V, T):
    """triangles dont la normale s'oppose à la moyenne des normales lissées de leurs sommets (repli de la peau)"""
    n = normales_faces(V, T); N = normales(V, T)
    return np.where((n * N[T].mean(1)).sum(1) < 0)[0]

def laplacien(nbr, n):
    """laplacien uniforme du graphe des arêtes (lignes de somme nulle)"""
    import scipy.sparse as sp
    rows, cols, vals = [], [], []
    for i, nb in enumerate(nbr):
        rows.append(i); cols.append(i); vals.append(1.0)
        for j in nb: rows.append(i); cols.append(j); vals.append(-1.0 / len(nb))
    return sp.csr_matrix((vals, (rows, cols)), shape=(n, n))

def biharmonique(L, omega, fixe, val):
    """champ scalaire δ minimisant ‖L δ‖² sur les sommets de omega, δ = val sur fixe, 0 hors de omega : interpolation
    lisse (C¹) entre des contraintes, sans pli à leur bord (le laplacien seul, harmonique, laisse un pli)"""
    import scipy.sparse.linalg as spl
    n = L.shape[0]; libre = omega & ~fixe; il = np.where(libre)[0]; ifx = np.where(fixe)[0]; rows = np.where(omega)[0]
    out = np.zeros(n); out[ifx] = val[ifx]
    if len(il):
        A = L[rows][:, il]; B = L[rows][:, ifx]
        out[il] = spl.spsolve((A.T @ A).tocsc(), A.T @ (-(B @ val[ifx])))
    return out

def dqs_rt(V, J, Wt, M):
    """quaternions duaux comme dqs(), mais renvoie aussi la rotation (n, 3, 3) de chaque sommet : un déplacement
    voulu dans la pose se ramène au repos par Rᵀ (morph targets correctifs)"""
    Q = np.array([dq_de_mat(m)[0] for m in M]); D = np.array([dq_de_mat(m)[1] for m in M])
    q0 = Q[J[:, 0]]
    br = np.zeros((len(V), 4)); bd = np.zeros((len(V), 4))
    for k in range(J.shape[1]):
        q = Q[J[:, k]]; d = D[J[:, k]]; s = np.sign((q * q0).sum(1)); s[s == 0] = 1
        br += (Wt[:, k] * s)[:, None] * q; bd += (Wt[:, k] * s)[:, None] * d
    nr = np.linalg.norm(br, axis=1, keepdims=True); br /= nr; bd /= nr
    x, y, z, w = br.T
    R = np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
                  np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                  np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], 1)
    dx, dy, dz, dw = bd.T
    t = 2 * np.stack([-dw * x + dx * w - dy * z + dz * y, -dw * y + dx * z + dy * w - dz * x, -dw * z - dx * y + dy * x + dz * w], -1)
    return np.einsum('nij,nj->ni', R, V) + t, R
