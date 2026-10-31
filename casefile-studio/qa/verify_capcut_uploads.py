"""Browser-check the actual uploaded exports in a temporary, unvoiced project.

No real audio, source media, rendering, downloads, approvals, or reseeding.
User exports are NOT distributed in the release; this audit runs in this workspace.
"""

from pathlib import Path
import json
import requests
import re
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
UP = ROOT.parent / "uploads"
BASE = "http://127.0.0.1:8000"
checks, errors = [], []
pid = None
try:
    r = requests.post(
        BASE + "/api/projects",
        json={
            "title": "Temporary timing-import QA — no audio/media",
            "mode": "narration",
        },
    )
    r.raise_for_status()
    pid = r.json()["id"]
    url = BASE + "/api/projects/" + pid
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE, wait_until="networkidle")
        page.evaluate('(id) => localStorage.setItem("casefile-project", id)', pid)
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="More settings", exact=True).click()
        for label, filename in [
            ("Upload narration script", "Untitled document (1).md"),
            ("Upload editing guide", "The_Last_Timeline_Real_Footage_Guide.md"),
            ("Upload narration timings", "draft_info.json"),
            ("Upload narration timings", "captions_continuous.srt.md"),
        ]:
            with page.expect_response(
                lambda r: (
                    r.url.endswith("/episode/import") and r.request.method == "POST"
                )
            ) as response:
                page.get_by_label(label, exact=True).set_input_files(str(UP / filename))
            assert response.value.status == 200, response.value.text()
            expect(page.get_by_label(label, exact=True)).to_be_enabled()
        checks.append(
            "Actual 2.7 MB draft and .srt.md import successfully through browser file pickers"
        )
        summary = page.get_by_label("Imported timing summary", exact=True)
        expect(summary).to_contain_text("2,353 supplied timing units")
        expect(summary).to_contain_text(
            "390 supplied caption blocks preserved from SRT"
        )
        expect(summary).to_contain_text("Audio referenced, not uploaded")
        expect(summary).to_contain_text("C02, C06, C08, C27, C31, C41, C42, C43")
        checks.append(
            "UI distinguishes provided units, grouped precision, exact SRT blocks, missing audio and eight candidate starts"
        )
        page.get_by_text("Review transcript differences (111)", exact=True).click()
        expect(page.get_by_label("Transcript differences", exact=True)).to_be_visible()
        checks.append(
            "111 comparison spans are accessible as review differences, not silently corrected"
        )
        assert (
            requests.get(url + "/captions.srt").text
            == (UP / "captions_continuous.srt.md").read_text()
        )
        checks.append(
            "Downloaded SRT byte-for-text matches all original 390 caption blocks"
        )
        before = requests.get(url + "/episode").json()
        toggle = page.get_by_role(
            "checkbox", name="Show captions (timing still needs review)", exact=True
        )
        with page.expect_response(
            lambda r: r.url.endswith("/episode/options") and r.request.method == "PATCH"
        ) as response:
            toggle.uncheck()
        assert response.value.status == 200
        expect(toggle).not_to_be_checked()
        after = requests.get(url + "/episode").json()
        assert before["word_clock"] == after["word_clock"]
        assert before["duration"] == after["duration"] == 903.533333
        checks.append(
            "Captions OFF retains the exact same imported word clock and 15:03.533 export duration"
        )
        expect(
            page.get_by_label("Narration cue timing reviewed", exact=True)
        ).to_be_disabled()
        expect(
            page.get_by_label("Timing transcript differences reviewed", exact=True)
        ).to_be_disabled()
        checks.append(
            "Timing and transcript approvals remain disabled without the actual recording"
        )
        with page.expect_response(
            lambda r: r.url.endswith("/episode/build") and r.request.method == "POST"
        ) as response:
            page.get_by_role(
                "button", name=re.compile(r"^(Preview|Rebuild) episode plan$")
            ).click()
        assert response.value.status == 200, response.value.text()
        p = requests.get(url).json()
        assert len(p["scenes"]) == 56
        assert not p["assets"] and p["narration_id"] is None
        assert p["episode"]["plan"]["has_voice"] is False
        assert all(s["captions_exact"] for s in p["scenes"])
        checks.append(
            "Rebuild creates a 56-scene timed, all-gap plan without pretending an audio reference is an upload"
        )
        page.screenshot(path=str(ROOT / "qa/capcut-import-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.reload(wait_until="networkidle")
        page.get_by_role("button", name="More settings", exact=True).click()
        expect(page.get_by_label("Imported timing summary", exact=True)).to_be_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        page.screenshot(path=str(ROOT / "qa/capcut-import-mobile.png"), full_page=True)
        checks.append(
            "390 px mobile layout has no horizontal overflow after the full timing pack import"
        )
        assert not errors, errors
        browser.close()
finally:
    if pid:
        (ROOT / "data/projects" / (pid + ".json")).unlink(missing_ok=True)
    (ROOT / "qa/capcut-browser-results.json").write_text(
        json.dumps(
            {
                "checks": checks,
                "count": len(checks),
                "browser_errors": errors,
                "temporary_project_removed": pid,
            },
            indent=2,
        )
    )
print(json.dumps(checks, indent=2))
