"""Josh: Anh's head (round face, straight black mushroom cut with side-swept bangs,
thick black rectangular glasses) on a browner skin, plain black t-shirt, dark jeans,
white sneakers. Donald (based_on josh) inherits this module: Josh without glasses.

Everything of Anh's comes from characters/anh.py, re-exported below. Its pieces are
gated on the spec being built, so Josh gets the glasses (his build.accessories lists
glasses_thick_rectangular), Donald gets no glasses, and neither gets the jersey
stripes / number / socks. Face art: art/josh/textures (Anh's art re-skinned with Josh's
colours, see make_textures.py there); Donald uses it through based_on.

The plain tee's sleeve end is the shared short-sleeve cut (sgl_body.short_sleeve_ends:
the sleeve ends at the same fraction of the upper arm as Anh's jersey sleeve, the end cap
past the elbow becomes skin), which Josh's and Donald's tees were first built with here.
"""
import sgl_characters

_anh = sgl_characters._module_for("anh")

HAIR_STYLE = _anh.HAIR_STYLE
ACCESSORIES = _anh.ACCESSORIES
head_parts = _anh.head_parts
head_roles = _anh.head_roles
