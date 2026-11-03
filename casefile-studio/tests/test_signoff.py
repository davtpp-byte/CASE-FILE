"""The producer sign-off is one explicit action; it records responsibility, it verifies nothing."""

import io
import subprocess
import time

from PIL import Image

from test_episode import api_project, tone_bytes


def test_producer_signoff_clears_the_itemized_review(isolated):
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
    assert c.post(url + "/upload", data={"episode_role": "sources"}, files=files).status_code == 200
    r = c.post(
        url + "/upload",
        data={"episode_role": "narration"},
        files=[("files", ("synthetic-voice.wav", tone_bytes(), "audio/wav"))],
    )
    assert r.status_code == 200
    v = r.json()["assets"][-1]
    assert (
        c.patch(url + "/episode/options", json={"narration_id": v["id"]}).status_code
        == 200
    )
    assert c.post(url + "/episode/autolink", json={}).status_code == 200
    # Push the first placement past a 0.2s lead-in, like a real recording
    # whose first caption starts slightly after 0:00.
    assert (
        c.patch(url + "/episode/cue/C01", json={"narration_start": 0.2}).status_code
        == 200
    )
    r = c.post(
        url + "/episode/build",
        json={"allow_placeholders": True, "inspection": True},
    )
    assert r.status_code == 200, r.text

    pre = c.get(url + "/preflight").json()
    assert not pre["ready_for_final"]

    # The sign-off must be explicitly confirmed; it is the producer's action.
    assert c.post(url + "/signoff", json={"confirmed": False}).status_code == 422
    r = c.post(url + "/signoff", json={"confirmed": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["signed_off"] and body["placements_reviewed"] >= 2
    assert body["sources_confirmed"] >= 2
    assert "not independently verified" in body["note"]
    # The 0.2s lead-in was covered by starting the first placement at 0:00.
    assert body["lead_in_covered"] and body["ready_for_final"], body

    p = c.get(url).json()
    assert all(s["reviewed"] for s in p["sources"])
    assert all(p["review"].values())
    assert all(
        str(a.get("license", "")).strip()
        for a in p["assets"]
        if a["kind"] in ("image", "video", "audio")
    )

    # The sign-off already rebuilt the reviewed plan; no further step needed.
    assert body["plan_mode"] == "reviewed"
    p = c.get(url).json()
    assert p["episode"]["plan"]["mode"] == "reviewed"
    assert not any(s.get("inspection_only") for s in p["scenes"])
    pre = c.get(url + "/preflight").json()
    assert pre["ready_for_draft"] and pre["ready_for_final"], pre
    assert not any(
        i["code"] in ("sources_await_review", "review_attestations")
        for i in pre["issues"]
    )

    # The final export needs no inspection consent anymore.
    r = c.post(
        url + "/render",
        json={"resolution": "480p", "draft": False, "captions": True},
    )
    assert r.status_code == 200, r.text
    job = r.json()["job_id"]
    for _ in range(120):
        jobs = {j["id"]: j for j in c.get(url + "/jobs").json()}
        if jobs[job]["status"] not in ("queued", "running"):
            break
        time.sleep(0.5)
    assert jobs[job]["status"] == "done", jobs[job]
    record = jobs[job]["result"]
    assert record["draft"] is False and "unreviewed-inspection" not in record["url"]
