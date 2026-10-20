"""Mesure des DÉFAUTS DE TRAIT d'une image rendue (fond transparent), commune à engine_planches.py et aux essais.
Relecture adverse du 19 octobre : l'ancienne mesure ne comptait que les composantes d'encre ISOLÉES de moins de 20 px à
moins de 0,9 cm d'une articulation ; les échardes RATTACHÉES à un trait (« poils » autour des bouts, fourches) et les
bouts des doigts lui échappaient. Trois comptes, sur l'image ENTIÈRE (rubans des plis éteints : ce sont des marques
voulues, et un pli court est une composante légitime) :
  - fragments : composante d'encre de moins de 20 px contenant au moins un pixel noir (luminance < 60) — un point, un
    tiret, un bout de trait détaché, où qu'il soit ;
  - échardes : branche du SQUELETTE de l'encre NOIRE qui part d'un endpoint et rejoint un nœud (≥ 3 voisins) après 2 à 6 px
    VISIBLES (au-delà de la demi-épaisseur du trait au nœud, transformée de distance ; en deçà de 2 px c'est le coin
    d'un trait épais), PLUS MINCE que le trait qu'elle quitte (≤ 0,6 × son épaisseur : sinon c'est une jonction en Y de
    deux vrais traits), et qui part d'un trait qui TRAVERSE le nœud (deux branches de plus de 8 px, à plus de 120° l'une
    de l'autre : au bout effilé d'un trait ou à la pointe d'un V, le squelette fait une petite pointe qui n'est pas une
    écharde). Une fourche de deux poils compte deux échardes.
`defauts(im)` rend {'fragments': [(x, y, aire)], 'echardes': [(x, y, longueur visible)]} ; `marquer(im, d)` dessine
des cercles rouges (fragments) et orange (échardes) pour regarder ce qui est compté."""
import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize

OMBRE = np.array([0, 161, 154.]) * 0.82
FRAG_AIRE = 20          # px : composante d'encre sous cette aire = fragment
ECH_MAX = 6.0           # px visibles : une branche plus courte qui part d'un trait = écharde
ECH_MIN = 2.0           # px visibles : en deçà, c'est le coin d'un trait épais (calibré sur les contours propres)


def encre(im, seuil=60):
    a = np.asarray(im); alpha = a[..., 3] >= 128; rgb = a[..., :3].astype(float); lum = rgb.mean(2)
    loin = lambda c: np.linalg.norm(rgb - np.array(c), axis=2) > 16
    enc = alpha & (((lum < 95) & loin(OMBRE) & loin(OMBRE * 0.86)) | (lum < seuil))
    noir = alpha & (lum < seuil)
    return enc, noir


def fragments(enc, noir):
    lab, n = ndimage.label(enc, structure=np.ones((3, 3)))
    if n == 0: return []
    idx = range(1, n + 1)
    aires = ndimage.sum(enc, lab, idx); nn = ndimage.sum(noir, lab, idx); cm = ndimage.center_of_mass(enc, lab, idx)
    return [(int(cx), int(cy), int(ar)) for ar, k, (cy, cx) in zip(aires, nn, cm) if ar < FRAG_AIRE and k > 0]


def echardes(enc, noir):
    # squelette de l'encre NOIRE (luminance < 60) : la lisière grise antialiasée, à la jonction en T ou en Y de deux
    # traits, fait des « barbules » de squelette qui ne se voient pas (vérifié en gros plan ×4 : 25 des 45 échardes
    # comptées sur l'encre à 95 étaient des jonctions propres) ; une écharde visible est noire
    m = noir & enc
    sk = skeletonize(m)
    dt = ndimage.distance_transform_edt(m)
    K = np.ones((3, 3), int); K[1, 1] = 0
    deg = ndimage.convolve(sk.astype(int), K, mode='constant') * sk
    H, W = sk.shape
    ys, xs = np.nonzero(sk & (deg == 1))
    out = []
    for y0, x0 in zip(ys, xs):
        px, py, x, y, L = -1, -1, x0, y0, 0.0
        trouve = None; chemin = [(x0, y0, 0.0)]
        for _ in range(40):
            nxt = None
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0: continue
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < W and 0 <= yy < H and sk[yy, xx] and not (xx == px and yy == py):
                        if nxt is None or (dx == 0 or dy == 0): nxt = (xx, yy, dx, dy)
            if nxt is None: break
            xx, yy, dx, dy = nxt
            L += 1.4142 if dx and dy else 1.0
            px, py, x, y = x, y, xx, yy
            chemin.append((x, y, L))
            if deg[y, x] >= 3: trouve = (x, y); break
            if L > ECH_MAX + 12: break
        if trouve is None: continue
        dj = dt[trouve[1], trouve[0]]; vis = L - dj
        # une écharde est un FILET plus mince que le trait qu'elle quitte (épaisseur le long de la branche, hors de la
        # demi-épaisseur du nœud, ≤ 0,6 × celle du nœud) : à la jonction en Y d'un trait de contact et du contour, la
        # « branche » courte du squelette a l'épaisseur des traits eux-mêmes — ce n'est pas un poil
        mince = [dt[q[1], q[0]] for q in chemin if L - q[2] > dj]
        if not mince or max(mince) > max(1.5, 0.6 * dj): continue
        if ECH_MIN <= vis <= ECH_MAX and trait_traversant(sk, trouve, (x0, y0)):
            out.append((int(x0), int(y0), round(float(vis), 1)))
    return out


def sorties_longues(sk, j, e, D=8):
    """nombre de branches qui partent du nœud j et vont à plus de D px (géodésiques) sans repasser par la branche
    courte venant de e : une écharde part d'un trait qui CONTINUE des deux côtés (≥ 2 sorties longues) ; au bout effilé
    d'un trait, le squelette fait une fourche de deux branches courtes et une seule longue — ce n'est pas une écharde"""
    H, W = sk.shape
    # pixels de la branche courte (de e jusqu'à j, exclus de l'exploration)
    interdit = set(); x, y, px, py = e[0], e[1], -1, -1
    for _ in range(40):
        interdit.add((x, y))
        if (x, y) == tuple(j): break
        nxt = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                xx, yy = x + dx, y + dy
                if (dx or dy) and 0 <= xx < W and 0 <= yy < H and sk[yy, xx] and (xx, yy) != (px, py) and (xx, yy) not in interdit:
                    if nxt is None or (dx == 0 or dy == 0): nxt = (xx, yy)
        if nxt is None: break
        px, py, (x, y) = x, y, nxt
    interdit.discard(tuple(j))
    dist = {tuple(j): 0}; file = [tuple(j)]; front = []
    while file:
        p = file.pop(0); dp = dist[p]
        if dp >= D: front.append(p); continue
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                q = (p[0] + dx, p[1] + dy)
                if (dx or dy) and 0 <= q[0] < W and 0 <= q[1] < H and sk[q[1], q[0]] and q not in dist and q not in interdit:
                    dist[q] = dp + 1; file.append(q)
    if not front: return []
    # grappes du front (pixels du front voisins = même branche) → centre de chaque grappe
    reste = set(front); grappes = []
    while reste:
        pile = [reste.pop()]; g = []
        while pile:
            p = pile.pop(); g.append(p)
            for dy in (-2, -1, 0, 1, 2):
                for dx in (-2, -1, 0, 1, 2):
                    q = (p[0] + dx, p[1] + dy)
                    if q in reste: reste.discard(q); pile.append(q)
        grappes.append((sum(q[0] for q in g) / len(g), sum(q[1] for q in g) / len(g)))
    return grappes


def trait_traversant(sk, j, e):
    """la branche courte venant de e part-elle d'un trait qui TRAVERSE le nœud j (deux sorties longues presque opposées,
    à plus de 120° l'une de l'autre) ? Au sommet d'un V ou d'un Y (deux traits qui se rejoignent en angle aigu), le
    squelette pousse une petite pointe vers la pointe du V : ce n'est pas un poil."""
    g = sorties_longues(sk, j, e)
    if len(g) != 2: return len(g) > 2
    import math
    a = [math.atan2(y - j[1], x - j[0]) for x, y in g]
    d = abs((a[0] - a[1] + math.pi) % (2 * math.pi) - math.pi)
    return d > math.radians(120)


def defauts(im):
    enc, noir = encre(im)
    return {'fragments': fragments(enc, noir), 'echardes': echardes(enc, noir)}


def marquer(im, d, k=3):
    """image agrandie ×k avec les défauts cerclés (rouge : fragment, orange : écharde)"""
    from PIL import Image, ImageDraw
    b = Image.new('RGBA', im.size, (255, 255, 255, 255)); b.alpha_composite(im.convert('RGBA'))
    b = b.convert('RGB').resize((im.width * k, im.height * k), Image.NEAREST); dr = ImageDraw.Draw(b)
    for x, y, _ in d['fragments']: dr.ellipse((x * k - 9, y * k - 9, x * k + 9, y * k + 9), outline=(255, 0, 0), width=2)
    for x, y, _ in d['echardes']: dr.ellipse((x * k - 7, y * k - 7, x * k + 7, y * k + 7), outline=(255, 140, 0), width=2)
    return b
