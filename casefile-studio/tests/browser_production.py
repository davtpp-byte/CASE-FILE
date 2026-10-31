"""New-workflow browser checks. No provider key or live AI calls.

The AI-origin script is an explicitly simulated fixture written only to a
new temporary QA project; approval, jobs, editing, and FFmpeg exports use
the actual running app. Run: python tests/browser_production.py
"""

from pathlib import Path
import json
import os
import re
import shutil
import uuid
import requests
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000")
QA = ROOT / "qa"
QA.mkdir(exist_ok=True)
created = []
errors = []
checks = []
image = QA / "production-qa.jpg"
Image.new("RGB", (1280, 720), "#31444a").save(image)


def create(title, mode):
    r = requests.post(
        BASE + "/api/projects",
        json={"title": title, "mode": mode, "target_minutes": 25},
    )
    r.raise_for_status()
    p = r.json()
    created.append(p["id"])
    return p


def load(page, id):
    page.goto(BASE, wait_until="networkidle")
    page.evaluate('(id)=>localStorage.setItem("casefile-project",id)', id)
    page.reload(wait_until="networkidle")


def approve(page):
    page.once("dialog", lambda d: d.accept())
    page.get_by_role("button", name="Approve for narration", exact=True).click()
    expect(page.locator(".script-approved-tag")).to_be_visible()


topic = create("Topic guard QA " + uuid.uuid4().hex[:6], "topic")
script = create("Guided production QA " + uuid.uuid4().hex[:6], "script")
sid = script["id"]
url = BASE + "/api/projects/" + sid
requests.post(
    url + "/sources",
    json={
        "title": "Synthetic QA source",
        "url": "",
        "notes": "Fictional test fixture only. No real case or person is described.",
        "reviewed": True,
    },
).raise_for_status()
requests.patch(url + "/sources/S1", json={"reviewed": True}).raise_for_status()
with image.open("rb") as f:
    requests.post(
        url + "/upload", files=[("files", (image.name, f, "image/jpeg"))]
    ).raise_for_status()
requests.patch(
    url,
    json={
        "script": "This is a fictional QA setup for a guided editing test. [S1]\n\nThe second paragraph exists only to validate source-linked scene assembly. [S1]"
    },
).raise_for_status()
# Simulate an AI response's origin for approval-UI testing. Never modify a user project.
path = ROOT / "data/projects" / f"{sid}.json"
fixture = json.loads(path.read_text())
fixture["script_origin"] = "ai"
fixture["script_approved_hash"] = None
path.write_text(json.dumps(fixture))

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            load(page, topic["id"])
            page.get_by_role("button", name="Produce draft", exact=True).click()
            expect(
                page.get_by_label("Allow paid AI stages in this run")
            ).to_be_disabled()
            expect(page.get_by_role("dialog")).to_contain_text("Local only")
            page.get_by_role("button", name="Run guided production", exact=True).click()
            expect(page.locator(".production-pause")).to_contain_text(
                "paid AI approval", timeout=10000
            )
            assert (
                requests.get(BASE + "/api/projects/" + topic["id"]).json()["sources"]
                == []
            )
            checks.append(
                "Topic-only production pauses without a paid request or invented sources"
            )
            page.get_by_role("button", name="Close dialog", exact=True).click()

            load(page, sid)
            page.get_by_role("button", name="Produce draft", exact=True).click()
            page.get_by_role("button", name="Run guided production", exact=True).click()
            expect(page.locator(".production-pause")).to_contain_text(
                "approve the AI-written script", timeout=10000
            )
            page.screenshot(
                path=str(QA / "production-script-stop.png"),
                full_page=True,
                animations="disabled",
            )
            page.get_by_role("button", name=re.compile("Open Script")).click()
            expect(page.locator(".script-approval-notice")).to_be_visible()
            approve(page)
            checks.append(
                "Simulated AI draft stops for a real producer-approval action before narration"
            )

            page.locator(".stage-nav>button").nth(2).click()
            expect(page.locator(".scene-card")).to_have_count(2)
            for i in range(2):
                page.locator(".scene-card").nth(i).click()
                expect(page.locator(".scene-card").nth(i)).to_have_class(
                    re.compile(".*selected.*")
                )
                page.get_by_label("Scene duration", exact=True).fill("3")
            page.locator(".scene-card").nth(0).click()
            expect(page.get_by_label("Scene source references")).to_have_value("S1")
            page.get_by_placeholder(
                "Add the narration for this scene…", exact=True
            ).fill("This revised sentence remains a fictional browser-test fixture.")
            page.get_by_label("Scene chapter label").fill("Fictional test setup")
            page.locator(".stage-nav>button").nth(1).click()
            expect(page.get_by_label("Documentary narration script")).to_contain_text(
                "[S1]"
            )
            expect(page.locator(".script-approval-notice")).to_be_visible()
            approve(page)
            checks.append(
                "Scene edits preserve source links and invalidate the previous text approval"
            )

            page.locator(".stage-nav>button").nth(3).click()
            page.get_by_role("button", name="Preflight checks", exact=True).click()
            expect(page.get_by_role("dialog")).to_contain_text(
                "No narration track assigned"
            )
            expect(page.get_by_role("dialog")).to_contain_text("Rights notes missing")
            expect(page.locator(".preflight-stats")).to_contain_text("2 / 2")
            page.screenshot(
                path=str(QA / "preflight-desktop.png"),
                full_page=True,
                animations="disabled",
            )
            issue = page.locator(".preflight-issue").filter(
                has_text="Rights notes missing"
            )
            issue.get_by_role("button", name=re.compile("Open Edit")).click()
            expect(page.get_by_role("dialog")).to_contain_text(
                "Rights & attribution notes"
            )
            notes = page.get_by_placeholder(
                "Owner, license, permission, and required credit…", exact=True
            )
            notes.fill(
                "Procedural QA image created for this test. No real case material."
            )
            with page.expect_response(
                lambda r: r.request.method == "PATCH" and "/assets/" in r.url
            ):
                notes.blur()
            page.get_by_role("button", name="Close dialog", exact=True).click()
            checks.append(
                "Preflight identifies missing voice/rights, shows source coverage, and opens the repair location"
            )

            page.get_by_role("button", name="Export video", exact=True).click()
            page.get_by_role(
                "switch", name="Review draft watermark", exact=True
            ).click()
            expect(
                page.get_by_role("button", name="Start render", exact=True)
            ).to_be_disabled()
            expect(page.get_by_role("dialog")).to_contain_text("final-export blockers")
            page.get_by_role("button", name="Close dialog", exact=True).click()
            checks.append(
                "Final rendering remains disabled while editorial or voice blockers exist"
            )

            page.get_by_role("button", name="Produce draft", exact=True).click()
            page.get_by_label("Production draft resolution").select_option("480p")
            page.get_by_text("Review-only exceptions", exact=True).click()
            page.get_by_label("Allow a silent picture draft", exact=True).check()
            page.get_by_role("button", name="Run guided production", exact=True).click()
            expect(page.locator(".production-success")).to_be_visible(timeout=40000)
            current = requests.get(url).json()
            export = current["exports"][0]
            assert export["draft"] is True and export["audio"] is False
            assert all(s["asset_id"] for s in current["scenes"])
            checks.append(
                "Guided run reuses approved script, fills missing visuals, and creates a real draft MP4"
            )
            page.get_by_role("button", name="Open exports", exact=True).click()
            expect(page.locator(".export-row")).to_have_count(1)
            for name in ["Preflight report", "Chapter draft", "Publication notes"]:
                link = page.get_by_role("link", name=name, exact=True)
                expect(link).to_be_visible()
                assert (
                    requests.get(BASE + link.get_attribute("href")).status_code == 200
                )
            assert (
                "Fictional test setup"
                in requests.get(BASE + export["chapters_url"]).text
            )
            assert (
                requests.get(BASE + export["url"])
                .headers["content-type"]
                .startswith("video/mp4")
            )
            checks.append(
                "Frozen preflight, chapter, and publication companions download with the export"
            )

            page.set_viewport_size({"width": 390, "height": 844})
            page.get_by_role(
                "button", name="Guided automatic production", exact=True
            ).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth") == 390
            assert page.locator(".production-modal").evaluate(
                "(e)=>e.scrollWidth <= e.clientWidth+1"
            )
            expect(page.locator(".production-step")).to_have_count(7)
            expect(
                page.get_by_role("button", name="Run guided production", exact=True)
            ).to_be_enabled()
            page.screenshot(
                path=str(QA / "production-mobile.png"),
                full_page=True,
                animations="disabled",
            )
            page.get_by_role("button", name="Close dialog", exact=True).click()
            page.get_by_role("button", name="Preflight checks", exact=True).click()
            assert page.evaluate("document.documentElement.scrollWidth") == 390
            assert page.locator(".preflight-modal").evaluate(
                "(e)=>e.scrollWidth <= e.clientWidth+1"
            )
            page.screenshot(
                path=str(QA / "preflight-mobile.png"),
                full_page=True,
                animations="disabled",
            )
            checks.append(
                "Production and preflight remain usable without horizontal overflow on mobile"
            )
            assert not errors, errors
            result = {
                "passed": checks,
                "browser_errors": errors,
                "provider_calls": "None; AI-origin metadata is an explicit temporary UI fixture.",
            }
            (QA / "production-browser-results.json").write_text(
                json.dumps(result, indent=2)
            )
            print(json.dumps(result, indent=2))
        except Exception:
            page.screenshot(
                path=str(QA / "production-browser-failure.png"), full_page=True
            )
            print("Browser errors:", errors)
            raise
        finally:
            browser.close()
finally:
    for id in created:
        p = requests.get(BASE + "/api/projects/" + id).json()
        for ex in p.get("exports", []):
            shutil.rmtree(ROOT / "data/exports" / ex["id"], ignore_errors=True)
        for job in (ROOT / "data/jobs").glob("*.json"):
            if json.loads(job.read_text()).get("project_id") == id:
                job.unlink()
        (ROOT / "data/projects" / f"{id}.json").unlink(missing_ok=True)
        shutil.rmtree(ROOT / "data/media" / id, ignore_errors=True)
    image.unlink(missing_ok=True)
