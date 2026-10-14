# Regenerate every object asset's preview with Blender's DEFAULT preview generator
# (ID.asset_generate_preview -- what Mark as Asset / the Asset Browser use), one piece
# at a time. NOT wm.previews_batch_generate: that renders them dark.
# Run with the UI (previews need it), it saves and quits by itself:
#   Blender kit/KIT_WALLS.blend --python regen_previews.py
import bpy, sys

queue = [o.name for o in bpy.data.objects if o.asset_data is not None]
state = {"i": 0, "wait": 0}


def tick():
    if bpy.app.is_job_running('RENDER_PREVIEW'):
        return 0.2
    if state["i"] >= len(queue):
        if state["wait"] < 5:                      # let the last job finish writing
            state["wait"] += 1
            return 0.5
        bpy.ops.wm.save_mainfile()
        print("PREVIEWS_DONE", len(queue), bpy.data.filepath)
        sys.stdout.flush()
        bpy.ops.wm.quit_blender()
        return None
    ob = bpy.data.objects.get(queue[state["i"]])
    state["i"] += 1
    if ob is not None:
        ob.asset_generate_preview()
    return 0.3


bpy.app.timers.register(tick, first_interval=3.0)
