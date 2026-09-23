# Builds blender_work_dir/NW_KIT_VILLAGE_ORGANIC.blend: a small village laid
# out the way NW_VILLAGE_01 (the reference asset) actually is -- buildings
# scattered at VARIED angles (not a 90-degree grid) around a central well,
# on a roughly circular clearing that rises into rolling hills at its edge,
# connected by a worn dirt path instead of paved road tiles.
#
# Studied directly from NW_VILLAGE_01 via the Blender MCP (top-down and
# perspective screenshots, its own material list): an organic clearing, not
# a grid: paths meet at odd angles, not intersections; building silhouettes
# vary a lot (a plain stucco "burgher" house, thatched farm buildings, an
# octagonal watchtower); a central pond/well anchors the whole layout.
# Doesn't attempt to match every building type in the reference (18 door
# markers there: tannery, smithy, sawmill, storehouse, windmill, barn, a
# harbour quarter -- none of those exist in this kit yet, see ROADMAP.md).
# What IS new here, built by studying that file: BURGHER_* (stucco wall
# variant), FARM_*/ROOF_THATCH_* (farmhouse variant), ROUND_TOWER_A (an
# octagonal watchtower, quads-only -- reads "round" without a pole or an
# n-gon cap), WELL_A (the pond/well anchor).
#
#   blender --background --python blender_work_dir/build_organic_village.py
import bpy, bmesh, math, os, random
from mathutils import Matrix, Vector

ROOT = "/Users/jakubjaworski/Creativity/Blender Projects/Blender User Scripts/KIT/"
KIT = ROOT + "blender_work_dir/kit/KIT_WALLS.blend"
OUT = ROOT + "blender_work_dir/NW_KIT_VILLAGE_ORGANIC.blend"
exec(open(ROOT + ".claude/skills/gothic-kit-piece/scripts/kit_lib.py").read())

bpy.ops.wm.read_homefile(use_empty=True)
village_coll = bpy.data.collections.new("VILLAGE"); bpy.context.scene.collection.children.link(village_coll)
zenc = bpy.data.collections.new("VILLAGE_EXPORT_ZEN"); bpy.context.scene.collection.children.link(zenc)

ALL_PIECES = [
    "NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_WINDOW_A", "NW_KIT_WALL_PLAIN_A", "NW_KIT_WALL_PLAIN_LIGHT_A",
    "NW_KIT_WALL_CORNER_A", "NW_KIT_WALL_CORNER_SOLO_A",
    "NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_WALL_UPPER_PLAIN_A", "NW_KIT_WALL_CORNER_UPPER_A",
    "NW_KIT_WALL_BURGHER_DOOR_A", "NW_KIT_WALL_BURGHER_WINDOW_A", "NW_KIT_WALL_BURGHER_PLAIN_A",
    "NW_KIT_WALL_BURGHER_CORNER_A", "NW_KIT_WALL_BURGHER_UPPER_WINDOW_A", "NW_KIT_WALL_BURGHER_UPPER_PLAIN_A",
    "NW_KIT_WALL_BURGHER_CORNER_UPPER_A",
    "NW_KIT_WALL_FARM_DOOR_A", "NW_KIT_WALL_FARM_WINDOW_A", "NW_KIT_WALL_FARM_PLAIN_A", "NW_KIT_WALL_FARM_CORNER_A",
    "NW_KIT_WALL_RH1_DOOR_A", "NW_KIT_WALL_RH1_WINDOW_A", "NW_KIT_WALL_RH1_PLAIN_A", "NW_KIT_WALL_RH1_CORNER_A",
    "NW_KIT_WALL_RH1_UPPER_WINDOW_A", "NW_KIT_WALL_RH1_UPPER_PLAIN_A", "NW_KIT_WALL_RH1_CORNER_UPPER_A",
    "NW_KIT_ROOF_RUN_A", "NW_KIT_ROOF_END_GABLE_A", "NW_KIT_ROOF_THATCH_RUN_A", "NW_KIT_ROOF_THATCH_END_GABLE_A",
    "NW_KIT_CHIMNEY_A", "NW_KIT_ROUND_TOWER_A", "NW_KIT_WELL_A", "NW_KIT_SIGN_POST_A",
]
with bpy.data.libraries.load(KIT, link=False) as (src, dst):
    dst.objects = ALL_PIECES
P = {o.name: o for o in dst.objects}


def M(x, y, z, rot):
    return Matrix.Translation(Vector((x, y, z))) @ Matrix.Rotation(math.radians(rot), 4, 'Z')


# ==================================================================== section
# Same section_placements as build_showcase_level.py -- see that file's own
# copy for the full docstring/derivation. Kept here too so this script
# stays runnable on its own.
def section_placements(x0, y0, rot, S, N, E, W_, corner, n_bays=2, upper=False,
                       US=None, UN=None, UE=None, UW_=None, upper_corner=None,
                       chimney_x=2.4, extra=(), off=0.4, upper_off=0.4,
                       roof_run="NW_KIT_ROOF_RUN_A", roof_gable="NW_KIT_ROOF_END_GABLE_A"):
    def pair(v, n):
        return [v] * n if isinstance(v, str) else list(v)
    S, N = pair(S, n_bays), pair(N, n_bays)
    local = []

    def storey(z, S, N, E, W_, corn, o):
        sx, sy = 2 * o + n_bays * 4.0, 2 * o + 4.0
        for i, nm in enumerate(S):
            local.append((nm, M(o + i * 4.0, 0, z, 0)))
        for i, nm in enumerate(N):
            local.append((nm, M(o + (i + 1) * 4.0, sy, z, 180)))
        local.append((E, M(sx, o, z, 90)))
        local.append((W_, M(0, o + 4.0, z, 270)))
        for (x, y, r) in ((0, 0, 0), (sx, 0, 90), (sx, sy, 180), (0, sy, 270)):
            local.append((corn, M(x, y, z, r)))
    storey(0, S, N, E, W_, corner, off)
    if upper:
        U = "NW_KIT_WALL_UPPER_WINDOW_A"
        storey(3, pair(US or U, n_bays), pair(UN or U, n_bays), UE or U, UW_ or U, upper_corner, upper_off)
    ZR = 6 if upper else 3
    span_y = 2 * off + 4.0
    for k in range(n_bays):
        local.append((roof_run, M(off + k * 4.0, 0, ZR, 0)))
    local.append((roof_gable, M(off - 0.7, 0, ZR, 0)))
    local.append((roof_gable, M(off + n_bays * 4.0 + 0.7, span_y, ZR, 180)))
    if chimney_x is not None:
        local.append(("NW_KIT_CHIMNEY_A", M(chimney_x, off + 2.0, ZR + 2.695, 0)))
    local += list(extra)
    outer = M(x0, y0, 0, rot)
    return [(nm, outer @ mat) for (nm, mat) in local]


def small_house_placements(x0, y0, rot, S, N, E, W_, corner, chimney_x=2.4,
                           roof_run="NW_KIT_ROOF_RUN_A", roof_gable="NW_KIT_ROOF_END_GABLE_A"):
    off = 0.4
    span = 2 * off + 4.0
    local = [
        (S, M(off, 0, 0, 0)), (N, M(off + 4.0, span, 0, 180)),
        (E, M(span, off, 0, 90)), (W_, M(0, off + 4.0, 0, 270)),
    ]
    for (x, y, r) in ((0, 0, 0), (span, 0, 90), (span, span, 180), (0, span, 270)):
        local.append((corner, M(x, y, 0, r)))
    ZR = 3
    local += [(roof_run, M(off, 0, ZR, 0)),
             (roof_gable, M(off - 0.7, 0, ZR, 0)),
             (roof_gable, M(off + 4.7, span, ZR, 180)),
             ("NW_KIT_CHIMNEY_A", M(chimney_x, off + 2.0, ZR + 2.695, 0))]
    outer = M(x0, y0, 0, rot)
    return [(nm, outer @ mat) for (nm, mat) in local]


def build_merged(name, placements, collection):
    house_mats, bm = [], bmesh.new()
    for pname, mat in placements:
        ob = P[pname]
        me = ob.data.copy()
        slots = [house_mats.index(m) if m in house_mats else (house_mats.append(m) or len(house_mats) - 1)
                 for m in ob.data.materials]
        for p in me.polygons:
            p.material_index = slots[p.material_index]
        me.transform(mat)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)
    groups = {}
    for f in bm.faces:
        groups.setdefault(frozenset(v.index for v in f.verts), []).append(f)
    inner = [f for g in groups.values() if len(g) == 2 for f in g]
    bmesh.ops.delete(bm, geom=inner, context='FACES')
    bmesh.ops.delete(bm, geom=[e for e in bm.edges if not e.link_faces], context='EDGES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context='VERTS')
    overlap = len([e for e in bm.edges if len(e.link_faces) > 2])
    for f in bm.faces:
        f.smooth = False
    hme = bpy.data.meshes.new(name)
    bm.to_mesh(hme); bm.free()
    for m in house_mats:
        hme.materials.append(m)
    ob = bpy.data.objects.new(name, hme); collection.objects.link(ob)
    return ob, overlap


# =================================================================== village
# Buildings scattered at varied angles around the well, NOT a 90-degree
# grid -- each is its own section_placements/small_house_placements call
# with an arbitrary `rot`, which works because every wall/roof/corner is
# built at a local origin and wrapped in one outer transform (SKILL.md
# lesson 19) -- nothing about the geometry cares which world direction it
# faces.
houses = {}

houses["BURGHER"], ovBu = build_merged("NW_HOUSE_BURGHER", section_placements(
    7.5, 4.0, 18, n_bays=2, upper=True,
    S=("NW_KIT_WALL_BURGHER_DOOR_A", "NW_KIT_WALL_BURGHER_WINDOW_A"),
    N=("NW_KIT_WALL_BURGHER_PLAIN_A", "NW_KIT_WALL_BURGHER_WINDOW_A"),
    E="NW_KIT_WALL_BURGHER_WINDOW_A", W_="NW_KIT_WALL_BURGHER_PLAIN_A",
    corner="NW_KIT_WALL_BURGHER_CORNER_A",
    UE="NW_KIT_WALL_BURGHER_UPPER_WINDOW_A", UW_="NW_KIT_WALL_BURGHER_UPPER_WINDOW_A",
    UN=("NW_KIT_WALL_BURGHER_UPPER_WINDOW_A", "NW_KIT_WALL_BURGHER_UPPER_WINDOW_A"),
    upper_corner="NW_KIT_WALL_BURGHER_CORNER_UPPER_A", chimney_x=1.6,
), village_coll)

houses["FARM"], ovFa = build_merged("NW_HOUSE_FARM", small_house_placements(
    -3.0, 8.5, -30,
    S="NW_KIT_WALL_FARM_DOOR_A", N="NW_KIT_WALL_FARM_PLAIN_A",
    E="NW_KIT_WALL_FARM_WINDOW_A", W_="NW_KIT_WALL_FARM_PLAIN_A",
    corner="NW_KIT_WALL_CORNER_SOLO_A", chimney_x=2.2,
    roof_run="NW_KIT_ROOF_THATCH_RUN_A", roof_gable="NW_KIT_ROOF_THATCH_END_GABLE_A",
), village_coll)

houses["ROW"], ovRow = build_merged("NW_HOUSES_ROW", (
    small_house_placements(8.0, -6.5, 105,
        S="NW_KIT_WALL_RH1_PLAIN_A", N="NW_KIT_WALL_RH1_PLAIN_A",
        E="NW_KIT_WALL_RH1_DOOR_A", W_="NW_KIT_WALL_RH1_PLAIN_A",
        corner="NW_KIT_WALL_CORNER_SOLO_A", chimney_x=2.4) +
    [(nm, M(8.0, -6.5, 0, 105) @ Matrix.Translation((4.8, 0, 0)) @ mat)
     for (nm, mat) in small_house_placements(0, 0, 0,
        S="NW_KIT_WALL_RH1_PLAIN_A", N="NW_KIT_WALL_RH1_PLAIN_A",
        E="NW_KIT_WALL_RH1_WINDOW_A", W_="NW_KIT_WALL_RH1_PLAIN_A",
        corner="NW_KIT_WALL_CORNER_SOLO_A", chimney_x=1.8)]
), village_coll)

houses["COTTAGE"], ovCo = build_merged("NW_HOUSE_COTTAGE", small_house_placements(
    -9.0, -4.0, 210,
    S="NW_KIT_WALL_WINDOW_A", N="NW_KIT_WALL_PLAIN_LIGHT_A",
    E="NW_KIT_WALL_PLAIN_LIGHT_A", W_="NW_KIT_WALL_DOOR_A",
    corner="NW_KIT_WALL_CORNER_SOLO_A", chimney_x=1.6,
), village_coll)

houses["STANDARD"], ovSt = build_merged("NW_HOUSE_STANDARD", section_placements(
    2.0, -11.0, 340, n_bays=2, upper=True,
    S=("NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_WINDOW_A"), N=("NW_KIT_WALL_PLAIN_A", "NW_KIT_WALL_WINDOW_A"),
    E="NW_KIT_WALL_PLAIN_A", W_="NW_KIT_WALL_WINDOW_A", corner="NW_KIT_WALL_CORNER_A",
    upper_corner="NW_KIT_WALL_CORNER_UPPER_A", chimney_x=6.4,
    extra=[("NW_KIT_SIGN_POST_A", M(0.4, 0, 0, 0) @ M(1.4, -0.55, 0, 0))],
), village_coll)

# freestanding pieces: the well at the clearing's own centre, the tower on
# its edge like a real watchtower overlooking the approach
tower_src = P["NW_KIT_ROUND_TOWER_A"]
tower_me = tower_src.data.copy(); tower_me.transform(M(-2.0, -9.5, 0, 0))
tower_ob = bpy.data.objects.new("NW_WATCHTOWER", tower_me)
for m in tower_src.data.materials:
    tower_me.materials.append(m)
village_coll.objects.link(tower_ob)

well_src = P["NW_KIT_WELL_A"]
well_me = well_src.data.copy(); well_me.transform(M(0, 0, 0, 0))
well_ob = bpy.data.objects.new("NW_VILLAGE_WELL", well_me)
for m in well_src.data.materials:
    well_me.materials.append(m)
village_coll.objects.link(well_ob)

for ob, ov in ((houses["BURGHER"], ovBu), (houses["FARM"], ovFa), (houses["ROW"], ovRow),
              (houses["COTTAGE"], ovCo), (houses["STANDARD"], ovSt)):
    print(ob.name, "faces:", len(ob.data.polygons), "overlap:", ov)

# --------------------------------------------------------------- terrain -----
# A CIRCULAR clearing (radial falloff, not the rectangular core+collar the
# showcase village uses) rising into rolling hills at its edge -- matches
# NW_VILLAGE_01's own layout far better than a rectangular tile footprint
# would (see this file's own module docstring for what was studied there).
# A dirt path band (a second material zone keyed off distance-to-nearest-
# path-segment, not a separate modular tile) connects the well to each
# building's own doorstep, the same "worn ground, not paved road" look the
# reference uses for its own connecting paths.
CLEAR_R = 15.0
COLLAR = 3.0
PAD_R = CLEAR_R + 26.0
NX, NY = 56, 56
_rng = random.Random(4242)

# doorstep points the paths radiate out to (rough door positions, by eye)
DOORSTEPS = [(7.9, 4.4), (-3.6, 8.9), (10.6, -4.4), (-9.9, -3.0), (0.6, -10.8)]


def _terrain_height(x, y):
    d = math.hypot(x, y)
    if d <= CLEAR_R:
        return 0.0
    rise = min((d - CLEAR_R) / 16.0, 1.0)
    hill = (0.55 + 0.45 * math.sin(x * 0.1 + 2.1) * math.cos(y * 0.09 - 0.6)
            + 0.3 * math.sin(x * 0.19 - y * 0.15))
    return rise * max(0.0, 4.2 * hill)


def _dist_to_path(x, y):
    """Distance from (x,y) to the nearest segment of the well-to-doorstep
    path network -- small values are 'on the path'."""
    best = 1e9
    for (dx, dy) in DOORSTEPS:
        # distance to the segment from (0,0) to (dx,dy)
        seg = Vector((dx, dy))
        t = max(0.0, min(1.0, Vector((x, y)).dot(seg) / seg.length_squared))
        proj = seg * t
        best = min(best, (Vector((x, y)) - proj).length)
    return best


tbm = bmesh.new()
tgrid = {}
for ix in range(NX + 1):
    for iy in range(NY + 1):
        x = -PAD_R + 2 * PAD_R * ix / NX
        y = -PAD_R + 2 * PAD_R * iy / NY
        z = _terrain_height(x, y)
        tgrid[(ix, iy)] = tbm.verts.new((x, y, z))
for ix in range(NX):
    for iy in range(NY):
        tbm.faces.new((tgrid[(ix, iy)], tgrid[(ix + 1, iy)], tgrid[(ix + 1, iy + 1)], tgrid[(ix, iy + 1)]))
bmesh.ops.recalc_face_normals(tbm, faces=tbm.faces[:])
for v in tbm.verts:
    if v.co.z > 0.02:
        v.co.z += (_rng.random() - 0.5) * 0.12
tbm.normal_update()

terrain_mats = [ensure_material("NW_Nature_Waldboden_03"), ensure_material("NW_Nature_Stein_01"),
               ensure_material("NW_Nature_Path_02")]
tuvl = tbm.loops.layers.uv.new("Float2")
tme = bpy.data.meshes.new("NW_TERRAIN_ORGANIC")
for m in terrain_mats:
    tme.materials.append(m)
for f in tbm.faces:
    c = f.calc_center_median()
    if c.z > 2.6:
        f.material_index = 1                         # rocky, at real height
    elif _dist_to_path(c.x, c.y) < 1.1 and c.z < 0.05:
        f.material_index = 2                         # worn dirt path, clearing only
    else:
        f.material_index = 0                         # grass
    for loop in f.loops:
        loop[tuvl].uv = (loop.vert.co.x * 0.2, loop.vert.co.y * 0.2)
tbm.to_mesh(tme)
tbm.free()
terrain = bpy.data.objects.new("NW_TERRAIN_ORGANIC", tme); village_coll.objects.link(terrain)

# ---------------------------------------------------------------- finish -----
for ob in list(houses.values()) + [tower_ob, well_ob, terrain]:
    make_export_copy(ob, zenc)
for im in bpy.data.images:
    if im.source == 'FILE' and not im.packed_file:
        try:
            im.pack()
        except Exception:
            pass
bpy.ops.wm.save_as_mainfile(filepath=OUT)
result = dict(burgher_overlap=ovBu, farm_overlap=ovFa, row_overlap=ovRow,
              cottage_overlap=ovCo, standard_overlap=ovSt,
              terrain_faces=len(terrain.data.polygons), file=OUT, size=os.path.getsize(OUT))
print("RESULT:", result)
