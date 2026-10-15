# Dossier « outil » — l'outil de conception (type Canva) dans UN SEUL fichier HTML

Atelier des mains LSF, palier v2. Dossier de recherche (pas de code livré), 15 octobre 2026.
Images, mesures, scripts et paquets téléchargés : `/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/v2/recherche/outil/`
(figures `fig_interface.png`, `fig_gabarits.png`, `fig_architecture.png` ; mesures `mesures.json`, `mesures_rendu.json` ; paquets npm dépaquetés dans `npm/` ; documents de référence dans `docs/`).

Question posée : l'utilisateur veut **copier une main et la coller où il veut, la déplacer, la redimensionner, la retourner, la modifier ensuite indépendamment**, avoir plusieurs mains sur la planche, **insérer une image de son ordinateur en fond**, ajouter du **texte** (bannière avec le mot, colonne de définitions), changer les couleurs, **surligner**, **exporter en PNG**, « comme dans Canva ou Word ». Contrainte : un fichier HTML autonome publié comme artifact claude.ai (Three.js r128 vendu dans le fichier ; toute bibliothèque vendue depuis registry.npmjs.org et légère), stockage local, export PNG via canvas.

Ce qui a été fait ici : lecture du code actuel (`source/script.js`, `head.html`, capacités `db` et `downloads` déjà utilisées), téléchargement et pesée des bibliothèques candidates depuis le registre npm, lecture de leurs définitions de types, lecture des pages MDN / WebKit / caniuse / web.dev (par recherche ; `developer.mozilla.org`, `threejs.org`, `canva.com`, `help.figma.com` ne sont pas joignables en direct depuis ce conteneur — les pages MDN ont été lues depuis le dépôt `mdn/content` sur GitHub), et **mesures dans Chromium (Playwright) sur l'application actuelle** : coût du rendu 3D par taille d'export, de la composition WebGL → canvas 2D, de l'encodage PNG/WebP, du balayage alpha, limites de taille de canvas et nombre de contextes WebGL.

---

## 0. Résumé en dix lignes

1. **Pas de calque 3D « vivant » par main.** Une main posée sur la planche est un **objet 2D** (position, taille, rotation, miroir, opacité) qui porte **sa propre pose 3D** et se rend dans une **image cache** ; UN seul `WebGLRenderer` rend toutes les mains, une à une, dans un canvas tampon copié par `drawImage` (mesuré : 1 à 13 ms la copie, contre 0,25 à 1,3 s le rendu lui-même). Créer un contexte WebGL par main est exclu : mesuré ici, à la 17e création **le contexte de l'application elle-même est perdu** (24 créés → 16 vivants, `main_context_lost: true`), ce qui est la limite de 16 contextes des navigateurs.
2. « Copier la main et la modifier ensuite indépendamment » = **la pose appartient à l'objet**, pas à l'atelier. Dupliquer copie la pose ; « Modifier la pose… » rouvre le mode marionnette **sur cet objet**, dans son cadre, avec le même renderer.
3. Gauche = droite en miroir **en 3D** (géométrie miroir, même lumière), pas une image retournée : une image retournée en 2D déplace l'ombre franche du mauvais côté. Le « Miroir » 2D reste disponible comme outil (c'est ce que fait Canva), mais la main gauche de qualité égale naît du miroir 3D.
4. Bibliothèques : toutes MIT sauf tldraw (licence propriétaire, clé obligatoire en production : **exclu**). Pesées (minifiées, brut / gzip) : **Konva 10.9 : 196 Ko / 58 Ko ; Fabric 7.4 : 299 Ko / 92 Ko ; PixiJS 8.22 : 841 Ko / 237 Ko** ; three.min.js r128 déjà vendu : 603 Ko / 149 Ko. Le fichier actuel pèse 3,96 Mo (dont 3,79 Mo de `hand3d.json`).
5. Recommandation : **couche d'objets écrite à la main** (≈ 1 800 à 2 500 lignes : modèle, poignées, rendu, texte via un `contenteditable` superposé, historique par instantanés), parce que l'objet « main » (cache 3D, édition en place, export à l'échelle exacte) devrait de toute façon être une classe maison dans Fabric ou Konva, et parce que le code 2D existe déjà (calques `bgL`/`fgL`, `drawRef`, `drawArrows`, `drawFond`, `alphaBox`). **Plan B : Fabric 7 UMD** (`FabricImage` accepte un `HTMLCanvasElement`, `toCanvasElement(multiplier)`, `classRegistry`, guides d'alignement en extension de 21 Ko), si la couche maison n'est pas tenue.
6. Images : importer par `<input type=file>`, glisser-déposer et collage (`paste` → `clipboardData.files`, compatible Chrome 66 / Firefox 63 / Safari 13.1) ; **HEIC ne se décode que dans Safari 17+** (les photos iPhone doivent être converties avant) ; EXIF : `createImageBitmap(file, {imageOrientation:'from-image'})` (défaut ; Chrome 81 / Firefox 26 / Safari 16) ; **réduire à l'import** (côté long ≤ 4 096 px : une photo de 12 Mpx décodée = 48 Mo en mémoire) via un canvas intermédiaire, pas via `resizeWidth` (bogue WebKit 202458 toujours ouvert).
7. Fond : couleur, dégradé, image (couvrir / contenir / mosaïque, opacité, assombrir pour la lisibilité) ou transparent (damier à l'écran, alpha à l'export). Polices : **vendre 1 à 2 polices OFL en base64** (Atkinson Hyperlegible latin 400 + 700 = 35 Ko ; Nunito 33 Ko ; Lexend 29 Ko), chargées par `FontFace`, `await document.fonts.load()` avant tout `fillText` ; polices système en repli.
8. Export : même fonction de dessin que l'écran, à l'échelle k, **mains re-rendues à leur taille d'export** (jamais un cache agrandi). Mesuré (SwiftShader, pessimiste) : **PNG 2048 px : 1,5 s ; 4096 px : 4,9 s** ; WebP 5 à 9 × plus léger et 2 à 4 × plus rapide (option, pas défaut : Canva importe les deux, le PNG garde l'alpha sans perte). Limites : Chrome aire ≤ 268 435 456 px (**16 384 × 16 384 mesuré OK, 20 000² vide**) ; iOS Safari ≈ 16,8 Mpx (4 096²) ; `MAX_TEXTURE_SIZE` 8 192 ici (16 384 sur GPU courants) → au-delà, rendre les mains par tuiles.
9. Gabarits : A) bannière + colonne de définitions (16:9), B) carte mot / signe (carré), C) fiche de vocabulaire (A4 portrait 2 480 × 3 508), D) planche 4 étapes (16:9 ou bandeau 4:1) ; formats 16:9 1 920 × 1 080, carré 1 080, A4/A3 à 300 dpi, libre ; export ×1 / ×2 / ×3 avec plafond par navigateur.
10. Projet : JSON versionné (`version: 9`), `planche` + `elements[]` ordonnés (l'ordre du tableau EST l'ordre des calques, comme Excalidraw/Polotno) + `assets` ; images par **id d'asset** (`assets` capability, 20 Mio par fichier) OU en `data:` URL dans le fichier `.json` exporté (autoporteur, comme `.excalidraw`) ; sauvegarde continue dans `db` ; brouillon local dans **IndexedDB** (localStorage : 5 Mio, trop petit pour des photos) ; et **le JSON du projet embarqué dans un chunk `tEXt` du PNG exporté**, pour rouvrir n'importe quelle image produite comme projet.

---

## 1. La demande, traduite en fonctions

| Mots de l'utilisateur | Fonction | Patron connu (Canva / Figma / Word) |
|---|---|---|
| « copier la main et la coller juste à côté » | Dupliquer (Ctrl+D) → copie décalée de +10/+10 px ; Ctrl+C / Ctrl+V → collage au même endroit ou sous la souris | Canva : Ctrl+D duplique, Alt+glisser duplique ([techjunkie](https://www.techjunkie.com/best-canva-keyboard-shortcuts-more-productive), [linuru](https://linuru.com/canva/)) |
| « la mettre où je veux » | Glisser, flèches 1 px, Maj+flèches 10 px, champ x/y | Figma : petit pas 1, grand pas 10 par défaut ([help.figma.com 4404575206295](https://help.figma.com/hc/en-us/articles/4404575206295)) |
| « la modifier ensuite » | Chaque main porte sa pose : « Modifier la pose… » (double-clic) rouvre la marionnette sur CET objet | Canva : double-clic ouvre l'éditeur de l'élément (texte, recadrage) |
| « la retourner » | Miroir horizontal / vertical (Maj+H / Maj+V), rotation libre par poignée, 15° avec Maj | Figma : Maj+H / Maj+V ([raycast](https://www.raycast.com/arturdz/figma-shortcuts), [tutsplus](https://webdesign.tutsplus.com/essential-figma-shortcuts--cms-35478t)) ; Canva : « Retourner » dans la barre |
| « même qualité gauche / droite » | Main gauche = miroir 3D de la droite (même lumière), rendue au même pipeline | — |
| « plusieurs mains » | Objets indépendants, calques, sélection multiple, groupes | tous |
| « une image de mon ordinateur en fond » | Fond image (couvrir / contenir / mosaïque, opacité), et images libres comme objets | Canva : « Définir comme arrière-plan » |
| « bannière où y a le mot », « colonne avec les définitions » | Gabarits (modèles) : un clic crée bannière + colonne + zone signe | Canva : modèles |
| « changer les couleurs, surligner » | Palette (planche, texte, fond de texte, main), surligneur (rectangle coloré multiplié derrière le texte, et style de texte « surligné ») | Word : surlignage ; Canva : « effet » de texte |
| « ça s'imprime automatiquement » | Export PNG ×1/×2/×3, fond transparent ou non, format choisi, nom de fichier = mot | Canva : Télécharger PNG, « fond transparent » réservé à Pro ([canva.com/pro/transparent-images](https://www.canva.com/pro/transparent-images/)) — ici gratuit |
| « comme dans Canva ou Word » | Sélection par clic, cadre de transformation à 8 poignées + poignée de rotation, barre contextuelle au-dessus de la sélection, panneau de propriétés à droite, liste des calques | Canva, Figma |

Un point à ne pas rater : **« Retourner »** en français courant veut dire aussi bien « miroir » que « tourner de 180° ». Les deux doivent exister et porter des noms distincts : **Miroir ⇄** (gauche/droite, haut/bas) et **Rotation** (poignée, champ en degrés, boutons ±90°).

---

## 2. Patrons d'interaction d'un éditeur de mise en page

### 2.1 Sélection

| Règle | Valeur | Source / raison |
|---|---|---|
| Clic sur un objet | sélectionne (le plus haut sous le pointeur) | Canva, Figma |
| Clic sur le vide | désélectionne ; glisser depuis le vide = **rectangle de sélection** | Figma sélectionne ce qui **intersecte** le rectangle ; Canva idem. Retenir l'intersection (plus tolérant au trackpad). |
| Maj+clic | ajoute / retire de la sélection | tous |
| Ctrl+A | tout sélectionner (hors verrouillés et fond) | tous |
| Seuil glisser / clic | 4 px écran (3 px Fabric, 3 px Konva `dragDistance`) | évite qu'un clic tremblant déplace |
| Zone de prise d'une ligne fine | ≥ 12 px autour du trait (Konva : `hitStrokeWidth`) | doigt / trackpad |
| Taille minimale d'un objet | 8 × 8 px planche | évite les objets perdus |
| Objet verrouillé | non sélectionnable par clic ni rectangle ; sélectionnable depuis la liste des calques | Canva : cadenas (Alt+Maj+L) |
| Fond | jamais sélectionnable sur la planche : propriétés dans le panneau « Planche » | Canva (l'arrière-plan se règle à part) |
| Test de collision | point transformé dans le repère local de l'objet (inverse de translate·rotate·scale) puis comparé au rectangle ; pour une main, en plus **alpha de l'image cache > 8** au point (clic dans le vide entre deux doigts = clic à travers) | précision attendue par l'utilisateur sur des mains proches |
| Curseurs | `move` sur l'objet, `nwse-resize` etc. sur les poignées (tournés avec l'objet par paliers de 45°), `grab` sur la poignée de rotation | Fabric, Konva |

### 2.2 Cadre de transformation

Schéma (voir `fig_interface.png`) : rectangle de sélection vert INJS, **8 poignées** (4 coins = échelle proportionnelle, 4 bords = échelle sur un axe), **poignée de rotation** décollée de 24 px au-dessus du bord haut (Konva : `rotateAnchorOffset` 50 par défaut, trop loin pour de petites mains ; Fabric : 40), reliée par un trait.

| Règle | Valeur | Source |
|---|---|---|
| Taille des poignées | 10 px écran, carré blanc bordé (Konva `anchorSize` 10 ; Fabric `cornerSize` 13) ; **indépendante du zoom** | `docs/konva_Transformer.ts` |
| Coins | échelle proportionnelle par défaut (Konva `keepRatio: true` ; Canva : les coins gardent les proportions) ; Maj inverse ; Alt = depuis le centre (Konva `centeredScaling`) | idem |
| Bords | pour une **main** : échelle proportionnelle quand même (une main étirée n'est plus une main) ; pour texte/formes : étire ; pour une zone de texte, le bord change la largeur de composition (Fabric `Textbox`) | choix v2 |
| Rotation | libre ; **Maj = pas de 15°** (Figma, Canva) ; tolérance d'accroche 5° (Konva `rotationSnapTolerance` 5) ; champ numérique ; boutons −90° / +90° | idem |
| Miroir | `flipX` / `flipY` sur l'objet (Fabric : `flipX: boolean` ; Konva `flipEnabled` permet le miroir en tirant une poignée à travers l'objet — **à désactiver** : un miroir accidentel sur une main est une faute de sens) | choix v2 |
| Pivot | centre de l'objet (Fabric 7 a changé son défaut `originX/originY` à `center/center`, `docs/fabric_CHANGELOG.md` 7.0.0) | — |
| Sélection multiple | cadre englobant, transformation de groupe (Fabric `ActiveSelection`) ; rotation de groupe autour du centre commun | Fabric |
| Mesure pendant le glisser | infobulle « 742, 310 » / « 180 × 220 » / « 15° » près du pointeur | Figma |

Mathématique de l'objet (à écrire une fois, utilisée partout : écran, test de collision, export) :
`M = T(x + w/2, y + h/2) · R(rot) · S(flipX ? −1 : 1, flipY ? −1 : 1) · T(−w/2, −h/2)` ; dessin dans le repère local `[0,w]×[0,h]`. Les poignées sont les coins/milieux de ce rectangle transformés par M ; tirer une poignée = résoudre la nouvelle `w`/`h` (et `x`/`y` pour garder le coin opposé fixe) dans le repère local, jamais dans le repère écran.

### 2.3 Ordre, groupes, verrou, alignement

| Fonction | Raccourci retenu | Référence |
|---|---|---|
| Avancer / reculer d'un cran | Ctrl+] / Ctrl+[ | Canva ([linuru](https://linuru.com/canva/)) |
| Tout devant / tout derrière | Ctrl+Alt+] / Ctrl+Alt+[ | Canva (une seule source, à confirmer) |
| Grouper / dégrouper | Ctrl+G / Ctrl+Maj+G | Canva, Figma |
| Verrouiller / déverrouiller | Alt+Maj+L / Alt+Maj+U (Canva) — ici un seul bascule Alt+Maj+L | Canva ([bloggingguide](https://bloggingguide.com/canva-keyboard-shortcuts/)) |
| Aligner (gauche, centre, droite, haut, milieu, bas), répartir | boutons de la barre contextuelle (sélection ≥ 2) ; aligner sur la planche (sélection = 1) | Canva « Position », Figma |
| Guides intelligents | lignes magenta quand un bord / centre de l'objet déplacé est à **≤ 5 px écran** d'un bord / centre d'un autre objet ou de la planche (Konva, démo « Objects Snapping », `GUIDELINE_OFFSET = 5`) ; espacement égal entre trois objets (Figma) en seconde priorité | [konvajs.org/docs/sandbox/Objects_Snapping](https://konvajs.org/docs/sandbox/Objects_Snapping.html) |
| Grille | optionnelle, pas 20 px planche, accroche Ctrl désactive | Canva « Règles et guides » |
| Calques | liste à droite, du haut (devant) vers le bas (derrière), glisser pour réordonner, œil (visible), cadenas, renommer au double-clic | Figma ; Canva « Positions → Calques » |

Modèle d'ordre : **l'ordre du tableau `elements[]` est l'ordre de dessin** (Excalidraw utilise en plus un index fractionnaire `index` pour la collaboration, `docs/excalidraw_element_types.ts` l. 69 ; inutile ici, un seul auteur). Un groupe = `groupIds` sur chaque membre (Excalidraw) plutôt qu'un objet conteneur : le dégroupage ne change rien à l'ordre, et un membre reste adressable (double-clic entre dans le groupe).

### 2.4 Copier, coller, dupliquer, supprimer

| Action | Raccourci | Comportement |
|---|---|---|
| Copier / couper / coller | Ctrl+C / Ctrl+X / Ctrl+V | presse-papiers **interne** (JSON des objets, avec leurs poses) ; en plus `navigator.clipboard.writeText(JSON)` pour coller entre deux onglets de l'atelier. Coller : décalage +10/+10 si la cible est au même endroit, sinon sous la souris si elle est sur la planche |
| Coller une image du système | Ctrl+V (événement `paste`) | `e.clipboardData.files` → nouvel objet image centré, taille = min(image, 60 % de la planche) |
| Dupliquer | Ctrl+D ; Alt+glisser | copie +10/+10 ; Alt+glisser dépose la copie à l'endroit lâché (Canva, Figma) |
| Supprimer | Suppr / Retour arrière | sans confirmation (annulable) |
| Tout désélectionner | Échap | aussi : sort du mode texte, sort du mode marionnette |

### 2.5 Annuler / rétablir

Deux familles ([dev.to, command-based undo](https://dev.to/npbee/command-based-undo-for-js-apps-34d6) ; l'éditeur three.js stocke attribut + ancienne / nouvelle valeur) : commandes inversibles (mémoire minimale, mais chaque action doit écrire son inverse — source de bogues) ou **instantanés** (memento). Mesure utile : le document **sans les pixels** est petit — une main = sa pose (≈ 60 nombres), un texte = sa chaîne ; un document de 20 objets fait ≈ 10 à 20 Ko de JSON. Donc :

| Règle | Valeur |
|---|---|
| Mécanisme | pile d'instantanés `structuredClone(doc)` ; **les images ne sont pas dans `doc`** (référence par id vers `assets`), donc un instantané pèse des Ko |
| Profondeur | 100 (100 × 20 Ko = 2 Mo) |
| Fusion | un glisser / un redimensionnement / une frappe continue = **une** entrée (instantané pris au `pointerdown`, validé au `pointerup` ; texte : entrée à chaque pause ≥ 500 ms ou changement de type d'action) |
| Marionnette | une entrée par relâchement de doigt, dans la **même** pile (annuler une pose = annuler, pas un sous-historique) |
| Raccourcis | Ctrl+Z ; Ctrl+Maj+Z et Ctrl+Y |
| Persistance | la pile n'est pas enregistrée ; le brouillon local, si |

### 2.6 Zoom, navigation, affichage

| Règle | Valeur |
|---|---|
| Zoom | Ctrl+molette (centré sur le pointeur), pincement, Ctrl+0 = ajuster, Ctrl+1 = 100 %, boutons − / + ; bornes 10 % – 800 % |
| Déplacement | Espace+glisser, glisser à deux doigts, molette = défilement vertical, Maj+molette = horizontal |
| Planche | ombre portée, fond gris 225 autour, règles optionnelles |
| Résolution d'écran | canvas à `devicePixelRatio` plafonné à 2 (comme aujourd'hui) ; les **mains sont re-rendues** quand leur taille écran change de plus de ×1,5 (sinon `drawImage` du cache) |
| Transparence | damier gris 8 px derrière la planche quand le fond est transparent (Canva, Photoshop) |

### 2.7 Texte

| Règle | Valeur | Raison |
|---|---|---|
| Création | outil T ou touche T puis clic ; ou gabarit | Canva : T crée une zone de texte |
| Édition | double-clic ; un **`<div contenteditable>` superposé** exactement sur le rectangle (même police, taille × zoom, retour à la ligne à la largeur de l'objet) ; à la sortie, le texte est re-dessiné dans le canvas | évite d'écrire un éditeur de texte dans le canvas (caret, sélection, IME, composition, correction automatique) ; c'est ce que fait Konva (démo « Editable text ») |
| Dessin | `fillText` ligne à ligne, retour à la ligne par mots mesuré avec `measureText` (mesuré : 193 mots / 42 lignes en 1,2 ms, dessin 0,6 ms) ; `textBaseline = 'alphabetic'`, hauteur de ligne = 1,25 × corps ; `letterSpacing`, `wordSpacing`, `fontKerning` disponibles (Chromium ; testés présents) | `mesures.json` |
| Styles | police (vendue + système), corps, gras, italique, couleur, alignement, interligne, **fond de texte** (bannière), **surlignage** (fond derrière chaque ligne, hauteur = corps × 1,1, mode `multiply` pour rester lisible sur image), contour (lisibilité sur photo), ombre | demande « bannière », « surligner » |
| Surlignage partiel | sur une sélection dans le `contenteditable` → `<mark>` → stocké en segments `{from,to,color}` | Word |
| Taille auto | option « ajuster le corps à la boîte » (Canva) pour les bannières | — |

### 2.8 Raccourcis : inventaire complet

| Touche | Action | | Touche | Action |
|---|---|---|---|---|
| V | outil sélection | | Ctrl+Z / Ctrl+Maj+Z / Ctrl+Y | annuler / rétablir |
| M | poser une main (droite ; Maj+M gauche) | | Ctrl+C / X / V | copier / couper / coller |
| T | texte | | Ctrl+D ; Alt+glisser | dupliquer |
| I | image | | Suppr / Retour | supprimer |
| R / O / L | rectangle / ellipse / ligne | | Ctrl+G / Ctrl+Maj+G | grouper / dégrouper |
| A | flèche de mouvement | | Alt+Maj+L | verrouiller |
| H | surligneur | | Ctrl+] / Ctrl+[ ; +Alt | ordre |
| P | référent (personnage) | | Maj+H / Maj+V | miroir |
| Échap | désélectionner / quitter le mode | | flèches ; Maj+flèches | 1 px ; 10 px |
| Entrée | sur une main : modifier la pose ; sur un texte : éditer | | Ctrl+A | tout sélectionner |
| Espace+glisser | déplacer la vue | | Ctrl+0 / Ctrl+1 | ajuster / 100 % |
| Ctrl+molette | zoom | | Ctrl+S | enregistrer |
| Ctrl+E | exporter | | Ctrl+Maj+E | exporter avec le gabarit (bannière + colonne) |
| ? | aide des raccourcis | | Maj pendant rotation / échelle | pas de 15° / proportions inversées |

Les raccourcis à une lettre ne s'appliquent qu'en dehors d'un champ de saisie ou d'un `contenteditable`.

---

## 3. Bibliothèques vendables : pesées, licences, aptitude

Tailles mesurées sur les paquets téléchargés de `registry.npmjs.org` (`npm/`), minifié brut / gzip −9 :

| Bibliothèque | Version (date) | Licence | Fichier à vendre | Brut | Gzip | Dépendances |
|---|---|---|---|---|---|---|
| three (déjà vendu) | r128 ; dernière 0.186.1 (2026-09-24) | MIT | `build/three.min.js` | 603 Ko | 149 Ko | 0 |
| **Konva** | 10.9.0 (2026-10-15) | MIT | `konva.min.js` (UMD) | **196 Ko** | **58 Ko** | 0 |
| **Fabric.js** | 7.4.0 (2026-05-18) | MIT | `dist/index.min.js` (UMD) ; `dist-extensions/fabric-extensions.min.js` | **299 Ko** ; +21 Ko | **92 Ko** | 0 |
| PixiJS | 8.22.0 (2026-10-01) | MIT | `dist/pixi.min.js` | 841 Ko | 237 Ko | 10 |
| tldraw | 5.5.2 (2026-10-02) | **« tldraw license »** : interdit en production sans clé, filigrane, télémétrie (`docs/tldraw_LICENSE.md`) | — | 15,2 Mo dépaqueté, 17 dépendances, React obligatoire | — | 17 |
| Paper.js | 0.12.18 (2024) | MIT | — | 12,3 Mo dépaqueté (non pesé : pas de poignées de transformation intégrées) | | 0 |
| interact.js | 1.10.28 | MIT | `interact.min.js` | 98 Ko | 29 Ko | 1 |
| moveable | 0.53.0 (2023-12) | MIT | `moveable.min.js` | 246 Ko | 78 Ko | 5 |
| html2canvas | 1.4.1 (2022) | MIT | 199 Ko | 46 Ko | (rend le DOM en canvas ; inutile si on dessine soi-même) | 2 |
| exifr | 7.1.3 (2021) | MIT | `dist/mini.umd.js` | 29 Ko | 9 Ko | 0 — **inutile** : le navigateur applique l'EXIF lui-même (§ 5) |
| fflate | 0.8.3 | MIT | `umd/index.js` | 33 Ko | 13 Ko | 0 — utile seulement pour un `.zip` de projet |

Pour situer : le fichier HTML actuel fait **3 960 Ko**, dont 3 794 Ko de `hand3d.json`. Konva ajouterait 5 %, Fabric 7,5 %, PixiJS 21 %. Aucune n'est bloquante par la taille ; la question est l'aptitude.

### 3.1 Grille d'aptitude

| Critère | Tout à la main | Fabric 7 | Konva 10 | PixiJS 8 |
|---|---|---|---|---|
| Sélection, 8 poignées, rotation, miroir | à écrire (~300 lignes de maths + 200 de dessin) | intégré (`controls`, `flipX`, `uniformScaling`, `centeredScaling`, `snapAngle`) — confirmé dans `fabric.d.ts` | `Konva.Transformer` (`rotationSnaps`, `keepRatio`, `flipEnabled`, `boundBoxFunc`, `anchorDragBoundFunc`) | non (jeu, pas éditeur) |
| Sélection multiple, groupes | à écrire | `ActiveSelection`, `Group` | `Transformer` multi-nœuds, `Group` | non |
| Texte éditable avec retour à la ligne | `contenteditable` superposé (~250 lignes) | `Textbox` (édition dans le canvas via textarea caché ; nombreux correctifs dans le changelog, mûr) | `Konva.Text` (`wrap`, `ellipsis`) ; édition = textarea superposé à écrire (démo officielle) | `Text` ; pas d'édition |
| Image depuis un canvas (la main rendue) | `drawImage` | `FabricImage`, `ImageSource = HTMLImageElement \| HTMLVideoElement \| HTMLCanvasElement` (type confirmé) | `Konva.Image.image: CanvasImageSource` (type confirmé) | `Texture.from(canvas)` |
| Export haute résolution | fonction de dessin paramétrée par l'échelle | `toCanvasElement(multiplier, {width,height,left,top})` | `node.toCanvas({pixelRatio})`, `toBlob` | `extract` |
| Guides d'alignement | ~150 lignes | extension `aligning_guidelines` (21 Ko, dans `dist-extensions`) | démo officielle à recopier (~120 lignes) | non |
| JSON | maison | `toJSON` / `loadFromJSON` + `classRegistry` pour une classe `Main` | `toJSON` ne sérialise **pas** les images (à réhydrater) | non |
| Annuler / rétablir | maison (instantanés) | **aucun** | **aucun** | aucun |
| Rendu du canvas | un canvas contenu + un canvas UI (existe déjà) | **un** canvas + un canvas supérieur (sélection) | un canvas **par couche** + un canvas de collision par couche (mémoire × 2 par couche) | WebGL : **un second contexte WebGL** à côté de Three (deux contextes, mais pas 16) |
| Cohabitation avec Three.js | triviale (même code que l'export actuel) | bonne : l'objet main est une `FabricImage` dont on remplace l'élément à chaque re-rendu | bonne : `image()` sur un canvas qu'on redessine | mauvaise : deux contextes, deux pipelines, tout le gain de Pixi (sprites par milliers) est inutile ici |
| Style maison (vert INJS, poignées, barre) | total | `cornerColor`, `borderColor`, `cornerStyle`, contrôles personnalisables | `anchorFill`, `anchorStroke`, `borderStroke`, `anchorStyleFunc` | — |
| Risque | volume de code et finitions (curseurs, poignées tournées, groupe tourné) | comportements implicites (événements, cache d'objet, `originX` center depuis 7.0, retina `enableRetinaScaling`) ; 299 Ko à auditer | édition de texte à écrire quand même ; couches multiples contraires au canvas unique d'export | taille, inadéquation |

**Verdict.** PixiJS et tldraw sont exclus (contexte WebGL supplémentaire et inadéquation ; licence). Entre Konva, Fabric et le fait-main, la différence de volume réel de travail est plus petite qu'il n'y paraît, parce que la partie dure est **l'objet main** (cache 3D, invalidation, édition en place, export à l'échelle exacte, test de collision par alpha) et elle est maison dans les trois cas, et parce que l'annulation, les guides, les gabarits, le projet et la bibliothèque sont maison dans les trois cas aussi. Recommandation : **fait-main**, selon la spécification de la section 8, dans l'esprit du projet (tout est mesuré et contrôlé, le code 2D de composition existe déjà). **Plan B Fabric 7** si la couche de sélection n'est pas tenue : recette d'intégration § 8.6.

---

## 4. Composer plusieurs mains 3D indépendantes

### 4.1 Les trois architectures possibles

| | A. Un renderer par main (N canvas WebGL) | B. Une scène orthographique, chaque main = objet transformé | C. **Un renderer, une main à la fois, images cache composées en 2D** |
|---|---|---|---|
| Contextes WebGL | N — **mesuré ici : 24 créés → 16 vivants, et le contexte de l'application est perdu** (`mesures.json`, `webgl_alive_after: 16`, `main_context_lost: true`). Limite de 16 contextes documentée pour Chrome et Firefox ([WebKit, commit 70e1086](https://webkit.googlesource.com/WebKit/+/70e10861eb2fbd9d0862fd8702874c25ae5d8bfd), [plotly](https://community.plotly.com/t/too-many-active-webgl-contexts/16379)) | 1 | 1 |
| Ordre des calques avec textes et images entre les mains | impossible proprement (les canvas WebGL sont des éléments DOM ; l'export recompose) | impossible : tout le 3D est **une** image, on ne peut pas mettre un texte entre deux mains, ni une image entre | natif : chaque main est une image dans l'ordre du tableau |
| Passes toon + contour (dossier « rendu ») | par main | une passe pour tout : l'identité, la profondeur et la coque des mains **se croisent** quand deux mains se chevauchent (contour entre deux mains = contour d'occultation 3D, pas de calque 2D) | par main, à la résolution de la main, cibles de rendu réutilisées |
| Coût par image | N × rendu | 1 rendu de tout, à chaque changement de n'importe quoi | **seulement les mains « sales »** (pose, orientation, couleur, taille ×1,5) ; les autres = `drawImage` (mesuré 1 à 13 ms) |
| Rotation 2D / miroir 2D d'une main | CSS | rotation 3D autour de l'axe de vue (ok) | `rotate` / `scale(−1,1)` du canvas 2D : exact (une image n'est pas rééchantillonnée en qualité si on re-rend à la bonne taille) |
| Export | recomposition | drawImage du tout, puis les 2D par-dessus/dessous : ordre faux | **même** fonction qu'à l'écran, à l'échelle k, mains re-rendues à k × leur taille |
| Transparence | alpha:true par canvas | alpha:true | canvas WebGL `alpha:true, premultipliedAlpha:true` (défaut) → `drawImage` composite correctement ; c'est exactement ce que fait l'export actuel (`xa.drawImage(gl,0,0)` l. 1653) et la planche de contrôle ne montre pas de frange ; mesuré : 2 300 à 9 700 pixels semi-transparents sur le contour (lisière anticrénelée normale) |

Référence : le manuel three.js « Multiple Canvases, Multiple Scenes » décrit les deux techniques (un canvas plein écran + `setScissorTest` / `setScissor` / `setViewport` par élément, OU rendu hors écran puis copie `drawImage` dans des canvas 2D), et motive le renderer unique par la limite de contextes et le coût mémoire d'un contexte ([threejs.org/manual/en/multiple-scenes.html](https://threejs.org/manual/en/multiple-scenes.html) ; forum : « scissor et viewport doivent être posés avant chaque `render` » [discourse](https://discourse.threejs.org/t/solved-what-to-use-a-renderers-scissor-for/1050)). r128 a `setScissor`, `setScissorTest`, `setViewport`, `WebGLRenderTarget` + `DepthTexture` (déjà utilisés par `idRT`).

**Retenir C.** B est à rejeter malgré sa simplicité apparente : la demande « mettre les mains où je veux, comme dans Canva » suppose textes et images **entre** les mains.

### 4.2 Coûts mesurés (Chromium headless, SwiftShader = WebGL logiciel, donc pessimiste d'un facteur ≈ 3 à 10 par rapport à un portable avec GPU)

Rendu complet de l'application actuelle (3 passes : identité, image + coque, arêtes), lu par `readPixels` pour forcer l'achèvement (`mesures_rendu.json` ; la première mesure avec `gl.finish()` donnait 0,3 ms : `finish` ne bloque pas sous SwiftShader — ne pas s'y fier) :

| Taille (côté long) | 1 main : rendu | 2 mains : rendu | `drawImage` WebGL → 2D | 8 copies 2D à ½ taille | PNG (`toBlob`) | WebP q 0,92 | balayage alpha (recadrage, pas 2) |
|---|---|---|---|---|---|---|---|
| 1 024 px | 242 ms | 365 ms | 1,2 ms | 23 ms | 631 ms, 146 Ko | 78 ms, 26 Ko | 8 ms |
| 2 048 px | 470 ms | 535 ms | 2,6 ms | 92 ms | 1 491 ms, 421 Ko | 417 ms, 57 Ko | 17 ms |
| 3 072 px | — | — | — | — | 2 734 ms, 789 Ko | 1 260 ms, 95 Ko | 53 ms |
| 4 096 px | 1 268 ms | 997 ms (mains plus petites à l'écran) | 13 ms | 456 ms | 4 871 ms, 1 235 Ko | 2 305 ms, 134 Ko | 86 ms |

Lectures :
- Le coût du rendu suit le **nombre de pixels couverts par les mains** (fragment), pas le nombre de mains (2 mains à 4 096 coûtent moins qu'une, parce que le cadrage les fait plus petites). D'où la règle : **rendre chaque main à sa taille, pas la planche entière**.
- La composition 2D est négligeable (≤ 13 ms même à 4 096 px) : la planche peut être redessinée intégralement à chaque image pendant un glisser.
- **L'encodage PNG domine l'export** : 1,5 s à 2 048 px, 4,9 s à 4 096 px (processeur seul ; sur un portable compter 0,3 à 1,5 s). Prévoir une barre d'attente et un bouton désactivé (déjà fait). WebP : 5 à 9 × plus léger, 2 à 4 × plus rapide, alpha conservé — à proposer en option « WebP (léger) », PNG par défaut (Canva et les diaporamas lisent les deux).
- Le balayage alpha pour le recadrage coûte < 90 ms : à garder.

### 4.3 Qualité du contour d'une main composée

Le dossier « rendu » établit que le contour doit être **constant en pixels d'écran**. Dans l'architecture C, « l'écran » d'une main est son canvas cache. Règle : l'épaisseur de contour est un paramètre de la **planche** (ex. 3 px pour une planche de 1 920 de large), convertie en pixels du cache : `px_cache = épaisseur_planche × (taille_cache / taille_planche_de_l'objet)`. Ainsi une main agrandie ×2 sur la planche a un contour identique à celle à ×1, et l'export ×3 un contour exactement ×3. Même règle pour le trait des ongles et le rayon du détecteur d'arêtes.

Marge du cache : la coque et l'anticrénelage débordent du maillage ; prévoir **+4 % de marge** autour de la boîte projetée de la main (mesuré sur le contour actuel : 6 px à dpr 2 sur ~1 000 px).

### 4.4 Cache d'images des mains : règles

| Règle | Valeur |
|---|---|
| Clé | hash(pose, orientation, côté, couleur de peau, épaisseur de contour, taille du cache arrondie à 64 px, ombre on/off) |
| Taille du cache | max(taille écran × dpr, taille demandée pour l'export) ; **re-rendu si la taille écran change de plus de ×1,5** (sinon `drawImage` interpolé, invisible à ≤ ×1,5) |
| Budget | 1 main à 1 200 × 1 400 px RGBA = 6,7 Mo ; 12 mains ≈ 80 Mo : acceptable ; **éviction LRU au-delà de 150 Mo**, et libération des caches d'export après l'export |
| Rendu | dans `requestAnimationFrame`, **une main sale par image** pendant une interaction (le reste du dessin utilise l'ancien cache, légèrement flou), toutes à la fin |
| Export | pour chaque main : rendu à `taille_export = taille_planche × k`, en tuiles de 4 096 px si > `MAX_TEXTURE_SIZE` (8 192 ici, 16 384 sur GPU courants) |
| Cible de rendu | un seul `WebGLRenderTarget` (identité + profondeur) redimensionné à la plus grande main, comme `ensureRT` aujourd'hui |

---

## 5. Images, fond, polices

### 5.1 Importer une image

| Voie | API | Compatibilité | Notes |
|---|---|---|---|
| Bouton | `<input type="file" accept="image/*" multiple>` | partout | `accept` ne filtre pas HEIC sur Windows ; vérifier `file.type` et l'extension |
| Glisser-déposer | `dragover` (preventDefault) + `drop` → `e.dataTransfer.files` / `items[].getAsFile()` | partout | MDN « File drag and drop » (`docs/mdn_file_dnd.md`) : pas de `dragstart` pour un fichier venant de l'OS ; afficher une zone « Déposer ici » sur `dragenter` |
| Coller | `paste` → `e.clipboardData.files` | Chrome 66, Edge 79, Firefox 63, **Safari 13.1** ([web.dev](https://web.dev/patterns/clipboard/paste-images)) | synchrone ; suffit. `navigator.clipboard.read()` (Chrome 76, Firefox **127**, Safari 13.1) ne sert que pour un bouton « Coller » ; contexte sécurisé obligatoire (`docs/mdn_clipboard_read.md`) ; `image/png` seulement |
| Appareil photo (tablette) | `<input type="file" accept="image/*" capture="environment">` | mobile | photo du tableau de classe en fond |

Formats : PNG, JPEG, WebP, GIF (1re image), SVG (`<img>` puis `drawImage` ; pas d'édition), BMP. **HEIC/HEIF (photos iPhone par défaut) : seul Safari 17+ les décode** ; Chrome, Firefox, Edge non ([testmuai](https://www.testmuai.com/learning-hub/heif-browser-support/), [dpreview](https://www.dpreview.com/forums/threads/why-does-chrome-not-support-hif-images.4791621)). Message clair : « Ce format (HEIC) n'est pas lisible ici : exporte la photo en JPEG depuis Photos, ou règle l'iPhone sur “Le plus compatible”. » Un décodeur HEIC en JS existe (`heic2any`, libheif en WebAssembly, > 1 Mo) : **non**, hors budget et hors cas d'usage courant (l'utilisateur travaille sur ordinateur).

EXIF (orientation des photos) : les navigateurs appliquent eux-mêmes l'orientation EXIF aux `<img>` depuis Chrome 81, Firefox 26, Safari 13.1 (`image-orientation: from-image` est la valeur initiale, [caniuse](https://caniuse.com/css-image-orientation)) ; pour `createImageBitmap`, `imageOrientation: "from-image"` est le défaut, Chrome 112 pour la valeur nommée (52 pour le paramètre), Safari 16 ([caniuse](https://caniuse.com/mdn-api_createimagebitmap_options_imageorientation_parameter_from-image)). Donc **pas de bibliothèque EXIF** ; passer par `createImageBitmap(file)` avec l'option explicite, repli `<img>` + `decode()`.

Grandes images : une photo de 12 Mpx décodée occupe 4 octets/px = **48 Mo** ; iOS limite la mémoire des canvas (384 Mo sur iOS 15, [WebKit 229825](https://bugs.webkit.org/show_bug.cgi?id=229825)). Règle : **réduire à l'import au côté long 4 096 px** (assez pour un export ×2 d'une planche 16:9, et pour une A4 à 300 dpi) par `drawImage` sur un canvas intermédiaire (deux étapes de ½ si le facteur dépasse 4, pour la qualité) ; **ne pas utiliser `resizeWidth/resizeHeight` de `createImageBitmap`** : bogue WebKit 202458 ouvert ([bugs.webkit.org](https://bugs.webkit.org/show_bug.cgi?id=202458)). Ré-encoder la version réduite en **JPEG q 0,9 si l'image n'a pas d'alpha, PNG sinon** (`toBlob`), et stocker cette version : c'est elle qui ira dans le projet et dans `assets`.

### 5.2 Où vivent les images d'un projet

| Support | Capacité | Rôle |
|---|---|---|
| `assets` (capability claude.ai) | 20 Mio par fichier ; png/jpeg/gif/webp/svg(2 Mio) ; renvoie un `id` durable, affichable par `"/_blob/" + id` ; quota par artifact dans `usage` | **stockage principal** des images d'un projet enregistré dans `db` : la ligne du projet garde l'`id` ; déclarer `{assets:{}, db:{}, user:{}}` ; `use("assets")` rend `null` pour un simple lecteur → cacher l'import |
| `db` | documents, quota global par artifact (`quota_exceeded`) | projets (JSON sans pixels) + bibliothèque de mains (déjà) |
| Fichier `.json` exporté (`downloads`) | « pas de limite » hors `too_large` ; extensions permises : json, png, webp, zip… | projet **autoporteur** : images inlinées en `data:` URL (comme `.excalidraw` : `files[fileId] = {mimeType, id, dataURL, created}`) ; une photo réduite à 4 096 px JPEG ≈ 1 à 2 Mo → base64 ×1,37 |
| IndexedDB | jusqu'à 60 % du disque (Chromium et Safari navigateur ; MDN `docs/mdn_storage_quotas.md`) | **brouillon local automatique** (toutes les 5 s après un changement), avec les images en `Blob` |
| localStorage | **5 Mio par origine** (MDN) | uniquement : préférences, dernier gabarit, dernier format ; jamais un projet avec images |
| Fichier `<input type=file>` | — | rouvrir un `.json` ou un **PNG exporté** (§ 7.3) |

### 5.3 Le fond

| Type | Paramètres | Rendu | Export |
|---|---|---|---|
| Transparent | — | damier 8 px gris 200/235 derrière la planche (non exporté) | alpha |
| Uni | couleur | `fillRect` | opaque |
| Dégradé | 2 couleurs, angle | `createLinearGradient` | opaque |
| Image | source, mode **couvrir** (par défaut) / contenir / étirer / mosaïque ; position (9 ancres + glisser) ; opacité ; **voile** (noir ou blanc, 0–80 %) pour garder le texte lisible ; flou (`ctx.filter = 'blur(px)'`, Chrome/Firefox/Safari 18+) | `drawImage` recadré | idem |
| Cadre | coins arrondis, bord | `roundRect` (Chrome 99, Safari 16, Firefox 112) avec repli par arcs | idem |

Le fond est une propriété de la planche, pas un objet : il ne se sélectionne pas, ne se déplace pas avec Ctrl+A, se règle dans le panneau « Planche ». Mais « Définir cette image comme fond » dans le menu d'une image objet, et inversement « Détacher le fond en image », comme Canva.

### 5.4 Polices sans CDN

Un fichier HTML autonome ne peut compter que sur (a) les polices système, variables d'une machine à l'autre, et (b) des polices **vendues en base64** dans une règle `@font-face` (ou `new FontFace(name, arrayBuffer)`, MDN `docs/mdn_fontface.md`). Pesées depuis `registry.npmjs.org` (paquets `@fontsource/*`, licence OFL-1.1, fichiers `latin-*.woff2` ; base64 = ×1,37) :

| Police | 400 | 700 | Total latin 400+700 | En base64 | Pourquoi |
|---|---|---|---|---|---|
| Atkinson Hyperlegible | 17,2 Ko | 17,5 Ko | 34,7 Ko | 47,6 Ko | conçue pour la basse vision (Braille Institute) ; lettres non ambiguës (I / l / 1, O / 0) |
| Nunito | 16,3 Ko | 16,2 Ko | 32,5 Ko | 44,6 Ko | ronde, chaleureuse, courante dans les supports scolaires |
| Lexend | 14,5 Ko | 14,8 Ko | 29,3 Ko | 40,2 Ko | espacement large (« visual crowding ») |
| Nunito variable (100–900) | — | — | 39,1 Ko | 53,6 Ko | une seule ressource pour toutes les graisses |

Aucune étude ne montre un avantage spécifique de ces polices pour des lecteurs sourds ([recherche](https://github.com/thibaudcolas/readability-group-survey) : Atkinson à 62 % de préférence, pas mieux que trois autres) ; le choix est de confort et de lisibilité à distance (tableau de classe) : **grande hauteur d'x, formes ouvertes, graisse 700 disponible**. Recommandation : vendre **Atkinson Hyperlegible 400/700 + Nunito 400/700** (≈ 92 Ko base64, 2,3 % du fichier), et proposer en plus Arial, Verdana, Georgia, Comic Sans MS, Trebuchet MS en polices système (avec repli `sans-serif` ; un texte en police système s'exporte avec la police présente sur la machine qui exporte — l'avertir dans l'infobulle).

Règle d'emploi dans un canvas : **`await document.fonts.load('700 32px "Atkinson Hyperlegible"')` avant le premier `fillText`** et avant l'export, sinon la première planche s'affiche en police de repli ; `document.fonts.ready` au démarrage.

---

## 6. Gabarits d'export pédagogiques et export PNG

### 6.1 Formats

| Nom | Pixels ×1 | ×2 | Usage | Note |
|---|---|---|---|---|
| Diapositive 16:9 | 1 920 × 1 080 | 3 840 × 2 160 | TBI, diaporama, Canva « Présentation » | format Canva courant ([websitebuilderinsider](https://www.websitebuilderinsider.com/what-are-the-sizes-in-canva/)) |
| Carré | 1 080 × 1 080 | 2 160 × 2 160 | carte, réseau, Canva « Publication » | idem |
| A4 portrait | 2 480 × 3 508 | — (×1 suffit : 300 dpi) | fiche imprimée | 210 × 297 mm à 300 dpi (calcul : 210/25,4 × 300 = 2 480,3) |
| A4 paysage | 3 508 × 2 480 | — | planche imprimée | idem |
| A3 portrait | 3 508 × 4 961 | — | affiche de classe | 297 × 420 mm à 300 dpi ; **17,4 Mpx : au-dessus de la limite iOS Safari** |
| Bandeau 4:1 | 2 400 × 600 | 4 800 × 1 200 | suite d'étapes, frise | — |
| Main seule (actuel) | recadré au plus juste, 1 024 / 2 048 | — | à coller dans Canva | garder tel quel |
| Libre | largeur × hauteur saisies | | | borné par § 6.3 |

Canva accepte les PNG avec alpha et ne propose le « fond transparent » qu'en Pro ([canva.com/pro/transparent-images](https://www.canva.com/pro/transparent-images/)) : l'atelier le donne gratuitement, c'est un argument pour exporter les mains seules sur fond transparent et faire la mise en page ici OU dans Canva.

### 6.2 Gabarits (voir `fig_gabarits.png`)

Un gabarit est un **jeu d'objets** créé en un clic sur une planche d'un format donné, chaque objet restant modifiable (c'est ce que fait Canva). Dimensions en fraction de la planche, marges 4 % :

| Gabarit | Format | Objets créés | Détails |
|---|---|---|---|
| **A. Bannière + colonne de définitions** (la demande explicite) | 16:9 | bannière pleine largeur en haut (hauteur 14 %, fond vert INJS 20 %, texte 72 px gras centré = le MOT) ; colonne gauche (42 % de largeur) « Définition » (28 px, interligne 1,3, fond blanc 90 %) ; zone droite « Signe » avec référent + main(s) ; pied optionnel (source, date) | le mot et la définition sont deux textes ; le nom de fichier d'export = le mot |
| **B. Carte mot / signe** | carré (ou 3:4) | signe en haut (68 %), bannière du mot en bas (24 %) | jeu de cartes, mémory, affichage mural |
| **C. Fiche de vocabulaire** | A4 portrait | bandeau mot + catégorie ; signe à gauche (50 %) ; définition / exemple / synonymes à droite ; image + légende en bas (40 %) | impression ; le texte à 300 dpi exige corps ≥ 36 px (≈ 9 pt) |
| **D. Planche 4 étapes** | 16:9 ou bandeau 4:1 | bandeau mot ; 4 cases égales (ou 2, 3, 6) numérotées, flèche entre les cases ; une main par case, étapes clés du mouvement | la case est un groupe ; « Remplir avec les étapes du mouvement » place automatiquement les N étapes clés d'une main en mouvement |
| E. Bilingue | 16:9 | mot + définition en français à gauche, signe à droite, place pour une image « sens » | notion mathématique : mot, signe, figure |
| F. Vide | tout format | rien | |

Variables de style du gabarit (changeables après coup, sur **tous** les objets du gabarit d'un coup : panneau « Thème ») : couleur principale (défaut vert INJS `#00a19a`), couleur de fond, police, taille de base.

### 6.3 Export PNG haute résolution

| Règle | Valeur | Source |
|---|---|---|
| Échelle | ×1, ×2, ×3 (Canva : « Taille ×1 à ×3 » en Pro) ; A4/A3 : ×1 = 300 dpi, pas de ×2 | — |
| Aire maximale Chrome/Edge | 268 435 456 px = **16 384 × 16 384** (mesuré ici : 16 384² OK, 20 000² vide ; 32 767 × 1 000 et 65 535 × 100 OK) | `mesures.json` ; [pqina](https://pqina.nl/blog/canvas-area-exceeds-the-maximum-limit/) |
| Firefox | 32 767 par côté, 472 907 776 px | [pqina](https://pqina.nl/blog/canvas-area-exceeds-the-maximum-limit/), [html2canvas #3169](https://github.com/niklasvh/html2canvas/issues/3169) |
| Safari iOS | **16 777 216 px (= 4 096²)** ; Safari macOS plus haut mais non documenté ; 384 Mo de mémoire canvas (iOS 15) | [react-pdf #1149](https://github.com/wojtekmaj/react-pdf/issues/1149), [canvas-size](https://jhildenbiddle.github.io/canvas-size/) |
| Texture WebGL | `MAX_TEXTURE_SIZE` 8 192 ici (SwiftShader), 16 384 sur la plupart des GPU | `mesures.json` |
| Règle de plafond | avant export, `probe = canvas(W,H)` + `getImageData(W−1,H−1,1,1)` sur un pixel peint ; si vide, proposer l'échelle inférieure (message : « Ce navigateur ne peut pas produire 3 840 × 2 160 ; export à ×1 ») | — |
| Tuiles | si une main dépasse `MAX_TEXTURE_SIZE`, rendu en tuiles de 4 096 (caméra orthographique décalée, `setViewOffset` existe en r128) ; si la **planche** dépasse l'aire max, export en tuiles PNG séparées (« planche_1-2.png ») — cas rare (A3 ×2), à documenter plutôt qu'à coder d'abord | — |
| Fond transparent | case à cocher ; le damier n'est jamais exporté | — |
| Recadrer au plus juste | option (déjà là) ; pour un gabarit, désactivée (le format compte) | — |
| Nom de fichier | mot de la bannière, sinon nom du projet, sinon `planche` ; `[^\w\-àâäéèêëîïôöùûüç ]` retiré (déjà fait) ; suffixe `@2x` | — |
| Encodage | `toBlob('image/png')` ; option WebP q 0,92 (5–9 × plus léger, alpha ok) ; **jamais `toDataURL`** pour des images de plusieurs Mo (chaîne base64 en mémoire, Konva le déconseille aussi) | [konvajs High-Quality-Export](https://konvajs.org/docs/data_and_serialization/High-Quality-Export.html) |
| Temps à annoncer | PNG 2 048 px ≈ 1,5 s (mesure pessimiste), 4 096 px ≈ 5 s : barre « Rendu… / Encodage… », bouton désactivé | `mesures.json` |
| Livraison | `downloads.save({filename, data: blob})` (`png`, `webp`, `json`, `zip` autorisés) ; repli `<dialog>` + clic droit (déjà fait) | `downloads.d.ts` |
| Texte à l'export | polices vendues chargées (`document.fonts.load`) ; `ctx.imageSmoothingQuality = 'high'` pour les images réduites | — |
| Couleurs | tout en sRGB ; `getContext('2d', {colorSpace:'srgb'})` explicite (évite un canvas P3 sur Mac) | — |

Pipeline (identique à l'écran) : `drawDoc(ctx, doc, k, {export:true})` → fond → pour chaque objet dans l'ordre : `save`, `transform(M × k)`, dessin (main : `drawImage(cache_k)` ; texte : lignes ; image : `drawImage` ; forme : `Path2D`), `restore` → `toBlob`.

---

## 7. Enregistrer, charger, pérennité

### 7.1 Format de projet (JSON, version 9)

```json
{
  "version": 9, "app": "atelier-mains-lsf", "nom": "carré", "creeLe": 0, "modifieLe": 0,
  "planche": { "w": 1920, "h": 1080, "format": "16:9",
               "fond": { "type": "image", "src": {"asset": "…"} , "mode": "couvrir", "ax": 0.5, "ay": 0.5, "opacite": 1, "voile": {"col": "#000000", "a": 0.3} },
               "theme": { "couleur": "#00a19a", "police": "Atkinson Hyperlegible", "corps": 32 } },
  "elements": [
    { "id": "e1", "type": "texte", "x": 77, "y": 43, "w": 1766, "h": 150, "rot": 0, "flipX": false, "flipY": false, "opacite": 1, "verrou": false, "visible": true, "nom": "Bannière", "groupes": [],
      "texte": "CARRÉ", "police": "Atkinson Hyperlegible", "corps": 72, "gras": true, "align": "centre", "couleur": "#1e1e1e", "fond": "#cceeec", "surlignages": [], "interligne": 1.25, "rayon": 12 },
    { "id": "e2", "type": "main", "x": 1100, "y": 300, "w": 360, "h": 440, "rot": 0, "flipX": false, "flipY": false, "opacite": 1, "verrou": false, "visible": true, "nom": "main D", "groupes": [],
      "cote": "D", "pose": { "f": { "pouce": {"av":0,"rap":0,"mcp":0,"ip":0}, "index": {"mcp":0,"ab":0,"pip":0,"dip":0}, "…": {} }, "q": [0,0,0,1] },
      "style": { "peau": "#00a19a", "contour": 3, "ombre": true }, "mouvement": null },
    { "id": "e3", "type": "image", "x": 0, "y": 0, "w": 400, "h": 300, "rot": 0, "flipX": false, "flipY": false, "opacite": 1, "verrou": false, "visible": true, "nom": "photo", "groupes": ["g1"],
      "src": { "asset": "0123…" }, "recadrage": null, "rayon": 0 },
    { "id": "e4", "type": "forme", "forme": "rect", "…": "fond, contour, rayon ; ellipse, ligne, fleche (style du mouvement actuel)" },
    { "id": "e5", "type": "referent", "style": "trait", "visage": true, "reperes": false, "personnage": "piccolo-v2" }
  ],
  "fichiers": { "0123…": { "mime": "image/jpeg", "w": 4096, "h": 3072, "dataURL": "data:image/jpeg;base64,…" } }
}
```

Règles :
- **L'ordre de `elements` est l'ordre de dessin** (Excalidraw, Polotno : `page.children[]`, [docs.polotno.com/docs/schema/page](https://docs.polotno.com/docs/schema/page)).
- Tout objet a les mêmes 12 champs de base (type, id, x, y, w, h, rot, flipX, flipY, opacité, verrou, visible, nom, groupes) ; le reste est propre au type.
- Une **main en mouvement** (plusieurs étapes clés + flèche) reste UN objet (`mouvement: {cles:[…], etapes, fl}`), qui se dessine avec ses fantômes et sa flèche, comme aujourd'hui ; « Éclater en étapes » le transforme en N objets main + flèches (pour la planche 4 étapes).
- `src` d'une image : `{asset: id}` (claude.ai) ou `{fichier: id}` → `fichiers[id].dataURL` (fichier autoporteur). À l'export `.json` : inliner tout dans `fichiers` ; à l'enregistrement `db` : téléverser dans `assets`, remplacer par `{asset}`, ne garder dans le document que les ids (un document `db` ne doit pas porter des Mo de base64).
- Validation à la lecture comme aujourd'hui (`vHex`, `vNum`, `vIn`, `vBool`) : **aucun champ n'est cru** ; un `elements[i]` invalide est écarté avec un message, pas tout le projet.
- Compatibilité : `version` 6–8 (configurations actuelles) se chargent comme **un projet à une main** (ou deux) sur une planche « main seule » ; `load()` actuel devient le convertisseur.

### 7.2 Où et quand enregistrer

| Événement | Action |
|---|---|
| Chaque changement (après 5 s de calme) | brouillon dans **IndexedDB** (`projets` : {id, json, blobs}), indicateur « Brouillon enregistré » |
| Ctrl+S / bouton | `db.collection('projets').doc(id).set({nom, etat, vignette, modifieLe})` ; images dans `assets` ; **vignette** 320 px en `data:` WebP (≈ 10 Ko) dans la ligne pour la galerie |
| Ouverture | galerie des projets `db` (vignette, nom, date) + « Reprendre le brouillon » + « Ouvrir un fichier » |
| Export `.json` | `downloads.save({filename: nom + '.atelier.json'})`, images inlinées |
| Export image | PNG avec le JSON embarqué (§ 7.3) |
| Partage | un projet `db` est lisible par ceux qui ouvrent l'artifact (règles par défaut : lecteurs lisent, contributeurs écrivent) |

### 7.3 Pérennité : le PNG qui se rouvre

Un PNG est une suite de chunks ; un chunk `tEXt` (ou `iTXt` pour l'UTF-8) peut porter n'importe quelle chaîne, ignorée par tous les lecteurs d'images (Canva, PowerPoint, l'Explorateur). Écrire le JSON du projet (sans les images de fond, ou avec si < 2 Mo) dans un chunk `iTXt` clé `atelier-mains-lsf` après `IHDR` : ~40 lignes (longueur, type, données, CRC-32 ; une table CRC de 256 entrées). À l'ouverture d'un PNG (bouton « Ouvrir », glisser-déposer), chercher ce chunk : s'il est là, **l'image redevient un projet modifiable** ; sinon elle devient une image objet. C'est la garantie que l'utilisateur ne perd jamais une planche, même s'il n'a gardé que l'image (Excalidraw fait exactement cela avec ses PNG et SVG exportés : « embed scene »). Coût : taille du PNG + JSON (≈ 20 Ko).

---

## 8. Architecture recommandée (prête à implémenter)

Voir `fig_architecture.png`.

### 8.1 Modèle d'objets

```
Doc { version, nom, planche{w,h,fond,theme}, elements: Element[], fichiers{} }
Element (base) { id, type, x, y, w, h, rot, flipX, flipY, opacite, verrou, visible, nom, groupes[] }
  ├ Main      { cote:'D'|'G', pose{f,q}, style{peau,contour,ombre}, mouvement|null }   → cache: HandCache
  ├ Texte     { texte, police, corps, gras, italique, align, couleur, fond, rayon, contour, surlignages[], interligne, auto }
  ├ Image     { src{asset|fichier}, recadrage{x,y,w,h}|null, rayon, opaciteFond }
  ├ Forme     { forme:'rect'|'ellipse'|'ligne'|'fleche'|'surligneur', fond, trait, epaisseur, rayon, fl{style,sens,double} }
  └ Referent  { style, visage, reperes, personnage }
Session (non enregistrée) { selection: Set<id>, outil, zoom, pan, mode:'planche'|'marionnette'|'texte', historique: Doc[] , caches: Map<id, HandCache> }
```

Pourquoi pas de classes avec méthodes dans le document : le document est **des données** (clonables, sérialisables, diffables), et le comportement est dans des tables `DRAW[type]`, `HIT[type]`, `PROPS[type]`, `DEFAULT[type]`. Ajouter un type = ajouter une ligne dans quatre tables.

### 8.2 Calques de rendu (DOM)

```
.stage
  canvas#planche      ← fond + éléments dans l'ordre (dessin 2D ; mains par drawImage de leur cache)
  canvas#ui           ← sélection, poignées, guides, rectangle de sélection, infobulle de mesure (redessiné seul pendant un survol)
  canvas#gl (caché)   ← le renderer Three.js ; affiché et positionné PAR-DESSUS l'objet main en mode marionnette
  div#texte (caché)   ← contenteditable positionné sur l'objet texte en mode texte
  div.barre-contextuelle, aside.proprietes, aside.calques, nav.outils, footer.biblio
```

Un seul contexte WebGL, un seul renderer, créé une fois (déjà le cas) ; `preserveDrawingBuffer: false` suffit si le `drawImage` vers le cache est fait **dans la même tâche** que le rendu (c'est garanti par construction : `renderHand(id)` rend puis copie) — garder `true` ne coûte que si on en abuse.

### 8.3 Boucle de rendu

```
marquer(dirty.planche | dirty.ui | dirty.mains.add(id))
rAF: si dirty.mains non vide → renderHand(premier id sale)  (une par image pendant un glisser, toutes si inactif)
     si dirty.planche → drawDoc(ctxPlanche, doc, zoom, {pan})
     si dirty.ui → drawUI(ctxUI, session)
```
`drawDoc(ctx, doc, k, opts)` est **la même fonction** à l'écran et à l'export (k = zoom à l'écran, k = échelle d'export). Elle ne connaît ni la sélection ni les poignées.

`renderHand(el, pxW, pxH)` : caméra orthographique cadrée sur la boîte de la main à cette orientation (+4 %), `setSize(pxW, pxH)` du renderer (ou viewport + scissor dans un canvas plus grand), 3 passes actuelles, `cache.ctx.drawImage(renderer.domElement, …)`. Contour et ongles en pixels de cache selon § 4.3.

Mode marionnette : le canvas WebGL est **affiché** par-dessus l'objet (même rectangle, `position:absolute`, `transform: rotate(rot) scale(flip)`), l'interaction actuelle (tirer un doigt, clic droit cadenas, Maj) s'y applique, et à chaque `pointerup` la pose est écrite dans l'élément + historique + cache invalidé. Sortie : Échap, clic hors de l'objet, bouton « Terminer ». L'orientation de la main se règle par les boutons de vue (face / dos / profil / dessus) et par le glisser de la paume comme aujourd'hui ; la caméra reste orthographique pour que la main ne change pas de taille en tournant (une perspective de 26° comme aujourd'hui fait « respirer » la taille : en orthographique l'objet garde w × h). **Point à trancher avec le dossier « rendu »** : si la perspective légère est jugée nécessaire à la lisibilité, la garder mais recadrer l'objet à sa boîte projetée après chaque rotation.

### 8.4 Mains gauche / droite, miroir, copie

| Opération | Effet |
|---|---|
| Poser une main gauche | élément `cote:'G'`, rendu 3D en miroir (scale.x = −1 avec la correction de normales déjà écrite), **même lumière** → ombre franche du bon côté |
| Dupliquer | nouvel élément, pose **copiée** (clone profond), +10/+10 px |
| Miroir ⇄ (outil 2D) | `flipX = !flipX` : exact, instantané, mais l'ombre change de côté : l'infobulle le dit (« pour une main gauche, préfère “Convertir en main gauche” ») |
| Convertir en main gauche / droite | `cote` inversé + pose conservée (la pose est symétrique par construction : mêmes angles) + `flipX` remis à faux ; `mirror(p)` actuel (`pos.x`, quaternion `[q0,−q1,−q2,q3]`) |
| Recopier la pose sur une autre main sélectionnée | « Coller la pose » (Ctrl+Maj+V) : ne copie que `pose`, garde place et taille |

### 8.5 Panneaux et outils (inventaire d'interface, voir `fig_interface.png`)

| Zone | Contenu |
|---|---|
| Barre haute | nom du projet (éditable), Nouveau, Ouvrir (galerie `db` / brouillon / fichier), Enregistrer, Exporter, Annuler/Rétablir, zoom (−, %, +, Ajuster), aide (?) |
| Barre d'outils gauche (icônes + libellés : public sourd = tout en visuel, pas d'infobulle sonore) | Sélection (V), Main (M, menu : droite / gauche / depuis la bibliothèque), Texte (T), Image (I : fichier, coller, appareil photo), Forme (R, O, L), Flèche (A), Surligneur (H), Référent (P), Gabarit (G) |
| Planche | zone grise, planche blanche ombrée, règles optionnelles, damier si transparent |
| Barre contextuelle (au-dessus de la sélection, suit l'objet) | Main : côté, Miroir, Dupliquer, Devant/Derrière, Cadenas, **Modifier la pose…**, Supprimer. Texte : police, corps, gras, couleur, fond, surligner, alignement. Image : Recadrer, Définir comme fond, Arrondir. Multi : Aligner, Répartir, Grouper |
| Panneau droit « Propriétés » | position, taille (chaîne), rotation, miroir H/V, opacité, verrou, nom ; puis section par type (Main : configuration de départ, orientation (4 vues + libre), couleur de peau, contour, ombre ; Mouvement : étapes clés, flèche — l'onglet actuel « Mouvement » ; Texte ; Image ; Forme) ; section « Planche » quand rien n'est sélectionné : format, fond, thème |
| Panneau droit « Calques » | liste ordonnée, glisser, œil, cadenas, renommer |
| Bandeau bas « Bibliothèque » | configurations de départ + mains enregistrées (vignettes), glisser sur la planche pour poser ; onglet « Gabarits » |
| Dialogues | Export (format / échelle / transparent / recadrer / PNG-WebP / nom), Ouvrir, Raccourcis, HEIC / trop grand / navigateur limité |

### 8.6 Plan B : intégration Fabric 7 (si la couche maison n'est pas tenue)

- `dist/index.min.js` inliné (UMD → `window.fabric`), + `fabric-extensions.min.js` (guides) ; `enableRetinaScaling: true`.
- `class Main extends fabric.FabricImage` avec `pose`, `cote`, `style` ; élément = canvas cache ; `toObject()` étendu ; `classRegistry.setClass(Main, 'main')` pour `loadFromJSON`.
- Avant export : pour chaque `Main`, re-rendre le cache à `multiplier × taille`, `setElement(cache)`, puis `canvas.toCanvasElement(multiplier)` → `toBlob`.
- `lockUniScaling` / `uniformScaling: true` pour les mains ; `controls` : retirer les poignées de bord (`ml`, `mr`, `mt`, `mb`) sur les mains ; `snapAngle: 15` avec Maj (`snapThreshold`).
- `Textbox` pour les textes (édition intégrée) ; surlignage = `backgroundColor` par ligne (Fabric gère `textBackgroundColor`).
- Historique : instantanés `canvas.toJSON(['pose','cote','style','…'])`.
- Attention aux changements 7.0 (`originX/originY` center par défaut ; `fireRightClick` : le clic droit « cadenas » du mode marionnette doit être capté **hors** Fabric, sur le canvas WebGL superposé).

### 8.7 Volumes estimés (ordre de grandeur, pour planifier)

| Module | Lignes | Dépend de |
|---|---|---|
| Modèle, validation, historique, presse-papiers interne | 300 | — |
| Transformations, test de collision, poignées, guides, rectangle de sélection | 500 | modèle |
| Dessin 2D des types (texte avec retour à la ligne et surlignage, image, formes, flèches réutilisées, fond) | 450 | modèle |
| Objet main : cache, invalidation, rendu orthographique par main, mode marionnette en place | 400 | rendu 3D actuel |
| Import d'images (fichier, dépôt, collage, réduction, HEIC), assets/db/IndexedDB, export `.json`, PNG + chunk | 350 | capacités |
| Export (dialogue, échelle, plafonds, tuiles) | 200 | drawDoc |
| Gabarits et thème | 200 | modèle |
| Interface (panneaux, barre contextuelle, calques, raccourcis, bibliothèque) | 600 | tout |
| **Total** | **≈ 3 000** (dont ≈ 1 800 à 2 500 pour la couche d'édition proprement dite) | |

---

## 9. Ce que ça implique pour la v2 (recommandations classées)

**Indispensable (sans quoi la demande n'est pas satisfaite)**
1. Un renderer WebGL unique ; chaque main de la planche est un objet 2D avec sa propre pose, rendue dans un cache, composée par `drawImage` dans l'ordre des calques (§ 4). Interdire tout chemin qui crée un second contexte (mesuré : le 17e contexte tue celui de l'application).
2. Dupliquer = copier la pose ; « Modifier la pose… » = mode marionnette en place sur l'objet ; main gauche = miroir 3D, même lumière (§ 8.4).
3. Sélection, 8 poignées + rotation, miroir, duplication, suppression, ordre, verrou, groupe, alignement, guides à 5 px, annuler/rétablir par instantanés, raccourcis de la table § 2.8 (conventions Canva/Figma).
4. Texte : édition dans un `contenteditable` superposé, dessin au canvas avec retour à la ligne ; bannière (fond de texte) et surligneur ; 2 polices OFL vendues en base64 + polices système (§ 5.4).
5. Images : fichier, dépôt, collage ; réduction à 4 096 px à l'import ; orientation EXIF par le navigateur ; message clair pour HEIC ; fond image couvrir/contenir/mosaïque + voile (§ 5).
6. Export : `drawDoc` unique écran/export, mains re-rendues à l'échelle d'export, contour en unités de planche ; ×1/×2/×3 avec sonde de plafond ; PNG par défaut, WebP en option ; fond transparent gratuit ; barre d'attente (§ 6.3).
7. Projet JSON v9 (§ 7.1), brouillon IndexedDB, enregistrement `db` + images `assets`, export `.json` autoporteur, lecture des versions 6–8.
8. Gabarits A (bannière + colonne), B, C, D en un clic, avec thème (§ 6.2).

**Fortement recommandé**
9. JSON embarqué dans un chunk `iTXt` du PNG exporté et réouverture d'un PNG comme projet (§ 7.3).
10. Caméra orthographique pour les mains posées (taille stable en tournant) — à trancher avec le dossier « rendu ».
11. Test de collision par alpha du cache (clic entre deux doigts = clic à travers).
12. « Éclater en étapes » (main en mouvement → N mains + flèches) et « Remplir la planche 4 étapes ».
13. Vignettes de projet dans la galerie ; nom de fichier = mot de la bannière.

**Plus tard**
14. Export par tuiles au-delà de l'aire maximale (A3 ×2) ; recadrage d'image interactif ; grille et règles ; espacement égal dans les guides ; collage entre onglets par `navigator.clipboard` ; mode « présentation » plein écran de la planche ; export PDF multi-pages (jsPDF ≈ 300 Ko, ou impression du navigateur).

**À ne pas faire**
15. tldraw (licence), PixiJS (second contexte, taille), html2canvas (inutile), exifr/heic2any (inutile / trop lourd), `toDataURL` pour l'export, `resizeWidth` de `createImageBitmap`, localStorage pour un projet, un objet 3D par main dans une seule scène (ordre des calques impossible).

---

## 10. Incertitudes et estimations

- Les temps de rendu sont mesurés en **WebGL logiciel** (SwiftShader) : sur un portable avec GPU intégré, compter 3 à 10 × plus vite pour le rendu 3D ; l'encodage PNG (processeur) est, lui, comparable (0,3 à 1,5 s à 2 048 px selon la machine).
- La limite de 16 contextes est mesurée dans Chromium ; Firefox annonce le même message (« Exceeded 16 live WebGL contexts ») ; Safari « recycle » aussi les contextes anciens (commit WebKit cité). Non mesuré sur Safari.
- Limite d'aire de Safari macOS : non documentée ; iOS ≈ 16,8 Mpx, rapports anciens (2022). La sonde à l'export (§ 6.3) rend la question sans conséquence.
- Raccourcis Canva « tout devant / tout derrière » (Ctrl+Alt+] / [) : une seule source ; peu importe, ce sont les nôtres.
- Les pages officielles Canva, Figma, three.js, Fabric et Konva n'ont pas pu être lues en direct (DNS bloqué) ; les faits sur Fabric et Konva viennent **des paquets eux-mêmes** (types, changelog, source du Transformer), les faits Canva/Figma de recoupements de plusieurs aide-mémoire.
- Les formats « Canva » exacts (présentation 1 920 × 1 080, publication 1 080 × 1 080) viennent de sources secondaires ; l'A4 300 dpi est un calcul.
- Lisibilité des polices pour des lecteurs sourds : aucune étude trouvée ; choix fondé sur la basse vision et la lecture à distance.

---

## 11. Sources

Mesures locales : `/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/v2/recherche/outil/mesures.json`, `mesures_rendu.json` (scripts `../outil_mesure.py`, `../outil_mesure2.py`) ; paquets npm dans `outil/npm/` (registre : https://registry.npmjs.org/fabric, /konva, /pixi.js, /tldraw, /@fontsource/atkinson-hyperlegible, /@fontsource/nunito, /@fontsource/lexend, /exifr, /interactjs, /moveable, /fflate, /html2canvas, /paper) ; documents dans `outil/docs/` (`fabric_README.md`, `fabric_CHANGELOG.md`, `konva_Transformer.ts`, `konva_CHANGELOG.md`, `excalidraw_element_types.ts`, `tldraw_LICENSE.md`, pages MDN `mdn_*.md` depuis https://github.com/mdn/content).

- three.js, manuel « Multiple Canvases, Multiple Scenes » : https://threejs.org/manual/en/multiple-scenes.html ; forum scissor : https://discourse.threejs.org/t/solved-what-to-use-a-renderers-scissor-for/1050
- Limite de contextes WebGL : https://webkit.googlesource.com/WebKit/+/70e10861eb2fbd9d0862fd8702874c25ae5d8bfd ; https://community.plotly.com/t/too-many-active-webgl-contexts/16379 ; https://github.com/fingerprintjs/fingerprintjs/pull/484 (message Firefox)
- Limites de taille de canvas : https://pqina.nl/blog/canvas-area-exceeds-the-maximum-limit/ ; https://github.com/niklasvh/html2canvas/issues/3169 ; https://github.com/wojtekmaj/react-pdf/issues/1149 ; https://jhildenbiddle.github.io/canvas-size/ ; mémoire canvas iOS : https://bugs.webkit.org/show_bug.cgi?id=229825
- createImageBitmap / EXIF : MDN `docs/mdn_createimagebitmap.md` ; https://caniuse.com/mdn-api_createimagebitmap_options_imageorientation_parameter_from-image ; https://caniuse.com/css-image-orientation ; bogue resize WebKit : https://bugs.webkit.org/show_bug.cgi?id=202458 ; https://github.com/whatwg/html/issues/7210
- Collage d'images : https://web.dev/patterns/clipboard/paste-images ; https://web.dev/articles/async-clipboard ; MDN `docs/mdn_clipboard_read.md` ; dépôt de fichiers : MDN `docs/mdn_file_dnd.md`
- Quotas de stockage : MDN `docs/mdn_storage_quotas.md` (https://developer.mozilla.org/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria)
- HEIC : https://www.testmuai.com/learning-hub/heif-browser-support/ ; https://www.dpreview.com/forums/threads/why-does-chrome-not-support-hif-images.4791621
- Raccourcis Canva : https://linuru.com/canva/ ; https://www.techjunkie.com/best-canva-keyboard-shortcuts-more-productive ; https://bloggingguide.com/canva-keyboard-shortcuts/ ; fond transparent Pro : https://www.canva.com/pro/transparent-images/ ; formats : https://www.websitebuilderinsider.com/what-are-the-sizes-in-canva/
- Raccourcis Figma : https://www.raycast.com/arturdz/figma-shortcuts ; https://webdesign.tutsplus.com/essential-figma-shortcuts--cms-35478t ; pas de déplacement : https://help.figma.com/hc/en-us/articles/4404575206295
- Konva : accroche aux objets https://konvajs.org/docs/sandbox/Objects_Snapping.html ; export haute qualité https://konvajs.org/docs/data_and_serialization/High-Quality-Export.html ; FAQ (couches multiples) https://konvajs.org/docs/faq.html ; `Konva.Image` (image, canvas ou vidéo) https://konvajs.org/api/konva.image
- Fabric vs Konva : https://dev.to/xingjian_hu_123dc779cbcac/konvajs-vs-fabricjs-in-depth-technical-comparison-and-use-case-analysis-3k7l
- tldraw : https://tldraw.dev/legal/tldraw-license ; https://tldraw.dev/sdk-features/license-key
- Excalidraw (format) : https://docs.excalidraw.com/docs/codebase/json-schema ; Polotno (format pages/children) : https://docs.polotno.com/docs/schema/page
- Annuler/rétablir : https://dev.to/npbee/command-based-undo-for-js-apps-34d6
- Polices : https://fontsource.org/fonts/atkinson-hyperlegible/about ; https://github.com/thibaudcolas/readability-group-survey
- Capacités de l'artifact : `assets.d.ts`, `downloads.d.ts`, `db.d.ts` du contrat 0.2.76 (skill `artifact-capabilities`)
