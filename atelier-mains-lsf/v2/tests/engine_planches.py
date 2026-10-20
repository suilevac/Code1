"""Planches de contrôle du moteur M2 et mesures (« qualité à tout angle ») :
  - 8 poses × 13 orientations (les 12 du brief + « dessous ») à la MÊME échelle (30 px/cm : la main ouverte fait ≈ 660 px de haut), une planche par pose
    (engine_planche_<pose>.png) et une vue d'ensemble réduite (engine_planche_ensemble.png) ;
  - largeur médiane du CONTOUR (bande sombre au bord du fond, aire / squelette) : constante ± 10 % sur les 13 vues ;
  - part d'ombre de la peau au repos (cible 16–24 %, dessin : 16–18 %) ;
  - DÉFAUTS DE TRAIT (engine_traits.py, mesure étendue après la relecture adverse) sur l'image ENTIÈRE, rubans des plis
    éteints : fragments noirs isolés < 20 px (cible 0) et échardes rattachées à un trait (branche mince de 2 à 6 px) ;
    l'ancienne mesure (fragments à moins de 0,9 cm d'une articulation) est gardée pour comparaison ;
  - temps de render() à 660 px (médiane sur 20) ;
  - gros plans ×3 (ongles de dos ¾ et de chant, jointures du poing, contacts) → engine_gros_plans.png.
Écrit tests/out/engine_mesures.json."""
import asyncio, json, os, sys, statistics
import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *
from engine_traits import defauts, marquer

POSES8 = ['Repos', 'Main ouverte (5)', 'Main plate (B)', 'Poing serré', 'Index (1)', 'V (2)', 'O', 'Pince']
O12 = [('paume', [0, 0, 0, 1]), ('dos', q_axe([0, 1, 0], 180)), ('profil radial', q_axe([0, 1, 0], -90)), ('profil cubital', q_axe([0, 1, 0], 90)),
       ('paume ¾ radial', q_axe([0, 1, 0], -40)), ('paume ¾ cubital', q_axe([0, 1, 0], 40)),
       ('dos ¾ radial', q_mul(q_axe([1, 0, 0], -20), q_axe([0, 1, 0], 220))), ('dos ¾ cubital', q_mul(q_axe([1, 0, 0], -20), q_axe([0, 1, 0], 145))),
       ('plongée paume', q_axe([1, 0, 0], 35)), ('contre-plongée paume', q_axe([1, 0, 0], -35)),
       ('dessus (bouts)', q_axe([1, 0, 0], 90)), ('dos plongée', q_mul(q_axe([1, 0, 0], 35), q_axe([0, 1, 0], 180))),
       # 13e vue (relecture adverse) : poignet vers l'œil — l'ouverture de la manche montrait l'intérieur creux
       ('dessous (poignet)', q_axe([1, 0, 0], -90))]
S_PX = 30.0          # px par cm (HL = 19 cm → la main ouverte ≈ 660 px avec ses marges)
CELL = 660
STYLE = {'largeurTrait': 0.8}
PEAU, OMBRE = np.array([0, 161, 154.]), np.array([0, 161, 154.]) * 0.82
ARTIC = [k + s for k in ['index', 'majeur', 'annulaire', 'auriculaire'] for s in ['_p1', '_p2', '_p3']] + ['pouce_p1', 'pouce_p2']

def mesure_contour(im, attendu):
    a = np.asarray(im)  # RGBA
    alpha = a[..., 3] >= 128; rgb = a[..., :3].astype(float); lum = rgb.mean(2)
    sombre = alpha & (lum < 70)
    fond = ~alpha
    dfond = ndimage.distance_transform_edt(~fond)
    bande = sombre & (dfond <= 2.5 * attendu + 2)
    lab, n = ndimage.label(bande)
    if n == 0: return None
    # la bande extérieure : composantes qui TOUCHENT le fond
    touche = set(np.unique(lab[ndimage.binary_dilation(fond) & bande])) - {0}
    ext = np.isin(lab, list(touche))
    # largeur = aire / longueur du squelette, par composante (continue, contrairement à 2 × distance au squelette, qui
    # ne prend que les valeurs 2, 2√2, 4, 2√5…) ; médiane pondérée par la longueur
    sk = skeletonize(ext); lab2, n2 = ndimage.label(ext)
    if n2 == 0: return None
    aire = ndimage.sum(ext, lab2, range(1, n2 + 1)); lg = ndimage.sum(sk, lab2, range(1, n2 + 1))
    ws = [(a / l, l) for a, l in zip(aire, lg) if l >= 10]
    if not ws: return None
    ws.sort(); tot = sum(l for _, l in ws); acc = 0
    for w_, l in ws:
        acc += l
        if acc >= tot / 2: return float(w_)
    return float(ws[-1][0])

def part_ombre(im):
    a = np.asarray(im); alpha = a[..., 3] >= 250; rgb = a[..., :3].astype(float)
    dl = np.linalg.norm(rgb - PEAU, axis=2); do = np.linalg.norm(rgb - OMBRE, axis=2)
    lit = alpha & (dl < 14) & (dl <= do); omb = alpha & (do < 14) & (do < dl)
    t = lit.sum() + omb.sum()
    return float(omb.sum() / t) if t else None

def fragments(im, joints, s, seuil=60):
    """fragments noirs ISOLÉS aux jointures : composante « encre » (le trait #111 et sa lisière antialiasée, mais ni
    l'ombre de la peau ni l'intérieur de la manche) d'aire < 20 px, contenant au
    moins un pixel noir (luminance < seuil, 60 = définition v1 / rendu.md), à moins de 0,9 cm d'une articulation.
    Un trait continu dont la lisière grise passe par endroits sous 60 n'est PAS une suite de fragments : c'est sa
    composante d'encre entière qui compte."""
    a = np.asarray(im); alpha = a[..., 3] >= 128; rgb = a[..., :3].astype(float); lum = rgb.mean(2)
    # encre : sombre (lum < 95) sans être l'ombre de la peau ni l'intérieur de la manche (couleurs exactes ± 16) ; la
    # lisière d'un trait contre un ongle clair (lum 60–90, vert ≈ 100) en fait partie
    loin = lambda c: np.linalg.norm(rgb - np.array(c), axis=2) > 16
    encre = alpha & (((lum < 95) & loin(OMBRE) & loin(OMBRE * 0.86)) | (lum < seuil)); noir = alpha & (lum < seuil)
    lab, n = ndimage.label(encre)
    if n == 0: return 0, []
    aires = ndimage.sum(encre, lab, range(1, n + 1)); cm = ndimage.center_of_mass(encre, lab, range(1, n + 1))
    nn = ndimage.sum(noir, lab, range(1, n + 1))
    r = 0.9 * s; out = []
    for i, (ar, (cy, cx), k) in enumerate(zip(aires, cm, nn)):
        if ar >= 20 or k == 0: continue
        for nom in ARTIC:
            jx, jy = joints[nom]
            if (cx - jx) ** 2 + (cy - jy) ** 2 <= r * r: out.append((nom, int(ar), int(cx), int(cy))); break
    return len(out), out

async def main():
    rap = {'s_px_par_cm': S_PX, 'poses': {}, 'contour': {}, 'ombre': {}, 'fragments': {}, 'temps': {}}
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, PAGE)
        presets = await pg.evaluate("AtelierHand.presets")
        ensemble = []
        tous_t = []
        tous_defauts = []
        for nom in POSES8:
            pose = presets[nom]; tuiles = []; rap['contour'][nom] = {}; rap['fragments'][nom] = {}
            for vn, q in O12:
                o = {'pose': pose, 'cote': 'D', 'orientation': q, 'style': STYLE}
                bd = await pg.evaluate("o=>AtelierHand.bounds(o)", o)
                o['w'] = max(8, round(bd['w'] * S_PX)); o['h'] = max(8, round(bd['h'] * S_PX))
                pr = await pg.evaluate("o=>AtelierHand._interne.projection(o)", o)
                im = await rendu(pg, o); tous_t.append(im.info['t'])
                cw = mesure_contour(im, pr['contourPx'])
                o2 = dict(o, style=dict(STYLE, plis=False)); im2 = await rendu(pg, o2)
                nf, lst = fragments(im2, pr['joints'], pr['s'])          # artefacts (arêtes, coque, ongles), sans les rubans
                dfx = defauts(im2)                                        # mesure étendue : image entière, échardes
                rap.setdefault('defauts', {}).setdefault(nom, {})[vn] = {'fragments': dfx['fragments'], 'echardes': dfx['echardes']}
                if dfx['fragments'] or dfx['echardes']: tous_defauts.append((marquer(im2, dfx, 2), '%s · %s · F %d · E %d' % (nom, vn, len(dfx['fragments']), len(dfx['echardes']))))
                nfp, _ = fragments(im, pr['joints'], pr['s'])            # avec les rubans des plis (marques voulues)
                n70, _ = fragments(im2, pr['joints'], pr['s'], 70)       # en comptant aussi les filets gris
                rap.setdefault('fragments_lum70', {}).setdefault(nom, {})[vn] = n70
                rap.setdefault('fragments_avec_plis', {}).setdefault(nom, {})[vn] = nfp
                rap['contour'][nom][vn] = cw; rap['fragments'][nom][vn] = {'n': nf, 'liste': lst}
                if nom == 'Repos': rap['ombre'][vn] = part_ombre(im)
                cell = Image.new('RGBA', (CELL, CELL), (255, 255, 255, 255))
                cell.alpha_composite(im, ((CELL - im.width) // 2, (CELL - im.height) // 2))
                lg = '%s · %s · contour %.2f px · F %d · E %d' % (nom, vn, cw or 0, len(dfx['fragments']), len(dfx['echardes']))
                tuiles.append((cell.convert('RGB'), lg))
                ensemble.append((cell.convert('RGB').resize((220, 220)), vn[:14]))
            nf = ''.join(ch for ch in nom if ch.isalnum() or ch in ' ').strip().replace(' ', '_')
            planche(tuiles, 4, '%s — 12 orientations à 30 px/cm (contour attendu %.2f px)' % (nom, pr['contourPx'])).save(os.path.join(OUT, 'engine_planche_%s.png' % nf))
        planche(ensemble, 13, '8 poses × 13 orientations (même échelle)', legende_h=16).save(os.path.join(OUT, 'engine_planche_ensemble.png'))
        # images qui gardent un défaut de trait, cerclé (rouge : fragment, orange : écharde), pour les regarder
        for i in range(0, max(1, len(tous_defauts)), 6):
            if tous_defauts: planche(tous_defauts[i:i + 6], 3, 'défauts de trait restants (×2)').save(os.path.join(OUT, 'engine_defauts_%d.png' % (i // 6 + 1)))
        # temps de render() à 660 px (médiane sur 20, Repos de face)
        ts = []
        for i in range(20):
            im = await rendu(pg, {'pose': presets['Repos'], 'orientation': [0, 0, 0, 1], 'w': 470, 'h': 660, 'style': STYLE}); ts.append(im.info['t'])
        rap['temps']['render_660_mediane_ms'] = statistics.median(ts); rap['temps']['render_planches_mediane_ms'] = statistics.median(tous_t)
        # gros plans ×3 : rendus à 90 px/cm, recadrés autour d'un point
        GP = [('ongle de l’index, dos ¾', 'V (2)', q_mul(q_axe([1, 0, 0], -20), q_axe([0, 1, 0], 145)), 'index_p3_bout', -0.5),
              ('ongles de chant (doigts repliés vus de la paume)', 'V (2)', [0, 0, 0, 1], 'annulaire_p3_bout', 0),
              ('ongle du pouce de chant', 'Poing serré', q_axe([0, 1, 0], -90), 'pouce_p2_bout', -0.4),
              ('jointures du poing, dos ¾', 'Poing serré', q_mul(q_axe([1, 0, 0], -20), q_axe([0, 1, 0], 145)), 'majeur_p1', 0),
              ('contact pouce / doigts', 'Poing serré', [0, 0, 0, 1], 'majeur_p2', 0),
              ('contact entre doigts repliés (V, paume)', 'V (2)', [0, 0, 0, 1], 'annulaire_p2', 0),
              ('jointures dos, main plate', 'Main plate (B)', q_axe([0, 1, 0], 180), 'majeur_p2', 0),
              ('pince : pulpe contre pulpe, profil', 'Pince', q_axe([0, 1, 0], -90), 'index_p3_bout', 0)]
        tu = []
        for lg, nom, q, art, dy in GP:
            o = {'pose': presets[nom], 'orientation': q, 'style': STYLE}
            bd = await pg.evaluate("o=>AtelierHand.bounds(o)", o)
            o['w'] = round(bd['w'] * S_PX * 3); o['h'] = round(bd['h'] * S_PX * 3)
            pr = await pg.evaluate("o=>AtelierHand._interne.projection(o)", o)
            im = sur_blanc(await rendu(pg, o))
            x, y = pr['joints'][art]; y += dy * pr['s']; R = 230
            x0, y0 = int(x - R), int(y - R); c = Image.new('RGB', (2 * R, 2 * R), 'white')   # hors de l'image : blanc
            c.paste(im.crop((max(0, x0), max(0, y0), min(im.width, x0 + 2 * R), min(im.height, y0 + 2 * R))), (max(0, x0) - x0, max(0, y0) - y0))
            tu.append((c, lg))
        planche(tu, 4, 'gros plans ×3 (90 px/cm)').save(os.path.join(OUT, 'engine_gros_plans.png'))
        rap['erreurs_js'] = [e for e in err if 'GPU stall' not in e][:10]
        await b.close()
    # synthèse
    syn = {}
    for nom, d in rap['contour'].items():
        v = [x for x in d.values() if x]; m = statistics.median(v)
        syn[nom] = {'contour_median': round(m, 2), 'min': round(min(v), 2), 'max': round(max(v), 2), 'ecart_max_pct': round(100 * max(abs(x - m) for x in v) / m, 1)}
    rap['synthese_contour'] = syn
    rap['fragments_total'] = sum(v['n'] for d in rap['fragments'].values() for v in d.values())
    rap['defauts_total'] = {'fragments': sum(len(v['fragments']) for d in rap['defauts'].values() for v in d.values()),
                            'echardes': sum(len(v['echardes']) for d in rap['defauts'].values() for v in d.values()),
                            'vues': sum(len(d) for d in rap['defauts'].values())}
    rap['defauts_par_pose'] = {n: [sum(len(v['fragments']) for v in d.values()), sum(len(v['echardes']) for v in d.values())] for n, d in rap['defauts'].items()}
    rap['fragments_total_lum70'] = sum(v for d in rap['fragments_lum70'].values() for v in d.values())
    rap['fragments_total_avec_plis'] = sum(v for d in rap['fragments_avec_plis'].values() for v in d.values())
    json.dump(rap, open(os.path.join(OUT, 'engine_mesures.json'), 'w'), ensure_ascii=False, indent=1)
    for nom, d in syn.items(): print('contour %-18s médiane %.2f px, min %.2f, max %.2f, écart max %.1f %%' % (nom, d['contour_median'], d['min'], d['max'], d['ecart_max_pct']))
    print('ombre au repos :', {k: round(v, 3) for k, v in rap['ombre'].items()})
    print('fragments noirs < 20 px aux jointures :', rap['fragments_total'], {n: sum(v['n'] for v in d.values()) for n, d in rap['fragments'].items()},
          '(filets gris compris : %d ; avec les plis : %d)' % (rap['fragments_total_lum70'], rap['fragments_total_avec_plis']))
    print('défauts de trait (image entière, plis éteints) :', rap['defauts_total'], rap['defauts_par_pose'])
    print('temps :', rap['temps'], 'erreurs JS :', rap['erreurs_js'] or 'aucune')
if __name__ == '__main__':
    asyncio.run(main())
