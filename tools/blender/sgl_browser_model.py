"""Export a static posed character for browser orbit previews.

Uses the same F3D palette, face images, tile scaling and hidden-wing rules as
sgl_preview. Browser PBR lighting approximates the game's camera-space shading;
the geometry and textures come directly from the generated character.
Only temporary copies are changed, so the saved game actor remains untouched.
"""
import os

import bpy
import bmesh

import sgl_preview


def _linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _material(source, images):
    col, amb, image, texel_unlit, scale = sgl_preview._f3d_info(source)
    # PBR viewers provide the directional light; include the material's ambient
    # contribution in its base colour rather than dropping it entirely.
    colour = tuple(_linear(min(1.0, a + c * 0.7)) for a, c in zip(amb, col))
    mat = bpy.data.materials.new("Browser " + source.name)
    mat.use_nodes = True
    mat.diffuse_color = (*colour, 1)
    mat.use_backface_culling = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*colour, 1)
    bsdf.inputs["Roughness"].default_value = 1
    bsdf.inputs["Metallic"].default_value = 0
    if image is not None:
        # glTF cannot represent the F3D face combiner. Flatten the alpha-backed
        # facial features onto skin, retaining an opaque face in every viewer.
        texture = image.copy()
        images.append(texture)
        texture.name = "Browser " + image.name
        pixels = list(image.pixels[:])
        for i in range(0, len(pixels), 4):
            alpha = pixels[i + 3]
            for channel in range(3):
                pixels[i + channel] = (pixels[i + channel] * alpha + colour[channel] * (1 - alpha)
                                       if texel_unlit else pixels[i + channel] * colour[channel])
            pixels[i + 3] = 1
        texture.pixels[:] = pixels
        texture.pack()
        node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = texture
        node.interpolation = "Linear"
        node.extension = "EXTEND"
        mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    return mat, scale


def export_browser_model(path, armature="Mario", mesh="Mario Mesh"):
    """Export only the evaluated normal body (no rigs, metal variants or wings)."""
    arm = bpy.data.objects[armature]
    body = bpy.data.objects[mesh]
    scene = bpy.context.scene
    frame = scene.frame_current
    had_animation = arm.animation_data is not None
    action = arm.animation_data.action if had_animation else None
    selected = list(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    temporary = None
    data = None
    materials, images = [], []
    try:
        pose = bpy.data.actions.get(sgl_preview.PREVIEW_ACTION)
        if pose is not None:
            arm.animation_data_create()
            arm.animation_data.action = pose
        scene.frame_set(0)
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        data = bpy.data.meshes.new_from_object(evaluated)
        temporary = bpy.data.objects.new("Character", data)
        scene.collection.objects.link(temporary)
        temporary.matrix_world = body.matrix_world.copy()
        hidden = {i for i, slot in enumerate(body.material_slots)
                  if slot.material and slot.material.name in sgl_preview.HIDDEN_IN_PREVIEW}
        bm = bmesh.new()
        try:
            bm.from_mesh(data)
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in hidden], context="FACES")
            bm.to_mesh(data)
        finally:
            bm.free()
        scales = {}
        data.materials.clear()
        for i, slot in enumerate(body.material_slots):
            if slot.material is None:
                fallback = bpy.data.materials.new("Browser Empty")
                materials.append(fallback)
                data.materials.append(fallback)
                continue
            material, scales[i] = _material(slot.material, images)
            materials.append(material)
            data.materials.append(material)
        if data.uv_layers.active:
            uv = data.uv_layers.active.data
            for poly in data.polygons:
                sx, sy = scales.get(poly.material_index, (1, 1))
                for loop in poly.loop_indices:
                    u, v = uv[loop].uv
                    uv[loop].uv = (u * sx, 1 - (1 - v) * sy)
        bpy.ops.object.select_all(action="DESELECT")
        temporary.select_set(True)
        bpy.context.view_layer.objects.active = temporary
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        result = bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                                           export_animations=False, export_cameras=False,
                                           export_lights=False, export_yup=True)
        if "FINISHED" not in result or not os.path.isfile(path):
            raise RuntimeError("browser GLB export did not finish")
        return path
    finally:
        if temporary is not None:
            bpy.data.objects.remove(temporary, do_unlink=True)
        if data is not None:
            bpy.data.meshes.remove(data)
        for material in materials:
            bpy.data.materials.remove(material)
        for image in images:
            bpy.data.images.remove(image)
        if had_animation:
            arm.animation_data.action = action
        else:
            arm.animation_data_clear()
        scene.frame_set(frame)
        bpy.ops.object.select_all(action="DESELECT")
        for obj in selected:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active
