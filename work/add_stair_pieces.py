# Adds / rebuilds the stair pieces in the two kit libraries without touching
# anything else in them (the full builders would replace the user's edits):
#   Blender -b kit/KIT_WALLS.blend --python add_stair_pieces.py -- gothic
#   Blender -b kit/KIT_MAYA.blend  --python add_stair_pieces.py -- maya
# Pieces: KIT_STAIR_A + KIT_FLOOR_STAIRWELL_A / _END_A (Gothic basic set),
# KIT_MAYA_STAIR_A + KIT_MAYA_FLOOR_UPPER_STAIRWELL_A (Maya). See stair.py.
import bpy, sys, os
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".claude", "skills", "gothic-kit-piece", "scripts") + "/"
KIT = sys.argv[sys.argv.index("--") + 1]
g = {'__name__': 'kit'}
for f in ("kit_lib.py", "weld_pieces.py", "floor_tile.py", "maya_bay.py", "stair.py"):
    exec(open(S + f).read(), g)
CATS = {"gothic": {"FLOORS": "45b4d690-e938-4fb0-902c-8c1044cbe921", "STRUCTS": "c9ec0d1e-978c-4254-bd6e-425c0c08de57"},
        "maya": {"FLOORS": "0970c342-c8aa-4c0f-a15d-1c5761ccf0a3", "STRUCTS": "fafaf0a5-8407-4291-b497-038794104d2a"}}[KIT]
STAIR_DESC = ("Straight stair, ground floor to upper floor, 1 m wide along the back wall (y 3..4), "
              "climbing +x. Origin = inner room corner on the ground: place it at the same point as the "
              "room's first ground floor tile, with the stairwell floor tile above it.")


def piece(name, coll, loc):
    ob = bpy.data.objects.get(name)
    if ob is None:
        me = bpy.data.meshes.new(name)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        ob.location = loc
    if "Float2" not in ob.data.uv_layers:
        ob.data.uv_layers.new(name="Float2")
    return ob


def asset(ob, cat, desc, tags):
    if ob.asset_data is None:
        ob.asset_mark()
    a = ob.asset_data
    a.catalog_id = CATS[cat]
    a.description = desc
    a.use_preferred_import_method = True
    a.preferred_import_method = 'APPEND'
    for t in tags:
        if t not in a.tags:
            a.tags.new(t)


out = {}
if KIT == "gothic":
    coll = bpy.data.collections["KIT_WALL"]
    fm = bpy.data.objects["KIT_FLOOR_A"].data.materials              # the floor's current materials
    mats = {"floor": fm[0], "timber": fm[1]}
    for i, (n, closed) in enumerate((("KIT_FLOOR_STAIRWELL_A", False), ("KIT_FLOOR_STAIRWELL_END_A", True))):
        ob = piece(n, coll, (24.0 + 6 * i, 100.2, 0.0))
        out[n] = g['build_floor_tile'](ob, mats, closed_x0=closed, hole=g['STAIRWELL'])
        asset(ob, "FLOORS", ("4 x 4 m upper floor tile with a 2.84 x 1 m stairwell against the y=4 wall "
                             "(for KIT_STAIR_A). Same snap loops as KIT_FLOOR%s_A: use it in its place, at z = 3."
                             % ("_END" if closed else "")), ["floor", "stairwell", "timber"])
    ob = piece("KIT_STAIR_A", coll, (36.0, 100.2, 0.0))
    out["KIT_STAIR_A"] = g['build_gothic_stair'](ob)
    asset(ob, "STRUCTS", STAIR_DESC + " Pair: KIT_FLOOR_STAIRWELL_A / _END_A at z = 3.", ["stair", "timber", "interior"])
else:
    coll = bpy.data.collections["MAYA"]
    mats = g['maya_mats']()
    ob = piece("KIT_MAYA_FLOOR_UPPER_STAIRWELL_A", coll, (22.0, -30.0, 0.0))
    out[ob.name] = g['build_maya_floor_stairwell'](ob, mats)
    asset(ob, "FLOORS", ("KIT_MAYA_FLOOR_UPPER_A with a 3 x 1 m stairwell against the y=4 wall (for "
                         "KIT_MAYA_STAIR_A); same open edges, place it the same way."), ["floor", "stairwell"])
    ob = piece("KIT_MAYA_STAIR_A", coll, (27.5, -30.0, 0.0))
    out[ob.name] = g['build_maya_stair'](ob, mats)
    asset(ob, "STRUCTS", STAIR_DESC + " Pair: KIT_MAYA_FLOOR_UPPER_STAIRWELL_A (same point).", ["stair", "stone", "interior"])
bpy.ops.wm.save_mainfile()
print("ADD_JSON", {n: {k: v for k, v in r.items() if k.endswith('_bad') and v} for n, r in out.items()})
