"""Reprise de la v1 dans la page construite (dist/atelier-v2.local.html).
1. Configurations enregistrées PAR LA V1 elle-même (dist/atelier-mains-lsf.local.html, snapshot() = JSON v8 avec la vue
   caméra) : V (2) de face, V (2) vue « signeur » (dos), V (2) dos ¾, Poing serré de ¾ ; rouvertes en v2 (charge →
   convertitV1, poses converties par AtelierHand.depuisV1, caméra v1 portée dans l'orientation) ; comparées à la capture
   v1 du même angle : IoU des silhouettes recadrées, contre l'IoU de la v2 retournée (un mauvais sens donnerait l'inverse).
2. JSON v6 (main gauche, pose fixe), v7 (mouvement début / fin), v8 à deux mains avec trois étapes : lus, mains, côtés,
   étapes, flèches.
3. Bibliothèque db : une fausse capability claude.ai (window.claude.use) sert la collection « configurations » de la v1
   (lignes {nom, note, etat, creeLe}) et « projets » ; « Ouvrir » une configuration v1 → planche ; « Enregistrer » →
   ligne dans « projets » ; aucune écriture dans « configurations ».
   La fausse capability applique la limite réelle du contrat db 0.2.76 (ligne ≤ 256 Kio = 262 144 octets sérialisés, sinon
   invalid_argument) ; une photo JPEG de ≈ 300 Ko collée sur la planche : (a) avec la capability assets, l'image part par
   assets.upload et la ligne tient ; rechargée, l'image revient ; (b) sans assets, la ligne part sans l'image avec un
   message qui le dit (et pas un faux problème de droits).
4. Capability downloads : l'export PNG et l'export .json passent par downloads.save({filename, data}).
→ tests/out/integration_v1.png, integration_v1.json"""
import asyncio, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integration_commun import *
from PIL import Image

VUES_V1 = [('V (2)', [0, 0, 52], 'V (2) · face'), ('V (2)', [0, 0, -52], 'V (2) · signeur (dos)'),
           ('V (2)', [-30, 10, -40], 'V (2) · dos ¾'), ('Poing serré', [34, 14, 38], 'Poing serré · ¾')]

FAUX_CLAUDE = """(()=>{const lignes={configurations:[],projets:[]},ecrits=[],sauves=[],blobs={},refus=[];let n=0;
  const LIM=262144,taille=d=>new Blob([JSON.stringify(d)]).size,verifie=d=>{const t=taille(d);if(t>LIM){refus.push(t);throw{code:'invalid_argument',message:'document over 256 KiB'}}return t};
  const col=nom=>({orderBy:()=>col(nom),onSnapshot:(ok)=>{const f=()=>ok({docs:lignes[nom].map(l=>({id:l.id,data:()=>l.data}))});f();(col.abo[nom]=col.abo[nom]||[]).push(f);return()=>{}},
    add:async d=>{const t=verifie(d);ecrits.push({nom,op:'add',octets:t});const id='x'+(++n);lignes[nom].push({id,data:d});(col.abo[nom]||[]).forEach(f=>f());return{id}},
    doc:id=>({set:async d=>{const t=verifie(d);ecrits.push({nom,op:'set',octets:t});const l=lignes[nom].find(x=>x.id===id);if(l)l.data=d;else lignes[nom].push({id,data:d});(col.abo[nom]||[]).forEach(f=>f())},
      delete:async()=>{ecrits.push({nom,op:'delete'});lignes[nom]=lignes[nom].filter(x=>x.id!==id);(col.abo[nom]||[]).forEach(f=>f())}})});
  col.abo={};
  const db={collection:col},downloads={save:async({filename,data})=>{sauves.push({filename,taille:data&&data.size,type:data&&data.type});return{status:'saved'}}};
  // assets : upload → id de 32 hex ; « /_blob/<id> » servi par un fetch enveloppé (la page est en file://)
  const assets={upload:async(b,o)=>{const id=(Math.random().toString(16).slice(2)+'0'.repeat(32)).slice(0,32);blobs[id]=b;return{id,url:'/_blob/'+id,sizeBytes:b.size,contentType:(o&&o.type)||b.type}}};
  const f0=window.fetch.bind(window);window.fetch=(u,...a)=>{const m=typeof u==='string'&&/^\/_blob\/([0-9a-f]{32})$/.exec(u);return m?Promise.resolve(blobs[m[1]]?new Response(blobs[m[1]]):new Response('',{status:404})):f0(u,...a)};
  window.__faux={lignes,ecrits,sauves,blobs,refus,assets:true};
  window.claude={use:async nom=>nom==='db'?db:nom==='downloads'?downloads:nom==='assets'?(window.__faux.assets?assets:null):null}})()"""


def masque(im, v1=False):
    """Silhouette recadrée sur sa boîte, puis sur ses 70 % du HAUT (la v1 montre un avant-bras plus long que la v2 : la
    main elle-même est comparée). v1 : capture d'écran, la main = pixels verts (g − r > 40 : ni le damier gris ni les
    boutons) bouchés (scipy binary_fill_holes) ; v2 : alpha de l'image rendue."""
    from scipy import ndimage
    a = np.asarray(im.convert('RGBA')).astype(int)
    if v1:
        m = ndimage.binary_closing((a[..., 1] - a[..., 0]) > 40, iterations=2)
        m = ndimage.binary_fill_holes(m)
        lab, n = ndimage.label(m)
        if n > 1:
            m = lab == (1 + int(np.argmax(ndimage.sum(m, lab, range(1, n + 1)))))
    else:
        m = a[..., 3] > 128
    ys, xs = np.nonzero(m)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    m = m[:max(2, int(0.7 * m.shape[0]))]
    ys, xs = np.nonzero(m)
    m = m[:, xs.min():xs.max() + 1]
    return Image.fromarray((m * 255).astype(np.uint8))


def iou(a, b):
    b = b.resize(a.size, Image.NEAREST)
    a = np.asarray(a) > 127; b = np.asarray(b) > 127
    return float((a & b).sum() / max(1, (a | b).sum()))


async def configs_v1(p):
    """Rend et enregistre des configurations avec la v1 elle-même → [(titre, json v8, capture PIL)]."""
    b = await p.chromium.launch(args=ARGS)
    pg = await b.new_page(viewport={'width': 1300, 'height': 820})   # Browser.new_page : three.js servi par run_rendu.py
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    await pg.goto(PAGE_V1); await pg.wait_for_timeout(7000)
    # captures de la MAIN v1 seule : l'infobulle « Tire un doigt… » et les boutons de vue de la v1 sont masqués (relecture M5)
    await pg.add_style_tag(content='#stage .over, #tip { display: none !important; }')
    L = []
    for preset, cam, titre in VUES_V1:
        await pg.evaluate("n=>{const A=window.__atelier;A.editable().f=JSON.parse(JSON.stringify(A.PRESETS['Dessin'].f));A.applyPreset(n)}", preset)
        await pg.evaluate("c=>{const A=window.__atelier;A.camera.position.set(...c);A.camera.lookAt(0,0,0)}", cam)
        await pg.wait_for_timeout(700)
        shot = await pg.screenshot(clip={'x': 16, 'y': 66, 'width': 878, 'height': 737})
        js = await pg.evaluate("()=>JSON.parse(JSON.stringify(window.__atelier.snapshot()))")
        L.append((titre, js, png_pil(shot)))
    await b.close()
    return L, errs


async def main():
    res = {'cas_v1': []}
    async with async_playwright() as p:
        v1, err_v1 = await configs_v1(p)
        res['erreurs_v1'] = err_v1
        b = await p.chromium.launch(args=ARGS)
        ctx = await b.new_context(viewport={'width': 1500, 'height': 950})
        await ctx.add_init_script(FAUX_CLAUDE)
        pg = await ctx.new_page()
        err = []; pg.on('pageerror', lambda e: err.append('pageerror ' + str(e)))
        pg.on('console', lambda m: err.append(m.type + ' ' + m.text) if m.type == 'error' else None)
        await pg.goto(PAGE); await pg.evaluate('()=>AtelierHand.ready'); await pg.wait_for_timeout(800)
        ims, tit = [], []
        # --- 1. configurations de la v1, rouvertes en v2 ---
        for titre, js, cap in v1:
            out = await pg.evaluate("""o=>{const P=__plate;P.charge(o);const e=P.S.doc.elements.find(x=>x.type==='main');
              const h=600,w=Math.round(h*e.w/e.h);return {u:P.mainCache(e,w,h,true).toDataURL(),q:e.orientation,cote:e.cote,pose:e.pose,vue:o.vue}}""", js)
            im2 = png_pil(out['u'])
            m1, m2 = masque(cap, True), masque(im2)
            juste, inverse = iou(m1, m2), iou(m1, m2.transpose(Image.FLIP_LEFT_RIGHT))
            res['cas_v1'].append({'cas': titre, 'vue_v1': out['vue'], 'orientation_v2': [round(x, 4) for x in out['q']],
                                  'iou_silhouette': round(juste, 3), 'iou_si_retournee': round(inverse, 3),
                                  'index_mcp_pip': [round(out['pose']['index'].get('mcp', 0), 1), round(out['pose']['index'].get('pip', 0), 1)]})
            ims += [cap, im2]; tit += ['v1 : ' + titre, 'v2 (rouvert) : ' + titre]
        # --- 2. JSON v6, v7, v8 à deux mains et trois étapes ---
        F = {'pouce': {'av': 30, 'rap': 20, 'mcp': 10, 'ip': 10}, 'index': {'mcp': 0, 'pip': 0, 'dip': 0, 'ab': 4},
             'majeur': {'mcp': 0, 'pip': 0, 'dip': 0, 'ab': 0}, 'annulaire': {'mcp': 85, 'pip': 95, 'dip': 60, 'ab': 0},
             'auriculaire': {'mcp': 85, 'pip': 95, 'dip': 60, 'ab': 0}}
        P0 = {'f': F, 'q': [0, 0, 0, 1], 'pos': [0, 0, 0]}
        Pq = {'f': F, 'q': [0, 0.3826834, 0, 0.9238795], 'pos': [-9, 0, 0]}
        PG = {'f': F, 'q': [0, -0.3826834, 0, 0.9238795], 'pos': [9, 0, 0]}
        jsons = {'v6': {'version': 6, 'gauche': True, 'mode': 'pose', 'pose': P0},
                 'v7': {'version': 7, 'mode': 'mouvement', 'debut': P0, 'fin': Pq, 'etapes': 2},
                 'v8_DG_3_etapes': {'version': 8, 'mode': 'mouvement', 'mains': 'DG', 'act': 'D', 'pose': {'D': Pq, 'G': PG},
                                    'cles': [{'D': P0, 'G': PG, 'fl': {'style': 'arc', 'sens': 1, 'double': False, 'col': '#e0007a'}},
                                             {'D': Pq, 'G': PG}, {'D': P0, 'G': P0}], 'cur': 0, 'etapes': 1,
                                    'fl': {'style': 'zigzag', 'sens': 1, 'double': True, 'col': '#1e1e1e'},
                                    'decor': {'fond': {'type': 'uni', 'col': '#fff8e0'}, 'ref': {'style': 'plein', 't': 1, 'h': 0, 'x': 0}}}}
        res['json'] = {}
        for k, o in jsons.items():
            r = await pg.evaluate("""o=>{const P=__plate;P.charge(o);const d=P.S.doc;return {note:P.noteMouvement(d),selection:P.S.sel.length,types:d.elements.map(e=>e.type),
              mains:d.elements.filter(e=>e.type==='main').map(e=>({cote:e.cote,etapes:e.mouvement?e.mouvement.cles.length:0,
                fleches:e.mouvement?e.mouvement.cles.map(c=>c.fl?c.fl.style:null):null,q:e.orientation.map(x=>+x.toFixed(3)),x:Math.round(e.x)})),fond:d.planche.fond.type+' '+d.planche.fond.col}}""", o)
            res['json'][k] = r
        exp = await pg.evaluate("""async()=>{const r=await __plate.exporte({k:1,embarque:false});return URL.createObjectURL(r.blob)}""")
        im = png_pil('data:image/png;base64,' + __import__('base64').b64encode(await blob_octets(pg, "fetch('%s').then(r=>r.blob())" % exp)).decode())
        ims.append(im); tit.append('JSON v8 · deux mains, 3 étapes, référent')
        # --- 3. bibliothèque db : configurations de la v1 (lecture seule) et projets v2 ---
        await pg.evaluate("""l=>{window.__faux.lignes.configurations.push(...l.map((x,i)=>({id:'c'+i,data:x})));}""",
                          [{'nom': 'V vu de dos', 'note': 'test v1', 'etat': v1[2][1], 'creeLe': 1760000000000},
                           {'nom': 'deux mains', 'note': '', 'etat': jsons['v8_DG_3_etapes'], 'creeLe': 1760000001000}])
        await pg.evaluate("()=>__plate.setItemsV1(window.__faux.lignes.configurations.map(l=>({id:l.id,data:()=>l.data})))")
        await pg.click('[role=tab][data-tab=projet]'); await pg.wait_for_timeout(300)
        bloc = await pg.evaluate("()=>({visible:!document.getElementById('libV1Bloc').hidden,lignes:document.querySelectorAll('#libV1 .item').length,texte:document.getElementById('libV1').innerText})")
        await pg.click('#libV1 [data-v1="c0"]'); await pg.wait_for_timeout(500)
        ouvert = await pg.evaluate("()=>({nom:document.getElementById('nom').value,mains:__plate.S.doc.elements.filter(e=>e.type==='main').length,msg:document.getElementById('topMsg').innerText})")
        await pg.click('#bEnregistrer'); await pg.wait_for_timeout(500)
        ligne_v1 = await pg.evaluate("window.__faux.lignes.projets.map(l=>({nom:l.data.nom,elements:l.data.etat.elements.length,version:l.data.etat.version}))")
        # --- 3b. limite de 256 Kio : photo JPEG ≈ 300 Ko collée, avec puis sans la capability assets ---
        import io as _io
        rng = np.random.default_rng(1); a = (rng.random((600, 900, 3)) * 255).astype('uint8'); bb = _io.BytesIO()
        Image.fromarray(a).save(bb, 'JPEG', quality=70); jp = bb.getvalue()
        lourd = {'photo_octets': len(jp)}
        for avec in (True, False):
            await pg.evaluate("a=>{window.__faux.assets=a;__plate.nouveau&&__plate.nouveau()}", avec); await pg.wait_for_timeout(300)
            await pg.evaluate("()=>{__plate.S.dbId=null}")
            await pg.focus('#stage')
            await pg.evaluate("""b64=>{const bin=atob(b64),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
              const f=new File([u],'photo.jpg',{type:'image/jpeg'});const dt=new DataTransfer();dt.items.add(f);document.dispatchEvent(new ClipboardEvent('paste',{clipboardData:dt,bubbles:true}))}""", __import__('base64').b64encode(jp).decode())
            await pg.wait_for_timeout(1200)
            nom = 'photo ' + ('avec assets' if avec else 'sans assets')
            await pg.fill('#nom', nom)
            avant = await pg.evaluate("()=>({octets:new Blob([JSON.stringify(__plate.serialise())]).size,images:__plate.S.doc.elements.filter(e=>e.type==='image').length})")
            await pg.click('#bEnregistrer'); await pg.wait_for_timeout(800)
            r = await pg.evaluate("""n=>{const l=window.__faux.lignes.projets.find(x=>x.data.nom===n);return {msg:document.getElementById('topMsg').innerText,
                enregistre:!!l,octets_ligne:l?new Blob([JSON.stringify(l.data)]).size:null,images_ligne:l?l.data.etat.elements.filter(e=>e.type==='image').length:null,
                assets_ligne:l?Object.values(l.data.etat.assets||{}).map(v=>v.slice(0,7)):null,blobs:Object.keys(window.__faux.blobs).length,refus:window.__faux.refus.slice()}}""", nom)
            r['projet_avant_octets'] = avant['octets']; r['images_planche'] = avant['images']
            if avec:   # relecture depuis la bibliothèque : l'image revient (data:), décodée
                await pg.evaluate("()=>__plate.nouveau&&__plate.nouveau()"); await pg.wait_for_timeout(300)
                idx = await pg.evaluate("n=>window.__faux.lignes.projets.findIndex(x=>x.data.nom===n)", nom)
                lid = await pg.evaluate("i=>window.__faux.lignes.projets[i].id", idx)
                await pg.click('#lib [data-load="%s"]' % lid); await pg.wait_for_timeout(1200)
                r['relu'] = await pg.evaluate("""()=>{const e=__plate.S.doc.elements.find(x=>x.type==='image');const im=e&&__plate.IMG.get(e.asset);
                  return {images:__plate.S.doc.elements.filter(x=>x.type==='image').length,data:e?String(__plate.S.doc.assets[e.asset]).slice(0,15):null,decodee:im?im.naturalWidth+'x'+im.naturalHeight:null}}""")
                await pg.screenshot(path=os.path.join(OUT, 'integration_v1_db_photo.png'))
            lourd['avec_assets' if avec else 'sans_assets'] = r
        res['db_lourd'] = lourd
        res['db'] = {'bloc_v1': bloc, 'ouvert': ouvert, 'ecritures': await pg.evaluate('window.__faux.ecrits'),
                     'projets': ligne_v1,
                     'lib_v2': await pg.evaluate("document.querySelectorAll('#lib .item').length")}
        await pg.screenshot(path=os.path.join(OUT, 'integration_v1_bibliotheque.png'))
        # --- 4. downloads : export PNG (dialogue) et projet .json ---
        await pg.click('#bExporter'); await pg.wait_for_timeout(300)
        await pg.click('#expGo')
        for i in range(120):
            await pg.wait_for_timeout(250)
            if await pg.evaluate('window.__faux.sauves.length'): break
        await pg.evaluate("()=>document.getElementById('dlgExport').close()")
        await pg.click('#bJsonExport'); await pg.wait_for_timeout(800)
        res['downloads'] = await pg.evaluate('window.__faux.sauves')
        res['erreurs'] = err
        await b.close()
    out = planche(ims, tit, 4, titre='Reprise de la v1 : configurations v1 rouvertes en v2 (même angle)', largeur_case=340)
    out.save(os.path.join(OUT, 'integration_v1.png'))
    json.dump(res, open(os.path.join(OUT, 'integration_v1.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    ok = (all(c['iou_silhouette'] > c['iou_si_retournee'] for c in res['cas_v1']) and not res['erreurs']
          and res['db']['bloc_v1']['lignes'] == 2 and all(e['nom'] != 'configurations' for e in res['db']['ecritures'])
          and len(res['db']['projets']) == 1 and len(res['downloads']) == 2)
    # mouvement v1 signalé à l'ouverture (relecture M5) : v7 et v8 sélectionnent leurs mains et le disent ; v6 non
    J = res['json']
    ok = ok and 'Éclater en étapes' in J['v7']['note'] and J['v8_DG_3_etapes']['selection'] == 2 and '3 étapes' in J['v8_DG_3_etapes']['note'] and J['v6']['note'] == ''
    L = res['db_lourd']; A, B = L['avec_assets'], L['sans_assets']
    ok = ok and (A['enregistre'] and A['octets_ligne'] <= 262144 and A['images_ligne'] == 1 and A['relu']['images'] == 1
                 and A['relu']['data'].startswith('data:image/') and A['relu']['decodee'] == '900x600'
                 and B['enregistre'] and B['octets_ligne'] <= 262144 and B['images_ligne'] == 0 and 'sans ses images' in B['msg']
                 and 'droits' not in A['msg'] + B['msg'] and not A['refus'] and not B['refus'])
    print('REPRISE V1 :', 'OK' if ok else 'ÉCHEC')
    sys.exit(0 if ok else 1)

asyncio.run(main())
