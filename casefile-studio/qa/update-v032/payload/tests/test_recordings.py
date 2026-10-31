"""Recorded narration/raw footage orchestration; provider transcription is mocked."""

import pytest
import ai
import editorial
import production
import renderer
import storage
from test_production import ready, run


def test_recording_transcription_is_source_aligned_and_reused(isolated, monkeypatch):
    c, root = isolated
    p = ready(c, root)
    voice = next(a for a in p["assets"] if a["id"] == p["narration_id"])
    p.update(
        script="", scenes=[], script_dirty=False, narration_id=None, mode="narration"
    )
    storage.save_project(p)
    calls = []

    def transcribe(*_):
        calls.append("transcribe")
        return [
            {"start": 0.5, "end": 2, "text": "Synthetic recognition fixture."},
            {"start": 2, "end": 3.8, "text": "Not actual case content."},
        ]

    monkeypatch.setattr(ai, "transcribe", transcribe)
    monkeypatch.setattr(
        ai,
        "research",
        lambda *_: pytest.fail("A recording must not trigger topic research"),
    )
    options = production.Options(allow_paid=True, render=False)
    result = run(p, options, {"key": "test-only"})
    assert result["outcome"] == "assembled"
    latest = storage.get_project(p["id"])
    assert (
        latest["script_origin"] == "transcript"
        and latest["narration_id"] == voice["id"]
    )
    assert latest["scenes"][0]["audio_start"] == 0.5
    assert latest["scenes"][0]["audio_duration"] == 3.3
    assert latest["scenes"][0]["captions"][0]["start"] == 0
    assert latest["scenes"][0]["timing"] == "transcribed"
    assert latest["review"]["facts"] is False
    run(latest, options, {"key": "test-only"})
    assert calls == ["transcribe"]


def test_raw_footage_assembly_uses_original_video_and_voice_in_points():
    video = {"id": "a" * 16, "kind": "video", "duration": 40, "has_audio": True}
    project = {"assets": [video]}
    segments = [
        {"start": 1.0, "end": 10.0, "text": "First synthetic segment."},
        {"start": 10.0, "end": 21.0, "text": "Second synthetic segment."},
        {"start": 24.0, "end": 32.0, "text": "Third synthetic segment."},
    ]
    scenes = production.transcript_scenes(project, video, segments)
    assert len(scenes) == 2
    assert [s["trim_start"] for s in scenes] == [1.0, 24.0]
    assert [s["audio_start"] for s in scenes] == [1.0, 24.0]
    assert [s["duration"] for s in scenes] == [20.0, 8.0]
    assert all(
        s["asset_id"] == video["id"] and s["transition"] == "cut" for s in scenes
    )
    assert scenes[0]["captions"][1]["start"] == 9.0


def test_multiple_recordings_require_selection_before_paid_work(isolated, monkeypatch):
    c, root = isolated
    p = ready(c, root)
    voice = next(a for a in p["assets"] if a["id"] == p["narration_id"])
    p["assets"].append({**voice, "id": storage.uid(), "name": "A second recording"})
    p.update(mode="footage", script="", scenes=[], sources=[], narration_id=None)
    storage.save_project(p)
    monkeypatch.setattr(
        ai,
        "transcribe",
        lambda *_: pytest.fail("Do not guess among several recordings"),
    )
    monkeypatch.setattr(
        ai,
        "research",
        lambda *_: pytest.fail("Do not research instead of asking for a recording"),
    )
    result = run(p, production.Options(allow_paid=True), {"key": "test-only"})
    assert result["stage"] == "recording" and "explicit selection" in result["message"]


@pytest.mark.parametrize("refs", ["[S1 S2]", "[ S1, S2 ]", "[s1;2]", "[S1,2]"])
def test_reference_formats_are_consistent_in_checks_and_renderer(refs):
    text = "A synthetic record. " + refs
    assert editorial.source_ids(text) == ["S1", "S2"]
    assert (
        editorial.strip_references(text)
        == renderer.plain(text)
        == "A synthetic record."
    )
