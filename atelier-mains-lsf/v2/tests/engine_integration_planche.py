"""Intégration : l'éditeur de planche (M3, v2/plate/index.html) avec le VRAI moteur à la place du bouchon. La page est
servie telle quelle, sauf la balise du bouchon (stub_hand.js) remplacée EN MÉMOIRE par three.js + GLTFLoader +
shaders.js + engine.js. Gabarits A (bannière + deux mains) et D (planche 4 étapes), export PNG ×1, marionnette sur une
main de la planche → tests/out/engine_integration_*.png.
Relecture adverse : la marionnette n'était pas posée sur l'objet (cadre plus grand, décalé) et sa barre (poignet,
pronation…) était invisible. Contrôlé maintenant : le cadre de l'hôte = le cadre de l'objet à l'écran (écart en px),
la barre est visible dans la barre contextuelle et ses curseurs agissent, un geste change la pose, Échap termine.
(M3 a été retouché pour cela : plate.js placeOverlays / ctxBar / marionnette, plate.css #puppet.)"""
import asyncio, base64, io, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *

async def main():
    html = open(os.path.join(V2, 'plate', 'index.html'), encoding='utf-8').read()
    moteur = ('<script src="../engine/vendor/three.min.js"></script><script src="../hand/vendor/GLTFLoader.js"></script>'
              '<script src="../engine/shaders.js"></script><script src="../engine/engine.js"></script>'
              '<script>window.pret=null;AtelierHand.charger("../hand/hand_v2.glb","../hand/hand_v2.json").then(()=>window.pret=true,e=>window.pret=String(e))</script>')
    assert '<script src="stub_hand.js"></script>' in html
    html = html.replace('<script src="stub_hand.js"></script>', moteur)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
        pg = await b.new_page(viewport={'width': 1500, 'height': 950})
        err = []; pg.on('pageerror', lambda e: err.append('pageerror ' + str(e)))
        pg.on('console', lambda m: err.append(m.text) if m.type == 'error' else None)
        async def route(r):
            u = r.request.url.split('?')[0]; ch = u.replace('https://m2.local/', '')
            if ch == 'plate/index.html': return await r.fulfill(body=html, content_type='text/html')
            f = os.path.join(V2, ch)
            if os.path.isfile(f): return await r.fulfill(path=f, content_type=TYPES.get(os.path.splitext(f)[1], 'application/octet-stream'))
            return await r.fulfill(status=404, body='absent')
        await pg.route('https://m2.local/**', route)
        await pg.goto('https://m2.local/plate/index.html')
        await pg.wait_for_function('window.pret !== null', timeout=180000)
        assert await pg.evaluate('window.pret') is True
        await pg.wait_for_timeout(1500)
        res = {}
        for g in ['A', 'D']:
            await pg.evaluate("g=>__plate.gabarit(g)", g)
            await pg.wait_for_timeout(500)
            # rendre toutes les mains (au repos, peint() les rend toutes)
            for i in range(30):
                await pg.evaluate("()=>{__plate.invalide();__plate.peint()}")
                await pg.wait_for_timeout(120)
            r = await pg.evaluate("""async()=>{const r=await __plate.exporte({k:1,embarque:false});const fr=new FileReader();
              const u=await new Promise(ok=>{fr.onload=()=>ok(fr.result);fr.readAsDataURL(r.blob)});return {u,w:r.w,h:r.h,mains:__plate.S.doc.elements.filter(e=>e.type==='main').length,rendus:__plate.S.rendus||0}}""")
            im = png(r['u']); im.convert('RGB').save(os.path.join(OUT, 'engine_integration_gabarit_%s.png' % g))
            res[g] = {'w': r['w'], 'h': r['h'], 'mains': r['mains'], 'rendus': r['rendus']}
        # marionnette sur la première main
        idm = await pg.evaluate("()=>__plate.S.doc.elements.find(e=>e.type==='main').id")
        await pg.evaluate("id=>__plate.marionnette(id)", idm)
        await pg.wait_for_timeout(1500)
        etat = await pg.evaluate("""id=>{const P=__plate,e=P.parId(id),cv=document.querySelector('#puppet canvas'),r=cv&&cv.getBoundingClientRect();
          const st=document.getElementById('stage')||document.querySelector('.stage')||cv.offsetParent, sr=st.getBoundingClientRect();
          // cadre de l'objet à l'écran (élément sans rotation dans le gabarit) : ecran(e.x, e.y) → coin haut-gauche
          const [sx,sy]=P.ecran?P.ecran(e.x,e.y):[NaN,NaN];
          const barre=document.querySelector('#ctx .puppet-barre'), ctx=document.getElementById('ctx');
          const curs=barre?barre.querySelectorAll('input[type=range]').length:0;
          return {mode:P.S.mode,canvas:!!cv,w:cv&&cv.width,cadre_ecran:[Math.round(sx+sr.left),Math.round(sy+sr.top),Math.round(e.w*P.S.zoom),Math.round(e.h*P.S.zoom)],
            canevas:r?[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]:null,barre_visible:!!(ctx&&!ctx.hidden&&barre&&barre.firstElementChild&&barre.firstElementChild.offsetWidth>0),curseurs:curs,
            ctx_rect:ctx?[Math.round(ctx.getBoundingClientRect().left),Math.round(ctx.getBoundingClientRect().top)]:null}}""", idm)
        if etat['cadre_ecran'] and etat['canevas']:
            etat['ecart_cadre_px'] = max(abs(a - b) for a, b in zip(etat['cadre_ecran'], etat['canevas']))
        shot = await pg.screenshot()
        png('data:image/png;base64,' + base64.b64encode(shot).decode()).convert('RGB').save(os.path.join(OUT, 'engine_integration_marionnette.png'))
        # geste : tirer le bout de l'index de la marionnette, relâcher → la pose de l'élément change (onChange)
        p0 = await pg.evaluate("id=>JSON.stringify(__plate.parId(id).pose)", idm)
        pt = await pg.evaluate("()=>{const m=__plate.S.puppet,p=m.centreDe('index',2),r=document.querySelector('#puppet canvas').getBoundingClientRect();return [p[0]+r.left,p[1]+r.top]}")
        await pg.mouse.move(*pt); await pg.mouse.down()
        for i in range(1, 9): await pg.mouse.move(pt[0], pt[1] + 12 * i); await pg.wait_for_timeout(50)
        await pg.mouse.up(); await pg.wait_for_timeout(400)
        p1 = await pg.evaluate("id=>JSON.stringify(__plate.parId(id).pose)", idm)
        # curseur « pronation » de la barre : il agit sur la pose de l'élément
        pr0 = await pg.evaluate("id=>__plate.parId(id).pose.prono||0", idm)
        await pg.evaluate("""()=>{const l=[...document.querySelectorAll('#ctx .puppet-barre label')].find(x=>x.textContent.startsWith('pronation'));
          const i=l.querySelector('input');i.value=40;i.dispatchEvent(new Event('input'));i.dispatchEvent(new Event('change'))}""")
        await pg.wait_for_timeout(600)
        pr1 = await pg.evaluate("id=>__plate.parId(id).pose.prono||0", idm)
        shot2 = await pg.screenshot()
        png('data:image/png;base64,' + base64.b64encode(shot2).decode()).convert('RGB').save(os.path.join(OUT, 'engine_integration_marionnette_geste.png'))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(300)
        mode_apres = await pg.evaluate("()=>__plate.S.mode")
        res['marionnette'] = dict(etat, pose_changee=p0 != p1, pronation_curseur=[round(pr0, 1), round(pr1, 1)], echap_mode=mode_apres)
        if mode_apres == 'marionnette': await pg.evaluate("()=>__plate.finMarionnette()")
        res['erreurs'] = err[:8]
        print(json.dumps(res, ensure_ascii=False))
        await b.close()
asyncio.run(main())
