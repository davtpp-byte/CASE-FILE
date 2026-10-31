"""Sanitized synthetic CapCut/SRT fixtures; no real recordings or private metadata.

Full user exports are validated separately in qa, never bundled as test fixtures.
"""

import copy
import json

import pytest

import app as server
import episode
import renderer
import storage
import timing_io
from test_episode import local_project, voice


def draft(grouped=False, substitution=False):
    p = local_project()
    materials, segments = [], []
    for i, section in enumerate(p["episode"]["script"]["sections"]):
        text = section["text"]
        values = [t[0] for t in episode.tokens(text)]
        if substitution and i == 0:
            values[0] = "Furst"
            text = text.replace("First", "Furst", 1)
        if grouped:
            values[:2] = [" ".join(values[:2])]
        start = 166666 if i == 0 else 3200000
        span = 2033334 if i == 0 else 2200000
        materials.append(
            {
                "id": f"t{i}",
                "content": json.dumps({"text": text}),
                "words": {
                    "text": values,
                    "start_time": [n * 150 for n in range(len(values))],
                    "end_time": [(n + 1) * 150 for n in range(len(values))],
                },
            }
        )
        segments.append(
            {
                "material_id": f"t{i}",
                "target_timerange": {"start": start, "duration": span},
                "speed": 1,
            }
        )
    return {
        "duration": 6040000,
        "fps": 30,
        "device_id": "PRIVATE-DEVICE-IDENTIFIER",
        "mac_address": "PRIVATE-MAC-ADDRESS",
        "tracks": [
            {"type": "text", "segments": segments},
            {
                "type": "audio",
                "segments": [
                    {
                        "material_id": "audio",
                        "target_timerange": {"start": 0, "duration": 6040000},
                        "source_timerange": {"start": 0, "duration": 6040000},
                        "speed": 1,
                    }
                ],
            },
        ],
        "materials": {
            "texts": materials,
            "audios": [
                {
                    "id": "audio",
                    "path": r"C:\Private-User\Secret-folder\synthetic-narration.mp3",
                }
            ],
        },
    }


def parsed(data=None):
    return episode.parse_timings(json.dumps(data or draft()), "draft_info.json")


def continuous_srt(data=None):
    d = data or draft()
    texts = [json.loads(m["content"])["text"] for m in d["materials"]["texts"]]
    return f"1\n00:00:00,167 --> 00:00:03,200\n{texts[0]}\n\n2\n00:00:03,200 --> 00:00:06,000\n{texts[1]}\n"


def imported(data=None):
    p = local_project()
    d = data or draft()
    episode.import_document(p, "timings", json.dumps(d), "draft_info.json")
    episode.import_document(
        p, "timings", continuous_srt(d), "captions_continuous.srt.md"
    )
    return p


def test_native_ms_words_and_us_target_range_are_not_interpolated():
    t = parsed(draft(grouped=True))
    first = t["units"][0]
    assert first["text"] == "First synthetic"
    assert first["start"] == 0.166666
    assert first["end"] == pytest.approx(0.316666)
    assert first == t["words"][0]
    assert t["precision"] == "provided-timed-units"
    assert t["grouped_units"] == 2
    assert not any(u["word"] == "synthetic" and u["caption"] == 1 for u in t["units"])


def test_group_interior_cue_is_estimated_not_a_manufactured_word_boundary():
    p = imported(draft(grouped=True))
    p["episode"]["guide"]["cues"][0]["anchor"] = (
        "synthetic sentence describes only a technical test"
    )
    r = episode.analyze(p)
    assert not r["errors"]
    assert r["placements"][0]["timing_source"] == "estimated"
    assert r["placements"][0]["narration_start"] > 0.166666


def test_single_word_substitution_is_only_a_review_candidate():
    p = imported(draft(substitution=True))
    r = episode.analyze(p)
    assert not r["errors"]
    assert r["timing_candidate_cues"] == ["C01"]
    assert r["placements"][0]["narration_start"] == 0.166666
    assert r["placements"][0]["timing_source"] == "word boundary; text review"
    assert r["transcript_comparison"]["difference_spans"] == 1
    assert "Furst" in renderer.project_srt(p)  # Do not silently correct captions.
    assert "First" in p["script"]


def test_private_platform_metadata_and_paths_are_not_retained():
    t = parsed()
    serialized = json.dumps(t)
    for value in [
        "PRIVATE-DEVICE-IDENTIFIER",
        "PRIVATE-MAC-ADDRESS",
        "Private-User",
        "Secret-folder",
        "device_id",
        "mac_address",
    ]:
        assert value not in serialized
    assert t["audio_reference_filename"] == "synthetic-narration.mp3"
    assert t["audio_verified"] is False


def test_small_frame_rounding_word_end_is_preserved_not_clamped():
    d = draft()
    span_ms = d["tracks"][0]["segments"][0]["target_timerange"]["duration"] / 1000
    d["materials"]["texts"][0]["words"]["end_time"][-1] = span_ms + 20
    t = parsed(d)
    assert t["word_end_frame_rounding_count"] == 1
    assert t["maximum_word_end_overrun_ms"] == 20
    assert t["units"][len(d["materials"]["texts"][0]["words"]["text"]) - 1][
        "end"
    ] == pytest.approx(t["native_captions"][0]["end"] + 0.02)


@pytest.mark.parametrize(
    "change,match",
    [
        ("audio-speed", "normal speed"),
        ("audio-trim", "untrimmed"),
        ("multiple-audio", "one continuous"),
        ("text-speed", "Retimed"),
        ("arrays", "different lengths"),
        ("outside", "outside its caption"),
        ("no-words", "No usable"),
        ("negative", "finite"),
        ("overlap", "Overlapping"),
        ("nan", "finite"),
    ],
)
def test_ambiguous_or_invalid_native_clocks_are_rejected(change, match):
    d = draft()
    a = d["tracks"][1]["segments"][0]
    w = d["materials"]["texts"][0]["words"]
    if change == "audio-speed":
        a["speed"] = 1.1
    if change == "audio-trim":
        a["source_timerange"]["start"] = 1000000
    if change == "multiple-audio":
        d["tracks"][1]["segments"].append(copy.deepcopy(a))
    if change == "text-speed":
        d["tracks"][0]["segments"][0]["speed"] = 2
    if change == "arrays":
        w["end_time"].pop()
    if change == "outside":
        w["end_time"][-1] = 4000
    if change == "no-words":
        for m in d["materials"]["texts"]:
            m["words"] = {}
    if change == "negative":
        w["start_time"][0] = -1
    if change == "overlap":
        d["tracks"][0]["segments"][1]["target_timerange"]["start"] = 2000000
    if change == "nan":
        w["start_time"][0] = float("nan")
    with pytest.raises(ValueError, match=match):
        parsed(d)


@pytest.mark.parametrize("reverse", [False, True])
def test_matching_srt_and_native_units_pair_in_either_order(reverse):
    p = local_project()
    files = [
        ("draft_info.json", json.dumps(draft())),
        ("captions_continuous.srt.md", continuous_srt()),
    ]
    for name, raw in files[::-1] if reverse else files:
        episode.import_document(p, "timings", raw, name)
    t = p["episode"]["timings"]
    assert t["source_kind"] == "capcut"
    assert t["captions_source"] == "srt"
    assert t["captions"][0]["end"] == 3.2
    assert t["units"][0]["start"] == 0.166666
    assert t["caption_end_hold_difference_count"] == 2
    assert len(t["sources"]) == 2
    assert episode.analyze(p)["duration"] == 6.04


def test_mismatched_srt_is_not_shifted_or_silently_combined():
    p = imported()
    old_hash = p["episode"]["timings"]["hash"]
    with pytest.raises(ValueError, match="different caption starts"):
        episode.import_document(
            p,
            "timings",
            continuous_srt().replace("00:00:03,200 -->", "00:00:03,300 -->"),
            "wrong.srt",
        )
    assert p["episode"]["timings"]["hash"] == old_hash


def test_corrected_srt_text_can_be_uploaded_without_rewriting_timing_transcript():
    p = imported(draft(substitution=True))
    episode.import_document(p, "timings", continuous_srt(), "producer-corrected.srt")
    assert p["episode"]["timings"]["caption_text_difference_count"] == 1
    assert "Furst" not in renderer.project_srt(p)
    assert p["episode"]["timings"]["units"][0]["word"] == "Furst"


def test_global_srt_is_exact_and_not_duplicated_at_visual_cuts():
    p = imported()
    plan = episode.build(p, True)
    assert plan["duration"] == pytest.approx(145 / 24)
    assert len(p["scenes"]) > 2
    assert renderer.project_srt(p) == continuous_srt()
    first = p["scenes"][0]
    assert first["duration"] == pytest.approx(4 / 24)
    assert first["captions_exact"] and first["narration"] == "First"
    assert (
        renderer.scene_captions(first) == []
    )  # Never regenerate a caption in an imported silence/gap.


def test_srt_only_preserves_blocks_but_word_starts_are_still_estimates():
    p = local_project()
    episode.import_document(p, "timings", continuous_srt(), "voice.srt.md")
    assert p["episode"]["timings"]["precision"] == "segment-interpolated"
    assert renderer.project_srt(p) == continuous_srt()
    episode.build(p, True)
    assert all(s["captions_exact"] for s in p["scenes"])
    assert "segment estimate" in episode.analyze(p)["placements"][0]["timing_source"]


def test_caption_toggle_does_not_remove_or_retime_the_imported_clock():
    p = imported()
    episode.build(p, True)
    before = episode.analyze(p)
    old_hash = p["episode"]["timings"]["hash"]
    p["captions"] = False
    after = episode.analyze(p)
    assert after["word_clock"] == before["word_clock"]
    assert after["plan_current"]
    assert p["episode"]["timings"]["hash"] == old_hash
    assert renderer.project_srt(p) == continuous_srt()


def test_short_intro_and_exact_captions_survive_general_scene_sanitization():
    p = imported()
    episode.build(p, True)
    p["scenes"] = [server.sanitize_scene(s, set()) for s in p["scenes"]]
    assert episode.analyze(p)["plan_current"]
    assert p["scenes"][0]["duration"] < 0.5
    assert renderer.scene_captions(p["scenes"][0]) == []
    assert renderer.project_srt(p) == continuous_srt()


def test_editing_supplied_caption_content_invalidates_frozen_plan():
    p = imported()
    episode.build(p, True)
    scene = next(s for s in p["scenes"] if s["captions"])
    scene["captions"][0]["text"] = "Changed outside the reviewed timing pack"
    assert not episode.analyze(p)["plan_current"]
    assert any(i["code"] == "episode_timeline_changed" for i in episode.issues(p))


def test_different_audio_duration_is_not_silently_stretched():
    p = imported()
    voice(p, 7)
    assert any("differs from the CapCut" in e for e in episode.analyze(p)["errors"])
    with pytest.raises(ValueError, match="differs from the CapCut"):
        episode.build(p, True)


def test_large_raw_draft_is_accepted_by_api_but_only_sanitized_data_is_stored(isolated):
    c, _ = isolated
    p = c.post(
        "/api/projects",
        json={"title": "Synthetic native-import test", "mode": "narration"},
    ).json()
    url = "/api/projects/" + p["id"]
    d = draft()
    d["unused_platform_blob"] = "x" * 1100000
    r = c.post(
        url + "/episode/import",
        json={"role": "timings", "text": json.dumps(d), "filename": "draft_info.json"},
    )
    assert r.status_code == 200, r.text
    saved = storage.get_project(p["id"])
    assert len(json.dumps(saved)) < 30000
    assert not saved["assets"] and saved["narration_id"] is None
    assert (
        saved["episode"]["timings"]["audio_reference_filename"]
        == "synthetic-narration.mp3"
    )
    assert (
        c.patch(url + "/episode/options", json={"confirm_transcript": True}).status_code
        == 422
    )
    assert (
        c.patch(url + "/episode/options", json={"confirm_timing": True}).status_code
        == 422
    )


def test_transcript_review_is_separate_from_timing_approval(isolated):
    c, _ = isolated
    p = imported(draft(substitution=True))
    voice(p, 6.04)
    episode.build(p, True)
    storage.save_project(p)
    url = "/api/projects/" + p["id"]
    r = c.patch(url + "/episode/options", json={"confirm_timing": True})
    assert r.status_code == 200, r.text
    assert r.json()["analysis"]["timing_reviewed"]
    assert not r.json()["analysis"]["transcript_reviewed"]
    assert any(
        i["code"] == "episode_transcript_differences"
        for i in episode.issues(r.json()["project"])
    )
    r = c.patch(url + "/episode/options", json={"confirm_transcript": True})
    assert r.status_code == 200, r.text
    assert r.json()["analysis"]["transcript_reviewed"]
    assert not any(
        i["code"] == "episode_transcript_differences"
        for i in episode.issues(r.json()["project"])
    )


def test_reuploading_native_json_does_not_silently_lose_the_srt_track():
    p = imported()
    episode.import_document(p, "timings", json.dumps(draft()), "draft_info.json")
    assert p["episode"]["timings"]["captions_source"] == "srt"
    assert renderer.project_srt(p) == continuous_srt()


@pytest.mark.parametrize("change", ["tracks", "materials", "content", "words"])
def test_bad_native_shapes_report_a_validation_error(change):
    d = draft()
    if change == "tracks":
        d["tracks"] = [None]
    if change == "materials":
        d["materials"]["audios"] = [None]
    if change == "content":
        d["materials"]["texts"][0]["content"] = "[]"
    if change == "words":
        d["materials"]["texts"][0]["words"] = [1]
    with pytest.raises(ValueError, match="Malformed"):
        parsed(d)


def test_synthetic_render_caption_on_off_preserves_audio_and_caption_holds(isolated):
    """A technical tone and flat image only, never a recording of the real case."""
    import io
    import subprocess
    import wave
    import numpy as np
    from PIL import Image, ImageChops

    _, root = isolated
    wav = root / "SYNTHETIC-technical-tone.wav"
    rate = 48000
    samples = (
        np.sin(np.arange(round(6.04 * rate)) / rate * 2 * np.pi * 440) * 3000
    ).astype("<i2")
    with wave.open(str(wav), "wb") as out:
        out.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        out.writeframes(samples.tobytes())
    d = draft()
    d["tracks"][0]["segments"][1]["target_timerange"]["start"] = 3000000
    supplied_srt = continuous_srt(d).replace("00:00:03,200", "00:00:03,000")
    p = local_project()
    episode.import_document(p, "timings", json.dumps(d), "draft_info.json")
    episode.import_document(p, "timings", supplied_srt, "captions.srt")
    a = voice(p, 6.04)
    a["path"] = str(wav.relative_to(storage.ROOT))
    a["name"] = wav.name
    image = root / "SYNTHETIC-flat-color.png"
    Image.new("RGB", (854, 480), "#233544").save(image)
    visual = {
        "id": storage.uid(),
        "kind": "image",
        "name": image.name,
        "path": str(image.relative_to(storage.ROOT)),
        "duration": 0,
        "license": "Synthetic test-created flat color, no real evidence.",
    }
    p["assets"].append(visual)
    episode.bind_source(p, "S03", {"asset_id": visual["id"], "rights_confirmed": True})
    episode.review_cue(p, "C01", {"reviewed": True, "narration_end": 2.5})
    episode.build(p, True)
    assert any(not s["narration"] and s["captions"] for s in p["scenes"])
    outputs = []
    for captions in (True, False):
        p["captions"] = captions
        out = root / (
            "synthetic-captions-on.mp4" if captions else "synthetic-captions-off.mp4"
        )
        renderer.render(
            p,
            {"resolution": "480p", "draft": True, "captions": captions},
            out,
            lambda *_: None,
            lambda: False,
        )
        info = renderer.probe(out)
        assert info["has_audio"] and info["video_duration"] == pytest.approx(
            145 / 24, abs=0.001
        )
        assert renderer.project_srt(p) == supplied_srt
        outputs.append(out)
    decoded = [
        subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(out),
                "-map",
                "0:a",
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-",
            ]
        )
        for out in outputs
    ]
    assert decoded[0] == decoded[1]
    frames = [
        Image.open(
            io.BytesIO(
                subprocess.check_output(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-ss",
                        "2.8",
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
        for out in outputs
    ]
    # 2.8s falls in a caption hold AFTER the last script word in that visual
    # scene. Captions must still appear, even though scene.narration is empty.
    assert (
        ImageChops.difference(
            frames[0].crop((70, 395, 780, 445)), frames[1].crop((70, 395, 780, 445))
        ).getbbox()
        is not None
    )


def test_timing_import_does_not_replace_existing_recording_guide_or_sources():
    p = local_project()
    a = voice(p, 6.04)
    p["assets"].append(
        {
            "id": storage.uid(),
            "kind": "image",
            "name": "Existing authorized source.png",
            "duration": 0,
        }
    )
    p["episode"]["reviews"] = {"C01": {"in": 1, "out": 2, "reviewed": False}}
    before = copy.deepcopy(p)
    episode.import_document(p, "timings", json.dumps(draft()), "draft_info.json")
    episode.import_document(p, "timings", continuous_srt(), "captions.srt")
    assert p["narration_id"] == a["id"]
    for key in ("assets", "script", "sources", "narration_id", "music_id"):
        assert p[key] == before[key]
    for key in ("script", "guide", "reviews", "bindings"):
        assert p["episode"][key] == before["episode"][key]
    assert episode.analyze(p)["has_voice"]


def test_index_asset_urls_match_the_api_version_for_cache_refresh(isolated):
    c, _ = isolated
    response = c.get("/")
    assert response.status_code == 200
    assert "/assets/app.js?v=" + server.app.version in response.text
    assert "/assets/app.css?v=" + server.app.version in response.text
