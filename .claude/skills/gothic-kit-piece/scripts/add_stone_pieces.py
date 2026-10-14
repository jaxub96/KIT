# Adds the stone ground-floor pieces to kit/KIT_WALLS.blend (run in background):
#   Blender -b kit/KIT_WALLS.blend --python add_stone_pieces.py
import bpy, os
S = os.path.dirname(os.path.abspath(__file__)) + "/"
g = {"__name__": "kit"}
for f in ("kit_lib.py", "weld_pieces.py", "stone_bay.py", "wall_l_inner.py"):
    exec(compile(open(S + f).read(), S + f, "exec"), g)

WALLS_CAT = "3bc920fb-3690-47d9-93bb-93041a16a9ff"      # Kit/WALLS
stone = g["ensure_material"]("NW_Seq_Maya_Stone_GreyTrans_03_XL")
for n in stone.node_tree.nodes:
    if n.type == 'TEX_IMAGE' and n.image and not n.image.packed_file:
        n.image.pack()
M = {"stone": stone, "timber": bpy.data.objects["KIT_WALL_PLAIN_A"].data.materials[1]}
COMMON = ("Rubble-stone ground floor (mossy at the foot) under a jettied timber storey: the stone face is set "
          "0.3 m back from the timber walls above, and a timber girt with brackets carries the overhang. "
          "Same grid point and rotation as the timber ground bay it replaces (origin on the floor at the upper "
          "wall's inside face, left end; front faces -Y). Open ends and an open top seam: welds to the next stone "
          "bay, the stone corners and the timber upper storey with Merge by Distance. ")
PIECES = [
    ("KIT_WALL_STONE_PLAIN_A", "plain", "4 m stone ground bay, closed. ", ["wall", "stone", "ground floor", "jetty", "plain"]),
    ("KIT_WALL_STONE_WINDOW_A", "window", "4 m stone ground bay with a window (same opening as the timber bays, "
     "so the glazing fits 0.3 m further in) and a stone sill. ", ["wall", "stone", "ground floor", "jetty", "window"]),
    ("KIT_WALL_STONE_DOOR_A", "door", "4 m stone ground bay with a 1.2 m round-arched door (threshold at 0.46). ",
     ["wall", "stone", "ground floor", "jetty", "door", "arch"]),
    ("KIT_WALL_STONE_DOOR_WIDE_A", "door_wide", "4 m stone ground bay with a 2 m round-arched gateway. ",
     ["wall", "stone", "ground floor", "jetty", "door", "arch", "wide"]),
    ("KIT_WALL_STONE_CORNER_A", "corner", "Outer corner for the stone ground floor: the bay's section mitred round "
     "the corner, girt included. Origin = the inside corner, like KIT_WALL_CORNER_A (rotate 0/90/180/270). ",
     ["corner", "stone", "ground floor", "jetty"]),
    ("KIT_WALL_STONE_L_INNER_A", "L:plain:plain", "Inner-corner L for the stone ground floor (two plain legs, 45 deg "
     "mitre, like KIT_WALL_L_INNER_A). Origin = the inside corner point. ", ["corner", "stone", "inner corner", "L"]),
    ("KIT_WALL_STONE_L_INNER_WINDOW_A", "L:plain:window", "Inner-corner L for the stone ground floor, window on leg B. "
     "Origin = the inside corner point. ", ["corner", "stone", "inner corner", "L", "window"]),
]
KINDS_BAY = ("plain", "window", "door", "door_wide")
coll = bpy.data.collections["KIT_WALL"]
row = [o for o in coll.objects if abs(o.location.y - 20.2) < 0.01]
x0 = max(o.location.x for o in row if not o.name.startswith("KIT_WALL_STONE")) + 6.0
report = {}
for i, (name, kind, head, tags) in enumerate(PIECES):
    ob = bpy.data.objects.get(name)
    if ob is None:
        ob = bpy.data.objects.new(name, bpy.data.meshes.new(name))
        coll.objects.link(ob)
    ob.location = (x0 + i * 6.0, 20.2, 0.0)
    if kind == "corner":
        r = g["build_stone_corner"](ob, bpy.data.objects["KIT_WALL_STONE_PLAIN_A"], M)
    elif kind.startswith("L:"):
        _, a, b = kind.split(":")
        nm = {"plain": "KIT_WALL_STONE_PLAIN_A", "window": "KIT_WALL_STONE_WINDOW_A"}
        r = g["build_l_inner"](ob, bpy.data.objects[nm[a]].data, bpy.data.objects[nm[b]].data, plaster_slot=None)
    else:
        r = g["build_stone_bay"](ob, M, kind=kind)
    report[name] = {k: v for k, v in r.items() if k.endswith("_bad") and v}
    ob["kit_origin"] = "see description"
    ob["kit_style"] = "city_timber_stone"
    ob.asset_mark()
    ad = ob.asset_data
    ad.catalog_id = WALLS_CAT
    ad.description = head + COMMON if kind in KINDS_BAY else head + "Welds to the stone bays and the timber storey above."
    ad.author = "Blend-Zen kit"
    for t in list(ad.tags):
        ad.tags.remove(t)
    for t in tags:
        ad.tags.new(t)
print("STONE_REPORT", report)
bpy.ops.wm.save_mainfile()     # previews: not regenerated here (see regen_previews.py)
print("SAVED", bpy.data.filepath, os.path.getsize(bpy.data.filepath))
