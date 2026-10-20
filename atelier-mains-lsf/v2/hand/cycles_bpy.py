"""Blender (module bpy 5.2) pour le chantier M1 : export glTF binaire skinné (attributs _REGION et _ONGLE) et
rendus de contrôle Cycles (CPU). Tout est construit dans une scène vide : rien ne dépend d'un fichier .blend."""
import math
import numpy as np

VERT_INJS = (0.0, 161 / 255, 154 / 255)        # vert INJS #00a19a (CLAUDE.md : relevé sur le logo du site)
DEBRUITAGE = True   # le débruiteur crénelle les bords francs (trait d'ongle) : les gros plans le coupent et montent les échantillons

def _lin(c):   # sRGB → linéaire (Blender travaille en linéaire)
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)

def scene_vide():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy

def _maillage(bpy, nom, V, F, attrs=None):
    me = bpy.data.meshes.new(nom); me.from_pydata([tuple(map(float, v)) for v in V], [], [list(map(int, f)) for f in F]); me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    for k, a in (attrs or {}).items():
        at = me.attributes.new(name=k, type='FLOAT', domain='POINT'); at.data.foreach_set('value', np.asarray(a, np.float32).ravel())
    ob = bpy.data.objects.new(nom, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def _materiau(bpy, nom='peau_injs', region=True):
    m = bpy.data.materials.new(nom); m.use_nodes = True
    nt = m.node_tree; bs = nt.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = _lin(VERT_INJS) + (1.0,)
    bs.inputs['Roughness'].default_value = 0.55
    if region:   # ongle plus clair : seuil sur _ONGLE (distance signée au bord de la plaque, mm) — trait net
        at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = '_ONGLE'; at.attribute_type = 'GEOMETRY'
        mr = nt.nodes.new('ShaderNodeMapRange'); mr.data_type = 'FLOAT'
        mr.inputs['From Min'].default_value = -0.15; mr.inputs['From Max'].default_value = 0.15
        nt.links.new(at.outputs['Fac'], mr.inputs['Value'])
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        mix.inputs['A'].default_value = _lin(VERT_INJS) + (1.0,)
        mix.inputs['B'].default_value = _lin((0.80, 0.93, 0.91)) + (1.0,)
        nt.links.new(mr.outputs['Result'], mix.inputs['Factor']); nt.links.new(mix.outputs['Result'], bs.inputs['Base Color'])
    return m

def exporter_glb(chemin, V, F, W, os_noms, parents, C, A, longueurs, attrs, couleurs=None, morphs=None):
    """V (n,3) cm, F faces (les triangles déjà choisis : le GLB garde EXACTEMENT cette triangulation), W (n, 20) poids
    (≤ 4 non nuls), C/A centres et axes des os (colonnes X, Y, Z) ; les axes glTF sont ceux du contrat (export_yup = False :
    aucune conversion d'axes), unités = nombres en cm ; morphs : {nom: déplacement (n, 3) dans l'espace de liaison} →
    morph targets glTF (POSITION et NORMAL en accesseurs CREUX — seuls les sommets déplacés —, noms dans mesh.extras.targetNames)"""
    bpy = scene_vide()
    from mathutils import Matrix, Vector
    ob = _maillage(bpy, 'main_v2', V, F, attrs)
    if morphs:
        ob.shape_key_add(name='Basis', from_mix=False)
        for nom, D in morphs.items():
            sk = ob.shape_key_add(name=nom, from_mix=False)
            sk.data.foreach_set('co', (np.asarray(V, np.float64) + np.asarray(D, np.float64)).astype(np.float32).ravel())
    for k, a in (couleurs or {}).items():     # attributs RGBA (FLOAT_COLOR) exportés comme attributs personnalisés VEC4
        at = ob.data.attributes.new(name=k, type='FLOAT_COLOR', domain='POINT'); at.data.foreach_set('color', np.asarray(a, np.float32).ravel())
    ob.data.materials.append(_materiau(bpy, region=False))
    arm = bpy.data.armatures.new('squelette'); ao = bpy.data.objects.new('squelette', arm)
    bpy.context.scene.collection.objects.link(ao)
    bpy.context.view_layer.objects.active = ao; bpy.ops.object.mode_set(mode='EDIT')
    ebs = {}
    for b in os_noms:
        eb = arm.edit_bones.new(b); c = Vector(C[b]); y = Vector(np.asarray(A[b])[:, 1])
        eb.head = c; eb.tail = c + y * float(longueurs[b])
        M = Matrix.Identity(4)
        for i in range(3):
            for j in range(3): M[i][j] = float(np.asarray(A[b])[i, j])
            M[i][3] = float(C[b][i])
        eb.matrix = M; eb.length = float(longueurs[b]); ebs[b] = eb
    for b in os_noms:
        if parents[b]: ebs[b].parent = ebs[parents[b]]; ebs[b].use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    # contrôle : repère de chaque os dans Blender = repère voulu
    err = 0.0
    for b in os_noms:
        mb = ao.data.bones[b].matrix_local
        R = np.array([[mb[i][j] for j in range(3)] for i in range(3)]); t = np.array([mb[i][3] for i in range(3)])
        err = max(err, float(np.abs(R - np.asarray(A[b])).max()), float(np.abs(t - np.asarray(C[b])).max()))
    for j, b in enumerate(os_noms):
        vg = ob.vertex_groups.new(name=b); idx = np.nonzero(W[:, j] > 0)[0]
        for i in idx: vg.add([int(i)], float(W[i, j]), 'REPLACE')
    mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = ao; ob.parent = ao
    bpy.ops.export_scene.gltf(filepath=chemin, export_format='GLB', export_yup=False, export_attributes=True,
                              export_skins=True, export_influence_nb=4, export_all_influences=False, export_normals=True,
                              export_texcoords=False, export_tangents=False, export_materials='EXPORT',
                              export_vertex_color='NONE', export_animations=False, export_morph=bool(morphs),
                              export_morph_normal=bool(morphs), export_morph_tangent=False, export_try_sparse_sk=True,
                              export_def_bones=False, export_rest_position_armature=True, export_apply=False)
    return err

def rendus(scenes, vues, taille=520, echantillons=24, chemin_tmp=None):
    """scenes : liste de (V, F, distance signée au bord de l'ongle en mm) ; vues : liste de (R (3×3, lignes = écran x, écran y, vers l'œil), centre,
    demi-hauteur visible en cm). Renvoie une liste de chemins PNG (scènes × vues)."""
    import os
    if chemin_tmp is None:      # images intermédiaires dans work/ (relecture : plus rien dans /tmp hors du dépôt)
        chemin_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'work', 'rendu_%d.png')
    bpy = scene_vide()
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = echantillons
    sc.cycles.use_denoising = DEBRUITAGE
    sc.render.resolution_x = taille; sc.render.resolution_y = taille; sc.render.film_transparent = False
    sc.view_settings.view_transform = 'Standard'
    w = bpy.data.worlds.new('monde'); w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.92, 0.92, 0.92, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55; sc.world = w
    mat = _materiau(bpy)
    from mathutils import Matrix, Vector
    cam_d = bpy.data.cameras.new('cam'); cam_d.type = 'ORTHO'; cam = bpy.data.objects.new('cam', cam_d)
    sc.collection.objects.link(cam); sc.camera = cam; cam_d.clip_start = 0.1; cam_d.clip_end = 400
    sun_d = bpy.data.lights.new('soleil', 'SUN'); sun_d.energy = 3.2; sun_d.angle = math.radians(8)
    sun = bpy.data.objects.new('soleil', sun_d); sc.collection.objects.link(sun)
    out = []; n = 0
    for V, F, ong in scenes:
        ob = _maillage(bpy, 'm', V, F, {'_ONGLE': ong}); ob.data.materials.append(mat)
        for R, c, demi in vues:
            R = np.asarray(R, float); c = np.asarray(c, float)
            M = Matrix.Identity(4)
            for i in range(3):
                for j in range(3): M[i][j] = float(R[j][i])        # colonnes = axes écran x, y, vers l'œil
                M[i][3] = float(c[i] + R[2][i] * 60)
            cam.matrix_world = M; cam_d.ortho_scale = 2 * demi
            ld = R.T @ np.array([0.45, 0.55, 0.9]); ld /= np.linalg.norm(ld)   # soleil en haut à droite, vers l'œil
            z = Vector(ld); rot = z.to_track_quat('Z', 'Y'); sun.rotation_euler = rot.to_euler()
            p = chemin_tmp % n; sc.render.filepath = p; bpy.ops.render.render(write_still=True); out.append(p); n += 1
        bpy.data.objects.remove(ob)
    return out
