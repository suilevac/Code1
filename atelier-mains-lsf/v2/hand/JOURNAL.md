# Chantier M1 — la main (assets) : journal

Objectif : `hand_v2.glb` + `hand_v2.json` conformes au contrat M1 → M2 de `v2/PLAN.md`, produits par `build_hand.py`
(reproductible), contrôlés par `checks/`.

## 0. Lecture (15 oct. 2026)
- PLAN.md, CLAUDE.md, anatomie.md, mobilite.md, modeles.md lus en entier.
- Repère du contrat : doigts +Y, paume +Z, pouce +X, poignet à l'origine, cm. Vu de la caméra « Paume (face) » en +Z
  (x à droite de l'écran), le pouce est à DROITE : c'est exactement le dessin `references/paume.jpg` (pouce à droite,
  paume vers nous). Anatomiquement, une paume tournée vers soi avec le pouce à droite est une main DROITE (test du
  « L » : dos de la main gauche vers soi → pouce à droite ; paume vers soi → pouce à gauche). Le contrat dit
  « main gauche » : les trois axes sont ce que le code consomme, je les respecte à la lettre ; l'autre main est le
  miroir x → −x, et le JSON le note (`"cote_anatomique"`). À trancher par l'orchestrateur/M2 si l'étiquette compte.
- Échelle du dessin : v1 SC = 50 px/unité et « 1 u ≈ 11 mm » (CLAUDE.md : 1,96 u entre deux centres de MCP pour ≈ 21 mm) ;
  ici on fixe HL = 190 mm (pli du poignet → bout du majeur) et la paume à 90,6 mm (PLAN.md).


## 1. Extraction
- boucle de coupe : 20 arêtes / 20 sommets, tous de degré 2 ; plan moyen à -2.71 cm du poignet (écart avant aplatissement -0.38..0.28 cm)
- redressement : plan médian de la paume incliné de -5.8° sur la ligne des cubes (z = -0.102·y + 0.78) → rotation autour de X ; résidu -11.76° ; recentrage à y = 0 : x0 = 0.12, z0 = 1.29 cm (épaisseur MH du poignet 2.21 cm, largeur 4.01 cm)
- main extraite : 1669 sommets, 1659 faces (1658 quads + 1 bouchon de 20 côtés) ; boîte x -6.0..6.8, y -3.1..17.6, z -3.7..2.9 cm
- longueur MH poignet → bout du majeur : 17.66 cm (cible 19.0)

## 2. Squelette
- dessin : 1re commissure à (690, 519) px, bord ulnaire x = 284 à y = 520 → échelle X 0.02232 cm/px (paume 90.6 mm) ; échelle Y 0.02455 cm/px (HL 190 mm sur 774 px)
- longueurs d’os (cm) : dessin (chaîne v1) | Buryanov × 1,03 | retenu
  | doigt | P1 dessin | P2 | P3+pulpe | P1 Bur. | P2 | P3+p | P1 retenu | P2 | P3+p | total retenu |
  |---|---|---|---|---|---|---|---|---|---|---|
  | index | 3.95 | 2.50 | 2.21 | 4.10 | 2.31 | 2.01 | 4.21 | 2.37 | 2.07 | 8.65 |
  | majeur | 4.57 | 2.84 | 2.31 | 4.59 | 2.71 | 2.19 | 4.70 | 2.78 | 2.24 | 9.72 |
  | annulaire | 3.92 | 2.63 | 2.26 | 4.26 | 2.65 | 2.18 | 4.13 | 2.57 | 2.11 | 8.80 |
  | auriculaire | 3.07 | 1.77 | 1.95 | 3.37 | 1.86 | 2.00 | 3.51 | 1.94 | 2.08 | 7.53 |
  | pouce | 4.70 | 2.95 | 2.40 | 4.76 | 3.25 | 2.81 | 4.76 | 3.25 | 2.81 | 10.82 |
  (auriculaire : total = Y du pli IPD de l’annulaire (15.81) − Y de sa MCP (8.28) = 7.53, Buryanov 7.23 : son auriculaire est long ; index 8.65 ≈ annulaire 8.80 : les siens)
  index : MCP (2.19, 9.11, -2.31) [MH z -2.34, peau -3.27..-1.13] ; IPP z -2.11, IPD z -2.00, bout z -1.90
  majeur : MCP (0.00, 9.28, -2.57) [MH z -2.27, peau -3.63..-0.97] ; IPP z -2.39, IPD z -2.28, bout z -2.19
  annulaire : MCP (-2.13, 9.12, -2.44) [MH z -2.40, peau -3.59..-1.02] ; IPP z -2.41, IPD z -2.40, bout z -2.38
  auriculaire : MCP (-3.68, 8.28, -1.67) [MH z -2.17, peau -2.94..-0.78] ; IPP z -1.70, IPD z -1.72, bout z -1.74
  pouce : CMC (3.28, 1.08, -0.73) ; MC I à 43° de +Y dans le plan XY (MC II à 8° → 35° entre les deux ; anatomie.md : ≈ 30° au repos), élévation palmaire 15° ; P1 à 30°, P2 à 26° ; bout (9.15, 9.49, 2.40)
- centres (cm) et longueurs centre → centre :
  | os | parent | centre | longueur (cm) | cible Buryanov×1,03 |
  |---|---|---|---|---|
  | poignet | — | (0, 0, 0) | 3.93 (→ base du mc3) | — |
  | mc1 | poignet | (3.28, 1.08, -0.73) | 4.76 | 4.76 |
  | pouce_p1 | mc1 | (6.45, 4.42, 0.47) | 3.25 | 3.25 |
  | pouce_p2 | pouce_p1 | (8.00, 7.10, 1.47) | 2.81 | 2.81 |
  | mc2 | poignet | (1.30, 2.90, -2.16) | 6.27 | (MC II–V : 7.01, de la base) |
  | index_p1 | mc2 | (2.19, 9.11, -2.31) | 4.22 | 4.10 |
  | index_p2 | index_p1 | (2.19, 13.32, -2.11) | 2.38 | 2.31 |
  | index_p3 | index_p2 | (2.19, 15.70, -2.00) | 2.07 | 2.01 |
  | mc3 | poignet | (0.10, 3.10, -2.42) | 6.18 | (MC II–V : 6.65, de la base) |
  | majeur_p1 | mc3 | (0.00, 9.28, -2.57) | 4.71 | 4.59 |
  | majeur_p2 | majeur_p1 | (0.00, 13.98, -2.39) | 2.78 | 2.71 |
  | majeur_p3 | majeur_p2 | (0.00, 16.76, -2.28) | 2.25 | 2.19 |
  | mc4 | poignet | (-1.10, 3.00, -2.29) | 6.21 | (MC II–V : 5.97, de la base) |
  | annulaire_p1 | mc4 | (-2.13, 9.12, -2.44) | 4.13 | 4.26 |
  | annulaire_p2 | annulaire_p1 | (-2.13, 13.25, -2.41) | 2.57 | 2.65 |
  | annulaire_p3 | annulaire_p2 | (-2.13, 15.81, -2.40) | 2.11 | 2.18 |
  | mc5 | poignet | (-2.30, 2.60, -1.52) | 5.85 | (MC II–V : 5.53, de la base) |
  | auriculaire_p1 | mc5 | (-3.68, 8.28, -1.67) | 3.51 | 3.37 |
  | auriculaire_p2 | auriculaire_p1 | (-3.68, 11.79, -1.70) | 1.94 | 1.86 |
  | auriculaire_p3 | auriculaire_p2 | (-3.68, 13.73, -1.72) | 2.08 | 2.00 |
- contrôle LEAN : bout du doigt après 90° de flexion de la MCP (X du bout, + vers le pouce) :
  index : bout (2.19, 17.76, -1.90) → (1.21, 8.70, 6.29) : déport latéral -0.98 cm
  majeur : bout (0.00, 19.00, -2.19) → (0.00, 8.90, 7.15) : déport latéral +0.00 cm
  annulaire : bout (-2.13, 17.92, -2.38) → (-1.13, 9.06, 6.31) : déport latéral +1.00 cm
  auriculaire : bout (-3.68, 15.81, -1.74) → (-2.12, 8.34, 5.69) : déport latéral +1.57 cm

(temps total 2 s)
