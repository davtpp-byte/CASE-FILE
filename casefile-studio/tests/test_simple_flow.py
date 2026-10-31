"""One-action visual preview must use real available files, never an empty success."""

import copy
from PIL import Image
import pytest
import storage
import episode
from test_capcut import imported


def image_project(root):
    p = imported()
    file = root / "S01-synthetic.jpg"
    Image.new("RGB", (640, 360), "#225c37").save(file)
    a = {
        "id": storage.uid(),
        "name": "S01-synthetic.jpg",
        "kind": "image",
        "duration": 0,
        "has_audio": False,
        "license": "",
        "path": str(file.relative_to(storage.ROOT)),
        "url": "/media/synthetic-image.jpg",
    }
    p["assets"].append(a)
    storage.save_project(p)
    return p, a


def test_one_action_links_builds_inspection_and_selects_first_real_visual_without_reviews(
    isolated,
):
    c, root = isolated
    p, a = image_project(root)
    r = c.post(f"/api/projects/{p['id']}/episode/first-draft", json={})
    assert r.status_code == 200, r.text
    data = r.json()
    p = data["project"]
    assert p["episode"]["plan"]["mode"] == "inspection"
    assert p["episode"]["bindings"]["S01"]["asset_id"] == a["id"]
    assert any(s.get("asset_id") == a["id"] for s in p["scenes"])
    assert data["preview"]["time"] > 3.2
    assert (
        next(s for s in p["scenes"] if s["id"] == data["preview"]["scene_id"])[
            "asset_id"
        ]
        == a["id"]
    )
    assert not any(p["review"].values()) and not p["episode"]["reviews"]
    assert not p["episode"]["bindings"]["S01"]["rights_confirmed"]
    assert not data["analysis"][
        "has_voice"
    ]  # Picture inspection does not pretend there is audio.


def test_empty_source_list_does_not_create_a_green_all_gap_draft(isolated):
    c, _ = isolated
    p = imported()
    storage.save_project(p)
    r = c.post(f"/api/projects/{p['id']}/episode/first-draft", json={})
    assert r.status_code == 422 and "at least one source photo or video" in r.text
    assert not storage.get_project(p["id"])["scenes"]


def test_lost_uploaded_bytes_are_explained_not_fixed_with_false_checkboxes(isolated):
    c, root = isolated
    p = imported()
    a = {
        "id": storage.uid(),
        "name": "S01-original.jpg",
        "kind": "image",
        "duration": 0,
        "has_audio": False,
        "license": "",
        "path": str((root / "missing.jpg").relative_to(storage.ROOT)),
    }
    p["assets"].append(a)
    episode.bind_source(p, "S01", {"asset_id": a["id"]})
    storage.save_project(p)
    before = storage.get_project(p["id"])
    r = c.post(f"/api/projects/{p['id']}/episode/first-draft", json={})
    assert r.status_code == 422 and "uploaded copies are not available" in r.text
    assert storage.get_project(p["id"]) == before


def test_available_photo_is_not_hidden_by_another_missing_source_file(isolated):
    c, root = isolated
    p, a = image_project(root)
    missing = {
        "id": storage.uid(),
        "name": "S03-missing.mp4",
        "kind": "video",
        "duration": 6,
        "has_audio": True,
        "license": "",
        "path": str((root / "gone.mp4").relative_to(storage.ROOT)),
    }
    p["assets"].append(missing)
    episode.bind_source(p, "S03", {"asset_id": missing["id"]})
    storage.save_project(p)
    r = c.post(f"/api/projects/{p['id']}/episode/first-draft", json={})
    assert r.status_code == 200, r.text
    p = r.json()["project"]
    assert not next(v for v in p["assets"] if v["id"] == missing["id"])[
        "available_on_server"
    ]
    assert all(s.get("asset_id") != missing["id"] for s in p["scenes"])
    assert any(s.get("asset_id") == a["id"] for s in p["scenes"])


def test_old_reviewed_all_gap_plan_is_automatically_replaced_for_inspection(isolated):
    c, root = isolated
    p, a = image_project(root)
    episode.build(p, True)
    assert not any(s.get("asset_id") for s in p["scenes"])
    storage.save_project(p)
    r = c.post(f"/api/projects/{p['id']}/episode/first-draft", json={})
    assert r.status_code == 200
    assert r.json()["project"]["episode"]["plan"]["mode"] == "inspection"
    assert r.json()["project"]["episode"]["plan"]["visual_seconds"] > 0


def test_repeated_preview_reuses_current_plan_and_does_not_churn_scene_ids(isolated):
    c, root = isolated
    p, _ = image_project(root)
    url = f"/api/projects/{p['id']}/episode/first-draft"
    first = c.post(url, json={}).json()
    second = c.post(url, json={}).json()
    assert second["reused_current_plan"]
    assert [s["id"] for s in first["project"]["scenes"]] == [
        s["id"] for s in second["project"]["scenes"]
    ]
    assert len(first["project"].get("undo", [])) == len(
        second["project"].get("undo", [])
    )


def test_preview_availability_does_not_follow_outside_workspace_paths(isolated):
    c, _ = isolated
    p = imported()
    a = {
        "id": storage.uid(),
        "name": "S01.jpg",
        "kind": "image",
        "duration": 0,
        "license": "",
        "path": "/etc/passwd",
    }
    p["assets"].append(a)
    storage.save_project(p)
    r = c.post(f"/api/projects/{p['id']}/episode/first-draft", json={})
    assert r.status_code == 422
    assert not any(storage.get_project(p["id"])["review"].values())
