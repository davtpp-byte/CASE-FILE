"""Inspection is explicitly unapproved; tests use synthetic technical media only."""

import copy
import json
import subprocess
import io
import wave

import numpy as np
import pytest
from PIL import Image, ImageChops

import app as server
import editorial
import episode
import renderer
import storage
from test_capcut import imported
from test_episode import voice


def unreviewed():
    p = imported()
    voice(p)
    for sid, kind in [("S03", "video"), ("S01", "image")]:
        a = {
            "id": storage.uid(),
            "name": sid + (".mp4" if kind == "video" else ".jpg"),
            "kind": kind,
            "duration": 4.0 if kind == "video" else 0,
            "has_audio": kind == "video",
            "license": "",
        }
        p["assets"].append(a)
        episode.bind_source(p, sid, {"asset_id": a["id"]})
    return p


def candidate(p, index=0):
    return episode.inspection_candidate(p, p["episode"]["guide"]["cues"][index])


def test_linked_sources_can_be_inspected_without_false_approvals():
    p = unreviewed()
    before = copy.deepcopy(p)
    r = episode.analyze(p)
    assert r["ready_cues"] == 0 and r["inspection_cues"] == 2
    episode.build(p, True, inspection=True)
    assert sum(bool(s["asset_id"]) for s in p["scenes"]) >= 2
    assert p["episode"]["plan"]["mode"] == "inspection"
    assert p["episode"]["bindings"] == before["episode"]["bindings"]
    assert p["episode"]["reviews"] == before["episode"]["reviews"]
    assert p["assets"] == before["assets"]
    assert not any(p["review"].values())
    assert all(s["inspection_only"] for s in p["scenes"])
    assert all(s["guide_unreviewed"] for s in p["scenes"] if s["asset_id"])


def test_reviewed_default_does_not_silently_admit_unapproved_sources():
    p = unreviewed()
    episode.build(p, True)
    assert all(not s["asset_id"] for s in p["scenes"])
    assert p["episode"]["plan"]["mode"] == "reviewed"


def test_guide_window_is_used_only_as_disclosed_candidate():
    c = candidate(unreviewed())
    assert c["usable"] and c["window"] == {"in": 1.0, "out": 2.0}
    assert "unapproved" in c["basis"]


def test_opening_sample_is_disclosed_when_guide_has_no_window():
    p = unreviewed()
    p["episode"]["guide"]["cues"][0]["suggested_windows"] = []
    c = candidate(p)
    assert c["usable"] and c["window"] == {"in": 0.0, "out": 4.0}
    assert "opening source sample" in c["basis"]
    assert "not a guide-selected or approved shot" in c["basis"]


def test_wrong_excerpt_clock_is_not_silently_offset_or_clamped():
    p = unreviewed()
    p["assets"][1]["duration"] = 0.75
    c = candidate(p)
    assert not c["usable"] and "do not fit" in c["status"]


@pytest.mark.parametrize(
    "bounds", [{"in": 1}, {"out": 2}, {"in": 3, "out": 2}, {"in": 0, "out": 7}]
)
def test_manual_invalid_bounds_are_never_replaced_with_guesses(bounds):
    p = unreviewed()
    p["episode"]["reviews"]["C01"] = bounds
    assert not candidate(p)["usable"]


def test_known_residential_restriction_applies_before_approval_in_inspection():
    p = unreviewed()
    p["episode"]["guide"]["cues"][0]["chapter"] = "chapter-3"
    p["episode"]["bindings"]["S03"]["contains_residence"] = True
    assert not candidate(p)["usable"]
    assert "prohibits residential" in candidate(p)["status"]


def test_guide_declared_source_exclusion_applies_even_without_residence_checkbox():
    p = unreviewed()
    c = p["episode"]["guide"]["cues"][0]
    c["chapter"], c["source_id"] = "chapter-3", "S02"
    p["episode"]["bindings"]["S02"] = p["episode"]["bindings"]["S03"]
    p["episode"]["guide"]["sources"].append(
        {"id": "S02", "notes": "Residential source. Do not use in Chapter 3."}
    )
    assert not candidate(p)["usable"]


def test_required_stop_is_not_guessed_in_inspection():
    p = unreviewed()
    p["episode"]["guide"]["cues"][0]["requires_stop"] = True
    assert not candidate(p)["usable"]
    p["episode"]["reviews"]["C01"] = {"narration_end": 1.0}
    assert candidate(p)["usable"]


def test_source_cannot_double_as_narration_or_music_in_inspection():
    p = unreviewed()
    p["music_id"] = p["assets"][1]["id"]
    assert not candidate(p)["usable"]


def test_inspection_keeps_full_voice_exact_captions_and_nonlooping_short_source():
    p = unreviewed()
    expected = renderer.project_srt(p)
    episode.build(p, True, inspection=True)
    assert renderer.project_srt(p) == expected
    assert sum(s["duration"] for s in p["scenes"]) == pytest.approx(145 / 24)
    used = [s for s in p["scenes"] if s["guide_source_id"] == "S03" and s["asset_id"]]
    assert sum(s["duration"] for s in used) == pytest.approx(1.0)
    assert all(
        1 <= s["trim_start"] and s["trim_start"] + s["duration"] <= 2.001 for s in used
    )
    assert not [i for i in episode.issues(p) if i["blocks_draft"]]
    p["captions"] = False
    assert renderer.project_srt(p) == expected


def test_inspection_never_becomes_final_merely_by_ticking_generic_review_boxes():
    p = unreviewed()
    episode.build(p, True, inspection=True)
    p["review"] = {key: True for key in p["review"]}
    report = editorial.inspect(p, check_files=False)
    assert report["ready_for_draft"] and not report["ready_for_final"]
    assert any(
        i["code"] == "episode_inspection_only" and i["blocks_final"]
        for i in report["issues"]
    )
    assert report["coverage"]["scenes_with_visuals"] >= 2
    assert report["coverage"]["scenes_with_references"] == 0
    assert not any(i["code"] == "estimated_captions" for i in report["issues"])


def test_removing_disclosure_or_extending_a_source_breaks_frozen_plan():
    p = unreviewed()
    episode.build(p, True, inspection=True)
    visual = next(s for s in p["scenes"] if s["asset_id"])
    visual["inspection_only"] = False
    assert any(
        i["code"] == "episode_timeline_changed" and i["blocks_draft"]
        for i in episode.issues(p)
    )


def test_api_and_renderer_require_explicit_inspection_and_never_allow_final(isolated):
    c, root = isolated
    p = unreviewed()
    episode.build(p, True, inspection=True)
    storage.save_project(p)
    for opts in [{"draft": True}, {"draft": False, "allow_inspection": True}]:
        r = c.post(
            f"/api/projects/{p['id']}/render", json={"resolution": "480p", **opts}
        )
        assert r.status_code == 400 and "inspection" in r.text.lower()
    with pytest.raises(ValueError, match="explicit inspection"):
        renderer.render(
            p,
            {"resolution": "480p", "draft": True},
            root / "blocked.mp4",
            lambda *_: None,
            lambda: False,
        )


def test_api_build_accepts_explicit_inspection_and_preserves_flags_in_editor(isolated):
    c, _ = isolated
    p = unreviewed()
    storage.save_project(p)
    r = c.post(
        f"/api/projects/{p['id']}/episode/build",
        json={"allow_placeholders": True, "inspection": True},
    )
    assert r.status_code == 200
    p = r.json()["project"]
    r = c.patch(f"/api/projects/{p['id']}", json={"scenes": p["scenes"]})
    assert r.status_code == 200
    p = r.json()
    assert all(s["inspection_only"] for s in p["scenes"])
    assert episode.analyze(p)["plan_current"]


def test_session_cleanup_requires_saved_confirmation_and_is_scoped(isolated):
    c, _ = isolated
    p = storage.new_project("Synthetic cleanup target", "narration")
    other = storage.new_project("Synthetic retained project", "narration")
    media = server.DATA / "media" / p["id"]
    media.mkdir()
    (media / "original-copy.bin").write_bytes(b"test upload copy")
    protected = server.DATA / "media" / other["id"]
    protected.mkdir()
    (protected / "keep.bin").write_bytes(b"keep")
    eid = storage.uid()
    ex = server.DATA / "exports" / eid
    ex.mkdir()
    (ex / "project.json").write_text(json.dumps({"id": p["id"]}))
    (ex / "documentary.mp4").write_bytes(b"fixture")
    p["exports"] = [{"id": eid}]
    storage.save_project(p)
    jid = storage.uid()
    server.JOBS[jid] = {"id": jid, "project_id": p["id"], "status": "done"}
    (server.DATA / "jobs" / f"{jid}.json").write_text(json.dumps(server.JOBS[jid]))
    url = f"/api/projects/{p['id']}/session"
    assert (
        c.request("DELETE", url, json={"confirm_download_saved": False}).status_code
        == 422
    )
    assert media.exists() and ex.exists()
    r = c.request("DELETE", url, json={"confirm_download_saved": True})
    assert r.status_code == 200
    assert not media.exists() and not ex.exists() and jid not in server.JOBS
    assert not (server.DATA / "projects" / f"{p['id']}.json").exists()
    assert (protected / "keep.bin").read_bytes() == b"keep"
    assert c.get(f"/api/projects/{other['id']}").status_code == 200


def test_session_cleanup_wont_follow_foreign_export_manifest_or_live_jobs(isolated):
    c, _ = isolated
    p = storage.new_project("Synthetic cleanup scope", "narration")
    eid = storage.uid()
    folder = server.DATA / "exports" / eid
    folder.mkdir()
    (folder / "project.json").write_text(json.dumps({"id": storage.uid()}))
    p["exports"] = [{"id": eid}]
    storage.save_project(p)
    jid = storage.uid()
    server.JOBS[jid] = {
        "id": jid,
        "project_id": p["id"],
        "status": "running",
        "kind": "render",
    }
    url = f"/api/projects/{p['id']}/session"
    assert (
        c.request("DELETE", url, json={"confirm_download_saved": True}).status_code
        == 409
    )
    server.JOBS[jid]["status"] = "done"
    assert (
        c.request("DELETE", url, json={"confirm_download_saved": True}).status_code
        == 200
    )
    assert folder.exists()


def test_real_inspection_mp4_shows_source_not_only_gap_and_keeps_audio_when_captions_hidden(
    isolated,
):
    _, root = isolated
    p = unreviewed()
    wav = root / "SYNTHETIC-continuous-tone.wav"
    sr = 16000
    n = round(6.04 * sr)
    samples = (np.sin(np.arange(n) * 2 * np.pi * 310 / sr) * 7000).astype("<i2")
    with wave.open(str(wav), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(samples.tobytes())
    p["assets"][0]["path"] = str(wav.relative_to(storage.ROOT))
    video = root / "S03-SYNTHETIC-red-test-video.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0xd32929:s=854x480:r=24:d=4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=990:sample_rate=16000:duration=4",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(video),
        ],
        check=True,
        timeout=30,
    )
    p["assets"][1]["path"] = str(video.relative_to(storage.ROOT))
    image = root / "S01-SYNTHETIC-green-test-image.jpg"
    Image.new("RGB", (854, 480), "#299c44").save(image)
    p["assets"][2]["path"] = str(image.relative_to(storage.ROOT))
    episode.build(p, True, inspection=True)
    expected_srt = renderer.project_srt(p)
    outputs = []
    for captions in [True, False]:
        p["captions"] = captions
        out = root / f"inspection-{captions}.mp4"
        renderer.render(
            p,
            {
                "resolution": "480p",
                "draft": True,
                "captions": captions,
                "allow_inspection": True,
            },
            out,
            lambda *_: None,
            lambda: False,
        )
        assert renderer.probe(out)["video_duration"] == pytest.approx(
            145 / 24, abs=0.001
        )
        assert renderer.project_srt(p) == expected_srt
        outputs.append(out)
    audio = [
        subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(o),
                "-map",
                "0:a",
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-",
            ]
        )
        for o in outputs
    ]
    assert audio[0] == audio[1]
    for time, channel in [(0.6, 0), (4.1, 1)]:
        frame = Image.open(
            io.BytesIO(
                subprocess.check_output(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-ss",
                        str(time),
                        "-i",
                        str(outputs[1]),
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
        assert r > g * 1.5 if channel == 0 else g > r * 1.5
        # The inspection strip is burned into every scene, not merely shown in UI.
        assert frame.getpixel((3, 3))[0] < 70
    overlay = renderer.overlay_image(
        p, next(s for s in p["scenes"] if s["asset_id"]), 0, 854, 480, True
    )
    assert overlay.crop((0, 0, 854, 28)).getbbox()
    assert not any(p["review"].values()) and not any(
        v.get("rights_confirmed") for v in p["episode"]["bindings"].values()
    )
