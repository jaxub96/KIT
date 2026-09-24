# Builds blender_work_dir/kit/KIT_MAYA.blend (Maya family) and runs the weld tests.
#   Blender -b --factory-startup --python build_maya_kit.py -- SAVE [RENDER]

import bpy, bmesh, json, math, sys
from mathutils import Matrix, Vector, Euler
S="/Users/jakubjaworski/Creativity/Blender Projects/Blender User Scripts/KIT/.claude/skills/gothic-kit-piece/scripts/"
OUTBLEND="/Users/jakubjaworski/Creativity/Blender Projects/Blender User Scripts/KIT/blender_work_dir/kit/KIT_MAYA.blend"
import os; SCR=os.path.join(os.path.dirname(os.path.abspath(__file__)), "maya_renders") + "/"; os.makedirs(SCR, exist_ok=True)
ARGS=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
g={'__name__':'kit'}
for f in ("kit_lib.py","weld_pieces.py","maya_bay.py","stair.py"): exec(open(S+f).read(), g)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
col=bpy.data.collections.new("MAYA"); bpy.context.scene.collection.children.link(col)
mats=g['maya_mats']()
def new(n):
    me=bpy.data.meshes.new(n); ob=bpy.data.objects.new(n,me); col.objects.link(ob); return ob
P={}; out={}
for n,(spec,seed) in g['MAYA_BAYS'].items():
    P[n]=new(n); out[n]=g['build_maya_bay'](P[n], json.loads(json.dumps(spec)), mats, seed=seed)
for n,kw in g['MAYA_PARAPETS'].items():
    P[n]=new(n); out[n]=g['build_maya_parapet'](P[n], mats, **kw)
for n,up in (("KIT_MAYA_FLOOR_GROUND_A",False),("KIT_MAYA_FLOOR_UPPER_A",True)):
    P[n]=new(n); out[n]=g['build_maya_floor'](P[n], mats, upper=up)
P["KIT_MAYA_STEP_A"]=new("KIT_MAYA_STEP_A"); out["KIT_MAYA_STEP_A"]=g['build_maya_step'](P["KIT_MAYA_STEP_A"], mats)
P["KIT_MAYA_FLOOR_UPPER_STAIRWELL_A"]=new("KIT_MAYA_FLOOR_UPPER_STAIRWELL_A"); out["KIT_MAYA_FLOOR_UPPER_STAIRWELL_A"]=g['build_maya_floor_stairwell'](P["KIT_MAYA_FLOOR_UPPER_STAIRWELL_A"], mats)
P["KIT_MAYA_STAIR_A"]=new("KIT_MAYA_STAIR_A"); out["KIT_MAYA_STAIR_A"]=g['build_maya_stair'](P["KIT_MAYA_STAIR_A"], mats)
for n,(src,cap) in g['MAYA_CORNERS'].items():
    P[n]=new(n); out[n]=g['maya_corner'](P[n], P[src], mats, cap_top=cap)
P["KIT_MAYA_ROOF_DECK_A"]=new("KIT_MAYA_ROOF_DECK_A"); out["KIT_MAYA_ROOF_DECK_A"]=g['build_maya_deck'](P["KIT_MAYA_ROOF_DECK_A"], mats)
for n,ob in P.items(): g['rebase_origin'](ob)
summ={n:{k:v for k,v in r.items() if (k.endswith('_bad') and v) or k in ('faces','sides')} for n,r in out.items()}
# lay the kit out in a row
for i,(n,ob) in enumerate(P.items()):
    ob.location=(i%6*5.5, -12-(i//6)*6, 0)
# weld test: 8 x 4 room, 2 storeys + parapet
def M(x,y,z,r): return Matrix.Translation((x,y,z))@Matrix.Rotation(math.radians(r),4,'Z')
def ring(z, S_, N_, E_, W_, C):
    return [(S_[0],M(0,0,z,0)),(S_[1],M(4,0,z,0)),(N_[0],M(8,4,z,180)),(N_[1],M(4,4,z,180)),(E_,M(8,0,z,90)),(W_,M(0,4,z,270))]+[(C,M(x,y,z,r)) for x,y,r in ((0,0,0),(8,0,90),(8,4,180),(0,4,270))]
gr=ring(0,("KIT_MAYA_WALL_DOOR_A","KIT_MAYA_WALL_WINDOW_A"),("KIT_MAYA_WALL_WINDOW_TWIN_A","KIT_MAYA_WALL_PLAIN_CRACKED_A"),"KIT_MAYA_WALL_NICHE_A","KIT_MAYA_WALL_PLAIN_A","KIT_MAYA_WALL_CORNER_A")
up=ring(3,("KIT_MAYA_WALL_UPPER_WINDOW_TWIN_A","KIT_MAYA_WALL_UPPER_WINDOW_A"),("KIT_MAYA_WALL_UPPER_PLAIN_A","KIT_MAYA_WALL_UPPER_CRACKED_A"),"KIT_MAYA_WALL_UPPER_WINDOW_A","KIT_MAYA_WALL_UPPER_PLAIN_A","KIT_MAYA_WALL_CORNER_UPPER_A")
pa=ring(6,("KIT_MAYA_PARAPET_SPOUT_A","KIT_MAYA_PARAPET_FRIEZE_A"),("KIT_MAYA_PARAPET_A","KIT_MAYA_PARAPET_SPOUT_A"),"KIT_MAYA_PARAPET_FRIEZE_A","KIT_MAYA_PARAPET_A","KIT_MAYA_PARAPET_CORNER_A")
fl=[("KIT_MAYA_FLOOR_GROUND_A",M(0,0,0,0)),("KIT_MAYA_FLOOR_GROUND_A",M(4,0,0,0)),("KIT_MAYA_FLOOR_UPPER_A",M(0,0,0,0)),("KIT_MAYA_FLOOR_UPPER_A",M(4,0,0,0)),
    ("KIT_MAYA_STEP_A",M(0,0,0,0))]
dk=[("KIT_MAYA_ROOF_DECK_A",M(0,0,3,0)),("KIT_MAYA_ROOF_DECK_A",M(4,0,3,0))]
def weld(pl):
    bm=bmesh.new()
    for n,Mx in pl:
        me=P[n].data.copy(); me.transform(Mx); bm.from_mesh(me); bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    b=[e for e in bm.edges if e.is_boundary]; nm=[e for e in bm.edges if len(e.link_faces)>2]
    loc=lambda es: sorted({(round((e.verts[0].co.x+e.verts[1].co.x)/2,1),round((e.verts[0].co.y+e.verts[1].co.y)/2,1),round((e.verts[0].co.z+e.verts[1].co.z)/2,2)) for e in es})
    r={'open':len(b),'open_z':sorted({x[2] for x in loc(b)})[:12],'nonmanifold':len(nm),'nm_at':loc(nm)[:10],'faces':len(bm.faces)}
    bm.free(); return r
wt={'house+floors':weld(gr+up+pa+dk+fl),'floors_only':weld(fl[:4]),'ground':weld(gr),'2storey':weld(gr+up),'2storey+parapet':weld(gr+up+pa),'1storey+parapet':weld(gr+[(n,M(0,0,-3,0)@m) for n,m in pa])}
# house for renders
hc=bpy.data.collections.new("TEST_HOUSE"); bpy.context.scene.collection.children.link(hc)
for n,Mx in gr+up+pa+dk+fl:
    o=bpy.data.objects.new(n+"_h",P[n].data); hc.objects.link(o); o.matrix_world=Matrix.Translation((0,20,0))@Mx
# asset catalogs: Maya/{WALLS,FLOORS,ROOFS,STRUCTS} in kit/blender_assets.cats.txt (mirrors Kit/*)
MAYA_CATS={"WALLS":"3081a433-c6c5-4d0f-8b51-03c4f9f29e52","FLOORS":"0970c342-c8aa-4c0f-a15d-1c5761ccf0a3",
    "ROOFS":"e3c8fec1-3d14-4174-afbb-c8c696eee9ac","STRUCTS":"fafaf0a5-8407-4291-b497-038794104d2a"}
for n,ob in P.items():
    ob.asset_mark()
    ob.asset_data.catalog_id=MAYA_CATS["WALLS" if "_WALL_" in n else "FLOORS" if "_FLOOR_" in n
        else "ROOFS" if ("_PARAPET_" in n or "_ROOF_" in n) else "STRUCTS"]
    ob.asset_data.use_preferred_import_method=True; ob.asset_data.preferred_import_method='APPEND'
    ob.asset_data.description={"FLOOR":"4x4 m room floor tile, origin = inner room corner; open sides weld to neighbours",
        "DECK":"flat roof slab of the top storey (place with the top storey's matrix): flagstones on top, beamed ceiling below",
        "PARAPET":"parapet run on top of the top storey (cornice, parapet wall, coping)",
        "CORNER":"outer corner, origin = inner corner; mitre of the matching bay's end loop",
        "STEP":"stone step in front of a door bay; place with the door bay's matrix"}.get(next((k for k in ("FLOOR","DECK","PARAPET","CORNER","STEP") if k in n),""),
        "4 m wall bay, 3 m storey; origin = inside face, left end. Any bay of a storey welds to any other (Merge by Distance 1 mm)")
if "SAVE" in ARGS:
    bpy.ops.wm.save_as_mainfile(filepath=OUTBLEND)
print("M_JSON "+json.dumps({"pieces":summ,"weld":wt}))
if "RENDER" in ARGS:
    sc=bpy.context.scene
    cam=bpy.data.objects.new("cam",bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera=cam
    sun=bpy.data.objects.new("sun",bpy.data.lights.new("sun",'SUN')); sc.collection.objects.link(sun); sun.rotation_euler=(math.radians(50),0,math.radians(-35)); sun.data.energy=4.0
    sc.render.engine='BLENDER_EEVEE' if 'BLENDER_EEVEE' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE_NEXT'
    w=bpy.data.worlds.new("w"); sc.world=w; w.use_nodes=True; w.node_tree.nodes["Background"].inputs[0].default_value=(0.55,0.62,0.75,1); w.node_tree.nodes["Background"].inputs[1].default_value=0.9
    sc.view_settings.view_transform='AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    gp=bpy.data.objects.new("ground",bpy.data.meshes.new("ground")); sc.collection.objects.link(gp)
    import bmesh as _b; _bm=_b.new(); _b.ops.create_grid(_bm,x_segments=1,y_segments=1,size=40); _bm.to_mesh(gp.data); gp.location=(4,20,-0.001)
    gp.data.materials.append(g['ensure_material']("NW_Seq_Maya_Ground_02"))
    sc.render.resolution_x, sc.render.resolution_y = 1500, 1000
    def look(n,loc,tgt,lens=35):
        cam.location=loc; d=Vector(tgt)-Vector(loc); cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler(); cam.data.lens=lens
        sc.render.filepath=SCR+f"maya_{n}.png"; bpy.ops.render.render(write_still=True)
    look("house_a",(-8,7,6),(4,22,3.6),30)
    look("house_b",(15,33,7),(4,22,3.4),30)
    look("door",(2.2,14.5,1.8),(2.2,20,1.7),35)
    look("kit",(14,-40,16),(14,-15,1),30)
    look("crack",(3.6,28.6,1.9),(2.0,24.3,1.3),35)
    look("niche",(11.5,21.5,1.8),(8.3,22.0,1.7),35)
    look("spout",(-3.5,15.5,7.0),(2.0,19.7,6.3),30)
    look("inside",(6.9,23.2,1.5),(1.0,20.5,2.4),24)
