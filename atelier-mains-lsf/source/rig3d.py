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
DA = bilinear(Dd, mx, my)                      # dessin dos, dans le repère du dessin paume
# là où le dos recalé tombe hors de sa silhouette (léger décalage entre les deux dessins), on prolonge la peau voisine
# le trait de contour du dessin dos peut tomber à l'intérieur de la silhouette paume (les deux dessins n'ont pas exactement la même forme) :
# on le repère dans le dessin dos lui-même, puis on le transporte
dmask = Dd[..., 3] > 0.5
ddist = ndimage.distance_transform_edt(dmask); ddark = Dd[..., :3].mean(-1) < 0.3
dband = dmask & (ddist <= 13) & ddark
dband_wide = dmask & (ddist <= 34) & ddark
bx_ = np.clip(np.round(mx).astype(int), 0, Dd.shape[1] - 1); by_ = np.clip(np.round(my).astype(int), 0, Dd.shape[0] - 1)
bad = mask & ((DA[..., 3] < 0.5) | dband[by_, bx_])
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
DA = strip_outline(DA)

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

def png_b64(arr):
    img = Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype(np.uint8), 'RGBA')
    b = io.BytesIO(); img.save(b, 'PNG', optimize=True); return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()
b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
data = {'W': W, 'H': H, 'chains': CP, 'segs': segs,
        'palm': {'n': int(len(verts)), 'xy': b64(verts.astype(np.int16)), 'zf': b64(np.round(zf * 8).astype(np.int16)), 'zb': b64(np.round(zb * 8).astype(np.int16)), 'idx': b64(tris), 'zscale': 8},
        'texFront': png_b64(P_tex), 'texBack': png_b64(DA), 'outw': OUTW,
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
