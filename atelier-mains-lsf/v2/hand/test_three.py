"""Test de chargement de hand_v2.glb dans three.js r128 (GLTFLoader de examples/js du paquet vendu), Chromium
swiftshader via Playwright :  python3 <scratchpad>/run_rendu.py v2/hand/test_three.py
Vérifie : une SkinnedMesh, 20 os aux noms du contrat, nombre de sommets, attribut _REGION ; rend la main au repos et
l'index fléchi de 90° à la MCP (rotation de l'os index_p1 autour de son X local) → checks/e10_three.png ; écrit le
rapport dans work/three.json."""
import asyncio, base64, json, os, sys
ICI = os.path.dirname(os.path.abspath(__file__))
SCRATCH = '/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad'
THREE = os.environ.get('THREE_DIR', SCRATCH + '/vendor/package')
# GLTFLoader r128 vendu DANS le dépôt (vendor/PROVENANCE.txt : three@0.128.0 npm, sha256 5c15967b…) : le paquet
# three.js du scratchpad n'avait que examples/js/controls/
LOADER = os.path.join(ICI, 'vendor', 'GLTFLoader.js')
FICHIERS = {'three.min.js': (os.path.join(THREE, 'build/three.min.js'), 'application/javascript'),
            'GLTFLoader.js': (LOADER, 'application/javascript'),
            'hand_v2.glb': (os.path.join(ICI, 'hand_v2.glb'), 'model/gltf-binary')}
OS = ['poignet', 'mc1', 'pouce_p1', 'pouce_p2', 'mc2', 'index_p1', 'index_p2', 'index_p3', 'mc3', 'majeur_p1', 'majeur_p2',
      'majeur_p3', 'mc4', 'annulaire_p1', 'annulaire_p2', 'annulaire_p3', 'mc5', 'auriculaire_p1', 'auriculaire_p2', 'auriculaire_p3']
PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#fff}</style></head><body>
<canvas id="c" width="1200" height="600"></canvas>
<script src="https://m1.local/three.min.js"></script><script src="https://m1.local/GLTFLoader.js"></script>
<script>
window.rapport = null;
const R = new THREE.WebGLRenderer({canvas: document.getElementById('c'), antialias: true, preserveDrawingBuffer: true});
R.setClearColor(0xffffff, 1);
new THREE.GLTFLoader().load('https://m1.local/hand_v2.glb', (gltf) => {
  let sk = null, nsk = 0; gltf.scene.traverse(o => { if (o.isSkinnedMesh) { sk = o; nsk++; } });
  const g = sk.geometry, reg = g.attributes._region;
  const hist = [0,0,0,0,0]; for (let i = 0; i < reg.count; i++) hist[Math.round(reg.getX(i))]++;
  // couleurs par région (peau verte, ongle clair, frange blanche, repli = peau, palmure = peau)
  const col = new Float32Array(reg.count * 3);
  for (let i = 0; i < reg.count; i++) { const r = Math.round(reg.getX(i));
    const c = (r === 1) ? [0.80, 0.93, 0.91] : (r === 2) ? [1, 1, 1] : [0.0, 0.63, 0.60]; col.set(c, 3 * i); }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  sk.material = new THREE.MeshLambertMaterial({vertexColors: true, skinning: true, morphTargets: true, morphNormals: true});
  const morphs = sk.morphTargetDictionary ? Object.keys(sk.morphTargetDictionary) : [];
  const nMorphPos = g.morphAttributes.position ? g.morphAttributes.position.length : 0;
  const nMorphNrm = g.morphAttributes.normal ? g.morphAttributes.normal.length : 0;
  const scene = new THREE.Scene(); scene.add(gltf.scene);
  scene.add(new THREE.AmbientLight(0xffffff, 0.45)); const d = new THREE.DirectionalLight(0xffffff, 0.75); d.position.set(0.4, 0.6, 1); scene.add(d);
  const cam = new THREE.OrthographicCamera(-11, 11, 11, -11, 0.1, 200);
  const bones = sk.skeleton.bones;
  const idx = sk.skeleton.getBoneByName('index_p1');
  const tip = new THREE.Vector3();
  function vue(x, px, py, pz, ux, uy, uz) { cam.position.set(px, py, pz); cam.up.set(ux, uy, uz); cam.lookAt(1, 8.5, 0); cam.updateMatrixWorld();
    R.setViewport(x, 0, 600, 600); R.setScissor(x, 0, 600, 600); R.setScissorTest(true); R.render(scene, cam); }
  // bout de l'index (os index_p3, extrémité) avant / après
  const p3 = sk.skeleton.getBoneByName('index_p3'); gltf.scene.updateMatrixWorld(true);
  const b0 = new THREE.Vector3(0, 2.07, 0).applyMatrix4(p3.matrixWorld);
  vue(0, 1, 8.5, 60, 0, 1, 0);                          // repos, vue paume (caméra en +Z)
  idx.rotateX(Math.PI / 2); gltf.scene.updateMatrixWorld(true);
  // correctif de la MCP de l'index à 90° : poids 1 (le moteur M2 : poids = clamp(angle / 90, 0, 1))
  if (sk.morphTargetDictionary && 'mcp_index' in sk.morphTargetDictionary) sk.morphTargetInfluences[sk.morphTargetDictionary['mcp_index']] = 1;
  const b1 = new THREE.Vector3(0, 2.07, 0).applyMatrix4(p3.matrixWorld);
  vue(600, 45, 8.5, 25, 0, 1, 0);                       // index fléchi de 90°, vue de 3/4 côté pouce
  // position skinnée d'un sommet de la pulpe de l'index (boneTransform)
  window.rapport = {skinnedMesh: nsk, os: bones.length, noms: bones.map(b => b.name), sommets: g.attributes.position.count,
    triangles: g.index ? g.index.count / 3 : null, attributs: Object.keys(g.attributes), regions: hist,
    bout_index_repos: b0.toArray(), bout_index_flechi: b1.toArray(), revision: THREE.REVISION,
    morphs: morphs, morph_position: nMorphPos, morph_normal: nMorphNrm};
}, undefined, (e) => { window.rapport = {erreur: String(e)}; });
</script></body></html>"""

async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        br = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'])
        pg = await br.new_page(viewport={'width': 1200, 'height': 600})
        msgs = []; pg.on('console', lambda m: msgs.append(m.text)); pg.on('pageerror', lambda e: msgs.append('ERREUR ' + str(e)))
        async def h(route):
            u = route.request.url
            for n, (chem, ct) in FICHIERS.items():
                if u.endswith('/' + n): return await route.fulfill(path=chem, content_type=ct)
            if u.startswith('https://m1.local/'): return await route.fulfill(body=PAGE, content_type='text/html')
            await route.fallback()
        await pg.route('https://m1.local/**', h)
        await pg.goto('https://m1.local/index.html')
        await pg.wait_for_function('window.rapport !== null', timeout=120000)
        rap = await pg.evaluate('window.rapport')
        png = await pg.evaluate("document.getElementById('c').toDataURL('image/png')")
        open(os.path.join(ICI, 'checks', 'e10_three_brut.png'), 'wb').write(base64.b64decode(png.split(',')[1]))
        rap['console'] = msgs[-10:]
        await br.close()
    rap['noms_conformes'] = sorted(rap.get('noms', [])) == sorted(OS)
    json.dump(rap, open(os.path.join(ICI, 'work', 'three.json'), 'w'), indent=1)
    # planche titrée
    sys.path.insert(0, ICI)
    from raster import police
    from PIL import Image, ImageDraw
    im = Image.open(os.path.join(ICI, 'checks', 'e10_three_brut.png')).convert('RGB')
    out = Image.new('RGB', (im.width, im.height + 70), 'white'); out.paste(im, (0, 70)); dr = ImageDraw.Draw(out)
    dr.text((10, 6), 'three.js r%s — GLTFLoader : %d SkinnedMesh, %d os (noms %s), %d sommets, %d triangles, attributs %s' %
            (rap.get('revision'), rap.get('skinnedMesh', 0), rap.get('os', 0), 'conformes' if rap['noms_conformes'] else 'NON conformes',
             rap.get('sommets', 0), rap.get('triangles', 0), ', '.join(rap.get('attributs', []))), fill='black', font=police(14))
    dr.text((10, 48), 'morph targets : %d (POSITION) / %d (NORMAL) : %s' % (rap.get('morph_position', 0), rap.get('morph_normal', 0),
            ', '.join(rap.get('morphs', []))), fill='black', font=police(14))
    dr.text((10, 30), 'gauche : repos, vue paume ; droite : index_p1.rotateX(90°) + correctif mcp_index, vue ¾ côté pouce — bout de l’index '
            '(%.1f, %.1f, %.1f) → (%.1f, %.1f, %.1f) cm' % (*rap.get('bout_index_repos', [0] * 3), *rap.get('bout_index_flechi', [0] * 3)), fill='black', font=police(14))
    out.save(os.path.join(ICI, 'checks', 'e10_three.png')); os.remove(os.path.join(ICI, 'checks', 'e10_three_brut.png'))
    print(json.dumps({k: v for k, v in rap.items() if k != 'noms'}, ensure_ascii=False))

asyncio.run(main())
