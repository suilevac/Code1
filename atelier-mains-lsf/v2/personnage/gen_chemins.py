"""Générateur des chemins du personnage (M4) → bloc de données de personnage.js.

Repère : creux du cou = (0, 0), x vers la droite DE L'IMAGE, y vers le bas, 1 longueur de main (HL) = 100 unités.
C'est le repère du dossier (personnage.md § 4.1, viewBox 400 × 620 décalé de (−200, −300)) : les ancres du dossier
s'y lisent directement (menton −58, épaules ±115, ancre des mains +100, taille +192).

Chaque pièce est un objet {f, d, s, o} :
  f  rôle de couleur du remplissage (clé de la palette de personnage.js), absent = pas de remplissage ;
  d  chemin SVG (syntaxe de l'attribut d, lue telle quelle par Path2D) ;
  s  facteur de trait (1 = trait principal, 0,8 = trait secondaire, 0 = aucun) ;
  o  ombres franches : [{f, d}], remplies APRÈS l'aplat et AVANT le trait, découpées par la pièce (clip). On peut donc
     les dessiner larges : seule la part qui tombe dans la pièce compte, et le trait du bord reste entier (dans les SVG du
     dossier l'ombre peinte par-dessus mangeait la moitié intérieure du trait côté ombre).

Lumière : fixe dans le repère caméra, (−0,45 ; 0,55 ; 1) (rendu.md : « Lumière », la même que le nuanceur de la main) —
elle vient d'en haut à GAUCHE, donc toutes les ombres franches sont à DROITE de l'image, de face comme de dos.

usage : python3 gen_chemins.py            (réécrit le bloc entre /*CHEMINS-DEBUT*/ et /*CHEMINS-FIN*/ de personnage.js)
"""
import json, os, re

ICI = os.path.dirname(os.path.abspath(__file__))
JS = os.path.join(ICI, 'personnage.js')


def n(v):
    """nombre compact : 12.0 → 12, 12.25 → 12.3 (0,1 unité = 1/1000 HL, invisible à 2 000 px de haut)."""
    v = round(v, 1)
    return str(int(v)) if v == int(v) else str(v)


def D(s):
    """normalise un chemin écrit à la main : espaces simples, nombres compacts."""
    s = re.sub(r'-?\d+\.?\d*', lambda m: n(float(m.group(0))), s)
    return re.sub(r'\s+', ' ', s.replace(',', ' ')).strip()


def cercle(cx, cy, r):
    return f'M {n(cx - r)} {n(cy)} A {n(r)} {n(r)} 0 1 0 {n(cx + r)} {n(cy)} A {n(r)} {n(r)} 0 1 0 {n(cx - r)} {n(cy)} Z'


def piece(f, d, s=1, o=None):
    p = {'d': D(d), 's': s}
    if f: p['f'] = f
    if o: p['o'] = [{'f': of, 'd': D(od)} for of, od in o]
    return p


def trait(d, s=1):
    return {'d': D(d), 's': s}


# ======================================================================================= tête (commune à A et B)
# Ovale haut, joues pleines, menton rond (personnage.md § 4.1 : sommet −186, menton −58, demi-largeur 0,50 HL à −114).
TETE = 'M 0,-186 C 52,-186 50,-134 48,-114 C 46,-86 28,-58 0,-58 C -28,-58 -46,-86 -48,-114 C -50,-134 -52,-186 0,-186 Z'

# Ombre de joue (v2.1, empruntée à la direction C) : un croissant le long du bord droit, mince sur le crâne (4 à 6 u.),
# qui s'élargit SOUS la pommette (12 u.) et suit la mâchoire jusqu'au menton. La joue sous l'œil reste éclairée : c'est
# ce creux qui fait lire une pommette, là où l'ancienne bande de largeur constante se lisait comme une tranche.
OMBRE_JOUE = ('M 22,-196 C 40,-178 46,-150 45,-126 C 44,-108 36,-100 33,-88 C 30,-74 20,-63 2,-60 '
              'L 0,-40 L 80,-40 L 80,-196 Z')


def antenne(sg, long=.9, x=14, y0=-170, w0=12, w1=8, lean=.7):
    """antenne courte et charnue : monte du haut du front puis part vers l'extérieur.
    Base 12 u., bout 8 u. (dossier : 9 et 5) : à 600 px de buste le trait fait 4,3 px, un bout de 5 u. (7,7 px) devenait
    une goutte d'encre (planche_finale_A_expressions.png : antennes « en crochet noir ») ; 8 u. laisse voir le vert.
    Les deux bords sont DÉCALÉS de l'axe le long de sa normale, et le bout est un demi-cercle dans l'axe : un bout fermé
    « en chapeau » (deux bords + une courbe posée à plat) se lisait comme une boule recourbée au bout de la tige.
    Dessinée AVANT la tête : sa base passe derrière le crâne, plus de trait de fermeture en travers du front."""
    import math
    bx = sg * x
    B = [(bx, y0 + 14), (bx + sg * 1, y0 - 16 * long), (bx + sg * 8 * lean, y0 - 32 * long), (bx + sg * 25 * lean, y0 - 40 * long)]
    def nrm(a, b):
        tx, ty = b[0] - a[0], b[1] - a[1]; l = math.hypot(tx, ty); return (-ty / l, tx / l), (tx / l, ty / l)
    N = [nrm(B[0], B[1])[0], nrm(B[0], B[2])[0], nrm(B[1], B[3])[0], nrm(B[2], B[3])[0]]
    T3 = nrm(B[2], B[3])[1]
    W = [w0 / 2, w0 / 2 * .85 + w1 / 2 * .15, w1 / 2 * 1.05, w1 / 2]
    G = [(B[i][0] + N[i][0] * W[i], B[i][1] + N[i][1] * W[i]) for i in range(4)]
    D_ = [(B[i][0] - N[i][0] * W[i], B[i][1] - N[i][1] * W[i]) for i in range(4)]
    k = W[3] * 4 / 3
    f = lambda q: f'{q[0]:.1f},{q[1]:.1f}'
    return (f'M {f(G[0])} C {f(G[1])} {f(G[2])} {f(G[3])} '
            f'C {f((G[3][0] + T3[0] * k, G[3][1] + T3[1] * k))} {f((D_[3][0] + T3[0] * k, D_[3][1] + T3[1] * k))} {f(D_[3])} '
            f'C {f(D_[2])} {f(D_[1])} {f(D_[0])} Z')


def oreille(sg, long=1.0, y=-114, pli=True, dos=False):
    """oreille pointue : attache au niveau des yeux, pointe vers le haut et l'extérieur (≈ 35°).
    Dessinée AVANT la tête et enfoncée de 8 u. dedans : le bord de la tête fait la jonction (le dossier la peignait
    par-dessus, d'où un trait vertical sur la tempe)."""
    ax = sg * 47
    tx, ty = sg * (47 + 40 * long), y - 36 * long
    if dos:
        # de dos l'oreille est peinte APRÈS le crâne : on voit son revers, posé sur le bord. Sa base est une courbe
        # qui rentre de 5 u. dans le crâne (essai à 9 u. avec une base droite : un coin carré « collé » sur la tête).
        b0, b1 = (sg * 44, y - 20), (sg * 44, y + 13)
        d = (f'M {b0[0]},{b0[1]} C {ax + sg * 14},{y - 30} {tx - sg * 10},{ty - 2} {tx},{ty} '
             f'C {tx - sg * 2},{ty + 16} {ax + sg * 18},{y + 14} {b1[0]},{b1[1]} '
             f'C {sg * 40},{y + 4} {sg * 40},{y - 11} {b0[0]},{b0[1]} Z')
        o = [('peauOmbre', f'M {ax - sg * 8},{y + 4} C {ax + sg * 14},{y + 6} {tx - sg * 8},{ty + 16} {tx + sg * 6},{ty + 4} '
                           f'L {tx + sg * 10},{y + 30} L {ax - sg * 8},{y + 30} Z')] if sg > 0 else None
        return [piece('peau', d, 1, o)]
    d = (f'M {ax - sg * 8},{y - 18} C {ax + sg * 14},{y - 30} {tx - sg * 10},{ty - 2} {tx},{ty} '
         f'C {tx - sg * 2},{ty + 16} {ax + sg * 18},{y + 14} {ax - sg * 8},{y + 14} Z')
    out = [piece('peau', d, 1, [('peauOmbre', f'M {ax - sg * 8},{y + 4} C {ax + sg * 14},{y + 6} {tx - sg * 8},{ty + 16} {tx + sg * 6},{ty + 4} '
                                               f'L {tx + sg * 10},{y + 30} L {ax - sg * 8},{y + 30} Z')] if sg > 0 else None)]
    if pli:
        out.append(trait(f'M {ax + sg * 4},{y - 6} Q {ax + sg * 14},{y - 14} {ax + sg * 20},{y - 2}', .8))
    return out


def cou(hw=30, fl=62, ombre_menton=True):
    """cou : demi-largeur 0,30 HL sous la tête (dossier : 0,27), puis il s'ÉVASE en trapèzes jusqu'à ±fl (0,62 HL en A,
    là où commence l'épaulette). Mesuré sur la planche : un cou de 0,25 HL qui tombait droit dans un col de ±0,34 HL se
    lisait « cou de girafe » / « poteau » sous une tête de 1 HL de large ; c'est la pente des trapèzes, pas la longueur
    (0,44 HL visibles, menton fixé à −0,58 par les ancres), qui fait un cou. Haut (−74) et bas (+14) cachés par la tête
    et par le vêtement : seul le trait des côtés se voit. Ombres : croissant sous le menton (13 u. au milieu) et bande
    du côté droit du cou qui s'arrête où le trapèze se retourne vers la lumière."""
    d = (f'M {-hw},-74 C {-hw},-52 {-hw},-40 {-hw - 2},-32 C {-hw - 5},-20 {-fl + 16},-8 {-fl},-3 L {-fl},14 '
         f'L {fl},14 L {fl},-3 C {fl - 16},-8 {hw + 5},-20 {hw + 2},-32 C {hw},-40 {hw},-52 {hw},-74 Z')
    o = [('peauOmbre', f'M {hw - 12},-90 C {hw - 9},-60 {hw - 8},-44 {hw - 7},-32 C {hw - 4},-22 {hw + 2},-14 {hw + 10},-9 L {hw + 40},-40 L {hw + 40},-90 Z')]
    if ombre_menton:
        o.append(('peauOmbre', 'M -50,-90 L 50,-90 L 50,-60 Q 0,-30 -50,-60 Z'))
    return piece('peau', d, 1, o)


# ======================================================================================= direction A (cape)
def epaulette(sg):
    """épaulette de cape : un coin séparé posé sur l'épaule, qui MONTE en pointe arrondie vers l'extérieur.
    v2.1 (emprunt à la direction C) : pointe à y −31 (dossier : −22) et bout arrondi ; le bord extérieur retombe en
    biais jusqu'à +27. Essai à −40 rejeté sur la planche : deux ailes dressées, l'épaulette prenait plus de place que la
    tête. La pointe s'arrête à ±1,43 HL : la boîte de la planche fait ±1,45 HL (PERS_HL.w = 2,9)."""
    d = (f'M {sg * 58},4 C {sg * 82},-2 {sg * 108},-16 {sg * 128},-26 Q {sg * 142},-33 {sg * 143},-20 '
         f'C {sg * 142},-4 {sg * 137},10 {sg * 132},27 C {sg * 110},33 {sg * 78},31 {sg * 58},24 Q {sg * 54},14 {sg * 58},4 Z')
    o = [('capeOmbre', f'M {sg * 150},26 C {sg * 110},20 {sg * 76},22 {sg * 46},18 L {sg * 46},50 L {sg * 150},50 Z')]
    if sg > 0:   # l'épaulette de droite tourne aussi son flanc extérieur vers l'ombre
        o.append(('capeOmbre', 'M 150,-60 L 134,-60 C 136,-30 132,0 124,30 L 150,30 Z'))
    return piece('cape', d, 1, o)


def pan(sg):
    """pan de cape derrière le flanc, EN CLOCHE (relecture adverse : « deux planches droites », évasement 0,13 HL).
    Bord extérieur courbe de ±1,22 (caché sous l'épaulette) à ±1,43 : évasement 0,21 HL, la courbe se creuse en haut et
    s'ouvre en bas comme un tissu qui tombe d'une épaule. Bas du pan : le coin extérieur est le plus BAS (+2,14) et le bord
    REMONTE vers le corps (+1,94 au flanc) — le dos de la cape est plus loin de l'œil, vu d'au-dessus du bas du buste il
    monte à l'écran, comme l'ourlet (dont le devant est le plus bas). Le bas du pan entre sous le CÔTÉ de la ceinture
    (+1,94, à mi-hauteur de la ceinture) : la jonction est un T sur un bord droit, plus de coin. L'ancien bas plat à +2,16
    passait sous le coin de l'ourlet (x ±0,80, y +2,12) et dépassait en petit ergot noir.
    Plis : à droite (côté ombre) l'ombre suit le bord extérieur + un pli oblique ; à gauche (côté lumière) un seul pli
    étroit. Un pli = un coin d'ombre qui s'ouvre vers le bas, pas un trait : à 200 px un trait de pli se lirait comme une
    déchirure."""
    d = (f'M {sg * 122},14 C {sg * 127},80 {sg * 137},150 {sg * 142},199 Q {sg * 144},214 {sg * 130},214 '
         f'C {sg * 112},213 {sg * 94},205 {sg * 82},194 L {sg * 60},194 L {sg * 60},14 Z')
    if sg > 0:
        o = [('capeOmbre', 'M 116,10 C 121,80 129,150 133,230 L 160,230 L 160,10 Z'),
             ('capeOmbre', 'M 96,64 C 103,110 110,160 114,230 L 102,230 C 100,170 98,120 96,64 Z')]
    else:
        o = [('capeOmbre', 'M -108,74 C -112,120 -117,170 -120,230 L -110,230 C -110,170 -109,120 -108,74 Z')]
    return piece('cape', d, 1, o)


# Vêtement : col rond (creux à +2 : le creux du cou se lit dans l'échancrure), trapèzes en pente douce sous les
# épaulettes, ourlet en arc qui descend de 6 u. au milieu (un cercle horizontal sous le niveau de l'œil se voit en ellipse
# dont le devant est plus BAS : l'arc donne le volume, la coupe droite du dossier faisait « carton »). Bas du buste à
# +2,2 HL = le bas de la boîte de la planche.
# Flancs (relecture adverse : « un placard », flancs de ±92 à ±80 en ligne presque droite) : la poitrine se BOMBE
# (±0,95 à +0,75) puis le flanc rentre à la taille (±0,82 au haut de la ceinture, +1,80) et la ceinture serre ;
# sous elle le tissu ressort à peine (±0,83 à l'ourlet). Écart poitrine / taille 0,13 HL de chaque côté : assez pour
# lire un corps, pas une taille de guêpe.
TUNIQUE_A = ('M -62,-3 C -74,0 -82,3 -88,8 C -94,14 -95,24 -93,34 C -96,80 -94,140 -82,180 '
             'C -82,192 -82,204 -83,212 Q 0,226 83,212 C 82,204 82,192 82,180 '
             'C 94,140 96,80 93,34 C 95,24 94,14 88,8 C 82,3 74,0 62,-3 Q 0,11 -62,-3 Z')
OMBRE_TUNIQUE_A = 'M 62,-30 C 72,0 76,50 74,100 C 72,140 66,170 62,240 L 130,240 L 130,-30 Z'
COL_V = 'M -14,3.6 L 0,26 L 14,3.6'
# Ceinture = repère « taille » (centrée sur +1,92 HL, personnage.md § 4.1) ; elle suit la même courbure que l'ourlet.
CEINTURE = 'M -83,180 Q 0,188 83,180 L 83,205 Q 0,213 -83,205 Z'
OMBRE_CEINTURE = 'M 60,160 L 60,230 L 100,230 L 100,160 Z'


def corps_A_face():
    L = [pan(-1), pan(1), cou(30)]
    L.append(piece('vetement', TUNIQUE_A, 1, [('vetementOmbre', OMBRE_TUNIQUE_A)]))
    L.append(trait(COL_V, .9))
    L.append(piece('ceinture', CEINTURE, 1, [('ceintureOmbre', OMBRE_CEINTURE)]))
    L += [epaulette(-1), epaulette(1)]
    return L


def tete_face(long_ant=1.0, long_or=1.0, ant=None, joue=True):
    ant = ant or {}
    L = [piece('peau', antenne(-1, long_ant, **ant), 1), piece('peau', antenne(1, long_ant, **ant), 1, [('peauOmbre', 'M 18,-260 L 60,-260 L 60,-150 L 26,-150 C 28,-170 30,-190 30,-200 Z')])]
    L += oreille(-1, long_or) + oreille(1, long_or)
    L.append(piece('peau', TETE, 1, [('peauOmbre', OMBRE_JOUE)] if joue else None))
    return L


def tete_nuque(hw=31, fl=62):
    """crâne + nuque vus de DOS, d'UNE pièce (relecture adverse : la tête de dos était l'œuf de face, menton compris,
    posé sur le cou : un « mannequin sans visage »). De dos il n'y a pas de menton : le crâne descend jusqu'à l'occiput
    (±0,36 à −0,76) et ENTRE dans la nuque par une courbe rentrante, sans trait de séparation ; la nuque est plus large
    en haut que le cou de face (±0,31 contre ±0,30, puis les trapèzes partent dès −0,40 au lieu de −0,32) et descend en
    pente vers les épaules. Le bas est caché par le col de la cape."""
    def cote(sg):
        return [(sg * 48, -114), (sg * 46, -96), (sg * 41, -84), (sg * 36, -76),
                (sg * (hw + 3), -68), (sg * hw, -58), (sg * hw, -48),
                (sg * hw, -36), (sg * (hw + 6), -22), (sg * (fl - 18), -10)]
    def f(q): return f'{n(q[0])},{n(q[1])}'
    D_ = cote(1); G = cote(-1)
    return (f'M 0,-186 C 52,-186 50,-134 {f(D_[0])} C {f(D_[1])} {f(D_[2])} {f(D_[3])} C {f(D_[4])} {f(D_[5])} {f(D_[6])} '
            f'C {f(D_[7])} {f(D_[8])} {f(D_[9])} Q {fl - 8},-6 {fl},-3 L {fl},16 L {-fl},16 L {-fl},-3 Q {-fl + 8},-6 {f(G[9])} '
            f'C {f(G[8])} {f(G[7])} {f(G[6])} C {f(G[5])} {f(G[4])} {f(G[3])} C {f(G[2])} {f(G[1])} {f(G[0])} '
            f'C -50,-134 -52,-186 0,-186 Z')


# Ombres de la tête de dos : le croissant du crâne à droite (comme de face) qui continue sur le côté droit de la nuque,
# et l'OMBRE PORTÉE DE L'OCCIPUT : le crâne surplombe la nuque, la lumière vient d'en haut à gauche, donc une bande en
# croissant sous la base du crâne, mince à gauche (4 u.) et plus épaisse à droite (11 u.). C'est elle, et pas un trait,
# qui dit où le crâne finit — un trait en travers refermerait la tête et referait un menton.
OMBRE_CRANE_DOS = ('M 22,-196 C 40,-178 47,-150 46,-120 C 45,-100 40,-88 33,-79 C 26,-66 22,-50 22,-36 '
                   'C 24,-22 34,-12 50,-6 L 90,-6 L 90,-196 Z')
OMBRE_OCCIPUT = 'M -40,-82 C -26,-68 18,-66 44,-84 L 44,-60 C 22,-52 -18,-58 -34,-70 Z'
# Sillon de la nuque : un trait court au milieu, là où le cou rentre entre les deux muscles (ligament nucal). Avec
# l'ombre d'occiput c'est ce qui dit « de dos » sans légende ; deux traits (plis horizontaux) faisaient « cou de tortue ».
SILLON_NUQUE = 'M 0,-60 Q -1.5,-48 0,-34'


def tete_dos(long_ant=1.0, long_or=1.0, ant=None, hw=31, fl=62):
    """vue de dos : antennes et oreilles de la même silhouette, crâne + nuque d'une pièce, PAS de visage.
    Les oreilles passent DEVANT le bord du crâne (on voit leur dos ; leur base est posée sur le crâne, 9 u. à
    l'intérieur du bord) : de face elles sont derrière la tête, de dos devant — c'est l'autre indice de la vue."""
    ant = ant or {}
    L = [piece('peau', antenne(-1, long_ant, **ant), 1), piece('peau', antenne(1, long_ant, **ant), 1, [('peauOmbre', 'M 18,-260 L 60,-260 L 60,-150 L 26,-150 C 28,-170 30,-190 30,-200 Z')])]
    L.append(piece('peau', tete_nuque(hw, fl), 1, [('peauOmbre', OMBRE_CRANE_DOS), ('peauOmbre', OMBRE_OCCIPUT)]))
    L.append(trait(SILLON_NUQUE, .8))
    return L, oreille(-1, long_or, pli=False, dos=True) + oreille(1, long_or, pli=False, dos=True)


def vue_dos(corps, tete):
    """ordre de peinture de dos : crâne + nuque, PUIS la cape ou la tunique (leur col couvre le bas de la nuque),
    PUIS les oreilles (devant le bord du crâne)."""
    fond, oreilles = tete
    return fond + corps + oreilles


# Dos de la cape : UNE nappe des épaules au bas, qui couvre tout le dos (bords = bords extérieurs des pans), col
# droit derrière la nuque (le col de dos est plus haut que l'encolure de devant). Deux plis seulement : deux coins
# d'ombre qui partent sous les épaulettes et s'ouvrent vers le bas — assez pour lire « tissu qui tombe », pas plus.
CAPE_DOS = ('M -62,-4 C -80,0 -104,6 -122,14 C -127,80 -137,150 -142,199 Q -144,214 -130,214 '
            'Q 0,224 130,214 Q 144,214 142,199 C 137,150 127,80 122,14 C 104,6 80,0 62,-4 Q 0,-18 -62,-4 Z')
OMBRES_CAPE_DOS = [
    ('capeOmbre', 'M 116,10 C 121,80 129,150 133,240 L 160,240 L 160,10 Z'),
    ('capeOmbre', 'M 38,40 C 46,110 52,170 58,240 L 30,240 C 34,170 36,110 38,40 Z'),
    ('capeOmbre', 'M -58,48 C -54,118 -48,178 -42,240 L -64,240 C -64,178 -62,118 -58,48 Z'),
]


def corps_A_dos():
    L = []
    L.append(piece('cape', CAPE_DOS, 1, OMBRES_CAPE_DOS))
    L += [epaulette(-1), epaulette(1)]
    return L


# ======================================================================================= direction B (simple)
# Tunique d'une pièce, épaules rondes à ±1,08 HL (dossier : E = 108), encolure ronde, pas de cape ni de ceinture.
TUNIQUE_B = ('M -56,-3 C -74,0 -90,8 -100,26 C -108,64 -110,150 -110,212 Q 0,226 110,212 '
             'C 110,150 108,64 100,26 C 90,8 74,0 56,-3 Q 0,11 -56,-3 Z')
TUNIQUE_B_DOS = ('M -56,-4 C -74,0 -90,8 -100,26 C -108,64 -110,150 -110,212 Q 0,226 110,212 '
                 'C 110,150 108,64 100,26 C 90,8 74,0 56,-4 Q 0,-12 -56,-4 Z')
OMBRE_TUNIQUE_B = 'M 74,-20 C 84,30 86,100 84,150 L 84,240 L 130,240 L 130,-20 Z'


def corps_B_face():
    return [cou(27, 56), piece('vetement', TUNIQUE_B, 1, [('vetementOmbre', OMBRE_TUNIQUE_B)])]


def corps_B_dos():
    return [piece('vetement', TUNIQUE_B_DOS, 1, [('vetementOmbre', OMBRE_TUNIQUE_B)])]


# ======================================================================================= visages
EY = -116          # hauteur des yeux (−1,16 HL)
EXPR = ('neutre', 'sourire', 'sourcils_leves', 'sourcils_fronces')


def visage_A(expr):
    """œil en amande + iris, arcade = masse d'encre (pas un trait : à 200 px elle se confondrait avec l'œil),
    nez = un crochet, bouche. Sourcils du dossier (§ 4.5, y relatif à l'œil) : −20 / −21 / −33 / −14 ; forme de l'œil
    ci-dessous (les ouvertures du dossier, 8 / 6 / 11 / 6, revues à la planche de 200 px)."""
    L = []
    # paupière haute / basse (flèche du contrôle de la courbe, u.) : neutre 11/8 (dossier : ouverture 8) ; sourire 11/−1,
    # l'œil devient un croissant que la joue remonte (le trait de paupière ajouté au-dessous faisait des « points de
    # couture » à 200 px) ; levés 14/11 ; froncés 4/7, la paupière haute descend sur l'iris.
    hb = {'neutre': (11, 8), 'sourire': (11, -1), 'sourcils_leves': (14, 11), 'sourcils_fronces': (4, 7)}[expr]
    by = EY + {'neutre': -20, 'sourire': -21, 'sourcils_leves': -33, 'sourcils_fronces': -14}[expr]
    tilt = {'neutre': 0, 'sourire': 1, 'sourcils_leves': 2, 'sourcils_fronces': 8}[expr]
    for sg in (-1, 1):
        ex = sg * 27
        iy = EY + (.5 if expr != 'sourire' else -1.5)
        # l'iris et son reflet sont des « ombres » de l'œil : découpés par lui, ils ne débordent jamais de la paupière.
        # Reflet en haut à GAUCHE de la pupille, du côté de la lumière : il donne le regard à 600 px et se perd sous le
        # trait à 200 px.
        if expr == 'sourire':
            # œil qui sourit = arche d'encre « ∩ » (yeux plissés par les joues). Relecture adverse : le croissant à
            # paupière basse PLATE (flèche 1 u.) et iris coupé se lisait « narquois » / « endormi » à 600 et 2 000 px,
            # deux traits à 200 px. Ici les DEUX bords montent (flèches 16 et 9 u.) : épaisseur 3,5 u. au sommet, nulle
            # aux coins, + le trait ; au sommet l'arche est à −8 u. de la ligne des yeux, comme les yeux du B qui se
            # lisaient déjà « ^ ^ ». La pommette remonte : un arc COURT (9 u.) sous le coin extérieur de l'œil ; un arc de 13 u. sous tout l'œil
            # se lisait à 200 px comme une seconde paupière.
            L.append(piece('trait', f'M {ex - 15},{EY + 2} Q {ex},{EY - 16} {ex + 15},{EY + 2} Q {ex},{EY - 9} {ex - 15},{EY + 2} Z', .6))
            L.append(trait(f'M {ex + sg * 8},{EY + 13} Q {ex + sg * 14},{EY + 13} {ex + sg * 17},{EY + 8}', .7))
        else:
            L.append(piece('oeil', f'M {ex - 15},{EY} Q {ex},{EY - hb[0]} {ex + 15},{EY} Q {ex},{EY + hb[1]} {ex - 15},{EY} Z', 1,
                           [('trait', cercle(ex + sg * 1.5, iy, 5.4)), ('oeil', cercle(ex + sg * 1.5 - 2, iy - 2.1, 1.5))]))
        xi, xo = ex - sg * 19, ex + sg * 18
        yi, yo = by + tilt, by - tilt * .4
        L.append(piece('trait', f'M {xi},{yi + 2} Q {ex},{by - 8} {xo},{yo + 1} Q {ex},{by} {xi},{yi + 7.6} Z', .5))

    if expr == 'sourcils_fronces':
        L.append(trait(f'M -4,{EY - 18} L -3,{EY - 7} M 4,{EY - 18} L 3,{EY - 7}', .9))
    if expr == 'sourcils_leves':            # UN pli au milieu du front (deux arcs au-dessus de chaque sourcil se
        L.append(trait('M -15,-166 Q 0,-171 15,-166', .7))   # lisaient comme des sourcils doublés)
    # nez : un crochet du côté de l'ombre (à droite), pas l'arc du dossier — sous l'arc, la bouche droite de « neutre »
    # se lisait comme une seconde bouche souriante
    L.append(trait('M 3,-101 Q 9,-91 5,-87 Q 1,-84 -4,-87', .9))
    my = -71
    if expr == 'sourire':                   # sourire ouvert : un croissant d'encre (bord haut presque droit, bas profond)
        # aux coins relevés ; l'arc seul (trait de 2,8 u.) se perdait à 200 px et n'aidait pas à lire « content »
        L.append(piece('trait', f'M -17,{my - 5} Q 0,{my - 1} 17,{my - 5} Q 0,{my + 14} -17,{my - 5} Z', .8))
    elif expr == 'sourcils_leves':          # bouche entrouverte : une petite ouverture sombre, pas un arc
        L.append(piece('trait', f'M -8,{my - 1} Q 0,{my - 4} 8,{my - 1} Q 0,{my + 8} -8,{my - 1} Z', .6))
    elif expr == 'sourcils_fronces':
        L.append(trait(f'M -13,{my + 3} Q 0,{my - 3} 13,{my + 3}'))
    else:
        L.append(trait(f'M -13,{my} L 13,{my}'))
    return L


def visage_B(expr):
    """style simple : yeux = deux points, sourcils = deux traits épais, bouche ; pas de nez (dossier : 17 éléments)."""
    L = []
    r = {'neutre': 5, 'sourire': 4.5, 'sourcils_leves': 6.2, 'sourcils_fronces': 4.5}[expr]
    by = EY + {'neutre': -20, 'sourire': -21, 'sourcils_leves': -31, 'sourcils_fronces': -13}[expr]
    tilt = {'neutre': 0, 'sourire': 1, 'sourcils_leves': 2, 'sourcils_fronces': 7}[expr]
    for sg in (-1, 1):
        ex = sg * 27
        if expr == 'sourire':               # yeux fermés en arc : deux points + un trait dessous se lisaient « ☹ »
            L.append(trait(f'M {ex - 7},{EY + 2} Q {ex},{EY - 8} {ex + 7},{EY + 2}', 1.3))
        else:
            L.append(piece('trait', cercle(ex, EY, r), 0))
        xi, xo = ex - sg * 16, ex + sg * 15
        L.append(trait(f'M {xi},{by + tilt} Q {ex},{by - 6} {xo},{by - tilt * .4}', 1.7))
    my = -71
    if expr == 'sourire':
        L.append(trait(f'M -15,{my - 3} Q 0,{my + 9} 15,{my - 3}', 1.2))
    elif expr == 'sourcils_leves':
        L.append(piece('trait', f'M -7,{my - 1} Q 0,{my - 4} 7,{my - 1} Q 0,{my + 7} -7,{my - 1} Z', .6))
    elif expr == 'sourcils_fronces':
        L.append(trait(f'M -12,{my + 3} Q 0,{my - 3} 12,{my + 3}', 1.2))
    else:
        L.append(trait(f'M -12,{my} L 12,{my}', 1.2))
    return L


def donnees():
    antB = dict(x=14, w0=10, w1=7)
    return {
        'A': {'face': corps_A_face() + tete_face(.9), 'dos': vue_dos(corps_A_dos(), tete_dos(.9)),
              'visage': {e: visage_A(e) for e in EXPR}},
        'B': {'face': corps_B_face() + tete_face(.75, .85, antB), 'dos': vue_dos(corps_B_dos(), tete_dos(.75, .85, antB, hw=28, fl=56)),
              'visage': {e: visage_B(e) for e in EXPR}},
    }


if __name__ == '__main__':
    data = donnees()
    txt = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    # une pièce par ligne : le bloc reste lisible et les différences de version restent courtes
    txt = txt.replace('},{"d"', '},\n  {"d"').replace('],"', '],\n "')
    src = open(JS, encoding='utf-8').read()
    a, b = '/*CHEMINS-DEBUT*/', '/*CHEMINS-FIN*/'
    i, j = src.index(a) + len(a), src.index(b)
    src = src[:i] + '\n' + txt + '\n' + src[j:]
    open(JS, 'w', encoding='utf-8').write(src)
    np_ = sum(len(v['face']) + len(v['dos']) + sum(len(x) for x in v['visage'].values()) for v in data.values())
    print(f'{np_} pièces, {len(txt)} octets de chemins → {JS}')
