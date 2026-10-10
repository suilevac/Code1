"""Rendus de contrôle sans navigateur visible (Playwright + Chromium en WebGL logiciel).

  pip install playwright && playwright install chromium
  python3 tests/rendu.py                 -> tests/out/*.png + planche tests/out/planche.png

Chaque cas = (configuration de départ OU réglages d'articulations, position caméra, cible caméra).
La ligne affichée donne 'pen' (interpénétration résiduelle, doit rester ≤ 0,5) et les angles posés.
"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = 'file://' + os.path.join(ROOT, 'dist', 'atelier-mains-lsf.local.html')
OUT = os.path.join(ROOT, 'tests', 'out'); os.makedirs(OUT, exist_ok=True)

FIST = {"mcp": 90, "pip": 105, "dip": 70, "ab": 0}
CASES = [
    ("Dessin", [0, 0, 52], [0, 0, 0]),                       # repos = dessin paume exact
    ("Dessin", [0, 0, -52], [0, 0, 0]),                      # repos = dessin dos exact
    ({"majeur": {"ab": 0}, "index": FIST, "annulaire": FIST, "auriculaire": FIST,
      "pouce": {"av": 40, "rap": 30, "mcp": 40, "ip": 40}}, [0, 0, 52], [0, 0, 0]),   # majeur levé
    ("Poing serré", [34, 14, 38], [0, 0, 0]),
    ("Pince", [20, 8, 22], [2, 5, 0]),
    ("Repos", [-8, 16, -14], [1, 10, 0]),                    # gros plan dos / ongles
]
ST = """()=>{const A=window.__atelier,f=A.S.pose.f,r=o=>Object.values(o).map(Math.round).join('/');
 return 'pen '+A.penetration(f).toFixed(1)+' | '+['pouce','index','majeur','annulaire','auriculaire'].map(k=>k.slice(0,3)+':'+r(f[k])).join(' ')}"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={'width': 1300, 'height': 820})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(PAGE); await pg.wait_for_timeout(7000)
        shots = []
        for i, (act, cam, tgt) in enumerate(CASES):
            if isinstance(act, str):
                await pg.evaluate("n=>{const A=window.__atelier;A.S.pose.f=JSON.parse(JSON.stringify(A.PRESETS['Dessin'].f));A.applyPreset(n)}", act)
            else:
                await pg.evaluate("""([patch])=>{const A=window.__atelier,p=A.S.pose;p.f=JSON.parse(JSON.stringify(A.PRESETS['Dessin'].f));
                  const t=JSON.parse(JSON.stringify(p.f));for(const k in patch)Object.assign(t[k],patch[k]);A.constrain({f:t});p.f=A.solve(p.f,t);A.refresh()}""", [act])
            await pg.evaluate("([c,t])=>{const A=window.__atelier;A.camera.position.set(...c);A.camera.lookAt(...t)}", [cam, tgt])
            await pg.wait_for_timeout(700)
            print(i, await pg.evaluate(ST))
            f = os.path.join(OUT, f'cas_{i}.png'); shots.append(f)
            await pg.screenshot(path=f, clip={'x': 16, 'y': 66, 'width': 878, 'height': 737})
        print('erreurs JS :', errs or 'aucune')
        await b.close()
    try:
        from PIL import Image
        ims = [Image.open(f) for f in shots]; w, h = ims[0].size
        c = Image.new('RGB', (w * 3, h * ((len(ims) + 2) // 3)), 'white')
        for i, im in enumerate(ims): c.paste(im, ((i % 3) * w, (i // 3) * h))
        c.thumbnail((1800, 1200)); c.save(os.path.join(OUT, 'planche.png'))
    except ImportError:
        pass

asyncio.run(main())
