"""Main 3D « fidèle au dessin » : phalanges rigides dont le volume vient de la silhouette du dessin paume,
texturées devant par le dessin paume (projection exacte) et derrière par le dessin dos recalé (TPS).
Usage: python3 -I rig3d.py <dossier_images> <dossier_sortie> [preview]
"""
import sys, os, json, base64, io
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from scipy import ndimage

SRC, OUT = sys.argv[1], sys.argv[2]
PREVIEW = len(sys.argv) > 3
os.makedirs(OUT, exist_ok=True)

GREEN = np.array([0, 161, 154], float)    # vert du logo INJS
NAILG = np.array([150, 220, 214], float)

def recolor(rgb, skin, nails):
    SKIN = np.array(skin, float)
    r, g, b = [rgb[..., i].astype(float) for i in range(3)]
    L = 0.299 * r + 0.587 * g + 0.114 * b
    Ls = 0.299 * SKIN[0] + 0.587 * SKIN[1] + 0.114 * SKIN[2]
    sat = np.clip((r - b) / (SKIN[0] - SKIN[2]), 0, 1.3)
    ratio = np.clip(L / Ls, 0, 1.2)
    nailness = (np.clip((ratio - sat - 0.2) / 0.25, 0, 1) * (sat > 0.2)) if nails else np.zeros_like(L)
    col = GREEN[None, None] * np.clip(ratio, 0, 1)[..., None] * (1 - nailness[..., None]) + NAILG[None, None] * np.clip(ratio / 1.06, 0, 1)[..., None] * nailness[..., None]
    ag = np.clip(1 - L / 255, 0, 1); ag = np.where(ag < 0.06, 0, (ag - 0.06) / 0.94)
    is_skin = sat > 0.22
    out = np.zeros(rgb.shape[:2] + (4,), float)
    out[..., :3] = np.where(is_skin[..., None], col, 0) / 255.0
    out[..., 3] = np.where(is_skin, 1.0, ag)
    return out

def load(name, skin, nails, median=False):
    pil = Image.open(os.path.join(SRC, name)).convert('RGB')
    if median: pil = pil.filter(ImageFilter.MedianFilter(5))
    return recolor(np.array(pil), skin, nails)

P = load('paume.jpg', [240, 190, 155], False, True)     # dessin paume (référence géométrique)
Dd = load('dos.png', [242, 192, 158], True)              # dessin dos
H, W = P.shape[:2]
mask = P[..., 3] > 0.5

# Chaînes : [MCP, PIP, DIP, bout] (pouce : [MCP, IP, bout])
CP = {  # dessin paume
  'auriculaire': [[312, 440], [256, 374], [217, 331], [158, 252]],
  'annulaire':   [[400, 368], [381, 263], [366, 178], [350, 66]],
  'majeur':      [[505, 352], [505, 228], [507, 128], [507, 18]],
  'index':       [[612, 368], [630, 262], [645, 180], [657, 72]],
  'pouce':       [[718, 566], [770, 480], [872, 402]],
}
CD = {  # dessin dos
  'auriculaire': [[675, 420], [740, 350], [775, 302], [815, 245]],
  'annulaire':   [[585, 372], [600, 235], [612, 155], [624, 68]],
  'majeur':      [[478, 348], [483, 222], [480, 118], [478, 14]],
  'index':       [[362, 388], [352, 240], [345, 155], [330, 62]],
  'pouce':       [[258, 520], [205, 440], [118, 375]],
}
HW = {'auriculaire': 40, 'annulaire': 42, 'majeur': 45, 'index': 44, 'pouce': 56}
# repères de la paume (paume -> dos ; gauche/droite inversés)
PALM_LM = [((343, 1008), (593, 960)), ((633, 1008), (317, 960)), ((360, 790), (588, 780)), ((632, 775), (345, 770)),
           ((298, 600), (668, 600)), ((742, 660), (242, 620)), ((680, 522), (298, 490)), ((500, 900), (455, 880)), ((500, 600), (455, 560))]

def edge(img_a, c, n, lim):
    """distance du point c au bord de la silhouette dans la direction n (None si pas trouvé)"""
    for d in range(0, int(lim)):
        x, y = int(round(c[0] + n[0] * d)), int(round(c[1] + n[1] * d))
        if x < 0 or y < 0 or x >= img_a.shape[1] or y >= img_a.shape[0] or img_a[y, x] < 0.5: return d
    return None

def frame(pts, i, side_ref):
    a, b = np.array(pts[i], float), np.array(pts[min(i + 1, len(pts) - 1)], float)
    if i == len(pts) - 1: a, b = np.array(pts[i - 1], float), np.array(pts[i], float)
    u = (b - a) / np.hypot(*(b - a)); n = np.array([-u[1], u[0]])
    if n @ side_ref < 0: n = -n
    return u, n

# --- correspondances pour le recalage du dessin dos sur le dessin paume
src, dst = [], []
for k in CP:
    ref_p = np.array([0, 1.]) if k == 'pouce' else np.array([1., 0])
    ref_d = np.array([0, 1.]) if k == 'pouce' else np.array([-1., 0])
    for i in range(len(CP[k])):
        src.append(CP[k][i]); dst.append(CD[k][i])
        if i < len(CP[k]) - 1:
            for sgn in (1, -1):
                _, npal = frame(CP[k], i, ref_p); _, ndor = frame(CD[k], i, ref_d)
                ep = edge(P[..., 3], CP[k][i], sgn * npal, HW[k] * 1.5); ed = edge(Dd[..., 3], CD[k][i], sgn * ndor, HW[k] * 1.5)
                if ep and ed:
                    src.append(list(np.array(CP[k][i]) + sgn * npal * ep)); dst.append(list(np.array(CD[k][i]) + sgn * ndor * ed))
for a, b in PALM_LM: src.append(a); dst.append(b)
src, dst = np.array(src, float), np.array(dst, float)

def tps_fit(s, d, reg=2e-4):
    s = s / 1000.0; N = len(s)
    r2 = ((s[:, None] - s[None]) ** 2).sum(-1); K = np.where(r2 > 0, r2 * np.log(r2 + 1e-12), 0) + reg * np.eye(N)
    Pm = np.hstack([np.ones((N, 1)), s]); L = np.zeros((N + 3, N + 3)); L[:N, :N] = K; L[:N, N:] = Pm; L[N:, :N] = Pm.T
    rhs = np.zeros((N + 3, 2)); rhs[:N] = d
    return s, np.linalg.solve(L, rhs)
def tps_eval(model, q):
    s, coef = model; q = q / 1000.0; out = np.zeros((len(q), 2))
    for i0 in range(0, len(q), 200000):
        qq = q[i0:i0 + 200000]; r2 = ((qq[:, None] - s[None]) ** 2).sum(-1); U = np.where(r2 > 0, r2 * np.log(r2 + 1e-12), 0)
        out[i0:i0 + 200000] = U @ coef[:len(s)] + coef[len(s)] + qq @ coef[len(s) + 1:]
    return out

tps = tps_fit(src, dst)
yy, xx = np.mgrid[0:H, 0:W]
m = tps_eval(tps, np.stack([xx.ravel(), yy.ravel()], 1).astype(float))
mx, my = m[:, 0].reshape(H, W), m[:, 1].reshape(H, W)
# échantillonnage bilinéaire du dessin dos
def bilinear(img, x, y):
    x = np.clip(x, 0, img.shape[1] - 1.001); y = np.clip(y, 0, img.shape[0] - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int); fx, fy = (x - x0)[..., None], (y - y0)[..., None]
    return img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy
# le trait de contour du dessin dos peut tomber à l'intérieur de la silhouette paume (les deux dessins n'ont pas exactement la même forme) :
# on le repère dans le dessin dos lui-même, puis on le transporte
dmask = Dd[..., 3] > 0.5
ddist = ndimage.distance_transform_edt(dmask); ddark = Dd[..., :3].mean(-1) < 0.3
dband_wide = dmask & (ddist <= 34) & ddark
# trait de contour (≈ 7 px d'épaisseur) effacé dans le dessin dos AVANT recalage, halo anti-crénelé compris : sinon le
# remplissage par le plus proche voisin recopie ce halo gris (et, là où l'ongle touche le contour, alterne ongle/peau/gris)
# → stries radiales. Les bouts des traits d'ongle qui rejoignent le contour (≤ 13 px du bord) partent aussi, sinon ils
# s'étirent en taches noires sur le flanc du doigt ; halo d'1 px seulement pour garder le mince coin de peau à côté.
dstroke = dmask & (ddist <= 8) & ddark
dline = dmask & (ddist <= 13) & ddark
dhalo = (ndimage.binary_dilation(dstroke, iterations=2) & dmask & (ddist <= 10)) | (ndimage.binary_dilation(dline, iterations=1) & dmask & (ddist <= 14))
dgood = dmask & ~dhalo
_, (hy_, hx_) = ndimage.distance_transform_edt(~dgood, return_indices=True)
Dc = Dd.copy(); Dc[dhalo, :3] = Dd[hy_[dhalo], hx_[dhalo], :3]
DA = bilinear(Dc, mx, my)                      # dessin dos, dans le repère du dessin paume
# là où le dos recalé tombe hors de sa silhouette (léger décalage entre les deux dessins), on prolonge la peau voisine
bx_ = np.clip(np.round(mx).astype(int), 0, Dd.shape[1] - 1); by_ = np.clip(np.round(my).astype(int), 0, Dd.shape[0] - 1)
DM = bilinear(dmask[..., None].astype(float), mx, my)[..., 0]   # silhouette dos transportée (< 1 : pixel mêlé au fond hors silhouette)
bad = mask & (DM < 0.98)
_PENDING_PALM_BAND = dband_wide[by_, bx_]
okd = mask & ~bad
if bad.any():
    _, (by, bx) = ndimage.distance_transform_edt(~okd, return_indices=True)
    DA[bad, :3] = DA[by[bad], bx[bad], :3]
DA[..., 3] = np.where(mask, 1, 0)

# --- le trait de contour du dessin est retiré des textures : en 3D, il est redessiné par la silhouette (sinon il apparaît
#     comme une bande noire peinte sur la tranche de la main vue de profil)
OUTW = 6
dist_in = ndimage.distance_transform_edt(mask)
def strip_outline(img):
    lum = img[..., :3].mean(-1)
    band = mask & (dist_in <= OUTW + 7) & (lum < 0.3)
    good = mask & ~band & (dist_in > 2)
    _, (iy2, ix2) = ndimage.distance_transform_edt(~good, return_indices=True)
    out = img.copy(); out[band, :3] = img[iy2[band], ix2[band], :3]
    return out
P_tex = strip_outline(P)
# (DA : contour déjà retiré dans le dessin dos, avant recalage)

# --- découpe : à qui appartient chaque pixel du dessin paume ?
owner = np.full((H, W), '', dtype=object); best = np.full((H, W), 1e9)
XX, YY = xx.astype(float), yy.astype(float)
for k, pts in CP.items():
    pts = np.array(pts, float); hw = HW[k]; ns = len(pts) - 1
    for i in range(ns):
        a, b = pts[i], pts[i + 1]; v = b - a; ln = np.hypot(*v); u = v / ln; n = np.array([-u[1], u[0]])
        t = (XX - a[0]) * u[0] + (YY - a[1]) * u[1]; s = np.abs((XX - a[0]) * n[0] + (YY - a[1]) * n[1])
        hi = ln + (hw * 1.6 if i == ns - 1 else 0)
        inside = mask & (t >= 0) & (t < hi) & (s <= hw * 1.3); closer = inside & (s < best)
        owner[closer] = f'{k}.{i}'; best[closer] = s[closer]
finger = mask & (owner != '')
# le dos de la main dessiné n'a aucun trait intérieur : tout noir qui y traîne vient du recalage
bad2 = mask & ~finger & (_PENDING_PALM_BAND | (DA[..., :3].mean(-1) < 0.2))
if bad2.any():
    ok2 = mask & ~bad2 & (DA[..., :3].mean(-1) >= 0.25)
    _, (cy2, cx2) = ndimage.distance_transform_edt(~ok2, return_indices=True)
    DA[bad2, :3] = DA[cy2[bad2], cx2[bad2], :3]
palm = mask & ~finger
# on ne garde que le gros morceau de paume
lab, nl = ndimage.label(palm); sizes = ndimage.sum(np.ones_like(lab), lab, range(1, nl + 1)); palm = lab == (1 + int(np.argmax(sizes)))

# --- profils des phalanges (largeurs mesurées sur le dessin paume)
segs = {}
INNER = ndimage.binary_erosion(mask, iterations=OUTW).astype(float)   # silhouette intérieure (sans le trait)
for k, pts in CP.items():
    pts = np.array(pts, float); hw = HW[k]; ns = len(pts) - 1; out = []
    for i in range(ns):
        a, b = pts[i], pts[i + 1]; v = b - a; ln = np.hypot(*v); u = v / ln; n = np.array([-u[1], u[0]])
        last = i == ns - 1
        if last:   # longueur réelle jusqu'au bout du doigt
            tend = ln * .5
            while tend < ln + hw * 2 and INNER[int(round(a[1] + u[1] * tend)), int(round(a[0] + u[0] * tend))] > .5: tend += 1
        else: tend = ln
        # échantillonnage serré (peau continue) ; au bout du doigt, encore plus serré pour un arrondi propre
        if last:
            T = tend; ts = T * np.sin(np.linspace(0, 1, 30) * np.pi / 2)
        else:
            ts = np.linspace(0, tend, max(10, int(ln / 8)))
        wl, wr = [], []
        for t in ts:
            c = a + u * t
            wr.append(edge(INNER, c, n, hw * 1.35)); wl.append(edge(INNER, c, -n, hw * 1.35))
        def fill(w):
            w = list(w); good = [j for j, x in enumerate(w) if x is not None and x > 2 and not (last and j > len(w) * 0.7)]
            if not good: return [hw] * len(w)
            for j in range(len(w)):
                if (w[j] is None and not (last and j > len(w) * 0.7)) or (w[j] is not None and w[j] <= 2 and not (last and j > len(w) * 0.6)):
                    w[j] = w[min(good, key=lambda g: abs(g - j))]
            return [float(x) if x is not None else 0.0 for x in w]
        wl, wr = fill(wl), fill(wr)
        wl = [max(0.0, w) for w in wl]; wr = [max(0.0, w) for w in wr]
        if last: wl[-1] = wr[-1] = 0.0
        out.append({'a': a.tolist(), 'u': u.tolist(), 'len': float(ln), 'ts': ts.tolist(), 'wl': wl, 'wr': wr, 'tip': last})
    segs[k] = out

# --- paume : nappe de hauteur (épaisseur arrondie, creux de la paume, éminences)
full = mask
dist_full = ndimage.distance_transform_edt(full)
dist_cut = ndimage.distance_transform_edt(~finger)
circ = lambda x: np.sqrt(np.clip(1 - (1 - np.clip(x, 0, 1)) ** 2, 0, 1))
def gauss(cx, cy, s): return np.exp(-((XX - cx) ** 2 + (YY - cy) ** 2) / (2 * s * s))
wr_ = 1 / (1 + np.exp(-(YY - 770) / 45.0))                      # 0 dans la paume, 1 dans l'avant-bras
Rr = 62 * (1 - wr_) + 115 * wr_
round_ = circ((dist_full - OUTW) / Rr) * circ(dist_cut / 34.0)
hf = (52 * (1 - wr_) + 88 * wr_ + 18 * gauss(675, 650, 75) + 10 * gauss(365, 640, 60) - 12 * gauss(500, 560, 85)) * round_
# côté dos : la paume garde son épaisseur jusqu'aux têtes des métacarpiens (relief des jointures quand on serre le poing)
round_b = circ((dist_full - OUTW) / Rr) * (0.75 + 0.25 * circ(dist_cut / 34.0))
hb = (46 * (1 - wr_) + 84 * wr_ + 8 * gauss(500, 420, 140)) * round_b
# à la racine des doigts, la paume prend l'épaisseur du doigt (coussinets palmaires, têtes des métacarpiens)
hf = np.minimum(hf, 34 + 0.55 * dist_cut); hb = np.minimum(hb, 24 + 0.55 * dist_cut)
inner = ndimage.binary_erosion(mask, iterations=OUTW)
ext = (palm | (ndimage.binary_dilation(palm, iterations=10) & mask)) & inner   # la paume rentre un peu sous la base des doigts
STEP = 5
gy, gx = np.mgrid[0:H:STEP, 0:W:STEP]
ok = ndimage.binary_dilation(ext, iterations=STEP)[gy, gx]
_, (iy, ix) = ndimage.distance_transform_edt(~ext, return_indices=True)
sx, sy = ix[gy, gx], iy[gy, gx]            # sommets hors paume ramenés sur le bord
vid = -np.ones(ok.shape, int); vid[ok] = np.arange(ok.sum())
verts = np.stack([sx[ok], sy[ok]], 1)
zf = np.where(ext[sy[ok], sx[ok]], hf[sy[ok], sx[ok]], 0) * (ext[gy, gx][ok] | True)
zb = np.where(ext[sy[ok], sx[ok]], hb[sy[ok], sx[ok]], 0)
# un sommet ramené depuis l'extérieur est sur la silhouette : hauteur nulle
outside = ~ext[gy, gx][ok]; zf[outside] = 0; zb[outside] = 0   # sur la silhouette, avant et arrière se rejoignent exactement
# bord lissé : les sommets de la silhouette sont moyennés avec leurs voisins de bord (pas d'escalier sur le contour)
rim = np.zeros(ok.shape, bool); rim[ok] = outside
vx = np.zeros(ok.shape); vy = np.zeros(ok.shape); vx[ok] = verts[:, 0]; vy[ok] = verts[:, 1]
for _ in range(1):
    sx_ = vx.copy(); sy_ = vy.copy(); cnt = np.ones(ok.shape)
    for dy_ in (-1, 0, 1):
        for dx_ in (-1, 0, 1):
            if dx_ == 0 and dy_ == 0: continue
            nb = np.roll(np.roll(rim, dy_, 0), dx_, 1)
            m_ = rim & nb
            sx_[m_] += np.roll(np.roll(vx, dy_, 0), dx_, 1)[m_]; sy_[m_] += np.roll(np.roll(vy, dy_, 0), dx_, 1)[m_]; cnt[m_] += 1
    vx = np.where(rim, .5 * vx + .5 * sx_ / cnt, vx); vy = np.where(rim, .5 * vy + .5 * sy_ / cnt, vy)
verts = np.stack([np.round(vx[ok]), np.round(vy[ok])], 1).astype(int)
tris = []
R, C = ok.shape
for r in range(R - 1):
    for c in range(C - 1):
        a, b, cc, d = vid[r, c], vid[r, c + 1], vid[r + 1, c], vid[r + 1, c + 1]
        for t in ((a, cc, b), (b, cc, d)):
            if min(t) >= 0: tris.append(t)
tris = np.array(tris, np.uint32)
# peau de la paume entraînée par la base des doigts (jointures, palmures) : poids selon la distance à chaque doigt
FW = []
for k in ['index', 'majeur', 'annulaire', 'auriculaire']:
    dk = ndimage.distance_transform_edt(~(owner == f'{k}.0'))
    x = np.clip(dk[verts[:, 1].clip(0, H - 1), verts[:, 0].clip(0, W - 1)] / 55.0, 0, 1)
    FW.append(1 - x * x * (3 - 2 * x))
FW = np.stack(FW, 1); tot = FW.sum(1, keepdims=True); FW = np.where(tot > 1, FW / np.maximum(tot, 1e-6), FW) * 0.85

# =====================================================================================================
# v8 : UNE peau fermée pour toute la main (paume + doigts + pouce), sans raccord.
#  - volume : la silhouette intérieure exacte du dessin paume, gonflée en épaisseur. Doigts : coupe en ellipse
#    (avant DF·r, arrière DB·r, r = demi-largeur locale) ; paume : nappes hf / hb ci-dessus ; fondu entre les deux.
#  - surface fermée extraite par « marching cubes » (aucun trou, aucun boudin, triangles réguliers jusque sur la tranche)
#  - poids de peau lisses vers un squelette anatomique : paume, métacarpien du pouce, 3 phalanges par doigt
#    (la base du doigt pivote à la tête du métacarpien, DEEP sous le pli de la racine du doigt)
# =====================================================================================================
from skimage import measure
DF8, DB8, DBT8 = .92, .70, .58
FINGS = ['index', 'majeur', 'annulaire', 'auriculaire']
M8 = INNER > .5
d8 = ndimage.gaussian_filter(ndimage.distance_transform_edt(M8), 1.0)
# demi-largeur locale r(x) = rayon de la plus grande boule inscrite qui contient x (plafonnée : seuls les doigts s'en servent)
loc = np.zeros((H, W))
for r_ in range(2, 61, 2):
    cov = ndimage.distance_transform_edt(~(d8 >= r_)) <= r_
    loc[cov & M8] = r_
loc = np.maximum(loc, 2)
circ8 = lambda u: np.sqrt(np.clip(1 - (1 - np.clip(u, 0, 1)) ** 2, 0, 1))
# aplatissement du dos au bout des doigts (lit de l'ongle)
tipf = np.zeros((H, W))
for k, pts in CP.items():
    pts = np.array(pts, float); a, b = pts[-2], pts[-1]; u = (b - a) / np.hypot(*(b - a))
    t = ((XX - a[0]) * u[0] + (YY - a[1]) * u[1]) / np.hypot(*(b - a))
    own = np.char.startswith(owner.astype(str), k + '.' + str(len(pts) - 2))
    tipf = np.where(own, np.clip((t - .15) / .35, 0, 1), tipf)
fF = DF8 * loc * circ8(d8 / loc)
fB = (DB8 - (DB8 - DBT8) * tipf) * loc * circ8(d8 / loc)
wfin = np.clip(ndimage.gaussian_filter(finger.astype(float), 6), 0, 1)
# la nappe de la paume, mesurée sur la silhouette intérieure (pour rejoindre exactement la tranche)
roundP = circ8(d8 / Rr) * circ8(dist_cut / 34.0)
hfP = np.minimum((52 * (1 - wr_) + 88 * wr_ + 18 * gauss(675, 650, 75) + 10 * gauss(365, 640, 60) - 12 * gauss(500, 560, 85)) * roundP, 34 + .55 * dist_cut)
hbP = np.minimum((46 * (1 - wr_) + 84 * wr_ + 8 * gauss(500, 420, 140)) * circ8(d8 / Rr) * (.75 + .25 * circ8(dist_cut / 34.0)), 24 + .55 * dist_cut)
front8 = wfin * fF + (1 - wfin) * hfP
back8 = wfin * fB + (1 - wfin) * hbP
out8 = ndimage.distance_transform_edt(~M8)
front8 = np.where(M8, front8, -out8); back8 = np.where(M8, back8, -out8)
# poignet coupé net (le bas du dessin) : on ferme le volume par un fond plat
STEP8 = 5
bottom = np.nonzero(M8.any(1))[0].max()
xs8, ys8 = np.arange(0, W, STEP8), np.arange(0, H, STEP8)
zmin, zmax = -float(back8.max()) - 3 * STEP8, float(front8.max()) + 3 * STEP8
zs8 = np.arange(zmin, zmax + STEP8, STEP8)
Fq, Bq = front8[np.ix_(ys8, xs8)], back8[np.ix_(ys8, xs8)]
vol = np.minimum(Fq[..., None] - zs8[None, None], zs8[None, None] + Bq[..., None])
vol = np.minimum(vol, (bottom - 2 - ys8)[:, None, None].astype(float))          # fond au poignet
vol = np.pad(vol, 1, constant_values=-50)
vv, ff, _, _ = measure.marching_cubes(vol, 0.0)
vv = vv - 1
V8 = np.stack([xs8[0] + vv[:, 1] * STEP8, ys8[0] + vv[:, 0] * STEP8, zmin + vv[:, 2] * STEP8], 1)
# lissage de Taubin léger (efface les facettes du maillage sans rétrécir)
from scipy import sparse
nV = len(V8)
I = np.concatenate([ff[:, 0], ff[:, 1], ff[:, 2], ff[:, 1], ff[:, 2], ff[:, 0]]); Jn = np.concatenate([ff[:, 1], ff[:, 2], ff[:, 0], ff[:, 0], ff[:, 1], ff[:, 2]])
A = sparse.csr_matrix((np.ones(len(I)), (I, Jn)), shape=(nV, nV)); A.data[:] = 1
deg = np.asarray(A.sum(1)).ravel(); Ln = sparse.diags(1 / np.maximum(deg, 1)) @ A
for _ in range(6):
    V8 = V8 + .5 * (Ln @ V8 - V8); V8 = V8 - .53 * (Ln @ V8 - V8)
# orientation des faces : normales vers l'extérieur
fn = np.cross(V8[ff[:, 1]] - V8[ff[:, 0]], V8[ff[:, 2]] - V8[ff[:, 0]])
top = np.argmax(V8[ff].mean(1)[:, 2])
if fn[top, 2] < 0: ff = ff[:, [0, 2, 1]]; fn = -fn
front_face = fn[:, 2] >= 0
ff = np.concatenate([ff[front_face], ff[~front_face]]); nFront = int(front_face.sum())
# l'image a y vers le bas, la 3D y vers le haut (miroir) : on inverse l'ordre des sommets pour garder les faces vers l'extérieur
ff = ff[:, [0, 2, 1]]

# ---------- squelette (pixels du dessin paume ; z = milieu de l'épaisseur) ----------
def zmid(p):
    x, y = int(round(p[0])), int(round(p[1])); return float((front8[y, x] - back8[y, x]) / 2)
def segw0(k):
    sg = segs[k][0]; w = [(a + b) / 2 for a, b in zip(sg['wl'], sg['wr']) if (a + b) / 2 > 4]; return float(np.mean(w))
DEEP8 = {k: .5 * 2 * segw0(k) for k in FINGS}   # tête du métacarpien ≈ ½ largeur de doigt sous le pli de la racine
CMC8 = np.array([652., 748.])
chain8 = {}
for k in FINGS:
    p = np.array(CP[k], float); u = (p[1] - p[0]) / np.hypot(*(p[1] - p[0]))
    chain8[k] = [p[0] - u * DEEP8[k], p[1], p[2], p[3]]
chain8['pouce'] = [CMC8, np.array(CP['pouce'][0], float), np.array(CP['pouce'][1], float), np.array(CP['pouce'][2], float)]
jointZ = {k: [zmid(q) for q in chain8[k][:3]] for k in chain8}

def polyproj(P, pts):
    """abscisse curviligne s (prolongée avant le 1er point) et distance latérale l de chaque point P à la polyligne"""
    best_l = np.full(len(P), 1e9); best_s = np.zeros(len(P)); S0 = 0.
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; L = np.hypot(*(b - a)); u = (b - a) / L
        t = (P[:, 0] - a[0]) * u[0] + (P[:, 1] - a[1]) * u[1]
        tc = t if i == 0 else np.maximum(t, 0)
        tc = np.minimum(tc, L) if i < len(pts) - 2 else tc
        q = a[None] + tc[:, None] * u[None]; l = np.hypot(P[:, 0] - q[:, 0], P[:, 1] - q[:, 1])
        better = l < best_l - 1e-9; best_l[better] = l[better]; best_s[better] = S0 + tc[better]; S0 += L
    return best_s, best_l
def sstep(a, b, x): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
cum = lambda pts: np.concatenate([[0], np.cumsum([np.hypot(*(pts[i + 1] - pts[i])) for i in range(len(pts) - 1)])])

P2 = V8[:, :2]
# région de chaque sommet (pixel intérieur le plus proche)
_, (iy8, ix8) = ndimage.distance_transform_edt(~M8, return_indices=True)
vx = np.clip(np.round(P2[:, 0]).astype(int), 0, W - 1); vy = np.clip(np.round(P2[:, 1]).astype(int), 0, H - 1)
vx, vy = ix8[vy, vx], iy8[vy, vx]
vown = owner[vy, vx].astype(str)
BONES = ['paume', 'pouce.cmc', 'pouce.0', 'pouce.1'] + [f'{k}.{i}' for k in FINGS for i in range(3)]
Wb = np.zeros((nV, len(BONES)))
# demi-largeur du doigt le long de son axe (pour savoir si un point de la paume est « sous » le doigt)
def half_width_at(k, s):
    sg = segs[k]; base = DEEP8[k]; out = np.full(len(s), segw0(k))
    S0 = base
    for g in sg:
        ts = np.array(g['ts']); w = (np.array(g['wl']) + np.array(g['wr'])) / 2
        m = (s >= S0) & (s <= S0 + ts[-1]); out[m] = np.interp(s[m] - S0, ts, w); S0 += g['len'] if not g['tip'] else ts[-1]
    return np.maximum(out, 6)
raw = {}; sK = {}; lat8 = {}
for k in FINGS:
    s, l = polyproj(P2, chain8[k]); w = half_width_at(k, s); sK[k] = s
    # palmure : elle reste surtout avec la paume (sinon, doigt plié, elle rentre dans le doigt voisin)
    r_ = np.where(l <= w + 2, 1.0, np.exp(-((l - w - 2) / 11.0) ** 2))
    own_other = np.array([o != '' and not o.startswith(k + '.') for o in vown])
    own_self = np.char.startswith(vown, k + '.')
    r_ = np.where(own_other, 0, np.where(own_self, 1, r_)); lat8[k] = r_
    raw[k] =r_ * sstep(-.55 * 2 * segw0(k) / 2 * 2, .55 * 2 * segw0(k), s - 0)   # transition à la tête du métacarpien
tot = sum(raw.values()); scale = np.where(tot > 1, 1 / np.maximum(tot, 1e-9), 1)
for k in FINGS:
    c = raw[k] * scale; s = sK[k]; cs = cum(chain8[k]); w0 = segw0(k)
    # zone de passage d'une phalange à l'autre assez large pour que la peau s'arrondisse sur l'articulation (pas de coude)
    t1 = sstep(cs[1] - .85 * w0, cs[1] + .85 * w0, s); t2 = sstep(cs[2] - .75 * w0, cs[2] + .75 * w0, s)
    b = BONES.index(k + '.0'); Wb[:, b] = c * (1 - t1); Wb[:, b + 1] = c * t1 * (1 - t2); Wb[:, b + 2] = c * t1 * t2
# pouce : métacarpien (éminence thénar) puis 2 phalanges
def thenarW8(x, y):
    ax, ay = CP['pouce'][0][0] - CMC8[0], CP['pouce'][0][1] - CMC8[1]; L2 = ax * ax + ay * ay; L = np.sqrt(L2); dx, dy = x - CMC8[0], y - CMC8[1]
    s = (dx * ax + dy * ay) / L2; nx, ny = -ay / L, ax / L
    if nx * (500 - CMC8[0]) + ny * (560 - CMC8[1]) < 0: nx, ny = -nx, -ny
    l = dx * nx + dy * ny
    # éminence thénar : influence large et progressive vers le creux de la paume (pouce rentré sans pliure en « feuille de papier »)
    return sstep(-.12, .78, s) * np.where(l > 0, 1 - sstep(20, 210, l), 1) * (1 - sstep(1.15, 1.6, s) * sstep(10, 60, l))
sT, lT = polyproj(P2, chain8['pouce']); csT = cum(chain8['pouce'])
# influence du pouce continue (pas de marche au bord de la « région pouce ») : éminence thénar OU proximité de l'axe du pouce
wT = np.array([np.mean([(a + b) / 2 for a, b in zip(g['wl'], g['wr']) if a + b > 8]) for g in segs['pouce']]).mean()
latT = np.where(lT <= wT + 2, 1.0, np.exp(-((lT - wT - 2) / 26.0) ** 2))
axT = sstep(csT[1] - 70, csT[1] + 10, sT) * latT
axT = np.where(np.array([o != '' and not o.startswith('pouce.') for o in vown]), 0, axT)
cT = np.maximum(thenarW8(P2[:, 0], P2[:, 1]), axT)
cT = np.minimum(cT, 1 - np.minimum(Wb[:, 4:].sum(1), 1))
tM = sstep(csT[1] - 40, csT[1] + 40, sT); tI = sstep(csT[2] - 32, csT[2] + 32, sT)
Wb[:, 1] = cT * (1 - tM); Wb[:, 2] = cT * tM * (1 - tI); Wb[:, 3] = cT * tM * tI
Wb[:, 0] = np.clip(1 - Wb[:, 1:].sum(1), 0, 1)

# ---------- déformeur en arc (articulations charnières : MCP, IPP, IPD des doigts ; MCP, IP du pouce) ----------
# Dans la zone d'une articulation, chaque section du doigt tourne d'une fraction tau de l'angle, autour d'un centre
# qui glisse : la peau suit un arc de cercle (rayon intérieur jamais négatif), et aux bords de la zone elle rejoint
# exactement l'os rigide (tau = 0 : os proximal, tau = 1 : os distal). Demi-largeur h de la zone : grande côté paume
# (pli sans repli : h >= r.tan(angle max / 2)), petite côté dos (jointure nette, pas de « tuyau »).
X8 = np.stack([V8[:, 0], -V8[:, 1], V8[:, 2]], 1)        # repère 3D du moteur (y en haut), en pixels
nz = lambda v: np.asarray(v, float) / np.linalg.norm(v)
Zj = np.array([0., 0., 1.])
def segu(k, i): u = segs[k][i]['u']; return nz([u[0], -u[1], 0.])
def arcj(C, z, u, f0, tmax, mask, w, dr=.45):
    C = np.array([C[0], -C[1], z]); lat = np.cross(u, f0); rel = X8 - C
    t, d = rel @ u, rel @ f0
    near = mask & (np.abs(t) < 10) & (np.abs(rel @ lat) < w)
    rp, rd = float(np.percentile(d[near], 98)), float(np.percentile(-d[near], 98))
    kf = 1.15 * np.tan(np.radians(tmax) / 2); hp = max(kf * rp, .8 * rp); hd = max(dr * hp, .35 * rp)
    # une fibre plus épaisse que rp (pulpe, coussinet de la paume) a sa propre zone, assez large pour ne jamais se replier
    h = np.maximum(hd + (hp - hd) * sstep(-rd, rp, d), kf * d)
    return {'u': u.tolist(), 'f': f0.tolist(), 'rp': rp, 'rd': rd, 'hp': hp, 'hd': hd, 'kf': kf}, t, h
lin8 = lambda t, h: np.clip((t + h) / (2 * h), 0, 1)
ARC = {}; TAU = {}; HM = {}
for k in FINGS:
    ch = chain8[k]; own = np.char.startswith(vown, k + '.'); w0 = segw0(k); u0, u1, u2 = segu(k, 0), segu(k, 1), segu(k, 2)
    J0, t0, h0 = arcj(ch[0], jointZ[k][0], u0, Zj, 90, np.ones(nV, bool), .6 * w0)
    J1, t1, h1 = arcj(ch[1], jointZ[k][1], nz(u0 + u1), Zj, 105, own, .6 * w0)
    J2, t2, h2 = arcj(ch[2], jointZ[k][2], nz(u1 + u2), Zj, 80, own, .6 * w0)
    # palmure (mince, entre deux doigts) : même zone devant et derrière, sinon la nappe se déchire en pliant
    #   (le plancher anti-repli des fibres épaisses, au-delà de hp, est gardé)
    h0 = np.maximum((J0['hp'] + J0['hd']) / 2 * (1 - lat8[k] ** 2) + h0 * lat8[k] ** 2, np.where(h0 > J0['hp'], h0, 0))
    ARC[k] = [J0, J1, J2]; TAU[k] = (lat8[k] * lin8(t0, h0), lin8(t1, h1), lin8(t2, h2)); HM[k] = h0
# pouce : axes de flexion obliques (comme tAxis dans script.js : lat·sin β + Z·cos β), flexion vers f = n × u
def tflex(u, beta): lat = np.cross(u, Zj); n = nz(lat * np.sin(np.radians(beta)) + Zj * np.cos(np.radians(beta))); return nz(np.cross(n, u))
chT = chain8['pouce']; ownT = np.char.startswith(vown, 'pouce.'); uT0, uT1 = segu('pouce', 0), segu('pouce', 1)
uM = nz([chT[1][0] - chT[0][0], -(chT[1][1] - chT[0][1]), 0])
JM, tM_, hM_ = arcj(chT[1], jointZ['pouce'][1], nz(uM + uT0), tflex(uT0, 45), 55, ownT, 22, .8)   # MCP du pouce : articulation large, dos arrondi
JI, tI_, hI_ = arcj(chT[2], jointZ['pouce'][2], nz(uT0 + uT1), tflex(uT1, 55), 80, ownT, 22, .6)
tM_, tI_ = lin8(tM_, hM_), lin8(tI_, hI_)
ARC['pouce'] = [JM, JI]
# part de chaque chaîne dans le sommet (base du doigt : rampe linéaire, avec la retombée latérale des palmures)
SH = np.stack([TAU[k][0] for k in FINGS], 1)
# palmures : la part de chaque doigt y est lissée sur la peau (les doigts restent fixes), sinon elle passe de 0,3 à 0,7
# en quelques pixels à la limite entre deux doigts et la palmure se plisse en pliant la base
freeP = (vown == '')[:, None]
for _ in range(25): SH = np.where(freeP, Ln @ SH, SH)
tl = SH.sum(1, keepdims=True); SH = np.where(tl > 1, SH / np.maximum(tl, 1e-9), SH)
shT = np.minimum(cT, 1 - np.minimum(SH.sum(1), 1))
SH = np.concatenate([shT[:, None], SH], 1)                 # colonnes : pouce, index, majeur, annulaire, auriculaire
ordc = np.argsort(-SH, 1)[:, :2]; shc = np.take_along_axis(SH, ordc, 1)
c1 = np.where(shc[:, 0] > 1e-4, ordc[:, 0] + 1, 0); c2 = np.where(shc[:, 1] > 1e-4, ordc[:, 1] + 1, 0)
# articulations internes de la chaîne principale (IPP / IPD, ou MCP / IP du pouce), seulement là où la chaîne domine
ta = np.zeros(nV); tb = np.zeros(nV)
for ci, k in enumerate(['pouce'] + FINGS):
    m = c1 == ci + 1
    if k == 'pouce': a_, b_ = tM_, tI_; g_ = sstep(.5, .95, shc[:, 0])
    else: a_, b_ = TAU[k][1], TAU[k][2]; g_ = sstep(.85, 1., shc[:, 0])
    ta[m] = (a_ * g_)[m]; tb[m] = (b_ * g_)[m]
print('arc :', {k: [(round(j['hp']), round(j['hd']), round(j['rp']), round(j['rd'])) for j in ARC[k]] for k in ARC},
      'sommets en zone', int(((ta > 0) & (ta < 1)).sum() + ((tb > 0) & (tb < 1)).sum()))
q16 = lambda a: base64.b64encode(np.round(np.clip(a, 0, 1) * 65535).astype(np.uint16).tobytes()).decode()
arc8 = {'joints': ARC, 'c': base64.b64encode(np.stack([c1, c2], 1).astype(np.uint8).tobytes()).decode(),
        's': q16(shc), 't': q16(np.stack([ta, tb], 1)),
        # demi-largeur de zone de la base du doigt (MCP) des deux chaînes, en demi-pixels
        'hm': base64.b64encode(np.clip(np.round(np.stack([np.choose(np.clip(c, 2, 5) - 2, [HM[k] for k in FINGS]) for c in (c1, c2)], 1) * 2), 0, 255).astype(np.uint8).tobytes()).decode()}
# 4 influences au plus par sommet
order = np.argsort(-Wb, 1)[:, :4]; wt = np.take_along_axis(Wb, order, 1); wt = wt / np.maximum(wt.sum(1, keepdims=True), 1e-9)
w8 = np.round(wt * 255).astype(np.int32); w8[:, 0] += 255 - w8.sum(1)
# partie dominante (survol, traits intérieurs) : paume / pouce / doigt
dom = np.argmax(Wb, 1)
PART = {'paume': 1, 'pouce': 2, 'index': 3, 'majeur': 4, 'annulaire': 5, 'auriculaire': 6}
# un doigt ne commence qu'à sa vraie racine (palmures et éminence = paume) : les traits intérieurs ne s'y dessinent pas
part8 = np.array([PART[o.split('.')[0]] if o else 1 for o in vown], np.uint8)
# couleur de la tranche prise un peu en retrait du bord dessiné (sinon le trait noir déborde sur le flanc)
gy8, gx8 = np.gradient(ndimage.gaussian_filter(d8, 2.0))
gn = np.hypot(gx8, gy8) + 1e-9; dv = d8[vy, vx]; push = np.clip(7 - dv, 0, 7)
UV8 = np.stack([vx + gx8[vy, vx] / gn[vy, vx] * push, vy + gy8[vy, vx] / gn[vy, vx] * push], 1)
mesh8 = {'uv': base64.b64encode(np.round(UV8 * 4).astype(np.int16).tobytes()).decode(), 'n': int(nV), 'xyz': base64.b64encode(np.round(V8 * 4).astype(np.int16).tobytes()).decode(), 'q': 4,
         'idx': base64.b64encode(ff.astype(np.uint16 if nV < 65536 else np.uint32).tobytes()).decode(), 'i32': nV >= 65536,
         'nFront': nFront, 'bi': base64.b64encode(order.astype(np.uint8).tobytes()).decode(), 'bw': base64.b64encode(w8.astype(np.uint8).tobytes()).decode(),
         'part': base64.b64encode(part8.tobytes()).decode(), 'bones': BONES,
         'chain': {k: [list(map(float, p)) for p in chain8[k]] for k in chain8}, 'jz': jointZ, 'arc': arc8}
print('peau v8 : sommets', nV, 'triangles', len(ff))

# ongles : sur une vraie main, l'ongle est bordé de peau (replis latéraux) et ne touche pas la tranche du doigt.
# Dans le dessin dos il touche le contour : en 3D, la tranche le coupait net (« ongle fendu »). On le termine avant la tranche.
nailm = (DA[..., :3].mean(-1) > .55) & mask
halo = ndimage.binary_dilation(nailm, iterations=2) & mask
skin_ok = mask & ~halo
_, (sy_, sx_) = ndimage.distance_transform_edt(~skin_ok, return_indices=True)
skinfill = DA[sy_, sx_, :3]
keep = np.clip((np.where(M8, d8, 0) - 11) / 3, 0, 1)[..., None]          # 0 près de la tranche, 1 à l'intérieur
DA[..., :3] = np.where(halo[..., None], skinfill * (1 - keep) + DA[..., :3] * keep, DA[..., :3])

def png_b64(arr):
    img = Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype(np.uint8), 'RGBA')
    b = io.BytesIO(); img.save(b, 'PNG', optimize=True); return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()
b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
data = {'W': W, 'H': H, 'chains': CP, 'segs': segs,
        'palm': {'n': int(len(verts)), 'xy': b64(verts.astype(np.int16)), 'zf': b64(np.round(zf * 8).astype(np.int16)), 'zb': b64(np.round(zb * 8).astype(np.int16)), 'idx': b64(tris), 'zscale': 8},
        'texFront': png_b64(P_tex), 'texBack': png_b64(DA), 'outw': OUTW,
        'mesh': mesh8,
        # carte d'épaisseur de la paume (collisions : un doigt ne traverse pas la paume)
        'fw': b64(np.round(FW * 255).astype(np.uint8)),
        'hgrid': {'step': 8, 'gw': int(np.ceil(W / 8)), 'gh': int(np.ceil(H / 8)),
                  'hf': b64(np.round(np.where(ext, hf, 0)[::8, ::8]).astype(np.int16)), 'hb': b64(np.round(np.where(ext, hb, 0)[::8, ::8]).astype(np.int16))}}
json.dump(data, open(os.path.join(OUT, 'hand3d.json'), 'w'))
print('verts', len(verts), 'tris', len(tris), 'json KB', os.path.getsize(os.path.join(OUT, 'hand3d.json')) // 1024, 'landmarks', len(src))

if PREVIEW:
    def toimg(a):
        bg = Image.new('RGBA', (W, H), (255, 255, 255, 255)); bg.alpha_composite(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), 'RGBA')); return bg.convert('RGB')
    f = toimg(P_tex); bk = toimg(DA)
    d = ImageDraw.Draw(bk)
    for (x, y) in src: d.ellipse([x - 4, y - 4, x + 4, y + 4], outline=(255, 0, 0), width=2)
    # contour du dessin paume posé sur le dos recalé
    edge_px = mask ^ ndimage.binary_erosion(mask, iterations=2)
    arr = np.array(bk); arr[edge_px] = [255, 60, 0]; bk = Image.fromarray(arr)
    c = Image.new('RGB', (W * 2, H), 'white'); c.paste(f, (0, 0)); c.paste(bk, (W, 0)); c.thumbnail((1600, 900)); c.save(os.path.join(OUT, 'preview_align.png'))
