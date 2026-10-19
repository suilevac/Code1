/* stub_hand.js — bouchon de l'API window.AtelierHand (contrat M2 → M3 de PLAN.md).
   Le vrai moteur (v2/engine/engine.js, Three.js) le remplacera sans changer plate.js : l'éditeur ne connaît
   que render / bounds / puppet / presets / solve / mirror / ready.
   Ici la main est une SILHOUETTE PLATE : une chaîne cinématique 3D simplifiée (capsules en cm, mêmes
   proportions que anatomie.md : HL = 19 cm, paume 8,5 cm de large, doigts 7,5 / 8,3 / 7,7 / 6,0 cm), posée par
   les angles de la pose v2, tournée par le quaternion d'orientation, puis projetée orthographiquement et dessinée
   en aplat + contour + ongles. Rien d'anatomique : c'est un gabarit pour tester l'éditeur, qui doit avoir la
   bonne BOÎTE, la bonne latéralité (gauche = miroir 3D, l'ombre reste du même côté) et le bon alpha. */
(function(){
'use strict';
const HL=19;                                   // longueur de main en cm (PLAN.md « HL »)
const D2R=Math.PI/180;
const clone=o=>JSON.parse(JSON.stringify(o));
const DOIGTS=['index','majeur','annulaire','auriculaire'];
// géométrie de repos d'une main GAUCHE (pouce vers +X, doigts vers +Y, paume vers +Z, poignet à l'origine)
const G={
  paume:{w:8.6,l:10.0},                        // largeur aux têtes métacarpiennes, longueur poignet → MCP
  // x de la MCP, longueur des 3 phalanges (cm), rayon (cm) — d'après anatomie.md (index 4.0/2.5/2.0 …)
  index:{x:2.6,y:9.8,L:[4.0,2.5,2.1],r:.85},
  majeur:{x:0.8,y:10.2,L:[4.4,2.8,2.2],r:.88},
  annulaire:{x:-1.0,y:9.9,L:[4.0,2.6,2.1],r:.82},
  auriculaire:{x:-2.8,y:9.0,L:[3.2,2.0,1.8],r:.72},
  pouce:{x:3.6,y:2.2,L:[4.6,3.1,2.7],r:1.0},    // CMC au poignet, métacarpien + P1 + P2 (+ pulpe)
};
/* ---------- petites maths ---------- */
const v=(x,y,z)=>[x,y,z];
const add=(a,b)=>[a[0]+b[0],a[1]+b[1],a[2]+b[2]];
const mul=(a,k)=>[a[0]*k,a[1]*k,a[2]*k];
// rotation d'un vecteur par un quaternion [x,y,z,w]
function qrot(q,p){const [x,y,z,w]=q;const ix=w*p[0]+y*p[2]-z*p[1],iy=w*p[1]+z*p[0]-x*p[2],iz=w*p[2]+x*p[1]-y*p[0],iw=-x*p[0]-y*p[1]-z*p[2];
  return[ix*w+iw*-x+iy*-z-iz*-y,iy*w+iw*-y+iz*-x-ix*-z,iz*w+iw*-z+ix*-y-iy*-x]}
function qmul(a,b){return[a[3]*b[0]+a[0]*b[3]+a[1]*b[2]-a[2]*b[1],a[3]*b[1]-a[0]*b[2]+a[1]*b[3]+a[2]*b[0],a[3]*b[2]+a[0]*b[1]-a[1]*b[0]+a[2]*b[3],a[3]*b[3]-a[0]*b[0]-a[1]*b[1]-a[2]*b[2]]}
function qaxis(ax,deg){const h=deg*D2R/2,s=Math.sin(h);return[ax[0]*s,ax[1]*s,ax[2]*s,Math.cos(h)]}
const num=(x,d)=>typeof x==='number'&&isFinite(x)?x:(d||0);
/* ---------- pose : champs absents = 0 (compatible v1 : F(mcp,pip,dip,ab), TH(av,rap,mcp,ip)) ---------- */
function norm(p){p=p&&typeof p==='object'?p:{};const o={poignet:{flex:num(p.poignet&&p.poignet.flex),dev:num(p.poignet&&p.poignet.dev)},prono:num(p.prono),arc:num(p.arc),
  pouce:{av:0,rap:0,mcp:0,ip:0,abdMcp:0}};
  const t=p.pouce||{};for(const k in o.pouce)o.pouce[k]=num(t[k]);
  DOIGTS.forEach(d=>{const f=p[d]||{};o[d]={mcp:num(f.mcp),pip:num(f.pip),dip:num(f.dip),ab:num(f.ab),rot:num(f.rot)}});
  return o}
// butées (mobilite.md § 5, valeurs rondes) : le bouchon se contente de borner
const BUT={mcp:[-30,95],pip:[0,110],dip:[-10,85],ab:[-25,25],rot:[-15,15],av:[0,60],rap:[-10,50],pmcp:[-10,60],ip:[-15,85],abdMcp:[-10,20],flex:[-70,75],dev:[-25,35],prono:[-90,90],arc:[0,30]};
const clampB=(x,b)=>Math.max(b[0],Math.min(b[1],x));
function constrain(p){p=norm(p);p.poignet.flex=clampB(p.poignet.flex,BUT.flex);p.poignet.dev=clampB(p.poignet.dev,BUT.dev);p.prono=clampB(p.prono,BUT.prono);p.arc=clampB(p.arc,BUT.arc);
  p.pouce.av=clampB(p.pouce.av,BUT.av);p.pouce.rap=clampB(p.pouce.rap,BUT.rap);p.pouce.mcp=clampB(p.pouce.mcp,BUT.pmcp);p.pouce.ip=clampB(p.pouce.ip,BUT.ip);p.pouce.abdMcp=clampB(p.pouce.abdMcp,BUT.abdMcp);
  DOIGTS.forEach(d=>{const f=p[d];f.mcp=clampB(f.mcp,BUT.mcp);f.pip=clampB(f.pip,BUT.pip);f.dip=clampB(f.dip,BUT.dip);f.ab=clampB(f.ab,BUT.ab);f.rot=clampB(f.rot,BUT.rot);
    // fléchisseur profond commun (CLAUDE.md) : dip ≤ 25 + 0,65 pip et dip ≥ 0,45 (pip − 55)
    f.dip=Math.min(f.dip,25+.65*f.pip);f.dip=Math.max(f.dip,.45*(f.pip-55))});
  return p}
/* ---------- chaîne cinématique → capsules 3D ---------- */
function capsules(pose,cote){
  const p=constrain(pose),C=[],m=cote==='G'?1:-1;    // droite = miroir en X de la gauche (contrat M1 : le GLB est la gauche)
  const flexQ=(deg)=>qaxis([1,0,0],deg);               // flexion = rotation autour de +X local, vers la paume (+Z)
  // poignet : flexion puis déviation ; la paume part du poignet
  let q=qmul(qaxis([0,0,1],p.poignet.dev*m),flexQ(p.poignet.flex));
  const seg=(a,b,r,part,nail)=>C.push({a,b,r,part,nail});
  const P=G.paume,hw=P.w/2;
  // paume : un bloc arrondi (4 capsules transversales) + poignet
  const pt=(x,y,z)=>qrot(q,[x*m,y,z]);
  // paume : UN polygone arrondi (poignet étroit → têtes métacarpiennes larges), pas des bandes, sinon la silhouette est striée
  C.push({poly:[pt(-hw*.72,-1.2,0),pt(-hw+1.2,P.l-1.4,0),pt(hw-1.2,P.l-1.4,0),pt(hw*.72,-1.2,0)],r:1.3,part:'paume'});
  // doigts
  DOIGTS.forEach(d=>{const g=G[d],f=p[d];
    let base=pt(g.x,g.y,0),qd=qmul(q,qmul(qaxis([0,0,1],-f.ab*m),qaxis([0,1,0],f.rot*m)));
    const ang=[f.mcp,f.pip,f.dip];
    for(let i=0;i<3;i++){qd=qmul(qd,flexQ(ang[i]));const dir=qrot(qd,[0,1,0]);const end=add(base,mul(dir,g.L[i]));
      const r=g.r*(1-.07*i);seg(base,end,r,d,i===2?{q:qd,r}:null);base=end}});
  // pouce : CMC = « avancer » (abduction palmaire, autour de Y vers +Z) et « rapprocher » (autour de Z) ; au repos il
  // est à 40° du bord radial dans le plan de la paume
  {const g=G.pouce,t=p.pouce;let base=pt(g.x,g.y,0);
    let qt=qmul(q,qmul(qaxis([0,0,1],(-40+t.rap)*m),qaxis([0,1,0],-t.av*m)));
    const ang=[0,t.mcp,t.ip];
    for(let i=0;i<3;i++){qt=qmul(qt,qmul(flexQ(ang[i]),i===1?qaxis([0,0,1],-t.abdMcp*m):[0,0,0,1]));const dir=qrot(qt,[0,1,0]);
      const end=add(base,mul(dir,g.L[i]));const r=g.r*(1-.08*i);seg(base,end,r,'pouce',i===2?{q:qt,r}:null);base=end}}
  return C}
function oriented(C,orientation){const q=Array.isArray(orientation)&&orientation.length===4?orientation:[0,0,0,1];
  const L=Math.hypot(q[0],q[1],q[2],q[3])||1,qn=q.map(x=>x/L);
  return C.map(c=>c.poly?{poly:c.poly.map(p=>qrot(qn,p)),r:c.r,part:c.part}:({a:qrot(qn,c.a),b:qrot(qn,c.b),r:c.r,part:c.part,nail:c.nail?{z:qrot(qn,qrot(c.nail.q,[0,0,-1]))[2],r:c.nail.r,dir:qrot(qn,qrot(c.nail.q,[0,1,0]))}:null}))}
// boîte projetée (x, −y) en cm, marge = rayon + 4 % (outil.md § 4.3 : la coque déborde)
function box(C){let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;C.forEach(c=>{(c.poly||[c.a,c.b]).forEach(p=>{x0=Math.min(x0,p[0]-c.r);x1=Math.max(x1,p[0]+c.r);y0=Math.min(y0,-p[1]-c.r);y1=Math.max(y1,-p[1]+c.r)})});
  const mx=(x1-x0)*.04,my=(y1-y0)*.04;return{x:x0-mx,y:y0-my,w:x1-x0+2*mx,h:y1-y0+2*my}}
/* ---------- dessin ---------- */
function shade(hex,k){const n=parseInt(hex.slice(1),16),r=(n>>16)&255,g=(n>>8)&255,b=n&255;const f=c=>Math.max(0,Math.min(255,Math.round(c*k)));return'#'+[f(r),f(g),f(b)].map(x=>x.toString(16).padStart(2,'0')).join('')}
function capsulePath(x,a,b,r){const dx=b[0]-a[0],dy=b[1]-a[1],L=Math.hypot(dx,dy)||1e-6,nx=-dy/L*r,ny=dx/L*r,ang=Math.atan2(dy,dx);
  x.beginPath();x.arc(a[0],a[1],r,ang+Math.PI/2,ang-Math.PI/2);x.arc(b[0],b[1],r,ang-Math.PI/2,ang+Math.PI/2);x.closePath()}
function render(o){
  o=o||{};const w=Math.max(2,Math.round(num(o.w,256))),h=Math.max(2,Math.round(num(o.h,256)));
  const st=Object.assign({peau:'#00a19a',ongle:'#bfe9e4',trait:'#111111',largeurTrait:1.2,ombre:true},o.style||{});
  const C=oriented(capsules(o.pose,o.cote),o.orientation),B=box(C);
  const cv=document.createElement('canvas');cv.width=w;cv.height=h;const x=cv.getContext('2d');
  const s=Math.min(w/B.w,h/B.h);                              // cm → px, la main remplit la boîte
  const ox=(w-B.w*s)/2-B.x*s,oy=(h-B.h*s)/2-B.y*s;
  const P=p=>[ox+p[0]*s,oy-p[1]*s];
  // tri par profondeur : la caméra est en +Z, le plus grand z est devant et se dessine en dernier
  const zmoy=c=>c.poly?c.poly.reduce((s,p)=>s+p[2],0)/c.poly.length-.01:(c.a[2]+c.b[2])/2;   // la paume passe juste derrière les doigts à z égal
  const ord=C.slice().sort((u,v2)=>zmoy(u)-zmoy(v2));
  // chemin d'une forme : capsule, ou polygone dont le contour arrondi est obtenu par un trait épais (lineJoin round)
  const path=(c,extra)=>{if(c.poly){x.beginPath();c.poly.forEach((p,i)=>{const q=P(p);i?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1])});x.closePath();x.lineWidth=2*c.r*s+(extra||0);return}
    capsulePath(x,P(c.a),P(c.b),c.r*s);x.lineWidth=extra||0};
  const lw=Math.max(1,st.largeurTrait/100*h);                 // contour en % de la hauteur (contrat M2)
  x.lineJoin='round';x.lineCap='round';
  // 1. ombre franche : une seule lumière en haut à gauche ; les capsules dont la normale moyenne regarde à droite
  //    sont dans le ton d'ombre (aplat + ombre, comme le dessin de l'utilisateur)
  const dark=shade(st.peau,.78);
  // 2. chaque capsule : aplat, puis contour tracé seulement là où rien n'est devant (on triche : contour de
  //    toute la capsule, puis on repeint l'intérieur — c'est ce que fait une coque inversée)
  ord.forEach(c=>{path(c,lw*2);x.strokeStyle=st.trait;x.stroke()});
  ord.forEach(c=>{path(c,0);x.fillStyle=st.peau;x.strokeStyle=st.peau;x.fill();if(c.poly){x.stroke();
      if(st.ombre){// ombre de la paume : bande le long du bord droit (lumière à gauche)
        x.save();x.beginPath();x.rect(0,0,w,h);path(c,0);x.clip();x.fillStyle=dark;const q=c.poly.map(P);x.beginPath();x.moveTo(q[2][0]-c.r*s*.3,q[2][1]);x.lineTo(q[3][0]-c.r*s*.3,q[3][1]);x.lineTo(q[3][0]+c.r*s*1.5,q[3][1]);x.lineTo(q[2][0]+c.r*s*1.5,q[2][1]);x.closePath();x.fill();x.restore()}
      return}
    const a=P(c.a),b=P(c.b),r=c.r*s;
    if(st.ombre){x.save();x.clip();x.fillStyle=dark;x.beginPath();const dx=b[0]-a[0],dy=b[1]-a[1],L=Math.hypot(dx,dy)||1,nx=-dy/L,ny=dx/L;
      // bande d'ombre sur le côté droit (lumière à gauche) : moitié de la capsule décalée de 0,45 r
      const k=nx>0?1:-1;x.moveTo(a[0]+nx*k*r*.45,a[1]+ny*k*r*.45);x.lineTo(b[0]+nx*k*r*.45,b[1]+ny*k*r*.45);x.lineTo(b[0]+nx*k*r*1.2,b[1]+ny*k*r*1.2);x.lineTo(a[0]+nx*k*r*1.2,a[1]+ny*k*r*1.2);x.closePath();x.fill();x.restore()}
    // ongle sur la dernière phalange quand son dos regarde la caméra
    if(c.nail&&c.nail.z>.15){const d=c.nail.dir,L=Math.hypot(d[0],d[1])||1e-6;const ux=d[0]/L,uy=-d[1]/L;
      const cx=b[0]-ux*r*.75,cy=b[1]-uy*r*.75;x.save();x.translate(cx,cy);x.rotate(Math.atan2(uy,ux));
      x.beginPath();x.ellipse(0,0,r*.55*Math.min(1,c.nail.z+.4),r*.62,0,0,Math.PI*2);x.fillStyle=st.ongle;x.fill();x.lineWidth=lw*.7;x.strokeStyle=st.trait;x.stroke();x.restore()}});
  return cv}
function bounds(o){const B=box(oriented(capsules(o&&o.pose,o&&o.cote),o&&o.orientation));return{w:B.w,h:B.h}}
/* ---------- presets (format v2 ; les 15 de la v1 + alphabet et chiffres, valeurs de bouchon) ---------- */
const F=(mcp,pip,dip,ab)=>({mcp,pip,dip,ab:ab||0,rot:0});
const TH=(av,rap,mcp,ip)=>({av,rap,mcp,ip,abdMcp:0});
const H=(pouce,i,m,a,au,extra)=>Object.assign({poignet:{flex:0,dev:0},prono:0,arc:0,pouce,index:i,majeur:m,annulaire:a,auriculaire:au},extra||{});
const OUV=F(0,0,0,0),PLI=F(90,105,70,0),CRO=F(40,90,60,0),DEMI=F(45,45,25,0);
const presets={
  'Dessin':H(TH(0,0,0,0),OUV,OUV,OUV,OUV),
  'Repos':H(TH(20,10,10,10),F(25,30,15,0),F(25,30,15,0),F(25,30,15,0),F(25,30,15,0),{poignet:{flex:15,dev:0}}),
  'B':H(TH(10,45,40,20),F(0,0,0,-4),F(0,0,0,-1),F(0,0,0,2),F(0,0,0,6)),
  'Poing (A)':H(TH(5,0,20,20),PLI,PLI,PLI,PLI),
  'Poing serré':H(TH(24,10,35,60),PLI,PLI,PLI,PLI),
  'Index (1)':H(TH(40,24,40,40),F(0,0,0,0),PLI,PLI,PLI),
  'V (2)':H(TH(40,35,40,40),F(0,0,0,-10),F(0,0,0,8),PLI,PLI),
  'Trois (3)':H(TH(45,0,0,0),F(0,0,0,-10),F(0,0,0,5),PLI,PLI),
  'Quatre (4)':H(TH(20,45,45,30),F(0,0,0,-10),F(0,0,0,-3),F(0,0,0,4),F(0,0,0,12)),
  'Main ouverte (5)':H(TH(45,0,0,0),F(0,0,0,-14),F(0,0,0,-4),F(0,0,0,5),F(0,0,0,16)),
  'L':H(TH(50,-5,0,0),F(0,0,0,-5),PLI,PLI,PLI),
  'Y':H(TH(50,-5,0,0),PLI,PLI,PLI,F(0,0,0,18)),
  'C':H(TH(45,10,20,20),DEMI,DEMI,DEMI,DEMI),
  'O':H(TH(30,30,30,30),F(55,60,40,0),F(55,60,40,0),F(55,60,40,0),F(55,60,40,0)),
  'Pince':H(TH(25,28,8,14),F(40,50,35,0),F(20,25,10,0),F(20,25,10,0),F(20,25,10,0)),
};
// alphabet et chiffres LSF (bouchon : silhouettes plausibles, le moteur M2 porte les vraies)
const AL={A:'Poing (A)',B:'B',C:'C',D:H(TH(30,30,30,30),OUV,CRO,CRO,CRO),E:H(TH(10,40,40,30),CRO,CRO,CRO,CRO),F:H(TH(30,30,30,30),F(50,60,40,0),OUV,OUV,OUV),
  G:H(TH(45,-5,0,0),F(0,0,0,0),PLI,PLI,PLI,{prono:90}),H:H(TH(10,45,40,20),OUV,OUV,PLI,PLI,{prono:90}),I:H(TH(10,45,40,20),PLI,PLI,PLI,F(0,0,0,8)),
  J:H(TH(10,45,40,20),PLI,PLI,PLI,F(0,0,0,8),{poignet:{flex:0,dev:20}}),K:H(TH(45,10,0,0),F(0,0,0,-8),F(45,0,0,4),PLI,PLI),L:'L',M:H(TH(10,45,45,20),F(80,30,10,0),F(80,30,10,0),F(80,30,10,0),PLI),
  N:H(TH(10,45,45,20),F(80,30,10,0),F(80,30,10,0),PLI,PLI),O:'O',P:H(TH(45,10,0,0),F(0,0,0,-8),F(45,0,0,4),PLI,PLI,{poignet:{flex:60,dev:0}}),Q:H(TH(45,-5,0,0),F(0,0,0,0),PLI,PLI,PLI,{poignet:{flex:60,dev:0}}),
  R:H(TH(10,45,40,20),F(0,0,0,6),F(0,0,0,-6),PLI,PLI),S:'Poing serré',T:H(TH(20,30,40,20),F(60,40,20,0),PLI,PLI,PLI),U:H(TH(10,45,40,20),F(0,0,0,-2),F(0,0,0,2),PLI,PLI),V:'V (2)',W:'Trois (3)',
  X:H(TH(10,45,40,20),CRO,PLI,PLI,PLI),Y:'Y',Z:'Index (1)'};
for(const k in AL)presets['Lettre '+k]=typeof AL[k]==='string'?clone(presets[AL[k]]):AL[k];
const CH={'0':'O','1':'Index (1)','2':'V (2)','3':'Trois (3)','4':'Quatre (4)','5':'Main ouverte (5)',
  '6':H(TH(45,0,0,0),OUV,OUV,OUV,F(70,80,40,0)),'7':H(TH(45,0,0,0),OUV,OUV,F(70,80,40,0),OUV),'8':H(TH(45,0,0,0),OUV,F(70,80,40,0),OUV,OUV),'9':H(TH(45,0,0,0),F(70,80,40,0),OUV,OUV,OUV)};
for(const k in CH)presets['Chiffre '+k]=typeof CH[k]==='string'?clone(presets[CH[k]]):CH[k];
/* ---------- marionnette minimale : un panneau de curseurs dans canvasHost ---------- */
// AtelierHand.puppet(canvasHost, element, onChange) : canvasHost est un élément DOM que l'éditeur positionne SUR la
// main ; le bouchon y pose des curseurs par articulation ; onChange(pose) est appelé à chaque changement ; l'objet
// rendu a stop() pour quitter proprement. Le moteur M2 affichera là son canvas WebGL et le glisser des doigts.
function puppet(host,element,onChange){
  const p=constrain(element&&element.pose);host.innerHTML='';host.classList.add('stub-puppet');
  const rows=[['pouce','av',BUT.av],['pouce','rap',BUT.rap],['pouce','mcp',BUT.pmcp],['pouce','ip',BUT.ip]];
  DOIGTS.forEach(d=>rows.push([d,'mcp',BUT.mcp],[d,'pip',BUT.pip],[d,'dip',BUT.dip],[d,'ab',BUT.ab]));
  rows.push(['poignet','flex',BUT.flex],['poignet','dev',BUT.dev]);
  const title=document.createElement('div');title.className='stub-puppet-title';title.textContent='Marionnette (bouchon) : curseurs par articulation';host.appendChild(title);
  const grid=document.createElement('div');grid.className='stub-puppet-grid';host.appendChild(grid);
  rows.forEach(([part,k,b])=>{const lab=document.createElement('label');lab.textContent=part+' '+k;const inp=document.createElement('input');inp.type='range';inp.min=b[0];inp.max=b[1];inp.step=1;inp.value=p[part][k];
    inp.setAttribute('data-joint',part+'.'+k);
    inp.oninput=()=>{p[part][k]=+inp.value;const c=constrain(p);onChange(clone(c))};grid.appendChild(lab);grid.appendChild(inp)});
  return{stop(){host.innerHTML='';host.classList.remove('stub-puppet')},pose:()=>clone(p)}}
function solve(dep,cib){return constrain(cib)}
// la pose est symétrique par construction : mêmes angles pour l'autre main (CLAUDE.md : mirror ne touche que la
// position et le quaternion, que l'éditeur porte dans `orientation`)
function mirror(pose){return constrain(pose)}
function mirrorOrientation(q){return Array.isArray(q)&&q.length===4?[q[0],-q[1],-q[2],q[3]]:[0,0,0,1]}
window.AtelierHand={ready:Promise.resolve(),render,bounds,puppet,presets,solve,mirror,mirrorOrientation,constrain,normalise:norm,stub:true,HL};
})();
