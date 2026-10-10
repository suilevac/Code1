"""Balayage anti-déformation (piste D).

Parcourt un grand nombre de poses — chaque articulation seule à plusieurs angles, combinaisons deux à deux,
poses extrêmes, les configurations de PRESETS — et MESURE sur le maillage de peau, pour chacune :
  replis     arêtes dont les deux faces voisines se font face (dièdre signé < -140° : la peau se replie sur elle-même) ;
  cassures   arêtes dont le dièdre a changé de plus de 100° depuis le repos (la peau se froisse) ;
  pincés     triangles dont l'aire tombe sous 12 % de son aire au repos (peau pincée) ;
  gonflés    triangles dont l'aire dépasse 320 % de son aire au repos (peau étirée en voile) ;
  os %       plus grande variation de longueur d'une phalange (le squelette ne doit pas s'allonger) ;
  épais %    plus grande variation d'épaisseur locale d'un doigt (boudin / pincement), mesurée sur les
             anneaux de peau de chaque phalange : rayon moyen de l'anneau rapporté à sa valeur au repos.
Sort un tableau des pires poses (format TSV) et, avec --images, les rend en PNG pour les regarder.

  python3 tests/balayage.py [--images N] [--out dossier] [--poses N]
"""
import asyncio, os, sys, json, argparse
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VEND = os.environ.get('ATELIER_VENDOR', '/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/vendor/package')

# ---- mesures faites dans la page (le maillage n'est accessible que là) --------------------------------
MESURE = r"""
(poses)=>{
 const A=window.__atelier,TH=THREE,h=A.main,MN=A.MN,NT=A.NT,SC=A.SC;
 const g=h.skin.g,idx=A.MINDEX.array,pos=g.attributes.position.array;
 // --- repos : aires, normales, longueurs d'os, anneaux de peau ---
 const dessin=JSON.parse(JSON.stringify(A.PRESETS['Dessin'].f));
 const poser=f=>{h.skin.key='';A.applyPose(h,{f,q:[0,0,0,1],pos:[0,0,0]});};
 const triN=(out)=>{for(let t=0;t<NT;t++){const a=3*idx[3*t],b=3*idx[3*t+1],c=3*idx[3*t+2];
   const ux=pos[b]-pos[a],uy=pos[b+1]-pos[a+1],uz=pos[b+2]-pos[a+2];
   const vx=pos[c]-pos[a],vy=pos[c+1]-pos[a+1],vz=pos[c+2]-pos[a+2];
   out[3*t]=uy*vz-uz*vy;out[3*t+1]=uz*vx-ux*vz;out[3*t+2]=ux*vy-uy*vx;}};
 poser(dessin);
 const N0=new Float32Array(3*NT);triN(N0);
 const S0=new Float32Array(NT);for(let t=0;t<NT;t++)S0[t]=Math.hypot(N0[3*t],N0[3*t+1],N0[3*t+2]);
 // arêtes intérieures : pour chaque arête, les deux triangles voisins et les deux sommets de l'arête
 const em=new Map(),E=[];
 for(let t=0;t<NT;t++)for(let e=0;e<3;e++){const a=idx[3*t+e],b=idx[3*t+(e+1)%3],k=a<b?a*100003+b:b*100003+a;
   const o=em.get(k);if(o===undefined)em.set(k,[t,a,b]);else E.push(o[0],t,o[1],o[2]);}
 const NE=E.length/4;
 // dièdre signé d'une arête : >0 convexe (normales sortantes d'une surface fermée)
 const diedre=(N,e)=>{const a=3*E[4*e],b=3*E[4*e+1],p=3*E[4*e+2],q=3*E[4*e+3];
   const na=Math.hypot(N[a],N[a+1],N[a+2]),nb=Math.hypot(N[b],N[b+1],N[b+2]);if(na<1e-12||nb<1e-12)return 0;
   const ax=N[a]/na,ay=N[a+1]/na,az=N[a+2]/na,bx=N[b]/nb,by=N[b+1]/nb,bz=N[b+2]/nb;
   let ex=pos[q]-pos[p],ey=pos[q+1]-pos[p+1],ez=pos[q+2]-pos[p+2];
   const el=Math.hypot(ex,ey,ez)||1;ex/=el;ey/=el;ez/=el;
   const cx=ay*bz-az*by,cy=az*bx-ax*bz,cz=ax*by-ay*bx;
   return Math.atan2(cx*ex+cy*ey+cz*ez,ax*bx+ay*by+az*bz);};
 const D0=new Float32Array(NE);for(let e=0;e<NE;e++)D0[e]=diedre(N0,e);
 // os : longueurs des segments du squelette ; anneaux : sommets groupés par (doigt, phalange, tranche)
 const os=[],ALL=A.ALL;
 const osLen=()=>{const L=[];ALL.forEach(k=>{const j=h.joints[k];for(let i=0;i<j.length;i++){
    const a=(j[i]).getWorldPosition(new TH.Vector3()),b=(j[i+1]||j.tip).getWorldPosition(new TH.Vector3());
    L.push(a.distanceTo(b));}});return L;};
 const L0=osLen();
 // anneaux : on range chaque sommet selon l'articulation dominante et son abscisse le long de l'os
 const ring=new Int32Array(MN).fill(-1),RN=[];
 {const parts=A.HD.mesh.part?null:null;
  ALL.forEach((k,ki)=>{const j=h.joints[k];
   for(let i=0;i<j.length;i++){const a=j[i].getWorldPosition(new TH.Vector3()),b=(j[i+1]||j.tip).getWorldPosition(new TH.Vector3());
     const u=b.clone().sub(a),ln=u.length();u.normalize();
     for(let v=0;v<MN;v++){if(ring[v]>=0)continue;
       const px=pos[3*v]-a.x,py=pos[3*v+1]-a.y,pz=pos[3*v+2]-a.z;
       const t=px*u.x+py*u.y+pz*u.z;if(t<.25*ln||t>.75*ln)continue;   // loin des articulations
       const d=Math.hypot(px-t*u.x,py-t*u.y,pz-t*u.z);if(d>.9)continue;
       ring[v]=RN.length+Math.min(2,Math.floor((t/ln-.25)/.5*3));}
     RN.push(0,0,0);}});}
 const NR=RN.length;
 const rayons=()=>{const s=new Float64Array(NR),n=new Float64Array(NR);
   // rayon = distance du sommet au barycentre de son anneau
   const cx=new Float64Array(NR),cy=new Float64Array(NR),cz=new Float64Array(NR);
   for(let v=0;v<MN;v++){const r=ring[v];if(r<0)continue;cx[r]+=pos[3*v];cy[r]+=pos[3*v+1];cz[r]+=pos[3*v+2];n[r]++;}
   for(let r=0;r<NR;r++)if(n[r]){cx[r]/=n[r];cy[r]/=n[r];cz[r]/=n[r];}
   for(let v=0;v<MN;v++){const r=ring[v];if(r<0)continue;
     s[r]+=Math.hypot(pos[3*v]-cx[r],pos[3*v+1]-cy[r],pos[3*v+2]-cz[r]);}
   for(let r=0;r<NR;r++)s[r]=n[r]?s[r]/n[r]:0;
   return s;};
 const R0=rayons();
 // --- mesure d'une pose ---
 const NC=new Float32Array(3*NT);
 const LIMR=-140*Math.PI/180,LIMC=100*Math.PI/180;
 const mesure=f=>{poser(f);triN(NC);
   let pin=0,gon=0;
   for(let t=0;t<NT;t++){if(S0[t]<=1e-9)continue;const r=Math.hypot(NC[3*t],NC[3*t+1],NC[3*t+2])/S0[t];
     if(r<.12)pin++;else if(r>3.2)gon++;}
   let rep=0,cas=0;
   for(let e=0;e<NE;e++){const d=diedre(NC,e);
     if(d<LIMR)rep++;                                     // les deux faces se font face : repli
     if(Math.abs(d-D0[e])>LIMC)cas++;}                    // la peau s'est froissée
   const L=osLen();let os=0;for(let i=0;i<L.length;i++)if(L0[i]>1e-6)os=Math.max(os,Math.abs(L[i]/L0[i]-1));
   const R=rayons();let ep=0;for(let r=0;r<NR;r++)if(R0[r]>.05)ep=Math.max(ep,Math.abs(R[r]/R0[r]-1));
   return {rep,cas,pin,gon,os:+(100*os).toFixed(1),ep:+(100*ep).toFixed(1)};};
 const out=[];
 for(const p of poses){const f=JSON.parse(JSON.stringify(dessin));
   for(const k in p.f)Object.assign(f[k],p.f[k]);
   if(p.preset){const e=A.editable();e.f=JSON.parse(JSON.stringify(dessin));A.applyPreset(p.preset);
     out.push(Object.assign({nom:p.nom},mesure(A.S.pose.f),{f:A.S.pose.f}));continue;}
   A.constrain({f});if(p.solve)Object.assign(f,A.solve(dessin,f));
   out.push(Object.assign({nom:p.nom},mesure(f),{f}));}
 return {NT,NE,NR,res:out};}
"""


def poses():
    """Liste des poses balayées (nom, angles)."""
    P = []
    FIN = ['index', 'majeur', 'annulaire', 'auriculaire']
    # 1. chaque articulation seule, à plusieurs angles (jusqu'aux butées et au-delà : constrain les ramène)
    GAM = {'mcp': [-25, -10, 20, 45, 70, 90, 100], 'pip': [20, 50, 80, 105, 115],
           'dip': [-15, 20, 45, 70, 85], 'ab': [-30, -15, 15, 25]}
    for k in FIN:
        for j, vs in GAM.items():
            for v in vs: P.append({'nom': f'{k}.{j}={v}', 'f': {k: {j: v}}})
    for j, vs in {'av': [-20, 0, 25, 50, 70], 'rap': [-20, 0, 20, 40, 60],
                  'mcp': [-10, 20, 45, 60], 'ip': [-25, 0, 40, 70, 85]}.items():
        for v in vs: P.append({'nom': f'pouce.{j}={v}', 'f': {'pouce': {j: v}}})
    # 2. combinaisons deux à deux dans un même doigt (c'est là que les zones d'arc se chevauchent)
    for k in FIN:
        for a in (45, 90):
            for b in (50, 105):
                for c in (0, 70):
                    P.append({'nom': f'{k}.{a}/{b}/{c}', 'f': {k: {'mcp': a, 'pip': b, 'dip': c}}})
    for a in (25, 60):
        for b in (20, 50):
            for c in (20, 60):
                for d in (40, 85):
                    P.append({'nom': f'pouce.{a}/{b}/{c}/{d}', 'f': {'pouce': {'av': a, 'rap': b, 'mcp': c, 'ip': d}}})
    # 3. poses extrêmes : tous les doigts ensemble, écartement maximal, hyperextension
    for a, b, c in [(100, 115, 85), (90, 105, 70), (-25, 0, -15), (0, 115, 85), (100, 0, 0), (45, 115, 0)]:
        P.append({'nom': f'tous.{a}/{b}/{c}', 'f': {k: {'mcp': a, 'pip': b, 'dip': c} for k in FIN}})
    for ab in (-25, 25):
        P.append({'nom': f'eventail.{ab}', 'f': {k: {'ab': ab * (1 if k != 'index' else -1)} for k in FIN}})
    P.append({'nom': 'poing+pouce', 'solve': True,
              'f': dict({k: {'mcp': 90, 'pip': 105, 'dip': 70} for k in FIN}, pouce={'av': 40, 'rap': 30, 'mcp': 40, 'ip': 40})})
    # 4. les configurations de l'atelier (chemin réel de l'application : settle + solve + thumbReach)
    for n in ['Dessin', 'Repos', 'Main plate (B)', 'Poing (A)', 'Poing serré', 'Index (1)', 'V (2)', 'L', 'Y', 'C', 'O', 'Pince']:
        P.append({'nom': 'PRESET ' + n, 'preset': n, 'f': {}})
    return P


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--images', type=int, default=0, help='rendre les N pires poses')
    ap.add_argument('--out', default=ROOT + '/tests/out/balayage')
    ap.add_argument('--poses', type=int, default=0, help='limiter le nombre de poses (mise au point)')
    ap.add_argument('--knk', type=float, default=None, help='multiplicateur du relief des jointures (A/B)')
    a = ap.parse_args()
    P = poses()
    if a.poses: P = P[:a.poses]
    os.makedirs(a.out, exist_ok=True)
    async with async_playwright() as pw:
        b = await pw.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = await b.new_page(viewport={'width': 900, 'height': 1000})
        async def h(route):
            u = route.request.url
            if u.endswith('three.min.js'): return await route.fulfill(path=VEND + '/build/three.min.js')
            if u.endswith('OrbitControls.js'): return await route.fulfill(path=VEND + '/examples/js/controls/OrbitControls.js')
            await route.continue_()
        await pg.route('https://**/*', h)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('file://' + ROOT + '/dist/atelier-mains-lsf.local.html')
        await pg.wait_for_timeout(6000)
        if a.knk is not None: await pg.evaluate('(v)=>window.__atelier.setKnk(v)', a.knk)
        r = await pg.evaluate(MESURE, P)
        res = r['res']
        print('triangles %d, arêtes %d, anneaux %d, poses %d' % (r['NT'], r['NE'], r['NR'], len(res)))
        # score : ce qui se voit le plus d'abord
        sc = lambda d: d['rep'] * 4 + d['cas'] * 2 + d['pin'] + d['gon'] + d['os'] * 40 + max(0, d['ep'] - 15) * 10
        res.sort(key=sc, reverse=True)
        print('pose\treplis\tcassures\tpincés\tgonflés\tos %\tépais %\tscore')
        for d in res[:30]:
            print('%s\t%d\t%d\t%d\t%d\t%.1f\t%.1f\t%.0f' % (d['nom'], d['rep'], d['cas'], d['pin'], d['gon'], d['os'], d['ep'], sc(d)))
        tot = {k: sum(d[k] for d in res) for k in ('rep', 'cas', 'pin', 'gon')}
        print('TOTAL\t%d\t%d\t%d\t%d\tos max %.1f\tépais max %.1f' % (
            tot['rep'], tot['cas'], tot['pin'], tot['gon'], max(d['os'] for d in res), max(d['ep'] for d in res)))
        with open(a.out + '/mesures.json', 'w') as fh: json.dump(res, fh)
        if a.images:
            el = await pg.query_selector('#stage canvas')
            for i, d in enumerate(res[:a.images]):
                await pg.evaluate("""([ff])=>{const A=window.__atelier;A.S.pose.f=ff;A.refresh();
                  A.camera.position.set(34,6,26);A.controls.target.set(0,0,0);A.controls.update()}""", [d['f']])
                await pg.wait_for_timeout(350)
                await el.screenshot(path='%s/%02d_%s.png' % (a.out, i, d['nom'].replace('/', '-').replace(' ', '_').replace('=', '')))
        print('erreurs JS :', errs or 'aucune')
        await b.close()

asyncio.run(main())
