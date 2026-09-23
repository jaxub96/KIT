# Scattered ruin debris: standalone decoration pieces that stand next to
# WALL_RUIN_A, not derived from it and not on its weld contract (nothing
# here needs to share a vertex with anything else -- it's scatter, placed
# by eye like the ruin site's own three wall remnants already are). Needs
# kit_lib.py exec'd first.
import bpy, bmesh, math, random

# ---------------------------------------------------------------- rubble pile
# A height-field grid, same "grid not rings" rule as gothic-terrain-piece:
# a top-only cap (no sides/bottom -- it sits IN the ground like any rubble
# scatter mesh, the underside is never seen), edges pinned to z=0 so it
# meets a flat ground/yard tile with no visible seam, interior verts raised
# by a falloff-weighted random height so the pile reads as a real irregular
# mound, not a smooth dome or a spike.

def build_rubble_pile(ob, mats, zen_coll=None, seed=71, nx=6, nz=5, w=1.3, d=1.0, h=0.42):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    rnd = random.Random(seed)
    bm = bmesh.new()
    xs = [i / (nx - 1) * w - w / 2 for i in range(nx)]
    ys = [j / (nz - 1) * d - d / 2 for j in range(nz)]
    grid = {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            # falloff: 0 at the rim, up to 1 at the centre, so the pile
            # closes flush to the ground all the way round
            fx = 1.0 - abs(x / (w / 2))
            fy = 1.0 - abs(y / (d / 2))
            fall = max(0.0, min(fx, fy))
            z = 0.0 if fall <= 0.0 else h * (fall ** 1.4) * (0.6 + 0.4 * rnd.random())
            grid[(i, j)] = bm.verts.new((x, y, z))
    faces = []
    for i in range(nx - 1):
        for j in range(nz - 1):
            faces.append(bm.faces.new((grid[(i, j)], grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # extra jitter on interior verts only (rim stays pinned at z=0 so it
    # keeps meeting the ground flush)
    interior = [grid[(i, j)] for i in range(1, nx - 1) for j in range(1, nz - 1)]
    jitter(bm, interior, (0.05, 0.05, 0.03), seed=seed + 3, keep_planes=[])
    bm.normal_update()

    ob.data.materials.clear()
    ob.data.materials.append(mats["rubble"])
    ob.data.materials.append(mats["stone"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        c = f.calc_center_median()
        # a few embedded cut-stone blocks (from the wall that fell here)
        # scattered among the rubble, keyed off position so it's stable
        f.material_index = 1 if (round(c.x, 2) * 7 + round(c.y, 2) * 13) % 5 < 1 else 0
        set_wrap_uv(f, uvl, (0.5, 0.5), (0.0, 0.0))
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(2, 0.0)], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res


# ---------------------------------------------------------------- fallen beam
# A rough-hewn timber lying on the ground: a plain quad box (never
# triangulated -- the "break" reads through irregular silhouette jitter,
# not a fractured cross-section) tilted slightly off level and half-buried,
# as if it dropped when the roof/upper storey it belonged to came down.

def build_fallen_beam(ob, mats, zen_coll=None, seed=81, length=2.1, w=0.22):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    rnd = random.Random(seed)
    bm = bmesh.new()
    n = 5   # stations along the beam's length, for a bit of bend/taper
    BL, BR, TR, TL = [], [], [], []   # 4 rings forming the beam's box cross-section
    for i in range(n):
        t = i / (n - 1)
        x = t * length
        sag = -0.03 * math.sin(math.pi * t)     # settles slightly in the middle
        taper = 1.0 - 0.15 * t                    # narrows a touch toward the broken end
        hw = (w / 2) * taper
        z0 = 0.02 + sag                            # underside, half-buried in the ground
        z1 = z0 + w * taper                        # top of the timber's cross-section
        BL.append(bm.verts.new((x, -hw, z0)))
        BR.append(bm.verts.new((x, hw, z0)))
        TR.append(bm.verts.new((x, hw, z1)))
        TL.append(bm.verts.new((x, -hw, z1)))
    for i in range(n - 1):
        bm.faces.new((BL[i], BR[i], BR[i + 1], BL[i + 1]))   # bottom
        bm.faces.new((BR[i], TR[i], TR[i + 1], BR[i + 1]))   # +y side
        bm.faces.new((TR[i], TL[i], TL[i + 1], TR[i + 1]))   # top
        bm.faces.new((TL[i], BL[i], BL[i + 1], TL[i + 1]))   # -y side
    bm.faces.new((BL[0], TL[0], TR[0], BR[0]))                # near end cap
    bm.faces.new((BR[-1], TR[-1], TL[-1], BL[-1]))            # broken end cap
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    interior = [v for ring in (BL, BR, TR, TL) for v in ring[1:-1]]
    jitter(bm, interior, (0.012, 0.012, 0.012), seed=seed + 5, keep_planes=[])
    bm.normal_update()

    ob.data.materials.clear()
    ob.data.materials.append(mats["timber"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        f.material_index = 0
        set_beam_uv(f, uvl, "H", TI, 0.1, 0.0)
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res
