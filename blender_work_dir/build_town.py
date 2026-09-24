# Builds blender_work_dir/NW_KIT_TOWN.blend: a small hill town from BOTH kit
# families (Gothic timber set + Maya stone set), on procedural terrain.
#
#   Blender -b --python blender_work_dir/build_town.py -- [RENDER]
#   (NOT --factory-startup: the Blend-Zen "Zen Waypoint Tools" add-on must be
#    enabled -- its zCVobLight helper creates the ZenGin lights.)
#
# What is procedural (Geometry Nodes, live in the saved file -- tweak the
# modifier inputs in the Properties editor, or move things in the viewport):
#   * TOWN_TERRAIN: noise hills + a big hill around the HILL empty, flattened
#     under every house plot / plaza (TOWN_PLOTS, TOWN_PLAZAS) and along every
#     road curve (TOWN_ROAD_CURVES), with a grass / dirt / rock material split.
#     Move a house (its TOWN_HOUSE_* empty) or a road control point and the
#     ground follows. Inputs: size, resolution, seed, noise, hill, flatten
#     falloffs, road width, material tiling.
#   * TOWN_ROADS_MAIN / TOWN_ROADS_PATH: road ribbons swept along the curves.
#   * TOWN_SCATTER_TREES / TOWN_SCATTER_BUSHES: Gothic plants from the Gothic
#     asset library, scattered outside the town (seed, density, distance).
# What is placed once by this script (real objects, exported as ZenGin VOBs):
#   houses (collection instances of kit pieces), zCVob props (market stalls,
#   well, carts, barrels, lamps, braziers, statue...), zCVobLight lights.
# Customise the layout in the CONFIG section below and rerun.
import bpy, bmesh, math, os, sys, random
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = "/Users/jakubjaworski/Creativity/Blender Projects/Blender User Scripts/KIT/"
KIT_WALLS = ROOT + "blender_work_dir/kit/KIT_WALLS.blend"
KIT_MAYA = ROOT + "blender_work_dir/kit/KIT_MAYA.blend"
GOTHIC_LIB = "/Users/jakubjaworski/Creativity/Blender Projects/GothicBlenderAssets-master/Blender_Asset_Library_Gothic/"
PROPS = GOTHIC_LIB + "Props/Props.blend"
OUT = ROOT + "blender_work_dir/NW_KIT_TOWN.blend"
RENDER_DIR = ROOT + "blender_work_dir/town_renders/"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
exec(open(ROOT + ".claude/skills/gothic-kit-piece/scripts/kit_lib.py").read())   # ensure_material

# =============================================================== CONFIG
SEED = 7
TERRAIN = dict(size=300.0, res=0.9, noise_height=2.8, noise_scale=1.6, slope=(0.0, 0.045),
               hill=(24.0, 50.0), hill_radius=36.0, hill_height=9.5, rim_start=70.0, rim_height=22.0,
               plot_falloff=7.0, road_half=2.6, road_falloff=4.5, tile=8.0)
TERRAIN_OFFSET = -0.04     # ground sits this far under plazas / road surfaces
HOUSE_SINK = 0.07          # house base under its plot level (walls sit IN the ground)

# Plazas: name -> (polygon xy, material, level group)
PLAZAS = {
    "MARKET_SQUARE": ([(-11, -9), (11, -9), (11, 9), (-11, 9)], "NW_City_Pflasterstein_01", "square"),
    "TEMPLE_COURT": ([(7, 39.5), (29, 39.5), (29, 50.8), (7, 50.8)], "NW_Misc_Maya_Ground_01", "temple"),
}

# Gothic wall families: role -> piece
G_STYLES = {
    "basic": dict(door="KIT_WALL_DOOR_A", window="KIT_WALL_WINDOW_A", twin="KIT_WALL_WINDOW_TWIN_A",
                  shutter="KIT_WALL_WINDOW_SHUTTER_A", plain="KIT_WALL_PLAIN_A", light="KIT_WALL_PLAIN_LIGHT_A",
                  corner="KIT_WALL_CORNER_A", corner_solo="KIT_WALL_CORNER_SOLO_A",
                  u_window="KIT_WALL_UPPER_WINDOW_A", u_plain="KIT_WALL_UPPER_PLAIN_A", corner_upper="KIT_WALL_CORNER_UPPER_A",
                  run="KIT_ROOF_RUN_A", gable="KIT_ROOF_END_GABLE_A"),
    "civic": dict(door="KIT_WALL_CIVIC_DOOR_A", window="KIT_WALL_CIVIC_WINDOW_A", plain="KIT_WALL_CIVIC_PLAIN_A",
                  corner="KIT_WALL_CIVIC_CORNER_A", corner_solo="KIT_WALL_CIVIC_CORNER_A",
                  u_window="KIT_WALL_CIVIC_UPPER_WINDOW_A", u_plain="KIT_WALL_CIVIC_UPPER_PLAIN_A",
                  corner_upper="KIT_WALL_CIVIC_CORNER_UPPER_A", run="KIT_ROOF_RUN_A", gable="KIT_ROOF_END_GABLE_A"),
    "burgher": dict(door="KIT_WALL_BURGHER_DOOR_A", window="KIT_WALL_BURGHER_WINDOW_A", plain="KIT_WALL_BURGHER_PLAIN_A",
                    corner="KIT_WALL_BURGHER_CORNER_A", corner_solo="KIT_WALL_BURGHER_CORNER_A",
                    u_window="KIT_WALL_BURGHER_UPPER_WINDOW_A", u_plain="KIT_WALL_BURGHER_UPPER_PLAIN_A",
                    corner_upper="KIT_WALL_BURGHER_CORNER_UPPER_A", run="KIT_ROOF_RUN_A", gable="KIT_ROOF_END_GABLE_A"),
    "farm": dict(door="KIT_WALL_FARM_DOOR_A", window="KIT_WALL_FARM_WINDOW_A", plain="KIT_WALL_FARM_PLAIN_A",
                 corner="KIT_WALL_FARM_CORNER_A", corner_solo="KIT_WALL_FARM_CORNER_A",
                 run="KIT_ROOF_THATCH_RUN_A", gable="KIT_ROOF_THATCH_END_GABLE_A"),
}
M_STYLE = dict(door="KIT_MAYA_WALL_DOOR_A", window="KIT_MAYA_WALL_WINDOW_A", twin="KIT_MAYA_WALL_WINDOW_TWIN_A",
               plain="KIT_MAYA_WALL_PLAIN_A", cracked="KIT_MAYA_WALL_PLAIN_CRACKED_A", wcracked="KIT_MAYA_WALL_WINDOW_CRACKED_A",
               niche="KIT_MAYA_WALL_NICHE_A", corner="KIT_MAYA_WALL_CORNER_A",
               u_window="KIT_MAYA_WALL_UPPER_WINDOW_A", u_twin="KIT_MAYA_WALL_UPPER_WINDOW_TWIN_A",
               u_plain="KIT_MAYA_WALL_UPPER_PLAIN_A", u_cracked="KIT_MAYA_WALL_UPPER_CRACKED_A",
               u_niche="KIT_MAYA_WALL_UPPER_NICHE_A", corner_upper="KIT_MAYA_WALL_CORNER_UPPER_A",
               parapet="KIT_MAYA_PARAPET_A", p_spout="KIT_MAYA_PARAPET_SPOUT_A", p_frieze="KIT_MAYA_PARAPET_FRIEZE_A",
               p_corner="KIT_MAYA_PARAPET_CORNER_A")

# Buildings. pos = inner room corner (x, y), rot = degrees (0: door side faces
# -Y). Gothic: bays along x (depth is always one 4 m bay). Maya: cells (nx, ny).
# Walls per side: S/N lists run along x, E/W along y; U* = upper storey.
# level = plots in the same group share one height; None = the land's own.
HOUSES = [
    dict(name="TOWNHALL", kit="gothic", style="civic", bays=3, storeys=2, pos=(-6, 10.6), rot=0, level="square",
         S=["window", "door", "window"], N=["plain", "window", "plain"], E=["window"], W=["plain"],
         US=["u_window"] * 3, UN=["u_plain", "u_window", "u_plain"], UE=["u_window"], UW=["u_window"], chimney=9.4, stair=True),
    dict(name="SHOP", kit="gothic", style="burgher", bays=2, storeys=2, pos=(-12.6, -4), rot=90, level="square",
         S=["door", "window"], N=["plain", "window"], E=["window"], W=["plain"],
         US=["u_window", "u_window"], UN=["u_plain", "u_window"], UE=["u_window"], UW=["u_plain"], chimney=6.2, stair=True),
    dict(name="TEMPLE", kit="maya", cells=(3, 2), storeys=2, pos=(12, 51.6), rot=0, level="temple", parapet="p_frieze",
         S=["niche", "door", "niche"], N=["niche", "plain", "niche"], E=["window", "niche"], W=["niche", "window"],
         US=["u_niche", "u_twin", "u_niche"], UN=["u_plain", "u_niche", "u_plain"], UE=["u_window", "u_niche"], UW=["u_niche", "u_window"],
         stair=True),
    dict(name="STORAGE", kit="gothic", style="farm", bays=3, storeys=1, pos=(-44, -18), rot=0, level=None,
         S=["window", "door", "plain"], N=["plain", "plain", "window"], E=["plain"], W=["window"]),
    dict(name="HOUSE_01", kit="gothic", style="basic", bays=2, storeys=2, pos=(7.6, -18), rot=270, level=None,
         S=["door", "shutter"], N=["plain", "window"], E=["twin"], W=["light"],
         US=["u_window", "u_window"], UN=["u_plain", "u_window"], UE=["u_window"], UW=["u_plain"], chimney=6.0, stair=True),
    dict(name="HOUSE_02", kit="gothic", style="basic", bays=1, storeys=1, pos=(-5.1, -24), rot=90, level=None,
         S=["door"], N=["window"], E=["plain"], W=["window"], chimney=2.2),
    dict(name="HOUSE_03", kit="maya", cells=(2, 1), storeys=2, pos=(6.5, -38), rot=270, level=None, parapet="p_spout",
         S=["door", "window"], N=["plain", "cracked"], E=["twin"], W=["niche"],
         US=["u_twin", "u_window"], UN=["u_plain", "u_cracked"], UE=["u_window"], UW=["u_plain"], stair=True),
    dict(name="HOUSE_04", kit="maya", cells=(1, 1), storeys=1, pos=(-4.8, -44), rot=90, level=None, parapet="parapet",
         S=["door"], N=["wcracked"], E=["plain"], W=["window"]),
    dict(name="HOUSE_05", kit="gothic", style="basic", bays=2, storeys=1, pos=(26, -3.9), rot=0, level=None,
         S=["window", "door"], N=["plain", "window"], E=["window"], W=["plain"], chimney=1.8),
    dict(name="HOUSE_06", kit="maya", cells=(2, 2), storeys=1, pos=(46, -12), rot=180, level=None, parapet="p_spout",
         S=["window", "door"], N=["twin", "plain"], E=["niche", "window"], W=["cracked", "plain"]),
]
TOWERS = [dict(name="WATCHTOWER", piece="KIT_ROUND_TOWER_A", pos=(64, 9), rot=20)]

# Roads: control points (x, y); z follows the land, ends snap to a plaza they touch.
ROADS = {
    "MAIN_SOUTH": ("main", [(0, -9), (1.5, -28), (-1, -50), (1, -70), (0, -93)]),
    "MAIN_EAST": ("main", [(11, -7), (24, -8.6), (40, -8), (58, -2), (93, 3)]),
    "TEMPLE_WAY": ("main", [(11, 8), (26, 12), (40, 22), (37, 33), (27, 38), (21, 39.5)]),
    "WEST_TRACK": ("path", [(-11, -8), (-20, -14), (-32, -22.5), (-48, -24), (-93, -27)]),
    "TOWER_PATH": ("path", [(58, -2), (61, 4)]),
}
ROAD_STYLE = {"main": dict(width=5.0, mat="NW_City_Pflasterstein_01"), "path": dict(width=3.2, mat="NW_City_DirtyGround_Weg_02")}

# Hand-placed props (zCVob mesh names from the Gothic asset library), x, y, rot.
VOBS = [
    ("OC_WELL_V1", 0, 0, 0),
    ("NW_CITY_MARKETSTALL_FOOD_01", 8.2, -5, 90), ("NW_CITY_MARKETSTALL_WEAPONS_01", 8.2, 0.5, 90),
    ("NW_CITY_MARKETSTALL_ALCHEMY_01", 8.2, 6, 90), ("NW_CITY_MARKETSTALL_JUNKSHOP_01", -3, -6.8, 0),
    ("NW_CITY_CART_01", -8.5, 6.5, 30), ("NW_HARBOUR_BARRELGROUP_01", -9.2, -6.8, 0), ("NW_CITY_FLOWERPOT_01", -4, 9.4, 0),
    ("NW_CITY_FLOWERPOT_01", 4, 9.4, 0), ("NW_CITY_SIGN_MIXSHOP_01", -11.6, 2.6, 90),
    ("NW_HARBOUR_CRATEPILE_01", -36, -21, 10), ("NW_HARBOUR_BARRELGROUP_02", -41, -21.2, 0), ("NW_MISC_STRAW_GROUP_01", -30, -16, 0),
    ("OC_SACK_V01", -34, -20.5, 0), ("NW_HARBOUR_CRATE_01", -46.5, -20.8, 35), ("NW_CITY_CART_01", -28.5, -19, 110),
    ("NW_MISC_DECO_INNOS_LARGE_01", 18, 44.5, 0, 0.42), ("NW_NATURE_STONE_CULT_STAND_01", 10, 47.5, 0), ("NW_NATURE_STONE_CULT_STAND_02", 26, 47.5, 0),
    ("OC_FIREWOOD_V2", 12.5, -14.5, 0), ("NW_NATURE_FENCE_01", -8.5, -30.5, 90), ("NW_CITY_TABLE_PEASANT_01", 30, -1.5, 0),
    ("OC_BARREL_V1", 50, -21, 0), ("NW_MISC_SIGN_01", 13, -11, 45),
]
# Fire bowls (zCVob + a zCVobLight each)
BRAZIERS = [(15.3, 50.0), (20.7, 50.0), (9.0, 41.0), (27.0, 41.0)]
LAMP_EVERY = 17.0          # street lamps along main roads (m); + 4 at the market square
SCATTER_TREES = ["NW_NATURE_SMALLTREE_79P", "NW_NATURE_SMALLTREE_103P", "NW_NATURE_HOHETANNE_59P", "NW_NATURE_HOHETANNE_91P",
                 "OW_NATURE_SMALLTREE_01", "NW_NATURE_BAUMSTUMPF_115P"]
SCATTER_BUSHES = ["NW_NATURE_BUSH_60P", "NW_NATURE_BUSH_120P", "NW_NATURE_BUSH_25P", "NW_NATURE_GRASSGROUP_01",
                  "NW_NATURE_FARN_102P", "NW_NATURE_STONE_BIGFLAT_01", "NW_NATURE_PLANT_02", "NW_NATURE_GREAT_WEED_XGROUP"]
# =====================================================================


def M(x, y, z, rot):
    return Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rot), 4, 'Z')


def coll(name, parent=None, exclude=False):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    if exclude:
        bpy.context.view_layer.layer_collection.children[name].exclude = True
    return c


# ---------------------------------------------------------------- house layouts
def gothic_layout(h):
    st = G_STYLES[h["style"]]
    L, two = h["bays"], h["storeys"] == 2
    out = []
    zr = 6.0 if two else 3.0
    for z, pre, corner in ((0.0, "", st["corner"] if two else st["corner_solo"]), (3.0, "U", st.get("corner_upper"))):
        if z > 0 and not two:
            continue
        for i, r in enumerate(h[pre + "S"]):
            out.append((st[r], M(4 * i, 0, z, 0)))
        for i, r in enumerate(h[pre + "N"]):
            out.append((st[r], M(4 * (L - i), 4, z, 180)))
        out.append((st[h[pre + "E"][0]], M(4 * L, 0, z, 90)))
        out.append((st[h[pre + "W"][0]], M(0, 4, z, 270)))
        for x, y, r in ((0, 0, 0), (4 * L, 0, 90), (4 * L, 4, 180), (0, 4, 270)):
            out.append((corner, M(x, y, z, r)))
    for i in range(L):
        out.append((st["run"], M(4 * i, 0, zr, 0)))
    out += [(st["gable"], M(0, 0, zr, 0)), (st["gable"], M(4 * L, 4, zr, 180))]
    if h.get("chimney") is not None:
        out.append(("KIT_CHIMNEY_A", M(h["chimney"], 2, zr, 0)))
    for z, end, mid in ((0.0, "KIT_FLOOR_GROUND_END_A", "KIT_FLOOR_GROUND_A"), (3.0, "KIT_FLOOR_END_A", "KIT_FLOOR_A")):
        if z > 0 and not two:
            continue
        first = "KIT_FLOOR_STAIRWELL_END_A" if (z > 0 and h.get("stair")) else end
        out.append((first, M(0, 0, z, 0)))
        for i in range(1, L - 1):
            out.append((mid, M(4 * i, 0, z, 0)))
        if L > 1:
            out.append((end, M(4 * L, 4, z, 180)))
    if two and h.get("stair"):
        out.append(("KIT_STAIR_A", M(0, 0, 0, 0)))
    return out, (4 * L, 4)


def maya_layout(h):
    st = M_STYLE
    nx, ny = h["cells"]
    W, D, two = 4 * nx, 4 * ny, h["storeys"] == 2
    out = []

    def ring(z, pre, corner, key=None):
        for i, r in enumerate(h[pre + "S"]) if key is None else enumerate([key] * nx):
            out.append((st[r], M(4 * i, 0, z, 0)))
        for i, r in enumerate(h[pre + "N"]) if key is None else enumerate([key] * nx):
            out.append((st[r], M(W - 4 * i, D, z, 180)))
        for j, r in enumerate(h[pre + "E"]) if key is None else enumerate([key] * ny):
            out.append((st[r], M(W, 4 * j, z, 90)))
        for j, r in enumerate(h[pre + "W"]) if key is None else enumerate([key] * ny):
            out.append((st[r], M(0, D - 4 * j, z, 270)))
        for x, y, r in ((0, 0, 0), (W, 0, 90), (W, D, 180), (0, D, 270)):
            out.append((st[corner], M(x, y, z, r)))
    ring(0.0, "", "corner")
    if two:
        ring(3.0, "U", "corner_upper")
    zt = 3.0 * h["storeys"]
    ring(zt, "", "p_corner", key=h.get("parapet", "parapet"))
    for i in range(nx):
        for j in range(ny):
            out.append(("KIT_MAYA_FLOOR_GROUND_A", M(4 * i, 4 * j, 0, 0)))
            out.append(("KIT_MAYA_ROOF_DECK_A", M(4 * i, 4 * j, zt - 3.0, 0)))
            if two:
                sw = h.get("stair") and i == 0 and j == ny - 1
                out.append(("KIT_MAYA_FLOOR_UPPER_STAIRWELL_A" if sw else "KIT_MAYA_FLOOR_UPPER_A", M(4 * i, 4 * j, 0, 0)))
    if two and h.get("stair"):
        out.append(("KIT_MAYA_STAIR_A", M(0, D - 4, 0, 0)))
    for i, r in enumerate(h["S"]):
        if r == "door":
            out.append(("KIT_MAYA_STEP_A", M(4 * i, 0, 0, 0)))
    return out, (W, D)


def footprint(h, size, margin=1.4):
    """Plot rectangle in house-local coords: room + walls + a yard margin."""
    W, D = size
    t = 0.65 + margin
    return [(-t, -t), (W + t, -t), (W + t, D + t), (-t, D + t)]


def local_to_world(h, p):
    m = M(h["pos"][0], h["pos"][1], 0, h["rot"])
    return (m @ Vector((p[0], p[1], 0))).to_2d()


# ---------------------------------------------------------------- geometry nodes helpers
class GN:
    def __init__(self, name):
        self.ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
        self.x = 0

    def inp(self, name, stype, default=None, lo=None, hi=None):
        s = self.ng.interface.new_socket(name, in_out='INPUT', socket_type=stype)
        if default is not None:
            s.default_value = default
        if lo is not None:
            s.min_value = lo
        if hi is not None:
            s.max_value = hi
        return s

    def out(self, name, stype):
        return self.ng.interface.new_socket(name, in_out='OUTPUT', socket_type=stype)

    def node(self, t, **props):
        n = self.ng.nodes.new(t)
        n.location = (self.x, 0)
        self.x += 180
        for k, v in props.items():
            setattr(n, k, v)
        return n

    @staticmethod
    def sock(sockets, key):
        if isinstance(key, int):
            return sockets[key]
        for s in sockets:
            if (s.name == key or s.identifier == key) and s.enabled:
                return s
        raise KeyError(key)

    def link(self, a, ak, b, bk):
        self.ng.links.new(self.sock(a.outputs, ak), self.sock(b.inputs, bk))

    def set(self, n, key, v):
        self.sock(n.inputs, key).default_value = v

    def math(self, op, a=None, b=None, ak=0, bk=0, c=None):
        n = self.node('ShaderNodeMath', operation=op)
        for i, src, k in ((0, a, ak), (1, b, bk), (2, c, 0)):
            if src is None:
                continue
            if isinstance(src, (int, float)):
                n.inputs[i].default_value = src
            else:
                self.ng.links.new(self.sock(src.outputs, k) if not isinstance(src, bpy.types.NodeSocket) else src, n.inputs[i])
        return n

    def vmath(self, op, a, b=None, ak=0, bk=0):
        n = self.node('ShaderNodeVectorMath', operation=op)
        for i, src, k in ((0, a, ak), (1, b, bk)):
            if src is None:
                continue
            if isinstance(src, Vector) or isinstance(src, tuple):
                n.inputs[i].default_value = src
            else:
                self.ng.links.new(self.sock(src.outputs, k) if not isinstance(src, bpy.types.NodeSocket) else src, n.inputs[i])
        return n

    def smooth_falloff(self, dist, lo, hi):
        """1 at dist <= lo, 0 at dist >= hi (smoothstep)."""
        n = self.node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP', clamp=True)
        self.ng.links.new(dist if isinstance(dist, bpy.types.NodeSocket) else dist.outputs[0], n.inputs["Value"])
        for sk, v in (("From Min", lo), ("From Max", hi)):
            if isinstance(v, (int, float)):
                n.inputs[sk].default_value = v
            else:
                self.ng.links.new(v if isinstance(v, bpy.types.NodeSocket) else v.outputs[0], n.inputs[sk])
        n.inputs["To Min"].default_value = 1.0
        n.inputs["To Max"].default_value = 0.0
        return n

    def mixf(self, a, b, fac):
        n = self.node('ShaderNodeMix', data_type='FLOAT')
        for sk, src in (("Factor", fac), ("A", a), ("B", b)):
            self.ng.links.new(src if isinstance(src, bpy.types.NodeSocket) else src.outputs[0], self.sock(n.inputs, sk))
        return n

    def store(self, geo, name, value, dtype='FLOAT', domain='POINT', gk=0):
        n = self.node('GeometryNodeStoreNamedAttribute', data_type=dtype, domain=domain)
        self.ng.links.new(geo.outputs[gk] if not isinstance(geo, bpy.types.NodeSocket) else geo, n.inputs["Geometry"])
        n.inputs["Name"].default_value = name
        self.ng.links.new(value if isinstance(value, bpy.types.NodeSocket) else value.outputs[0], self.sock(n.inputs, "Value"))
        return n

    def named(self, name, dtype='FLOAT'):
        n = self.node('GeometryNodeInputNamedAttribute', data_type=dtype)
        n.inputs["Name"].default_value = name
        return n


def terrain_tree(mats):
    g = GN("TOWN_Terrain")
    ng = g.ng
    T = TERRAIN
    g.out("Geometry", 'NodeSocketGeometry')
    s_size = g.inp("Size", 'NodeSocketFloat', T["size"], 20)
    s_res = g.inp("Resolution", 'NodeSocketFloat', T["res"], 0.3)
    g.inp("Seed", 'NodeSocketFloat', float(SEED))
    g.inp("Noise Height", 'NodeSocketFloat', T["noise_height"], 0)
    g.inp("Noise Scale", 'NodeSocketFloat', T["noise_scale"], 0)
    g.inp("Slope X", 'NodeSocketFloat', T["slope"][0])
    g.inp("Slope Y", 'NodeSocketFloat', T["slope"][1])
    g.inp("Hill", 'NodeSocketObject')
    g.inp("Hill Radius", 'NodeSocketFloat', T["hill_radius"], 1)
    g.inp("Hill Height", 'NodeSocketFloat', T["hill_height"])
    g.inp("Rim Start", 'NodeSocketFloat', T["rim_start"], 0)
    g.inp("Rim Height", 'NodeSocketFloat', T["rim_height"])
    g.inp("Plots", 'NodeSocketCollection')
    g.inp("Plazas", 'NodeSocketCollection')
    g.inp("Roads", 'NodeSocketCollection')
    g.inp("Flatten", 'NodeSocketFloat', 1.0, 0, 1)
    g.inp("Plot Falloff", 'NodeSocketFloat', T["plot_falloff"], 0.1)
    g.inp("Road Half Width", 'NodeSocketFloat', T["road_half"], 0)
    g.inp("Road Falloff", 'NodeSocketFloat', T["road_falloff"], 0.1)
    g.inp("Ground Offset", 'NodeSocketFloat', TERRAIN_OFFSET)
    g.inp("Texture Tile", 'NodeSocketFloat', T["tile"], 0.1)
    g.inp("Rock Slope", 'NodeSocketFloat', 0.78, 0, 1)
    gi = g.node('NodeGroupInput')
    go = g.node('NodeGroupOutput')
    # grid
    verts = g.math('ADD', g.math('DIVIDE', gi, gi, "Size", "Resolution"), 1.0)
    grid = g.node('GeometryNodeMeshGrid')
    for k in ("Size X", "Size Y"):
        g.link(gi, "Size", grid, k)
    for k in ("Vertices X", "Vertices Y"):
        ng.links.new(verts.outputs[0], grid.inputs[k])
    pos = g.node('GeometryNodeInputPosition')
    sep = g.node('ShaderNodeSeparateXYZ')
    g.link(pos, 0, sep, 0)
    p2 = g.node('ShaderNodeCombineXYZ')
    g.link(sep, "X", p2, "X")
    g.link(sep, "Y", p2, "Y")
    # noise + hill + slope
    nz = g.node('ShaderNodeTexNoise', noise_dimensions='4D')
    g.link(p2, 0, nz, "Vector")
    g.link(gi, "Seed", nz, "W")
    sc = g.math('DIVIDE', gi, 100.0, "Noise Scale")
    ng.links.new(sc.outputs[0], nz.inputs["Scale"])
    g.set(nz, "Detail", 4.0)
    g.set(nz, "Roughness", 0.55)
    nzc = g.math('MULTIPLY', g.math('SUBTRACT', nz, 0.5, "Fac"), 2.0)
    noise_z = g.math('MULTIPLY', nzc, gi, 0, "Noise Height")
    hill = g.node('GeometryNodeObjectInfo')
    g.link(gi, "Hill", hill, "Object")
    hloc = g.node('ShaderNodeSeparateXYZ')
    g.link(hill, "Location", hloc, 0)
    h2 = g.node('ShaderNodeCombineXYZ')
    g.link(hloc, "X", h2, "X")
    g.link(hloc, "Y", h2, "Y")
    hd = g.vmath('DISTANCE', p2, h2)
    hq = g.math('DIVIDE', hd, gi, "Value", "Hill Radius")
    hexp = g.math('EXPONENT', g.math('MULTIPLY', g.math('MULTIPLY', hq, hq), -1.0))
    hill_z = g.math('MULTIPLY', hexp, gi, 0, "Hill Height")
    tilt = g.math('ADD', g.math('MULTIPLY', sep, gi, "X", "Slope X"), g.math('MULTIPLY', sep, gi, "Y", "Slope Y"))
    # rim: the land rises toward the edge of the map (hides the terrain border)
    edge = g.math('MAXIMUM', g.math('ABSOLUTE', sep, None, "X"), g.math('ABSOLUTE', sep, None, "Y"))
    rim_w = g.smooth_falloff(edge.outputs[0], g.math('MULTIPLY', gi, 0.5, "Size").outputs[0], g.sock(gi.outputs, "Rim Start"))
    rim_z = g.math('MULTIPLY', rim_w, gi, 0, "Rim Height")
    raw = g.math('ADD', g.math('ADD', g.math('ADD', noise_z, hill_z), tilt), rim_z)

    def flat_source(key):
        ci = g.node('GeometryNodeCollectionInfo', transform_space='RELATIVE')
        g.link(gi, key, ci, "Collection")
        g.set(ci, "Separate Children", False)
        g.set(ci, "Reset Children", False)
        rz = g.node('GeometryNodeRealizeInstances')
        g.link(ci, 0, rz, 0)
        return rz
    # plots + plazas: nearest surface height and xy distance
    j = g.node('GeometryNodeJoinGeometry')
    g.link(flat_source("Plots"), 0, j, 0)
    g.link(flat_source("Plazas"), 0, j, 0)
    pz = g.node('GeometryNodeInputPosition')
    pzs = g.node('ShaderNodeSeparateXYZ')
    g.link(pz, 0, pzs, 0)
    st = g.store(j, "oz", pzs.outputs["Z"])
    flat = g.node('GeometryNodeSetPosition')
    g.link(st, 0, flat, "Geometry")
    fp = g.node('ShaderNodeCombineXYZ')
    g.link(pzs, "X", fp, "X")
    g.link(pzs, "Y", fp, "Y")
    g.link(fp, 0, flat, "Position")
    prox = g.node('GeometryNodeProximity', target_element='FACES')
    g.link(flat, 0, prox, 0)
    g.link(p2, 0, prox, "Source Position" if "Source Position" in prox.inputs else "Sample Position")
    sns = g.node('GeometryNodeSampleNearestSurface', data_type='FLOAT')
    g.link(flat, 0, sns, "Mesh")
    g.link(g.named("oz"), 0, sns, "Value")
    g.link(p2, 0, sns, "Sample Position")
    w_plot = g.smooth_falloff(g.sock(prox.outputs, "Distance"), 0.0, g.sock(gi.outputs, "Plot Falloff"))
    # roads: nearest resampled point
    rr = g.node('GeometryNodeResampleCurve')
    g.link(flat_source("Roads"), 0, rr, "Curve")
    try:
        rr.mode = 'LENGTH'
    except Exception:
        g.set(rr, "Mode", 'Length')
    g.set(rr, "Length", 0.5)
    ctp = g.node('GeometryNodeCurveToPoints', mode='EVALUATED')
    g.link(rr, 0, ctp, "Curve")
    rpos = g.node('GeometryNodeInputPosition')
    rsep = g.node('ShaderNodeSeparateXYZ')
    g.link(rpos, 0, rsep, 0)
    rst = g.store(ctp, "oz", rsep.outputs["Z"], gk="Points" if False else 0)
    rflat = g.node('GeometryNodeSetPosition')
    g.link(rst, 0, rflat, "Geometry")
    rf = g.node('ShaderNodeCombineXYZ')
    g.link(rsep, "X", rf, "X")
    g.link(rsep, "Y", rf, "Y")
    g.link(rf, 0, rflat, "Position")
    snear = g.node('GeometryNodeSampleNearest', domain='POINT')
    g.link(rflat, 0, snear, "Geometry")
    g.link(p2, 0, snear, "Sample Position")
    si_p = g.node('GeometryNodeSampleIndex', data_type='FLOAT_VECTOR', domain='POINT')
    g.link(rflat, 0, si_p, "Geometry")
    g.link(g.node('GeometryNodeInputPosition'), 0, si_p, "Value")
    g.link(snear, "Index", si_p, "Index")
    si_z = g.node('GeometryNodeSampleIndex', data_type='FLOAT', domain='POINT')
    g.link(rflat, 0, si_z, "Geometry")
    g.link(g.named("oz"), 0, si_z, "Value")
    g.link(snear, "Index", si_z, "Index")
    d_road = g.vmath('DISTANCE', p2, si_p)
    rhi = g.math('ADD', gi, gi, "Road Half Width", "Road Falloff")
    w_road = g.smooth_falloff(d_road.outputs["Value"], g.sock(gi.outputs, "Road Half Width"), rhi.outputs[0])
    # blend: land -> road level -> plot level
    wr = g.math('MULTIPLY', w_road, gi, 0, "Flatten")
    wp = g.math('MULTIPLY', w_plot, gi, 0, "Flatten")
    z_road = g.math('ADD', si_z, gi, "Value", "Ground Offset")
    z_plot = g.math('ADD', sns, gi, "Value", "Ground Offset")
    z1 = g.mixf(raw.outputs[0], z_plot.outputs[0], wp.outputs[0])     # plots first,
    z2 = g.mixf(z1.outputs[0], z_road.outputs[0], wr.outputs[0])      # roads on top (they cross yards)
    newp = g.node('ShaderNodeCombineXYZ')
    g.link(sep, "X", newp, "X")
    g.link(sep, "Y", newp, "Y")
    g.link(z2, 0, newp, "Z")
    setp = g.node('GeometryNodeSetPosition')
    g.link(grid, "Mesh", setp, "Geometry")
    g.link(newp, 0, setp, "Position")
    # attributes for the scatter + materials
    town = g.math('MAXIMUM', w_road, w_plot)
    d_town = g.math('MINIMUM', g.sock(prox.outputs, "Distance"), g.math('SUBTRACT', d_road, gi, "Value", "Road Half Width").outputs[0])
    a1 = g.store(setp, "town_dist", d_town.outputs[0])
    a2 = g.store(a1, "town_w", town.outputs[0])
    uvv = g.vmath('SCALE', p2)
    inv = g.math('DIVIDE', 1.0, gi, 0, "Texture Tile")
    ng.links.new(inv.outputs[0], g.sock(uvv.inputs, "Scale"))
    a3 = g.store(a2, "Float2", uvv.outputs[0], dtype='FLOAT2', domain='CORNER')
    m_grass = g.node('GeometryNodeSetMaterial')
    g.link(a3, 0, m_grass, "Geometry")
    m_grass.inputs["Material"].default_value = mats["grass"]
    nrm = g.node('GeometryNodeInputNormal')
    nsep = g.node('ShaderNodeSeparateXYZ')
    g.link(nrm, 0, nsep, 0)
    steep = g.math('LESS_THAN', nsep, gi, "Z", "Rock Slope")
    m_rock = g.node('GeometryNodeSetMaterial')
    g.link(m_grass, 0, m_rock, "Geometry")
    g.link(steep, 0, m_rock, "Selection")
    m_rock.inputs["Material"].default_value = mats["rock"]
    near = g.math('GREATER_THAN', g.named("town_w"), 0.8)
    m_dirt = g.node('GeometryNodeSetMaterial')
    g.link(m_rock, 0, m_dirt, "Geometry")
    g.link(near, 0, m_dirt, "Selection")
    m_dirt.inputs["Material"].default_value = mats["dirt"]
    g.link(m_dirt, 0, go, 0)
    return ng


def road_tree():
    g = GN("TOWN_Road")
    ng = g.ng
    g.out("Geometry", 'NodeSocketGeometry')
    g.inp("Roads", 'NodeSocketCollection')
    g.inp("Width", 'NodeSocketFloat', 5.0, 0.2)
    g.inp("Material", 'NodeSocketMaterial')
    g.inp("Texture Tile", 'NodeSocketFloat', 4.0, 0.1)
    g.inp("Lift", 'NodeSocketFloat', 0.0)
    gi = g.node('NodeGroupInput')
    go = g.node('NodeGroupOutput')
    ci = g.node('GeometryNodeCollectionInfo', transform_space='RELATIVE')
    g.link(gi, "Roads", ci, "Collection")
    g.set(ci, "Separate Children", False)
    rz = g.node('GeometryNodeRealizeInstances')
    g.link(ci, 0, rz, 0)
    rr = g.node('GeometryNodeResampleCurve')
    g.link(rz, 0, rr, "Curve")
    try:
        rr.mode = 'LENGTH'
    except Exception:
        g.set(rr, "Mode", 'Length')
    g.set(rr, "Length", 0.8)
    nrm = g.node('GeometryNodeSetCurveNormal')
    g.link(rr, 0, nrm, "Curve")
    try:
        nrm.mode = 'Z_UP'
    except Exception:
        g.set(nrm, "Mode", 'Z Up')
    sp = g.node('GeometryNodeSplineParameter')
    s1 = g.store(nrm, "ulen", g.sock(sp.outputs, "Length"))
    half = g.math('MULTIPLY', gi, 0.5, "Width")
    neg = g.math('MULTIPLY', half, -1.0)
    a = g.node('ShaderNodeCombineXYZ')
    g.link(neg, 0, a, "X")
    b = g.node('ShaderNodeCombineXYZ')
    g.link(half, 0, b, "X")
    line = g.node('GeometryNodeCurvePrimitiveLine')
    g.link(a, 0, line, "Start")
    g.link(b, 0, line, "End")
    sp2 = g.node('GeometryNodeSplineParameter')
    s2 = g.store(line, "vpar", g.sock(sp2.outputs, "Factor"))
    c2m = g.node('GeometryNodeCurveToMesh')
    g.link(s1, 0, c2m, "Curve")
    g.link(s2, 0, c2m, "Profile Curve")
    lift = g.node('ShaderNodeCombineXYZ')
    g.link(gi, "Lift", lift, "Z")
    setp = g.node('GeometryNodeSetPosition')
    g.link(c2m, 0, setp, "Geometry")
    g.link(lift, 0, setp, "Offset")
    u = g.math('DIVIDE', g.math('MULTIPLY', g.named("vpar"), gi, 0, "Width"), gi, 0, "Texture Tile")
    v = g.math('DIVIDE', g.named("ulen"), gi, 0, "Texture Tile")
    uv = g.node('ShaderNodeCombineXYZ')
    g.link(u, 0, uv, "X")
    g.link(v, 0, uv, "Y")
    st = g.store(setp, "Float2", uv.outputs[0], dtype='FLOAT2', domain='CORNER')
    sm = g.node('GeometryNodeSetMaterial')
    g.link(st, 0, sm, "Geometry")
    g.link(gi, "Material", sm, "Material")
    g.link(sm, 0, go, 0)
    return ng


def scatter_tree():
    g = GN("TOWN_Scatter")
    ng = g.ng
    g.out("Geometry", 'NodeSocketGeometry')
    g.inp("Terrain", 'NodeSocketObject')
    g.inp("Instances", 'NodeSocketCollection')
    g.inp("Density", 'NodeSocketFloat', 0.01, 0)
    g.inp("Seed", 'NodeSocketInt', SEED)
    g.inp("Min Distance From Town", 'NodeSocketFloat', 8.0)
    g.inp("Clumping", 'NodeSocketFloat', 0.45, 0, 1)
    g.inp("Clump Scale", 'NodeSocketFloat', 3.0, 0)
    g.inp("Max Slope", 'NodeSocketFloat', 0.8, 0, 1)
    g.inp("Scale Min", 'NodeSocketFloat', 0.8, 0.01)
    g.inp("Scale Max", 'NodeSocketFloat', 1.25, 0.01)
    gi = g.node('NodeGroupInput')
    go = g.node('NodeGroupOutput')
    oi = g.node('GeometryNodeObjectInfo', transform_space='RELATIVE')
    g.link(gi, "Terrain", oi, "Object")
    far = g.math('GREATER_THAN', g.named("town_dist"), gi, 0, "Min Distance From Town")
    nrm = g.node('GeometryNodeInputNormal')
    ns = g.node('ShaderNodeSeparateXYZ')
    g.link(nrm, 0, ns, 0)
    flat = g.math('GREATER_THAN', ns, gi, "Z", "Max Slope")
    nz = g.node('ShaderNodeTexNoise')
    g.link(g.node('GeometryNodeInputPosition'), 0, nz, "Vector")
    g.link(g.math('DIVIDE', gi, 100.0, "Clump Scale"), 0, nz, "Scale")
    clump = g.math('GREATER_THAN', nz, gi, "Fac", "Clumping")
    sel = g.math('MULTIPLY', g.math('MULTIPLY', far, flat), clump)
    dist = g.node('GeometryNodeDistributePointsOnFaces', distribute_method='RANDOM')
    g.link(oi, "Geometry", dist, "Mesh")
    g.link(sel, 0, dist, "Selection")
    g.link(gi, "Density", dist, "Density")
    g.link(gi, "Seed", dist, "Seed")
    ci = g.node('GeometryNodeCollectionInfo', transform_space='ORIGINAL')
    g.link(gi, "Instances", ci, "Collection")
    g.set(ci, "Separate Children", True)
    g.set(ci, "Reset Children", False)
    rnd_i = g.node('FunctionNodeRandomValue', data_type='INT')
    g.set(rnd_i, "Max", 999)
    g.link(gi, "Seed", rnd_i, "Seed")
    rnd_r = g.node('FunctionNodeRandomValue', data_type='FLOAT')
    g.set(rnd_r, "Max", 6.2832)
    rot = g.node('ShaderNodeCombineXYZ')
    g.link(rnd_r, "Value", rot, "Z")
    rnd_s = g.node('FunctionNodeRandomValue', data_type='FLOAT')
    g.link(gi, "Scale Min", rnd_s, "Min")
    g.link(gi, "Scale Max", rnd_s, "Max")
    iop = g.node('GeometryNodeInstanceOnPoints')
    g.link(dist, "Points", iop, "Points")
    g.link(ci, 0, iop, "Instance")
    g.set(iop, "Pick Instance", True)
    g.link(rnd_i, "Value", iop, "Instance Index")
    g.link(rot, 0, iop, "Rotation")
    g.link(rnd_s, "Value", iop, "Scale")
    g.link(iop, 0, go, 0)
    return ng


def set_modifier_inputs(mod, values):
    """Blender 5.x: modifier inputs live in mod.properties.inputs.<Socket_N>.value
    (older versions: ID properties mod["Socket_N"])."""
    for item in mod.node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name in values:
            props = getattr(mod, "properties", None)
            if props is not None and hasattr(props, "inputs"):
                getattr(props.inputs, item.identifier).value = values[item.name]
            else:
                mod[item.identifier] = values[item.name]


# ================================================================ build
def main():
    bpy.ops.wm.read_homefile(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    rnd = random.Random(SEED)
    # ---- libraries -------------------------------------------------------
    need = set()
    layouts = {}
    for h in HOUSES:
        lay, size = (gothic_layout if h["kit"] == "gothic" else maya_layout)(h)
        layouts[h["name"]] = (lay, size)
        need |= {n for n, _ in lay}
    need |= {t["piece"] for t in TOWERS}
    kit = {}
    for path in (KIT_WALLS, KIT_MAYA):
        with bpy.data.libraries.load(path, link=True, relative=True) as (src, dst):
            dst.objects = [n for n in src.objects if n in need]
        kit.update({o.name: o for o in dst.objects if o})
    missing = need - set(kit)
    assert not missing, missing
    prop_names = {v[0] for v in VOBS} | set(SCATTER_TREES) | set(SCATTER_BUSHES) | {"NW_CITY_STREETLAMP_01", "PC_LOB_FIREBOWL", "NW_CITY_MARKETSTALL_ROOF_01"}
    with bpy.data.libraries.load(PROPS, link=True, relative=True) as (src, dst):
        dst.objects = ["zCVob:" + n for n in prop_names if "zCVob:" + n in src.objects]
    props = {o.name[6:]: o for o in dst.objects if o}
    lost = prop_names - set(props)
    if lost:
        print("TOWN_WARN missing props", sorted(lost))

    def prop_bottom(n):
        return -min((Vector(c)).z for c in props[n].bound_box)
    mats = {"grass": ensure_material("NW_Seq_Ground_02_XL"), "dirt": ensure_material("NW_Nature_WBoden_Var_01"),
            "rock": ensure_material("NW_Nature_DarkWood_Fels_01")}
    # ---- collections -----------------------------------------------------
    c_town = coll("TOWN")
    c_ground = coll("TOWN_GROUND", c_town)
    c_plazas = coll("TOWN_PLAZAS", c_town)
    c_roads = coll("TOWN_ROAD_CURVES", c_town)
    c_rmain = coll("TOWN_ROADS_MAIN_CURVES", c_roads)
    c_rpath = coll("TOWN_ROADS_PATH_CURVES", c_roads)
    c_houses = coll("TOWN_HOUSES", c_town)
    c_vobs = coll("TOWN_VOBS", c_town)
    c_lights = coll("TOWN_LIGHTS", c_town)
    c_plots = coll("TOWN_PLOTS")
    c_src = coll("TOWN_HOUSE_SOURCES")
    c_scat = coll("TOWN_SCATTER_SOURCES")
    for c in (c_plots, c_src, c_scat):
        bpy.context.view_layer.layer_collection.children[c.name].exclude = True
    # ---- terrain (raw first, to read the land's height) -------------------
    hill = bpy.data.objects.new("HILL", None)
    hill.empty_display_type = 'SPHERE'
    hill.empty_display_size = TERRAIN["hill_radius"] * 0.25
    hill.location = (*TERRAIN["hill"], 0)
    c_ground.objects.link(hill)
    terr = bpy.data.objects.new("TOWN_TERRAIN", bpy.data.meshes.new("TOWN_TERRAIN"))
    c_ground.objects.link(terr)
    for m in mats.values():
        terr.data.materials.append(m)
    tmod = terr.modifiers.new("Terrain", 'NODES')
    tmod.node_group = terrain_tree(mats)
    set_modifier_inputs(tmod, {"Hill": hill, "Plots": c_plots, "Plazas": c_plazas, "Roads": c_roads, "Flatten": 0.0})
    dg = bpy.context.evaluated_depsgraph_get()

    def land_bvh():
        terr.update_tag()
        dg.update()
        ev = terr.evaluated_get(dg)
        me = ev.to_mesh()
        bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [p.vertices[:] for p in me.polygons])
        ev.to_mesh_clear()
        return bvh

    def height(bvh, x, y):
        hit = bvh.ray_cast(Vector((x, y, 500.0)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] else 0.0
    bvh = land_bvh()
    # ---- plot levels ----------------------------------------------------
    groups = {}
    samples = {}
    for h in HOUSES:
        lay, size = layouts[h["name"]]
        fp = footprint(h, size, 0.0)
        pts = [local_to_world(h, p) for p in fp] + [local_to_world(h, (size[0] / 2, size[1] / 2))]
        samples[h["name"]] = sum(height(bvh, *p) for p in pts) / len(pts)
    for n, (poly, mat, lvl) in PLAZAS.items():
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        samples[n] = sum(height(bvh, *p) for p in poly + [(cx, cy)]) / (len(poly) + 1)
    for h in HOUSES:
        if h["level"]:
            groups.setdefault(h["level"], []).append(samples[h["name"]])
    for n, (poly, mat, lvl) in PLAZAS.items():
        groups.setdefault(lvl, []).append(samples[n])
    glevel = {k: round(sum(v) / len(v), 1) for k, v in groups.items()}
    level = {}
    for h in HOUSES:
        level[h["name"]] = glevel[h["level"]] if h["level"] else round(samples[h["name"]], 1)
    # ---- plazas ----------------------------------------------------------
    plaza_poly = {}
    for n, (poly, mat, lvl) in PLAZAS.items():
        z = glevel[lvl]
        me = bpy.data.meshes.new("PLAZA_" + n)
        bm = bmesh.new()
        f = bm.faces.new([bm.verts.new((x, y, z)) for x, y in poly])
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
        uvl = bm.loops.layers.uv.new("Float2")
        for f in bm.faces:
            for l in f.loops:
                l[uvl].uv = (l.vert.co.x / 4.0, l.vert.co.y / 4.0)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(ensure_material(mat))
        ob = bpy.data.objects.new("PLAZA_" + n, me)
        c_plazas.objects.link(ob)
        plaza_poly[n] = (poly, z)

    def in_plaza(x, y):
        for poly, z in plaza_poly.values():
            xs, ys = [p[0] for p in poly], [p[1] for p in poly]
            if min(xs) - 0.6 <= x <= max(xs) + 0.6 and min(ys) - 0.6 <= y <= max(ys) + 0.6:
                return z
        return None
    # ---- roads: z from the land, smoothed; ends on plazas take their level --
    road_objs = {}
    for n, (kind, pts) in ROADS.items():
        cu = bpy.data.curves.new("ROAD_" + n, 'CURVE')
        cu.dimensions = '3D'
        sp = cu.splines.new('BEZIER')
        sp.bezier_points.add(len(pts) - 1)
        zs = []
        for x, y in pts:
            pz = in_plaza(x, y)
            zs.append((height(bvh, x, y), pz))
        zz = [z for z, _ in zs]
        for _ in range(3):
            zz = [zz[0]] + [(zz[i - 1] + 2 * zz[i] + zz[i + 1]) / 4 for i in range(1, len(zz) - 1)] + [zz[-1]]
        for i, (z, pz) in enumerate(zs):
            if pz is not None:
                zz[i] = pz
        for bp, (x, y), z in zip(sp.bezier_points, pts, zz):
            bp.co = (x, y, z)
            bp.handle_left_type = bp.handle_right_type = 'AUTO'
        ob = bpy.data.objects.new("ROAD_" + n, cu)
        (c_rmain if kind == "main" else c_rpath).objects.link(ob)
        road_objs[n] = ob
    # road centre lines as points (for lamps and for house levels)
    road_pts = {}
    for n, ob in road_objs.items():
        sp = ob.data.splines[0]
        seg = []
        for a, b in zip(sp.bezier_points, list(sp.bezier_points)[1:]):
            for k in range(24):
                t = k / 24
                seg.append(((1 - t) ** 3 * a.co + 3 * (1 - t) ** 2 * t * a.handle_right
                            + 3 * (1 - t) * t ** 2 * b.handle_left + t ** 3 * b.co).copy())
        seg.append(sp.bezier_points[-1].co.copy())
        road_pts[n] = seg
    # a house without a level group takes the road height in front of its door
    for h in HOUSES:
        if h["level"]:
            continue
        di = [i for i, r in enumerate(h["S"]) if r == "door"]
        door = local_to_world(h, (4 * (di[0] if di else 0) + 2.0, -3.0))
        best = min((((p.to_2d() - door).length, p.z) for pts in road_pts.values() for p in pts), default=(99, 0))
        if best[0] < 10.0:
            level[h["name"]] = round(best[1], 1)
    # ---- houses ------------------------------------------------------------
    for h in HOUSES:
        lay, size = layouts[h["name"]]
        hc = bpy.data.collections.new("SRC_" + h["name"])
        c_src.children.link(hc)
        for n, mat in lay:
            o = bpy.data.objects.new(n + "@" + h["name"], kit[n].data)
            o.matrix_world = mat
            hc.objects.link(o)
        e = bpy.data.objects.new("TOWN_HOUSE_" + h["name"], None)
        e.instance_type = 'COLLECTION'
        e.instance_collection = hc
        e.location = (*h["pos"], level[h["name"]] - HOUSE_SINK)
        e.rotation_euler = (0, 0, math.radians(h["rot"]))
        e.empty_display_size = 2.0
        e["town_kit"] = h["kit"]
        e["town_role"] = h["name"]
        c_houses.objects.link(e)
        pme = bpy.data.meshes.new("PLOT_" + h["name"])
        pme.from_pydata([(x, y, HOUSE_SINK) for x, y in footprint(h, size)], [], [(0, 1, 2, 3)])
        p = bpy.data.objects.new("PLOT_" + h["name"], pme)
        p.parent = e
        p.display_type = 'WIRE'
        c_plots.objects.link(p)
    for t in TOWERS:
        z = round(height(bvh, *t["pos"]), 1)
        o = bpy.data.objects.new("TOWN_" + t["name"], kit[t["piece"]].data)
        o.location = (*t["pos"], z - HOUSE_SINK)
        o.rotation_euler = (0, 0, math.radians(t["rot"]))
        c_houses.objects.link(o)
        pme = bpy.data.meshes.new("PLOT_" + t["name"])
        r = 2.6
        pme.from_pydata([(-r, -r, HOUSE_SINK), (r, -r, HOUSE_SINK), (r, r, HOUSE_SINK), (-r, r, HOUSE_SINK)], [], [(0, 1, 2, 3)])
        p = bpy.data.objects.new("PLOT_" + t["name"], pme)
        p.parent = o
        c_plots.objects.link(p)
    for kind, cc in (("main", c_rmain), ("path", c_rpath)):
        st = ROAD_STYLE[kind]
        ro = bpy.data.objects.new("TOWN_ROADS_" + kind.upper(), bpy.data.meshes.new("TOWN_ROADS_" + kind.upper()))
        c_ground.objects.link(ro)
        m = ensure_material(st["mat"])
        ro.data.materials.append(m)
        md = ro.modifiers.new("Road", 'NODES')
        md.node_group = bpy.data.node_groups.get("TOWN_Road") or road_tree()
        set_modifier_inputs(md, {"Roads": cc, "Width": st["width"], "Material": m, "Texture Tile": 4.0,
                                 "Lift": 0.0 if kind == "main" else -0.01})
    # the terrain now flattens under everything
    set_modifier_inputs(tmod, {"Flatten": 1.0})
    terr.data.update()
    bvh = land_bvh()

    def ground(x, y):
        return height(bvh, x, y) - TERRAIN_OFFSET * 0.0
    # ---- VOBs ----------------------------------------------------------------
    def vob(n, x, y, rot, z=None, lift=0.0, scale=1.0):
        if n not in props:
            return None
        o = bpy.data.objects.new("zCVob:" + n, props[n].data)
        gz = ground(x, y) if z is None else z
        o.location = (x, y, gz + prop_bottom(n) * scale + lift)
        o.scale = (scale,) * 3
        o.rotation_euler = (0, 0, math.radians(rot))
        c_vobs.objects.link(o)
        return o
    for n, x, y, r, *sc_ in VOBS:
        pz = in_plaza(x, y)
        o = vob(n, x, y, r, z=pz, scale=sc_[0] if sc_ else 1.0)
        if o and "MARKETSTALL" in n and n != "NW_CITY_MARKETSTALL_ROOF_01":
            vob("NW_CITY_MARKETSTALL_ROOF_01", x, y, r, z=o.location.z - prop_bottom(n), lift=2.35)
    try:
        from zen_waypoint_tools.light_props import create_light_object
    except Exception as ex:
        create_light_object = None
        print("TOWN_WARN no Blend-Zen light helper:", ex)
    n_light = [0]

    def zlight(x, y, z, range_cm, rgb, tag):
        n_light[0] += 1
        name = "zCVobLight:TOWN_%s_%02d" % (tag, n_light[0])
        if create_light_object:
            lo = create_light_object(name, "POINT", range_cm=range_cm, color_rgb=rgb)
        else:
            ld = bpy.data.lights.new(name, 'POINT')
            ld.color = [c / 255 for c in rgb]
            lo = bpy.data.objects.new(name, ld)
        lo.data.energy = range_cm * 0.25          # viewport/render look only (not exported)
        lo.data.shadow_soft_size = 0.15
        lo.location = (x, y, z)
        c_lights.objects.link(lo)
        return lo
    # street lamps: along main roads, alternating sides
    lamp_pts = [(-10.2, -8.2), (10.2, -8.2), (-10.2, 8.2), (10.2, 8.2)]
    for n, (kind, pts) in ROADS.items():
        if kind != "main":
            continue
        seg = road_pts[n]
        dist, side, nxt = 0.0, 1, LAMP_EVERY * 0.5
        for a, b in zip(seg, seg[1:]):
            d = (b - a).to_2d().length
            if dist + d >= nxt:
                tan = (b - a).to_2d().normalized()
                nor = Vector((-tan.y, tan.x)) * side * (ROAD_STYLE[kind]["width"] / 2 + 1.0)
                q = b.to_2d() + nor
                if in_plaza(*q) is None:
                    lamp_pts.append(tuple(q))
                side, nxt = -side, nxt + LAMP_EVERY
            dist += d
    for x, y in lamp_pts:
        pz = in_plaza(x, y)
        o = vob("NW_CITY_STREETLAMP_01", x, y, rnd.uniform(0, 360), z=pz)
        if o:
            zlight(x, y, o.location.z + 1.75, 900.0, (255, 196, 128), "LAMP")
    for x, y in BRAZIERS:
        pz = in_plaza(x, y)
        o = vob("PC_LOB_FIREBOWL", x, y, 0, z=pz)
        if o:
            zlight(x, y, o.location.z + 1.9, 700.0, (255, 150, 70), "FIRE")
    # house door lights (lantern light only, over the door)
    for h in HOUSES:
        lay, size = layouts[h["name"]]
        di = [i for i, r in enumerate(h["S"]) if r == "door"]
        if not di:
            continue
        p = local_to_world(h, (4 * di[0] + 2.0, -1.2))
        zlight(p.x, p.y, level[h["name"]] + 2.9, 500.0, (255, 180, 110), "DOOR")
    # ---- scatter (Gothic plants) ------------------------------------------------
    for key, names, dens, mind, clump, smin, smax in (("TREES", SCATTER_TREES, 0.0035, 10.0, 0.42, 0.75, 1.2),
                                                       ("BUSHES", SCATTER_BUSHES, 0.02, 2.5, 0.5, 0.7, 1.3)):
        sc_c = bpy.data.collections.new("SCATTER_" + key)
        c_scat.children.link(sc_c)
        for n in names:
            if n in props:
                o = bpy.data.objects.new("zCVob:" + n, props[n].data)
                o.location = (0, 0, prop_bottom(n) - (0.25 if key == "TREES" else 0.05))
                sc_c.objects.link(o)
        so = bpy.data.objects.new("TOWN_SCATTER_" + key, bpy.data.meshes.new("TOWN_SCATTER_" + key))
        c_ground.objects.link(so)
        md = so.modifiers.new("Scatter", 'NODES')
        md.node_group = bpy.data.node_groups.get("TOWN_Scatter") or scatter_tree()
        set_modifier_inputs(md, {"Terrain": terr, "Instances": sc_c, "Density": dens, "Seed": SEED + len(key),
                                 "Min Distance From Town": mind, "Clumping": clump, "Scale Min": smin, "Scale Max": smax})
    # ---- world lighting (Blender native) ---------------------------------------
    sun = bpy.data.objects.new("SUN", bpy.data.lights.new("SUN", 'SUN'))
    sun.data.energy = 4.5
    sun.data.color = (1.0, 0.93, 0.82)
    sun.data.angle = math.radians(1.5)
    sun.rotation_euler = (math.radians(52), 0, math.radians(-38))
    c_lights.objects.link(sun)
    w = bpy.data.worlds.new("TOWN_SKY")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    try:
        sky = nt.nodes.new('ShaderNodeTexSky')
        types = [e.identifier for e in sky.bl_rna.properties['sky_type'].enum_items]
        for t in ('MULTIPLE_SCATTERING', 'NISHITA', 'SINGLE_SCATTERING', 'HOSEK_WILKIE'):
            if t in types:
                sky.sky_type = t
                break
        if hasattr(sky, "sun_disc"):
            sky.sun_disc = False
        if hasattr(sky, "sun_elevation"):
            sky.sun_elevation = math.radians(38)
            sky.sun_rotation = math.radians(-38 + 90 + 180)
        nt.links.new(sky.outputs[0], bg.inputs[0])
        bg.inputs[1].default_value = 0.22
    except Exception as ex:
        print("TOWN_WARN sky:", ex)
        bg.inputs[0].default_value = (0.55, 0.65, 0.8, 1)
    try:
        sc.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    ee = sc.eevee
    for attr, val in (("use_shadows", True), ("use_raytracing", True), ("use_gtao", True)):
        if hasattr(ee, attr):
            setattr(ee, attr, val)
    # ---- cameras ---------------------------------------------------------------
    views = {"CAM_OVERVIEW": ((-62, -78, 55), (6, 4, 4), 28), "CAM_SQUARE": ((-2, -24, 6.5), (0, 4, 3), 24),
             "CAM_TEMPLE": ((30, 16, 14), (17, 46, 14), 26), "CAM_STREET": ((-1.5, -58, 3.2), (1, -20, 3), 30),
             "CAM_EAST": ((70, -24, 12), (35, -4, 3), 30)}
    for n, (loc, tgt, lens) in views.items():
        cam = bpy.data.objects.new(n, bpy.data.cameras.new(n))
        cam.location = loc
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = lens
        cam.data.clip_end = 1000
        c_town.objects.link(cam)
    sc.camera = bpy.data.objects["CAM_OVERVIEW"]
    bpy.ops.wm.save_as_mainfile(filepath=OUT, relative_remap=True)
    print("TOWN_JSON", {"levels": glevel, "house_levels": level, "lamps": len(lamp_pts), "lights": n_light[0],
                        "vobs": len(c_vobs.objects), "missing_props": sorted(lost)})
    if "RENDER" in ARGS:
        os.makedirs(RENDER_DIR, exist_ok=True)
        sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
        for n in views:
            sc.camera = bpy.data.objects[n]
            sc.render.filepath = RENDER_DIR + n.lower() + ".png"
            bpy.ops.render.render(write_still=True)
        sc.camera = bpy.data.objects["CAM_OVERVIEW"]


main()
