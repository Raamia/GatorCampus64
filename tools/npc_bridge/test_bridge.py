"""Offline tests for bridge.py: python3 -m unittest discover -s tools/npc_bridge"""
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge  # noqa: E402


def write_outbox(sav, text):
    """What sgl_npc.lua's mod_fs_save() leaves on disk: a zip with npc_out.txt (+ properties.json)."""
    with zipfile.ZipFile(os.path.join(sav, bridge.OUT_MODFS), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(bridge.OUT_FILE, text)
        z.writestr("properties.json", json.dumps({"isPublic": False, "files": {}}))


def read_inbox(sav):
    with zipfile.ZipFile(os.path.join(sav, bridge.IN_MODFS)) as z:
        return z.read(bridge.IN_FILE).decode(), json.loads(z.read("properties.json"))


class EchoReplier:
    def __init__(self):
        self.calls = []

    def reply(self, npc, player, message, history):
        self.calls.append((npc, player, message, list(history)))
        return "%s heard %s" % (npc, message)


class EscapeTest(unittest.TestCase):
    def test_round_trip(self):
        for s in ["plain", "tab\there", "line\nbreak", "back\\slash", "\\t literal", "mix\\\t\n"]:
            self.assertEqual(bridge.unescape(bridge.escape(s)), s)
        self.assertNotIn("\t", bridge.escape("a\tb"))
        self.assertNotIn("\n", bridge.escape("a\nb"))

    def test_clean_reply(self):
        self.assertEqual(bridge.clean_reply("“Hi” — **go** Gators!\n\U0001F40A"), '"Hi" - go Gators!')
        self.assertNotIn("\\", bridge.clean_reply("\\#ff0000\\red"))
        long = "Sentence one is here. " * 20
        out = bridge.clean_reply(long)
        self.assertLessEqual(len(out), bridge.MAX_REPLY)
        self.assertTrue(out.endswith("."))


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.sav = tempfile.mkdtemp()
        self.cast = {"npcs": {"albert": {"name": "Albert", "fake": ["Hi %s"]}}}
        self.echo = EchoReplier()
        self.b = bridge.Bridge(self.sav, self.echo, self.cast, log=lambda *_: None)

    def tearDown(self):
        shutil.rmtree(self.sav)

    def test_no_outbox_yet(self):
        self.assertEqual(self.b.poll(), 0)
        self.assertFalse(os.path.exists(os.path.join(self.sav, bridge.IN_MODFS)))

    def test_half_written_outbox_is_retried(self):
        with open(os.path.join(self.sav, bridge.OUT_MODFS), "wb") as f:
            f.write(b"PK\x03\x04 not a whole zip")
        self.assertEqual(self.b.poll(), 0)

    def test_answers_each_request_once(self):
        write_outbox(self.sav, "session\t42\n1\talbert\tPranav\thi there\n2\talbert\tSam\tgo\\tgators\n")
        self.assertEqual(self.b.poll(), 2)
        self.assertEqual(self.b.poll(), 0)
        text, props = read_inbox(self.sav)
        self.assertEqual(text, "session\t42\n1\talbert\talbert heard hi there\n2\talbert\talbert heard go gators\n")
        self.assertTrue(props["isPublic"])
        self.assertTrue(props["files"][bridge.IN_FILE]["isPublic"])
        self.assertEqual(self.echo.calls[1][2], "go\tgators")

    def test_new_session_starts_over(self):
        write_outbox(self.sav, "session\t1\n1\talbert\tP\tone\n")
        self.b.poll()
        write_outbox(self.sav, "session\t2\n1\talbert\tP\tagain\n")
        self.assertEqual(self.b.poll(), 1)
        text, _ = read_inbox(self.sav)
        self.assertEqual(text, "session\t2\n1\talbert\talbert heard again\n")

    def test_history_per_player_and_npc(self):
        write_outbox(self.sav, "session\t1\n1\talbert\tP\tfirst\n")
        self.b.poll()
        write_outbox(self.sav, "session\t1\n2\talbert\tP\tsecond\n3\talbert\tQ\tother\n")
        self.b.poll()
        self.assertEqual(self.echo.calls[1][3], [("user", "first"), ("model", "albert heard first")])
        self.assertEqual(self.echo.calls[2][3], [])

    def test_unknown_npc_and_failures_are_skipped(self):
        class Boom:
            def reply(self, *a):
                raise RuntimeError("offline")
        self.b.replier = Boom()
        write_outbox(self.sav, "session\t1\n1\tnobody\tP\thi\n2\talbert\tP\thi\n")
        self.assertEqual(self.b.poll(), 0)
        self.assertEqual(self.b.done, 2)

    def test_keeps_recent_replies_only(self):
        lines = "".join("%d\talbert\tP\tm%d\n" % (i, i) for i in range(1, 30))
        write_outbox(self.sav, "session\t1\n" + lines)
        self.b.poll()
        text, _ = read_inbox(self.sav)
        self.assertEqual(len(text.splitlines()), 1 + bridge.KEEP_REPLIES)


class FakeTest(unittest.TestCase):
    def test_fake_lines_use_player_name(self):
        cast = bridge.load_cast()
        fake = bridge.FakeReplier(cast)
        for npc in cast["npcs"]:
            out = fake.reply(npc, "Pranav", "hi", [])
            self.assertIn("Pranav", out)
            self.assertEqual(out, bridge.clean_reply(out))


if __name__ == "__main__":
    unittest.main()
