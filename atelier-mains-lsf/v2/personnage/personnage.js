/* Atelier des mains LSF — palier v2, chantier M4 : LE PERSONNAGE (le référent à qui appartiennent les mains).

   Tronc + tête, SANS BRAS (demande de l'utilisateur : « retire-lui les bras, garde le tronc et la tête, inspire-toi de
   Piccolo »). Direction A du dossier personnage.md : crâne nu, antennes courtes et charnues, oreilles pointues, vêtement
   violet à col rond, ceinture rouge à la taille, cape ivoire à épaulettes — la cape COUVRE les bras, donc la silhouette est
   fermée et l'absence de bras est un vêtement, pas une amputation (§ 2.3). Hommage, pas copie : ni turban, ni taches, ni
   crocs, ni nom ; antennes visibles et tournées vers l'extérieur, épaulettes d'une autre coupe, cinq doigts (§ 1.3).
   Direction B : style « simple » (tunique seule, yeux-points), et repli automatique quand le buste fait moins de 160 px.

   Sans dépendance. Expose window.AtelierPersonnage :
     draw(ctx, {x, y, HLpx, vue:'face'|'dos', expression:'neutre'|'sourire'|'sourcils_leves'|'sourcils_fronces',
                style:'A'|'B', couleurs?, reperes?, repli?:false, HLrepli?})
                                    → {style, vue, expression, repli, trait, boite, corrections} ; null si HLpx invalide
         (x, y) = CREUX DU COU dans le repère courant de ctx ; HLpx = une longueur de main en pixels de ce repère.
         corrections = ce que le garde-fou de contraste a changé dans les couleurs données (vide d'ordinaire).
     ancres(HLpx, {vue, style}?)   → lieux du corps en px, relatifs au creux du cou (front, menton, nuque, épaules,
                                     poitrine, taille, ancre des mains, espace neutre, boîte du dessin) ; null si invalide
     boite(HLpx)                    → {x, y, w, h} du dessin, relative au creux du cou ; null si invalide
     styleEffectif(HLpx, style)     → 'A' ou 'B' (repli)

   Le dessin est fait de chemins SVG (1 HL = 100 unités, creux du cou = (0, 0)) générés par gen_chemins.py, convertis
   en Path2D UNE fois au chargement et gardés en cache. Le canvas est mis à l'échelle (1 unité = HLpx/100 px), et la
   largeur du trait est divisée par cette échelle : le trait reste constant À L'ÉCRAN, max(1,3 ; 0,028 · HLpx) px —
   le poids du contour de la main (coque ≈ 0,03 HL, personnage.md § 4.2) ; à 1,3 px minimum il ne se brise pas en
   pointillé sur une vignette.

   Lumière : la même que le nuanceur de la main, fixe dans le repère caméra, (−0,45 ; 0,55 ; 1) (rendu.md, « Lumière ») :
   elle vient d'en haut à GAUCHE, donc l'ombre franche est à DROITE de l'image, de face COMME de dos (la lumière ne
   tourne pas avec le personnage). Deux tons seulement, aplat + ombre franche, comme la main.
*/
(function () {
  'use strict';

  /* ---------------------------------------------------------------- chemins (générés : ne pas éditer à la main) */
  const CHEMINS = /*CHEMINS-DEBUT*/
{"A":{"face":[{"d":"M -122 14 C -127 80 -137 150 -142 199 Q -144 214 -130 214 C -112 213 -94 205 -82 194 L -60 194 L -60 14 Z","s":1,"f":"cape","o":[{"f":"capeOmbre","d":"M -108 74 C -112 120 -117 170 -120 230 L -110 230 C -110 170 -109 120 -108 74 Z"}]},
  {"d":"M 122 14 C 127 80 137 150 142 199 Q 144 214 130 214 C 112 213 94 205 82 194 L 60 194 L 60 14 Z","s":1,"f":"cape","o":[{"f":"capeOmbre","d":"M 116 10 C 121 80 129 150 133 230 L 160 230 L 160 10 Z"},{"f":"capeOmbre","d":"M 96 64 C 103 110 110 160 114 230 L 102 230 C 100 170 98 120 96 64 Z"}]},
  {"d":"M -30 -74 C -30 -52 -30 -40 -32 -32 C -35 -20 -46 -8 -62 -3 L -62 14 L 62 14 L 62 -3 C 46 -8 35 -20 32 -32 C 30 -40 30 -52 30 -74 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 18 -90 C 21 -60 22 -44 23 -32 C 26 -22 32 -14 40 -9 L 70 -40 L 70 -90 Z"},{"f":"peauOmbre","d":"M -50 -90 L 50 -90 L 50 -60 Q 0 -30 -50 -60 Z"}]},
  {"d":"M -62 -3 C -74 0 -82 3 -88 8 C -94 14 -95 24 -93 34 C -96 80 -94 140 -82 180 C -82 192 -82 204 -83 212 Q 0 226 83 212 C 82 204 82 192 82 180 C 94 140 96 80 93 34 C 95 24 94 14 88 8 C 82 3 74 0 62 -3 Q 0 11 -62 -3 Z","s":1,"f":"vetement","o":[{"f":"vetementOmbre","d":"M 62 -30 C 72 0 76 50 74 100 C 72 140 66 170 62 240 L 130 240 L 130 -30 Z"}]},
  {"d":"M -14 3.6 L 0 26 L 14 3.6","s":0.9},
  {"d":"M -83 180 Q 0 188 83 180 L 83 205 Q 0 213 -83 205 Z","s":1,"f":"ceinture","o":[{"f":"ceintureOmbre","d":"M 60 160 L 60 230 L 100 230 L 100 160 Z"}]},
  {"d":"M -58 4 C -82 -2 -108 -16 -128 -26 Q -142 -33 -143 -20 C -142 -4 -137 10 -132 27 C -110 33 -78 31 -58 24 Q -54 14 -58 4 Z","s":1,"f":"cape","o":[{"f":"capeOmbre","d":"M -150 26 C -110 20 -76 22 -46 18 L -46 50 L -150 50 Z"}]},
  {"d":"M 58 4 C 82 -2 108 -16 128 -26 Q 142 -33 143 -20 C 142 -4 137 10 132 27 C 110 33 78 31 58 24 Q 54 14 58 4 Z","s":1,"f":"cape","o":[{"f":"capeOmbre","d":"M 150 26 C 110 20 76 22 46 18 L 46 50 L 150 50 Z"},{"f":"capeOmbre","d":"M 150 -60 L 134 -60 C 136 -30 132 0 124 30 L 150 30 Z"}]},
  {"d":"M -8 -156.2 C -9.3 -185.1 -16.3 -201.3 -29.4 -209.4 C -34 -212.2 -38.1 -205.3 -33.6 -202.6 C -22.9 -196.3 -20.7 -183.7 -20 -155.8 Z","s":1,"f":"peau"},
  {"d":"M 20 -155.8 C 20.7 -183.7 22.9 -196.3 33.6 -202.6 C 38.1 -205.3 34 -212.2 29.4 -209.4 C 16.3 -201.3 9.3 -185.1 8 -156.2 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 18 -260 L 60 -260 L 60 -150 L 26 -150 C 28 -170 30 -190 30 -200 Z"}]},
  {"d":"M -39 -132 C -61 -144 -77 -152 -87 -150 C -85 -134 -65 -100 -39 -100 Z","s":1,"f":"peau"},
  {"d":"M -51 -120 Q -61 -128 -67 -116","s":0.8},
  {"d":"M 39 -132 C 61 -144 77 -152 87 -150 C 85 -134 65 -100 39 -100 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 39 -110 C 61 -108 79 -134 93 -146 L 97 -84 L 39 -84 Z"}]},
  {"d":"M 51 -120 Q 61 -128 67 -116","s":0.8},
  {"d":"M 0 -186 C 52 -186 50 -134 48 -114 C 46 -86 28 -58 0 -58 C -28 -58 -46 -86 -48 -114 C -50 -134 -52 -186 0 -186 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 22 -196 C 40 -178 46 -150 45 -126 C 44 -108 36 -100 33 -88 C 30 -74 20 -63 2 -60 L 0 -40 L 80 -40 L 80 -196 Z"}]}],
 "dos":[{"d":"M -8 -156.2 C -9.3 -185.1 -16.3 -201.3 -29.4 -209.4 C -34 -212.2 -38.1 -205.3 -33.6 -202.6 C -22.9 -196.3 -20.7 -183.7 -20 -155.8 Z","s":1,"f":"peau"},
  {"d":"M 20 -155.8 C 20.7 -183.7 22.9 -196.3 33.6 -202.6 C 38.1 -205.3 34 -212.2 29.4 -209.4 C 16.3 -201.3 9.3 -185.1 8 -156.2 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 18 -260 L 60 -260 L 60 -150 L 26 -150 C 28 -170 30 -190 30 -200 Z"}]},
  {"d":"M 0 -186 C 52 -186 50 -134 48 -114 C 46 -96 41 -84 36 -76 C 34 -68 31 -58 31 -48 C 31 -36 37 -22 44 -10 Q 54 -6 62 -3 L 62 16 L -62 16 L -62 -3 Q -54 -6 -44 -10 C -37 -22 -31 -36 -31 -48 C -31 -58 -34 -68 -36 -76 C -41 -84 -46 -96 -48 -114 C -50 -134 -52 -186 0 -186 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 22 -196 C 40 -178 47 -150 46 -120 C 45 -100 40 -88 33 -79 C 26 -66 22 -50 22 -36 C 24 -22 34 -12 50 -6 L 90 -6 L 90 -196 Z"},{"f":"peauOmbre","d":"M -40 -82 C -26 -68 18 -66 44 -84 L 44 -60 C 22 -52 -18 -58 -34 -70 Z"}]},
  {"d":"M 0 -60 Q -1.5 -48 0 -34","s":0.8},
  {"d":"M -62 -4 C -80 0 -104 6 -122 14 C -127 80 -137 150 -142 199 Q -144 214 -130 214 Q 0 224 130 214 Q 144 214 142 199 C 137 150 127 80 122 14 C 104 6 80 0 62 -4 Q 0 -18 -62 -4 Z","s":1,"f":"cape","o":[{"f":"capeOmbre","d":"M 116 10 C 121 80 129 150 133 240 L 160 240 L 160 10 Z"},{"f":"capeOmbre","d":"M 38 40 C 46 110 52 170 58 240 L 30 240 C 34 170 36 110 38 40 Z"},{"f":"capeOmbre","d":"M -58 48 C -54 118 -48 178 -42 240 L -64 240 C -64 178 -62 118 -58 48 Z"}]},
  {"d":"M -58 4 C -82 -2 -108 -16 -128 -26 Q -142 -33 -143 -20 C -142 -4 -137 10 -132 27 C -110 33 -78 31 -58 24 Q -54 14 -58 4 Z","s":1,"f":"cape","o":[{"f":"capeOmbre","d":"M -150 26 C -110 20 -76 22 -46 18 L -46 50 L -150 50 Z"}]},
  {"d":"M 58 4 C 82 -2 108 -16 128 -26 Q 142 -33 143 -20 C 142 -4 137 10 132 27 C 110 33 78 31 58 24 Q 54 14 58 4 Z","s":1,"f":"cape","o":[{"f":"capeOmbre","d":"M 150 26 C 110 20 76 22 46 18 L 46 50 L 150 50 Z"},{"f":"capeOmbre","d":"M 150 -60 L 134 -60 C 136 -30 132 0 124 30 L 150 30 Z"}]},
  {"d":"M -44 -134 C -61 -144 -77 -152 -87 -150 C -85 -134 -65 -100 -44 -101 C -40 -110 -40 -125 -44 -134 Z","s":1,"f":"peau"},
  {"d":"M 44 -134 C 61 -144 77 -152 87 -150 C 85 -134 65 -100 44 -101 C 40 -110 40 -125 44 -134 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 39 -110 C 61 -108 79 -134 93 -146 L 97 -84 L 39 -84 Z"}]}],
 "visage":{"neutre":[{"d":"M -42 -116 Q -27 -127 -12 -116 Q -27 -108 -42 -116 Z","s":1,"f":"oeil","o":[{"f":"trait","d":"M -33.9 -115.5 A 5.4 5.4 0 1 0 -23.1 -115.5 A 5.4 5.4 0 1 0 -33.9 -115.5 Z"},{"f":"oeil","d":"M -32 -117.6 A 1.5 1.5 0 1 0 -29 -117.6 A 1.5 1.5 0 1 0 -32 -117.6 Z"}]},
  {"d":"M -8 -134 Q -27 -144 -45 -135 Q -27 -136 -8 -128.4 Z","s":0.5,"f":"trait"},
  {"d":"M 12 -116 Q 27 -127 42 -116 Q 27 -108 12 -116 Z","s":1,"f":"oeil","o":[{"f":"trait","d":"M 23.1 -115.5 A 5.4 5.4 0 1 0 33.9 -115.5 A 5.4 5.4 0 1 0 23.1 -115.5 Z"},{"f":"oeil","d":"M 25 -117.6 A 1.5 1.5 0 1 0 28 -117.6 A 1.5 1.5 0 1 0 25 -117.6 Z"}]},
  {"d":"M 8 -134 Q 27 -144 45 -135 Q 27 -136 8 -128.4 Z","s":0.5,"f":"trait"},
  {"d":"M 3 -101 Q 9 -91 5 -87 Q 1 -84 -4 -87","s":0.9},
  {"d":"M -13 -71 L 13 -71","s":1}],
 "sourire":[{"d":"M -42 -114 Q -27 -132 -12 -114 Q -27 -125 -42 -114 Z","s":0.6,"f":"trait"},
  {"d":"M -35 -103 Q -41 -103 -44 -108","s":0.7},
  {"d":"M -8 -134 Q -27 -145 -45 -136.4 Q -27 -137 -8 -128.4 Z","s":0.5,"f":"trait"},
  {"d":"M 12 -114 Q 27 -132 42 -114 Q 27 -125 12 -114 Z","s":0.6,"f":"trait"},
  {"d":"M 35 -103 Q 41 -103 44 -108","s":0.7},
  {"d":"M 8 -134 Q 27 -145 45 -136.4 Q 27 -137 8 -128.4 Z","s":0.5,"f":"trait"},
  {"d":"M 3 -101 Q 9 -91 5 -87 Q 1 -84 -4 -87","s":0.9},
  {"d":"M -17 -76 Q 0 -72 17 -76 Q 0 -57 -17 -76 Z","s":0.8,"f":"trait"}],
 "sourcils_leves":[{"d":"M -42 -116 Q -27 -130 -12 -116 Q -27 -105 -42 -116 Z","s":1,"f":"oeil","o":[{"f":"trait","d":"M -33.9 -115.5 A 5.4 5.4 0 1 0 -23.1 -115.5 A 5.4 5.4 0 1 0 -33.9 -115.5 Z"},{"f":"oeil","d":"M -32 -117.6 A 1.5 1.5 0 1 0 -29 -117.6 A 1.5 1.5 0 1 0 -32 -117.6 Z"}]},
  {"d":"M -8 -145 Q -27 -157 -45 -148.8 Q -27 -149 -8 -139.4 Z","s":0.5,"f":"trait"},
  {"d":"M 12 -116 Q 27 -130 42 -116 Q 27 -105 12 -116 Z","s":1,"f":"oeil","o":[{"f":"trait","d":"M 23.1 -115.5 A 5.4 5.4 0 1 0 33.9 -115.5 A 5.4 5.4 0 1 0 23.1 -115.5 Z"},{"f":"oeil","d":"M 25 -117.6 A 1.5 1.5 0 1 0 28 -117.6 A 1.5 1.5 0 1 0 25 -117.6 Z"}]},
  {"d":"M 8 -145 Q 27 -157 45 -148.8 Q 27 -149 8 -139.4 Z","s":0.5,"f":"trait"},
  {"d":"M -15 -166 Q 0 -171 15 -166","s":0.7},
  {"d":"M 3 -101 Q 9 -91 5 -87 Q 1 -84 -4 -87","s":0.9},
  {"d":"M -8 -72 Q 0 -75 8 -72 Q 0 -63 -8 -72 Z","s":0.6,"f":"trait"}],
 "sourcils_fronces":[{"d":"M -42 -116 Q -27 -120 -12 -116 Q -27 -109 -42 -116 Z","s":1,"f":"oeil","o":[{"f":"trait","d":"M -33.9 -115.5 A 5.4 5.4 0 1 0 -23.1 -115.5 A 5.4 5.4 0 1 0 -33.9 -115.5 Z"},{"f":"oeil","d":"M -32 -117.6 A 1.5 1.5 0 1 0 -29 -117.6 A 1.5 1.5 0 1 0 -32 -117.6 Z"}]},
  {"d":"M -8 -120 Q -27 -138 -45 -132.2 Q -27 -130 -8 -114.4 Z","s":0.5,"f":"trait"},
  {"d":"M 12 -116 Q 27 -120 42 -116 Q 27 -109 12 -116 Z","s":1,"f":"oeil","o":[{"f":"trait","d":"M 23.1 -115.5 A 5.4 5.4 0 1 0 33.9 -115.5 A 5.4 5.4 0 1 0 23.1 -115.5 Z"},{"f":"oeil","d":"M 25 -117.6 A 1.5 1.5 0 1 0 28 -117.6 A 1.5 1.5 0 1 0 25 -117.6 Z"}]},
  {"d":"M 8 -120 Q 27 -138 45 -132.2 Q 27 -130 8 -114.4 Z","s":0.5,"f":"trait"},
  {"d":"M -4 -134 L -3 -123 M 4 -134 L 3 -123","s":0.9},
  {"d":"M 3 -101 Q 9 -91 5 -87 Q 1 -84 -4 -87","s":0.9},
  {"d":"M -13 -68 Q 0 -74 13 -68","s":1}]}},"B":{"face":[{"d":"M -27 -74 C -27 -52 -27 -40 -29 -32 C -32 -20 -40 -8 -56 -3 L -56 14 L 56 14 L 56 -3 C 40 -8 32 -20 29 -32 C 27 -40 27 -52 27 -74 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 15 -90 C 18 -60 19 -44 20 -32 C 23 -22 29 -14 37 -9 L 67 -40 L 67 -90 Z"},{"f":"peauOmbre","d":"M -50 -90 L 50 -90 L 50 -60 Q 0 -30 -50 -60 Z"}]},
  {"d":"M -56 -3 C -74 0 -90 8 -100 26 C -108 64 -110 150 -110 212 Q 0 226 110 212 C 110 150 108 64 100 26 C 90 8 74 0 56 -3 Q 0 11 -56 -3 Z","s":1,"f":"vetement","o":[{"f":"vetementOmbre","d":"M 74 -20 C 84 30 86 100 84 150 L 84 240 L 130 240 L 130 -20 Z"}]},
  {"d":"M -9 -156.2 C -10.3 -182.7 -16.9 -196.5 -29.9 -203.1 C -34.1 -205.2 -37.2 -199 -33.1 -196.9 C -22.3 -191.5 -19.7 -181.3 -19 -155.8 Z","s":1,"f":"peau"},
  {"d":"M 19 -155.8 C 19.7 -181.3 22.3 -191.5 33.1 -196.9 C 37.2 -199 34.1 -205.2 29.9 -203.1 C 16.9 -196.5 10.3 -182.7 9 -156.2 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 18 -260 L 60 -260 L 60 -150 L 26 -150 C 28 -170 30 -190 30 -200 Z"}]},
  {"d":"M -39 -132 C -61 -144 -71 -146.6 -81 -144.6 C -79 -128.6 -65 -100 -39 -100 Z","s":1,"f":"peau"},
  {"d":"M -51 -120 Q -61 -128 -67 -116","s":0.8},
  {"d":"M 39 -132 C 61 -144 71 -146.6 81 -144.6 C 79 -128.6 65 -100 39 -100 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 39 -110 C 61 -108 73 -128.6 87 -140.6 L 91 -84 L 39 -84 Z"}]},
  {"d":"M 51 -120 Q 61 -128 67 -116","s":0.8},
  {"d":"M 0 -186 C 52 -186 50 -134 48 -114 C 46 -86 28 -58 0 -58 C -28 -58 -46 -86 -48 -114 C -50 -134 -52 -186 0 -186 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 22 -196 C 40 -178 46 -150 45 -126 C 44 -108 36 -100 33 -88 C 30 -74 20 -63 2 -60 L 0 -40 L 80 -40 L 80 -196 Z"}]}],
 "dos":[{"d":"M -9 -156.2 C -10.3 -182.7 -16.9 -196.5 -29.9 -203.1 C -34.1 -205.2 -37.2 -199 -33.1 -196.9 C -22.3 -191.5 -19.7 -181.3 -19 -155.8 Z","s":1,"f":"peau"},
  {"d":"M 19 -155.8 C 19.7 -181.3 22.3 -191.5 33.1 -196.9 C 37.2 -199 34.1 -205.2 29.9 -203.1 C 16.9 -196.5 10.3 -182.7 9 -156.2 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 18 -260 L 60 -260 L 60 -150 L 26 -150 C 28 -170 30 -190 30 -200 Z"}]},
  {"d":"M 0 -186 C 52 -186 50 -134 48 -114 C 46 -96 41 -84 36 -76 C 31 -68 28 -58 28 -48 C 28 -36 34 -22 38 -10 Q 48 -6 56 -3 L 56 16 L -56 16 L -56 -3 Q -48 -6 -38 -10 C -34 -22 -28 -36 -28 -48 C -28 -58 -31 -68 -36 -76 C -41 -84 -46 -96 -48 -114 C -50 -134 -52 -186 0 -186 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 22 -196 C 40 -178 47 -150 46 -120 C 45 -100 40 -88 33 -79 C 26 -66 22 -50 22 -36 C 24 -22 34 -12 50 -6 L 90 -6 L 90 -196 Z"},{"f":"peauOmbre","d":"M -40 -82 C -26 -68 18 -66 44 -84 L 44 -60 C 22 -52 -18 -58 -34 -70 Z"}]},
  {"d":"M 0 -60 Q -1.5 -48 0 -34","s":0.8},
  {"d":"M -56 -4 C -74 0 -90 8 -100 26 C -108 64 -110 150 -110 212 Q 0 226 110 212 C 110 150 108 64 100 26 C 90 8 74 0 56 -4 Q 0 -12 -56 -4 Z","s":1,"f":"vetement","o":[{"f":"vetementOmbre","d":"M 74 -20 C 84 30 86 100 84 150 L 84 240 L 130 240 L 130 -20 Z"}]},
  {"d":"M -44 -134 C -61 -144 -71 -146.6 -81 -144.6 C -79 -128.6 -65 -100 -44 -101 C -40 -110 -40 -125 -44 -134 Z","s":1,"f":"peau"},
  {"d":"M 44 -134 C 61 -144 71 -146.6 81 -144.6 C 79 -128.6 65 -100 44 -101 C 40 -110 40 -125 44 -134 Z","s":1,"f":"peau","o":[{"f":"peauOmbre","d":"M 39 -110 C 61 -108 73 -128.6 87 -140.6 L 91 -84 L 39 -84 Z"}]}],
 "visage":{"neutre":[{"d":"M -32 -116 A 5 5 0 1 0 -22 -116 A 5 5 0 1 0 -32 -116 Z","s":0,"f":"trait"},
  {"d":"M -11 -136 Q -27 -142 -42 -136","s":1.7},
  {"d":"M 22 -116 A 5 5 0 1 0 32 -116 A 5 5 0 1 0 22 -116 Z","s":0,"f":"trait"},
  {"d":"M 11 -136 Q 27 -142 42 -136","s":1.7},
  {"d":"M -12 -71 L 12 -71","s":1.2}],
 "sourire":[{"d":"M -34 -114 Q -27 -124 -20 -114","s":1.3},
  {"d":"M -11 -136 Q -27 -143 -42 -137.4","s":1.7},
  {"d":"M 20 -114 Q 27 -124 34 -114","s":1.3},
  {"d":"M 11 -136 Q 27 -143 42 -137.4","s":1.7},
  {"d":"M -15 -74 Q 0 -62 15 -74","s":1.2}],
 "sourcils_leves":[{"d":"M -33.2 -116 A 6.2 6.2 0 1 0 -20.8 -116 A 6.2 6.2 0 1 0 -33.2 -116 Z","s":0,"f":"trait"},
  {"d":"M -11 -145 Q -27 -153 -42 -147.8","s":1.7},
  {"d":"M 20.8 -116 A 6.2 6.2 0 1 0 33.2 -116 A 6.2 6.2 0 1 0 20.8 -116 Z","s":0,"f":"trait"},
  {"d":"M 11 -145 Q 27 -153 42 -147.8","s":1.7},
  {"d":"M -7 -72 Q 0 -75 7 -72 Q 0 -64 -7 -72 Z","s":0.6,"f":"trait"}],
 "sourcils_fronces":[{"d":"M -31.5 -116 A 4.5 4.5 0 1 0 -22.5 -116 A 4.5 4.5 0 1 0 -31.5 -116 Z","s":0,"f":"trait"},
  {"d":"M -11 -122 Q -27 -135 -42 -131.8","s":1.7},
  {"d":"M 22.5 -116 A 4.5 4.5 0 1 0 31.5 -116 A 4.5 4.5 0 1 0 22.5 -116 Z","s":0,"f":"trait"},
  {"d":"M 11 -122 Q 27 -135 42 -131.8","s":1.7},
  {"d":"M -12 -68 Q 0 -74 12 -68","s":1.2}]}}}
/*CHEMINS-FIN*/;

  /* ---------------------------------------------------------------- palette (personnage.md § 4.3, contrastes WCAG)
     main #00a19a contre : peau 2,11:1 (luminance de la peau ≥ 2 × celle de la main, 0,644 contre 0,278 : la main ne se
     fond jamais dans le visage, c'est son contour qui la sépare) ; vêtement 2,65:1 ; ombre du vêtement 3,47:1 ;
     cape 2,84:1. Le violet n'a que 1,98:1 avec l'encre : peu de traits intérieurs sur le vêtement (col, V). La
     ceinture est la seule note chaude. */
  const PALETTE = {
    peau: '#a8dcd6', peauOmbre: '#74c2b9',
    vetement: '#5a3d8c', vetementOmbre: '#44306d',
    cape: '#f4f1ea', capeOmbre: '#d6d0c2',
    ceinture: '#c0392b', ceintureOmbre: '#932b21',   // ombre de la ceinture : même rapport que le vêtement (≈ 0,76)
    trait: '#14201f',
    oeil: '#ffffff',
  };
  const BASES = ['peau', 'vetement', 'cape', 'ceinture'];

  /* ---------------------------------------------------------------- réglages, chacun avec sa mesure */
  const TRAIT_MIN = 1.3;        // px : sous 1,3 px le trait antialiasé se brise en pointillé (vignettes de 160-200 px)
  const TRAIT_HL = 0.028;       // × HLpx : poids du contour de la main (coque ≈ 0,03 HL) ; 4,3 px pour un buste de 600 px
  const HAUT_BUSTE_HL = 3.92;   // hauteur du buste « crâne → bas de la ceinture » (−1,86 → +2,06 HL, § 4.1 et § 4.6 :
                                // 600 px de buste ↔ HL 154 px)
  const SEUIL_REPLI = 160;      // px de buste : en dessous, l'arcade et l'œil en amande fusionnent (§ 4.6) → style B
  // Boîte du dessin, en HL depuis le creux du cou : bouts des antennes −2,10 ; bas du buste +2,20 ; pointes des
  // épaulettes ±1,44 (+ ½ trait). C'est exactement la boîte de la planche (plate.js : PERS_HL = {w 2,9 ; h 4,3 ; cou 2,1}).
  const BOITE_HL = { x0: -1.45, y0: -2.10, x1: 1.45, y1: 2.20 };
  const ACCENT = '#e8590c';     // repères : orange, 3,2:1 sur le vêtement, 2,9:1 sur la cape, lisible sur la peau

  const EXPRESSIONS = ['neutre', 'sourire', 'sourcils_leves', 'sourcils_fronces'];
  const ALIAS = { leves: 'sourcils_leves', fronces: 'sourcils_fronces', levés: 'sourcils_leves', froncés: 'sourcils_fronces' };

  /* ---------------------------------------------------------------- Path2D, construits une fois */
  const CACHE = new Map();
  function chemin(d) {
    let p = CACHE.get(d);
    if (!p) { p = new Path2D(d); CACHE.set(d, p); }
    return p;
  }
  function prechauffe() {
    if (typeof Path2D === 'undefined') return;
    for (const st of Object.keys(CHEMINS)) {
      const S = CHEMINS[st], listes = [S.face, S.dos].concat(Object.values(S.visage));
      for (const L of listes) for (const p of L) { chemin(p.d); if (p.o) for (const q of p.o) chemin(q.d); }
    }
  }

  /* ---------------------------------------------------------------- couleurs */
  function hexRgb(h) {
    const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(h || '').trim());
    if (!m) return null;
    let s = m[1]; if (s.length === 3) s = s.replace(/./g, c => c + c);
    return [0, 2, 4].map(i => parseInt(s.slice(i, i + 2), 16));
  }
  function rgbHex(c) { return '#' + c.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join(''); }
  // Ombre d'une couleur choisie par l'utilisateur : chaque canal c → c · (0,68 + 0,20 · c/255), un « multiplier » doux
  // ajusté sur les trois couples du dossier (peau, vêtement, cape : écart total 46 niveaux sur 9 canaux). Essayé et
  // écarté : clarté HSL × 0,8 — même écart sur le dossier, mais sur une couleur claire la saturation HSL explose
  // (pêche #f2c9a0 → orange vif #e1a160, jaune #ffe8a3 → #f6cf58 : des taches criardes sur la planche de contrôle) ;
  // ici pêche → #d2a881, jaune → #e0c884, l'ombre reste de la même famille.
  function ombreDe(hex) {
    const c = hexRgb(hex); if (!c) return hex;
    return rgbHex(c.map(v => v * (0.68 + 0.20 * v / 255)));
  }
  /* Garde-fou de contraste (personnage.md § 4.3 et § 5.5) : le tronc est la « table » sur laquelle on pose les mains,
     donc vêtement et cape ≥ 2,6:1 contre la main (WCAG), et la luminance de la peau ≥ 2 × celle de la main (sinon une
     main posée au menton se fond dans le visage, seul son contour la sépare). Mesuré (relecture adverse) : les couleurs
     par défaut de la planche, peau #9fd8a8 et vêtement #5e4b8b, donnent 1,96:1 et 2,30:1, et l'ombre de peau dérivée
     #80b788 tombe à 1,38:1. Une couleur hors règle est poussée vers le noir ou vers le blanc (mélange sRGB, par
     dichotomie) juste assez pour passer la règle : elle garde sa teinte. La palette du dossier passe telle quelle
     (2,65 / 2,84 / 0,644 ≥ 0,556). couleurs.garde === false coupe le garde-fou. */
  const MAIN = '#00a19a';            // vert INJS de la main
  const CONTRASTE_TRONC = 2.6;       // vêtement, cape contre la main
  const PEAU_LUM_X = 2;              // luminance peau ≥ 2 × luminance main
  function lumRel(c) {
    const l = c.map(v => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2];
  }
  function contraste(a, b) { const x = lumRel(a), y = lumRel(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
  // mélange ARRONDI aux 8 bits : on teste la couleur qui sera réellement peinte (sans l'arrondi, la couleur trouvée
  // à 2,600 retombait à 2,59 une fois écrite en hexadécimal)
  const melange = (c, d, t) => c.map((v, i) => Math.round(v + (d[i] - v) * t));
  // plus petit t ∈ [0, 1] tel que ok(melange(c, d, t)) (ok monotone en t le long du mélange)
  function pousse(c, d, ok) {
    if (ok(c)) return { t: 0, c };
    if (!ok(d)) return null;
    let a = 0, b = 1;
    for (let i = 0; i < 24; i++) { const m = (a + b) / 2; if (ok(melange(c, d, m))) b = m; else a = m; }
    return { t: b, c: melange(c, d, b) };
  }
  function garde(P, main) {
    const corr = [];
    const m = hexRgb(main) || hexRgb(MAIN), lm = lumRel(m);
    for (const k of ['vetement', 'cape']) {
      const c = hexRgb(P[k]), ok = x => contraste(x, m) >= CONTRASTE_TRONC + 0.005;   // 0,005 : marge d'arrondi
      if (ok(c)) continue;
      const n = pousse(c, [0, 0, 0], ok), b = pousse(c, [255, 255, 255], ok);
      const r = !n ? b : !b ? n : (n.t <= b.t ? n : b);   // le plus petit déplacement
      if (r) { corr.push({ couleur: k, avant: P[k], apres: rgbHex(r.c), contraste: +contraste(c, m).toFixed(2) }); P[k] = rgbHex(r.c); }
    }
    const cp = hexRgb(P.peau), okp = x => lumRel(x) >= PEAU_LUM_X * lm + 0.002;
    if (!okp(cp)) {
      const r = pousse(cp, [255, 255, 255], okp);
      if (r) { corr.push({ couleur: 'peau', avant: P.peau, apres: rgbHex(r.c), luminance: +lumRel(cp).toFixed(3) }); P.peau = rgbHex(r.c); }
    }
    return corr;
  }

  // couleurs : {peau, vetement, cape, ceinture, trait (ou encre), oeil, peauOmbre…, ombres:false, main, garde:false}
  // (plate.js passe {peau, vetement, cape, trait}). Une couleur illisible est ignorée, pas propagée.
  // La palette rendue porte la liste des corrections du garde-fou dans P._corrections (vide si rien n'a bougé).
  function palette(cc) {
    const P = Object.assign({}, PALETTE);
    let corr = [];
    if (!cc || typeof cc !== 'object') { Object.defineProperty(P, '_corrections', { value: corr }); return P; }
    if (cc.encre && !cc.trait) cc = Object.assign({}, cc, { trait: cc.encre });
    for (const k of Object.keys(PALETTE)) {
      if (cc[k] == null || !hexRgb(cc[k])) continue;
      P[k] = rgbHex(hexRgb(cc[k]));
    }
    if (cc.garde !== false) corr = garde(P, cc.main);
    for (const k of BASES) {          // base changée, ombre non donnée → ombre dérivée de la nouvelle base
      const kO = k + 'Ombre';
      if (P[k] !== PALETTE[k] && !(cc[kO] && hexRgb(cc[kO]))) P[kO] = ombreDe(P[k]);
    }
    if (cc.ombres === false) for (const k of BASES) P[k + 'Ombre'] = P[k];
    Object.defineProperty(P, '_corrections', { value: corr });   // non énumérable : P reste une table de couleurs
    return P;
  }

  /* ---------------------------------------------------------------- dessin */
  function normExpr(e) {
    e = ALIAS[e] || e;
    return EXPRESSIONS.indexOf(e) >= 0 ? e : 'neutre';
  }
  function styleEffectif(HLpx, style) {
    const st = style === 'B' ? 'B' : 'A';
    return st === 'A' && HLpx * HAUT_BUSTE_HL < SEUIL_REPLI ? 'B' : st;
  }
  function largeurTrait(HLpx) { return Math.max(TRAIT_MIN, TRAIT_HL * HLpx); }

  // W = trait principal à l'écran (px), k = pixels par unité. Traits secondaires (s < 1 : sourcils 0,5, pli du front
  // 0,7, pli d'oreille 0,8…) : W × s, mais jamais sous TRAIT_MIN à l'écran — relecture adverse : à 200 px de buste
  // (W = 1,43 px) le contour des sourcils tombait à 0,71 px, le pli du front à 1,0 px, en pointillé.
  function peindre(ctx, p, P, W, k) {
    const ch = chemin(p.d);
    if (p.f) {
      ctx.fillStyle = P[p.f];
      ctx.fill(ch);
      if (p.o) {
        ctx.save();
        ctx.clip(ch);
        for (const q of p.o) {
          ctx.fillStyle = P[q.f];
          ctx.fill(chemin(q.d));
        }
        ctx.restore();
      }
    }
    if (p.s > 0) {
      ctx.lineWidth = Math.max(TRAIT_MIN, W * p.s) / k;
      ctx.stroke(ch);
    }
  }

  // HLpx invalide (absent, ≤ 0, NaN) : on ne dessine RIEN et on rend null (relecture adverse : un repli silencieux sur
  // HLpx = 100 dessinait un buste de 392 px là où l'appelant croyait en demander un autre).
  // Le repli vers B suit les pixels d'ÉCRAN (c'est là que l'arcade et l'œil fusionnent). Une planche dont l'aperçu est
  // zoomé à 17 % mais l'export à ×2 peut passer o.HLrepli = HL de l'export (l'aperçu montre alors le style exporté),
  // ou repli:false pour forcer le style demandé.
  function draw(ctx, o) {
    o = o || {};
    if (!ctx || !(isFinite(+o.HLpx) && +o.HLpx > 0)) return null;
    const HLpx = +o.HLpx;
    const x = isFinite(+o.x) ? +o.x : 0, y = isFinite(+o.y) ? +o.y : 0;
    const vue = o.vue === 'dos' ? 'dos' : 'face';
    const expression = normExpr(o.expression);
    const demande = o.style === 'B' ? 'B' : 'A';
    const HLrepli = isFinite(+o.HLrepli) && +o.HLrepli > 0 ? +o.HLrepli : HLpx;
    const style = o.repli === false ? demande : styleEffectif(HLrepli, demande);   // repli:false = forcer
    const P = palette(o.couleurs);
    const W = largeurTrait(HLpx);
    const k = HLpx / 100;
    const S = CHEMINS[style];
    const pieces = vue === 'face' ? S.face.concat(S.visage[expression]) : S.dos;

    ctx.save();
    ctx.translate(x, y);
    ctx.scale(k, k);
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.strokeStyle = P.trait;
    ctx.setLineDash([]);
    for (const p of pieces) peindre(ctx, p, P, W, k);
    ctx.restore();

    if (o.reperes) dessineReperes(ctx, x, y, HLpx, { vue, style, expression, etiquettes: o.reperes.etiquettes !== false, couleur: (o.reperes && o.reperes.couleur) || ACCENT, trait: P.trait });
    return { style, vue, expression, repli: style !== demande, trait: W, HLpx, boite: boite(HLpx), corrections: P._corrections };
  }

  /* ---------------------------------------------------------------- ancres (lieux du corps) */
  // Positions en HL depuis le creux du cou (personnage.md § 4.1 ; ancres de la v1 gardées : menton −0,58, taille +1,92,
  // ancre des mains +1,00 = (épaules + taille)/2 → une main de 1 HL y occupe +0,50 … +1,50).
  const LIEUX = {
    sommet: [0, -1.86], front: [0, -1.50], yeux: [0, -1.16], nez: [0, -0.86], bouche: [0, -0.71], menton: [0, -0.58],
    cou: [0, -0.30], nuque: [0, -0.45], creuxCou: [0, 0], poitrine: [0, 1.00], mains: [0, 1.00], taille: [0, 1.92],
  };
  // épaule (lieu du signe) : ±1,15 / +0,10 HL, la valeur du dossier (§ 4.1), la MÊME en A et en B. Relecture adverse :
  // l'ancienne ancre suivait la surface du dessin, (1,15 ; −0,20) en A et (0,90 ; +0,16) en B, donc une main posée
  // sur « épaule » sautait de 0,36 HL en y et 0,25 en x au repli (dézoom sous 160 px de buste). En A ce point est sur
  // la face de l'épaulette (bord haut −0,20, bas +0,31 à x 1,15). Le REPÈRE dessiné, lui, suit le dessin : en B
  // l'épaule ronde ne va qu'à ±0,96 à cette hauteur, la pastille se pose sur son arrondi (0,90 ; +0,16) — exposé à
  // part (epauleRepereG/D), pour ne pas déplacer les mains.
  const EPAULE = [1.15, 0.10];
  const EPAULE_REPERE = { A: [1.15, 0.10], B: [0.90, 0.16] };
  const NEUTRE = { x: -0.75, y: 0.60, w: 1.50, h: 0.80 };   // espace neutre devant le tronc, +0,60 … +1,40 (§ 4.1)

  const valide = h => isFinite(+h) && +h > 0;
  function boite(HLpx) {
    if (!valide(HLpx)) return null;
    const u = +HLpx;
    return { x: BOITE_HL.x0 * u, y: BOITE_HL.y0 * u, w: (BOITE_HL.x1 - BOITE_HL.x0) * u, h: (BOITE_HL.y1 - BOITE_HL.y0) * u };
  }

  function ancres(HLpx, opt) {
    if (!valide(HLpx)) return null;
    const u = +HLpx;
    opt = typeof opt === 'string' ? { vue: opt } : (opt || {});
    const st = opt.repli === false ? (opt.style === 'B' ? 'B' : 'A') : styleEffectif(valide(opt.HLrepli) ? +opt.HLrepli : u, opt.style);
    const dos = opt.vue === 'dos';
    const R = { unite: 'px, depuis le creux du cou (x vers la droite de l\'image, y vers le bas)', HLpx: u, style: st };
    for (const k of Object.keys(LIEUX)) R[k] = { x: LIEUX[k][0] * u, y: LIEUX[k][1] * u };
    const e = EPAULE, er = EPAULE_REPERE[st];
    R.epauleG = { x: -e[0] * u, y: e[1] * u };            // à GAUCHE de l'image
    R.epauleD = { x: e[0] * u, y: e[1] * u };             // à DROITE de l'image
    R.epauleRepereG = { x: -er[0] * u, y: er[1] * u };    // où la pastille se pose sur le dessin du style effectif
    R.epauleRepereD = { x: er[0] * u, y: er[1] * u };
    // épaule droite DU PERSONNAGE : à gauche de l'image vu de face, à droite vu de dos
    R.epauleDroitePersonnage = dos ? R.epauleD : R.epauleG;
    R.epauleGauchePersonnage = dos ? R.epauleG : R.epauleD;
    R.epaules = [R.epauleG, R.epauleD];
    R.espaceNeutre = { x: NEUTRE.x * u, y: NEUTRE.y * u, w: NEUTRE.w * u, h: NEUTRE.h * u };
    R.boite = boite(u);
    return R;
  }

  /* ---------------------------------------------------------------- repères d'emplacement (option) */
  function dessineReperes(ctx, x, y, HLpx, o) {
    const A = ancres(HLpx, { vue: o.vue, style: o.style, repli: false }), W = largeurTrait(HLpx);
    // pastille : 0,045 HL, jamais sous 3,5 px… sauf sur les vignettes (HL < 55 px, buste < 215 px) où une pastille de
    // 3,5 px (0,086 HL à 160 px de buste) couvrait la bouche et le bout des sourcils levés (relecture adverse) :
    // là elle descend à 2,5 px (0,06 HL), le liseré blanc la garde visible.
    const r = HLpx >= 55 ? Math.max(3.5, 0.045 * HLpx) : Math.max(2.5, 0.06 * HLpx);
    const fs = Math.max(11, Math.min(22, 0.11 * HLpx));    // étiquettes : 0,11 HL, entre 11 et 22 px
    const avecTexte = o.etiquettes && HLpx >= 55;           // sous 55 px de main (buste ≈ 215 px), le texte couvrirait le visage
    ctx.save();
    ctx.translate(x, y);
    // espace neutre : un cadre arrondi en pointillé devant le tronc
    const N = A.espaceNeutre, rr = 0.12 * HLpx;
    ctx.beginPath();
    ctx.moveTo(N.x + rr, N.y); ctx.arcTo(N.x + N.w, N.y, N.x + N.w, N.y + N.h, rr); ctx.arcTo(N.x + N.w, N.y + N.h, N.x, N.y + N.h, rr);
    ctx.arcTo(N.x, N.y + N.h, N.x, N.y, rr); ctx.arcTo(N.x, N.y, N.x + N.w, N.y, rr); ctx.closePath();
    ctx.setLineDash([W * 2.2, W * 1.8]);
    ctx.lineWidth = Math.max(1.5, W * 0.8);
    ctx.strokeStyle = '#ffffff'; ctx.lineWidth += 2; ctx.stroke();          // liseré blanc : lisible sur le violet
    ctx.strokeStyle = o.couleur; ctx.lineWidth -= 2; ctx.stroke();
    ctx.setLineDash([]);
    // menton : la pastille se pose SOUS le bord du menton (centre ½ rayon plus bas), pas sur la bouche.
    const menton = { x: A.menton.x, y: A.menton.y + 0.5 * r };
    // de dos il n'y a ni front ni menton à montrer (ils s'affichaient sur l'arrière du crâne) : « nuque » à la place,
    // et pas de « poitrine » (cachée par le dos) ; épaules et taille restent, elles se voient des deux côtés.
    const pts = o.vue === 'dos'
      ? [['nuque', A.nuque, 1], ['épaule', A.epauleRepereG, -1], ['épaule', A.epauleRepereD, 1], ['taille', A.taille, 1]]
      : [['front', A.front, 1], ['menton', menton, 1], ['épaule', A.epauleRepereG, -1], ['épaule', A.epauleRepereD, 1],
         ['poitrine', A.poitrine, 1], ['taille', A.taille, 1]];
    for (const [, p] of pts) {
      ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = '#ffffff'; ctx.fill();
      ctx.lineWidth = Math.max(1, W * 0.6); ctx.strokeStyle = o.trait; ctx.stroke();
      ctx.beginPath(); ctx.arc(p.x, p.y, r * 0.45, 0, Math.PI * 2); ctx.fillStyle = o.couleur; ctx.fill();
    }
    if (avecTexte) {
      ctx.font = `600 ${fs}px "Atkinson Hyperlegible", system-ui, sans-serif`;
      ctx.textBaseline = 'middle';
      ctx.lineJoin = 'round';
      // les étiquettes restent DANS la boîte du dessin (±1,45 HL) : l'« épaule » de gauche commençait à 10 px du bord
      // du canvas à 600 px de buste (relecture adverse), la planche la rognait.
      const halo = Math.max(3, fs * 0.28) / 2 + 1;           // le liseré blanc déborde du texte de ½ trait
      const bx0 = BOITE_HL.x0 * HLpx + halo, bx1 = BOITE_HL.x1 * HLpx - halo;
      const lab = (t, px, py, al) => {
        const w = ctx.measureText(t).width;
        if (al === 'right') px = Math.max(px, bx0 + w); else px = Math.min(px, bx1 - w);
        ctx.textAlign = al;
        ctx.lineWidth = Math.max(3, fs * 0.28); ctx.strokeStyle = 'rgba(255,255,255,.92)'; ctx.strokeText(t, px, py);
        ctx.fillStyle = o.trait; ctx.fillText(t, px, py);
      };
      // front, menton, nuque, poitrine, taille : étiquette à droite, au-delà de la pastille ; épaules : au-dessus, vers
      // l'extérieur
      for (const [t, p, sg] of pts) {
        if (t === 'épaule') lab(t, p.x + sg * r * 0.2, p.y - r - fs * 0.75, sg < 0 ? 'right' : 'left');
        else lab(t, p.x + r * 1.7, p.y, 'left');
      }
      lab('espace neutre', N.x + N.w - rr * 0.6, N.y + N.h - fs * 0.85, 'right');
    }
    ctx.restore();
  }

  prechauffe();

  window.AtelierPersonnage = {
    version: 2,
    draw, ancres, boite, styleEffectif, largeurTrait, palette, ombreDe, contraste: (a, b) => contraste(hexRgb(a), hexRgb(b)),
    MAIN, CONTRASTE_TRONC, PEAU_LUM_X,
    EXPRESSIONS: EXPRESSIONS.slice(),
    PALETTE: Object.assign({}, PALETTE),
    BOITE_HL: Object.assign({}, BOITE_HL),
    HAUT_BUSTE_HL, SEUIL_REPLI,
    _chemins: CHEMINS, _cache: CACHE,
  };
})();
