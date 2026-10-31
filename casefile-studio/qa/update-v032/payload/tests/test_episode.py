"""Guide-driven setup regressions. Local fixtures only; never downloads or paid AI.

The Last Timeline documents are user-supplied parsing fixtures, not verified facts.
All audio/video used for rendering tests below is clearly synthetic technical media.
"""

import copy
import io
import json
import subprocess
import wave

import numpy as np
import pytest
from PIL import Image, ImageChops

import ai
import app as server
import editorial
import episode
import renderer
import storage

EXAMPLE = storage.ROOT / "examples/the-last-timeline"
SCRIPT = (storage.ROOT / "tests/fixtures/synthetic-script.md").read_text()
GUIDE = (storage.ROOT / "tests/fixtures/synthetic-guide.md").read_text()


def local_project():
    p = {
        "id": storage.uid(),
        "title": "Synthetic episode QA",
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
        "look": "noir",
        "review": {
            "facts": False,
            "picture": False,
            "rights": False,
            "disclosure": False,
        },
    }
    episode.import_document(p, "script", SCRIPT, "synthetic-script.md")
    episode.import_document(p, "guide", GUIDE, "synthetic-guide.md")
    return p


def voice(p, duration=6.04):
    a = {
        "id": storage.uid(),
        "name": "SYNTHETIC voice tone.wav",
        "kind": "audio",
        "duration": duration,
        "has_audio": True,
        "license": "Test-created tone; not narration of a real case.",
    }
    p["assets"].append(a)
    p["narration_id"] = a["id"]
    return a


def linked(p, sid="S03", kind="video"):
    a = {
        "id": storage.uid(),
        "name": sid + (".mp4" if kind == "video" else ".jpg"),
        "kind": kind,
        "duration": 10 if kind == "video" else 0,
        "has_audio": kind == "video",
        "license": "Synthetic technical test fixture created for this test.",
    }
    p["assets"].append(a)
    episode.bind_source(p, sid, {"asset_id": a["id"], "rights_confirmed": True})
    return a


def prepared():
    p = local_project()
    voice(p)
    linked(p)
    linked(p, "S01", "image")
    episode.review_cue(p, "C01", {"reviewed": True, "in": 1, "out": 2})
    episode.review_cue(p, "C02", {"reviewed": True})
    return p


def api_project(c):
    p = c.post(
        "/api/projects", json={"title": "Episode API QA", "mode": "narration"}
    ).json()
    url = "/api/projects/" + p["id"]
    for role, text in [("script", SCRIPT), ("guide", GUIDE)]:
        r = c.post(
            url + "/episode/import",
            json={"role": role, "text": text, "filename": "synthetic-" + role + ".md"},
        )
        assert r.status_code == 200, r.text
    return c.get(url).json(), url


def tone_bytes(seconds=6.04, rate=16000):
    t = np.arange(round(seconds * rate)) / rate
    hz = np.where(t < seconds / 2, 440, 880)
    samples = (np.sin(t * hz * 2 * np.pi) * 3500).astype("<i2")
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        w.writeframes(samples.tobytes())
    return out.getvalue()


def test_supplied_documents_are_parsed_without_changing_claims():
    raw = (EXAMPLE / "narration-script.md").read_text()
    g = (EXAMPLE / "editing-guide.md").read_text()
    p = local_project()
    p["sources"] = []
    episode.import_document(p, "script", raw, "Untitled document (1).md")
    episode.import_document(p, "guide", g, "The_Last_Timeline_Real_Footage_Guide.md")
    r = episode.analyze(p)
    assert (
        r["word_count"],
        len(r["sections"]),
        r["cue_count"],
        r["matched_cues"],
        r["source_count"],
        r["used_source_count"],
    ) == (2366, 13, 43, 43, 24, 15)
    assert r["errors"] == [] and r["has_voice"] is False
    assert [c["source_id"] for c in r["placements"][:2]] == ["S03", "S01"]
    assert {c["source_id"] for c in r["placements"]} == {
        "S01",
        "S02",
        "S03",
        "S04",
        "S05",
        "S06",
        "S07",
        "S08",
        "S12",
        "S13",
        "S14",
        "S15",
        "S16",
        "S17",
        "S19",
    }
    assert p["episode"]["script"]["raw"] == raw and p["episode"]["guide"]["raw"] == g
    assert all(not s["reviewed"] for s in p["sources"])
    assert len(p["episode"]["guide"]["sources"][-1]["notes"]) < 500
    assert {c["id"] for c in r["placements"] if c["requires_stop"]} == {"C03", "C20"}
    plan = episode.build(p, True)
    assert plan["scene_count"] == 57 and plan["gap_seconds"] == plan["duration"]
    assert [
        t[3] for t in episode.tokens(" ".join(s["narration"] for s in p["scenes"]))
    ] == [t[3] for t in episode.tokens(p["script"])]


def test_guide_cannot_replace_narration_in_wrong_card(isolated):
    c, _ = isolated
    p, url = api_project(c)
    before = p["script"]
    raw = (EXAMPLE / "editing-guide.md").read_text()
    r = c.post(
        url + "/episode/import",
        json={"role": "script", "text": raw, "filename": "wrong.md"},
    )
    assert r.status_code == 422 and "editing guide" in r.text
    assert c.get(url).json()["script"] == before
    r = c.post(
        url + "/upload", files={"files": ("wrong.md", raw.encode(), "text/markdown")}
    )
    assert r.status_code == 422 and "separate" in r.text
    assert c.get(url).json()["script"] == before


def test_reference_ids_keep_leading_zeros():
    assert editorial.source_ids("Claims [S01, S03] and [S1].") == ["S01", "S03", "S1"]
    assert "Acquisition notes" not in episode.parse_guide(GUIDE)["sources"][-1]["notes"]


def test_plan_is_allowed_without_audio_but_rendering_is_not(isolated):
    c, _ = isolated
    p, url = api_project(c)
    r = c.post(url + "/episode/build", json={"allow_placeholders": True})
    assert r.status_code == 200, r.text
    assert r.json()["analysis"]["plan_current"]
    pre = c.get(url + "/preflight").json()
    assert not pre["ready_for_draft"]
    assert any(
        i["code"] == "episode_voice_missing" and i["blocks_draft"]
        for i in pre["issues"]
    )
    assert c.post(url + "/render", json={"draft": True}).status_code == 400
    assert c.post(url + "/render", json={"draft": False}).status_code == 400
    assert "Source audio is muted" in c.get(url + "/episode/plan.md").text


def test_short_approved_clips_play_once_and_leave_marked_gaps():
    p = prepared()
    plan = episode.build(p, True)
    source = [
        s
        for s in p["scenes"]
        if s.get("guide_source_id") == "S03" and s.get("asset_id")
    ]
    assert (
        len(source) == 1 and source[0]["duration"] == 1 and source[0]["trim_start"] == 1
    )
    assert source[0]["source_label"] == "SYNTHETIC TEST PATTERN | 2026"
    assert plan["gap_seconds"] > 0 and plan["preserves_narration"]
    assert (
        source[0]["source_ids"] == []
    )  # a visual reference is not automatic factual proof
    assert all(s["duration"] >= 0.5 and s["duration"] <= 30 for s in p["scenes"])
    with pytest.raises(ValueError, match="marked gaps"):
        episode.build(p, False)


def test_every_word_and_every_audio_second_stays_in_order():
    p = prepared()
    duration = next(a["duration"] for a in p["assets"] if a["id"] == p["narration_id"])
    plan = episode.build(p, True)
    cursor = 0
    for scene in p["scenes"]:
        assert scene["audio_start"] == pytest.approx(cursor)
        assert scene["audio_duration"] == scene["duration"]
        cursor += scene["duration"]
    assert duration <= cursor < duration + 1 / 24
    assert cursor == pytest.approx(plan["duration"])
    assert [
        t[3] for t in episode.tokens(" ".join(s["narration"] for s in p["scenes"]))
    ] == [t[3] for t in episode.tokens(p["script"])]
    assert not any(i["blocks_draft"] for i in episode.issues(p))


def test_rights_notes_are_required_before_permission_confirmation():
    p = local_project()
    a = linked(p)
    a["license"] = ""
    with pytest.raises(ValueError, match="Record the permission"):
        episode.bind_source(p, "S03", {"rights_confirmed": True})
    assert not episode.source_ready(p, p["episode"]["guide"]["cues"][0])[0]


def test_approximate_web_preview_is_not_an_approved_clip_range():
    p = local_project()
    linked(p)
    with pytest.raises(ValueError, match="exact in/out"):
        episode.review_cue(p, "C01", {"reviewed": True})
    assert not episode.analyze(p)["placements"][0]["ready"]


@pytest.mark.parametrize(
    "start,end", [(-1, 2), (2, 2.2), (9, 11), (0, float("nan")), (0, float("inf"))]
)
def test_invalid_and_out_of_file_clip_ranges_are_rejected(start, end):
    p = local_project()
    linked(p)
    with pytest.raises(ValueError):
        episode.review_cue(p, "C01", {"reviewed": True, "in": start, "out": end})


def test_rebinding_source_resets_rights_and_all_affected_reviews():
    p = prepared()
    replacement = {
        "id": storage.uid(),
        "name": "S03-replacement.mp4",
        "kind": "video",
        "duration": 20,
        "license": "New test file",
    }
    p["assets"].append(replacement)
    episode.bind_source(p, "S03", {"asset_id": replacement["id"]})
    assert p["episode"]["bindings"]["S03"]["rights_confirmed"] is False
    assert "C01" not in p["episode"]["reviews"]
    assert not episode.analyze(p)["placements"][0]["ready"]


def test_changed_license_cannot_reuse_old_confirmation():
    p = prepared()
    episode.build(p, True)
    source = next(a for a in p["assets"] if a["name"] == "S03.mp4")
    source["license"] = "Changed rights claim"
    assert not episode.source_ready(p, p["episode"]["guide"]["cues"][0])[0]
    assert any(i["code"] == "episode_unapproved_source" for i in episode.issues(p))


def test_explicit_narration_stop_is_required_for_context_switch():
    p = prepared()
    p["episode"]["guide"]["cues"][0]["requires_stop"] = True
    with pytest.raises(ValueError, match="explicit stop"):
        episode.review_cue(p, "C01", {"reviewed": True, "in": 1, "out": 2})
    episode.review_cue(
        p, "C01", {"reviewed": True, "in": 1, "out": 2, "narration_end": 1}
    )
    assert episode.analyze(p)["placements"][0]["ready"]
    episode.build(p, True)
    assert all(
        s["audio_start"] + s["duration"] <= 1 + 0.001
        for s in p["scenes"]
        if s.get("asset_id") and s.get("guide_cue_id") == "C01"
    )


@pytest.mark.parametrize("sid,tag", [("S02", False), ("S01", True)])
def test_residential_material_cannot_be_approved_for_chapter_three(sid, tag):
    p = local_project()
    g = p["episode"]["guide"]
    g["cues"][1]["chapter"] = "chapter-3"
    g["cues"][1]["source_id"] = sid
    if sid == "S02":
        g["sources"].append(
            {
                "id": sid,
                "title": "Synthetic residence",
                "url": "https://example.org/house",
            }
        )
    linked(p, sid, "image")
    episode.bind_source(p, sid, {"contains_residence": tag})
    with pytest.raises(ValueError, match="Chapter 3"):
        episode.review_cue(p, "C02", {"reviewed": True})


@pytest.mark.parametrize(
    "mutation",
    [
        "reorder",
        "audio_start",
        "audio_duration",
        "duration",
        "asset",
        "label",
        "cue",
        "source",
        "remove_scene",
    ],
)
def test_manual_timeline_mutations_cannot_bypass_guide_guards(mutation):
    p = prepared()
    episode.build(p, True)
    if mutation == "reorder":
        p["scenes"].reverse()
    elif mutation == "remove_scene":
        p["scenes"].pop()
    else:
        key = {
            "asset": "asset_id",
            "label": "source_label",
            "cue": "guide_cue_id",
            "source": "guide_source_id",
        }.get(mutation, mutation)
        p["scenes"][0][key] = (
            2
            if mutation in ("audio_start", "audio_duration", "duration")
            else "changed"
        )
    issues = episode.issues(p)
    assert any(
        i["code"] == "episode_timeline_changed" and i["blocks_draft"] for i in issues
    )
    assert not episode.analyze(p)["plan_current"]


def test_cosmetic_look_and_mix_changes_do_not_break_the_plan():
    p = prepared()
    episode.build(p, True)
    p.update(look="archive", music_volume=0.2, captions=False)
    assert episode.analyze(p)["plan_current"]
    assert not any(i["blocks_draft"] for i in episode.issues(p))


def test_word_timings_and_manual_cues_share_one_chapter_clock():
    p = prepared()
    voice(p, 20)
    words = episode.tokens(p["script"])
    boundary = p["episode"]["script"]["sections"][1]["word_start"]
    entries = [
        {
            "word": t[0],
            "start": 1 + i * 0.35 if i < boundary else 12 + (i - boundary) * 0.35,
            "end": 1.3 + i * 0.35 if i < boundary else 12.3 + (i - boundary) * 0.35,
        }
        for i, t in enumerate(words)
    ]
    episode.import_document(p, "timings", json.dumps({"words": entries}), "words.json")
    r = episode.analyze(p)
    assert r["errors"] == [] and r["timing_word_match_percent"] == 100
    assert r["placements"][1]["narration_start"] == 12
    episode.build(p, True)
    assert (
        next(s["audio_start"] for s in p["scenes"] if s["guide_cue_id"] == "C02") == 12
    )
    # Moving a chapter's first cue no longer conflicts with a proportional chapter boundary.
    episode.review_cue(p, "C02", {"reviewed": True, "narration_start": 11.8})
    assert episode.analyze(p)["errors"] == []
    episode.build(p, True)


def test_srt_is_marked_segment_interpolated_and_overlap_is_rejected():
    p = local_project()
    sections = p["episode"]["script"]["sections"]
    text = (
        "1\n00:00:01,000 --> 00:00:04,000\n"
        + sections[0]["text"]
        + "\n\n2\n00:00:05,000 --> 00:00:08,000\n"
        + sections[1]["text"]
        + "\n"
    )
    t = episode.parse_timings(text, "voice.srt")
    assert t["precision"] == "segment-interpolated"
    assert len(t["words"]) == len(episode.tokens(p["script"]))
    with pytest.raises(ValueError, match="ordered"):
        episode.parse_timings(
            json.dumps(
                [
                    {"start": 0, "end": 2, "word": "one"},
                    {"start": 1, "end": 3, "word": "two"},
                ]
            ),
            "bad.json",
        )


def test_wrong_timing_file_and_impossible_stop_are_flagged():
    p = prepared()
    episode.import_document(
        p,
        "timings",
        json.dumps([{"word": "completely unrelated material", "start": 0, "end": 2}]),
        "wrong.json",
    )
    assert any("less than 70%" in e for e in episode.analyze(p)["errors"])
    with pytest.raises(ValueError, match="70%"):
        episode.build(p, True)
    p["episode"].pop("timings")
    episode.review_cue(p, "C02", {"narration_end": 0.1})
    assert any("visual stop" in e for e in episode.analyze(p)["errors"])


def test_source_filename_matching_is_exact_and_ambiguous_matches_are_not_linked():
    p = local_project()
    p["assets"] = [
        {"id": "a", "name": "S01-portrait.jpg", "kind": "image"},
        {"id": "b", "name": "S1.jpg", "kind": "image"},
        {"id": "c", "name": "S03.mp4", "kind": "video"},
        {"id": "d", "name": "S03-excerpt.mp4", "kind": "video"},
    ]
    assert episode.suggestions(p) == {"S01": "a"}


def test_importing_changed_script_invalidates_clip_context_reviews():
    p = prepared()
    episode.build(p, True)
    episode.import_document(
        p,
        "script",
        SCRIPT.replace("technical test", "technical fixture"),
        "updated-script.md",
    )
    assert p["episode"]["reviews"] == {}
    assert not episode.analyze(p)["plan_current"]


def test_episode_options_assign_separate_media_roles_and_remove_timings(isolated):
    c, _ = isolated
    p, url = api_project(c)
    r = c.post(
        url + "/upload",
        data={"episode_role": "narration"},
        files={"files": ("synthetic-voice.wav", tone_bytes(), "audio/wav")},
    )
    assert r.status_code == 200, r.text
    a = r.json()["assets"][-1]
    r = c.patch(url + "/episode/options", json={"narration_id": a["id"]})
    assert r.status_code == 200
    r = c.patch(url + "/episode/options", json={"music_id": a["id"]})
    assert r.status_code == 422
    assert c.get(url).json()["music_id"] is None
    r = c.post(
        url + "/episode/import",
        json={
            "role": "timings",
            "text": json.dumps([{"word": "a test", "start": 0, "end": 1}]),
            "filename": "wrong.json",
        },
    )
    assert r.status_code == 200
    assert (
        c.patch(url + "/episode/options", json={"clear_timings": True}).status_code
        == 200
    )
    assert "timings" not in c.get(url).json()["episode"]
    assert (
        c.patch(url + "/episode/options", json={"music_volume": 0.8}).status_code == 422
    )


def test_explicit_media_roles_reject_wrong_file_types_before_script_changes(isolated):
    c, _ = isolated
    p, url = api_project(c)
    out = io.BytesIO()
    Image.new("RGB", (32, 32), "#334455").save(out, format="PNG")
    r = c.post(
        url + "/upload",
        data={"episode_role": "narration"},
        files={"files": ("not-a-voice.png", out.getvalue(), "image/png")},
    )
    assert r.status_code == 422 and "audio track" in r.text
    r = c.post(
        url + "/upload",
        data={"episode_role": "music"},
        files={"files": ("not-a-track.md", GUIDE.encode(), "text/markdown")},
    )
    assert r.status_code == 422
    r = c.post(
        url + "/upload",
        data={"episode_role": "sources"},
        files={"files": ("not-a-visual.wav", tone_bytes(), "audio/wav")},
    )
    assert r.status_code == 422
    assert c.get(url).json()["script"] == p["script"]
    assert c.get(url).json()["assets"] == []


def test_legacy_assembly_and_destructive_generation_are_blocked_for_guide_projects(
    isolated, monkeypatch
):
    c, _ = isolated
    p, url = api_project(c)
    for fn in ["generate_narration", "draft_script", "transcribe"]:
        monkeypatch.setattr(
            ai, fn, lambda *_: pytest.fail("No provider call is permitted")
        )
    for endpoint in [
        "/assemble",
        "/produce",
        "/production-plan",
        "/draft",
        "/narrate",
        "/transcribe/" + "a" * 16,
    ]:
        r = c.post(url + endpoint, json={})
        assert r.status_code == 400, (endpoint, r.text)
    assert c.get(url).json()["script"] == p["script"]


@pytest.mark.parametrize(
    "path", ["/episode/options", "/episode/source/S03", "/episode/cue/C01"]
)
def test_malformed_patch_objects_are_rejected(isolated, path):
    c, _ = isolated
    _, url = api_project(c)
    assert c.patch(url + path, json=[]).status_code == 422


def test_failed_cue_approval_is_not_saved_and_undo_restores_episode_state(isolated):
    c, _ = isolated
    p, url = api_project(c)
    r = c.patch(url + "/episode/cue/C01", json={"reviewed": True})
    assert r.status_code == 422
    assert c.get(url).json()["episode"].get("reviews", {}) == {}
    c.patch(url + "/episode/options", json={"brief": "Changed brief"})
    r = c.post(url + "/undo")
    assert r.status_code == 200
    assert r.json()["episode"]["brief"] != "Changed brief"


def test_guide_source_collision_never_reassigns_an_existing_id(isolated):
    c, _ = isolated
    p = c.post(
        "/api/projects", json={"title": "Collision QA", "mode": "narration"}
    ).json()
    url = "/api/projects/" + p["id"]
    p["sources"] = [
        {
            "id": "S03",
            "title": "Different source",
            "url": "https://example.org/different",
            "reviewed": True,
            "notes": "Unrelated test source",
        }
    ]
    storage.save_project(p)
    r = c.post(
        url + "/episode/import",
        json={"role": "guide", "text": GUIDE, "filename": "guide.md"},
    )
    assert r.status_code == 422
    assert c.get(url).json()["sources"] == p["sources"]


def test_source_date_label_is_drawn_in_the_video_overlay():
    p = prepared()
    episode.build(p, True)
    s = p["scenes"][0]
    a = renderer.overlay_image(p, s, 0, 854, 480, True)
    b = renderer.overlay_image(p, {**s, "source_label": ""}, 0, 854, 480, True)
    assert ImageChops.difference(a, b).crop((0, 350, 854, 415)).getbbox()


def test_real_guided_renderer_mutes_source_audio_preserves_tail_and_freezes_plan(
    isolated, monkeypatch
):
    c, root = isolated
    p, url = api_project(c)
    source = root / "S03-synthetic-pattern.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x304552:s=320x180:r=24:d=4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1600:sample_rate=48000:duration=4",
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    picture = io.BytesIO()
    Image.new("RGB", (640, 360), "#283c47").save(picture, format="JPEG")
    files = [
        ("files", ("S01-synthetic.jpg", picture.getvalue(), "image/jpeg")),
        ("files", (source.name, source.read_bytes(), "video/mp4")),
    ]
    r = c.post(url + "/upload", data={"episode_role": "sources"}, files=files)
    assert r.status_code == 200, r.text
    r = c.post(
        url + "/upload",
        data={"episode_role": "narration"},
        files={"files": ("synthetic-voice.wav", tone_bytes(), "audio/wav")},
    )
    assert r.status_code == 200
    v = r.json()["assets"][-1]
    assert (
        c.patch(url + "/episode/options", json={"narration_id": v["id"]}).status_code
        == 200
    )
    assert c.post(url + "/episode/autolink", json={}).status_code == 200
    for sid in ("S01", "S03"):
        assert (
            c.patch(
                url + "/episode/source/" + sid,
                json={
                    "license": "Synthetic QA media created locally, not case evidence.",
                    "rights_confirmed": True,
                },
            ).status_code
            == 200
        )
    assert (
        c.patch(
            url + "/episode/cue/C01", json={"reviewed": True, "in": 1, "out": 2}
        ).status_code
        == 200
    )
    assert c.patch(url + "/episode/cue/C02", json={"reviewed": True}).status_code == 200
    r = c.post(url + "/episode/build", json={"allow_placeholders": True})
    assert r.status_code == 200, r.text
    p = r.json()["project"]
    assert editorial.inspect(p)["ready_for_draft"]
    missing_consent = c.post(url + "/render", json={"draft": True})
    assert (
        missing_consent.status_code == 400
        and "Explicitly allow" in missing_consent.text
    )
    calls = []
    run = renderer.run

    def capture(command, cancelled=None):
        calls.append(command[:])
        return run(command, cancelled)

    monkeypatch.setattr(renderer, "run", capture)
    record = server.write_export(
        p,
        {"resolution": "480p", "draft": True, "captions": True},
        lambda *_: None,
        lambda: False,
    )
    folder = storage.DATA / "exports" / record["id"]
    out = folder / "documentary.mp4"
    info = renderer.probe(out)
    assert info["has_audio"] and info["width"] == 854
    assert info["duration"] >= 6.04 and info["duration"] < 6.14
    assert (folder / "episode-plan.md").exists() and record[
        "episode_plan_url"
    ].endswith("/episode-plan.md")
    assert "Source audio is muted" in (folder / "episode-plan.md").read_text()
    assert (
        json.loads((folder / "project.json").read_text())["episode"]["plan"][
            "input_digest"
        ]
        == p["episode"]["plan"]["input_digest"]
    )
    # A bounded guide clip has no stream_loop. Music may loop; no music is used here.
    assert all("-stream_loop" not in command for command in calls)
    final = " ".join(str(v) for v in calls[-1])
    assert "asplit=" not in final and "asetpts=PTS-STARTPTS" in final
    decoded = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(out),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "f32le",
            "pipe:1",
        ],
        check=True,
        capture_output=True,
    ).stdout
    audio = np.frombuffer(decoded, dtype=np.float32)

    def peak(start, end):
        section = audio[int(start * 16000) : int(end * 16000)]
        spectrum = np.abs(np.fft.rfft(section * np.hanning(len(section))))
        return np.fft.rfftfreq(len(section), 1 / 16000)[int(np.argmax(spectrum))]

    assert abs(peak(0.3, 0.8) - 440) < 8 and abs(peak(5.7, 6.0) - 880) < 8
    frozen = (folder / "episode-plan.md").read_bytes()
    p["episode"]["brief"] = "After-export change"
    storage.save_project(p)
    assert (folder / "episode-plan.md").read_bytes() == frozen


def test_guide_director_preserves_narration_but_supports_look_captions_and_music(
    isolated,
):
    c, _ = isolated
    p = prepared()
    episode.build(p, True)
    p.update(
        created_at=storage.now(),
        updated_at=storage.now(),
        undo=[],
        messages=[],
        exports=[],
    )
    storage.save_project(p)
    url = "/api/projects/" + p["id"]
    before = copy.deepcopy(p["scenes"])
    r = c.post(url + "/command", json={"instruction": "set scene 1 to 8 seconds"})
    assert r.status_code == 400 and "Episode setup" in r.text
    assert c.get(url).json()["scenes"] == before
    r = c.post(url + "/command", json={"instruction": "set music to 8%"})
    assert r.status_code == 200, r.text
    latest = c.get(url).json()
    assert latest["music_volume"] == 0.08
    assert (
        latest["narration_id"] == p["narration_id"]
        and episode.analyze(latest)["plan_current"]
    )
    r = c.post(url + "/command", json={"instruction": "use the archive look"})
    assert r.status_code == 200
    assert c.get(url).json()["look"] == "archive"


def test_factual_source_annotations_do_not_change_spoken_narration_or_cuts():
    p = prepared()
    episode.build(p, True)
    p["scenes"][0]["source_ids"] = ["S03"]
    p["script"] = editorial.script_from_scenes(p["scenes"])
    assert episode.analyze(p)["plan_current"]
    assert not any(i["blocks_draft"] for i in episode.issues(p))


@pytest.mark.parametrize("role", ["narration_id", "music_id"])
def test_bound_source_audio_cannot_leak_into_a_voice_or_music_role(role):
    p = prepared()
    episode.build(p, True)
    p[role] = p["episode"]["bindings"]["S03"]["asset_id"]
    assert any(
        i["code"] == "episode_source_audio_role" and i["blocks_draft"]
        for i in episode.issues(p)
    )
