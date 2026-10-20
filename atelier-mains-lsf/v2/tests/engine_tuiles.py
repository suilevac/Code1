"""Grands rendus par TUILES (exports ×2, ×3, A4, A3 : dès que w·ss ou h·ss dépasse la tuile, 4096 px de cible).
Relecture adverse du 19 octobre : une traînée noire horizontale traversait V (2) en dos ¾ à 2600 px (texture de la
couche des traits relue avec le mauvais pas de ligne) et le contour faisait une marche de 1 à 2 px à la couture.
Trois contrôles :
  A. COUTURES : la même image rendue d'une seule tuile, puis en tuiles forcées petites (RENDU.tuileMax = 520 px de
     cible : 8 à 12 tuiles), 3 poses × 12 orientations à 30 px/cm. Le rendu n'est pas identique au bit près : la
     rastérisation d'un sous-cadre (setViewOffset) bascule quelques échantillons au bord des triangles, et une arête AU
     SEUIL suit (mesuré : 200 à 250 petites taches de 1 à 20 px par image, réparties partout). Ce qu'une couture
     fausse produirait se voit autrement : des écarts CONCENTRÉS le long des lignes de couture. On compte donc les pixels
     dont l'alpha ou une couleur diffère de plus de 96 / 255 (deux échantillons sur quatre), et leur densité dans la
     bande de ± 3 px autour des coutures rapportée à la densité ailleurs, sur les 36 images ensemble (1 = aucune trace
     de couture ; exigence ≤ 2). Les plus grandes « taches » d'écart sont des rangées de 1 px le long du bord NET de la
     coupe de l'avant-bras (horizontal en vue paume, aligné sur les pixels : il bascule d'un bloc).
  B. EXACT À LA VRAIE TAILLE : Repos paume 2200 × 2600 (la marche signalée) et V (2) dos ¾ 2600 × 2600 (la traînée), en
     tuiles de 4096 contre une seule tuile de 8192 (la limite de swiftshader) : même mesure de couture, et ENCRE HORS DE
     LA MAIN → 0.
  C. VRAIE TAILLE, 12 ORIENTATIONS : V (2) à 2400 et 3000 px contre le rendu d'une seule tuile de moitié agrandi :
     encre hors de la main (alpha > 0 à plus de 10 px de la silhouette de référence) → 0 attendu.
Écrit tests/out/engine_tuiles.json et engine_tuiles.png (gros plans des coutures et vues à 3000 px)."""
import asyncio, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *
from engine_planches import O12

S_PX = 30.0

async def rendu_t(pg, o, tuile):
    await pg.evaluate("t => AtelierHand._interne.RENDU.tuileMax = t", tuile)
    r = await pg.evaluate("""o=>{const c=AtelierHand.render(o);return {url:c.toDataURL('image/png'),t:c.dureeRendu,n:c.tuiles,cx:(c.coutures||{}).x||[],cy:(c.coutures||{}).y||[]}}""", o)
    await pg.evaluate("AtelierHand._interne.RENDU.tuileMax = 0")
    im = png(r['url']).convert('RGBA'); im.info.update(t=r['t'], n=r['n'], cx=r['cx'], cy=r['cy'])
    return im

def coutures(a1, a2, cx, cy, seuil=96):
    """écarts (> seuil) et densité dans la bande ± 3 px des coutures / densité ailleurs"""
    d = (np.abs(a1.astype(int) - a2.astype(int)) > seuil).any(axis=2)
    bande = np.zeros(d.shape, bool)
    for x in cx: bande[:, max(0, int(round(x)) - 3):int(round(x)) + 4] = True
    for y in cy: bande[max(0, int(round(y)) - 3):int(round(y)) + 4, :] = True
    main = ndimage.binary_dilation((a1[..., 3] > 0) | (a2[..., 3] > 0), iterations=3)   # densités sur la main seulement
    db = d[bande & main].mean() if (bande & main).any() else 0.0
    da = d[~bande & main].mean() if (~bande & main).any() else 0.0
    lab, n = ndimage.label(d, structure=np.ones((3, 3)))
    gros = int(ndimage.sum(d, lab, range(1, n + 1)).max()) if n else 0
    return {'pixels_ecart': int(d.sum()), 'dans_bande': int(d[bande & main].sum()), 'aire_bande': int((bande & main).sum()),
            'hors_bande': int(d[~bande & main].sum()), 'aire_hors_bande': int((~bande & main).sum()),
            'densite_bande_sur_ailleurs': round(float(db / da), 2) if da > 0 else (0.0 if db == 0 else 99.0), 'plus_grande_tache': gros}

def hors_main(big, ref):
    """encre du grand rendu à plus de 10 px (5 px de la référence) de la silhouette de référence agrandie : la traînée
    corrigée passait à 300 px de la main ; une rangée de 1 px au bord net de la coupe (alignée sur les pixels, elle
    bascule d'un bloc d'une taille à l'autre) n'en est pas une"""
    refg = np.asarray(ref.resize(big.size, Image.NEAREST))[..., 3] > 0
    return int(((np.asarray(big)[..., 3] > 0) & ~ndimage.binary_dilation(refg, iterations=10)).sum())

async def main():
    rap = {'A_tuiles_forcees': {}, 'B_exact_vraie_taille': {}, 'C_12_orientations': {}}
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, PAGE)
        pr = await pg.evaluate("AtelierHand.presets")
        # ---------- A ----------
        for nom in ['V (2)', 'Repos', 'Poing serré']:
            rap['A_tuiles_forcees'][nom] = {}
            for vn, q in O12:
                o = {'pose': pr[nom], 'cote': 'D', 'orientation': q}
                bd = await pg.evaluate("o=>AtelierHand.bounds(o)", o)
                o['w'] = round(bd['w'] * S_PX); o['h'] = round(bd['h'] * S_PX)
                r1 = await rendu_t(pg, o, 0); r2 = await rendu_t(pg, o, 520)
                m = coutures(np.asarray(r1), np.asarray(r2), r2.info['cx'], r2.info['cy']); m['tuiles'] = r2.info['n']
                rap['A_tuiles_forcees'][nom][vn] = m
                print('A', nom, vn, m, flush=True)
        va = [m for d in rap['A_tuiles_forcees'].values() for m in d.values()]
        # densité d'écarts dans la bande des coutures rapportée à celle d'ailleurs, sur les 36 images ensemble (une image
        # isolée n'a souvent que 0 à 15 pixels d'écart : son rapport ne veut rien dire)
        db = sum(m['dans_bande'] for m in va) / max(1, sum(m['aire_bande'] for m in va))
        da = sum(m['hors_bande'] for m in va) / max(1, sum(m['aire_hors_bande'] for m in va))
        rap['A_densite_bande_sur_ailleurs'] = round(db / da, 2) if da else 0.0
        rap['A_pixels_ecart_total'] = sum(m['pixels_ecart'] for m in va)
        rap['A_pire_tache'] = max(m['plus_grande_tache'] for m in va)
        # ---------- B ----------
        gp = []
        for nom, vn, w, h in [('Repos', 'paume', 2200, 2600), ('V (2)', 'dos ¾ cubital', 2600, 2600)]:
            q = dict(O12)[vn]; o = {'pose': pr[nom], 'cote': 'D', 'orientation': q, 'w': w, 'h': h}
            t4 = await rendu_t(pg, o, 0); t8 = await rendu_t(pg, o, 8192)
            m = coutures(np.asarray(t4), np.asarray(t8), t4.info['cx'], t4.info['cy']); m['tuiles'] = t4.info['n']
            m['encre_hors_main'] = hors_main(t4, t8); m['ms_tuiles'] = round(t4.info['t']); m['ms_une'] = round(t8.info['t'])
            rap['B_exact_vraie_taille']['%s %s %d×%d' % (nom, vn, w, h)] = m
            print('B', nom, vn, m, flush=True)
            # gros plan de la couture horizontale, là où le contour la traverse
            y = int(t4.info['cy'][0]) if t4.info['cy'] else h // 2
            al = np.asarray(t4)[y, :, 3] > 0; xs = np.nonzero(al)[0]
            x = int(xs[-1]) if len(xs) else w // 2
            gp.append((sur_blanc(t4.crop((x - 120, y - 60, x + 40, y + 60))).resize((480, 360), Image.NEAREST), '%s : couture y = %d (×3)' % (nom, y)))
            if nom == 'V (2)': gp.append((sur_blanc(t4).resize((360, 360), Image.LANCZOS), 'V (2) 2600 px en 4 tuiles'))
        # ---------- C ----------
        vign = []
        for taille in [2400, 3000]:
            for vn, q in O12:
                o = {'pose': pr['V (2)'], 'cote': 'D', 'orientation': q, 'w': taille, 'h': taille}
                big = await rendu_t(pg, o, 0); ref = await rendu_t(pg, dict(o, w=taille // 2, h=taille // 2), 0)
                m = {'tuiles': big.info['n'], 'ms': round(big.info['t']), 'encre_hors_main': hors_main(big, ref)}
                rap['C_12_orientations']['%d %s' % (taille, vn)] = m
                print('C', taille, vn, m, flush=True)
                if taille == 3000: vign.append((sur_blanc(big).resize((240, 240), Image.LANCZOS), vn))
        rap['C_pire_hors_main'] = max(v['encre_hors_main'] for v in rap['C_12_orientations'].values())
        rap['B_pire_hors_main'] = max(v['encre_hors_main'] for v in rap['B_exact_vraie_taille'].values())
        rap['erreurs_js'] = [e for e in err if 'GPU stall' not in e][:10]
        planche(gp, 3, 'Coutures des tuiles à la vraie taille (gros plans ×3)').save(os.path.join(OUT, 'engine_tuiles_coutures.png'))
        planche(vign, 6, 'V (2) à 3000 px, rendu par tuiles (réduit)').save(os.path.join(OUT, 'engine_tuiles.png'))
        json.dump(rap, open(os.path.join(OUT, 'engine_tuiles.json'), 'w'), ensure_ascii=False, indent=1)
        print('A densité bande/ailleurs', rap['A_densite_bande_sur_ailleurs'], 'écarts', rap['A_pixels_ecart_total'], 'tache max', rap['A_pire_tache'], '| B hors main', rap['B_pire_hors_main'],
              '| C hors main', rap['C_pire_hors_main'], '| erreurs', rap['erreurs_js'])
        await b.close()

if __name__ == '__main__':
    asyncio.run(main())
