# Shed-roof dormer: sits on an existing roof run's slope the same way
# build_chimney's base does (a "saddle" that follows the roof's own zu(y)
# underside function), rather than requiring the roof run to have a literal
# hole cut into it -- a surface-mounted dormer, not a Boolean one. A full
# hip roof (the roof run's own cross-section tapering to a point at the
# building end) would need reworking build_roof_run's fundamental sweep;
# this is the tractable alternative from that same "roof variant" ask.
# Needs kit_lib.py and roof_gable.py exec'd first (reuses KNEE/TAN/W-style
# roof geometry via a local zu()).
import bpy, bmesh, math
from mathutils import Vector

DW = 1.2            # dormer width (x)
DEPTH = 1.0          # footprint depth along the roof slope (y)
FRONT_H = 0.85       # front wall height above the roof surface
WIN_W, WIN_H = 0.45, 0.55
SURF = 0.08          # roof run's shingle-surface offset above zu(y) (course thickness + fascia)


def build_dormer(ob, mats, zen_coll=None, seed=71, x0=1.4, y_lo=0.7, W=4.8):
    """A small shed-roofed, single-window dormer. Place at world
    (roof_run_x + x0_local... ) i.e. directly on top of an already-placed
    NW_KIT_ROOF_RUN_A -- same x,y,z origin as the run (it reads the run's
    own slope via the same KNEE/TAN/W the run uses, so it sits flush)."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)

    def zu(y):
        return KNEE + TAN * (y if y <= W / 2 else W - y)
    y_hi = y_lo + DEPTH
    zf, zb = zu(y_lo) + SURF, zu(y_hi) + SURF        # roof surface at the dormer's front/back
    ztop = zf + FRONT_H

    bm = bmesh.new()

    def v(x, y, z):
        return bm.verts.new((x, y, z))
    BL, BR = v(x0, y_hi, zb), v(x0 + DW, y_hi, zb)

    kinds = {}
    # front wall, with a window hole: a simple 3x3 grid (sill/lintel rows,
    # jamb columns), reveal quads bridge front to a recessed back plane.
    # The wall's 4 outer corners ARE the front-wall corners used below for
    # the cheeks/roof -- built once here and reused, not duplicated, or
    # they'd be coincident-but-disconnected verts and split the mesh.
    xs = [x0, x0 + (DW - WIN_W) / 2, x0 + (DW + WIN_W) / 2, x0 + DW]
    zs = [zf, zf + (FRONT_H - WIN_H) / 2, zf + (FRONT_H + WIN_H) / 2, ztop]
    FV = {}
    for i, x in enumerate(xs):
        for k, z in enumerate(zs):
            FV[(i, k)] = v(x, y_lo, z)
    FL_b, FR_b, FL_t, FR_t = FV[(0, 0)], FV[(3, 0)], FV[(0, 3)], FV[(3, 3)]
    win_cell = (1, 1)
    front_faces = []
    for i in range(3):
        for k in range(3):
            if (i, k) == win_cell:
                continue
            f = bm.faces.new((FV[(i, k)], FV[(i + 1, k)], FV[(i + 1, k + 1)], FV[(i, k + 1)]))
            kinds[f] = "plaster"
            front_faces.append(f)
    RECESS = 0.10
    BV = {(i, k): v(xs[i], y_lo - RECESS, zs[k]) for (i, k) in ((1, 1), (2, 1), (2, 2), (1, 2))}
    ring = [(1, 1), (2, 1), (2, 2), (1, 2)]
    for idx in range(4):
        a, b = ring[idx], ring[(idx + 1) % 4]
        f = bm.faces.new((FV[a], FV[b], BV[b], BV[a]))
        kinds[f] = "timber"

    left = bm.faces.new((FL_b, FL_t, BL))
    right = bm.faces.new((FR_b, BR, FR_t))
    roof = bm.faces.new((FL_t, FR_t, BR, BL))
    kinds[left] = kinds[right] = "timber"
    kinds[roof] = "roof"

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    jitter(bm, [vv for vv in bm.verts if vv not in (BL, BR)], (0.008, 0.008, 0.008), seed=seed)
    bm.normal_update()

    ob.data.materials.clear()
    slot = {}
    for k in ("plaster", "timber", "roof"):
        ob.data.materials.append(mats[k])
        slot[k] = len(ob.data.materials) - 1
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        k = kinds.get(f, "timber")
        f.material_index = slot[k]
        if k == "plaster":
            set_window_uv(f, uvl, (1.2, 1.0), (0.12, 0.88, 0.43, 0.90))
        elif k == "roof":
            for loop in f.loops:
                c = loop.vert.co
                loop[uvl].uv = ((c.x - x0) * 0.5, roof_slope_uv(c.y, c.z, W=W))
        else:
            set_beam_uv(f, uvl, "V", TI, 0.1, x0)
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(1, y_lo + 0), (2, zf)], flat_tri_ok=True, expect_tris=2)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res
