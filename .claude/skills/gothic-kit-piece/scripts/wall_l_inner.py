# Inner-corner L wall: two wall bays meeting at a concave (re-entrant) corner,
# e.g. where a wing leaves a house. Needs kit_lib.py exec'd first.
#
# Two plain 4 m bays placed at an inner corner overlap in the 0.4 x 0.4 square
# behind the corner, and each one's front runs 0.4 m into the other wall. The L
# replaces both bays with the SAME footprint (two 4 m inside faces from the
# corner point), so it drops into a house in place of the two bays:
#   * each leg is a kit bay with its front fitted from 4.0 to 3.6 m (_x_map):
#     the corner end loop lands on the 45 deg mitre, the end post there is
#     widened to POST_W, and the far end loop stays exactly where it was (it
#     still welds to a corner block or the next bay). Piecewise linear in x and
#     linear in depth: flat faces stay flat.
#   * the two legs' corner ends are a bay's x=0 and x=4 end loops, which every
#     bay shares, so they coincide on the mitre vertex for vertex and weld: the
#     two widened end posts become one timber post turning the inner corner
#     (and the stone footing, eave and storey seam turn with it).
#   * the storey seams get the same shear on both storeys, so a ground L and an
#     upper L stack and weld like bays do.
# Frame (rebased, like a corner): origin = the inside corner point on the floor.
# Leg A runs +x (outer face y = -0.4, facing -y), leg B runs -y (outer face
# x = 0.4, facing +x); far ends at x = 4 and y = -4 are open snap planes.
import bpy, bmesh
from mathutils import Matrix, Vector

L_T = 0.4           # wall thickness = the mitre's size
POST = 0.15         # a bay's half-width end post
POST_W = 0.30       # the inner corner post's face width on each leg


def _x_map(x, y, corner_at_start):
    """Bay x -> leg x at legacy depth y. The end post at the corner end is
    widened from 0.15 to POST_W and starts on the mitre; the rest of the bay
    is fitted between the post and the untouched far end. Piecewise linear in
    x (the bay has a vertex column at the post edge, no face spans it) and
    linear in y at every x: flat faces stay flat."""
    if corner_at_start:
        m = L_T - y                                    # mitre x at this depth
        if x <= POST + 1e-6:
            return m + x * POST_W / POST
        return m + POST_W + (x - POST) * (4.0 - m - POST_W) / (4.0 - POST)
    m = 4.0 - L_T + y
    if x >= 4.0 - POST - 1e-6:
        return m - (4.0 - x) * POST_W / POST
    return x * (m - POST_W) / (4.0 - POST)


def _face_uv_maps(bm, uvl):
    """Per face: its UV as an affine function of position in the face's own
    plane (basis e1, e2), fitted from its loops. Every kit UV mapping is planar
    per face, so this reproduces it exactly."""
    maps = {}
    for f in bm.faces:
        ls = list(f.loops)
        p0 = ls[0].vert.co.copy()
        e1 = (ls[1].vert.co - p0)
        if e1.length < 1e-9:
            continue
        e1.normalize()
        e2 = f.normal.cross(e1).normalized()
        rows = [((l.vert.co - p0).dot(e1), (l.vert.co - p0).dot(e2), 1.0) for l in ls]
        ata = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
        for r in rows:
            for i in range(3):
                for j in range(3):
                    ata[i][j] += r[i] * r[j]
        try:
            inv = ata.inverted()
        except ValueError:
            continue
        coef = []
        for k in range(2):
            atb = Vector([sum(r[i] * l[uvl].uv[k] for r, l in zip(rows, ls)) for i in range(3)])
            coef.append(inv @ atb)
        maps[f] = (e1, e2, coef)
    return maps


def _leg(bm_src, corner_at_start, plaster_slot=0):
    """Copy of a rebased bay (inside face y=0, outer y=-T) in the legacy depth
    frame (outer face y=0), with its corner end on the mitre and a wide post.
    Timber and stone UVs follow the move at the bay's own texel density: each
    loop's UV is its face's mapping evaluated at the vertex's new x (a face
    whose plane the move leaves, e.g. an end-post side, keeps its UVs)."""
    bm = bm_src.copy()
    bm.normal_update()
    uvl = bm.loops.layers.uv["Float2"]
    maps = _face_uv_maps(bm, uvl)
    in_post = lambda x: x <= POST + 1e-4 if corner_at_start else x >= 4.0 - POST - 1e-4
    post_plaster = [f for f in bm.faces if f.material_index == plaster_slot and all(in_post(v.co.x) for v in f.verts)]
    dx = {}
    for v in bm.verts:
        y = v.co.y + L_T                       # legacy depth: 0 = outer face, T = inside face
        nx = _x_map(v.co.x, y, corner_at_start)
        dx[v] = nx - v.co.x
        v.co.x = nx
        v.co.y = y
    for f, (e1, e2, coef) in maps.items():
        if f.material_index == plaster_slot:
            # plaster is a cropped panel texture (set_window_uv): extending its
            # UVs runs past the crop into the painted frame, so it keeps the
            # bay's UVs (squeezed with the leg, at most ~15 %, invisible on plaster)
            continue
        for l in f.loops:
            d = Vector((dx[l.vert], 0.0, 0.0))
            a, b = d.dot(e1), d.dot(e2)
            l[uvl].uv = (l[uvl].uv[0] + coef[0][0] * a + coef[0][1] * b,
                         l[uvl].uv[1] + coef[1][0] * a + coef[1][1] * b)
    bm.normal_update()
    for f in post_plaster:                     # the inside strip behind the post doubled in width
        set_window_uv(f, uvl, (1.5, 1.0), (0.12, 0.88, 0.43, 0.90))
    return bm


def build_l_inner(ob, mesh_a, mesh_b, plaster_slot=0):
    """ob <- L wall from two rebased kit bay meshes: mesh_a = leg along +x
    (its x=0 end goes to the corner), mesh_b = leg along -y (its x=4 end goes
    to the corner; seen from outside it is the left leg)."""
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    # basic-set bays share the slot order plaster / timber / stone: the L keeps
    # leg A's material objects (whatever the user swapped in) for both legs
    mats = list(mesh_a.materials)
    out = bmesh.new()
    for mesh, start in ((mesh_a, True), (mesh_b, False)):
        src = bmesh.new()
        src.from_mesh(mesh)
        leg = _leg(src, start, plaster_slot)
        src.free()
        if not start:                          # B: corner end x'=3.6+y -> mitre of A (0.4-y, y)
            leg.transform(Matrix.Translation((L_T, -3.6, 0)) @ Matrix.Rotation(1.5707963267948966, 4, 'Z'))
        tmp = bpy.data.meshes.new("_l_leg")
        leg.to_mesh(tmp)
        leg.free()
        out.from_mesh(tmp)                     # appends (keeps UVs "Float2" and material indices)
        bpy.data.meshes.remove(tmp)
    bmesh.ops.remove_doubles(out, verts=out.verts[:], dist=1e-4)   # the mitre welds here
    out.transform(Matrix.Translation((0, -L_T, 0)))                 # origin = inside corner point
    ob.data.materials.clear()
    for m in mats:
        ob.data.materials.append(m)
    write_piece(ob, out)
    out.free()
    return check_piece(ob, snap_planes=[(0, 4.0), (1, -4.0), (2, 0.0), (2, 3.0)], flat_tri_ok=True)
