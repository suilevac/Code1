# Dossier « personnage » — le référent (tronc + tête, sans bras), hommage stylisé à Piccolo

Palier v2 de l'Atelier des mains LSF. Dossier de recherche et de conception, pas de code.
Images, SVG et scripts : `/tmp/claude-0/-home-user-Code1/1652bac3-cb8e-5b75-b942-b710d61c6a62/scratchpad/v2/recherche/personnage/`
(sous-dossiers `svg/` et `iterations/` ; générateur `gen.py`, rendu `rendu_svg.py`).

Conditions de travail à connaître : dans ce conteneur, WebFetch ne résout **aucun** hôte (fandom, wikipedia, elix, lsfdico,
spreadthesign, w3.org, openedition, aclanthology : `ENOTFOUND` à chaque fois) et `images.unsplash.com` est refusé par le
proxy (403). Les faits ci-dessous viennent donc des **extraits renvoyés par WebSearch** (cités avec leur URL) et, quand c'est
dit explicitement, de ma connaissance générale (marquée « [connaissance, à vérifier] »). Aucune photo de référence n'a pu
être téléchargée ; les trois directions ont été dessinées et rendues ici même.

---

## 0. Le constat sur le référent actuel

`wf2/referent/avant_apres.png` (trois versions successives de `drawRef`, `source/script.js` l. 1113) :

| Ce qu'on voit | Pourquoi c'est « affreux » |
|---|---|
| Calotte de cheveux en demi-dôme, puis frange à festons | Lit « casque » ou « perruque » ; c'est le seul élément qui donne une identité et il n'en donne aucune |
| Bras-moignons qui descendent le long du corps, coupés au coude | Des bras sans avant-bras ni mains : l'œil cherche les mains au bout des bras et ne les trouve pas **là**, il les trouve devant la poitrine ; contradiction |
| Tronc = trapèze, cou = tube, tête = ovale | « Pile de formes géométriques » (grief déjà noté dans CLAUDE.md) |
| Visage : deux yeux en amande, un nez, une bouche-sourire | Aucune expression possible, or l'expression est un paramètre du signe (voir §3) |
| Buste gris-vert (#dbe8e6) sous une main verte | Main et buste sont dans la même famille de teinte ; le contraste ne tient que par le trait |

Le point de départ de la v2 est donc : **retirer les bras, garder tronc + tête, donner une identité (hommage à Piccolo),
rendre le visage expressif, et faire du tronc une surface calme et contrastée sur laquelle les mains se lisent.**

---

## 1. Piccolo : ce qui le rend reconnaissable, et ce qu'on peut en reprendre

### 1.1 Faits sur le personnage

| Fait | Valeur | Source |
|---|---|---|
| Créateur / éditeur / studio | Akira Toriyama (Bird Studio) ; manga publié par Shueisha ; anime par Toei Animation | [Wikipedia EN (extrait WebSearch)](https://en.wikipedia.org/wiki/Piccolo_(Dragon_Ball)) ; marque « TOEI ANIMATION » US n° 3908315 classes 9, 16, 25, 28, 30, 38, 41 [Justia](https://trademarks.justia.com/772/54/toei-77254973.html) |
| Première apparition | Piccolo Daimaō, chapitre 135, août 1987 ; « designed to appear as a strange-looking divine creature, who had pointy ears, antennae, fangs and four-fingers » | [extrait WebSearch, Wikipedia EN](https://en.wikipedia.org/wiki/Piccolo_(Dragon_Ball)) |
| Piccolo Jr. | « roughly the same as Piccolo Daimao, but with a more solid facial structure » ; le kanji du gi est abandonné | idem |
| Doigts | 4 dans le manga, 5 dans l'anime | [manga.fandom (extrait)](https://manga.fandom.com/wiki/Piccolo_(Dragon_Ball)) |
| Race | Namek : « green-skinned, tall, and hairless » ; nom = jeu de mots sur *namekuji* (limace), à cause des antennes | [manga.fandom (extrait)](https://manga.fandom.com/wiki/Piccolo_(Dragon_Ball)) ; [chise.org miroir Wikipedia](https://www.chise.org/ipfs/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco/wiki/Makankosappo.html) |
| Antennes | « sit at the top-back of the forehead and curve backward, then forward » ; d'ordinaire cachées sous le turban | [guide de dessin (extrait, qualité faible)](https://slbubble.studentbridge.com/celebnews162/7-secrets-to-drawing-piccolo-master-his-classic-dbz-look-and-new-orange-form-q32j2.html) ; [thegamer](https://www.thegamer.com/dragon-ball-weird-things-piccolo-anatomy/) |
| Oreilles | « large, pointed ears », trait namek définitoire ; Daima en fait la preuve de l'origine « Demon Realm » | idem ; [espinof](https://www.espinof.com/anime/dragon-ball-daima-desvela-verdadero-origen-piccolo-namekianos-akira-toriyama-da-marcha-atras-nuevo-anime-pequeno-detalle) |
| Tenue | gi violet lesté, cape blanche « heavy and thick, with deep, angular folds at the shoulders and neck », turban blanc « large and billowy » ; vêtements lestés retirés pour combattre | [toyhypeusa](https://toyhypeusa.com/2021/02/16/tamashii-nations-sh-figuarts-dragon-ball-z-piccolo-figure-review/) ; [thenostalgiaspot](https://thenostalgiaspot.com/2021/09/07/s-h-figuarts-piccolo-the-proud-namekian/) |
| Stabilité du design | « kept essentially the same look through many fusions and power-ups » | [thenostalgiaspot](https://thenostalgiaspot.com/2021/09/07/s-h-figuarts-piccolo-the-proud-namekian/) |
| Taille / poids officiels | 226 cm / 116 kg selon les listes de fans ; 223,5 cm / 115,6 kg sur MyAnimeList ; la liste qui cite le Daizenshuu 7 (1996) n'a pas pu être lue | [esportstales](https://esportstales.com/dragon-ball/characters-official-heights-and-weights) ; [MAL](https://myanimelist.net/character/914) |
| Taches roses sur les bras, arcade saillante | **Non confirmé** par les extraits (un wiki de fans parle de « pale yellow patches »). [connaissance, à vérifier] : les taches roses sur les avant-bras et les muscles sont bien dans le manga et l'anime | [fandomwire](https://fandomwire.com/they-get-their-energy-via-photosynthesis-akira-toriyama-hid-the-biggest-secret-about-the-namekians-right-in-front-of-dragon-ball-fans-faces/) |

### 1.2 Ce qui fait « Piccolo » graphiquement (analyse)

Dans l'ordre de ce que l'œil reconnaît en premier, à petite taille (test de silhouette : « fill the character with solid
black and check whether it is still recognizable from its outline alone », à 32 × 32 px —
[rocketbrush](https://rocketbrush.com/blog/shape-language-in-game-character-design-how-to-make-characters-readable-and-consistent),
[bugnet](https://bugnet.io/blog/character-design-basics-for-indie-devs)) :

| Rang | Trait | Nature | Lisible à 200 px ? | Repris dans nos directions |
|---|---|---|---|---|
| 1 | **Épaulettes massives et carrées** de la cape : silhouette en T inversé | silhouette | oui | A (coins arrondis), C (pointes) |
| 2 | **Oreilles pointues** longues, vers le haut et l'extérieur | silhouette | oui | A, B, C |
| 3 | **Deux antennes** sur le front | silhouette | oui | A, B, C (toutes visibles : Piccolo les cache sous le turban → déjà un écart) |
| 4 | **Crâne nu**, tête allongée, menton court | forme | oui | A, B, C |
| 5 | Teint vert | couleur | oui | vert clair de peau, main en vert INJS |
| 6 | **Arcade sourcilière** en masse noire, regard dur, bouche fine | détail du visage | à 600 px seulement | A, C (B : sourcils en trait simple) |
| 7 | Turban blanc | silhouette | oui, mais cache oreilles et antennes | C seulement |
| 8 | Gi violet, ceinture rouge, cape blanche | couleur | oui | A, C (B : tunique violette seule) |
| 9 | Taches roses, crocs, 4 doigts, plis du vêtement lesté | détails | non | **jamais** (c'est là que commence la copie) |

Règle tirée de la hiérarchie : l'identité tient dans les rangs 1-5 (silhouette + couleur). Tout ce qui est en dessous est
du détail qui ne se lit pas à l'échelle d'une planche de classe et qui, en plus, rapproche de la contrefaçon.

### 1.3 Droit : hommage, pas copie

| Point | Règle | Source |
|---|---|---|
| Un personnage est protégé par le droit d'auteur | Les exceptions sont une liste fermée : courte citation, parodie, caricature, pastiche (CPI L.122-5 4°) | [Legavox](https://www.legavox.fr/blog/maitre-anthony-bem/parodie-pastiche-caricature-uvre-auteur-6321.htm) ; [village-justice](https://www.village-justice.com/articles/droit-propriete-intellectuelle-autorise-les-parodies,35755.html) |
| L'exception de parodie suppose l'humour | « en l'absence de dérision, de ridicule ou d'un véritable effet humoristique, cette exception ne peut être invoquée » (CA Aix-en-Provence, 18 déc. 2025, Tintin) ; un simple hommage ne suffit pas | [blip.education](https://blip.education/protection-du-personnage-tintin-par-le-droit-dauteur-face-aux-createurs-contemporains) |
| Fan art = œuvre dérivée | « nécessite en principe l'accord de l'auteur » ; contrefaçon « lorsque les emprunts sont massifs et directement identifiables » | [mymangaacademia](https://mymangaacademia.fr/les-fanart-sont-il-legal-en-france/) ; [apprendre-a-dessiner](https://www.apprendre-a-dessiner.org/dessin-fanart-legal/) |
| Toei et les œuvres de fans | Pas de décision trouvée sur un personnage dérivé ; mises en demeure contre des fansubs (Toei Europe, 2015) ; les jeux de fans seraient tolérés (affirmation de forum, non vérifiée) | [kanzenshuu forum](https://www.kanzenshuu.com/forum/viewtopic.php?p=967337) |
| Marques | « TOEI ANIMATION » enregistrée (US 3908315). Aucune marque « Piccolo » trouvée ; registre EUIPO non consulté | [Justia](https://trademarks.justia.com/772/54/toei-77254973.html) |

**Conséquence pour nous** (raisonnement, pas avis d'avocat) : ce qui est protégé, c'est la *combinaison* des traits
caractéristiques, pas l'idée « extraterrestre vert à oreilles pointues » (idée libre). Un personnage ORIGINAL inspiré est
défendable si :
1. il ne porte **ni le nom, ni le kanji, ni aucun logo** Dragon Ball ;
2. il modifie la combinaison : **antennes toujours visibles** (pas de turban qui les cache ; en C le turban les laisse
   sortir), antennes **courtes et charnues qui partent vers l'extérieur** (Piccolo : longues, en arrière), **épaulettes
   d'une autre coupe** (coins arrondis montant vers l'extérieur, pas le bloc carré), **col rond + petit V** au lieu du gi
   croisé, **cinq doigts** (ce sont les mains de l'utilisateur), **vert INJS** et vert d'eau au lieu du vert franc, **pas
   de taches roses, pas de crocs, pas de plis de vêtement lesté** ;
3. la cape et la ceinture restent des **vêtements génériques** (une cape à épaulettes existe hors Dragon Ball) ;
4. l'usage est pédagogique et non commercial — ce qui n'est **pas** une exception légale, mais réduit le risque pratique.
Ce que l'utilisateur garde réellement de Piccolo : la **tenue d'esprit** (sérieux, calme, regard droit), la **silhouette en
T** (épaulettes), le **crâne nu à antennes et oreilles pointues**, le **vert**. C'est assez pour que lui le reconnaisse,
pas assez pour que ce soit le personnage de Toriyama.

---

## 2. Comment les supports LSF représentent le signeur

### 2.1 Les dictionnaires vidéo

| Dictionnaire | Ce qu'on sait | Source |
|---|---|---|
| **Elix** (Signes de Sens, 2010) | 15 300 à 21 000 signes, deux vidéos par entrée (signe + définition signée) ; appli : « définition en LS à gauche, définition écrite au centre, signe(s) à droite » ; Signes de Sens a proposé de passer ses vidéos en CC-BY-SA pour Wikimedia | [handicap.fr](https://informations.handicap.fr/a-dico-vivant-traduit-francais-en-langue-des-signes-13286.php) ; [bepep.insei.fr](https://bepep.insei.fr/mod/resource/view.php?id=880) ; [meta.wikimedia](https://meta.wikimedia.org/wiki/Wikimedia_France/Groupes_de_travail/Groupes_th%C3%A9matiques/Langues/LSF) |
| **Spread the Sign** | « une petite vidéo avec le mot dit en langue des signes par un comédien », vidéos comparables côte à côte, 15 000 signes par langue ; « il n'est pas permis de télécharger ou d'utiliser nos vidéos » | [outilstice](https://outilstice.com/2018/10/spreadthesign-dictionnaire-international-des-langues-de-signes/) ; [spreadthesign about](https://spreadthesign.com/en.us/about/) |
| **LSFdico INJS Metz** | site de l'INJS de Metz, recherche par mot, vidéos de signes citées par d'autres lexiques (« Web LSF Lexique - INJS METZ ») ; aucune page lisible ici | [theinterpretersfriend](https://theinterpretersfriend.com/indj/cty/france.html) ; [sw-l 2012](https://listserv.linguistlist.org/pipermail/sw-l/2012-August/057563.html) |
| **IVT** (Moody et al., 1983 → *La langue des signes*, 2 tomes, 4 500 signes dessinés) | « la plupart des signes de la LSF contemporaine proviennent de dictionnaires produits par IVT » ; les vignettes figuratives d'IVT servent de couche illustrée à une base lexicale universitaire | [Gallaudet UP](https://ssl.gallaudet.edu/gupress/excerpts/HEDASLpreface.pdf) ; [Fnac](https://www.fnac.com/a932065/Bill-Moody-La-langue-des-signes-Tome-1-Introduction-a-l-histoire-et-a-la-grammaire-de-la-langue-des-signes-Entre-les-mains-des-sourds) ; [univ-lyon2](https://perso.univ-lyon2.fr/~bonucci/IMG/pdf/PlanCom.pdf) |
| Lexiques dessinés | premiers lexiques de signes dessinés édités en France dans les années 1850 ; dictionnaire d'astronomie LSF : « chaque entrée est accompagnée d'un dessin du signe » | [CNRS mshmondes](https://www.mshmondes.cnrs.fr/?p=12394) ; [Observatoire de Paris](https://observatoiredeparis.psl.eu/un-dictionnaire-international.html) |

[connaissance, à vérifier sur les sites] : Elix cadre le signeur **de la taille au-dessus de la tête, de face, sur fond
uni clair**, vêtement sombre ; Spread the Sign cadre **de la poitrine à la tête, fond gris foncé uni**, vêtement noir ;
les planches IVT sont des **dessins au trait d'un buste de face avec les bras**, flèches de mouvement, visage neutre ou
expressif selon le signe. Aucune source trouvée ne montre de référent **sans bras** dans un dictionnaire ; ce sont les
**pictogrammes** et icônes LSF (sites, affiches) qui isolent les mains (parfois avec une tête). Le buste sans bras de
l'atelier est donc une convention à **inventer proprement**, pas à copier.

### 2.2 Règles de cadrage et d'espace (vidéo, transposables au dessin)

| Règle | Chiffre / énoncé | Source |
|---|---|---|
| Cadrage | « framed from the waist up » ; plan moyen « lets viewers see all hand movements, facial expressions, and upper body language » | [EQui-T checklist](https://static.uni-graz.at/fileadmin/_files/_cooperation_sites/_equi-t/FAQs_Recommendations_Short_Checklist_AlleSprachen_Maerz2026/24.03.2026_Short_Checklist/EN_03.2026_Short_Checklist/EN_4.4.2_Short_checklist_deaf_learners_Sign_language.pdf) ; [EQui-T recommandations](https://static.uni-graz.at/fileadmin/_files/_cooperation_sites/_equi-t/FAQs_Recommendations_Short_Checklist_AlleSprachen_Maerz2026/24.03._Recommendations_Gesamt_und_einzelne_Dimensionen/EN_03.2026_Recommendations/EN_4.4.2_Recommendations_deaf_learners_Sign_language.pdf) |
| Espace de signation | « extends from well below the waist to above the head » (W3C) ; « du sommet de la tête jusqu'aux hanches, et d'une épaule à l'autre » (OQLF, LSQ/ASL) | [W3C WAI](https://www.w3.org/WAI/media/av/sign-languages) ; [OQLF espace de signation](https://vitrinelinguistique.oqlf.gouv.qc.ca/fiche-gdt/fiche/26571053/espace-de-signation) |
| Fond | « background and the signer's clothing are solid colors that contrast with their skin tone » ; mur uni, sans distraction | [W3C WAI](https://www.w3.org/WAI/media/av/sign-languages) ; [signdict](https://signdict.org/recorder/5) ; [ASL guidelines](https://media.asldeafined.com/wp-content/uploads/2025/06/18182821/ASL_Video_Recording_Guidelines.docx.pdf) |
| Lieux d'articulation cités | espace neutre, espace d'épellation, **front, menton, oreille, poitrine, épaule** ; un signe peut aller « du front vers le menton » | [OQLF lieu d'articulation](https://vitrinelinguistique.oqlf.gouv.qc.ca/fiche-gdt/fiche/26570974/lieu-darticulation) |
| Paramètres du signe | configuration, orientation, mouvement, emplacement « exprimés simultanément » ; « le regard, l'expression du visage, le mouvement du corps et celui des lèvres viennent compléter ces paramètres, sans être toujours activés » | [programme LSF L2, education.gouv.fr](https://www.education.gouv.fr/sites/default/files/document/Programme%20de%20langue%20des%20signes%20fran%C3%A7aise,%20langue%20seconde%20(LSF%20L2),%20de%20seconde,%20premi%C3%A8re%20et%20terminale%20des%20voies%20g%C3%A9n%C3%A9rales%20et%20technologique,%20enseignement%20optionnel-290817.pdf) ; [UGA éditions ch. 2](https://books.openedition.org/ugaeditions/30910) |
| Paire minimale par l'expression | MAL-AU-CŒUR / CONTENT ne diffèrent que par l'expression faciale | [TAL 2007](https://aclanthology.org/2007.tal-3.3.pdf) |
| Sourcils | Majorité des sources grand public : **levés = question fermée (oui/non), froncés = question ouverte (qui/quoi/où…)** ; une source dit l'inverse ; aucune source linguistique lue. Thèse de référence : Chételat-Pelé 2010, *Les gestes non manuels en LSF… application aux mouvements des sourcils et aux clignements des yeux* (HAL tel-00547777) | [clic-campus](https://clic-campus.fr/vocabulaire-lsf/langue-des-signes-10-mots-essentiels-pour-debuter-facilement/) ; [docteurtamalou (inverse)](https://docteurtamalou.fr/langue-signes-francaise-5-infos-a-retenir/) ; [TALS thèses](https://tals.lisn.upsaclay.fr/en/theses/soutenues) |

Les lieux d'articulation manquants dans les extraits (tempe, joue, nez, bouche, cou, ventre, bras) sont d'usage courant
[connaissance] ; l'utilisateur, signeur natif, est la référence pour la liste finale des repères.

### 2.3 Ce qu'un buste SANS bras implique

Les mains flottent devant le torse. Pour que ça reste lisible, cinq conditions, toutes vérifiées sur les rendus :

1. **Le torse est une surface calme et contrastée** : un aplat (violet) + une ombre franche, zéro motif, zéro texte,
   sur lequel une main verte à contour noir se détache (contraste main/gi 2,65:1, main/cape 2,84:1, voir §4.3).
2. **La main garde son propre contour noir** : c'est déjà le cas (coque inversée) ; c'est lui qui fait la lecture quand la
   main passe devant le visage (contraste main/peau seulement 2,1:1, mais le trait de 1,3 à 3 px sépare).
3. **La main est TOUJOURS peinte par-dessus le référent** : déjà le cas (`#bgL` → 3D → `#fgL`). Le test « main au front »
   (`A_final_front_600.png`) montre les antennes qui traversent la main-témoin parce que le témoin est dans le SVG ; dans
   l'atelier la 3D passe devant, le problème n'existe pas.
4. **La cape explique l'absence de bras.** C'est l'argument décisif pour une cape à épaulettes : une cape COUVRE les
   bras, la silhouette est fermée, et « les mains sortent de sous la cape » est une lecture naturelle. Avec un tee-shirt
   (référent actuel) l'absence de bras est une amputation ; avec une cape c'est un vêtement. Le mannequin B (tunique sans
   cape) est plus faible sur ce point : il se lit comme un buste de vitrine, ce qui est acceptable (« mannequin ») mais
   moins vivant.
5. **Les repères d'emplacement sont des traits du personnage, pas des lignes pointillées** : la ceinture rouge
   = taille ; l'encolure = creux du cou ; le menton, le front, l'oreille, la pointe de l'épaulette sont des lieux
   dessinés. L'option « repères » (lignes pointillées) peut rester, mais le personnage lui-même doit déjà porter les lieux.

---

## 3. Trois directions, dessinées et itérées

Toutes en SVG (aplat + ombre franche + trait noir), viewBox 400 × 620, 1 longueur de main (HL) = 100 unités, rendues par
Chromium à 200 px et 600 px de haut (`rendu_svg.py` : le trait est remis à l'échelle à `max(1,3 px ; 0,028 × HL_px)`,
comme la règle de `drawRef`). La **main-témoin** verte (#00a19a, silhouette simplifiée, longueur 1 HL) sert seulement à
juger le contraste et l'échelle ; ce n'est pas la main de l'atelier.

| Direction | Fichiers | Idée |
|---|---|---|
| **A — Buste à cape et épaulettes** | `A_final_*_{200,600}.png`, `svg/A_final_*.svg` | Crâne nu, antennes, oreilles pointues, arcade marquée ; vêtement violet à col rond, ceinture rouge à la taille ; cape ivoire : deux épaulettes séparées en coin arrondi montant vers l'extérieur, deux pans qui tombent derrière les flancs. 31 éléments. |
| **B — Mannequin néo-Piccolo sobre** | `B_final_*` | Même tête, antennes plus courtes, yeux = deux points, sourcils = deux traits ; tunique violette d'une pièce, épaules rondes, encolure ronde. 17 éléments. |
| **C — Buste au trait façon manga, grands aplats** | `C_final_*` | Mâchoire anguleuse + ombre franche sur la joue, arcade lourde, turban en bulbe d'où sortent les antennes, cape à pointes d'épaule relevées, pans devant, ceinture rouge. 34 éléments. |

### 3.1 Historique des itérations (les planches sont dans `iterations/`)

| Version | Ce qui n'allait pas (vu sur le rendu) | Correction |
|---|---|---|
| v1 (`planche_v1.png`) | Cou de girafe (68 u. pour 20 de demi-largeur) ; tête trop petite pour le torse ; traits du visage timides ; antennes = tentacules de limace à boule ; oreilles en ailes horizontales ; A = boîte en carton / blouse de labo ; B = cloche ; C = bandeau de tennis ; trait de 0,8 px à 200 px (illisible) | Cou 240→294, demi-largeur 27 ; tête 128 × 100 ; visage × 1,25 ; antennes courtes et charnues (9 → 5 u.), sans boule ; oreilles attachées au niveau des yeux, pointe à 35° ; trait remis à l'échelle au rendu |
| v2 (`planche_v2.png`) | A : épaulettes = deux petits rouleaux hors des épaules, col croisé « étole de prêtre » ; B : épaules trop hautes et larges ; C : turban = bonnet de douche | A : épaulettes larges couvrant l'épaule, col rond + petit V ; B : épaules abaissées (E 108) ; C : turban en bulbe plus large que le crâne, sommet plat, pli diagonal |
| v3 (`planche_v3.png`) | A : les deux épaulettes se rejoignent en une barre, « cintre » ; ceinture absente ; C acceptable ; B le plus lisible à 200 px | A : deux coins SÉPARÉS (départ à ±58 u. du centre), pointe extérieure à y 278 ; ceinture à la taille (y 480-506 = 1,92 HL) |
| v4 (`planche_v4_A.png`) | A tient ; test main au menton et au front : la main reste lisible grâce au trait, mais peau (#8fd1ca) et main (#00a19a) sont proches (1,85:1) | Peau éclaircie à #a8dcd6 (2,11:1), ombre de peau #74c2b9 ; variante « trait » (papier blanc) validée à 200 px |
| final (`planche_finale_ABC.png`, `planche_finale_A_expressions.png`) | — | A, B, C en quatre expressions, avec et sans main-témoin |

### 3.2 Critique finale, direction par direction

**A.** Silhouette en T immédiatement lisible à 200 px (épaulettes + oreilles + antennes) ; le violet est une bonne
« table » pour la main ; la ceinture donne la taille ; la cape ferme la silhouette et justifie l'absence de bras. Visage :
arcade + œil en amande + iris → quatre expressions distinctes à 600 px, trois à 200 px (neutre / sourire / sourcils
froncés ; « sourcils levés » se lit surtout par la bouche entrouverte et les yeux plus ouverts). Défauts qui restent : les
pans de cape sont deux bandes droites (on pourrait leur donner un léger évasement), l'ombre de peau sur la joue est une
bande un peu mécanique, le cou est encore un peu long à 600 px (acceptable à 200).
**B.** Le plus économe et le plus lisible à 200 px (yeux-points, sourcils-traits). Mais sans cape : un buste de vitrine,
l'absence de bras se voit ; et peu de personnalité (le « Piccolo » n'y est que par la tête). À garder comme **style
« simple »** optionnel, pas comme référent principal.
**C.** Le plus « manga » et le plus proche de Piccolo (pointes d'épaule, turban, mâchoire) — c'est précisément son
problème : c'est la direction la plus exposée juridiquement, et le turban cache les oreilles-silhouette. À 200 px le turban
et les pans multiplient les traits (34 éléments) et la tête devient confuse. Bonne source d'éléments (pointes d'épaule,
ombre de joue), mauvais candidat principal.

| Critère | A | B | C |
|---|---|---|---|
| Lisibilité à 200 px | bonne | très bonne | moyenne (turban + pans) |
| Identité (silhouette) | forte (T) | faible | forte |
| Expressions distinctes à 200 px | 3 | 3 | 2-3 |
| Absence de bras justifiée | oui (cape) | non | oui |
| Distance à Piccolo (risque) | moyenne : pas de turban, antennes et épaulettes différentes | grande | faible (turban + pointes + gi) |
| Éléments à dessiner | 31 | 17 | 34 |
| Surface de contraste pour la main | violet + ivoire | violet | violet + ivoire |

**Recommandation : A**, avec B conservé comme variante « simple » (même tête, même ancre, tunique seule), et deux emprunts
à C pour une v2.1 si l'utilisateur veut plus de caractère : la pointe d'épaule plus haute, l'ombre de joue.

---

## 4. Spécification d'intégration de la direction A

### 4.1 Géométrie, en longueurs de main (HL), origine = creux du cou (ancre actuelle `refAnchor`)

Dans le SVG, 1 HL = 100 unités, creux du cou = (200, 300). Coordonnées (x à droite, y vers le bas) :

| Élément | x (HL) | y (HL) | Note |
|---|---|---|---|
| Sommet du crâne | 0 | −1,86 | tête 1,28 HL de haut (actuel : 1,20) |
| Yeux | ±0,27 | −1,16 | hauteur de l'oreille |
| Base du nez | 0 | −0,86 | une seule ligne |
| Bouche | ±0,13 | −0,71 | |
| Menton | 0 | −0,58 | **inchangé** (BODY.menton) |
| Tête, demi-largeur max | ±0,50 | −1,14 | tête 1,0 HL de large (actuel : 0,88) |
| Pointe d'oreille | ±0,87 | −1,50 | attache sur le bord de la tête à y −1,30 … −1,00 |
| Antenne : base / pointe | ±0,14 / ±0,40 | −1,72 / −2,10 | 9 u. à la base, 5 au bout |
| Cou : demi-largeur | ±0,27 (haut) → ±0,32 (bas) | −0,60 → −0,06 | |
| Encolure | ±0,34 | −0,08 … +0,16 | arc + petit V jusqu'à +0,30 |
| Épaules (vêtement) | ±1,15 | +0,22 | **inchangé** (BODY.ep = 1,15 → 2,3 HL d'épaules) |
| Épaulettes : coin intérieur / pointe extérieure | ±0,58 / ±1,36 | +0,00 … +0,26 / −0,22 | bord bas à +0,26 |
| Pans de cape | ±0,75 … ±1,40 | +0,22 → bas de l'image | s'évasent de 0,04 HL vers le bas |
| Flancs du vêtement | ±0,91 (épaule) → ±0,75 (bas) | | |
| **Ceinture = taille** | ±0,81 | +1,80 … +2,06 | centrée sur +1,92 = BODY.yTa, **inchangé** |
| **Ancre des mains (poitrine)** | 0 | **+1,00** | = (yEp + yTa)/2 ; la main de 1 HL occupe +0,50 … +1,50 |
| Lieux à exposer dans l'interface | front −1,50 ; œil −1,16 ; nez −0,86 ; bouche −0,71 ; menton −0,58 ; cou −0,30 ; épaule ±1,15 / +0,10 ; poitrine +1,00 ; taille +1,92 ; espace neutre +0,60 … +1,40 devant | |

Taille totale visible : 3,9 HL de haut (crâne → ceinture 2,06 + marge), 2,8 HL de large (épaulettes 2,72). C'est 0,2 HL
de plus que l'actuel en hauteur (tête plus grande) ; `fitView` le prend déjà en compte via `contentBox`.

### 4.2 Trait

`lineWidth = max(1.3, 0.028 · u)` avec `u` = HL en pixels (l'actuel : `max(1.2, .021·u)`), parce que le trait du référent
doit être du même poids que le contour de la main (coque ≈ 0,03 HL). Traits secondaires (pli d'oreille, V du col, plis du
front) à 0,8 ×. L'arcade sourcilière n'est **pas** un trait : c'est une forme fermée remplie d'encre (sinon, à 200 px,
elle se confond avec le trait de l'œil).

### 4.3 Palette et contrastes (WCAG, luminance relative)

| Rôle | Couleur | Contraste avec la main #00a19a | Avec l'encre #14201f |
|---|---|---|---|
| Main (vert INJS) | #00a19a | — | 5,23 |
| Peau | #a8dcd6 | 2,11 | 11,0 |
| Peau, ombre franche | #74c2b9 | ≈1,5 | ≈8 |
| Cape | #f4f1ea | 2,84 | 14,8 |
| Cape, ombre | #d6d0c2 | 2,08 | 10,9 |
| Vêtement | #5a3d8c | 2,65 | 1,98 |
| Vêtement, ombre | #44306d | 3,47 | 1,50 |
| Ceinture | #c0392b | 1,70 | 3,07 |
| Papier (style « trait ») | #ffffff | 3,20 | 16,7 |
| Fond actuel du référent | #dbe8e6 | 2,54 | 13,3 |

Lecture : la main se détache le mieux sur le vêtement (2,65-3,47) et la cape (2,84) ; sur la peau (2,11) c'est le
contour qui travaille — il faut donc **ne jamais** mettre la peau dans la même valeur que la main (règle : luminance de la
peau ≥ 2 × celle de la main ; 0,644 contre 0,278, ok). Le violet a un contraste faible avec l'encre (1,98) : les traits
intérieurs sur le vêtement doivent rester rares (encolure, V). La ceinture est volontairement la seule note chaude.
En mode sombre de l'interface, garder ces valeurs : le référent est une image, pas de l'UI.

### 4.4 Dessin en canvas 2D : la méthode recommandée

Ne pas retranscrire les courbes en `bezierCurveTo` à la main comme aujourd'hui : **embarquer les chemins SVG tels quels
et les tracer avec `Path2D`**, qui accepte la syntaxe `d` des chemins SVG. Ordre de peinture (du fond vers l'avant) :

```
pans de cape (gauche, droite) → ombre du pan droit → vêtement → ombre du vêtement → encolure, V →
ceinture → épaulettes (gauche, droite) + leurs ombres → cou + ombre sous le menton →
tête → ombre de joue → oreilles (+ pli) → antennes → visage (yeux, arcades, nez, bouche)
```

Squelette de fonction (description, pas de code à livrer) :

```
drawRef2(ctx, W, H):
  A = projTo(refAnchor())                      // creux du cou à l'écran
  u = ppuAt(A, H) * HL * S.ref.t               // pixels par longueur de main
  k = u / 100                                   // unités SVG → pixels
  ctx.setTransform(k, 0, 0, k, A.x - 200*k, A.y - 300*k)
  ctx.lineWidth = max(1.3, .028*u) / k          // largeur constante À L'ÉCRAN
  for each piece in REF_A[expr][style]:         // {d, fill, stroke, lw}
      p = new Path2D(piece.d); if fill: ctx.fill(p); if stroke: ctx.stroke(p)
  ctx.setTransform(1,0,0,1,0,0)
```

Les pièces sont des chaînes `d` en unités (viewBox 400 × 620) générées depuis `gen.py` (ou copiées de
`svg/A_final_sansmain.svg`, 5,4 Ko). Mise en cache des `Path2D` au chargement. Le miroir n'est pas nécessaire : le
personnage est symétrique sauf l'ombre franche, qui est à droite de l'image (lumière venant de la gauche, comme l'ombre de
la main dans le nuanceur — à vérifier que les deux sont du même côté, sinon inverser les pièces d'ombre).

Styles : `plein` (palette ci-dessus), `trait` (tous les fills = papier blanc, pas d'ombres : `A_final_trait_*.png`),
`aucun`. Pour la vue « dos (signeur) » : même silhouette vue de derrière = pans de cape pleins, nuque, antennes et
oreilles visibles, **pas de visage** ; à générer à partir des mêmes pièces (cape sans vêtement devant, tête sans traits).

### 4.5 Expressions (le visage est un paramètre du signe)

Quatre états, tous paramétrés sur trois variables (`planche_finale_A_expressions.png`) :

| État | Sourcils (y relatif à l'œil, en u.) | Ouverture de l'œil (u.) | Bouche | Usage LSF (à valider par l'utilisateur) |
|---|---|---|---|---|
| neutre | −20, horizontaux | 8 | trait droit | signe lexical isolé |
| sourire | −21 | 6 | arc vers le bas | affirmation, contexte positif, CONTENT |
| sourcils levés | −33, + pli de front | 11 | entrouverte | question fermée (oui/non) — majorité des sources, une contradictoire |
| sourcils froncés | −14, intérieur abaissé de 8, deux plis entre les sourcils, paupière abaissée | 6 | arc vers le haut | question ouverte (qui/quoi/où), négation, concentration |

À ajouter en v2.1 si besoin : joues gonflées / bouche en « o » (morphèmes buccaux), regard dirigé (iris décalé vers une
main), tête inclinée (une rotation de 8° de tout le groupe tête). L'expression doit être **réglable par étape clé**
(comme la pose de la main), pas globale : en LSF elle change en cours de signe.

### 4.6 Tailles

| Contexte | Hauteur du buste à l'écran | HL (px) | Trait (px) |
|---|---|---|---|
| Vignette de bibliothèque | 160-200 | 41-51 | 1,3 |
| Planche de classe à l'écran | 600 | 154 | 4,3 |
| Export PNG 2000 px de haut | 2000 | 513 | 14 |

En dessous de 160 px, passer en style B (yeux-points) ou masquer le visage : l'arcade et l'œil fusionnent.

---

## 5. Ce que ça implique pour la v2 (recommandations classées)

1. **Adopter la direction A** comme référent par défaut : cape à épaulettes séparées, vêtement violet à col rond, ceinture
   rouge à la taille, crâne nu, antennes courtes vers l'extérieur, oreilles pointues, arcade en masse. Pas de turban, pas de
   taches, pas de crocs, pas de nom ni de kanji : hommage, pas copie.
2. **Supprimer les bras** et faire porter leur absence par la cape (silhouette fermée) ; ne jamais redessiner un tee-shirt à
   manches sans mains au bout.
3. **Garder les ancres existantes** : creux du cou, menton −0,58 HL, épaules ±1,15 HL, taille +1,92 HL, mains à +1,00 HL.
   Seule la tête grandit (1,28 × 1,0 HL) ; `contentBox` suit.
4. **Passer `drawRef` en `Path2D` + chemins SVG embarqués** (unités : 1 HL = 100) avec `setTransform` et un `lineWidth`
   constant à l'écran (`max(1,3 ; 0,028·u)`). Les cheveux, bras, trapèzes et autres pièces du `drawRef` actuel disparaissent.
5. **Palette fixée** (§4.3) avec la règle de contraste : luminance de la peau ≥ 2 × celle de la main, vêtement et cape
   ≥ 2,6:1 contre la main. La peau du personnage n'est PAS le vert INJS de la main.
6. **Visage à quatre états, réglable par étape clé**, exposé dans l'onglet Mouvement à côté de la configuration de la main ;
   état « neutre » par défaut ; la fonction grammaticale des sourcils (levés / froncés) est à **valider par l'utilisateur**
   avant d'étiqueter les boutons (les sources se contredisent).
7. **Repères d'emplacement portés par le dessin** : front, œil, nez, bouche, menton, cou, épaule (pointe d'épaulette),
   poitrine, taille (ceinture) ; l'option « repères » pointillés reste pour les lieux hors silhouette (espace neutre,
   espace d'épellation).
8. **Style B conservé** comme « simple » (même tête, tunique, 17 pièces) et comme repli automatique sous 160 px.
9. **Vue signeur (dos)** : dériver un dos de la même silhouette (cape pleine, pas de visage), ne pas montrer le visage
   en miroir.
10. **Fond** : uni, contrasté avec la main et avec le vêtement (le fond actuel #dbe8e6 va ; éviter tout vert d'eau proche de
    la peau #a8dcd6 : prévoir un garde-fou qui éclaircit ou assombrit le fond si son contraste avec la peau passe sous 1,3).
11. Pour la v2.1 (après retour de l'utilisateur) : pointe d'épaule plus relevée (empruntée à C), ombre de joue, tête
    inclinable, regard dirigé, morphèmes buccaux.

---

## 6. Incertitudes et ce qui n'a pas pu être vérifié

- Cadrage et fond exacts d'Elix, de Spread the Sign et de LSFdico INJS Metz : sites inaccessibles d'ici ; décrits de mémoire.
- Fonction grammaticale des sourcils en LSF : les sources lues (grand public) se contredisent ; la thèse de Chételat-Pelé
  (2010) et Cuxac (2000) n'ont pas pu être lues. L'utilisateur tranche.
- Liste complète des lieux d'articulation : les extraits n'en donnent que sept.
- Taille officielle de Piccolo (226 vs 223,5 cm) : sans incidence sur le dessin.
- Marques « Dragon Ball » / « Piccolo » à l'EUIPO : non consultées ; sans incidence tant qu'on n'utilise ni nom ni logo.
- Aucune photo de référence (Unsplash) n'a pu être téléchargée ; les proportions du buste viennent du canon classique
  (épaules ≈ 2 têtes de large, [trouverecole](https://trouverecole.fr/blog/dessiner-corps-humain-mouvement-manquin-bois/))
  et des ancres déjà validées de l'atelier (2,3 HL d'épaules pour une tête de 1 HL de large → 2,3 têtes : carrure
  marquée, cohérente avec l'hommage).
- Le côté de l'ombre franche du référent (droite de l'image) doit être aligné sur l'éclairage du nuanceur de la main.
