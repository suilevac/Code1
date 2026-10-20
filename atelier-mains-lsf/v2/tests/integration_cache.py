"""Cache des mains avec le VRAI coût de rendu (outil.md § 4.4) dans la page construite dist/atelier-v2.local.html.
Règles contrôlées : au plus UN rendu par image pendant un geste ; un cache sert jusqu'à ×1,5 pendant un geste ;
rendus « asynchrones » (une main par image, l'interface repeinte entre deux) quand un rendu coûte plus de 50 ms.
Mesures (dpr 2, rendu logiciel) : gabarit D (4 mains) — nombre de rendus, plus longue image, temps jusqu'à la dernière
main ; redimensionnement d'une main au coin (geste) — rendus pendant / après, plus longue image ; déplacement (0 rendu
attendu) ; zoom à la molette. → tests/out/integration_cache.json"""
import asyncio, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integration_commun import *


async def attendre_rendus(pg, delai=60):
    """Attend qu'aucune main ne reste à rendre ; → secondes."""
    t = time.time()
    while time.time() - t < delai:
        n = await pg.evaluate('()=>__plate.salesRestantes?__plate.salesRestantes():0')
        await pg.wait_for_timeout(200)
        n2 = await pg.evaluate('()=>__plate.salesRestantes?__plate.salesRestantes():0')
        if n == 0 and n2 == 0:
            return time.time() - t
    return None


async def main():
    res = {}
    async with async_playwright() as p:
        b, pg, err, t_pret = await ouvrir(p, dpr=2)
        res['pret_s'] = round(t_pret, 2)
        await pg.wait_for_timeout(500)
        # --- A. gabarit D : quatre mains à rendre d'un coup ---
        await chrono_debut(pg)
        r0 = await pg.evaluate('__plate.S.rendus||0'); t0 = time.time()
        await pg.evaluate("()=>__plate.gabarit('D')")
        res['D_attente_s'] = await attendre_rendus(pg)
        res['D_attente_s'] = round(res['D_attente_s'] or -1, 2) if res['D_attente_s'] else None
        res['D_total_s'] = round(time.time() - t0, 2)
        res['D_rendus'] = await pg.evaluate('__plate.S.rendus||0') - r0
        res['D_images'] = await chrono_fin(pg)
        res['D_apercus'] = await pg.evaluate('__plate.S.apercus||0')
        res['ms_par_Mpx'] = await pg.evaluate('()=>__plate.coutMpx?Math.round(__plate.coutMpx()):null')
        # --- B. redimensionner la 1re main par le coin bas-droit (geste de 1,5 s, 24 pas, ×1,6 en tout) ---
        ids = await pg.evaluate("()=>__plate.S.doc.elements.filter(e=>e.type==='main').map(e=>e.id)")
        e0 = ids[0]
        await pg.evaluate('id=>__plate.selectionne([id])', e0)
        await pg.wait_for_timeout(300)
        c = await pg.evaluate("""id=>{const P=__plate,e=P.parId(id),r=document.getElementById('stage').getBoundingClientRect();
          const [x,y]=P.ecran(e.x+e.w,e.y+e.h);return [x+r.left,y+r.top,e.w*P.S.zoom]}""", e0)
        await attendre_rendus(pg)
        await chrono_debut(pg)
        r0 = await pg.evaluate('__plate.S.rendus||0')
        await pg.mouse.move(c[0], c[1]); await pg.mouse.down()
        for i in range(1, 25):
            await pg.mouse.move(c[0] + c[2] * 0.6 * i / 24, c[1] + c[2] * 0.6 * i / 24 * 1.3)
            await pg.wait_for_timeout(60)
        r_pendant = await pg.evaluate('__plate.S.rendus||0') - r0
        im_pendant = await chrono_fin(pg)
        await pg.mouse.up()
        await chrono_debut(pg)
        t0 = time.time(); await attendre_rendus(pg); t_apres = time.time() - t0
        res['coin'] = {'rendus_pendant': r_pendant, 'images_pendant': im_pendant,
                       'rendus_apres': await pg.evaluate('__plate.S.rendus||0') - r0 - r_pendant,
                       'images_apres': await chrono_fin(pg), 'attente_apres_s': round(t_apres, 2),
                       'agrandi': await pg.evaluate('id=>Math.round(__plate.parId(id).w)', e0)}
        # --- C. déplacer la main (même taille : aucun rendu) ---
        c = await pg.evaluate("""id=>{const P=__plate,e=P.parId(id),r=document.getElementById('stage').getBoundingClientRect();
          const [x,y]=P.ecran(e.x+e.w/2,e.y+e.h*.6);return [x+r.left,y+r.top]}""", e0)
        await chrono_debut(pg); r0 = await pg.evaluate('__plate.S.rendus||0')
        await pg.mouse.move(c[0], c[1]); await pg.mouse.down()
        for i in range(1, 21):
            await pg.mouse.move(c[0] + 6 * i, c[1] + 2 * i); await pg.wait_for_timeout(40)
        await pg.mouse.up(); await pg.wait_for_timeout(600)
        res['deplacer'] = {'rendus': await pg.evaluate('__plate.S.rendus||0') - r0, 'images': await chrono_fin(pg)}
        # --- D. zoom à la molette (Ctrl) ×2 environ, 10 crans ---
        await attendre_rendus(pg)
        r0 = await pg.evaluate('__plate.S.rendus||0'); await chrono_debut(pg)
        await pg.mouse.move(700, 500)
        await pg.keyboard.down('Control')
        for i in range(10):
            await pg.mouse.wheel(0, -60); await pg.wait_for_timeout(50)
        await pg.keyboard.up('Control')
        r_pendant = await pg.evaluate('__plate.S.rendus||0') - r0
        im_pendant = await chrono_fin(pg)
        await chrono_debut(pg); t0 = time.time(); await attendre_rendus(pg)
        res['zoom'] = {'rendus_pendant': r_pendant, 'images_pendant': im_pendant, 'zoom': await pg.evaluate('__plate.S.zoom'),
                       'rendus_total': await pg.evaluate('__plate.S.rendus||0') - r0, 'images_apres': await chrono_fin(pg),
                       'attente_apres_s': round(time.time() - t0, 2)}
        res['cache_Mo'] = round(await pg.evaluate('__plate.cacheOctets()') / 1e6, 1)
        res['ms_par_Mpx'] = await pg.evaluate('()=>__plate.coutMpx?Math.round(__plate.coutMpx()):null')
        res['dernier_rendu'] = await pg.evaluate('__plate.S.dernierRendu||null')
        res['apercus_total'] = await pg.evaluate('__plate.S.apercus||0')
        res['erreurs'] = err
        await pg.screenshot(path=os.path.join(OUT, 'integration_cache.png'))
        await b.close()
    nom = sys.argv[1] if len(sys.argv) > 1 else 'integration_cache.json'
    json.dump(res, open(os.path.join(OUT, nom), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))

asyncio.run(main())
