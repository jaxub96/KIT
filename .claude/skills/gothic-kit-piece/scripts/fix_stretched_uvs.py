# Post-pass: re-project timber faces whose texture is stretched (or collapsed).
# Stretch = ratio of the two singular values of the face's UV->3D map, measured in
# texture pixels (so a 256 x 512 image counts right). Faces over LIMIT get a planar
# projection in their own plane: grain (V) along the face's longest edge, 300 px/m
# like the rest of the kit's timber, centred where the face's UVs already were (so
# it keeps the same part of the beam texture).
#   Kit:  Blender -b kit/KIT_WALLS.blend --python fix_stretched_uvs.py -- KIT_WALL_STONE_ KIT_WALL_UPPER_ ...
#   Live: exec it, then fix_mesh(mesh)
import bpy, bmesh, math, sys

LIMIT = 2.2
TIMBER_PX_PER_M = 300


def image_size(m):
    if m and m.node_tree:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image and n.image.size[0]:
                return tuple(n.image.size)
    return (512, 512)


def stretch(f, uvl, W, H):
    ls = list(f.loops)
    a, b, c = max(((ls[0], ls[i], ls[i + 1]) for i in range(1, len(ls) - 1)),
                  key=lambda t: (t[1].vert.co - t[0].vert.co).cross(t[2].vert.co - t[0].vert.co).length)
    p0 = a.vert.co
    e1, e2 = b.vert.co - p0, c.vert.co - p0
    x = e1.normalized()
    y = e1.cross(e2).normalized().cross(x)
    P1, P2 = (e1.dot(x), e1.dot(y)), (e2.dot(x), e2.dot(y))
    d1 = ((b[uvl].uv.x - a[uvl].uv.x) * W, (b[uvl].uv.y - a[uvl].uv.y) * H)
    d2 = ((c[uvl].uv.x - a[uvl].uv.x) * W, (c[uvl].uv.y - a[uvl].uv.y) * H)
    det = P1[0] * P2[1] - P2[0] * P1[1]
    if abs(det) < 1e-12:
        return 999.0
    i = (P2[1] / det, -P2[0] / det, -P1[1] / det, P1[0] / det)
    A, B = d1[0] * i[0] + d2[0] * i[2], d1[0] * i[1] + d2[0] * i[3]
    C, D = d1[1] * i[0] + d2[1] * i[2], d1[1] * i[1] + d2[1] * i[3]
    s, dt = A * A + B * B + C * C + D * D, abs(A * D - B * C)
    q = math.sqrt(max(s * s / 4 - dt * dt, 0))
    return math.sqrt(s / 2 + q) / max(math.sqrt(max(s / 2 - q, 0)), 1e-6)


def reproject_timber(f, uvl, W, H, d=TIMBER_PX_PER_M):
    e = max(f.edges, key=lambda e: e.calc_length())
    v = (e.verts[1].co - e.verts[0].co).normalized()
    u = f.normal.cross(v).normalized()
    P = [(l.vert.co.dot(u) * d / W, l.vert.co.dot(v) * d / H) for l in f.loops]
    n = len(P)
    cu, cv = sum(p[0] for p in P) / n, sum(p[1] for p in P) / n
    tu, tv = sum(l[uvl].uv.x for l in f.loops) / n, sum(l[uvl].uv.y for l in f.loops) / n
    for l, p in zip(f.loops, P):
        l[uvl].uv = (p[0] - cu + tu, p[1] - cv + tv)


def fix_mesh(me, timber_prefix="NW_City_WoodBeam"):
    bm = bmesh.new()
    bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active
    fixed = 0
    for f in bm.faces:
        m = me.materials[f.material_index]
        if not (m and m.name.startswith(timber_prefix)):
            continue
        W, H = image_size(m)
        if stretch(f, uvl, W, H) > LIMIT:
            reproject_timber(f, uvl, W, H)
            fixed += 1
    if fixed:
        bm.to_mesh(me)
    bm.free()
    return fixed


if __name__ == "__main__" and "--" in sys.argv:
    prefixes = sys.argv[sys.argv.index("--") + 1:]
    report = {}
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.name.startswith(tuple(prefixes)) and ob.data.users >= 1:
            n = fix_mesh(ob.data)
            if n:
                report[ob.name] = n
    print("FIX_UV_REPORT", report)
    bpy.ops.wm.save_mainfile()
