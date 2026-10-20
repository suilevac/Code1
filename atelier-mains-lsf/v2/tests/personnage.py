"""Planches de contrôle et mesures du personnage (M4, v2/personnage/personnage.js).

  python3 v2/tests/personnage.py                (ou via run_rendu.py : aucune ressource réseau n'est demandée)
  → v2/tests/out/personnage_*.png  et le relevé des mesures sur la sortie standard

Rend : les 4 expressions en A à 600 px de buste ; A et B à 200 px ; la vue de dos ; le repli sous 160 px ; les repères ;
une planche avec une vraie main de l'atelier (capture « V (2) » de face) posée à l'ancre des mains et au menton, pour
contrôler l'échelle et les contrastes ; les couleurs (garde-fou de contraste) ; le personnage dans plate/index.html (M3).
"""
import asyncio, base64, io, json, os, sys
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = 'file://' + os.path.join(ROOT, 'personnage', 'test.html') + '#auto'
OUT = os.path.join(ROOT, 'tests', 'out'); os.makedirs(OUT, exist_ok=True)
MAIN_PNG = '/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/exp/pit/after/V_(2)_face.png'

ECHECS = []
def check(cond, msg):
    print(('  ok   ' if cond else '  ÉCHEC ') + msg)
    if not cond: ECHECS.append(msg)

BUSTE = 3.92                     # HL de buste (crâne → bas de ceinture), personnage.js HAUT_BUSTE_HL
HL600 = 600 / BUSTE              # 153,1 px
HL200 = 200 / BUSTE              # 51,0 px
EXPR = ['neutre', 'sourire', 'sourcils_leves', 'sourcils_fronces']
NOMS = {'neutre': 'neutre', 'sourire': 'sourire', 'sourcils_leves': 'sourcils levés', 'sourcils_fronces': 'sourcils froncés'}


def main_decoupee():
    """La capture de l'atelier v1 (878 × 737, fond en damier, boutons) → la main seule sur fond transparent.
    Le fond est rempli depuis le bord du recadrage (pixels clairs et gris, R,G,B > 200) : le contour noir de la main
    l'arrête. Longueur de main mesurée sur la capture : bout du majeur y = 64, pli du poignet ≈ y 545 → HL ≈ 481 px."""
    from scipy import ndimage
    im = Image.open(MAIN_PNG).convert('RGB')
    x0, y0, x1, y1 = 296, 56, 562, 680
    a = np.array(im.crop((x0, y0, x1, y1))).astype(int)
    clair = (a[..., 0] > 200) & (a[..., 1] > 200) & (a[..., 2] > 200)
    lab, _ = ndimage.label(clair)
    bord = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fond = np.isin(lab, list(bord))
    alpha = np.where(fond, 0, 255).astype(np.uint8)
    rgba = np.dstack([a.astype(np.uint8), alpha])
    buf = io.BytesIO(); Image.fromarray(rgba, 'RGBA').save(buf, 'PNG')
    # repères dans le recadrage : bout du doigt le plus long, pli du poignet, axe de la main
    return ('data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode(),
            dict(w=x1 - x0, h=y1 - y0, bout=64 - y0, poignet=545 - y0, cx=425 - x0, HL=545 - 64))


def lum(c):
    c = np.asarray(c, float) / 255
    c = np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    return .2126 * c[..., 0] + .7152 * c[..., 1] + .0722 * c[..., 2]

def contraste(a, b):
    la, lb = lum(a), lum(b); return (max(la, lb) + .05) / (min(la, lb) + .05)

def hexrgb(h): return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


async def rend(pg, spec, nom):
    infos = await pg.evaluate('s => scene(s)', spec)
    el = await pg.query_selector('#scene')
    path = os.path.join(OUT, nom)
    await el.screenshot(path=path)
    return infos, np.array(Image.open(path).convert('RGB')).astype(int)


async def main():
    src, M = main_decoupee()
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 2000, 'height': 1400}, device_scale_factor=1)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        await pg.goto(PAGE); await pg.wait_for_timeout(300)
        await pg.add_style_tag(content='#scene{margin:0!important;border:0!important;border-radius:0!important;max-width:none!important}')
        PAL = await pg.evaluate('() => AtelierPersonnage.PALETTE')
        n_cache = await pg.evaluate('() => AtelierPersonnage._cache.size')
        print(f'Path2D en cache au chargement : {n_cache}')
        check(n_cache > 80, f'chemins convertis en Path2D au chargement ({n_cache})')

        # ------------------------------------------------------------ 1. quatre expressions, A, 600 px de buste
        print('1. Quatre expressions en A, buste 600 px (HL = %.1f px)' % HL600)
        cw = 2.9 * HL600 + 40; y0 = 30 + 2.1 * HL600
        spec = dict(w=round(4 * cw), h=round(y0 + 2.2 * HL600 + 50), fond='#ffffff',
                    items=[dict(x=cw * (i + .5), y=y0, HLpx=HL600, expression=e, style='A', legende=NOMS[e]) for i, e in enumerate(EXPR)])
        inf, img = await rend(pg, spec, 'personnage_expressions_A_600.png')
        tr = inf[0]['trait']
        check(abs(tr - .028 * HL600) < 1e-6, f'trait à 600 px : {tr:.2f} px = 0,028 × HL')
        # largeur de trait mesurée : couverture d'encre en travers du flanc gauche du pan de cape, à +1,5 HL
        enc = np.array(hexrgb(PAL['trait'])); fondc = np.array([255, 255, 255]); capec = np.array(hexrgb(PAL['cape']))
        yy = round(y0 + 1.5 * HL600); xg = round(cw * .5 - 1.44 * HL600); ligne = img[yy, xg:xg + round(.4 * HL600)]
        d = np.linalg.norm(ligne - enc, axis=1); k = int(np.argmin(d))
        seg = ligne[max(0, k - 8):k + 9]
        # pixel par pixel : part d'encre = projection sur le segment fond→encre (fond blanc à gauche, cape à droite)
        cov = 0
        for j, px in enumerate(seg):
            ref = fondc if j < 8 else capec
            cov += np.clip(np.dot(ref - px, ref - enc) / np.dot(ref - enc, ref - enc), 0, 1)
        print(f'  largeur de trait mesurée sur l\'image (flanc du pan de cape) : {cov:.2f} px (attendu {tr:.2f})')
        check(abs(cov - tr) < .8, f'trait mesuré {cov:.2f} px ≈ {tr:.2f} px')
        # ombre franche à droite : pixels aux tons d'ombre de part et d'autre de l'axe du personnage
        g = d_ = 0
        for kk in ('peauOmbre', 'vetementOmbre', 'capeOmbre'):
            c = np.array(hexrgb(PAL[kk])); m = np.linalg.norm(img - c, axis=2) < 6
            fig = m[:, :round(cw)]
            cols = np.arange(fig.shape[1])[None, :].repeat(fig.shape[0], 0)
            g += int((fig & (cols < cw / 2)).sum()); d_ += int((fig & (cols >= cw / 2)).sum())
        print(f'  pixels d\'ombre franche, figure 1 : gauche {g}, droite {d_} ({100 * d_ / max(1, g + d_):.1f} % à droite)')
        check(d_ > 4 * g, 'ombre franche à DROITE de l\'image (lumière fixe caméra (−0,45 ; 0,55 ; 1))')
        # expressions distinctes : pixels du visage qui changent par rapport à « neutre »
        fx0, fx1 = -0.45, 0.45; fy0, fy1 = -1.55, -0.62
        def visage(i, im, cw_, y0_, HL):
            cx = cw_ * (i + .5)
            X, Y = round(cx + fx0 * HL), round(y0_ + fy0 * HL)
            return im[Y:Y + round((fy1 - fy0) * HL), X:X + round((fx1 - fx0) * HL)]
        v0 = visage(0, img, cw, y0, HL600)
        for i, e in enumerate(EXPR[1:], 1):
            dv = (np.abs(visage(i, img, cw, y0, HL600) - v0).sum(2) > 60).mean()
            print(f'  {NOMS[e]} : {100 * dv:.1f} % des pixels du visage diffèrent de « neutre »')
            check(dv > .03, f'{NOMS[e]} se distingue de neutre à 600 px')
        # sourire : l'œil est une ARCHE d'encre dont le bord bas remonte au milieu (relecture adverse : paupière basse
        # plate, 1 u. de flèche, lue « narquois »). Mesure : bord bas de l'encre au centre de l'œil gauche contre à ±10 u.
        def bas_encre(im, cx, x_u):
            col = im[round(y0 - 1.40 * HL600):round(y0 - 0.95 * HL600), round(cx + x_u / 100 * HL600)]
            k_ = np.where(np.linalg.norm(col - enc, axis=1) < 60)[0]
            return (k_.max() + round(y0 - 1.40 * HL600)) if len(k_) else None
        cx1 = cw * 1.5
        b0_, bl_, br_ = bas_encre(img, cx1, -27), bas_encre(img, cx1, -37), bas_encre(img, cx1, -17)
        fl = ((bl_ + br_) / 2 - b0_) / HL600 * 100
        print(f'  sourire : bord bas de l\'œil, flèche {fl:.1f} u. vers le HAUT (centre plus haut que les côtés à ±10 u.)')
        check(fl >= 4, f'sourire : paupière basse en arc qui remonte (flèche {fl:.1f} u. ≥ 4)')
        zone = img[round(y0 - 1.30 * HL600):round(y0 - 1.05 * HL600), round(cx1 - .45 * HL600):round(cx1 + .45 * HL600)]
        n_bl = int((np.abs(zone - 255).sum(2) < 10).sum())
        print(f'  sourire : {n_bl} px de blanc d\'œil (yeux plissés en arche)')
        check(n_bl == 0, 'sourire : pas de blanc d\'œil ni d\'iris coupé')
        print(f'  temps de dessin (A face, 600 px) : {", ".join("%.2f" % i["ms"] for i in inf)} ms')

        # ------------------------------------------------------------ 2. A et B à 200 px (+ les 4 expressions en A et en B)
        print('2. A et B à 200 px de buste (HL = %.1f px)' % HL200)
        cw2 = 2.9 * HL200 + 24; y2 = 18 + 2.1 * HL200
        items = []
        for r_, st in enumerate(('A', 'B')):
            for i, e in enumerate(EXPR):
                items.append(dict(x=cw2 * (i + .5), y=y2 + r_ * (4.3 * HL200 + 44), HLpx=HL200, expression=e, style=st, legende=f'{st} · {NOMS[e]}'))
        spec = dict(w=round(4 * cw2), h=round(2 * (4.3 * HL200 + 44) + 10), fond='#ffffff', items=items)
        inf, img2 = await rend(pg, spec, 'personnage_AB_200.png')
        check(all(i['style'] == it['style'] for i, it in zip(inf, items)), 'à 200 px, A reste A (pas de repli au-dessus de 160 px)')
        check(abs(inf[0]['trait'] - max(1.3, .028 * HL200)) < 1e-6, f'trait à 200 px : {inf[0]["trait"]:.2f} px')
        for r_, st in enumerate(('A', 'B')):
            yb = y2 + r_ * (4.3 * HL200 + 44)
            v0 = visage(0, img2, cw2, yb, HL200)
            ds = [(np.abs(visage(i, img2, cw2, yb, HL200) - v0).sum(2) > 60).mean() for i in range(1, 4)]
            print(f'  {st} : pixels du visage différents de neutre (sourire, levés, froncés) : ' + ', '.join(f'{100 * x:.1f} %' for x in ds))
            check(min(ds) > .03, f'{st} : les 4 expressions restent distinctes à 200 px')
        big = Image.open(os.path.join(OUT, 'personnage_AB_200.png'))
        big.resize((big.width * 3, big.height * 3), Image.NEAREST).crop((0, 0, round(2 * cw2 * 3), big.height * 3)).save(os.path.join(OUT, 'personnage_AB_200_zoom3.png'))

        # ------------------------------------------------------------ 3. vue de dos (A et B, 600 px), à côté de la face
        print('3. Vue de dos')
        items = [dict(x=cw * .5, y=y0, HLpx=HL600, vue='face', style='A', legende='A · face'),
                 dict(x=cw * 1.5, y=y0, HLpx=HL600, vue='dos', style='A', legende='A · dos'),
                 dict(x=cw * 2.5, y=y0, HLpx=HL600, vue='face', style='B', legende='B · face'),
                 dict(x=cw * 3.5, y=y0, HLpx=HL600, vue='dos', style='B', legende='B · dos')]
        spec = dict(w=round(4 * cw), h=round(y0 + 2.2 * HL600 + 50), fond='#ffffff', items=items)
        inf, img3 = await rend(pg, spec, 'personnage_dos.png')
        # silhouette identique face / dos : masque « pas blanc »
        def masque(im, i):
            cx = cw * (i + .5); X, Y = round(cx - 1.5 * HL600), round(y0 - 2.15 * HL600)
            return (np.abs(im[Y:Y + round(4.37 * HL600), X:X + round(3 * HL600)] - 255).sum(2) > 30)
        for i0, i1, st in ((0, 1, 'A'), (2, 3, 'B')):
            mf, md = masque(img3, i0), masque(img3, i1)
            iou = (mf & md).sum() / (mf | md).sum()
            print(f'  {st} : silhouette face/dos, recouvrement (IoU) {iou:.3f}')
            check(iou > .93, f'{st} : la vue de dos garde la silhouette de face')
        # pas de visage de dos : aucun pixel blanc d'œil ni d'encre dans la zone des yeux
        cx1 = cw * 1.5; zone = img3[round(y0 - 1.25 * HL600):round(y0 - 1.0 * HL600), round(cx1 - .42 * HL600):round(cx1 + .42 * HL600)]
        n_enc = int((np.linalg.norm(zone - enc, axis=2) < 40).sum())
        n_bl = int((np.abs(zone - 255).sum(2) < 10).sum())
        print(f'  dos, zone des yeux : {n_enc} px d\'encre, {n_bl} px blancs')
        check(n_bl == 0, 'vue de dos : pas d\'œil')
        # de dos, pas de MENTON : aucune encre en travers du cou entre −0,95 et −0,35 HL (colonnes à ±0,15 HL ; le sillon
        # de la nuque est au milieu). De face ces colonnes traversent le contour du menton.
        for i, nom in ((0, 'A face'), (1, 'A dos'), (2, 'B face'), (3, 'B dos')):
            cxi = cw * (i + .5); n_ = 0
            for xo in (-.15, .15):
                col = img3[round(y0 - .95 * HL600):round(y0 - .35 * HL600), round(cxi + xo * HL600)]
                n_ += int((np.linalg.norm(col - enc, axis=1) < 60).sum())
            print(f'  {nom} : {n_} px d\'encre en travers du cou (±0,15 HL, y −0,95 … −0,35)')
            if 'dos' in nom: check(n_ == 0, f'{nom} : pas de menton, la tête entre dans la nuque')
            else: check(n_ > 0, f'{nom} : le menton est bien là')
        # la tête de dos n'est plus la tête de face : pixels de la zone tête + cou qui diffèrent
        def tete(im, i):
            cx = round(cw * (i + .5)); w_ = round(.6 * HL600); return im[round(y0 - 1.9 * HL600):round(y0 - .05 * HL600), cx - w_:cx + w_]
        for i0, i1, st in ((0, 1, 'A'), (2, 3, 'B')):
            dd = (np.abs(tete(img3, i0) - tete(img3, i1)).sum(2) > 60).mean()
            print(f'  {st} : tête + cou, {100 * dd:.1f} % des pixels diffèrent entre face et dos')

        # ------------------------------------------------------------ 4. repli sous 160 px
        print('4. Repli automatique sous 160 px de buste')
        rows = []
        for hb in (200, 170, 160, 150, 120, 90):
            hl = hb / BUSTE
            r = await pg.evaluate('h => AtelierPersonnage.styleEffectif(h, "A")', hl)
            rows.append((hb, hl, r))
            print(f'  buste {hb} px (HL {hl:.1f}) → style {r}')
        check([r for *_, r in rows] == ['A', 'A', 'A', 'B', 'B', 'B'], 'repli vers B exactement sous 160 px')
        hl150 = 150 / BUSTE; cw4 = 2.9 * hl150 + 24; y4 = 18 + 2.1 * hl150
        items = [dict(x=cw4 * .5, y=y4, HLpx=hl150, style='A', repli=False, legende='A forcé'),
                 dict(x=cw4 * 1.5, y=y4, HLpx=hl150, style='A', legende='A → repli B'),
                 dict(x=cw4 * 2.5, y=y4, HLpx=hl150, style='A', expression='sourire', legende='sourire'),
                 dict(x=cw4 * 3.5, y=y4, HLpx=hl150, style='A', expression='sourcils_fronces', legende='froncés'),
                 dict(x=cw4 * 4.5, y=y4, HLpx=hl150, style='A', vue='dos', legende='dos')]
        spec = dict(w=round(5 * cw4), h=round(y4 + 2.2 * hl150 + 36), fond='#ffffff', items=items)
        inf, _ = await rend(pg, spec, 'personnage_repli_150.png')
        check([i['style'] for i in inf] == ['A', 'B', 'B', 'B', 'B'] and inf[1]['repli'], f'buste 150 px : A demandé → {inf[1]["style"]} (repli {inf[1]["repli"]})')
        big = Image.open(os.path.join(OUT, 'personnage_repli_150.png'))
        big.resize((big.width * 3, big.height * 3), Image.NEAREST).save(os.path.join(OUT, 'personnage_repli_150_zoom3.png'))

        # ------------------------------------------------------------ 5. repères d'emplacement
        print('5. Repères d\'emplacement')
        items = [dict(x=cw * .5, y=y0, HLpx=HL600, style='A', reperes=True, legende='A · repères'),
                 dict(x=cw * 1.5, y=y0, HLpx=HL600, style='B', reperes=True, legende='B · repères'),
                 dict(x=cw * 2.5, y=y0, HLpx=HL600, style='A', vue='dos', reperes=True, legende='A · dos · repères')]
        spec = dict(w=round(3 * cw), h=round(y0 + 2.2 * HL600 + 50), fond='#ffffff', items=items)
        inf, img5 = await rend(pg, spec, 'personnage_reperes.png')
        horsb = 0
        for i in range(3):
            cx = cw * (i + .5)
            for xa, xb in ((cx - .5 * cw, cx - 1.47 * HL600), (cx + 1.47 * HL600, cx + .5 * cw)):
                horsb += int((np.abs(img5[2:round(y0 + 2.2 * HL600), round(xa):round(xb)] - 255).sum(2) > 30).sum())   # ligne 0 : bord de la page
        print(f'  pixels de repères ou d\'étiquettes hors de la boîte ±1,47 HL : {horsb}')
        check(horsb == 0, 'étiquettes et pastilles restent dans la boîte du dessin')
        A = await pg.evaluate('h => AtelierPersonnage.ancres(h)', HL600)
        for k in ('front', 'menton', 'epauleG', 'epauleD', 'poitrine', 'mains', 'taille'):
            print(f'  {k:9s} : ({A[k]["x"] / HL600:+.2f} ; {A[k]["y"] / HL600:+.2f}) HL')
        AB = await pg.evaluate('h => [AtelierPersonnage.ancres(h, {style: "A"}).epauleD, AtelierPersonnage.ancres(h, {style: "B"}).epauleD, AtelierPersonnage.ancres(30, {style: "A"}).epauleD]', HL600)
        print(f'  épaule (lieu) A {AB[0]["x"] / HL600:+.2f} ; {AB[0]["y"] / HL600:+.2f} HL, B {AB[1]["x"] / HL600:+.2f} ; {AB[1]["y"] / HL600:+.2f}, après repli (HL 30) {AB[2]["x"] / 30:+.2f} ; {AB[2]["y"] / 30:+.2f}')
        check(abs(AB[0]['x'] - AB[1]['x']) < 1e-9 and abs(AB[0]['y'] - AB[1]['y']) < 1e-9 and abs(AB[2]['y'] / 30 - .10) < 1e-9,
              'épaule = (±1,15 ; +0,10) HL en A, en B et après le repli (plus de saut)')
        inval = await pg.evaluate('''() => { const c = document.createElement('canvas').getContext('2d');
            return [-5, 0, 'abc', NaN, undefined].map(h => AtelierPersonnage.draw(c, {x: 10, y: 10, HLpx: h})).concat([AtelierPersonnage.boite(-1), AtelierPersonnage.ancres(0)]); }''')
        print(f'  HLpx invalide (−5, 0, \'abc\', NaN, absent) → {inval[:5]} ; boite(−1) → {inval[5]} ; ancres(0) → {inval[6]}')
        check(all(v is None for v in inval), 'HLpx invalide : rien n\'est dessiné, null rendu')
        check(abs(A['menton']['y'] / HL600 + .58) < 1e-9 and abs(A['taille']['y'] / HL600 - 1.92) < 1e-9 and abs(A['mains']['y'] / HL600 - 1) < 1e-9,
              'ancres de la v1 gardées : menton −0,58, taille +1,92, mains +1,00 HL')

        # traits secondaires : jamais sous 1,3 px à l'écran (relecture adverse : 0,71 px pour le contour des sourcils à 200 px)
        mins = await pg.evaluate('''(hls) => hls.map(h => { const c = document.createElement('canvas'); c.width = 400; c.height = 400;
            const x = c.getContext('2d'); let m = 1e9; const s0 = x.stroke.bind(x);
            x.stroke = function (p) { const t = x.getTransform(); m = Math.min(m, x.lineWidth * Math.hypot(t.a, t.b)); return s0(p); };
            for (const e of AtelierPersonnage.EXPRESSIONS) for (const st of ['A', 'B']) for (const vue of ['face', 'dos'])
              AtelierPersonnage.draw(x, {x: 200, y: 200, HLpx: h, expression: e, style: st, vue, repli: false});
            return m; })''', [HL200, 160 / BUSTE, HL600])
        print(f'  trait le plus fin dessiné (px écran) : buste 200 px {mins[0]:.2f}, 160 px {mins[1]:.2f}, 600 px {mins[2]:.2f}')
        check(min(mins) >= 1.3 - 1e-6, 'aucun trait sous 1,3 px à l\'écran')

        # ------------------------------------------------------------ 6. boîte du dessin (fond transparent)
        print('6. Boîte du dessin contre la boîte de la planche (PERS_HL 2,9 × 4,3, creux du cou à 2,1)')
        HLb = 200; W6, H6 = round(3.4 * HLb), round(4.8 * HLb)
        for st, vue in (('A', 'face'), ('A', 'dos'), ('B', 'face')):
            al = await pg.evaluate('''([st, vue, HL, W, H]) => { const c = document.createElement('canvas'); c.width = W; c.height = H;
                 const x = c.getContext('2d'); AtelierPersonnage.draw(x, {x: W/2, y: 0.25*HL + 2.1*HL, HLpx: HL, style: st, vue});
                 const d = x.getImageData(0, 0, W, H).data; let x0=W,y0=H,x1=-1,y1=-1;
                 for (let j=0;j<H;j++) for (let i=0;i<W;i++) if (d[(j*W+i)*4+3] > 8) { if(i<x0)x0=i; if(i>x1)x1=i; if(j<y0)y0=j; if(j>y1)y1=j; }
                 return [x0, y0, x1, y1]; }''', [st, vue, HLb, W6, H6])
            cx, cy = W6 / 2, .25 * HLb + 2.1 * HLb
            bx = [(al[0] - cx) / HLb, (al[1] - cy) / HLb, (al[2] + 1 - cx) / HLb, (al[3] + 1 - cy) / HLb]
            print(f'  {st} {vue} : x {bx[0]:+.3f} … {bx[2]:+.3f}, y {bx[1]:+.3f} … {bx[3]:+.3f} HL')
            check(bx[0] >= -1.47 and bx[2] <= 1.47 and bx[1] >= -2.12 and bx[3] <= 2.22, f'{st} {vue} tient dans la boîte de la planche (±1,45 ; −2,1 … +2,2, à ½ trait près)')

        # ------------------------------------------------------------ 7. planche avec une main de l'atelier
        print('7. Planche avec une main (capture « V (2) » de face) : à l\'ancre des mains, et au menton')
        HLp = 150; Wp, Hp = 1500, round(4.3 * HLp + 120)
        yc = 60 + 2.1 * HLp
        sc = HLp / M['HL']                                 # la main de la capture ramenée à 1 HL du personnage
        mw, mh = M['w'] * sc, M['h'] * sc
        A1 = await pg.evaluate('h => AtelierPersonnage.ancres(h)', HLp)
        def pose(cx, ay):                                  # milieu bout ↔ poignet de la main sur l'ancre
            mid = (M['bout'] + M['poignet']) / 2 * sc
            return dict(src=src, x=cx - M['cx'] * sc, y=ay - mid, w=mw, h=mh)
        xs = [Wp * .17, Wp * .5, Wp * .83]
        items = [dict(x=xs[0], y=yc, HLpx=HLp, style='A', legende='main à l\'ancre (poitrine +1,00 HL)'),
                 dict(x=xs[1], y=yc, HLpx=HLp, style='A', expression='sourcils_leves', legende='main au menton'),
                 dict(x=xs[2], y=yc, HLpx=HLp, style='B', legende='B · main à l\'ancre')]
        imgs = [pose(xs[0], yc + A1['mains']['y']), pose(xs[1] + .55 * HLp, yc + A1['menton']['y'] + .05 * HLp), pose(xs[2], yc + A1['mains']['y'])]
        spec = dict(w=Wp, h=Hp, fond='#dbe8e6', items=items, images=imgs)
        inf, img7 = await rend(pg, spec, 'personnage_planche_main.png')
        print(f'  main : {mw:.0f} × {mh:.0f} px pour HL = {HLp} px (échelle {sc:.3f} de la capture)')
        main_c = hexrgb('#00a19a')
        for k in ('peau', 'peauOmbre', 'vetement', 'vetementOmbre', 'cape', 'capeOmbre'):
            print(f'  contraste main #00a19a / {k} {PAL[k]} : {contraste(main_c, hexrgb(PAL[k])):.2f}:1')
        check(contraste(main_c, hexrgb(PAL['vetement'])) > 2.6 and contraste(main_c, hexrgb(PAL['cape'])) > 2.6, 'main ≥ 2,6:1 sur le vêtement et la cape')
        check(lum(hexrgb(PAL['peau'])) >= 2 * lum(main_c), f'luminance de la peau ≥ 2 × celle de la main ({lum(hexrgb(PAL["peau"])):.3f} / {lum(main_c):.3f})')
        # la main posée à l'ancre couvre bien le tronc, entre les épaules et la ceinture
        mx = np.array(hexrgb('#00a19a'))
        mm = np.linalg.norm(img7[:, :round(Wp / 3)] - mx, axis=2) < 30
        ys_, xs_ = np.where(mm)
        print(f'  main 1 : y {(ys_.min() - yc) / HLp:+.2f} … {(ys_.max() - yc) / HLp:+.2f} HL, x {(xs_.min() - xs[0]) / HLp:+.2f} … {(xs_.max() - xs[0]) / HLp:+.2f} HL')
        check(ys_.min() > yc + .2 * HLp and ys_.max() < yc + 1.92 * HLp, 'la main posée à l\'ancre reste entre les épaules et la taille')

        # ------------------------------------------------------------ 8. couleurs de la planche (plate.js passe {peau, vetement, cape, trait})
        print('8. Couleurs données par la planche')
        items = [dict(x=cw * .5, y=y0, HLpx=HL600, style='A', legende='palette du dossier'),
                 dict(x=cw * 1.5, y=y0, HLpx=HL600, style='A', couleurs={'peau': '#9fd8a8', 'vetement': '#5e4b8b', 'cape': '#f4f1ea', 'trait': '#14201f'}, legende='couleurs par défaut de plate.js'),
                 dict(x=cw * 2.5, y=y0, HLpx=HL600, style='A', couleurs={'peau': '#9fd8a8', 'vetement': '#5e4b8b', 'cape': '#f4f1ea', 'trait': '#14201f', 'garde': False}, legende='les mêmes SANS garde-fou'),
                 dict(x=cw * 3.5, y=y0, HLpx=HL600, style='A', couleurs={'peau': '#f2c9a0', 'vetement': '#1f5f8b', 'cape': '#ffe8a3', 'ceinture': '#2e7d32'}, legende='couleurs libres (ombres dérivées)')]
        spec = dict(w=round(4 * cw), h=round(y0 + 2.2 * HL600 + 50), fond='#ffffff', items=items)
        await rend(pg, spec, 'personnage_couleurs.png')
        od = await pg.evaluate('() => [AtelierPersonnage.ombreDe("#a8dcd6"), AtelierPersonnage.ombreDe("#5a3d8c"), AtelierPersonnage.palette({peau:"zzz"}).peau]')
        print(f'  ombre dérivée de la peau du dossier {od[0]} (dossier #74c2b9), du vêtement {od[1]} (dossier #44306d) ; couleur illisible ignorée → {od[2]}')
        check(od[2] == PAL['peau'], 'une couleur illisible ne casse rien')
        g = await pg.evaluate('''() => { const P = AtelierPersonnage.palette({peau: '#9fd8a8', vetement: '#5e4b8b', cape: '#f4f1ea', trait: '#14201f'});
            const Q = AtelierPersonnage.palette({vetement: '#5e4b8b', garde: false}), D = AtelierPersonnage.palette();
            return {P: Object.assign({}, P), corr: P._corrections, sans: Q.vetement, D: Object.assign({}, D), corrD: D._corrections}; }''')
        P2 = g['P']; m_ = hexrgb('#00a19a')
        print(f'  couleurs de la planche → corrections : {g["corr"]}')
        print(f'  vêtement #5e4b8b → {P2["vetement"]} : {contraste(m_, hexrgb(P2["vetement"])):.2f}:1 (avant 2,30:1), ombre {P2["vetementOmbre"]} {contraste(m_, hexrgb(P2["vetementOmbre"])):.2f}:1')
        print(f'  peau #9fd8a8 : luminance {lum(hexrgb(P2["peau"])):.3f} ≥ 2 × {lum(m_):.3f} = {2 * lum(m_):.3f} → gardée ({contraste(m_, hexrgb(P2["peau"])):.2f}:1)')
        check(contraste(m_, hexrgb(P2['vetement'])) >= 2.6 and contraste(m_, hexrgb(P2['cape'])) >= 2.6 and lum(hexrgb(P2['peau'])) >= 2 * lum(m_),
              'garde-fou : les couleurs de la planche respectent la règle du dossier')
        check(not g['corrD'] and g['D'] == PAL, 'la palette du dossier passe le garde-fou sans changement')
        check(g['sans'] == '#5e4b8b', 'couleurs.garde = false coupe le garde-fou')
        ex = await pg.evaluate('() => ["#00a19a", "#b0f0e8", "#20c0b0", "#777777"].map(v => { const P = AtelierPersonnage.palette({vetement: v, cape: v, peau: v}); return [P.vetement, P.cape, P.peau]; })')
        for v, (a_, b_, c_) in zip(['#00a19a', '#b0f0e8', '#20c0b0', '#777777'], ex):
            print(f'  {v} comme vêtement/cape/peau → {a_} ({contraste(m_, hexrgb(a_)):.2f}:1) / {b_} / peau {c_} (lum {lum(hexrgb(c_)):.3f})')
            check(contraste(m_, hexrgb(a_)) >= 2.6 and lum(hexrgb(c_)) >= 2 * lum(m_), f'{v} : corrigée au-dessus des seuils')

        check(not errs, f'aucune erreur JS ({errs[:3]})')

        # ------------------------------------------------------------ 9. dans la planche (plate/index.html, M3)
        print('9. Dans la planche : plate/index.html charge personnage.js, référent souriant + une main')
        pg2 = await b.new_page(viewport={'width': 1400, 'height': 860}, device_scale_factor=1)
        errs2 = []; pg2.on('pageerror', lambda e: errs2.append(str(e)))
        await pg2.goto('file://' + os.path.join(ROOT, 'plate', 'index.html')); await pg2.wait_for_timeout(1200)
        r9 = await pg2.evaluate('''() => { const P = __plate.S.doc.planche;
            const e = __plate.ajoute('personnage', {expression: 'sourire'});
            __plate.ajoute('main', {cote: 'D', h: P.h * .26, w: P.h * .26 * .62, x: P.w / 2 - P.h * .1, y: e.y + e.h * .52});
            __plate.selectionne([]);
            const c = document.createElement('canvas'); c.width = P.w; c.height = P.h; const x = c.getContext('2d');
            __plate.drawDoc(x, __plate.S.doc, 1, {export: true});
            return {M4: !!window.AtelierPersonnage, perso: e, png: c.toDataURL('image/png'), couleurs: e.couleurs}; }''')
        await pg2.wait_for_timeout(300)
        await pg2.screenshot(path=os.path.join(OUT, 'personnage_dans_planche.png'))
        ex9 = np.array(Image.open(io.BytesIO(base64.b64decode(r9['png'].split(',')[1]))).convert('RGB')).astype(int)
        e9 = r9['perso']; Bh = await pg2.evaluate('() => { const b = AtelierPersonnage.boite(100); return {h: b.h / 100, y: -b.y / 100}; }')
        hl9 = e9['h'] / (Bh['h'] * 1.04); cy9 = e9['y'] + (Bh['y'] + Bh['h'] * .02) * hl9; cx9 = e9['x'] + e9['w'] / 2
        att = hexrgb((await pg2.evaluate('c => AtelierPersonnage.palette(c).vetement', r9['couleurs'])))
        px = ex9[round(cy9 + .55 * hl9), round(cx9 - .45 * hl9)]
        print(f'  M4 chargé : {r9["M4"]} ; couleurs passées par la planche {r9["couleurs"]} ; vêtement exporté {tuple(px)} (attendu {tuple(att)}, '
              f'{contraste(hexrgb("#00a19a"), px):.2f}:1 contre la main)')
        check(r9['M4'] and np.abs(px - np.array(att)).max() <= 2 and contraste(hexrgb('#00a19a'), px) >= 2.6, 'dans la planche : le garde-fou corrige le vêtement par défaut de plate.js')
        check(not errs2, f'planche : aucune erreur JS ({errs2[:3]})')
        await b.close()
    print('\n' + ('TOUT EST BON' if not ECHECS else f'{len(ECHECS)} ÉCHEC(S) : ' + ' | '.join(ECHECS)))
    return 1 if ECHECS else 0

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
