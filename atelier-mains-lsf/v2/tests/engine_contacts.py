"""Contacts : la pénétration des capsules du moteur (rapide, pour le solveur) contre la mesure sur la PEAU de M1
(build_hand.penetration : sommet sous la surface de l'autre partie, normales opposées), sur des poses de contrôle.
Usage : engine_contacts.py [poses.json]   (défaut : poses de contrôle de M1 + quelques presets v1 bruts)"""
import asyncio, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *
sys.path.insert(0, os.path.join(V2, 'hand'))
import build_hand as bh
from glb import lire   # v2/tests/glb.py (dans le dépôt)

def maillage():
    J, acc = lire(os.path.join(V2, 'hand', 'hand_v2.glb'))
    pr = J['meshes'][0]['primitives'][0]
    T = acc(pr['indices']).reshape(-1, 3).astype(np.int64)
    jn = acc(pr['attributes']['JOINTS_0']).astype(int); wt = acc(pr['attributes']['WEIGHTS_0']).astype(float)
    noms = [J['nodes'][j]['name'] for j in J['skins'][0]['joints']]
    W = np.zeros((len(jn), 20))
    for c in range(4): np.add.at(W, (np.arange(len(jn)), [bh.OSI[noms[j]] for j in jn[:, c]]), wt[:, c])
    return T, W

async def mesurer(pg, poses, T, g):
    out = {}
    for nom, pose in poses.items():
        r = await pg.evaluate("""p=>{const A=AtelierHand._interne.assets(),P=new Float32Array(3*A.n),N=new Float32Array(3*A.n);
           const q=AtelierHand.constrain(p,{passif:true});AtelierHand._interne.skin(q,P,N);return {P:Array.from(P),pen:AtelierHand.penetration(q,true)}}""", pose)
        P = np.array(r['P']).reshape(-1, 3)
        m = bh.penetration(P, T, g)
        pire = max(m.items(), key=lambda kv: kv[1])
        out[nom] = (r['pen'], pire, m)
    return out

if __name__ == '__main__':
    async def main():
        T, W = maillage(); g = bh.groupes_contact(W)
        js = json.load(open(os.path.join(V2, 'hand', 'hand_v2.json')))
        EV = {'index': 4.0, 'majeur': 0.0, 'annulaire': -5.5, 'auriculaire': -14.0}
        def depuis_m1(p):
            p = json.loads(json.dumps(p))
            for k in EV:
                p.setdefault(k, {}); p[k]['ab'] = p[k].get('ab', 0) + EV[k]
            return p
        if len(sys.argv) > 1: poses = json.load(open(sys.argv[1]))
        else:
            F = lambda m, p, d, a=0: {'mcp': m, 'pip': p, 'dip': d, 'ab': a}
            poing = F(90, 105, 70)
            poses = {'M1 poing': depuis_m1(js['poses_controle']['poing']), 'M1 V': depuis_m1(js['poses_controle']['V']),
                     'v1 Poing serré': {'index': poing, 'majeur': poing, 'annulaire': poing, 'auriculaire': poing, 'pouce': {'av': 24, 'rap': 10, 'mcp': 35, 'ip': 60}},
                     'v1 Index (1)': {'index': F(0, 0, 0), 'majeur': poing, 'annulaire': poing, 'auriculaire': poing, 'pouce': {'av': 40, 'rap': 35, 'mcp': 40, 'ip': 40}},
                     'v1 B': {'index': F(0, 0, 0, -6), 'majeur': F(0, 0, 0), 'annulaire': F(0, 0, 0, 6), 'auriculaire': F(0, 0, 0, 9), 'pouce': {'av': 20, 'rap': 35, 'mcp': 30, 'ip': 10}},
                     'v1 O': {'index': F(55, 60, 40, -2), 'majeur': F(58, 62, 42), 'annulaire': F(60, 64, 42, 2), 'auriculaire': F(62, 66, 44, 4), 'pouce': {'av': 45, 'rap': 30, 'mcp': 25, 'ip': 30}},
                     'v1 Pince': {'index': F(45, 55, 35), 'majeur': F(0, 0, 0), 'annulaire': F(0, 0, 0, 6), 'auriculaire': F(0, 0, 0, 9), 'pouce': {'av': 45, 'rap': 20, 'mcp': 20, 'ip': 20}},
                     'repos': {}}
        async with async_playwright() as p:
            b, pg, err = await ouvrir(p, PAGE)
            res = await mesurer(pg, poses, T, g)
            for nom, (pen, pire, m) in res.items():
                print('%-16s capsules %5.2f mm (%s) [%s] | peau M1 %5.2f mm (%s) | %s' % (nom, pen['profondeur'] * 10, pen['paire'], ', '.join('%s %.1f' % (k, v * 10) for k, v in pen['paires'].items() if v > 0.03), pire[1] * 10, '/'.join(pire[0]),
                      ', '.join('%s/%s %.1f' % (a, b2, v * 10) for (a, b2), v in m.items() if v > 0.03)))
            await b.close()
    asyncio.run(main())
