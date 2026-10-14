# Decorated window variant of the standard window bay: a carved-ornament
# jamb (replacing the plain timber trim) via one small, backward-compatible
# addition to wall_bay.py's build_wall_bay -- an opening's "trim" key
# overrides its jamb from plain "timber" to any other registered kind (here
# "ornament").
#
# An earlier version of this piece also added a pair of open shutter panels
# (via the generic extra_members/extra_kinds/extra_uv mechanism, still used
# here for the ornament jamb), hinged just outside the jamb and folded flat
# against the wall. Dropped: at the piece's actual scale the shutter panel
# is only wide enough to show a sliver of the door-plank texture reused for
# it (NW_City_Door_01, chosen for its wood-plank look), which put that
# texture's own hinge-and-lock hardware decal squarely on the shutter panel
# -- a door fitting on a window shutter, in a jarring off-palette orange
# against the rest of the piece's aged dark timber. Not a UV-stretch bug
# (see the piece's own separate, already-documented anisotropic-UV note),
# a wrong-texture-for-the-part problem, and not worth a dedicated shutter
# texture for two small panels -- simpler to keep the ornament jamb, which
# reads fine on its own, and drop the shutters. See SKILL.md lesson 23.
# Needs kit_lib.py and wall_bay.py exec'd first.
import bpy, bmesh


def build_window_shutter_bay(ob, x0, x1, mats, zen_coll=None, seed=15, storey="ground"):
    """Ground or upper window bay with a carved-ornament jamb (replacing the
    plain timber trim). `mats` needs an "ornament" key in addition to the
    usual plaster/timber/stone."""
    spec = dict(openings=[dict(kind="window", x0=x0, x1=x1, trim="ornament", jamb=DOOR_JAMB)],
                extra_kinds=("ornament",))
    if storey == "upper":
        spec["storey"] = "upper"
    TI_ORN = (300 / 128, 300 / 512)   # NW_City_Wood_Ornament_01 is 128x512

    def uv_ornament(f, uvl, mem):
        set_beam_uv(f, uvl, "V", TI_ORN, 0.1, mem[0] if mem else 0.0)

    spec["extra_uv"] = {"ornament": uv_ornament}
    return build_wall_bay(ob, spec, mats, zen_coll=zen_coll, seed=seed)
