"""Planche de livraison de la v2 (chantier M5) → tests/out/livraison_v2.png
  1. gabarit A « cent » avec deux vraies mains et le référent (export ×1 de la page construite) ;
  2. « V (2) » v1 / v2 au MÊME angle (configuration enregistrée par la v1, rouverte par la v2) : face et dos ¾ ;
  3. poing serré (v1 / v2, ¾) et pince (v2, ¾) ;
  4. ongles en gros plan (dos, bouts des doigts, rendu 1 800 px) ;
  5. main droite et main gauche côte à côte (paume et dos ¾) ;
  6. gabarit F : un référent par étape, chacun son expression ;
  7. taille d'impression (relecture M5) : export A3 ×1 d'une main « V (2) » de 4 600 px par la page construite (gros
     plan du pouce : bord frange / tablette, plis arrêtés avant le pouce) et poing serré paume ¾ rendu à 1 800 px.
     Mesures : durée de l'export A3 et messages de progression vus, rugosité du bord de la frange (écart max et RMS à un
     polynôme de degré 3, px), jours enclos bouchés et seuil de miettes du rendu à 1 800 px.
Chiffres écrits dans tests/out/livraison_v2.json."""
import asyncio, io, json, math, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integration_commun import *
from PIL import Image, ImageDraw, ImageFont

POL = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
POLG = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
V1_CAS = [('V (2)', [0, 0, 52]), ('V (2)', [-30, 10, -40]), ('Poing serré', [34, 14, 38])]


def recadre_v1(im, marge=20):
    a = np.asarray(im.convert('RGB')).astype(int)
    from scipy import ndimage
    m = ndimage.binary_dilation((a[..., 1] - a[..., 0]) > 40, iterations=6)
    ys, xs = np.nonzero(m)
    return im.crop((max(0, xs.min() - marge), max(0, ys.min() - marge), min(im.width, xs.max() + marge), min(im.height, ys.max() + marge)))


def sur_blanc(im):
    im = im.convert('RGBA'); f = Image.new('RGBA', im.size, (255, 255, 255, 255)); f.alpha_composite(im); return f.convert('RGB')


def rugosite_frange(im):
    """bord entre la frange (claire) et la tablette de l'ongle : pixels de bord ajustés par un polynôme de degré 3 le long
    de leur axe principal → écart max et RMS (px). Escalier du masque par sommet : 10,0 / 3,9 px à 4 600 px."""
    from scipy import ndimage
    a = np.asarray(im.convert('RGB')).astype(int); L = a.mean(2)
    tab = (np.abs(a[..., 0] - 150) < 25) & (np.abs(a[..., 1] - 220) < 20) & (np.abs(a[..., 2] - 214) < 20)
    fr = ndimage.binary_opening((L > 214) & (a[..., 0] > 175) & (a[..., 0] < 250) & (a[..., 1] > 225), iterations=1)
    lab, n = ndimage.label(tab)
    if not n: return None
    tab = lab == (1 + int(np.argmax(ndimage.sum(tab, lab, range(1, n + 1)))))
    ys, xs = np.nonzero(fr & ndimage.binary_dilation(tab, iterations=2))
    if len(xs) < 20: return None
    P = np.stack([xs, ys], 1).astype(float); c = P.mean(0); Vt = np.linalg.svd(P - c, full_matrices=False)[2]
    t = (P - c) @ Vt[0]; d = (P - c) @ Vt[1]; r = d - np.polyval(np.polyfit(t, d, 3), t)
    return {'pixels': int(len(P)), 'longueur_px': round(float(np.ptp(t)), 1), 'ecart_max_px': round(float(np.abs(r).max()), 2), 'rms_px': round(float(np.sqrt((r ** 2).mean())), 2)}


def hauteur(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


async def main():
    res = {}
    async with async_playwright() as p:
        # --- v1 : configurations enregistrées et captures ---
        b1 = await p.chromium.launch(args=ARGS)
        pg1 = await b1.new_page(viewport={'width': 1300, 'height': 820})
        await pg1.goto(PAGE_V1); await pg1.wait_for_timeout(7000)
        # captures de la MAIN v1 seule : l'infobulle « Tire un doigt… » et les boutons de vue de la v1 sont masqués (relecture M5)
        await pg1.add_style_tag(content='#stage .over, #tip { display: none !important; }')
        v1 = []
        for preset, cam in V1_CAS:
            await pg1.evaluate("n=>{const A=window.__atelier;A.editable().f=JSON.parse(JSON.stringify(A.PRESETS['Dessin'].f));A.applyPreset(n)}", preset)
            await pg1.evaluate("c=>{const A=window.__atelier;A.camera.position.set(...c);A.camera.lookAt(0,0,0)}", cam)
            await pg1.wait_for_timeout(700)
            shot = await pg1.screenshot(clip={'x': 16, 'y': 66, 'width': 878, 'height': 737})
            v1.append((png_pil(shot), await pg1.evaluate("()=>JSON.parse(JSON.stringify(window.__atelier.snapshot()))")))
        await b1.close()
        # --- v2 ---
        b, pg, err, _ = await ouvrir(p, vue=(1500, 950))
        rend = """async([pose,cote,q,h])=>{const A=AtelierHand,p=typeof pose==='string'?A.presets[pose]:pose,b=A.bounds({pose:p,cote,orientation:q});
          return A.render({pose:p,cote,orientation:q,w:Math.round(h*b.w/b.h),h}).toDataURL()}"""
        v2 = []
        for (im1, js), (preset, cam) in zip(v1, V1_CAS):
            o = await pg.evaluate("o=>{__plate.charge(o);const e=__plate.S.doc.elements.find(x=>x.type==='main');return {pose:e.pose,q:e.orientation}}", js)
            v2.append(png_pil(await pg.evaluate(rend, [o['pose'], 'D', o['q'], 700])))
        q34 = v1[2] and (await pg.evaluate("o=>{__plate.charge(o);return __plate.S.doc.elements.find(x=>x.type==='main').orientation}", v1[2][1]))
        pince = png_pil(await pg.evaluate(rend, ['Pince', 'D', q34, 700]))
        # ongles : dos, bouts des doigts en gros plan
        ongles = png_pil(await pg.evaluate(rend, ['Main plate (B)', 'D', [0, 1, 0, 0], 1800]))
        oa = np.asarray(ongles)[..., 3] > 0
        ys, xs = np.nonzero(oa)
        ongles_gp = ongles.crop((xs.min() - 10, ys.min() - 10, xs.max() + 10, ys.min() + int(0.3 * (ys.max() - ys.min()))))
        # main droite et gauche côte à côte (paume, dos ¾)
        a = math.radians(150) / 2; qd = [0.0, math.sin(a), 0, math.cos(a)]   # dos ¾ : 150° autour de Y
        DG = []
        for pose, q in [('Main ouverte (5)', [0, 0, 0, 1]), ('L', qd)]:
            DG.append(png_pil(await pg.evaluate(rend, [pose, 'D', q, 520])))
            DG.append(png_pil(await pg.evaluate(rend, [pose, 'G', [q[0], -q[1], -q[2], q[3]], 520])))
        # gabarit A « cent » et gabarit F, export ×1
        await pg.evaluate("()=>{__plate.gabarit('A');const L=__plate.S.doc.elements;L[0].texte='cent';L[1].texte='Définition\\nLe nombre cent : dix fois dix.\\nLa main part du chiffre des centaines et glisse vers les zéros.';L[1].invite=undefined;L[1].surlignages=[{from:21,to:25,couleur:'#fff176'}];const m=L.filter(e=>e.type==='main');m[0].pose=JSON.parse(JSON.stringify(AtelierHand.presets['Index (1)']));m[1].pose=JSON.parse(JSON.stringify(AtelierHand.presets['O']));__plate.invalide()}")
        oct = await blob_octets(pg, "__plate.exporte({k:1,embarque:false}).then(r=>r.blob)")
        gabA = Image.open(io.BytesIO(oct)).convert('RGB')
        await pg.evaluate("""()=>{__plate.gabarit('F');const L=__plate.S.doc.elements;L[0].texte='content ?';const P=L.filter(e=>e.type==='personnage'),M=L.filter(e=>e.type==='main');
          ['neutre','sourcils_leves','sourire'].forEach((x,i)=>P[i].expression=x);['Main plate (B)','Main plate (B)','Main ouverte (5)'].forEach((n,i)=>M[i].pose=JSON.parse(JSON.stringify(AtelierHand.presets[n])));__plate.invalide()}""")
        oct = await blob_octets(pg, "__plate.exporte({k:1,embarque:false}).then(r=>r.blob)")
        gabF = Image.open(io.BytesIO(oct)).convert('RGB')
        # 7. taille d'impression : export A3 ×1 (main V (2) de 4 600 px), puis poing serré paume ¾ à 1 800 px
        await pg.evaluate("""()=>{__plate.nouveau();const d=__plate.S.doc;d.planche.format='A3';d.planche.w=3508;d.planche.h=4961;
          window.__msgs=[];new MutationObserver(()=>{const t=document.getElementById('expMsg').textContent;if(t&&window.__msgs[window.__msgs.length-1]!==t)window.__msgs.push(t)}).observe(document.getElementById('expMsg'),{childList:true,characterData:true,subtree:true})}""")
        await pg.evaluate("""()=>{const P=__plate,pose=JSON.parse(JSON.stringify(AtelierHand.presets['V (2)'])),b=AtelierHand.bounds({pose,cote:'D',orientation:[0,0,0,1]});
          const e=P.ajoute('main',{cote:'D',pose,orientation:[0,0,0,1],h:4600,w:4600*b.w/b.h});e.id='grande';e.x=(3508-e.w)/2;e.y=180;P.invalide()}""")
        t0 = time.time()
        oct = await blob_octets(pg, "__plate.exporte({k:1,transparent:true,embarque:false}).then(r=>r.blob)")
        res['A3'] = {'export_s': round(time.time() - t0, 1), 'messages': await pg.evaluate('window.__msgs')}
        a3 = Image.open(io.BytesIO(oct)).convert('RGBA'); res['A3']['taille'] = a3.size
        e = await pg.evaluate("()=>{const e=__plate.S.doc.elements.find(x=>x.id==='grande');return [e.x,e.y,e.w,e.h]}")
        pouce = a3.crop((int(e[0] + 0.25 * e[2]), int(e[1] + 0.42 * e[3]), int(e[0] + 0.75 * e[2]), int(e[1] + 0.72 * e[3])))
        res['A3']['frange_pouce'] = rugosite_frange(sur_blanc(pouce))
        r = await pg.evaluate("""q=>{const A=AtelierHand,p=A.presets['Poing serré'],b=A.bounds({pose:p,cote:'D',orientation:q});const c=A.render({pose:p,cote:'D',orientation:q,w:Math.round(1800*b.w/b.h),h:1800});
          return {u:c.toDataURL(),jours:c.jours,seuil:c.seuilMiettes,miettes:c.miettes,ms:Math.round(c.dureeRendu)}}""", [-0.12449, 0.29813, -0.03925, 0.94556])
        poing18 = png_pil(r['u']); res['poing_1800'] = {k: r[k] for k in ('jours', 'seuil', 'miettes', 'ms')}
        res['erreurs'] = err
        await b.close()

    # --- composition ---
    W = 2400
    f = ImageFont.truetype(POL, 24); fg = ImageFont.truetype(POLG, 34); fs = ImageFont.truetype(POLG, 28)
    blocs = []
    def section(titre, ims, legendes, h):
        ims = [hauteur(sur_blanc(i), h) for i in ims]
        tot = sum(i.width for i in ims) + 30 * (len(ims) - 1)
        if tot > W - 60:
            k = (W - 60 - 30 * (len(ims) - 1)) / sum(i.width for i in ims)
            ims = [hauteur(i, max(1, round(h * k))) for i in ims]; h = ims[0].height
        c = Image.new('RGB', (W, h + 100), 'white'); d = ImageDraw.Draw(c)
        d.text((30, 8), titre, fill=(0, 110, 105), font=fs)
        x = 30
        for im, lg in zip(ims, legendes):
            c.paste(im, (x, 50)); d.text((x, 56 + h), lg, fill=(20, 32, 31), font=f); x += im.width + 30
        blocs.append(c)
    section('1. Gabarit A « cent » : deux vraies mains (moteur 3D) et le référent — export ×1 de la page construite',
            [gabA], ['1 920 × 1 080, main droite « Index (1) », main gauche « O »'], 760)
    section('2. « V (2) » : la configuration enregistrée par la v1, rouverte par la v2 sous le même angle',
            [recadre_v1(v1[0][0]), v2[0], recadre_v1(v1[1][0]), v2[1]], ['v1 · face', 'v2 · face', 'v1 · dos ¾', 'v2 · dos ¾'], 560)
    section('3. Poing serré (v1 / v2) et pince (v2), vus de ¾',
            [recadre_v1(v1[2][0]), v2[2], pince], ['v1 · poing serré', 'v2 · poing serré', 'v2 · pince'], 520)
    section('4. Ongles en gros plan (Main plate (B), dos, rendu 1 800 px) — 5. main droite et main gauche (miroir 3D, même lumière)',
            [ongles_gp] + DG, ['ongles (dos)', 'D · paume', 'G · paume', 'D · dos ¾', 'G · dos ¾'], 460)
    section('6. Gabarit F : un référent par étape, chacun son expression (neutre · sourcils levés · sourire)',
            [gabF], ['expression réglée par étape (Propriétés du référent)'], 700)
    fp = res['A3']['frange_pouce'] or {}
    section('7. Taille d\u2019impression : export A3 ×1 (main de 4 600 px, gros plan du pouce) et poing serré paume ¾ (1 800 px)',
            [pouce, poing18], ['A3 · pouce de « V (2) » : frange nette (écart %.1f px), plis arrêtés avant le pouce' % fp.get('ecart_max_px', -1),
                               'poing serré ¾ · 1 800 px'], 900)
    H = sum(c.height for c in blocs) + 90
    out = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(out)
    d.text((30, 20), 'Atelier des mains LSF — v2 : planche de livraison (dist/atelier-v2.html)', fill=(20, 32, 31), font=fg)
    y = 80
    for c in blocs:
        out.paste(c, (0, y)); y += c.height
    out.save(os.path.join(OUT, 'livraison_v2.png'))
    res['taille'] = out.size
    json.dump(res, open(os.path.join(OUT, 'livraison_v2.json'), 'w'), indent=1, ensure_ascii=False)
    print(res)
    sys.exit(1 if res['erreurs'] else 0)

asyncio.run(main())
