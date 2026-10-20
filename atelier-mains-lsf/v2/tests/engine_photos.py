"""Comparaison avec les photos de l'utilisateur, à l'angle de la photo : photo | rendu du moteur (même pose LSF, même
orientation estimée à l'œil sur la photo). → tests/out/engine_photos.png
Option --essais : pour chaque photo, plusieurs orientations candidates (choix de l'orientation)."""
import asyncio, json, os, sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *
PHOTOS_DIR = PHOTOS

def Q(*rots):
    """rotations successives [(axe, degrés)…] appliquées dans l'ordre (la première d'abord)"""
    q = [0, 0, 0, 1]
    for ax, d in rots: q = q_mul(q_axe(ax, d), q)
    return q
X, Y, Z = [1, 0, 0], [0, 1, 0], [0, 0, 1]
# pince annulaire des photos 2368 / 2369 : index et majeur tendus, pouce en anneau avec l'annulaire (mobilite.md § 3)
PINCE_ANN = {'pouce': {'av': 40, 'rap': 40, 'mcp': 30, 'ip': 25}, 'index': {'ab': 12}, 'majeur': {'ab': -8},
             'annulaire': {'mcp': 60, 'pip': 75, 'dip': 30, 'ab': -5.5}, 'auriculaire': {'mcp': 75, 'pip': 90, 'dip': 50, 'ab': -14}, 'arc': 0.6}
CAS = [
    (2357, 'Poing serré', Q((X, -15), (Z, 22)), 'poing (photo 2357), paume vers l’objectif'),
    (2359, 'V (2)', Q((X, -10), (Z, 12)), 'V (photo 2359)'),
    (2367, 'O', Q((Y, -90), (Z, 30)), 'O (photo 2367)'),
    (2368, 'Pince annulaire', Q((Y, -80), (Z, 30)), 'pince annulaire (photo 2368)'),
    (2369, 'Pince annulaire', Q((X, -30), (Z, 40)), 'pince annulaire (photo 2369)'),
    (2370, 'Quatre (4)', Q((X, -10), (Z, -8)), 'quatre (photo 2370)'),
    (2374, 'Pouce levé', Q((Z, 90), (Y, -30), (X, 45)), 'pouce levé (photo 2374)'),
]
ESSAIS = {
    2374: [Q((Z, 90), (X, 40)), Q((Z, 90), (Y, -30), (X, 45)), Q((Z, 100), (Y, 30), (X, 50)), Q((Z, 90), (X, 65), (Y, -20))],
    2357: [Q((X, -15), (Z, 22)), Q((X, -30), (Z, 20)), Q((X, 10), (Z, 25)), Q((Y, -20), (X, -20), (Z, 20))],
    2359: [Q((X, -10), (Z, 12)), Q((Z, 5)), Q((Y, 20), (Z, 10)), Q((Y, -20), (Z, 10))],
    2367: [Q((Y, -70), (X, -10), (Z, 25)), Q((Y, -90), (Z, 30)), Q((Y, -50), (X, -20), (Z, 20)), Q((Y, -110), (Z, 30))],
    2368: [Q((Y, -60), (Z, 25)), Q((Y, -80), (Z, 30)), Q((Y, -40), (Z, 20)), Q((Y, -60), (X, -20), (Z, 30))],
    2369: [Q((X, -20), (Y, -25), (Z, 35)), Q((Y, -40), (Z, 45)), Q((X, -30), (Z, 40)), Q((Y, -20), (Z, 30))],
    2370: [Q((X, -10), (Z, -8)), Q((Z, -5)), Q((X, -20), (Z, -10)), Q((Y, 15), (Z, -8))],
}

async def main():
    essais = '--essais' in sys.argv
    manquent = [n for n, *_ in CAS if not os.path.isfile(os.path.join(PHOTOS_DIR, 'IMG_%d_small.jpg' % n))]
    if manquent:
        print('Photos absentes de %s (%s) : comparaison sautée. Donner le dossier par ATELIER_PHOTOS=…' % (PHOTOS_DIR, ', '.join(map(str, manquent))))
        return
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, PAGE)
        presets = await pg.evaluate("AtelierHand.presets")
        tuiles = []
        H = 520
        for num_, pose, q, lg in CAS:
            ph = Image.open(os.path.join(PHOTOS_DIR, 'IMG_%d_small.jpg' % num_)).convert('RGB')
            ph = ph.resize((round(ph.width * H / ph.height), H))
            pz = presets[pose] if isinstance(pose, str) else pose
            if essais and len(sys.argv) > 2 and str(num_) not in sys.argv[2:]: continue
            qs = ESSAIS[num_] if essais else [q]
            rend = []
            for qq in qs:
                o = {'pose': pz, 'orientation': qq, 'style': {'largeurTrait': 0.8}}
                bd = await pg.evaluate("o=>AtelierHand.bounds(o)", o)
                s = H * 0.9 / max(bd['w'], bd['h']); o['w'] = round(bd['w'] * s); o['h'] = round(bd['h'] * s)
                im = sur_blanc(await rendu(pg, o))
                cell = Image.new('RGB', (H, H), 'white'); cell.paste(im, ((H - im.width) // 2, (H - im.height) // 2)); rend.append(cell)
            ligne = Image.new('RGB', (ph.width + H * len(rend), H), 'white'); ligne.paste(ph, (0, 0))
            for i, c in enumerate(rend): ligne.paste(c, (ph.width + i * H, 0))
            tuiles.append((ligne, lg + (' — orientations candidates' if essais else ' | rendu du moteur, même angle')))
        planche(tuiles, 1 if essais else 2, 'photos de l’utilisateur et rendu du moteur').save(os.path.join(OUT, 'engine_photos_essais.png' if essais else 'engine_photos.png'))
        print('erreurs', [e for e in err if 'GPU stall' not in e][:5])
        await b.close()
asyncio.run(main())
