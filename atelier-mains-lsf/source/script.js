<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script type="application/json" id="handData">__DATA__</script>
<script>
(async function(){
const $=id=>document.getElementById(id), D=Math.PI/180, clone=o=>JSON.parse(JSON.stringify(o));
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)), smooth=(a,b,x)=>{const t=clamp((x-a)/(b-a),0,1);return t*t*(3-2*t)};
const HD=JSON.parse($('handData').textContent);
const LOCK_SVG='<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="7" width="10" height="7" rx="1.5" fill="currentColor" stroke="none"/><path d="M5 7V5a3 3 0 0 1 6 0v2"/></svg>';

/* ======================================================================
   Repère : pixels du dessin paume -> unités 3D (x à droite, y en haut, z vers la paume)
   ====================================================================== */
const SC=50, CX=HD.W/2, CY=HD.H*.48;
const toM=(x,y,z)=>new THREE.Vector3((x-CX)/SC,-(y-CY)/SC,z/SC);
const Z=new THREE.Vector3(0,0,1);
const FING=['index','majeur','annulaire','auriculaire'],ALL=['pouce',...FING];
const NOMS={pouce:'Pouce',index:'Index',majeur:'Majeur',annulaire:'Annulaire',auriculaire:'Auriculaire'};
const SEGN={pouce:['base','bout'],doigt:['base','milieu','bout']};
const typ=k=>k==='pouce'?'pouce':'doigt';

/* ======================================================================
   Anatomie
   - doigts : MCP (flexion + écartement), IPP et IPD (charnières) ; l'IPD suit l'IPP (tendon commun)
   - en pliant, les doigts se resserrent et convergent (ils pointent vers le scaphoïde)
   - l'écartement se referme quand la MCP plie (ligaments collatéraux tendus)
   - l'annulaire entraîne ses voisins ; l'index est libre
   - pouce : trapézo-métacarpienne (avancer / rapprocher + pronation), MCP, IP ;
     la MCP du pouce ne plie loin que si le pouce s'est avancé devant la paume,
     et le bout du pouce ne pointe jamais vers le poignet
   ====================================================================== */
const AX={};
ALL.forEach(k=>{AX[k]=HD.segs[k].map(sg=>{const u=new THREE.Vector3(sg.u[0],-sg.u[1],0).normalize();return{u,lat:u.clone().cross(Z).normalize()}})});
// doigts : axes repris sur la chaîne CORRIGÉE (l'IPD n'est pas au pli distal dessiné, voir rig3d.py).
// Le segment de base garde exactement sa direction, donc PAR et l'éventail des doigts ne bougent pas.
const chAx=C=>{const u=new THREE.Vector3(C[1][0]-C[0][0],-(C[1][1]-C[0][1]),0).normalize();return{u,lat:u.clone().cross(Z).normalize()}};
FING.forEach(k=>{const C=HD.mesh.chain[k];AX[k]=[0,1,2].map(i=>chAx([C[i],C[i+1]]))});
// pouce : chaîne corrigée [CMC, MCP, IP, bout] (le pli IP dessiné n'est pas le centre de l'articulation, voir rig3d.py).
// Ses axes de flexion sont repris sur les OS corrigés, pas sur les segments du dessin.
const TCH=HD.mesh.chain.pouce;
AX.pouce=[0,1].map(i=>{const a=TCH[i+1],b=TCH[i+2],u=new THREE.Vector3(b[0]-a[0],-(b[1]-a[1]),0).normalize();return{u,lat:u.clone().cross(Z).normalize()}});
const ang=k=>Math.atan2(AX[k][0].u.y,AX[k][0].u.x);
const PAR={};FING.forEach(k=>PAR[k]=-(ang('majeur')-ang(k))/D);
const SPREAD={index:[-10,25],majeur:[-15,15],annulaire:[-20,12],auriculaire:[-45,15]}; // + = vers le pouce, 0 = parallèle au majeur
// Convergence : en pliant, les doigts se rapprochent (ils pointent vers le scaphoïde, à la base de l'éminence).
// Mesuré : poing fermé, les bouts des quatre doigts s'écartaient de 310 px alors que les MCP ne s'écartent que de
// 263 px — les doigts DIVERGEAIENT. Les signes étaient inversés : avec ces valeurs l'écartement des bouts tombe
// à 236 px (et à 239 px aux 3/4), le poing se ferme en entier sans pénétration (cas_3 : 90/105/70 au lieu de
// 89/103/69) et le jour entre les bouts et la paume se referme en bonne partie.
const CONV={index:6,majeur:2,annulaire:-2,auriculaire:-7};
const LIMF={mcp:[-20,90],pip:[0,105],dip:[-10,80]};
const LIMT={av:[0,45],rap:[-20,40],mcp:[-10,55],ip:[-20,80]};
const ENSLAVE=[['index','majeur',90],['majeur','annulaire',85],['annulaire','auriculaire',75]];
const CMC_IMG=TCH[0],MCP_T=TCH[1];
const CMC=toM(CMC_IMG[0],CMC_IMG[1],HD.mesh.jz.pouce[0]);
// axe du 1er métacarpien pris d'une articulation à l'autre, à leur vraie profondeur (la colonne du pouce
// est en avant du plan de la paume) ; LATM lui est perpendiculaire, dans le plan de la paume
const UM=toM(MCP_T[0],MCP_T[1],HD.mesh.jz.pouce[1]).sub(CMC).normalize(),LATM=UM.clone().cross(Z).normalize();
const convOf=(k,v)=>CONV[k]*clamp((Math.max(0,v.mcp)+.6*Math.max(0,v.pip))/150,0,1);

function constrain(p,driver){
  FING.forEach(k=>{const v=p.f[k];
    v.mcp=clamp(v.mcp,...LIMF.mcp);v.pip=clamp(v.pip,...LIMF.pip);v.dip=clamp(v.dip,LIMF.dip[0],Math.min(LIMF.dip[1],25+.65*v.pip));
    const fr=1-.85*clamp(v.mcp,0,90)/90;v.ab=clamp(v.ab,SPREAD[k][0]*fr,SPREAD[k][1]*fr)});
  const t=p.f.pouce;for(const j in LIMT)t[j]=clamp(t[j],...LIMT[j]);
  if(t.av+t.rap>80){const e=(t.av+t.rap-80)/2;t.av-=e;t.rap-=e}
  t.mcp=Math.min(t.mcp,30+.8*t.av+.4*Math.max(0,t.rap));   // la MCP du pouce plie davantage quand il s'avance ou se rapproche
  if(driver&&driver!=='pouce'){
    const order=[driver];const seen=new Set(order);
    for(let i=0;i<order.length;i++){const a=order[i];
      ENSLAVE.forEach(([x,y,mx])=>{if(x!==a&&y!==a)return;const b=x===a?y:x;if(seen.has(b))return;
        const va=p.f[a],vb=p.f[b],d=va.mcp-vb.mcp;
        if(Math.abs(d)>mx){if(S.locks[b][0]){va.mcp=vb.mcp+Math.sign(d)*mx}else{vb.mcp=va.mcp-Math.sign(d)*mx;seen.add(b);order.push(b)}}
      })}
  }
  return p;
}

const F=(mcp,pip,dip,ab)=>({mcp,pip,dip,ab});
const TH=(av,rap,mcp,ip)=>({av,rap,mcp,ip});
function pose(fn,t){const f={pouce:t};FING.forEach(k=>f[k]=fn(k));return{f,q:[0,0,0,1],pos:[0,0,0]}}
const fist=()=>F(90,105,70,0);
const together={index:-6,majeur:0,annulaire:6,auriculaire:9};
const PRESETS={
  'Dessin':pose(k=>F(0,0,0,-PAR[k]),TH(0,0,0,0)),
  'Repos':pose(k=>({index:F(18,28,14,5),majeur:F(22,33,16,0),annulaire:F(27,38,18,-3),auriculaire:F(32,42,20,-8)})[k],TH(25,10,10,15)),
  'Main plate (B)':pose(k=>F(0,0,0,together[k]),TH(20,35,30,10)),
  'Poing (A)':pose(fist,TH(5,35,10,5)),
  'Poing serré':pose(fist,TH(45,35,40,25)),
  'Index (1)':pose(k=>k==='index'?F(0,0,0,0):fist(),TH(40,35,40,40)),
  'V (2)':pose(k=>k==='index'?F(0,0,0,8):k==='majeur'?F(0,0,0,-8):fist(),TH(40,35,40,40)),
  'L':pose(k=>k==='index'?F(0,0,0,0):fist(),TH(0,-20,0,0)),
  'Y':pose(k=>k==='auriculaire'?F(0,0,0,-30):fist(),TH(0,-20,0,0)),
  'C':pose(k=>F(35,45,30,together[k]),TH(45,5,10,10)),
  'O':pose(k=>({index:F(55,60,40,-2),majeur:F(58,62,42,0),annulaire:F(60,64,42,2),auriculaire:F(62,66,44,4)})[k],TH(45,30,25,30)),
  'Pince':pose(k=>k==='index'?F(45,55,35,0):F(0,0,0,together[k]),TH(45,20,20,20))
};
const S={mode:'pose',target:'debut',etapes:2,fleche:true,gauche:false,pose:clone(PRESETS['Dessin']),debut:null,fin:null,locks:{}};
ALL.forEach(k=>S.locks[k]=SEGN[typ(k)].map(()=>false));
const editable=()=>S.mode==='pose'?S.pose:(S.target==='debut'?S.debut:S.fin);

/* ======================================================================
   Textures : dessin paume devant, dessin dos recalé derrière
   ====================================================================== */
function tex(src){return new Promise(r=>{const t=new THREE.TextureLoader().load(src,()=>r(t));t.anisotropy=4})}
const [TF,TB,TN,TE,TC]=await Promise.all([tex(HD.texFront),tex(HD.texBack),tex(HD.texNail),tex(HD.texNailE),tex(HD.texCrease)]);
[TN,TE].forEach(t=>{t.generateMipmaps=false;t.minFilter=THREE.LinearFilter});   // distance signée : pas de moyenne entre niveaux (elle déborderait sur la tranche)
const NAILC=new THREE.Vector3(...HD.nail.col),NAILS=new THREE.Vector3(...HD.nail.skin);
const LIGHT=new THREE.Vector3(-.45,.55,1).normalize();
const VS=`attribute float part;attribute float rnz;attribute vec2 crf;uniform float hlPart;varying float vH;varying float vS;varying vec2 vCr;varying vec2 vUv;varying vec3 vN;void main(){vH=abs(part-hlPart)<.5?1.:0.;vS=smoothstep(-.3,.3,rnz);vCr=crf;vUv=uv;vN=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}`;
// ongles (dos seulement) : texNail R = distance signée au bord (px) → aplat net + trait fin du dessin, nets à tout grossissement ;
// G/B = peau repeinte (sous l'ongle, son trait, bouts de trait étirés en taches), sur le dos franc (vS≈0) ; texNailE = poids
// du trait : il s'amincit jusqu'à rien au bord libre (« U » ouvert du dessin). Pose du dessin : rien sur la tranche ni vu en biais (vue paume = dessin exact) ; hors pose (npose) partout
// plis et rides (piste R) : crTex = trait de la paume (R), le même élargi (G), aplat du dos (B) et masque des rides
// du dos (A) ; vCr donne l'effacement du trait selon l'angle de l'articulation voisine (x paume, négatif = creusé ;
// y dos, positif = effacé). Paume : le trait est gris, un multiplicateur (1-a(1-e))/(1-a) suffit. Dos : le trait est
// NOIR, on le remplace par l'aplat voisin. Les deux valent exactement l'identité à e = 0 (dessin exact au repos).
const FS=`uniform sampler2D nailTex;uniform sampler2D nailE;uniform float npose;uniform vec3 nailCol;uniform vec3 nailSkin;uniform float nailLW;uniform sampler2D colTex;uniform sampler2D colTex2;uniform sampler2D crTex;uniform sampler2D alphaTex;uniform float opacity;uniform float hl;uniform vec3 L;varying float vH;varying float vS;varying vec2 vCr;varying vec2 vUv;varying vec3 vN;
void main(){if(texture2D(alphaTex,vUv).a<.35){gl_FragColor=vec4(.067,.067,.067,opacity);return;}vec3 cb=texture2D(colTex2,vUv).rgb,cf=texture2D(colTex,vUv).rgb;
if(vCr.x!=0.||vCr.y!=0.){vec4 cr=texture2D(crTex,vUv);
 cb=mix(cb,nailSkin*cr.b*255.,cr.a*vCr.y);
 cf*=max(1.-cr.r*(1.-vCr.x),.08)/max(1.-cr.r,.15)*(1.-.22*max(-vCr.x,0.)*smoothstep(.13,.26,cr.g));}
vec3 nt=texture2D(nailTex,vUv).rgb;cb=mix(cb,nailSkin*nt.b*255.,nt.g*max((1.-smoothstep(0.,.15,vS))*smoothstep(.15,.4,normalize(vN).z),npose));
float sd=(nt.r*255.-128.)/12.,aw=clamp(fwidth(sd),.03,1.5),wn=max(1.-smoothstep(.5,.9,vS),npose);cb=mix(cb,nailCol,wn*clamp(.5-sd/aw,0.,1.));
float lw=nailLW*texture2D(nailE,vUv).r;cb*=1.-wn*min(lw/aw,1.)*clamp(.5-(abs(sd+lw*.5)-lw*.5)/aw,0.,1.);vec3 c=mix(cb,cf,vS);
float s=clamp(.8+.26*max(dot(normalize(vN),L),0.),0.,1.);c*=s;c=mix(c,vec3(1.,.78,.1),hl*vH*.4);gl_FragColor=vec4(c,opacity);}`;
const skinMat=back=>new THREE.ShaderMaterial({uniforms:{colTex:{value:back?TB:TF},colTex2:{value:TB},crTex:{value:TC},alphaTex:{value:TF},nailTex:{value:TN},nailE:{value:TE},npose:{value:0},nailCol:{value:NAILC},nailSkin:{value:NAILS},nailLW:{value:HD.nail.lw},opacity:{value:1},hl:{value:0},hlPart:{value:-10},L:{value:LIGHT}},vertexShader:VS,fragmentShader:FS,extensions:{derivatives:true}});
const HULL=HD.outw+.6;

function orient(geo,inside){
  geo.computeVertexNormals();const p=geo.attributes.position,n=geo.attributes.normal,ix=geo.index.array;
  let s=0;for(let i=0;i<ix.length;i+=21){const a=ix[i];const v=new THREE.Vector3().fromBufferAttribute(p,a),nn=new THREE.Vector3().fromBufferAttribute(n,a);s+=Math.sign(nn.dot(v.sub(inside(a))))}
  if(s<0){for(let i=0;i<ix.length;i+=3){const t=ix[i+1];ix[i+1]=ix[i+2];ix[i+2]=t}geo.index.needsUpdate=true;geo.computeVertexNormals()}
  return geo;
}

/* ======================================================================
   Doigts : une peau continue par doigt, portée par des os rigides.
   Chaque anneau de peau suit un os ; près d'une articulation il se partage entre les deux os
   (mélange par quaternions duaux : la peau plie sans se pincer ni s'allonger).
   ====================================================================== */
const DF=.92,DB=.7,DB_TIP=.58;   // épaisseur côté paume (pulpe) / côté dos (plus plat, ongle)
function chainRings(k){
  const segs=HD.segs[k],rings=[];let S0=0;const joints=[];
  segs.forEach((sg,i)=>{joints.push(S0);
    const n=[-sg.u[1],sg.u[0]];
    if(i===0){const w0=(sg.wl[0]+sg.wr[0])/2,CAP=7;
      for(let j=CAP;j>=1;j--){const th=j/CAP*Math.PI/2;rings.push({seg:0,t:-w0*.85*Math.sin(th),s:-w0*.85*Math.sin(th),wl:sg.wl[0],wr:sg.wr[0],f:Math.cos(th),a:sg.a,u:sg.u,n})}}
    sg.ts.forEach((t,j)=>{if(i>0&&j===0)return;rings.push({seg:i,t,s:S0+t,wl:sg.wl[j],wr:sg.wr[j],f:1,a:sg.a,u:sg.u,n,tip:sg.tip,tEnd:sg.ts[sg.ts.length-1]})});
    S0+=sg.ts[sg.ts.length-1]<sg.len&&!sg.tip?sg.len:(sg.tip?0:sg.len);
  });
  // poids des os : bone 0 = paume (ou base du pouce), bone i+1 = phalange i
  rings.forEach(r=>{const w=(r.wl+r.wr)/2||10;let m=0;joints.forEach((sj,j)=>{if(r.s>sj+1e-6)m=j+1});
    let best=null;joints.forEach((sj,j)=>{const z=Math.max(14,.6*w);if(Math.abs(r.s-sj)<z&&(!best||Math.abs(r.s-sj)<best.d))best={j,d:Math.abs(r.s-sj),z,sj}});
    if(best){r.b0=best.j;r.b1=best.j+1;r.w=smooth(-best.z,best.z,r.s-best.sj)}else{r.b0=m;r.b1=m;r.w=0}});
  return rings;
}
const RINGS={};ALL.forEach(k=>RINGS[k]=chainRings(k));
function tubeGeo(k,side){
  const rings=RINGS[k],M=16,pos=[],uv=[],axis=[],idx=[],ringOf=[];
  rings.forEach((r,ri)=>{
    // dos du bout du doigt aplati progressivement (lit de l'ongle), pulpe pleine côté paume
    const kb=r.tip?DB-(DB-DB_TIP)*smooth(.15,.5,r.t/r.tEnd):DB,dfr=DF*(r.wl+r.wr)/2,dbr=kb*(r.wl+r.wr)/2;
    for(let j=0;j<=M;j++){
      const ph=(side>0?-Math.PI/2:Math.PI/2)+Math.PI*j/M,s=Math.sin(ph),c=Math.cos(ph),w=s>=0?r.wr:r.wl,d=c>=0?dfr:dbr;
      const lat=w*r.f*s,dep=d*r.f*c,px=r.a[0]+r.u[0]*r.t+r.n[0]*lat,py=r.a[1]+r.u[1]*r.t+r.n[1]*lat;
      const v=toM(px,py,dep);pos.push(v.x,v.y,v.z);
      // la couleur vient de l'endroit exact du dessin (projection), y compris au bout du doigt : aucun étirement
      // sur les flancs du doigt, la couleur est prise un peu en retrait du bord dessiné (pas de traînées sur la tranche)
      const ut=r.t<0?Math.min(14,r.tEnd||14):(r.tip?Math.min(r.t,r.tEnd-(side<0?13:9)):r.t),ul=lat*(.82+.18*Math.abs(c)),qx=r.a[0]+r.u[0]*ut+r.n[0]*ul,qy=r.a[1]+r.u[1]*ut+r.n[1]*ul;
      uv.push(qx/HD.W,1-qy/HD.H);axis.push(toM(r.a[0]+r.u[0]*r.t,r.a[1]+r.u[1]*r.t,0));ringOf.push(ri);
    }});
  for(let r=0;r<rings.length-1;r++)for(let j=0;j<M;j++){const p0=r*(M+1)+j,p1=p0+1,q0=p0+M+1,q1=q0+1;idx.push(p0,q0,p1,p1,q0,q1)}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));g.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));g.setIndex(idx);
  orient(g,i=>axis[i]);
  g.userData.rest=Float32Array.from(g.attributes.position.array);g.userData.restN=Float32Array.from(g.attributes.normal.array);g.userData.ringOf=Int32Array.from(ringOf);
  return g;
}
const TUBE={};ALL.forEach(k=>TUBE[k]=[tubeGeo(k,1),tubeGeo(k,-1)]);

/* ---------- paume ---------- */
function b64arr(s,T){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new T(b.buffer)}
const PXY=b64arr(HD.palm.xy,Int16Array),PZF=b64arr(HD.palm.zf,Int16Array),PZB=b64arr(HD.palm.zb,Int16Array),PIX=b64arr(HD.palm.idx,Uint32Array);
const NP=HD.palm.n,ZS=HD.palm.zscale||1;
const thenarW=(x,y)=>{
  const ax=MCP_T[0]-CMC_IMG[0],ay=MCP_T[1]-CMC_IMG[1],L2=ax*ax+ay*ay,L=Math.sqrt(L2),dx=x-CMC_IMG[0],dy=y-CMC_IMG[1];
  const s=(dx*ax+dy*ay)/L2;let nx=-ay/L,ny=ax/L;if(nx*(500-CMC_IMG[0])+ny*(560-CMC_IMG[1])<0){nx=-nx;ny=-ny}
  const l=dx*nx+dy*ny;return smooth(-.12,.78,s)*(l>0?1-smooth(28,135,l):1)*(1-smooth(1.15,1.6,s)*smooth(10,60,l));
};
const PW=new Float32Array(NP);for(let i=0;i<NP;i++)PW[i]=thenarW(PXY[2*i],PXY[2*i+1]);
function palmGeo(side){
  const pos=new Float32Array(NP*3),uv=new Float32Array(NP*2);
  for(let i=0;i<NP;i++){const x=PXY[2*i],y=PXY[2*i+1],v=toM(x,y,(side>0?PZF[i]:-PZB[i])/ZS);pos.set([v.x,v.y,v.z],3*i);uv.set([x/HD.W,1-y/HD.H],2*i)}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setAttribute('uv',new THREE.BufferAttribute(uv,2));g.setIndex(new THREE.BufferAttribute(new Uint32Array(PIX),1));
  orient(g,i=>new THREE.Vector3(pos[3*i],pos[3*i+1],pos[3*i+2]-side*5));
  g.userData.rest=pos.slice();return g;
}
const PALM_RIM=[];for(let i=0;i<NP;i+=3)if(PZF[i]<=2*ZS)PALM_RIM.push(toM(PXY[2*i],PXY[2*i+1],0));

/* ---------- collisions ---------- */
const HG=HD.hgrid,HGF=b64arr(HG.hf,Int16Array),HGB=b64arr(HG.hb,Int16Array);
const palmH=(x,y)=>{const i=Math.round(x/HG.step),j=Math.round(y/HG.step);if(i<0||j<0||i>=HG.gw||j>=HG.gh)return null;const k=j*HG.gw+i;return HGF[k]||HGB[k]?[HGF[k],HGB[k]]:null};
const SEGW={};ALL.forEach(k=>SEGW[k]=HD.segs[k].map(sg=>{const w=sg.ts.map((_,i)=>(sg.wl[i]+sg.wr[i])/2).filter(v=>v>4);return w.reduce((a,b)=>a+b,0)/w.length/SC}));
// la vraie articulation de la base (tête du métacarpien) n'est pas au pli de la racine du doigt visible sur le dessin,
// mais ≈ 1,5 cm plus bas, sous le pli distal de la paume : le doigt pivote de là (sinon 1re phalange trop courte,
// les deux autres trop longues : le bout plonge dans la paume au lieu de s'y poser). Le dessin au repos ne change pas.
const DEEP={};ALL.forEach(k=>DEEP[k]=k==='pouce'?0:Math.hypot(HD.chains[k][0][0]-HD.mesh.chain[k][0][0],HD.chains[k][0][1]-HD.mesh.chain[k][0][1])/SC);
const MCPJ=k=>{const c=HD.mesh.chain[k][0];return toM(c[0],c[1],HD.mesh.jz[k][0])};

/* ======================================================================
   Peau v8 : UN maillage fermé pour toute la main (paume, doigts, pouce), sans raccord.
   Chaque sommet suit jusqu'à 4 os (paume, métacarpien du pouce, phalanges) avec des poids lisses ;
   le mélange se fait par quaternions duaux : la peau plie sans se pincer ni gonfler.
   ====================================================================== */
const MS=HD.mesh,MN=MS.n;
const MXYZ=b64arr(MS.xyz,Int16Array),MUVQ=b64arr(MS.uv,Int16Array),MBI=b64arr(MS.bi,Uint8Array),MBW=b64arr(MS.bw,Uint8Array),MPRT=b64arr(MS.part,Uint8Array);
const MREST=new Float32Array(3*MN),muv=new Float32Array(2*MN),mpart=new Float32Array(MN),midc=new Float32Array(3*MN);
for(let i=0;i<MN;i++){const v=toM(MXYZ[3*i]/MS.q,MXYZ[3*i+1]/MS.q,MXYZ[3*i+2]/MS.q);MREST[3*i]=v.x;MREST[3*i+1]=v.y;MREST[3*i+2]=v.z;
  muv[2*i]=MUVQ[2*i]/MS.q/HD.W;muv[2*i+1]=1-MUVQ[2*i+1]/MS.q/HD.H;mpart[i]=MPRT[i];midc[3*i]=MPRT[i]/8;midc[3*i+1]=MPRT[i]===1?0:1}
const MUVA=new THREE.BufferAttribute(muv,2),MPARTA=new THREE.BufferAttribute(mpart,1),MIDC=new THREE.BufferAttribute(midc,3);
const MINDEX=new THREE.BufferAttribute(MS.i32?b64arr(MS.idx,Uint32Array):b64arr(MS.idx,Uint16Array),1);
// passe « identité » : une partie nette par triangle (pas de mélange de couleurs d'un sommet à l'autre)
const NT=MINDEX.count/3,MIDF=new Float32Array(9*NT);
for(let t=0;t<NT;t++){const a=MPRT[MINDEX.array[3*t]],b=MPRT[MINDEX.array[3*t+1]],c=MPRT[MINDEX.array[3*t+2]],pp=(a===b||a===c)?a:(b===c?b:Math.min(a,b,c));
  for(let j=0;j<3;j++){MIDF[9*t+3*j]=pp/8;MIDF[9*t+3*j+1]=pp===1?0:1}}
const MIDFA=new THREE.BufferAttribute(MIDF,3);
// racines des doigts et du pouce sans « col » (gorge + bourrelet du volume du dessin) : déplacement en z, appliqué
// progressivement dès que la pose quitte celle du dessin (le dessin au repos reste exact au pixel près)
const MDZ=new Float32Array(MN);if(MS.dz){const d=b64arr(MS.dz,Int16Array);for(let i=0;i<MN;i++)MDZ[i]=d[i]/MS.q/SC}
let MRNZC=null;const rootBlend=f=>{const d0=PRESETS['Dessin'].f;let m=0;for(const k in d0)for(const a in d0[k])m=Math.max(m,Math.abs((f[k][a]||0)-d0[k][a]));return smooth(0,12,m)};
let MRNZ=null;const SKIN_ID=new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide});

/* ======================================================================
   Une main = une hiérarchie d'articulations + des peaux
   ====================================================================== */
const scene=new THREE.Scene();
const ID={paume:1,pouce:2,index:3,majeur:4,annulaire:5,auriculaire:6};
const idMats={};for(const k in ID)idMats[k]=new THREE.MeshBasicMaterial({color:new THREE.Color(ID[k]/8,k==='paume'?0:1,0),side:THREE.DoubleSide});
/* coque du contour. Hors pose du dessin (main entière seulement), elle s'efface là où elle ne fait que ressortir d'un pli
   (fente noire en dents de scie, « confettis ») : fragment de coque à moins de « push » devant la peau qu'il recouvre
   (profondeur lue dans la passe identité), quand la peau recouverte est la même partie, la paume sous un doigt (racine)
   ou le pouce et la paume (pli de l'éminence, pli de la MCP du pouce). Le vrai contour garde tout son poids : silhouette
   (pas de peau derrière), doigt sur doigt, pouce et doigt, et pouce posé devant la paume, toujours loin devant elle
   (écart ≥ 2 push mesuré dans pouce_ip80_cote) ; pas d'exception près du fond (elle laissait des éclats à l'embouchure des plis). */
const HULL_VS=`attribute float part;varying float vP;varying float vZ;void main(){vP=part;vec4 mv=modelViewMatrix*vec4(position,1.);vZ=-mv.z;gl_Position=projectionMatrix*mv;}`;
const HULL_FS=`uniform float opacity;uniform float push;uniform sampler2D tId;uniform sampler2D tDepth;uniform vec2 res;uniform float cn;uniform float cf;varying float vP;varying float vZ;
  float L(vec2 uv){float z=texture2D(tDepth,uv).r*2.-1.;return 2.*cn*cf/(cf+cn-z*(cf-cn));}
  void main(){if(push>0.){vec2 uv=gl_FragCoord.xy/res;vec4 c=texture2D(tId,uv);
    if(c.a>.5){float pb=floor(c.r*8.+.5),ph=floor(vP+.5);
      bool real=pb!=ph&&pb>1.5&&ph>1.5;   // doigt sur doigt, pouce et doigt
      if(!real&&L(uv)-vZ<push)discard;}}
    gl_FragColor=vec4(.067,.067,.067,opacity);}`;
const hullMatProto=()=>new THREE.ShaderMaterial({uniforms:{opacity:{value:1},push:{value:0},tId:{value:null},tDepth:{value:null},res:{value:new THREE.Vector2(1,1)},cn:{value:.5},cf:{value:500}},
  vertexShader:HULL_VS,fragmentShader:HULL_FS,side:THREE.BackSide,polygonOffset:true,polygonOffsetFactor:2,polygonOffsetUnits:4});
const HPUSH=1.8;   // recul de la coque (× épaisseur du contour)
function makeHand(skeletonOnly){
  const root=new THREE.Group(),mats=[],chainMats={},hullMat=hullMatProto(),meshes=[];mats.push(hullMat);
  const addSkin=(geos,key)=>{const f=skinMat(false),b=skinMat(true);mats.push(f,b);chainMats[key]=[f,b];if(key==='paume')[f,b].forEach(m=>m.side=THREE.DoubleSide);
    [[geos[0],f,false],[geos[1],b,false],[geos[2],hullMat,true],[geos[3],hullMat,true]].forEach(([g,m,h])=>{const me=new THREE.Mesh(g,m);me.frustumCulled=false;me.userData={hull:h,idMat:idMats[key]};root.add(me);meshes.push(me)})};
  let skin=null,skinMats=[];
  if(!skeletonOnly){
    // une seule matière : dessin paume devant, dessin dos derrière, fondus sur la tranche
    const f=skinMat(false);mats.push(f);skinMats=[f];
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(MREST.slice(),3));g.setAttribute('uv',MUVA);
    g.setAttribute('part',MPARTA);g.setAttribute('color',MIDC);g.setIndex(MINDEX);
    g.computeVertexNormals();if(!MRNZ){MRNZ=new Float32Array(MN);const nn=g.attributes.normal.array;for(let i=0;i<MN;i++)MRNZ[i]=nn[3*i+2];
      const gc=new THREE.BufferGeometry(),pc=MREST.slice();for(let i=0;i<MN;i++)pc[3*i+2]+=MDZ[i];gc.setAttribute('position',new THREE.BufferAttribute(pc,3));gc.setIndex(MINDEX);
      gc.computeVertexNormals();MRNZC=new Float32Array(MN);const nc=gc.attributes.normal.array;for(let i=0;i<MN;i++)MRNZC[i]=nc[3*i+2]}
    g.setAttribute('rnz',new THREE.BufferAttribute(MRNZ.slice(),1));
    g.setAttribute('crf',new THREE.BufferAttribute(new Int8Array(2*MN),2,true));   // plis et rides (piste R)
    const hg=new THREE.BufferGeometry();hg.setAttribute('position',new THREE.BufferAttribute(MREST.slice(),3));hg.setAttribute('part',MPARTA);hg.setIndex(MINDEX);
    const me=new THREE.Mesh(g,f),mh=new THREE.Mesh(hg,hullMat);me.frustumCulled=mh.frustumCulled=false;
    me.userData={hull:false,idMat:SKIN_ID};mh.userData={hull:true};root.add(me,mh);meshes.push(me,mh);
    const idg=new THREE.BufferGeometry();idg.setAttribute('position',new THREE.BufferAttribute(new Float32Array(9*NT),3));idg.setAttribute('color',MIDFA);
    const idm=new THREE.Mesh(idg,SKIN_ID);idm.visible=false;idm.frustumCulled=false;root.add(idm);skin={g,hg,idg,idm,key:'',hm:hullMat,sm:f,gR:0,crZ:true};
  }
  const joints={};
  ALL.forEach(k=>{
    const off=k==='pouce'?1:0,src=k==='pouce'?TCH.slice(1):HD.mesh.chain[k];   // doigts : chaîne corrigée (IPD glissée)
    const J=src.map((p,i)=>toM(p[0],p[1],i<HD.segs[k].length?HD.mesh.jz[k][i+off]:0));if(DEEP[k])J[0]=MCPJ(k);joints[k]=[];joints[k].J=J;
    let parent=root,prev=new THREE.Vector3();
    if(k==='pouce'){const c=new THREE.Group();c.position.copy(CMC);root.add(c);joints.cmc=c;parent=c;prev=CMC.clone()}
    HD.segs[k].forEach((sg,i)=>{const g=new THREE.Group();g.position.copy(J[i].clone().sub(prev));parent.add(g);joints[k].push(g);parent=g;prev=J[i]});
    const sg=HD.segs[k][HD.segs[k].length-1],te=sg.ts[sg.ts.length-1];
    const tip=new THREE.Object3D();tip.position.copy(toM(sg.a[0]+sg.u[0]*te*.9,sg.a[1]+sg.u[1]*te*.9,0).sub(prev));parent.add(tip);joints[k].tip=tip;
  });
  scene.add(root);
  return {root,joints,mats,chainMats,skin,skinMats,meshes};
}
const qa=(axis,deg)=>new THREE.Quaternion().setFromAxisAngle(axis,deg*D);
// pouce : le dessin montre sa pulpe ; MCP et IP plient vers l'avant et un peu en travers de la paume
const tAxis=(i,beta)=>AX.pouce[i].lat.clone().multiplyScalar(Math.sin(beta*D)).add(Z.clone().multiplyScalar(Math.cos(beta*D))).normalize();
const TFA=[tAxis(0,45),tAxis(1,55)];
/* ---------- base du pouce : trapézo-métacarpienne en selle (Hollister 1992, Imaeda 1994) ----------
   Deux axes FIXES, ni perpendiculaires entre eux ni aux os, et qui NE SE CROISENT PAS :
   - flexion/extension (« rapprocher », vers les doigts) dans le TRAPÈZE, donc par CMC ;
   - abduction/adduction palmaire (« avancer », en avant de la paume) dans la BASE DU 1er MÉTACARPIEN,
     donc décalée de TOFF vers le pouce. Le pouce n'a plus de centre de rotation unique : sa base glisse.
   Chaque axe est incliné de TFT / TAT sur l'os : la flexion comme l'abduction entraînent déjà un peu de
   pronation, comme l'articulation réelle (l'axe oblique en produit ≈ 25° à pleine opposition). */
const TFT=20*D,TAT=15*D,FEV=15*D,TOFF=.30;
// axe de flexion : incliné de TFT sur l'os (→ pronation) et de FEV vers la paume (→ en se rapprochant des
// doigts, le pouce passe DEVANT la paume au lieu de glisser dans son plan : la colonne du pouce est antérieure)
const E_FE=Z.clone().addScaledVector(LATM,Math.tan(FEV)).addScaledVector(UM,-Math.tan(TFT)).normalize();
const E_AA=LATM.clone().multiplyScalar(Math.cos(TAT)).addScaledVector(UM,-Math.sin(TAT)).normalize();
const P_FE=CMC,P_AA=CMC.clone().addScaledVector(UM,TOFF);
// Pronation : elle suit l'OPPOSITION, pas « avancer ». Elle démarre avec l'abduction palmaire mais ne culmine
// qu'une fois le pouce ramené vers les doigts (42° en abduction radiale → 99° en opposition, soit ≈ 57° d'écart ;
// les axes obliques en donnent déjà ≈ 25°, PRONA fournit le reste). Au repos (0,0) : aucune pronation.
let PRONA=34;
const pronOf=t=>{const a=clamp(t.av/LIMT.av[1],0,1),r=clamp(Math.max(t.rap,0)/LIMT.rap[1],0,1);
  return -PRONA*(a*(.35+.65*r)+.25*r*(1-a))};
const _pv=new THREE.Vector3();
function cmcPose(t,g){
  const qp=qa(UM,pronOf(t)),qb=qa(E_AA,t.av),qf=qa(E_FE,t.rap);
  g.quaternion.copy(qf).multiply(qb).multiply(qp);
  // axes non sécants : on applique les trois rotations au point CMC, chacune autour de SON axe
  _pv.copy(CMC).sub(P_AA).applyQuaternion(qp).add(P_AA);        // pronation, autour de l'axe du métacarpien
  _pv.sub(P_AA).applyQuaternion(qb).add(P_AA);                   // abduction, axe dans la base du métacarpien
  _pv.sub(P_FE).applyQuaternion(qf).add(P_FE);                   // flexion, axe dans le trapèze
  g.position.copy(_pv);
}
function setJoints(h,p){
  FING.forEach(k=>{const v=p.f[k],A=AX[k],j=h.joints[k];
    j[0].quaternion.copy(qa(Z,-(v.ab+convOf(k,v)+PAR[k]))).multiply(qa(A[0].lat,v.mcp));
    j[1].quaternion.copy(qa(A[1].lat,v.pip));j[2].quaternion.copy(qa(A[2].lat,v.dip))});
  const t=p.f.pouce,j=h.joints.pouce;
  cmcPose(t,h.joints.cmc);j[0].quaternion.copy(qa(TFA[0],t.mcp));j[1].quaternion.copy(qa(TFA[1],t.ip));
}
/* ---------- peau : mélange par quaternions duaux, anneau par anneau ---------- */
const _inv=new THREE.Matrix4(),_m=new THREE.Matrix4(),_q=new THREE.Quaternion(),_t=new THREE.Vector3(),_s=new THREE.Vector3();
function boneDQ(h,k){
  // transformations « repos -> posé » de chaque os, dans le repère de la main
  _inv.copy(h.root.matrixWorld).invert();const out=[];
  const list=[k==='pouce'?{g:h.joints.cmc,J:CMC}:null,...h.joints[k].map((g,i)=>({g,J:h.joints[k].J[i]}))];
  list.forEach(b=>{let q=new THREE.Quaternion(),t=new THREE.Vector3();
    if(b){_m.multiplyMatrices(_inv,b.g.matrixWorld);_m.multiply(new THREE.Matrix4().makeTranslation(-b.J.x,-b.J.y,-b.J.z));_m.decompose(t,q,_s)}
    // quaternion dual : réel q, dual 0.5 * (t,0) * q
    const d=[.5*(t.x*q.w+t.y*q.z-t.z*q.y),.5*(-t.x*q.z+t.y*q.w+t.z*q.x),.5*(t.x*q.y-t.y*q.x+t.z*q.w),-.5*(t.x*q.x+t.y*q.y+t.z*q.z)];
    out.push({r:[q.x,q.y,q.z,q.w],d})});
  return out;
}
function ringXform(dq,r){
  const a=dq[r.b0],b=dq[r.b1],w=r.w;let s=1;if(a.r[0]*b.r[0]+a.r[1]*b.r[1]+a.r[2]*b.r[2]+a.r[3]*b.r[3]<0)s=-1;
  const R=[0,1,2,3].map(i=>a.r[i]*(1-w)+s*b.r[i]*w),Dd=[0,1,2,3].map(i=>a.d[i]*(1-w)+s*b.d[i]*w);
  const n=Math.hypot(...R);for(let i=0;i<4;i++){R[i]/=n;Dd[i]/=n}
  // translation = 2 * dual * conj(réel)
  const [x,y,z,wq]=R,[dx,dy,dz,dw]=Dd;
  const tx=2*(-dw*x+dx*wq-dy*z+dz*y),ty=2*(-dw*y+dx*z+dy*wq-dz*x),tz=2*(-dw*z-dx*y+dy*x+dz*wq);
  return {q:new THREE.Quaternion(x,y,z,wq),t:new THREE.Vector3(tx,ty,tz)};
}
function skinTube(h,k,key){
  const T=h.tubes[k];if(T.key===key)return;T.key=key;
  const dq=boneDQ(h,k),X=RINGS[k].map(r=>ringXform(dq,r)),v=new THREE.Vector3(),e=HULL/SC;
  [[T.f,T.hf],[T.b,T.hb]].forEach(([g,hg])=>{
    const rest=g.userData.rest,rn=g.userData.restN,ro=g.userData.ringOf,p=g.attributes.position.array,n=g.attributes.normal.array,hp=hg.attributes.position.array;
    for(let i=0;i<ro.length;i++){const x=X[ro[i]],o=3*i;
      v.set(rest[o],rest[o+1],rest[o+2]).applyQuaternion(x.q).add(x.t);p[o]=v.x;p[o+1]=v.y;p[o+2]=v.z;
      v.set(rn[o],rn[o+1],rn[o+2]).applyQuaternion(x.q);n[o]=v.x;n[o+1]=v.y;n[o+2]=v.z;
      hp[o]=p[o]+v.x*e;hp[o+1]=p[o+1]+v.y*e;hp[o+2]=p[o+2]+v.z*e}
    g.attributes.position.needsUpdate=true;g.attributes.normal.needsUpdate=true;hg.attributes.position.needsUpdate=true;
  });
}
// peau de la paume : suit la paume, le pouce (éminence thénar) et la base des doigts (jointures, palmures)
const PFW=b64arr(HD.fw,Uint8Array);
function blendDQ(list){ // [[dq,w],...] -> {q,t}
  const R=[0,0,0,0],Dd=[0,0,0,0];const ref=list[0][0].r;
  list.forEach(([dq,w])=>{const s=dq.r[0]*ref[0]+dq.r[1]*ref[1]+dq.r[2]*ref[2]+dq.r[3]*ref[3]<0?-1:1;for(let i=0;i<4;i++){R[i]+=s*w*dq.r[i];Dd[i]+=s*w*dq.d[i]}});
  const n=Math.hypot(...R);for(let i=0;i<4;i++){R[i]/=n;Dd[i]/=n}
  const [x,y,z,wq]=R,[dx,dy,dz,dw]=Dd;
  return {q:new THREE.Quaternion(x,y,z,wq),t:new THREE.Vector3(2*(-dw*x+dx*wq-dy*z+dz*y),2*(-dw*y+dx*z+dy*wq-dz*x),2*(-dw*z-dx*y+dy*x+dz*wq))};
}
const DQ_ID={r:[0,0,0,1],d:[0,0,0,0]};
const PINF=[];for(let i=0;i<NP;i++){let wt=PW[i];const wf=[0,1,2,3].map(j=>PFW[4*i+j]/255);let tot=wt+wf[0]+wf[1]+wf[2]+wf[3];
  if(tot<=1e-3)continue;if(tot>1){wt/=tot;for(let j=0;j<4;j++)wf[j]/=tot;tot=1}PINF.push([i,1-tot,wt,wf[0],wf[1],wf[2],wf[3]])}
function skinPalm(h,p){
  const key=JSON.stringify([p.f.pouce.av,p.f.pouce.rap,...FING.map(k=>[p.f[k].mcp,p.f[k].ab,p.f[k].pip])]);if(h.palm.key===key)return;h.palm.key=key;
  const B=[DQ_ID,boneDQ(h,'pouce')[0],...FING.map(k=>boneDQ(h,k)[1])];
  // alignement des signes une fois pour toutes (référence : identité)
  B.forEach(b=>{if(b.r[3]<0){b.r=b.r.map(x=>-x);b.d=b.d.map(x=>-x)}});
  const R=new Float64Array(4),Dd=new Float64Array(4);
  [[h.palm.pf,h.palm.hf],[h.palm.pb,h.palm.hb]].forEach(([g,hg])=>{
    const rest=g.userData.rest,pa=g.attributes.position.array;pa.set(rest);
    for(const inf of PINF){const i=inf[0],o=3*i;R.fill(0);Dd.fill(0);
      for(let b=0;b<6;b++){const w=inf[b+1];if(w<=0)continue;const q=B[b];for(let c=0;c<4;c++){R[c]+=w*q.r[c];Dd[c]+=w*q.d[c]}}
      const n=Math.hypot(R[0],R[1],R[2],R[3]),x=R[0]/n,y=R[1]/n,z=R[2]/n,w=R[3]/n,dx=Dd[0]/n,dy=Dd[1]/n,dz=Dd[2]/n,dw=Dd[3]/n;
      const tx=2*(-dw*x+dx*w-dy*z+dz*y),ty=2*(-dw*y+dx*z+dy*w-dz*x),tz=2*(-dw*z-dx*y+dy*x+dz*w);
      const px=rest[o],py=rest[o+1],pz=rest[o+2];
      // rotation du point par le quaternion (x,y,z,w)
      const ix=w*px+y*pz-z*py,iy=w*py+z*px-x*pz,iz=w*pz+x*py-y*px,iw=-x*px-y*py-z*pz;
      pa[o]=ix*w+iw*-x+iy*-z-iz*-y+tx;pa[o+1]=iy*w+iw*-y+iz*-x-ix*-z+ty;pa[o+2]=iz*w+iw*-z+ix*-y-iy*-x+tz}
    g.attributes.position.needsUpdate=true;g.computeVertexNormals();
    const nn=g.attributes.normal.array,hp=hg.attributes.position.array,e=HULL/SC;for(let i=0;i<3*NP;i++)hp[i]=pa[i]+nn[i]*e;
    hg.attributes.position.needsUpdate=true;
  });
}
function boneDQ1(h,g,J){
  let q=new THREE.Quaternion(),t=new THREE.Vector3();
  _m.multiplyMatrices(_inv,g.matrixWorld);_m.multiply(new THREE.Matrix4().makeTranslation(-J.x,-J.y,-J.z));_m.decompose(t,q,_s);
  if(q.w<0){q.x=-q.x;q.y=-q.y;q.z=-q.z;q.w=-q.w}
  return {r:[q.x,q.y,q.z,q.w],d:[.5*(t.x*q.w+t.y*q.z-t.z*q.y),.5*(-t.x*q.z+t.y*q.w+t.z*q.x),.5*(t.x*q.y-t.y*q.x+t.z*q.w),-.5*(t.x*q.x+t.y*q.y+t.z*q.z)]};
}
/* ---------- déformeur en arc aux articulations charnières (MCP, IPP, IPD ; MCP et IP du pouce) ----------
   Dans la zone d'une articulation, la section d'abscisse tau (0 = début de zone, 1 = fin) tourne de tau·θ autour
   d'un centre Q(tau) qui glisse : chaque fibre de peau devient un arc de cercle (rayon jamais négatif côté paume :
   pas de repli, pas de fente noire, pas de creux), et en fin de zone la section rejoint exactement l'os distal
   (Q = centre de l'articulation). Q - C = h·[(tau-1)·u + (tau·g(tau·θ) - g(θ))·f], g(x) = 2/x - cot(x/2),
   u = axe du doigt, f = côté de la flexion, h = demi-largeur de zone (grande côté paume, petite côté dos).
   Chaque chaîne (pouce, doigt) ajoute son déplacement ; la base du pouce (trapézo-métacarpienne) reste en quaternions duaux. */
const ARC=MS.arc,ACH=b64arr(ARC.c,Uint8Array),AHM=b64arr(ARC.hm,Uint8Array),ASH=b64arr(ARC.s,Uint16Array),ATA=b64arr(ARC.t,Uint16Array),CHN=['pouce',...FING];
const ARCJ={};CHN.forEach(k=>ARCJ[k]=ARC.joints[k].map((p,j)=>{
  const c=k==='pouce'?HD.mesh.chain.pouce[j+1]:HD.mesh.chain[k][j],z=k==='pouce'?HD.mesh.jz.pouce[j+1]:HD.mesh.jz[k][j];
  const C=toM(c[0],c[1],z);
  return {C,u:new THREE.Vector3(...p.u),f0:new THREE.Vector3(...p.f),rp:p.rp/SC,rd:p.rd/SC,hp:p.hp/SC,hd:p.hd/SC,kf:p.kf}}));
// demi-largeur de zone de chaque sommet (selon sa profondeur côté paume / côté dos) : chaîne principale (3 art.), MCP de la 2e
const AH1=new Float32Array(3*MN),AH2=new Float32Array(MN);
{const hOf=(J,o)=>{const d=(MREST[o]-J.C.x)*J.f0.x+(MREST[o+1]-J.C.y)*J.f0.y+(MREST[o+2]-J.C.z)*J.f0.z;return Math.max(J.hd+(J.hp-J.hd)*smooth(-J.rd,J.rp,d),J.kf*d)};
  for(let i=0;i<MN;i++){const c1=ACH[2*i],c2=ACH[2*i+1];
    if(c1)ARCJ[CHN[c1-1]].forEach((J,j)=>AH1[3*i+j]=hOf(J,3*i));if(c1>1)AH1[3*i]=AHM[2*i]/2/SC;if(c2>1)AH2[i]=AHM[2*i+1]/2/SC}}

/* ---------- piste R : les rides et les plis suivent la flexion ----------
   Côté DOS la peau s'étire quand l'articulation plie (+0,35 %/° à l'IPP, 0,29 à la MCP, 0,20 à l'IPD, ≈30 % en tout) :
   les rides dessinées s'écartent (la peau porte sa texture) puis s'effacent, et la phalange pliée a le dos lisse et
   tendu (photos 2374, 2375, 2360). Côté PAUME le pli de flexion se creuse, s'assombrit et s'élargit ; en
   hyperextension c'est l'inverse des deux côtés. Le pli thénar suit le pouce qui se rapproche ou s'oppose.
   On envoie au shader, par sommet, l'effacement e du trait du dessin : crf.x côté paume (< 0 : creusé), crf.y côté
   dos (> 0 : effacé) ; texCrease dit OÙ sont les traits. Au repos tous les angles valent 0, donc e = 0 partout et le
   multiplicateur vaut exactement 1 : le dessin reste exact au pixel près.
   Chaque sommet retient les DEUX articulations qui le commandent le plus (bosse le long de l'os, refermée de côté). */
// Le dos s'étire de 0,29 %/° à la MCP, 0,35 à l'IPP, 0,20 à l'IPD (≈30 % en tout). La réserve de peau plissée d'une
// jointure est à la mesure de ce qu'elle doit rendre : l'effacement est donc la part de course parcourue, ×1,1
// (le dos est lisse un peu avant la butée, comme sur les photos 2374 et 2375).
const CRMX=[95,110,85],CRMXT=[55,80];     // flexion maximale : MCP / IPP / IPD, puis MCP / IP du pouce (°)
const CRJ=[],crAdd=(C,u,f0,sp,sq,sd,wp,wd,drv)=>{const U=u.clone().normalize();
  CRJ.push({C,u:U,lat:U.clone().cross(f0).normalize(),sp:sp/SC,sq:sq/SC,sd:sd/SC,wp:wp/SC,wd:wd/SC,drv})};
FING.forEach(k=>ARCJ[k].forEach((J,j)=>{
  const g=HD.segs[k][j],n=g.wl.length,hw=g.wl.reduce((s,v,i)=>s+(v+g.wr[i])/2,0)/n;   // demi-largeur du doigt (px)
  const key=['mcp','pip','dip'][j];
  crAdd(J.C,J.u,J.f0,1.7*hw,1.25*hw,1.15*hw,j?1.3*hw:2.2*hw,1.3*hw,
    f=>{const a=f?f[k][key]||0:0,t=1.1*a/CRMX[j];return [clamp(t,-.6,1),-clamp(t,-.5,1)]})}));
['mcp','ip'].forEach((key,j)=>{const J=ARCJ.pouce[j],g=HD.segs.pouce[j],
   hw=g.wl.reduce((s,v,i)=>s+(v+g.wr[i])/2,0)/g.wl.length;
  crAdd(J.C,J.u,J.f0,1.6*hw,1.2*hw,1.1*hw,1.4*hw,1.3*hw,
    f=>{const a=f?f.pouce[key]||0:0,t=1.1*a/CRMXT[j];return [clamp(t,-.6,1),-clamp(t,-.5,1)]})});
// pli thénar : le plus constant de la paume (grande mobilité de la CMC). Son arc passe à ≈0,95 × la longueur du
// métacarpien du pouce sur le côté ulnaire de celui-ci : on centre là une tache large, menée par « rapprocher » et « avancer ».
{const n=LATM.clone().multiplyScalar(LATM.dot(toM(500,560,0).clone().sub(CMC))>0?1:-1);
 crAdd(CMC.clone().addScaledVector(UM,.45*193.6/SC).addScaledVector(n,.95*193.6/SC),UM,Z,170,170,170,120,120,
   f=>[0,-clamp((Math.max(f?f.pouce.rap:0,0)*.9+Math.max(f?f.pouce.av:0,0)*.45)/55,0,1)])}
const CRN=CRJ.length,CRA=new Float32Array(2*CRN);
const CRIP=new Uint8Array(2*MN),CRWP=new Uint8Array(2*MN),CRID=new Uint8Array(2*MN),CRWD=new Uint8Array(2*MN);
{const bump=(J,x,y,z,dor)=>{const rx=x-J.C.x,ry=y-J.C.y,rz=z-J.C.z;
   const t=rx*J.u.x+ry*J.u.y+rz*J.u.z,l=rx*J.lat.x+ry*J.lat.y+rz*J.lat.z,s=dor?J.sd:(t<0?J.sp:J.sq),q=t/s,w=dor?J.wd:J.wp;
   return q*q>9?0:Math.exp(-q*q)*(1-smooth(w,1.9*w,Math.abs(l)))};
 for(let i=0;i<MN;i++){const x=MREST[3*i],y=MREST[3*i+1],z=MREST[3*i+2];
   for(let d=0;d<2;d++){let b0=0,i0=0,b1=0,i1=0;
     for(let j=0;j<CRN;j++){const v=bump(CRJ[j],x,y,z,d===1);if(v>b0){b1=b0;i1=i0;b0=v;i0=j}else if(v>b1){b1=v;i1=j}}
     const I=d?CRID:CRIP,W=d?CRWD:CRWP;I[2*i]=i0;I[2*i+1]=i1;W[2*i]=255*Math.min(b0,1);W[2*i+1]=255*Math.min(b1,1)}}}
const gArc=x=>Math.abs(x)<1e-3?x/6+x*x*x/360:2/x-1/Math.tan(x/2);
function arcState(J,q){ // décomposition « pivot + torsion » autour de l'axe u du doigt
  const u=J.u,tw=q.x*u.x+q.y*u.y+q.z*u.z,tn=Math.hypot(tw,q.w)||1;
  const twq=new THREE.Quaternion(u.x*tw/tn,u.y*tw/tn,u.z*tw/tn,q.w/tn),sw=q.clone().multiply(twq.clone().conjugate());
  if(sw.w<0){sw.x=-sw.x;sw.y=-sw.y;sw.z=-sw.z;sw.w=-sw.w}
  const vs=Math.hypot(sw.x,sw.y,sw.z),th=2*Math.atan2(vs,sw.w),n=vs>1e-9?new THREE.Vector3(sw.x/vs,sw.y/vs,sw.z/vs):new THREE.Vector3(0,0,1);
  return {C:J.C,u,n,f:n.clone().cross(u),th,al:2*Math.atan2(tw,q.w),gth:gArc(th),q:q.clone()};
}
function rotAx(n,a,v){const c=Math.cos(a),s=Math.sin(a),d=(n.x*v[0]+n.y*v[1]+n.z*v[2])*(1-c),cx=n.y*v[2]-n.z*v[1],cy=n.z*v[0]-n.x*v[2],cz=n.x*v[1]-n.y*v[0];
  v[0]=v[0]*c+cx*s+n.x*d;v[1]=v[1]*c+cy*s+n.y*d;v[2]=v[2]*c+cz*s+n.z*d}
function arcApply(S,tau,h,p){ // p : [x,y,z] modifié sur place
  if(tau<=0)return;const C=S.C,r=[p[0]-C.x,p[1]-C.y,p[2]-C.z];
  if(tau>=1){const q=S.q,x=q.x,y=q.y,z=q.z,w=q.w,ix=w*r[0]+y*r[2]-z*r[1],iy=w*r[1]+z*r[0]-x*r[2],iz=w*r[2]+x*r[1]-y*r[0],iw=-x*r[0]-y*r[1]-z*r[2];
    p[0]=C.x+ix*w-iw*x-iy*z+iz*y;p[1]=C.y+iy*w-iw*y-iz*x+ix*z;p[2]=C.z+iz*w-iw*z-ix*y+iy*x;return}
  if(Math.abs(S.al)>1e-6)rotAx(S.u,S.al*tau,r);
  const ph=S.th*tau,F=tau*gArc(ph)-S.gth,a=h*(tau-1),b=h*F,u=S.u,f=S.f;
  const ox=a*u.x+b*f.x,oy=a*u.y+b*f.y,oz=a*u.z+b*f.z;r[0]-=ox;r[1]-=oy;r[2]-=oz;rotAx(S.n,ph,r);
  p[0]=C.x+ox+r[0];p[1]=C.y+oy+r[1];p[2]=C.z+oz+r[2];
}
function dqApply(b,s,p){ // base du pouce : mélange (paume, métacarpien) par quaternions duaux, part s du métacarpien
  // signes (essai C) : le métacarpien est ramené dans l'hémisphère de l'identité (boneDQ1 : w ≥ 0), donc aligné sur l'os
  // principal du sommet quel qu'il soit : le mélange prend toujours le court chemin (pas de peau retournée)
  if(s<=0)return;if(b.r[3]<0)b={r:b.r.map(x=>-x),d:b.d.map(x=>-x)};const R0=s*b.r[0],R1=s*b.r[1],R2=s*b.r[2],R3=1-s+s*b.r[3],n=Math.hypot(R0,R1,R2,R3);
  const x=R0/n,y=R1/n,z=R2/n,w=R3/n,dx=s*b.d[0]/n,dy=s*b.d[1]/n,dz=s*b.d[2]/n,dw=s*b.d[3]/n;
  const tx=2*(-dw*x+dx*w-dy*z+dz*y),ty=2*(-dw*y+dx*z+dy*w-dz*x),tz=2*(-dw*z-dx*y+dy*x+dz*w),px=p[0],py=p[1],pz=p[2];
  const ix=w*px+y*pz-z*py,iy=w*py+z*px-x*pz,iz=w*pz+x*py-y*px,iw=-x*px-y*py-z*pz;
  p[0]=ix*w+iw*-x+iy*-z-iz*-y+tx;p[1]=iy*w+iw*-y+iz*-x-ix*-z+ty;p[2]=iz*w+iw*-z+ix*-y-iy*-x+tz;
}
function skinMesh(h,key,f){
  const S_=h.skin;if(S_.key===key)return;S_.key=key;
  const gR=f?rootBlend(f):0;
  if(gR!==S_.gR){S_.gR=gR;S_.sm.uniforms.npose.value=gR;const rz=S_.g.attributes.rnz;for(let i=0;i<MN;i++)rz.array[i]=MRNZ[i]+(MRNZC[i]-MRNZ[i])*gR;rz.needsUpdate=true}
  _inv.copy(h.root.matrixWorld).invert();
  const ST={};CHN.forEach(k=>ST[k]=ARCJ[k].map((J,j)=>arcState(J,h.joints[k][j].quaternion)));
  const BC=boneDQ1(h,h.joints.cmc,CMC),pa=S_.g.attributes.position.array,p=[0,0,0],K=1/65535;
  pa.set(MREST);if(gR)for(let i=0;i<MN;i++)pa[3*i+2]+=gR*MDZ[i];   // racines sans col (voir MDZ)
  for(let i=0;i<MN;i++){const c1=ACH[2*i];if(!c1)continue;
    const o=3*i,c2=ACH[2*i+1],x0=MREST[o],y0=MREST[o+1],z0=pa[o+2];let dx=0,dy=0,dz=0;
    for(let c=0;c<2;c++){const ch=c?c2:c1;if(!ch)continue;const S=ST[CHN[ch-1]],sh=ASH[2*i+c]*K;p[0]=x0;p[1]=y0;p[2]=z0;
      if(c===0){const ta=ATA[2*i]*K,tb=ATA[2*i+1]*K;
        if(ch===1){arcApply(S[1],tb,AH1[o+1],p);arcApply(S[0],ta,AH1[o],p);dqApply(BC,sh,p)}
        else{arcApply(S[2],tb,AH1[o+2],p);arcApply(S[1],ta,AH1[o+1],p);arcApply(S[0],sh,AH1[o],p)}}
      else if(ch===1)dqApply(BC,sh,p);else arcApply(S[0],sh,AH2[i],p);
      dx+=p[0]-x0;dy+=p[1]-y0;dz+=p[2]-z0}
    pa[o]=x0+dx;pa[o+1]=y0+dy;pa[o+2]=z0+dz}
  // plis et rides (piste R) : effacement du trait dessiné, côté paume et côté dos, pour chaque sommet
  let crAny=false;for(let j=0;j<CRN;j++){const v=CRJ[j].drv(f);CRA[2*j]=v[0];CRA[2*j+1]=v[1];if(v[0]||v[1])crAny=true}
  if(crAny||!S_.crZ){S_.crZ=!crAny;const cf=S_.g.attributes.crf.array;
    for(let i=0;i<MN;i++){const q=2*i;
      const pp=(CRWP[q]*CRA[2*CRIP[q]+1]+CRWP[q+1]*CRA[2*CRIP[q+1]+1])*.498,dd=(CRWD[q]*CRA[2*CRID[q]]+CRWD[q+1]*CRA[2*CRID[q+1]])*.498;
      cf[q]=pp<-127?-127:pp>127?127:pp;cf[q+1]=dd<-127?-127:dd>127?127:dd}
    S_.g.attributes.crf.needsUpdate=true}
  S_.g.attributes.position.needsUpdate=true;S_.g.computeVertexNormals();
  const nn=S_.g.attributes.normal.array,hp=S_.hg.attributes.position.array,e=HULL/SC;for(let i=0;i<3*MN;i++)hp[i]=pa[i]+nn[i]*e;
  S_.hg.attributes.position.needsUpdate=true;
  const ip=S_.idg.attributes.position.array,ix=MINDEX.array;for(let t=0;t<3*NT;t++){const v=3*ix[t];ip[3*t]=pa[v];ip[3*t+1]=pa[v+1];ip[3*t+2]=pa[v+2]}
  S_.idg.attributes.position.needsUpdate=true;
}
function applyPose(h,p,light){
  setJoints(h,p);
  if(light){h.root.updateMatrixWorld(true);return}
  h.root.quaternion.fromArray(p.q);h.root.position.fromArray(p.pos);h.root.scale.x=S.gauche?-1:1;h.root.updateMatrixWorld(true);
  skinMesh(h,JSON.stringify(p.f),p.f);
}
function setLook(h,op){h.mats.forEach(m=>{if(m.uniforms)m.uniforms.opacity.value=op;else m.opacity=op;m.transparent=op<1;m.depthWrite=op>=1})}
function lerpF(a,b,t){const o=clone(a);for(const k in o)for(const j in o[k])o[k][j]=a[k][j]+(b[k][j]-a[k][j])*t;return o}
function lerpPose(a,b,t){const o=clone(a);o.f=lerpF(a.f,b.f,t);o.q=new THREE.Quaternion().fromArray(a.q).slerp(new THREE.Quaternion().fromArray(b.q),t).toArray();o.pos=a.pos.map((v,i)=>v+(b.pos[i]-v)*t);return o}

/* ======================================================================
   La main « réelle » ne se traverse pas, et reste dans des postures humaines
   ====================================================================== */
const probe=makeHand(true);probe.root.visible=false;
function segLocal(h,k,i){const g=h.joints[k][i],next=h.joints[k][i+1]||h.joints[k].tip;return[g.getWorldPosition(new THREE.Vector3()),next.getWorldPosition(new THREE.Vector3())]}
function ssd(p1,q1,p2,q2){const d1=q1.clone().sub(p1),d2=q2.clone().sub(p2),r=p1.clone().sub(p2),a=d1.dot(d1),e=d2.dot(d2),f=d2.dot(r);let s,t;
  const c=d1.dot(r),b=d1.dot(d2),den=a*e-b*b;s=den>1e-9?clamp((b*f-c*e)/den,0,1):0;t=(b*s+f)/e;
  if(t<0){t=0;s=clamp(-c/a,0,1)}else if(t>1){t=1;s=clamp((b-c)/a,0,1)}
  return p1.clone().addScaledVector(d1,s).distanceTo(p2.clone().addScaledVector(d2,t))}
const SOFT=12;
function penetration(f){
  const h=probe;applyPose(h,{f,q:[0,0,0,1],pos:[0,0,0]},true);
  const segs={};ALL.forEach(k=>segs[k]=HD.segs[k].map((_,i)=>segLocal(h,k,i)));
  let pen=0;const tol=1.5/SC;
  // 1. pas d'enfoncement dans la paume (tissus mous : un peu d'appui permis)
  ALL.forEach(k=>segs[k].forEach(([a,b],i)=>{
    if(k!=='pouce'&&i===0)return;const r=SEGW[k][i]*.85;
    [.25,.6,1].forEach(fr=>{const q=a.clone().lerp(b,fr),x=q.x*SC+CX,y=-q.y*SC+CY;
      if(k==='pouce'&&thenarW(x,y)>.6)return;
      const hh=palmH(x,y);if(!hh)return;const z=q.z*SC,rp=r*SC,front=(hh[0]-SOFT)-(z-rp),back=(z+rp)+hh[1]-SOFT;
      if(front>0&&back>0)pen+=Math.min(front,back)})}));
  // la partie cachée de la 1re phalange (dans la paume) ne compte pas entre doigts
  const vis=k=>segs[k].map(([a,b],i)=>i?[a,b]:[a.clone().lerp(b,DEEP[k]/(DEEP[k]+HD.segs[k][0].len/SC)),b]);
  
  // 2. le pouce ne traverse pas les doigts
  segs.pouce.forEach(([a,b],i)=>FING.forEach(k=>vis(k).forEach(([c,d],j)=>{const o=(SEGW.pouce[i]+SEGW[k][j])*.8-ssd(a,b,c,d)-tol;if(o>0)pen+=o*SC})));
  // 3. doigts voisins : ils peuvent se toucher, pas se traverser ; un doigt ne se replie pas dans lui-même
  for(let n=0;n<3;n++){const A=vis(FING[n]),B=vis(FING[n+1]);A.forEach(([a,b],i)=>B.forEach(([c,d],j)=>{const o=(SEGW[FING[n]][i]+SEGW[FING[n+1]][j])*.68-ssd(a,b,c,d)-tol;if(o>0)pen+=o*SC}))}
  FING.forEach(k=>{const [a,b]=segs[k][2],[c,d]=vis(k)[0];const o=(SEGW[k][2]+SEGW[k][0])*.8-ssd(a,b,c,d)-tol;if(o>0)pen+=o*SC});
  // 4. posture du pouce : jamais le bout tourné vers le poignet
  const [ta,tb]=segs.pouce[1],[pa,pb]=segs.pouce[0],dd=tb.clone().sub(ta).normalize(),dp=pb.clone().sub(pa).normalize();
  if(dd.y<-.45)pen+=(-.45-dd.y)*60;if(dp.y<-.2)pen+=(-.2-dp.y)*60;
  return pen;
}
function solve(fromF,toF){
  const ref=Math.max(penetration(fromF)+.05,.5);
  if(penetration(toF)<=ref)return toF;
  let lo=0,hi=1;for(let i=0;i<8;i++){const m=(lo+hi)/2;if(penetration(lerpF(fromF,toF,m))<=ref)lo=m;else hi=m}
  let cur=lerpF(fromF,toF,lo);
  for(const k in toF)for(const j in toF[k]){if(Math.abs(toF[k][j]-cur[k][j])<.5)continue;
    const tgt=clone(cur);tgt[k][j]=toF[k][j];if(penetration(tgt)<=ref){cur=tgt;continue}
    let a=0,b=1;const v0=cur[k][j];for(let i=0;i<6;i++){const m=(a+b)/2;tgt[k][j]=v0+(toF[k][j]-v0)*m;if(penetration(tgt)<=ref)a=m;else b=m}
    cur[k][j]=v0+(toF[k][j]-v0)*a}
  return cur;
}
function thumbReach(f,targetFn){
  let cur=clone(f);const ref=Math.max(penetration(cur)+.05,.5),V=()=>new THREE.Vector3();
  const at=ff=>{applyPose(probe,{f:ff,q:[0,0,0,1],pos:[0,0,0]},true);return{tip:probe.joints.pouce.tip.getWorldPosition(V()),tgt:targetFn(probe)}};
  const cost=ff=>{const r=at(ff);return r.tip.distanceTo(r.tgt)};
  let best=cost(cur);
  for(const step of [12,6,3,1.5])for(let loop=0;loop<10;loop++){let moved=false;
    for(const j of ['av','rap','mcp','ip'])for(const sg of [1,-1]){const c={f:clone(cur)};c.f.pouce[j]=clamp(c.f.pouce[j]+sg*step,...LIMT[j]);constrain(c);
      if(c.f.pouce[j]===cur.pouce[j])continue;const v=cost(c.f);if(v<best-1e-3&&penetration(c.f)<=ref){cur=c.f;best=v;moved=true}}
    if(!moved)break}
  return cur;
}
const W3=()=>new THREE.Vector3();
const REACH={
  'O':h=>h.joints.index.tip.getWorldPosition(W3()),
  'Pince':h=>h.joints.index.tip.getWorldPosition(W3()),
  'Poing serré':h=>h.joints.index[1].getWorldPosition(W3()).lerp(h.joints.majeur[2].getWorldPosition(W3()),.5),
  'Index (1)':h=>h.joints.majeur[1].getWorldPosition(W3()).lerp(h.joints.annulaire[2].getWorldPosition(W3()),.5),
  'V (2)':h=>h.joints.annulaire[1].getWorldPosition(W3()).lerp(h.joints.auriculaire[2].getWorldPosition(W3()),.5)
};
// passage d'une configuration à une autre : le pouce s'écarte d'abord (il ne bloque plus les doigts), puis chaque doigt,
// puis le pouce rejoint sa place. Le résultat ne dépend donc pas de la pose précédente.
function settle(fromF,toF){let cur=clone(fromF);
  {const tgt=clone(cur);tgt.pouce={av:0,rap:-10,mcp:0,ip:0};cur=solve(cur,tgt)}
  [...FING,'pouce'].forEach(k=>{const tgt=clone(cur);tgt[k]=clone(toF[k]);cur=solve(cur,tgt)});return cur}

/* ======================================================================
   Scène et rendu (couleurs + traits intérieurs là où une partie passe devant une autre)
   ====================================================================== */
const stage=$('stage');
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});
renderer.setClearColor(0,0);renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));
stage.prepend(renderer.domElement);
renderer.domElement.style.cssText='display:block;width:100%;height:100%;touch-action:none;position:relative;z-index:1';
const camera=new THREE.PerspectiveCamera(26,1,.5,500);
const VIEWS={face:[0,0,52],signeur:[0,0,-52],profil:[52,0,0],dessus:[0,52,.1]};
camera.position.fromArray(VIEWS.face);
const controls=new THREE.OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.update();
const main=makeHand(),ghosts=[makeHand(),makeHand(),makeHand(),makeHand()];
$('loading').hidden=true;
const arrow=new THREE.Group();scene.add(arrow);
const arrowMat=new THREE.MeshBasicMaterial({color:0x00857f});
const shaft=new THREE.Mesh(new THREE.CylinderGeometry(.3,.3,1,16),arrowMat),head=new THREE.Mesh(new THREE.ConeGeometry(.95,2.2,20),arrowMat);arrow.add(shaft,head);
// passe « identité » : chaque partie dans sa couleur, pour tracer les contours intérieurs
let idRT=null;
function ensureRT(w,h){if(idRT&&idRT.width===w&&idRT.height===h)return;if(idRT){idRT.depthTexture.dispose();idRT.dispose()}
  idRT=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.NearestFilter,magFilter:THREE.NearestFilter,depthBuffer:true});idRT.depthTexture=new THREE.DepthTexture(w,h);idRT.depthTexture.type=THREE.UnsignedIntType}
const edgeMat=new THREE.ShaderMaterial({transparent:true,depthTest:false,depthWrite:false,
  uniforms:{tId:{value:null},tDepth:{value:null},texel:{value:new THREE.Vector2()},cn:{value:.5},cf:{value:500},rad:{value:2}},
  vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}',
  fragmentShader:`uniform sampler2D tId;uniform sampler2D tDepth;uniform vec2 texel;uniform float cn;uniform float cf;uniform float rad;varying vec2 vUv;
  float lin(float d){float z=d*2.-1.;return 2.*cn*cf/(cf+cn-z*(cf-cn));}
  void main(){vec4 c=texture2D(tId,vUv);if(c.a<.5)discard;float d0=lin(texture2D(tDepth,vUv).r);float e=0.;
    for(int i=0;i<12;i++){float a=float(i)*.5235988;vec2 o=vec2(cos(a),sin(a))*rad*texel;vec4 q=texture2D(tId,vUv+o);if(q.a<.5)continue;
      float dn=lin(texture2D(tDepth,vUv+o).r);
      if(abs(q.r-c.r)>.02){
        // deux parties différentes : trait du côté de celle qui passe devant
        bool fingers=c.g>.5&&q.g>.5;
        float thr=(c.g>.5&&q.g>.5)?.12:.3;   // doigt sur paume : seulement s'il passe vraiment devant (pas à la jointure)
        if(dn-d0>thr||(fingers&&(dn-d0>.02||(abs(dn-d0)<=.02&&c.r<q.r))))e=1.;
      }else if(c.g>.5&&dn-d0>.7)e=1.; // un doigt replié devant lui-même
    }
    if(e<.5)discard;gl_FragColor=vec4(.067,.067,.067,1.);}`});
const edgeQuad=new THREE.Mesh(new THREE.PlaneGeometry(2,2),edgeMat),edgeScene=new THREE.Scene(),edgeCam=new THREE.Camera();edgeScene.add(edgeQuad);
function renderAll(){
  const size=renderer.getDrawingBufferSize(new THREE.Vector2());ensureRT(size.x,size.y);
  // 1. identités (main pleine seulement)
  const hidden=[];const hide=o=>{if(o.visible){o.visible=false;hidden.push(o)}};
  ghosts.forEach(g=>hide(g.root));hide(arrow);
  main.meshes.forEach(hide);main.skin.idm.visible=true;
  const cc=renderer.getClearColor(new THREE.Color()),ca=renderer.getClearAlpha();
  renderer.setRenderTarget(idRT);renderer.setClearColor(0,0);renderer.clear();renderer.render(scene,camera);renderer.setRenderTarget(null);
  main.skin.idm.visible=false;hidden.forEach(o=>o.visible=true);
  renderer.setClearColor(cc,ca);
  // 2. image normale (coque de la main entière : voir hullMatProto), 3. traits intérieurs par-dessus
  const hu=main.skin.hm.uniforms;hu.push.value=HPUSH*main.skin.gR*HULL/SC;hu.tId.value=idRT.texture;hu.tDepth.value=idRT.depthTexture;
  hu.res.value.set(size.x,size.y);hu.cn.value=camera.near;hu.cf.value=camera.far;
  renderer.render(scene,camera);
  edgeMat.uniforms.tId.value=idRT.texture;edgeMat.uniforms.tDepth.value=idRT.depthTexture;edgeMat.uniforms.texel.value.set(1/size.x,1/size.y);
  edgeMat.uniforms.rad.value=1.6*renderer.getPixelRatio();edgeMat.uniforms.cn.value=camera.near;edgeMat.uniforms.cf.value=camera.far;
  renderer.autoClear=false;renderer.render(edgeScene,edgeCam);renderer.autoClear=true;
}
let playing=null;
function render3D(){
  if(playing)return;
  main.root.visible=true;setLook(main,1);
  if(S.mode==='pose'){applyPose(main,S.pose);ghosts.forEach(g=>g.root.visible=false);arrow.visible=false;return}
  const ef=S.target==='fin';applyPose(main,editable());
  ghosts.forEach((g,i)=>{if(i<S.etapes){const t=ef?i/S.etapes:(i+1)/S.etapes;g.root.visible=true;setLook(g,.2+.3*(ef?t:1-t));applyPose(g,lerpPose(S.debut,S.fin,t))}else g.root.visible=false});
  const a=new THREE.Vector3().fromArray(S.debut.pos).add(new THREE.Vector3(0,-7,5)),b=new THREE.Vector3().fromArray(S.fin.pos).add(new THREE.Vector3(0,-7,5));
  const dist=a.distanceTo(b);arrow.visible=S.fleche&&dist>3;
  if(arrow.visible){const dir=b.clone().sub(a).normalize(),len=dist-2.2;shaft.scale.y=len;shaft.position.copy(a).addScaledVector(dir,len/2);head.position.copy(a).addScaledVector(dir,len+1.1);
    const q=new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,1,0),dir);shaft.quaternion.copy(q);head.quaternion.copy(q)}
}
function resize(){const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix()}
new ResizeObserver(resize).observe(stage);resize();
renderer.setAnimationLoop(()=>{controls.update();renderAll()});
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{camera.position.fromArray(VIEWS[b.dataset.view]);controls.target.set(0,0,0);controls.update()});

/* ======================================================================
   Attraper
   ====================================================================== */
const cv=renderer.domElement;
function scr(v){const p=v.clone().project(camera),r=cv.getBoundingClientRect();return new THREE.Vector2((p.x+1)/2*r.width,(1-p.y)/2*r.height)}
const wp=o=>o.getWorldPosition(new THREE.Vector3());
function segEnds(h,k,g){const j=h.joints[k];return[wp(j[g]),wp(j[g+1]||j.tip)]}
function distSeg(p,a,b){const ab=b.clone().sub(a),t=clamp(p.clone().sub(a).dot(ab)/Math.max(ab.lengthSq(),1e-6),0,1);return p.distanceTo(a.clone().addScaledVector(ab,t))}
function pxPerUnit(at){const cr=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0);return scr(at.clone().addScaledVector(cr,1)).distanceTo(scr(at))}
function hull(P){P=P.slice().sort((a,b)=>a.x-b.x||a.y-b.y);const cr=(o,a,b)=>(a.x-o.x)*(b.y-o.y)-(a.y-o.y)*(b.x-o.x),lo=[],up=[];
  for(const p of P){while(lo.length>1&&cr(lo[lo.length-2],lo[lo.length-1],p)<=0)lo.pop();lo.push(p)}
  for(const p of P.slice().reverse()){while(up.length>1&&cr(up[up.length-2],up[up.length-1],p)<=0)up.pop();up.push(p)}return lo.slice(0,-1).concat(up.slice(0,-1))}
function inPoly(p,P){let c=false;for(let i=0,j=P.length-1;i<P.length;j=i++)if(((P[i].y>p.y)!==(P[j].y>p.y))&&(p.x<(P[j].x-P[i].x)*(p.y-P[i].y)/(P[j].y-P[i].y)+P[i].x))c=!c;return c}
function pick(e){
  const r=cv.getBoundingClientRect(),m=new THREE.Vector2(e.clientX-r.left,e.clientY-r.top);let best=null;
  ALL.forEach(k=>SEGN[typ(k)].forEach((_,g)=>{const [a,b]=segEnds(main,k,g),w=SEGW[k][g];
    const tol=Math.max(10,pxPerUnit(a)*w*1.1),d=distSeg(m,scr(a),scr(b)),depth=a.clone().add(b).multiplyScalar(.5).distanceTo(camera.position);
    if(d<tol){const sc=d/tol+depth*.02;if(!best||sc<best.sc)best={k,g,sc}}}));
  if(best)return best;
  const rim=hull(PALM_RIM.map(v=>scr(v.clone().applyMatrix4(main.root.matrixWorld))));
  return inPoly(m,rim)?{k:null}:null;
}
const label=s=>!s?'':s.k===null?'Main · tourner (Maj : déplacer)':`${NOMS[s.k]} · ${SEGN[typ(s.k)][s.g]}${S.locks[s.k][s.g]?' 🔒':''}`;
let hovered=null;
function setHL(s){const key=s?(s.k===null?'paume':s.k):null;if(key===hovered)return;
  hovered=key;main.skinMats.forEach(m=>{m.uniforms.hl.value=key?1:0;m.uniforms.hlPart.value=key?ID[key]:-10})}

/* ======================================================================
   Marionnette
   ====================================================================== */
// tirer le bout du pouce vers la paume = vrai repli du pouce : il s'avance devant la paume en même temps qu'il plie
const GRAB={doigt:[{mcp:1},{mcp:.85,pip:1},{mcp:.85,pip:1,dip:.7}],pouce:[{av:1},{av:.15,rap:.6,mcp:.5,ip:.8}]};
const LOCKJ={doigt:[['mcp','ab'],['pip'],['dip']],pouce:[['av','rap','mcp'],['ip']]};
const locked=(k,n)=>LOCKJ[typ(k)].some((g,gi)=>g.includes(n)&&S.locks[k][gi]);
let drag=null;
// glisser le long du doigt = plier ; glisser de côté = écarter / serrer contre les voisins (depuis n'importe quelle phalange)
// Alt + glisser : les quatre doigts ensemble (plier, écarter en éventail ou serrer)
const FAN={index:1,majeur:.15,annulaire:-.6,auriculaire:-1.2};
function grabAxes(p,s,shift,group){
  const k=s.k,t=typ(k),axes=[],j=main.joints[k];group=group&&k!=='pouce';
  let set=GRAB[t][s.g];
  if(shift){set={};LOCKJ[t][s.g].forEach(n=>{if(n!=='ab'&&n!=='rap')set[n]=1})}
  const js=Object.keys(set).filter(n=>shift||!locked(k,n));
  const ks=group?FING.filter(f=>f===k||!S.locks[f].some(Boolean)):[k];
  if(js.length){const st=ks.map(f=>js.map(n=>p.f[f][n]));axes.push({flex:true,set:c=>ks.forEach((f,fi)=>js.forEach((n,i)=>p.f[f][n]=st[fi][i]+c*set[n]))})}
  if(!shift&&!S.locks[k][0]){const n=t==='pouce'?'rap':'ab';
    if(group){const st=ks.map(f=>p.f[f].ab),sg=Math.sign(FAN[k])||1;axes.push({set:c=>ks.forEach((f,fi)=>p.f[f].ab=st[fi]+c*FAN[f]*sg)})}
    else{const st=p.f[k][n];axes.push({set:c=>p.f[k][n]=st+c})}}
  const end=()=>wp(j[s.g+1]||j.tip),base=wp(j[0]);
  const snap=clone(p.f);
  axes.forEach(a=>{p.f=clone(snap);applyPose(main,p);const w0=end(),e0=scr(w0);a.set(3);applyPose(main,p);const w1=end(),e1=scr(w1);p.f=clone(snap);applyPose(main,p);
    a.dir=e1.clone().sub(e0).divideScalar(3);
    if(a.flex){const toCam=camera.position.clone().sub(w0).normalize(),depth=Math.abs(w1.clone().sub(w0).dot(toCam))*pxPerUnit(w0)/3,ub=scr(base).sub(e0);
      if(ub.lengthSq()>1)a.dir.addScaledVector(ub.normalize(),depth*.6)}});
  return axes;
}
stage.addEventListener('pointerdown',e=>{
  if(e.target!==cv||e.button===2||playing)return;const s=pick(e);if(!s)return;
  e.stopPropagation();e.preventDefault();const p=editable();
  drag={s,x0:e.clientX,y0:e.clientY,start:clone(p),shift:e.shiftKey,ok:clone(p.f)};if(s.k!==null)drag.axes=grabAxes(p,s,e.shiftKey,e.altKey);drag.group=e.altKey;
  controls.enabled=false;cv.style.cursor='grabbing';
},true);
let pending=null;
window.addEventListener('pointermove',e=>{
  if(!drag){if(e.target!==cv){setHL(null);showTip(e,'');return}const s=pick(e);setHL(s);showTip(e,label(s));cv.style.cursor=s?'grab':'';return}
  pending=e;requestAnimationFrame(()=>{if(!pending||!drag)return;const ev=pending;pending=null;onDrag(ev)});
});
function onDrag(e){
  const dx=e.clientX-drag.x0,dy=e.clientY-drag.y0,p=editable();
  const cr=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0),cu=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,1);
  if(drag.s.k===null){
    if(drag.shift){const k=1/pxPerUnit(new THREE.Vector3().fromArray(drag.start.pos));p.pos=new THREE.Vector3().fromArray(drag.start.pos).addScaledVector(cr,dx*k).addScaledVector(cu,-dy*k).toArray()}
    else p.q=qa(cu,dx*.45).multiply(qa(cr,dy*.45)).multiply(new THREE.Quaternion().fromArray(drag.start.q)).normalize().toArray();
  }else{
    p.f=clone(drag.start.f);const A=drag.axes;
    if(A.length===1){const d=A[0].dir,l=d.lengthSq();A[0].set(l>.01?(d.x*dx+d.y*dy)/l:0)}
    else if(A.length===2){const a=A[0].dir,b=A[1].dir,lam=.02,aa=a.dot(a)+lam,bb=b.dot(b)+lam,ab=a.dot(b),am=a.x*dx+a.y*dy,bm=b.x*dx+b.y*dy,det=aa*bb-ab*ab;
      A[0].set((bb*am-ab*bm)/det);A[1].set((aa*bm-ab*am)/det)}
    constrain(p,drag.group?null:drag.s.k);
    p.f=solve(drag.ok,p.f);drag.ok=clone(p.f);
  }
  syncSliders();render3D();showTip(e,label(drag.s));
}
function endDrag(){if(!drag)return;drag=null;pending=null;controls.enabled=true;cv.style.cursor='';$('tip').hidden=true;refresh()}
window.addEventListener('pointerup',endDrag);window.addEventListener('pointercancel',endDrag);
cv.addEventListener('contextmenu',e=>{e.preventDefault();const s=pick(e);if(s&&s.k){S.locks[s.k][s.g]=!S.locks[s.k][s.g];refresh();showTip(e,label(s))}});
cv.addEventListener('dblclick',e=>{const s=pick(e);if(!s)return;const p=editable();
  if(s.k===null)p.q=[0,0,0,1];else{const t=clone(p.f);if(s.k==='pouce')Object.assign(t.pouce,{mcp:0,ip:0});else Object.assign(t[s.k],{mcp:0,pip:0,dip:0});p.f=solve(p.f,t)}refresh()});
function showTip(e,txt){const t=$('tip');if(!txt){t.hidden=true;return}const r=stage.getBoundingClientRect();t.textContent=txt;t.hidden=false;t.style.left=(e.clientX-r.left)+'px';t.style.top=(e.clientY-r.top)+'px'}

/* ======================================================================
   Panneau
   ====================================================================== */
const sliders=[];
const JOINTS={doigt:[['mcp','Base',...LIMF.mcp,0],['pip','Milieu',...LIMF.pip,1],['dip','Bout',...LIMF.dip,2],['ab','Écart',-45,25,-1]],
              pouce:[['av','Avancer',...LIMT.av,0],['rap','Rapprocher',...LIMT.rap,-1],['mcp','Base',...LIMT.mcp,-1],['ip','Bout',...LIMT.ip,1]]};
function row(box,id,lab,mn,mx,get,set,lock,unit='°'){
  const r=document.createElement('div');r.className='row'+(lock?'':' nolock');
  r.innerHTML=`<label for="${id}">${lab}</label><input type="range" id="${id}" min="${mn}" max="${mx}" step="1"><output></output>`+(lock?`<button class="lockbtn" aria-label="Bloquer ${lab}" title="Bloquer">${LOCK_SVG}</button>`:'');
  box.appendChild(r);const el=r.querySelector('input'),out=r.querySelector('output'),lb=r.querySelector('.lockbtn');
  el.addEventListener('input',()=>{set(+el.value);syncSliders();render3D()});if(lb)lb.onclick=()=>{lock.toggle();refresh()};
  sliders.push({el,out,get,unit,lb,lock});
}
ALL.forEach(k=>{
  const b=document.createElement('div');b.className='block';b.innerHTML=`<h3>${NOMS[k]}</h3>`;$('jointBlocks').appendChild(b);const t=typ(k);
  JOINTS[t].forEach(([j,lab,mn,mx,gi])=>{
    const mm=j==='ab'?SPREAD[k]:[mn,mx];
    row(b,`${k}-${j}`,lab,mm[0],mm[1],()=>editable().f[k][j],v=>{const p=editable(),tg=clone(p);tg.f[k][j]=v;constrain(tg,k);p.f=solve(p.f,tg.f)},
      gi>=0?{get:()=>S.locks[k][gi],toggle:()=>S.locks[k][gi]=!S.locks[k][gi]}:null)});
});
const eul=()=>new THREE.Euler().setFromQuaternion(new THREE.Quaternion().fromArray(editable().q),'YXZ');
const setE=(ax,deg)=>{const e=eul();e[ax]=deg*D;editable().q=new THREE.Quaternion().setFromEuler(e).toArray()};
[['x','Bascule'],['y','Pivot'],['z','Roulis']].forEach(([a,l])=>row($('orientRows'),'o-'+a,l,-180,180,()=>eul()[a]/D,v=>setE(a,v),null));
[['0','Gauche/droite'],['1','Bas/haut']].forEach(([i,l])=>row($('orientRows'),'p-'+i,l,-25,25,()=>editable().pos[+i],v=>editable().pos[+i]=v,null,''));
$('presets').innerHTML=Object.keys(PRESETS).map(n=>`<button data-preset="${n}">${n}</button>`).join('');
function applyPreset(name){const p=editable(),tg=constrain(clone(PRESETS[name]));p.f=settle(p.f,tg.f);if(REACH[name])p.f=thumbReach(p.f,REACH[name]);refresh()}
document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>applyPreset(b.dataset.preset));
function syncSliders(){sliders.forEach(s=>{const v=Math.round(s.get());s.el.value=v;s.out.textContent=v+s.unit;if(s.lb)s.lb.setAttribute('aria-pressed',s.lock.get())})}
const press=(a,b,f)=>{a.setAttribute('aria-pressed',f);b.setAttribute('aria-pressed',!f)};
function refresh(){
  syncSliders();press($('mainD'),$('mainG'),!S.gauche);press($('modePose'),$('modeMvt'),S.mode==='pose');press($('editD'),$('editF'),S.target==='debut');
  $('mvtOn').hidden=S.mode!=='mouvement';$('mvtOff').hidden=S.mode==='mouvement';$('etapes').value=S.etapes;$('etapesOut').textContent=S.etapes;$('fleche').checked=S.fleche;
  $('status').innerHTML=`<span class="chip">Main ${S.gauche?'gauche':'droite'}</span>`+(S.mode==='pose'?`<span class="chip on">Pose fixe</span>`:`<span class="chip ${S.target==='debut'?'debut':'fin'}">Main pleine : ${S.target==='debut'?'début':'fin'}</span>`);
  render3D();
}
$('mainD').onclick=()=>{S.gauche=false;refresh()};$('mainG').onclick=()=>{S.gauche=true;refresh()};
$('resetOrient').onclick=()=>{editable().q=[0,0,0,1];refresh()};
$('unlockAll').onclick=()=>{for(const k in S.locks)S.locks[k]=S.locks[k].map(()=>false);refresh()};
$('modePose').onclick=()=>{S.mode='pose';refresh()};
$('modeMvt').onclick=()=>{if(!S.debut){S.debut=clone(S.pose);S.fin=clone(S.pose);S.fin.pos[0]+=14}S.mode='mouvement';refresh()};
$('editD').onclick=()=>{S.target='debut';refresh()};$('editF').onclick=()=>{S.target='fin';refresh()};
$('copyDF').onclick=()=>{const p=S.fin.pos;S.fin=clone(S.debut);S.fin.pos=p;refresh()};
$('copyFD').onclick=()=>{const p=S.debut.pos;S.debut=clone(S.fin);S.debut.pos=p;refresh()};
$('etapes').oninput=e=>{S.etapes=+e.target.value;$('etapesOut').textContent=S.etapes;render3D()};
$('fleche').onchange=e=>{S.fleche=e.target.checked;render3D()};
$('play').onclick=()=>{if(playing)return;ghosts.forEach(g=>g.root.visible=false);arrow.visible=false;const t0=performance.now(),dur=1400;playing=true;
  (function step(now){const k=Math.min(1,(now-t0)/dur),e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;applyPose(main,lerpPose(S.debut,S.fin,e));
    if(k<1)requestAnimationFrame(step);else setTimeout(()=>{playing=null;render3D()},600)})(t0)};
document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(x=>x.setAttribute('aria-selected',x===b));
  document.querySelectorAll('[data-pane]').forEach(p=>p.hidden=p.dataset.pane!==b.dataset.tab)});

/* ======================================================================
   Sauvegarde, JSON, export
   ====================================================================== */
function snapshot(){const o={version:7,mode:S.mode,gauche:S.gauche,verrous:clone(S.locks),vue:{pos:camera.position.toArray().map(v=>+v.toFixed(2)),cible:controls.target.toArray().map(v=>+v.toFixed(2))}};
  if(S.mode==='pose')o.pose=clone(S.pose);else{o.debut=clone(S.debut);o.fin=clone(S.fin);o.etapes=S.etapes;o.fleche=S.fleche}return o}
const okPose=p=>p&&p.f&&ALL.every(k=>p.f[k])&&p.f.pouce.av!==undefined&&Array.isArray(p.q)&&Array.isArray(p.pos);
function load(o){
  if(!o||(o.version!==7&&o.version!==6))throw new Error('format d\'une ancienne version de l\'atelier');
  if(o.mode==='mouvement'){if(!okPose(o.debut)||!okPose(o.fin))throw new Error('début ou fin manquant');S.debut=clone(o.debut);S.fin=clone(o.fin);S.etapes=o.etapes||2;S.fleche=o.fleche!==false;S.mode='mouvement';S.target='fin';S.pose=clone(o.fin)}
  else{if(!okPose(o.pose))throw new Error('pose manquante');S.pose=clone(o.pose);S.mode='pose'}
  S.gauche=!!o.gauche;if(o.verrous)for(const k in S.locks)if(o.verrous[k])S.locks[k]=o.verrous[k].slice();
  if(o.vue&&o.vue.pos){camera.position.fromArray(o.vue.pos);controls.target.fromArray(o.vue.cible||[0,0,0]);controls.update()}refresh();
}
let db=null,items=[];const libMsg=h=>$('lib').innerHTML=h;
(async()=>{try{if(!window.claude||!window.claude.use)throw 0;db=await window.claude.use('db');if(!db)throw 0;
  db.collection('configurations').orderBy('creeLe','desc').onSnapshot(s=>{items=s.docs;renderLib()},e=>libMsg(`<div class="empty">La bibliothèque ne répond plus (${e.code}). Recharge la page.</div>`));
}catch(e){db=null;$('save').disabled=true;libMsg('<div class="empty">Bibliothèque indisponible dans cet affichage. Utilise « Échanger en JSON » pour garder une configuration.</div>')}})();
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function renderLib(){
  if(!items.length){libMsg('<div class="empty">Aucune configuration enregistrée. Pose une main, donne-lui un nom et clique sur « Enregistrer » : elle apparaîtra ici.</div>');return}
  libMsg(items.map(d=>{const v=d.data(),date=v.creeLe?new Date(v.creeLe).toLocaleDateString('fr-FR',{day:'numeric',month:'short'}):'';
    return `<div class="item"><b>${esc(v.nom||'Sans nom')}<span class="tag">${v.etat&&v.etat.mode==='mouvement'?'mouvement':'pose'}</span></b><div class="actions"><button class="btn" data-load="${d.id}">Charger</button><button class="btn danger" data-del="${d.id}">Suppr.</button></div><small>${esc(v.note||'')}${v.note&&date?' · ':''}${date}</small></div>`}).join(''));
  document.querySelectorAll('[data-load]').forEach(b=>b.onclick=()=>{const d=items.find(x=>x.id===b.dataset.load);try{load(d.data().etat);$('saveMsg').textContent=''}catch(e){$('saveMsg').textContent='Impossible de charger : '+e.message}});
  document.querySelectorAll('[data-del]').forEach(b=>b.onclick=async()=>{if(b.dataset.armed!=='1'){b.dataset.armed='1';b.textContent='Confirmer';setTimeout(()=>{b.dataset.armed='';b.textContent='Suppr.'},3000);return}
    b.disabled=true;try{await db.collection('configurations').doc(b.dataset.del).delete()}catch(e){b.disabled=false;$('saveMsg').textContent='Suppression impossible.'}});
}
$('save').onclick=async()=>{const nom=$('nom').value.trim(),m=$('saveMsg');m.className='msg';
  if(!nom){m.textContent='Donne un nom à la configuration.';m.className='msg err';$('nom').focus();return}if(!db)return;$('save').disabled=true;
  try{await db.collection('configurations').add({nom,note:$('noteIn').value.trim(),etat:snapshot(),creeLe:Date.now()});m.textContent=`« ${nom} » enregistrée.`;$('nom').value='';$('noteIn').value=''}
  catch(e){m.className='msg err';m.textContent=e&&e.code==='invalid_argument'?'Tu n\'as pas les droits d\'écriture sur cette bibliothèque.':'Enregistrement impossible, réessaie.'}$('save').disabled=false};
$('copyJson').onclick=()=>{const txt=JSON.stringify(snapshot());$('json').value=txt;const ok=()=>$('jsonMsg').textContent='Copiée dans le presse-papiers.',fb=()=>{$('json').select();$('jsonMsg').textContent='Sélectionnée : copie-la avec Ctrl+C.'};
  try{navigator.clipboard.writeText(txt).then(ok,fb)}catch(e){fb()}};
$('importJson').onclick=()=>{try{load(JSON.parse($('json').value));$('jsonMsg').textContent='Configuration chargée.'}catch(e){$('jsonMsg').textContent='JSON illisible : '+(e.message||'format inattendu')}};
let downloads=null;(async()=>{try{if(window.claude&&window.claude.use)downloads=await window.claude.use('downloads')}catch(e){}})();
$('export').onclick=async()=>{const m=$('exportMsg');m.className='msg';m.textContent='Rendu en cours…';
  const size=+$('taille').value,white=$('fondBlanc').checked,w=stage.clientWidth,h=stage.clientHeight,old=renderer.getPixelRatio();
  setHL(null);renderer.setPixelRatio(size/Math.max(w,h));renderer.setSize(w,h,false);if(white)renderer.setClearColor(0xffffff,1);
  renderAll();let out=renderer.domElement;if(!white)out=cropAlpha(out);const blob=await new Promise(r=>out.toBlob(r,'image/png'));
  renderer.setClearColor(0,0);renderer.setPixelRatio(old);resize();
  const nom=($('nom').value.trim()||'main-lsf').replace(/[^\w\-àâäéèêëîïôöùûüç ]/gi,'').replace(/\s+/g,'-');
  if(downloads){try{await downloads.save({filename:nom+'.png',data:blob});m.textContent='Image enregistrée.';return}catch(e){if(e&&e.code==='declined'){m.textContent='Export annulé.';return}}}
  $('imgOut').src=URL.createObjectURL(blob);$('imgDlg').showModal();m.textContent=''};
$('closeDlg').onclick=()=>$('imgDlg').close();
function cropAlpha(src){const c=document.createElement('canvas');c.width=src.width;c.height=src.height;const x=c.getContext('2d');x.drawImage(src,0,0);
  const d=x.getImageData(0,0,c.width,c.height).data;let x0=c.width,y0=c.height,x1=-1,y1=-1;
  for(let y=0;y<c.height;y+=2)for(let i=0;i<c.width;i+=2)if(d[(y*c.width+i)*4+3]>8){if(i<x0)x0=i;if(i>x1)x1=i;if(y<y0)y0=y;if(y>y1)y1=y}
  if(x1<0)return c;const pad=Math.round(c.width*.02);x0=Math.max(0,x0-pad);y0=Math.max(0,y0-pad);x1=Math.min(c.width,x1+pad);y1=Math.min(c.height,y1+pad);
  const o=document.createElement('canvas');o.width=x1-x0;o.height=y1-y0;o.getContext('2d').drawImage(c,x0,y0,o.width,o.height,0,0,o.width,o.height);return o}

window.__atelier={renderer,setPron:v=>{PRONA=v;main.skin.key=''},S,refresh,main,camera,controls,PRESETS,PAR,applyPreset,penetration,editable,constrain,solve,renderAll};
refresh();
})();
</script>
