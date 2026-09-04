"""Runs INSIDE Blender's own Python (bpy), not with the repo's interpreter.

Invoked by step_convert.py as:

    blender -b --python py/blender_convert_headless.py -- \
        --in <model.gltf|.glb|.obj> --obj-out <model.obj> --preview-out <preview.png>

Migrated from blender_convert.py in the sketchfab_fdo_prototype (neighbouring
chat). First run against real Blender (5.2.1 LTS, Windows) on 2026-09-04:
import, export and render all completed, but every texture was silently
dropped (see relink_images() below for why and the fix) -- worth knowing if
you diff this file against an even older copy floating around a chat.

Imports the model (glTF/GLB via bpy.ops.import_scene.gltf, OBJ via
bpy.ops.wm.obj_import), exports OBJ+MTL with copied textures
(path_mode="COPY", for nxsbuild in S4), then renders a fixed-camera,
three-point-lit preview.png. step_convert.py handles everything downstream
of this (moving copied textures into textures/, rewriting the .mtl).

Determinism: render sample count and camera/light placement are derived
only from the mesh's own bounding box (no randomness, no datetime), so
preview.png *should* render identically for the same input across runs on
the same machine/Blender version/GPU driver -- not yet checked with an
actual two-run comparison though (this chat's sandbox has no Blender to
run it with; PRIMER.md S3 records this as still open).
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


def relink_images(model_dir: Path) -> None:
    """Re-point every image datablock at the real file under model_dir.

    Befund 2026-09-04 (first real run, Blender 5.2.1 LTS): the glTF
    importer's relative image paths ("textures/foo.jpeg") get resolved
    against bpy.data.filepath -- the *current .blend file's* location, via
    Blender's "//" convention -- not against the imported .gltf's own
    directory. Since this script never saves a .blend file, that base
    directory does not exist, and Blender falls back to something useless
    (observed: the OS drive root, e.g. "C:\\foo.jpeg", silently dropping the
    "textures/" subfolder). The OBJ exporter's path_mode="COPY" then reports
    "Missing source file" and skips every texture -- the model exports but
    ends up untextured, which is also why the preview render came out
    almost black (materials with no base colour).

    Fixed by matching on filename against everything under model_dir (the
    directory step_fetch.py/S2 already collected the model's sibling files
    into) rather than trusting whatever path Blender computed.

    Nachtrag 2026-09-04: after a real run, this had *zero* measurable
    effect (identical preview.png, byte-for-byte, before and after this
    function was added) -- so whatever is going wrong is not simply "wrong
    path, otherwise normal datablock". Printing diagnostics below rather
    than guessing again; step_convert.py (S3, Python side) now does its own
    texture copy independent of this function and of Blender's OBJ-export
    COPY mechanism entirely, so the *exported package* no longer depends on
    this working -- but the *preview render* still does, since that needs
    real pixel data loaded into `bpy.data.images`, not just a correct
    filename in a .mtl.
    """
    by_name = {p.name: p for p in model_dir.rglob("*") if p.is_file()}
    print(f"[relink_images] model_dir={model_dir} candidate files={len(by_name)}")
    relinked = 0
    for image in bpy.data.images:
        name = Path(image.filepath or image.name).name
        match = by_name.get(name)
        print(
            f"[relink_images] image.name={image.name!r} image.filepath={image.filepath!r} "
            f"source={image.source!r} lookup_key={name!r} -> {'MATCH ' + str(match) if match else 'no match'}"
        )
        if not match:
            continue
        resolved = str(match)
        image.filepath = resolved
        image.filepath_raw = resolved
        try:
            image.reload()
            relinked += 1
        except RuntimeError as exc:
            print(f"[relink_images] reload() failed for {image.name!r}: {exc}")
    print(f"[relink_images] relinked {relinked}/{len(bpy.data.images)} image datablock(s)")


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
    relink_images(Path(in_path).resolve().parent)

    # OBJ export: path_mode="STRIP" only asks Blender to declare which
    # texture *name* belongs to which material -- not to copy any bytes.
    # Nachtrag 2026-09-04: path_mode="COPY" turned out unreliable here (see
    # relink_images() above); step_convert.py now does the actual texture
    # copy itself afterwards, from data/raw/<slug>/ (which S2 already
    # guarantees is complete) rather than trusting Blender's own copy.
    bpy.ops.wm.obj_export(
        filepath=obj_out,
        export_selected_objects=False,
        export_materials=True,
        path_mode="STRIP",
    )

    if preview_out:
        center, radius = mesh_bounds()
        setup_camera_and_lights(center, radius)
        render_preview(preview_out)


if __name__ == "__main__":
    main()
