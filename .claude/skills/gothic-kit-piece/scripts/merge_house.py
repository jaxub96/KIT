# Merge a kit-built house into ONE connected mesh (non-destructive).
# Run from Blender's Text Editor with the house collection active in the Outliner
# (or set COLLECTION below). The pieces stay untouched: the result is a new object
# <COLLECTION>_MERGED in its own collection (replaced on every run).
#
# What it does, in plain Blender terms:
#   1. Join copies of every mesh in the collection (world space, materials kept).
#   2. Merge by Distance 0.001 m (the kit's weld tolerance). Coincident back-to-back
#      faces collapse into one face here, like in Edit Mode.
#   3. Delete the hidden floor partitions. Kit floor tiles are closed slabs, so where
#      two tiles meet, or a tile sits against a wall's inside face, a vertical face is
#      left INSIDE the solid floor. Do NOT use Select > Interior Faces for this: a tile
#      with neighbours on all four sides has its walkable top selected too, which
#      leaves a hole. Only vertical faces that lie on a floor tile's side, within its
#      thickness, with every edge shared by 3+ faces, are removed.
#   4. Report non-manifold edges / open edges / flipped neighbours.
import bpy, bmesh

COLLECTION = None          # None = active collection in the Outliner
FLOOR_PREFIX = "KIT_FLOOR"
WELD = 1e-3


def merge_house(coll):
    obs = [o for o in coll.all_objects if o.type == 'MESH']
    mats = []
    bm = bmesh.new()
    slabs = []                                     # world AABBs of the floor tiles
    for o in obs:
        me = o.data.copy()
        me.transform(o.matrix_world)
        remap = []
        for m in me.materials:
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        for p in me.polygons:
            p.material_index = remap[p.material_index] if remap else 0
        bm.from_mesh(me)
        if o.name.startswith(FLOOR_PREFIX):
            cs = [v.co for v in me.vertices]
            slabs.append([min(c[i] for c in cs) for i in range(3)] + [max(c[i] for c in cs) for i in range(3)])
        bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=WELD)

    def on_slab_side(f):
        if abs(f.normal.z) > 0.01 or any(len(e.link_faces) < 3 for e in f.edges):
            return False
        cs = [v.co for v in f.verts]
        lo = [min(c[i] for c in cs) for i in range(3)]
        hi = [max(c[i] for c in cs) for i in range(3)]
        for x0, y0, z0, x1, y1, z1 in slabs:
            if lo[2] < z0 - WELD or hi[2] > z1 + WELD:
                continue
            for ax, a0, a1, b, b0, b1 in ((0, x0, x1, 1, y0, y1), (1, y0, y1, 0, x0, x1)):
                if hi[ax] - lo[ax] > WELD:
                    continue                       # not in a plane of constant x / y
                if (abs(lo[ax] - a0) < WELD or abs(lo[ax] - a1) < WELD) and lo[b] > b0 - WELD and hi[b] < b1 + WELD:
                    return True
        return False
    hidden = [f for f in bm.faces if on_slab_side(f)]
    bmesh.ops.delete(bm, geom=hidden, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')

    report = dict(
        objects=len(obs), verts=len(bm.verts), faces=len(bm.faces), hidden_faces_removed=len(hidden),
        non_manifold=sum(1 for e in bm.edges if len(e.link_faces) > 2),
        open_edges=sum(1 for e in bm.edges if len(e.link_faces) == 1),
        flipped=sum(1 for e in bm.edges if len(e.link_faces) == 2 and e.link_loops[0].vert is e.link_loops[1].vert))

    name = coll.name + "_MERGED"
    out_coll = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if out_coll.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(out_coll)
    old = bpy.data.objects.get(name)
    if old:
        me_old = old.data
        bpy.data.objects.remove(old)
        bpy.data.meshes.remove(me_old)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    out_coll.objects.link(ob)
    return ob, report


if __name__ == "__main__":
    c = bpy.data.collections[COLLECTION] if COLLECTION else bpy.context.view_layer.active_layer_collection.collection
    ob, rep = merge_house(c)
    print("MERGE_HOUSE", ob.name, rep)
