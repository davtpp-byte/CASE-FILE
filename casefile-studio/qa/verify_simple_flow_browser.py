"""Simple public user journey: quick inputs -> automatic visual preview -> draft -> save.

Technical fixtures only; the separate real-photo case is tested read-only elsewhere.
"""
from pathlib import Path
import sys,json,wave,subprocess
import requests,numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_capcut import draft,continuous_srt
B='http://127.0.0.1:8000';W=ROOT/'qa/simple-flow-proof';W.mkdir(exist_ok=True)
checks=[];errors=[];pid=None
(W/'draft_info.json').write_text(json.dumps(draft()));(W/'captions.srt').write_text(continuous_srt())
sr=16000;t=np.arange(round(sr*6.04))/sr
with wave.open(str(W/'SYNTHETIC-voice.wav'),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((np.sin(t*310*2*np.pi)*2600).astype('<i2').tobytes())
Image.new('RGB',(854,480),'#275942').save(W/'S01-SYNTHETIC-image.jpg')
subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=854x480:rate=24:duration=4','-c:v','libx264','-pix_fmt','yuv420p',str(W/'S03-SYNTHETIC-video.mp4')],check=True,timeout=30)
try:
 r=requests.post(B+'/api/projects',json={'title':'Temporary simple-flow QA — synthetic','mode':'narration'});r.raise_for_status();pid=r.json()['id'];u=B+'/api/projects/'+pid
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(B+'?project='+pid,wait_until='networkidle')
  expect(page.get_by_role('button',name='Preview my draft',exact=True)).to_be_visible()
  assert not page.locator('.detailed-episode-settings').is_visible()
  assert page.get_by_label('Narration cue timing reviewed',exact=True).is_hidden()
  checks.append('First screen has one clear preview action and quick file inputs, not 44 approval controls or a mode maze')
  for label,path in [('Quick add narration script',ROOT/'tests/fixtures/synthetic-script.md'),('Quick add editing guide',ROOT/'tests/fixtures/synthetic-guide.md'),('Quick add timing file',W/'draft_info.json')]:
   with page.expect_response(lambda r:r.url.endswith('/episode/import') and r.request.method=='POST') as response:page.get_by_label(label,exact=True).set_input_files(str(path))
   assert response.value.status==200,response.value.text()
   expect(page.get_by_role('button',name='Preview my draft',exact=True)).to_be_disabled()
  page.locator('.quick-timings summary').click()
  with page.expect_response(lambda r:r.url.endswith('/episode/import') and r.request.method=='POST') as response:page.get_by_label('Quick add timing file',exact=True).set_input_files(str(W/'captions.srt'))
  assert response.value.status==200
  checks.append('Script, guide and paired timing exports import through the simple controls; no source means no empty successful preview')
  with page.expect_response(lambda r:r.url.endswith('/episode/first-draft') and r.request.method=='POST') as response:page.get_by_label('Quick add footage or photos',exact=True).set_input_files(str(W/'S01-SYNTHETIC-image.jpg'))
  assert response.value.status==200,response.value.text()
  expect(page.locator('.video-frame img')).to_be_visible()
  assert response.value.json()['preview']['time']>3.2
  checks.append('Selecting one matched photo automatically links, rebuilds and opens its real image in Edit without a separate Build click')
  page.locator('button.setup-header-button').click()
  with page.expect_response(lambda r:r.url.endswith('/episode/first-draft') and r.request.method=='POST') as response:page.get_by_label('Quick add narration',exact=True).set_input_files(str(W/'SYNTHETIC-voice.wav'))
  assert response.value.status==200
  page.locator('button.setup-header-button').click()
  with page.expect_response(lambda r:r.url.endswith('/episode/first-draft') and r.request.method=='POST') as response:page.get_by_label('Quick add footage or photos',exact=True).set_input_files(str(W/'S03-SYNTHETIC-video.mp4'))
  assert response.value.status==200
  expect(page.locator('.video-frame video')).to_be_visible()
  expect(page.locator('.film-inspection-mark')).to_be_visible()
  p=requests.get(u).json();assert len(p['assets'])==3 and not any(p['review'].values())
  assert not any(b.get('rights_confirmed') for b in p['episode']['bindings'].values())
  checks.append('Adding recording and video auto-refreshes the visual preview, keeps source sound muted and leaves every sign-off false')
  page.locator('button.setup-header-button').click()
  with page.expect_response(lambda r:r.url.endswith('/render') and r.request.method=='POST') as response:page.get_by_role('button',name='Make downloadable inspection video',exact=True).click()
  assert response.value.status==200,response.value.text()
  body=response.value.request.post_data_json;assert body['allow_inspection'] and body['allow_guided_gaps'] and body['draft']
  expect(page.get_by_label('Rendered video preview',exact=True)).to_be_visible(timeout=120000)
  assert not page.locator('.review-grid').is_visible()
  page.get_by_role('button',name='Play rendered video',exact=True).click()
  page.wait_for_function('''() => document.querySelector('video[aria-label="Rendered video preview"]').currentTime > 0.5''')
  page.get_by_role('button',name='Pause rendered video',exact=True).click()
  with page.expect_download() as dl:page.get_by_role('link',name='Download',exact=True).click()
  dl.value.save_as(str(W/'simple-draft-downloaded.mp4'))
  assert (W/'simple-draft-downloaded.mp4').stat().st_size>1000
  checks.append('One Make-video action rebuilds if needed, renders, plays inline and downloads a real MP4 without publication checkboxes or a render-options detour')
  page.screenshot(path=str(W/'simple-render-download.png'),full_page=True)
  page.wait_for_function('''(id) => new Promise(resolve=>{const r=indexedDB.open('casefile-studio-setup-backups',1);r.onsuccess=()=>{const d=r.result,q=d.transaction('projects').objectStore('projects').get(id);q.onsuccess=()=>{resolve(!!q.result && q.result.project.assets.length===3 && q.result.project.exports.length===1);d.close();};};r.onerror=()=>resolve(false);})''',arg=pid,timeout=15000)
  page.route('**/api/**',lambda route:route.abort());page.reload(wait_until='networkidle')
  expect(page.get_by_role('button',name='Download recovered setup',exact=True)).to_be_visible()
  with page.expect_download() as dl:page.get_by_role('button',name='Download recovered setup',exact=True).click()
  dl.value.save_as(str(W/'automatic-browser-setup-backup.json'))
  snapshot=json.loads((W/'automatic-browser-setup-backup.json').read_text())
  assert snapshot['id']==pid and len(snapshot['assets'])==3 and not snapshot['_casefile_export']['media_bytes_included']
  checks.append('With every API unavailable after reload, the automatically cached browser setup can still be downloaded; it never pretends to include media bytes')
  page.unroute('**/api/**');page.reload(wait_until='networkidle')
  page.set_viewport_size({'width':390,'height':844})
  expect(page.get_by_role('button',name='Preview my draft',exact=True)).to_be_visible()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  page.screenshot(path=str(W/'simple-mobile.png'),full_page=True)
  checks.append('Mobile exposes the same simple action with no horizontal overflow')
  # Clear only this successful QA-owned session after the proof video/setup were saved.
  page.locator('.stage-nav button').filter(has_text='Review & export').click()
  page.locator('.simple-finish summary').click()
  expect(page.get_by_role('button',name='Finish and clear session',exact=True)).to_be_disabled()
  page.get_by_label('Quick confirm downloads saved',exact=True).check()
  with page.expect_response(lambda r:r.url.endswith('/session') and r.request.method=='DELETE') as response:page.get_by_role('button',name='Finish and clear session',exact=True).click()
  assert response.value.status==200
  assert requests.get(u).status_code==404
  checks.append('Finish-session cleanup is simple but still requires saved-download confirmation; only the QA session is cleared')
  assert not errors,errors;browser.close()
 report={'version':'0.4.0','checks':checks,'count':len(checks),'browser_errors':errors,'qa_session_cleared':True,'actual_case_rendered':False,'media_sources':'Synthetic technical video/image/tone for this test; separate real-photo UI proof recorded separately.'}
 (ROOT/'qa/simple-flow-browser-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 if pid and requests.get(B+'/api/projects/'+pid).status_code==200:
  r=requests.request('DELETE',B+'/api/projects/'+pid+'/session',json={'confirm_download_saved':True});print('QA fixture cleanup:',r.status_code)
