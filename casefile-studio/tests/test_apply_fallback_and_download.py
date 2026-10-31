"""Apply-through-API and other-case guards; download never queues another render."""

from pathlib import Path
import copy
import pytest
from PIL import Image
import app as server
import episode
import storage
from test_automatic_fallback_resolution import case
from test_alternatives import with_rule


def photo(p, root, sid):
    path = root / (sid + "-synthetic.jpg")
    Image.new("RGB", (640, 360), "#265e39").save(path)
    a = {
        "id": storage.uid(),
        "name": path.name,
        "kind": "image",
        "duration": 0,
        "has_audio": False,
        "license": "",
        "path": str(path.relative_to(storage.ROOT)),
    }
    p["assets"].append(a)
    return a


def test_manual_primary_dropdown_is_corrected_at_api_without_user_relinking(isolated):
    c, root = isolated
    p = case()
    a = photo(p, root, "S01")
    storage.save_project(p)
    r = c.patch(
        f"/api/projects/{p['id']}/episode/source/S10", json={"asset_id": a["id"]}
    )
    assert r.status_code == 200, r.text
    p = r.json()["project"]
    slots = {v["id"]: v for v in r.json()["analysis"]["placements"]}
    assert p["episode"]["bindings"]["S10"]["asset_id"] is None
    assert p["episode"]["bindings"]["S01"]["asset_id"] == a["id"]
    assert slots["C17"]["source_id"] == "S01" and "not funeral" in slots["C17"]["label"]
    assert not any(p["review"].values()) and not p["episode"]["reviews"]
    r = c.post(f"/api/projects/{p['id']}/episode/first-draft", json={})
    assert r.status_code == 200
    assert any(
        s.get("guide_cue_id") == "C17"
        and s.get("guide_alternative")
        and s.get("asset_id") == a["id"]
        for s in r.json()["project"]["scenes"]
    )


def test_future_guide_with_different_ids_gets_same_automatic_correction(isolated):
    c, root = isolated
    p = with_rule(
        rule="S12 permitted synthetic portrait.", label="FUTURE CASE S12 — PORTRAIT"
    )
    a = photo(p, root, "S12")
    storage.save_project(p)
    r = c.patch(
        f"/api/projects/{p['id']}/episode/source/S03", json={"asset_id": a["id"]}
    )
    assert r.status_code == 200, r.text
    slot = r.json()["analysis"]["placements"][0]
    assert slot["source_id"] == "S12" and slot["using_alternative"]
    assert slot["label"] == "FUTURE CASE S12 — PORTRAIT"
    assert not any(r.json()["project"]["review"].values())


def test_unbound_named_alternative_auto_links_during_direct_inspection_build():
    p = case()
    a = {
        "id": storage.uid(),
        "name": "S01-future-test.jpg",
        "kind": "image",
        "duration": 0,
        "has_audio": False,
        "license": "",
    }
    p["assets"].append(a)
    episode.build(p, True, inspection=True)
    c17 = next(v for v in episode.analyze(p)["placements"] if v["id"] == "C17")
    assert c17["source_id"] == "S01" and c17["asset_id"] == a["id"]
    assert any(
        s.get("guide_cue_id") == "C17" and s.get("asset_id") == a["id"]
        for s in p["scenes"]
    )


def export_fixture(root, owner):
    eid = storage.uid()
    folder = server.DATA / "exports" / eid
    folder.mkdir()
    data = b"QA-ONLY-FAKE-MP4-BYTES-NOT-FOR-PLAYBACK" * 40
    (folder / "documentary.mp4").write_bytes(data)
    (folder / "project.json").write_text("{}")
    owner["exports"] = [
        {
            "id": eid,
            "draft": True,
            "inspection_only": True,
            "url": f"/exports/{eid}/documentary.mp4",
        }
    ]
    storage.save_project(owner)
    return eid, folder, data


def test_completed_mp4_download_is_attachment_and_does_not_render_or_delete(isolated):
    c, root = isolated
    p = storage.new_project("Download fixture", "narration")
    eid, folder, data = export_fixture(root, p)
    before = storage.get_project(p["id"])
    jobs = copy.deepcopy(server.JOBS)
    r = c.get(f"/api/projects/{p['id']}/exports/{eid}/download")
    assert r.status_code == 200 and r.content == data
    assert r.headers["content-type"].startswith("video/mp4")
    assert r.headers["content-disposition"].startswith("attachment;")
    assert "unreviewed-inspection.mp4" in r.headers["content-disposition"]
    assert server.JOBS == jobs and storage.get_project(p["id"]) == before
    assert (folder / "documentary.mp4").read_bytes() == data


def test_completed_download_supports_head_and_byte_ranges(isolated):
    c, root = isolated
    p = storage.new_project("Range fixture", "narration")
    eid, _, data = export_fixture(root, p)
    u = f"/api/projects/{p['id']}/exports/{eid}/download"
    head = c.head(u)
    assert (
        head.status_code == 200
        and not head.content
        and int(head.headers["content-length"]) == len(data)
    )
    r = c.get(u, headers={"Range": "bytes=0-7"})
    assert r.status_code == 206 and r.content == data[:8]


def test_download_cannot_read_another_project_export(isolated):
    c, root = isolated
    p = storage.new_project("Owner", "narration")
    other = storage.new_project("Other", "narration")
    eid, _, _ = export_fixture(root, p)
    assert (
        c.get(f"/api/projects/{other['id']}/exports/{eid}/download").status_code == 404
    )


def test_missing_render_bytes_have_an_honest_error_no_new_job(isolated):
    c, root = isolated
    p = storage.new_project("Missing export", "narration")
    eid, folder, _ = export_fixture(root, p)
    (folder / "documentary.mp4").unlink()
    jobs = copy.deepcopy(server.JOBS)
    r = c.get(f"/api/projects/{p['id']}/exports/{eid}/download")
    assert r.status_code == 404 and "record exists" in r.text
    assert server.JOBS == jobs


def test_download_refuses_a_file_symlink_escaping_the_export_folder(isolated):
    c, root = isolated
    p = storage.new_project("Escape guard", "narration")
    eid, folder, _ = export_fixture(root, p)
    outside = root / "not-an-export.txt"
    outside.write_text("Synthetic test only")
    (folder / "documentary.mp4").unlink()
    (folder / "documentary.mp4").symlink_to(outside)
    assert c.get(f"/api/projects/{p['id']}/exports/{eid}/download").status_code == 404


def test_future_video_alternative_uses_its_own_range_not_this_cases_ranges():
    from test_episode import GUIDE
    from test_capcut import imported

    p = imported()
    raw = GUIDE.replace(
        "**Care:** Technical fixture, not actual footage.",
        "**Alternative:** S12 synthetic video. **Alternative preview:** S12 around 0:04–0:05. **Alternative label:** FUTURE VIDEO CONTEXT **Care:** Technical fixture, not actual footage.",
    )
    episode.import_document(p, "guide", raw, "future-video-guide.md")
    a = {
        "id": storage.uid(),
        "name": "S12-future-source.mp4",
        "kind": "video",
        "duration": 8,
        "has_audio": False,
        "license": "",
    }
    p["assets"].append(a)
    episode.bind_source(p, "S03", {"asset_id": a["id"]})
    before = episode.analyze(p)["word_clock"]
    episode.build(p, True, inspection=True)
    slot = episode.analyze(p)["placements"][0]
    assert slot["source_id"] == "S12" and slot["using_alternative"]
    assert slot["inspection_window"] == {"in": 4.0, "out": 5.0}
    assert slot["label"] == "FUTURE VIDEO CONTEXT"
    assert episode.analyze(p)["word_clock"] == before


def test_explicit_main_filename_is_not_reclassified_using_only_media_kind():
    p = case()
    a = {
        "id": storage.uid(),
        "name": "S10-explicit-main-frame.jpg",
        "kind": "image",
        "duration": 0,
        "has_audio": False,
        "license": "",
    }
    p["assets"].append(a)
    episode.bind_source(p, "S10", {"asset_id": a["id"]})
    assert episode.resolve_automatic_source_links(p) == []
    assert p["episode"]["bindings"]["S10"]["asset_id"] == a["id"]
