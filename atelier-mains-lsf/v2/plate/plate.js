/* plate.js — l'éditeur de planche de l'Atelier des mains LSF (palier v2, chantier M3).
   Couche d'édition maison (pas de bibliothèque : outil.md § 3 — l'objet « main » serait maison de toute façon, et
   l'annulation, les guides, les gabarits, le projet aussi). Le DOCUMENT est des données (JSON v9, PLAN.md « Contrat
   M3 ») ; le comportement est dans des tables par type (DEFAUT / DESSINE / VALIDE / PROPS). drawDoc(ctx, doc, k)
   est LA fonction de dessin, à l'écran (k = zoom) comme à l'export (k = échelle) ; elle ne connaît ni la sélection
   ni les poignées. Les mains sont rendues par window.AtelierHand (contrat M2 → M3), dans des images cache.
   Chaque réglage porte la mesure qui l'a fixé (outil.md § 2). */
(function(){
'use strict';
const $=id=>document.getElementById(id);
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const clone=o=>JSON.parse(JSON.stringify(o));
const uid=()=>'e'+Date.now().toString(36).slice(-5)+Math.random().toString(36).slice(2,6);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const D2R=Math.PI/180;
// validation « aucun champ n'est cru » (reprise de load() de la v1)
const vHex=(v,d)=>typeof v==='string'&&/^#[0-9a-fA-F]{6}$/.test(v)?v.toLowerCase():d;
const vNum=(v,a,b,d)=>typeof v==='number'&&isFinite(v)?clamp(v,a,b):d;
const vIn=(v,l,d)=>l.indexOf(v)>=0?v:d;
const vBool=(v,d)=>typeof v==='boolean'?v:d;
const vStr=(v,n,d)=>typeof v==='string'?v.slice(0,n):d;

/* ======================================================================
   Constantes mesurées
   ====================================================================== */
const INJS='#00a19a';                                   // vert INJS relevé sur le logo (CLAUDE.md)
const FORMATS={'16:9':[1920,1080,'Diapositive 16:9'],'carre':[1080,1080,'Carré'],'A4':[2480,3508,'A4 portrait (300 dpi)'],
  'A4p':[3508,2480,'A4 paysage (300 dpi)'],'A3':[3508,4961,'A3 portrait (300 dpi)'],'bandeau':[2400,600,'Bandeau 4:1'],'libre':[1600,900,'Libre']};
const POLICES=['Atkinson Hyperlegible','Nunito','Arial','Verdana','Georgia','Comic Sans MS','Trebuchet MS'];
const SNAP=5;            // guides : ≤ 5 px écran (Konva GUIDELINE_OFFSET = 5)
const SEUIL=4;           // seuil glisser / clic : 4 px écran (Fabric 3, Konva 3 : un clic tremblant ne déplace pas)
const POIGNEE=10;        // poignées de 10 px écran, indépendantes du zoom (Konva anchorSize 10)
const ROT_OFF=24;        // poignée de rotation décollée de 24 px (Konva 50 trop loin pour de petites mains, Fabric 40)
const ROT_TOL=5;         // accroche de rotation : 5° (Konva rotationSnapTolerance)
const MIN_T=8;           // taille minimale d'un objet : 8 × 8 px planche
const HIST_MAX=100;      // 100 instantanés (≈ 20 Ko chacun sans les pixels = 2 Mo)
const BROUILLON_MS=5000; // brouillon IndexedDB après 5 s de calme
const IMG_MAX=4096;      // côté long à l'import : 4 096 px (une photo 12 Mpx décodée = 48 Mo)
const PRISE_LIGNE=12;    // zone de prise d'une ligne fine : 12 px écran
const PERS_HL={w:2.9,h:4.3,cou:2.1}; // boîte du personnage en HL (personnage.md § 4.1 : 2,8 HL de large, crâne −2,1 → ceinture +2,2)

/* ======================================================================
   Polices vendues (OFL, base64 dans fonts.js) : chargées par FontFace, attendues avant tout fillText
   ====================================================================== */
const FONTS_PRETES=(async()=>{try{const F=window.ATELIER_FONTS||{};const ps=[];
  for(const nom in F)for(const w in F[nom]){const b=Uint8Array.from(atob(F[nom][w]),c=>c.charCodeAt(0));
    const ff=new FontFace(nom,b.buffer,{weight:String(w)});ps.push(ff.load().then(f=>document.fonts.add(f)))}
  await Promise.all(ps)}catch(e){console.warn('polices',e)}})();

/* ======================================================================
   Le document (JSON v9) et les valeurs par défaut par type
   ====================================================================== */
function docNeuf(format){const f=FORMATS[format]?format:'16:9',[w,h]=FORMATS[f];
  return{version:9,app:'atelier-mains-lsf',nom:'',creeLe:Date.now(),modifieLe:Date.now(),
    planche:{w,h,format:f,fond:fondDefaut()},
    theme:{couleur:INJS,police:'Atkinson Hyperlegible',corps:48},elements:[],assets:{}}}
const fondDefaut=()=>({type:'uni',col:'#ffffff',col2:'#cceeec',angle:180,src:null,mode:'couvrir',ax:.5,ay:.5,opacite:1,voile:{col:'#000000',a:0},flou:0});
const AH=()=>window.AtelierHand;
const poseDessin=()=>{const p=AH()&&AH().presets&&AH().presets['Dessin'];return p?clone(p):{}};
const BASE=()=>({id:uid(),x:0,y:0,w:100,h:100,rot:0,flipH:false,flipV:false,opacite:1,verrou:false,visible:true,nom:'',groupes:[]});
const DEFAUT={
  main:()=>({cote:'D',pose:poseDessin(),orientation:[0,0,0,1],style:{peau:INJS,ongle:'#d6f2ee',trait:'#111111',largeurTrait:1.2,ombre:true},mouvement:null}),
  texte:()=>({texte:'Texte',police:S.doc.theme.police,corps:S.doc.theme.corps,gras:false,couleur:'#1e1e1e',fond:null,align:'gauche',surlignages:[],contour:null,interligne:1.25,rayon:0,marge:12,surligneur:'#fff176'}),
  image:()=>({asset:null,rayon:0}),
  personnage:()=>({expression:'neutre',vue:'face',style:'A',couleurs:{peau:'#9fd8a8',vetement:'#5e4b8b',cape:'#f4f1ea',trait:'#14201f'}}),
  fleche:()=>({de:[0,.5],a:[1,.5],style:'droite',double:false,couleur:'#1e1e1e',epaisseur:0}),
};
const NOMS={main:'Main',texte:'Texte',image:'Image',personnage:'Référent',fleche:'Flèche'};
function nouvelElement(type,props){const e=Object.assign(BASE(),{type},DEFAUT[type](),props||{});
  if(!e.nom)e.nom=type==='main'?'Main '+e.cote:NOMS[type];return e}

/* ======================================================================
   Session (non enregistrée)
   ====================================================================== */
const S={doc:null,sel:[],outil:'select',zoom:1,ox:0,oy:0,mode:'planche',hover:null,guides:[],marquee:null,drag:null,
  clip:null,editId:null,puppetId:null,puppet:null,dirty:true,dirtyUI:true,souris:null,espace:false,gabaritNom:''};
const IMG=new Map();      // id d'asset → HTMLImageElement décodée
const HC=new Map();       // clé → canvas cache d'une main (LRU 60 entrées)
const stage=$('stage'),cvP=$('planche'),cvU=$('ui');

/* ======================================================================
   Historique : instantanés du document SANS les pixels (assets partagés), fusion d'un glisser en une entrée
   ====================================================================== */
const hist={undo:[],redo:[],pending:null,
  snap(){const d=S.doc,a=d.assets;d.assets=null;const s=JSON.stringify(d);d.assets=a;return s},
  begin(){if(this.pending===null)this.pending=this.snap()},
  commit(){if(this.pending===null)return;const now=this.snap();
    if(now!==this.pending){this.undo.push(this.pending);if(this.undo.length>HIST_MAX)this.undo.shift();this.redo.length=0;modifie()}
    this.pending=null},
  restore(s){const a=S.doc.assets;S.doc=JSON.parse(s);S.doc.assets=a;S.sel=S.sel.filter(id=>parId(id));quitteModes();invalide();modifie();panneaux()},
  undoer(){if(this.pending!==null)this.commit();if(!this.undo.length)return;this.redo.push(this.snap());this.restore(this.undo.pop())},
  redoer(){if(!this.redo.length)return;this.undo.push(this.snap());this.restore(this.redo.pop())}};
// une action = début + fonction + validation : UNE entrée d'historique
function act(fn){hist.begin();try{fn()}finally{hist.commit();invalide();panneaux()}}
let brouillonT=null;
function modifie(){S.doc.modifieLe=Date.now();clearTimeout(brouillonT);brouillonT=setTimeout(brouillonSauve,BROUILLON_MS);majUndo()}
function majUndo(){$('bUndo').disabled=!hist.undo.length;$('bRedo').disabled=!hist.redo.length}

const parId=id=>S.doc.elements.find(e=>e.id===id);
const selection=()=>S.sel.map(parId).filter(Boolean);
function selectionne(ids,ajoute){const l=Array.isArray(ids)?ids:(ids?[ids]:[]);S.sel=ajoute?Array.from(new Set(S.sel.concat(l))):l.slice();S.dirtyUI=true;panneaux()}
function groupeDe(e){if(!e.groupes||!e.groupes.length)return[e.id];const g=e.groupes[e.groupes.length-1];return S.doc.elements.filter(x=>x.groupes&&x.groupes.indexOf(g)>=0).map(x=>x.id)}

/* ======================================================================
   Géométrie : M = T(c)·R(rot)·S(flip)·T(−w/2,−h/2) ; dessin dans le repère local [0,w]×[0,h]
   ====================================================================== */
function versLocal(e,px,py){const cx=e.x+e.w/2,cy=e.y+e.h/2,c=Math.cos(-e.rot*D2R),s=Math.sin(-e.rot*D2R);
  let dx=px-cx,dy=py-cy;let lx=dx*c-dy*s,ly=dx*s+dy*c;if(e.flipH)lx=-lx;if(e.flipV)ly=-ly;return[lx+e.w/2,ly+e.h/2]}
function versPlanche(e,lx,ly){let dx=lx-e.w/2,dy=ly-e.h/2;if(e.flipH)dx=-dx;if(e.flipV)dy=-dy;
  const c=Math.cos(e.rot*D2R),s=Math.sin(e.rot*D2R);return[e.x+e.w/2+dx*c-dy*s,e.y+e.h/2+dx*s+dy*c]}
const coins=e=>[[0,0],[e.w,0],[e.w,e.h],[0,e.h]].map(p=>versPlanche(e,p[0],p[1]));
function bbox(els){let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;els.forEach(e=>coins(e).forEach(p=>{x0=Math.min(x0,p[0]);y0=Math.min(y0,p[1]);x1=Math.max(x1,p[0]);y1=Math.max(y1,p[1])}));
  return x1<x0?null:{x:x0,y:y0,w:x1-x0,h:y1-y0}}
const ecran=(px,py)=>[S.ox+px*S.zoom,S.oy+py*S.zoom];
const planche=(sx,sy)=>[(sx-S.ox)/S.zoom,(sy-S.oy)/S.zoom];
// test de collision : point dans le rectangle local ; pour une main, en plus alpha du cache > 8 (clic entre deux doigts = clic à travers)
function touche(e,px,py){if(!e.visible)return false;const[lx,ly]=versLocal(e,px,py);
  if(e.type==='fleche'){const pts=flechePts(e,1),tol=Math.max(PRISE_LIGNE/S.zoom,flecheLw(e)*1.2);
    for(let i=0;i+1<pts.length;i++)if(distSeg(lx,ly,pts[i],pts[i+1])<=tol)return true;return false}
  if(lx<0||ly<0||lx>e.w||ly>e.h)return false;
  if(e.type==='main'){const c=mainCache(e,Math.max(32,Math.round(e.w*S.zoom)),Math.max(32,Math.round(e.h*S.zoom)));
    if(c){const X=clamp(Math.floor(lx/e.w*c.width),0,c.width-1),Y=clamp(Math.floor(ly/e.h*c.height),0,c.height-1);
      try{return c.getContext('2d').getImageData(X,Y,1,1).data[3]>8}catch(err){return true}}}
  return true}
function distSeg(px,py,a,b){const dx=b.x-a.x,dy=b.y-a.y,l2=dx*dx+dy*dy||1e-9;const t=clamp(((px-a.x)*dx+(py-a.y)*dy)/l2,0,1);return Math.hypot(px-a.x-dx*t,py-a.y-dy*t)}
// le plus haut sous le pointeur (hors verrouillés et invisibles)
function sous(px,py){const L=S.doc.elements;for(let i=L.length-1;i>=0;i--){const e=L[i];if(!e.verrou&&e.visible&&touche(e,px,py))return e}return null}

/* ======================================================================
   Mains : cache d'images rendu par AtelierHand (clé = pose + orientation + côté + style + taille arrondie à 64)
   ====================================================================== */
function mainCle(e,w,h){return e.cote+'|'+JSON.stringify(e.pose)+'|'+(e.orientation||[]).join(',')+'|'+JSON.stringify(e.style)+'|'+w+'x'+h}
function mainCache(e,pxW,pxH,exact){const A=AH();if(!A)return null;
  const w=exact?Math.round(pxW):Math.max(64,Math.ceil(pxW/64)*64),h=exact?Math.round(pxH):Math.max(64,Math.ceil(pxH/64)*64);
  const k=mainCle(e,w,h);let c=HC.get(k);if(c){HC.delete(k);HC.set(k,c);return c}
  try{c=A.render({pose:e.pose,cote:e.cote,orientation:e.orientation,w,h,scale:w/Math.max(1,e.w),style:e.style})}catch(err){console.warn('rendu main',err);return null}
  if(!c)return null;if(!exact){HC.set(k,c);while(HC.size>60)HC.delete(HC.keys().next().value)}return c}
// boîte de la main posée (cm) → proportions de l'objet ; HL = 19 cm ≈ 0,26 × hauteur d'une planche 16:9 par défaut
function mainBoite(e){const A=AH();try{const b=A.bounds({pose:e.pose,cote:e.cote,orientation:e.orientation});if(b&&b.w>0&&b.h>0)return b}catch(err){}return{w:10,h:19}}
function ajusteProportionMain(e){const b=mainBoite(e),r=b.w/b.h,cx=e.x+e.w/2,cy=e.y+e.h/2,aire=e.w*e.h;
  e.h=Math.sqrt(aire/r);e.w=e.h*r;e.x=cx-e.w/2;e.y=cy-e.h/2}

/* ======================================================================
   drawDoc : fond puis éléments dans l'ordre, à l'échelle k. Identique écran / export.
   opts : {export, transparent, pix (pixels par px planche en plus de k, pour la netteté écran), editId}
   ====================================================================== */
function drawDoc(ctx,doc,k,opts){opts=opts||{};const P=doc.planche,W=P.w*k,H=P.h*k;
  ctx.save();ctx.beginPath();ctx.rect(0,0,W,H);ctx.clip();
  if(!opts.transparent)drawFond(ctx,doc,k);
  doc.elements.forEach(e=>{if(!e.visible)return;ctx.save();ctx.globalAlpha=e.opacite;
    ctx.translate((e.x+e.w/2)*k,(e.y+e.h/2)*k);ctx.rotate(e.rot*D2R);ctx.scale(e.flipH?-1:1,e.flipV?-1:1);ctx.translate(-e.w/2*k,-e.h/2*k);
    try{DESSINE[e.type](ctx,e,k,opts,doc)}catch(err){console.warn('dessin',e.type,err)}
    ctx.restore()});
  ctx.restore()}
function drawFond(ctx,doc,k){const F=doc.planche.fond,W=doc.planche.w*k,H=doc.planche.h*k;if(!F||F.type==='transparent')return;
  ctx.save();
  if(F.type==='uni'){ctx.fillStyle=F.col;ctx.fillRect(0,0,W,H)}
  else if(F.type==='degrade'){const a=(F.angle||0)*D2R,L=Math.abs(W*Math.sin(a))+Math.abs(H*Math.cos(a));
    const g=ctx.createLinearGradient(W/2-Math.sin(a)*L/2,H/2+Math.cos(a)*L/2,W/2+Math.sin(a)*L/2,H/2-Math.cos(a)*L/2);
    g.addColorStop(0,F.col);g.addColorStop(1,F.col2);ctx.fillStyle=g;ctx.fillRect(0,0,W,H)}
  else if(F.type==='image'){ctx.fillStyle=F.col;ctx.fillRect(0,0,W,H);const im=F.src&&IMG.get(F.src);
    if(im&&im.naturalWidth){ctx.globalAlpha=vNum(F.opacite,0,1,1);if(F.flou>0)ctx.filter='blur('+(F.flou*k)+'px)';ctx.imageSmoothingQuality='high';
      const iw=im.naturalWidth,ih=im.naturalHeight;
      if(F.mode==='mosaique'){const s=Math.max(.05,(F.echelle||1));const tw=iw*s*k*(doc.planche.w/1920),th=ih*s*k*(doc.planche.w/1920);
        for(let y=0;y<H;y+=th)for(let x=0;x<W;x+=tw)ctx.drawImage(im,x,y,tw,th)}
      else if(F.mode==='etirer')ctx.drawImage(im,0,0,W,H);
      else{const s=F.mode==='contenir'?Math.min(W/iw,H/ih):Math.max(W/iw,H/ih),dw=iw*s,dh=ih*s;
        ctx.drawImage(im,(W-dw)*vNum(F.ax,0,1,.5),(H-dh)*vNum(F.ay,0,1,.5),dw,dh)}
      ctx.filter='none';ctx.globalAlpha=1}
    if(F.voile&&F.voile.a>0){ctx.fillStyle=F.voile.col;ctx.globalAlpha=F.voile.a;ctx.fillRect(0,0,W,H)}}
  ctx.restore()}
function rrect(ctx,x,y,w,h,r){r=Math.min(r,w/2,h/2);ctx.beginPath();if(r<=0){ctx.rect(x,y,w,h);return}
  ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath()}
const DESSINE={
  main(ctx,e,k,opts){const pix=opts.pix||1,c=mainCache(e,e.w*k*pix,e.h*k*pix,!!opts.export);
    if(c)ctx.drawImage(c,0,0,e.w*k,e.h*k);
    else{ctx.fillStyle='rgba(0,161,154,.3)';ctx.fillRect(0,0,e.w*k,e.h*k)}},
  texte(ctx,e,k,opts){const W=e.w*k,H=e.h*k;
    if(e.fond){ctx.fillStyle=e.fond;rrect(ctx,0,0,W,H,e.rayon*k);ctx.fill()}
    if(opts.editId===e.id)return;                       // le contenteditable montre le texte pendant l'édition
    const L=lignesTexte(ctx,e,k),m=e.marge*k,lh=e.corps*e.interligne*k,asc=e.corps*k*.8;
    const hTot=L.length*lh,y0=e.fond?Math.max(m,(H-hTot)/2):m;
    ctx.font=fonte(e,k);ctx.textBaseline='alphabetic';
    const xDe=l=>e.align==='centre'?(W-l.w)/2:e.align==='droite'?W-m-l.w:m;
    // surligneur par segments : bande de corps × 1,1 derrière les mots, en mode multiply (lisible sur photo)
    if(e.surlignages&&e.surlignages.length){ctx.save();ctx.globalCompositeOperation='multiply';
      L.forEach((l,i)=>{e.surlignages.forEach(sg=>{const a=Math.max(sg.from,l.de),b=Math.min(sg.to,l.a);if(b<=a)return;
        const x=xDe(l)+ctx.measureText(l.t.slice(0,a-l.de)).width,w=ctx.measureText(l.t.slice(a-l.de,b-l.de)).width;
        ctx.fillStyle=sg.couleur;ctx.fillRect(x-k*2,y0+i*lh+asc-e.corps*k*.95,w+k*4,e.corps*k*1.1)})});ctx.restore()}
    L.forEach((l,i)=>{const x=xDe(l),y=y0+i*lh+asc;
      if(e.contour){ctx.lineJoin='round';ctx.lineWidth=e.corps*k*.14;ctx.strokeStyle=e.contour;ctx.strokeText(l.t,x,y)}
      ctx.fillStyle=e.couleur;ctx.fillText(l.t,x,y)})},
  image(ctx,e,k){const im=e.asset&&IMG.get(e.asset);
    if(im&&im.naturalWidth){ctx.imageSmoothingQuality='high';if(e.rayon>0){rrect(ctx,0,0,e.w*k,e.h*k,e.rayon*k);ctx.clip()}ctx.drawImage(im,0,0,e.w*k,e.h*k)}
    else{ctx.fillStyle='rgba(120,120,120,.25)';ctx.fillRect(0,0,e.w*k,e.h*k)}},
  personnage(ctx,e,k){const HLpx=e.h*k/PERS_HL.h,x=e.w*k/2,y=PERS_HL.cou*HLpx;
    const P=window.AtelierPersonnage;
    if(P&&typeof P.draw==='function'){P.draw(ctx,{x,y,HLpx,vue:e.vue,expression:e.expression,style:e.style,couleurs:e.couleurs})}
    else personnageStub(ctx,x,y,HLpx,e)},
  fleche(ctx,e,k){let pts=flechePts(e,k);if(pts.length<2)return;const lw=flecheLw(e)*k;
    if(pts.length>2)pts=trim(pts,lw*2.6);
    ctx.strokeStyle=e.couleur;ctx.fillStyle=e.couleur;ctx.lineWidth=lw;ctx.lineCap='round';ctx.lineJoin='round';
    ctx.beginPath();ctx.moveTo(pts[0].x,pts[0].y);for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i].x,pts[i].y);ctx.stroke();
    tete(ctx,pts[pts.length-1],pts[Math.max(0,pts.length-3)],lw);if(e.double)tete(ctx,pts[0],pts[Math.min(pts.length-1,2)],lw)},
};
/* ---- texte : police, retour à la ligne par mots mesuré (1,2 ms pour 42 lignes, outil.md § 2.7) ---- */
const fonte=(e,k)=>(e.gras?'700 ':'400 ')+(e.corps*k)+'px "'+e.police+'", "Atkinson Hyperlegible", sans-serif';
function lignesTexte(ctx,e,k){ctx.font=fonte(e,k);const maxW=Math.max(1,(e.w-2*e.marge)*k),out=[],txt=e.texte||'';let pos=0;
  txt.split('\n').forEach(par=>{const mots=par.split(' ');let cur='',de=pos;
    const pousse=(t,a)=>out.push({t,de:a,a:a+t.length,w:ctx.measureText(t).width});
    mots.forEach((mot,i)=>{const essai=cur?cur+' '+mot:mot;
      if(ctx.measureText(essai).width<=maxW||!cur){cur=essai}
      else{pousse(cur,de);de+=cur.length+1;cur=mot}
      // un mot plus long que la boîte est coupé au caractère
      while(ctx.measureText(cur).width>maxW&&cur.length>1){let n=cur.length-1;while(n>1&&ctx.measureText(cur.slice(0,n)).width>maxW)n--;pousse(cur.slice(0,n),de);de+=n;cur=cur.slice(n)}});
    pousse(cur,de);pos+=par.length+1});
  return out}
function hauteurTexte(e){const ctx=cvP.getContext('2d');const L=lignesTexte(ctx,e,1);return L.length*e.corps*e.interligne+2*e.marge}
function ajusteTexte(e){const h=hauteurTexte(e);if(!e.fond||h>e.h)e.h=Math.max(MIN_T,h)}
/* ---- flèches : mêmes tracés que la v1 (arrowPts), en coordonnées locales de l'objet ---- */
const flecheLw=e=>e.epaisseur>0?e.epaisseur:Math.max(2.4,.0105*Math.min(S.doc.planche.w,S.doc.planche.h));
function flechePts(e,k){const A={x:e.de[0]*e.w*k,y:e.de[1]*e.h*k},B={x:e.a[0]*e.w*k,y:e.a[1]*e.h*k},st=e.style==='courbe'?'arc':e.style;
  const dx=B.x-A.x,dy=B.y-A.y,L=Math.hypot(dx,dy)||1,nx=dx/L,ny=dy/L,sens=e.sens<0?-1:1,px=-ny*sens,py=nx*sens,o=[];
  const at=(t,q)=>({x:A.x+dx*t+px*q,y:A.y+dy*t+py*q});
  if(st==='droite')return[A,B];
  if(st==='zigzag'){const n=5,amp=.11*L;for(let i=0;i<=n;i++)o.push(at(i/n,(i===0||i===n)?0:(i%2?1:-1)*amp));return o}
  for(let i=0;i<=48;i++){const t=i/48;
    if(st==='arc')o.push(at(t,Math.sin(Math.PI*t)*.20*L));
    else if(st==='demi')o.push({x:(A.x+B.x)/2+(A.x-B.x)/2*Math.cos(Math.PI*t)+px*(L/2)*Math.sin(Math.PI*t),y:(A.y+B.y)/2+(A.y-B.y)/2*Math.cos(Math.PI*t)+py*(L/2)*Math.sin(Math.PI*t)});
    else if(st==='vague')o.push(at(t,Math.sin(2*Math.PI*2*t)*.10*L));
    else if(st==='boucle'){if(t<.3)o.push(at(t/.3*.34,0));else if(t<.78){const a=(t-.3)/.48*6.2832,r=.22*L,c=at(.5,0);
        o.push({x:c.x+nx*(-Math.sin(a))*r+px*(Math.cos(a)-1)*r,y:c.y+ny*(-Math.sin(a))*r+py*(Math.cos(a)-1)*r})}else o.push(at(.66+(t-.78)/.22*.34,0))}
    else o.push(at(t,0))}
  return o}
function tete(ctx,p,q,lw){const dx=p.x-q.x,dy=p.y-q.y,l=Math.hypot(dx,dy)||1,ux=dx/l,uy=dy/l,h=3.6*lw,w=1.5*lw;
  ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(p.x-ux*h-uy*w,p.y-uy*h+ux*w);ctx.lineTo(p.x-ux*h+uy*w,p.y-uy*h-ux*w);ctx.closePath();ctx.fill()}
function trim(p,d){const cut=(q,d)=>{let r=d;while(q.length>2){const l=Math.hypot(q[1].x-q[0].x,q[1].y-q[0].y);
    if(l>r){const t=r/l;q[0]={x:q[0].x+(q[1].x-q[0].x)*t,y:q[0].y+(q[1].y-q[0].y)*t};return q}r-=l;q.shift()}return q};
  return cut(cut(p.slice(),d).reverse(),d).reverse()}
/* ---- personnage : bouchon simple (tronc + tête, oreilles pointues, antennes ; direction A, sans bras) ---- */
function personnageStub(ctx,x,y,u,e){const C=e.couleurs||{},peau=C.peau||'#9fd8a8',vet=C.vetement||'#5e4b8b',cape=C.cape||'#f4f1ea',trait=C.trait||'#14201f';
  ctx.save();ctx.lineWidth=Math.max(1.3,.028*u);ctx.strokeStyle=trait;ctx.lineJoin='round';ctx.lineCap='round';
  const P=(bx,by)=>[x+bx*u,y+by*u];
  const piece=(f,fill)=>{ctx.beginPath();f();ctx.closePath();ctx.fillStyle=fill;ctx.fill();ctx.stroke()};
  // cape à épaulettes (silhouette en T inversé : rang 1 de ce que l'œil reconnaît)
  piece(()=>{ctx.moveTo(...P(-1.36,-.22));ctx.lineTo(...P(1.36,-.22));ctx.lineTo(...P(1.4,2.2));ctx.lineTo(...P(-1.4,2.2))},cape);
  // tronc (vêtement) et ceinture
  piece(()=>{ctx.moveTo(...P(-.91,.22));ctx.lineTo(...P(.91,.22));ctx.lineTo(...P(.75,2.2));ctx.lineTo(...P(-.75,2.2))},vet);
  ctx.fillStyle=trait;ctx.fillRect(...P(-.81,1.8),1.62*u,.26*u);
  // cou
  piece(()=>{ctx.moveTo(...P(-.27,-.6));ctx.lineTo(...P(.27,-.6));ctx.lineTo(...P(.32,-.06));ctx.lineTo(...P(-.32,-.06))},peau);
  // oreilles pointues
  [-1,1].forEach(s=>piece(()=>{ctx.moveTo(...P(s*.42,-1.3));ctx.lineTo(...P(s*.87,-1.5));ctx.lineTo(...P(s*.46,-1.0))},peau));
  // tête (ovale, menton −0,58, crâne −1,86)
  piece(()=>{ctx.ellipse(x,y-1.22*u,.5*u,.64*u,0,0,Math.PI*2)},peau);
  // antennes
  [-1,1].forEach(s=>{ctx.beginPath();ctx.moveTo(...P(s*.14,-1.72));ctx.quadraticCurveTo(...P(s*.2,-2.05),...P(s*.4,-2.1));ctx.stroke();ctx.beginPath();ctx.arc(...P(s*.4,-2.1),.05*u,0,7);ctx.fillStyle=peau;ctx.fill();ctx.stroke()});
  if(e.vue!=='dos'){// visage : yeux, sourcils selon l'expression, bouche
    const ex=e.expression||'neutre';ctx.fillStyle=trait;
    [-1,1].forEach(s=>{ctx.beginPath();ctx.ellipse(x+s*.27*u,y-1.16*u,.07*u,.09*u,0,0,7);ctx.fill();
      const dy=ex==='sourcils_leves'?-.16:ex==='sourcils_fronces'?-.07:-.12,pente=ex==='sourcils_fronces'?.06:ex==='sourcils_leves'?-.03:0;
      ctx.beginPath();ctx.moveTo(x+s*.4*u,y+(-1.16+dy-pente)*u);ctx.lineTo(x+s*.14*u,y+(-1.16+dy+pente)*u);ctx.stroke()});
    ctx.beginPath();if(ex==='sourire'){ctx.arc(x,y-.78*u,.14*u,.2,Math.PI-.2)}else{ctx.moveTo(x-.13*u,y-.71*u);ctx.lineTo(x+.13*u,y-.71*u)}ctx.stroke()}
  ctx.restore()}

/* ======================================================================
   Rendu à l'écran : canvas planche (contenu) + canvas ui (sélection, poignées, guides)
   ====================================================================== */
const dpr=()=>Math.min(devicePixelRatio||1,2);
function invalide(){S.dirty=true;S.dirtyUI=true;demande()}
let rafId=0;function demande(){if(!rafId)rafId=requestAnimationFrame(()=>{rafId=0;peint()})}
function tailleCanvas(){const w=stage.clientWidth,h=stage.clientHeight,r=dpr();[cvP,cvU].forEach(c=>{const W=Math.round(w*r),H=Math.round(h*r);if(c.width!==W||c.height!==H){c.width=W;c.height=H;S.dirty=S.dirtyUI=true}})}
function peint(){if(!S.doc)return;tailleCanvas();const r=dpr(),w=stage.clientWidth,h=stage.clientHeight;
  if(S.dirty){const ctx=cvP.getContext('2d');ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,cvP.width,cvP.height);ctx.setTransform(r,0,0,r,0,0);
    const P=S.doc.planche,[x,y]=ecran(0,0),W=P.w*S.zoom,H=P.h*S.zoom;
    // ombre portée et planche blanche ; damier 8 px derrière si le fond est transparent (jamais exporté)
    ctx.save();ctx.shadowColor='rgba(0,0,0,.25)';ctx.shadowBlur=18;ctx.shadowOffsetY=4;ctx.fillStyle='#fff';ctx.fillRect(x,y,W,H);ctx.restore();
    if(P.fond.type==='transparent'){ctx.save();ctx.beginPath();ctx.rect(x,y,W,H);ctx.clip();ctx.fillStyle='#e6e6e6';ctx.fillRect(x,y,W,H);ctx.fillStyle='#c8c8c8';
      for(let j=0;j*8<H;j++)for(let i=0;i*8<W;i++)if((i+j)%2===0)ctx.fillRect(x+i*8,y+j*8,8,8);ctx.restore()}
    ctx.save();ctx.translate(x,y);drawDoc(ctx,S.doc,S.zoom,{pix:r,editId:S.editId});ctx.restore();S.dirty=false}
  if(S.dirtyUI){peintUI();S.dirtyUI=false}
  placeOverlays()}
function cadre(){const els=selection();if(!els.length)return null;
  if(els.length===1){const e=els[0];return{cx:e.x+e.w/2,cy:e.y+e.h/2,w:e.w,h:e.h,rot:e.rot,flipH:e.flipH,flipV:e.flipV,e}}
  const b=bbox(els);return{cx:b.x+b.w/2,cy:b.y+b.h/2,w:b.w,h:b.h,rot:0,flipH:false,flipV:false}}
// coins / milieux du cadre en coordonnées écran (0 hg, 1 hm, 2 hd, 3 md, 4 bd, 5 bm, 6 bg, 7 mg, 8 rotation)
function poignees(c){const z=S.zoom,cs=Math.cos(c.rot*D2R),sn=Math.sin(c.rot*D2R);
  const L=[[0,0],[.5,0],[1,0],[1,.5],[1,1],[.5,1],[0,1],[0,.5]].map(([ax,ay])=>{const dx=(ax-.5)*c.w*z,dy=(ay-.5)*c.h*z;const[sx,sy]=ecran(c.cx,c.cy);return{x:sx+dx*cs-dy*sn,y:sy+dx*sn+dy*cs,ax,ay}});
  const dyr=-c.h*z/2-ROT_OFF,[sx,sy]=ecran(c.cx,c.cy);L.push({x:sx-dyr*sn,y:sy+dyr*cs,rot:true});return L}
function peintUI(){const ctx=cvU.getContext('2d'),r=dpr();ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,cvU.width,cvU.height);ctx.setTransform(r,0,0,r,0,0);
  const acc=getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()||INJS;
  // survol
  if(S.hover&&S.sel.indexOf(S.hover)<0&&!S.drag){const e=parId(S.hover);if(e){ctx.save();ctx.strokeStyle=acc;ctx.lineWidth=1;ctx.setLineDash([4,3]);ctx.beginPath();coins(e).map(p=>ecran(p[0],p[1])).forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.stroke();ctx.restore()}}
  const c=cadre();
  if(c&&S.mode==='planche'){ctx.save();ctx.strokeStyle=acc;ctx.lineWidth=1.5;
    const H=poignees(c);ctx.beginPath();H.slice(0,8).filter((_,i)=>i%2===0).forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();ctx.stroke();
    if(selection().length>1)selection().forEach(e=>{ctx.save();ctx.lineWidth=1;ctx.setLineDash([3,3]);ctx.beginPath();coins(e).map(p=>ecran(p[0],p[1])).forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));ctx.closePath();ctx.stroke();ctx.restore()});
    const verrou=selection().some(e=>e.verrou);
    if(!verrou){ctx.fillStyle='#fff';ctx.lineWidth=1.5;const main=c.e&&c.e.type==='main';
      H.forEach((p,i)=>{if(i===8){ctx.beginPath();ctx.moveTo(H[1].x,H[1].y);ctx.lineTo(p.x,p.y);ctx.stroke();ctx.beginPath();ctx.arc(p.x,p.y,POIGNEE/2+1,0,7);ctx.fill();ctx.stroke();return}
        if(main&&i%2===1)return;      // une main n'a que les coins : étirée, elle n'est plus une main
        if(c.e&&c.e.type==='fleche'&&i%2===1)return;
        ctx.save();ctx.translate(p.x,p.y);ctx.rotate(c.rot*D2R);ctx.fillRect(-POIGNEE/2,-POIGNEE/2,POIGNEE,POIGNEE);ctx.strokeRect(-POIGNEE/2,-POIGNEE/2,POIGNEE,POIGNEE);ctx.restore()})}
    else{ctx.fillStyle=getComputedStyle(document.documentElement).getPropertyValue('--lock');ctx.font='700 12px sans-serif';ctx.fillText('verrouillé',H[0].x,H[0].y-6)}
    ctx.restore()}
  // guides magenta
  if(S.guides.length){ctx.save();ctx.strokeStyle=getComputedStyle(document.documentElement).getPropertyValue('--guide').trim()||'#e0007a';ctx.lineWidth=1;ctx.setLineDash([6,4]);
    S.guides.forEach(g=>{ctx.beginPath();if(g.v!==undefined){const[x]=ecran(g.v,0);ctx.moveTo(x,0);ctx.lineTo(x,cvU.height)}else{const[,y]=ecran(0,g.h);ctx.moveTo(0,y);ctx.lineTo(cvU.width,y)}ctx.stroke()});ctx.restore()}
  if(S.marquee){const m=S.marquee;ctx.save();ctx.fillStyle='rgba(0,133,127,.12)';ctx.strokeStyle=acc;ctx.lineWidth=1;ctx.fillRect(m.x0,m.y0,m.x1-m.x0,m.y1-m.y0);ctx.strokeRect(m.x0,m.y0,m.x1-m.x0,m.y1-m.y0);ctx.restore()}}

/* ======================================================================
   Superpositions DOM : barre contextuelle, éditeur de texte, marionnette
   ====================================================================== */
function transformCSS(e){const[sx,sy]=ecran(e.x+e.w/2,e.y+e.h/2);
  return`translate(${sx}px,${sy}px) rotate(${e.rot}deg) scale(${e.flipH?-1:1},${e.flipV?-1:1}) translate(${-e.w*S.zoom/2}px,${-e.h*S.zoom/2}px)`}
function placeOverlays(){const c=cadre(),bar=$('ctx');
  if(c&&S.mode==='planche'&&!S.drag){const H=poignees(c);let x0=1e9,y0=1e9,x1=-1e9;H.slice(0,8).forEach(p=>{x0=Math.min(x0,p.x);y0=Math.min(y0,p.y);x1=Math.max(x1,p.x)});
    bar.hidden=false;const bw=bar.offsetWidth,bh=bar.offsetHeight;
    bar.style.left=clamp((x0+x1)/2-bw/2,8,Math.max(8,stage.clientWidth-bw-8))+'px';bar.style.top=clamp(y0-bh-ROT_OFF-14,8,stage.clientHeight-bh-8)+'px'}
  else if(S.mode!=='texte')bar.hidden=true;
  const ed=$('texte');if(S.mode==='texte'&&S.editId){const e=parId(S.editId);if(e){ed.style.transform=transformCSS(e);ed.style.width=e.w*S.zoom+'px';ed.style.minHeight=e.h*S.zoom+'px';
    ed.style.fontSize=e.corps*S.zoom+'px';ed.style.fontFamily='"'+e.police+'", "Atkinson Hyperlegible", sans-serif';ed.style.fontWeight=e.gras?700:400;ed.style.color=e.couleur;
    ed.style.padding=e.marge*S.zoom+'px';ed.style.lineHeight=e.interligne;ed.style.textAlign=e.align==='centre'?'center':e.align==='droite'?'right':'left';
    // bannière : le texte est centré verticalement comme au canvas (marge haute = (h − hauteur des lignes) / 2)
    const hl=hauteurTexte(e)-2*e.marge;ed.style.display='block';ed.style.height=e.fond?e.h*S.zoom+'px':'auto';ed.style.paddingTop=(e.fond?Math.max(e.marge,(e.h-hl)/2):e.marge)*S.zoom+'px';
    ed.style.webkitTextStroke=e.contour?(e.corps*S.zoom*.05)+'px '+e.contour:'';
    const bar2=$('ctx');bar2.hidden=false;const[sx,sy]=ecran(e.x,e.y);bar2.style.left=clamp(sx,8,stage.clientWidth-bar2.offsetWidth-8)+'px';bar2.style.top=clamp(sy-bar2.offsetHeight-12,8,stage.clientHeight-40)+'px'}}
  const pp=$('puppet');if(S.mode==='marionnette'&&S.puppetId){const e=parId(S.puppetId);if(e){const[sx,sy]=ecran(e.x,e.y);pp.style.left=Math.round(Math.min(sx+e.w*S.zoom+8,stage.clientWidth-270))+'px';pp.style.top=Math.round(clamp(sy,8,stage.clientHeight-220))+'px'}}}
function quitteModes(){if(S.mode==='texte')finTexte();if(S.mode==='marionnette')finMarionnette();S.mode='planche'}

/* ======================================================================
   Souris : sélection, glisser, poignées, rotation, rectangle, vue
   ====================================================================== */
let pointeurs=new Map();
function poigneeSous(sx,sy){const c=cadre();if(!c||S.mode!=='planche'||selection().some(e=>e.verrou))return null;const H=poignees(c),main=c.e&&(c.e.type==='main'||c.e.type==='fleche');
  for(let i=H.length-1;i>=0;i--){if(main&&i%2===1&&i<8)continue;const p=H[i];const r=i===8?POIGNEE/2+4:POIGNEE/2+3;if(Math.abs(sx-p.x)<=r&&Math.abs(sy-p.y)<=r)return Object.assign({i},p)}return null}
function curseur(sx,sy){if(S.espace)return'grab';const h=poigneeSous(sx,sy);if(h){if(h.rot)return'grab';const c=cadre();const a=((Math.atan2(h.ay-.5,h.ax-.5)/D2R+c.rot)%360+360)%360;const k=Math.round(a/45)%8;
    return['ew-resize','nwse-resize','ns-resize','nesw-resize','ew-resize','nwse-resize','ns-resize','nesw-resize'][k]}
  const[px,py]=planche(sx,sy);const e=sous(px,py);return e?'move':S.outil==='select'?'default':'crosshair'}
stage.addEventListener('pointerdown',ev=>{if(ev.target.closest&&ev.target.closest('#ctx,#puppet,#texte,.over'))return;   // les superpositions gardent leurs clics
  if(ev.button===1)return;stage.focus();const sx=ev.offsetX,sy=ev.offsetY;pointeurs.set(ev.pointerId,{x:sx,y:sy});
  if(pointeurs.size>1)return;          // pincement : géré dans pointermove
  stage.setPointerCapture(ev.pointerId);
  if(S.mode==='texte'){finTexte();S.mode='planche'}
  if(S.mode==='marionnette'){const e=parId(S.puppetId);const[px,py]=planche(sx,sy);if(!e||!touche(e,px,py)){finMarionnette();S.mode='planche'}else return}
  if(S.espace||ev.button===1){S.drag={type:'pan',sx,sy,ox:S.ox,oy:S.oy};return}
  if(ev.button===2)return;
  const[px,py]=planche(sx,sy);
  // outils de création : un clic pose l'objet
  if(S.outil!=='select'){creeAvecOutil(px,py);return}
  const h=poigneeSous(sx,sy);
  if(h){hist.begin();const c=cadre();S.drag=h.rot?{type:'rot',c,a0:Math.atan2(sy-ecran(c.cx,c.cy)[1],sx-ecran(c.cx,c.cy)[0])/D2R,rot0:c.rot,els:selection().map(clone)}
      :{type:'resize',h,c,els:selection().map(clone),sx,sy};return}
  const e=sous(px,py);
  if(e){const ids=groupeDe(e);
    if(ev.shiftKey){if(S.sel.indexOf(e.id)>=0)selectionne(S.sel.filter(id=>ids.indexOf(id)<0));else selectionne(ids,true)}
    else if(S.sel.indexOf(e.id)<0)selectionne(ids);
    hist.begin();S.drag={type:'move',sx,sy,els:selection().map(clone),alt:ev.altKey,bouge:false};S.dirtyUI=true;demande();return}
  if(!ev.shiftKey)selectionne([]);
  S.drag={type:'marquee',sx,sy,shift:ev.shiftKey,base:S.sel.slice()};S.dirtyUI=true;demande()});
stage.addEventListener('pointermove',ev=>{const sx=ev.offsetX,sy=ev.offsetY;S.souris=[sx,sy];
  if(pointeurs.has(ev.pointerId)){const prev=pointeurs.get(ev.pointerId);pointeurs.set(ev.pointerId,{x:sx,y:sy});
    if(pointeurs.size===2){const [a,b]=Array.from(pointeurs.values());if(!S.pince){S.pince={d:Math.hypot(a.x-b.x,a.y-b.y),zoom:S.zoom}}else{const d=Math.hypot(a.x-b.x,a.y-b.y);zoomVers(S.pince.zoom*d/S.pince.d,(a.x+b.x)/2,(a.y+b.y)/2)}S.drag=null;return}}
  const d=S.drag;
  if(!d){const[px,py]=planche(sx,sy);const e=S.mode==='planche'?sous(px,py):null;const id=e?e.id:null;if(id!==S.hover){S.hover=id;S.dirtyUI=true;demande()}stage.style.cursor=curseur(sx,sy);return}
  if(d.type==='pan'){S.ox=d.ox+sx-d.sx;S.oy=d.oy+sy-d.sy;invalide();return}
  if(d.type==='marquee'){S.marquee={x0:Math.min(d.sx,sx),y0:Math.min(d.sy,sy),x1:Math.max(d.sx,sx),y1:Math.max(d.sy,sy)};
    const[a,b]=planche(S.marquee.x0,S.marquee.y0),[c,e2]=planche(S.marquee.x1,S.marquee.y1);
    // intersection (Figma, Canva) : plus tolérant au trackpad
    const ids=S.doc.elements.filter(e=>!e.verrou&&e.visible&&bbox([e])&&!(bbox([e]).x>c||bbox([e]).x+bbox([e]).w<a||bbox([e]).y>e2||bbox([e]).y+bbox([e]).h<b)).map(e=>e.id);
    S.sel=Array.from(new Set((d.shift?d.base:[]).concat(ids)));S.dirtyUI=true;demande();return}
  if(d.type==='move'){const dx=(sx-d.sx)/S.zoom,dy=(sy-d.sy)/S.zoom;if(!d.bouge&&Math.hypot(sx-d.sx,sy-d.sy)<SEUIL)return;
    if(!d.bouge){d.bouge=true;if(d.alt){// Alt+glisser : la copie part, l'original reste (Canva, Figma)
        const copies=dupliqueElements(selection(),0,0);S.sel=copies.map(e=>e.id);d.els=selection().map(clone)}}
    const els=selection();els.forEach((e,i)=>{e.x=d.els[i].x+dx;e.y=d.els[i].y+dy});
    guidesEtAccroche(els,ev.ctrlKey);infobulle(sx,sy,Math.round(els[0].x)+', '+Math.round(els[0].y));invalide();return}
  if(d.type==='resize'){redimensionne(d,sx,sy,ev.shiftKey,ev.altKey);infobulle(sx,sy,Math.round(selection()[0].w)+' × '+Math.round(selection()[0].h));invalide();return}
  if(d.type==='rot'){const c=d.c,[cx,cy]=ecran(c.cx,c.cy);let a=d.rot0+Math.atan2(sy-cy,sx-cx)/D2R-d.a0;
    if(ev.shiftKey)a=Math.round(a/15)*15;else{const q=Math.round(a/90)*90;if(Math.abs(a-q)<=ROT_TOL)a=q}   // Maj : pas de 15° ; sinon accroche à 5° des quarts
    a=((a%360)+360)%360;if(a>180)a-=360;const els=selection();
    if(els.length===1){els[0].rot=a}
    else{const da=(a-d.rot0)*D2R,cs=Math.cos(da),sn=Math.sin(da);els.forEach((e,i)=>{const o=d.els[i],ox=o.x+o.w/2-c.cx,oy=o.y+o.h/2-c.cy;e.x=c.cx+ox*cs-oy*sn-e.w/2;e.y=c.cy+ox*sn+oy*cs-e.h/2;e.rot=o.rot+a-d.rot0})}
    infobulle(sx,sy,Math.round(a)+'°');invalide()}});
function finDrag(ev){const d=S.drag;if(!d)return;S.drag=null;S.marquee=null;S.guides=[];$('tip').hidden=true;
  if(d.type==='marquee'){selectionne(S.sel)}
  else if(d.type!=='pan'){if(d.type==='move'&&!d.bouge){hist.pending=null;if(ev&&ev.shiftKey===false&&ev.detail!==2){const[px,py]=planche(ev.offsetX,ev.offsetY);const e=sous(px,py);if(e&&!ev.shiftKey&&selection().length>1&&S.sel.indexOf(e.id)>=0)selectionne(groupeDe(e))}}
    else{selection().forEach(e=>{if(e.type==='texte')ajusteTexte(e)});hist.commit()}}
  invalide();panneaux()}
stage.addEventListener('pointerup',ev=>{pointeurs.delete(ev.pointerId);if(pointeurs.size<2)S.pince=null;finDrag(ev)});
stage.addEventListener('pointercancel',ev=>{pointeurs.delete(ev.pointerId);S.pince=null;finDrag(null)});
stage.addEventListener('lostpointercapture',()=>{});
stage.addEventListener('dblclick',ev=>{const[px,py]=planche(ev.offsetX,ev.offsetY);const e=sous(px,py);if(!e)return;selectionne([e.id]);
  if(e.type==='texte')editeTexte(e.id);else if(e.type==='main')marionnette(e.id)});
stage.addEventListener('contextmenu',ev=>ev.preventDefault());
stage.addEventListener('wheel',ev=>{ev.preventDefault();if(ev.ctrlKey||ev.metaKey){zoomVers(S.zoom*Math.exp(-ev.deltaY*.0015),ev.offsetX,ev.offsetY)}
  else if(ev.shiftKey){S.ox-=ev.deltaY;invalide()}else{S.ox-=ev.deltaX;S.oy-=ev.deltaY;invalide()}},{passive:false});
function infobulle(sx,sy,txt){const t=$('tip');t.hidden=false;t.textContent=txt;t.style.left=(sx+14)+'px';t.style.top=(sy-28)+'px'}
// redimensionnement : résolu dans le repère LOCAL de l'objet, le coin opposé reste fixe ; coins proportionnels (Maj inverse)
function redimensionne(d,sx,sy,shift,altK){const h=d.h,c=d.c,els=selection();const o=d.els,coin=h.ax!==.5&&h.ay!==.5;
  const base=els.length===1?o[0]:{x:c.cx-c.w/2,y:c.cy-c.h/2,w:c.w,h:c.h,rot:0,flipH:false,flipV:false};
  const[px,py]=planche(sx,sy),[lx,ly]=versLocal(base,px,py);
  const ux=1-h.ax,uy=1-h.ay;let w=base.w,hh=base.h;
  if(h.ax!==.5)w=h.ax===1?lx:base.w-lx;if(h.ay!==.5)hh=h.ay===1?ly:base.h-ly;
  const main=els.length===1&&(els[0].type==='main'||els[0].type==='personnage'||els[0].type==='image');
  let prop=coin?!shift:false;if(main)prop=true;
  if(prop){// proportionnel : l'axe qui a le plus bougé commande
    const sx=w/base.w,sy=hh/base.h;const s=h.ax===.5?sy:h.ay===.5?sx:(Math.abs(sx-1)>Math.abs(sy-1)?sx:sy);w=base.w*s;hh=base.h*s}
  w=Math.max(MIN_T,w);hh=Math.max(MIN_T,hh);
  if(altK){// depuis le centre : le centre reste fixe
    const cx=base.x+base.w/2,cy=base.y+base.h/2;applique(els,o,base,{x:cx-w/2,y:cy-hh/2,w,h:hh});return}
  const x0=h.ax===0?base.w-w:0,y0=h.ay===0?base.h-hh:0;const[cx,cy]=versPlanche(base,x0+w/2,y0+hh/2);
  applique(els,o,base,{x:cx-w/2,y:cy-hh/2,w,h:hh})}
function applique(els,o,base,n){if(els.length===1){const e=els[0];const sx=n.w/base.w,sy=n.h/base.h;
    e.x=n.x;e.y=n.y;e.w=n.w;e.h=n.h;
    if(e.type==='texte'){if(Math.abs(sx-sy)<1e-6&&sx!==1)e.corps=Math.max(6,+(o[0].corps*sx).toFixed(1));else if(!e.fond)e.h=hauteurTexte(e)}
    if(e.type==='fleche'&&e.epaisseur>0)e.epaisseur=o[0].epaisseur;return}
  const sx=n.w/base.w,sy=n.h/base.h;els.forEach((e,i)=>{const a=o[i];e.x=n.x+(a.x-base.x)*sx;e.y=n.y+(a.y-base.y)*sy;e.w=Math.max(MIN_T,a.w*sx);e.h=Math.max(MIN_T,a.h*sy);
    if(e.type==='texte'&&Math.abs(sx-sy)<1e-6)e.corps=Math.max(6,+(a.corps*sx).toFixed(1))})}
// guides intelligents : bords et centres à ≤ 5 px écran d'un autre objet ou de la planche
function guidesEtAccroche(els,sans){S.guides=[];if(sans)return;const b=bbox(els);if(!b)return;const tol=SNAP/S.zoom,P=S.doc.planche;
  const autres=S.doc.elements.filter(e=>e.visible&&S.sel.indexOf(e.id)<0);
  const xs=[0,P.w/2,P.w],ys=[0,P.h/2,P.h];autres.forEach(e=>{const o=bbox([e]);xs.push(o.x,o.x+o.w/2,o.x+o.w);ys.push(o.y,o.y+o.h/2,o.y+o.h)});
  let bx=null,by=null,dx=0,dy=0;
  [b.x,b.x+b.w/2,b.x+b.w].forEach(v=>xs.forEach(x=>{if(Math.abs(v-x)<=tol&&(bx===null||Math.abs(v-x)<Math.abs(dx))){bx=x;dx=x-v}}));
  [b.y,b.y+b.h/2,b.y+b.h].forEach(v=>ys.forEach(y=>{if(Math.abs(v-y)<=tol&&(by===null||Math.abs(v-y)<Math.abs(dy))){by=y;dy=y-v}}));
  if(bx!==null){els.forEach(e=>e.x+=dx);S.guides.push({v:bx})}if(by!==null){els.forEach(e=>e.y+=dy);S.guides.push({h:by})}}
function zoomVers(z,sx,sy){z=clamp(z,.1,8);const[px,py]=planche(sx,sy);S.zoom=z;S.ox=sx-px*z;S.oy=sy-py*z;$('zOut').textContent=Math.round(z*100)+' %';invalide()}
function ajuste(){const P=S.doc.planche,w=stage.clientWidth,h=stage.clientHeight;const z=clamp(Math.min((w-48)/P.w,(h-48)/P.h),.05,8);S.zoom=z;S.ox=(w-P.w*z)/2;S.oy=(h-P.h*z)/2;$('zOut').textContent=Math.round(z*100)+' %';invalide()}

/* ======================================================================
   Outils de création
   ====================================================================== */
function creeAvecOutil(px,py){const P=S.doc.planche,o=S.outil;let e=null;
  if(o==='mainD'||o==='mainG'){e=nouvelElement('main',{cote:o==='mainD'?'D':'G'});e.nom='Main '+e.cote;const h=P.h*.38;e.h=h;e.w=h*mainBoite(e).w/mainBoite(e).h}
  else if(o==='texte'){e=nouvelElement('texte');e.w=Math.max(200,P.w*.3);ajusteTexte(e)}
  else if(o==='fleche'){e=nouvelElement('fleche',{couleur:S.doc.theme.couleur});e.w=P.w*.2;e.h=P.h*.1}
  else if(o==='personnage'){e=nouvelElement('personnage');e.h=P.h*.9;e.w=e.h*PERS_HL.w/PERS_HL.h}
  else if(o==='image'){$('fichierImage').click();outil('select');return}
  if(!e)return;e.x=px-e.w/2;e.y=py-e.h/2;act(()=>{S.doc.elements.push(e)});selectionne([e.id]);outil('select');
  if(e.type==='texte')editeTexte(e.id)}
function ajoute(type,props){const e=nouvelElement(type,props||{});const P=S.doc.planche;
  if(type==='main'){if(!props||!props.h){e.h=P.h*.38;e.w=e.h*mainBoite(e).w/mainBoite(e).h}}
  if(type==='personnage'&&(!props||!props.h)){e.h=P.h*.9;e.w=e.h*PERS_HL.w/PERS_HL.h}
  if(type==='texte')ajusteTexte(e);
  if(!props||props.x===undefined){e.x=(P.w-e.w)/2;e.y=(P.h-e.h)/2}
  act(()=>{S.doc.elements.push(e)});selectionne([e.id]);return e}
function outil(o){S.outil=o;document.querySelectorAll('[data-outil]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.outil===o)));stage.style.cursor=o==='select'?'default':'crosshair'}
document.querySelectorAll('[data-outil]').forEach(b=>b.onclick=()=>{quitteModes();outil(b.dataset.outil);if(b.dataset.outil==='image'){$('fichierImage').click();outil('select')}});
$('bGabarits').onclick=()=>onglet('projet');

/* ======================================================================
   Opérations sur les éléments
   ====================================================================== */
function dupliqueElements(els,dx,dy){const nouveaux=[];const map={};els.forEach(e=>{const c=clone(e);c.id=uid();c.x+=dx;c.y+=dy;map[e.id]=c.id;nouveaux.push(c)});
  // un groupe dupliqué devient un nouveau groupe
  const gmap={};nouveaux.forEach(c=>{c.groupes=(c.groupes||[]).map(g=>gmap[g]||(gmap[g]='g'+uid()))});
  S.doc.elements.push(...nouveaux);return nouveaux}
function duplique(){const els=selection();if(!els.length)return;let ids=[];act(()=>{ids=dupliqueElements(els,10,10).map(e=>e.id)});selectionne(ids)}
function supprime(){const ids=S.sel;if(!ids.length)return;act(()=>{S.doc.elements=S.doc.elements.filter(e=>ids.indexOf(e.id)<0||e.verrou)});selectionne([])}
function copie(){const els=selection();if(!els.length)return;S.clip=clone(els);try{navigator.clipboard.writeText(JSON.stringify({app:'atelier-mains-lsf',elements:S.clip}))}catch(e){}}
function colle(){if(!S.clip)return;let ids=[];const sur=S.souris&&S.souris[0]>=0;const b=bbox(S.clip);let dx=10,dy=10;
  if(sur&&b){const[px,py]=planche(S.souris[0],S.souris[1]);if(px>=0&&py>=0&&px<=S.doc.planche.w&&py<=S.doc.planche.h){dx=px-b.x-b.w/2;dy=py-b.y-b.h/2}}
  act(()=>{ids=dupliqueElements(S.clip,dx,dy).map(e=>e.id)});selectionne(ids)}
function ordre(sens){const L=S.doc.elements,ids=S.sel;if(!ids.length)return;act(()=>{
  if(sens==='devant'){const m=L.filter(e=>ids.indexOf(e.id)>=0);S.doc.elements=L.filter(e=>ids.indexOf(e.id)<0).concat(m)}
  else if(sens==='derriere'){const m=L.filter(e=>ids.indexOf(e.id)>=0);S.doc.elements=m.concat(L.filter(e=>ids.indexOf(e.id)<0))}
  else if(sens===1){for(let i=L.length-2;i>=0;i--)if(ids.indexOf(L[i].id)>=0&&ids.indexOf(L[i+1].id)<0){[L[i],L[i+1]]=[L[i+1],L[i]]}}
  else{for(let i=1;i<L.length;i++)if(ids.indexOf(L[i].id)>=0&&ids.indexOf(L[i-1].id)<0){[L[i],L[i-1]]=[L[i-1],L[i]]}}})}
function verrou(){const els=selection();if(!els.length)return;const v=!els.every(e=>e.verrou);act(()=>els.forEach(e=>e.verrou=v))}
function groupe(){const els=selection();if(els.length<2)return;const g='g'+uid();act(()=>els.forEach(e=>{e.groupes=(e.groupes||[]).concat([g])}))}
function degroupe(){const els=selection();act(()=>els.forEach(e=>{if(e.groupes&&e.groupes.length)e.groupes.pop()}))}
function miroir(axe){const els=selection();if(!els.length)return;act(()=>{if(els.length===1){const e=els[0];if(axe==='H')e.flipH=!e.flipH;else e.flipV=!e.flipV}
  else{const b=bbox(els);els.forEach(e=>{if(axe==='H'){e.x=2*(b.x+b.w/2)-e.x-e.w;e.flipH=!e.flipH;e.rot=-e.rot}else{e.y=2*(b.y+b.h/2)-e.y-e.h;e.flipV=!e.flipV;e.rot=-e.rot}})}})}
function aligne(mode){const els=selection();if(!els.length)return;const P=S.doc.planche;const ref=els.length>1?bbox(els):{x:0,y:0,w:P.w,h:P.h};
  act(()=>els.forEach(e=>{const b=bbox([e]);const dx=mode==='gauche'?ref.x-b.x:mode==='centre'?ref.x+ref.w/2-b.x-b.w/2:mode==='droite'?ref.x+ref.w-b.x-b.w:0;
    const dy=mode==='haut'?ref.y-b.y:mode==='milieu'?ref.y+ref.h/2-b.y-b.h/2:mode==='bas'?ref.y+ref.h-b.y-b.h:0;e.x+=dx;e.y+=dy}))}
function repartit(axe){const els=selection();if(els.length<3)return;const k=axe==='h'?'x':'y',d=axe==='h'?'w':'h';const L=els.slice().sort((a,b)=>bbox([a])[k]-bbox([b])[k]);
  const b0=bbox([L[0]]),b1=bbox([L[L.length-1]]);const tot=L.reduce((s,e)=>s+bbox([e])[d],0);const gap=((b1[k]+b1[d])-b0[k]-tot)/(L.length-1);
  act(()=>{let p=b0[k];L.forEach(e=>{const b=bbox([e]);e[k]+=p-b[k];p+=b[d]+gap})})}
function deplace(dx,dy){const els=selection().filter(e=>!e.verrou);if(!els.length)return;act(()=>els.forEach(e=>{e.x+=dx;e.y+=dy}))}
// convertir en main gauche / droite : miroir 3D (côté inversé, orientation réfléchie), PAS miroir d'image (l'ombre resterait du bon côté)
function convertitCote(){const els=selection().filter(e=>e.type==='main');if(!els.length)return;act(()=>els.forEach(e=>{e.cote=e.cote==='D'?'G':'D';e.flipH=false;
  const A=AH();e.pose=A&&A.mirror?A.mirror(e.pose):e.pose;e.orientation=A&&A.mirrorOrientation?A.mirrorOrientation(e.orientation):[e.orientation[0],-e.orientation[1],-e.orientation[2],e.orientation[3]];
  e.nom=e.nom.replace(/Main [DG]/,'Main '+e.cote);ajusteProportionMain(e)}))}
let posePP=null;
function copiePose(){const e=selection().find(x=>x.type==='main');if(e){posePP={pose:clone(e.pose),orientation:clone(e.orientation),cote:e.cote};message('Pose copiée.')}}
function collePose(){if(!posePP)return;const els=selection().filter(e=>e.type==='main');if(!els.length)return;act(()=>els.forEach(e=>{const A=AH();e.pose=clone(posePP.pose);
  if(e.cote!==posePP.cote&&A&&A.mirror)e.pose=A.mirror(e.pose);e.orientation=clone(posePP.orientation);ajusteProportionMain(e)}))}
// éclater en étapes : N mains côte à côte + flèches entre elles (depuis mouvement.cles s'il existe, sinon copies)
function eclate(n){const e=selection().find(x=>x.type==='main');if(!e)return;const cles=e.mouvement&&Array.isArray(e.mouvement.cles)&&e.mouvement.cles.length>1?e.mouvement.cles:null;
  n=cles?cles.length:clamp(n||3,2,6);const gap=e.w*.45;let ids=[];
  act(()=>{for(let i=0;i<n;i++){const c=clone(e);c.id=uid();c.mouvement=null;c.x=e.x+i*(e.w+gap);c.nom=e.nom+' · étape '+(i+1);c.groupes=[];
      if(cles){c.pose=clone(cles[i].pose||c.pose);if(cles[i].orientation)c.orientation=clone(cles[i].orientation)}
      S.doc.elements.push(c);ids.push(c.id);
      if(i<n-1){const f=nouvelElement('fleche',{couleur:S.doc.theme.couleur,style:(cles&&cles[i].fl&&cles[i].fl.style)||'droite'});f.x=c.x+c.w+gap*.1;f.y=e.y+e.h*.45;f.w=gap*.8;f.h=e.h*.1;S.doc.elements.push(f);ids.push(f.id)}}
    S.doc.elements=S.doc.elements.filter(x=>x.id!==e.id)});selectionne(ids)}
function toutSelectionner(){selectionne(S.doc.elements.filter(e=>!e.verrou&&e.visible).map(e=>e.id))}
function message(t,err){const m=$('topMsg');m.textContent=t;m.className='msg'+(err?' err':'');clearTimeout(message.t);message.t=setTimeout(()=>{m.textContent=''},6000)}

/* ======================================================================
   Texte : un <div contenteditable> superposé exactement sur l'objet ; à la sortie, le texte est redessiné au canvas
   ====================================================================== */
const ed=$('texte');
function editeTexte(id){const e=parId(id);if(!e||e.verrou)return;quitteModes();S.mode='texte';S.editId=id;hist.begin();
  ed.hidden=false;ed.innerHTML=htmlTexte(e);S.dirty=true;demande();placeOverlays();panneaux();
  // le focus après le geste : le mousedown qui a créé le texte rend sinon le focus au plateau juste après
  setTimeout(()=>{if(S.editId!==id)return;ed.focus();const r=document.createRange();r.selectNodeContents(ed);r.collapse(false);const sel=getSelection();sel.removeAllRanges();sel.addRange(r)},0)}
function htmlTexte(e){const t=e.texte||'',segs=(e.surlignages||[]).slice().sort((a,b)=>a.from-b.from);let h='',p=0;
  segs.forEach(sg=>{if(sg.from>p)h+=esc(t.slice(p,sg.from));h+='<mark style="background:'+esc(sg.couleur)+'">'+esc(t.slice(Math.max(p,sg.from),sg.to))+'</mark>';p=Math.max(p,sg.to)});
  return h+esc(t.slice(p))}
// relire le DOM : nœuds texte dans l'ordre, <br> = retour, <mark> = segment surligné
function litEditeur(){let t='';const segs=[];const marche=(n,mark)=>{if(n.nodeType===3){if(mark){const s=segs[segs.length-1];if(s&&s.to===t.length&&s.couleur===mark)s.to+=n.data.length;else segs.push({from:t.length,to:t.length+n.data.length,couleur:mark})}t+=n.data;return}
    if(n.nodeName==='BR'){t+='\n';return}
    const bloc=/^(DIV|P)$/.test(n.nodeName);if(bloc&&t.length&&!t.endsWith('\n'))t+='\n';
    const m=n.nodeName==='MARK'?(n.style.backgroundColor?rgbVersHex(n.style.backgroundColor):mark):mark;Array.from(n.childNodes).forEach(c=>marche(c,m))};
  Array.from(ed.childNodes).forEach(c=>marche(c,null));return{texte:t.replace(/\n$/,''),surlignages:segs.filter(s=>s.to>s.from)}}
function rgbVersHex(s){const m=s.match(/\d+/g);if(!m||m.length<3)return'#fff176';return'#'+m.slice(0,3).map(x=>(+x).toString(16).padStart(2,'0')).join('')}
ed.addEventListener('input',()=>{const e=parId(S.editId);if(!e)return;const r=litEditeur();e.texte=r.texte;e.surlignages=r.surlignages;ajusteTexte(e);invalide()});
ed.addEventListener('keydown',ev=>{if(ev.key==='Escape'){ev.preventDefault();quitteModes();invalide();stage.focus();return}
  if(ev.key==='Enter'){ev.preventDefault();document.execCommand('insertLineBreak');return}ev.stopPropagation()});
ed.addEventListener('paste',ev=>{ev.preventDefault();const t=(ev.clipboardData||window.clipboardData).getData('text/plain');document.execCommand('insertText',false,t)});
function finTexte(){const e=parId(S.editId);S.mode='planche';S.editId=null;ed.hidden=true;ed.style.display='none';
  if(e){const r=litEditeur();e.texte=r.texte;e.surlignages=r.surlignages;if(!e.texte.trim()){S.doc.elements=S.doc.elements.filter(x=>x.id!==e.id);S.sel=S.sel.filter(id=>id!==e.id)}else ajusteTexte(e)}
  hist.commit();invalide();panneaux()}
// décalages [from,to] de la sélection courante dans le texte plat de l'éditeur
function offsetsSelection(){const sel=getSelection();if(!sel.rangeCount||!ed.contains(sel.anchorNode))return null;const r=sel.getRangeAt(0);
  const pos=(node,off)=>{const pre=document.createRange();pre.selectNodeContents(ed);pre.setEnd(node,off);const frag=pre.cloneContents();let n=0;const m=x=>{if(x.nodeType===3)n+=x.data.length;else if(x.nodeName==='BR')n++;else{if(/^(DIV|P)$/.test(x.nodeName)&&n&&!endsNl(n))n++;Array.from(x.childNodes).forEach(m)}};
    const endsNl=()=>false;Array.from(frag.childNodes).forEach(m);return n};
  return[pos(r.startContainer,r.startOffset),pos(r.endContainer,r.endOffset)]}
function restaureSelection(a,b){const sel=getSelection();const r=document.createRange();let n=0,s=null,e=null;
  const marche=x=>{if(s&&e)return;if(x.nodeType===3){const L=x.data.length;if(!s&&a<=n+L){s=[x,a-n]}if(s&&!e&&b<=n+L){e=[x,b-n]}n+=L}else if(x.nodeName==='BR'){n++}else Array.from(x.childNodes).forEach(marche)};
  marche(ed);if(!s)return;r.setStart(s[0],s[1]);if(e)r.setEnd(e[0],e[1]);else r.collapse(false);sel.removeAllRanges();sel.addRange(r)}
function surligne(couleur){const e=parId(S.editId);if(!e)return;let o=offsetsSelection();if(!o||o[0]===o[1]){o=[0,(e.texte||'').length]}  // rien de sélectionné : tout le texte
  const[a,b]=o;let segs=[];(e.surlignages||[]).forEach(sg=>{if(sg.to<=a||sg.from>=b){segs.push(sg);return}if(sg.from<a)segs.push({from:sg.from,to:a,couleur:sg.couleur});if(sg.to>b)segs.push({from:b,to:sg.to,couleur:sg.couleur})});
  if(couleur)segs.push({from:a,to:b,couleur});segs.sort((x,y)=>x.from-y.from);e.surlignages=segs;ed.innerHTML=htmlTexte(e);restaureSelection(a,b);invalide()}

/* ======================================================================
   Marionnette : AtelierHand.puppet en place sur l'objet ; une entrée d'historique par relâchement
   ====================================================================== */
function marionnette(id){const e=parId(id);if(!e||e.type!=='main'||e.verrou)return;const A=AH();if(!A||!A.puppet){message('Moteur de main absent.',true);return}
  quitteModes();S.mode='marionnette';S.puppetId=id;hist.begin();const host=$('puppet');host.hidden=false;
  S.puppet=A.puppet(host,e,pose=>{const el=parId(S.puppetId);if(!el)return;el.pose=pose;ajusteProportionMain(el);S.dirty=true;S.dirtyUI=true;demande()});
  host.onpointerup=()=>{hist.commit();hist.begin()};panneaux();placeOverlays()}
function finMarionnette(){try{if(S.puppet&&S.puppet.stop)S.puppet.stop()}catch(e){}S.puppet=null;$('puppet').hidden=true;$('puppet').onpointerup=null;S.mode='planche';S.puppetId=null;hist.commit();invalide();panneaux()}

/* ======================================================================
   Clavier (hors champs de saisie et contenteditable)
   ====================================================================== */
const dansSaisie=()=>{const a=document.activeElement;return a&&(a.isContentEditable||/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName))};
document.addEventListener('keydown',ev=>{if(ev.key===' '&&!dansSaisie()){if(!S.espace){S.espace=true;stage.style.cursor='grab'}ev.preventDefault();return}
  const C=ev.ctrlKey||ev.metaKey,M=ev.shiftKey,k=ev.key.toLowerCase();
  if(C&&!dansSaisie()){const map={z:()=>M?hist.redoer():hist.undoer(),y:()=>hist.redoer(),c:copie,x:()=>{copie();supprime()},v:()=>{},d:duplique,a:toutSelectionner,g:()=>M?degroupe():groupe(),
      ']':()=>ordre(ev.altKey?'devant':1),'[':()=>ordre(ev.altKey?'derriere':-1),s:enregistreDb,e:()=>ouvreExport(),'0':ajuste,'1':()=>zoomVers(1,stage.clientWidth/2,stage.clientHeight/2)};
    if(map[k]){ev.preventDefault();map[k]();return}if(k==='v'&&M){ev.preventDefault();collePose();return}return}
  if(dansSaisie()){if(ev.key==='Escape'&&document.activeElement!==ed){document.activeElement.blur();stage.focus()}return}
  if(ev.key==='Escape'){if(S.mode!=='planche'){quitteModes();invalide()}else selectionne([]);outil('select');return}
  if(ev.key==='Delete'||ev.key==='Backspace'){ev.preventDefault();supprime();return}
  if(/^Arrow/.test(ev.key)){ev.preventDefault();const p=M?10:1;deplace(ev.key==='ArrowLeft'?-p:ev.key==='ArrowRight'?p:0,ev.key==='ArrowUp'?-p:ev.key==='ArrowDown'?p:0);return}
  if(ev.key==='Enter'){const e=selection()[0];if(e){ev.preventDefault();if(e.type==='main')marionnette(e.id);else if(e.type==='texte')editeTexte(e.id)}return}
  if(ev.altKey&&M&&k==='l'){ev.preventDefault();verrou();return}
  if(M&&k==='h'){miroir('H');return}if(M&&k==='v'){miroir('V');return}
  if(M&&k==='m'){outil('mainG');return}
  const outils={v:'select',m:'mainD',t:'texte',i:'image',a:'fleche',p:'personnage'};
  if(outils[k]&&!ev.altKey){outil(outils[k]);if(k==='i')$('fichierImage').click();return}
  if(k==='g'&&!ev.altKey){onglet('projet');return}
  if(ev.key==='?'){$('dlgAide').showModal()}});
document.addEventListener('keyup',ev=>{if(ev.key===' '){S.espace=false;stage.style.cursor='default'}});
// coller : une image du système (clipboardData.files) ou des éléments de l'atelier
document.addEventListener('paste',ev=>{if(dansSaisie()&&document.activeElement!==stage)return;const cd=ev.clipboardData;if(!cd)return;
  const files=Array.from(cd.files||[]).filter(f=>/^image\//.test(f.type)||/\.(heic|heif)$/i.test(f.name));
  if(files.length){ev.preventDefault();importeImages(files);return}
  const t=cd.getData('text/plain');if(t&&/"app":"atelier-mains-lsf"/.test(t)){try{const o=JSON.parse(t);if(Array.isArray(o.elements)){S.clip=o.elements;ev.preventDefault();colle();return}}catch(e){}}
  if(S.clip){ev.preventDefault();colle()}});
// glisser-déposer depuis l'ordinateur
let dragN=0;stage.addEventListener('dragenter',ev=>{ev.preventDefault();dragN++;$('drop').hidden=false});
stage.addEventListener('dragleave',()=>{if(--dragN<=0){dragN=0;$('drop').hidden=true}});
stage.addEventListener('dragover',ev=>{ev.preventDefault();ev.dataTransfer.dropEffect='copy'});
stage.addEventListener('drop',ev=>{ev.preventDefault();dragN=0;$('drop').hidden=true;const files=Array.from(ev.dataTransfer.files||[]);const r=stage.getBoundingClientRect();
  const[px,py]=planche(ev.clientX-r.left,ev.clientY-r.top);
  const proj=files.find(f=>/\.json$/i.test(f.name));if(proj){ouvreFichier(proj);return}
  importeImages(files,{x:px,y:py})});
$('fichierImage').onchange=()=>{importeImages(Array.from($('fichierImage').files));$('fichierImage').value=''};

/* ======================================================================
   Images : décodage (EXIF appliqué par le navigateur), réduction à 4 096 px, ré-encodage, asset en data:
   ====================================================================== */
async function decodeImage(file){try{return await createImageBitmap(file,{imageOrientation:'from-image'})}catch(e){}
  // repli : <img> + decode()
  const url=URL.createObjectURL(file);try{const im=new Image();im.src=url;await im.decode();return im}finally{URL.revokeObjectURL(url)}}
async function reduitImage(src,typeSrc){let w=src.width||src.naturalWidth,h=src.height||src.naturalHeight;const f=Math.max(w,h)/IMG_MAX;let cur=src;
  // deux étapes de ½ si le facteur dépasse 4 (qualité), jamais resizeWidth de createImageBitmap (bogue WebKit 202458)
  if(f>1){let tw=Math.round(w/f),th=Math.round(h/f);while(w/tw>4){const c=document.createElement('canvas');c.width=Math.round(w/2);c.height=Math.round(h/2);const x=c.getContext('2d');x.imageSmoothingQuality='high';x.drawImage(cur,0,0,c.width,c.height);cur=c;w=c.width;h=c.height}
    const c=document.createElement('canvas');c.width=tw;c.height=th;const x=c.getContext('2d');x.imageSmoothingQuality='high';x.drawImage(cur,0,0,tw,th);cur=c;w=tw;h=th}
  if(!(cur instanceof HTMLCanvasElement)){const c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(cur,0,0);cur=c}
  // JPEG q 0,9 sans alpha, PNG sinon
  const jpeg=/jpe?g/i.test(typeSrc);const data=cur.toDataURL(jpeg?'image/jpeg':'image/png',.9);return{data,w,h}}
function assetAjoute(data){const id='a'+uid();S.doc.assets[id]=data;chargeAsset(id,data);return id}
function chargeAsset(id,data){const im=new Image();im.onload=()=>invalide();im.src=data;IMG.set(id,im);return im}
async function importeImages(files,pos){const P=S.doc.planche;let n=0;
  for(const f of files){if(/heic|heif/i.test(f.type)||/\.(heic|heif)$/i.test(f.name)){message('Ce format (HEIC) n\'est pas lisible ici : exporte la photo en JPEG depuis Photos, ou règle l\'iPhone sur « Le plus compatible ».',true);continue}
    if(!/^image\//.test(f.type)&&!/\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(f.name))continue;
    let src;try{src=await decodeImage(f)}catch(e){message('Image illisible : '+f.name,true);continue}
    const r=await reduitImage(src,f.type);const id=assetAjoute(r.data);
    if(S.fondCible){S.fondCible=false;act(()=>{const F=S.doc.planche.fond;F.type='image';F.src=id});n++;continue}   // « Choisir une image… » du panneau Planche
    // taille = min(image, 60 % de la planche), centrée ou sous le pointeur
    const s=Math.min(1,P.w*.6/r.w,P.h*.6/r.h),w=r.w*s,h=r.h*s;
    const e=nouvelElement('image',{asset:id,nom:f.name.replace(/\.[^.]+$/,'').slice(0,40)||'Image',w,h});e.x=(pos?pos.x:P.w/2)-w/2+n*10;e.y=(pos?pos.y:P.h/2)-h/2+n*10;
    act(()=>S.doc.elements.push(e));selectionne([e.id]);n++}
  if(n)message(n+(n>1?' images importées.':' image importée.'))}
function definirFond(){const e=selection().find(x=>x.type==='image');if(!e)return;act(()=>{const F=S.doc.planche.fond;F.type='image';F.src=e.asset;F.mode='couvrir';S.doc.elements=S.doc.elements.filter(x=>x.id!==e.id)});selectionne([]);onglet('planche')}
function detacherFond(){const F=S.doc.planche.fond;if(F.type!=='image'||!F.src)return;const im=IMG.get(F.src),P=S.doc.planche;
  const iw=im?im.naturalWidth:P.w,ih=im?im.naturalHeight:P.h,s=Math.max(P.w/iw,P.h/ih);
  const e=nouvelElement('image',{asset:F.src,nom:'Fond',w:iw*s,h:ih*s});e.x=(P.w-e.w)/2;e.y=(P.h-e.h)/2;
  act(()=>{F.type='uni';F.src=null;S.doc.elements.unshift(e)});selectionne([e.id])}

/* ======================================================================
   Panneaux : propriétés (par type), planche, calques, thème, barre contextuelle
   ====================================================================== */
function onglet(n){document.querySelectorAll('[role=tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===n)));document.querySelectorAll('[data-pane]').forEach(p=>p.hidden=p.dataset.pane!==n)}
document.querySelectorAll('[role=tab]').forEach(b=>b.onclick=()=>onglet(b.dataset.tab));
const h=(tag,attrs,...kids)=>{const el=document.createElement(tag);for(const k in attrs||{}){if(k==='on')for(const ev in attrs.on)el.addEventListener(ev,attrs.on[ev]);else if(k==='html')el.innerHTML=attrs[k];else if(k in el&&k!=='style')el[k]=attrs[k];else el.setAttribute(k,attrs[k])}
  kids.flat().forEach(c=>{if(c==null)return;el.appendChild(c instanceof Node?c:document.createTextNode(String(c)))});return el};
// champ numérique lié à un attribut de TOUS les éléments sélectionnés
function champNum(label,get,set,min,max,step){const inp=h('input',{type:'number',value:get(),min,max,step:step||1});
  inp.onchange=()=>{const v=+inp.value;if(!isFinite(v))return;act(()=>selection().forEach(e=>set(e,clamp(v,min,max))))};return h('div',{className:'row'},h('label',{},label),inp,h('span',{}))}
function champRange(label,val,min,max,step,oncommit,fmt){const inp=h('input',{type:'range',min,max,step,value:val}),out=h('output',{},(fmt||(v=>v))(val));
  let began=false;inp.oninput=()=>{if(!began){hist.begin();began=true}out.textContent=(fmt||(v=>v))(+inp.value);oncommit(+inp.value);invalide()};inp.onchange=()=>{hist.commit();began=false;panneaux()};
  return h('div',{className:'row'},h('label',{},label),inp,out)}
function champCouleur(label,val,set,nullable){const inp=h('input',{type:'color',value:val||'#ffffff'});inp.oninput=()=>{hist.begin();set(inp.value);invalide()};inp.onchange=()=>{hist.commit()};
  const kids=[h('label',{},label),inp];if(nullable){const cb=h('input',{type:'checkbox',checked:!!val});cb.onchange=()=>act(()=>set(cb.checked?inp.value:null));kids.push(h('label',{className:'check'},cb,'actif'))}
  return h('div',{className:'row'},...kids)}
function seg(options,val,set){const d=h('div',{className:'seg'});options.forEach(([v,lab])=>d.appendChild(h('button',{'aria-pressed':String(v===val),on:{click:()=>act(()=>set(v))}},lab)));return d}
function check(label,val,set){const cb=h('input',{type:'checkbox',checked:!!val});cb.onchange=()=>act(()=>set(cb.checked));return h('label',{className:'check'},cb,label)}
function panneaux(){majUndo();propsPane();planchePane();calquesPane();ctxBar();themePane();placeOverlays()}
function propsPane(){const P=$('props');P.innerHTML='';const els=selection();
  if(!els.length){P.appendChild(h('div',{className:'howto'},h('p',{html:'<b>Rien n\'est sélectionné.</b> Clique un objet de la planche, ou pose-en un avec les outils de gauche. Les réglages de la planche (format, fond, thème) sont dans l\'onglet <b>Planche</b>.'})));
    P.appendChild(h('div',{className:'howto'},h('p',{html:'Raccourcis utiles : <kbd>Ctrl+D</kbd> dupliquer · <kbd>Maj+H</kbd> miroir · <kbd>Ctrl+]</kbd> devant · <kbd>Entrée</kbd> sur une main : modifier la pose · <kbd>?</kbd> tous les raccourcis.'})));return}
  const e=els[0],multi=els.length>1;
  P.appendChild(h('div',{className:'label'},multi?els.length+' objets':NOMS[e.type]+' — '+e.nom));
  if(!multi){const inp=h('input',{value:e.nom,maxLength:60});inp.onchange=()=>act(()=>{e.nom=inp.value});P.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Nom'),inp))}
  const B=h('div',{className:'block'},h('h3',{},'Position et taille'));
  if(!multi){B.appendChild(champNum('x',()=>Math.round(e.x),(x,v)=>x.x=v,-9999,9999));B.appendChild(champNum('y',()=>Math.round(e.y),(x,v)=>x.y=v,-9999,9999));
    B.appendChild(champNum('largeur',()=>Math.round(e.w),(x,v)=>{const r=x.h/x.w;x.w=v;if(x.type==='main'||x.type==='image'||x.type==='personnage')x.h=v*r;if(x.type==='texte')ajusteTexte(x)},MIN_T,20000));
    B.appendChild(champNum('hauteur',()=>Math.round(e.h),(x,v)=>{const r=x.w/x.h;x.h=v;if(x.type==='main'||x.type==='image'||x.type==='personnage')x.w=v*r},MIN_T,20000));
    B.appendChild(champNum('rotation °',()=>Math.round(e.rot),(x,v)=>x.rot=v,-180,180))}
  B.appendChild(h('div',{className:'actions'},h('button',{className:'btn small',on:{click:()=>act(()=>els.forEach(x=>x.rot=((x.rot-90+180)%360+360)%360-180))}},'−90°'),h('button',{className:'btn small',on:{click:()=>act(()=>els.forEach(x=>x.rot=((x.rot+90+180)%360+360)%360-180))}},'+90°'),
    h('button',{className:'btn small',title:'Miroir horizontal (Maj+H)',on:{click:()=>miroir('H')}},'Miroir ⇄'),h('button',{className:'btn small',title:'Miroir vertical (Maj+V)',on:{click:()=>miroir('V')}},'Miroir ⇅')));
  B.appendChild(champRange('opacité',Math.round(e.opacite*100),0,100,1,v=>els.forEach(x=>x.opacite=v/100),v=>v+' %'));
  B.appendChild(h('div',{className:'actions'},check('verrouillé',els.every(x=>x.verrou),v=>els.forEach(x=>x.verrou=v)),check('visible',els.every(x=>x.visible),v=>els.forEach(x=>x.visible=v))));
  P.appendChild(B);
  const A=h('div',{className:'block'},h('h3',{},'Aligner'+(multi?' entre eux':' sur la planche')),h('div',{className:'actions'},
    ...[['gauche','⇤'],['centre','↔'],['droite','⇥'],['haut','⤒'],['milieu','↕'],['bas','⤓']].map(([m,l])=>h('button',{className:'btn small',title:m,on:{click:()=>aligne(m)}},l)),
    els.length>2?h('button',{className:'btn small',on:{click:()=>repartit('h')}},'Répartir ↔'):null,els.length>2?h('button',{className:'btn small',on:{click:()=>repartit('v')}},'Répartir ↕'):null));
  P.appendChild(A);
  if(!multi&&PROPS[e.type])PROPS[e.type](P,e);
  P.appendChild(h('div',{className:'actions'},h('button',{className:'btn small',on:{click:duplique}},'Dupliquer'),h('button',{className:'btn small',on:{click:()=>ordre(1)}},'Avancer'),h('button',{className:'btn small',on:{click:()=>ordre(-1)}},'Reculer'),
    multi?h('button',{className:'btn small',on:{click:groupe}},'Grouper'):null,els.some(x=>x.groupes&&x.groupes.length)?h('button',{className:'btn small',on:{click:degroupe}},'Dégrouper'):null,h('button',{className:'btn small danger',on:{click:supprime}},'Supprimer')))}
const PROPS={
  main(P,e){const A=AH(),B=h('div',{className:'block'},h('h3',{},'Main'));
    B.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Côté'),seg([['D','Droite'],['G','Gauche']],e.cote,v=>{if(v!==e.cote){S.sel=[e.id];convertitCote()}})));
    B.appendChild(h('p',{className:'note'},'« Gauche » est le miroir 3D de la droite (même lumière) ; le bouton Miroir ⇄ ne fait qu\'un miroir d\'image.'));
    B.appendChild(h('div',{className:'actions'},h('button',{className:'btn primary',on:{click:()=>marionnette(e.id)}},'Modifier la pose…'),h('button',{className:'btn',on:{click:copiePose}},'Copier la pose'),h('button',{className:'btn',disabled:!posePP,on:{click:collePose}},'Coller la pose')));
    if(A&&A.presets){const pr=h('div',{className:'presets'});Object.keys(A.presets).forEach(n=>pr.appendChild(h('button',{on:{click:()=>act(()=>{e.pose=clone(A.presets[n]);ajusteProportionMain(e)})}},n)));
      B.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Configuration de départ'),pr))}
    // orientation : 4 vues (quaternions autour de Y / X) + libre par curseurs
    const Q={face:[0,0,0,1],dos:[0,1,0,0],profil:[0,Math.SQRT1_2,0,Math.SQRT1_2],dessus:[Math.SQRT1_2,0,0,Math.SQRT1_2]};
    B.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Orientation'),h('div',{className:'actions'},...Object.keys(Q).map(k=>h('button',{className:'btn small',on:{click:()=>act(()=>{e.orientation=Q[k].slice();ajusteProportionMain(e)})}},k)))));
    const eul=quatVersEuler(e.orientation);['x','y','z'].forEach((ax,i)=>B.appendChild(champRange('tourner '+ax,Math.round(eul[i]),-180,180,1,v=>{eul[i]=v;e.orientation=eulerVersQuat(eul);ajusteProportionMain(e)},v=>v+'°')));
    B.appendChild(champCouleur('peau',e.style.peau,v=>e.style.peau=v));B.appendChild(champCouleur('ongles',e.style.ongle,v=>e.style.ongle=v));B.appendChild(champCouleur('trait',e.style.trait,v=>e.style.trait=v));
    B.appendChild(champRange('trait %',e.style.largeurTrait,0,4,.1,v=>e.style.largeurTrait=v));B.appendChild(check('ombre franche',e.style.ombre,v=>e.style.ombre=v));
    const n=h('input',{type:'number',min:2,max:6,value:e.mouvement&&e.mouvement.cles?e.mouvement.cles.length:3,style:'width:60px'});
    B.appendChild(h('div',{className:'actions'},h('button',{className:'btn',on:{click:()=>eclate(+n.value)}},'Éclater en étapes'),n,h('span',{className:'note'},e.mouvement?'(étapes du mouvement importé)':'copies à poser')));
    P.appendChild(B)},
  texte(P,e){const B=h('div',{className:'block'},h('h3',{},'Texte'));
    const ta=h('textarea',{value:e.texte});ta.onchange=()=>act(()=>{e.texte=ta.value;e.surlignages=e.surlignages.filter(s=>s.to<=ta.value.length);ajusteTexte(e)});B.appendChild(h('div',{className:'field'},ta));
    const sel=h('select',{},...POLICES.map(p=>h('option',{value:p,selected:p===e.police},p)));sel.onchange=()=>act(()=>{e.police=sel.value;ajusteTexte(e)});
    B.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Police'),sel,h('p',{className:'note'},POLICES.indexOf(e.police)>1?'Police système : l\'export utilise celle de la machine qui exporte.':'Police embarquée (OFL).')));
    B.appendChild(champRange('corps',e.corps,8,400,1,v=>{e.corps=v;ajusteTexte(e)}));
    B.appendChild(h('div',{className:'actions'},check('gras',e.gras,v=>{e.gras=v;ajusteTexte(e)})));
    B.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Alignement'),seg([['gauche','Gauche'],['centre','Centre'],['droite','Droite']],e.align,v=>e.align=v)));
    B.appendChild(champCouleur('couleur',e.couleur,v=>e.couleur=v));B.appendChild(champCouleur('fond (bannière)',e.fond,v=>{e.fond=v;ajusteTexte(e)},true));
    B.appendChild(champCouleur('contour',e.contour,v=>e.contour=v,true));B.appendChild(champRange('interligne',e.interligne,1,2,.05,v=>{e.interligne=v;ajusteTexte(e)}));
    B.appendChild(champRange('marge',e.marge,0,80,1,v=>{e.marge=v;ajusteTexte(e)}));B.appendChild(champRange('arrondi',e.rayon,0,100,1,v=>e.rayon=v));
    B.appendChild(champCouleur('surligneur',e.surligneur,v=>e.surligneur=v));
    B.appendChild(h('div',{className:'actions'},h('button',{className:'btn',on:{click:()=>editeTexte(e.id)}},'Modifier le texte…'),h('button',{className:'btn',on:{click:()=>act(()=>{e.surlignages=[{from:0,to:e.texte.length,couleur:e.surligneur}]})}},'Tout surligner'),h('button',{className:'btn',on:{click:()=>act(()=>{e.surlignages=[]})}},'Enlever')));
    P.appendChild(B)},
  image(P,e){const B=h('div',{className:'block'},h('h3',{},'Image'));B.appendChild(champRange('arrondi',e.rayon,0,300,1,v=>e.rayon=v));
    B.appendChild(h('div',{className:'actions'},h('button',{className:'btn',on:{click:definirFond}},'Définir comme fond')));P.appendChild(B)},
  personnage(P,e){const B=h('div',{className:'block'},h('h3',{},'Référent'));
    B.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Expression'),seg([['neutre','Neutre'],['sourire','Sourire'],['sourcils_leves','Sourcils levés'],['sourcils_fronces','Froncés']],e.expression,v=>e.expression=v)));
    B.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Vue'),seg([['face','Face'],['dos','Dos']],e.vue,v=>e.vue=v)));
    B.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Style'),seg([['A','A (cape)'],['B','B (simple)']],e.style,v=>e.style=v)));
    ['peau','vetement','cape','trait'].forEach(k=>B.appendChild(champCouleur(k,e.couleurs[k],v=>e.couleurs[k]=v)));
    B.appendChild(h('p',{className:'note'},window.AtelierPersonnage?'Dessiné par le personnage M4.':'Bouchon simple : le personnage M4 le remplacera.'));P.appendChild(B)},
  fleche(P,e){const B=h('div',{className:'block'},h('h3',{},'Flèche'));
    B.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Tracé'),seg([['droite','Droite'],['courbe','Courbe'],['demi','Demi-cercle'],['vague','Vague'],['zigzag','Zigzag'],['boucle','Boucle']],e.style,v=>e.style=v)));
    B.appendChild(h('div',{className:'actions'},check('aller-retour (deux pointes)',e.double,v=>e.double=v),h('button',{className:'btn small',on:{click:()=>act(()=>e.sens=e.sens<0?1:-1)}},'Inverser la courbure')));
    B.appendChild(champCouleur('couleur',e.couleur,v=>e.couleur=v));B.appendChild(champRange('épaisseur',e.epaisseur,0,40,1,v=>e.epaisseur=v,v=>v?v:'auto'));P.appendChild(B)},
};
function quatVersEuler(q){const[x,y,z,w]=q||[0,0,0,1];const r=Math.atan2(2*(w*x+y*z),1-2*(x*x+y*y)),p=Math.asin(clamp(2*(w*y-z*x),-1,1)),yw=Math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));return[r/D2R,p/D2R,yw/D2R]}
function eulerVersQuat(e){const[r,p,y]=e.map(a=>a*D2R/2),cr=Math.cos(r),sr=Math.sin(r),cp=Math.cos(p),sp=Math.sin(p),cy=Math.cos(y),sy=Math.sin(y);
  return[sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy,cr*cp*cy+sr*sp*sy].map(v=>+v.toFixed(5))}
function planchePane(){const P=$('planchePane');P.innerHTML='';const pl=S.doc.planche,F=pl.fond;
  const fmt=h('select',{},...Object.keys(FORMATS).map(k=>h('option',{value:k,selected:k===pl.format},FORMATS[k][2]+' — '+FORMATS[k][0]+' × '+FORMATS[k][1])));
  fmt.onchange=()=>act(()=>{pl.format=fmt.value;if(fmt.value!=='libre'){pl.w=FORMATS[fmt.value][0];pl.h=FORMATS[fmt.value][1]}});
  const B=h('div',{className:'block'},h('h3',{},'Format'),h('div',{className:'field'},fmt));
  const wi=h('input',{type:'number',value:pl.w,min:100,max:16384}),hi=h('input',{type:'number',value:pl.h,min:100,max:16384});
  wi.onchange=()=>act(()=>{pl.format='libre';pl.w=clamp(+wi.value||pl.w,100,16384)});hi.onchange=()=>act(()=>{pl.format='libre';pl.h=clamp(+hi.value||pl.h,100,16384)});
  B.appendChild(h('div',{className:'row'},h('label',{},'largeur'),wi,h('span',{},'px')));B.appendChild(h('div',{className:'row'},h('label',{},'hauteur'),hi,h('span',{},'px')));P.appendChild(B);
  const Fb=h('div',{className:'block'},h('h3',{},'Fond'));
  Fb.appendChild(seg([['transparent','Transp.'],['uni','Uni'],['degrade','Dégradé'],['image','Image']],F.type,v=>{F.type=v;if(v==='image'&&!F.src){const im=S.doc.elements.find(e=>e.type==='image');if(im)F.src=im.asset}}));
  if(F.type!=='transparent'){Fb.appendChild(champCouleur('couleur',F.col,v=>F.col=v))}
  if(F.type==='degrade'){Fb.appendChild(champCouleur('couleur 2',F.col2,v=>F.col2=v));Fb.appendChild(champRange('angle',F.angle,0,360,5,v=>F.angle=v,v=>v+'°'))}
  if(F.type==='image'){Fb.appendChild(h('div',{className:'actions'},h('button',{className:'btn',on:{click:()=>{S.fondCible=true;$('fichierImage').click()}}},'Choisir une image…'),F.src?h('button',{className:'btn',on:{click:detacherFond}},'Détacher en image'):null));
    Fb.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Ajustement'),seg([['couvrir','Couvrir'],['contenir','Contenir'],['etirer','Étirer'],['mosaique','Mosaïque']],F.mode,v=>F.mode=v)));
    Fb.appendChild(champRange('position x',Math.round(F.ax*100),0,100,5,v=>F.ax=v/100,v=>v+' %'));Fb.appendChild(champRange('position y',Math.round(F.ay*100),0,100,5,v=>F.ay=v/100,v=>v+' %'));
    if(F.mode==='mosaique')Fb.appendChild(champRange('échelle',F.echelle||1,.1,3,.1,v=>F.echelle=v));
    Fb.appendChild(champRange('opacité',Math.round(F.opacite*100),0,100,5,v=>F.opacite=v/100,v=>v+' %'));
    Fb.appendChild(champRange('flou',F.flou,0,40,1,v=>F.flou=v,v=>v+' px'));
    Fb.appendChild(champCouleur('voile',F.voile.col,v=>F.voile.col=v));Fb.appendChild(champRange('voile %',Math.round(F.voile.a*100),0,80,5,v=>F.voile.a=v/100,v=>v+' %'))}
  P.appendChild(Fb)}
function themePane(){const T=$('theme');T.innerHTML='';const th=S.doc.theme;
  T.appendChild(champCouleur('couleur',th.couleur,v=>{th.couleur=v;appliqueTheme()}));
  const sel=h('select',{},...POLICES.map(p=>h('option',{value:p,selected:p===th.police},p)));sel.onchange=()=>act(()=>{th.police=sel.value;appliqueTheme()});T.appendChild(h('div',{className:'field'},h('span',{className:'label'},'Police'),sel));
  T.appendChild(champRange('corps',th.corps,12,160,1,v=>{th.corps=v;appliqueTheme()}))}
// le thème s'applique à TOUS les objets issus d'un gabarit (descripteur e.theme : corps relatif, fond/couleur « accent »)
function mixe(hex,blanc){const n=parseInt(hex.slice(1),16),r=(n>>16)&255,g=(n>>8)&255,b=n&255;const f=c=>Math.round(c+(255-c)*blanc).toString(16).padStart(2,'0');return'#'+f(r)+f(g)+f(b)}
function appliqueTheme(){const th=S.doc.theme;S.doc.elements.forEach(e=>{const d=e.theme;if(!d)return;
  if(e.type==='texte'){e.police=th.police;if(d.corps)e.corps=Math.round(th.corps*d.corps);if(d.fond==='accent')e.fond=mixe(th.couleur,.8);if(d.fond==='accentPlein')e.fond=th.couleur;if(d.couleur==='accent')e.couleur=th.couleur;ajusteTexte(e)}
  if(e.type==='fleche'&&d.couleur==='accent')e.couleur=th.couleur})}
function calquesPane(){const C=$('calques');C.innerHTML='';const L=S.doc.elements;if(!L.length){C.appendChild(h('div',{className:'empty'},'Aucun objet sur la planche.'));return}
  L.slice().reverse().forEach(e=>{const row=h('div',{className:'calque'+(S.sel.indexOf(e.id)>=0?' on':'')+(e.visible?'':' off'),draggable:true});
    row.appendChild(h('button',{className:'ic',title:'visible','aria-pressed':String(e.visible),on:{click:ev=>{ev.stopPropagation();act(()=>e.visible=!e.visible)}}},e.visible?'👁':'◌'));
    row.appendChild(h('button',{className:'ic',title:'verrouillé','aria-pressed':String(e.verrou),on:{click:ev=>{ev.stopPropagation();act(()=>e.verrou=!e.verrou)}}},e.verrou?'🔒':'🔓'));
    const b=h('b',{},e.nom||NOMS[e.type]);b.appendChild(h('small',{},NOMS[e.type]+(e.groupes&&e.groupes.length?' · groupe':'')));row.appendChild(b);
    row.appendChild(h('button',{className:'ic',title:'supprimer',on:{click:ev=>{ev.stopPropagation();S.sel=[e.id];act(()=>{S.doc.elements=S.doc.elements.filter(x=>x.id!==e.id)});selectionne([])}}},'✕'));
    row.onclick=ev=>selectionne([e.id],ev.shiftKey);
    row.ondblclick=()=>{const n=prompt('Nom du calque',e.nom);if(n!==null)act(()=>e.nom=n.slice(0,60))};
    row.ondragstart=ev=>{ev.dataTransfer.setData('text/plain',e.id);ev.dataTransfer.effectAllowed='move'};
    row.ondragover=ev=>{ev.preventDefault();row.classList.add('drag-over')};row.ondragleave=()=>row.classList.remove('drag-over');
    row.ondrop=ev=>{ev.preventDefault();row.classList.remove('drag-over');const id=ev.dataTransfer.getData('text/plain');if(!id||id===e.id)return;
      act(()=>{const m=parId(id);if(!m)return;const L2=S.doc.elements.filter(x=>x.id!==id);const i=L2.indexOf(e);L2.splice(i+1,0,m);S.doc.elements=L2})};
    C.appendChild(row)})}
function ctxBar(){const b=$('ctx');b.innerHTML='';const els=selection();
  if(S.mode==='texte'){const e=parId(S.editId);if(!e)return;
    b.append(h('button',{className:'btn',title:'Gras',on:{mousedown:ev=>ev.preventDefault(),click:()=>{e.gras=!e.gras;ajusteTexte(e);invalide();placeOverlays()}}},'G'),
      h('button',{className:'btn',on:{mousedown:ev=>ev.preventDefault(),click:()=>{e.corps=Math.max(8,e.corps-4);ajusteTexte(e);invalide();placeOverlays()}}},'A−'),h('button',{className:'btn',on:{mousedown:ev=>ev.preventDefault(),click:()=>{e.corps=Math.min(400,e.corps+4);ajusteTexte(e);invalide();placeOverlays()}}},'A+'),
      h('button',{className:'btn',title:'Surligner la sélection',on:{mousedown:ev=>ev.preventDefault(),click:()=>surligne(e.surligneur)}},'Surligner'),h('button',{className:'btn',on:{mousedown:ev=>ev.preventDefault(),click:()=>surligne(null)}},'Ôter'),
      ...[['gauche','⇤'],['centre','↔'],['droite','⇥']].map(([m,l])=>h('button',{className:'btn',on:{mousedown:ev=>ev.preventDefault(),click:()=>{e.align=m;invalide();placeOverlays()}}},l)),
      h('button',{className:'btn primary',on:{mousedown:ev=>ev.preventDefault(),click:()=>{quitteModes();invalide()}}},'Terminer'));return}
  if(S.mode==='marionnette'){b.append(h('button',{className:'btn primary',on:{click:()=>{quitteModes();invalide()}}},'Terminer la pose'));return}
  if(!els.length)return;const e=els[0],multi=els.length>1;
  if(!multi&&e.type==='main')b.append(h('button',{className:'btn primary',on:{click:()=>marionnette(e.id)}},'Modifier la pose…'),h('button',{className:'btn',on:{click:convertitCote}},'→ main '+(e.cote==='D'?'gauche':'droite')),h('button',{className:'btn',disabled:!posePP,on:{click:collePose}},'Coller la pose'));
  if(!multi&&e.type==='texte')b.append(h('button',{className:'btn',on:{click:()=>editeTexte(e.id)}},'Modifier le texte'),h('button',{className:'btn',on:{click:()=>act(()=>{e.gras=!e.gras;ajusteTexte(e)})}},'G'));
  if(!multi&&e.type==='image')b.append(h('button',{className:'btn',on:{click:definirFond}},'Définir comme fond'));
  if(multi)b.append(h('button',{className:'btn',on:{click:groupe}},'Grouper'),h('button',{className:'btn',on:{click:()=>aligne('centre')}},'Centrer ↔'),h('button',{className:'btn',on:{click:()=>aligne('milieu')}},'Centrer ↕'));
  b.append(h('button',{className:'btn',on:{click:()=>miroir('H')}},'Miroir ⇄'),h('button',{className:'btn',on:{click:duplique}},'Dupliquer'),h('button',{className:'btn',on:{click:()=>ordre(1)}},'Devant'),h('button',{className:'btn',on:{click:()=>ordre(-1)}},'Derrière'),
    h('button',{className:'btn',title:'Verrouiller (Alt+Maj+L)',on:{click:verrou}},els.every(x=>x.verrou)?'🔒':'🔓'),h('button',{className:'btn danger',on:{click:supprime}},'Suppr.'))}

/* ======================================================================
   Gabarits : un jeu d'objets modifiables sur une planche d'un format donné (marges 4 %, outil.md § 6.2)
   ====================================================================== */
function texteGab(p){const e=nouvelElement('texte',p);ajusteTexte(e);return e}
function mainGab(cote,x,y,h,pose){const e=nouvelElement('main',{cote});const b=mainBoite(e);e.h=h;e.w=h*b.w/b.h;e.x=x-e.w/2;e.y=y;if(pose&&AH().presets[pose])e.pose=clone(AH().presets[pose]);return e}
const GABARITS={
  A:{nom:'A · Bannière + définitions',format:'16:9',desc:'bannière du mot en haut, colonne de définitions à gauche, signe à droite',
    cree(d){const W=d.planche.w,H=d.planche.h,m=W*.04,th=d.theme,L=[];
      L.push(texteGab({texte:'MOT',x:m,y:m,w:W-2*m,h:H*.14,corps:th.corps*1.5,gras:true,align:'centre',fond:mixe(th.couleur,.8),rayon:16,theme:{corps:1.5,fond:'accent'},nom:'Bannière'}));
      L.push(texteGab({texte:'Définition\nÉcris ici la définition, un exemple, les synonymes…',x:m,y:H*.14+2*m,w:W*.42,h:H-H*.14-3*m,corps:th.corps*.6,fond:'#ffffffe6',rayon:12,interligne:1.3,theme:{corps:.6},nom:'Définitions'}));
      const cx=m+W*.42+(W-2*m-W*.42)/2,y0=H*.14+2*m,hz=H-y0-m;
      const p=nouvelElement('personnage');p.h=hz;p.w=hz*PERS_HL.w/PERS_HL.h;p.x=cx-p.w/2;p.y=y0;L.push(p);
      L.push(mainGab('D',cx-hz*.16,y0+hz*.42,hz*.38));L.push(mainGab('G',cx+hz*.16,y0+hz*.42,hz*.38));return L}},
  B:{nom:'B · Carte mot / signe',format:'carre',desc:'signe en haut (68 %), bannière du mot en bas',
    cree(d){const W=d.planche.w,H=d.planche.h,m=W*.04,th=d.theme;
      return[mainGab('D',W/2,m+H*.06,H*.56),texteGab({texte:'MOT',x:m,y:H*.72,w:W-2*m,h:H*.24,corps:th.corps*1.6,gras:true,align:'centre',fond:mixe(th.couleur,.8),rayon:20,theme:{corps:1.6,fond:'accent'},nom:'Bannière'})]}},
  C:{nom:'C · Fiche de vocabulaire',format:'A4',desc:'bandeau mot + catégorie, signe à gauche, définition à droite, image et légende en bas',
    cree(d){const W=d.planche.w,H=d.planche.h,m=W*.04,th=d.theme,c=th.corps*(W/1920)*1.6;const L=[];
      L.push(texteGab({texte:'MOT',x:m,y:m,w:W*.62,h:H*.09,corps:c*1.8,gras:true,align:'gauche',fond:mixe(th.couleur,.8),rayon:16,theme:{corps:1.8*(W/1920)*1.6,fond:'accent'},nom:'Bannière'}));
      L.push(texteGab({texte:'catégorie',x:m+W*.64,y:m,w:W-2*m-W*.64,h:H*.09,corps:c,align:'centre',fond:'#eeeeee',rayon:16,theme:{corps:1*(W/1920)*1.6},nom:'Catégorie'}));
      const y0=m+H*.09+m;L.push(mainGab('D',m+W*.23,y0+H*.02,H*.3));
      L.push(texteGab({texte:'Définition\n…\n\nExemple\n…\n\nSynonymes\n…',x:m+W*.5,y:y0,w:W*.5-m,h:H*.34,corps:c*.9,interligne:1.35,theme:{corps:.9*(W/1920)*1.6},nom:'Définition'}));
      L.push(texteGab({texte:'Image et légende (glisse une photo ici)',x:m,y:H*.6,w:W-2*m,h:H*.36,corps:c*.8,align:'centre',fond:'#f3f6f5',rayon:16,theme:{corps:.8*(W/1920)*1.6},nom:'Légende'}));return L}},
  D:{nom:'D · Planche 4 étapes',format:'16:9',desc:'bandeau mot, 4 cases numérotées avec une main et une flèche entre elles',
    cree(d){const W=d.planche.w,H=d.planche.h,m=W*.04,th=d.theme,L=[];
      L.push(texteGab({texte:'MOT',x:m,y:m,w:W-2*m,h:H*.14,corps:th.corps*1.5,gras:true,align:'centre',fond:mixe(th.couleur,.8),rayon:16,theme:{corps:1.5,fond:'accent'},nom:'Bannière'}));
      const y0=H*.14+2*m,hc=H-y0-m,gap=m*.6,wc=(W-2*m-3*gap)/4;
      for(let i=0;i<4;i++){const x=m+i*(wc+gap);const g='g'+uid();
        const case_=texteGab({texte:String(i+1),x,y:y0,w:wc,h:hc,corps:th.corps*.8,gras:true,align:'gauche',fond:'#ffffffe6',rayon:14,theme:{corps:.8},nom:'Étape '+(i+1),couleur:th.couleur});case_.groupes=[g];
        const mn=mainGab('D',x+wc/2,y0+hc*.2,hc*.7);mn.nom='Main étape '+(i+1);mn.groupes=[g];L.push(case_,mn);
        if(i<3){const f=nouvelElement('fleche',{couleur:th.couleur,theme:{couleur:'accent'},nom:'Flèche '+(i+1)});f.x=x+wc-gap*.1;f.y=y0+hc*.5;f.w=gap*1.2;f.h=hc*.08;L.push(f)}}
      return L}},
  E:{nom:'E · Bilingue',format:'16:9',desc:'mot et définition en français à gauche, signe à droite, place pour une image « sens »',
    cree(d){const W=d.planche.w,H=d.planche.h,m=W*.04,th=d.theme,L=[];
      L.push(texteGab({texte:'MOT',x:m,y:m,w:W*.46,h:H*.14,corps:th.corps*1.5,gras:true,align:'gauche',fond:mixe(th.couleur,.8),rayon:16,theme:{corps:1.5,fond:'accent'},nom:'Mot'}));
      L.push(texteGab({texte:'Définition en français…',x:m,y:H*.14+2*m,w:W*.46,h:H*.36,corps:th.corps*.65,interligne:1.3,theme:{corps:.65},nom:'Définition'}));
      L.push(texteGab({texte:'Image « sens »',x:m,y:H*.58,w:W*.46,h:H-H*.58-m,corps:th.corps*.6,align:'centre',fond:'#f3f6f5',rayon:14,theme:{corps:.6},nom:'Sens'}));
      L.push(texteGab({texte:'SIGNE',x:W*.54,y:m,w:W-W*.54-m,h:H*.14,corps:th.corps*1.5,gras:true,align:'centre',fond:mixe(th.couleur,.8),rayon:16,theme:{corps:1.5,fond:'accent'},nom:'Signe'}));
      L.push(mainGab('D',W*.77,H*.14+2*m,H*.6));return L}},
};
function gabarit(k){const G=GABARITS[k];if(!G)return;quitteModes();act(()=>{const th=clone(S.doc.theme),assets=S.doc.assets;const d=docNeuf(G.format);d.theme=th;d.assets=assets;d.nom=S.doc.nom;S.doc=d;S.doc.elements=G.cree(d);S.gabaritNom=k});
  selectionne([]);ajuste();message('Gabarit '+k+' posé : chaque objet reste modifiable.')}
function gabaritsPane(){const G=$('gabarits');G.innerHTML='';for(const k in GABARITS){const g=GABARITS[k],[w,hh]=FORMATS[g.format];
    const svg='<svg viewBox="0 0 '+w+' '+hh+'" width="100" height="'+(100*hh/w)+'"><rect width="'+w+'" height="'+hh+'" fill="#fff" stroke="#bbb" stroke-width="'+(w/100)+'"/>'+
      (k==='A'?'<rect x="4%" y="4%" width="92%" height="14%" fill="#cceeec"/><rect x="4%" y="24%" width="42%" height="72%" fill="#eef2f1"/><ellipse cx="73%" cy="60%" rx="12%" ry="30%" fill="#00a19a"/>':
       k==='B'?'<ellipse cx="50%" cy="36%" rx="22%" ry="30%" fill="#00a19a"/><rect x="4%" y="72%" width="92%" height="24%" fill="#cceeec"/>':
       k==='C'?'<rect x="4%" y="4%" width="62%" height="9%" fill="#cceeec"/><ellipse cx="27%" cy="30%" rx="14%" ry="15%" fill="#00a19a"/><rect x="54%" y="18%" width="42%" height="34%" fill="#eef2f1"/><rect x="4%" y="60%" width="92%" height="36%" fill="#f3f6f5"/>':
       k==='D'?'<rect x="4%" y="4%" width="92%" height="14%" fill="#cceeec"/>'+[0,1,2,3].map(i=>'<rect x="'+(4+i*23.5)+'%" y="24%" width="21%" height="72%" fill="#eef2f1"/><ellipse cx="'+(14.5+i*23.5)+'%" cy="62%" rx="7%" ry="25%" fill="#00a19a"/>').join(''):
       '<rect x="4%" y="4%" width="46%" height="14%" fill="#cceeec"/><rect x="4%" y="26%" width="46%" height="30%" fill="#eef2f1"/><rect x="4%" y="58%" width="46%" height="38%" fill="#f3f6f5"/><rect x="54%" y="4%" width="42%" height="14%" fill="#cceeec"/><ellipse cx="77%" cy="60%" rx="14%" ry="30%" fill="#00a19a"/>')+'</svg>';
    G.appendChild(h('button',{title:g.desc,on:{click:()=>gabarit(k)}},h('div',{html:svg}),h('b',{},g.nom),h('small',{},FORMATS[g.format][2])))}}

/* ======================================================================
   Export PNG / WebP : drawDoc à l'échelle k, sonde de plafond, projet embarqué dans un chunk iTXt
   ====================================================================== */
let downloads=null;(async()=>{try{if(window.claude&&window.claude.use)downloads=await window.claude.use('downloads')}catch(e){}})();
let expK=1;
function nomFichier(){const ban=S.doc.elements.find(e=>e.type==='texte'&&e.theme&&(e.theme.fond==='accent'))||S.doc.elements.find(e=>e.type==='texte'&&e.fond);
  const brut=(ban&&ban.texte.split('\n')[0].trim())||S.doc.nom||'planche';return brut.replace(/[^\w\-àâäéèêëîïôöùûüç ]/gi,'').replace(/\s+/g,'-').slice(0,60)||'planche'}
function ouvreExport(){quitteModes();const d=$('dlgExport');$('expNom').value=nomFichier();majExport();if(!d.open)d.showModal()}
function majExport(){const P=S.doc.planche;$('expTaille').textContent=Math.round(P.w*expK)+' × '+Math.round(P.h*expK)+' px'+(P.w*expK*P.h*expK>16777216?' — au-dessus de la limite d\'iOS Safari (16,8 Mpx)':'');
  $('expEchelle').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.k===expK)))}
$('expEchelle').querySelectorAll('button').forEach(b=>b.onclick=()=>{expK=+b.dataset.k;majExport()});
$('expFermer').onclick=()=>$('dlgExport').close();$('imgFermer').onclick=()=>{$('dlgImg').close();if(lastURL){URL.revokeObjectURL(lastURL);lastURL=null}};
$('aideFermer').onclick=()=>$('dlgAide').close();
let lastURL=null,exporting=false;
// sonde : un canvas de cette taille peint-il vraiment ? (Chrome : aire ≤ 268 435 456 ; iOS ≈ 16,8 Mpx)
function sonde(W,H){try{const c=document.createElement('canvas');c.width=W;c.height=H;const x=c.getContext('2d');x.fillStyle='#fff';x.fillRect(W-1,H-1,1,1);return x.getImageData(W-1,H-1,1,1).data[3]===255}catch(e){return false}}
async function exporte(o){o=o||{};let k=o.k||expK;const P=S.doc.planche;const prog=$('expProg').firstElementChild,m=$('expMsg');m.className='msg';
  let W=Math.round(P.w*k),H=Math.round(P.h*k);
  while(!sonde(W,H)&&k>1){k=Math.max(1,k-1);W=Math.round(P.w*k);H=Math.round(P.h*k);m.textContent='Ce navigateur ne peut pas produire '+Math.round(P.w*(k+1))+' × '+Math.round(P.h*(k+1))+' ; export à ×'+k}
  if(!sonde(W,H))throw new Error('planche trop grande pour ce navigateur');
  prog.style.width='15%';m.textContent='Rendu…';await FONTS_PRETES;await document.fonts.ready;
  const c=document.createElement('canvas');c.width=W;c.height=H;const ctx=c.getContext('2d',{colorSpace:'srgb'});ctx.imageSmoothingQuality='high';
  drawDoc(ctx,S.doc,k,{export:true,transparent:!!o.transparent});
  prog.style.width='55%';m.textContent='Encodage…';await new Promise(r=>setTimeout(r,10));
  let blob=await new Promise(r=>c.toBlob(r,o.webp?'image/webp':'image/png',.92));if(!blob)throw new Error('encodage impossible');
  if(!o.webp&&o.embarque!==false){blob=await pngAvecProjet(blob)}
  prog.style.width='100%';return{blob,w:W,h:H,k}}
$('expGo').onclick=async()=>{if(exporting)return;exporting=true;$('expGo').disabled=true;const m=$('expMsg');let r=null;
  try{r=await exporte({k:expK,transparent:$('expTransparent').checked,webp:$('expWebp').checked,embarque:$('expProjet').checked})}
  catch(e){m.className='msg err';m.textContent='Export impossible : '+(e&&e.message||'erreur')}
  finally{exporting=false;$('expGo').disabled=false;$('expProg').firstElementChild.style.width='0'}
  if(!r)return;const nom=($('expNom').value.trim().replace(/[^\w\-àâäéèêëîïôöùûüç ]/gi,'').replace(/\s+/g,'-')||nomFichier())+(r.k>1?'@'+r.k+'x':'')+($('expWebp').checked?'.webp':'.png');
  if(downloads){try{await downloads.save({filename:nom,data:r.blob});m.textContent='Image enregistrée ('+r.w+' × '+r.h+').';return}catch(e){if(e&&e.code==='declined'){m.textContent='Export annulé.';return}}}
  if(lastURL)URL.revokeObjectURL(lastURL);lastURL=URL.createObjectURL(r.blob);$('imgOut').src=lastURL;$('imgLien').href=lastURL;$('imgLien').download=nom;$('dlgExport').close();if(!$('dlgImg').open)$('dlgImg').showModal();m.textContent=''};
$('bExporter').onclick=ouvreExport;
/* ---- PNG : chunk iTXt « atelier-mains-lsf » inséré après IHDR (longueur, type, données, CRC-32) ---- */
const CRC=(()=>{const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c>>>0}return t})();
function crc32(b){let c=0xFFFFFFFF;for(let i=0;i<b.length;i++)c=CRC[(c^b[i])&255]^(c>>>8);return(c^0xFFFFFFFF)>>>0}
const CLE_PNG='atelier-mains-lsf';
async function pngAvecProjet(blob){const src=new Uint8Array(await blob.arrayBuffer());const json=new TextEncoder().encode(JSON.stringify(serialise()));
  const kw=new TextEncoder().encode(CLE_PNG);const data=new Uint8Array(kw.length+5+json.length);data.set(kw,0);data[kw.length]=0;data[kw.length+1]=0;data[kw.length+2]=0;data[kw.length+3]=0;data[kw.length+4]=0;data.set(json,kw.length+5);
  const type=new TextEncoder().encode('iTXt');const chunk=new Uint8Array(12+data.length);const dv=new DataView(chunk.buffer);dv.setUint32(0,data.length);chunk.set(type,4);chunk.set(data,8);
  const tc=new Uint8Array(4+data.length);tc.set(type,0);tc.set(data,4);dv.setUint32(8+data.length,crc32(tc));
  const fin=8+4+4+13+4;                                  // signature (8) + chunk IHDR (4+4+13+4)
  const out=new Uint8Array(src.length+chunk.length);out.set(src.subarray(0,fin),0);out.set(chunk,fin);out.set(src.subarray(fin),fin+chunk.length);return new Blob([out],{type:'image/png'})}
function projetDuPng(buf){const b=new Uint8Array(buf);if(b.length<8||b[0]!==137||b[1]!==80)return null;let p=8;const dv=new DataView(buf);
  while(p+8<=b.length){const len=dv.getUint32(p),type=String.fromCharCode(b[p+4],b[p+5],b[p+6],b[p+7]);
    if(type==='iTXt'){const d=b.subarray(p+8,p+8+len);let z=d.indexOf(0);const kw=new TextDecoder().decode(d.subarray(0,z));if(kw===CLE_PNG){let q=z+1+2;q=d.indexOf(0,q)+1;q=d.indexOf(0,q)+1;try{return JSON.parse(new TextDecoder().decode(d.subarray(q)))}catch(e){return null}}}
    if(type==='IEND')break;p+=12+len}return null}

/* ======================================================================
   Projet : sérialisation, validation champ par champ, lecture des JSON v6–v8 de la v1
   ====================================================================== */
function serialise(){const d=clone(Object.assign({},S.doc,{assets:null}));d.assets={};const utiles=new Set();S.doc.elements.forEach(e=>{if(e.type==='image'&&e.asset)utiles.add(e.asset)});if(S.doc.planche.fond.src)utiles.add(S.doc.planche.fond.src);
  utiles.forEach(id=>{if(S.doc.assets[id])d.assets[id]=S.doc.assets[id]});d.nom=$('nom').value.trim();d.modifieLe=S.doc.modifieLe;return d}
const POSE_OK=p=>p&&typeof p==='object';
function valideElement(o,assets){if(!o||typeof o!=='object'||!DEFAUT[o.type])return null;const e=nouvelElement(o.type);
  e.id=vStr(o.id,40,e.id)||e.id;e.x=vNum(o.x,-1e5,1e5,0);e.y=vNum(o.y,-1e5,1e5,0);e.w=vNum(o.w,MIN_T,2e4,100);e.h=vNum(o.h,MIN_T,2e4,100);e.rot=vNum(o.rot,-360,360,0);
  e.flipH=vBool(o.flipH,false);e.flipV=vBool(o.flipV,false);e.opacite=vNum(o.opacite,0,1,1);e.verrou=vBool(o.verrou,false);e.visible=vBool(o.visible,true);e.nom=vStr(o.nom,60,e.nom);
  e.groupes=Array.isArray(o.groupes)?o.groupes.filter(g=>typeof g==='string').slice(0,8):[];if(o.theme&&typeof o.theme==='object')e.theme=o.theme;
  switch(o.type){
    case'main':e.cote=vIn(o.cote,['D','G'],'D');if(!POSE_OK(o.pose))return null;e.pose=clone(o.pose);
      e.orientation=Array.isArray(o.orientation)&&o.orientation.length===4&&o.orientation.every(v=>typeof v==='number'&&isFinite(v))?o.orientation.slice():[0,0,0,1];
      const st=o.style||{};e.style={peau:vHex(st.peau,INJS),ongle:vHex(st.ongle,'#d6f2ee'),trait:vHex(st.trait,'#111111'),largeurTrait:vNum(st.largeurTrait,0,4,1.2),ombre:vBool(st.ombre,true)};
      e.mouvement=o.mouvement&&Array.isArray(o.mouvement.cles)?{cles:o.mouvement.cles.filter(c=>c&&POSE_OK(c.pose)).map(c=>({pose:clone(c.pose),orientation:Array.isArray(c.orientation)?c.orientation.slice(0,4):[0,0,0,1],fl:c.fl&&typeof c.fl==='object'?{style:vIn(c.fl.style,['droite','courbe','demi','vague','zigzag','boucle'],'droite')}:undefined}))}:null;break;
    case'texte':e.texte=vStr(o.texte,5000,'');e.police=vStr(o.police,60,e.police);e.corps=vNum(o.corps,6,400,e.corps);e.gras=vBool(o.gras,false);e.couleur=vHex(o.couleur,'#1e1e1e');
      e.fond=typeof o.fond==='string'&&/^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$/.test(o.fond)?o.fond:null;e.align=vIn(o.align,['gauche','centre','droite'],'gauche');
      e.surlignages=Array.isArray(o.surlignages)?o.surlignages.filter(s=>s&&typeof s.from==='number'&&typeof s.to==='number'&&s.to>s.from).map(s=>({from:clamp(s.from,0,e.texte.length),to:clamp(s.to,0,e.texte.length),couleur:vHex(s.couleur,'#fff176')})):[];
      e.contour=vHex(o.contour,null);e.interligne=vNum(o.interligne,1,2,1.25);e.rayon=vNum(o.rayon,0,300,0);e.marge=vNum(o.marge,0,200,12);e.surligneur=vHex(o.surligneur,'#fff176');break;
    case'image':if(typeof o.asset!=='string'||!assets[o.asset])return null;e.asset=o.asset;e.rayon=vNum(o.rayon,0,1000,0);break;
    case'personnage':e.expression=vIn(o.expression,['neutre','sourire','sourcils_leves','sourcils_fronces'],'neutre');e.vue=vIn(o.vue,['face','dos'],'face');e.style=vIn(o.style,['A','B'],'A');
      const c=o.couleurs||{};e.couleurs={peau:vHex(c.peau,e.couleurs.peau),vetement:vHex(c.vetement,e.couleurs.vetement),cape:vHex(c.cape,e.couleurs.cape),trait:vHex(c.trait,e.couleurs.trait)};break;
    case'fleche':const pt=v=>Array.isArray(v)&&v.length===2&&v.every(x=>typeof x==='number'&&isFinite(x))?[clamp(v[0],-2,3),clamp(v[1],-2,3)]:null;e.de=pt(o.de)||[0,.5];e.a=pt(o.a)||[1,.5];
      e.style=vIn(o.style,['droite','courbe','demi','vague','zigzag','boucle'],'droite');e.double=vBool(o.double,false);e.couleur=vHex(o.couleur,'#1e1e1e');e.epaisseur=vNum(o.epaisseur,0,60,0);e.sens=o.sens<0?-1:1;break}
  return e}
// convertit une configuration v6–v8 de la v1 en projet : les poses sont reprises telles quelles (le moteur M2 les lit)
function poseV1(p){const f=p.f||{};const o={pouce:Object.assign({av:0,rap:0,mcp:0,ip:0},f.pouce||{})};['index','majeur','annulaire','auriculaire'].forEach(k=>o[k]=Object.assign({mcp:0,pip:0,dip:0,ab:0},f[k]||{}));return o}
function convertitV1(o){const d=docNeuf('16:9');const P=d.planche;const mains=o.version<8?[o.gauche?'G':'D']:(o.mains==='DG'?['D','G']:[vIn(o.mains,['D','G'],'D')]);
  const D=o.decor||{},F=D.fond||{},R=D.ref||{};
  if(F.type==='uni'||F.type==='degrade'){P.fond.type=F.type;P.fond.col=vHex(F.col,'#ffffff');P.fond.col2=mixe(P.fond.col,.55)}else P.fond.type='transparent';
  if(R.style&&R.style!=='aucun'){const p=nouvelElement('personnage');p.h=P.h*.92*vNum(R.t,.6,1.7,1);p.w=p.h*PERS_HL.w/PERS_HL.h;p.x=(P.w-p.w)/2+vNum(R.x,-60,60,0)*P.w/200;p.y=P.h*.04+vNum(R.h,-60,60,0)*P.h/200;d.elements.push(p)}
  mains.forEach((c,i)=>{let pose,cles=null;
    if(o.version<8){if(o.mode==='mouvement'&&o.debut&&o.fin){cles=[o.debut,o.fin];pose=o.fin}else pose=o.pose}
    else{const set=o.pose||{};pose=set[c];if(Array.isArray(o.cles)&&o.cles.length>1){cles=o.cles.map(s=>s[c]).filter(Boolean);if(!pose)pose=cles[cles.length-1]}}
    if(!pose||!pose.f)return;const e=nouvelElement('main',{cote:c});e.pose=poseV1(pose);e.orientation=Array.isArray(pose.q)&&pose.q.length===4?pose.q.slice():[0,0,0,1];
    if(cles&&cles.length>1)e.mouvement={cles:cles.map((k,j)=>({pose:poseV1(k),orientation:Array.isArray(k.q)?k.q.slice(0,4):[0,0,0,1],fl:o.cles&&o.cles[j]&&o.cles[j].fl?{style:o.cles[j].fl.style}:(o.fl?{style:o.fl.style}:undefined)}))};
    e.h=P.h*.38;e.w=e.h*mainBoite(e).w/mainBoite(e).h;e.x=P.w/2+(c==='D'?-1:1)*P.w*.14-e.w/2+(i?0:0);e.y=P.h*.42;d.elements.push(e)});
  d.nom=vStr(o.nom,80,'');return d}
function charge(o){if(!o||typeof o!=='object')throw new Error('JSON illisible');const rejets=[];let d;
  if([6,7,8].indexOf(o.version)>=0){d=convertitV1(o)}
  else{if(o.version!==9)throw new Error('version inconnue ('+o.version+')');d=docNeuf('16:9');
    const assets={};if(o.assets&&typeof o.assets==='object')for(const k in o.assets){const v=o.assets[k];if(typeof k==='string'&&typeof v==='string'&&/^data:image\/(png|jpeg|webp|gif|svg\+xml);base64,/.test(v))assets[k]=v}
    const P=o.planche||{};d.planche.format=vIn(P.format,Object.keys(FORMATS),'libre');d.planche.w=vNum(P.w,100,16384,1920);d.planche.h=vNum(P.h,100,16384,1080);
    const F=P.fond||{},f=d.planche.fond;f.type=vIn(F.type,['transparent','uni','degrade','image'],'uni');f.col=vHex(F.col,'#ffffff');f.col2=vHex(F.col2,'#cceeec');f.angle=vNum(F.angle,0,360,180);
    f.src=typeof F.src==='string'&&assets[F.src]?F.src:null;if(f.type==='image'&&!f.src)f.type='uni';f.mode=vIn(F.mode,['couvrir','contenir','etirer','mosaique'],'couvrir');f.ax=vNum(F.ax,0,1,.5);f.ay=vNum(F.ay,0,1,.5);
    f.opacite=vNum(F.opacite,0,1,1);f.flou=vNum(F.flou,0,40,0);f.echelle=vNum(F.echelle,.1,3,1);const V=F.voile||{};f.voile={col:vHex(V.col,'#000000'),a:vNum(V.a,0,.8,0)};
    const T=o.theme||{};d.theme={couleur:vHex(T.couleur,INJS),police:vStr(T.police,60,'Atkinson Hyperlegible'),corps:vNum(T.corps,12,160,48)};
    d.nom=vStr(o.nom,80,'');d.creeLe=vNum(o.creeLe,0,1e14,Date.now());d.assets=assets;
    (Array.isArray(o.elements)?o.elements:[]).forEach((el,i)=>{const e=valideElement(el,assets);if(e)d.elements.push(e);else rejets.push(i)})}
  // tout est validé : on écrit
  quitteModes();S.doc=d;IMG.clear();HC.clear();for(const k in d.assets)chargeAsset(k,d.assets[k]);$('nom').value=d.nom||'';hist.undo.length=0;hist.redo.length=0;hist.pending=null;
  selectionne([]);ajuste();panneaux();
  if(rejets.length)message(rejets.length+' élément(s) invalide(s) écarté(s) : '+rejets.join(', '),true);return d}
async function ouvreFichier(file){try{if(/\.png$/i.test(file.name)||file.type==='image/png'){const o=projetDuPng(await file.arrayBuffer());if(o){charge(o);message('Projet rouvert depuis le PNG.');return}importeImages([file]);return}
    const o=JSON.parse(await file.text());charge(o);message('Projet chargé.')}catch(e){message('Impossible d\'ouvrir : '+(e.message||'format inattendu'),true)}}
$('fichierProjet').onchange=()=>{const f=$('fichierProjet').files[0];if(f)ouvreFichier(f);$('fichierProjet').value=''};
$('bOuvrir').onclick=()=>$('fichierProjet').click();
$('bJsonExport').onclick=async()=>{const d=serialise();const blob=new Blob([JSON.stringify(d)],{type:'application/json'});const nom=(d.nom||nomFichier())+'.atelier.json';
  if(downloads){try{await downloads.save({filename:nom,data:blob});$('projMsg').textContent='Projet enregistré.';return}catch(e){if(e&&e.code==='declined')return}}
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=nom;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),2000);$('projMsg').textContent='Projet téléchargé ('+Math.round(blob.size/1024)+' Ko).'};
$('bNouveau').onclick=()=>{if(S.doc.elements.length&&!confirm('Nouvelle planche ? Le travail en cours reste dans le brouillon.'))return;charge(docNeuf('16:9'))};
$('nom').onchange=()=>{S.doc.nom=$('nom').value.trim();modifie()};

/* ======================================================================
   Brouillon IndexedDB (5 s après un changement) et bibliothèque db (capability claude.ai, collection « projets »)
   ====================================================================== */
function idb(){return new Promise((res,rej)=>{try{const r=indexedDB.open('atelier-v2',1);r.onupgradeneeded=()=>r.result.createObjectStore('projets',{keyPath:'id'});r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)}catch(e){rej(e)}})}
async function brouillonSauve(){try{const db=await idb();const tx=db.transaction('projets','readwrite');tx.objectStore('projets').put({id:'brouillon',json:serialise(),date:Date.now()});await new Promise(r=>tx.oncomplete=r);$('projMsg').textContent='Brouillon enregistré ('+new Date().toLocaleTimeString('fr-FR')+').'}catch(e){}}
async function brouillonLit(){try{const db=await idb();return await new Promise((res,rej)=>{const r=db.transaction('projets').objectStore('projets').get('brouillon');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)})}catch(e){return null}}
$('bBrouillon').onclick=async()=>{const b=await brouillonLit();if(b&&b.json){try{charge(b.json);message('Brouillon repris.')}catch(e){message('Brouillon illisible.',true)}}};
let db=null,items=[];
(async()=>{try{if(!window.claude||!window.claude.use)throw 0;db=await window.claude.use('db');if(!db)throw 0;$('libNote').textContent='Projets partagés avec ceux qui ouvrent cet atelier.';
  db.collection('projets').orderBy('modifieLe','desc').onSnapshot(s=>{items=s.docs;renderLib()},e=>{$('lib').innerHTML='<div class="empty">La bibliothèque ne répond plus ('+esc(e.code||'')+'). Recharge la page.</div>'})}
  catch(e){db=null;$('libNote').textContent='Bibliothèque indisponible hors claude.ai : utilise « Exporter le projet (.json) » et « Ouvrir… ».';$('lib').innerHTML='<div class="empty">Hors claude.ai, le brouillon local et les fichiers .json gardent ton travail.</div>'}})();
function renderLib(){const L=$('lib');if(!items.length){L.innerHTML='<div class="empty">Aucun projet enregistré. Donne un nom à la planche et clique sur « Enregistrer ».</div>';return}
  L.innerHTML=items.map(d=>{const v=d.data(),date=v.modifieLe?new Date(v.modifieLe).toLocaleDateString('fr-FR',{day:'numeric',month:'short'}):'';
    return'<div class="item"><b>'+esc(v.nom||'Sans nom')+'</b><div class="actions"><button class="btn small" data-load="'+d.id+'">Charger</button><button class="btn small danger" data-del="'+d.id+'">Suppr.</button></div><small>'+esc((v.etat&&v.etat.elements?v.etat.elements.length:0)+' objets')+(date?' · '+date:'')+'</small></div>'}).join('');
  L.querySelectorAll('[data-load]').forEach(b=>b.onclick=()=>{const d=items.find(x=>x.id===b.dataset.load);try{charge(d.data().etat);S.dbId=d.id;message('Projet chargé.')}catch(e){message('Impossible de charger : '+e.message,true)}});
  L.querySelectorAll('[data-del]').forEach(b=>b.onclick=async()=>{if(b.dataset.armed!=='1'){b.dataset.armed='1';b.textContent='Confirmer';setTimeout(()=>{b.dataset.armed='';b.textContent='Suppr.'},3000);return}
    b.disabled=true;try{await db.collection('projets').doc(b.dataset.del).delete()}catch(e){b.disabled=false;message('Suppression impossible.',true)}})}
async function enregistreDb(){const nom=$('nom').value.trim();if(!nom){message('Donne un nom au projet (en haut).',true);$('nom').focus();return}
  if(!db){await brouillonSauve();message('Hors claude.ai : brouillon local enregistré ; exporte le .json pour le garder.');return}
  const etat=serialise();let txt=JSON.stringify(etat);if(txt.length>900000){etat.assets={};etat.elements=etat.elements.filter(e=>e.type!=='image');if(etat.planche.fond.type==='image'){etat.planche.fond.type='uni';etat.planche.fond.src=null}message('Images trop lourdes pour la bibliothèque : enregistrées sans elles (garde le .json).',true)}
  try{const col=db.collection('projets');const row={nom,etat,modifieLe:Date.now()};if(S.dbId)await col.doc(S.dbId).set(row);else{const r=await col.add(row);S.dbId=r&&r.id}message('« '+nom+' » enregistré.')}
  catch(e){message(e&&e.code==='invalid_argument'?'Tu n\'as pas les droits d\'écriture sur cette bibliothèque.':'Enregistrement impossible, réessaie.',true)}}
$('bEnregistrer').onclick=enregistreDb;

/* ======================================================================
   Aide, zoom, démarrage
   ====================================================================== */
const RACC=[['V','sélection'],['M / Maj+M','main droite / gauche'],['T','texte'],['I','image'],['A','flèche'],['P','référent'],['G','gabarits'],['Échap','désélectionner / quitter le mode'],['Entrée','modifier la pose / le texte'],
  ['Ctrl+Z / Ctrl+Maj+Z','annuler / rétablir'],['Ctrl+C / X / V','copier / couper / coller'],['Ctrl+D ; Alt+glisser','dupliquer'],['Suppr','supprimer'],['Ctrl+G / Ctrl+Maj+G','grouper / dégrouper'],['Alt+Maj+L','verrouiller'],
  ['Ctrl+] / Ctrl+[','avancer / reculer (+Alt : tout devant / derrière)'],['Maj+H / Maj+V','miroir'],['Flèches / Maj+flèches','1 px / 10 px'],['Ctrl+A','tout sélectionner'],['Ctrl+Maj+V','coller la pose sur une main'],
  ['Espace+glisser','déplacer la vue'],['Ctrl+molette','zoom'],['Ctrl+0 / Ctrl+1','ajuster / 100 %'],['Ctrl+S','enregistrer'],['Ctrl+E','exporter'],['Maj (rotation / échelle)','pas de 15° / proportions inversées'],['Alt (échelle)','depuis le centre'],['Ctrl (déplacement)','sans guides']];
$('raccourcis').innerHTML=RACC.map(([k,v])=>'<div><kbd>'+esc(k)+'</kbd><span>'+esc(v)+'</span></div>').join('');
$('bAide').onclick=()=>$('dlgAide').showModal();
$('bUndo').onclick=()=>hist.undoer();$('bRedo').onclick=()=>hist.redoer();
$('zMoins').onclick=()=>zoomVers(S.zoom/1.25,stage.clientWidth/2,stage.clientHeight/2);$('zPlus').onclick=()=>zoomVers(S.zoom*1.25,stage.clientWidth/2,stage.clientHeight/2);$('zFit').onclick=ajuste;
window.addEventListener('resize',()=>invalide());
(async()=>{S.doc=docNeuf('16:9');gabaritsPane();panneaux();ajuste();
  const b=await brouillonLit();if(b&&b.json&&b.json.elements&&b.json.elements.length){$('bBrouillon').hidden=false;$('projMsg').textContent='Un brouillon du '+new Date(b.date).toLocaleString('fr-FR')+' existe (onglet Projet).'}
  await FONTS_PRETES;invalide();
  if(AH()&&AH().ready)AH().ready.then(()=>{HC.clear();invalide()})})();
// surface de mise au point et de test (scripts Playwright v2/tests/plate_*.py) : rien de tout cela n'est utilisé par l'interface
window.__plate={S,doc:()=>S.doc,ajoute,selectionne,parId,hist,act,drawDoc,exporte,charge,serialise,docNeuf,gabarit,duplique,miroir,convertitCote,copiePose,collePose,eclate,supprime,ordre,groupe,degroupe,aligne,verrou,
  editeTexte,finTexte,surligne,marionnette,finMarionnette,importeImages,definirFond,detacherFond,ajuste,zoomVers,invalide,peint,mainCache,lignesTexte,projetDuPng,pngAvecProjet,brouillonSauve,brouillonLit,appliqueTheme,
  ecran,planche,bbox,FORMATS,GABARITS,poseV1,convertitV1,nomFichier,IMG,HC};
})();
