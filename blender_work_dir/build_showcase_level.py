# Builds blender_work_dir/NW_KIT_SHOWCASE.blend: every kit piece made so
# far, in two areas.
#
#   CATALOG (north, y >= 40): one of each of the 23 pieces, unmerged and
#   individually selectable, laid out in rows by family, for inspection.
#
#   VILLAGE (around the origin): three differently-dressed, differently-
#   massed houses -- A (fully framed, standard), B (twin windows, light
#   framing, blank upper storey), C (shuttered windows, a jettied upper
#   storey, a roof dormer) -- plus a small ruin site, all connected by the
#   modular ground/road tiles. Each house is welded into one mesh the same
#   way build_two_house_level.py's houses are.
#
#   blender --background --python blender_work_dir/build_showcase_level.py
#   (or exec() it through the blender MCP execute_blender_code tool)
import bpy, bmesh, math, os
from mathutils import Matrix, Vector

ROOT = "/Users/jakubjaworski/Creativity/Blender Projects/Blender User Scripts/KIT/"
KIT = ROOT + "blender_work_dir/kit/KIT_WALLS.blend"
OUT = ROOT + "blender_work_dir/NW_KIT_SHOWCASE.blend"
exec(open(ROOT + ".claude/skills/gothic-kit-piece/scripts/kit_lib.py").read())

bpy.ops.wm.read_homefile(use_empty=True)
catalog_coll = bpy.data.collections.new("CATALOG"); bpy.context.scene.collection.children.link(catalog_coll)
village_coll = bpy.data.collections.new("VILLAGE"); bpy.context.scene.collection.children.link(village_coll)
zenc = bpy.data.collections.new("VILLAGE_EXPORT_ZEN"); bpy.context.scene.collection.children.link(zenc)

ALL_PIECES = [
    "NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_WINDOW_A", "NW_KIT_WALL_WINDOW_TWIN_A", "NW_KIT_WALL_WINDOW_SHUTTER_A",
    "NW_KIT_WALL_PLAIN_A", "NW_KIT_WALL_PLAIN_LIGHT_A", "NW_KIT_WALL_RUIN_A", "NW_KIT_WALL_CORNER_A",
    "NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_WALL_UPPER_PLAIN_A", "NW_KIT_WALL_UPPER_JETTY_A",
    "NW_KIT_WALL_CORNER_UPPER_A", "NW_KIT_WALL_CORNER_JETTY_A", "NW_KIT_TRIM_FASCIA_A",
    "NW_KIT_ROOF_RUN_A", "NW_KIT_ROOF_END_GABLE_A", "NW_KIT_ROOF_DORMER_A", "NW_KIT_CHIMNEY_A",
    "NW_KIT_FLOOR_A", "NW_KIT_FLOOR_END_A",
    "NW_KIT_TERRAIN_FLAT_A", "NW_KIT_TERRAIN_YARD_A", "NW_KIT_ROAD_STRAIGHT_A", "NW_KIT_ROAD_JUNCTION_A",
    "NW_KIT_RUIN_RUBBLE_A", "NW_KIT_RUIN_BEAM_A", "NW_KIT_SIGN_POST_A", "NW_KIT_CHURCH_TOWER_A",
    "NW_KIT_WALL_CORNER_SOLO_A",
    "NW_KIT_WALL_CIVIC_DOOR_A", "NW_KIT_WALL_CIVIC_WINDOW_A", "NW_KIT_WALL_CIVIC_PLAIN_A",
    "NW_KIT_WALL_CIVIC_CORNER_A", "NW_KIT_WALL_CIVIC_UPPER_WINDOW_A", "NW_KIT_WALL_CIVIC_UPPER_PLAIN_A",
    "NW_KIT_WALL_CIVIC_CORNER_UPPER_A",
    "NW_KIT_WALL_SACRED_DOOR_A", "NW_KIT_WALL_SACRED_WINDOW_A", "NW_KIT_WALL_SACRED_PLAIN_A",
    "NW_KIT_WALL_SACRED_CORNER_A", "NW_KIT_WALL_SACRED_UPPER_WINDOW_A", "NW_KIT_WALL_SACRED_CORNER_UPPER_A",
    "NW_KIT_WALL_RH1_DOOR_A", "NW_KIT_WALL_RH1_WINDOW_A", "NW_KIT_WALL_RH1_PLAIN_A",
    "NW_KIT_WALL_RH1_CORNER_A", "NW_KIT_WALL_RH1_UPPER_WINDOW_A", "NW_KIT_WALL_RH1_UPPER_PLAIN_A",
    "NW_KIT_WALL_RH1_CORNER_UPPER_A", "NW_KIT_ROOF_RH1_RUN_A", "NW_KIT_ROOF_RH1_END_GABLE_A",
    "NW_KIT_WALL_RH2_DOOR_A", "NW_KIT_WALL_RH2_WINDOW_A", "NW_KIT_WALL_RH2_PLAIN_A",
    "NW_KIT_WALL_RH2_CORNER_A", "NW_KIT_WALL_RH2_UPPER_WINDOW_A", "NW_KIT_WALL_RH2_UPPER_PLAIN_A",
    "NW_KIT_WALL_RH2_CORNER_UPPER_A", "NW_KIT_ROOF_RH2_RUN_A", "NW_KIT_ROOF_RH2_END_GABLE_A",
]
with bpy.data.libraries.load(KIT, link=False) as (src, dst):
    dst.objects = ALL_PIECES
P = {o.name: o for o in dst.objects}


def M(x, y, z, rot):
    return Matrix.Translation(Vector((x, y, z))) @ Matrix.Rotation(math.radians(rot), 4, 'Z')


# ==================================================================== catalog
ROWS = [
    ("Walls - ground", ["NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_WINDOW_A", "NW_KIT_WALL_WINDOW_TWIN_A",
                        "NW_KIT_WALL_WINDOW_SHUTTER_A", "NW_KIT_WALL_PLAIN_A", "NW_KIT_WALL_PLAIN_LIGHT_A",
                        "NW_KIT_WALL_RUIN_A", "NW_KIT_WALL_CORNER_A", "NW_KIT_WALL_CORNER_SOLO_A"]),
    ("Walls - upper", ["NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_WALL_UPPER_PLAIN_A", "NW_KIT_WALL_UPPER_JETTY_A",
                       "NW_KIT_WALL_CORNER_UPPER_A", "NW_KIT_WALL_CORNER_JETTY_A", "NW_KIT_TRIM_FASCIA_A"]),
    ("Roofs", ["NW_KIT_ROOF_RUN_A", "NW_KIT_ROOF_END_GABLE_A", "NW_KIT_ROOF_DORMER_A", "NW_KIT_CHIMNEY_A"]),
    ("Interior", ["NW_KIT_FLOOR_A", "NW_KIT_FLOOR_END_A"]),
    ("Streets", ["NW_KIT_TERRAIN_FLAT_A", "NW_KIT_TERRAIN_YARD_A", "NW_KIT_ROAD_STRAIGHT_A", "NW_KIT_ROAD_JUNCTION_A"]),
    ("Ruin debris", ["NW_KIT_RUIN_RUBBLE_A", "NW_KIT_RUIN_BEAM_A"]),
    ("Tavern / church props", ["NW_KIT_SIGN_POST_A", "NW_KIT_CHURCH_TOWER_A"]),
    ("Townhall (civic)", ["NW_KIT_WALL_CIVIC_DOOR_A", "NW_KIT_WALL_CIVIC_WINDOW_A", "NW_KIT_WALL_CIVIC_PLAIN_A",
                          "NW_KIT_WALL_CIVIC_CORNER_A", "NW_KIT_WALL_CIVIC_UPPER_WINDOW_A",
                          "NW_KIT_WALL_CIVIC_UPPER_PLAIN_A", "NW_KIT_WALL_CIVIC_CORNER_UPPER_A"]),
    ("Church (sacred)", ["NW_KIT_WALL_SACRED_DOOR_A", "NW_KIT_WALL_SACRED_WINDOW_A", "NW_KIT_WALL_SACRED_PLAIN_A",
                         "NW_KIT_WALL_SACRED_CORNER_A", "NW_KIT_WALL_SACRED_UPPER_WINDOW_A",
                         "NW_KIT_WALL_SACRED_CORNER_UPPER_A"]),
    ("Row house palette 1", ["NW_KIT_WALL_RH1_DOOR_A", "NW_KIT_WALL_RH1_WINDOW_A", "NW_KIT_WALL_RH1_PLAIN_A",
                             "NW_KIT_WALL_RH1_CORNER_A", "NW_KIT_ROOF_RH1_RUN_A", "NW_KIT_ROOF_RH1_END_GABLE_A"]),
    ("Row house palette 2", ["NW_KIT_WALL_RH2_DOOR_A", "NW_KIT_WALL_RH2_WINDOW_A", "NW_KIT_WALL_RH2_PLAIN_A",
                             "NW_KIT_WALL_RH2_CORNER_A", "NW_KIT_ROOF_RH2_RUN_A", "NW_KIT_ROOF_RH2_END_GABLE_A"]),
]
CATALOG_Y0, SP_X, SP_Y = 40.0, 5.0, 7.0
for ri, (label, names) in enumerate(ROWS):
    for ci, nm in enumerate(names):
        ob = P[nm]
        ob.location = (ci * SP_X, CATALOG_Y0 - ri * SP_Y, 0.0)
        catalog_coll.objects.link(ob)
    lbl = bpy.data.objects.new(f"_LABEL_{label.replace(' ', '_')}", None)
    lbl.location = (-2.0, CATALOG_Y0 - ri * SP_Y, 0.0)
    lbl.empty_display_size = 0.3
    catalog_coll.objects.link(lbl)

# =================================================================== village
D = 4.8


def section_placements(x0, y0, rot, S, N, E, W_, corner, n_bays=2, upper=False,
                       US=None, UN=None, UE=None, UW_=None, upper_corner=None,
                       chimney_x=2.4, extra=(), off=0.4, upper_off=0.4,
                       roof_run="NW_KIT_ROOF_RUN_A", roof_gable="NW_KIT_ROOF_END_GABLE_A"):
    """A complete rectangular gable-roofed SECTION: n_bays long (ridge runs
    along the section's own LOCAL +x -- S/N are the long eave walls, always
    a LIST of n_bays piece names) x 1 bay deep (E/W are the gable-end
    walls, always a single piece name). Built entirely at local origin
    (0,0), then the WHOLE section is wrapped in M(x0,y0,0,rot) -- so `rot`
    alone decides which world direction the gable faces, without touching
    any wall/roof geometry. This is the generalization `house_placements`/
    `small_house_placements` always were a special case of: a plain 2-bay
    house is section_placements(..., rot=0, n_bays=2, upper=True) with its
    gable sideways; a row-house unit is the SAME call with rot=90 (or 270)
    so what was the gable-end wall now faces the street; an L-shaped
    building is two sections, each keeping its OWN separate roof (no
    valley yet -- see SKILL.md lesson 19) -- one at rot=0, the other at
    rot=90, positioned so their footprints share an inside corner.

    upper=True adds a matching upper storey; `corner` is then the GROUND
    corner (NOT nudge_top -- it welds to the upper corner stacked on it)
    and `upper_corner` must be a nudge_top=True piece (CORNER_UPPER_A/
    CORNER_JETTY_A already are, built that way from the start).
    upper=False needs `corner` itself to be nudge_top=True
    (CORNER_SOLO_A) since the roof then sits directly on the ground
    corner -- see SKILL.md lesson 18. chimney_x=None omits the chimney
    (a row of attached units wants at most one chimney per unit, or the
    caller may want to place it explicitly instead)."""
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
        storey(3, pair(US or U, n_bays), pair(UN or U, n_bays), UE or U, UW_ or U,
              upper_corner, upper_off)
        for z in (0.46, 3.0):
            local.append(("NW_KIT_FLOOR_END_A", M(off, off, z, 0)))
            for k in range(n_bays - 2):
                local.append(("NW_KIT_FLOOR_A", M(off + (k + 1) * 4.0, off, z, 0)))
            local.append(("NW_KIT_FLOOR_END_A", M(off + n_bays * 4.0, off + 4.0, z, 180)))
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


def house_placements(x0, y0, S, N, E, W_, corner, US=None, UN=None, UE=None, UW_=None,
                     upper_corner="NW_KIT_WALL_CORNER_UPPER_A", chimney_x=6.4, extra=(),
                     upper_off=0.4):
    """upper_off: the wall-to-corner offset the UPPER storey's own corner
    piece actually welds at. build_corner_from_bay derives a corner's own
    weld-edge distance (T_new, called `off` here) from the wall's own
    boundary loop as T_new = max(loop.y) -- for a normal wall that's just
    WALL_T (0.4, the default here, baked into a plain 90-degree mitre). A
    JETTIED wall's whole profile (front AND back) is shifted outward by
    JETTY, so its own max-y -- and therefore CORNER_JETTY_A's own T_new --
    shrinks to WALL_T-JETTY (0.25). Placing a jetty wall/corner pair with
    the NORMAL 0.4 offset (as if upper_off were still 0.4) leaves a real
    0.15 m gap at every jettied corner -- pass upper_off=WALL_T-JETTY
    (0.25) whenever upper_corner is a jetty variant. Verified by a direct
    two-piece merge test (UPPER_JETTY_A + CORNER_JETTY_A): 0 overlap AND
    the two pieces' own open-edge counts (36+22=58) actually drop once
    merged at the correct offset, instead of just summing unchanged."""
    def pair(v):
        return (v, v) if isinstance(v, str) else v
    S, N = pair(S), pair(N)
    U = "NW_KIT_WALL_UPPER_WINDOW_A"
    US, UN = pair(US or (U, U)), pair(UN or (U, U))
    UE, UW_ = UE or U, UW_ or U
    placements = []

    def storey(z, S, N, E, W_, corn, off=0.4):
        span_x, span_y = 2 * off + 8.0, 2 * off + 4.0
        placements.extend([(S[0], M(x0 + off, y0, z, 0)), (S[1], M(x0 + off + 4.0, y0, z, 0)),
                           (N[0], M(x0 + off + 4.0, y0 + span_y, z, 180)),
                           (N[1], M(x0 + off + 8.0, y0 + span_y, z, 180)),
                           (E, M(x0 + span_x, y0 + off, z, 90)), (W_, M(x0, y0 + off + 4.0, z, 270))])
        for (x, y, r) in ((x0, y0, 0), (x0 + span_x, y0, 90), (x0 + span_x, y0 + span_y, 180), (x0, y0 + span_y, 270)):
            placements.append((corn, M(x, y, z, r)))
    storey(0, S, N, E, W_, corner)
    storey(3, US, UN, UE, UW_, upper_corner, off=upper_off)
    for z in (0.46, 3.0):
        placements += [("NW_KIT_FLOOR_END_A", M(x0 + 0.4, y0 + 0.4, z, 0)),
                       ("NW_KIT_FLOOR_END_A", M(x0 + 8.4, y0 + 4.4, z, 180))]
    ZR = 6
    placements += [("NW_KIT_ROOF_RUN_A", M(x0 + 0.4, y0, ZR, 0)), ("NW_KIT_ROOF_RUN_A", M(x0 + 4.4, y0, ZR, 0)),
                   ("NW_KIT_ROOF_END_GABLE_A", M(x0 - 0.3, y0, ZR, 0)),
                   ("NW_KIT_ROOF_END_GABLE_A", M(x0 + 9.1, y0 + D, ZR, 180)),
                   ("NW_KIT_CHIMNEY_A", M(x0 + chimney_x, y0 + 2.4, ZR + 2.695, 0))]
    for (nm, mat) in extra:
        placements.append((nm, mat))
    return placements


def small_house_placements(x0, y0, S, N, E, W_, corner, chimney_x=1.8, extra=()):
    """A single-bay (4.8 x 4.8 m footprint), ground-floor-only cottage: one
    wall per side, 4 corners, one roof run + 2 gable ends, one chimney --
    the smallest complete unit the kit's own 0.4 m corner-offset convention
    supports (see house_placements' own upper_off docstring for why that
    offset matters). No upper storey, no interior floor deck (nothing
    inside is visible from outside a closed cottage anyway).

    `corner` must be a nudge_top=True ground corner (NW_KIT_WALL_CORNER_SOLO_A,
    not the plain NW_KIT_WALL_CORNER_A) -- CORNER_A's own top lip assumes an
    UPPER corner stacks above it, not a roof/gable sitting directly on it;
    without the nudge the roof and corner both contribute a face to the
    same z=3 edge as the corner's own un-nudged top, a real 3-face overlap
    (found via the same house-level merge test every house gets, not by
    either piece's own check_piece -- see SKILL.md lesson 17's general
    point about placement-derived offsets needing a merge test)."""
    off = 0.4
    span = 2 * off + 4.0   # = 4.8, same on both axes for a single bay
    placements = [
        (S, M(x0 + off, y0, 0, 0)), (N, M(x0 + off + 4.0, y0 + span, 0, 180)),
        (E, M(x0 + span, y0 + off, 0, 90)), (W_, M(x0, y0 + off + 4.0, 0, 270)),
    ]
    for (x, y, r) in ((x0, y0, 0), (x0 + span, y0, 90), (x0 + span, y0 + span, 180), (x0, y0 + span, 270)):
        placements.append((corner, M(x, y, 0, r)))
    ZR = 3
    placements += [("NW_KIT_ROOF_RUN_A", M(x0 + off, y0, ZR, 0)),
                   ("NW_KIT_ROOF_END_GABLE_A", M(x0 + off - 0.7, y0, ZR, 0)),
                   ("NW_KIT_ROOF_END_GABLE_A", M(x0 + off + 4.7, y0 + span, ZR, 180)),
                   ("NW_KIT_CHIMNEY_A", M(x0 + chimney_x, y0 + 2.4, ZR + 2.695, 0))]
    for (nm, mat) in extra:
        placements.append((nm, mat))
    return placements


def church_placements(x0, y0, corner="NW_KIT_WALL_SACRED_CORNER_A",
                      upper_corner="NW_KIT_WALL_SACRED_CORNER_UPPER_A", chimney=False):
    """A 2-bay sacred-palette nave (built on the same two-storey shell as
    house_placements, tall proportions read as a nave rather than a
    dwelling once the upper storey's own windows -- tall and set high,
    same fix as the rest of the kit -- line up above the ground ones) plus
    a freestanding bell tower standing off the west gable end, close
    enough to read as attached, its own footprint clear of the nave's."""
    D_ = "NW_KIT_WALL_SACRED_DOOR_A"
    W_ = "NW_KIT_WALL_SACRED_WINDOW_A"
    PL = "NW_KIT_WALL_SACRED_PLAIN_A"
    UW = "NW_KIT_WALL_SACRED_UPPER_WINDOW_A"
    placements = house_placements(
        x0, y0, S=(D_, W_), N=(PL, W_), E=PL, W_=W_, corner=corner,
        US=(UW, UW), UN=(UW, UW), UE=UW, UW_=UW, upper_corner=upper_corner,
        chimney_x=100.0,   # off in the weeds -- a church has no chimney; see below
    )
    # drop the chimney entry house_placements always appends (last one added
    # for the z=ZR+2.695 placement) rather than special-case house_placements
    # itself for "no chimney" -- simplest to just filter it back out here.
    placements = [p for p in placements if p[0] != "NW_KIT_CHIMNEY_A"]
    placements.append(("NW_KIT_CHURCH_TOWER_A", M(x0 - 2.4, y0 + 1.4, 0, 0)))
    return placements


def build_house(name, x0, y0, placements_fn=house_placements, **kw):
    house_mats, bm = [], bmesh.new()
    for pname, mat in placements_fn(x0, y0, **kw):
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
    house = bpy.data.objects.new(name, hme); village_coll.objects.link(house)
    return house, overlap


# Fascia boards along house A's south upper-storey wall, at the same
# transforms as that wall's own two bays -- a surface-mounted trim board,
# not a vertex weld (see fascia.py's module docstring / SKILL.md lesson 13).
houseA, ovA = build_house("NW_HOUSE_A", 0.0, 0.0,
                          S=("NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_WINDOW_A"),
                          N=("NW_KIT_WALL_PLAIN_A", "NW_KIT_WALL_WINDOW_A"),
                          E="NW_KIT_WALL_PLAIN_A", W_="NW_KIT_WALL_WINDOW_A",
                          corner="NW_KIT_WALL_CORNER_A",
                          extra=[("NW_KIT_TRIM_FASCIA_A", M(0.4, 0.0, 3, 0)),
                                 ("NW_KIT_TRIM_FASCIA_A", M(4.4, 0.0, 3, 0))])

X0_B = 16.0
houseB, ovB = build_house("NW_HOUSE_B", X0_B, 0.0,
                          S=("NW_KIT_WALL_WINDOW_TWIN_A", "NW_KIT_WALL_DOOR_A"),
                          N=("NW_KIT_WALL_PLAIN_LIGHT_A", "NW_KIT_WALL_PLAIN_LIGHT_A"),
                          E="NW_KIT_WALL_PLAIN_LIGHT_A", W_="NW_KIT_WALL_WINDOW_TWIN_A",
                          corner="NW_KIT_WALL_CORNER_A",
                          US=("NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_WALL_UPPER_PLAIN_A"),
                          UN="NW_KIT_WALL_UPPER_PLAIN_A", UE="NW_KIT_WALL_UPPER_PLAIN_A",
                          UW_="NW_KIT_WALL_UPPER_PLAIN_A", chimney_x=1.4)

# House C: shuttered windows downstairs, a jettied upper storey all round
# (a jetty wall must meet a jetty corner, never a plain one -- see the user
# guide), and a dormer sitting on its own south roof run.
X0_C = 32.0
houseC, ovC = build_house(
    "NW_HOUSE_C", X0_C, 0.0,
    S=("NW_KIT_WALL_WINDOW_SHUTTER_A", "NW_KIT_WALL_DOOR_A"),
    N=("NW_KIT_WALL_PLAIN_A", "NW_KIT_WALL_WINDOW_SHUTTER_A"),
    E="NW_KIT_WALL_PLAIN_A", W_="NW_KIT_WALL_WINDOW_SHUTTER_A",
    corner="NW_KIT_WALL_CORNER_A",
    US=("NW_KIT_WALL_UPPER_JETTY_A", "NW_KIT_WALL_UPPER_JETTY_A"),
    UN=("NW_KIT_WALL_UPPER_JETTY_A", "NW_KIT_WALL_UPPER_JETTY_A"),
    UE="NW_KIT_WALL_UPPER_JETTY_A", UW_="NW_KIT_WALL_UPPER_JETTY_A",
    upper_corner="NW_KIT_WALL_CORNER_JETTY_A", chimney_x=6.4,
    upper_off=0.25,  # WALL_T(0.4) - JETTY(0.15): see house_placements' docstring
    extra=[("NW_KIT_ROOF_DORMER_A", M(X0_C + 0.4, 0.0, 6.0, 0))],
)

# ------------------------------------------------------------- small houses --
# Two single-bay cottages, one door-bay and one window-bay, continuing the
# road east of house C.
X0_S1 = 44.0
houseS1, ovS1 = build_house("NW_HOUSE_SMALL_1", X0_S1, 0.0, placements_fn=small_house_placements,
                            S="NW_KIT_WALL_DOOR_A", N="NW_KIT_WALL_PLAIN_LIGHT_A",
                            E="NW_KIT_WALL_WINDOW_A", W_="NW_KIT_WALL_PLAIN_LIGHT_A",
                            corner="NW_KIT_WALL_CORNER_SOLO_A", chimney_x=2.4)

X0_S2 = 52.0
houseS2, ovS2 = build_house("NW_HOUSE_SMALL_2", X0_S2, 0.0, placements_fn=small_house_placements,
                            S="NW_KIT_WALL_WINDOW_A", N="NW_KIT_WALL_PLAIN_LIGHT_A",
                            E="NW_KIT_WALL_PLAIN_LIGHT_A", W_="NW_KIT_WALL_DOOR_A",
                            corner="NW_KIT_WALL_CORNER_SOLO_A", chimney_x=1.6)

# ------------------------------------------------------------------ tavern --
# A standard two-bay, two-storey shell (same residential palette as houses
# A/B/C -- a tavern is still a timber-framed building, not a civic one) with
# extra windows both storeys (a public house wants to look lively/lit, not
# blank-walled) and a hanging sign by the door.
X0_T = 60.0
tavern, ovT = build_house(
    "NW_TAVERN", X0_T, 0.0,
    S=("NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_WINDOW_TWIN_A"),
    N=("NW_KIT_WALL_WINDOW_A", "NW_KIT_WALL_WINDOW_A"),
    E="NW_KIT_WALL_WINDOW_A", W_="NW_KIT_WALL_WINDOW_TWIN_A",
    corner="NW_KIT_WALL_CORNER_A",
    US=("NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_WALL_UPPER_WINDOW_A"),
    UN=("NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_WALL_UPPER_WINDOW_A"),
    UE="NW_KIT_WALL_UPPER_WINDOW_A", UW_="NW_KIT_WALL_UPPER_WINDOW_A",
    chimney_x=1.4,
    extra=[("NW_KIT_SIGN_POST_A", M(X0_T + 1.4, -0.55, 0, 0))],
)

# ----------------------------------------------------------------- townhall --
# Same two-bay, two-storey shell as the houses, entirely in the civic
# material palette (cut ashlar facade, same timber trim) instead of a new
# footprint -- the "different texture palette" IS the townhall's identity,
# same way SACRED does for the church below. Set back from the road on its
# own north spur so it reads as a civic building facing a square, not just
# another house in the row.
X0_H, Y0_H = 46.0, 12.0
townhall, ovH = build_house(
    "NW_TOWNHALL", X0_H, Y0_H,
    S=("NW_KIT_WALL_CIVIC_DOOR_A", "NW_KIT_WALL_CIVIC_WINDOW_A"),
    N=("NW_KIT_WALL_CIVIC_PLAIN_A", "NW_KIT_WALL_CIVIC_PLAIN_A"),
    E="NW_KIT_WALL_CIVIC_WINDOW_A", W_="NW_KIT_WALL_CIVIC_WINDOW_A",
    corner="NW_KIT_WALL_CIVIC_CORNER_A",
    US=("NW_KIT_WALL_CIVIC_UPPER_WINDOW_A", "NW_KIT_WALL_CIVIC_UPPER_WINDOW_A"),
    UN=("NW_KIT_WALL_CIVIC_UPPER_WINDOW_A", "NW_KIT_WALL_CIVIC_UPPER_WINDOW_A"),
    UE="NW_KIT_WALL_CIVIC_UPPER_WINDOW_A", UW_="NW_KIT_WALL_CIVIC_UPPER_WINDOW_A",
    upper_corner="NW_KIT_WALL_CIVIC_CORNER_UPPER_A", chimney_x=1.4,
)

# -------------------------------------------------------------------- church --
# A sacred-palette nave (church_placements: same 2-storey shell, tall
# windows in the upper band the way the window-position fix now puts them
# on every storey) plus its own freestanding bell tower off the west end.
X0_CH, Y0_CH = 62.0, 12.0
church, ovCh = build_house("NW_CHURCH", X0_CH, Y0_CH, placements_fn=church_placements)

# --------------------------------------------------------------- row houses --
# Gable-fronted terrace, Nyhavn/Amsterdam-style: each unit is its OWN
# section_placements call (n_bays=1, its own complete roof -- not one
# continuous ridge over the row) at rot=270, which empirically (checked by
# placing one and reading its DOOR object's world position back) puts what
# was the section's own gable-end "E" wall facing world -Y, i.e. the
# street. A unit's local S/N walls (the long eave walls in the
# unrotated frame) become the party walls after rotation -- always
# NW_KIT_WALL_*_PLAIN_A, since they're shared with the next unit over and
# would never be seen. Units are placed edge-to-edge (4.8 m apart, the
# n_bays=1 footprint's own width) with NO gap and no corner treatment
# between neighbours beyond each unit's own 4 corner blocks (a real party
# wall doesn't need its own extra piece here -- the two neighbours'
# corner posts simply sit back to back).
def row_house_placements(x0, y_back, tag, front, upper_front, roof_run, roof_gable):
    """y_back: the section's own local origin's y -- the door/gable edge
    lands at y_back-4.8 (see the module-level rotation note above)."""
    W = f"NW_KIT_WALL_{tag}_PLAIN_A" if tag else "NW_KIT_WALL_PLAIN_A"
    C = f"NW_KIT_WALL_{tag}_CORNER_A" if tag else "NW_KIT_WALL_CORNER_A"
    CU = f"NW_KIT_WALL_{tag}_CORNER_UPPER_A" if tag else "NW_KIT_WALL_CORNER_UPPER_A"
    return section_placements(
        x0, y_back, 270, S=W, N=W, E=front, W_=W, corner=C, n_bays=1, upper=True,
        UE=upper_front, upper_corner=CU, chimney_x=2.4,
        roof_run=roof_run, roof_gable=roof_gable,
    )


Y_ROW = 4.8   # door edge lands at y=0, matching the main road's south-facing convention
X0_ROW = 76.0
ROW_UNITS = [
    (None, "NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_ROOF_RUN_A", "NW_KIT_ROOF_END_GABLE_A"),
    ("RH1", "NW_KIT_WALL_RH1_WINDOW_A", "NW_KIT_WALL_RH1_UPPER_WINDOW_A", "NW_KIT_ROOF_RH1_RUN_A", "NW_KIT_ROOF_RH1_END_GABLE_A"),
    ("RH2", "NW_KIT_WALL_RH2_DOOR_A", "NW_KIT_WALL_RH2_UPPER_WINDOW_A", "NW_KIT_ROOF_RH2_RUN_A", "NW_KIT_ROOF_RH2_END_GABLE_A"),
    (None, "NW_KIT_WALL_WINDOW_A", "NW_KIT_WALL_UPPER_WINDOW_A", "NW_KIT_ROOF_RUN_A", "NW_KIT_ROOF_END_GABLE_A"),
    ("RH1", "NW_KIT_WALL_RH1_DOOR_A", "NW_KIT_WALL_RH1_UPPER_WINDOW_A", "NW_KIT_ROOF_RH1_RUN_A", "NW_KIT_ROOF_RH1_END_GABLE_A"),
]
row_mats, row_bm = [], bmesh.new()
row_overlap_parts = []
for i, (tag, front, upper_front, rrun, rgable) in enumerate(ROW_UNITS):
    for pname, mat in row_house_placements(X0_ROW + i * 4.8, Y_ROW, tag, front, upper_front, rrun, rgable):
        ob = P[pname]
        me = ob.data.copy()
        slots = [row_mats.index(m) if m in row_mats else (row_mats.append(m) or len(row_mats) - 1)
                 for m in ob.data.materials]
        for p in me.polygons:
            p.material_index = slots[p.material_index]
        me.transform(mat)
        row_bm.from_mesh(me)
        bpy.data.meshes.remove(me)
bmesh.ops.remove_doubles(row_bm, verts=row_bm.verts[:], dist=0.001)
groups = {}
for f in row_bm.faces:
    groups.setdefault(frozenset(v.index for v in f.verts), []).append(f)
inner = [f for g in groups.values() if len(g) == 2 for f in g]
bmesh.ops.delete(row_bm, geom=inner, context='FACES')
bmesh.ops.delete(row_bm, geom=[e for e in row_bm.edges if not e.link_faces], context='EDGES')
bmesh.ops.delete(row_bm, geom=[v for v in row_bm.verts if not v.link_edges], context='VERTS')
ovRow = len([e for e in row_bm.edges if len(e.link_faces) > 2])
for f in row_bm.faces:
    f.smooth = False
row_me = bpy.data.meshes.new("NW_ROW_HOUSES")
row_bm.to_mesh(row_me); row_bm.free()
for m in row_mats:
    row_me.materials.append(m)
row_houses = bpy.data.objects.new("NW_ROW_HOUSES", row_me); village_coll.objects.link(row_houses)

# ------------------------------------------------------------------ L-shape --
# First step toward L-shaped buildings (see SKILL.md lesson 19): two
# section_placements sections, each keeping its OWN complete, separate
# roof -- no valley yet, that's real future work. Section 2 sits directly
# north of section 1's own west bay, sharing that full wall length (not
# just a corner point) so the footprint actually reads as an L, at the
# cost of a doubled-up wall where the two sections' own N/S walls now
# stand back to back (an accepted simplification for this first pass,
# not hidden -- see the printed result's `lshape_doubled_wall` count).
def l_shape_placements(x0, y0):
    wing1 = section_placements(
        x0, y0, 0, n_bays=2, upper=True,
        S=("NW_KIT_WALL_DOOR_A", "NW_KIT_WALL_WINDOW_A"), N=("NW_KIT_WALL_PLAIN_A", "NW_KIT_WALL_PLAIN_A"),
        E="NW_KIT_WALL_WINDOW_A", W_="NW_KIT_WALL_PLAIN_A", corner="NW_KIT_WALL_CORNER_A",
        UE="NW_KIT_WALL_UPPER_WINDOW_A", upper_corner="NW_KIT_WALL_CORNER_UPPER_A", chimney_x=6.4,
    )
    wing2 = section_placements(
        x0 + 4.8, y0 + 4.8, 90, n_bays=1, upper=True,
        S="NW_KIT_WALL_PLAIN_A", N="NW_KIT_WALL_WINDOW_A",
        E="NW_KIT_WALL_WINDOW_A", W_="NW_KIT_WALL_PLAIN_A", corner="NW_KIT_WALL_CORNER_A",
        UN="NW_KIT_WALL_UPPER_WINDOW_A", UE="NW_KIT_WALL_UPPER_WINDOW_A",
        upper_corner="NW_KIT_WALL_CORNER_UPPER_A", chimney_x=2.4,
    )
    return wing1 + wing2


X0_L, Y0_L = -30.0, 8.0
lshape, ovL = build_house("NW_LSHAPE", X0_L, Y0_L, placements_fn=l_shape_placements)

# ---------------------------------------------------------------- ruin site --
# Three ruin walls (unmerged from each other -- a ruin site is a scatter of
# broken remnants, not a sealed volume) forming a rough broken enclosure on
# its own yard patch, south-west of house A.
RX0, RY0 = -14.0, -14.0
ruin_pieces = [("NW_KIT_WALL_RUIN_A", M(RX0, RY0, 0, 0)), ("NW_KIT_WALL_RUIN_A", M(RX0 + 4, RY0, 0, 0)),
              ("NW_KIT_WALL_RUIN_A", M(RX0, RY0 + 4, 0, 90))]
for i, (nm, mat) in enumerate(ruin_pieces):
    src_ob = P[nm]
    me = src_ob.data.copy()
    me.transform(mat)
    ob = bpy.data.objects.new(f"NW_RUIN_SITE_{i}", me)
    for m in src_ob.data.materials:
        me.materials.append(m)
    village_coll.objects.link(ob)

# fallen debris scattered around the broken enclosure -- two rubble mounds
# (one half-blocking the gap between the two south-facing remnants, one in
# the open corner) and a fallen beam slumped across the threshold, all
# unmerged standalone props, placed by eye like the ruin walls themselves.
debris_placements = [
    ("NW_KIT_RUIN_RUBBLE_A", M(RX0 + 2.0, RY0 - 0.6, 0, 15)),
    ("NW_KIT_RUIN_RUBBLE_A", M(RX0 + 4.9, RY0 + 3.2, 0, -40)),
    ("NW_KIT_RUIN_BEAM_A", M(RX0 + 0.6, RY0 + 0.3, 0, 20)),
]
for i, (nm, mat) in enumerate(debris_placements):
    src_ob = P[nm]
    me = src_ob.data.copy()
    me.transform(mat)
    ob = bpy.data.objects.new(f"NW_RUIN_DEBRIS_{i}", me)
    for m in src_ob.data.materials:
        me.materials.append(m)
    village_coll.objects.link(ob)

# ---------------------------------------------------------------- ground -----
TILE = 4.0
FLAT, YARD, ROAD, JUNC = "flat", "yard", "road", "junction"
grid = {}
for i in range(-9, 26):
    for j in range(-5, 5):
        grid[(i, j)] = (FLAT, 0)
for i in (0, 1, 2):        # house A dooryard
    for j in (0, 1):
        grid[(i, j)] = (YARD, 0)
for i in (4, 5, 6):        # house B dooryard
    for j in (0, 1):
        grid[(i, j)] = (YARD, 0)
for i in (8, 9, 10):       # house C dooryard
    for j in (0, 1):
        grid[(i, j)] = (YARD, 0)
for i in (11, 12):         # small house 1 dooryard
    for j in (0, 1):
        grid[(i, j)] = (YARD, 0)
for i in (13,):            # small house 2 dooryard (door faces the branch/square side)
    for j in (0, 1):
        grid[(i, j)] = (YARD, 0)
for i in (15, 16, 17):     # tavern dooryard
    for j in (0, 1):
        grid[(i, j)] = (YARD, 0)
for i in (-4, -3):         # ruin site yard
    for j in (-4, -3):
        grid[(i, j)] = (YARD, 0)
for i in (19, 20, 21, 22, 23):   # row house dooryards (one tile each, 4.8 m units on a 4 m grid)
    grid[(i, 0)] = (YARD, 0)
for i in range(-1, 25):    # the connecting road, one row in front of every building
    grid[(i, -1)] = (ROAD, 90)
for i in (0, 4, 8, 11, 15, 19):
    grid[(i, -1)] = (JUNC, 0)
# north branch off the main road, between small house 2 and the tavern, up
# to the civic square the townhall and church face onto
grid[(14, -1)] = (JUNC, 0)
for j in (0, 1):
    grid[(14, j)] = (ROAD, 0)
for i in range(11, 18):    # the square itself
    grid[(i, 2)] = (YARD, 0)
for i in (-8, -7, -6):     # L-shape building's own yard, west of the ruin site
    for j in (1, 2):
        grid[(i, j)] = (YARD, 0)

PIECE_OF = {FLAT: "NW_KIT_TERRAIN_FLAT_A", YARD: "NW_KIT_TERRAIN_YARD_A",
            ROAD: "NW_KIT_ROAD_STRAIGHT_A", JUNC: "NW_KIT_ROAD_JUNCTION_A"}


def GM(i, j, rot):
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
gbm.free()
for m in ground_mats:
    gme.materials.append(m)
ground = bpy.data.objects.new("NW_GROUND", gme); village_coll.objects.link(ground)

# --------------------------------------------------------------- terrain -----
# Rolling ground surrounding the flat modular footprint -- a height-field
# grid (gothic-terrain-piece's own technique: a rectangular vertex grid
# with a height field, never concentric rings, so it stays quad-only with
# no poles), flat (z=0) under the whole village tile footprint plus a
# short flat collar around it, rising into low hills further out. This is
# a SEPARATE mesh, positioned so its own flat collar sits at the same z=0
# plane and X/Y extent as the tile grid's outer edge -- a continuous-
# looking join, not a vertex weld (the tile grid and a hand-authored
# height field don't share a partition to weld against, the same
# touches-not-welds relationship the chimney/dormer already use elsewhere
# in this kit).
import random as _random
CORE_X0, CORE_X1 = -36.0, 100.0
CORE_Y0, CORE_Y1 = -20.0, 16.0
COLLAR = 4.0                                    # extra flat margin outside the tiles
PAD_X0, PAD_X1 = CORE_X0 - 28.0, CORE_X1 + 20.0
PAD_Y0, PAD_Y1 = CORE_Y0 - 26.0, CORE_Y1 + 22.0
NX, NY = 44, 40
_rng = _random.Random(1701)


def _terrain_height(x, y):
    dx = max(CORE_X0 - COLLAR - x, 0.0, x - (CORE_X1 + COLLAR))
    dy = max(CORE_Y0 - COLLAR - y, 0.0, y - (CORE_Y1 + COLLAR))
    d = math.hypot(dx, dy)
    if d <= 0.0:
        return 0.0
    rise = min(d / 14.0, 1.0)                    # smooth ramp up over ~14 m
    hill = (0.55 + 0.45 * math.sin(x * 0.09 + 1.3) * math.cos(y * 0.11 - 0.4)
            + 0.35 * math.sin(x * 0.21 - y * 0.17))
    return rise * max(0.0, 3.4 * hill)


tbm = bmesh.new()
tgrid = {}
for ix in range(NX + 1):
    for iy in range(NY + 1):
        x = PAD_X0 + (PAD_X1 - PAD_X0) * ix / NX
        y = PAD_Y0 + (PAD_Y1 - PAD_Y0) * iy / NY
        z = _terrain_height(x, y)
        tgrid[(ix, iy)] = tbm.verts.new((x, y, z))
for ix in range(NX):
    for iy in range(NY):
        tbm.faces.new((tgrid[(ix, iy)], tgrid[(ix + 1, iy)], tgrid[(ix + 1, iy + 1)], tgrid[(ix, iy + 1)]))
bmesh.ops.recalc_face_normals(tbm, faces=tbm.faces[:])
# small per-vertex roughening, skipped on the flat core+collar so the tile
# join stays exactly z=0
for v in tbm.verts:
    if v.co.z > 0.02:
        v.co.z += (_rng.random() - 0.5) * 0.10
tbm.normal_update()
terrain_mats = [ensure_material("NW_Nature_Waldboden_03"), ensure_material("NW_Nature_Stein_01")]
tuvl = tbm.loops.layers.uv.new("Float2")
tme = bpy.data.meshes.new("NW_TERRAIN")
tme.materials.append(terrain_mats[0])
tme.materials.append(terrain_mats[1])
for f in tbm.faces:
    c = f.calc_center_median()
    f.material_index = 1 if c.z > 2.2 else 0        # rocky above a height, grass below
    for loop in f.loops:
        loop[tuvl].uv = (loop.vert.co.x * 0.2, loop.vert.co.y * 0.2)
tbm.to_mesh(tme)
tbm.free()
terrain = bpy.data.objects.new("NW_TERRAIN", tme); village_coll.objects.link(terrain)

# ---------------------------------------------------------------- finish -----
for ob in (houseA, houseB, houseC, houseS1, houseS2, tavern, townhall, church,
          row_houses, lshape, ground, terrain):
    make_export_copy(ob, zenc)
for im in bpy.data.images:
    if im.source == 'FILE' and not im.packed_file:
        try:
            im.pack()
        except Exception:
            pass
bpy.ops.wm.save_as_mainfile(filepath=OUT)
result = dict(houseA_faces=len(houseA.data.polygons), houseA_overlap=ovA,
              houseB_faces=len(houseB.data.polygons), houseB_overlap=ovB,
              houseC_faces=len(houseC.data.polygons), houseC_overlap=ovC,
              houseS1_faces=len(houseS1.data.polygons), houseS1_overlap=ovS1,
              houseS2_faces=len(houseS2.data.polygons), houseS2_overlap=ovS2,
              tavern_faces=len(tavern.data.polygons), tavern_overlap=ovT,
              townhall_faces=len(townhall.data.polygons), townhall_overlap=ovH,
              church_faces=len(church.data.polygons), church_overlap=ovCh,
              row_houses_faces=len(row_houses.data.polygons), row_houses_overlap=ovRow,
              lshape_faces=len(lshape.data.polygons), lshape_overlap=ovL,
              ground_faces=len(ground.data.polygons), ground_overlap=ground_overlap,
              terrain_faces=len(terrain.data.polygons),
              catalog_pieces=len(ALL_PIECES), file=OUT, size=os.path.getsize(OUT))
print("RESULT:", result)
