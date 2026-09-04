"""Runs INSIDE Blender's own Python (bpy), not with the repo's interpreter.

Invoked by step_convert.py as:

    blender -b --python py/blender_convert_headless.py -- \
        --in <model.gltf|.glb|.obj> --obj-out <model.obj> --preview-out <preview.png>

Migrated from blender_convert.py in the sketchfab_fdo_prototype (neighbouring
chat), which itself was never run against a real Blender in a chat sandbox
(no Blender available there either) -- so while this mirrors Blender's
documented operator API as closely as the prototype did, the first real
execution against actual Blender is still an open verification step for the
person running it locally (see PRIMER.md S3).

Imports the model (glTF/GLB via bpy.ops.import_scene.gltf, OBJ via
bpy.ops.wm.obj_import), exports OBJ+MTL with copied textures
(path_mode="COPY", for nxsbuild in S4), then renders a fixed-camera,
three-point-lit preview.png. step_convert.py handles everything downstream
of this (moving copied textures into textures/, rewriting the .mtl).

Determinism: render sample count and camera/light placement are derived
only from the mesh's own bounding box (no randomness, no datetime), so
preview.png *should* render identically for the same input across runs on
the same machine/Blender version/GPU driver -- but this could not be
verified without a real Blender, so treat it as a working assumption, not a
proven guarantee, until checked against a real two-run comparison (PRIMER.md
S3 Abnahme).
"""
import math
import sys
from pathlib import Path

import bpy
import mathutils

MODEL_SUFFIXES = {".gltf", ".glb", ".obj"}


def parse_args() -> dict:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    args, key = {}, None
    for a in argv:
        if a.startswith("--"):
            key = a[2:]
            args[key] = True
        elif key:
            args[key] = a
            key = None
    return args


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_model(path: str) -> None:
    suffix = Path(path).suffix.lower()
    if suffix in (".gltf", ".glb"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif suffix == ".obj":
        # Blender 3.4+/4.x importer; ancient versions used
        # bpy.ops.import_scene.obj instead.
        bpy.ops.wm.obj_import(filepath=path)
    else:
        raise ValueError(
            f"Unsupported input format: {suffix} (expected one of {sorted(MODEL_SUFFIXES)})"
        )


def mesh_bounds() -> tuple[mathutils.Vector, float]:
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("No mesh found after model import")
    mins = mathutils.Vector((math.inf, math.inf, math.inf))
    maxs = mathutils.Vector((-math.inf, -math.inf, -math.inf))
    for obj in meshes:
        for corner in obj.bound_box:
            world_co = obj.matrix_world @ mathutils.Vector(corner)
            mins = mathutils.Vector(min(a, b) for a, b in zip(mins, world_co))
            maxs = mathutils.Vector(max(a, b) for a, b in zip(maxs, world_co))
    center = (mins + maxs) / 2
    radius = max((maxs - mins).length / 2, 0.1)
    return center, radius


def setup_camera_and_lights(center: mathutils.Vector, radius: float) -> None:
    target = bpy.data.objects.new("preview_target", None)
    target.location = center
    bpy.context.collection.objects.link(target)

    cam_data = bpy.data.cameras.new("preview_cam")
    cam = bpy.data.objects.new("preview_cam", cam_data)
    cam.location = center + mathutils.Vector((radius * 1.8, -radius * 1.8, radius * 1.2))
    bpy.context.collection.objects.link(cam)
    constraint = cam.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    bpy.context.scene.camera = cam

    # Fixed three-point setup, purely a function of the mesh's own bounding
    # box -- no randomness, so this stays a deterministic function of the
    # model, not the run (see module docstring for the caveat on rendering).
    lights = [
        ("key", center + mathutils.Vector((radius * 2, -radius * 2, radius * 2)), 1200),
        ("fill", center + mathutils.Vector((-radius * 2, -radius * 1, radius * 1.5)), 500),
        ("rim", center + mathutils.Vector((0, radius * 2.5, radius * 1)), 700),
    ]
    for name, loc, energy in lights:
        light_data = bpy.data.lights.new(name, type="AREA")
        light_data.energy = energy
        light_data.size = radius
        light_obj = bpy.data.objects.new(name, light_data)
        light_obj.location = loc
        constraint = light_obj.constraints.new(type="TRACK_TO")
        constraint.target = target
        constraint.track_axis = "TRACK_NEGATIVE_Z"
        constraint.up_axis = "UP_Y"
        bpy.context.collection.objects.link(light_obj)


def render_preview(preview_out: str) -> None:
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"  # Blender 4.2+
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    # Fixed sample count, no denoiser -- deterministic given a fixed engine
    # version/GPU, see module docstring.
    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 64
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.filepath = preview_out
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    in_path = args["in"]
    obj_out = args["obj-out"]
    preview_out = args.get("preview-out")

    clear_scene()
    import_model(in_path)

    # OBJ export with texture copy, for nxsbuild (S4). step_convert.py moves
    # whatever lands next to model.obj into textures/ and rewrites the .mtl
    # (PRIMER.md A4: textures/ -> auxiliary role in classification_rules.yaml).
    bpy.ops.wm.obj_export(
        filepath=obj_out,
        export_selected_objects=False,
        export_materials=True,
        path_mode="COPY",
    )

    if preview_out:
        center, radius = mesh_bounds()
        setup_camera_and_lights(center, radius)
        render_preview(preview_out)


if __name__ == "__main__":
    main()
