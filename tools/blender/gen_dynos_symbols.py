"""Regenerate dynos_symbols_v1.5.1.json (used by validate_level.py) from sm64coopdx sources.

Usage: python3 gen_dynos_symbols.py <coopdx_src_dir> [out.json]
<coopdx_src_dir> needs data/dynos_bin_{lvl,geo,gfx,col,common,macro_object}.cpp,
data/dynos_mgr_builtin.cpp and include/gfx_symbols.h of the coopdx version the game runs
(raw files from https://github.com/coop-deluxe/sm64coopdx/tree/v1.5.1). The tables are the
names DynOS resolves itself when it compiles levels/<name>/*.c into a .lvl.
"""
import json
import os
import re
import sys


def main():
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                             "dynos_symbols_v1.5.1.json")

    def rd(p):
        p2 = os.path.join(src, p)
        if not os.path.exists(p2):  # include/gfx_symbols.h may sit next to the data/ files
            p2 = os.path.join(src, os.path.basename(p))
        return open(p2, encoding="utf-8", errors="replace").read()

    def grab(pat, text):
        return sorted(set(re.findall(pat, text)))

    lvl, geo, gfx = rd("data/dynos_bin_lvl.cpp"), rd("data/dynos_bin_geo.cpp"), rd("data/dynos_bin_gfx.cpp")
    col, com, mac = rd("data/dynos_bin_col.cpp"), rd("data/dynos_bin_common.cpp"), rd("data/dynos_bin_macro_object.cpp")
    bi, gs = rd("data/dynos_mgr_builtin.cpp"), rd("include/gfx_symbols.h")
    data = {
        "source": "sm64coopdx v1.5.1 data/dynos_*.cpp, include/gfx_symbols.h",
        "lvl_constants": grab(r"lvl_constant\((\w+)\)", lvl) + grab(r"lvl_legacy_constant\((\w+),", lvl),
        "geo_constants": grab(r"geo_constant\(([^)]+)\)", geo),
        "gfx_constants": grab(r"gfx_constant\(([^)]+)\)", gfx) + grab(r"gfx_set_combine_mode_arg\((\w+)\)", gfx),
        "col_constants": grab(r"col_constant\((\w+)\)", col),
        "macro_constants": grab(r"macro_object_constant\((\w+)\)", mac) + grab(r"\b(macro_\w+)\b", mac),
        "bhv_constants": grab(r"(?:bhv|common)_constant\((\w+)\)", com) + grab(r"\"(bhv\w+)\"", com),
        "builtin_functions": grab(r"define_builtin_function\((\w+),", bi),
        "builtin_names": grab(r"define_builtin(?:_ptr)?\((\w+)\)", bi),
        "gfx_symbols": grab(r"define_gfx_symbol(?:_manual)?\((\w+)", gs),
    }
    with open(out, "w") as f:
        json.dump(data, f, indent=0, sort_keys=True)
    for k, v in data.items():
        if isinstance(v, list):
            print(f"{k}: {len(v)}")


if __name__ == "__main__":
    main()
