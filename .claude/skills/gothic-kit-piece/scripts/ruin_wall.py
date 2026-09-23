# Ruined/weathered ground wall bay. The broken top is modelled as several
# rectangular "openings" (the part of each zone above its own break height)
# through slab_planar -- the SAME proven front/back/reveal/side machinery
# wall_bay.py uses for windows and doors, just with the openings running
# off the top of the domain instead of sitting inside it. Needs kit_lib.py
# and wall_bay.py exec'd first (reuses WALL_T, FOOT).
import bpy, bmesh, math

TOP = 3.00   # nominal full height, matching an intact ground wall's eave line

# Per-column break height: the end posts (more resilient, half the post
# width each) stand fullest; the rest breaks down unevenly, each stretch
# stopping at a row an intact wall would ALSO have a horizontal line on
# (mid rail / eave / base rail), so it reads as a real building that lost
# its upper storey and roof, not a random jagged cutout.
RUIN_ZONES = [(0.00, 0.15, TOP), (0.15, 0.55, 1.62), (0.55, 1.35, 0.65),
              (1.35, 2.15, 2.70), (2.15, 2.55, 0.65), (2.55, 3.85, 1.50),
              (3.85, 4.00, TOP)]
HOLE = (1.5, 2.0, 0.65, 1.5)          # a fallen-through window, in the tallest zone


def build_ruin_wall(ob, mats, zen_coll=None, seed=61):
    """Ground-floor ruin: broken top, one hole, stone footing below FOOT,
    weathered rubble above. Open at x=0/4 (may not weld to a pristine wall
    bay -- the point of a ruin is usually to stand on its own or next to
    another ruin) and at z=0 (sits on terrain like any ground bay)."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    gaps = [(x0, x1, z, TOP) for (x0, x1, z) in RUIN_ZONES if z < TOP - 1e-6]
    openings = gaps + [HOLE]
    xl = [0.0, 4.0] + [c for r in openings for c in (r[0], r[1])]
    zl = [0.0, FOOT, TOP] + [c for r in openings for c in (r[2], r[3])]
    xs, zs = lines_from(xl), lines_from(zl)
    inside = lambda x, z: any(r[0] < x < r[1] and r[2] < z < r[3] for r in openings)
    nx, nz = len(xs) - 1, len(zs) - 1
    rid = [[None] * nz for _ in range(nx)]
    for i in range(nx):
        for k in range(nz):
            cx, cz = (xs[i] + xs[i + 1]) / 2, (zs[k] + zs[k + 1]) / 2
            if inside(cx, cz):
                continue
            rid[i][k] = "stone" if cz < FOOT else "rubble"
    bm = bmesh.new()
    r = slab_planar(bm, xs, zs, rid, openings, (0.0, 4.0), zs, thickness=WALL_T)
    # open the bottom, the two ends (kit convention: those are snap planes,
    # not closed edges) and the domain's own z=TOP line: the two end posts
    # are the only solid cells that reach it, everything between them is
    # already open (part of a "gap" opening), but slab_planar's outer-edge
    # stitch doesn't know that -- it bridges ALL of z=TOP into one strip,
    # spanning straight across the gap as if the two posts were connected
    # up there. Each zone's OWN break line is already capped correctly by
    # its own opening's reveal (openings don't span each other), so it's
    # only this outer TOP line that needs dropping, not the whole piece's
    # broken silhouette.
    kill = [f for f in r["side"] if all(abs(v.co.z) < 1e-4 for v in f.verts)
            or all(abs(v.co.x) < 1e-4 for v in f.verts) or all(abs(v.co.x - 4.0) < 1e-4 for v in f.verts)
            or all(abs(v.co.z - TOP) < 1e-3 for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.verts.ensure_lookup_table()
    interior = [v for v in bm.verts if 1e-4 < v.co.x < 4.0 - 1e-4]
    jitter(bm, interior, (0.02, 0.02, 0.03), seed=seed, keep_planes=[(2, 0.0)])
    bm.normal_update()
    ob.data.materials.clear()
    slot = {"stone": 0, "rubble": 1}
    ob.data.materials.append(mats["stone"])
    ob.data.materials.append(mats["rubble"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    for f in bm.faces:
        if not f.is_valid:
            continue
        c = f.calc_center_median()
        k = "stone" if c.z < FOOT else "rubble"
        f.material_index = slot[k]
        if k == "stone":
            set_wrap_uv(f, uvl, (0.566, 0.566), (0.0, 0.10))
        else:
            set_wrap_uv(f, uvl, (0.5, 0.5), (0.0, 0.0))
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(0, 0.0), (0, 4.0), (2, 0.0), (2, TOP)], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res
