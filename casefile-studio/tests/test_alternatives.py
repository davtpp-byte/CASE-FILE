"""Guide-authorized alternatives never imply licensing or change the voice clock."""

import copy
import pytest
import episode
import storage
import editorial
from test_capcut import imported
from test_episode import GUIDE


def with_rule(
    rule="`S01` permitted synthetic portrait.",
    field="Alternative",
    label="SYNTHETIC ALTERNATIVE PORTRAIT — NOT PRIMARY FOOTAGE",
    library=False,
):
    p = imported()
    from test_episode import voice

    voice(p)
    if library:
        raw = GUIDE.replace(
            "Test video file; no actual evidence.",
            f"Test video file; no actual evidence. **{field}:** {rule} **Alternative label:** {label}",
        )
    else:
        raw = GUIDE.replace(
            "**Care:** Technical fixture, not actual footage.",
            f"**{field}:** {rule} **Alternative label:** {label} **Care:** Technical fixture, not actual footage.",
        )
    episode.import_document(p, "guide", raw, "synthetic-alternatives.md")
    image = {
        "id": storage.uid(),
        "name": "S01-synthetic-portrait.jpg",
        "kind": "image",
        "duration": 0,
        "has_audio": False,
        "license": "",
    }
    p["assets"].append(image)
    episode.bind_source(p, "S01", {"asset_id": image["id"]})
    return p


def add_main(p):
    a = {
        "id": storage.uid(),
        "name": "S03-synthetic.mp4",
        "kind": "video",
        "duration": 4,
        "has_audio": True,
        "license": "",
    }
    p["assets"].append(a)
    episode.bind_source(p, "S03", {"asset_id": a["id"]})
    return a


def first(p):
    return episode.analyze(p)["placements"][0]


@pytest.mark.parametrize(
    "field",
    ["Alternative", "Alternatives", "Fallback", "Alt", "If unavailable", "If missing"],
)
def test_explicit_rule_aliases_become_options(field):
    p = with_rule(field=field)
    c = first(p)
    assert (
        c["primary_source_id"] == "S03"
        and c["source_id"] == "S01"
        and c["using_alternative"]
    )
    assert [o["source_id"] for o in c["source_choices"]] == ["S03", "S01"]
    assert c["inspection_ready"] and not c["ready"]


def test_missing_main_uses_guide_alternative_without_false_review_or_licensing():
    p = with_rule()
    before = copy.deepcopy(p)
    r = episode.analyze(p)
    assert r["alternative_cues"] == 1 and r["placements_with_files"] == 2
    assert r["linked_source_count"] == 1 and r["used_source_count"] == 2
    episode.build(p, True, inspection=True)
    scene = next(s for s in p["scenes"] if s["guide_cue_id"] == "C01" and s["asset_id"])
    assert (
        scene["guide_source_id"] == "S01" and scene["guide_primary_source_id"] == "S03"
    )
    assert scene["guide_alternative"] and scene["guide_unreviewed"]
    assert scene["source_label"].startswith("SYNTHETIC ALTERNATIVE")
    assert p["assets"] == before["assets"] and p["review"] == before["review"]
    assert not p["episode"]["reviews"] and not any(
        b.get("rights_confirmed") for b in p["episode"]["bindings"].values()
    )
    assert not [i for i in episode.issues(p) if i["blocks_draft"]]


def test_available_main_is_preferred_even_if_its_rights_are_not_signed_off():
    p = with_rule()
    add_main(p)
    c = first(p)
    assert c["source_id"] == "S03" and not c["using_alternative"]
    assert not c["ready"] and c["inspection_ready"]


def test_user_can_force_main_or_alternative_without_moving_narration_clock():
    p = with_rule()
    before = episode.analyze(p)["word_clock"]
    episode.choose_source(p, "C01", {"mode": "primary"})
    assert first(p)["source_id"] == "S03" and not first(p)["asset_id"]
    add_main(p)
    episode.choose_source(p, "C01", {"mode": "alternative", "source_id": "S01"})
    assert first(p)["source_id"] == "S01" and first(p)["using_alternative"]
    assert episode.analyze(p)["word_clock"] == before
    episode.choose_source(p, "C01", {"mode": "auto"})
    assert first(p)["source_id"] == "S03"


def test_arbitrary_source_not_permitted_by_guide_is_rejected():
    p = with_rule()
    before = copy.deepcopy(p)
    with pytest.raises(ValueError, match="not an alternative permitted"):
        episode.choose_source(p, "C01", {"mode": "alternative", "source_id": "S99"})
    assert p == before


def test_an_explicit_source_library_rule_can_be_inherited():
    p = with_rule(library=True)
    c = first(p)
    assert c["source_id"] == "S01" and c["alternative_origin"] == "source-library"
    assert c["label"].startswith("SYNTHETIC ALTERNATIVE")


def test_global_research_alternative_is_not_a_per_placement_substitution_rule():
    p = imported()
    raw = (
        "S17 and S19 are alternative case footage for later chapters, not substitutes for this hearing.\n\n"
        + GUIDE
    )
    episode.import_document(p, "guide", raw, "synthetic-negative-intro.md")
    assert len(episode.source_options(p, p["episode"]["guide"]["cues"][0])) == 1


def test_positive_conditional_in_care_is_preserved_as_a_local_rule():
    p = imported()
    raw = GUIDE.replace(
        "**Care:** Technical fixture, not actual footage.",
        "**Care:** Technical fixture. If S03 is unavailable, use `S01` portrait instead.",
    )
    episode.import_document(p, "guide", raw, "conditional.md")
    assert p["episode"]["guide"]["cues"][0]["alternatives"][0]["source_id"] == "S01"


@pytest.mark.parametrize(
    "rule",
    [
        "No alternative permitted.",
        "Do not substitute S01 for this event.",
        "S01 is not a substitute for this hearing.",
    ],
)
def test_negative_rule_does_not_allow_manual_or_automatic_arbitrary_replacements(rule):
    p = with_rule(rule=rule)
    c = first(p)
    assert len(c["source_choices"]) == 1 and c["source_id"] == "S03"
    with pytest.raises(ValueError):
        episode.choose_source(p, "C01", {"mode": "alternative", "source_id": "S01"})


def test_unnamed_portrait_rule_requires_explicit_choice_not_random_rotation():
    p = with_rule(rule="Use a permitted portrait instead.", label="")
    assert first(p)["source_id"] == "S03"
    assert all(o.get("manual_only") for o in first(p)["source_choices"][1:])
    episode.choose_source(p, "C01", {"mode": "alternative", "source_id": "S01"})
    assert first(p)["source_id"] == "S01"
    assert "NOT PRIMARY EVENT FOOTAGE" in first(p)["label"]


def test_text_card_rule_does_not_become_permission_to_use_unrelated_footage():
    p = with_rule(rule="Use a plain text date card instead.", label="")
    c = first(p)
    assert c["alternative_instructions"]
    assert len(c["source_choices"]) == 1 and not c["asset_id"]


def test_chapter3_guard_applies_to_the_alternative_actually_selected():
    p = with_rule(rule="`S02` permitted synthetic portrait.")
    raw = p["episode"]["guide"]["cues"][0]
    raw["chapter"] = "chapter-3"
    a = {
        "id": storage.uid(),
        "name": "S02-synthetic.jpg",
        "kind": "image",
        "duration": 0,
        "license": "",
    }
    p["assets"].append(a)
    p["episode"]["bindings"]["S02"] = {"asset_id": a["id"], "contains_residence": True}
    episode.choose_source(p, "C01", {"mode": "alternative", "source_id": "S02"})
    c = episode.resolve_cue(p, raw)
    assert not episode.inspection_candidate(p, c)["usable"]
    assert "prohibits residential" in episode.inspection_candidate(p, c)["status"]


def test_new_main_or_alternative_file_invalidates_prior_context_review():
    p = with_rule()
    main = add_main(p)
    main["license"] = "Synthetic test-created video."
    episode.bind_source(p, "S03", {"rights_confirmed": True})
    episode.review_cue(
        p, "C01", {"in": 1, "out": 2, "reviewed": True, "narration_start": 0.166666}
    )
    assert p["episode"]["reviews"]["C01"]["source_id"] == "S03"
    episode.choose_source(p, "C01", {"mode": "alternative", "source_id": "S01"})
    review = p["episode"]["reviews"]["C01"]
    assert review == {"narration_start": 0.166666} and not first(p)["ready"]


def test_own_alternative_review_does_not_inherit_primary_approval():
    p = with_rule()
    image = next(a for a in p["assets"] if a["name"].startswith("S01"))
    image["license"] = "Synthetic QA image created for tests."
    episode.bind_source(p, "S01", {"rights_confirmed": True})
    episode.review_cue(p, "C01", {"reviewed": True})
    assert first(p)["ready"] and p["episode"]["reviews"]["C01"]["source_id"] == "S01"
    episode.choose_source(
        p, "C01", {"label": "ALTERNATIVE PORTRAIT — NOT EVENT FOOTAGE"}
    )
    assert not first(p)["ready"]


def test_media_type_and_required_stop_in_alternative_rule_are_not_ignored():
    p = with_rule()
    a = next(a for a in p["assets"] if a["name"].startswith("S01"))
    a.update(kind="video", duration=4)
    assert not first(p)["inspection_ready"]
    p = with_rule(rule="`S01` portrait. Stop before the next account.")
    assert not first(p)["inspection_ready"]


def test_context_scoped_alternative_is_not_automatically_used_in_every_chapter():
    p = with_rule(rule="S01 portrait, only for later chapters.")
    assert first(p)["source_id"] == "S03"
    episode.choose_source(p, "C01", {"mode": "alternative", "source_id": "S01"})
    assert first(p)["source_id"] == "S01"


def test_source_switch_marks_existing_plan_stale_and_preserves_exact_srt():
    import renderer

    p = with_rule()
    before = renderer.project_srt(p)
    episode.build(p, True, inspection=True)
    assert episode.analyze(p)["plan_current"]
    episode.choose_source(p, "C01", {"mode": "primary"})
    assert not episode.analyze(p)["plan_current"]
    assert renderer.project_srt(p) == before
    assert any(
        i["code"] == "episode_plan_stale" and i["blocks_draft"]
        for i in episode.issues(p)
    )


def test_choice_api_requires_guide_permission_and_keeps_every_signoff_false(isolated):
    c, _ = isolated
    p = with_rule()
    storage.save_project(p)
    url = f"/api/projects/{p['id']}/episode/choice/C01"
    assert (
        c.patch(url, json={"mode": "alternative", "source_id": "S99"}).status_code
        == 422
    )
    r = c.patch(url, json={"mode": "alternative", "source_id": "S01"})
    assert r.status_code == 200
    assert r.json()["analysis"]["placements"][0]["source_id"] == "S01"
    assert not any(r.json()["project"]["review"].values())


def test_replacing_guide_clears_choices_whose_permissions_may_no_longer_apply():
    p = with_rule()
    episode.choose_source(p, "C01", {"mode": "alternative", "source_id": "S01"})
    episode.import_document(p, "guide", GUIDE, "no-alternatives.md")
    assert not p["episode"]["choices"]
    assert len(first(p)["source_choices"]) == 1


def test_or_preview_keeps_each_source_video_clock_separate():
    p = imported()
    raw = GUIDE.replace(
        "around 0:01–0:02.",
        "around 0:01–0:02 or `S04` [Alternate](https://example.org/alternate-video), around 0:20–0:24.",
    )
    episode.import_document(p, "guide", raw, "two-source-windows.md")
    cue = p["episode"]["guide"]["cues"][0]
    assert cue["suggested_windows"] == [{"start": 1.0, "end": 2.0}]
    assert cue["alternatives"][0]["suggested_windows"] == [{"start": 20.0, "end": 24.0}]
    asset = {
        "id": storage.uid(),
        "name": "S04.mp4",
        "kind": "video",
        "duration": 30,
        "has_audio": True,
        "license": "",
    }
    p["assets"].append(asset)
    episode.bind_source(p, "S04", {"asset_id": asset["id"]})
    candidate = episode.inspection_candidate(p, cue)
    assert candidate["usable"] and candidate["window"] == {"in": 20.0, "out": 24.0}


def test_alternative_clock_is_not_used_to_make_an_invalid_main_excerpt_fit():
    p = imported()
    raw = GUIDE.replace(
        "around 0:01–0:02.",
        "around 0:10–0:12 or `S04` [Alternate](https://example.org/alternate-video), around 0:01–0:02.",
    )
    episode.import_document(p, "guide", raw, "invalid-main-clock.md")
    add_main(p)
    assert not first(p)["inspection_ready"]


def test_real_inspection_render_uses_fallback_image_when_main_file_is_absent(isolated):
    import io
    import subprocess
    import wave
    import numpy as np
    from PIL import Image
    import renderer

    _, root = isolated
    p = with_rule()
    path = root / "SYNTHETIC-tone.wav"
    sr = 16000
    with wave.open(str(path), "wb") as f:
        f.setparams((1, 2, sr, 0, "NONE", "not compressed"))
        f.writeframes(
            (np.sin(np.arange(round(sr * 6.04)) * 2 * np.pi * 310 / sr) * 2500)
            .astype("<i2")
            .tobytes()
        )
    p["assets"][0]["path"] = str(path.relative_to(storage.ROOT))
    image = root / "S01-SYNTHETIC-green.jpg"
    Image.new("RGB", (854, 480), "#249649").save(image)
    p["assets"][1]["path"] = str(image.relative_to(storage.ROOT))
    episode.build(p, True, inspection=True)
    out = root / "synthetic-alternative-inspection.mp4"
    renderer.render(
        p,
        {
            "resolution": "480p",
            "draft": True,
            "captions": False,
            "allow_inspection": True,
        },
        out,
        lambda *_: None,
        lambda: False,
    )
    assert renderer.probe(out)["video_duration"] == pytest.approx(145 / 24, abs=0.001)
    frame = Image.open(
        io.BytesIO(
            subprocess.check_output(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-ss",
                    "0.6",
                    "-i",
                    str(out),
                    "-frames:v",
                    "1",
                    "-f",
                    "image2pipe",
                    "-vcodec",
                    "png",
                    "-",
                ]
            )
        )
    ).convert("RGB")
    r, g, b = frame.getpixel((427, 200))
    assert g > r * 2 and g > b
    assert not any(p["review"].values())
    assert all(
        not binding.get("rights_confirmed")
        for binding in p["episode"]["bindings"].values()
    )
