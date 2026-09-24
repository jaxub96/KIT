# Straight interior stair (one flight, ground floor -> upper floor), shared by the
# Gothic basic set (KIT_STAIR_A) and the Maya family (KIT_MAYA_STAIR_A).
# Needs kit_lib.py exec'd first.
#
# Frame = the room tile frame: origin on the ground at the inner room corner,
# the flight runs along the back wall (y = Y0..Y1, the wall's inside face at
# y = 4) and climbs +x. Its last tread stops at x_top, under the edge of the
# stairwell floor tile's opening (floor_tile.build_floor_tile(hole=...) /
# maya_bay.build_maya_floor_stairwell): that edge is the top riser, so the
# stair and the stairwell tile go to the same room corner.
#
# Low poly on purpose: one sawtooth profile swept across the width, no
# balusters, no nosing boxes. Every riser except the first leans back by RAKE,
# so the profile's points all have different x and each side is one strip of
# vertical-edged quads down to the soffit (or the floor): quads only, no
# poles, no n-gons. Faces on the floor are left out (open, like KIT_MAYA_STEP_A).
import bpy, bmesh, math, random
from mathutils import Vector

RAKE = 0.03          # riser lean (top edge set back), also a visual nosing
STAIR_Y = (3.0, 4.0)  # 1 m wide flight against the back wall


def stair_profile(z0, z1, n, x_top, going):
    """Top profile points (x, z, kind) in +x order: n risers of equal height
    from z0 to z1, n-1 treads, the n-th riser being the floor edge at x_top.
    kind tags the face that STARTS at that point ('riser' / 'tread')."""
    h = (z1 - z0) / n
    x0 = x_top - (n - 1) * going
    pts = [(x0, z0 + h, "tread")]                            # riser 0 is vertical: A0 -> B0
    for i in range(1, n - 1):
        pts.append((x0 + i * going, z0 + i * h, "riser"))    # tread end = riser bottom
        pts.append((x0 + i * going + RAKE, z0 + (i + 1) * h, "tread"))
    pts.append((x_top, z0 + (n - 1) * h, None))              # top tread ends at the floor edge
    return x0, h, pts


def build_stair(ob, mats, z0, z1, n, x_top, going, soffit=None, y=STAIR_Y, seed=3,
                uv=None, wear=0.006):
    """mats: {'tread', 'riser', 'side', 'soffit'} -> material (may repeat).
    soffit=None: solid to the floor (masonry); soffit=D: underside parallel to
    the pitch, D metres (vertical) under the nosing line, floored where it
    would go below z0 (timber). uv(face, uvl, kind, info) assigns UVs."""
    x0, h, pts = stair_profile(z0, z1, n, x_top, going)
    tanp = h / going
    rnd = random.Random(seed)

    def zb(x):
        if soffit is None:
            return z0
        return max(z0, z0 + (x - x0) * tanp + h - soffit)
    bm = bmesh.new()
    Y0, Y1 = y
    top, bot = {}, {}
    for k, (x, z, _) in enumerate(pts):
        for yy in (Y0, Y1):
            dz = 0.0 if k in (0, len(pts) - 1) else (rnd.random() * 2 - 1) * wear
            top[(k, yy)] = bm.verts.new((x, yy, z + dz))
            bot[(k, yy)] = bm.verts.new((x, yy, zb(x)))
    foot = {yy: bm.verts.new((x0, yy, z0)) for yy in (Y0, Y1)}   # A0: bottom of riser 0
    kinds = {}

    def face(vs, kind, info=None):
        f = bm.faces.new(vs)
        kinds[f] = (kind, info)
        return f
    # riser 0 (front of the foot); the first side strip starts at the foot vertex
    face((foot[Y0], foot[Y1], top[(0, Y1)], top[(0, Y0)]), "riser", 0)
    for k in range(len(pts) - 1):
        kind = pts[k][2]
        face((top[(k, Y0)], top[(k, Y1)], top[(k + 1, Y1)], top[(k + 1, Y0)]), kind, k)
        for yy, flip in ((Y0, False), (Y1, True)):
            b0 = foot[yy] if k == 0 else bot[(k, yy)]
            q = (b0, bot[(k + 1, yy)], top[(k + 1, yy)], top[(k, yy)])
            face(q[::-1] if flip else q, "side", k)
        if soffit is not None and zb(pts[k + 1][0]) > z0 + 1e-6:
            b0y0 = foot[Y0] if k == 0 else bot[(k, Y0)]
            b0y1 = foot[Y1] if k == 0 else bot[(k, Y1)]
            face((b0y0, bot[(k + 1, Y0)], bot[(k + 1, Y1)], b0y1), "soffit", k)
    kl = len(pts) - 1                                        # end against the stairwell rim
    face((bot[(kl, Y0)], top[(kl, Y0)], top[(kl, Y1)], bot[(kl, Y1)]), "side", kl)
    for k in range(len(pts)):                                # merge the unused bottom row at the foot
        for yy in (Y0, Y1):
            v = bot[(k, yy)]
            if v.is_valid and not v.link_faces:
                bm.verts.remove(v)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # the treads/risers must face up/forward; recalc may flip an open shell inward
    trd = [f for f, (kd, _) in kinds.items() if kd == "tread" and f.is_valid]
    if trd and sum(f.normal.z for f in trd) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bm.normal_update()
    slots = []
    for kd in ("tread", "riser", "side", "soffit"):
        if mats[kd] not in slots:
            slots.append(mats[kd])
    ob.data.materials.clear()
    for m in slots:
        ob.data.materials.append(m)
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    info = dict(x0=x0, h=h, going=going, z0=z0, tanp=tanp, pts=pts)
    for f in bm.faces:
        kd, k = kinds.get(f, ("side", None))
        f.material_index = slots.index(mats[kd])
        if uv:
            uv(f, uvl, kd, dict(info, k=k))
        else:
            set_wrap_uv(f, uvl, (0.5, 0.5))
    write_piece(ob, bm)
    bm.free()
    return check_piece(ob, snap_planes=[(2, z0)], flat_tri_ok=True)


# ---- Gothic basic set: timber stair --------------------------------------------
# ground planks at FOOT = 0.46, upper floor tile (placed at z = 3) planks at 3.0;
# the stairwell opening of floor_tile.STAIRWELL spans x 0.58..3.42 (between the
# first and last joist), so the flight tops out at x = 3.42.
GOTHIC_STAIR = dict(z0=0.46, z1=3.0, n=10, x_top=3.42, going=0.30, soffit=0.34)


def gothic_stair_uv(f, uvl, kind, info):
    """Treads and risers: one floor board each (NW_City_BodenDielen_02 has 4
    boards across v, 0.25 each, like floor_tile). Stringer sides / soffit:
    boards running up the pitch."""
    k = info["k"] or 0
    if kind in ("tread", "riser"):
        row = (k * 3 + (1 if kind == "riser" else 0)) % 4
        n = f.normal
        vs = [l.vert.co for l in f.loops]
        if kind == "tread":
            a0, a1 = min(c.x for c in vs), max(c.x for c in vs)
            span = lambda c: (c.x - a0) / max(a1 - a0, 1e-6)
        else:
            a0, a1 = min(c.z for c in vs), max(c.z for c in vs)
            span = lambda c: (c.z - a0) / max(a1 - a0, 1e-6)
        for l in f.loops:
            c = l.vert.co
            l[uvl].uv = (c.y * 0.5 + k * 0.37, row * 0.25 + 0.01 + span(c) * 0.23)
        return
    # WoodBeam_01's grain runs along V: V up the pitch (1 m per repeat, the iron
    # strap becomes bands on the stringer), U across it (one beam per 0.5 m)
    d = Vector((1.0, 0.0, info["tanp"])).normalized()
    o = Vector((info["x0"], 0.0, info["z0"]))
    across = Vector((0, 1, 0)) if kind == "soffit" else Vector((-d.z, 0.0, d.x))
    set_directional_uv(f, uvl, o, across, d, 0.5, 1.0)


def build_gothic_stair(ob):
    m = ensure_material("NW_City_BodenDielen_02")
    s = ensure_material("NW_City_WoodBeam_01")
    return build_stair(ob, {"tread": m, "riser": m, "side": s, "soffit": s}, uv=gothic_stair_uv,
                       wear=0.004, **GOTHIC_STAIR)


# ---- Maya family: solid masonry stair ------------------------------------------
# ground flags at 0.05, upper plank floor at 2.98 (both placed at the room
# corner at z = 0); the stairwell opening of maya_bay.MAYA_STAIRWELL spans
# x 0.5..3.5.
MAYA_STAIR = dict(z0=0.05, z1=2.98, n=11, x_top=3.5, going=0.30, soffit=None)


def build_maya_stair(ob, mats):
    """mats = maya_bay.maya_mats(): ashlar treads/risers ('step'), plastered
    solid body ('plaster')."""
    def uv(f, uvl, kind, info):
        set_wrap_uv(f, uvl, (0.5, 0.5), (0.0, 0.0))
    return build_stair(ob, {"tread": mats["step"], "riser": mats["step"], "side": mats["plaster"],
                            "soffit": mats["plaster"]}, uv=uv, wear=0.008, seed=5, **MAYA_STAIR)
