"""Guided production and editorial regression tests. No real provider calls."""

import copy
import wave

import numpy as np
import pytest
from PIL import Image
from test_studio import make

import ai
import app as server
import editorial
import production
import storage


def run(p, options=None, cfg=None, export_fn=None, cancelled=None):
    return production.run(
        p["id"],
        options or production.Options(),
        cfg,
        lambda *_: None,
        cancelled or (lambda: False),
        export_fn or (lambda *_: pytest.fail("Unexpected export")),
    )


def ready(c, root):
    p = make(
        c,
        "A fictional test record supports this sentence. [S1]\n\nThe next synthetic scene cites the same test record. [S1]",
    )
    image = root / "licensed-test.jpg"
    Image.new("RGB", (640, 360), "#2d4148").save(image)
    audio = root / "synthetic-tone.wav"
    with wave.open(str(audio), "wb") as out:
        out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        samples = (np.sin(np.arange(64000) / 16000 * 2 * np.pi * 600) * 2000).astype(
            "<i2"
        )
        out.writeframes(samples.tobytes())
    visual = {
        "id": storage.uid(),
        "name": "Synthetic test scenery",
        "kind": "image",
        "path": str(image.relative_to(storage.ROOT)),
        "license": "Procedural unit-test image; no real people or events.",
        "duration": 0,
        "has_audio": False,
    }
    voice = {
        "id": storage.uid(),
        "name": "Synthetic test tone (not speech)",
        "kind": "audio",
        "path": str(audio.relative_to(storage.ROOT)),
        "license": "Generated unit-test tone, not a human or AI narrator.",
        "duration": 4,
        "has_audio": True,
    }
    p["assets"] = [visual, voice]
    p["narration_id"] = voice["id"]
    p["sources"] = [
        {
            "id": "S1",
            "title": "Synthetic unit-test record",
            "url": "",
            "notes": "Fictional structural test material only.",
            "reviewed": True,
        }
    ]
    for i, s in enumerate(p["scenes"]):
        s.update(
            duration=2,
            audio_start=i * 2,
            audio_duration=2,
            asset_id=visual["id"],
            source_ids=["S1"],
            motion="none",
            transition="cut",
        )
    p["script"] = editorial.script_from_scenes(p["scenes"])
    p["review"] = {k: True for k in p["review"]}
    storage.save_project(p)
    return p


def test_provided_script_is_not_claimed_as_researched(isolated):
    c, _ = isolated
    p = make(c)
    plan = production.plan(p)
    assert plan["steps"][0]["status"] == "provided"
    assert plan["human_review_required"] is True


def test_no_paid_consent_no_provider_request(isolated, monkeypatch):
    c, _ = isolated
    p = c.post("/api/projects", json={"title": "Fictional test topic"}).json()
    monkeypatch.setattr(
        ai, "research", lambda *_: pytest.fail("Must not charge without consent")
    )
    result = run(p, cfg={"key": "test-only"})
    assert result["outcome"] == "paused" and result["stage"] == "research"
    assert "paid AI approval" in result["message"]
    assert storage.get_project(p["id"])["sources"] == []


def test_paid_consent_without_connection_sends_nothing(isolated, monkeypatch):
    c, _ = isolated
    p = c.post("/api/projects", json={"title": "Fictional test topic"}).json()
    monkeypatch.setattr(
        ai, "research", lambda *_: pytest.fail("Must not request without a key")
    )
    result = run(p, production.Options(allow_paid=True))
    assert "No paid request was sent" in result["message"]
    assert storage.get_project(p["id"])["production"]["next_tab"] == "settings"


def test_research_pauses_and_resume_does_not_recharge(isolated, monkeypatch):
    c, _ = isolated
    p = c.post("/api/projects", json={"title": "Fictional research fixture"}).json()
    calls = []

    def research(*_):
        calls.append("research")
        return {
            "research_report": "Synthetic report, not real case facts.",
            "sources": [
                {
                    "id": "S1",
                    "title": "Synthetic source lead",
                    "notes": "Needs producer review.",
                    "url": "https://example.org",
                    "reviewed": False,
                }
            ],
        }

    monkeypatch.setattr(ai, "research", research)
    monkeypatch.setattr(
        ai, "draft_script", lambda *_: pytest.fail("Source review must come first")
    )
    opts = production.Options(
        allow_paid=True, generate_voice=True, allow_placeholders=True, allow_silent=True
    )
    result = run(p, opts, {"key": "test-only"})
    assert result["stage"] == "source_review"
    assert calls == ["research"]
    second = run(storage.get_project(p["id"]), opts, {"key": "test-only"})
    assert second["stage"] == "source_review" and calls == ["research"]
    assert not storage.get_project(p["id"])["sources"][0]["reviewed"]


def test_ai_script_requires_approval_before_voice_and_reuses_voice(
    isolated, monkeypatch
):
    c, root = isolated
    p = c.post("/api/projects", json={"title": "Fictional writing fixture"}).json()
    p["sources"] = [
        {
            "id": "S1",
            "title": "Fictional producer record",
            "notes": "Synthetic checked notes for testing.",
            "reviewed": True,
            "url": "",
        }
    ]
    storage.save_project(p)
    calls = []

    def draft(*_):
        calls.append("draft")
        return {
            "script": "A fictional scripted sentence. [S1]",
            "note": "Synthetic test only.",
        }

    def narrate(cfg, project, progress, cancelled):
        calls.append("voice")
        path = root / "fake-voice.wav"
        with wave.open(str(path), "wb") as out:
            out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            out.writeframes(b"\x00\x00" * 64000)
        asset = {
            "id": storage.uid(),
            "name": "Synthetic test silence",
            "kind": "audio",
            "has_audio": True,
            "duration": 4,
            "path": str(path.relative_to(storage.ROOT)),
            "license": "Synthetic unit test only.",
        }
        scenes = copy.deepcopy(project["scenes"])
        scenes[0].update(
            duration=4, audio_start=0, audio_duration=4, timing="scene-aligned"
        )
        return asset, scenes

    monkeypatch.setattr(ai, "draft_script", draft)
    monkeypatch.setattr(ai, "generate_narration", narrate)
    opts = production.Options(
        allow_paid=True, generate_voice=True, allow_placeholders=True, render=False
    )
    first = run(p, opts, {"key": "test-only"})
    assert first["stage"] == "script_review" and calls == ["draft"]
    p = storage.get_project(p["id"])
    assert p["script_origin"] == "ai" and not editorial.script_approved(p)
    blocked = run(p, opts, {"key": "test-only"})
    assert blocked["stage"] == "script_review" and calls == ["draft"]
    approval = c.post(
        "/api/projects/" + p["id"] + "/approve-script", json={"acknowledge": True}
    )
    assert approval.status_code == 200, approval.text
    assert editorial.script_approved(approval.json())
    resumed = run(approval.json(), opts, {"key": "test-only"})
    assert resumed["outcome"] == "assembled" and calls == ["draft", "voice"]
    run(storage.get_project(p["id"]), opts, {"key": "test-only"})
    assert calls == ["draft", "voice"], (
        "A saved voice must be reused, not silently recharged"
    )


def test_character_cap_blocks_voice_request(isolated, monkeypatch):
    c, _ = isolated
    p = make(c, "documentation " * 150)
    monkeypatch.setattr(
        ai,
        "generate_narration",
        lambda *_: pytest.fail("Character cap must stop before a paid voice request"),
    )
    result = run(
        p,
        production.Options(
            allow_paid=True,
            generate_voice=True,
            allow_placeholders=True,
            max_voice_characters=1000,
        ),
        {"key": "test-only"},
    )
    assert result["stage"] == "narration" and "character cap" in result["message"]


def test_unresolved_claims_block_paid_voice_even_with_signoffs(isolated, monkeypatch):
    c, root = isolated
    p = ready(c, root)
    p["script"] += " [NEEDS SOURCE]"
    p["scenes"][0]["narration"] += " [NEEDS SOURCE]"
    storage.save_project(p)
    sid = c.cookies.get("casefile_session")
    server.SESSIONS[sid] = {"key": "test-only-not-real"}
    monkeypatch.setattr(
        ai,
        "generate_narration",
        lambda *_: pytest.fail("No paid speech for unresolved claims"),
    )
    r = c.post("/api/projects/" + p["id"] + "/narrate")
    assert r.status_code == 400
    assert "NEEDS SOURCE" in r.text
    report = editorial.inspect(p)
    assert any(i["code"] == "unresolved_claims" for i in report["issues"])
    assert (
        c.post(
            "/api/projects/" + p["id"] + "/render", json={"draft": False}
        ).status_code
        == 400
    )


def test_unknown_source_id_blocks_approval_and_final(isolated):
    c, root = isolated
    p = ready(c, root)
    p["scenes"][0]["source_ids"] = ["S99"]
    p["script"] = editorial.script_from_scenes(p["scenes"])
    p["script_origin"] = "ai"
    storage.save_project(p)
    assert (
        c.post(
            "/api/projects/" + p["id"] + "/approve-script", json={"acknowledge": True}
        ).status_code
        == 400
    )
    assert (
        c.post(
            "/api/projects/" + p["id"] + "/render", json={"draft": False}
        ).status_code
        == 400
    )
    assert editorial.script_problems(p)["unknown_sources"] == ["S99"]


def test_rights_notes_are_required_even_if_checkbox_ticked(isolated):
    c, root = isolated
    p = ready(c, root)
    assert editorial.inspect(p)["ready_for_final"] is True
    p["assets"][0]["license"] = ""
    storage.save_project(p)
    report = editorial.inspect(p)
    assert report["ready_for_final"] is False and report["ready_for_draft"] is True
    assert any(i["code"] == "rights_notes" for i in report["issues"])
    assert (
        c.post(
            "/api/projects/" + p["id"] + "/render", json={"draft": False}
        ).status_code
        == 400
    )


def test_references_survive_long_unpunctuated_script(isolated):
    c, _ = isolated
    p = make(c, ("record " * 160) + " [S1, S2]")
    assert len(p["scenes"]) == 3
    assert all(s["source_ids"] == ["S1", "S2"] for s in p["scenes"])
    assert all(len(s["narration"].split()) <= 65 for s in p["scenes"])
    assert "[S1]" in editorial.script_from_scenes(p["scenes"])
    assert all("[S1" not in s["narration"] for s in p["scenes"])


def test_scene_reference_edit_preserves_script_and_approval_invalidation(isolated):
    c, _ = isolated
    p = make(c, "Fictional source-backed sentence. [S1]")
    p["sources"] = [
        {
            "id": "S1",
            "reviewed": True,
            "title": "Synthetic source",
            "notes": "A fictional fixture.",
            "url": "",
        }
    ]
    p["script_origin"] = "ai"
    storage.save_project(p)
    approved = c.post(
        "/api/projects/" + p["id"] + "/approve-script", json={"acknowledge": True}
    ).json()
    assert approved["script_approved_hash"]
    scenes = approved["scenes"]
    scenes[0]["narration"] = "A revised fictional sentence."
    changed = c.patch("/api/projects/" + p["id"], json={"scenes": scenes}).json()
    assert "[S1]" in changed["script"]
    assert changed["script_approved_hash"] is None
    assert not editorial.script_approved(changed)


def test_style_commands_do_not_destroy_unapplied_script(isolated):
    c, _ = isolated
    p = make(c)
    proposed = "A replacement draft not yet applied."
    c.patch("/api/projects/" + p["id"], json={"script": proposed})
    r = c.post(
        "/api/projects/" + p["id"] + "/command",
        json={"instruction": "use the archive look"},
    ).json()["project"]
    assert r["script"] == proposed and r["script_dirty"] is True


def test_project_is_read_only_during_production(isolated):
    c, _ = isolated
    p = make(c)
    job = storage.uid()
    server.JOBS[job] = {
        "id": job,
        "project_id": p["id"],
        "kind": "production",
        "status": "running",
        "created_at": storage.now(),
    }
    assert (
        c.patch(
            "/api/projects/" + p["id"],
            json={"title": "Cannot overwrite while producing"},
        ).status_code
        == 409
    )
    assert c.get("/api/projects/" + p["id"] + "/preflight").status_code == 200
    assert (
        c.post("/api/projects/" + p["id"] + "/production-plan", json={}).status_code
        == 200
    )


def test_invalid_scene_reference_payload_is_rejected(isolated):
    c, _ = isolated
    p = make(c)
    p["scenes"][0]["source_ids"] = None
    assert (
        c.patch("/api/projects/" + p["id"], json={"scenes": p["scenes"]}).status_code
        == 422
    )


def test_cancel_keeps_original_story_and_marks_run(isolated):
    c, _ = isolated
    p = make(c)
    result = run(p, cancelled=lambda: True)
    latest = storage.get_project(p["id"])
    assert (
        result["outcome"] == "cancelled"
        and latest["production"]["status"] == "cancelled"
    )
    assert latest["script"] == p["script"]


def test_provider_error_does_not_fabricate_material(isolated, monkeypatch):
    c, _ = isolated
    p = c.post("/api/projects", json={"title": "Fictional topic fixture"}).json()

    def failing(*_):
        raise RuntimeError("Mock provider failure")

    monkeypatch.setattr(ai, "research", failing)
    with pytest.raises(RuntimeError):
        run(p, production.Options(allow_paid=True), {"key": "test-only"})
    latest = storage.get_project(p["id"])
    assert (
        latest["production"]["status"] == "error"
        and latest["sources"] == []
        and latest["script"] == ""
    )


def test_real_guided_export_writes_frozen_handoff_files(isolated):
    c, root = isolated
    p = ready(c, root)
    result = run(
        p, production.Options(resolution="480p"), export_fn=server.write_export
    )
    assert result["outcome"] == "complete"
    latest = storage.get_project(p["id"])
    assert latest["production"]["status"] == "complete"
    assert len(latest["exports"]) == 1 and latest["exports"][0]["draft"] is True
    folder = server.DATA / "exports" / result["export_id"]
    for name in [
        "documentary.mp4",
        "captions.srt",
        "sources.md",
        "project.json",
        "preflight.json",
        "preflight.md",
        "chapters.txt",
        "publication-notes.md",
    ]:
        assert (folder / name).is_file()
    assert "S1" in (folder / "preflight.md").read_text()
    assert "0:00" in (folder / "chapters.txt").read_text()
    assert "Synthetic test scenery" in (folder / "sources.md").read_text()


def test_audio_overrun_blocks_final_even_after_signoffs(isolated):
    c, root = isolated
    p = ready(c, root)
    p["scenes"][-1]["audio_start"] = 3.5
    storage.save_project(p)
    report = editorial.inspect(p)
    assert any(i["code"] == "audio_out_of_bounds" for i in report["issues"])
    assert report["ready_for_draft"] is True and report["ready_for_final"] is False
    assert (
        c.post(
            "/api/projects/" + p["id"] + "/render", json={"draft": False}
        ).status_code
        == 400
    )


def test_missing_media_blocks_drafts_and_names_repair_asset(isolated):
    c, root = isolated
    p = ready(c, root)
    image = p["assets"][0]
    (storage.ROOT / image["path"]).unlink()
    report = editorial.inspect(p)
    problem = next(i for i in report["issues"] if i["code"] == "missing_media_file")
    assert problem["blocks_draft"] and problem["asset_id"] == image["id"]
    assert report["ready_for_draft"] is False and report["ready_for_final"] is False
    assert (
        c.post("/api/projects/" + p["id"] + "/render", json={"draft": True}).status_code
        == 400
    )


def test_source_context_edits_invalidate_ai_approval(isolated):
    c, root = isolated
    p = ready(c, root)
    p["script_origin"] = "ai"
    storage.save_project(p)
    approved = c.post(
        "/api/projects/" + p["id"] + "/approve-script", json={"acknowledge": True}
    ).json()
    assert editorial.script_approved(approved)
    changed = c.patch(
        "/api/projects/" + p["id"] + "/sources/S1",
        json={"notes": "Changed synthetic supporting context; check the script again."},
    ).json()
    assert changed["sources"][0]["reviewed"] is False
    assert changed["script_approved_hash"] is None
    assert not editorial.script_approved(changed)


def test_undo_cannot_resurrect_approval_against_changed_sources(isolated):
    c, root = isolated
    p = ready(c, root)
    p["script_origin"] = "ai"
    storage.save_project(p)
    approved = c.post(
        "/api/projects/" + p["id"] + "/approve-script", json={"acknowledge": True}
    ).json()
    scenes = approved["scenes"]
    scenes[0]["duration"] = 2.1
    c.patch("/api/projects/" + p["id"], json={"scenes": scenes})
    c.patch(
        "/api/projects/" + p["id"] + "/sources/S1",
        json={
            "notes": "A materially revised fictional source context.",
            "reviewed": True,
        },
    )
    restored = c.post("/api/projects/" + p["id"] + "/undo").json()
    assert restored["sources"][0]["reviewed"] is True
    assert restored["script_approved_hash"] is None
    assert not editorial.script_approved(restored)
