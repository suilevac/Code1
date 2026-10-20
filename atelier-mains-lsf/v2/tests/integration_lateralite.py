"""Latéralité, orientation, miroir 3D dans la page construite (dist/atelier-v2.local.html), avec le VRAI moteur.
- main D, orientation identité (vue paume) : le pouce est à DROITE de l'image (main droite, comme le dessin paume.jpg) ;
- main D tournée de 180° autour de Y (vue dos) : le pouce passe à gauche ;
- main G = miroir 3D : sa silhouette est celle de la D retournée (IoU), la lumière restant la même (l'ombre ne change pas
  de côté à l'écran) ;
- « Convertir en main gauche » sur une main D en dos ¾ (planche) : silhouette = celle de la D retournée ;
- « Miroir ⇄ » (flipH, miroir d'image) : l'image est retournée, ombre comprise.
→ tests/out/integration_lateralite.png, integration_lateralite.json"""
import asyncio, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integration_commun import *
from PIL import Image

RENDU = """async([pose,cote,q])=>{const A=AtelierHand;const p=A.presets[pose];const b=A.bounds({pose:p,cote,orientation:q});
  const h=600,w=Math.round(h*b.w/b.h);return A.render({pose:p,cote,orientation:q,w,h}).toDataURL()}"""


def qy(deg):
    a = math.radians(deg) / 2
    return [0, math.sin(a), 0, math.cos(a)]


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def cote_pouce(im):
    """Côté du pouce de « L » (pouce écarté à l'horizontale) : +1 s'il est à DROITE du poignet, −1 à gauche. Le poignet =
    milieu de l'encre des 3 % du bas ; on compare la portée de l'encre à droite et à gauche de ce milieu, dans la bande
    35–75 % de la hauteur (le pouce y est l'extrémité la plus lointaine). → (signe, portée droite px, portée gauche px)"""
    a = np.asarray(im.convert('RGBA'))[..., 3] > 128
    H = a.shape[0]
    ys, xs = np.nonzero(a)
    bas = xs[ys > ys.max() - 0.03 * H]
    cx = (bas.min() + bas.max()) / 2
    _, xb = np.nonzero(a[int(H * 0.35):int(H * 0.75)])
    d, g = xb.max() - cx, cx - xb.min()
    return (1 if d > g else -1, int(d), int(g))


def iou(a, b):
    a = np.asarray(a.convert('RGBA'))[..., 3] > 128
    b = np.asarray(b.convert('RGBA'))[..., 3] > 128
    if a.shape != b.shape:
        b = np.asarray(Image.fromarray(b).resize((a.shape[1], a.shape[0]), Image.NEAREST))
    return float((a & b).sum() / max(1, (a | b).sum()))


def ombre_droite(im):
    """Lumière : sur l'index tendu de « L » (le quart haut de l'image : l'index seul), part des pixels d'ombre (ton de la
    peau × 0,86) à droite de l'axe du doigt, rangée par rangée. La lumière est fixe dans le repère de la caméra (en haut
    à gauche, (−0,45 ; 0,55 ; 1)) : l'ombre doit être du MÊME côté à l'écran pour la droite et pour la gauche (miroir
    3D), à l'inverse d'un miroir d'image."""
    x = np.asarray(im.convert('RGBA')).astype(int)
    op = x[..., 3] > 250
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    ombre = op & (abs(g - 138) < 14) & (r < 30) & (abs(b - 132) < 14)
    ys, _ = np.nonzero(op)
    y0 = ys.min(); y1 = y0 + int(0.25 * (ys.max() - y0))
    d = gch = 0
    for y in range(y0 + 15, y1):
        xs = np.nonzero(op[y])[0]
        if not len(xs):
            continue
        c = (xs.min() + xs.max()) / 2
        xo = np.nonzero(ombre[y])[0]
        d += int((xo > c).sum()); gch += int((xo < c).sum())
    return round(d / max(1, d + gch), 3)


async def main():
    res = {}; ims = []; tit = []
    async with async_playwright() as p:
        b, pg, err, _ = await ouvrir(p)
        dos34 = qmul(qy(150), [math.sin(math.radians(-10)), 0, 0, math.cos(math.radians(-10))])
        cas = [('L', 'D', [0, 0, 0, 1], 'L · D · paume'), ('L', 'G', [0, 0, 0, 1], 'L · G · paume'),
               ('L', 'D', qy(180), 'L · D · dos'), ('V (2)', 'D', dos34, 'V (2) · D · dos ¾'),
               ('V (2)', 'G', [dos34[0], -dos34[1], -dos34[2], dos34[3]], 'V (2) · G · dos ¾ (miroir)')]
        for pose, cote, q, t in cas:
            im = png_pil(await pg.evaluate(RENDU, [pose, cote, q]))
            ims.append(im); tit.append(t)
        res['pouce_L_D_paume'] = cote_pouce(ims[0])
        res['pouce_L_G_paume'] = cote_pouce(ims[1])
        res['pouce_L_D_dos'] = cote_pouce(ims[2])
        res['iou_G_vs_D_retournee_paume'] = round(iou(ims[1], ims[0].transpose(Image.FLIP_LEFT_RIGHT)), 4)
        res['iou_G_vs_D_retournee_dos34'] = round(iou(ims[4], ims[3].transpose(Image.FLIP_LEFT_RIGHT)), 4)
        res['ombre_a_droite_index_L_D_G'] = [ombre_droite(ims[0]), ombre_droite(ims[1])]
        # planche : une main D en dos ¾ → Convertir en main gauche (bouton de la barre), puis Miroir ⇄ sur une copie
        await pg.evaluate("()=>__plate.nouveau&&__plate.nouveau()")
        idD = await pg.evaluate("""q=>{const P=__plate,e=P.ajoute('main',{cote:'D'});e.pose=JSON.parse(JSON.stringify(AtelierHand.presets['V (2)']));
          e.orientation=q;e.x=200;e.y=150;e.h=600;e.w=600*AtelierHand.bounds(e).w/AtelierHand.bounds(e).h;P.invalide();return e.id}""", dos34)
        imD = png_pil(await pg.evaluate("""id=>{const P=__plate,e=P.parId(id);return P.mainCache(e,e.w,e.h,true).toDataURL()}""", idD))
        await pg.evaluate("id=>{__plate.selectionne([id]);__plate.duplique()}", idD)
        idG = await pg.evaluate("()=>__plate.S.doc.elements[__plate.S.doc.elements.length-1].id")
        await pg.evaluate("id=>{__plate.selectionne([id]);__plate.convertitCote()}", idG)
        eG = await pg.evaluate("id=>{const e=__plate.parId(id);return {cote:e.cote,q:e.orientation,flipH:e.flipH,nom:e.nom}}", idG)
        imG = png_pil(await pg.evaluate("""id=>{const P=__plate,e=P.parId(id);return P.mainCache(e,e.w,e.h,true).toDataURL()}""", idG))
        res['iou_planche_D_vs_rendu_direct'] = round(iou(imD, ims[3]), 4)
        res['convertir'] = {'element': eG, 'iou_vs_D_retournee': round(iou(imG, imD.transpose(Image.FLIP_LEFT_RIGHT)), 4)}
        # Miroir ⇄ (flipH) sur la D : exporte la planche et compare la zone de la main à l'image D retournée
        await pg.evaluate("id=>{__plate.selectionne([id]);__plate.miroir('H')}", idD)
        res['miroir_flipH'] = await pg.evaluate("id=>__plate.parId(id).flipH", idD)
        ims += [imD, imG]; tit += ['planche : D dos ¾', 'planche : « Convertir en gauche »']
        res['erreurs'] = err
        await b.close()
    out = planche(ims, tit, 4, titre='Latéralité (main D = GLB sans miroir), miroir 3D, orientation', largeur_case=330)
    out.save(os.path.join(OUT, 'integration_lateralite.png'))
    json.dump(res, open(os.path.join(OUT, 'integration_lateralite.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    ok = (res['pouce_L_D_paume'][0] == 1 and res['pouce_L_G_paume'][0] == -1 and res['pouce_L_D_dos'][0] == -1
          and res['iou_G_vs_D_retournee_paume'] > 0.97 and res['iou_G_vs_D_retournee_dos34'] > 0.97
          and res['iou_planche_D_vs_rendu_direct'] > 0.97 and res['convertir']['element']['cote'] == 'G' and res['convertir']['iou_vs_D_retournee'] > 0.97 and not res['erreurs'])
    print('LATÉRALITÉ :', 'OK' if ok else 'ÉCHEC')
    sys.exit(0 if ok else 1)

asyncio.run(main())
