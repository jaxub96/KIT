# The basic residential set (KIT_WALL_*_A ground + upper bays and their corners): the
# build spec of every piece, so the set can be rebuilt after a change to
# wall_bay.py / weld_pieces.py. Specs and seeds were recovered 2026-09-23 by
# rebuilding with the then-current builders and matching the shipped meshes
# vertex for vertex (all 11 exact).
# Needs kit_lib.py, wall_bay.py, window_dress.py and weld_pieces.py exec'd first.
import bpy
from mathutils import Matrix, Vector

W = lambda a, b: dict(kind="window", x0=a, x1=b)
D = lambda a, b: dict(kind="door", x0=a, x1=b)

BASIC_GROUND = {                     # name: (spec, seed); None spec = window_dress
    "KIT_WALL_DOOR_A": (dict(openings=[D(1.4, 2.6)]), 1),
    "KIT_WALL_WINDOW_A": (dict(openings=[W(1.5, 2.5)]), 1),
    "KIT_WALL_WINDOW_TWIN_A": (dict(openings=[W(0.5, 1.5), W(2.5, 3.5)]), 4),
    "KIT_WALL_PLAIN_A": (dict(openings=[]), 3),
    "KIT_WALL_PLAIN_LIGHT_A": (dict(openings=[], sparse=True), 6),
    "KIT_WALL_WINDOW_SHUTTER_A": (None, 15),        # build_window_shutter_bay(ob, 1.4, 2.6)
}
BASIC_CORNERS = {                    # derived from KIT_WALL_PLAIN_A's end loop
    "KIT_WALL_CORNER_A": dict(nudge_top=False),
    "KIT_WALL_CORNER_SOLO_A": dict(nudge_top=False),   # open top: the gable end welds onto it
}
BASIC_UPPER = {                      # same recovery, against the git HEAD builders
    "KIT_WALL_UPPER_WINDOW_A": (dict(storey="upper", openings=[W(1.5, 2.5)]), 1),
    "KIT_WALL_UPPER_PLAIN_A": (dict(storey="upper", openings=[]), 7),
}
UPPER_CORNERS = {                    # derived from KIT_WALL_UPPER_PLAIN_A's end loop
    "KIT_WALL_CORNER_UPPER_A": dict(nudge_top=False),
}


def _mats(ob):
    """The piece's CURRENT materials by slot (whatever the user swapped in)."""
    ms = ob.data.materials
    d = {"plaster": ms[0], "timber": ms[1], "stone": ms[2]}
    if len(ms) > 3:
        d["ornament"] = ms[3]
    return d


def rebuild_basic_ground(objects=None):
    """Rebuild the basic ground set in place (legacy frame, corners derived,
    then rebase_origin on all). `objects` maps piece name -> target object
    (default: the kit objects of the same name). Returns {name: check_piece}."""
    objects = objects or {n: bpy.data.objects[n] for n in
                          list(BASIC_GROUND) + list(BASIC_CORNERS) + list(BASIC_UPPER) + list(UPPER_CORNERS)}
    res = {}
    for n, (spec, seed) in list(BASIC_GROUND.items()) + list(BASIC_UPPER.items()):
        ob = objects[n]
        if spec is None:
            res[n] = build_window_shutter_bay(ob, 1.4, 2.6, _mats(ob), seed=seed)
        else:
            res[n] = build_wall_bay(ob, {k: (list(v) if isinstance(v, list) else v) for k, v in spec.items()},
                                    _mats(ob), seed=seed)
    for bay_name, corners in (("KIT_WALL_PLAIN_A", BASIC_CORNERS), ("KIT_WALL_UPPER_PLAIN_A", UPPER_CORNERS)):
        for n, kw in corners.items():
            ob = objects[n]
            res[n] = build_corner_from_bay(ob, objects[bay_name], {0: "plaster", 1: "timber", 2: "stone"},
                                           _mats(ob), **kw)
    for n, ob in objects.items():
        ob.data.transform(Matrix.Translation(-Vector(origin_shift(n))))   # rebase_origin, by piece name
    return res
