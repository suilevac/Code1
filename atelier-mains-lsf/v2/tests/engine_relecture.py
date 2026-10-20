"""Les cas de la relecture adverse du 19 octobre, rejoués après correction (une image par défaut, et ses chiffres) :
  1. grand rendu par tuiles (V (2) dos ¾ à 2600 px) : traînée → aucune encre hors de la main ;
  2. vues « dessus » et « dessous » (B, Main ouverte, V (2), Pince, Poing serré) : anneaux doublés, échardes, gant vide ;
  3. poing : presets (MCP des quatre doigts) et fermeture par solve() depuis la main ouverte ;
  4. tunnel du poing vu de profil (Poing serré, 900 px) ;
  5. dos de la main (Poing serré, Main plate (B), Main ouverte en dos et dos ¾) ;
  6. Clé (paume, profil, dessus) ;
  7. styles : couleur illisible → vert par défaut ; IPD / IPP (constrain et préférence de geste).
→ tests/out/engine_relecture_<n>.png et engine_relecture.json"""
import asyncio, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine_commun import *
from engine_traits import defauts

VUES['dos34'] = q_mul(q_axe([1, 0, 0], -20), q_axe([0, 1, 0], 145))
VUES['paume34'] = q_mul(q_axe([1, 0, 0], 12), q_axe([0, 1, 0], -30))
FIST = "{index:{mcp:90,pip:105,dip:70,ab:4},majeur:{mcp:90,pip:105,dip:70,ab:0},annulaire:{mcp:90,pip:105,dip:70,ab:-5.5},auriculaire:{mcp:90,pip:105,dip:70,ab:-14}}"

async def main():
    rap = {}
    async with async_playwright() as p:
        b, pg, err = await ouvrir(p, PAGE)
        pr = await pg.evaluate("AtelierHand.presets")
        R = lambda o: rendu(pg, o)
        # 1. tuiles
        big = await R({'pose': pr['V (2)'], 'orientation': VUES['dos34'], 'w': 2600, 'h': 2600})
        ref = await R({'pose': pr['V (2)'], 'orientation': VUES['dos34'], 'w': 1300, 'h': 1300})
        refg = np.asarray(ref.resize(big.size, Image.NEAREST))[..., 3] > 0
        hors = int(((np.asarray(big)[..., 3] > 0) & ~ndimage.binary_dilation(refg, iterations=10)).sum())
        rap['1_tuiles'] = {'encre_hors_main': hors, 'ms': round(big.info['t'])}
        bg = sur_blanc(big)
        planche([(bg.resize((650, 650), Image.LANCZOS), 'V (2) dos ¾ à 2600 px (4 tuiles), réduit'),
                 (bg.crop((300, 2100, 2100, 2500)).resize((900, 200), Image.LANCZOS), 'bas de l’image (là où passait la traînée)')], 2,
                'Relecture 1 — grand rendu par tuiles : encre hors de la main = %d px' % hors).save(os.path.join(OUT, 'engine_relecture_1_tuiles.png'))
        # 2. dessus / dessous
        tu = []; df = {}
        for n in ['Main plate (B)', 'Main ouverte (5)', 'V (2)', 'Pince', 'Poing serré']:
            for v in ['dessus', 'dessous']:
                o = {'pose': pr[n], 'orientation': VUES[v], 'style': {'largeurTrait': 0.8}}
                bd = await pg.evaluate("o=>AtelierHand.bounds(o)", o); o['w'] = round(bd['w'] * 30); o['h'] = round(bd['h'] * 30)
                im = await R(o); d = defauts(await R(dict(o, style={'largeurTrait': 0.8, 'plis': False})))
                df['%s %s' % (n, v)] = [len(d['fragments']), len(d['echardes'])]
                cell = Image.new('RGBA', (560, 560), (255, 255, 255, 255)); cell.alpha_composite(im, ((560 - im.width) // 2, (560 - im.height) // 2))
                tu.append((cell.convert('RGB'), '%s · %s · F %d · E %d' % (n, v, len(d['fragments']), len(d['echardes']))))
        rap['2_dessus_dessous_fragments_echardes'] = df
        planche(tu, 4, 'Relecture 2 — vues « dessus » (bouts vers l’œil) et « dessous » (poignet vers l’œil), 30 px/cm').save(os.path.join(OUT, 'engine_relecture_2_dessus_dessous.png'))
        o = {'pose': pr['Main ouverte (5)'], 'orientation': VUES['dessus'], 'w': 900, 'h': 900}
        z = sur_blanc(await R(o)); z.crop((135, 270, 630, 540)).resize((990, 540), Image.LANCZOS).save(os.path.join(OUT, 'engine_relecture_2b_dessus_zoom.png'))
        # 3. poing
        r3 = await pg.evaluate("""(F)=>{const H=AtelierHand,f=p=>['index','majeur','annulaire','auriculaire'].map(k=>Math.round(p[k].mcp)).join('/'),o={};
          for(const n of ['Poing (A)','Poing serré','Lettre S','Pouce levé','Poing pouce dedans','Y','Lettre I','Lettre A']) o[n]=f(H.presets[n]);
          const fist=eval('('+F+')');
          for(const d of ['Main ouverte (5)','Repos','Dessin','L','Main plate (B)','Quatre (4)']){const c=Object.assign(JSON.parse(JSON.stringify(H.presets[d])),JSON.parse(JSON.stringify(fist)));const s=H.solve(H.presets[d],c);o['solve depuis '+d]=f(s)+' (capsules '+(H.penetration(s)*10).toFixed(2)+' mm)'}
          const c=Object.assign(JSON.parse(JSON.stringify(H.presets['Main ouverte (5)'])),fist);window.__poing=H.solve(H.presets['Main ouverte (5)'],c);return o}""", FIST)
        rap['3_poing_MCP'] = r3
        poing = await pg.evaluate("window.__poing")
        tu = []
        for lg, pose, v in [('Poing serré (preset)', pr['Poing serré'], 'paume'), ('Poing serré (preset)', pr['Poing serré'], 'dos34'),
                            ('solve(Main ouverte → poing)', poing, 'paume'), ('solve(Main ouverte → poing)', poing, 'profil')]:
            im = await R({'pose': pose, 'orientation': VUES[v], 'w': 420, 'h': 420}); tu.append((sur_blanc(im), '%s · %s' % (lg, v)))
        planche(tu, 4, 'Relecture 3 — poing : MCP %s (preset) ; solve depuis la main ouverte %s' % (r3['Poing serré'], r3['solve depuis Main ouverte (5)'])).save(os.path.join(OUT, 'engine_relecture_3_poing.png'))
        # 4. tunnel
        im = sur_blanc(await R({'pose': pr['Poing serré'], 'orientation': VUES['profil'], 'w': 900, 'h': 900}))
        planche([(im.resize((450, 450), Image.LANCZOS), 'Poing serré, profil radial (900 px, réduit)'), (im.crop((270, 135, 675, 450)).resize((540, 420), Image.LANCZOS), 'tunnel de l’index (gros plan)')], 2,
                'Relecture 4 — tunnel du poing vu de profil : creux peint dans l’ombre, sans cadre').save(os.path.join(OUT, 'engine_relecture_4_tunnel.png'))
        # 5. dos
        tu = []
        for n in ['Poing serré', 'Main plate (B)', 'Main ouverte (5)']:
            for v in ['dos', 'dos34']:
                im = await R({'pose': pr[n], 'orientation': VUES[v], 'w': 420, 'h': 420}); tu.append((sur_blanc(im), '%s · %s' % (n, v)))
        planche(tu, 6, 'Relecture 5 — dos de la main : sillons entre les têtes (poing), vallées entre les tendons (main étendue)').save(os.path.join(OUT, 'engine_relecture_5_dos.png'))
        # 6. Clé
        tu = []
        for v in ['paume', 'profil', 'paume34', 'dos34']:
            im = await R({'pose': pr['Clé'], 'orientation': VUES[v], 'w': 380, 'h': 380}); tu.append((sur_blanc(im), 'Clé · %s' % v))
        ecart = await pg.evaluate("""()=>{const H=AtelierHand,I=H._interne,p=H.presets['Clé'];const F=I.fk(p);
          const a=I.pulpe(p,'pouce'),c=I.CIBLES['flanc:index_p2'](F);return Math.hypot(a[0]-c[0],a[1]-c[1],a[2]-c[2])}""")
        rap['6_cle_ecart_pulpe_flanc_cm'] = round(ecart, 3)
        planche(tu, 4, 'Relecture 6 — Clé : pulpe du pouce contre le flanc radial de la P2 de l’index (écart %.1f mm)' % (ecart * 10)).save(os.path.join(OUT, 'engine_relecture_6_cle.png'))
        # 7. styles, IPD / IPP
        tu = []
        for st in [{}, {'peau': 'pas une couleur'}, {'peau': '#e05050', 'ongle': '#ffffff', 'trait': '#0000ff'}, {'peau': 'rgb(240,200,40)'}]:
            im = await R({'pose': pr['Pince'], 'orientation': VUES['paume34'], 'w': 300, 'h': 300, 'style': st}); tu.append((sur_blanc(im), json.dumps(st, ensure_ascii=False)[:38]))
            if st.get('peau') == 'pas une couleur':
                a = np.asarray(im).astype(int); m = a[..., 3] > 250; rap['7_couleur_illisible_peau_mediane'] = [int(np.median(a[..., c][m & (a[..., 1] > 120)])) for c in range(3)]
        planche(tu, 4, 'Relecture 7 — styles (une couleur illisible retombe sur le vert INJS)').save(os.path.join(OUT, 'engine_relecture_7_styles.png'))
        rap['7_ipd_ipp'] = await pg.evaluate("""()=>{const H=AtelierHand,I=H._interne,o={};
          for(const [pip,dip] of [[90,0],[90,90],[60,10]]){const c=H.constrain({index:{pip,dip}});const q=I.preferences(H.constrain({index:{pip,dip}}),'index',{index:[false,false,false]},{doigts:['index']});
            o['IPP '+pip+' IPD '+dip]={constrain:Math.round(c.index.dip*10)/10, geste:Math.round(q.index.dip*10)/10, geste_Maj:Math.round(I.preferences(H.constrain({index:{pip,dip}}),'index',null,{maj:true,doigts:['index']}).index.dip*10)/10}}
          return o}""")
        rap['erreurs_js'] = [e for e in err if 'GPU stall' not in e][:10]
        json.dump(rap, open(os.path.join(OUT, 'engine_relecture.json'), 'w'), ensure_ascii=False, indent=1)
        print(json.dumps(rap, ensure_ascii=False, indent=1))
        await b.close()

if __name__ == '__main__':
    asyncio.run(main())
