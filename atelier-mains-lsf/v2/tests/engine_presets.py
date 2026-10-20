"""Presets : chaque preset (pose RÉSOLUE exposée par l'API) rendu dans deux vues, sa pénétration mesurée sur la peau
(build_hand.penetration de M1) et sur les capsules ; écrit tests/out/engine_presets_<page>.png et engine_presets.json.
Option --reach : règle le pouce des presets à cible (pulpe sur la cible) et imprime les valeurs à recopier."""
import asyncio, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *
from engine_contacts import maillage, mesurer, bh

VUES['dos34'] = q_mul(q_axe([1, 0, 0], -20), q_axe([0, 1, 0], 145))
VUES['paume34'] = q_mul(q_axe([1, 0, 0], 12), q_axe([0, 1, 0], -30))
TH4 = ['av', 'rap', 'mcp', 'ip']
IDX = TH4 + [['index', 'mcp'], ['index', 'pip'], ['index', 'dip']]
MAJ = TH4 + [['majeur', 'mcp'], ['majeur', 'pip'], ['majeur', 'dip']]
BEC = TH4 + [['index', 'mcp'], ['majeur', 'mcp'], ['annulaire', 'mcp'], ['auriculaire', 'mcp']]
AP = '\u2019'
REACH = {'O': ('pulpe:index', IDX), 'Pince': ('pulpe:index', IDX), 'Pince ronde (F)': ('pulpe:index', IDX), 'Pince fermée': ('pulpe:index', IDX),
         'Bec d' + AP + 'oiseau fermé': ('pulpe:index', IDX), 'Bec d' + AP + 'oiseau rond': ('pulpe:index', IDX), 'Bec de canard fermé': ('pulpes:bec', BEC),
         'Bec d' + AP + 'oie fermé': ('pulpes:bec', TH4 + [['index', 'mcp'], ['majeur', 'mcp']]), 'Lettre D': ('pulpes:D', TH4 + [[k, c] for k in ['majeur', 'annulaire', 'auriculaire'] for c in ['mcp', 'pip']]),
         'Majeur pouce': ('pulpe:majeur', MAJ), 'Lettre H': ('pulpe:majeur', MAJ), 'Lettre T': ('P2:index', TH4),
         'Poing serré': ('P2:index+majeur', TH4), 'Pince annulaire': ('pulpe:annulaire', TH4 + [['annulaire', c] for c in ['mcp', 'pip', 'dip']]),
         'Quatre (4)': ('P2:annulaire+auriculaire', TH4), 'V (2)': ('P2:annulaire+auriculaire', TH4), 'Index (1)': ('P2:majeur+annulaire', TH4),
         'Clé': ('flanc:index_p2', TH4)}

async def main():
    reach = '--reach' in sys.argv
    filtre = [a for a in sys.argv[1:] if not a.startswith('--')]
    T, W = maillage(); g = bh.groupes_contact(W)
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, PAGE)
        if reach:
            for nom, (cible, champs) in REACH.items():
                if filtre and not any(f in nom for f in filtre): continue
                r = await pg.evaluate("""([nom,cible,champs])=>{const H=AtelierHand,I=H._interne,p=H.presets[nom];
                  const r=H.reach(p,I.CIBLES[cible],champs);const s=H.solve(p,r.pose);
                  const ar=x=>Math.round(x*10)/10,f=o=>Object.fromEntries(Object.entries(o).map(([k,v])=>[k,ar(v)]));
                  const doigts={};['index','majeur','annulaire','auriculaire'].forEach(k=>{if(JSON.stringify(f(p[k]))!==JSON.stringify(f(r.pose[k])))doigts[k]=f(r.pose[k])});
                  return {avant:f(p.pouce),apres:f(r.pose.pouce),doigts,ecart:r.ecart,pen:H.penetration(s)}}""", [nom, cible, champs])
                print('%-24s %s -> %s %s écart %.2f cm pen %.2f mm' % (nom, json.dumps(r['avant']), json.dumps(r['apres']), json.dumps(r['doigts']), r['ecart'], r['pen'] * 10))
            await b.close(); return
        noms = await pg.evaluate("Object.keys(AtelierHand.presets)")
        if filtre: noms = [n for n in noms if any(f in n for f in filtre)]
        presets = await pg.evaluate("Object.fromEntries(Object.entries(AtelierHand.presets))")
        res = await mesurer(pg, {n: presets[n] for n in noms}, T, g)
        rapport = {}
        tuiles = []
        for n in noms:
            pen, pire, m = res[n]
            rapport[n] = {'pose': presets[n], 'peau_mm': round(pire[1] * 10, 2), 'paire_peau': '/'.join(pire[0]),
                          'capsules_mm': round(pen['profondeur'] * 10, 2), 'paire_capsules': pen['paire']}
            for v in ['paume34', 'dos34']:
                im = await rendu(pg, {'pose': presets[n], 'cote': 'D', 'orientation': VUES[v], 'w': 300, 'h': 300, 'style': {'largeurTrait': 0.8}})
                tuiles.append((sur_blanc(im), '%s (%s) %.1f mm' % (n, v[:4], pire[1] * 10)))
        par_page = 40
        for i in range(0, len(tuiles), par_page):
            planche(tuiles[i:i + par_page], 8, 'presets (pose résolue), pénétration mesurée sur la peau').save(os.path.join(OUT, 'engine_presets_%d.png' % (i // par_page + 1)))
        # propositions « à valider » (chiffres 6–10, hors des presets : CLAUDE.md « Chiffres ») : mesurées aussi
        av = await pg.evaluate("Object.fromEntries(Object.entries(AtelierHand.presetsAValider))")
        if av and not filtre:
            resv = await mesurer(pg, av, T, g)
            rapport['_a_valider'] = {n: {'peau_mm': round(resv[n][1][1] * 10, 2), 'capsules_mm': round(resv[n][0]['profondeur'] * 10, 2)} for n in av}
            print('à valider :', {n: v['peau_mm'] for n, v in rapport['_a_valider'].items()})
        if not filtre:
            json.dump(rapport, open(os.path.join(OUT, 'engine_presets.json'), 'w'), ensure_ascii=False, indent=1)
        vrais = {n: r for n, r in rapport.items() if not n.startswith('_')}
        pires = sorted(vrais.items(), key=lambda kv: -kv[1]['peau_mm'])[:12]
        for n, r in pires: print('%-26s peau %.2f mm (%s)  capsules %.2f (%s)' % (n, r['peau_mm'], r['paire_peau'], r['capsules_mm'], r['paire_capsules']))
        print('max peau %.2f mm sur %d presets' % (max(r['peau_mm'] for r in vrais.values()), len(vrais)))
        print('erreurs', [e for e in err if 'GPU stall' not in e][:5])
        await b.close()
asyncio.run(main())
