"""Correctifs de la relecture adverse du chantier M3 (éditeur de planche, 19 octobre 2026) : chaque défaut relevé est
rejoué ici avec la mesure qui le montrait, et doit être corrigé.

  python3 run_rendu.py v2/tests/plate_correctifs.py   → v2/tests/out/plate_correctifs_*.png

 1. la main affichée = la main exportée (rapport largeur/hauteur à dpr 1, dpr 2, zoom 150 % ; écart < 2 %)
 2. latéralité : main D en vue paume = pouce à DROITE de l'image (dessin paume.jpg, « face élève »)
 3. brouillons : un par planche, « Nouveau » et le démarrage n'écrasent plus celui d'avant ; Nouveau s'annule
 4. collage d'un JSON « atelier » forgé : validé champ par champ, aucune erreur JS
 5. « Éclater en étapes » reste dans la planche
 6. un gabarit sur une planche pleine demande confirmation, et Ctrl+Z la ramène
 7. flèches courbes : la boîte suit le tracé ; extrémités A / B tirables
 8. téléphone (390 × 844) : la page défile jusqu'à l'onglet Projet
 9. cache des mains : pas de rendu au survol, un rendu par image pendant un geste, mémoire ≤ 150 Mo
10–16. mineurs : fond après dialogue annulé, PNG déposé = projet, A4/A3 à ×1, ids en double et thème, surlignages
       décalés, finitions des gabarits (titre, invites, cadre photo), boîte du personnage M4
"""
import asyncio, base64, io, json, os, sys
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont
def police(t=16):
    try: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', t)   # accents des légendes
    except Exception: return ImageFont.load_default()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = 'file://' + os.path.join(ROOT, 'plate', 'index.html')
OUT = os.path.join(ROOT, 'tests', 'out'); os.makedirs(OUT, exist_ok=True)
ECHECS = []; MESURES = []
def check(cond, msg):
    print(('  ok   ' if cond else '  ÉCHEC ') + msg)
    if not cond: ECHECS.append(msg)
    MESURES.append(msg)

def b64(im, fmt='PNG'):
    b = io.BytesIO(); im.save(b, fmt); return base64.b64encode(b.getvalue()).decode()
def depuis_url(u):
    return Image.open(io.BytesIO(base64.b64decode(u.split(',', 1)[1]))).convert('RGBA')
FICHIER = "({b,nom,type})=>{const bin=atob(b),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return new File([u],nom,{type})}"
COLLE = "t=>{const dt=new DataTransfer();dt.setData('text/plain',t);document.getElementById('stage').focus();document.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true}))}"
# boîte des pixels du contour (trait #111, opaques) d'un canvas, dans un rectangle
BOITE_TRAIT = """(c,r)=>{const x=c.getContext('2d'),R=r||[0,0,c.width,c.height],d=x.getImageData(R[0],R[1],R[2],R[3]).data;let x0=1e9,y0=1e9,x1=-1,y1=-1;
  for(let j=0;j<R[3];j++)for(let i=0;i<R[2];i++){const k=(j*R[2]+i)*4;if(d[k+3]>200&&d[k]<40&&d[k+1]<40&&d[k+2]<40){if(i<x0)x0=i;if(i>x1)x1=i;if(j<y0)y0=j;if(j>y1)y1=j}}
  return[x0+R[0],y0+R[1],x1-x0+1,y1-y0+1]}"""

async def nouvelle_page(b, dpr=1, vw=1400, vh=860, dialogue=None):
    ctx = await b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=dpr)
    pg = await ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    msgs = []
    async def rep(d):
        msgs.append(d.message)
        if dialogue and dialogue[0]: await d.accept()
        else: await d.dismiss()
    pg.on('dialog', lambda d: asyncio.ensure_future(rep(d)))
    await pg.goto(PAGE); await pg.wait_for_timeout(900)
    return ctx, pg, errs, msgs

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        tous_errs = []

        # ---------------------------------------------------------------- 1
        print('1. la main affichée = la main exportée')
        crops = []
        for dpr, zoom in ((1, None), (2, None), (1, 1.5)):
            ctx, pg, errs, _ = await nouvelle_page(b, dpr)
            r = await pg.evaluate("""async([BT,zoom])=>{const P=__plate,bt=eval(BT);const e=P.ajoute('main');P.selectionne([]);
                if(zoom){const[sx,sy]=P.ecran(e.x+e.w/2,e.y+e.h/2);P.zoomVers(zoom,sx,sy)}P.invalide();P.peint();
                const cv=document.getElementById('planche'),r=devicePixelRatio,[sx,sy]=P.ecran(e.x,e.y);
                const R=[Math.max(0,Math.floor(sx*r)-4),Math.max(0,Math.floor(sy*r)-4),Math.ceil(e.w*P.S.zoom*r)+8,Math.ceil(e.h*P.S.zoom*r)+8];
                const ec=bt(cv,R);const ex=await P.exporte({k:1,embarque:false});const bm=await createImageBitmap(ex.blob);
                const c2=document.createElement('canvas');c2.width=bm.width;c2.height=bm.height;c2.getContext('2d').drawImage(bm,0,0);const xp=bt(c2,[Math.floor(e.x)-4,Math.floor(e.y)-4,Math.ceil(e.w)+8,Math.ceil(e.h)+8]);
                const crop=(c,b)=>{const t=document.createElement('canvas');t.width=b[2]+8;t.height=b[3]+8;const g=t.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,t.width,t.height);g.drawImage(c,b[0]-4,b[1]-4,t.width,t.height,0,0,t.width,t.height);return t.toDataURL()};
                return{ecran:ec,export:xp,obj:[e.w,e.h],rendus:P.S.rendus,u1:crop(cv,ec),u2:crop(c2,xp)}}""", [BOITE_TRAIT, zoom])
            re_, rx = r['ecran'][2] / r['ecran'][3], r['export'][2] / r['export'][3]
            ecart = abs(re_ / rx - 1)
            check(ecart < 0.02, f'dpr {dpr}{", zoom 150 %" if zoom else ""} : silhouette écran {r["ecran"][2]}×{r["ecran"][3]} (rapport {re_:.3f}) / export ×1 {r["export"][2]}×{r["export"][3]} ({rx:.3f}) : écart {ecart*100:.1f} % (avant : 0,616 / 0,652 contre 0,685)')
            crops.append((f'écran dpr {dpr}' + (' zoom 150 %' if zoom else ''), depuis_url(r['u1'])));
            if dpr == 1 and not zoom: crops.append(('export ×1', depuis_url(r['u2'])))
            tous_errs += errs; await ctx.close()
        H = 420; ims = [(t, im.resize((max(1, round(im.width * H / im.height)), H))) for t, im in crops]
        pl = Image.new('RGB', (sum(im.width for _, im in ims) + 20 * (len(ims) + 1), H + 50), 'white'); d = ImageDraw.Draw(pl); x = 20
        for t, im in ims: pl.paste(im, (x, 40), im); d.text((x, 10), t, fill='black', font=police()); x += im.width + 20
        pl.save(os.path.join(OUT, 'plate_correctifs_01_aspect.png'))

        # ---------------------------------------------------------------- 2
        print('2. latéralité')
        ctx, pg, errs, msgs = await nouvelle_page(b, 1, dialogue=[True])
        r = await pg.evaluate("""()=>{const P=__plate,out={};['D','G'].forEach(c=>{const e=P.ajoute('main',{cote:c});const cv=P.mainCache(e,300,440,true),x=cv.getContext('2d'),d=x.getImageData(0,0,300,440).data;
            const op=(i,j)=>d[(j*300+i)*4+3]>8;let tip=-1;for(let j=0;j<440&&tip<0;j++)for(let i=0;i<300;i++)if(op(i,j)){tip=i;break}
            // poignet : milieu des pixels opaques de la dernière rangée ; pouce : le côté qui s'étend le plus loin à mi-hauteur
            let jb=439;while(jb>0&&!Array.from({length:300},(_,i)=>op(i,jb)).some(Boolean))jb--;
            let a=1e9,z=-1;for(let i=0;i<300;i++)if(op(i,jb)){a=Math.min(a,i);z=Math.max(z,i)}const pw=(a+z)/2;let g=0,dr=0;
            for(let j=Math.round(440*.35);j<Math.round(440*.7);j++)for(let i=0;i<300;i++)if(op(i,j)){g=Math.max(g,pw-i);dr=Math.max(dr,i-pw)}
            out[c]={tip,poignet:Math.round(pw),gauche:Math.round(g),droite:Math.round(dr),url:cv.toDataURL()}});return out}""")
        D, G = r['D'], r['G']
        check(D['droite'] > D['gauche'] + 10 and G['gauche'] > G['droite'] + 10,
              f'vue paume : main D, pouce à DROITE (s\'étend à {D["droite"]} px à droite du poignet contre {D["gauche"]} à gauche) ; main G, pouce à gauche ({G["gauche"]} contre {G["droite"]})')
        check(D['tip'] < 150 < G['tip'], f'bout du majeur : D x = {D["tip"]} (à gauche du milieu : les doigts longs sont côté auriculaire… et le pouce à droite), G x = {G["tip"]}')
        await pg.evaluate("()=>{__plate.charge(__plate.docNeuf('16:9'));__plate.gabarit('A');__plate.invalide()}"); await pg.wait_for_timeout(300)
        g = await pg.evaluate("()=>{const P=__plate,L=P.S.doc.elements.filter(e=>e.type==='main');return L.map(e=>({cote:e.cote,cx:Math.round(e.x+e.w/2)}))}")
        check(g[0]['cote'] == 'D' and g[0]['cx'] < g[1]['cx'], f'gabarit A : la main D du référent est à gauche de l\'image (x {g[0]["cx"]} < {g[1]["cx"]}), pouces vers le milieu')
        st = await pg.evaluate("()=>{const r=document.getElementById('stage').getBoundingClientRect();return[r.left,r.top,r.width,r.height]}")
        await pg.screenshot(path=os.path.join(OUT, 'plate_correctifs_02b_gabaritA.png'), clip={'x': st[0], 'y': st[1], 'width': st[2], 'height': st[3]})
        ref = Image.open(os.path.join(os.path.dirname(ROOT), 'references', 'paume.jpg')).convert('RGB') if os.path.exists(os.path.join(os.path.dirname(ROOT), 'references', 'paume.jpg')) else None
        ims = [('main D (vue paume)', depuis_url(D['url'])), ('main G', depuis_url(G['url']))]
        if ref: ims.insert(0, ('dessin paume.jpg (main droite)', ref.resize((round(ref.width * 440 / ref.height), 440)).convert('RGBA')))
        pl = Image.new('RGB', (sum(im.width for _, im in ims) + 20 * (len(ims) + 1), 500), 'white'); d = ImageDraw.Draw(pl); x = 20
        for t, im in ims: pl.paste(im, (x, 40), im); d.text((x, 10), t, fill='black', font=police()); x += im.width + 20
        pl.save(os.path.join(OUT, 'plate_correctifs_02_lateralite.png'))
        tous_errs += errs; await ctx.close()

        # ---------------------------------------------------------------- 3
        print('3. brouillons')
        ctx, pg, errs, msgs = await nouvelle_page(b, 1)
        await pg.evaluate("""async()=>{const db=await new Promise(r=>{const q=indexedDB.open('atelier-v2',1);q.onupgradeneeded=()=>q.result.createObjectStore('projets',{keyPath:'id'});q.onsuccess=()=>r(q.result)});
            const t=db.transaction('projets','readwrite');t.objectStore('projets').clear();await new Promise(r=>t.oncomplete=r)}""")
        await pg.evaluate("async()=>{const P=__plate;P.ajoute('texte',{texte:'mon travail',x:100,y:100,w:500});P.ajoute('main');await P.brouillonSauve();P.nouveau();P.ajoute('main')}")
        await pg.wait_for_timeout(5600)
        L = await pg.evaluate("async()=>(await __plate.brouillonsListe()).map(b=>b.n)")
        check(sorted(L) == [1, 2], f'« Nouveau », une main, 5,6 s : deux brouillons, {L} objets (avant : celui de 2 objets remplacé par [\'main\'])')
        n = await pg.evaluate("()=>{__plate.hist.undoer();__plate.hist.undoer();return __plate.S.doc.elements.map(e=>e.type)}")
        check(n == ['texte', 'main'], f'deux Ctrl+Z (la main posée, puis « Nouveau ») ramènent la planche : {n}')
        await pg.reload(); await pg.wait_for_timeout(900)
        vis = await pg.evaluate("()=>!document.getElementById('bBrouillon').hidden")
        await pg.evaluate("()=>{__plate.ajoute('main')}"); await pg.wait_for_timeout(5600)
        L2 = await pg.evaluate("async()=>(await __plate.brouillonsListe()).map(b=>b.n)")
        check(vis and 2 in L2 and len(L2) == 3, f'démarrage, une action avant « Reprendre », 5,6 s : le brouillon de 2 objets est toujours là ({L2}), bouton « Reprendre » visible : {vis}')
        await pg.evaluate("async()=>{const P=__plate;P.nouveau();P.ajoute('texte',{texte:'quatrième'});await P.brouillonSauve()}")
        L3 = await pg.evaluate("async()=>(await __plate.brouillonsListe()).map(b=>b.n)")
        check(len(L3) == 3, f'rotation : 4 planches, les 3 brouillons les plus récents gardés ({L3})')
        await pg.click('[data-tab=projet]'); await pg.wait_for_timeout(200)
        nb = await pg.evaluate("()=>document.querySelectorAll('#brouillons [data-br]').length")
        check(nb == 2, f'onglet Projet : {nb} brouillons d\'autres planches proposés (« Reprendre »)')
        tous_errs += errs; await ctx.close()

        # ---------------------------------------------------------------- 4
        print('4. collage d\'un JSON forgé')
        ctx, pg, errs, msgs = await nouvelle_page(b, 1)
        await pg.evaluate("()=>{__plate.ajoute('texte',{texte:'base',x:100,y:100,w:300})}")
        n0 = await pg.evaluate("()=>__plate.S.doc.elements.length")
        A = 'atelier-mains-lsf'
        forges = [{'app': A, 'elements': [{'type': 'main'}]}, {'app': A, 'elements': [None]}, {'app': A, 'elements': [{'type': 'zzz', 'x': 'a'}]},
                  {'app': A, 'elements': 'non'}, {'app': A, 'elements': [{'type': 'image', 'asset': 'zz', 'x': 1}], 'assets': {'zz': 'javascript:alert(1)'}}]
        for f in forges: await pg.evaluate(COLLE, json.dumps(f)); await pg.wait_for_timeout(50)
        n1 = await pg.evaluate("()=>__plate.S.doc.elements.length")
        check(n1 == n0 and not errs, f'5 collages invalides ({{"type":"main"}}, [null], type inconnu, elements:"non", image à data: forgée) : {n1 - n0} objet ajouté, {len(errs)} erreur JS (avant : 2 erreurs, une main x NaN)')
        bons = [{'app': A, 'elements': [{'type': 'texte', 'x': 'a', 'w': None, 'corps': 'x', 'texte': 'collé', 'theme': {'corps': 'x'}, 'surlignages': [{'from': 'a'}]}]},
                {'app': A, 'elements': [{'type': 'main', 'pose': {'index': {'mcp': 'x', 'pip': 30}, 'prono': 1e9, 'pouce': {'av': None}}, 'x': 50, 'y': 50, 'w': 200, 'h': 300}]},
                {'app': A, 'elements': [{'type': 'image', 'asset': 'zz', 'x': 10, 'y': 10, 'w': 100, 'h': 50}], 'assets': {'zz': 'data:image/png;base64,' + b64(Image.new('RGB', (20, 10), (200, 0, 0)))}}]
        for f in bons: await pg.evaluate(COLLE, json.dumps(f)); await pg.wait_for_timeout(80)
        r = await pg.evaluate("""()=>{const L=__plate.S.doc.elements;const fin=L.every(e=>['x','y','w','h','rot'].every(k=>typeof e[k]==='number'&&isFinite(e[k])));
            const m=L.find(e=>e.type==='main'),t=L.find(e=>e.texte==='collé'),im=L.find(e=>e.type==='image');
            return{n:L.length,fin,pose:m&&m.pose,corps:t&&t.corps,theme:t&&t.theme,ids:new Set(L.map(e=>e.id)).size,img:im&&!!__plate.S.doc.assets[im.asset]}}""")
        check(r['n'] == n0 + 3 and r['fin'] and r['ids'] == r['n'], f'3 collages valides mais sales : {r["n"] - n0} objets, toutes les coordonnées finies, ids uniques ({r["ids"]})')
        check(r['pose'] == {'index': {'pip': 30}, 'prono': 360, 'pouce': {}} and r['corps'] == 48 and r['theme'] is None and r['img'],
              f'champs filtrés : pose {r["pose"]}, corps {r["corps"]} (« x » refusé), thème {r["theme"]}, image collée avec ses pixels : {r["img"]}')
        tous_errs += errs; await ctx.close()

        # ---------------------------------------------------------------- 5
        print('5. éclater en étapes dans la planche')
        ctx, pg, errs, msgs = await nouvelle_page(b, 1)
        for n in (4, 6):
            r = await pg.evaluate("""n=>{const P=__plate;P.charge(P.docNeuf('16:9'));const e=P.ajoute('main',{x:1500,y:300,w:279,h:410});P.selectionne([e.id]);P.eclate(n);P.invalide();
                const L=P.S.doc.elements,W=P.S.doc.planche.w,H=P.S.doc.planche.h;return{boites:L.map(e=>[Math.round(e.x),Math.round(e.x+e.w),Math.round(e.y),Math.round(e.y+e.h)]),
                dedans:L.every(e=>{const b=P.bbox([e]);return b.x>=-.5&&b.x+b.w<=W+.5&&b.y>=-.5&&b.y+b.h<=H+.5}),mains:L.filter(e=>e.type==='main').length}}""", n)
            xs = [bb for bb in r['boites']]
            check(r['dedans'] and r['mains'] == n, f'main en x = 1 500 sur 1 920, éclater en {n} : {r["mains"]} mains, toutes dans [0, 1 920] (x de {min(b[0] for b in xs)} à {max(b[1] for b in xs)} ; avant : jusqu\'à 2 991)')
        await pg.wait_for_timeout(300)
        st = await pg.evaluate("()=>{const r=document.getElementById('stage').getBoundingClientRect();return[r.left,r.top,r.width,r.height]}")
        await pg.screenshot(path=os.path.join(OUT, 'plate_correctifs_05_eclate.png'), clip={'x': st[0], 'y': st[1], 'width': st[2], 'height': st[3]})
        tous_errs += errs; await ctx.close()

        # ---------------------------------------------------------------- 6
        print('6. gabarit sur une planche pleine')
        rep = [False]
        ctx, pg, errs, msgs = await nouvelle_page(b, 1, dialogue=rep)
        await pg.evaluate("()=>{__plate.ajoute('texte',{texte:'mon travail',x:100,y:100,w:500})}")
        await pg.click('[data-tab=projet]'); await pg.click('#gabarits button:has-text("Carte")'); await pg.wait_for_timeout(150)
        t1 = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>e.type+':'+(e.texte||''))")
        check(len(msgs) == 1 and t1 == ['texte:mon travail'], f'confirmation refusée : planche gardée {t1} (avant : remplacée sans question)')
        rep[0] = True
        await pg.click('#gabarits button:has-text("Carte")'); await pg.wait_for_timeout(150)
        t2 = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>e.type+':'+(e.texte||''))")
        await pg.evaluate("()=>document.getElementById('stage').focus()"); await pg.keyboard.press('Control+z'); await pg.wait_for_timeout(100)
        t3 = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>e.type+':'+(e.texte||''))")
        check(t2 == ['main:', 'texte:MOT'] and t3 == ['texte:mon travail'] and 'Ctrl+Z' in msgs[-1], f'acceptée : {t2} ; Ctrl+Z : {t3} ; le message le dit')
        tous_errs += errs; await ctx.close()

        # ---------------------------------------------------------------- 7
        print('7. flèches : boîte = tracé, extrémités tirables')
        ctx, pg, errs, msgs = await nouvelle_page(b, 1)
        st = await pg.evaluate("()=>{const r=document.getElementById('stage').getBoundingClientRect();return[r.left,r.top,r.width,r.height]}")
        DEB = """e=>{const P=__plate,pts=P.flechePts(e,1);let o=0;pts.forEach(p=>{o=Math.max(o,-p.x,-p.y,p.x-e.w,p.y-e.h)});return Math.round(o)}"""
        avant = await pg.evaluate("""DEB=>{const P=__plate,deb=eval(DEB),e=P.ajoute('fleche',{x:600,y:500,w:384,h:108,de:[0,.5],a:[1,.5],style:'demi'});const o=deb(e);P.S.doc.elements.pop();return o}""", DEB)
        await pg.click('[data-outil=fleche]'); await pg.mouse.click(st[0] + 300, st[1] + 200)
        res = {}
        for code, lab in (('droite', 'Droite'), ('courbe', 'Courbe'), ('demi', 'Demi-cercle'), ('vague', 'Vague'), ('zigzag', 'Zigzag'), ('boucle', 'Boucle')):
            await pg.click(f'#props .seg button:has-text("{lab}")'); await pg.wait_for_timeout(30)
            res[code] = await pg.evaluate("DEB=>{const P=__plate,e=P.S.doc.elements[P.S.doc.elements.length-1];return[eval(DEB)(e),Math.round(e.w),Math.round(e.h)]}", DEB)
        check(all(v[0] <= 0 for v in res.values()), 'tracé dans la boîte pour les 6 styles (débordement max ' + str(max(v[0] for v in res.values())) + ' px ; ' +
              ', '.join(f'{k} {v[1]}×{v[2]}' for k, v in res.items()) + f') ; avant : le demi-cercle débordait de {avant} px')
        # demi-cercle : tirer l'extrémité B de +120, +60 px écran
        await pg.click('#props .seg button:has-text("Demi-cercle")')
        r0 = await pg.evaluate("""()=>{const P=__plate,e=P.S.doc.elements[P.S.doc.elements.length-1],H=P.poigneesFleche(),M=x=>{const c=Math.cos(e.rot*Math.PI/180);return[e.x+x[0]*e.w,e.y+x[1]*e.h]};return{H,A:M(e.de),B:M(e.a),z:P.S.zoom}}""")
        hb = r0['H'][1]
        await pg.mouse.move(st[0] + hb['x'], st[1] + hb['y']); await pg.mouse.down()
        for i in range(1, 9): await pg.mouse.move(st[0] + hb['x'] + 15 * i, st[1] + hb['y'] + 7.5 * i)
        await pg.mouse.up(); await pg.wait_for_timeout(100)
        r1 = await pg.evaluate("DEB=>{const P=__plate,e=P.S.doc.elements[P.S.doc.elements.length-1];return{A:[e.x+e.de[0]*e.w,e.y+e.de[1]*e.h],B:[e.x+e.a[0]*e.w,e.y+e.a[1]*e.h],o:eval(DEB)(e),n:P.S.doc.elements.length}}", DEB)
        dA = max(abs(r1['A'][0] - r0['A'][0]), abs(r1['A'][1] - r0['A'][1])); dB = [(r1['B'][0] - r0['B'][0]) * r0['z'], (r1['B'][1] - r0['B'][1]) * r0['z']]
        check(dA < 0.5 and abs(dB[0] - 120) < 1.5 and abs(dB[1] - 60) < 1.5 and r1['o'] <= 0,
              f'extrémité B tirée de (120, 60) px écran : B a bougé de ({dB[0]:.1f}, {dB[1]:.1f}), A de {dA:.2f} px, boîte refaite (débordement {r1["o"]} px)')
        # planche de contrôle : les 6 styles, sélectionnés
        await pg.evaluate("""()=>{const P=__plate;P.charge(P.docNeuf('16:9'));const S=['droite','courbe','demi','vague','zigzag','boucle'],ids=[];
            S.forEach((s,i)=>{const e=P.ajoute('fleche',{style:s,x:120+(i%3)*600,y:150+Math.floor(i/3)*480,w:420,h:100,couleur:'#00a19a'});P.ajusteBoiteFleche(e);ids.push(e.id)});P.selectionne(ids);P.invalide()}""")
        await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(OUT, 'plate_correctifs_07_fleches.png'), clip={'x': st[0], 'y': st[1], 'width': st[2], 'height': st[3]})
        tous_errs += errs; await ctx.close()

        # ---------------------------------------------------------------- 8
        print('8. téléphone 390 × 844')
        ctx, pg, errs, msgs = await nouvelle_page(b, 2, 390, 844)
        sh = await pg.evaluate("()=>document.scrollingElement.scrollHeight")
        # molette sur l'en-tête du panneau (hors du plateau, qui garde la molette et le doigt pour la vue)
        top = await pg.evaluate("()=>document.querySelector('aside').getBoundingClientRect().top")
        await pg.mouse.move(195, min(840, top + 15)); await pg.mouse.wheel(0, 2000); await pg.wait_for_timeout(300)
        sy = await pg.evaluate("()=>scrollY")
        await pg.click('[data-tab=projet]'); await pg.wait_for_timeout(200)
        bb = await pg.evaluate("()=>{const b=document.getElementById('bJsonExport');b.scrollIntoView({block:'center'});const r=b.getBoundingClientRect();return[r.top,r.bottom,innerHeight,scrollY]}")
        check(sh > 844 and sy > 0 and 0 <= bb[0] and bb[1] <= bb[2], f'la page défile : scrollHeight {sh}, scrollY {sy} après la molette (avant : 0) ; « Exporter le projet (.json) » atteint (haut {bb[0]:.0f} px, scrollY {bb[3]})')
        await pg.screenshot(path=os.path.join(OUT, 'plate_correctifs_08_mobile.png'))
        tous_errs += errs; await ctx.close()

        # ---------------------------------------------------------------- 9
        print('9. cache des mains (gabarit D, dpr 2)')
        ctx, pg, errs, msgs = await nouvelle_page(b, 2)
        st = await pg.evaluate("()=>{const r=document.getElementById('stage').getBoundingClientRect();return[r.left,r.top,r.width,r.height]}")
        await pg.evaluate("()=>{__plate.gabarit('D');__plate.invalide()}"); await pg.wait_for_timeout(400)
        # échantillonneur : rendus par image
        await pg.evaluate("()=>{window.__par=[];let p=__plate.S.rendus||0;const f=()=>{const n=__plate.S.rendus||0;window.__par.push(n-p);p=n;window.__raf=requestAnimationFrame(f)};f()}")
        r0 = await pg.evaluate("()=>__plate.S.rendus||0")
        # survol des quatre mains
        mains = await pg.evaluate("()=>__plate.S.doc.elements.filter(e=>e.type==='main').map(e=>__plate.ecran(e.x+e.w/2,e.y+e.h*.6))")
        for m in mains: await pg.mouse.move(st[0] + m[0], st[1] + m[1]); await pg.wait_for_timeout(40)
        r1 = await pg.evaluate("()=>__plate.S.rendus||0")
        check(r1 == r0, f'survol des 4 mains : {r1 - r0} rendu (avant : 1 — le test de collision demandait une autre taille qu\'à l\'affichage)')
        z0 = await pg.evaluate("()=>{window.__par=[];return __plate.S.zoom}")
        await pg.mouse.move(st[0] + st[2] / 2, st[1] + st[3] / 2); await pg.keyboard.down('Control')
        for i in range(12): await pg.mouse.wheel(0, -100); await pg.wait_for_timeout(16)
        await pg.keyboard.up('Control')
        pend = await pg.evaluate("()=>({n:(__plate.S.rendus||0),max:Math.max(0,...window.__par)})")
        await pg.wait_for_timeout(700)
        r2 = await pg.evaluate("()=>({n:(__plate.S.rendus||0),max:Math.max(0,...window.__par),zoom:__plate.S.zoom})")
        check(pend['max'] <= 1 and r2['n'] - r1 <= 8, f'12 crans de Ctrl+molette (zoom {z0:.2f} → {r2["zoom"]:.2f}, les 4 mains identiques partagent leur cache) : {pend["n"] - r1} rendus pendant le geste (au plus {pend["max"]} par image), {r2["n"] - r1} en tout avec la mise au net des 4 mains (avant : 6 rendus synchrones dans drawDoc)')
        await pg.evaluate("()=>{__plate.ajuste()}"); await pg.wait_for_timeout(400)
        # caches vidés (sinon ceux du zoom, plus grands, servent encore : réduire ×1,8 au plus est permis)
        r3 = await pg.evaluate("()=>{const P=__plate;P.videCache();const e=P.S.doc.elements.find(e=>e.type==='main');P.selectionne([e.id]);P.invalide();P.peint();window.__par=[];return{n:P.S.rendus||0,c:P.ecran(e.x+e.w,e.y+e.h),w:e.w,id:e.id}}")
        await pg.wait_for_timeout(100)
        await pg.mouse.move(st[0] + r3['c'][0], st[1] + r3['c'][1]); await pg.mouse.down()
        for i in range(1, 21): await pg.mouse.move(st[0] + r3['c'][0] + 6 * i, st[1] + r3['c'][1] + 9 * i); await pg.wait_for_timeout(16)
        mid = await pg.evaluate("()=>({n:(__plate.S.rendus||0),max:Math.max(0,...window.__par)})")
        await pg.mouse.up(); await pg.wait_for_timeout(400)
        r4 = await pg.evaluate("id=>({n:__plate.S.rendus||0,oct:__plate.cacheOctets(),w:__plate.parId(id).w})", r3['id'])
        check(r4['w'] > 1.5 * r3['w'] and mid['max'] <= 1 and mid['n'] - r3['n'] <= 3, f'glisser d\'un coin (main ×{r4["w"] / r3["w"]:.2f}) : {mid["n"] - r3["n"]} rendu(s) pendant le geste (au plus {mid["max"]} par image), {r4["n"] - r3["n"]} en tout (avant : 5)')
        # mémoire : 16 mains, zoom 8, va-et-vient : le cache reste sous 150 Mo
        r5 = await pg.evaluate("""async()=>{const P=__plate;for(let i=0;i<12;i++)P.ajoute('main',{x:100+i*140,y:100,w:279,h:410});for(const z of [8,4,2,1,.5,8]){P.zoomVers(z,700,400);P.invalide();P.peint();await new Promise(r=>setTimeout(r,30))}
            return{oct:P.cacheOctets(),n:[...P.HC.values()].reduce((s,l)=>s+l.length,0)}}""")
        check(r5['oct'] <= 150e6, f'16 mains, zooms 8 → 0,5 → 8 : cache {r5["oct"] / 1e6:.1f} Mo, {r5["n"]} images (limite 150 Mo, LRU à la mémoire)')
        await pg.evaluate("()=>cancelAnimationFrame(window.__raf)")
        tous_errs += errs; await ctx.close()

        # ---------------------------------------------------------------- 10–16
        print('10–16. défauts mineurs')
        rep = [True]
        ctx, pg, errs, msgs = await nouvelle_page(b, 1, dialogue=rep)
        st = await pg.evaluate("()=>{const r=document.getElementById('stage').getBoundingClientRect();return[r.left,r.top,r.width,r.height]}")
        # 10. « Choisir une image… » (fond) puis Annuler, puis une photo collée : elle devient un OBJET
        await pg.click('[data-tab=planche]'); await pg.click('#planchePane .seg button:has-text("Image")'); await pg.click('#planchePane button:has-text("Choisir une image")')
        await pg.evaluate("""([F,b])=>{const f=eval(F)({b,nom:'photo.png',type:'image/png'});const dt=new DataTransfer();dt.items.add(f);document.getElementById('stage').focus();
            document.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true}))}""", [FICHIER, b64(Image.new('RGB', (200, 100), (0, 120, 200)))])
        await pg.wait_for_timeout(400)
        r = await pg.evaluate("()=>({types:__plate.S.doc.elements.map(e=>e.type),fond:__plate.S.doc.planche.fond.src})")
        check(r['types'] == ['image'] and r['fond'] is None, f'« Choisir une image… » annulé puis photo collée : objet {r["types"]}, fond {r["fond"]} (avant : le fond était remplacé)')
        # 11. PNG de l'atelier déposé : rouvert comme projet (OK) ou inséré comme image (Annuler)
        await pg.evaluate("()=>{__plate.charge(__plate.docNeuf('carre'));__plate.gabarit('B')}")
        png = await pg.evaluate("async()=>{const r=await __plate.exporte({k:1});const u=new Uint8Array(await r.blob.arrayBuffer());let s='';for(let i=0;i<u.length;i+=8192)s+=String.fromCharCode.apply(null,u.subarray(i,i+8192));return btoa(s)}")
        DEPOT = """([F,b,x,y])=>{const f=eval(F)({b,nom:'cent.png',type:'image/png'});const dt=new DataTransfer();dt.items.add(f);const st=document.getElementById('stage');
            st.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,clientX:x,clientY:y}))}"""
        await pg.evaluate("()=>__plate.charge(__plate.docNeuf('16:9'))")
        await pg.evaluate(DEPOT, [FICHIER, png, st[0] + 400, st[1] + 300]); await pg.wait_for_timeout(500)
        t1 = await pg.evaluate("()=>[__plate.S.doc.planche.format,__plate.S.doc.elements.map(e=>e.type)]")
        rep[0] = False
        await pg.evaluate("()=>__plate.charge(__plate.docNeuf('16:9'))")
        await pg.evaluate(DEPOT, [FICHIER, png, st[0] + 400, st[1] + 300]); await pg.wait_for_timeout(500)
        t2 = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>e.type)")
        rep[0] = True
        check(t1 == ['carre', ['main', 'texte']] and t2 == ['image'], f'PNG de l\'atelier déposé : OK → planche rouverte {t1} ; Annuler → {t2}')
        # 12. A4 / A3 : ×1 seulement (déjà 300 dpi)
        await pg.evaluate("()=>__plate.charge(__plate.docNeuf('A3'))")
        await pg.keyboard.press('Control+e'); await pg.wait_for_timeout(150)
        dis = await pg.evaluate("()=>Array.from(document.querySelectorAll('#expEchelle button')).map(b=>b.disabled)")
        await pg.click('#expFermer')
        r = await pg.evaluate("async()=>{const r=await __plate.exporte({k:3,embarque:false});return[r.k,r.w,r.h]}")
        check(dis == [False, True, True] and r == [1, 3508, 4961], f'A3 : boutons ×2 / ×3 désactivés {dis}, export demandé à ×3 → ×{r[0]} = {r[1]} × {r[2]} (avant : 10 524 × 14 883)')
        # 13. ids en double, thème non numérique
        await pg.evaluate("""()=>__plate.charge({version:9,planche:{w:1920,h:1080},elements:[{type:'texte',id:'x',texte:'A',x:100,y:100,w:300,h:80},
            {type:'texte',id:'x',texte:'B',x:100,y:500,w:300,h:80,theme:{corps:'x',fond:'rouge'}}]})""")
        bxy = await pg.evaluate("()=>{const e=__plate.S.doc.elements[1];return __plate.ecran(e.x+e.w/2,e.y+e.h/2)}")
        await pg.mouse.click(st[0] + bxy[0], st[1] + bxy[1]); await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('ArrowRight')
        r = await pg.evaluate("()=>{const L=__plate.S.doc.elements;__plate.S.doc.theme.corps=60;__plate.appliqueTheme();return{ids:L.map(e=>e.id),x:L.map(e=>e.texte+':'+e.x),theme:L[1].theme||null,corps:L[1].corps}}")
        check(r['ids'][0] != r['ids'][1] and r['x'] == ['A:100', 'B:102'] and r['theme'] is None and isinstance(r['corps'], (int, float)),
              f'ids en double rendus uniques, clic sur B puis →→ : {r["x"]} (avant : A bougeait) ; thème {{corps:"x"}} refusé, corps {r["corps"]}')
        # 14. surlignages qui suivent la zone de saisie
        res = []
        for nouveau in ('le gros chat noir', 'chat noir', 'le chat nXoir'):
            res.append(await pg.evaluate("""nv=>{const P=__plate;P.charge(P.docNeuf('16:9'));const e=P.ajoute('texte',{texte:'le chat noir',x:100,y:100,w:800,surlignages:[{from:8,to:12,couleur:'#fff176'}]});
                P.selectionne([e.id]);P.S.dirty=true;const ta=document.querySelector('#props textarea');ta.value=nv;ta.dispatchEvent(new Event('change'));const x=P.parId(e.id);return x.surlignages.map(s=>x.texte.slice(s.from,s.to))}""", nouveau))
        check(res == [['noir'], ['noir'], ['nXoir']], f'« le chat noir » (noir surligné) modifié au panneau : {res} (avant : mauvais mots surlignés)')
        # 15. gabarits : titre en gras, invites non exportées, cadre photo de la fiche C
        r = await pg.evaluate("""async()=>{const P=__plate;P.charge(P.docNeuf('16:9'));P.gabarit('A');const c=P.S.doc.elements[1],g=document.createElement('canvas').getContext('2d');
            const L=P.lignesTexte(g,c,1);const enc=async()=>{const ex=await P.exporte({k:1,embarque:false});const bm=await createImageBitmap(ex.blob);const cv=document.createElement('canvas');cv.width=bm.width;cv.height=bm.height;
              const x=cv.getContext('2d');x.drawImage(bm,0,0);const d=x.getImageData(Math.round(c.x),Math.round(c.y),Math.round(c.w),Math.round(c.h)).data;let n=0;for(let i=0;i<d.length;i+=4)if(d[i]<90&&d[i+1]<90&&d[i+2]<90)n++;return n};
            const n0=await enc();c.texte='Définition\\nUn nombre entier, cent unités.';const n1=await enc();
            g.font='400 '+c.corps+'px "'+c.police+'"';const wr=g.measureText('Définition').width;return{titre:L[0].g,wb:Math.round(L[0].w),wr:Math.round(wr),n0,n1}}""")
        check(r['titre'] and r['wb'] > r['wr'] and r['n0'] == 0 and r['n1'] > 500,
              f'gabarit A : « Définition » en gras ({r["wb"]} px contre {r["wr"]} en maigre) ; invite non modifiée : {r["n0"]} pixel d\'encre à l\'export, modifiée : {r["n1"]}')
        await pg.evaluate("()=>{__plate.charge(__plate.docNeuf('A4'));__plate.gabarit('C');__plate.invalide()}"); await pg.wait_for_timeout(300)
        cad = await pg.evaluate("()=>{const e=__plate.S.doc.elements.find(e=>e.cadre);return{c:__plate.ecran(e.x+e.w/2,e.y+e.h*.4),b:[e.x,e.y,e.w,e.h]}}")
        photo = Image.new('RGB', (1200, 800), (240, 180, 60)); dd = ImageDraw.Draw(photo); dd.ellipse((300, 150, 900, 650), fill=(40, 120, 200))
        await pg.evaluate("""([F,b,x,y])=>{const f=eval(F)({b,nom:'photo.jpg',type:'image/jpeg'});const dt=new DataTransfer();dt.items.add(f);document.getElementById('stage').dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,clientX:x,clientY:y}))}""",
                          [FICHIER, b64(photo, 'JPEG'), st[0] + cad['c'][0], st[1] + cad['c'][1]])
        await pg.wait_for_timeout(600)
        r = await pg.evaluate("()=>{const L=__plate.S.doc.elements,c=L.find(e=>e.cadre),im=L.find(e=>e.type==='image');return{im:im&&[im.x,im.y,im.w,im.h],texte:c.texte,ordre:L.indexOf(im)-L.indexOf(c)}}")
        bx = cad['b']; im = r['im']
        dedans = im and im[0] >= bx[0] - .5 and im[1] >= bx[1] - .5 and im[0] + im[2] <= bx[0] + bx[2] + .5 and im[1] + im[3] <= bx[1] + bx[3] + .5
        check(dedans and r['texte'] == 'Légende…' and r['ordre'] == 1, f'fiche C : photo déposée sur le cadre, calée dedans ({[round(v) for v in im]} dans {[round(v) for v in bx]}), invite → « {r["texte"]} »')
        await pg.screenshot(path=os.path.join(OUT, 'plate_correctifs_15_ficheC.png'), clip={'x': st[0], 'y': st[1], 'width': st[2], 'height': st[3]})
        # 16. personnage : boîte lue chez M4, le dessin y tient
        r = await pg.evaluate("""async()=>{const P=__plate,A=window.AtelierPersonnage;P.charge(P.docNeuf('16:9'));P.S.doc.planche.fond.type='transparent';const e=P.ajoute('personnage');e.y=60;
            const B=P.persHL(),b=A&&A.boite?A.boite(100):null;const ex=await P.exporte({k:1,embarque:false,transparent:true});const bm=await createImageBitmap(ex.blob);const cv=document.createElement('canvas');cv.width=bm.width;cv.height=bm.height;
            const x=cv.getContext('2d');x.drawImage(bm,0,0);const d=x.getImageData(0,0,cv.width,cv.height).data;let y0=1e9,y1=-1,x0=1e9,x1=-1;for(let j=0;j<cv.height;j++)for(let i=0;i<cv.width;i++)if(d[(j*cv.width+i)*4+3]>16){y0=Math.min(y0,j);y1=Math.max(y1,j);x0=Math.min(x0,i);x1=Math.max(x1,i)}
            return{M4:!!A,B,b,enc:[x0,y0,x1,y1],boite:[e.x,e.y,e.x+e.w,e.y+e.h]}}""")
        enc, bo = r['enc'], r['boite']
        check(r['M4'] and abs(r['B']['w'] - r['b']['w'] / 100) < 1e-9 and enc[1] >= bo[1] - 0.5 and enc[3] <= bo[3] + 0.5 and enc[0] >= bo[0] - 0.5 and enc[2] <= bo[2] + 0.5,
              f'personnage M4 : boîte lue chez AtelierPersonnage.boite ({r["b"]["w"] / 100:.2f} × {r["b"]["h"] / 100:.2f} HL, +2 % en haut et en bas) ; encre {enc} dans la boîte {[round(v) for v in bo]} (antennes comprises)')
        tous_errs += errs; await ctx.close()

        print('erreurs JS :', tous_errs or 'aucune'); check(not tous_errs, 'aucune erreur JS (pageerror) dans les 10 pages')
        await b.close()
    print(f'{len(MESURES) - len(ECHECS)} contrôles verts sur {len(MESURES)}')
    print('ÉCHECS :', ECHECS or 'aucun')
    sys.exit(1 if ECHECS else 0)

asyncio.run(main())
