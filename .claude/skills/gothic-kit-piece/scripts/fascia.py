# Fascia trim board: a timber board that laps over an upper wall bay's top
# edge and the roof's underside, visually finishing the wall-to-roof joint.
# Needs kit_lib.py exec'd first.
#
# What this does and doesn't fix: SKILL.md lesson 13 established that a wall
# bay's top, the roof run above it, AND both pieces' own sideways neighbours
# can't all four share one edge (a manifold edge holds 2 faces, not 4) --
# that's a real limit of the current piece boundaries. The first version of
# this piece tried to dodge that by vertex-welding its bottom edge directly
# to the wall's own top boundary loop, on the theory that the wall's z=3
# "LIP" row (SKILL.md lesson 09) was one flat straight edge. It isn't: the
# LIP row is a set of points where several *branching* zigzag edges (the
# eave cap's own relief, one row below) happen to touch z=3 -- there is no
# single edge on the wall running from x=0 to x=4 at y=0,z=3 for a fascia's
# bottom edge to coincide with, even though the two *endpoints* do coincide.
# Confirmed directly: the wall's own vertex at (0,0,3) has three link_edges,
# none of which run toward (4,0,3) -- they go to (0,0,2.98) and
# (0,0.4,2.994), both branch stubs of the relief, not a long flat span.
#
# So this piece does NOT claim a vertex weld to the wall, and check_piece
# below does not declare the wall-facing edges as anything other than open.
# It uses the same "surface-mounted, sits flush, doesn't vertex-weld"
# relationship that build_chimney/build_dormer already use successfully:
# embed its bottom edge a few cm *into* the wall's top (past z=3, the way a
# real fascia board is nailed over the wall it covers) so the two surfaces
# overlap rather than merely touch, and let it stand proud of the wall's
# front face and tuck up under the roof's underside. It genuinely improves
# the visual finish of the seam; it does not reduce the model's open-edge
# count, and shouldn't be advertised as if it did.
#
# It DOES weld sideways, end to end, to a second fascia board placed at the
# next bay over: its x=0/x=4 end loops are plain vertical rectangles with no
# wall-derived geometry, so two adjacent copies share identical end loops
# the same way any other kit piece's sideways neighbours do.
import bpy, bmesh, math
from mathutils import Vector

BAY_W = 4.0        # matches the standard wall bay width -- not derived from
                    # any particular wall's own vertices, see docstring above
Z0 = 3.0            # the wall's top row (storey height)
EMBED = 0.06        # how far the board's bottom laps down over the wall's
                    # own top face, so the two surfaces overlap, not just touch
FASCIA_H = 0.22     # board height, measured from Z0 - EMBED
FASCIA_D = 0.05     # board thickness, standing proud of the wall's front face


def build_fascia(ob, mats, zen_coll=None, seed=81, W=BAY_W):
    """Surface-mounted trim board covering the wall/roof seam. See the
    module docstring for why this does not vertex-weld to the wall."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)

    xs = [0.0, W]
    zb = Z0 - EMBED
    zt = zb + FASCIA_H
    bm = bmesh.new()

    def v(x, y, z):
        return bm.verts.new((x, y, z))
    BL = [v(x, 0.0, zb) for x in xs]                   # back-bottom, embedded into the wall
    BR = [v(x, -FASCIA_D, zb) for x in xs]              # front-bottom, proud of the wall face
    TR = [v(x, -FASCIA_D, zt) for x in xs]              # front-top
    TL = [v(x, 0.0, zt) for x in xs]                    # back-top, tucked under the roof

    faces = []
    for i in range(len(xs) - 1):
        faces.append(bm.faces.new((BL[i], BL[i + 1], BR[i + 1], BR[i])))   # underside
        faces.append(bm.faces.new((BR[i], BR[i + 1], TR[i + 1], TR[i])))   # front -- the visible board face
        faces.append(bm.faces.new((TR[i], TR[i + 1], TL[i + 1], TL[i])))   # top -- tucked under the roof
        faces.append(bm.faces.new((TL[i], TL[i + 1], BL[i + 1], BL[i])))   # back -- flush against the wall
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    interior = [vv for vv in bm.verts if xs[0] + 1e-4 < vv.co.x < xs[-1] - 1e-4]
    if interior:
        jitter(bm, interior, (0.0, 0.01, 0.015), seed=seed, keep_planes=[(2, zb), (2, zt)])
    bm.normal_update()

    ob.data.materials.clear()
    ob.data.materials.append(mats["timber"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    TI = (300 / 256, 300 / 512)
    for f in bm.faces:
        f.material_index = 0
        set_beam_uv(f, uvl, "H", TI, 0.2, zb)
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(0, xs[0]), (0, xs[-1])], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res
