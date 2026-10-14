# Adds the inner-corner L walls to kit/KIT_WALLS.blend (run in background):
#   Blender -b kit/KIT_WALLS.blend --python add_l_inner_pieces.py
# Built from the kit's own bays (wall_l_inner.build_l_inner), marked as assets
# in Kit/WALLS next to the other wall pieces, file saved.
import bpy, os
S = os.path.dirname(os.path.abspath(__file__)) + "/"
g = {"__name__": "kit"}
for f in ("kit_lib.py", "wall_l_inner.py"):
    exec(compile(open(S + f).read(), S + f, "exec"), g)

WALLS_CAT = "3bc920fb-3690-47d9-93bb-93041a16a9ff"      # Kit/WALLS
ORIGIN = ("Origin = the inside corner point on the floor (where the two inside faces meet); "
          "leg A runs +X (front faces -Y), leg B runs -Y (front faces +X), each 4 m along its inside face. ")
USE = ("Replaces the two overlapping bays at an inner (re-entrant) corner: put it on the inside corner's "
       "grid point. The far ends are standard bay end loops (weld to a corner block or the next bay); "
       "the two legs meet on a 45 deg mitre with a 0.3 m timber post in the corner.")
PIECES = [  # name, leg A bay, leg B bay, description head, tags
    ("KIT_WALL_L_INNER_A", "KIT_WALL_PLAIN_A", "KIT_WALL_PLAIN_A",
     "Inner-corner L wall, ground floor, closed. ", ["wall", "corner", "inner corner", "L", "plain"]),
    ("KIT_WALL_L_INNER_WINDOW_A", "KIT_WALL_PLAIN_A", "KIT_WALL_WINDOW_A",
     "Inner-corner L wall, ground floor, window on leg B (the left leg seen from outside). ",
     ["wall", "corner", "inner corner", "L", "window"]),
    ("KIT_WALL_UPPER_L_INNER_A", "KIT_WALL_UPPER_PLAIN_A", "KIT_WALL_UPPER_PLAIN_A",
     "Inner-corner L wall, upper floor, closed (stacks on a ground L). ",
     ["wall", "corner", "inner corner", "L", "upper floor", "plain"]),
    ("KIT_WALL_UPPER_L_INNER_WINDOW_A", "KIT_WALL_UPPER_PLAIN_A", "KIT_WALL_UPPER_WINDOW_A",
     "Inner-corner L wall, upper floor, window on leg B (the left leg seen from outside). ",
     ["wall", "corner", "inner corner", "L", "upper floor", "window"]),
]

coll = bpy.data.collections["KIT_WALL"]
row = [o for o in coll.objects if abs(o.location.y - 20.2) < 0.01]
x0 = max(o.location.x for o in row) + 6.0
report = {}
for i, (name, a, b, head, tags) in enumerate(PIECES):
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, bpy.data.meshes.new(name))
        coll.objects.link(ob)
    ob.location = (x0 + i * 6.0, 20.2, 0.0)
    r = g["build_l_inner"](ob, bpy.data.objects[a].data, bpy.data.objects[b].data)
    report[name] = {k: v for k, v in r.items() if k.endswith("_bad") and v}
    ob["kit_origin"] = "see description"
    ob["kit_style"] = "city_timber"
    ob.asset_mark()
    ad = ob.asset_data
    ad.catalog_id = WALLS_CAT
    ad.description = head + ORIGIN + USE
    ad.author = "Blend-Zen kit"
    for t in list(ad.tags):
        ad.tags.remove(t)
    for t in tags:
        ad.tags.new(t)
print("L_INNER_REPORT", report)
bpy.ops.wm.save_mainfile()
print("SAVED", bpy.data.filepath, os.path.getsize(bpy.data.filepath))
