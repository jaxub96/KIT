# New pieces inspired by studying NW_VILLAGE_01 (the reference asset) directly:
# a tapering octagonal watchtower/dovecote (a "round" silhouette built from an
# octagon, same quads-only rule as everything else), and a village well. Both
# freestanding, chimney/dormer pattern -- not on any weld contract. Needs
# kit_lib.py exec'd first.
import bpy, bmesh, math

TAU = 2 * math.pi


def _ring(bm, cx, cy, z, r, n=8, rot0=0.0):
    return [bm.verts.new((cx + r * math.cos(rot0 + i * TAU / n),
                          cy + r * math.sin(rot0 + i * TAU / n), z)) for i in range(n)]


def _band(bm, r0, r1, faces_out):
    n = len(r0)
    for i in range(n):
        faces_out.append(bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i])))


def _cap(bm, ring, inset_frac=0.4):
    """Close an 8-sided ring with quads, not a single n-gon (this kit
    checks every piece for ngons_bad > 4-sided faces unconditionally, no
    exemption) and not a fan from a centre point (that's a pole). Textbook
    octagon-to-square reduction: pair up adjacent ring verts (0,1)(2,3)
    (4,5)(6,7), inset each pair's own midpoint toward the centre to make
    a 4-point inner square, triangle each aligned pair into its own inner
    point, quad each GAP between one pair and the next across to the two
    neighbouring inner points, then cap the resulting plain 4-gon with one
    final quad. 4 triangles are unavoidable (SKILL.md's "no clean quad
    alternative" exception, same tier as the dormer's 2 cheek walls / the
    road junction's mitre fan) -- everything else here is quads."""
    n = len(ring)
    assert n % 2 == 0
    cx = sum(v.co.x for v in ring) / n
    cy = sum(v.co.y for v in ring) / n
    cz = ring[0].co.z
    m = n // 2
    inner = []
    for k in range(m):
        a, b = ring[2 * k], ring[2 * k + 1]
        mx, my = (a.co.x + b.co.x) / 2, (a.co.y + b.co.y) / 2
        inner.append(bm.verts.new((cx + (mx - cx) * inset_frac, cy + (my - cy) * inset_frac, cz)))
    faces = []
    for k in range(m):
        a, b = ring[2 * k], ring[2 * k + 1]
        faces.append(bm.faces.new((a, b, inner[k])))                                    # aligned-pair triangle
        c = ring[(2 * k + 2) % n]
        faces.append(bm.faces.new((b, c, inner[(k + 1) % m], inner[k])))                 # gap-bridging quad
    faces.append(bm.faces.new(tuple(inner)))                                              # final inner-square cap
    return faces


# ------------------------------------------------------------- round tower --
# An octagonal shaft (reads as "round" at village scale, stays quads-only --
# no circle-from-a-point fan) with a belfry-style open band partway up and a
# steep conical roof. The roof is a FRUSTUM (small flat octagon cap), same
# trick as CHURCH_TOWER_A's own spire -- no pole at the apex.

def build_round_tower(ob, mats, zen_coll=None, seed=101, r=1.15, wall_h=6.2, spire_h=3.4, tip=0.18, n=8):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    bm = bmesh.new()
    OPEN_LO, OPEN_HI = wall_h - 1.6, wall_h - 0.4

    base = _ring(bm, 0, 0, 0.0, r, n)
    open_lo = _ring(bm, 0, 0, OPEN_LO, r, n)
    open_hi = _ring(bm, 0, 0, OPEN_HI, r, n)
    top = _ring(bm, 0, 0, wall_h, r, n)
    tip_ring = _ring(bm, 0, 0, wall_h + spire_h, tip, n)

    shaft_faces, band_faces, spire_faces = [], [], []
    _band(bm, base, open_lo, shaft_faces)
    _band(bm, open_lo, open_hi, band_faces)
    _band(bm, open_hi, top, shaft_faces)
    for i in range(n):
        spire_faces.append(bm.faces.new((top[i], top[(i + 1) % n], tip_ring[(i + 1) % n], tip_ring[i])))
    spire_faces += _cap(bm, tip_ring)                          # small flat cap, quad grid, no pole
    shaft_faces += _cap(bm, list(reversed(base)))              # foot, sits on the ground
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    interior = [v for v in bm.verts if v.co.z > 0.02]
    jitter(bm, interior, (0.025, 0.025, 0.02), seed=seed, keep_planes=[])
    bm.normal_update()

    ob.data.materials.clear()
    ob.data.materials.append(mats["stone"])
    ob.data.materials.append(mats["band"])
    ob.data.materials.append(mats["spire"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    band_set, spire_set = set(band_faces), set(spire_faces)
    for f in bm.faces:
        if f in band_set:
            f.material_index = 1
            set_wrap_uv(f, uvl, (0.4, 0.4), (0.0, 0.0))
        elif f in spire_set:
            f.material_index = 2
            set_wrap_uv(f, uvl, (0.3, 0.3), (0.0, 0.0))
        else:
            f.material_index = 0
            set_wrap_uv(f, uvl, (0.5, 0.5), (0.0, 0.1))
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(2, wall_h)], flat_tri_ok=True, expect_tris=8)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res


# ------------------------------------------------------------------- well ---
# A small octagonal stone well: a short ring wall and a shallow, dark
# interior "water" cap. Deliberately simple -- an earlier version tried
# adding 4 free-standing corner posts + a peaked roof, but connecting them
# to the well ring either left them as disconnected components (SKILL.md's
# "one connected mesh" rule) or, once welded to the rim, pushed several rim
# verts to a real 6-quad pole (3 bands legitimately meeting at one ring:
# the outer wall, the rim shelf, and the roof, 2 faces each). Kept as the
# well ring alone rather than force either compromise; a roofed well-house
# is future work, built with its own dedicated support ring instead of
# retrofitting one onto this ring's own rim.

def build_well(ob, mats, zen_coll=None, seed=111, r=0.65, wall_h=0.75):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    bm = bmesh.new()
    n = 8
    outer_b = _ring(bm, 0, 0, 0.0, r, n)
    outer_t = _ring(bm, 0, 0, wall_h, r, n)
    inner_t = _ring(bm, 0, 0, wall_h - 0.06, r - 0.16, n)
    inner_b = _ring(bm, 0, 0, wall_h - 0.32, r - 0.16, n)
    wall_faces, water_faces = [], []
    _band(bm, outer_b, outer_t, wall_faces)                    # outside of the ring wall
    for i in range(n):                                          # rim (top face of the wall)
        wall_faces.append(bm.faces.new((outer_t[i], outer_t[(i + 1) % n], inner_t[(i + 1) % n], inner_t[i])))
    _band(bm, inner_t, inner_b, water_faces)                    # inside of the shaft
    water_faces += _cap(bm, list(reversed(inner_b)))            # water surface, quad cap
    wall_faces += _cap(bm, list(reversed(outer_b)))             # foot
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    jitter(bm, [v for v in bm.verts if v.co.z > 0.02], (0.015, 0.015, 0.012), seed=seed, keep_planes=[])
    bm.normal_update()

    ob.data.materials.clear()
    ob.data.materials.append(mats["stone"])
    ob.data.materials.append(mats["water"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    water_set = set(water_faces)
    for f in bm.faces:
        if f in water_set:
            f.material_index = 1
            set_wrap_uv(f, uvl, (0.3, 0.3), (0.0, 0.0))
        else:
            f.material_index = 0
            set_wrap_uv(f, uvl, (0.5, 0.5), (0.0, 0.1))
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[], flat_tri_ok=True, expect_tris=8)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res
