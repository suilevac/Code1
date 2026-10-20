"""Construit l'atelier v2 en UN fichier autonome (chantier M5, intégration).

  python3 v2/build.py           -> dist/atelier-v2.html        (sans doctype : claude.ai ajoute doctype, head et body)
                                   dist/atelier-v2.local.html  (page complète, s'ouvre directement dans un navigateur)

Ce qui est embarqué, dans l'ordre de chargement (aucun CDN, aucune requête réseau) :
  plate.css                          l'éditeur de planche (M3)
  fonts.js                           polices OFL en base64 (Atkinson Hyperlegible, Nunito ; 65 Ko bruts)
  three.min.js r128 + GLTFLoader.js  vendus (v2/engine/vendor, v2/hand/vendor : sha256 dans PROVENANCE.txt)
  shaders.js                         passes toon du moteur (M2)
  ATELIER_HAND_ASSETS                hand_v2.glb en base64 + hand_v2.json (M1) : engine.js les lit au chargement
  engine.js                          le moteur (window.AtelierHand)
  personnage.js                      le référent (M4)
  plate.js                           l'éditeur ; il appelle window.AtelierHand (le bouchon stub_hand.js n'est PAS embarqué)

Contrôles : syntaxe de chaque script (node --check), aucune séquence « </script » dans le code embarqué, taille (le
contrat vise < 12 Mo ; la page fait ≈ 5 Mo, dont 3,9 Mo pour le GLB en base64)."""
import base64, hashlib, json, os, re, subprocess, sys, tempfile

V2 = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(V2)
DIST = os.path.join(RACINE, 'dist')
PLAFOND = 12 * 1024 * 1024        # octets : contrat M5 (« viser < 12 Mo » ; un artifact claude.ai accepte 16 Mo)


def lit(*chemin):
    return open(os.path.join(V2, *chemin), encoding='utf-8').read()


def script(code, nom):
    # « </script » fermerait la balise au milieu du code ; « <!-- » suivi de « <script » ferait basculer l'analyseur HTML
    # dans l'état « script data escaped » : les deux sont refusés plutôt que réécrits en silence
    if re.search(r'</script', code, re.I) or '<!--' in code:
        sys.exit('ERREUR : %s contient « </script » ou « <!-- » : impossible de l\'embarquer tel quel' % nom)
    return '<script>/* ' + nom + ' */\n' + code + '\n</script>'


def verifie_syntaxe(nom, code):
    f = tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8')
    f.write(code); f.close()
    try:
        r = subprocess.run(['node', '--check', f.name], capture_output=True, text=True)
    except FileNotFoundError:
        print('  node absent : contrôle de syntaxe ignoré pour', nom); return True
    finally:
        os.unlink(f.name)
    if r.returncode:
        print('  SYNTAXE', nom, ':', r.stderr.strip()[:800]); return False
    return True


def main():
    page = lit('plate', 'index.html')
    glb = open(os.path.join(V2, 'hand', 'hand_v2.glb'), 'rb').read()
    jmain = json.load(open(os.path.join(V2, 'hand', 'hand_v2.json'), encoding='utf-8'))
    # JSON de la main en littéral JS : « </ » échappé (une chaîne du JSON ne doit pas fermer la balise)
    assets = ('window.ATELIER_HAND_ASSETS={glb:"' + base64.b64encode(glb).decode('ascii') + '",json:' +
              json.dumps(jmain, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + '};')
    scripts = [
        ('fonts.js', lit('plate', 'fonts.js')),
        ('three.min.js r128', lit('engine', 'vendor', 'three.min.js')),
        ('GLTFLoader.js r128', lit('hand', 'vendor', 'GLTFLoader.js')),
        ('shaders.js', lit('engine', 'shaders.js')),
        ('assets de la main (hand_v2.glb base64 + hand_v2.json)', assets),
        ('engine.js', lit('engine', 'engine.js')),
        ('personnage.js', lit('personnage', 'personnage.js')),
    ]
    ok = all(verifie_syntaxe(n, c) for n, c in scripts + [('plate.js', lit('plate', 'plate.js'))])
    if not ok:
        sys.exit('ERREUR : syntaxe JS')

    # --- index.html → fragments : <head> (titre, viewport, styles, scripts) et le contenu de <body> ---
    tete = re.search(r'<head>(.*?)</head>', page, re.S).group(1)
    corps = re.search(r'<body>(.*?)</body>', page, re.S).group(1)
    titre = re.search(r'<title>.*?</title>', tete, re.S).group(0)
    # le titre de l'onglet : un nom court (artifact claude.ai : « deux à quatre mots »)
    titre = '<title>Atelier des mains LSF</title>'
    assert '<script src="plate.js"></script>' in corps
    corps = corps.replace('<script src="plate.js"></script>', script(lit('plate', 'plate.js'), 'plate.js'))
    style = '<style>/* plate.css */\n' + lit('plate', 'plate.css') + '\n</style>'
    entete = (titre + '\n<meta name="viewport" content="width=device-width,initial-scale=1">\n' + style + '\n' +
              '\n'.join(script(c, n) for n, c in scripts))
    # version artifact (claude.ai ajoute doctype, <html>, <head>, <body>) : un fragment, comme la v1
    artifact = entete + '\n' + corps.strip() + '\n'
    local = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n' + entete + '\n</head>\n<body>\n' +
             corps.strip() + '\n</body>\n</html>\n')
    for nom, txt in (('atelier-v2.html', artifact), ('atelier-v2.local.html', local)):
        if 'stub_hand' in txt and 'src="stub_hand.js"' in txt:
            sys.exit('ERREUR : le bouchon stub_hand.js est encore chargé')
        if re.search(r'<script[^>]+src=', txt) or re.search(r'<link[^>]+href=', txt):
            sys.exit('ERREUR : %s charge encore un fichier externe' % nom)
        os.makedirs(DIST, exist_ok=True)
        open(os.path.join(DIST, nom), 'w', encoding='utf-8').write(txt)
        n = len(txt.encode('utf-8'))
        print('dist/%s : %.2f Mo (%d octets) %s' % (nom, n / 1048576, n, 'OK' if n < PLAFOND else 'TROP LOURD'))
        if n >= PLAFOND:
            sys.exit('ERREUR : %s dépasse %d Mo' % (nom, PLAFOND // 1048576))
    print('syntaxe JS : OK (%d scripts)' % (len(scripts) + 1))
    print('GLB : %d octets, sha256 %s' % (len(glb), hashlib.sha256(glb).hexdigest()[:16]))


if __name__ == '__main__':
    main()
