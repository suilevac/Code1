"""Projet, formats et robustesse de l'éditeur de planche (v2/plate) : JSON v6–v8 de la v1 lus comme projet, JSON
tordus refusés sans casser l'atelier, PNG exporté rouvert comme projet, brouillon IndexedDB, formats et sonde
d'export, thème des gabarits, main gauche = miroir 3D (pas d'image retournée).

  python3 v2/tests/plate_projet.py        → v2/tests/out/plate_projet_*.png
"""
import asyncio, base64, json, os, sys
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = 'file://' + os.path.join(ROOT, 'plate', 'index.html')
OUT = os.path.join(ROOT, 'tests', 'out'); os.makedirs(OUT, exist_ok=True)
ECHECS = []
def check(cond, msg):
    print(('  ok   ' if cond else '  ÉCHEC ') + msg)
    if not cond: ECHECS.append(msg)

# une configuration v8 de la v1 (snapshot()) : deux mains, deux étapes clés, fond uni, référent.
# Dans la v1, la flèche du segment i → i+1 est portée par la clé i (segFl(i) = cles[i].fl || fl, script.js l. 1222).
POSE = lambda mcp: {"f": {"pouce": {"av": 20, "rap": 10, "mcp": 15, "ip": 10}, "index": {"mcp": mcp, "pip": 30, "dip": 15, "ab": 0},
                           "majeur": {"mcp": 25, "pip": 30, "dip": 15, "ab": 0}, "annulaire": {"mcp": 25, "pip": 30, "dip": 15, "ab": 0},
                           "auriculaire": {"mcp": 25, "pip": 30, "dip": 15, "ab": 0}}, "q": [0, 0.2, 0, 0.98], "pos": [-10, 0, 0]}
V8 = {"version": 8, "mode": "mouvement", "mains": "DG", "act": "D", "pose": {"D": POSE(25), "G": POSE(40)},
      "cles": [{"D": POSE(0), "G": POSE(40), "fl": {"style": "demi", "sens": -1, "double": True, "col": "#b3261e"}}, {"D": POSE(90), "G": POSE(40)}],
      "cur": 0, "etapes": 1, "fleche": True, "fl": {"style": "arc", "sens": 1, "double": False, "col": "#1e1e1e"},
      "decor": {"fond": {"type": "uni", "col": "#fff4d6", "cadre": False}, "ref": {"style": "trait", "t": 1, "h": 0, "x": 0, "visage": True, "reperes": False}},
      "verrous": {}, "vue": {"pos": [0, 0, 52], "cible": [0, 0, 0]}}
V6 = {"version": 6, "mode": "pose", "gauche": True, "pose": POSE(50)}
TORDUS = [None, 42, {"version": 9, "elements": "non"}, {"version": 9, "elements": [{"type": "main"}, {"type": "texte", "texte": 12, "couleur": 7, "corps": "gros"}, {"type": "inconnu"}]},
          {"version": 9, "planche": {"w": "large", "fond": {"type": "image", "src": "absent"}}, "theme": {"couleur": 12}}, {"version": 3}, {"version": 9, "assets": {"a": "pas une image"}, "elements": [{"type": "image", "asset": "a"}]}]

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 1400, 'height': 860})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(PAGE); await pg.wait_for_timeout(1200)
        n = lambda: pg.evaluate("()=>__plate.S.doc.elements.length")

        print('1. JSON v8 de la v1 lu comme projet')
        await pg.evaluate("o=>__plate.charge(o)", V8)
        d = await pg.evaluate("()=>{const d=__plate.S.doc;return{types:d.elements.map(e=>e.type),cotes:d.elements.filter(e=>e.type==='main').map(e=>e.cote),fond:d.planche.fond,"
                              "mcpD:d.elements.find(e=>e.cote==='D').pose.index.mcp,q:d.elements.find(e=>e.cote==='D').orientation,cles:d.elements.find(e=>e.cote==='D').mouvement.cles.length,"
                              "mcp0:d.elements.find(e=>e.cote==='D').mouvement.cles[0].pose.index.mcp,mcp1:d.elements.find(e=>e.cote==='D').mouvement.cles[1].pose.index.mcp,fl0:d.elements.find(e=>e.cote==='D').mouvement.cles[0].fl,fl1:d.elements.find(e=>e.cote==='D').mouvement.cles[1].fl}}")
        check(d['types'] == ['personnage', 'main', 'main'] and d['cotes'] == ['D', 'G'], f'référent + deux mains : {d["types"]} {d["cotes"]}')
        check(d['fond']['type'] == 'uni' and d['fond']['col'] == '#fff4d6', f'fond repris : {d["fond"]["type"]} {d["fond"]["col"]}')
        check(d['mcpD'] == 25 and d['q'] == [0, 0.2, 0, 0.98], f'pose convertie telle quelle (index.mcp {d["mcpD"]}, orientation {d["q"]})')
        check(d['cles'] == 2 and d['mcp0'] == 0 and d['mcp1'] == 90 and d['fl0'] == {'style': 'demi', 'sens': -1, 'double': True, 'couleur': '#b3261e'} and d['fl1']['style'] == 'courbe',
              f'étapes clés gardées dans mouvement.cles : {d["cles"]} (mcp {d["mcp0"]} → {d["mcp1"]}, flèche du segment 0 {d["fl0"]}, « arc » global → {d["fl1"]["style"]})')
        await pg.evaluate("()=>{const e=__plate.S.doc.elements.find(e=>e.cote==='D');__plate.selectionne([e.id]);__plate.eclate()}")
        t = await pg.evaluate("()=>__plate.S.doc.elements.map(e=>e.type+(e.type==='main'?e.pose.index.mcp:e.type==='fleche'?e.style+(e.double?'+double':'')+e.couleur:''))")
        check(t == ['personnage', 'main40', 'main0', 'flechedemi+double#b3261e', 'main90'], f'éclater en étapes reprend les poses et la flèche des clés : {t}')
        await pg.screenshot(path=os.path.join(OUT, 'plate_projet_01_v8.png'))
        await pg.evaluate("o=>__plate.charge(o)", V6)
        d = await pg.evaluate("()=>{const e=__plate.S.doc.elements[0];return{n:__plate.S.doc.elements.length,cote:e.cote,mcp:e.pose.index.mcp}}")
        check(d == {'n': 1, 'cote': 'G', 'mcp': 50}, f'JSON v6 (main gauche, pose fixe) : {d}')

        print('2. JSON tordus : refusés ou nettoyés, l\'atelier répond encore')
        for o in TORDUS:
            r = await pg.evaluate("o=>{try{__plate.charge(o);return'ok:'+__plate.S.doc.elements.length}catch(e){return'refus:'+e.message}}", o)
            vivant = await pg.evaluate("()=>{__plate.ajoute('texte',{texte:'x'});__plate.hist.undoer();return __plate.S.doc.elements.length>=0}")
            check(vivant, f'{json.dumps(o)[:60]} → {r}, atelier vivant')
        d = await pg.evaluate("o=>{__plate.charge(o);return __plate.S.doc.elements.map(e=>e.type)}", TORDUS[3])
        check(d == ['texte'], f'éléments invalides écartés un par un (main sans pose, type inconnu) : {d}')

        print('3. PNG exporté rouvert comme projet')
        await pg.evaluate("()=>{__plate.charge(__plate.docNeuf('carre'));__plate.gabarit('B')}")
        r = await pg.evaluate("""async()=>{const r=await __plate.exporte({k:1});const f=new File([r.blob],'carte.png',{type:'image/png'});
          __plate.charge(__plate.docNeuf('16:9'));const avant=__plate.S.doc.elements.length;const buf=await f.arrayBuffer();const o=__plate.projetDuPng(buf);__plate.charge(o);
          return{avant,apres:__plate.S.doc.elements.length,w:__plate.S.doc.planche.w,png:r.w,octets:r.blob.size}}""")
        check(r['avant'] == 0 and r['apres'] == 2 and r['w'] == 1080 and r['png'] == 1080, f'carte B exportée ({r["png"]} px, {r["octets"]//1024} Ko) puis rouverte : {r["apres"]} objets, planche {r["w"]}')
        ok = await pg.evaluate("""async()=>{const r=await __plate.exporte({k:1});const u=new Uint8Array(await r.blob.arrayBuffer());
          // le chunk iTXt est juste après IHDR et sa clé est « atelier-mains-lsf »
          const type=String.fromCharCode(u[37],u[38],u[39],u[40]);const cle=new TextDecoder().decode(u.subarray(41,58));return type+'|'+cle}""")
        check(ok == 'iTXt|atelier-mains-lsf', f'chunk après IHDR : {ok}')

        print('4. brouillon IndexedDB')
        await pg.evaluate("()=>{__plate.ajoute('texte',{texte:'brouillon',x:50,y:50,w:400})}")
        await pg.evaluate("()=>__plate.brouillonSauve()")
        b2 = await pg.evaluate("async()=>{const b=await __plate.brouillonLit();return b&&b.json&&b.json.elements.length}")
        check(b2 == 3, f'brouillon lu : {b2} éléments')
        await pg.reload(); await pg.wait_for_timeout(1500)
        vis = await pg.evaluate("()=>!document.getElementById('bBrouillon').hidden")
        check(vis, 'après rechargement : bouton « Reprendre le brouillon » proposé')
        await pg.click('[data-tab=projet]'); await pg.click('#bBrouillon'); await pg.wait_for_timeout(300)
        check(await n() == 3, f'brouillon repris : {await n()} éléments')

        print('5. formats, sonde et thème')
        for fmt, w, h in [('A4', 2480, 3508), ('bandeau', 2400, 600), ('A3', 3508, 4961)]:
            await pg.evaluate("f=>__plate.charge(__plate.docNeuf(f))", fmt)
            r = await pg.evaluate("async()=>{const r=await __plate.exporte({k:1,embarque:false});return[r.w,r.h,r.k]}")
            check(r[0] == w and r[1] == h, f'{fmt} ×1 = {r[0]} × {r[1]}')
        # sonde (outil.md § 6.3) : Chrome peint jusqu'à 268 Mpx d'aire ; A3 ×3 = 157 Mpx passe, 16 384² ×2 = 1 074 Mpx non
        r = await pg.evaluate("()=>[__plate.echelleExport(3,{w:3508,h:4961}),__plate.echelleExport(2,{w:16384,h:16384}),__plate.echelleExport(3,{w:12000,h:9000})]")
        check(r == [3, 1, 1], f'sonde : A3 ×3 (157 Mpx) → ×{r[0]} ; 16 384² ×2 → ×{r[1]} ; 12 000 × 9 000 ×3 (972 Mpx) → ×{r[2]}')
        await pg.evaluate("()=>{__plate.charge(__plate.docNeuf('16:9'));__plate.gabarit('A');__plate.S.doc.theme.couleur='#b3261e';__plate.S.doc.theme.corps=60;__plate.S.doc.theme.police='Nunito';__plate.appliqueTheme();__plate.invalide()}")
        th = await pg.evaluate("()=>__plate.S.doc.elements.filter(e=>e.type==='texte').map(e=>[e.police,e.corps,e.fond])")
        check(th[0] == ['Nunito', 90, '#f0d4d2'] and th[1][1] == 36,   # #b3261e mêlé à 80 % de blanc : (240, 212, 210)
               f'thème appliqué aux objets du gabarit : {th}')
        await pg.wait_for_timeout(300); await pg.screenshot(path=os.path.join(OUT, 'plate_projet_02_theme.png'))

        print('6. main gauche = miroir 3D : l\'ombre reste du même côté, le pouce change de côté')
        r = await pg.evaluate("""()=>{const e=__plate.ajoute('main',{cote:'D'});const cD=__plate.mainCache(e,256,384,true);__plate.selectionne([e.id]);__plate.convertitCote();const cG=__plate.mainCache(__plate.parId(e.id),256,384,true);
          // pointe = pixel opaque le plus haut (bout du majeur) ; le pouce est du côté opposé à la masse des doigts.
          // ombre = pixels au ton d'ombre de la peau (#00a19a × 0,78 = 0,126,120 ; ±20), trait noir exclu
          const cols=(c)=>{const d=c.getContext('2d').getImageData(0,0,256,384).data;let tip=-1,sombreL=0,sombreR=0,cx=0,n=0;for(let y=0;y<384;y++)for(let x=0;x<256;x++){const i=(y*256+x)*4;if(d[i+3]<8)continue;
              if(tip<0)tip=x;cx+=x;n++;if(Math.abs(d[i])<20&&Math.abs(d[i+1]-126)<20&&Math.abs(d[i+2]-120)<20){if(x<cx/n)sombreL++;else sombreR++}}return[tip,Math.round(cx/n),sombreL,sombreR]};
          return{D:cols(cD),G:cols(cG),cote:__plate.parId(e.id).cote}}""")
        D, G = r['D'], r['G']
        # vue paume (caméra en +Z) : main DROITE = pouce à DROITE de l'image (dessin paume.jpg, « face élève »), donc la masse
        # des doigts et le bout du majeur à gauche du milieu ; la gauche est son miroir (relecture M3 : c'était inversé)
        check(r['cote'] == 'G' and D[0] < 128 and G[0] > 128, f'bout du majeur : D x={D[0]} (pouce à droite en vue paume, comme le dessin), G x={G[0]} (pouce à gauche)')
        check(D[3] > 2 * D[2] and G[3] > 2 * G[2], f'ombre franche à droite du centre pour les deux mains : D {D[2]}/{D[3]} px, G {G[2]}/{G[3]} px (un miroir d\'image l\'aurait mise à gauche pour l\'une)')

        print('erreurs JS :', errs or 'aucune'); check(not errs, 'aucune erreur JS')
        await b.close()
    print('ÉCHECS :', ECHECS or 'aucun')
    sys.exit(1 if ECHECS else 0)

asyncio.run(main())
