# Journal du chantier M3 — l'éditeur de planche

## 19 octobre 2026 — reprise (« Réessayer »)
État trouvé sur disque : plate.js (968 lignes denses, 111 Ko), plate.css, index.html, fonts.js (polices b64),
stub_hand.js, tests plate_scenario.py (tous verts) et plate_projet.py (5 échecs : éclater depuis les clés,
sonde A3 ×3, thème du gabarit, miroir 3D gauche/droite du bouchon, ombre).

### Corrections de la reprise
- Flèches des étapes v1 : dans la v1 la flèche du segment i → i+1 est portée par la clé i (`segFl(i)`,
  script.js l. 1222) ; le test supposait la clé i+1. Conversion complète (style, sens, aller-retour, couleur),
  « arc » de la v1 = « courbe » ici. Test corrigé.
- Sonde d'export : `echelleExport(k)` (plus grande échelle ≤ k que le navigateur peint). Mesuré : A3 ×3 =
  157 Mpx passe dans Chromium (aire max 268 Mpx), 16 384² ×2 → ×1, 12 000 × 9 000 ×3 → ×1.
- Thème : #b3261e mêlé à 80 % de blanc = (240, 212, 210) = #f0d4d2 (le test attendait d3, faux).
- Bouchon de main : l'ombre de la paume suivait le miroir (bord q[2]-q[3]) ; elle prend maintenant le bord le
  plus à droite À L'ÉCRAN. Mesuré : pixels au ton d'ombre à droite du centre D 6 123 / 2 307, G 6 843 / 1 430.
- Ctrl+V : la touche était annulée au keydown, donc Chrome n'émettait pas « paste » ; corrigé (Ctrl+C / Ctrl+V au
  clavier : copie centrée sous la souris à 0 px près).
- Texte : alignement vertical dans la boîte (`valign` haut / milieu / bas ; bannière au milieu, colonne de
  définitions en haut). Mesuré : 1re encre à y = 24 / 120 / 215 dans une bannière de 300 px.
- PNG : projet embarqué avec ses images s'il pèse < 2 Mo, sans elles au-delà (message).
- Barre haute : un message long passait sur deux lignes et décalait le plateau (~30 px) ; une ligne réservée.
- Nom de fichier : « Cent / 100 ? » → « Cent-100 » (plus de tiret final).
- index.html charge ../personnage/personnage.js s'il existe (M4), sinon le bouchon.
- Nouveau test tests/plate_edition.py (poignées, guides, ordre, verrou, Ctrl+C/V, coller la pose, pile de 100,
  EXIF, 4 096 px, HEIC, dépôt, fonds, texte, WebP, gabarits A–E, référent).
- Gabarits : marge intérieure des textes ∝ corps (0,35 × corps, ≥ 12 px) — le « cent » gras de 178 px de la fiche
  A4 collait au bord de sa bannière ; colonne de définitions (A) et cases d'étapes (D) teintées #f3f6f5 (le blanc
  90 % disparaissait sur une planche blanche). Planche de contrôle tests/out/plate_gabarits.png.
- Fond image qui couvre : la couleur de dessous n'est plus peinte, et l'origine de la planche est calée sur un pixel
  physique (filet rouge vu au bord haut à l'écran ; mesuré après : 3 rangées du bord = (255,255,255)).

## 19 octobre 2026 — correction après relecture adverse (16 défauts : 1 bloquant, 8 importants, 7 mineurs)
Tous corrigés, chacun rejoué par tests/plate_correctifs.py (34 contrôles, mesure « avant » rappelée dans le message).

Bloquant
- **Main affichée ≠ main exportée.** Le cache arrondissait w et h au multiple de 64 chacun de son côté, puis l'image
  était étirée dans la boîte. Maintenant : un seul facteur d'échelle, cache dessiné « contenu » à ses propres
  proportions. Mesuré (boîte du contour) : écran dpr 1 0,677 / dpr 2 0,687 / zoom 150 % 0,685 contre export 0,686
  (écart 1,2 / 0,2 / 0,1 %, avant 0,616 et 0,652). Planche tests/out/plate_correctifs_01_aspect.png.

Importants
- **Latéralité.** Le trièdre du contrat M1 (doigts +Y, paume +Z vers la caméra, pouce +X) est une main DROITE ; M1
  l'a d'ailleurs livrée comme droite (hand/JOURNAL.md). Le bouchon disait l'inverse : `m` inversé dans stub_hand.js.
  Mesuré : main D vue paume, pouce à droite (204 px à droite du poignet contre 84 à gauche), comme paume.jpg ; G
  miroir ; gabarit A : D à gauche de l'image, pouces vers le milieu. Critère de plate_projet § 6 corrigé.
  À SIGNALER à l'orchestrateur : PLAN.md (contrat M1) écrit encore « main GAUCHE » pour hand_v2.glb.
- **Brouillons.** Un brouillon PAR planche (clé = id du document, nouveau champ `id` du JSON v9, validé), 3 gardés.
  « Nouveau » est annulable (Ctrl+Z) et écrit d'abord le brouillon de la planche quittée ; gabarit, Ouvrir, PNG
  déposé, bibliothèque, Reprendre font de même. Onglet Projet : liste « Reprendre » des autres planches. Mesuré :
  Nouveau + une main + 5,6 s → brouillons [1, 2] objets (avant : [1]) ; au démarrage, une action avant
  « Reprendre » ne touche plus celui de la veille ; 4 planches → 3 brouillons.
- **Collage d'un JSON « atelier » du presse-papiers système** : chaque élément passe par valideElement, ids neufs,
  pixels des images validés (data:image/png|jpeg|webp|gif) ; la copie emporte les images (< 2 Mo). La reconnaissance
  accepte aussi un JSON indenté. Poses filtrées (`vPose` : nombres finis bornés à ±360 sur deux niveaux).
  Mesuré : 5 collages forgés → 0 objet, 0 erreur JS (avant 2 pageerror, main x NaN) ; 3 collages sales mais
  valides → 3 objets, coordonnées finies.
- **Éclater en étapes** : rangée dans la planche (marges 4 %), réduite si besoin. Depuis x = 1 500 : 4 étapes
  x 384..1 877, 6 étapes x 43..1 877 (avant jusqu'à 2 991).
- **Gabarit sur planche pleine** : confirmation (« Ctrl+Z ramène la planche actuelle »), message Ctrl+Z après pose.
- **Flèches** : `ajusteBoiteFleche` — la boîte suit le tracé (A et B fixes sur la planche), à la création, au
  changement de tracé / courbure / épaisseur, au relâchement d'un redimensionnement. Poignées rondes aux extrémités
  A / B (comme la v1). Mesuré : débordement 0 px pour les 6 styles (avant : demi-cercle 138 px hors boîte) ;
  B tiré de (120, 60) px → (120,0 ; 60,0), A immobile. Planche plate_correctifs_07_fleches.png.
- **Téléphone** : `html,body{height:auto;overflow:auto}` sous 900 px. Mesuré 390 × 844 : scrollY 216 après la molette
  (avant 0), « Exporter le projet (.json) » atteint. Le plateau garde le doigt et la molette pour la vue
  (touch-action:none) : on fait défiler par l'en-tête ou le panneau.
- **Cache des mains (outil.md § 4.4)** : clé = identité (côté, pose, orientation, style), plusieurs tailles ; rendu à
  1,2 × la taille affichée ; servi dans [÷1,8 ; ×1,05] au repos, [÷1,8 ; ×1,5] pendant un geste ; plafond 2 048 px
  à l'écran ; jamais de rendu dans drawDoc : les mains « sales » sont rendues dans peint(), une par image pendant un
  geste (glisser, marionnette, zoom à la molette), toutes au repos ; test de collision sur le cache affiché ; LRU
  à la mémoire (150 Mo). Mesuré (gabarit D, dpr 2) : survol 0 rendu (avant 1) ; zoom 0,49 → 1,21 : 1 rendu pendant
  le geste, 2 en tout (avant 6) ; coin ×1,75 : 0 pendant, 1 en tout (avant 5) ; 16 mains, zooms 8/0,5/8 : 15 Mo.

Mineurs
- Fond : champ fichier à lui (#fichierFond) ; annuler le dialogue ne laisse plus de drapeau armé.
- PNG de l'atelier déposé : « OK : rouvrir la planche / Annuler : insérer comme image ».
- A4 / A3 : ×2 et ×3 désactivés (300 dpi à ×1), export borné à ×1 ; une seule sonde par échelle.
- JSON v9 : ids en double renouvelés, descripteur de thème validé (`vTheme`).
- Zone de saisie du texte : surlignages décalés / coupés par préfixe-suffixe communs (`decaleSurlignages`).
- Gabarits : option texte `titre` (1re ligne en gras, aussi dans l'éditeur) pour « Définition » ; invites (`invite`)
  à 55 % à l'écran, jamais exportées tant qu'elles ne sont pas modifiées, sélectionnées entières à l'édition ;
  cadres photo (`cadre`) dans C et E : l'image déposée s'y cale au-dessus de la légende.
- Personnage : boîte lue chez AtelierPersonnage.boite (M4 est sur disque et chargé) + 2 % haut et bas (antennes
  à −2,115 HL pour une boîte à −2,10) ; PERS_HL en repli. Mesuré : encre [646,75 → 1273,1014] dans la boîte
  [645,60 → 1275,1032].

## État final (19 octobre 2026)
Tests (Chromium headless, 0 erreur JS) : plate_scenario.py 33 contrôles, plate_projet.py 27, plate_edition.py 35,
plate_correctifs.py 34 — tous verts. Captures dans v2/tests/out/plate_*.png.

## Ce qui reste (hors de ce chantier ou à brancher plus tard)
- Le vrai moteur M2 (engine.js) remplacera stub_hand.js : plate.js n'appelle que render / bounds / puppet /
  presets / mirror (+ mirrorOrientation facultatif, repli [x,−y,−z,w]).
- Le personnage M4 (../personnage/personnage.js) est sur disque et chargé ; sa boîte vient de AtelierPersonnage.boite.
- Images de la bibliothèque db : gardées en data: dans la ligne (retirées au-delà de 900 Ko, message) ; le
  passage par la capability `assets` (outil.md § 7.2) est à faire à l'intégration, quand l'artifact la déclarera.
- PLAN.md (contrat M1) dit encore « hand_v2.glb : main GAUCHE » alors que ses axes (et le GLB livré) sont ceux d'une
  main DROITE : à corriger par l'orchestrateur ; le moteur M2 doit rendre « D » sans miroir.
- Chemins claude.ai (db, downloads) non testables ici.
- Non mesuré ici : Safari (HEIC décodable, limite 16,8 Mpx annoncée dans le dialogue d'export).

## Intégration du moteur M2 (19 octobre, correction après relecture adverse du chantier M2)
Retouches minimales faites par le chantier M2 pour que la marionnette soit EN PLACE (contrat M2 → M3) :
- `placeOverlays` : #puppet posé exactement sur le cadre de l'objet (`transformCSS(e)`, e.w·zoom × e.h·zoom) ; en mode
  marionnette la barre contextuelle (#ctx) reste visible au-dessus de l'objet et accueille la barre du moteur
  (`S.puppetBarre`, vues / poignet / inclinaison / pronation / arc) ;
- `DESSINE.main` : la main en marionnette n'est pas peinte (le canevas 3D la montre) — `drawDoc(…, {puppetId})` ;
- `marionnette()` : puppet(host, e, onChange, {onFin, barreHote, boutonFin:false}) ; l'orientation rendue par
  onChange est recopiée ;
- plate.css #puppet : ni marge, ni bordure, ni fond, overflow visible (le cadre en pointillé seul) ;
- défauts du style de la main alignés sur le moteur : largeurTrait 0,8 (% de HL), ongle #96dcd6 (PLAN.md tranché).
Mesuré (v2/tests/engine_integration_planche.py) : cadre du canevas = cadre de l'objet à 0 px près, barre visible,
curseur pronation appliqué, Échap termine, 0 erreur JS.

## Retouches du chantier M5 (intégration, 19 octobre) — détail et mesures dans v2/integration/JOURNAL.md
- Cache des mains au vrai coût du moteur : estimation ms/Mpx (départ 400), RENDU_LENT = 50 ms (jamais pendant un geste,
  une main par image au repos), aperçu d'abord pour une main sans image (entrée `apercu`, jamais « juste », jetée quand
  l'image juste arrive), ss 1 à l'écran pour dpr ≥ 1,75. `__plate.salesRestantes()`, `__plate.coutMpx()`.
- `convertitV1` : vue caméra v1 → orientation (vueV1 / qV1) ; poses par `AtelierHand.depuisV1`.
- Bibliothèque : collection « configurations » de la v1 en lecture seule (#libV1Bloc dans index.html).
- Configurations rangées par famille (details.famille), `data-preset` sur chaque bouton.
- Gabarit F « Étapes avec référent » (un référent par étape, expression réglable).
Non-régression : plate_scenario, plate_projet, plate_edition, plate_correctifs verts après ces retouches.
