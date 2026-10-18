"""Josh face textures (GatorCampus 64) - FINAL set.

Josh is Anh's face on a browner skin, so this folder holds Anh's final face art
(art/anh/textures/make_textures.py, unchanged) re-skinned with Josh's colours:
skin, skin_shadow (the lower-lid / half-lid crease lines) and hair (the dead-eye
X) come from art/josh/character.json, and Anh's three lip colours are scaled per
channel to Josh's skin.  Eye colours (lashes, iris, pupil, sclera, glint) and
every pixel position are Anh's.

Why a re-skinned copy instead of Anh's PNGs: the builder keys the flat border
(Anh's #E4AE8E) to alpha 0 either way, but Anh's crease texels are drawn in
Anh's skin_shadow (#CB9476), which the builder only recognises (and darkens)
when it equals the building character's skin_shadow.  On Josh they stayed
opaque and unlit: a pale line under every eye and a pink, light-skin mouth.

Donald (based_on josh, same skin / skin_shadow / hair) uses this set too.

Regenerate (writes the PNGs + previews next to this script, then re-checks them
with Anh's independent verifier):
    tools/.venv/bin/python -I make_textures.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, '..', 'character.json')
ANH = os.path.join(HERE, '..', '..', 'anh', 'textures')


def main():
    subprocess.run([sys.executable, '-I', os.path.join(ANH, 'make_textures.py'),
                    '--spec', SPEC, '--out', HERE], check=True)
    subprocess.run([sys.executable, '-I', os.path.join(ANH, 'verify_textures.py'),
                    HERE, '--spec', SPEC], check=True)


if __name__ == '__main__':
    main()
