"""TRAIT DE CONTACT entre deux doigts et vallées entre les jointures (grief de l'utilisateur, 20 octobre 2026 : « des
doigts qui se fondent dans la main, tu ne vois même plus les traits de chaque doigt », capture de « L » vue de dos).

Mesure, sur le moteur courant, le trait dans la VALLÉE entre deux jointures voisines (disque de 0,4 × l'écart des deux
MCP, remonté de 0,45 cm au-dessus de leur milieu — la vallée est au-dessus du centre de la MCP, qui est dans la tête —,
hors de la bande du contour) et entre deux doigts tendus collés (B, au milieu des IPP) : pixels noirs (luminance < 60)
et ÉPAISSEUR du trait (aire / longueur du squelette), à 30 px/cm (échelle d'usage) et à 90 px/cm (×3).
Écrit tests/out/engine_contact.json.

Avec ATELIER_MOTEUR_AVANT=<dossier contenant engine.js et shaders.js d'une version précédente>, rend aussi cette
version-là (même main, mêmes vues) et compose la planche tests/out/engine_contact_avant_apres.png : la capture de
l'utilisateur, des mains entières à 30 px/cm, les rangées de jointures et des contacts à ×3.
Lancer :  python3 <scratchpad>/run_rendu.py v2/tests/engine_contact.py"""
import asyncio, json, os, sys, tempfile
import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine_commun
from engine_commun import *
from engine_traits import encre

V = {'paume': [0, 0, 0, 1], 'dos': q_axe([0, 1, 0], 180), 'profil': q_axe([0, 1, 0], -90),
     'dos ¾': q_mul(q_axe([1, 0, 0], -20), q_axe([0, 1, 0], 145)),
     # orientation de la capture de l'utilisateur : « L » tourné, index vers la gauche, pouce en bas, vu de dos
     'sa capture': q_mul(q_axe([0, 0, 1], 90), q_axe([0, 1, 0], 180))}
D = ['index', 'majeur', 'annulaire', 'auriculaire']
# fenêtres : (preset, paire k / k+1, articulation repère, vue)
FEN = [(n, k, '_p1', v) for n, ks in [('L', [0, 1, 2]), ('Index (1)', [0, 1, 2]), ('V (2)', [1, 2]), ('Poing serré', [0, 1, 2])]
       for k in ks for v in ('dos', 'dos ¾')] + [('Main plate (B)', k, '_p2', v) for k in (0, 1, 2) for v in ('dos', 'dos ¾', 'paume')]
STYLE = {'largeurTrait': 0.8}
# planche : (légende, preset, vue, px/cm, recadrage : None = main entière, '_p1' = rangée des jointures, '_p2' = IPP)
PL = [('sa capture (« L » de dos)', 'L', 'sa capture', 40, None),
      ('', 'L', 'dos', 30, None), ('', 'Index (1)', 'dos', 30, None), ('', 'Poing serré', 'dos', 30, None), ('', 'V (2)', 'dos ¾', 30, None),
      ('×3', 'Poing serré', 'dos', 90, '_p1'), ('×3', 'Poing serré', 'dos ¾', 90, '_p1'), ('×3', 'L', 'dos', 90, '_p1'),
      ('×3', 'V (2)', 'dos ¾', 90, '_p1'), ('×3 doigts tendus collés', 'Main plate (B)', 'paume', 90, '_p2'),
      ('×3 un doigt devant l’autre', 'Pince', 'profil', 90, '_p2')]


def fenetre(im, joints, k, art, contour, s):
    a = np.asarray(im); enc, noir = encre(im)
    A = np.array(joints[D[k] + art]); B = np.array(joints[D[k + 1] + art]); c = (A + B) / 2; r = 0.4 * np.linalg.norm(B - A)
    if art == '_p1': c = c + np.array([0, -0.45 * s])
    H, W = enc.shape; yy, xx = np.mgrid[0:H, 0:W]
    m = ((xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r) & (ndimage.distance_transform_edt(a[..., 3] >= 128) > contour + 3)
    t = noir & m; sk = skeletonize(t).sum()
    return {'noir': int(t.sum()), 'epaisseur': round(float(t.sum() / sk), 2) if sk > 5 else None}


def miroir_avant(dossier):
    """dossier temporaire : le v2 du dépôt (main comprise) avec engine.js / shaders.js de la version précédente"""
    t = tempfile.mkdtemp(prefix='atelier_avant_'); os.makedirs(os.path.join(t, 'engine'))
    os.symlink(os.path.join(V2, 'hand'), os.path.join(t, 'hand'))
    os.symlink(os.path.join(V2, 'engine', 'vendor'), os.path.join(t, 'engine', 'vendor'))
    for f in ('engine.js', 'shaders.js'): os.symlink(os.path.abspath(os.path.join(dossier, f)), os.path.join(t, 'engine', f))
    return t


async def passe(racine, avec_planche):
    engine_commun.V2 = racine
    mes, tu = {}, []
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, page_html=PAGE)
        pr0 = await pg.evaluate("AtelierHand.presets")
        for ech in (30, 90):
            for nom, k, art, vn in FEN:
                o = {'pose': pr0[nom], 'cote': 'D', 'orientation': V[vn], 'style': STYLE}
                bd = await pg.evaluate("o=>AtelierHand.bounds(o)", o); o['w'] = round(bd['w'] * ech); o['h'] = round(bd['h'] * ech)
                pr = await pg.evaluate("o=>AtelierHand._interne.projection(o)", o)
                mes['%d px/cm · %s · %s / %s · %s' % (ech, nom, D[k], D[k + 1], vn)] = fenetre(await rendu(pg, o), pr['joints'], k, art, pr['contourPx'], pr['s'])
        if avec_planche:
            for lg, nom, vn, ech, cr in PL:
                o = {'pose': pr0[nom], 'cote': 'D', 'orientation': V[vn], 'style': STYLE}
                bd = await pg.evaluate("o=>AtelierHand.bounds(o)", o); o['w'] = round(bd['w'] * ech); o['h'] = round(bd['h'] * ech)
                pr = await pg.evaluate("o=>AtelierHand._interne.projection(o)", o)
                im = sur_blanc(await rendu(pg, o))
                if cr:
                    xs = [pr['joints'][d + cr][0] for d in D]; ys = [pr['joints'][d + cr][1] for d in D]; m = 1.3 * pr['s']
                    x0, y0 = int(min(xs) - m), int(min(ys) - m)
                    c = Image.new('RGB', (int(max(xs) + m) - x0, int(max(ys) + 0.6 * m) - y0), 'white')
                    c.paste(im.crop((max(0, x0), max(0, y0), int(max(xs) + m), int(max(ys) + 0.6 * m))), (max(0, x0) - x0, max(0, y0) - y0))
                    im = c
                tu.append(im)
        erreurs = [e for e in err if 'GPU stall' not in e]
        await b.close()
    return mes, tu, erreurs


def composer(av, ap, chemin):
    cases = []
    for i, (lg, nom, vn, ech, cr) in enumerate(PL):
        for j, (im, quand) in enumerate(((av[i], 'avant'), (ap[i], 'après'))):
            cases.append((im, '%s · %s · %s%s' % (nom, vn, quand, (' · ' + lg) if lg else '')))
    # rangées : capture (2 cases), mains entières (8), gros plans (10) — largeur commune, hauteur propre à chaque rangée
    rangs = [cases[0:2], cases[2:10], cases[10:14], cases[14:18], cases[18:22]]
    W = 2000; f = police(15); out = []
    for r in rangs:
        w = W // len(r); hs = [int(im.height * min(1.0, (w - 8) / im.width, 520 / im.height)) for im, _ in r]; h = max(hs) + 24
        c = Image.new('RGB', (W, h), 'white'); d = ImageDraw.Draw(c)
        for i, (im, lgd) in enumerate(r):
            k = min(1.0, (w - 8) / im.width, 520 / im.height); im2 = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))))
            c.paste(im2, (i * w + (w - im2.width) // 2, 22)); d.text((i * w + 4, 3), lgd, fill=(0, 0, 0) if 'après' in lgd else (120, 120, 120), font=f)
        out.append(c)
    titre = Image.new('RGB', (W, 40), 'white')
    ImageDraw.Draw(titre).text((8, 10), 'Trait de contact entre deux doigts et vallées des jointures — avant (gris) / après (noir) ; mêmes poses, même main',
                              fill=(0, 0, 0), font=police(19))
    tot = Image.new('RGB', (W, sum(x.height for x in out) + 40), 'white'); tot.paste(titre, (0, 0)); y = 40
    for x in out: tot.paste(x, (0, y)); y += x.height
    tot.save(chemin)


async def main():
    avant = os.environ.get('ATELIER_MOTEUR_AVANT')
    ici = V2
    mes, tu, err = await passe(ici, bool(avant))
    rap = {'apres': mes, 'erreurs_js': err}
    if avant:
        mes0, tu0, err0 = await passe(miroir_avant(avant), True)
        rap['avant'] = mes0; rap['erreurs_js_avant'] = err0
        composer(tu0, tu, os.path.join(OUT, 'engine_contact_avant_apres.png'))
    json.dump(rap, open(os.path.join(OUT, 'engine_contact.json'), 'w'), ensure_ascii=False, indent=1)
    for k, v in mes.items():
        a = rap.get('avant', {}).get(k)
        print('%-62s noir %5d  épaisseur %5s' % (k, v['noir'], v['epaisseur']) + ('   (avant : %5d / %5s)' % (a['noir'], a['epaisseur']) if a else ''))
    print('erreurs JS :', err or 'aucune')

if __name__ == '__main__':
    asyncio.run(main())
