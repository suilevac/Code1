"""Fumée : chargement, contrôles des assets décodés, quatre vues de la pose zéro, temps."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *

async def main():
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, PAGE)
        info = await pg.evaluate("""()=>{const I=AtelierHand._interne,A=I.assets();
          return {ecart:A.ecartJsonGlb,eventail:A.eventail,couture:A.couture,n:A.n,morphs:A.morphs.map(m=>[m.nom,m.idx.length]),
            parts:[0,1,2,3,4,5].map(k=>A.part.filter(x=>x===k).length),
            segs:I.segs().map(s=>[s.chaine,s.g,+s.L.toFixed(2),+s.rLat.toFixed(3),+s.rPal.toFixed(3),+s.rDos.toFixed(3)]),
            webgl2:I.horsEcran().webgl2,tuile:I.horsEcran().tuile}}""")
        print(json.dumps(info, ensure_ascii=False))
        tuiles = []
        for nom in ['paume', 'dos', 'profil', 'dessus']:
            im = await rendu(pg, {'pose': {}, 'cote': 'D', 'orientation': VUES[nom], 'w': 420, 'h': 520})
            tuiles.append((sur_blanc(im), '%s %.0f ms' % (nom, im.info['t'])))
        for nom in ['paume', 'dos']:
            im = await rendu(pg, {'pose': {}, 'cote': 'G', 'orientation': VUES[nom], 'w': 420, 'h': 520})
            tuiles.append((sur_blanc(im), 'G %s %.0f ms' % (nom, im.info['t'])))
        planche(tuiles, 6, 'fumée : pose zéro').save(os.path.join(OUT, 'engine_fumee.png'))
        print('erreurs', err[:8])
        await b.close()
asyncio.run(main())
