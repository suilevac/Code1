"""Essai libre (réglages) : quelques poses × vues, image unique.
Usage : engine_essai.py ['{"nom": pose, …}'] [vues] [sortie.png] [taille] — sans argument : quatre presets (Repos,
Poing serré, V (2), Pince) dans les vues paume, dos, profil, dos ¾."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *
POSES = json.loads(sys.argv[1]) if len(sys.argv) > 1 else None
VV = sys.argv[2].split(',') if len(sys.argv) > 2 else ['paume', 'dos', 'profil', 'dos34']
NOM = sys.argv[3] if len(sys.argv) > 3 else 'engine_essai.png'
TAILLE = int(sys.argv[4]) if len(sys.argv) > 4 else 440
VUES['dos34'] = q_mul(q_axe([1, 0, 0], -20), q_axe([0, 1, 0], 145))
VUES['paume34'] = q_mul(q_axe([1, 0, 0], 15), q_axe([0, 1, 0], -35))
async def main():
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, PAGE)
        tuiles = []
        poses = POSES
        if poses is None:
            pr = await pg.evaluate("AtelierHand.presets")
            poses = {n: pr[n] for n in ['Repos', 'Poing serré', 'V (2)', 'Pince']}
        for nom, pose in poses.items():
            for v in VV:
                im = await rendu(pg, {'pose': pose, 'cote': 'D', 'orientation': VUES[v], 'w': TAILLE, 'h': TAILLE, 'style': {'largeurTrait': 0.8}})
                pen = await pg.evaluate("p=>AtelierHand.penetration(p,true)", pose)
                tuiles.append((sur_blanc(im), '%s %s %.0fms pen %.2f %s' % (nom, v, im.info['t'], pen['profondeur'] * 10, pen['paire'])))
        planche(tuiles, len(VV)).save(os.path.join(OUT, NOM))
        print('erreurs', [e for e in err if 'GPU stall' not in e][:8])
        await b.close()
asyncio.run(main())
