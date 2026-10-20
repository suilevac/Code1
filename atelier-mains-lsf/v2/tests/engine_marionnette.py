"""Marionnette (v2/engine/test.html, vraie page) : tirer le bout de l'index (tout le doigt se replie), le milieu du
majeur, Maj + bout de l'annulaire (une articulation), clic droit (verrou), double clic (tendre), Alt (quatre doigts),
paume (rotation) ; mesure le temps d'un rafraîchissement (médiane sur 20) ; captures → tests/out/engine_marionnette.png"""
import asyncio, json, os, sys, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *

async def main():
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, None, url='https://m2.local/engine/test.html', vue=(1200, 860))
        await pg.wait_for_function('window.pret !== undefined && window.marionnette', timeout=180000)
        etapes, controles = [], []
        async def capture(lg):
            box = await pg.locator('#scene').bounding_box()
            im = png('data:image/png;base64,' + __import__('base64').b64encode(await pg.screenshot(clip=box)).decode())
            etapes.append((im.convert('RGB').resize((im.width // 2 * 2 // 2, im.height // 2 * 2 // 2)), lg))
        async def ecran(k, g, centre=False):
            r = await pg.evaluate("([k,g,c])=>{const m=window.marionnette,p=c?m.centreDe(k,g):m.ecranDe(k,g),r=document.querySelector('#cadre canvas').getBoundingClientRect();return [p[0]+r.left,p[1]+r.top]}", [k, g, centre])
            return r
        async def tirer(k, g, dx, dy, mods=(), centre=True):
            x, y = await ecran(k, g, centre)
            for m in mods: await pg.keyboard.down(m)
            await pg.mouse.move(x, y); await pg.mouse.down()
            for i in range(1, 9): await pg.mouse.move(x + dx * i / 8, y + dy * i / 8); await pg.wait_for_timeout(60)
            await pg.mouse.up()
            for m in mods: await pg.keyboard.up(m)
            await pg.wait_for_timeout(250)
            return await pg.evaluate('window.marionnette.pose()')
        await capture('départ (Dessin)')
        p0 = await pg.evaluate('window.marionnette.pose()')
        # 1. bout de l'index tiré vers le poignet : MCP, IPP, IPD se plient ensemble (GRAB .85/1/.7)
        p1 = await tirer('index', 2, 0, 140)
        i = p1['index']; controles.append(('bout de l’index tiré : tout le doigt plie', i['mcp'] > 15 and i['pip'] > 15 and i['dip'] > 5, 'mcp %.0f pip %.0f dip %.0f' % (i['mcp'], i['pip'], i['dip'])))
        await capture('bout de l’index tiré')
        # 2. milieu du majeur : MCP + IPP, IPD inchangée (sauf couplage IPD ≥ 0,45 (IPP − 55))
        p2 = await tirer('majeur', 1, 0, 110)
        m = p2['majeur']; controles.append(('milieu du majeur : MCP + IPP', m['mcp'] > 10 and m['pip'] > 10, 'mcp %.0f pip %.0f dip %.0f' % (m['mcp'], m['pip'], m['dip'])))
        await capture('milieu du majeur tiré')
        # 3. Maj + bout de l'annulaire : l'IPD seule (la MCP et l'IPP ne bougent pas)
        p3 = await tirer('annulaire', 2, 0, 60, mods=['Shift'])
        a = p3['annulaire']; controles.append(('Maj + bout : une seule articulation (IPD)', abs(a['mcp'] - p2['annulaire']['mcp']) < 0.5 and abs(a['pip'] - p2['annulaire']['pip']) < 0.5 and a['dip'] > 3, 'mcp %.1f pip %.1f dip %.1f' % (a['mcp'], a['pip'], a['dip'])))
        # 4. clic droit sur la base de l'auriculaire (verrou), puis tirer son bout : la MCP ne bouge pas
        x, y = await ecran('auriculaire', 0, True)
        await pg.mouse.click(x, y, button='right'); await pg.wait_for_timeout(200)
        v = await pg.evaluate('window.marionnette.verrous()')
        p4 = await tirer('auriculaire', 2, 0, 90)
        au = p4['auriculaire']; controles.append(('clic droit = verrou : la MCP verrouillée ne bouge pas', v['auriculaire'][0] and abs(au['mcp'] - p3['auriculaire']['mcp']) < 0.5 and au['pip'] > 5, 'verrou %s, mcp %.1f pip %.1f' % (v['auriculaire'], au['mcp'], au['pip'])))
        await capture('verrou sur la base de l’auriculaire, bout tiré')
        # 5. double clic sur l'index : tendu
        x, y = await ecran('index', 1, True)
        await pg.mouse.dblclick(x, y); await pg.wait_for_timeout(300)
        p5 = await pg.evaluate('window.marionnette.pose()')
        controles.append(('double clic : doigt tendu', abs(p5['index']['mcp']) + abs(p5['index']['pip']) + abs(p5['index']['dip']) < 1, json.dumps(p5['index'])))
        await capture('double clic sur l’index : tendu')
        # 6. Alt + bout du majeur : les quatre doigts ensemble
        p6 = await tirer('majeur', 2, 0, 120, mods=['Alt'])
        controles.append(('Alt : les quatre doigts se plient ensemble', all(p6[k]['pip'] > p5[k]['pip'] + 5 or p6[k]['pip'] > 60 for k in ['index', 'majeur', 'annulaire', 'auriculaire']) or all(p6[k]['mcp'] > p5[k]['mcp'] + 5 for k in ['index', 'majeur', 'annulaire']),
                          ' / '.join('%s %.0f-%.0f' % (k[:3], p6[k]['mcp'], p6[k]['pip']) for k in ['index', 'majeur', 'annulaire', 'auriculaire'])))
        await capture('Alt + bout du majeur : quatre doigts')
        # 7. bout du pouce tiré vers la paume : vis sans fin (av ≥ 0,7 rap)
        p7 = await tirer('pouce', 2, -90, -20)
        t = p7['pouce']; controles.append(('pouce : vis sans fin respectée', t['av'] >= 0.7 * max(0, t['rap']) - 0.01, json.dumps({k: round(v, 1) for k, v in t.items()})))
        await capture('bout du pouce tiré')
        pen = await pg.evaluate('AtelierHand.penetration(window.marionnette.pose())')
        controles.append(('aucune interpénétration après les gestes', pen <= 0.3001, 'pénétration %.2f mm' % (pen * 10)))
        # 8. paume : rotation de la main
        q0 = await pg.evaluate('window.marionnette.orientation()')
        # point de la paume : on cherche un pixel « paume » près du bas du cadre
        pt = await pg.evaluate("""()=>{const c=document.querySelector('#cadre canvas'),r=c.getBoundingClientRect();return [r.left+r.width*0.5,r.top+r.height*0.78]}""")
        await pg.mouse.move(*pt); await pg.mouse.down()
        for i in range(1, 9): await pg.mouse.move(pt[0] + 15 * i, pt[1]); await pg.wait_for_timeout(50)
        await pg.mouse.up(); await pg.wait_for_timeout(300)
        q1 = await pg.evaluate('window.marionnette.orientation()')
        controles.append(('glisser la paume : la main tourne', sum(abs(a - b) for a, b in zip(q0, q1)) > 0.2, 'q %s → %s' % ([round(x, 2) for x in q0], [round(x, 2) for x in q1])))
        await capture('paume glissée : rotation')
        # temps de rafraîchissement : 20 rafraîchissements (peau + rendu, une pose qui change à chaque fois)
        d = await pg.evaluate("""async()=>{const m=window.marionnette,p=m.pose(),t=[];
          for(let i=0;i<20;i++){p.index.mcp=(i%2)*20;m.poser(p);t.push(m.chrono(true));await new Promise(r=>requestAnimationFrame(r))}return t}""")
        dc = await pg.evaluate("""async()=>{const m=window.marionnette,p=m.pose(),t=[];
          for(let i=0;i<20;i++){p.index.mcp=(i%2)*20;m.poser(p);t.push(m.chrono(false));await new Promise(r=>requestAnimationFrame(r))}return t}""")
        med = statistics.median(d); medc = statistics.median(dc)
        controles.append(('rafraîchissement de la marionnette pendant un geste (médiane sur 20, seuil 200 ms en rendu logiciel)', med < 200, '%.0f ms (min %.0f, max %.0f ; image de geste à 0,7 × la taille, sans MSAA) ; image complète au relâchement %.0f ms — rendu LOGICIEL swiftshader, 442 × 520 px (GPU : 3 à 10 × plus rapide, outil.md § 4.2)' % (med, min(d), max(d), medc)))
        planche(etapes, 4, 'marionnette (test.html) : gestes successifs').save(os.path.join(OUT, 'engine_marionnette.png'))
        # image de geste (réduite, sans MSAA) contre image complète : V (2) vue de dos → engine_marionnette_geste.png
        await pg.evaluate("()=>{const m=window.marionnette;m.poser(AtelierHand.presets['V (2)']);m.vue('dos')}")
        await pg.wait_for_timeout(400)
        box = await pg.locator('#cadre canvas').first.bounding_box(); gi = []
        for rap in [True, False]:
            await pg.evaluate("r=>window.marionnette.chrono(r)", rap)
            im = png('data:image/png;base64,' + __import__('base64').b64encode(await pg.screenshot(clip=box)).decode())
            gi.append((im.convert('RGB'), 'pendant un geste (0,7 ×, sans MSAA)' if rap else 'image complète (au relâchement)'))
        planche(gi, 2, 'marionnette : image de geste / image complète').save(os.path.join(OUT, 'engine_marionnette_geste.png'))
        # Échap : options.onFin (test.html affiche « Marionnette : Terminer … »)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
        fin = await pg.evaluate("document.body.innerText.includes('Marionnette : Terminer')")
        controles.append(('Échap : fin de la marionnette (options.onFin)', fin, 'message de test.html affiché' if fin else 'rien'))
        ok = True
        for nom, r, det in controles:
            print(('OK   ' if r else 'ÉCHEC') + ' ' + nom + ' — ' + det); ok &= bool(r)
        errs = [e for e in err if 'GPU stall' not in e]
        print('erreurs JS :', errs[:6] or 'aucune')
        print('TOUT EST BON' if ok and not errs else 'À REVOIR')
        await b.close()
asyncio.run(main())
