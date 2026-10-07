"""Construit dist/atelier-mains-lsf.html (fichier unique, autonome).

  python3 build.py            -> assemble à partir de source/hand3d.json existant
  python3 build.py --rig      -> régénère d'abord source/hand3d.json depuis references/
  python3 build.py --rig --preview -> idem + source/preview_align.png (contrôle du recalage dos)
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'source')

if '--rig' in sys.argv:
    cmd = [sys.executable, os.path.join(SRC, 'rig3d.py'), os.path.join(ROOT, 'references'), SRC]
    if '--preview' in sys.argv:
        cmd.append('preview')
    subprocess.run(cmd, check=True)

head = open(os.path.join(SRC, 'head.html'), encoding='utf-8').read()
style = open(os.path.join(SRC, 'style.css'), encoding='utf-8').read()
script = open(os.path.join(SRC, 'script.js'), encoding='utf-8').read()
data = open(os.path.join(SRC, 'hand3d.json'), encoding='utf-8').read()
assert '</script' not in data

out = head.replace('__STYLE__', '<style>\n' + style + '</style>') + '\n' + script.replace('__DATA__', data)
os.makedirs(os.path.join(ROOT, 'dist'), exist_ok=True)
open(os.path.join(ROOT, 'dist', 'atelier-mains-lsf.html'), 'w', encoding='utf-8').write(out)

# version « page complète » pour l'ouvrir hors claude.ai (claude.ai ajoute lui-même doctype/head/body)
full = ('<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>[hidden]{display:none!important}body{margin:0}</style></head><body>' + out + '</body></html>')
open(os.path.join(ROOT, 'dist', 'atelier-mains-lsf.local.html'), 'w', encoding='utf-8').write(full)

# contrôle de syntaxe du script principal (si node est installé)
js = re.findall(r'<script>(.*?)</script>', out, re.S)[-1]
chk = os.path.join(ROOT, 'dist', '.chk.js')
open(chk, 'w', encoding='utf-8').write(js)
try:
    r = subprocess.run(['node', '--check', chk], capture_output=True, text=True)
    print('syntaxe JS :', 'OK' if r.returncode == 0 else r.stderr)
except FileNotFoundError:
    print('node absent : contrôle de syntaxe ignoré')
finally:
    os.remove(chk)
print('dist/atelier-mains-lsf.html :', len(out) // 1024, 'Ko')
