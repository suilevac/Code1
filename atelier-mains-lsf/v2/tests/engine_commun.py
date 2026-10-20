"""Outils communs des tests du moteur M2 (v2/engine) : Chromium (swiftshader) piloté par Playwright, fichiers du dépôt
servis sous https://m2.local/ (aucun réseau, aucun CDN), page minimale qui charge three.js r128 vendu, GLTFLoader,
shaders.js, engine.js puis hand_v2.glb + hand_v2.json par URL.
Lancer un test :  python3 <scratchpad>/run_rendu.py v2/tests/engine_<nom>.py"""
import asyncio, base64, io, json, os, sys
from playwright.async_api import async_playwright

ICI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(ICI, '..'))
RACINE = os.path.abspath(os.path.join(V2, '..'))
OUT = os.path.join(ICI, 'out')
# photos de l'utilisateur (IMG_23xx_small.jpg) : hors du dépôt (ce sont SES photos) ; dossier donné par la variable
# d'environnement ATELIER_PHOTOS, sinon le brouillon de travail du chantier ; engine_photos.py s'arrête proprement
# (code 0, message) si le dossier est absent
PHOTOS = os.environ.get('ATELIER_PHOTOS', '/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/photos')
os.makedirs(OUT, exist_ok=True)
TYPES = {'.js': 'application/javascript', '.html': 'text/html', '.json': 'application/json', '.glb': 'model/gltf-binary',
         '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg'}
CARTE = {'three.min.js': os.path.join(V2, 'engine', 'vendor', 'three.min.js'),
         'GLTFLoader.js': os.path.join(V2, 'hand', 'vendor', 'GLTFLoader.js')}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#fff}</style></head><body>
<script src="/engine/vendor/three.min.js"></script><script src="/hand/vendor/GLTFLoader.js"></script>
<script src="/engine/shaders.js"></script><script src="/engine/engine.js"></script>
<script>window.pret=null;AtelierHand.charger('/hand/hand_v2.glb','/hand/hand_v2.json').then(()=>window.pret=true,e=>window.pret=String(e&&e.stack||e));</script>
</body></html>"""


async def ouvrir(p, page_html=None, url='https://m2.local/test.html', vue=(1400, 900), dpr=1):
    b = await p.chromium.launch(args=['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'])
    pg = await b.new_page(viewport={'width': vue[0], 'height': vue[1]}, device_scale_factor=dpr)
    erreurs = []
    pg.on('pageerror', lambda e: erreurs.append('pageerror ' + str(e)))
    pg.on('console', lambda m: erreurs.append(m.text) if m.type in ('error', 'warning') else None)

    async def route(r):
        u = r.request.url.split('?')[0]
        chemin = u.replace('https://m2.local/', '')
        if chemin == 'test.html' and page_html is not None:
            return await r.fulfill(body=page_html, content_type='text/html')
        f = os.path.join(V2, chemin)
        if os.path.isfile(f):
            return await r.fulfill(path=f, content_type=TYPES.get(os.path.splitext(f)[1], 'application/octet-stream'))
        return await r.fulfill(status=404, body='absent : ' + chemin)
    await pg.route('https://m2.local/**', route)
    await pg.goto(url)
    if page_html is not None or url.endswith('test.html'):
        await pg.wait_for_function('window.pret !== null && window.pret !== undefined', timeout=180000)
        etat = await pg.evaluate('window.pret')
        if etat is not True:
            raise RuntimeError('chargement : %s' % etat)
    return b, pg, erreurs


def png(data_url):
    from PIL import Image
    return Image.open(io.BytesIO(base64.b64decode(data_url.split(',', 1)[1])))


# rendu d'une main → image PIL (RGBA) ; o = {pose, cote, orientation, w, h, style}
async def rendu(pg, o):
    r = await pg.evaluate("""o=>{const c=AtelierHand.render(o);return {url:c.toDataURL('image/png'),t:c.dureeRendu}}""", o)
    im = png(r['url']).convert('RGBA'); im.info['t'] = r['t']
    return im


def sur_blanc(im, fond=(255, 255, 255)):
    from PIL import Image
    b = Image.new('RGBA', im.size, fond + (255,)); b.alpha_composite(im); return b.convert('RGB')


def police(t=16):
    from PIL import ImageFont
    for f in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf']:
        if os.path.exists(f): return ImageFont.truetype(f, t)
    return ImageFont.load_default()


def planche(tuiles, cols, titre=None, legende_h=22, fond=(255, 255, 255)):
    """tuiles = [(image PIL, légende)] → une image en grille"""
    from PIL import Image, ImageDraw
    w = max(t[0].width for t in tuiles); h = max(t[0].height for t in tuiles)
    rows = (len(tuiles) + cols - 1) // cols; th = 34 if titre else 0
    c = Image.new('RGB', (cols * w, th + rows * (h + legende_h)), fond); d = ImageDraw.Draw(c); f = police(15)
    if titre: d.text((8, 8), titre, fill=(0, 0, 0), font=police(18))
    for i, (im, lg) in enumerate(tuiles):
        x, y = (i % cols) * w, th + (i // cols) * (h + legende_h)
        c.paste(im.convert('RGB'), (x, y + legende_h)); d.text((x + 6, y + 3), lg, fill=(0, 0, 0), font=f)
    return c


# orientations utiles (quaternions [x, y, z, w]) : la caméra regarde −Z, la paume de la main droite est en +Z
import math
def q_axe(ax, deg):
    s = math.sin(math.radians(deg) / 2); n = math.sqrt(sum(a * a for a in ax))
    return [ax[0] / n * s, ax[1] / n * s, ax[2] / n * s, math.cos(math.radians(deg) / 2)]
def q_mul(a, b):
    return [a[3]*b[0]+a[0]*b[3]+a[1]*b[2]-a[2]*b[1], a[3]*b[1]-a[0]*b[2]+a[1]*b[3]+a[2]*b[0],
            a[3]*b[2]+a[0]*b[1]-a[1]*b[0]+a[2]*b[3], a[3]*b[3]-a[0]*b[0]-a[1]*b[1]-a[2]*b[2]]
VUES = {
    'paume': [0, 0, 0, 1],
    'dos': q_axe([0, 1, 0], 180),
    'profil': q_axe([0, 1, 0], -90),          # côté du pouce (radial) vers la caméra
    'profil_cubital': q_axe([0, 1, 0], 90),   # côté de l'auriculaire
    'dessus': q_axe([1, 0, 0], 90),           # bouts des doigts vers la caméra
    'dessous': q_axe([1, 0, 0], -90),         # poignet vers la caméra
}
