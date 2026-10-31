"""Episode Setup browser checks against a running local server.

User documents are tested only as an unvoiced, missing-media plan. Any rendering
uses a separate synthetic project with technical tones and clearly fake imagery.
No source downloads, factual clearance, provider keys, or paid calls.
"""

from pathlib import Path
import json
import os
import shutil
import subprocess
import uuid
import wave

import numpy as np
import requests
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000")
QA = ROOT / "qa"
QA.mkdir(exist_ok=True)
WORK = QA / ("episode-browser-" + uuid.uuid4().hex[:8])
WORK.mkdir()
created = []
errors = []
checks = []


def tone(path, seconds, hz):
    rate = 16000
    t = np.arange(round(rate * seconds)) / rate
    with wave.open(str(path), "wb") as out:
        out.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        out.writeframes((np.sin(t * hz * 2 * np.pi) * 2500).astype("<i2").tobytes())


def load(page, id):
    page.goto(BASE, wait_until="networkidle")
    page.evaluate('(id)=>localStorage.setItem("casefile-project",id)', id)
    page.reload(wait_until="networkidle")


def response_for(page, path, method):
    return page.expect_response(
        lambda r: r.url.endswith(path) and r.request.method == method
    )


def import_document(page, label, path):
    with response_for(page, "/episode/import", "POST") as r:
        page.get_by_label(label, exact=True).set_input_files(str(path))
    assert r.value.status == 200, r.value.text()
    expect(
        page.locator(".ep-material")
        .nth(2 if label == "Upload narration script" else 3)
        .locator(".ep-document-summary")
    ).to_be_visible()


try:
    voice = WORK / "SYNTHETIC-voice-tone.wav"
    music = WORK / "SYNTHETIC-music-tone.wav"
    picture = WORK / "S01-synthetic.jpg"
    video = WORK / "S03-synthetic.mp4"
    tone(voice, 6.04, 440)
    tone(music, 1.5, 110)
    Image.new("RGB", (640, 360), "#2d424c").save(picture)
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
            str(video),
        ],
        check=True,
        capture_output=True,
    )
    pack = requests.post(
        BASE + "/api/projects",
        json={
            "title": "Supplied documents QA " + uuid.uuid4().hex[:6],
            "mode": "narration",
        },
    ).json()
    created.append(pack["id"])
    url = BASE + "/api/projects/" + pack["id"]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            load(page, pack["id"])
            expect(page.locator(".episode-setup")).to_be_visible()
            assert page.get_by_role("dialog").count() == 0
            checks.append(
                "Narration/media projects open Episode Setup without a confusing generic import modal"
            )
            import_document(
                page,
                "Upload narration script",
                ROOT / "examples/the-last-timeline/narration-script.md",
            )
            import_document(
                page,
                "Upload editing guide",
                ROOT / "examples/the-last-timeline/editing-guide.md",
            )
            expect(page.locator(".ep-cue")).to_have_count(43)
            expect(page.locator(".ep-source")).to_have_count(15)
            expect(page.locator(".ep-matched")).to_contain_text("43 / 43")
            expect(
                page.get_by_role(
                    "button", name="Create guided review video", exact=True
                )
            ).to_be_disabled()
            checks.append(
                "Both supplied Markdown documents import in separate cards; 43 chapter-scoped matches and 15 required source files are visible"
            )
            page.get_by_role("button", name="All references (24)", exact=True).click()
            expect(page.locator(".ep-source")).to_have_count(24)
            page.get_by_role("button", name="Used by guide (15)", exact=True).click()
            page.get_by_label("Filter guide chapter").select_option("chapter-3")
            expect(page.locator(".ep-cue")).to_have_count(4)
            page.get_by_label("Filter guide chapter").select_option("all")
            checks.append(
                "The source catalog distinguishes all 24 references from the 15 used sources; chapter filters preserve the guide structure"
            )
            with response_for(page, "/episode/build", "POST") as r:
                page.get_by_role(
                    "button", name="Preview episode plan", exact=True
                ).click()
            assert r.value.status == 200, r.value.text()
            expect(page.locator(".ep-plan-result")).to_contain_text("57 scenes planned")
            expect(page.locator(".ep-plan-result")).to_contain_text(
                "script-only estimate"
            )
            page.get_by_role("button", name="Plan & draft", exact=True).click()
            expect(page.locator(".ep-create")).to_be_in_viewport()
            assert (
                requests.post(url + "/render", json={"draft": True}).status_code == 400
            )
            current = requests.get(url).json()
            before = current["script"]
            checks.append(
                "A full script-only guide plan can be inspected, but the UI and API both block video rendering without the actual narration"
            )
            with response_for(page, "/episode/import", "POST") as r:
                page.get_by_label(
                    "Upload narration script", exact=True
                ).set_input_files(
                    str(ROOT / "examples/the-last-timeline/editing-guide.md")
                )
            assert r.value.status == 422
            expect(page.get_by_role("status")).to_contain_text(
                "editing guide, not narration"
            )
            assert requests.get(url).json()["script"] == before
            checks.append(
                "Putting the editing guide in the script card gives a clear error and never overwrites the narration"
            )
            # Capture the real supplied-input screen, with no invented voice/media.
            page.locator(".episode-setup").evaluate("(el)=>el.scrollTop=0")
            page.screenshot(
                path=str(QA / "episode-supplied-documents-desktop.png"),
                full_page=True,
                animations="disabled",
            )
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth") == 390
            assert page.locator(".episode-setup").evaluate(
                "(el)=>el.scrollWidth<=el.clientWidth+1"
            )
            page.screenshot(
                path=str(QA / "episode-supplied-documents-mobile.png"),
                full_page=True,
                animations="disabled",
            )
            checks.append(
                "The supplied-input Setup screen has no horizontal overflow at 1440px desktop or 390px mobile"
            )
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.get_by_role("button", name="New project", exact=True).click()
            title = "SYNTHETIC episode browser QA " + uuid.uuid4().hex[:6]
            page.get_by_label("Case name or working title").fill(title)
            page.locator(".start-modes>button").nth(2).click()
            with response_for(page, "/api/projects", "POST") as r:
                page.get_by_role("button", name="Create project", exact=True).click()
            project = r.value.json()
            created.append(project["id"])
            url = BASE + "/api/projects/" + project["id"]
            expect(page.locator(".episode-setup")).to_be_visible()
            expect(page.get_by_role("dialog")).to_have_count(0)
            for label, path in [
                ("Upload finished narration", voice),
                ("Upload background music", music),
            ]:
                with response_for(page, "/episode/options", "PATCH") as r:
                    page.get_by_label(label, exact=True).set_input_files(str(path))
                assert r.value.status == 200, r.value.text()
            current = requests.get(url).json()
            assert (
                current["narration_id"]
                and current["music_id"]
                and current["narration_id"] != current["music_id"]
            )
            assert len(current["assets"]) == 2
            checks.append(
                "Finished narration and background music upload into separate explicit roles without an AI connection or regenerated voice"
            )
            import_document(
                page,
                "Upload narration script",
                ROOT / "tests/fixtures/synthetic-script.md",
            )
            import_document(
                page, "Upload editing guide", ROOT / "tests/fixtures/synthetic-guide.md"
            )
            with response_for(page, "/upload", "POST") as r:
                page.get_by_label("Upload source footage", exact=True).set_input_files(
                    [str(picture), str(video)]
                )
            assert r.value.status == 200, r.value.text()
            with response_for(page, "/episode/autolink", "POST") as r:
                page.get_by_role("button", name="Match filenames", exact=True).click()
            assert r.value.status == 200
            for sid in ("S03", "S01"):
                row = page.locator(".ep-source").filter(
                    has=page.locator(".ep-id", has_text=sid)
                )
                row.locator(".ep-source-summary").click()
                expect(
                    page.get_by_label("File for " + sid, exact=True)
                ).not_to_have_value("")
                with response_for(page, "/episode/source/" + sid, "PATCH") as r:
                    page.get_by_label("Rights notes for " + sid, exact=True).fill(
                        "Synthetic technical fixture created locally for QA; not actual case footage."
                    )
                    page.get_by_label("Rights notes for " + sid, exact=True).press(
                        "Tab"
                    )
                assert r.value.status == 200, r.value.text()
                with response_for(page, "/episode/source/" + sid, "PATCH") as r:
                    page.get_by_label(
                        "Rights basis recorded for " + sid, exact=True
                    ).check()
                assert r.value.status == 200, r.value.text()
            checks.append(
                "Exact source IDs autolink unique filenames but never auto-approve permissions; each actual file retains its own reuse notes and attestation"
            )
            cue = page.locator(".ep-cue").nth(0)
            cue.locator(":scope>summary").click()
            page.get_by_label("Clip in C01", exact=True).fill("1")
            page.get_by_label("Clip out C01", exact=True).fill("2")
            page.get_by_label("Reviewed placement C01", exact=True).check()
            with response_for(page, "/episode/cue/C01", "PATCH") as r:
                cue.get_by_role(
                    "button", name="Save placement review", exact=True
                ).click()
            assert r.value.status == 200, r.value.text()
            cue = page.locator(".ep-cue").nth(1)
            cue.locator(":scope>summary").click()
            page.get_by_label("Reviewed placement C02", exact=True).check()
            with response_for(page, "/episode/cue/C02", "PATCH") as r:
                cue.get_by_role(
                    "button", name="Save placement review", exact=True
                ).click()
            assert r.value.status == 200, r.value.text()
            with response_for(page, "/episode/options", "PATCH") as r:
                page.get_by_label("Narration cue timing reviewed", exact=True).check()
            assert r.value.status == 200, r.value.text()
            with response_for(page, "/episode/build", "POST") as r:
                page.get_by_role(
                    "button", name="Preview episode plan", exact=True
                ).click()
            assert r.value.status == 200, r.value.text()
            current = r.value.json()["project"]
            assert current["episode"]["plan"]["gap_seconds"] > 0
            expect(
                page.get_by_role(
                    "button", name="Create guided review video", exact=True
                )
            ).to_be_disabled()
            checks.append(
                "Producer-reviewed exact clip windows and Care context are separate from rights; a short clip leaves a marked gap instead of looping"
            )
            page.get_by_role("button", name="View timeline", exact=True).click()
            expect(page.locator(".film-source-label")).to_contain_text(
                "SYNTHETIC TEST PATTERN | 2026"
            )
            assert page.locator(".video-frame video").evaluate(
                "(el)=>!el.loop && el.muted"
            )
            with response_for(page, "/command", "POST") as r:
                page.locator("#direction").fill("set music to 8%")
                page.get_by_role(
                    "button", name="Apply editing instruction", exact=True
                ).click()
            assert (
                r.value.status == 200
                and requests.get(url).json()["music_volume"] == 0.08
            )
            with response_for(page, "/command", "POST") as r:
                page.locator("#direction").fill("set scene 1 to 8 seconds")
                page.get_by_role(
                    "button", name="Apply editing instruction", exact=True
                ).click()
            assert r.value.status == 400 and "preserved narration" in r.value.text()
            checks.append(
                "Timeline preview carries the source/date label, mutes source audio, and disables looping; music-level instructions work while destructive timing commands are rejected"
            )
            page.locator(".stage-nav").get_by_role(
                "button", name="Episode setup"
            ).click()
            expect(
                page.get_by_label("Narration cue timing reviewed", exact=True)
            ).to_be_checked()
            page.get_by_label("Allow marked visual gaps", exact=True).check()
            page.get_by_label("Guide draft resolution", exact=True).select_option(
                "480p"
            )
            with response_for(page, "/render", "POST") as r:
                page.get_by_role(
                    "button", name="Create guided review video", exact=True
                ).click()
            assert r.value.status == 200, r.value.text()
            expect(page.locator(".export-row")).to_have_count(1, timeout=60000)
            current = requests.get(url).json()
            export = current["exports"][0]
            assert (
                export["draft"]
                and export["audio"]
                and 6.04 <= export["duration"] < 6.14
            )
            frozen = page.get_by_role("link", name="Frozen episode plan", exact=True)
            expect(frozen).to_be_visible()
            assert requests.get(BASE + frozen.get_attribute("href")).status_code == 200
            video_response = requests.get(
                BASE + export["url"], headers={"Range": "bytes=0-255"}
            )
            assert video_response.status_code == 206 and video_response.headers[
                "content-type"
            ].startswith("video/mp4")
            checks.append(
                "With explicit marked-gap consent, the browser renders a real 480p MP4 with the full uploaded voice, mixed music, and a frozen episode-plan companion; range playback works"
            )
            page.screenshot(
                path=str(QA / "episode-synthetic-export-desktop.png"),
                full_page=True,
                animations="disabled",
            )
            assert not errors, errors
            result = {
                "passed": checks,
                "browser_errors": errors,
                "provider_calls": 0,
                "source_downloads": 0,
                "render_fixture": "Separate synthetic technical episode only; never the user's actual case.",
            }
            (QA / "episode-browser-results.json").write_text(
                json.dumps(result, indent=2)
            )
            print(json.dumps(result, indent=2))
        except Exception:
            page.screenshot(
                path=str(QA / "episode-browser-failure.png"),
                full_page=True,
                animations="disabled",
            )
            print("Browser errors:", errors)
            raise
        finally:
            browser.close()
finally:
    for id in created:
        try:
            current = requests.get(BASE + "/api/projects/" + id).json()
        except Exception:
            current = {}
        for export in current.get("exports", []):
            shutil.rmtree(ROOT / "data/exports" / export["id"], ignore_errors=True)
        for path in (ROOT / "data/jobs").glob("*.json"):
            if json.loads(path.read_text()).get("project_id") == id:
                path.unlink()
        (ROOT / "data/projects" / (id + ".json")).unlink(missing_ok=True)
        shutil.rmtree(ROOT / "data/media" / id, ignore_errors=True)
    shutil.rmtree(WORK, ignore_errors=True)
