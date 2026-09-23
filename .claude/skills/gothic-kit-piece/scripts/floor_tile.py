# Floor tile: 4 m x 4 m timber floor for the ground floor (parterre) and every storey.
# Needs kit_lib.py exec'd first.
#
# Frame: x 0..4 along the planks, y 0..4 across, top of the planks at z = 0, joists
# hang down to z = -0.31. Place at (x0, y0, z): the tile occupies x0..x0+4, y0..y0+4
# and z-0.31..z. Open snap loops at x=0 and x=4 (identical), so tiles weld along x;
# the two y edges are closed (the walls cover them), i.e. one tile fills the 4 m
# house depth and a longer house is a row of tiles.
import bpy, bmesh, math
from mathutils import Vector

PLANK = 0.25          # board width
GROOVE = 0.02         # gap between boards (half of it at each tile edge)
RISE = 0.03           # planks stand this proud of the groove floor
DECK = 0.06           # plank layer thickness (top of planks to underside of the deck)
JOIST_DROP = 0.25     # joists hang this far below the deck
JOIST_W = 0.16        # joists: 4 of them, centred at x = 0.5, 1.5, 2.5, 3.5


def build_floor_tile(ob, mats, zen_coll=None, seed=41, closed_x0=False):
    """closed_x0=True makes the END tile: its x=0 side is closed with a rim (so a floor
    made of two END tiles, one rotated 180, is watertight); x=4 stays an open snap loop."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    bm = bmesh.new()
    # ---- top sheet: planks and grooves at the groove floor level ---------------
    ylines = [0.0]
    for i in range(16):
        ylines += [PLANK * i + GROOVE / 2, PLANK * i + PLANK - GROOVE / 2]
    ylines.append(4.0)
    ylines = sorted(set(round(y, 5) for y in ylines))
    rid_top = []
    for j in range(len(ylines) - 1):
        ym = (ylines[j] + ylines[j + 1]) / 2
        i = int(ym // PLANK)
        inplank = GROOVE / 2 < (ym - PLANK * i) < PLANK - GROOVE / 2
        rid_top.append(("plank", i) if inplank else ("groove",))
    faces_t, VT, _, _ = tensor_partition(bm, [0.0, 4.0], ylines, [rid_top], -(RISE), protect_z=ylines)
    for v in VT.values():                                    # (x, const, y) -> (x, y, const)
        x, c, y = v.co
        v.co = (x, y, c)
    # ---- bottom deck: joists and gaps ------------------------------------------
    jc = [0.5, 1.5, 2.5, 3.5]
    xb = [0.0]
    for c in jc:
        xb += [c - JOIST_W / 2, c + JOIST_W / 2]
    xb.append(4.0)
    rid_b = []
    for i in range(len(xb) - 1):
        xm = (xb[i] + xb[i + 1]) / 2
        rid_b.append(("joist",) if any(abs(xm - c) < JOIST_W / 2 for c in jc) else ("deck", i))
    faces_b, VB, _, _ = tensor_partition(bm, xb, [0.0, 4.0], [[r] for r in rid_b], -DECK, protect_x=xb)
    for v in VB.values():
        x, c, y = v.co
        v.co = (x, y, c)
    # ---- close the two y edges (top sheet -> deck), hidden behind the walls ---------
    for yv in (0.0, 4.0):
        tch = sorted([v for v in VT.values() if abs(v.co.y - yv) < 1e-5], key=lambda v: v.co.x)
        bch = sorted([v for v in VB.values() if abs(v.co.y - yv) < 1e-5], key=lambda v: v.co.x)
        _stitch(bm, tch, bch, 0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # ---- relief: planks up, joists down ------------------------------------------
    planks = [f for f, r in faces_t if r[0] == "plank"]
    ptag = {}
    caps_p, sides_p = extrude_faces(bm, planks, RISE, along=Vector((0, 0, 1)), with_sides=True)
    joists = [f for f, r in faces_b if r[0] == "joist"]
    caps_j, sides_j = extrude_faces(bm, joists, JOIST_DROP, along=Vector((0, 0, -1)), with_sides=True)
    capset_p = set(caps_p)
    plank_of = {f: int(f.calc_center_median().y // PLANK) for f in caps_p}
    # hand-made irregularity (identical at x=0 and x=4 so tiles weld)
    bm.verts.ensure_lookup_table()
    pv = {v for f in caps_p for v in f.verts}
    # mirror-symmetric about y=2 (and periodic in x): the SAME tile welds to itself
    # after a 180 degree turn, which is how the two END tiles meet
    import random
    for v in pv:
        ym = min(v.co.y, 4.0 - v.co.y)
        rnd = random.Random(hash((round(v.co.x % 4.0, 3), round(ym, 3), seed)))
        sgn = 0.0 if abs(v.co.y - 2.0) < 1e-4 else (1.0 if v.co.y < 2.0 else -1.0)
        v.co.y += (rnd.random() * 2 - 1) * 0.002 * sgn
        v.co.z += (rnd.random() * 2 - 1) * 0.003
    if closed_x0:                                            # rim: close x=0 (hidden behind the wall)
        t0 = sorted([v for v in VT.values() if abs(v.co.x) < 1e-5], key=lambda v: v.co.y)
        b0 = sorted([v for v in VB.values() if abs(v.co.x) < 1e-5], key=lambda v: v.co.y)
        _stitch(bm, t0, b0, 1)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    kill = [f for f in bm.faces if all(abs(v.co.x - 4) < 1e-4 for v in f.verts)
            or (not closed_x0 and all(abs(v.co.x) < 1e-4 for v in f.verts))]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.normal_update()
    # ---- materials + UVs -------------------------------------------------------------
    ob.data.materials.clear()
    ob.data.materials.append(mats["floor"])
    ob.data.materials.append(mats["timber"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    joist_faces = set(caps_j) | set(sides_j) | set(joists)
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        c = f.calc_center_median()
        is_joist = f in joist_faces or (c.z < -DECK - 0.01)
        if is_joist:
            f.material_index = 1
            for loop in f.loops:
                p = loop.vert.co
                if abs(f.normal.x) > 0.5:
                    loop[uvl].uv = (0.3 + p.z * TI[0], p.y * TI[1])
                else:
                    loop[uvl].uv = (0.3 + (p.x % 1.0) * TI[0] * 0.3, p.y * TI[1])
            continue
        f.material_index = 0
        i = plank_of.get(f)
        if i is not None:                                      # plank top: one texture plank per board
            row = i % 4
            y0 = PLANK * i + GROOVE / 2
            for loop in f.loops:
                p = loop.vert.co
                loop[uvl].uv = (p.x * 0.5, row * 0.25 + 0.01 + (p.y - y0))
        else:
            set_wrap_uv(f, uvl, (0.5, 0.5), (0.0, 0.0))
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(0, 4.0)] if closed_x0 else [(0, 0.0), (0, 4.0)], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res
