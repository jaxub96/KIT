# New standalone pieces for the village expansion: a tavern sign post and a
# church bell tower. Neither is on a wall-bay weld contract -- both are
# freestanding, placed by eye next to/on a building the way the chimney and
# dormer already are. Needs kit_lib.py exec'd first.
import bpy, bmesh, math

# ------------------------------------------------------------------ sign post
# A post + bracket arm + hanging board, planted by a tavern's door, built as
# ONE continuous ring-sweep (post ring -> arm ring -> board rings) instead
# of three separate boxes -- each new ring REUSES the previous station's
# verts where they coincide, so the whole thing is one connected mesh from
# the start (lesson 15: shared grid verts, not separately-created
# coincident ones -- bmesh never merges those on its own).

def build_sign_post(ob, mats, zen_coll=None, seed=91, post_h=2.5, arm_len=0.85):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    bm = bmesh.new()
    hw = 0.09   # post/arm half-width (square cross-section throughout)

    def xy_ring(cz, hx=hw, hy=hw):
        """4 verts of an XY-plane square at height cz, cyclic order
        (-x,-y),(+x,-y),(+x,+y),(-x,+y) -- consistent with yz_ring's own
        cyclic order so a band between one of each never twists."""
        return [bm.verts.new((-hx, -hy, cz)), bm.verts.new((hx, -hy, cz)),
                bm.verts.new((hx, hy, cz)), bm.verts.new((-hx, hy, cz))]

    def yz_ring(cx, hy, hz_lo, hz_hi):
        """4 verts of a YZ-plane rectangle at x=cx, SAME cyclic order as
        xy_ring's (-x,-y)/(+x,-y)/(+x,+y)/(-x,+y) corners read as
        (lo,-y)/(hi,-y)/(hi,+y)/(lo,+y) here -- so it can pick up directly
        from an xy_ring's own +x-side pair without any twist."""
        return [bm.verts.new((cx, -hy, hz_lo)), bm.verts.new((cx, -hy, hz_hi)),
                bm.verts.new((cx, hy, hz_hi)), bm.verts.new((cx, hy, hz_lo))]

    def band(r0, r1, faces_out):
        for i in range(4):
            faces_out.append(bm.faces.new((r0[i], r0[(i + 1) % 4], r1[(i + 1) % 4], r1[i])))

    post_faces, arm_faces, board_faces = [], [], []
    base = xy_ring(0.0)
    mid = xy_ring(post_h - 2 * hw)                # extra ring: its +x side becomes the arm's own base
    top = xy_ring(post_h)
    band(base, mid, post_faces)
    # mid-top band, but SKIP the +x side (i=1): the arm's own band takes
    # over that exact rectangle (mid1,top1,top2,mid2) instead of the post
    # having its own flat face there AND the arm poking out through it --
    # each of the OTHER 3 edges of that rectangle already gets its 2nd
    # face from a neighbour (mid-top's i=0/i=2, or base-mid's i=1 for the
    # mid1-mid2 edge); only the far top1-top2 edge ends up with just the
    # arm's own single face -- a small, genuinely open transition edge,
    # declared via snap_planes below, not a bug.
    for i in (0, 2, 3):
        post_faces.append(bm.faces.new((mid[i], mid[(i + 1) % 4], top[(i + 1) % 4], top[i])))
    bm.faces.new(tuple(reversed(base)))            # post foot cap (sits on the ground)

    arm_base = [mid[1], top[1], top[2], mid[2]]    # the post's own +x-facing verts, REUSED (lesson 15)
    arm_tip = yz_ring(arm_len, hw, post_h - 2 * hw, post_h)
    band(arm_base, arm_tip, arm_faces)

    # The board is ONE taper straight from the arm's tip to the board's own
    # outline, then capped -- no intermediate ring (an earlier version used
    # two rings meeting at a shared seam z, but since they were built as
    # two SEPARATE `yz_ring()` calls at that same z, lesson 15 bit again:
    # coincident-but-not-shared verts collapsed that seam's faces to zero
    # area instead of welding).
    board_end = yz_ring(arm_len + 0.10, 0.42, post_h - 1.10, post_h - 0.30)
    band(arm_tip, board_end, board_faces)
    bm.faces.new(tuple(reversed(board_end)))       # board's outward-facing end cap

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    interior = [v for v in bm.verts if v.co.z > 0.05]
    # keep_planes=(2,post_h): the top ring's 4 edges are genuinely open (no
    # cap there -- the arm continues from 2 of its corners, the other 2
    # sides are just the post's unfinished top rim) and declared via
    # snap_planes below; z-jitter would push them off that exact plane and
    # break the snap match.
    jitter(bm, interior, (0.006, 0.006, 0.006), seed=seed, keep_planes=[(2, post_h)])
    bm.normal_update()

    ob.data.materials.clear()
    ob.data.materials.append(mats["timber"])
    ob.data.materials.append(mats["board"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    TI = (300 / 256, 300 / 512)
    board_set = set(board_faces)
    for f in bm.faces:
        if f in board_set:
            f.material_index = 1
            set_wrap_uv(f, uvl, (1.0, 1.0), (0.0, 0.0))
        else:
            f.material_index = 0
            set_beam_uv(f, uvl, "V", TI, 0.1, 0.0)
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(2, post_h)], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res


# ------------------------------------------------------------------ bell tower
# A square stone tower with a steep hip-style spire. The spire is a
# FRUSTUM (wall-top ring tapering to a small flat ring, not a single
# point), capped by one small flat quad -- reads as a spire silhouette
# without a pole at the apex (a true 4-triangle pyramid tip is a valence-4
# pole; this sidesteps it the same way a real hip roof's ridge does).

def build_bell_tower(ob, mats, zen_coll=None, seed=95, w=2.0, wall_h=5.6, spire_h=2.6, tip=0.25):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    if zen_coll is not None:
        for o in [o for o in bpy.data.objects if o.name == ob.name + "_ZEN"]:
            bpy.data.meshes.remove(o.data)
    bm = bmesh.new()
    hw = w / 2
    # wall shaft: base ring -> belfry-opening ring -> wall-top ring, so the
    # belfry (louvre) band reads as a distinct storey, not just a texture
    OPEN_LO, OPEN_HI = wall_h - 1.5, wall_h - 0.3

    def ring(z, half):
        return [bm.verts.new((-half, -half, z)), bm.verts.new((half, -half, z)),
                bm.verts.new((half, half, z)), bm.verts.new((-half, half, z))]

    base = ring(0.0, hw)
    belfry_lo = ring(OPEN_LO, hw)
    belfry_hi = ring(OPEN_HI, hw)
    top = ring(wall_h, hw)
    tip_ring = ring(wall_h + spire_h, tip / 2)

    shaft_faces, belfry_faces, spire_faces = [], [], []

    def wall_band(lo, hi, store):
        for i in range(4):
            f = bm.faces.new((lo[i], lo[(i + 1) % 4], hi[(i + 1) % 4], hi[i]))
            store.append(f)
    wall_band(base, belfry_lo, shaft_faces)
    wall_band(belfry_lo, belfry_hi, belfry_faces)
    wall_band(belfry_hi, top, shaft_faces)
    for i in range(4):
        spire_faces.append(bm.faces.new((top[i], top[(i + 1) % 4], tip_ring[(i + 1) % 4], tip_ring[i])))
    spire_faces.append(bm.faces.new((tip_ring[0], tip_ring[1], tip_ring[2], tip_ring[3])))  # small flat cap
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    interior = [v for v in bm.verts if abs(v.co.z) > 1e-4]
    jitter(bm, interior, (0.02, 0.02, 0.015), seed=seed, keep_planes=[])
    bm.normal_update()

    ob.data.materials.clear()
    ob.data.materials.append(mats["stone"])
    ob.data.materials.append(mats["belfry"])
    ob.data.materials.append(mats["spire"])
    uvl = bm.loops.layers.uv.get("Float2") or bm.loops.layers.uv.new("Float2")
    belfry_set, spire_set = set(belfry_faces), set(spire_faces)
    for f in bm.faces:
        c = f.calc_center_median()
        if f in belfry_set:
            f.material_index = 1
            set_wrap_uv(f, uvl, (0.4, 0.4), (0.0, 0.0))
        elif f in spire_set:
            f.material_index = 2
            set_wrap_uv(f, uvl, (0.35, 0.35), (0.0, 0.0))
        else:
            f.material_index = 0
            set_wrap_uv(f, uvl, (0.5, 0.5), (0.0, 0.10))
    write_piece(ob, bm)
    bm.free()
    res = check_piece(ob, snap_planes=[(2, 0.0)], flat_tri_ok=True)
    if zen_coll is not None:
        make_export_copy(ob, zen_coll)
    return res
