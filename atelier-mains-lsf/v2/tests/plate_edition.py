"""Gestes d'édition, images et fonds de l'éditeur de planche (v2/plate), sous Playwright + Chromium headless.

  python3 v2/tests/plate_edition.py      → v2/tests/out/plate_edition_*.png + plate_gabarits.png

Complète plate_scenario.py (le parcours de l'utilisateur) et plate_projet.py (le fichier) : poignées (coin
proportionnel, bord, rotation Maj = 15°), guides à 5 px, Ctrl+C / Ctrl+V au clavier, coller la pose, ordre des
calques, verrou, pile d'annulation plafonnée à 100, images (EXIF, réduction à 4 096 px, HEIC, glisser-déposer),
fond (dégradé, mosaïque, voile, flou, détacher), texte (gras, taille, bannière, alignement vertical), export WebP,
nom de fichier. Chaque étape vérifie un chiffre ; aucune erreur JS tolérée.
"""
import asyncio, base64, io, json, os, sys
from playwright.async_api import async_playwright
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = 'file://' + os.path.join(ROOT, 'plate', 'index.html')
OUT = os.path.join(ROOT, 'tests', 'out'); os.makedirs(OUT, exist_ok=True)
ECHECS = []
def check(cond, msg):
    print(('  ok   ' if cond else '  ÉCHEC ') + msg)
    if not cond: ECHECS.append(msg)

def b64(im, fmt='PNG', **kw):
    b = io.BytesIO(); im.save(b, fmt, **kw); return base64.b64encode(b.getvalue()).decode()

# JS : fabrique un File à partir de base64 (nom, type)
FICHIER = "({b,nom,type})=>{const bin=atob(b),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return new File([u],nom,{type})}"
# JS : rend la planche à l'échelle 1 et lit un pixel
PIXEL = """([x,y])=>{const d=__plate.S.doc,c=document.createElement('canvas');c.width=d.planche.w;c.height=d.planche.h;const g=c.getContext('2d');
  __plate.drawDoc(g,d,1,{export:true});return Array.from(g.getImageData(x,y,1,1).data)}"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1400, 'height': 860})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(PAGE); await pg.wait_for_timeout(1200)
        st = await pg.evaluate("()=>{const r=document.getElementById('stage').getBoundingClientRect();return[r.left,r.top]}")
        E = lambda js, *a: pg.evaluate(js, *a)
        async def ecr(px, py):
            x, y = await E("([x,y])=>__plate.ecran(x,y)", [px, py]); return st[0] + x, st[1] + y
        async def poignee(i):
            """position page de la poignée i (0 hg … 7 mg, 8 rotation) du cadre de sélection"""
            x, y = await E("i=>{const S=__plate.S,e=__plate.parId(S.sel[0]);const c={cx:e.x+e.w/2,cy:e.y+e.h/2,w:e.w,h:e.h,rot:e.rot};"
                           "const z=S.zoom,cs=Math.cos(c.rot*Math.PI/180),sn=Math.sin(c.rot*Math.PI/180),[sx,sy]=__plate.ecran(c.cx,c.cy);"
                           "if(i===8){const d=-c.h*z/2-24;return[sx-d*sn,sy+d*cs]}const a=[[0,0],[.5,0],[1,0],[1,.5],[1,1],[.5,1],[0,1],[0,.5]][i];"
                           "const dx=(a[0]-.5)*c.w*z,dy=(a[1]-.5)*c.h*z;return[sx+dx*cs-dy*sn,sy+dx*sn+dy*cs]}", i)
            return st[0] + x, st[1] + y
        async def glisse(x0, y0, x1, y1, n=8, mods=()):
            for m in mods: await pg.keyboard.down(m)
            await pg.mouse.move(x0, y0); await pg.mouse.down()
            for i in range(1, n + 1): await pg.mouse.move(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n)
            await pg.mouse.up()
            for m in mods: await pg.keyboard.up(m)
        el = lambda id: E("id=>{const e=__plate.parId(id);return e&&JSON.parse(JSON.stringify(e))}", id)

        print('1. poignées')
        idM = await E("()=>__plate.ajoute('main',{cote:'D'}).id")
        e0 = await el(idM); r0 = e0['w'] / e0['h']
        x, y = await poignee(4); await glisse(x, y, x + 60, y + 10)
        e1 = await el(idM)
        check(abs(e1['w'] / e1['h'] - r0) < 0.005 * r0 and e1['w'] > e0['w'] * 1.1 and abs(e1['x'] - e0['x']) < 0.5 and abs(e1['y'] - e0['y']) < 0.5,
              f'coin bas-droit d\'une main : {e0["w"]:.0f}×{e0["h"]:.0f} → {e1["w"]:.0f}×{e1["h"]:.0f}, proportions {r0:.3f} → {e1["w"]/e1["h"]:.3f}, coin opposé fixe')
        n_poignees = await E("()=>{__plate.peint();return 1}")
        x, y = await poignee(8); cx, cy = await ecr(e1['x'] + e1['w'] / 2, e1['y'] + e1['h'] / 2)
        await pg.mouse.move(x, y); await pg.mouse.down()
        await pg.keyboard.down('Shift')
        for i in range(1, 9): await pg.mouse.move(x + 9 * i, y + 2 * i)
        await pg.screenshot(path=os.path.join(OUT, 'plate_edition_01_rotation.png'))
        await pg.mouse.up(); await pg.keyboard.up('Shift')
        rot = (await el(idM))['rot']
        check(rot != 0 and abs(rot / 15 - round(rot / 15)) < 1e-9, f'rotation à la poignée avec Maj : {rot}° (multiple de 15°)')
        await pg.keyboard.press('Control+z')
        check((await el(idM))['rot'] == 0, 'Ctrl+Z annule la rotation d\'un coup (un glisser = une entrée)')
        idT = await E("()=>__plate.ajoute('texte',{texte:'Une phrase de définition assez longue pour passer à la ligne',x:200,y:700,w:500,corps:40}).id")
        t0 = await el(idT)
        x, y = await poignee(3); z = await E("()=>__plate.S.zoom"); await glisse(x, y, x - 200 * z, y)
        t1 = await el(idT)
        check(abs(t1['w'] - (t0['w'] - 200)) < 1 and t1['corps'] == t0['corps'] and t1['h'] > t0['h'],
              f'bord droit d\'un texte : largeur {t0["w"]:.0f} → {t1["w"]:.0f} (−200), corps gardé {t1["corps"]}, hauteur {t0["h"]:.0f} → {t1["h"]:.0f} (une ligne de plus)')

        print('2. guides à 5 px et ordre')
        idA = await E("()=>__plate.ajoute('texte',{texte:'A',x:300,y:120,w:240}).id")
        idB = await E("()=>__plate.ajoute('texte',{texte:'B',x:900,y:420,w:240}).id")
        bB = await el(idB); z = await E("()=>__plate.S.zoom")
        x, y = await ecr(bB['x'] + 30, bB['y'] + 20)
        # amener le bord gauche de B à 4 px planche (≈ 2 px écran) du bord gauche de A, sans Ctrl : les guides l'accrochent
        await pg.mouse.move(x, y); await pg.mouse.down()
        for i in range(1, 9): await pg.mouse.move(x + (304 - 900) * z * i / 8, y)
        g = await E("()=>__plate.S.guides.slice()")
        await pg.screenshot(path=os.path.join(OUT, 'plate_edition_02_guide.png'))
        await pg.mouse.up()
        bx = (await el(idB))['x']
        check(abs(bx - 300) < 1e-6 and any(abs(v.get('v', -1) - 300) < 1e-6 for v in g), f'accroche : x de B = {bx:.2f} (bord de A = 300), guide vertical {g}')
        ordre = lambda: E("()=>__plate.S.doc.elements.map(e=>e.id)")
        await E("id=>__plate.selectionne([id])", idA); await pg.focus('#stage')
        await pg.keyboard.press('Control+]'); o = await ordre()
        check(o.index(idA) == o.index(idB) + 1, f'Ctrl+] : A avance d\'un cran, juste devant B (rang {o.index(idA)} / {len(o)})')
        await pg.keyboard.press('Control+Alt+['); o = await ordre()
        check(o[0] == idA, 'Ctrl+Alt+[ : A tout derrière')
        await pg.keyboard.press('Control+Alt+]'); o = await ordre()
        check(o[-1] == idA, 'Ctrl+Alt+] : A tout devant')
        rows = await E("()=>document.querySelectorAll('#calques .calque').length")
        check(rows == len(o), f'panneau des calques : {rows} lignes pour {len(o)} éléments')

        print('3. verrou')
        await pg.keyboard.press('Alt+Shift+L')
        check((await el(idA))['verrou'] is True, 'Alt+Maj+L verrouille')
        await E("()=>__plate.selectionne([])")
        a = await el(idA); x, y = await ecr(a['x'] + 10, a['y'] + 10); await pg.mouse.click(x, y)
        check(idA not in await E("()=>__plate.S.sel"), 'objet verrouillé : un clic ne le sélectionne pas')
        await E("id=>__plate.selectionne([id])", idA); await pg.focus('#stage'); await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('Delete')
        a2 = await el(idA)
        check(a2 is not None and a2['x'] == a['x'], 'verrouillé : ni les flèches ni Suppr ne le touchent')
        await pg.keyboard.press('Alt+Shift+L')

        print('4. copier / coller au clavier, coller la pose')
        await E("id=>__plate.selectionne([id])", idM); await pg.focus('#stage')
        n0 = await E("()=>__plate.S.doc.elements.length")
        await pg.keyboard.press('Control+c')
        mx, my = await ecr(1500, 300); await pg.mouse.move(mx, my)
        await pg.keyboard.press('Control+v'); await pg.wait_for_timeout(100)
        els = await E("()=>__plate.S.doc.elements.map(e=>({id:e.id,type:e.type,cx:e.x+e.w/2,cy:e.y+e.h/2}))")
        c = els[-1]
        check(len(els) == n0 + 1 and c['type'] == 'main' and abs(c['cx'] - 1500) < 2 and abs(c['cy'] - 300) < 2,
              f'Ctrl+C puis Ctrl+V sous la souris : {n0} → {len(els)} éléments, copie centrée en ({c["cx"]:.0f}, {c["cy"]:.0f}) pour (1500, 300)')
        idM2 = c['id']
        await E("id=>{__plate.act(()=>{__plate.parId(id).pose.index.mcp=70;__plate.parId(id).pose.pouce.av=30});__plate.selectionne([id]);__plate.copiePose()}", idM)
        await E("id=>__plate.selectionne([id])", idM2); await pg.focus('#stage'); await pg.keyboard.press('Control+Shift+v')
        m2 = await el(idM2)
        check(m2['pose']['index']['mcp'] == 70 and m2['pose']['pouce']['av'] == 30 and abs(m2['x'] + m2['w'] / 2 - 1500) < 40, f'Ctrl+Maj+V colle la pose (index.mcp {m2["pose"]["index"]["mcp"]}) et garde la place')

        print('5. pile d\'annulation : 100 instantanés')
        await E("id=>__plate.selectionne([id])", idM2); await pg.focus('#stage')
        for i in range(120): await pg.keyboard.press('ArrowDown')
        nu = await E("()=>__plate.hist.undo.length")
        check(nu == 100, f'120 déplacements → {nu} entrées gardées')
        for i in range(100): await pg.keyboard.press('Control+z')
        nr = await E("()=>[__plate.hist.undo.length,__plate.hist.redo.length]")
        check(nr == [0, 100], f'100 × Ctrl+Z : pile vide, 100 à rétablir ({nr})')
        await E("()=>__plate.charge(__plate.docNeuf('16:9'))")

        print('6. images : EXIF, réduction, HEIC, glisser-déposer')
        # JPEG 300 × 100 stocké couché avec l'étiquette EXIF « tourner de 90° » (6) : le navigateur doit l'afficher 100 × 300
        im = Image.new('RGB', (300, 100), (200, 30, 30)); im.paste((30, 30, 200), (0, 0, 60, 100))
        ex = Image.Exif(); ex[0x0112] = 6
        f_exif = b64(im, 'JPEG', exif=ex.tobytes(), quality=95)
        big = b64(Image.new('RGB', (5000, 1000), (40, 160, 90)))
        await E("async ([F,a,b])=>{const mk=eval(F);await __plate.importeImages([mk({b:a,nom:'exif.jpg',type:'image/jpeg'}),mk({b:b,nom:'grande.png',type:'image/png'})])}", [FICHIER, f_exif, big])
        await pg.wait_for_timeout(300)
        ims = await E("()=>__plate.S.doc.elements.filter(e=>e.type==='image').map(e=>{const i=__plate.IMG.get(e.asset);return[i.naturalWidth,i.naturalHeight,e.nom]})")
        check(ims[0][:2] == [100, 300], f'orientation EXIF appliquée : 300 × 100 couché → {ims[0][0]} × {ims[0][1]}')
        check(ims[1][:2] == [4096, 819], f'photo 5 000 × 1 000 réduite à l\'import : {ims[1][0]} × {ims[1][1]} (côté long 4 096)')
        await E("([F])=>{const mk=eval(F);return __plate.importeImages([mk({b:'AAAA',nom:'IMG_2401.HEIC',type:''})])}", [FICHIER])
        msg = await E("()=>document.getElementById('topMsg').textContent")
        check('HEIC' in msg and 'JPEG' in msg, f'HEIC : « {msg[:70]}… »')
        n0 = await E("()=>__plate.S.doc.elements.length")
        st2 = await E("()=>{const r=document.getElementById('stage').getBoundingClientRect();return[r.left,r.top]}")
        check(st2 == st, f'le message long ne décale pas le plateau : coin {st} → {st2}')
        dx, dy = await ecr(400, 800)
        await E("""async ([F,b,x,y])=>{const f=eval(F)({b,nom:'deposee.png',type:'image/png'});const dt=new DataTransfer();dt.items.add(f);
          const st=document.getElementById('stage');st.dispatchEvent(new DragEvent('dragenter',{dataTransfer:dt,bubbles:true}));
          st.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,clientX:x,clientY:y}))}""", [FICHIER, b64(Image.new('RGB', (200, 100), (250, 200, 0))), dx, dy])
        await pg.wait_for_timeout(400)
        d = await E("()=>{const e=__plate.S.doc.elements[__plate.S.doc.elements.length-1];return[e.type,e.x+e.w/2,e.y+e.h/2,document.getElementById('drop').hidden]}")
        check(await E("()=>__plate.S.doc.elements.length") == n0 + 1 and d[0] == 'image' and abs(d[1] - 400) < 3 and abs(d[2] - 800) < 3 and d[3],   # clientX/Y d'un DragEvent sont entiers : ±1 px écran = ±2 px planche
              f'glisser-déposer : image centrée sous le pointeur ({d[1]:.0f}, {d[2]:.0f}) pour (400, 800), zone de dépôt refermée')

        print('7. fond : dégradé, mosaïque, voile, flou, détacher')
        await E("()=>{__plate.charge(__plate.docNeuf('16:9'));const F=__plate.S.doc.planche.fond;F.type='degrade';F.col='#ff0000';F.col2='#0000ff';F.angle=180}")
        h, w = 1080, 1920
        top, bot = await E(PIXEL, [960, 2]), await E(PIXEL, [960, h - 3])
        check(top[0] > 240 and top[2] < 15 and bot[2] > 240 and bot[0] < 15, f'dégradé 180° : haut {top[:3]}, bas {bot[:3]}')
        damier = Image.new('RGB', (200, 200), (255, 255, 255))
        for yy in range(0, 200, 100):
            for xx in range(0, 200, 100):
                if (xx + yy) // 100 % 2 == 0: damier.paste((0, 0, 0), (xx, yy, xx + 100, yy + 100))
        await E("async ([F,b])=>{await __plate.importeImages([eval(F)({b,nom:'damier.png',type:'image/png'})]);__plate.definirFond();}", [FICHIER, b64(damier)])
        await pg.wait_for_timeout(300)
        await E("()=>{const F=__plate.S.doc.planche.fond;F.mode='mosaique';F.echelle=1}")
        p1, p2, p3 = await E(PIXEL, [50, 50]), await E(PIXEL, [250, 50]), await E(PIXEL, [150, 50])
        check(p1[:3] == p2[:3] and abs(p1[0] - p3[0]) > 200, f'mosaïque (tuile 200 px) : (50,50) {p1[:3]} = (250,50) {p2[:3]}, (150,50) {p3[:3]} opposé')
        await E("()=>{const F=__plate.S.doc.planche.fond;F.mode='etirer';F.col='#ff0000'}")
        bord = [await E(PIXEL, [1500, 0]), await E(PIXEL, [1500, 1079])]
        await E("()=>{const F=__plate.S.doc.planche.fond;F.mode='couvrir'}")
        bord += [await E(PIXEL, [1500, 0]), await E(PIXEL, [5, 0])]
        check(all(q[1] > 250 or q[1] < 5 for q in bord) and bord[0][1] > 250, f'pas de filet de la couleur de dessous au bord (fond rouge, image noir/blanc) : {[q[:3] for q in bord]}')
        await E("()=>{const F=__plate.S.doc.planche.fond;F.mode='etirer';F.voile={col:'#000000',a:.5}}")
        v = await E(PIXEL, [1500, 100])   # case blanche (tuile étirée : x > 960 et y < 540)
        check(120 <= v[0] <= 135, f'voile noir 50 % sur le blanc : {v[:3]} (≈ 128)')
        await E("()=>{const F=__plate.S.doc.planche.fond;F.voile.a=0;F.flou=0}")
        nette = await E(PIXEL, [955, 270])
        await E("()=>{__plate.S.doc.planche.fond.flou=20}")
        floue = await E(PIXEL, [955, 270])
        check(nette[0] < 10 and 40 < floue[0] < 215, f'flou 20 px au bord noir/blanc : {nette[0]} net → {floue[0]} flou')
        await E("()=>{__plate.S.doc.planche.fond.flou=0;__plate.S.doc.planche.fond.mode='couvrir';__plate.invalide()}")
        await pg.click('[data-tab=planche]'); await pg.wait_for_timeout(150)
        await E("()=>{__plate.S.doc.planche.fond.col='#ff0000';__plate.invalide()}"); await pg.wait_for_timeout(150)
        await pg.screenshot(path=os.path.join(OUT, 'plate_edition_03_fond.png'))
        # à l'écran : la rangée du bord haut de la planche ne montre pas la couleur de dessous (rouge) sous une image qui couvre
        hx, hy = await ecr(1500, 0)
        im3 = Image.open(os.path.join(OUT, 'plate_edition_03_fond.png')).convert('RGB')
        rangs = [im3.getpixel((int(hx), int(hy) + k)) for k in range(0, 3)]
        check(all(not (q[0] > q[1] + 40) for q in rangs), f'bord haut à l\'écran sans filet rouge : {rangs}')
        await pg.click('#planchePane button:has-text("Détacher en image")')
        f = await E("()=>[__plate.S.doc.planche.fond.type,__plate.S.doc.elements.map(e=>e.type+':'+Math.round(e.w)+'x'+Math.round(e.h))]")
        check(f[0] == 'uni' and f[1] == ['image:1920x1920'], f'« Détacher en image » : fond {f[0]}, objet {f[1]} (couvre la planche)')

        print('8. texte : barre contextuelle, bannière, alignement vertical')
        await E("()=>__plate.charge(__plate.docNeuf('16:9'))")
        idT = await E("()=>__plate.ajoute('texte',{texte:'cent',x:100,y:100,w:800,h:300,fond:'#cceeec',corps:60}).id")
        await E("id=>__plate.editeTexte(id)", idT); await pg.wait_for_timeout(100)
        await pg.click('#ctx button[title=Gras]'); await pg.click('#ctx button:has-text("A+")'); await pg.click('#ctx button:has-text("A+")')
        await pg.screenshot(path=os.path.join(OUT, 'plate_edition_04_texte.png'))
        await pg.click('#ctx button:has-text("Terminer")')
        t = await el(idT)
        check(t['gras'] is True and t['corps'] == 68 and t['h'] == 300, f'gras {t["gras"]}, A+ ×2 : corps 60 → {t["corps"]}, bannière gardée à {t["h"]} px de haut')
        ys = await E("""id=>{const d=__plate.S.doc,e=__plate.parId(id),c=document.createElement('canvas');c.width=d.planche.w;c.height=d.planche.h;const g=c.getContext('2d');
          const r={};for(const va of ['haut','milieu','bas']){e.valign=va;g.clearRect(0,0,c.width,c.height);__plate.drawDoc(g,d,1,{export:true,transparent:true});
          const px=g.getImageData(e.x,e.y,e.w,e.h).data;let y0=-1;for(let y=0;y<e.h&&y0<0;y++)for(let x=0;x<e.w;x++){const i=(y*e.w+x)*4;if(px[i]<100&&px[i+3]>200){y0=y;break}}r[va]=y0}return r}""", idT)
        check(ys['haut'] < ys['milieu'] < ys['bas'] and abs(ys['milieu'] - (300 - 68 * 0.75) / 2) < 25,
              f'alignement vertical dans la bannière : 1re encre à y = {ys["haut"]} / {ys["milieu"]} / {ys["bas"]} (haut / milieu / bas)')
        await E("([id])=>{const e=__plate.parId(id);e.texte='Cent / 100 ?';__plate.invalide()}", [idT])
        check(await E("()=>__plate.nomFichier()") == 'Cent-100', f'nom de fichier tiré de la bannière : « {await E("()=>__plate.nomFichier()")} »')

        print('9. export WebP, gabarits C, D, E')
        r = await E("async()=>{const a=await __plate.exporte({k:1,embarque:false}),b=await __plate.exporte({k:1,webp:true});return[a.blob.type,a.blob.size,b.blob.type,b.blob.size]}")
        check(r[0] == 'image/png' and r[2] == 'image/webp' and r[3] < r[1], f'WebP {r[3]//1024} Ko contre PNG {r[1]//1024} Ko')
        planches = []
        for k in 'ABCDE':
            r = await E("""async k=>{__plate.gabarit(k);__plate.S.doc.elements.filter(e=>e.type==='texte'&&/^(MOT|SIGNE)$/.test(e.texte)).forEach(e=>{e.texte=e.texte==='MOT'?'cent':'[signe]'});
              const r=await __plate.exporte({k:1,embarque:false});const u=new Uint8Array(await r.blob.arrayBuffer());let s='';for(let i=0;i<u.length;i+=8192)s+=String.fromCharCode.apply(null,u.subarray(i,i+8192));
              return{b:btoa(s),w:r.w,h:r.h,types:__plate.S.doc.elements.map(e=>e.type)}}""", k)
            f = os.path.join(OUT, f'plate_gabarit_{k}.png'); open(f, 'wb').write(base64.b64decode(r['b'])); planches.append((k, f))
            print(f'     gabarit {k} : {r["w"]} × {r["h"]}, {len(r["types"])} objets ({", ".join(sorted(set(r["types"])))})')
        check(len(planches) == 5, 'cinq gabarits exportés')
        # planche de contrôle : les cinq gabarits côte à côte, à 300 px de haut
        ims = [Image.open(f).convert('RGB') for _, f in planches]
        ims = [im.resize((int(im.width * 300 / im.height), 300)) for im in ims]
        W = sum(im.width for im in ims) + 10 * (len(ims) + 1)
        c = Image.new('RGB', (W, 320), (200, 205, 204)); x = 10
        for im in ims: c.paste(im, (x, 10)); x += im.width + 10
        c.save(os.path.join(OUT, 'plate_gabarits.png'))

        print('10. référent')
        await E("()=>{__plate.charge(__plate.docNeuf('16:9'));__plate.ajoute('personnage')}")
        enc = await E("""()=>{const d=__plate.S.doc,e=d.elements[0],c=document.createElement('canvas');c.width=d.planche.w;c.height=d.planche.h;const g=c.getContext('2d');__plate.drawDoc(g,d,1,{export:true,transparent:true});
          const px=g.getImageData(e.x,e.y,e.w,e.h).data;let n=0;for(let i=3;i<px.length;i+=4)if(px[i]>8)n++;return[n/(e.w*e.h),!!window.AtelierPersonnage]}""")
        check(0.2 < enc[0] < 0.9, f'référent dessiné ({"personnage M4" if enc[1] else "bouchon"}) : {enc[0]*100:.0f} % de sa boîte couverte')

        print('erreurs JS :', errs or 'aucune'); check(not errs, 'aucune erreur JS')
        await b.close()
    print('ÉCHECS :', ECHECS or 'aucun')
    sys.exit(1 if ECHECS else 0)

asyncio.run(main())
