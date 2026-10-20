# Chantier M1 — LA MAIN (assets) : journal

## 20 octobre 2026 — grief « L » vu de dos : largeurs, obliquité des doigts repliés, pouce

Grief (capture de « L » vu de dos, tournée de 90°) : « J'ai jamais vu des doigts aussi inclinés. Un L où le pouce fait
40 cm de large et l'index 10. On a perdu en précision par rapport à avant. » Tout est MESURÉ avant d'être touché ; deux
hypothèses de départ ont été démenties par la mesure (marquées ✗).

### 1. Largeurs : maillage contre SON dessin (pose « dessin », silhouette de face, grille 0,25 mm)

✗ « l'index est plus fin que son dessin » : c'était l'inverse. Avec les tables 4.1, les quatre doigts sortaient 1 à 4 mm
PLUS LARGES que son dessin (rapportés à la paume, qui colle à 1–2 mm : 10 à 20 % trop gros). Sa photo IMG_2354, en
rapport à la largeur de la paume (283 px, apex de la 1re commissure → bord ulnaire), donne l'index P1 / P2 / P3 =
18,4 / 16,8 / 15,5 mm : exactement son dessin au MILIEU DU TRAIT (18,2 / 16,0 / 14,9), convention de l'échelle X et de
l'ajustement 3b de la paume. Cibles retenues = son dessin au milieu du trait (`largeurs_du_dessin()`, chaîne v1 corrigée),
épaisseur = largeur × e/l des tables 4.2 (0,76–0,87, inchangés). Le pouce garde les tables (voir 3).

| doigt | station | AVANT maillage | APRÈS maillage | dessin intérieur | dessin milieu du trait |
|---|---|---|---|---|---|
| index | P1 (0,55) / P1 (0,8) / IPP | 20,5 / 20,9 / 20,8 | 18,0 / 18,0 / 17,6 | 17,2 / 16,9 / 16,8 | 18,2 / 17,6 / 17,8 |
| index | P2 / IPD / P3 | 18,2 / 17,2 / 16,4 | 16,1 / 16,2 / 14,9 | 15,0 / 14,6 / 13,9 | 16,0 / 15,9 / 14,9 |
| majeur | P1 / P1 / IPP | 21,5 / 21,2 / 21,0 | 19,5 / 19,5 / 19,5 | 18,2 / 18,2 / 18,4 | 19,2 / 19,2 / 19,4 |
| majeur | P2 / IPD / P3 | 19,0 / 17,8 / 17,0 | 17,5 / 16,2 / 16,0 | 16,2 / 15,8 / 15,3 | 17,0 / 16,2 / 16,0 |
| annulaire | P1 / P1 / IPP | 20,0 / 19,5 / 19,6 | 18,8 / 18,5 / 18,5 | 17,2 / 17,2 / 17,1 | 18,8 / 18,2 / 18,2 |
| annulaire | P2 / IPD / P3 | 17,5 / 16,8 / 16,0 | 16,8 / 16,2 / 16,0 | 15,5 / 14,9 / 14,9 | 16,5 / 15,9 / 16,0 |
| auriculaire | P1 / P1 / IPP | 18,0 / 17,9 / 17,1 | 18,6 / 18,1 / 17,6 | 17,1 / 16,4 / 15,8 | 18,5 / 17,8 / 17,2 |
| auriculaire | P2 / IPD / P3 | 15,3 / 14,6 / 14,0 | 16,4 / 16,0 / 14,8 | 14,8 / 14,2 / 13,4 | 16,1 / 15,8 / 14,9 |
| pouce (projeté) | P1 0,3 / P1 0,55 / IP | 29,1 / 19,6 / 18,2 | 21,9 / 21,1 / 19,8 | 19,5 / 19,9 / 20,8 | 21,9 / 21,2 / 21,9 |
| pouce (projeté) | P2 0,35 / P2 0,55 | 17,9 / 17,1 | 19,4 / 18,4 | 18,4 / 16,5 | 19,8 / 18,1 |
| paume (largeur à y = 1 / 3 / 5 cm) | | 69,2 / 93,5 / 101,6 | 69,2 / 93,3 / 101,6 | 67,5 / 92,0 / 101,1 | — |

(mm ; écart au milieu du trait APRÈS : doigts −0,3 à +0,6 mm, pouce −2,1 à +0,5 ; IoU de la silhouette sur son dessin
0,943 → 0,955, sur la silhouette intérieure 0,919 → 0,932 ; image `checks/e11_largeurs_avant_apres.png`.)
Épaisseurs (e/l des tables gardé) : index 15,2 / 15,2 / 13,3 / 13,5 / 11,7 mm, majeur 16,5 / 16,6 / 14,2 / 13,9 / 12,7,
annulaire 15,4 / 15,9 / 13,6 / 13,5 / 12,5, auriculaire 15,1 / 15,2 / 13,4 / 13,0 / 11,7. Les ongles suivent (0,70–0,74 ×
la largeur à l'IPD).

### 2. Obliquité des doigts repliés (mesurée dans le MOTEUR : presets résolus, cinématique `_interne.fk`, repère de la main)

La v1 mettait toute la convergence dans la MCP (`LEAN` −6,5 / 0 / +6,5 / +12°). Mesuré : P1 repliées inclinées de
−6,5 / 0 / +8,0 / +4,9° (index, majeur, annulaire, auriculaire ; l'arc automatique du moteur, mc4 flexion 12°·arc et mc5
supination 20°·arc, s'y ajoute). Vues de dos en plongée, l'inclinaison s'amplifie (projection ×1/sin de la plongée) :
d'où les jointures « en vague ». Sur SES photos (V de dos, `photo_dos_V2.jpg` ; poing 2357) les P1 repliées sont
PARALLÈLES sous le majeur et ce sont les P2–P3 qui convergent vers la base du thénar (mobilite.md R1 : « axes des MCP ET
des IP obliques »). D'où (repères de liaison du GLB, lus par le moteur) :

| | AVANT | APRÈS |
|---|---|---|
| axe de la MCP (X de P1), rotation autour de l'os | −6,5 / 0 / +6,5 / +12° | **−3 / 0 / +1,5 / +10°** |
| axes de l'IPP et de l'IPD (X de P2, P3) | 0 / 0 / 0 / 0 | **−4 / 0 / +4 / +8°** |
| P1 repliée à 90° (moteur, arc 0,6), angle latéral | −6,5 / 0 / +8,0 / +4,9° | **−3,0 / 0 / +2,9 / +2,6°** |
| P2 du poing vue de face (vers le pouce) | −4,2 / 0 / +3,3 / −0,1° (parallèles) | +4,2 / 0 / −7,4 / −11,8° (convergent : photo 2357) |
| écart des bouts / écart des MCP (poing) | 0,97 | **0,88** (v1 piste P : 0,90) |
| jour entre P1 voisines, poing, DQS + correctifs (mm, ¼ → 1 de P1) | i–m 1,8/0,2/0,5/0,2 ; m–a 2,6/0,4/0,4/0,1 ; a–a 3,4/1,4/2,2/2,8 | i–m 1,7/0,5/0,2/0,3 ; m–a 2,9/1,3/0,8/0,8 ; a–a 3,8/0,2/0,1/0,1 |
| pénétration entre P1 voisines (poing) | i–m 3,0, m–a 2,4 mm | i–m 0,6, a–a 0,9 mm |

L'auriculaire garde +10° d'axe parce que la supination de mc5 par l'arc (6,8° à arc 0,6) le renverse : visible, il fait
+2,6°. Le CONTACT, que la v1 obtenait en inclinant les P1, vient maintenant de la chair des flancs : correctif de la MCP
(`CORRECTIFS['mcp']['elargit']` = 1,2 mm par côté à 90°, sur P1 jusqu'à l'IPP, flancs côté dos et mi-épaisseur, nul sur
le pli palmaire — sans cette restriction, 12 arêtes vives au repos sur l'auriculaire ; avec : repos 3 / 0 comme avant).
Images : `checks/e10_jointures_dos.jpg`, `checks/e11_jointures_avant_apres.jpg` (poing et V : vue « dessus » où l'on voyait
l'éventail des P1, maintenant parallèles), `checks/e10_signes.jpg`.

### 3. Pouce de « L » et de « 5 » : pronation de repos

✗ « pronation de repos 90°, le pouce écarté montre son flanc » : mesuré, c'est l'inverse. Sur SON dessin le pouce vu de
face fait 21,2 mm à mi-P1, 21,9 à l'IP — plus que son épaisseur (17,5) : on y voit sa face large. Ses photos aussi :
pouce écarté vu côté paume = 1,3 à 1,5 × la P2 de l'index (IMG_2354 : P1 79 / IP 72,5 / P2 67 px contre 52,5 ; IMG_2361 :
76 / 72 / 59,5 contre ≈ 47). Le maillage à 75° (MakeHuman) montrait son FLANC : 19,6 / 18,2 / 17,9 mm, aussi mince que
l'index ; dans « L » de dos, pouce P1 / IP / P2 = ×1,20 / ×1,04 / ×0,98 l'index — un cône, large à la base (41 mm à la
MCP, la palmure) et mince au bout. À 90° ce serait pire (17,5 mm partout).
Retenu : la PEAU de P1–P2 du pouce tourne de −18° autour de l'os (`PRONATION_POUCE_DELTA`, pulpe à 57°, balayage −20 /
−35 : −35 dépasse son dessin de 3 mm) ; les repères de LIAISON (axes de la MCP et de l'IP que lit le moteur) et mc1 sont
INCHANGÉS. Essayé d'abord : tourner aussi les axes — dans le moteur la pince, le F et les becs s'ouvraient d'≈ 1 cm (presets
réglés par `reach` sur ces axes ; `checks/e11_pinces_moteur_avant_apres.png` montre la version retenue : fermés comme
avant). Résultat dans le moteur, « L » de dos : pouce P1 / IP / P2 = ×1,48 / ×1,28 / ×1,23 l'index (photo 2361 :
×1,62 / ×1,53 / ×1,27) ; « 5 » : ×1,40 / ×1,23 / ×1,20.

### 4. Base du pouce dans « L » de dos (palmure de la 1re commissure) — pas par les poids : par un 9e correctif (4 bis)

Mesure : largeur de la silhouette perpendiculaire à P1 du pouce (vue de dos, DQS + correctifs, banc d'essai sur les poids
finaux). Dans « L » (rap −28 : 53° entre pouce et index, vue paume) : **39,6 mm à la MCP**, 27,9 au quart de P1, 23,5 à la
moitié ; « 5 » : 27,6 au quart (à la MCP la corde rentre dans la main). Sa photo 2361 (pouce à 50° de l'index, échelle
par la P3 de l'index, 14,7 mm) : ≈ 27 mm à la MCP, ≈ 25 sur P1, ≈ 24 à l'IP. L'excès est À LA MCP SEULEMENT (+12 mm) ;
au-delà, le pouce a sa largeur. Les bouts de la corde à la MCP : bord radial du pouce (part du pouce 0,97) et l'APEX de la
commissure (repos (4,34 ; 6,65 ; 0,93), part 0,51).

Essayé (part du pouce = mc1 + P1 + P2 ; L / 5 / V / Quatre / B / repos / opposition / rapprocher ; arêtes > 60° et
triangles retournés comptés DANS la commissure ; bord radial vu de dos pouce replié : flèche concave / bosse, mm) :

| variante | L : MCP / ¼ P1 (mm) | 5 : ¼ P1 | bord radial V / Quatre / B | replis commissure V / Quatre / B / repos / opp. / rapp. |
|---|---|---|---|---|
| livrée | 39,6 / 27,9 | 27,6 | 0,4/6,7 · 0,3/7,0 · 0,3/8,3 | 18/0 · 24/3 · 13/1 · 0/0 · 19/3 · 14/1 |
| recette v1 côté dos (part annulée en deçà de la ligne tête de MC II → trapèze, pli XW(y) 0,46–2,17 cm, tranche z ±0,45) | 39,6 / 27,9 | 27,6 | 1,7/5,7 · 1,7/6,3 · 1,3/8,4 | 45/0 · 46/5 · 25/1 · — |
| part de MC I renforcée dès sa base (peau à < 1,3–2,0 cm de l'axe) | 40,4 / 25,9 | 27,6 | 0,4/5,8 · 0,3/6,3 · 0,3/7,6 | plus de plis (V 353 arêtes au total) |
| apex tiré vers le pouce (0,9) / laissé à la main (0,1) | 45,8 / 26,4 · 42,0 / 34,9 | 26,3 · 32,2 | — | — |
| part contrastée dans la palmure (autour de 0,4, w 0,7 dos → 1,0 paume, dès y 4,5) — **construite et rendue** | 39,8 / 25,2 | 26,0 | 0,0/6,4 · 0,0/6,7 · 0,0/8,0 | 24/2 · 37/2 · 16/0 · 0/0 · 18/2 · 10/0 |

La dernière variante a été construite (`--depuis 5`) et rendue en Cycles (`checks/e11_commissure_avant_apres.jpg`, L, 5, V
de dos) : les chiffres s'améliorent au quart de P1, mais à l'œil le bord libre de la palmure devient une DROITE de la tête
de MC II au pouce (le coin s'agrandit au lieu de se creuser) et un pli horizontal marque le bord radial en V. **Écartée**
(`COMMISSURE = None`, code gardé et commenté dans `poids_propres`) ; la reconstruction redonne les fichiers à l'octet près
(`hand_v2.glb` d8e4cc47…, `hand_v2.json` a7da8256…).

Diagnostic : la largeur à la MCP vient de la GÉOMÉTRIE, pas des poids. L'apex de la commissure de SON dessin (686, 525 px)
est à 1,4 cm au-delà de la MCP du pouce ; quand le pouce s'écarte, la vraie peau de la palmure GLISSE le long du pouce
vers sa MCP (photo 2361 : le bord libre rejoint le pouce à la MCP), alors qu'une peau à poids fixes reste accrochée au
même endroit du pouce. Aucun mélange de poids ne fait glisser : dans « L » (MCP du pouce à 0°) mc1 et P1 bougent
ensemble. Ce qu'il faudrait : un correctif (morph) de la palmure piloté par « rapprocher » < 0 (le bord libre ramené vers
la MCP, ≈ 1 cm), c'est-à-dire un 9e morph target — hors du contrat actuel (8 morphs aux noms fixés). À décider par
l'orchestrateur (le moteur applique déjà les correctifs sur le CPU, la limite de 8 morphs de three.js r128 ne le gêne pas).
Le bord radial de la main vue de dos, pouce replié (V, Quatre, B), reste droit au sens de la v1 (flèche concave 0,3–0,4
mm) ; la bosse de 6,7 / 7,0 / 8,3 mm au-dessus de la corde poignet → tête de MC II est la base du pouce (MC I et thénar
autour du trapèze, qui ne bouge pas : v1 en gardait 2,8–4,3 mm, « le contour dessiné du poignet »).

### 4 bis. Le 9e correctif `commissure_abd` (feu vert de l'orchestrateur : le contrat passe à 9 correctifs)

- **Nom du morph target** (GLB `mesh.extras.targetNames`, JSON `correctifs.liste`) : **`commissure_abd`**.
- **Pilote** : `angle` = **`pouce.rap`** (« rapprocher »), `reference` = **−28** ; poids = clamp(pouce.rap / −28, 0, 1) =
  clamp(−rap / 28, 0, 1). Écrit dans `hand_v2.json → correctifs.liste` au MÊME format que les 8 autres : le moteur actuel
  (`a.morphs`, `w = clamp(p[doigt][champ] / ref, 0, 1)`) l'applique SANS modification (vérifié ci-dessous).
  Poids 0 pour tout pouce ramené (rap ≥ 0 : repos 10, dessin 4, V 45, Quatre 42, B 35, poing 30, O, pinces…), 1 dans « L »
  et « Y » (rap −28, mobilite.md 4.2 : angle droit), 0,43 dans « Main ouverte (5) » (rap −12).
  Pourquoi « rapprocher » et pas « avancer » : sur ses photos 2354 et 2361 le pouce est écarté DANS le plan de la paume
  (abduction radiale = rap < 0), palmure tendue ; « avancer » est grand aussi pouce replié (V : av 35, B : av 20), palmure
  relâchée — un pilote par « avancer » aurait déformé V, Quatre, B.
- **Construction** (`correctif_commissure`, étape 8) : dans la pose pouce seul rap = −28 (DQS), l'apex de la commissure de
  son dessin est à 28,3 mm de la MCP du pouce ; la peau de la palmure (faces dorsale ET palmaire) est ramenée vers la MCP,
  dans le plan de la paume, de 17 mm à l'apex (gaussienne σ 1,3 cm), nulle à moins de 0,9 cm de l'axe du pouce (rampe
  jusqu'à 1,8 cm : la peau du pouce ne bouge pas), champ lissé 12 passes et Taubin, ramené au repos par Rᵀ. 2 522 sommets,
  15,4 mm au plus.
- **Réglage** (largeur perpendiculaire à P1 du pouce vue de dos, MCP / quart de P1, banc sur les poids livrés) : sans
  correctif 39,6 / 27,9 mm. Protection par la part du pouce : 1,0 cm → 31,7 / 24,5 ; 1,2 → 29,8 mais un CROCHET au bord libre
  (la peau du pouce immobile, la palmure voisine tirée) — rampe de part plus douce, champ lissé 20 et 40 passes : le crochet
  reste. Protection par la distance à l'axe du pouce : bord libre en V arrondi, sans crochet ; amplitude 1,4 → 29,6 mm, mais
  31,6 dans le moteur (sa cinématique du pouce élargit de 2 mm) ; **1,7 retenu**.

| mesure | sans `commissure_abd` | avec |
|---|---|---|
| « L » de dos, largeur à la MCP du pouce — pipeline (DQS + correctifs) | 39,6 mm | **27,5 mm** |
| « L » de dos, à la MCP — MOTEUR (rendu, trait retiré) | 41,2 mm (×2,58 la P2 de l'index) | **29,1 mm (×1,82)** ; photo 2361 ≈ ×1,72 |
| « L » de dos, quart / milieu de P1 — moteur | 23,6 / 20,5 mm | 21,6 / 20,5 mm |
| « 5 » (poids 0,43), quart de P1 — pipeline / milieu de P1 — moteur | 27,6 / 22,6 mm | 22,5 / 21,5 mm |
| arêtes > 60° / triangles retournés DANS la commissure : L, 5, repos | 0/0, 0/0, 0/0 | 0/0, 0/0, 0/0 |
| main entière, L (les 3 doigts repliés, plis palmaires connus) | 370 / 19 | 370 / 19 (identique) |
| V, Quatre, B, repos, opposition, rapprocher : écart des sommets (pipeline) | — | **0,0 cm** (poids 0) |
| moteur, rendus V (2), Quatre (4), Main plate (B), Repos, Poing serré × 4 vues : pixels différents (même GLB, JSON avec / sans l'entrée) | — | **0** partout ; L et Y : 1 000–5 200 px (le coin du pouce) ; « 5 » : 1 600–2 600 |

Images : `checks/e11_commissure_avant_apres.jpg` (Cycles, L / 5 / V de dos, sans / avec), `checks/e11_commissure_moteur.png`
(moteur : L capture tournée, L de dos, 5 de dos et de face, sans / avec). Regardées : la palmure devient une courbe creuse
qui rejoint le pouce à sa base, le pouce sort de la main comme un doigt au lieu d'un coin ; V identique.
Empreintes : `hand_v2.glb` sha256 9fa3b504d92fb030…, `hand_v2.json` 8545527486ee1598… (`python3 build_hand.py --depuis 8`).

### Ce qui change pour le moteur (v2/engine, non touché)

- `hand_v2.glb` : mêmes noms d'os et attributs ; **9 morphs** : les 8 d'avant (mêmes noms) + `commissure_abd` (piloté par
  `pouce.rap`, référence −28 : voir 4 bis ; appliqué par le moteur actuel sans changement de code). Changent : les repères de liaison des P1
  (X : LEAN), des P2 et P3 (X : LEAN_IP, nouveau) ; la géométrie (doigts plus minces, peau du pouce tournée) ; le morph
  `mcp_*` (flancs élargis en flexion). `A.eventail` (axe Y des P1) est INCHANGÉ : les `ab` des presets gardent leur sens.
- `hand_v2.json` : `os.*.axes` (P1, P2, P3 des quatre doigts), `os.*.rayon / largeur / epaisseur` des phalanges
  (capsules de contact : index P1 0,925 → 0,827 cm, P2 0,825 → 0,733, P3 0,738 → 0,665 ; auriculaire P1 0,787 → 0,822), `couplages.convergence`, `convention_pose.doigts`
  et `.pouce` (textes), `poses_controle.V.arc` 0,4 → 0,6, `dessin` (pouce rap 4, av 3, ip −15, mcp 1), plis, ongles.
- Presets : AUCUN angle à changer. Mesuré sur les 77 presets résolus : pénétration max 0,30 → 0,23 ; O, pince, F, becs
  inchangés à l'œil ; « Angle droit », « Bec de canard ouvert / rond », « Cône », « Majeur pouce »… passent de 0,16–0,29
  à 0,00 (plus de contact forcé : doigts plus minces) — à revoir avec `reach` seulement si l'utilisateur trouve un
  contact manquant. Poing, Index (1), V (2), L : les doigts repliés se posent autrement (P1 droites, P2 convergentes) avec
  les MÊMES angles.

### Ce qui reste

- Base du pouce en « L » : réglée par le 9e correctif (4 bis), 41,2 → 29,1 mm dans le moteur. À faire valider par lui sur
  `checks/e11_commissure_moteur.png`. Le contrat (PLAN.md) doit passer à « 9 correctifs » (l'orchestrateur).
- Tunnel du poing vu de profil : 52 → 74 mm² (doigts plus minces, mêmes angles) ; poing 2,6 mm de pénétration (bout de
  l'index sur la paume), V 2,3 mm.
- Petite fissure de peau à la base dorsale du majeur dans V (dos en plongée), présente AVANT (vérifié au même rendu).
- La pronation « 90° » demandée n'est pas appliquée : SON dessin et ses deux photos disent ≈ 55–60° pouce écarté ; à
  faire valider par lui sur `checks/e10_signes.jpg` (L et 5).
- `--regler-poses` relancé sur la nouvelle main donnait des poses moins naturelles (IPP du majeur à 90°, IP du pouce à
  63°, tunnel 111 mm²) : angles validés gardés.

Empreintes (avant le 9e correctif, voir 4 bis pour les fichiers livrés) : `hand_v2.glb` sha256 d8e4cc4773818056… (3,1 Mo), `hand_v2.json` a7da8256a9bede90… ; reconstruction
`python3 build_hand.py` 12 min (78 rendus Cycles).

## État au 19 octobre 2026 : TERMINÉ, CORRIGÉ après relecture adverse

| livrable | contenu | contrôle |
|---|---|---|
| `hand_v2.glb` (2,9 Mo) | glTF 2.0 binaire, UNE SkinnedMesh, 20 os aux noms du contrat, 26 610 sommets, 53 216 triangles (la triangulation des mesures : diagonale la plus courte), normales lissées, ≤ 4 os par sommet, attributs `_REGION`, `_ONGLE`, `_MASQUES`, **8 morph targets correctifs** (MCP et IPP des quatre doigts, POSITION + NORMAL, accesseurs creux) | relu octet par octet (étape 9) : repères des os à 2,5·10⁻⁶, poids à 10⁻⁷, morphs à 10⁻⁶ près ; **au repos, sur ses propres triangles : 0 triangle retourné, 3 arêtes > 60°** (fond de la commissure annulaire–auriculaire, déjà là à l'étape 4) ; chargé dans three.js r128 (`test_three.py`, morphs compris) |
| `hand_v2.json` (0,14 Mo) | os, butées, couplages (formule de la vis sans fin), convention de pose, 44 plis barycentriques, ongles MESURÉS, correctifs (loi de poids), contacts, poses `repos`, `dessin`, `poses_controle` (poing, V réglés), `poses_essai`, côté anatomique, conseils au moteur | plis sur les triangles du GLB (écart 0,000 mm) ; poses dans les butées, R2, IPD–IPP, vis sans fin ; pénétrations mesurées |
| `build_hand.py` + `noyau.py`, `raster.py`, `cycles_bpy.py`, `test_three.py`, `vendor/GLTFLoader.js` | MakeHuman brut → GLB testé : `python3 build_hand.py` (≈ 6 min 30 s à vide, work/ et checks/ effacés, 4 cœurs) ; `--depuis N`, `--jusqu N`, `--sans-cycles`, `--regler-poses` (re-règle les poses de contrôle, ≈ 8 min de plus) | reconstruit à vide le 19 octobre après la correction : code 0 (empreintes du GLB et du JSON ci-dessous) |
| `checks/` | e1 … e8, **e6_ongles, e6_bouts_geo** (bouts isolés, 5 vues), **e8_correctifs** (jointures et tunnel), **e10_cycles** (DQS + correctifs), **e10_pouce**, **e10_bouts** (Cycles), e10_gros_plans, e10_three | toutes regardées |

## Correction après relecture adverse (19 octobre 2026)

Chaque défaut, ce qui a été fait, la mesure avant → après (détail : section automatique, étapes 5 à 10).

1. **Ongles déchirés, sillons froissés — BLOQUANT — corrigé.** Cause mesurée : l'ancienne étape 6 déplaçait les sommets
   PAR MORCEAUX — coupure nette en z = −1 mm sur les flancs (l'auriculaire, R = 5,8 mm, avait une plaque de 132° d'arc dont
   les bords tombaient sur cette coupure), bande du bord exclue au-delà du bord libre (crans aux coins distaux), sillon de
   0,2 mm sur 0,2 mm de large (double trait). Et le chiffre « 1 arête > 60° » du journal était celui de l'étape 4.
   Nouvelle étape 6 : champ de déplacement LISSE (peau de référence = la peau, creux de la plaque MakeHuman comblé par
   interpolation biharmonique ; plaque = cylindre de rayon R calé tranche par tranche ; pente plafonnée à 14° ; raccord
   biharmonique sur 1,5 mm ; distance signée de la plaque en « squircle » C²). Largeur = SES rapports par doigt (0,70 /
   0,74 / 0,72 / 0,70 / 0,72). Mesuré sur la main entière APRÈS les ongles, sur les triangles exportés : **arêtes > 60° :
   262 → 3, > 90° : 77 → 0, triangles retournés : 8 → 0** ; sur le GLB relu : 3 / 0 / 0. Rayons 9,1 / 8,8 / 7,4 / 5,9 /
   12,1 mm (cibles 8,9 / 8,8 / 7,3 / 5,8 / 11,4), inclinaison 14,5 / 12,2 / 12,3 / 9,8 / 9,7°, relief moyen 0,29–0,54 mm,
   repli latéral 0,3–0,7 mm au-dessus du bord de la plaque, bord libre décollé de 0,7–1,6 mm. Images : `e6_bouts_geo.png`,
   `e6_ongles.png`, `e10_bouts.jpg` (cinq bouts × dos, bout, deux profils, en Cycles). Le trait de couleur de l'ongle
   (`_ONGLE`) est le minimum de deux champs lisses : plus d'escalier au bord libre.
2. **Interpénétrations des poses de contrôle — corrigé.** Mesure de contact écrite (étape 8 : sommet sous la surface de
   l'autre partie, normales opposées, écart le long de la normale), sur toutes les poses du JSON. Poses réglées
   (`--regler-poses` : descente par coordonnées en DQS + correctifs, contact mou ≤ 2,5 mm, bouts posés, pouce sur les P2,
   butées, R2, IPD–IPP, vis sans fin, aucune rotation axiale — R6). **Poing : 5,9 → 2,2 mm ; V : 7,9 → 2,5 mm** (mobilite.md
   P2.1 : 1,5–3 mm admis). Repos, dessin, opposition, « rapprocher » couplé : 0.
3. **Tunnel du poing vu de profil — réduit de 73 %.** Mesuré comme la cavité où l'on voit à travers la boucle de l'index
   (jour TRAVERSANT, fond visible : 0 mm² avant comme après — le « trou » était une cavité sombre). Ancien poing : 195 mm²
   (DQS) ; poing réglé (pouce en travers des P2 de l'index et du majeur, photo 2357 ; index 95 / 105 / 72) : 106 mm² ; avec
   les coussinets palmaires des correctifs (la chair du coin de la MCP) : **52 mm² (10,8 × 7,0 mm)**. Image :
   `e8_correctifs.jpg` (ancien / réglé / réglé + correctifs).
4. **Jointures qui ne saillent pas, rides dorsales — corrigé par 8 morph targets correctifs.** Pour chaque MCP (90°) et
   IPP (100°), calculés en DQS dans la pose puis ramenés au repos (Rᵀ) : dôme dorsal en plateau (largeur d'une tête de
   métacarpien), coussinets palmaires plafonnés au plan du pli, lissage de Taubin des rides. Rayon dorsal sur la
   bissectrice, index MCP : repos 9,6 mm, LBS 6,7, DQS 9,5, **DQS + correctif 13,1 mm (saillie +3,5)** ; IPP +2,5 mm.
   Forme réglée sur la silhouette du poing vu de dos : un dôme gaussien étroit faisait des PICS (bosses de 6 à 9 mm de
   large), le plateau des têtes de 11 à 14 mm. Saillie 3,5 mm et pas 4–5 : à 4 mm les têtes redevenaient pointues (v1 :
   3,2). Rendus de contrôle e10 tous faits en DQS + correctifs (comme M2). Loi : poids = clamp(angle / angle_ref, 0, 1),
   dans le JSON.
5. **Pli palmaire distal des doigts trop proximal — corrigé.** Règle de SA photo 2354 (pli IPD → bout = pli IPP → pli
   IPD) au lieu des 7,5 mm d'anatomie.md : **index 3,0 mm avant l'IPD (rapport 1,00 ; photo 0,98)**, majeur 4,2,
   annulaire 3,8, auriculaire 0,8 mm (sa P3 est aussi longue que P2).
6. **Main gauche ou droite — à trancher par l'orchestrateur (l'asset n'est pas en cause).** Preuve : repère direct
   (déterminant des repères des os +1), paume +Z, doigts +Y, pouce +X ⇒ main DROITE ; une gauche aurait le pouce en −X.
   Le contrat de PLAN.md est donc contradictoire dans les termes. Correction proposée (non faite : le PLAN appartient à
   l'orchestrateur) : « main droite skinnée (la gauche = miroir x → −x) ». `hand_v2.json` → `cote_anatomique`,
   `cote_note_plan`.
7. **Pouce « rapprocher 45 » et opposition : peau de la paume repliée — corrigé en partie, et un cas hors couplage.**
   (a) Frontière du poids de mc1 en rampe large (de 3,0 à 1,2 cm de son axe au lieu de 2,4 → 1,6) : changement de dièdre
   de la peau palmaire (99e centile / arêtes > 30°) opposition 29,8° / 82 → 26,1° / 70, rapprocher 45 + avancer 32 :
   28,7° / 80 → 23,9° / 62. (b) Le « X » au centre de la paume n'est PAS une déformation : en opposition, 0 arête du
   centre de la paume ne change de plus de 20° (131 sur le thénar) — c'est le relief MakeHuman de la paume au repos.
   (c) « rapprocher 45 / avancer 0 » est HORS COUPLAGE : la vis sans fin de la v1 impose av ≥ 0,7·rap (31,5°) ; sans elle
   le pouce entre de 7,3 mm dans le 2e métacarpien (mesuré) — le long pli vif vu par le relecteur. Avec le couplage :
   0 mm de pénétration, 24 arêtes nouvelles > 60°, 2 triangles retournés (fond du pli thénar). Formule écrite dans le JSON.
   (d) En corrigeant, trouvé et corrigé un vrai défaut de poids : le poids retiré à mc1 allait aussi à l'os « poignet »,
   un sommet mc1 + avant-bras passait à 1,0 d'avant-bras entre des voisins à 0,35 : **5 triangles retournés au dos du
   poignet dès 15° d'extension (la pose de repos !), trait sombre au rendu → 0**.
8. **Pouce trop long (Buryanov au lieu de SES proportions) — infondé, mesure à l'appui.** Sur sa photo IMG_2354 (pouce
   posé à plat sur la table, donc vu en vraie grandeur ; 0,055 mm/px), pli MCP → bout = **61,6 mm** ; le modèle (MCP →
   bout, Buryanov × 1,03) : **60,6 mm** ; son dessin : 54,1 mm. La photo confirme Buryanov et montre que le dessin
   raccourcit le pouce (projection). Les 72 mm « commissure → bout » de la photo dépendent de l'écartement du pouce : ce
   n'est pas une longueur d'os. À noter pour l'utilisateur : sur la photo, le pli IP est à 36 mm du bout contre 28 mm
   pour le centre de l'IP du modèle (règle 1 : 0,84 de la v1, piste T, validée par lui).
9. **Trapèze très proximal, pronation 75° — mineur, justifié.** La CMC est celle de SON dessin, validée en v1 (piste T :
   (652, 748) px, à la base de l'éminence) → 1,4 cm au-delà du pli du poignet ; anatomiquement le tubercule du scaphoïde
   est au pli distal du poignet et le trapèze juste au-delà (≈ 1 cm) : la trapézo-métacarpienne à 1,5–2 cm est plausible ;
   les « ≈ 30 mm » d'anatomie.md § 3 sont une estimation marquée [estim.]. Pronation de repos du pouce : 75° (normale de
   l'ongle MakeHuman) contre 90° conseillés : noté pour M2 (convention_pose), qui ajoute la pronation couplée.
10. **26 610 sommets pour ≈ 20–25 k — mineur, accepté.** La densité vient du maillage hm08 lui-même après Catmull-Clark ×2
    (2,7 cm d'avant-bras et le bouchon : quelques centaines de sommets) ; rogner l'avant-bras d'une boucle n'en retire que
    ≈ 320. Proposition : écrire « ≈ 27 k » au contrat.
11. **Détails de livraison — faits.** Noms vus par three.js (`_region`, `_ongle`, `_masques`) écrits dans le JSON ;
    `cycles_bpy.py` écrit dans `work/` (plus rien dans /tmp) ; `GLTFLoader.js` vendu dans `v2/hand/vendor/` (provenance,
    sha256) et utilisé par le test ; `e3_retaille.png` recomposée sans cases vides. Le `.gitignore` de v2/hand fait
    apparaître l'ancien work/ et un __pycache__ suivis comme supprimés : à valider par l'orchestrateur.

**Reproductibilité** : deux reconstructions intégrales à vide successives (387 s) donnent des fichiers identiques à
l'octet — `hand_v2.glb` sha256 19e74631f525…28e95d, `hand_v2.json` sha256 31c4c711d3a7…c6c41a.

**Contre-vérification indépendante** (scripts du relecteur, pygltflib + LBS, relancés sur le GLB livré) : 0 arête de
bord, poids somme 1 ± 1·10⁻⁷, repères des os à 4·10⁻⁵, déterminant +1 ; au repos 83 arêtes > 60° dont 80 sur l'anneau
vif du bouchon du poignet (coupe oblique, y de −2,9 à −2,3 cm, que son script n'exclut pas) et 3 au fond de la
commissure annulaire–auriculaire, 0 triangle opposé aux normales du GLB (avant : 353 / 149 / 10) ; pénétrations LBS :
poing 1,9 mm max, V 2,5 mm (avant : 5,2 / 5,6 mm).

**Bord de l'ongle au rendu Cycles** : la limite blanche montre de petites irrégularités (≈ 0,25 mm) vues du bout ; le
champ `_ONGLE` lui-même est lisse (rastérisé au seuil 0 : bord continu, vérifié) — c'est la lèvre du bord libre vue de
chant sous 20 échantillons. `cycles_bpy.DEBRUITAGE` permet de couper le débruiteur pour un gros plan.

## Synthèse des mesures (livraison corrigée)

| contrôle | mesure | cible |
|---|---|---|
| longueur poignet → bout du majeur ; index / annulaire | 19,00 cm ; 17,72 / 17,65 cm | HL 19,0 ; index = annulaire |
| largeurs / épaisseurs aux 25 stations | doigts : SON dessin au milieu du trait (−0,3 à +0,6 mm, 20 oct.) ; épaisseurs : e/l des tables | dessin ; tables 4.2 |
| silhouette de la paume sur son dessin (pose « dessin ») | écart moyen 0,43 mm, max 4,5 ; IoU 0,943 | contour du dessin |
| surface du GLB au repos (ses triangles) | 0 triangle retourné ; 3 arêtes > 60° (commissure) ; 0 > 90° | pas de pli |
| ongles | 0,70–0,74 × doigt à l'IPD ; R 9,1 / 8,8 / 7,4 / 5,9 / 12,1 mm ; 9,7–14,5° ; relief 0,29–0,54 mm | Jung ; 10–15° ; 0,3–0,5 mm |
| pénétrations (DQS + correctifs) | repos 0, dessin 0, poing 2,2, V 2,5, opposition 0, rapprocher 0 mm | ≤ 2,5–3 mm |
| tunnel du poing vu de profil | 52 mm² (ancien 195) ; jour traversant 0 | « aucun jour traversant » |
| jointures à 90° / 100° (DQS + correctif) | saillie +3,5 mm MCP, +2,5 mm IPP ; LBS : jointure écrasée de 2,9 mm | tête qui sort |
| plis distaux des doigts | 3,0 mm avant l'IPD à l'index, rapport 1,00 | photo 2354 : 0,98 |
| repos (DQS + correctifs) | 3 arêtes devenues > 60°, 0 triangle retourné | — |
| three.js r128 | 1 SkinnedMesh, 20 os, 26 610 sommets, `_region`, 8 morphs (POSITION + NORMAL) | contrat |

## Décisions (à relire avant de toucher au pipeline)

1. **Côté anatomique.** Les axes du contrat donnent une main DROITE (voir défaut 6) ; le maillage MakeHuman gauche est
   passé au miroir x → −x. L'autre main = miroir x → −x à l'exécution. `cote_anatomique`.
2. **Repère.** Origine au centre du poignet, Y = plan médian de la paume redressé (pente résiduelle 0,0°), Z = normale
   vers la paume.
3. **Proportions.** Longueur de chaque doigt = son dessin, partage de Buryanov × 1,03 ; auriculaire par la règle du pli
   IPD de l'annulaire ; pouce = Buryanov (confirmé par la photo 2354, défaut 8). Largeurs des doigts : SON dessin au
   milieu du trait (20 octobre 2026) ; épaisseurs : largeur × e/l des tables 4.2 ; pouce : tables 4.1–4.2.
4. **Pouce MakeHuman.** Cube CMC 1,8 cm trop distal : la retaille du pouce est ancrée à la MCP.
5. **Bind = main ouverte**, doigts en léger éventail (index +4°, annulaire −5,5°, auriculaire −14°).
6. **Poids.** MakeHuman, subdivisés, nettoyés : avant-bras séparé au pli du poignet ; chaînes recentrées sur NOS centres ;
   MC I limité au thénar par une rampe large (3,0 → 1,2 cm), son poids retiré n'allant JAMAIS à l'avant-bras ; MC IV–V
   limités au-delà de leur base ; palmures lissées ; ongle rigide (rampe de poids vers 1,0 sur P3).
7. **Ongles** : champ de déplacement lisse (défaut 1). Ne jamais revenir à un déplacement par morceaux.
8. **Plis.** Doigts : proximal à mi-P1, moyen 3 mm avant l'IPP, distal par SA photo (défaut 5). Paume, pouce, poignet :
   SES plis, relevés sur le dessin.
9. **Retouches de forme mesurées** (étape 4) : creux de la paume 5 mm, sections en trapèze arrondi, commissures lissées.
10. **Correctifs des jointures** (morph targets, étape 8) : calculés en DQS, appliqués avant le skinning, poids
    clamp(θ/θref, 0, 1). Le moteur M2 doit utiliser les quaternions duaux.
11. **Poses de contrôle** réglées par la mesure de contact (étape 8, `--regler-poses`) ; les constantes du fichier sont le
    résultat de ce réglage.

## Limites connues (à traiter par le moteur M2 ou plus tard)

- **Plis palmaires des poses très fléchies.** Poing en DQS + correctifs : 512 arêtes deviennent > 60° et 21 triangles se
  retournent, tous au fond des plis palmaires (la peau se replie là où les pulpes se touchent : P1 contre P2, IPD) ; LBS :
  181 / 8. Un vrai pli, que le rendu toon tracera comme un trait intérieur ; il n'y en a aucun sur le dos ni aux ongles.
- **Tunnel du poing** : 52 mm² de cavité vue de profil (photo 2357 : quasi nul). Le pouce couché sur les P2 ne la
  couvre pas de profil ; un poing plus serré (IPP > 105°) l'écraserait contre la paume.
- **three.js r128** n'applique que 8 morphs (4 avec morphNormals) : les 8 correctifs sont tous actifs dans un poing ;
  morphNormals éteint ou morphs côté CPU (noté dans le JSON).
- **Pose « dessin »** : écart de 4,5 mm à la base ulnaire de l'auriculaire écarté (bourrelet de skinning) ; le pouce
  dépasse son dessin de ≈ 4 mm (le dessin raccourcit le pouce, défaut 8) ; doigts : à −0,3..+0,6 mm du milieu de son
  trait depuis le 20 octobre (avant : 1–4 mm plus larges).
- **Pli IP du pouce** : sur la photo 2354 il est à 36 mm du bout, le centre IP du modèle à 28 mm (règle v1 validée) — à
  confirmer par l'utilisateur.
- **26 610 sommets** pour « ≈ 20–25 k » (défaut 10).
- `work/` (intermédiaires) est ignoré par git (`.gitignore`), tout se régénère.

## Détail des mesures, étape par étape (section réécrite par `build_hand.py`)

<!-- MESURES AUTOMATIQUES : DÉBUT (build_hand.py réécrit cette section) -->
<!-- étape 1 -->
### 1. Extraction (MakeHuman hm08, CC0)
- boucle de coupe : 20 arêtes, 20 sommets tous de degré 2 ; plan moyen à -2.71 cm du centre du poignet le long de l’avant-bras (écart avant aplatissement -0.38..0.28 cm)
- redressement sur le plan médian de la paume (3 passes) : rotation totale 6.2° ; pente résiduelle du plan médian -0.04° ; origine = milieu de la section du poignet au cube MH « wrist » (largeur 4.74 cm, épaisseur 3.39 cm)
- main extraite : 1669 sommets, 1659 faces (1658 quads + 1 bouchon de 20 côtés), volume 282 cm³ (> 0 : faces orientées vers l’extérieur) ; boîte x -5.6..7.2, y -2.9..17.4, z -1.8..5.2 cm
- os MH sans équivalent ignorés : aucun ; longueur MH poignet → bout du majeur : 17.39 cm (cible 19.0)

<!-- étape 2 -->
### 2. Squelette (20 os, centres articulaires corrigés)
- dessin : apex de la 1re commissure (686, 525) px, bord ulnaire x = 290 px à la même hauteur → échelle X 0.02288 cm/px (paume 90.6 mm) ; échelle Y 0.02455 cm/px (HL 190 mm sur 774 px) ; anisotropie 1.073
- longueurs centre → centre (cm) : dessin (chaîne v1 corrigée) | Buryanov × 1,03 | RETENU (total du dessin, partage de Buryanov ; pouce : Buryanov)

| doigt | P1 dessin | P2 dessin | P3+pulpe dessin | total dessin | P1 Bur. | P2 Bur. | P3+p Bur. | total Bur. | P1 retenu | P2 retenu | P3+p retenu | total retenu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| index | 3.95 | 2.50 | 2.21 | 8.66 | 4.10 | 2.31 | 2.01 | 8.42 | **4.22** | **2.38** | **2.07** | **8.66** |
| majeur | 4.57 | 2.84 | 2.31 | 9.72 | 4.59 | 2.71 | 2.19 | 9.49 | **4.70** | **2.78** | **2.24** | **9.72** |
| annulaire | 3.92 | 2.63 | 2.26 | 8.81 | 4.26 | 2.65 | 2.18 | 9.09 | **4.13** | **2.57** | **2.11** | **8.81** |
| auriculaire | 3.10 | 1.78 | 1.96 | 6.84 | 3.37 | 1.86 | 2.00 | 7.23 | **3.33** | **1.84** | **1.98** | **7.14** |
| pouce | 4.72 | 2.98 | 2.43 | 10.12 | 4.76 | 3.25 | 2.81 | 10.82 | **4.76** | **3.25** | **2.81** | **10.82** |

  (pouce : colonnes « dessin » = MC I, P1, P2 + pulpe projetés ; auriculaire : total = mi-chemin entre le centre de l’IPD de l’annulaire (y = 15.58) et son pli IPD dessiné (y = 15.07) − y de sa MCP (8.18) = 7.14 ; dessin 6.84, Buryanov 7.23)
- centres articulaires retenus (cm, repère du contrat) et longueurs :

| os | parent | centre (x, y, z) | longueur | cible | X local (axe de flexion) | Z local |
|---|---|---|---|---|---|---|
| poignet | — | (0.00, 0.00, 0.00) | 2.66 | — | (1.00, 0.00, 0.00) | (0.00, 0.00, 1.00) |
| mc1 | poignet | (3.20, 1.40, 0.30) | 4.76 | 4.76 | (0.01, -0.40, 0.92) | (-0.88, 0.44, 0.20) |
| pouce_p1 | mc1 | (5.50, 5.24, 1.93) | 3.25 | 3.25 | (0.08, -0.28, 0.96) | (-0.87, 0.45, 0.20) |
| pouce_p2 | pouce_p1 | (7.09, 7.99, 2.60) | 2.81 | 2.81 | (0.13, -0.21, 0.97) | (-0.82, 0.53, 0.22) |
| mc2 | poignet | (1.25, 2.14, -0.11) | 7.01 | MC Bur. 7.01 | (0.99, -0.14, 0.00) | (0.00, 0.00, 1.00) |
| index_p1 | mc2 | (2.24, 9.08, -0.11) | 4.22 | 4.22 | (1.00, -0.07, 0.05) | (-0.05, 0.00, 1.00) |
| index_p2 | index_p1 | (2.54, 13.28, -0.11) | 2.38 | 2.38 | (1.00, -0.07, 0.07) | (-0.07, 0.00, 1.00) |
| index_p3 | index_p2 | (2.70, 15.65, -0.11) | 2.07 | 2.07 | (1.00, -0.07, 0.07) | (-0.07, 0.00, 1.00) |
| mc3 | poignet | (0.15, 2.63, -0.36) | 6.65 | MC Bur. 6.65 | (1.00, 0.02, -0.00) | (0.00, 0.00, 1.00) |
| majeur_p1 | mc3 | (0.00, 9.28, -0.36) | 4.70 | 4.70 | (1.00, 0.00, 0.00) | (0.00, 0.00, 1.00) |
| majeur_p2 | majeur_p1 | (0.00, 13.98, -0.36) | 2.78 | 2.78 | (1.00, 0.00, 0.00) | (0.00, 0.00, 1.00) |
| majeur_p3 | majeur_p2 | (0.00, 16.76, -0.36) | 2.24 | 2.24 | (1.00, 0.00, 0.00) | (0.00, 0.00, 1.00) |
| mc4 | poignet | (-0.95, 3.04, -0.16) | 5.97 | MC Bur. 5.97 | (0.98, 0.21, -0.00) | (0.00, 0.00, 1.00) |
| annulaire_p1 | mc4 | (-2.18, 8.88, -0.16) | 4.13 | 4.13 | (1.00, 0.10, -0.03) | (0.03, 0.00, 1.00) |
| annulaire_p2 | annulaire_p1 | (-2.58, 12.99, -0.16) | 2.57 | 2.57 | (0.99, 0.10, -0.07) | (0.07, 0.01, 1.00) |
| annulaire_p3 | annulaire_p2 | (-2.83, 15.54, -0.16) | 2.11 | 2.11 | (0.99, 0.10, -0.07) | (0.07, 0.01, 1.00) |
| mc5 | poignet | (-2.00, 2.94, 0.44) | 5.53 | MC Bur. 5.53 | (0.95, 0.32, -0.00) | (0.00, 0.00, 1.00) |
| auriculaire_p1 | mc5 | (-3.78, 8.18, 0.44) | 3.33 | 3.33 | (0.96, 0.24, -0.17) | (0.17, 0.04, 0.98) |
| auriculaire_p2 | auriculaire_p1 | (-4.58, 11.41, 0.44) | 1.84 | 1.84 | (0.96, 0.24, -0.14) | (0.14, 0.03, 0.99) |
| auriculaire_p3 | auriculaire_p2 | (-5.03, 13.19, 0.44) | 1.98 | 1.98 | (0.96, 0.24, -0.14) | (0.14, 0.03, 0.99) |

- bouts : index (2.85, 17.72, -0.11), majeur (0.00, 19.00, -0.36), annulaire (-3.03, 17.65, -0.16), auriculaire (-5.50, 15.11, 0.44), pouce (8.65, 10.30, 2.90) ; majeur à y = 19.00 (HL 19.0) ; index 17.72 / annulaire 17.65 (son index = son annulaire)
- arc des têtes : MCP y index -2.0, annulaire -4.0, auriculaire -11.0 mm sous le majeur ; voûte : flèche du majeur sur la corde II–V 4.5 mm
- pouce : CMC (3.20, 1.40, 0.30) ; MC I à 30.0° de MC II en 3D (dans le plan de la paume 31.0° contre 8.1°, élévation palmaire 20°) ; pronation de la pulpe 56° (0 = pulpe vers +Z, 90 = pulpe vers l’index ; reprise de MH : normale de son ongle) ; ongles MH repérés : 4/8/8/8/8 faces
- pronation de repos de P1–P2 du pouce : 75° chez MakeHuman, -18° → 56° (voir PRONATION_POUCE_DELTA : largeurs du pouce vu de face sur SON dessin)
- obliquité (LEAN -3.0/+0.0/+1.5/+10.0 ; LEAN_IP -4.0/+0.0/+4.0/+8.0) : poing (MCP 90 / IPP 105 / IPD 70, arc 0,6) — P1 inclinées de index -3.0° / majeur +0.0° / annulaire +3.0° / auriculaire +3.2° par rapport à la normale de la paume (+ vers le pouce) ; écart des bouts index–auriculaire 52.3 mm pour 59.6 mm entre MCP (rapport 0.88)
- obliquité (LEAN) : déport latéral du bout après 90° de flexion de la MCP (+ vers le pouce) : index -1.06 cm, majeur +0.00 cm, annulaire +1.07 cm, auriculaire +2.93 cm

<!-- étape 3 -->
### 3. Retaille aux proportions de l’utilisateur
- roulis des doigts MH (normale de la plaque d’ongle contre −Z) corrigé à la retaille : index -12.3°, majeur -3.8°, annulaire -4.3°, auriculaire +2.4°
- largeurs cibles des doigts = SON dessin au milieu du trait (mm, stations P1 / IPP / P2 / IPD / pulpe ; entre parenthèses les tables 4.1 de la version précédente) : index 17.9 / 17.8 / 16.0 / 15.9 / 14.9 (20.0 / 20.5 / 18.0 / 17.0 / 16.5) ; majeur 19.2 / 19.4 / 17.0 / 16.2 / 16.0 (21.0 / 21.0 / 18.5 / 17.5 / 17.0) ; annulaire 18.2 / 18.2 / 16.5 / 15.9 / 16.0 (19.5 / 19.5 / 17.0 / 16.5 / 16.0) ; auriculaire 17.8 / 17.2 / 16.1 / 15.8 / 14.9 (17.0 / 17.0 / 15.0 / 14.5 / 14.0) ; épaisseurs = largeur × e/l des tables 4.2
- 3a : écart de largeur max aux stations après une passe 0.6 mm, après rétroaction 0.1 mm
- pose « dessin » (angles des doigts et du pouce, descente par coordonnées sur l’IoU de la silhouette de face, 129 évaluations) : {"index": {"ab": 5.0}, "annulaire": {"ab": -3.8}, "auriculaire": {"ab": -27.8}, "pouce": {"rap": 4, "av": 2, "ip": -14}} ; IoU 0.9091
- 3b, champ 2D lissé sur le contour de la paume (milieu du trait du dessin), par itération : 243 sommets de contour, écart moyen 3.90 mm, max 9.65 mm, IoU 0.9086 ; 239 sommets de contour, écart moyen 0.42 mm, max 3.16 mm, IoU 0.9519 ; 245 sommets de contour, écart moyen 0.35 mm, max 2.30 mm, IoU 0.9535 ; 270 sommets de contour, écart moyen 0.32 mm, max 2.06 mm, IoU 0.9534 ; 288 sommets de contour, écart moyen 0.32 mm, max 1.82 mm, IoU 0.9536
- divergence du champ : médiane 0.000, max |div| 0.225 au sommet (-3.0, 0.3, -0.4) cm
- épaisseur suivant la divergence du champ (moitié) : facteur z 0.900..1.100
- superposition finale (pose « dessin ») : IoU 0.9536 ; contour de la paume (hors doigts et pouce libres) : écart moyen 0.47 mm, médian 0.25, 95e centile 1.58, MAX 4.80 mm ; doigts et pouce (largeurs anatomiques imposées, longueurs retenues) : moyen 1.03 mm, max 6.54 mm

<!-- étape 4 -->
### 4. Surface (Catmull-Clark ×2)
- (a) creux de la paume : 8.1 / 10.2 / 11.0 mm → 1.8 / 4.7 / 5.1 mm (bosse palmaire gaussienne de 13.1 mm au centre, σ 1.5 × 1.9 cm)
- (c) palmures : lissage de Taubin local sur 96 sommets autour des plis vifs des commissures
- (b) sections en trapèze arrondi sur les parties libres des doigts : τ = 0.07 (flancs : dos −7 %, paume +7 %), épaules du dos relevées de 10 % de la demi-épaisseur (effet mesuré dans le tableau ci-dessous, colonne dos/paume)
- 26610 sommets, 26608 quads → 53216 triangles à l’export (contrat : 20–25 k sommets) ; arête médiane 1.00 mm (min 0.13, max 19.15)
- pincements / plis de la surface au repos : angle entre faces voisines médian 3.6°, 99,9e centile 23.6°, max 63.3° ; arêtes > 30° : 19, > 60° : 1 (hors bord vif du poignet)

| doigt | station | largeur (mm) | cible (doigts : SON dessin, milieu du trait ; pouce : table 4.1) | épaisseur (mm) | cible (e/l des tables 4.2) | e/l | dos/paume (largeur à 25 % / 75 % de l’épaisseur) |
|---|---|---|---|---|---|---|---|
| index | P1 milieu | 17.9 | 17.9 | 15.3 | 15.2 | 0.85 | 0.93 |
| index | IPP | 17.9 | 17.8 | 15.1 | 15.2 | 0.84 | 0.91 |
| index | P2 milieu | 16.2 | 16.0 | 13.5 | 13.3 | 0.83 | 0.89 |
| index | IPD | 16.0 | 15.9 | 13.6 | 13.5 | 0.85 | 0.91 |
| index | pulpe | 14.8 | 14.9 | 12.1 | 11.7 | 0.82 | 1.03 |
| majeur | P1 milieu | 19.4 | 19.2 | 16.6 | 16.5 | 0.86 | 0.85 |
| majeur | IPP | 19.5 | 19.4 | 16.6 | 16.6 | 0.85 | 0.89 |
| majeur | P2 milieu | 17.3 | 17.0 | 14.4 | 14.2 | 0.83 | 0.84 |
| majeur | IPD | 16.4 | 16.2 | 13.9 | 13.9 | 0.85 | 0.89 |
| majeur | pulpe | 15.8 | 16.0 | 13.1 | 12.7 | 0.83 | 1.08 |
| annulaire | P1 milieu | 18.3 | 18.2 | 15.6 | 15.4 | 0.85 | 0.92 |
| annulaire | IPP | 18.4 | 18.2 | 15.9 | 15.9 | 0.86 | 0.92 |
| annulaire | P2 milieu | 16.7 | 16.5 | 13.8 | 13.6 | 0.82 | 0.88 |
| annulaire | IPD | 16.0 | 15.9 | 13.5 | 13.5 | 0.84 | 0.88 |
| annulaire | pulpe | 15.9 | 16.0 | 12.7 | 12.5 | 0.80 | 1.02 |
| auriculaire | P1 milieu | 17.7 | 17.8 | 15.3 | 15.1 | 0.86 | 0.95 |
| auriculaire | IPP | 17.4 | 17.2 | 15.2 | 15.2 | 0.87 | 0.90 |
| auriculaire | P2 milieu | 16.3 | 16.1 | 13.5 | 13.4 | 0.83 | 0.87 |
| auriculaire | IPD | 15.9 | 15.8 | 13.0 | 13.0 | 0.82 | 0.89 |
| auriculaire | pulpe | 14.8 | 14.9 | 11.8 | 11.7 | 0.80 | 1.06 |
| pouce | P1 milieu | 23.0 | 23.0 | 19.0 | 19.0 | 0.83 | 0.94 |
| pouce | P1 3/4 | 22.5 | 22.5 | 18.5 | 18.5 | 0.82 | 0.90 |
| pouce | IP | 22.0 | 22.0 | 17.6 | 17.5 | 0.80 | 0.85 |
| pouce | P2 1/3 | 21.9 | 22.0 | 16.9 | 17.0 | 0.77 | 0.93 |
| pouce | pulpe | 21.1 | 21.0 | 16.0 | 16.0 | 0.76 | 1.09 |

- bouts en goutte (profil sagittal de la dernière phalange) : index : dos rectiligne à 0.43 mm près, pulpe 7.2 mm sous l’axe contre dos 5.8 mm au-dessus (rapport 1.23), bout à -0.2 mm au-delà de l’axe ; majeur : dos rectiligne à 0.37 mm près, pulpe 7.5 mm sous l’axe contre dos 6.1 mm au-dessus (rapport 1.23), bout à -1.1 mm au-delà de l’axe ; annulaire : dos rectiligne à 0.43 mm près, pulpe 7.3 mm sous l’axe contre dos 5.8 mm au-dessus (rapport 1.25), bout à 0.6 mm au-delà de l’axe ; auriculaire : dos rectiligne à 0.17 mm près, pulpe 6.9 mm sous l’axe contre dos 5.6 mm au-dessus (rapport 1.24), bout à 0.5 mm au-delà de l’axe ; pouce : dos rectiligne à 0.57 mm près, pulpe 9.6 mm sous l’axe contre dos 7.4 mm au-dessus (rapport 1.31), bout à 1.3 mm au-delà de l’axe
- creux de la paume (profil palmaire à travers la paume) : y = 4.5 cm : thénar z = 2.65, hypothénar 1.60, creux 1.42 → profondeur 1.8 mm ; y = 5.5 cm : thénar z = 2.22, hypothénar 1.53, creux 1.07 → profondeur 4.7 mm ; y = 6.5 cm : thénar z = 1.51, hypothénar 1.60, creux 1.00 → profondeur 5.1 mm (anatomie.md § 4.3 : 3–5 mm au repos)
- épaisseur de la paume aux têtes métacarpiennes (y ≈ 8,6 cm, x ∈ [−2 ; 1]) : 33.2 mm (anatomie : 30 ± 3) ; au poignet (y = 0) : 39.2 mm × 61.1 mm de large (40 × 60–66)

<!-- étape 5 -->
### 5. Poids (default_weights.mhw nettoyés)
- poids MH interpolés par l’opérateur de subdivision (positifs, somme 1) : 1 à 10 os par sommet (histogramme 1→10 : [2635, 10242, 6197, 2528, 2163, 2005, 756, 70, 13, 1])
- avant-bras / main : poids de l’os « poignet » sur la paume (y > 0.8 cm) : 0.94 dans MH → 0.00 ; zone de passage y ∈ [-1.2 ; 0.8] cm
- partage des chaînes recentré sur les centres cibles (demi-largeurs de mélange : MCP 0.70, IPP 0.45, IPD 0.35, MCP du pouce 0.60, IP 0.40 cm) ; palmures lissées sur 2483 sommets
- résultat : os par sommet [12277, 9495, 2471, 2367] (1, 2, 3, 4) ; somme des poids 1.000000..1.000000 ; poids retiré par la coupe à 4 os : max 0.121
- 1er métacarpien limité au thénar (au-delà du trapèze ; rampe radiale de 3,0 à 1,2 cm de son axe) : jusqu’à 0.82 de poids rendu aux os voisins ; 4e et 5e métacarpiens limités à la paume au-delà de leur base : jusqu’à 0.86 rendu au 3e

<!-- étape 6 -->
### 6. Régions et ongles
- la plaque MakeHuman (topologie hm08, repérée à l’étape 2 ; EN CREUX de 0,8 mm) est remplacée par un champ de déplacement LISSE : peau de référence (creux MH comblé par interpolation biharmonique), plaque = cylindre de rayon R calé sur la référence + 0.42 mm (cuticule : 0.17 mm), raccord biharmonique sur 1,5 mm ; bord libre à l’hyponychium (dos qui plonge à plus de 35°) + 1.2 mm de frange ; ongle rigide (rampe de poids vers 1,0 sur P3)

| doigt | plaque MH l × L (mm) | largeur (mm) | / doigt à l’IPD | longueur (mm) | / P3 | R cible (mm) | R mesuré | inclinaison de la plaque / axe de P3 (°) | relief moyen sur la peau de référence (mm) | repli latéral au-dessus du bord de la plaque (mm) | bord libre décollé de la peau (mm) | déplacement max (mm) | sommets de plaque |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| index | 8.0 × 10.2 | 11.1 | 0.70 | 11.1 | 0.54 | 8.9 | 8.8 | 14.9 | 0.52 | 0.16 | 1.15 | 1.29 | 353 |
| majeur | 8.5 × 9.6 | 12.0 | 0.74 | 12.0 | 0.54 | 8.8 | 8.8 | 13.0 | 0.48 | 0.36 | 1.24 | 1.56 | 457 |
| annulaire | 8.8 × 9.4 | 11.4 | 0.72 | 11.4 | 0.54 | 7.3 | 7.5 | 12.7 | 0.51 | 0.64 | 1.60 | 1.65 | 372 |
| auriculaire | 7.7 × 6.3 | 11.0 | 0.70 | 11.0 | 0.56 | 5.8 | 5.9 | 10.1 | 0.28 | 0.78 | 0.74 | 1.62 | 573 |
| pouce | 11.3 × 10.8 | 15.8 | 0.72 | 15.2 | 0.54 | 11.4 | 12.1 | 9.6 | 0.38 | 0.35 | 1.43 | 1.68 | 272 |

- surface APRÈS les ongles (triangles exportés, diagonale la plus courte ; hors bord vif du bouchon du poignet) : arêtes > 30° : 34, > 45° : 7, > 60° : 3, > 90° : 0, max 69.4° ; triangles retournés : 0 (étape 4 : > 60° : 3, max 69.4°) ; arêtes > 60° restantes : (-3.3, 9.7, 0.6), (-3.3, 9.6, 0.4), (-3.3, 9.7, 0.6)
- régions : peau 22286, plaque 1597, frange 430, repli 850, palmure 1447 sommets

<!-- étape 7 -->
### 7. Plis
- 44 courbes de plis (1739 points), points à 0.000 mm au plus de la surface : index_digital_proximal (33), index_moyen_a (35), index_moyen_b (33), index_distal (27), majeur_digital_proximal (37), majeur_moyen_a (38), majeur_moyen_b (35), majeur_distal (28), annulaire_digital_proximal (34), annulaire_moyen_a (36), annulaire_moyen_b (32), annulaire_distal (27), auriculaire_digital_proximal (34), auriculaire_moyen_a (34), auriculaire_moyen_b (33), auriculaire_distal (26), ip_pouce_dos_a (26), ip_pouce_dos_b (26), paume_distal (128), paume_proximal (144), paume_thenar (161), pouce_base_1 (33), pouce_base_2 (36), pouce_mcp (26), pouce_ip_1 (18), pouce_ip_2 (21), poignet_distal (122), poignet_proximal (98)
- positions mesurées sur la surface : index : proximal à 0.50 de P1, moyen 3.0 mm avant l’IPP, distal 3.0 mm avant l’IPD (pli IPD → bout / pli IPP → pli IPD = 1.00 ; sa photo 0,98) ; majeur : proximal à 0.50 de P1, moyen 3.0 mm avant l’IPP, distal 4.2 mm avant l’IPD (pli IPD → bout / pli IPP → pli IPD = 1.00 ; sa photo 0,98) ; annulaire : proximal à 0.50 de P1, moyen 3.0 mm avant l’IPP, distal 3.8 mm avant l’IPD (pli IPD → bout / pli IPP → pli IPD = 1.00 ; sa photo 0,98) ; auriculaire : proximal à 0.50 de P1, moyen 3.0 mm avant l’IPP, distal 0.8 mm avant l’IPD (pli IPD → bout / pli IPP → pli IPD = 1.00 ; sa photo 0,98)

<!-- étape 8 -->
### 8. Butées, poses, contacts et correctifs des jointures
- pose « dessin » réajustée sur la main finale (poids et ongles compris) : IoU de la silhouette de face avec son dessin 0.9550 (grille 0,25 mm) ; angles {"index": {"ab": 5.0}, "annulaire": {"ab": -3.8}, "auriculaire": {"ab": -27.8}, "pouce": {"rap": 4, "av": 3, "ip": -15, "mcp": 1}}
- superposition de la main LIVRÉE (pose « dessin ») : contour de la paume écart moyen 0.43 mm, médian 0.25, max 4.2 mm ; doigts et pouce : moyen 1.0 mm, max 6.5 mm (checks/e8_dessin.png)

| jointure | angle de référence | rayon dorsal au repos (mm) | LBS (mm) | DQS (mm) | DQS + correctif (mm) | saillie (mm) | déplacement max (mm) |
|---|---|---|---|---|---|---|---|
| MCP index | 90° | 9.6 | 6.7 | 9.5 | 13.1 | +3.5 | 5.5 |
| MCP majeur | 90° | 12.9 | 9.0 | 12.7 | 16.4 | +3.5 | 5.5 |
| MCP annulaire | 90° | 12.4 | 8.6 | 12.2 | 15.9 | +3.5 | 5.5 |
| MCP auriculaire | 90° | 9.8 | 6.6 | 9.3 | 13.2 | +3.5 | 6.9 |
| PIP index | 100° | 6.8 | 4.3 | 6.8 | 9.3 | +2.5 | 2.5 |
| PIP majeur | 100° | 7.4 | 4.7 | 7.3 | 9.9 | +2.5 | 2.7 |
| PIP annulaire | 100° | 7.1 | 4.6 | 7.1 | 9.6 | +2.5 | 2.6 |
| PIP auriculaire | 100° | 6.8 | 4.3 | 6.7 | 9.3 | +2.5 | 2.7 |

- correctifs : rayon dorsal mesuré sur la bissectrice de la jointure (centre articulaire → peau) ; saillie = rayon posé avec correctif − rayon au repos ; cible 3.5 mm à la MCP, 2.5 mm à l’IPP ; coussinets palmaires 6.0 / 2.5 mm
- 9e correctif « commissure_abd » (palmure de la 1re commissure, poids clamp(pouce.rap / -28, 0, 1)) : calculé dans la pose pouce rap = -28 ; apex de la commissure à 28.3 mm de la MCP du pouce, ramené vers elle de 15.4 mm au plus, 2522 sommets

| pose | pénétration max DQS + correctifs (mm) | paires > 0,3 mm (mm) | LBS sans correctif : max (mm) |
|---|---|---|---|
| repos | 0.0 | aucune | 0.0 |
| dessin | 0.0 | aucune | 0.0 |
| poing | 2.6 | index_bout/paume 2.6, pouce/index 0.8, pouce/majeur 0.4 | 2.3 |
| V | 2.3 | annulaire_bout/paume 2.3, pouce/auriculaire 1.7, annulaire/auriculaire 1.0 | 2.2 |
| poing (avant relecture) | 5.2 | pouce/annulaire 5.2, pouce/majeur 4.0, auriculaire_bout/paume 2.9, annulaire_bout/paume 1.8, annulaire/auriculaire 0.9, index/majeur 0.6, pouce/auriculaire 0.5 | 5.0 |
| V (avant relecture) | 7.7 | pouce/annulaire 7.7, pouce/auriculaire 2.7, annulaire/auriculaire 2.3, auriculaire_bout/paume 1.5 | 7.6 |
| rapprocher | 0.0 | aucune | 0.0 |
| opposition | 0.0 | aucune | 0.0 |
| arc | 0.0 | aucune | 0.0 |
| rapprocher_sans_vis | 7.6 | pouce/paume 7.6 | 7.4 |

- tunnel du poing vu de profil côté pouce (jour à travers la boucle de l’index) : LBS 129 mm² (16.0 × 11.8 mm), DQS 129 mm², DQS + correctifs 74 mm² (12.0 × 8.6 mm)
- tunnel du poing (avant relecture) vu de profil côté pouce (jour à travers la boucle de l’index) : LBS 271 mm² (22.2 × 26.0 mm), DQS 216 mm², DQS + correctifs 148 mm² (15.6 × 16.4 mm)
- pose « repos » : dans les butées actives et les couplages (R2, IPD–IPP, vis sans fin)
- pose « dessin » : dans les butées actives et les couplages (R2, IPD–IPP, vis sans fin)
- pose « poing » : dans les butées actives et les couplages (R2, IPD–IPP, vis sans fin)
- pose « V » : dans les butées actives et les couplages (R2, IPD–IPP, vis sans fin)
- pose « rapprocher » : dans les butées actives et les couplages (R2, IPD–IPP, vis sans fin)
- pose « opposition » : dans les butées actives et les couplages (R2, IPD–IPP, vis sans fin)
- pose « arc » : dans les butées actives et les couplages (R2, IPD–IPP, vis sans fin)
- pose « rapprocher_sans_vis » : HORS butées : pouce.vis (av < 0,7·rap)

<!-- étape 9 -->
### 9. Export GLB et hand_v2.json
- export bpy (export_yup = False : les axes du contrat passent tels quels) ; repères des os dans Blender = repères voulus à 1.3e-06 près
- relu : 26610 sommets (pipeline 26610, appariés à 9.6e-07 cm près, permutation identité), 53216 triangles (100 % triangles), 20 os nommés comme le contrat ; attributs JOINTS_0, NORMAL, POSITION, WEIGHTS_0, _MASQUES, _ONGLE, _REGION ; matrice du nœud du maillage = identité à 0.0e+00 près
- os relus : repère monde de chaque nœud = (axes, centre) voulus à 2.5e-06 près ; liaison⁻¹ × monde = identité à 3.9e-06 près ; poids relus = poids du pipeline à 1.1e-07 près (≤ 4 os, somme 1.0000..1.0000)
- morph targets relus : 9 (mcp_index, mcp_majeur, mcp_annulaire, mcp_auriculaire, pip_index, pip_majeur, pip_annulaire, pip_auriculaire, commissure_abd), attributs NORMAL/POSITION ; déplacements = correctifs du pipeline à 9.5e-07 cm près
- surface du GLB au repos (ses 53216 triangles, identiques à ceux des mesures) : arêtes > 30° : 34, > 60° : 3, > 90° : 0, max 69.4° (hors bord vif du bouchon du poignet) ; triangles retournés : 0
- plis convertis en barycentriques sur les triangles du GLB : 44 courbes, écart max point ↔ surface 0.0000 mm
- hand_v2.glb : 3215 Ko ; hand_v2.json : 143 Ko

<!-- étape 10 -->
### 10. Contrôles

| pose | LBS : arêtes devenues > 60° / triangles retournés | DQS | DQS + correctifs |
|---|---|---|---|
| repos | 3 / 0 | 3 / 0 | 3 / 0 |
| dessin | 0 / 0 | 0 / 0 | 0 / 0 |
| poing | 167 / 5 | 448 / 9 | 508 / 21 |
| V | 113 / 9 | 213 / 8 | 236 / 12 |
| rapprocher | 21 / 0 | 24 / 3 | 24 / 3 |
| opposition | 81 / 7 | 80 / 4 | 90 / 5 |
| arc | 20 / 0 | 20 / 0 | 20 / 0 |
| rapprocher_sans_vis | 20 / 1 | 19 / 0 | 19 / 0 |

- lecture : les arêtes nouvelles > 60° d’une pose fléchie sont surtout les plis PALMAIRES (la peau se replie au pli de flexion, c’est un vrai pli) ; un triangle retourné est une peau qui se traverse : ils sont au fond de ces plis
- poing (DQS + correctifs) : distance de l’extrémité de l’axe de chaque doigt à la peau de la paume : index 2.3 mm, majeur 6.3 mm, annulaire 3.6 mm, auriculaire 1.8 mm (demi-épaisseur de la pulpe 5,5–6,8 mm : le bout appuie)
- 78 rendus Cycles (CPU, 20 à 32 échantillons) en 328 s : e10_cycles.jpg, e10_pouce.jpg, e8_correctifs.jpg, e10_bouts.jpg, e10_gros_plans.jpg, e10_signes.jpg, e10_jointures_dos.jpg
- three.js r128 (GLTFLoader) : 1 SkinnedMesh, 20 os (noms du contrat : oui), 26610 sommets, 53216 triangles, attributs _region, _ongle, _masques, position, normal, skinIndex, skinWeight, color, morphTarget0, morphNormal0, morphTarget1, morphNormal1, morphTarget2, morphNormal2, morphTarget3, morphNormal3, morphTarget4, morphNormal4, morphTarget5, morphNormal5, morphTarget6, morphNormal6, morphTarget7, morphNormal7 ; régions (sommets) [22286, 1597, 430, 850, 1447] ; index_p1.rotateX(90°) : bout de l’index (2.85, 17.72, -0.11) → (1.79, 9.11, 8.54) cm — checks/e10_three.png
<!-- MESURES AUTOMATIQUES : FIN -->
