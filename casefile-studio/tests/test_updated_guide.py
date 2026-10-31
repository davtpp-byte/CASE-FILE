"""Regression against the supplied 44-placement guide. No real media or licensing.

Metadata-only source fixtures test selection; they are never saved as real assets.
"""

import copy
import hashlib
from pathlib import Path

import pytest
import episode
import storage
from test_episode import local_project, GUIDE

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "examples/the-last-timeline/editing-guide-44.md").read_text()


def parsed():
    return episode.parse_guide(RAW, "The_Last_Timeline_Real_Footage_Guide (1).md")


def cue(g, cid):
    return next(c for c in g["cues"] if c["id"] == cid)


def metadata_project(missing=("S10", "S18")):
    p = local_project()
    p["sources"] = []
    episode.import_document(
        p,
        "script",
        (ROOT / "examples/the-last-timeline/narration-script.md").read_text(),
        "original-script.md",
    )
    episode.import_document(p, "guide", RAW, "updated-guide.md")
    g = p["episode"]["guide"]
    for sid in sorted({c["source_id"] for c in g["cues"]} - set(missing)):
        kind = "image" if sid in ("S01", "S02") else "video"
        asset = {
            "id": storage.uid(),
            "name": sid + "-METADATA-ONLY-NOT-UPLOADED",
            "kind": kind,
            "duration": 0 if kind == "image" else 1800,
            "has_audio": False,
            "license": "",
        }
        p["assets"].append(asset)
        episode.bind_source(p, sid, {"asset_id": asset["id"]})
    return p


def test_updated_guide_is_preserved_exactly_and_has_the_reported_counts():
    g = parsed()
    assert g["raw"] == RAW and len(g["cues"]) == 44 and len(g["sources"]) == 26
    assert len({c["source_id"] for c in g["cues"]}) == 18
    assert (
        hashlib.sha256(
            (ROOT / "examples/the-last-timeline/editing-guide-44.md").read_bytes()
        ).hexdigest()
        == "28d5e71e641d619f77a4dd5d8a442f63889fae75eea99228f11dbaa0809e72de"
    )


def test_funeral_conditional_links_to_the_named_portrait_not_arbitrary_catalog():
    c = cue(parsed(), "C17")
    assert c["source_id"] == "S10"
    assert c["suggested_windows"] == [{"start": 35.0, "end": 38.0}]
    assert len(c["alternatives"]) == 1
    a = c["alternatives"][0]
    assert (
        a["source_id"] == "S01" and a["media_kind"] == "image" and not a["manual_only"]
    )
    assert a["label"] == "Portrait — not funeral footage"
    assert "independently cleared" in a["instructions"]


@pytest.mark.parametrize(
    "cid,main,alternate",
    [
        (
            "C36",
            [{"start": 50.0, "end": 52.0}, {"start": 57.0, "end": 63.0}],
            [{"start": 5.0, "end": 9.0}],
        ),
        ("C37", [{"start": 95.0, "end": 112.0}], [{"start": 20.0, "end": 24.0}]),
    ],
)
def test_trial_alternatives_keep_their_own_source_clocks_and_neutral_labels(
    cid, main, alternate
):
    c = cue(parsed(), cid)
    assert c["source_id"] == "S18" and c["suggested_windows"] == main
    a = c["alternatives"][0]
    assert a["source_id"] == "S17" and a["suggested_windows"] == alternate
    assert a["label"] == "Courtroom coverage | September 2026."
    assert "Sinardi" not in a["label"] and "judge" not in a["label"].lower()


def test_2024_no_bond_hearing_does_not_gain_a_2026_courtroom_substitute():
    p = metadata_project(missing=("S16",))
    c = cue(p["episode"]["guide"], "C34")
    assert not c["alternatives"]
    assert episode.resolve_cue(p, c)["source_id"] == "S16"
    assert not episode.inspection_candidate(p, c)["usable"]
    with pytest.raises(ValueError):
        episode.choose_source(p, "C34", {"mode": "alternative", "source_id": "S17"})


def test_vigil_followup_is_retained_but_not_misread_as_a_range_in_wfla_video():
    c = cue(parsed(), "C16")
    assert c["source_id"] == "S25"
    assert c["suggested_windows"] == [
        {"start": 74.0, "end": 84.0},
        {"start": 90.0, "end": 92.0},
    ]
    assert not c["alternatives"]
    followup = c["additional_previews"][0]
    assert followup["source_id"] == "S26" and followup["suggested_windows"] == [
        {"start": 46.0, "end": 56.0}
    ]
    assert "not an automatic replacement" in followup["role"]


def test_fox_sentencing_extension_is_an_optional_choice_not_an_automatic_requirement():
    p = metadata_project(missing=("S19",))
    c = cue(p["episode"]["guide"], "C40")
    assert c["suggested_windows"] == [{"start": 10.0, "end": 22.0}]
    optional = c["alternatives"][0]
    assert (
        optional["source_id"] == "S20"
        and optional["optional"]
        and optional["manual_only"]
    )
    assert optional["suggested_windows"] == [{"start": 40.0, "end": 62.0}]
    assert episode.resolve_cue(p, c)["source_id"] == "S19"


def test_sixteen_main_metadata_records_resolve_every_slot_when_s10_and_s18_missing():
    p = metadata_project()
    before = copy.deepcopy(p)
    r = episode.analyze(p)
    assert r["matched_cues"] == 44 and not r["errors"]
    assert r["linked_source_count"] == 16 and r["used_source_count"] == 18
    assert r["alternative_cues"] == 3 and r["placements_with_files"] == 44
    actual = {
        c["id"]: c["source_id"] for c in r["placements"] if c["using_alternative"]
    }
    assert actual == {"C17": "S01", "C36": "S17", "C37": "S17"}
    assert r["ready_cues"] == 0 and r["inspection_cues"] == 42
    assert {c["id"] for c in r["placements"] if c.get("requires_stop")} == {
        "C03",
        "C21",
    }
    assert "S26" in r["source_option_ids"] and "S20" in r["source_option_ids"]
    assert p == before  # No stored project, media or approval is modified by analysis.


def test_explicit_primary_and_alternative_choices_remain_available_for_actual_rules():
    p = metadata_project()
    episode.choose_source(p, "C17", {"mode": "primary"})
    assert (
        episode.resolve_cue(p, cue(p["episode"]["guide"], "C17"))["source_id"] == "S10"
    )
    episode.choose_source(p, "C17", {"mode": "alternative", "source_id": "S01"})
    assert (
        episode.resolve_cue(p, cue(p["episode"]["guide"], "C17"))["source_id"] == "S01"
    )
    assert not any(p["review"].values())


def test_negative_trailing_reference_is_not_promoted_by_alternative_keyword():
    raw = GUIDE.replace(
        "`S03` [Preview](https://example.org/synthetic-video), around 0:01–0:02.",
        "[Main — 0:01–0:02](https://example.org/synthetic-video) (`S03`); not an alternative [Other portrait](https://example.org/synthetic-image) (`S01`).",
    )
    p = local_project()
    episode.import_document(p, "guide", raw, "negative-reference.md")
    c = p["episode"]["guide"]["cues"][0]
    assert not c["alternatives"]
    assert len(episode.source_options(p, c)) == 1
