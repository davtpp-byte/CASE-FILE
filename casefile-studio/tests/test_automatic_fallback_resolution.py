"""Automatic inspection correction, runnable without server/media/paid providers."""

from pathlib import Path
import copy
import unittest
import episode
import storage

ROOT = Path(__file__).resolve().parents[1]


def case():
    p = {
        "id": storage.uid(),
        "title": "Metadata-only automatic fallback QA",
        "mode": "narration",
        "is_demo": False,
        "script": "",
        "sources": [],
        "assets": [],
        "scenes": [],
        "narration_id": None,
        "music_id": None,
        "music_volume": 0.12,
        "captions": True,
        "review": {
            "facts": False,
            "rights": False,
            "picture": False,
            "disclosure": False,
        },
    }
    episode.import_document(
        p,
        "script",
        (ROOT / "examples/the-last-timeline/narration-script.md").read_text(),
        "script.md",
    )
    episode.import_document(
        p,
        "guide",
        (ROOT / "examples/the-last-timeline/editing-guide-44.md").read_text(),
        "guide.md",
    )
    return p


def asset(p, sid, kind="image", name=None):
    a = {
        "id": storage.uid(),
        "name": name or sid + "-METADATA-ONLY",
        "kind": kind,
        "duration": 1800 if kind == "video" else 0,
        "has_audio": False,
        "license": "",
    }
    p["assets"].append(a)
    return a


class AutomaticFallbackTests(unittest.TestCase):
    def test_portrait_filed_as_funeral_main_uses_portrait_alternative_automatically(
        self,
    ):
        p = case()
        a = asset(p, "S01")
        episode.bind_source(p, "S10", {"asset_id": a["id"]})
        episode.build(p, True, inspection=True)
        c = next(c for c in episode.analyze(p)["placements"] if c["id"] == "C17")
        self.assertEqual(c["source_id"], "S01")
        self.assertIn("not funeral", c["label"])
        self.assertIsNone(p["episode"]["bindings"]["S10"]["asset_id"])
        self.assertTrue(
            any(
                s.get("guide_alternative")
                and s.get("guide_cue_id") == "C17"
                and s.get("asset_id") == a["id"]
                for s in p["scenes"]
            )
        )
        self.assertFalse(any(p["review"].values()))

    def test_trial_alternative_uses_each_alternative_crop_not_the_main_ranges(self):
        p = case()
        a = asset(p, "S17", "video")
        episode.bind_source(p, "S18", {"asset_id": a["id"]})
        episode.build(p, True, inspection=True)
        placements = {c["id"]: c for c in episode.analyze(p)["placements"]}
        self.assertEqual(
            placements["C36"]["inspection_window"], {"in": 5.0, "out": 9.0}
        )
        self.assertEqual(
            placements["C37"]["inspection_window"], {"in": 20.0, "out": 24.0}
        )
        self.assertNotIn("Sinardi", placements["C37"]["label"])

    def test_unique_image_alternative_can_resolve_a_manually_added_unnamed_portrait(
        self,
    ):
        p = case()
        a = asset(p, "unused", name="manually-added-portrait.jpg")
        episode.bind_source(p, "S10", {"asset_id": a["id"]})
        result = episode.resolve_automatic_source_links(p)
        self.assertEqual(result[0]["alternative_source"], "S01")
        self.assertEqual(p["episode"]["bindings"]["S01"]["asset_id"], a["id"])

    def test_visual_rebinding_preserves_narration_anchors_but_never_carries_review(
        self,
    ):
        p = case()
        a = asset(p, "S01")
        episode.bind_source(p, "S10", {"asset_id": a["id"]})
        start = next(
            c["narration_start"]
            for c in episode.analyze(p)["placements"]
            if c["id"] == "C17"
        )
        p["episode"]["reviews"]["C17"] = {
            "narration_start": start,
            "narration_end": start + 2,
            "in": 35,
            "out": 38,
            "reviewed": True,
            "source_id": "S10",
            "asset_id": a["id"],
        }
        before = episode.analyze(p)["word_clock"]
        episode.resolve_automatic_source_links(p)
        self.assertEqual(episode.analyze(p)["word_clock"], before)
        self.assertEqual(
            p["episode"]["reviews"]["C17"],
            {"narration_start": start, "narration_end": start + 2},
        )
        self.assertFalse(p["episode"]["bindings"]["S01"].get("rights_confirmed"))

    def test_unrelated_source_is_not_used_for_a_guide_without_that_alternative(self):
        p = case()
        a = asset(p, "S17", "video")
        episode.bind_source(p, "S16", {"asset_id": a["id"]})
        original_s16 = copy.deepcopy(p["episode"]["bindings"]["S16"])
        self.assertEqual(episode.resolve_automatic_source_links(p), [])
        # The independently named S17 may auto-link for its own permitted cues;
        # it must not become an automatic replacement for the S16 hearing.
        self.assertEqual(p["episode"]["bindings"]["S16"], original_s16)
        slot = next(c for c in p["episode"]["guide"]["cues"] if c["id"] == "C34")
        self.assertEqual(episode.resolve_cue(p, slot)["source_id"], "S16")
        self.assertFalse(episode.resolve_cue(p, slot)["using_alternative"])

    def test_repeated_resolution_is_stable_and_does_not_create_approvals(self):
        p = case()
        a = asset(p, "S01")
        episode.bind_source(p, "S10", {"asset_id": a["id"]})
        self.assertEqual(len(episode.resolve_automatic_source_links(p)), 1)
        before = copy.deepcopy(p)
        self.assertEqual(episode.resolve_automatic_source_links(p), [])
        self.assertEqual(p, before)
        self.assertFalse(any(p["review"].values()))


if __name__ == "__main__":
    unittest.main()
