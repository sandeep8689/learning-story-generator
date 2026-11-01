"""Offline tests: the Claude call is mocked, so no API key is needed.  Run: python -m unittest discover -s tests"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["STORY_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")

import story_generator as sg  # noqa: E402
import storage  # noqa: E402
from server import create_app  # noqa: E402

GOOD = """TITLE: Sunny and the Seed
STORY:
Mia had a small seed. She put it in a pot. She gave it water.

Days went by. A green leaf came up. The leaf turned to the sun.

Mia said, "Plants need sunlight!" The plant grew tall.
KEY IDEA: Plants need sunlight to grow.
QUESTIONS:
1. What did Mia plant?
2. Why did the leaf turn to the sun?
3. What do plants need to grow?"""

HARD = GOOD.replace(
    "She put it in a pot. She gave it water.",
    "She carefully placed it inside a large clay pot that sat on the old wooden windowsill "
    "of her grandmother's kitchen and then gave it plenty of fresh cool water every single morning "
    "while the sun slowly rose above the quiet houses and the hills far beyond the little village.",
)


class CoreTests(unittest.TestCase):
    def test_parse(self):
        p = sg.parse_story(GOOD)
        self.assertEqual(p["title"], "Sunny and the Seed")
        self.assertEqual(len(p["questions"]), 3)
        self.assertTrue(p["key_idea"].startswith("Plants"))

    def test_parse_bad_reply(self):
        with self.assertRaises(sg.StoryError):
            sg.parse_story("Sorry, I can't do that.")

    def test_readability(self):
        m = sg.analyze_readability(sg.parse_story(GOOD)["story"], "1-2")
        self.assertTrue(m["sentence_ok"])
        self.assertLess(m["avg_sentence_length"], 8)

    def test_keyword_flags(self):
        self.assertEqual(sg.keyword_flags("The knight killed the dragon."), ["killed"])
        self.assertEqual(sg.keyword_flags("A skilled baker."), [])

    def test_generate_ok(self):
        with mock.patch.object(sg, "call_model", return_value=GOOD):
            s = sg.generate_story("plants", "1-2", name="Mia")
        self.assertEqual(s["attempts"], 1)
        self.assertTrue(s["safety"]["passed"])

    def test_regenerates_when_too_hard(self):
        with mock.patch.object(sg, "call_model", side_effect=[HARD, GOOD]) as m:
            s = sg.generate_story("plants", "1-2")
        self.assertEqual(s["attempts"], 2)
        self.assertIn("shorter", m.call_args_list[1].args[1])

    def test_flagged_word_triggers_ai_review(self):
        flagged = GOOD.replace("What did Mia plant?", "Who killed the plant?")
        with mock.patch.object(sg, "call_model", side_effect=[flagged, "UNSAFE - mentions killing"]):
            s = sg.generate_story("plants", "1-2")
        self.assertFalse(s["safety"]["passed"])

    def test_validation(self):
        with self.assertRaises(sg.StoryError):
            sg.generate_story("   ", "3-5")
        with self.assertRaises(sg.StoryError):
            sg.generate_story("plants", "9-9")

    def test_missing_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(sg.StoryError) as ctx:
                sg.call_model("s", "u")
        self.assertIn("ANTHROPIC_API_KEY", str(ctx.exception))


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_pages_and_levels(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(set(self.client.get("/api/levels").get_json()), {"1-2", "3-5", "6-8"})

    def test_generate_save_list_delete(self):
        with mock.patch.object(sg, "call_model", return_value=GOOD):
            r = self.client.post("/api/generate", json={"topic": "plants", "level": "1-2"})
        self.assertEqual(r.status_code, 200)
        story = r.get_json()
        sid = self.client.post("/api/stories", json=story).get_json()["id"]
        self.assertEqual(self.client.get(f"/api/stories/{sid}").get_json()["title"], story["title"])
        self.assertTrue(any(x["id"] == sid for x in self.client.get("/api/stories").get_json()))
        self.assertEqual(self.client.delete(f"/api/stories/{sid}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/stories/{sid}").status_code, 404)

    def test_generate_error(self):
        r = self.client.post("/api/generate", json={"topic": ""})
        self.assertEqual(r.status_code, 400)
        self.assertIn("topic", r.get_json()["error"].lower())


if __name__ == "__main__":
    unittest.main()
