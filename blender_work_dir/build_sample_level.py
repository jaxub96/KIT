# Builds blender_work_dir/NW_SAMPLE_LEVEL.blend: a small Gothic-style sample level
# (terrain + welded two-storey kit house + a road that starts at the front door).
#
#   blender --background --python blender_work_dir/build_sample_level.py
#   (or exec() it through the blender MCP execute_blender_code tool)
#
# Conventions (see .claude/skills/gothic-terrain-piece): one connected quad grid,
# no poles, flat shaded, one UV map named Float2, stock level materials, quads
# master + hidden triangulated _ZEN copy. The road is a 2-column band of the same
# grid, warped sideways so it meanders; its UVs run along its arc length.
import bpy, bmesh, math, os
from mathutils import Matrix, Vector

ROOT = "/Users/jakubjaworski/Creativity/Blender Projects/Blender User Scripts/KIT/"
KIT = ROOT + "blender_work_dir/kit/KIT_WALLS.blend"
OUT = ROOT + "blender_work_dir/NW_SAMPLE_LEVEL.blend"
exec(open(ROOT + ".claude/skills/gothic-kit-piece/scripts/kit_lib.py").read())

bpy.ops.wm.read_homefile(use_empty=True)
level = bpy.data.collections.new("LEVEL"); bpy.context.scene.collection.children.link(level)
zenc = bpy.data.collections.new("LEVEL_EXPORT_ZEN"); bpy.context.scene.collection.children.link(zenc)

# ---------------------------------------------------------------- house ----------
PIECES = ["KIT_WALL_DOOR_A", "KIT_WALL_WINDOW_A", "KIT_WALL_PLAIN_A", "KIT_WALL_CORNER_A",
          "KIT_WALL_UPPER_WINDOW_A", "KIT_WALL_CORNER_UPPER_A", "KIT_ROOF_RUN_A",
          "KIT_ROOF_END_GABLE_A", "KIT_CHIMNEY_A", "KIT_FLOOR_END_A", "KIT_FLOOR_GROUND_END_A"]
with bpy.data.libraries.load(KIT, link=False) as (src, dst):
    dst.objects = PIECES
P = {o.name: o for o in dst.objects}
D = 4.8
def M(x, y, z, rot):
    return Matrix.Translation(Vector((x, y, z))) @ Matrix.Rotation(math.radians(rot), 4, 'Z')
placements = []
def storey(z, S, N, E, W_, corner):
    placements.extend([(S[0], M(0.4, 0, z, 0)), (S[1], M(4.4, 0, z, 0)),
                       (N[0], M(4.4, D, z, 180)), (N[1], M(8.4, D, z, 180)),
                       (E, M(8.8, 0.4, z, 90)), (W_, M(0, 4.4, z, 270))])
    for (x, y, r) in ((0, 0, 0), (8.8, 0, 90), (8.8, D, 180), (0, D, 270)):
        placements.append((corner, M(x, y, z, r)))
storey(0, ("KIT_WALL_DOOR_A", "KIT_WALL_WINDOW_A"), ("KIT_WALL_PLAIN_A", "KIT_WALL_WINDOW_A"),
       "KIT_WALL_PLAIN_A", "KIT_WALL_WINDOW_A", "KIT_WALL_CORNER_A")
U = "KIT_WALL_UPPER_WINDOW_A"
storey(3, (U, U), (U, U), U, U, "KIT_WALL_CORNER_UPPER_A")
for fl, z in (("KIT_FLOOR_GROUND_END_A", 0.0), ("KIT_FLOOR_END_A", 3.0)):
    placements += [(fl, M(0.4, 0.4, z, 0)), (fl, M(8.4, 4.4, z, 180))]
ZR = 6
placements += [("KIT_ROOF_RUN_A", M(0.4, 0, ZR, 0)), ("KIT_ROOF_RUN_A", M(4.4, 0, ZR, 0)),
               ("KIT_ROOF_END_GABLE_A", M(-0.3, 0, ZR, 0)), ("KIT_ROOF_END_GABLE_A", M(9.1, D, ZR, 180)),
               ("KIT_CHIMNEY_A", M(6.4, 2.4, ZR + 2.695, 0))]
house_mats, bm = [], bmesh.new()
for name, mat in placements:
    ob = P[name]
    me = ob.data.copy()
    slots = [house_mats.index(m) if m in house_mats else (house_mats.append(m) or len(house_mats) - 1)
             for m in ob.data.materials]
    for p in me.polygons:
        p.material_index = slots[p.material_index]
    me.transform(legacy_placement(ob.name, mat))
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)        # weld every seam of the kit
groups = {}
for f in bm.faces:
    groups.setdefault(frozenset(v.index for v in f.verts), []).append(f)
inner = [f for g in groups.values() if len(g) == 2 for f in g]      # coincident pairs = interior faces
bmesh.ops.delete(bm, geom=inner, context='FACES')
bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context='VERTS')
for f in bm.faces:
    f.smooth = False
hme = bpy.data.meshes.new("NW_SAMPLE_HOUSE")
bm.to_mesh(hme); bm.free()
for m in house_mats:
    hme.materials.append(m)
house = bpy.data.objects.new("NW_SAMPLE_HOUSE", hme); level.objects.link(house)

# ---------------------------------------------------------------- terrain ----------
def sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)
XC0, HALF = 3.3, 2.0                                  # road centre on the door, half width 2 (2 cells of 2 m)
def g(Y):                                             # sideways meander of every row south of the house
    return 5.5 * sstep(-8, -30, Y) * math.sin((-Y - 8) * 0.22)
def xc(Y):
    return XC0 + g(Y)
xl = [XC0 - HALF + 2.0 * k for k in range(-15, 17)]   # 1.3, 3.3, 5.3 are grid lines: road = 2 columns
yl = [2.0 * j for j in range(-24, 13)]
def zterr(X, Y):
    n = (1.6 * math.sin(X * 0.11 + 1.3) * math.cos(Y * 0.09) + 1.1 * math.sin(X * 0.23 + Y * 0.17)
         + 0.6 * math.sin(X * 0.41 - Y * 0.33))
    hill = 7.0 * math.exp(-(((X - 4) ** 2) / (2 * 14 ** 2) + ((Y - 16) ** 2) / (2 * 8 ** 2)))
    r = max(abs(X - 4) / 30.0, abs(Y + 12) / 36.0)
    rim = 6.0 * sstep(0.55, 1.0, r)
    return n + hill + rim
def zfinal(X, Y):
    z = zterr(X, Y)
    d = max(0.0, abs(X - 4.4) - 8.0, abs(Y - 2.4) - 6.0)
    w = 1.0 - sstep(0.0, 6.0, d)                       # flat yard around the house
    z = z * (1 - w) + 0.05 * w
    if Y <= 0.0:
        dx = abs(X - xc(Y))
        if Y <= -2.0:                                  # gently falling road with a little undulation
            hr = 0.05 + (Y + 2.0) * 0.05 + 0.12 * math.sin(Y * 0.3) * sstep(-2.0, -6.0, Y)
        else:                                          # last 2 m: rise to the door threshold (0.46)
            up = sstep(-2, 0, Y) * max(0.0, 1.0 - dx / 2.0)
            hr = 0.05 + 0.41 * up
        wr = 1.0 - sstep(HALF, HALF + 5.0, dx)
        z = z * (1 - wr) + hr * wr
    return z
tm = bmesh.new()
V = [[None] * len(yl) for _ in xl]
for i, x in enumerate(xl):
    for j, y in enumerate(yl):
        X = x + g(y)
        V[i][j] = tm.verts.new((X, y, zfinal(X, y)))
cells = []
for i in range(len(xl) - 1):
    for j in range(len(yl) - 1):
        cells.append((tm.faces.new((V[i][j], V[i + 1][j], V[i + 1][j + 1], V[i][j + 1])), i, j))
tm.normal_update()
GRASS, ROCK, DIRT, COBBLE, PATH = ("NW_Seq_Ground_02_XL", "NW_Nature_Stein_03", "NW_City_DirtyGround_01",
                                   "NW_City_Pflasterstein_01", "NW_Seq_GrassPath_01_XL")
tmats = [ensure_material(n) for n in (GRASS, ROCK, DIRT, COBBLE, PATH)]
uvl = tm.loops.layers.uv.new("Float2")
# arc length of the road centre per row, so the path texture runs along the road
S = {0.0: 0.0}
acc = 0.0
ys_road = sorted([y for y in yl if y <= 0.0], reverse=True)
for a, b in zip(ys_road[:-1], ys_road[1:]):
    acc += math.hypot(xc(b) - xc(a), b - a)
    S[b] = acc
zones = {}
for f, i, j in cells:
    c = f.calc_center_median()
    dx = abs(c.x - xc(c.y))
    road = c.y < 0.0 and dx <= HALF
    if road:
        zone = 3 if c.y > -7.0 else 4
    elif abs(c.x - 4.4) < 6.5 and abs(c.y - 2.4) < 4.5:
        zone = 2
    elif f.normal.z < 0.72:
        zone = 1
    else:
        zone = 0
    f.material_index = zone
    f.smooth = False
    if zone == 4:                                      # the path tile is one road width wide: u across, v along
        for loop in f.loops:
            p = loop.vert.co
            loop[uvl].uv = ((p.x - xc(p.y)) / (2 * HALF) + 0.5, S[round(p.y, 4)] / (2 * HALF))
    else:
        set_grid_uv(f, uvl, {0: 5.0, 1: 4.0, 2: 3.0, 3: 2.0}[zone])
tme = bpy.data.meshes.new("NW_SAMPLE_TERRAIN")
tm.to_mesh(tme); tm.free()
for m in tmats:
    tme.materials.append(m)
for p in tme.polygons:
    p.use_smooth = False
terrain = bpy.data.objects.new("NW_SAMPLE_TERRAIN", tme); level.objects.link(terrain)

# ---------------------------------------------------------------- finish -----------
for ob in (terrain, house):
    make_export_copy(ob, zenc)
for im in bpy.data.images:
    if im.source == 'FILE' and not im.packed_file:
        try:
            im.pack()
        except Exception:
            pass
for o in list(bpy.data.objects):                       # drop the appended kit pieces
    if o.name in PIECES:
        bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
result = dict(terrain_faces=len(terrain.data.polygons), house_faces=len(house.data.polygons),
              house_verts=len(house.data.vertices), file=OUT, size=os.path.getsize(OUT),
              terrain_bounds=tuple(round(v, 1) for v in (min(v.co.x for v in tme.vertices), max(v.co.x for v in tme.vertices),
                                                         min(v.co.y for v in tme.vertices), max(v.co.y for v in tme.vertices))))
