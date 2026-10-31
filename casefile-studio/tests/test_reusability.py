"""Shared feature tests: source IDs/chapter numbers have no cross-case meaning."""

import copy
import pytest
import episode
import storage
from test_inspection import unreviewed
from test_alternatives import with_rule
from test_updated_guide import metadata_project, cue


def future_case(
    boundaries="Technical case; no chapter-specific visual exclusions.",
    chapter="chapter-3",
):
    p = unreviewed()
    p["title"] = "Entirely different synthetic future case"
    g = p["episode"]["guide"]
    g["boundaries"] = boundaries
    c = g["cues"][0]
    c["source_id"] = "S02"
    c["source_ids"] = ["S02"]
    c["chapter"] = chapter
    g["sources"].append(
        {
            "id": "S02",
            "title": "Different case source",
            "notes": "No declared chapter exclusion for this source.",
        }
    )
    p["episode"]["bindings"]["S02"] = copy.deepcopy(p["episode"]["bindings"]["S03"])
    return p, c


def test_future_case_s02_is_not_the_last_timeline_portrait():
    p, c = future_case()
    assert episode.inspection_candidate(p, c)["usable"]


def test_residence_flag_is_not_an_unconditional_chapter3_ban():
    p, c = future_case("Residential establishing footage is permitted in Chapter 3.")
    p["episode"]["bindings"]["S02"]["contains_residence"] = True
    assert episode.inspection_candidate(p, c)["usable"]


@pytest.mark.parametrize(
    "rule",
    [
        "No residential imagery in Chapter 7.",
        "Chapter 7 must contain no residential-property images.",
        "Chapter 7 prohibits residential imagery.",
        "Chapter 7 must not show residential property.",
    ],
)
def test_restriction_follows_this_guides_chapter_number_not_a_fixed_chapter(rule):
    p, c = future_case(rule, chapter="chapter-7")
    p["episode"]["bindings"]["S02"]["contains_residence"] = True
    r = episode.inspection_candidate(p, c)
    assert not r["usable"] and "Chapter 7" in r["status"]
    c["chapter"] = "chapter-3"
    assert episode.inspection_candidate(p, c)["usable"]


def test_explicit_source_exclusion_is_read_from_its_own_guide_notes():
    p, c = future_case(chapter="chapter-7")
    next(s for s in p["episode"]["guide"]["sources"] if s["id"] == "S02")["notes"] = (
        "Technical source. Do not use in Chapter 7."
    )
    assert not episode.inspection_candidate(p, c)["usable"]
    c["chapter"] = "chapter-3"
    assert episode.inspection_candidate(p, c)["usable"]


def test_cue_level_care_restriction_does_not_apply_to_other_cues():
    p, c = future_case(chapter="chapter-2")
    p["episode"]["bindings"]["S02"]["contains_residence"] = True
    c["care"] = "No residential-property imagery in this placement."
    assert not episode.inspection_candidate(p, c)["usable"]
    c["care"] = "Technical inspection fixture only."
    assert episode.inspection_candidate(p, c)["usable"]


def test_two_projects_can_use_identical_ids_with_different_guide_rules():
    restricted, c1 = future_case("No residential imagery in Chapter 3.")
    allowed, c2 = future_case(
        "Residential establishing footage is permitted in Chapter 3."
    )
    restricted["episode"]["bindings"]["S02"]["contains_residence"] = True
    allowed["episode"]["bindings"]["S02"]["contains_residence"] = True
    assert not episode.inspection_candidate(restricted, c1)["usable"]
    assert episode.inspection_candidate(allowed, c2)["usable"]


def test_different_case_named_alternative_does_not_use_this_cases_s01_or_s17():
    p = with_rule(rule="S12 permitted synthetic portrait.")
    a = {
        "id": storage.uid(),
        "name": "S12-synthetic.jpg",
        "kind": "image",
        "duration": 0,
        "license": "",
    }
    p["assets"].append(a)
    episode.bind_source(p, "S12", {"asset_id": a["id"]})
    first = episode.analyze(p)["placements"][0]
    assert first["using_alternative"] and first["source_id"] == "S12"
    assert first["primary_source_id"] == "S03"
    assert not any(p["review"].values())


def test_last_timeline_original_explicit_source_exclusion_is_still_enforced():
    p = metadata_project()
    c = copy.deepcopy(cue(p["episode"]["guide"], "C06"))
    c["chapter"] = "chapter-3"
    assert c["source_id"] == "S02" and not p["episode"]["bindings"]["S02"].get(
        "contains_residence"
    )
    r = episode.inspection_candidate(p, c)
    assert not r["usable"] and "Chapter 3" in r["status"]


@pytest.mark.parametrize("chapter", ["hook", "chapter-9"])
def test_whole_episode_restriction_applies_without_a_fixed_chapter(chapter):
    p, c = future_case(
        "No residential-property images anywhere in this episode.", chapter=chapter
    )
    p["episode"]["bindings"]["S02"]["contains_residence"] = True
    assert not episode.inspection_candidate(p, c)["usable"]


def test_multiple_explicit_chapters_are_scoped_without_blocking_other_chapters():
    p, c = future_case(
        "No residential imagery in Chapters 2 and 7.", chapter="chapter-7"
    )
    p["episode"]["bindings"]["S02"]["contains_residence"] = True
    assert not episode.inspection_candidate(p, c)["usable"]
    c["chapter"] = "chapter-2"
    assert not episode.inspection_candidate(p, c)["usable"]
    c["chapter"] = "chapter-3"
    assert episode.inspection_candidate(p, c)["usable"]
