"""Le skinning du moteur (JS, quaternions duaux + correctifs) contre celui de M1 (build_hand.py poser_v2, numpy) sur des
poses où les deux conventions coïncident (pouce à 0 : la pronation couplée et l'axe décalé sont propres à M2 ; prono
à 0 ; ab du moteur = ab de M1 + éventail de liaison). Écart attendu : arrondi float32."""
import asyncio, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *
sys.path.insert(0, os.path.join(V2, 'hand'))
import build_hand as bh
from glb import lire   # v2/tests/glb.py (dans le dépôt)

POSES_M1 = [
    {'index': {'mcp': 90, 'pip': 100, 'dip': 60, 'ab': -3}, 'majeur': {'mcp': 60, 'pip': 30}, 'annulaire': {'mcp': 20, 'pip': 80, 'dip': 40, 'ab': 4},
     'auriculaire': {'mcp': 95, 'pip': 105, 'dip': 70}, 'poignet': {'flex': 30, 'dev': -10}, 'arc': 0.7},
    {'index': {'mcp': -20, 'ab': 10}, 'auriculaire': {'mcp': 45, 'pip': 45, 'dip': 20, 'ab': -10}, 'poignet': {'flex': -40, 'dev': 15}, 'arc': 0.3},   # arc = l'arc automatique du moteur (0,6 × 45/90)
]
EV = {'index': 4.0, 'majeur': 0.0, 'annulaire': -5.5, 'auriculaire': -14.0}

async def main():
    J, acc = lire(os.path.join(V2, 'hand', 'hand_v2.glb'))
    pr = J['meshes'][0]['primitives'][0]['attributes']
    V = acc(pr['POSITION']).astype(float); T = acc(J['meshes'][0]['primitives'][0]['indices']).reshape(-1, 3)
    jn = acc(pr['JOINTS_0']).astype(int); wt = acc(pr['WEIGHTS_0']).astype(float)
    noms = [J['nodes'][j]['name'] for j in J['skins'][0]['joints']]
    W = np.zeros((len(V), 20))
    for c in range(4): np.add.at(W, (np.arange(len(V)), [bh.OSI[noms[j]] for j in jn[:, c]]), wt[:, c])
    js = json.load(open(os.path.join(V2, 'hand', 'hand_v2.json')))
    sq = {'C': {b: np.array(js['os'][b]['centre']) for b in bh.OS},
          'A': {b: np.stack([js['os'][b]['axes'][a] for a in 'xyz'], 1) for b in bh.OS}}
    # correctifs de M1 relus dans le GLB (déplacements de liaison)
    cor = {}
    for i, nom in enumerate(J['meshes'][0]['extras']['targetNames']):
        cor[nom] = acc(J['meshes'][0]['primitives'][0]['targets'][i]['POSITION']).astype(float)
    corr = {'%s_%s' % (a, k): cor['%s_%s' % (a, k)] for a in ['mcp', 'pip'] for k in bh.DOIGTS}
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, PAGE)
        for pm in POSES_M1:
            pj = json.loads(json.dumps(pm))
            for k in bh.DOIGTS:
                if k in pj: pj[k]['ab'] = pj[k].get('ab', 0) + EV[k]
                else: pj[k] = {'ab': EV[k]}
            P = await pg.evaluate("""p=>{const A=AtelierHand._interne.assets(),P=new Float32Array(3*A.n),N=new Float32Array(3*A.n);
               AtelierHand._interne.skin(p,P,N);return Array.from(P)}""", pj)
            P = np.array(P).reshape(-1, 3)
            # M1 : correctifs (poids clamp(θ/θref)) puis DQS
            D = 0
            for a, ref in [('mcp', 90.0), ('pip', 100.0)]:
                for k in bh.DOIGTS:
                    D = D + float(np.clip(pm.get(k, {}).get(a, 0) / ref, 0, 1)) * corr['%s_%s' % (a, k)]
            Q = bh.poser(V + D, W, sq, pm, 'dqs')
            e = np.linalg.norm(P - Q, axis=1)
            print('pose', json.dumps(pm)[:60], '… écart max %.5f cm, moyen %.6f cm, 99e centile %.5f' % (e.max(), e.mean(), np.percentile(e, 99)))
        await b.close()
asyncio.run(main())
