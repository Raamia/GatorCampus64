"""Offline tests for the game guide and its routing: python3 -m unittest discover -s tools/npc_bridge"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bridge  # noqa: E402
import guide  # noqa: E402

# question -> the guide entry that answers it, or None (general: Gemini)
ROUTES = [
    ("how do i get into marston", "marston-door"),
    ("how many stars do I have", "my-stars"),
    ("my stats", "my-stats"),
    ("how do I do the coffee run", "libwest-act2"),
    ("how do i press l + start", "l-start"),
    ("where do i go next", "next"),
    ("what is this game", "about"),
    ("what does the game have to offer", "offer"),
    ("who are you", "who-albert"),
    ("how do i unlock lake alice", "alice-door"),
    ("what are the controls", "controls"),
    ("how do i jump", "jump"),
    ("how do i get to the plaza", "warp"),
    ("is there a leaderboard", "leaderboard"),
    ("how do i play with my friends", "multiplayer"),
    ("where are the meal swipe tokens", "reitz-act2"),
    ("how do i beat the stair sprint", "swamp-act2"),
    ("how many lives do i have", "lives"),
    ("who can i play as", "characters"),
    ("how do i do act 3 of the swamp", "swamp-act3"),
    ("why is the door locked", "locked-door"),
    ("how do i ground pound", "punch"),
    ("where is library west", "libwest-door"),
    ("how do I do hide and seek", "libwest-act3"),
    ("how do i get 100 coins", "hundred-coins"),
    ("what is a star", "stars-what"),
    ("how many coins do i have", "coins"),
    ("what are the commands", "commands"),
    ("where is the swamp", "swamp-door"),
    ("can i go inside the reitz union", "reitz-interior"),
    ("how do I finish the bat census", "alice-act3"),
    ("what is the gator hop", "alice-act2"),
    ("what do i do in act 2 of marston", "marston-act2"),
    ("what is century tower", "century-tower"),
    ("is this the real campus", "real-campus"),
    ("what's the capital of france", None),
    ("tell me a joke", None),
    ("what's the tallest building in the world", None),
    ("whats the weather like", None),
    ("who won the national championship in 2006", None),
    ("hi", None),
    ("where is alberta", "where-alberta"),
    ("hi albert how do i get into marston", "marston-door"),
    ("where are you", "where-am-i-albert"),
    ("who else can i talk to", "npcs"),
]

STATS = {"albert_at": "in The Swamp, near where you arrive", "alberta_at": "on the Plaza of the Americas, right by the spawn",
         "stars": "3", "lives": "4", "coins": "12", "here": "THE HUB", "char": "Daniel", "players": "2",
         "go": "REITZ & ENGINEERING|THE HUB", "lock": "LAKE ALICE|NEWELL HALL|5",
         "s_swamp": "2", "s_reitz": "1", "s_alice": "0", "s_marston": "0", "s_libwest": "0"}


class GuideFileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = guide.Guide()

    def test_parses_with_enough_entries(self):
        self.assertGreaterEqual(len(self.g.entries), 60)
        for e in self.g.entries:
            self.assertRegex(e.id, r"^[a-z0-9-]+$")
            self.assertTrue(e.asks, e.id)
            self.assertTrue(e.answer, e.id)

    def test_placeholders_are_known(self):
        self.assertEqual(guide.check_placeholders(self.g.entries), [])

    def test_answers_are_plain_ascii(self):
        for e in self.g.entries:
            self.assertTrue(all(32 <= ord(c) < 127 for c in e.answer), e.id)
            self.assertNotIn("\\", e.answer, e.id)
            self.assertLessEqual(len(e.answer), bridge.MAX_REPLY, e.id)

    def test_routes(self):
        wrong = []
        for q, want in ROUTES:
            score, e = self.g.match(q, npc="albert")[0]
            got = e.id if score >= guide.ANSWER else None
            if got != want:
                wrong.append("%r -> %s %.2f (want %s)" % (q, e.id, score, want))
        self.assertEqual(wrong, [])

    def test_npc_specific_entries(self):
        self.assertEqual(self.g.match("who are you", npc="alberta")[0][1].id, "who-alberta")
        self.assertEqual(self.g.match("where are you", npc="alberta")[0][1].id, "where-am-i-alberta")
        self.assertEqual(self.g.match("where is albert", npc="alberta")[0][1].id, "where-albert")
        self.assertEqual(self.g.match("hey alberta, what are the controls", npc="alberta")[0][1].id, "controls")

    def test_malformed_entries_are_rejected(self):
        with self.assertRaises(ValueError):
            guide.parse("## S\n### Q?\nid: a\nask: x\n")
        with self.assertRaises(ValueError):
            guide.parse("## S\n### Q?\nid: a\nask: x\nanswer: y\n### R?\nid: a\nask: z\nanswer: w\n")


class FillTest(unittest.TestCase):
    def test_live_stats(self):
        out = guide.fill("{player}: {stars} stars, {lives} lives, {coins} coins as {character} in {here}. "
                         "{stage_stars} / swamp {stage_stars:swamp}. {next_hint}", "Pranav", STATS)
        self.assertIn("Pranav: 3 stars, 4 lives, 12 coins as Daniel in The Hub.", out)
        self.assertIn("The Swamp 2, Reitz & Engineering 1, Lake Alice 0", out)
        self.assertIn("swamp 2.", out)
        self.assertIn("Head to The Hub door for Reitz & Engineering!", out)
        self.assertIn("Lake Alice (the Newell Hall door) opens at 5 stars: 2 more to go.", out)
        self.assertNotIn("{", out)

    def test_mascot_spots(self):
        out = guide.fill("{albert_at} / {alberta_at}", "P", STATS)
        self.assertEqual(out, "in The Swamp, near where you arrive / on the Plaza of the Americas, right by the spawn")
        self.assertNotIn("{", guide.fill("{albert_at}", "P", {}))

    def test_without_stats(self):
        out = guide.fill("{stars} {next_hint}", "P", {})
        self.assertNotIn("{", out)
        self.assertIn("University Auditorium", out)

    def test_everything_open(self):
        self.assertIn("Every stage door is open", guide.next_hint({"stars": "20"}))


class Recorder:
    def __init__(self):
        self.calls = []

    def reply(self, npc, player, message, history, context=None):
        self.calls.append((message, context))
        return "AI says hi"


class RoutingTest(unittest.TestCase):
    def setUp(self):
        self.sav = tempfile.mkdtemp()
        self.log = os.path.join(self.sav, "unanswered.log")
        self.ai = Recorder()
        cast = {"npcs": {"albert": {"name": "Albert", "guide_flair": [""]}}}
        self.b = bridge.Bridge(self.sav, self.ai, cast, log=lambda *_: None, guide=guide.Guide(), unanswered=self.log)

    def tearDown(self):
        shutil.rmtree(self.sav)

    def ask(self, q, stats=STATS):
        return self.b.answer("albert", "Pranav", q, stats, [])

    def test_game_question_never_calls_the_ai(self):
        text, route = self.ask("how many stars do I have")
        self.assertTrue(route.startswith("guide: my-stars"))
        self.assertIn("You have 3 stars, Pranav!", text)
        self.assertEqual(self.ai.calls, [])

    def test_general_question_goes_to_the_ai_without_guide_notes(self):
        text, route = self.ask("what's the capital of france")
        self.assertEqual((text, route), ("AI says hi", "ai"))
        self.assertEqual(self.ai.calls, [("what's the capital of france", None)])
        self.assertFalse(os.path.exists(self.log))

    def test_half_matched_game_question_is_grounded_and_logged(self):
        text, route = self.ask("who won the national championship in 2006")
        self.assertTrue(route.startswith("ai+guide"), route)
        self.assertTrue(self.ai.calls[0][1])   # grounding notes passed along
        with open(self.log) as f:
            self.assertIn("who won the national championship in 2006", f.read())

    def test_end_to_end_through_the_files(self):
        stats = bridge.escape("stars=3;lives=4;here=THE HUB")
        with __import__("zipfile").ZipFile(os.path.join(self.sav, bridge.OUT_MODFS), "w") as z:
            z.writestr(bridge.OUT_FILE, "session\t9\n1\talbert\tPranav\thow many stars do i have\t%s\n" % stats)
        self.assertEqual(self.b.poll(), 1)
        with __import__("zipfile").ZipFile(os.path.join(self.sav, bridge.IN_MODFS)) as z:
            self.assertIn("You have 3 stars, Pranav!", z.read(bridge.IN_FILE).decode())


if __name__ == "__main__":
    unittest.main()
