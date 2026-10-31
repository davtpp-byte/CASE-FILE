"""Local regression tests. Provider responses are mocked; no paid calls are made."""

import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

import ai
import app as server
import renderer
import storage


def make(
    client,
    script="A careful documentary begins with a source.\n\nThe producer reviews the facts before publication.",
):
    p = client.post(
        "/api/projects",
        json={"title": "Test documentary", "mode": "script", "target_minutes": 25},
    ).json()
    assert (
        client.patch("/api/projects/" + p["id"], json={"script": script}).status_code
        == 200
    )
    result = client.post("/api/projects/" + p["id"] + "/assemble")
    assert result.status_code == 200, result.text
    return result.json()


def test_project_save_and_script_assembly(isolated):
    c, _ = isolated
    p = make(c)
    assert len(p["scenes"]) == 2
    assert all(s["duration"] >= 0.5 for s in p["scenes"])
    assert p["script_dirty"] is False
    assert p["scenes"][1]["audio_start"] == p["scenes"][0]["duration"]
    assert c.get("/api/projects/" + p["id"]).json()["script"] == p["script"]


def test_unapplied_script_is_marked(isolated):
    c, _ = isolated
    p = make(c)
    new = c.patch(
        "/api/projects/" + p["id"], json={"script": "A different script."}
    ).json()
    assert new["script_dirty"] is True
    assert new["scenes"] == p["scenes"]
    assert (
        c.post(
            "/api/projects/" + p["id"] + "/render", json={"draft": False}
        ).status_code
        == 400
    )


def test_local_director_and_undo_without_ai(isolated):
    c, _ = isolated
    p = make(c)
    result = c.post(
        "/api/projects/" + p["id"] + "/command",
        json={"instruction": "use the archive look"},
    )
    assert result.status_code == 200
    assert result.json()["project"]["look"] == "archive"
    undone = c.post("/api/projects/" + p["id"] + "/undo").json()
    assert undone["look"] == "noir"


def test_duration_command_and_reorder(isolated):
    c, _ = isolated
    p = make(c)
    base = "/api/projects/" + p["id"]
    result = c.post(
        base + "/command", json={"instruction": "set scene 2 to 12 seconds"}
    ).json()["project"]
    assert result["scenes"][1]["duration"] == 12
    expected = result["scenes"][1]["audio_start"]
    result = c.post(
        base + "/command", json={"instruction": "move scene 2 to 1"}
    ).json()["project"]
    assert result["scenes"][0]["id"] == p["scenes"][1]["id"]
    assert result["scenes"][0]["audio_start"] == expected


def test_unknown_creative_command_requires_key(isolated):
    c, _ = isolated
    p = make(c)
    r = c.post(
        "/api/projects/" + p["id"] + "/command",
        json={"instruction": "Rewrite the opening in a calmer voice"},
    )
    assert r.status_code == 412
    assert storage.get_project(p["id"])["scenes"] == p["scenes"]


def test_ai_features_fail_honestly_without_key(isolated):
    c, _ = isolated
    p = make(c)
    for endpoint in ["research", "draft", "narrate"]:
        r = c.post("/api/projects/" + p["id"] + "/" + endpoint)
        assert r.status_code == 412
    assert not c.get("/api/config").json()["connected"]


def test_session_header_is_private_and_iframe_compatible(isolated):
    c, _ = isolated
    first, second = "a" * 32, "b" * 32
    server.SESSIONS[first] = {"key": "test-only-never-real", "model": "test-model"}
    one = c.get("/api/config", headers={"X-Casefile-Session": first})
    two = c.get("/api/config", headers={"X-Casefile-Session": second})
    assert one.json()["connected"] is True
    assert two.json()["connected"] is False
    assert "test-only-never-real" not in one.text
    assert "key" not in one.json()


def test_source_review_and_unsafe_url_validation(isolated):
    c, _ = isolated
    p = make(c)
    base = "/api/projects/" + p["id"]
    assert (
        c.post(
            base + "/sources", json={"title": "Bad link", "url": "javascript:alert(1)"}
        ).status_code
        == 422
    )
    source = c.post(
        base + "/sources",
        json={
            "title": "Producer interview",
            "url": "",
            "notes": "An offline primary recording.",
        },
    ).json()["sources"][0]
    assert source["reviewed"] is False
    p = c.patch(base + "/sources/" + source["id"], json={"reviewed": True}).json()
    assert p["sources"][0]["reviewed"] is True
    assert "Producer interview" in c.get(base + "/sources.md").text


def test_upload_image_and_text(isolated):
    c, root = isolated
    p = make(c)
    image = root / "test.jpg"
    Image.new("RGB", (640, 360), "#25333a").save(image)
    with image.open("rb") as f:
        r = c.post(
            "/api/projects/" + p["id"] + "/upload",
            files=[
                ("files", ("scenery.jpg", f, "image/jpeg")),
                ("files", ("script.txt", b"A newly imported script.", "text/plain")),
            ],
        )
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["script"] == "A newly imported script."
    assert p["script_dirty"] is True
    assert p["assets"][0]["kind"] == "image"
    assert p["assets"][0]["width"] == 640
    assert renderer.asset_path(p["assets"][0]).exists()
    assert not p["assets"][0]["license"]


def test_unsupported_upload_rejected(isolated):
    c, _ = isolated
    p = make(c)
    r = c.post(
        "/api/projects/" + p["id"] + "/upload",
        files={"files": ("unsafe.html", b"<script>bad()</script>", "text/html")},
    )
    assert r.status_code == 422


def test_project_fields_and_missing_projects(isolated):
    c, _ = isolated
    p = make(c)
    assert (
        c.patch("/api/projects/" + p["id"], json={"path": "/etc/passwd"}).status_code
        == 422
    )
    assert c.get("/api/projects/not-a-real-id").status_code == 404
    assert c.post("/api/projects", json={"target_minutes": 100}).status_code == 422


def test_manual_narration_edit_detaches_stale_voice(isolated):
    c, _ = isolated
    p = make(c)
    p["assets"].append(
        {
            "id": storage.uid(),
            "name": "test voice",
            "kind": "audio",
            "has_audio": True,
            "duration": 10,
        }
    )
    p["narration_id"] = p["assets"][0]["id"]
    storage.save_project(p)
    p["scenes"][0]["narration"] = "Changed narration text."
    p = c.patch("/api/projects/" + p["id"], json={"scenes": p["scenes"]}).json()
    assert p["narration_id"] is None
    assert p["review"]["facts"] is False


def test_final_export_and_empty_timeline_gates(isolated):
    c, _ = isolated
    p = make(c)
    assert (
        c.post(
            "/api/projects/" + p["id"] + "/render", json={"draft": False}
        ).status_code
        == 400
    )
    blank = c.post("/api/projects", json={"title": "Blank"}).json()
    assert (
        c.post(
            "/api/projects/" + blank["id"] + "/render", json={"draft": True}
        ).status_code
        == 400
    )


def test_srt_has_monotonic_cues_and_omits_source_ids(isolated):
    c, _ = isolated
    p = make(c, "A documented claim. [S1]\n\nThe next scene begins here.")
    srt = c.get("/api/projects/" + p["id"] + "/captions.srt").text
    assert "00:00:00,000 -->" in srt
    assert "[S1]" not in srt
    assert "The next scene" in srt
    assert (
        renderer.scene_captions(p["scenes"][0])[-1]["end"] <= p["scenes"][0]["duration"]
    )


def test_research_adapter_extracts_citations(monkeypatch):
    called = {}

    class Fake:
        def json(self):
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "A fictional test brief.",
                                "annotations": [
                                    {
                                        "type": "url_citation",
                                        "url": "https://example.org/record",
                                        "title": "Test record",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }

    def fake(config, endpoint, payload):
        called.update(payload)
        return Fake()

    monkeypatch.setattr(ai, "request", fake)
    result = ai.research(
        {"key": "test"}, {"topic": "Fictional unit test"}, lambda *_: None
    )
    assert called["tools"][0]["type"] == "web_search"
    assert result["sources"][0]["url"] == "https://example.org/record"
    assert result["sources"][0]["reviewed"] is False


def test_invalid_ai_plan_is_not_saved(isolated):
    c, _ = isolated
    p = make(c)
    before = storage.get_project(p["id"])
    with pytest.raises(ValueError):
        server.apply_plan(
            p,
            {
                "operations": [
                    {"op": "arbitrary_shell_command", "command": "not allowed"}
                ]
            },
        )
    assert storage.get_project(p["id"]) == before


def test_renderer_real_picture_audio_ducking_and_source_reorder(isolated):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg is required for the media integration test")
    c, root = isolated
    p = make(c, "First section.\n\nSecond section.")
    voice = root / "voice.wav"
    music = root / "music.wav"
    image = root / "scene.jpg"
    Image.new("RGB", (960, 540), "#253943").save(image)
    # Test tones are not human or AI narration. Reverse the two source ranges.
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=500:duration=1.5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=900:duration=1.5",
            "-filter_complex",
            "[0:a][1:a]concat=n=2:v=0:a=1[a]",
            "-map",
            "[a]",
            str(voice),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=200:duration=3",
            str(music),
        ],
        check=True,
        capture_output=True,
    )

    def asset(path, kind):
        return {
            "id": storage.uid(),
            "name": path.name,
            "kind": kind,
            "has_audio": kind == "audio",
            "path": str(path.relative_to(storage.ROOT)),
        }

    va, ma, im = asset(voice, "audio"), asset(music, "audio"), asset(image, "image")
    p.update(assets=[va, ma, im], narration_id=va["id"], music_id=ma["id"])
    for i, s in enumerate(p["scenes"]):
        s.update(
            duration=1.5,
            audio_duration=1.5,
            audio_start=1.5 if i == 0 else 0,
            asset_id=im["id"],
            show_title=False,
            transition="cut",
        )
    out = root / "actual-render.mp4"
    info = renderer.render(
        p,
        {"resolution": "480p", "draft": True, "captions": True},
        out,
        lambda *_: None,
        lambda: False,
    )
    metadata = renderer.probe(out)
    assert info["audio"] is True
    assert metadata["width"] == 854 and metadata["height"] == 480
    assert abs(metadata["duration"] - 3) < 0.12
    assert metadata["has_audio"] and out.stat().st_size > 10000
    decoded = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(out),
            "-t",
            "1",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "8000",
            "-f",
            "f32le",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    samples = np.frombuffer(decoded.stdout, dtype=np.float32)
    dominant = np.fft.rfftfreq(len(samples), 1 / 8000)[
        np.argmax(abs(np.fft.rfft(samples)))
    ]
    assert abs(dominant - 900) < 5, (
        f"Expected the second source range first, got {dominant} Hz"
    )
