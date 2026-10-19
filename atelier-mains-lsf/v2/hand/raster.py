"""Rendu de contrôle rapide, entièrement en numpy (pas d'OpenGL dans ce conteneur) : z-buffer EXACT par pixel.

    img = Vue(V, T, R, taille, centre, echelle).ombre(...)   ou   rendu(V, T, R, ...)

Chaque triangle est rastérisé sur sa boîte englobante (couples triangle × pixel générés d'un bloc, par paquets),
puis on garde, pour chaque pixel, le fragment le plus proche de l'œil (tri lexicographique). On obtient le tampon
d'identité (triangle vu par pixel), la profondeur et les coordonnées barycentriques : de quoi ombrer en normales
lissées, tracer la silhouette (saut de profondeur), un fil de fer des seuls triangles VUS, et colorer des régions.
Mesuré : main de 45 000 triangles à 900 px ≈ 1 s.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

POLICE = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'   # police avec accents (la police par défaut de PIL n'a pas « é »)
def police(t=14):
    try: return ImageFont.truetype(POLICE, t)
    except Exception: return ImageFont.load_default()

def vues():
    """matrices de vue (lignes = axe écran x, axe écran y, direction VERS l'œil), repère du contrat :
    doigts +Y, paume +Z, pouce +X"""
    s = np.sqrt(0.5)
    V = {'paume': [[1, 0, 0], [0, 1, 0], [0, 0, 1]],                     # caméra en +Z (vue « Paume (face) »)
         'dos': [[-1, 0, 0], [0, 1, 0], [0, 0, -1]],
         'profil_radial': [[0, 0, -1], [0, 1, 0], [1, 0, 0]],            # caméra en +X (côté pouce)
         'profil_ulnaire': [[0, 0, 1], [0, 1, 0], [-1, 0, 0]],
         'dessus': [[1, 0, 0], [0, 0, -1], [0, 1, 0]],                   # caméra en +Y : bouts des doigts vers l'œil
         'dessous': [[1, 0, 0], [0, 0, 1], [0, -1, 0]]}
    V = {k: np.array(v, float) for k, v in V.items()}
    # trois quarts : dos tourné de 35° vers le pouce et incliné de 25° vers le haut
    def rot(ax, a):
        a = np.radians(a); c, s_ = np.cos(a), np.sin(a)
        if ax == 'x': return np.array([[1, 0, 0], [0, c, -s_], [0, s_, c]])
        if ax == 'y': return np.array([[c, 0, s_], [0, 1, 0], [-s_, 0, c]])
        return np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])
    V['dos_34'] = V['dos'] @ rot('y', -35) @ rot('x', 20)
    V['paume_34'] = V['paume'] @ rot('y', -35) @ rot('x', -15)
    return V

def normales_sommets(V, T):
    n = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])     # pondérées par l'aire
    N = np.zeros_like(V)
    for k in range(3): np.add.at(N, T[:, k], n)
    return N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)

class Vue:
    def __init__(self, V, T, R, taille=700, centre=None, echelle=None, marge=0.44, hauteur=None):
        self.V = np.asarray(V, float); self.T = np.asarray(T, np.int64); self.R = np.asarray(R, float)
        W = taille; H = hauteur or taille; self.W, self.H = W, H
        P = self.V @ self.R.T
        c = P.mean(0) if centre is None else np.asarray(centre, float) @ self.R.T
        if echelle is None:
            ext = max(np.abs(P[:, 0] - c[0]).max() / W, np.abs(P[:, 1] - c[1]).max() / H)
            echelle = marge / max(ext, 1e-9)
        self.c, self.s = c, echelle
        X = (P[:, 0] - c[0]) * echelle + W / 2; Y = H / 2 - (P[:, 1] - c[1]) * echelle; Z = P[:, 2]
        self.X, self.Y, self.Z = X, Y, Z
        self._raster()

    def proj(self, p):
        q = (np.asarray(p, float) @ self.R.T)
        return np.stack([(q[..., 0] - self.c[0]) * self.s + self.W / 2, self.H / 2 - (q[..., 1] - self.c[1]) * self.s], -1)

    def _raster(self):
        T, X, Y, Z, W, H = self.T, self.X, self.Y, self.Z, self.W, self.H
        x0 = np.clip(np.floor(X[T].min(1)).astype(np.int64), 0, W - 1); x1 = np.clip(np.ceil(X[T].max(1)).astype(np.int64), 0, W - 1)
        y0 = np.clip(np.floor(Y[T].min(1)).astype(np.int64), 0, H - 1); y1 = np.clip(np.ceil(Y[T].max(1)).astype(np.int64), 0, H - 1)
        bw = x1 - x0 + 1; bh = y1 - y0 + 1
        ok = (X[T].max(1) >= 0) & (X[T].min(1) < W) & (Y[T].max(1) >= 0) & (Y[T].min(1) < H)
        n = np.where(ok, bw * bh, 0)
        zbuf = np.full(W * H, -np.inf); idb = np.full(W * H, -1, np.int64); bary = np.zeros((W * H, 3))
        tri_ids = np.nonzero(n)[0]
        # paquets d'environ 4 M de couples
        cs = np.cumsum(n[tri_ids]); start = 0
        while start < len(tri_ids):
            base = cs[start - 1] if start > 0 else 0
            stop = int(np.searchsorted(cs, base + 4_000_000, side='right'))
            stop = max(stop, start + 1)
            ids = tri_ids[start:stop]; nn = n[ids]
            rep = np.repeat(ids, nn)
            off = np.arange(nn.sum()) - np.repeat(np.cumsum(nn) - nn, nn)
            px = x0[rep] + off % bw[rep]; py = y0[rep] + off // bw[rep]
            fx = px + 0.5; fy = py + 0.5
            a, b, c = T[rep, 0], T[rep, 1], T[rep, 2]
            d = (Y[b] - Y[c]) * (X[a] - X[c]) + (X[c] - X[b]) * (Y[a] - Y[c])
            d = np.where(np.abs(d) < 1e-12, 1e-12, d)
            l0 = ((Y[b] - Y[c]) * (fx - X[c]) + (X[c] - X[b]) * (fy - Y[c])) / d
            l1 = ((Y[c] - Y[a]) * (fx - X[c]) + (X[a] - X[c]) * (fy - Y[c])) / d
            l2 = 1 - l0 - l1
            ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
            px, py, rep = px[ins], py[ins], rep[ins]; l0, l1, l2 = l0[ins], l1[ins], l2[ins]
            z = l0 * Z[T[rep, 0]] + l1 * Z[T[rep, 1]] + l2 * Z[T[rep, 2]]
            pix = py * W + px
            o = np.lexsort((-z, pix)); pix, z = pix[o], z[o]
            first = np.ones(len(pix), bool); first[1:] = pix[1:] != pix[:-1]
            sel = o[first]; pp = pix[first]; zz = z[first]
            better = zz > zbuf[pp]
            pp, sel, zz = pp[better], sel[better], zz[better]
            zbuf[pp] = zz; idb[pp] = rep[sel]; bary[pp] = np.stack([l0[sel], l1[sel], l2[sel]], 1)
            start = stop
        self.zbuf = zbuf.reshape(H, W); self.idb = idb.reshape(H, W); self.bary = bary.reshape(H, W, 3)
        self.masque = self.idb >= 0

    def interp(self, A):
        """interpole un attribut de sommet (n, k) sur les pixels vus"""
        A = np.asarray(A, float); A2 = A if A.ndim == 2 else A[:, None]
        out = np.zeros((self.H, self.W, A2.shape[1]))
        m = self.masque; t = self.T[self.idb[m]]; b = self.bary[m]
        out[m] = b[:, 0:1] * A2[t[:, 0]] + b[:, 1:2] * A2[t[:, 1]] + b[:, 2:3] * A2[t[:, 2]]
        return out if A.ndim == 2 else out[..., 0]

    def image(self, couleur=(0, 161, 154), couleurs=None, lumiere=(0.35, 0.45, 1.0), fond=(255, 255, 255),
              lisse=True, contour=True, fil=False, seuil_saut=None, ambiant=0.38):
        """ombrage de Lambert (normales lissées), couleurs de sommet facultatives (n,3), contour par saut de profondeur"""
        N = normales_sommets(self.V, self.T)
        if lisse: n = self.interp(N @ self.R.T)
        else:
            fn = np.cross(self.V[self.T[:, 1]] - self.V[self.T[:, 0]], self.V[self.T[:, 2]] - self.V[self.T[:, 0]]) @ self.R.T
            n = np.zeros((self.H, self.W, 3)); n[self.masque] = fn[self.idb[self.masque]]
        n /= np.linalg.norm(n, axis=2, keepdims=True) + 1e-12
        L = np.asarray(lumiere, float); L /= np.linalg.norm(L)
        sh = np.clip(np.abs(n @ L) if False else n @ L, 0, 1)
        sh = np.where(n[..., 2] < 0, 0.15, sh)       # face arrière vue (maillage ouvert) : sombre
        base = self.interp(np.asarray(couleurs, float)) if couleurs is not None else np.broadcast_to(np.asarray(couleur, float), (self.H, self.W, 3))
        img = np.empty((self.H, self.W, 3)); img[:] = fond
        m = self.masque
        img[m] = base[m] * (ambiant + (1 - ambiant) * sh[m][:, None])
        if fil:
            b = self.bary; w = 0.9 / max(1.0, 1.0)
            # largeur du fil en barycentrique ≈ 1 px / hauteur du triangle à l'écran
            T = self.T; X, Y = self.X, self.Y
            e = np.stack([np.hypot(X[T[:, 1]] - X[T[:, 2]], Y[T[:, 1]] - Y[T[:, 2]]), np.hypot(X[T[:, 2]] - X[T[:, 0]], Y[T[:, 2]] - Y[T[:, 0]]),
                          np.hypot(X[T[:, 0]] - X[T[:, 1]], Y[T[:, 0]] - Y[T[:, 1]])], 1)
            area2 = np.abs((X[T[:, 1]] - X[T[:, 0]]) * (Y[T[:, 2]] - Y[T[:, 0]]) - (X[T[:, 2]] - X[T[:, 0]]) * (Y[T[:, 1]] - Y[T[:, 0]]))
            h = area2[:, None] / (e + 1e-9)          # hauteurs du triangle (px) relatives à chaque sommet opposé
            hh = np.zeros((self.H, self.W, 3)); hh[m] = h[self.idb[m]]
            on = m & ((b * hh) < 0.6).any(2)
            img[on] = img[on] * 0.55
        if contour:
            z = self.zbuf.copy(); z[~m] = -1e9
            sj = seuil_saut if seuil_saut is not None else 0.25     # cm
            ed = np.zeros_like(m)
            for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
                a = z; b2 = np.roll(np.roll(z, -dy, 0), -dx, 1)
                j = np.abs(a - b2) > sj
                ed |= j & (m | np.roll(np.roll(m, -dy, 0), -dx, 1))
            img[ed] = (20, 20, 20)
        return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))

def planche(images, titres, cols=None, pad=8, titre=None, taille_police=15):
    cols = cols or len(images); w = max(i.width for i in images); h = max(i.height for i in images)
    rows = (len(images) + cols - 1) // cols; top = 30 if titre else 0
    S = Image.new('RGB', (cols * (w + pad) + pad, top + rows * (h + pad + 22) + pad), 'white'); dr = ImageDraw.Draw(S)
    f = police(taille_police)
    if titre: dr.text((pad, 6), titre, fill='black', font=police(taille_police + 3))
    for k, (im, lab) in enumerate(zip(images, titres)):
        r, cc = divmod(k, cols); x = pad + cc * (w + pad); y = top + pad + r * (h + pad + 22)
        S.paste(im, (x, y + 22)); dr.text((x + 4, y + 3), lab, fill='black', font=f)
    return S
