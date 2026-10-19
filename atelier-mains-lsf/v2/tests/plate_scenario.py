"""Scénario d'interface de l'éditeur de planche (v2/plate) sous Playwright + Chromium headless.

  python3 v2/tests/plate_scenario.py        → captures v2/tests/out/plate_*.png + planche v2/tests/out/plate_scenario.png

Le scénario passe par les VRAIS gestes (clics d'outil, glisser à la souris, raccourcis clavier, collage d'un fichier
image, boutons de la barre contextuelle) et vérifie des chiffres : nombre d'éléments, position après déplacement,
segments de surlignage, taille de l'export, nombre d'éléments après annuler. Aucune erreur JS tolérée (pageerror).
"""
import asyncio, base64, io, json, os, sys
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = 'file://' + os.path.join(ROOT, 'plate', 'index.html')
OUT = os.path.join(ROOT, 'tests', 'out'); os.makedirs(OUT, exist_ok=True)
ECHECS = []
def check(cond, msg):
    print(('  ok   ' if cond else '  ÉCHEC ') + msg)
    if not cond: ECHECS.append(msg)

def png_test():
    """une image 800 × 600 : dégradé rouge → bleu, pour reconnaître le fond après collage"""
    from PIL import Image
    im = Image.new('RGB', (800, 600))
    px = im.load()
    for y in range(600):
        for x in range(800):
            px[x, y] = (255 - x * 255 // 800, 40, x * 255 // 800)
    b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1400, 'height': 860})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(PAGE); await pg.wait_for_timeout(1200)
        shots = []
        async def shot(nom):
            f = os.path.join(OUT, f'plate_{nom}.png'); await pg.wait_for_timeout(250); await pg.screenshot(path=f); shots.append(f)
        st = await pg.evaluate("()=>{const r=document.getElementById('stage').getBoundingClientRect();return[r.left,r.top]}")
        async def ecran(id):
            """centre d'un élément en coordonnées de page"""
            x, y = await pg.evaluate("id=>{const e=__plate.parId(id);return __plate.ecran(e.x+e.w/2,e.y+e.h/2)}", id)
            return st[0] + x, st[1] + y
        n = lambda: pg.evaluate("()=>__plate.S.doc.elements.length")
        sel = lambda: pg.evaluate("()=>__plate.S.sel.slice()")

        # 1. deux mains par les outils (clic sur l'outil, clic sur la planche)
        print('1. deux mains')
        await pg.click('[data-outil=mainD]'); await pg.mouse.click(st[0] + 300, st[1] + 400)
        await pg.click('[data-outil=mainG]'); await pg.mouse.click(st[0] + 700, st[1] + 400)
        els = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>({type:e.type,cote:e.cote,w:Math.round(e.w),h:Math.round(e.h)}))")
        check(len(els) == 2 and els[0]['cote'] == 'D' and els[1]['cote'] == 'G', f'2 mains D et G : {els}')
        alpha = await pg.evaluate("()=>{const e=__plate.S.doc.elements[0];const c=__plate.mainCache(e,256,256);const d=c.getContext('2d').getImageData(0,0,256,256).data;let n=0;for(let i=3;i<d.length;i+=4)if(d[i]>8)n++;return n/(256*256)}")
        check(0.15 < alpha < 0.8, f'couverture alpha du cache de la main D = {alpha:.2f} (silhouette, pas un bloc)')
        await shot('01_deux_mains')

        # 2. dupliquer (Ctrl+D) : copie décalée de +10/+10
        print('2. dupliquer')
        idD = els and await pg.evaluate("()=>__plate.S.doc.elements[0].id")
        cx, cy = await ecran(idD); await pg.mouse.click(cx, cy)
        check((await sel()) == [idD], 'clic sur la main D la sélectionne')
        await pg.keyboard.press('Control+d')
        pos = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>[Math.round(e.x),Math.round(e.y)])")
        check(await n() == 3 and pos[2][0] == pos[0][0] + 10 and pos[2][1] == pos[0][1] + 10, f'3 éléments, copie à +10/+10 : {pos}')
        idC = await pg.evaluate("()=>__plate.S.doc.elements[2].id")

        # 3. retourner : miroir d'image (Maj+H) puis conversion en main gauche (miroir 3D, flipH remis à faux)
        print('3. retourner')
        await pg.keyboard.press('Shift+H')
        check(await pg.evaluate("id=>__plate.parId(id).flipH", idC) is True, 'Maj+H : flipH = true')
        await pg.click('#ctx button:has-text("→ main gauche")')
        e = await pg.evaluate("id=>{const e=__plate.parId(id);return{cote:e.cote,flipH:e.flipH}}", idC)
        check(e == {'cote': 'G', 'flipH': False}, f'conversion en main gauche : {e}')
        await shot('02_duplique_retourne')

        # 4. déplacer à la souris (Ctrl enfoncé : pas de guides) puis aux flèches (1 px, Maj : 10 px)
        print('4. déplacer')
        zoom = await pg.evaluate("()=>__plate.S.zoom")
        x0, y0 = await pg.evaluate("id=>{const e=__plate.parId(id);return[e.x,e.y]}", idC)
        cx, cy = await ecran(idC)
        await pg.keyboard.down('Control'); await pg.mouse.move(cx, cy); await pg.mouse.down()
        for i in range(1, 11): await pg.mouse.move(cx + 12 * i, cy + 4 * i)
        await pg.mouse.up(); await pg.keyboard.up('Control')
        x1, y1 = await pg.evaluate("id=>{const e=__plate.parId(id);return[e.x,e.y]}", idC)
        attendu = (120 / zoom, 40 / zoom)
        check(abs(x1 - x0 - attendu[0]) < 1 and abs(y1 - y0 - attendu[1]) < 1, f'glisser de 120 × 40 px écran → +{x1-x0:.1f} / +{y1-y0:.1f} px planche (attendu {attendu[0]:.1f} / {attendu[1]:.1f})')
        nu = await pg.evaluate("()=>__plate.hist.undo.length")
        await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('Shift+ArrowDown')
        x2, y2 = await pg.evaluate("id=>{const e=__plate.parId(id);return[e.x,e.y]}", idC)
        check(abs(x2 - x1 - 1) < 1e-6 and abs(y2 - y1 - 10) < 1e-6, f'flèches : +1 / +10 px ({x2-x1:.0f}, {y2-y1:.0f})')
        check(await pg.evaluate("()=>__plate.hist.undo.length") == nu + 2, 'un glisser = une entrée d\'historique, chaque flèche une autre')

        # 5. texte avec surlignage : outil T, clic, frappe, sélection de « les », bouton Surligner
        print('5. texte')
        tx, ty = await pg.evaluate("()=>__plate.ecran(500,120)")      # un point DANS la planche (500, 120)
        await pg.click('[data-outil=texte]'); await pg.mouse.click(st[0] + tx, st[1] + ty)
        check(await pg.evaluate("()=>__plate.S.mode") == 'texte', 'le texte s\'ouvre en édition')
        await pg.keyboard.press('Control+a'); await pg.keyboard.type('Bonjour les mains')
        await pg.evaluate("()=>{const ed=document.getElementById('texte');const t=ed.firstChild;const r=document.createRange();r.setStart(t,8);r.setEnd(t,11);const s=getSelection();s.removeAllRanges();s.addRange(r)}")
        await pg.click('#ctx button:has-text("Surligner")')
        await pg.keyboard.press('Escape')
        t = await pg.evaluate("()=>{const e=__plate.S.doc.elements.find(e=>e.type==='texte');return{texte:e.texte,s:e.surlignages,h:Math.round(e.h)}}")
        check(t['texte'] == 'Bonjour les mains' and t['s'] == [{'from': 8, 'to': 11, 'couleur': '#fff176'}], f'texte et segment surligné : {t}')
        # le surlignage se voit : pixel jaune (multiply sur blanc) sous « les », noir sur les lettres
        pix = await pg.evaluate("""()=>{const d=__plate.S.doc,c=document.createElement('canvas');c.width=d.planche.w;c.height=d.planche.h;const x=c.getContext('2d');__plate.drawDoc(x,d,1,{export:true});
          const e=d.elements.find(e=>e.type==='texte');const L=__plate.lignesTexte(x,e,1);const w8=x.measureText(L[0].t.slice(0,8)).width,w11=x.measureText(L[0].t.slice(0,11)).width;
          const px=Math.round(e.x+e.marge+(w8+w11)/2),py=Math.round(e.y+e.marge+e.corps*.3);const p=x.getImageData(px,py,1,1).data;const q=x.getImageData(px,Math.round(e.y+2),1,1).data;return[Array.from(p),Array.from(q)]}""")
        check(pix[0][0] > 230 and pix[0][2] < 160 and pix[1][2] > 230, f'pixel sous « les » jaune {pix[0][:3]}, pixel au-dessus de la bande blanc {pix[1][:3]}')
        await shot('03_texte_surligne')

        # 6. image collée (clipboardData.files) puis « Définir comme fond »
        print('6. image collée en fond')
        b64 = base64.b64encode(png_test()).decode()
        await pg.focus('#stage')
        await pg.evaluate("""b64=>{const bin=atob(b64),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
          const f=new File([u],'photo.png',{type:'image/png'});const dt=new DataTransfer();dt.items.add(f);document.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true}))}""", b64)
        await pg.wait_for_timeout(800)
        im = await pg.evaluate("()=>{const e=__plate.S.doc.elements.find(e=>e.type==='image');return e?{w:Math.round(e.w),h:Math.round(e.h),asset:!!__plate.S.doc.assets[e.asset]}:null}")
        check(im and im['w'] == 800 and im['h'] == 600 and im['asset'], f'image collée (≤ 60 % de la planche, asset gardé) : {im}')
        await pg.click('#ctx button:has-text("Définir comme fond")')
        f = await pg.evaluate("()=>{const F=__plate.S.doc.planche.fond;return{type:F.type,src:!!(F.src&&__plate.S.doc.assets[F.src]),images:__plate.S.doc.elements.filter(e=>e.type==='image').length}}")
        check(f == {'type': 'image', 'src': True, 'images': 0}, f'fond image, objet retiré : {f}')
        # pixel du fond à gauche rouge, à droite bleu (mode couvrir)
        pix = await pg.evaluate("""()=>{const d=__plate.S.doc,c=document.createElement('canvas');c.width=d.planche.w;c.height=d.planche.h;const x=c.getContext('2d');__plate.drawDoc(x,d,1,{export:true});
          return[Array.from(x.getImageData(5,d.planche.h-5,1,1).data),Array.from(x.getImageData(d.planche.w-5,d.planche.h-5,1,1).data)]}""")
        check(pix[0][0] > 200 and pix[1][2] > 200, f'fond couvrant : coin gauche {pix[0][:3]}, coin droit {pix[1][:3]}')
        await shot('04_fond_image')

        # 7. annuler : supprimer la main D puis Ctrl+Z
        print('7. annuler')
        cx, cy = await ecran(idD); await pg.mouse.click(cx, cy); avant = await n()
        await pg.keyboard.press('Delete'); check(await n() == avant - 1, f'Suppr : {avant} → {avant-1}')
        await pg.keyboard.press('Control+z'); check(await n() == avant, f'Ctrl+Z : {avant} éléments de nouveau')
        await pg.keyboard.press('Control+Shift+z'); check(await n() == avant - 1, 'Ctrl+Maj+Z rétablit la suppression')
        await pg.keyboard.press('Control+z')

        # 8. marionnette sur une main (bouchon : curseurs) et éclatement en étapes
        print('8. pose et étapes')
        cx, cy = await ecran(idD); await pg.mouse.dblclick(cx, cy)
        check(await pg.evaluate("()=>__plate.S.mode==='marionnette'&&!document.getElementById('puppet').hidden"), 'double-clic sur une main : marionnette ouverte')
        await pg.evaluate("()=>{const i=document.querySelector('#puppet input[data-joint=\"index.mcp\"]');i.value=60;i.dispatchEvent(new Event('input'))}")
        await pg.evaluate("()=>document.getElementById('puppet').dispatchEvent(new PointerEvent('pointerup',{bubbles:true}))")
        await pg.keyboard.press('Escape')
        mcp = await pg.evaluate("id=>__plate.parId(id).pose.index.mcp", idD)
        check(mcp == 60 and await pg.evaluate("()=>__plate.S.mode") == 'planche', f'index.mcp = {mcp} après le curseur, mode planche après Échap')
        await pg.mouse.click(cx, cy); await pg.click('[data-tab=props]'); await pg.click('#props button:has-text("Éclater en étapes")')
        types = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>e.type)")
        check(types.count('main') == 5 and types.count('fleche') == 2, f'éclaté en 3 étapes (3 mains + 2 flèches remplacent la main D) : {types}')
        await shot('05_etapes')

        # 9. gabarit A (bannière + colonne), nom de fichier = mot de la bannière
        print('9. gabarit A')
        await pg.click('#bGabarits'); await pg.click('#gabarits button:has-text("Bannière")')
        g = await pg.evaluate("()=>({types:__plate.S.doc.elements.map(e=>e.type),w:__plate.S.doc.planche.w,nom:__plate.nomFichier()})")
        check(g['types'] == ['texte', 'texte', 'personnage', 'main', 'main'] and g['w'] == 1920 and g['nom'] == 'MOT', f'gabarit A : {g}')
        await shot('06_gabarit_A')

        # 10. export ×2 : taille, projet embarqué dans le PNG, fond transparent
        print('10. export')
        r = await pg.evaluate("""async()=>{const r=await __plate.exporte({k:2});const buf=await r.blob.arrayBuffer();const o=__plate.projetDuPng(buf);
          const bm=await createImageBitmap(r.blob);return{w:r.w,h:r.h,bw:bm.width,bh:bm.height,octets:buf.byteLength,version:o&&o.version,n:o&&o.elements.length}}""")
        check(r['w'] == 3840 and r['h'] == 2160 and r['bw'] == 3840, f'export ×2 = {r["w"]} × {r["h"]} ({r["octets"]//1024} Ko)')
        check(r['version'] == 9 and r['n'] == 5, f'projet v9 embarqué dans le PNG (iTXt) : {r["n"]} éléments')
        b64png = await pg.evaluate("async()=>{const r=await __plate.exporte({k:2});const u=new Uint8Array(await r.blob.arrayBuffer());let s='';for(let i=0;i<u.length;i+=8192)s+=String.fromCharCode.apply(null,u.subarray(i,i+8192));return btoa(s)}")
        open(os.path.join(OUT, 'plate_export_2x.png'), 'wb').write(base64.b64decode(b64png))
        t = await pg.evaluate("""async()=>{const r=await __plate.exporte({k:1,transparent:true,embarque:false});const bm=await createImageBitmap(r.blob);const c=document.createElement('canvas');c.width=bm.width;c.height=bm.height;const x=c.getContext('2d');x.drawImage(bm,0,0);
          return Array.from(x.getImageData(3,bm.height-3,1,1).data)}""")
        check(t[3] == 0, f'export transparent : alpha du coin = {t[3]}')

        # 11. enregistrer / recharger en JSON
        print('11. projet JSON')
        j = await pg.evaluate("()=>JSON.stringify(__plate.serialise())")
        o = json.loads(j); check(o['version'] == 9 and len(o['elements']) == 5 and 'assets' in o, f'JSON v9 : {len(j)//1024} Ko, {len(o["elements"])} éléments')
        await pg.evaluate("()=>__plate.charge(__plate.docNeuf('carre'))")
        check(await n() == 0, 'planche vide avant rechargement')
        await pg.evaluate("j=>__plate.charge(JSON.parse(j))", j)
        o2 = await pg.evaluate("()=>__plate.serialise()")
        same = [(a['type'], round(a['x']), round(a['y']), round(a['w'])) for a in o['elements']] == [(a['type'], round(a['x']), round(a['y']), round(a['w'])) for a in o2['elements']]
        check(same and o2['planche']['w'] == 1920, 'rechargé à l\'identique (types, positions, largeur)')
        await pg.evaluate("()=>__plate.charge(__plate.docNeuf('16:9'))")

        # 12. plusieurs objets : rectangle de sélection, groupe, alignement
        print('12. sélection multiple')
        await pg.evaluate("()=>{__plate.ajoute('texte',{texte:'A',x:200,y:200,w:200});__plate.ajoute('texte',{texte:'B',x:600,y:500,w:200});__plate.selectionne([])}")
        a = await pg.evaluate("()=>__plate.ecran(150,150)"); c = await pg.evaluate("()=>__plate.ecran(900,700)")
        await pg.mouse.move(st[0] + a[0], st[1] + a[1]); await pg.mouse.down(); await pg.mouse.move(st[0] + c[0], st[1] + c[1], steps=5); await pg.mouse.up()
        check(len(await sel()) == 2, 'rectangle de sélection : 2 objets')
        await pg.keyboard.press('Control+g'); await pg.click('[data-tab=props]'); await pg.click('#props button[title=gauche]')
        xs = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>Math.round(e.x))")
        check(xs == [200, 200], f'aligner à gauche : x = {xs}')
        await pg.keyboard.press('Control+]'); check(await pg.evaluate("()=>__plate.S.doc.elements.every(e=>e.groupes.length===1)"), 'groupe posé (Ctrl+G)')
        await shot('07_selection_multiple')

        print('erreurs JS :', errs or 'aucune'); check(not errs, 'aucune erreur JS')
        await b.close()
    try:
        from PIL import Image
        ims = [Image.open(f) for f in shots]; w, h = ims[0].size
        c = Image.new('RGB', (w * 2, h * ((len(ims) + 1) // 2)), 'white')
        for i, im in enumerate(ims): c.paste(im, ((i % 2) * w, (i // 2) * h))
        c.thumbnail((2200, 2600)); c.save(os.path.join(OUT, 'plate_scenario.png'))
    except ImportError:
        pass
    print('ÉCHECS :', ECHECS or 'aucun')
    sys.exit(1 if ECHECS else 0)

asyncio.run(main())
