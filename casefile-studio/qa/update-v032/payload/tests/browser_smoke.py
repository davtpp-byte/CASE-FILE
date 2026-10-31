"""Browser smoke test against a running local server; no AI credentials needed.
Run: python tests/browser_smoke.py
Requires: pip install playwright; python -m playwright install --with-deps chromium
Creates a temporary test project, then removes its local test data after success.
"""

from pathlib import Path
import json
import os
import shutil
import uuid
import requests
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000")
QA = ROOT / "qa"
QA.mkdir(exist_ok=True)
name = "Browser QA " + uuid.uuid4().hex[:8]
image = QA / "qa-upload.jpg"
Image.new("RGB", (1280, 720), "#2d424b").save(image)
created = None
errors = []
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(BASE, wait_until="networkidle")
        # Guide projects are the new onboarding default. Explicitly open the
        # unchanged fictional sample before exercising the legacy editor.
        if page.locator("h1").inner_text() != "The Blackwater tapes":
            page.get_by_role("button", name="Switch project", exact=True).click()
            page.locator(".project-list-modal>button").filter(
                has_text="The Blackwater tapes"
            ).click()
        expect(page.locator("h1")).to_have_text("The Blackwater tapes")
        page.get_by_role("button", name="New project", exact=True).click()
        page.get_by_label("Case name or working title").fill(name)
        page.locator(".start-modes>button").nth(1).click()
        with page.expect_response(
            lambda r: r.url.endswith("/api/projects") and r.request.method == "POST"
        ) as response:
            page.get_by_role("button", name="Create project", exact=True).click()
        created = response.value.json()["id"]
        expect(page.locator("h1")).to_have_text(name)
        checks.append("Project creation through the browser")
        page.get_by_label("Documentary narration script").fill(
            "This is a fictional browser test. The script is not about any real person or event.\n\nA second paragraph becomes a second editable scene in the timeline."
        )
        page.locator("input[type=file]").set_input_files(str(image))
        expect(page.get_by_role("status")).to_contain_text("imported", timeout=10000)
        page.get_by_role("button", name="Build timeline", exact=True).click()
        expect(page.locator(".scene-card")).to_have_count(2)
        checks.append("Script autosave, image upload, and scene assembly")
        page.get_by_label("Scene duration", exact=True).fill("3")
        page.locator(".scene-card").nth(1).click()
        expect(page.locator(".scene-card").nth(1)).to_have_class(
            __import__("re").compile(".*selected.*")
        )
        page.get_by_label("Scene duration", exact=True).fill("3")
        page.locator(".scene-card").nth(0).click()
        expect(page.locator(".scene-card").nth(0)).to_have_class(
            __import__("re").compile(".*selected.*")
        )
        expect(page.get_by_label("Scene duration", exact=True)).to_have_value("3")
        # The right trim handle changes real scene duration.
        handle = page.locator(".clip.selected .trim-handle.right").bounding_box()
        page.mouse.move(handle["x"] + 2, handle["y"] + 4)
        page.mouse.down()
        page.mouse.move(handle["x"] + 20, handle["y"] + 4, steps=5)
        page.mouse.up()
        assert float(page.get_by_label("Scene duration", exact=True).input_value()) > 3
        checks.append("Inspector timing and direct timeline trimming")
        ruler = page.locator(".ruler").bounding_box()
        page.locator(".ruler").click(position={"x": ruler["width"] * 0.2, "y": 9})
        page.get_by_role("button", name="Split scene at playhead", exact=True).click()
        expect(page.locator(".scene-card")).to_have_count(3)
        page.get_by_role("button", name="Undo last saved edit", exact=True).click()
        expect(page.locator(".scene-card")).to_have_count(2)
        checks.append("Playhead splitting and persisted undo")
        page.locator("#direction").fill("use the archive look")
        page.get_by_role("button", name="Apply editing instruction", exact=True).click()
        expect(page.locator(".video-frame")).to_have_class(
            __import__("re").compile(".*look-archive.*")
        )
        page.get_by_role("button", name="Undo last saved edit", exact=True).click()
        expect(page.locator(".video-frame")).to_have_class(
            __import__("re").compile(".*look-noir.*")
        )
        checks.append("Plain-English local direction and undo")
        page.locator(".stage-nav>button").nth(0).click()
        page.get_by_role("button", name="Add a source", exact=True).click()
        page.get_by_label("Source title", exact=True).fill(
            "Fictional QA production notes"
        )
        page.get_by_label("Verified facts & context", exact=True).fill(
            "Synthetic testing material only. No real case facts are asserted."
        )
        page.get_by_role("button", name="Add source", exact=True).click()
        expect(page.locator(".sources > .source")).to_have_count(1)
        page.get_by_title("Mark as producer-reviewed", exact=True).click()
        expect(page.locator(".source-check")).to_have_text("Reviewed")
        checks.append("Offline source recording and producer review")
        page.locator(".stage-nav>button").nth(2).click()
        page.get_by_role(
            "button", name="Settings and AI connection", exact=True
        ).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        expect(page.get_by_role("dialog")).to_contain_text("Not connected")
        page.get_by_role("button", name="Close dialog", exact=True).click()
        checks.append("Honest disconnected AI state")
        page.get_by_role("button", name="Export video", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.get_by_label("Export resolution", exact=True).select_option("480p")
        expect(page.get_by_role("dialog")).to_contain_text("No narration assigned")
        page.get_by_role("button", name="Start render", exact=True).click()
        expect(page.locator(".export-row")).to_have_count(1, timeout=30000)
        export = requests.get(BASE + "/api/projects/" + created).json()["exports"][0]
        assert requests.get(BASE + export["url"]).status_code == 200
        assert export["size"] > 10000 and export["audio"] is False
        checks.append("Queued render, real MP4, and download")
        page.reload(wait_until="networkidle")
        expect(page.locator("h1")).to_have_text(name)
        expect(page.locator(".scene-card")).to_have_count(2)
        checks.append("Reload persistence")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth") == 390
        page.get_by_role("button", name="Open scene inspector", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.get_by_role("button", name="Close dialog", exact=True).click()
        checks.append("Mobile layout and scene inspector")
        assert not errors, errors
        (QA / "browser-results.json").write_text(
            json.dumps({"passed": checks, "browser_errors": errors}, indent=2)
        )
        print(json.dumps({"passed": checks, "browser_errors": errors}, indent=2))
    except Exception:
        page.screenshot(path=str(QA / "browser-failure.png"), full_page=True)
        print("Browser errors:", errors)
        raise
    finally:
        browser.close()
if created:
    data = requests.get(BASE + "/api/projects/" + created).json()
    for export in data.get("exports", []):
        shutil.rmtree(ROOT / "data/exports" / export["id"], ignore_errors=True)
    for path in (ROOT / "data/jobs").glob("*.json"):
        if json.loads(path.read_text()).get("project_id") == created:
            path.unlink()
    (ROOT / "data/projects" / f"{created}.json").unlink(missing_ok=True)
    shutil.rmtree(ROOT / "data/media" / created, ignore_errors=True)
image.unlink(missing_ok=True)
