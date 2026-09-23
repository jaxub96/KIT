# Jettied (overhanging) upper storey: the SAME upper wall bay construction,
# shifted outward as a whole AFTER normal construction -- translating
# everything (relief, jitter, UVs are unaffected by position) together
# keeps the wall's own internal detail correct without wall_bay.py needing
# to know a jetty exists at all. The corner is built the usual way, from
# THIS wall's own (already-shifted) boundary loop, so it automatically
# matches. Needs kit_lib.py, wall_bay.py, weld_pieces.py exec'd first.
import bpy, bmesh

JETTY = 0.15   # overhang depth, comfortably inside the roof's own 0.40 m eave overhang


def build_jetty_wall(ob, spec, mats, zen_coll=None, seed=25):
    """Build a normal upper wall bay from `spec` (storey="upper" is implied
    -- a jetty is an upper-storey feature), then push the WHOLE piece JETTY
    metres further out. Weld contract, corner derivation, roof/floor
    relationships all work exactly like a normal upper bay, just at a
    shifted Y -- a real jetty overhangs the floor below it and reaches a
    bit further out than the ground wall, which is exactly what shifting
    the whole footprint does."""
    spec = dict(spec)
    spec["storey"] = "upper"
    build_wall_bay(ob, spec, mats, zen_coll=None, seed=seed)   # ZEN copy made AFTER the shift, below
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for v in bm.verts:
        v.co.y -= JETTY
    bm.normal_update()
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(0, 0.0), (0, 4.0)], flat_tri_ok=True)
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
        make_export_copy(ob, zen_coll)
    return res
