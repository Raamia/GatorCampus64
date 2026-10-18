"""Generate the ride gator: a saddled alligator that replaces SM64's Koopa shell, as a coopdx DynOS actor.

DynOS matches the vanilla `koopa_shell_geo` layout symbol, so every rideable shell (the three on the Reitz stage
and any a Koopa drops) is drawn as this gator while `bhvKoopaShell` keeps the ride: jump on it to ride, Z to get
off, it floats on water and burns over lava. mods/sgl64/sgl_ride_gator.lua stops the shell's idle spin so the
gator rests facing its spawn yaw (with a lazy head sway) instead of spinning like a top.

Units are game units (1 = 1 cm), +Y up, the snout faces +Z (the shell copies the rider's move yaw). The shell's
hitbox is 50 wide and 50 high and Mario's riding animation stands him on top of it, so the back (the orange
saddle blanket where he stands) peaks near y = 38 over the origin; the snout and tail reach out past the hitbox.

Usage: python3 -I tools/actors/make_ride_gator.py [--out DIR]
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_gators as G  # noqa: E402

ROOT = G.ROOT
OUT = os.path.join(ROOT, "mods", "sgl64", "actors", "koopa_shell")
NAME = "sgl_ride_gator"

G.COLORS.update({
    "claw": (235, 228, 205),
})

BODY_C, BODY_R = (0, 21, -6), (29, 17, 46)   # the belly-down torso; its top (y 38) is where the rider stands


def build_body(m):
    m.ball("skin", BODY_C, BODY_R, seg=12, rings=8)
    m.ball("belly", (0, 12, -6), (25, 9, 42), seg=12, rings=5)   # pale underside showing along the flanks
    # the saddle blanket: UF orange draped over the middle of the back, a blue rim showing past its edges
    m.ball("blue", BODY_C, (30.2, 18.0, 35), seg=12, rings=6)
    m.ball("jersey", BODY_C, (30.8, 18.6, 31), seg=12, rings=6)
    # a girth strap under the belly, blue
    m.box("blue", -22, 22, 3.5, 6, -10, -2)


def build_head(m):
    # skull and neck
    m.ball("skin", (0, 22, 40), (22, 14, 20), seg=10, rings=6)
    # upper snout: long and flat, tapering to the nose
    m.zbar("skin", 44, 88, (-18, 18, 13, 27), (-11, 11, 14, 22))
    m.ball("skin", (0, 18, 88), (11, 5, 6))
    # lower jaw (pale) under the snout, and a red mouth line between them
    m.zbar("belly", 38, 86, (-17, 17, 6, 13.5), (-10, 10, 9, 14))
    m.box("mouth", -15, 15, 13.4, 14.2, 46, 82)
    # nostrils on top of the nose
    for s in (-1, 1):
        m.box("black", 4.5 * s - 1.8, 4.5 * s + 1.8, 22.6, 23.6, 80, 85)
    # brows and big cartoon eyes on top of the head (they peek over the snout at the rider and the camera)
    for s in (-1, 1):
        ex = 10 * s
        m.box("skin_dark", ex - 8, ex + 8, 32, 36, 36, 46)
        m.ball("white", (ex, 36, 45), (7, 7.5, 6))
        m.ball("black", (ex + 1.2 * s, 36.5, 50.2), (3, 3.6, 1.6))
    # the grin: upper teeth down both sides of the snout
    for s in (-1, 1):
        for k in range(5):
            z = 50 + 8 * k
            x = (17 - 6 * (z - 44) / 44) * s
            m.pyramid("white", [(x - 1.4, 14, z - 1.8), (x + 1.4, 14, z - 1.8), (x + 1.4, 14, z + 1.8),
                                (x - 1.4, 14, z + 1.8)], (x, 9.5, z))


def build_tail(m):
    """Tapering segments from the hips to the tip, each with a dark scute on top."""
    rings = [(-44, 14, 6, 30), (-62, 11, 7, 26), (-80, 8, 8, 22), (-96, 5, 8.5, 18), (-110, 2, 9, 14)]
    for (z0, w0, b0, t0), (z1, w1, b1, t1) in zip(rings, rings[1:]):
        m.zbar("skin", z0 + 2, z1, (-w0, w0, b0, t0), (-w1, w1, b1, t1))
        zc, top = (z0 + z1) / 2, (t0 + t1) / 2
        m.pyramid("skin_dark", [(-2.5, top - 1, zc - 4), (2.5, top - 1, zc - 4), (2.5, top - 1, zc + 4),
                                (-2.5, top - 1, zc + 4)], (0, top + 5, zc))


def build_scutes(m):
    """Two rows of ridges down the back, ahead of and behind the saddle (never under the rider's feet)."""
    for z in (26, 34, -34, -41):
        y = math.sqrt(max(0.0, 1 - ((z - BODY_C[2]) / BODY_R[2]) ** 2)) * BODY_R[1] + BODY_C[1]
        for x in (-8, 8):
            m.pyramid("skin_dark", [(x - 2.5, y - 2, z - 3), (x + 2.5, y - 2, z - 3), (x + 2.5, y - 2, z + 3),
                                    (x - 2.5, y - 2, z + 3)], (x, y + 4, z))


def build_legs(m):
    """Four stubby legs splayed out to the sides, feet flat on the ground with pale claws."""
    for s in (-1, 1):
        for z in (20, -30):
            m.box("skin", 22 * s - 6, 22 * s + 6, 8, 20, z - 7, z + 7)        # upper leg out of the flank
            m.box("skin", 33 * s - 5, 33 * s + 5, 2, 14, z - 6, z + 6)        # lower leg down to the foot
            m.box("skin_dark", 33 * s - 8, 33 * s + 8, 0, 3, z - 6, z + 10)   # foot
            for k in (-1, 0, 1):
                x = 33 * s + 5 * k
                m.pyramid("claw", [(x - 1.5, 0, z + 9), (x + 1.5, 0, z + 9), (x + 1.5, 2.5, z + 9),
                                   (x - 1.5, 2.5, z + 9)], (x, 0.5, z + 14))


def build_mesh():
    mesh = G.Mesh()
    build_body(mesh)
    build_head(mesh)
    build_tail(mesh)
    build_scutes(mesh)
    build_legs(mesh)
    return mesh


def build():
    mesh = build_mesh()
    vtx, dls, used = [], [], set()
    top = G.emit_mesh(NAME, mesh, "gator", vtx, dls, used)
    model = "// GENERATED by tools/actors/make_ride_gator.py. Do not edit; edit the script and re-run it.\n\n"
    model += "\n".join(G.materials(NAME, used)) + "\n" + "\n".join(vtx) + "\n" + "\n".join(dls)
    model = "\n".join(line.rstrip() for line in model.splitlines()) + "\n"
    geo = ("// GENERATED by tools/actors/make_ride_gator.py. Do not edit; edit the script and re-run it.\n\n"
           "// Replaces the vanilla Koopa shell appearance; bhvKoopaShell (the ride) is unchanged.\n"
           "const GeoLayout koopa_shell_geo[] = {\n"
           "\tGEO_SHADOW(SHADOW_CIRCLE_4_VERTS, 0xC8, 110),\n"
           "\tGEO_OPEN_NODE(),\n"
           "\t\tGEO_DISPLAY_LIST(LAYER_OPAQUE, %s),\n"
           "\tGEO_CLOSE_NODE(),\n"
           "\tGEO_END(),\n"
           "};\n") % top
    header = ["extern const GeoLayout koopa_shell_geo[];"]
    for mat in sorted(used):
        header += ["extern Lights1 %s_%s_lights;" % (NAME, mat),
                   "extern Gfx mat_%s_%s[];" % (NAME, mat),
                   "extern Gfx mat_revert_%s_%s[];" % (NAME, mat)]
    header += ["extern " + chunk.split(" = ")[0] + ";" for chunk in vtx + dls]
    triangles = sum(len(tris) for tris in mesh.tris.values())
    return model, geo, "\n".join(header) + "\n", triangles, mesh


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=OUT, help="actor folder (default mods/sgl64/actors/koopa_shell)")
    args = parser.parse_args(argv)
    model, geo, header, triangles, _ = build()
    os.makedirs(args.out, exist_ok=True)
    for filename, text in (("model.inc.c", model), ("geo.inc.c", geo), ("geo_header.h", header)):
        with open(os.path.join(args.out, filename), "w") as output:
            output.write(text)
    print("make_ride_gator: %d triangles -> %s (koopa_shell_geo)" % (triangles, os.path.relpath(args.out, ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
