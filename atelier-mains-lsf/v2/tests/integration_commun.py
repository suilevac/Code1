"""Outils communs des tests d'intégration (chantier M5) : la page CONSTRUITE dist/atelier-v2.local.html (v2/build.py), ouverte
en file:// dans Chromium (swiftshader, rendu logiciel : les temps sont pessimistes d'un facteur 3 à 10, outil.md § 4.2).
Aucun réseau, aucun CDN : tout est dans la page.
Lancer :  python3 v2/build.py && python3 <scratchpad>/run_rendu.py v2/tests/integration_<nom>.py"""
import base64, io, json, os, struct, sys, time, zlib
from playwright.async_api import async_playwright

ICI = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.abspath(os.path.join(ICI, '..'))
RACINE = os.path.abspath(os.path.join(V2, '..'))
OUT = os.path.join(ICI, 'out')
os.makedirs(OUT, exist_ok=True)
PAGE = 'file://' + os.path.join(RACINE, 'dist', 'atelier-v2.local.html')
PAGE_V1 = 'file://' + os.path.join(RACINE, 'dist', 'atelier-mains-lsf.local.html')
ARGS = ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader']

# enregistreur d'images : écart entre deux requestAnimationFrame = temps pendant lequel la page ne répond pas
CHRONO = """()=>{if(window.__chrono)return;const c=window.__chrono={t:[],on:false};
  const f=t=>{if(c.on)c.t.push(t);requestAnimationFrame(f)};requestAnimationFrame(f)}"""


async def ouvrir(p, vue=(1500, 950), dpr=1, page=PAGE, attendre=True):
    b = await p.chromium.launch(args=ARGS)
    ctx = await b.new_context(viewport={'width': vue[0], 'height': vue[1]}, device_scale_factor=dpr, accept_downloads=True)
    pg = await ctx.new_page()
    erreurs = []
    pg.on('pageerror', lambda e: erreurs.append('pageerror ' + str(e)))
    # les messages « GPU stall due to ReadPixels » sont des avertissements du pilote logiciel, pas des erreurs de la page
    pg.on('console', lambda m: erreurs.append(m.type + ' ' + m.text) if m.type == 'error' else None)
    t0 = time.time()
    await pg.goto(page)
    if attendre:
        await pg.evaluate('()=>AtelierHand.ready')
    return b, pg, erreurs, time.time() - t0


async def chrono_debut(pg):
    await pg.evaluate(CHRONO)
    await pg.evaluate('()=>{__chrono.t=[];__chrono.on=true}')


async def chrono_fin(pg):
    """→ {images, max_ms, p95_ms} : la plus longue image = le plus long gel de l'interface pendant la fenêtre."""
    t = await pg.evaluate('()=>{__chrono.on=false;return __chrono.t}')
    d = sorted(b - a for a, b in zip(t, t[1:]))
    if not d:
        return {'images': 0, 'max_ms': None, 'p95_ms': None}
    return {'images': len(d), 'max_ms': round(d[-1]), 'p95_ms': round(d[int(0.95 * (len(d) - 1))])}


def png_pil(data):
    from PIL import Image
    if isinstance(data, str):
        data = base64.b64decode(data.split(',', 1)[1])
    return Image.open(io.BytesIO(data))


def chunks_png(octets):
    """Liste (type, données) des chunks d'un PNG."""
    assert octets[:8] == b'\x89PNG\r\n\x1a\n', 'pas un PNG'
    i, L = 8, []
    while i < len(octets):
        n = struct.unpack('>I', octets[i:i + 4])[0]
        t = octets[i + 4:i + 8].decode('latin-1')
        L.append((t, octets[i + 8:i + 8 + n]))
        i += 12 + n
    return L


def itxt(octets, cle='atelier-mains-lsf'):
    """Texte du chunk iTXt `cle` (JSON du projet embarqué), ou None."""
    for t, d in chunks_png(octets):
        if t == 'iTXt' and d.split(b'\0', 1)[0].decode('latin-1') == cle:
            k, reste = d.split(b'\0', 1)
            comp, meth = reste[0], reste[1]
            reste = reste[2:]
            lang, reste = reste.split(b'\0', 1)
            trad, txt = reste.split(b'\0', 1)
            return (zlib.decompress(txt) if comp else txt).decode('utf-8')
    return None


async def blob_octets(pg, expr):
    """Évalue `expr` (une promesse de Blob) dans la page → octets."""
    b64 = await pg.evaluate("""async()=>{const b=await (%s);const u=new Uint8Array(await b.arrayBuffer());let s='';
      for(let i=0;i<u.length;i+=32768)s+=String.fromCharCode.apply(null,u.subarray(i,i+32768));return btoa(s)}""" % expr)
    return base64.b64decode(b64)


def planche(images, titres, colonnes, fond=(255, 255, 255), titre=None, largeur_case=None):
    """Assemble des images PIL en une planche annotée (titres sous chaque case)."""
    from PIL import Image, ImageDraw, ImageFont
    try:
        police = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
        grande = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 26)
    except OSError:
        police = grande = ImageFont.load_default()
    wc = largeur_case or max(im.width for im in images)
    ims = []
    for im in images:
        im = im.convert('RGBA')
        if im.width != wc:
            im = im.resize((wc, max(1, round(im.height * wc / im.width))), Image.LANCZOS)
        ims.append(im)
    lignes = [ims[i:i + colonnes] for i in range(0, len(ims), colonnes)]
    hl = [max(im.height for im in l) + 34 for l in lignes]
    ht = 50 if titre else 0
    out = Image.new('RGB', (colonnes * (wc + 16) + 16, sum(hl) + ht + 16 * len(lignes) + 16), fond)
    d = ImageDraw.Draw(out)
    if titre:
        d.text((16, 12), titre, fill=(20, 32, 31), font=grande)
    y = ht + 16
    k = 0
    for l, h in zip(lignes, hl):
        for j, im in enumerate(l):
            x = 16 + j * (wc + 16)
            out.paste(im, (x, y), im)
            d.text((x, y + h - 30), titres[k], fill=(20, 32, 31), font=police)
            k += 1
        y += h + 16
    return out
