"""Read-only final check of the existing case project; never approves or renders it."""
from pathlib import Path
import json
import requests
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:8000'
PID = '7fa005880e97474f'
checks, errors = [], []
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1050})
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(BASE, wait_until='networkidle')
    page.evaluate('(id)=>localStorage.setItem("casefile-project",id)', PID)
    page.reload(wait_until='networkidle')
    expect(page.get_by_role('heading', name='The Last Timeline', exact=True)).to_be_visible()
    checks.append('Existing project opens with the imported pack')
    expect(page.get_by_label('Imported timing summary')).to_contain_text('390 supplied caption blocks preserved from SRT')
    expect(page.get_by_text('15:03.533', exact=True)).to_be_visible()
    checks.append('Export duration shown to the millisecond, without implying the recording was uploaded')
    assert page.locator('.ep-cue').count() == 43
    cue = page.locator('.ep-cue').filter(has=page.get_by_text('C05', exact=True))
    expect(cue).to_contain_text('0:51.993')
    checks.append('Cue badges expose millisecond positions, including a phrase inside an SRT block')
    expect(page.get_by_label('Narration cue timing reviewed', exact=True)).to_be_disabled()
    expect(page.get_by_label('Timing transcript differences reviewed', exact=True)).to_be_disabled()
    expect(page.get_by_role('button', name='Create guided review video', exact=True)).to_be_disabled()
    checks.append('No audio: both approvals and real documentary rendering remain blocked')
    expect(page.locator('.ep-plan-result')).to_contain_text('timed plan · audio missing')
    checks.append('Plan status does not call an imported clock a script-only estimate')
    page.locator('.episode-setup').evaluate('(e)=>e.scrollTop=0')
    page.screenshot(path='qa/the-last-timeline-capcut-desktop.png', full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.reload(wait_until='networkidle')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    page.screenshot(path='qa/the-last-timeline-capcut-mobile.png', full_page=True)
    checks.append('Actual saved project passes desktop and 390 px mobile layout')
    assert not errors, errors
    browser.close()
assert requests.get(BASE, headers={'Host': '8000-casefile-preview.e2b.app'}).status_code == 200
Path('qa/capcut-final-ui.json').write_text(json.dumps({'checks': checks, 'count': len(checks), 'browser_errors': errors, 'preview_host_accepted': True}, indent=2))
print(json.dumps(checks, indent=2))
