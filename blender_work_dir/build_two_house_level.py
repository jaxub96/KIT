# Builds blender_work_dir/NW_SAMPLE_LEVEL_2HOUSES.blend: two different welded
# kit houses connected by the modular terrain/yard/road tiles (not the
# one-off procedural terrain build_sample_level.py used).
#
#   blender --background --python blender_work_dir/build_two_house_level.py
#   (or exec() it through the blender MCP execute_blender_code tool)
import bpy, bmesh, math, os
from mathutils import Matrix, Vector

ROOT = "/Users/jakubjaworski/Creativity/Blender Projects/Blender User Scripts/KIT/"
KIT = ROOT + "blender_work_dir/kit/KIT_WALLS.blend"
OUT = ROOT + "blender_work_dir/NW_SAMPLE_LEVEL_2HOUSES.blend"
exec(open(ROOT + ".claude/skills/gothic-kit-piece/scripts/kit_lib.py").read())

bpy.ops.wm.read_homefile(use_empty=True)
level = bpy.data.collections.new("LEVEL"); bpy.context.scene.collection.children.link(level)
zenc = bpy.data.collections.new("LEVEL_EXPORT_ZEN"); bpy.context.scene.collection.children.link(zenc)

# ---------------------------------------------------------------- append ----------
HOUSE_PIECES = ["NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_WINDOW_A", "NW_KIT_WALL_PLAIN_A", "NW_KIT_WALL_PLAIN_LIGHT_A",
                "NW_KIT_WALL_WINDOW_TWIN_A", "NW_KIT_WALL_UPPER_PLAIN_A",
                "NW_KIT_WALL_CORNER_A", "NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_WALL_CORNER_UPPER_A",
                "NW_KIT_ROOF_RUN_A", "NW_KIT_ROOF_END_GABLE_A", "NW_KIT_CHIMNEY_A", "NW_KIT_FLOOR_END_A"]
GROUND_PIECES = ["NW_KIT_TERRAIN_FLAT_A", "NW_KIT_TERRAIN_YARD_A", "NW_KIT_ROAD_STRAIGHT_A", "NW_KIT_ROAD_JUNCTION_A"]
PIECES = HOUSE_PIECES + GROUND_PIECES
with bpy.data.libraries.load(KIT, link=False) as (src, dst):
    dst.objects = PIECES
P = {o.name: o for o in dst.objects}
D = 4.8


def M(x, y, z, rot):
    return Matrix.Translation(Vector((x, y, z))) @ Matrix.Rotation(math.radians(rot), 4, 'Z')


def house_placements(x0, y0, S, N, E, W_, corner, US=None, UN=None, UE=None, UW_=None, chimney_x=6.4):
    """S/N/E/W_ = (piece_A, piece_B) or a single name for both bays of that
    wall; corner = the ground corner piece name (upper corner is always
    NW_KIT_WALL_CORNER_UPPER_A, only one variant exists). US/UN/UE/UW_ are
    the matching upper-storey walls (default NW_KIT_WALL_UPPER_WINDOW_A
    everywhere, same as before, if left out)."""
    def pair(v):
        return (v, v) if isinstance(v, str) else v
    S, N = pair(S), pair(N)
    U = "NW_KIT_WALL_UPPER_WINDOW_A"
    US, UN = pair(US or (U, U)), pair(UN or (U, U))
    UE, UW_ = UE or U, UW_ or U
    placements = []

    def storey(z, S, N, E, W_, corn):
        placements.extend([(S[0], M(x0 + 0.4, y0, z, 0)), (S[1], M(x0 + 4.4, y0, z, 0)),
                           (N[0], M(x0 + 4.4, y0 + D, z, 180)), (N[1], M(x0 + 8.4, y0 + D, z, 180)),
                           (E, M(x0 + 8.8, y0 + 0.4, z, 90)), (W_, M(x0, y0 + 4.4, z, 270))])
        for (x, y, r) in ((x0, y0, 0), (x0 + 8.8, y0, 90), (x0 + 8.8, y0 + D, 180), (x0, y0 + D, 270)):
            placements.append((corn, M(x, y, z, r)))
    storey(0, S, N, E, W_, corner)
    storey(3, US, UN, UE, UW_, "NW_KIT_WALL_CORNER_UPPER_A")
    for z in (0.46, 3.0):
        placements += [("NW_KIT_FLOOR_END_A", M(x0 + 0.4, y0 + 0.4, z, 0)),
                       ("NW_KIT_FLOOR_END_A", M(x0 + 8.4, y0 + 4.4, z, 180))]
    ZR = 6
    placements += [("NW_KIT_ROOF_RUN_A", M(x0 + 0.4, y0, ZR, 0)), ("NW_KIT_ROOF_RUN_A", M(x0 + 4.4, y0, ZR, 0)),
                   ("NW_KIT_ROOF_END_GABLE_A", M(x0 - 0.3, y0, ZR, 0)),
                   ("NW_KIT_ROOF_END_GABLE_A", M(x0 + 9.1, y0 + D, ZR, 180)),
                   ("NW_KIT_CHIMNEY_A", M(x0 + chimney_x, y0 + 2.4, ZR + 2.695, 0))]
    return placements


def build_house(name, x0, y0, S, N, E, W_, corner, US=None, UN=None, UE=None, UW_=None, chimney_x=6.4):
    house_mats, bm = [], bmesh.new()
    for pname, mat in house_placements(x0, y0, S, N, E, W_, corner, US, UN, UE, UW_, chimney_x):
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
    house = bpy.data.objects.new(name, hme); level.objects.link(house)
    return house, overlap


# House A: fully-framed, symmetric window rhythm, windows on every upper
# bay, chimney centred on the ridge.
houseA, ovA = build_house("NW_HOUSE_A", 0.0, 0.0,
                          S=("NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_WINDOW_A"),
                          N=("NW_KIT_WALL_PLAIN_A", "NW_KIT_WALL_WINDOW_A"),
                          E="NW_KIT_WALL_PLAIN_A", W_="NW_KIT_WALL_WINDOW_A",
                          corner="NW_KIT_WALL_CORNER_A")
# House B: deliberately different massing, not just a palette swap --
# twin-light windows instead of single ones, light (no mid rail) framing on
# the plain sides, BLANK upper storey on three sides (NW_KIT_WALL_UPPER_PLAIN_A,
# so it doesn't repeat house A's all-windows upper floor), and the chimney
# at the gable end instead of the ridge centre.
X0_B = 16.0
houseB, ovB = build_house("NW_HOUSE_B", X0_B, 0.0,
                          S=("NW_KIT_WALL_WINDOW_TWIN_A", "NW_KIT_WALL_DOOR_A"),
                          N=("NW_KIT_WALL_PLAIN_LIGHT_A", "NW_KIT_WALL_PLAIN_LIGHT_A"),
                          E="NW_KIT_WALL_PLAIN_LIGHT_A", W_="NW_KIT_WALL_WINDOW_TWIN_A",
                          corner="NW_KIT_WALL_CORNER_A",
                          US=("NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_WALL_UPPER_PLAIN_A"),
                          UN="NW_KIT_WALL_UPPER_PLAIN_A",
                          UE="NW_KIT_WALL_UPPER_PLAIN_A", UW_="NW_KIT_WALL_UPPER_PLAIN_A",
                          chimney_x=1.4)

# ---------------------------------------------------------------- ground ----------
# 4x4m tile grid. i,j are tile indices (world x = i*4, y = j*4). Doors face
# south (y=0): house A's door bay is at world x 1.4-2.6 (tile i=0); house
# B's is at world x0_B+1.4..0_B+2.6 = 17.4-18.6 (tile i=4).
TILE = 4.0
FLAT, YARD, ROAD, JUNC = "flat", "yard", "road", "junction"
grid = {}
for i in range(-1, 8):
    for j in range(-2, 3):
        grid[(i, j)] = (FLAT, 0)
# dooryards around each house footprint (x 0..12 for A, 16..28 for B; y 0..8)
for i in (0, 1, 2):
    for j in (0, 1):
        grid[(i, j)] = (YARD, 0)
for i in (4, 5, 6):
    for j in (0, 1):
        grid[(i, j)] = (YARD, 0)
# the road: one east-west row in front of both houses, with a junction at
# each house's own doorstep column so a spur could branch off toward it
for i in range(-1, 8):
    grid[(i, -1)] = (ROAD, 90)
grid[(0, -1)] = (JUNC, 0)
grid[(4, -1)] = (JUNC, 0)

PIECE_OF = {FLAT: "NW_KIT_TERRAIN_FLAT_A", YARD: "NW_KIT_TERRAIN_YARD_A",
            ROAD: "NW_KIT_ROAD_STRAIGHT_A", JUNC: "NW_KIT_ROAD_JUNCTION_A"}


def GM(i, j, rot):
    # A tile's local frame is a corner-anchored [0,4]x[0,4] square, so a
    # plain M(i*4, j*4, 0, rot) rotates it about that CORNER -- for rot=90
    # its footprint lands a whole tile-width off from the (i,j) cell the
    # grid meant, overlapping the neighbour. Rotate about the tile's own
    # centre instead so its footprint is always exactly [i*4,i*4+4] x
    # [j*4,j*4+4], whatever the rotation.
    c = TILE / 2.0
    return (Matrix.Translation(Vector((i * TILE + c, j * TILE + c, 0.0)))
            @ Matrix.Rotation(math.radians(rot), 4, 'Z') @ Matrix.Translation(Vector((-c, -c, 0.0))))


ground_mats, gbm = [], bmesh.new()
for (i, j), (kind, rot) in grid.items():
    ob = P[PIECE_OF[kind]]
    me = ob.data.copy()
    slots = [ground_mats.index(m) if m in ground_mats else (ground_mats.append(m) or len(ground_mats) - 1)
             for m in ob.data.materials]
    for p in me.polygons:
        p.material_index = slots[p.material_index]
    me.transform(GM(i, j, rot))
    gbm.from_mesh(me)
    bpy.data.meshes.remove(me)
bmesh.ops.remove_doubles(gbm, verts=gbm.verts[:], dist=0.001)
for f in gbm.faces:
    f.smooth = False
gme = bpy.data.meshes.new("NW_GROUND")
gbm.to_mesh(gme)
ground_overlap = len([e for e in gbm.edges if len(e.link_faces) > 2])
ground_open = len([e for e in gbm.edges if len(e.link_faces) < 2])
gbm.free()
for m in ground_mats:
    gme.materials.append(m)
ground = bpy.data.objects.new("NW_GROUND", gme); level.objects.link(ground)

# ---------------------------------------------------------------- finish -----------
for ob in (houseA, houseB, ground):
    make_export_copy(ob, zenc)
for im in bpy.data.images:
    if im.source == 'FILE' and not im.packed_file:
        try:
            im.pack()
        except Exception:
            pass
for o in list(bpy.data.objects):
    if o.name in PIECES:
        bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
result = dict(houseA_faces=len(houseA.data.polygons), houseA_overlap=ovA,
              houseB_faces=len(houseB.data.polygons), houseB_overlap=ovB,
              ground_faces=len(ground.data.polygons), ground_overlap=ground_overlap, ground_open=ground_open,
              file=OUT, size=os.path.getsize(OUT))
