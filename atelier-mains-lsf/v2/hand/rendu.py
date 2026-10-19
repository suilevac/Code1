"""Rendu orthographique rapide (numpy, z-buffer par face) pour les contrôles intermédiaires.
render(V, F, R, size, ...) : V (n,3), F liste de faces (tri/quad), R matrice 3x3 (lignes = axes écran x, y, profondeur vers l'œil)."""
import numpy as np
from PIL import Image, ImageDraw
def tris_of(F):
    out=[]
    for f in F:
        for k in range(1,len(f)-1): out.append((f[0],f[k],f[k+1]))
    return np.array(out)
def render(V,F,R,size=600,scale=None,center=None,color=(0,161,154),light=(0.3,0.4,1.0),wire=False,points=None,segs=None,bg=(255,255,255)):
    T=tris_of(F) if not isinstance(F,np.ndarray) or F.shape[1]!=3 else F
    P=V@R.T
    c=P.mean(0) if center is None else np.asarray(center)@R.T
    s=(size*0.44)/max(1e-9,np.abs(P[:,:2]-c[:2]).max()) if scale is None else scale
    X=(P[:,0]-c[0])*s+size/2; Y=size/2-(P[:,1]-c[1])*s; Z=P[:,2]
    N=np.cross(P[T[:,1]]-P[T[:,0]],P[T[:,2]]-P[T[:,0]]); nn=np.linalg.norm(N,axis=1)+1e-12; N/=nn[:,None]
    L=np.array(light,float); L/=np.linalg.norm(L); sh=np.clip(N@L,0,1)
    col=np.array(color,float)
    img=np.full((size,size,3),bg,np.uint8); zb=np.full((size,size),-1e9)
    order=np.argsort(Z[T].mean(1))
    for fi in order:
        if N[fi,2]<=0: continue
        tri=np.c_[X[T[fi]],Y[T[fi]]]; z=Z[T[fi]].mean()
        x0,x1=int(max(0,tri[:,0].min())),int(min(size-1,tri[:,0].max())); y0,y1=int(max(0,tri[:,1].min())),int(min(size-1,tri[:,1].max()))
        if x1<x0 or y1<y0: continue
        xs,ys=np.meshgrid(np.arange(x0,x1+1),np.arange(y0,y1+1)); pts=np.c_[xs.ravel(),ys.ravel()]+0.5
        d=np.ones(len(pts),bool)
        sgn=np.sign((tri[1][0]-tri[0][0])*(tri[2][1]-tri[0][1])-(tri[1][1]-tri[0][1])*(tri[2][0]-tri[0][0])+1e-12)
        for k in range(3):
            a,b=tri[k],tri[(k+1)%3]; d&=((b[0]-a[0])*(pts[:,1]-a[1])-(b[1]-a[1])*(pts[:,0]-a[0]))*sgn>=0
        sel=pts[d].astype(int)
        if len(sel)==0: continue
        msk=z>zb[sel[:,1],sel[:,0]]; sel=sel[msk]; zb[sel[:,1],sel[:,0]]=z
        img[sel[:,1],sel[:,0]]=(col*(0.35+0.65*sh[fi])).astype(np.uint8)
    im=Image.fromarray(img); dr=ImageDraw.Draw(im)
    if wire:
        for fi in order:
            if N[fi,2]<=0: continue
            dr.polygon([(X[i],Y[i]) for i in T[fi]],outline=(30,30,30))
    def proj(p):
        q=np.asarray(p)@R.T; return ((q[0]-c[0])*s+size/2, size/2-(q[1]-c[1])*s)
    if segs:
        for a,b,colr in segs:
            dr.line([proj(a),proj(b)],fill=colr,width=3)
    if points:
        for p,colr in points:
            x,y=proj(p); dr.ellipse([x-4,y-4,x+4,y+4],fill=colr)
    return im,proj
def view(name):
    """matrices de vue : lignes = axe écran x, axe écran y, direction vers l'œil"""
    V={'paume':np.array([[1,0,0],[0,1,0],[0,0,1.]]),       # caméra en +Z : x à droite, y en haut
       'dos':np.array([[-1,0,0],[0,1,0],[0,0,-1.]]),
       'profil_radial':np.array([[0,0,-1],[0,1,0],[1,0,0.]]),  # caméra en +X (côté pouce)
       'profil_ulnaire':np.array([[0,0,1],[0,1,0],[-1,0,0.]]),
       'dessus':np.array([[1,0,0],[0,0,-1],[0,1,0.]]),   # caméra en +Y (bouts des doigts vers nous)
       }
    return V[name]
def sheet(images,labels,cols=None,pad=8,font=None):
    cols=cols or len(images); w=max(i.width for i in images); h=max(i.height for i in images)
    rows=(len(images)+cols-1)//cols
    S=Image.new('RGB',(cols*(w+pad)+pad, rows*(h+pad+18)+pad),'white'); dr=ImageDraw.Draw(S)
    for k,(im,lab) in enumerate(zip(images,labels)):
        r,cc=divmod(k,cols); x=pad+cc*(w+pad); y=pad+r*(h+pad+18)
        S.paste(im,(x,y+18)); dr.text((x+4,y+2),lab,fill='black')
    return S

def overlay_dessin(mask, sx, segs=None, pts=None, size=560, sy=None, contour=None):
    """le dessin paume (masque gris) à l'échelle anisotrope du repère (cm), avec des segments/points 3D projetés en XY,
    et éventuellement un contour (liste de polylignes XY en cm, couleur)"""
    import numpy as np
    from PIL import Image, ImageDraw
    H, W = mask.shape
    x0, ypli = 505.0, 792.0
    sy = sy or 19.0 / (792.0 - 18.0)
    # boîte en cm
    xs = np.where(mask.any(0))[0]; ys = np.where(mask.any(1))[0]
    X0, X1 = (xs.min() - x0) * sx, (xs.max() - x0) * sx; Y0, Y1 = (ypli - ys.max()) * sy, (ypli - ys.min()) * sy
    ext = max(X1 - X0, Y1 - Y0) * 1.08; s = size / ext
    cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    def P(x, y): return ((x - cx) * s + size / 2, size / 2 - (y - cy) * s)
    img = Image.new('RGB', (size, size), 'white')
    # masque rééchantillonné
    mi = Image.fromarray((mask * 255).astype(np.uint8))
    # coin haut-gauche du masque en cm → px image
    px0, py0 = P((0 - x0) * sx, (ypli - 0) * sy)
    mi = mi.resize((max(1, int(W * sx * s)), max(1, int(H * sy * s))))
    gray = Image.new('RGB', mi.size, (205, 205, 205))
    img.paste(gray, (int(px0), int(py0)), mi)
    dr = ImageDraw.Draw(img)
    if contour:
        for poly, col in contour:
            dr.line([P(x, y) for x, y in poly], fill=col, width=2)
    for a, b, col in (segs or []): dr.line([P(a[0], a[1]), P(b[0], b[1])], fill=col, width=3)
    for p, col in (pts or []):
        x, y = P(p[0], p[1]); dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=col)
    return img
