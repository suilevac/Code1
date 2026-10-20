# Chantier M4 — le personnage (journal)

## Livré
- `personnage.js` : module sans dépendance, `window.AtelierPersonnage` = {draw, ancres, boite, styleEffectif,
  largeurTrait, palette, ombreDe, EXPRESSIONS, PALETTE, BOITE_HL, HAUT_BUSTE_HL, SEUIL_REPLI}. Chemins SVG embarqués
  (1 HL = 100 u., creux du cou = (0,0)), convertis en Path2D au chargement (91 chemins en cache), trait constant à
  l'écran max(1,3 ; 0,028·HLpx). Ombres franches découpées par leur pièce (clip) et peintes AVANT le trait : le contour
  garde toute sa largeur côté ombre. `draw` accepte `repli:false` (forcer A, pour les essais).
- `gen_chemins.py` : générateur des chemins (réécrit le bloc /*CHEMINS-DEBUT*/…/*CHEMINS-FIN*/ de personnage.js).
- `test.html` : page d'essai interactive + `scene(spec)` utilisée par `v2/tests/personnage.py`.
- `v2/tests/personnage.py` → `v2/tests/out/personnage_*.png` (11 images, dont `personnage_dans_planche.png`, étape 9).

## Ce qui a changé par rapport aux SVG du dossier (chaque fois vu sur la planche)
- Cou : 0,30 HL et s'évase en trapèzes jusqu'à ±0,62 HL (col large) — à 0,25 HL tombant droit dans un col de ±0,34
  il se lisait « poteau » / « girafe ».
- Épaulettes : pointe relevée à −0,31 HL (dossier −0,22) ; essai à −0,40 rejeté (deux ailes dressées).
- Ombre de joue (v2.1) : croissant mince sur le crâne, 12 u. sous la pommette, le long de la mâchoire.
- Antennes : bords décalés le long de la normale, bout en demi-cercle dans l'axe, dessinées derrière le crâne
  (l'ancien bout « en chapeau » faisait une boule recourbée) ; base 12 u., bout 8 u.
- Oreilles derrière la tête (plus de trait vertical sur la tempe) ; ombre sur le bas de l'oreille droite.
- Nez en crochet côté ombre (l'arc du dossier + bouche droite = « deux bouches ») ; pli du front unique (sourcils
  levés) ; bouche entrouverte = petite ouverture sombre ; sourire A = œil en croissant ; sourire B = yeux fermés en arc
  (points + trait dessous lus « ☹ » à 200 px) ; iris et reflet découpés par l'œil.
- Bas du buste à +2,2 HL, ourlet et ceinture en arc léger (volume) ; dessin dans la boîte de plate.js (2,9 × 4,3 HL).
- Vue dos : nappe de cape pleine, deux plis, nuque, antennes, oreilles sans pli, pas de visage. Ombre à droite aussi.

## Mesures (dernier passage, TOUT EST BON)
- trait 600 px : 4,29 px voulu, 4,31 px mesuré sur l'image ; 200 px : 1,43 px.
- ombre franche : 92,1 % des pixels d'ombre à droite de l'axe (le reste : dessous des épaulettes et du menton).
- expressions, pixels du visage ≠ neutre : 600 px A 8,7 / 18,6 / 19,7 % ; 200 px A 10,5 / 23,5 / 22,3 %, B 8,1 / 14,9 / 15,5 %.
- silhouette face/dos (IoU) : A 0,992, B 0,998 ; zone des yeux de dos : 0 px blanc, 0 px d'encre.
- repli : buste 160 px → A, 150 px → B (HAUT_BUSTE 3,92 HL, seuil HL < 40,8 px).
- boîte : A x ±1,445, y −2,115 … +2,205 HL (planche : ±1,45 ; −2,1 … +2,2).
- contrastes main #00a19a : peau 2,11, vêtement 2,65, ombre vêtement 3,47, cape 2,84 ; peau/main en luminance 0,644/0,278.
- dessin : 0,1 à 1,2 ms par personnage à 600 px.

## Reste / à savoir pour l'intégration
- plate.js passe `couleurs.peau = #9fd8a8` par défaut (pas le #a8dcd6 du dossier) : choix de M3, rendu vérifié
  (`personnage_couleurs.png`, colonne du milieu) ; à aligner sur le dossier si l'orchestrateur le souhaite.
- Planche avec main : la main est une capture v1 réduite (×0,31), son contour y est plus fin que celui de la vraie
  main du moteur M2 (coque ≈ 0,03 HL) ; refaire le contrôle avec engine.js quand il existe.
- Le repli remplace aussi la cape par la tunique B (contrat) ; si l'utilisateur regrette la cape en vignette, piste :
  garder le corps A et ne prendre que le visage B sous 160 px.
- Fonction des sourcils levés / froncés en LSF : à faire valider par l'utilisateur (personnage.md § 6).

## Correction après relecture adverse (passe 2)

Relevé complet : `python3 run_rendu.py v2/tests/personnage.py` → « TOUT EST BON » (11 images, dont
`personnage_dans_planche.png`, désormais produite par le script). Sauvegarde de la passe 1 :
`scratchpad/m4c/` (gen_chemins.avant.py, personnage.avant.js, out_avant/).

Défauts importants, tous corrigés :
1. **Vue de dos = visage vide.** Nouvelle pièce `tete_nuque` : crâne + nuque d'UNE pièce, le crâne descend à l'occiput
   (±0,36 à −0,76) et rentre dans la nuque sans trait de séparation (plus de menton) ; trapèzes dès −0,40 ; ombre
   portée de l'occiput (croissant 4 → 11 u.) au lieu de l'ombre « sous le menton » ; sillon de la nuque (un trait court) ;
   oreilles peintes APRÈS le crâne, base courbe posée 5 u. dedans (essai base droite à 9 u. : coin carré, rejeté) ;
   col de cape relevé à −0,10 au milieu. Mesures : encre en travers du cou à ±0,15 HL entre −0,95 et −0,35 HL :
   0 px de dos (A et B) contre 9 et 8 px de face (le menton) ; tête + cou : 21,0 % (A) et 17,2 % (B) des pixels
   changent entre face et dos ; IoU de silhouette 0,982 / 0,994. Lu « de dos » sans légende à 600 et à 150 px.
2. **Sourire A « narquois ».** Œil = arche d'encre « ∩ » (bords à 16 et 9 u. de flèche, plus de blanc ni d'iris),
   petit arc de pommette sous le coin extérieur (9 u. ; à 13 u. il faisait une seconde paupière à 200 px), bouche en
   sourire ouvert (croissant d'encre). Mesures : bord bas de l'œil 10,1 u. plus haut au centre qu'à ±10 u. (seuil 4) ;
   0 px de blanc d'œil ; visage différent de neutre 11,9 % à 600 px (avant 8,7), 15,6 % à 200 px (avant 10,5).
3. **Tronc géométrique.** Pans en cloche : bord extérieur courbe de ±1,22 à ±1,43 (évasement 0,21 HL, avant 0,13), bas
   du pan qui remonte du coin extérieur (+2,14) vers le corps et entre sous le CÔTÉ de la ceinture (+1,94) : plus
   d'ergot sous le coin de l'ourlet ; plis en coins d'ombre (deux à droite, un à gauche). Vêtement : poitrine bombée
   ±0,95, taille ±0,82 au haut de la ceinture, ±0,83 à l'ourlet. Dos de cape à la même cloche. Boîte inchangée :
   x ±1,445, y −2,115 … +2,205 HL.
4. **Couleurs de la planche hors règle.** Garde-fou dans `palette()` : vêtement et cape ≥ 2,6:1 contre la main,
   luminance peau ≥ 2 × main ; une couleur hors règle est poussée vers le noir ou le blanc (le plus court), mélange
   arrondi aux 8 bits testé tel qu'il sera peint ; `couleurs.garde:false` le coupe ; `draw()` rend `corrections`.
   Mesures : #5e4b8b (2,30:1) → #55447e (2,61:1), ombre dérivée 3,56:1 ; la palette du dossier passe sans changement ;
   #00a19a, #b0f0e8, #20c0b0, #777777 donnés comme vêtement/cape/peau ressortent tous ≥ 2,6:1 et ≥ 0,556 de luminance.
   Dans plate/index.html, le vêtement exporté vaut bien (85, 68, 126), 2,61:1.
   **Infondé en partie** : la peau #9fd8a8 de plate.js respecte la règle du dossier (luminance 0,593 ≥ 2 × 0,278 =
   0,556) ; son contraste de 1,96:1 n'est pas une règle (la peau du dossier n'a que 2,11:1, c'est le contour qui
   sépare). Elle n'est donc pas modifiée. Je n'ai pas touché plate.js (M3) : aligner ses défauts sur le dossier reste
   conseillé (#a8dcd6, #5a3d8c), le garde-fou couvre le cas en attendant.

Défauts mineurs :
- Traits secondaires : `max(1,3 ; W × s)` px à l'écran. Trait le plus fin mesuré (stroke instrumenté, 4 expressions ×
  A/B × face/dos) : 1,30 px à 200 et 160 px de buste (avant 0,71), 2,14 px à 600 px.
- Tête B de face : même croissant d'ombre de joue qu'en A.
- Ancre « épaule » : (±1,15 ; +0,10) HL, valeur du dossier, IDENTIQUE en A, en B et après repli (avant : saut de
  0,36 HL en y). Le repère dessiné suit le dessin (`epauleRepereG/D` : A = le lieu, B = (0,90 ; +0,16) sur l'épaule
  ronde, qui ne va qu'à ±0,96 à cette hauteur — en B le lieu est 0,15 HL hors du trait, < 6 px à ces tailles).
- Repères : de dos, « nuque » (0 ; −0,45) remplace front/menton, pas de « poitrine » ; pastille menton ½ rayon sous le
  bord du menton ; rayon 2,5 px (0,06 HL) sous 55 px de main ; étiquettes contraintes à la boîte, liseré compris
  (0 px hors de ±1,47 HL).
- `personnage_dans_planche.png` : étape 9 du script (plate/index.html, référent souriant + main du bouchon M3).
- HLpx invalide : `draw` → null sans rien peindre, `boite`/`ancres` → null. Option `HLrepli` (HL qui décide du repli,
  p. ex. celui de l'export) en plus de `repli:false`.
- Antennes : laissées plantées derrière le crâne. CHOIX OUVERT pour l'utilisateur : la base visible sur le front
  (dossier ±0,14 ; −1,72) ajoute un trait de fermeture en travers du haut du crâne, déjà jugé « crochet » en passe 1.

## Reste
- Contrôle de la main à refaire avec le vrai moteur M2 (capture v1 réduite ×0,31 pour l'instant).
- Fonction des sourcils levés / froncés en LSF à faire valider par l'utilisateur.
- Antennes (voir ci-dessus) : à trancher par l'utilisateur.
