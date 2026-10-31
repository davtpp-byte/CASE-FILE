"""Actual guide UI regressions; no actual media, narration, approvals or rendering.

Mutates only a clearly named temporary metadata clone, never the prepared user case.
"""
from pathlib import Path
import copy,json,hashlib
import requests
from playwright.sync_api import sync_playwright,expect
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import storage

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8000';prepared=json.loads((ROOT/'qa/prepared-guide44-project.json').read_text());pid=None
checks=[];errors=[]
try:
 original=requests.get(BASE+'/api/projects/'+prepared['project_id']).json()
 q=requests.post(BASE+'/api/projects',json={'title':'Temporary updated-guide UI audit — no media','mode':'narration'});q.raise_for_status();pid=q.json()['id']
 clone=copy.deepcopy(original);clone.update(id=pid,title='Temporary updated-guide UI audit — no media');storage.save_project(clone)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1020})
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'?project='+pid,wait_until='networkidle')
  expect(page.get_by_text('WORKING PROTOTYPE · v0.3.5',exact=True)).to_be_visible()
  assert page.locator('.ep-cue').count()==44
  expect(page.get_by_label('Imported timing summary',exact=True)).to_contain_text('390 supplied caption blocks')
  checks.append('Updated 44-placement guide and preserved 390-block timing pack open in v0.3.5')
  def open_cue(cid):
   row=page.locator('.ep-cue').filter(has=page.get_by_text(cid,exact=True));row.locator(':scope > summary').click();return row
  c17=open_cue('C17')
  with page.expect_response(lambda r:r.url.endswith('/episode/choice/C17') and r.request.method=='PATCH') as resp:
   page.get_by_label('Source choice C17',exact=True).select_option('alternative:S01')
  assert resp.value.status==200
  expect(page.get_by_label('Alternative label C17',exact=True)).to_have_value('Portrait — not funeral footage')
  checks.append('C17 offers the explicitly linked portrait S01 and does not retain the funeral-footage label')
  for cid,clock in [('C36','0:05–0:09'),('C37','0:20–0:24')]:
   row=open_cue(cid)
   with page.expect_response(lambda r:r.url.endswith('/episode/choice/'+cid) and r.request.method=='PATCH') as resp:
    page.get_by_label('Source choice '+cid,exact=True).select_option('alternative:S17')
   assert resp.value.status==200
   expect(page.get_by_label('Alternative label '+cid,exact=True)).to_have_value('Courtroom coverage | September 2026.')
   expect(row).to_contain_text('Guide preview: '+clock)
  checks.append('C36 and C37 select S17 with separate 5–9s and 20–24s windows; neither identifies the alternative as Sinardi speaking')
  c34=open_cue('C34');assert page.get_by_label('Source choice C34',exact=True).count()==0
  expect(c34).to_contain_text('do not substitute 2026 sentencing footage')
  checks.append('C34 preserves the explicit ban on substituting 2026 footage for the December 2024 hearing')
  c16=open_cue('C16');expect(c16).to_contain_text('S26: 10 Tampa Bay: family appeal after the vigil')
  expect(c16).to_contain_text('Guide preview: 1:14–1:24 or 1:30–1:32')
  checks.append('C16 retains S26 as a separate follow-up, not an S25 timestamp or an automatic substitute')
  c40=open_cue('C40')
  picker=page.get_by_label('Source choice C40',exact=True)
  assert picker.locator('option[value="alternative:S20"]').count()==1
  expect(picker.locator('option[value="alternative:S20"]')).to_contain_text('Optional guide source')
  checks.append('C40 exposes S20 as an optional manual choice rather than a required primary upload')
  assert not any(requests.get(BASE+'/api/projects/'+pid).json()['review'].values())
  page.locator('.ep-cue').filter(has=page.get_by_text('C17',exact=True)).scroll_into_view_if_needed()
  page.screenshot(path=str(ROOT/'qa/guide44-alternatives-desktop.png'),full_page=True)
  page.set_viewport_size({'width':390,'height':844});page.reload(wait_until='networkidle')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  expect(page.get_by_role('button',name='Save project backup',exact=True)).to_be_visible()
  page.screenshot(path=str(ROOT/'qa/guide44-mobile.png'),full_page=True)
  checks.append('The 44-cue document and source selectors remain usable at 390 px with no horizontal overflow')
  assert not errors,errors;browser.close()
 report={'version':'0.3.5','checks':checks,'count':len(checks),'browser_errors':errors,'prepared_project_id':prepared['project_id'],'actual_case_rendered':False,'actual_media_received':0}
 (ROOT/'qa/guide44-browser-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 if pid:
  r=requests.request('DELETE',BASE+'/api/projects/'+pid+'/session',json={'confirm_download_saved':True});print('Temporary metadata-only clone removed:',r.status_code)
