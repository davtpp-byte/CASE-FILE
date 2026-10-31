"""Read-only discovery/layout checks for timestamp controls in the existing case.

No audio uploads, project changes, approvals, renders, provider calls or downloads.
"""
from pathlib import Path
import json
import requests
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8000'
PID = '7fa005880e97474f'
checks, errors = [], []
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(BASE, wait_until='networkidle')
    page.evaluate('(id)=>localStorage.setItem("casefile-project",id)', PID)
    page.reload(wait_until='networkidle')
    expect(page.get_by_text('WORKING PROTOTYPE · v0.3.2', exact=True)).to_be_visible()
    checks.append('The current build is visibly labeled v0.3.2')
    panel = page.get_by_role('region', name='Narration timestamps', exact=True)
    assert panel.locator('input[aria-label="Upload narration timings"]').count() == 1
    expect(panel.get_by_text('Upload SRT / JSON', exact=True)).to_be_visible()
    assert page.locator('.ep-materials input[aria-label="Upload narration timings"]').count() == 0
    checks.append('A dedicated timestamp panel contains the clearly labeled file picker, not the narration card')
    positions = page.evaluate('''() => {
      const materials = document.querySelector('.ep-materials');
      const panel = document.querySelector('.ep-timestamp-panel');
      const overview = document.querySelector('.ep-overview');
      return [!!(materials.compareDocumentPosition(panel) & 4), !!(panel.compareDocumentPosition(overview) & 4)];
    }''')
    assert positions == [True, True]
    checks.append('The panel is directly after the four input cards and before the metrics shown in the user screenshot')
    page.get_by_role('button', name='Go to timestamp uploader', exact=True).click()
    expect(panel).to_be_in_viewport(ratio=0.35)
    checks.append('The top SRT / JSON shortcut scrolls to the timestamp panel')
    expect(panel).to_contain_text('Attached to this project:')
    expected_sources = requests.get(BASE + '/api/projects/' + PID).json()['episode']['timings']['sources']
    for source in expected_sources:
        expect(panel).to_contain_text(source['filename'])
    expect(panel).to_contain_text('390 supplied caption blocks preserved from SRT')
    checks.append('Attached filenames and imported results stay visible per project')
    expect(page.get_by_role('note').filter(has_text='Guide links are references')).to_contain_text('Automatic link downloads are not available in this build')
    expect(page.get_by_role('note').filter(has_text='Guide links are references')).to_contain_text('do not need to pre-trim each clip')
    checks.append('Source upload copy explicitly explains that links are not files and full originals are usable')
    page.screenshot(path=str(ROOT / 'qa/timestamp-panel-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 1060, 'height': 900})
    page.reload(wait_until='networkidle')
    page.get_by_role('button', name='Go to timestamp uploader', exact=True).click()
    expect(panel).to_be_in_viewport(ratio=0.35)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(ROOT / 'qa/timestamp-panel-preview-width.png'), full_page=True)
    checks.append('The panel is usable at the narrow embedded-preview width from the screenshot')
    page.set_viewport_size({'width': 390, 'height': 844})
    page.reload(wait_until='networkidle')
    page.get_by_role('button', name='Go to timestamp uploader', exact=True).click()
    expect(panel.get_by_text('Upload SRT / JSON', exact=True)).to_be_in_viewport()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(ROOT / 'qa/timestamp-panel-mobile.png'), full_page=True)
    checks.append('Mobile 390 px: the upload button remains visible and no horizontal overflow occurs')
    assert not errors, errors
    browser.close()
version = requests.get(BASE + '/openapi.json').json()['info']['version']
assert version == '0.3.2'
assert requests.get(BASE, headers={'Host': '8000-casefile-preview.e2b.app'}).status_code == 200
Path(ROOT / 'qa/timestamp-ux-browser-results.json').write_text(json.dumps({'version': version, 'checks': checks, 'count': len(checks), 'browser_errors': errors, 'preview_host_accepted': True}, indent=2))
print(json.dumps(checks, indent=2))
