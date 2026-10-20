"""Parcours complet de l'utilisateur sur la page CONSTRUITE (dist/atelier-v2.local.html), avec les vrais gestes :
ouvrir la page → poser une main (outil Main D + clic) → configuration « V (2) » (bouton du panneau) → modifier la pose en
marionnette (double-clic, tirer le bout de l'index) → dupliquer (Ctrl+D), convertir en gauche (bouton), retourner
(Maj+H) → gabarit A « cent » (deux mains + référent) → texte de la définition surligné → image de fond collée (Ctrl+V
d'un fichier) → export ×2 (taille, transparence, JSON iTXt) → sauvegarde du projet (.json, téléchargement) →
rechargement de la page et réouverture du fichier → annuler (Suppr puis Ctrl+Z).
Aucune erreur JS tolérée ; temps mesurés (rendu logiciel). → tests/out/integration_parcours_*.png, _planche.png, .json"""
import asyncio, base64, io, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integration_commun import *
from PIL import Image

ECHECS = []
def check(c, msg):
    print(('  ok    ' if c else '  ÉCHEC ') + msg)
    if not c:
        ECHECS.append(msg)


def png_fond():
    """photo de test 1200 × 800 : dégradé orange → bleu (reconnaissable dans l'export)"""
    im = Image.new('RGB', (1200, 800))
    px = im.load()
    for y in range(800):
        for x in range(1200):
            px[x, y] = (250 - x * 200 // 1200, 150, 40 + x * 200 // 1200)
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()


async def main():
    T = {}; res = {}; shots = []; titres = []
    async with async_playwright() as p:
        b, pg, err, t = await ouvrir(p, vue=(1500, 950))
        T['ouvrir_page_pret_s'] = round(t, 2)
        dialogues = []
        async def accepte(d): dialogues.append(d.message); await d.accept()
        pg.on('dialog', lambda d: asyncio.ensure_future(accepte(d)))
        st = await pg.evaluate("()=>{const r=document.getElementById('stage').getBoundingClientRect();return[r.left,r.top]}")

        async def stable(delai=90):
            t0 = time.time()
            while time.time() - t0 < delai:
                if await pg.evaluate('()=>__plate.salesRestantes()') == 0:
                    await pg.wait_for_timeout(250)
                    if await pg.evaluate('()=>__plate.salesRestantes()') == 0:
                        return round(time.time() - t0, 2)
                await pg.wait_for_timeout(100)
            return None

        async def shot(nom, titre):
            await stable()
            f = os.path.join(OUT, 'integration_parcours_%s.png' % nom)
            await pg.screenshot(path=f); shots.append(f); titres.append(titre)

        async def centre(id, fy=0.5):
            x, y = await pg.evaluate("([id,fy])=>{const e=__plate.parId(id);return __plate.ecran(e.x+e.w/2,e.y+e.h*fy)}", [id, fy])
            return st[0] + x, st[1] + y

        n = lambda: pg.evaluate("()=>__plate.S.doc.elements.length")

        # 1. poser une main droite
        t0 = time.time()
        await pg.click('[data-outil=mainD]'); await pg.mouse.click(st[0] + 520, st[1] + 300)
        T['main_posee_rendue_s'] = round(time.time() - t0 + (await stable() or 0), 2)
        idD = await pg.evaluate("()=>__plate.S.doc.elements.find(e=>e.type==='main').id")
        check(await n() == 1, 'une main posée')
        # 2. configuration « V (2) » depuis le panneau Propriétés
        cx, cy = await centre(idD); await pg.mouse.click(cx, cy)
        await pg.click('[data-tab=props]')
        t0 = time.time()
        await pg.click('#props button[data-preset="V (2)"]')
        T['preset_V2_rendu_s'] = round(time.time() - t0 + (await stable() or 0), 2)
        v2 = await pg.evaluate("id=>__plate.parId(id).pose", idD)
        check(v2['annulaire']['mcp'] > 60 and v2['index']['mcp'] < 10, 'V (2) appliqué (annulaire replié %.0f°, index tendu)' % v2['annulaire']['mcp'])
        await shot('01_V2', '1-2. main D, « V (2) »')
        # 3. marionnette : double-clic, tirer le bout de l'index vers le bas
        cx, cy = await centre(idD, 0.6); await pg.mouse.dblclick(cx, cy)
        await pg.wait_for_timeout(1500)
        check(await pg.evaluate("()=>__plate.S.mode") == 'marionnette', 'double-clic → marionnette')
        pt = await pg.evaluate("()=>{const m=__plate.S.puppet,p=m.centreDe('index',2),r=document.querySelector('#puppet canvas').getBoundingClientRect();return [p[0]+r.left,p[1]+r.top]}")
        await chrono_debut(pg)
        t0 = time.time()
        await pg.mouse.move(*pt); await pg.mouse.down()
        for i in range(1, 11):
            await pg.mouse.move(pt[0], pt[1] + 9 * i); await pg.wait_for_timeout(60)
        await pg.mouse.up(); await pg.wait_for_timeout(600)
        T['geste_marionnette_s'] = round(time.time() - t0, 2)
        T['geste_marionnette_images'] = await chrono_fin(pg)
        p1 = await pg.evaluate("id=>__plate.parId(id).pose", idD)
        check(p1['index']['mcp'] + p1['index']['pip'] > v2['index']['mcp'] + v2['index']['pip'] + 15,
              'index tiré : MCP %.0f / IPP %.0f (avant %.0f / %.0f)' % (p1['index']['mcp'], p1['index']['pip'], v2['index']['mcp'], v2['index']['pip']))
        await shot('02_marionnette', '3. marionnette : index tiré')
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(400)
        check(await pg.evaluate("()=>__plate.S.mode") == 'planche', 'Échap → planche')
        # 4. dupliquer, convertir en gauche, retourner
        cx, cy = await centre(idD); await pg.mouse.click(cx, cy)
        await pg.keyboard.press('Control+d'); await pg.wait_for_timeout(200)
        idC = await pg.evaluate("()=>__plate.S.sel[0]")
        check(await n() == 2 and idC != idD, 'Ctrl+D : copie')
        await pg.evaluate("id=>{const e=__plate.parId(id);e.x+=e.w*1.3;__plate.invalide()}", idC)
        await pg.click('#ctx button:has-text("main gauche")')
        e = await pg.evaluate("id=>{const e=__plate.parId(id);return{cote:e.cote,q:e.orientation,pose:e.pose}}", idC)
        check(e['cote'] == 'G' and e['pose']['index']['mcp'] == p1['index']['mcp'], 'convertie en gauche, pose gardée')
        await pg.keyboard.press('Shift+H'); await pg.wait_for_timeout(200)
        check(await pg.evaluate("id=>__plate.parId(id).flipH", idC) is True, 'retournée (Maj+H)')
        await shot('03_copie_gauche', '4. copie → main gauche, retournée')
        # 5. gabarit A « cent » : deux mains + référent
        t0 = time.time()
        await pg.click('#bGabarits'); await pg.click('#gabarits button:has-text("Bannière")')
        await pg.wait_for_timeout(300)
        T['gabarit_A_rendu_s'] = round(time.time() - t0 + (await stable() or 0), 2)
        g = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>e.type)")
        check(g == ['texte', 'texte', 'personnage', 'main', 'main'], 'gabarit A : %s' % g)
        ban = await pg.evaluate("()=>__plate.S.doc.elements[0].id")
        await pg.evaluate("id=>__plate.editeTexte(id)", ban); await pg.wait_for_timeout(200)
        await pg.keyboard.press('Control+a'); await pg.keyboard.type('cent')
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
        check(await pg.evaluate("id=>__plate.parId(id).texte", ban) == 'cent', 'bannière « cent »')
        mains = await pg.evaluate("()=>__plate.S.doc.elements.filter(e=>e.type==='main').map(e=>e.id)")
        for idm, pr in zip(mains, ['Index (1)', 'O']):
            cx, cy = await centre(idm); await pg.mouse.click(cx, cy); await pg.click('[data-tab=props]')
            await pg.click('#props button[data-preset="%s"]' % pr)
        # 6. définition : texte et surlignage
        dfn = await pg.evaluate("()=>__plate.S.doc.elements[1].id")
        await pg.evaluate("id=>__plate.editeTexte(id)", dfn); await pg.wait_for_timeout(200)
        await pg.keyboard.press('Control+a')
        await pg.keyboard.type('Définition')
        await pg.keyboard.press('Enter')
        await pg.keyboard.type('Le nombre cent : dix fois dix.')
        txt = await pg.evaluate("id=>document.getElementById('texte').innerText", dfn)
        await pg.evaluate("""()=>{const ed=document.getElementById('texte');const w=document.createTreeWalker(ed,NodeFilter.SHOW_TEXT);let t;
          while((t=w.nextNode())){const i=t.data.indexOf('cent');if(i>=0){const r=document.createRange();r.setStart(t,i);r.setEnd(t,i+4);const s=getSelection();s.removeAllRanges();s.addRange(r);return}}}""")
        await pg.click('#ctx button:has-text("Surligner")'); await pg.wait_for_timeout(200)
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
        t_ = await pg.evaluate("id=>{const e=__plate.parId(id);return{texte:e.texte,s:e.surlignages}}", dfn)
        sl = t_['s'][0] if t_['s'] else None
        check(sl is not None and t_['texte'][sl['from']:sl['to']] == 'cent', 'surlignage sur « cent » : %s' % sl)
        # 7. image de fond collée (Ctrl+V d'un fichier) → Définir comme fond
        await pg.evaluate("()=>__plate.selectionne([])")
        await pg.focus('#stage')
        await pg.evaluate("""b64=>{const bin=atob(b64),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
          const f=new File([u],'photo.png',{type:'image/png'});const dt=new DataTransfer();dt.items.add(f);document.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true}))}""",
                          base64.b64encode(png_fond()).decode())
        await pg.wait_for_timeout(1000)
        check(await pg.evaluate("()=>__plate.S.doc.elements.some(e=>e.type==='image')"), 'image collée')
        await pg.click('#ctx button:has-text("Définir comme fond")'); await pg.wait_for_timeout(300)
        F = await pg.evaluate("()=>({type:__plate.S.doc.planche.fond.type,images:__plate.S.doc.elements.filter(e=>e.type==='image').length})")
        check(F == {'type': 'image', 'images': 0}, 'fond image : %s' % F)
        await shot('04_gabarit_A_cent', '5-7. gabarit A « cent », surlignage, fond collé')
        # 8. export ×2 : taille, JSON iTXt ; ×1 transparent
        t0 = time.time()
        octets = await blob_octets(pg, "__plate.exporte({k:2}).then(r=>r.blob)")
        T['export_x2_s'] = round(time.time() - t0, 2)
        im2 = Image.open(io.BytesIO(octets)); im2.save(os.path.join(OUT, 'integration_parcours_export_x2.png'))
        res['export_x2'] = {'w': im2.width, 'h': im2.height, 'octets': len(octets)}
        check((im2.width, im2.height) == (3840, 2160), 'export ×2 : %d × %d, %d Ko' % (im2.width, im2.height, len(octets) // 1024))
        js = itxt(octets)
        o = json.loads(js) if js else None
        res['export_x2']['itxt_octets'] = len(js.encode()) if js else 0
        check(o is not None and o['version'] == 9 and len(o['elements']) == 5, 'JSON du projet dans le chunk iTXt : v%s, %s éléments' % (o and o['version'], o and len(o['elements'])))
        t0 = time.time()
        oct1 = await blob_octets(pg, "__plate.exporte({k:1,transparent:true,embarque:false}).then(r=>r.blob)")
        T['export_x1_transparent_s'] = round(time.time() - t0, 2)
        im1 = Image.open(io.BytesIO(oct1)).convert('RGBA')
        a = im1.getchannel('A')
        coins = [a.getpixel((3, 3)), a.getpixel((im1.width - 4, im1.height - 4))]
        main_px = int((__import__('numpy').asarray(a) > 0).sum())
        check(coins == [0, 0] and main_px > 10000, 'export transparent : coins alpha %s, %d px opaques (textes, référent, mains)' % (coins, main_px))
        im1.save(os.path.join(OUT, 'integration_parcours_export_transparent.png'))
        res['export_transparent'] = {'w': im1.width, 'h': im1.height, 'coins_alpha': coins, 'px_opaques': main_px}
        # 9. sauvegarde du projet (.json) : téléchargement (pas de capability hors claude.ai)
        await pg.click('[data-tab=projet]')
        async with pg.expect_download() as dl:
            await pg.click('#bJsonExport')
        d = await dl.value
        chemin = os.path.join(OUT, 'integration_parcours_projet.atelier.json')
        await d.save_as(chemin)
        proj = json.load(open(chemin, encoding='utf-8'))
        res['projet_json'] = {'nom_fichier': d.suggested_filename, 'octets': os.path.getsize(chemin), 'elements': len(proj['elements']),
                              'fond': proj['planche']['fond']['type'], 'assets': len(proj.get('assets', {}))}
        check(len(proj['elements']) == 5 and proj['planche']['fond']['type'] == 'image' and len(proj['assets']) == 1,
              'projet téléchargé : %s' % res['projet_json'])
        avant = await pg.evaluate("()=>JSON.stringify(__plate.serialise().elements.map(e=>[e.type,Math.round(e.x),Math.round(e.y),e.pose||e.texte||e.expression||'']))")
        # 10. rechargement de la page, réouverture du fichier
        t0 = time.time()
        await pg.reload(); await pg.evaluate('()=>AtelierHand.ready')
        T['rechargement_pret_s'] = round(time.time() - t0, 2)
        await pg.click('[data-tab=projet]')
        await pg.set_input_files('#fichierProjet', chemin)
        await pg.wait_for_timeout(800)
        T['reouverture_rendue_s'] = await stable()
        apres = await pg.evaluate("()=>JSON.stringify(__plate.serialise().elements.map(e=>[e.type,Math.round(e.x),Math.round(e.y),e.pose||e.texte||e.expression||'']))")
        check(apres == avant, 'rechargé et rouvert à l\'identique (types, positions, poses, textes)')
        await shot('05_rouvert', '10. après rechargement : projet rouvert')
        # 11. annuler : supprimer une main, Ctrl+Z
        nb = await n()
        idm = await pg.evaluate("()=>__plate.S.doc.elements.find(e=>e.type==='main').id")
        cx, cy = await centre(idm); await pg.mouse.click(cx, cy)
        await pg.keyboard.press('Delete'); await pg.wait_for_timeout(200)
        n1 = await n()
        await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(300)
        n2 = await n()
        check(n1 == nb - 1 and n2 == nb and await pg.evaluate("id=>!!__plate.parId(id)", idm), 'Suppr puis Ctrl+Z : %d → %d → %d' % (nb, n1, n2))
        res['rendus_total'] = await pg.evaluate('__plate.S.rendus||0')
        res['dialogues'] = dialogues
        res['erreurs'] = err
        check(not err, 'aucune erreur JS (%d)' % len(err))
        await b.close()
    res['temps'] = T
    res['echecs'] = ECHECS
    ims = [Image.open(f).convert('RGB').crop((64, 78, 1160, 950)) for f in shots]
    planche(ims, titres, 3, titre='Parcours complet (page construite, vrai moteur)', largeur_case=560).save(os.path.join(OUT, 'integration_parcours_planche.png'))
    json.dump(res, open(os.path.join(OUT, 'integration_parcours.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(T, indent=1, ensure_ascii=False))
    print('PARCOURS :', 'OK' if not ECHECS else 'ÉCHEC (%d)' % len(ECHECS))
    sys.exit(1 if ECHECS else 0)

asyncio.run(main())
