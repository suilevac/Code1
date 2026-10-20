"""Lecture minimale d'un glTF binaire (.glb) en numpy, pour les tests du moteur (engine_contacts.py, engine_skin_m1.py,
engine_presets.py) : lire(chemin) → (JSON du glTF, acc), où acc(i) rend l'accesseur i en tableau (n, c), avec les
accesseurs entrelacés et CREUX (« sparse » : les morph targets de M1 sont stockés ainsi). Aucune dépendance hors numpy.
(Copié du brouillon de travail du chantier M2 dans le dépôt : relecture adverse, les mesures doivent pouvoir être
relancées sans le dossier temporaire.)"""
import json, struct
import numpy as np

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def lire(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'glTF', path + " n'est pas un glTF binaire"
    l0 = struct.unpack('<I', b[12:16])[0]
    J = json.loads(b[20:20 + l0])
    o = 20 + l0
    l1 = struct.unpack('<I', b[o:o + 4])[0]
    BIN = b[o + 8:o + 8 + l1]

    def acc(i):
        a = J['accessors'][i]; n = a['count']; c = NC[a['type']]; dt = CT[a['componentType']]
        if 'bufferView' in a:
            bv = J['bufferViews'][a['bufferView']]; off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
            st = bv.get('byteStride', 0); isz = np.dtype(dt).itemsize * c
            if st and st != isz:   # entrelacé
                arr = np.frombuffer(BIN, dtype=np.uint8, count=st * (n - 1) + isz, offset=off)
                arr = np.stack([np.frombuffer(arr[k * st:k * st + isz].tobytes(), dtype=dt) for k in range(n)])
            else:
                arr = np.frombuffer(BIN, dtype=dt, count=n * c, offset=off).reshape(n, c).copy()
        else:
            arr = np.zeros((n, c), dt)
        if 'sparse' in a:          # creux : valeurs aux indices donnés, zéro ailleurs
            s = a['sparse']; m = s['count']
            ib = J['bufferViews'][s['indices']['bufferView']]
            idx = np.frombuffer(BIN, dtype=CT[s['indices']['componentType']], count=m, offset=ib.get('byteOffset', 0) + s['indices'].get('byteOffset', 0))
            vb = J['bufferViews'][s['values']['bufferView']]
            val = np.frombuffer(BIN, dtype=dt, count=m * c, offset=vb.get('byteOffset', 0) + s['values'].get('byteOffset', 0)).reshape(m, c)
            arr = arr.astype(dt).copy(); arr[idx] = val
        return arr
    return J, acc
