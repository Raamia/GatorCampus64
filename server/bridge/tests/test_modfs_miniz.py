"""The inbox archive read back by coopdx's own zip reader (miniz from the v1.5.1 source tree).

Needs a C compiler and the sm64coopdx v1.5.1 source (SM64COOPDX_SRC, default /tmp/sm64coopdx);
skipped otherwise. This checks the zip layer only; a live mod_fs_reload() test needs the game.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from sglbridge.inbox import Inbox

SRC = Path(os.environ.get("SM64COOPDX_SRC", "/tmp/sm64coopdx"))
MINIZ = SRC / "src/pc/utils/miniz"
CC = shutil.which("cc") or shutil.which("gcc")


@pytest.mark.skipif(not (MINIZ / "miniz.c").exists() or CC is None, reason="no coopdx source / C compiler")
def test_miniz_reads_inbox(tmp_path):
    exe = tmp_path / "modfs_check"
    subprocess.run([CC, "-O1", "-w", "-I", str(MINIZ), str(Path(__file__).with_name("modfs_check.c")),
                    str(MINIZ / "miniz.c"), "-o", str(exe)], check=True)
    inbox = Inbox(tmp_path / "sav" / "sgl64.modfs")
    inbox.push("announce", text="New gator café arrives", secs=60)
    out = subprocess.run([str(exe), str(inbox.path)], capture_output=True, check=True, text=True).stdout
    head, file_line = out.rstrip("\n").split("\nFILE ", 1)
    props = json.loads(head.removeprefix("PROPERTIES "))
    assert props["files"]["inbox.json"]["isText"] is True
    name, size, text, body = file_line.split(" ", 3)
    assert name == "inbox.json" and text == "1" and int(size) == len(body)
    assert json.loads(body)["cmds"][0]["text"] == "New gator café arrives"
