"""Verify the actual iframe restriction and automatic local-file session recovery.

Uses only an owned synthetic QA project; server-loss simulation moves only its
files. Existing user projects, originals and publication approvals are untouched.
"""
from pathlib import Path
import sys,json,shutil
import requests
from playwright.sync_api import sync_playwright,expect,Error
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_capcut import draft,continuous_srt
B='http://127.0.0.1:8000';W=ROOT/'qa/frame-recovery-proof';W.mkdir(exist_ok=True)
inputs=ROOT/'qa/simple-flow-proof';checks=[];errors=[];pid=None
(W/'draft_info.json').write_text(json.dumps(draft()));(W/'captions.srt').write_text(continuous_srt())
backup=W/'simulated-lost-server';backup.mkdir(exist_ok=True)
try:
 r=requests.post(B+'/api/projects',json={'title':'Temporary browser-file recovery QA — synthetic','mode':'narration'});r.raise_for_status();pid=r.json()['id'];u=B+'/api/projects/'+pid
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport={'width':1440,'height':1020},accept_downloads=True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));trace=[];page.on('response',lambda r:trace.append({'url':r.url,'status':r.status}) if '/api/' in r.url else None);page.on('console',lambda m:trace.append({'console':m.text}) if m.type in ['error','warning','debug'] else None)
  page.goto(B+'?project='+pid,wait_until='networkidle')
  for label,path in [('Quick add narration script',ROOT/'tests/fixtures/synthetic-script.md'),('Quick add editing guide',ROOT/'tests/fixtures/synthetic-guide.md'),('Quick add timing file',W/'draft_info.json')]:
   with page.expect_response(lambda r:r.url.endswith('/episode/import') and r.request.method=='POST') as resp:page.get_by_label(label,exact=True).set_input_files(str(path))
   assert resp.value.status==200,resp.value.text()
  page.locator('.quick-timings summary').click()
  with page.expect_response(lambda r:r.url.endswith('/episode/import') and r.request.method=='POST') as resp:page.get_by_label('Quick add timing file',exact=True).set_input_files(str(W/'captions.srt'))
  assert resp.value.status==200
  with page.expect_response(lambda r:r.url.endswith('/episode/options') and r.request.method=='PATCH') as resp:page.get_by_label('Quick add narration',exact=True).set_input_files(str(inputs/'SYNTHETIC-voice.wav'))
  assert resp.value.status==200
  with page.expect_response(lambda r:r.url.endswith('/episode/first-draft') and r.request.method=='POST') as resp:page.get_by_label('Quick add footage or photos',exact=True).set_input_files([str(inputs/'S01-SYNTHETIC-image.jpg'),str(inputs/'S03-SYNTHETIC-video.mp4')])
  assert resp.value.status==200;expect(page.locator('.video-frame video')).to_be_visible()
  page.wait_for_function('''(id)=>new Promise(resolve=>{const r=indexedDB.open('casefile-studio-working-files',1);r.onsuccess=()=>{const d=r.result,q=d.transaction('files').objectStore('files').getAll();q.onsuccess=()=>{resolve(q.result.filter(x=>x.project_id===id).length===7);d.close();};};r.onerror=()=>resolve(false);})''',arg=pid,timeout=15000)
  page.wait_for_function('''(id)=>new Promise(resolve=>{const r=indexedDB.open('casefile-studio-setup-backups',1);r.onsuccess=()=>{const d=r.result,q=d.transaction('projects').objectStore('projects').get(id);q.onsuccess=()=>{resolve(!!q.result&&q.result.project.assets.length===3);d.close();};};r.onerror=()=>resolve(false);})''',arg=pid,timeout=15000)
  checks.append('Original script/guide/timing files and accepted audio/video/photo are cached locally for the active working session')
  page.wait_for_timeout(800)  # Allow the async transaction to commit, not just a truthy Promise object.
  cached_before=page.evaluate('''(id)=>new Promise(resolve=>{const r=indexedDB.open('casefile-studio-setup-backups',1);r.onsuccess=()=>{const d=r.result,q=d.transaction('projects').objectStore('projects').get(id);q.onsuccess=()=>resolve(q.result);};})''',pid)
  assert len(cached_before['project']['assets'])==3,cached_before
  (W/'cache-before-loss.json').write_text(json.dumps(cached_before,indent=2))
  before=requests.get(u).json();before_srt=requests.get(u+'/captions.srt').text
  shutil.move(str(ROOT/'data/projects'/f'{pid}.json'),str(backup/'project.json'))
  shutil.move(str(ROOT/'data/media'/pid),str(backup/'media'))
  assert requests.get(u).status_code==404
  page.reload(wait_until='networkidle')
  page.wait_for_timeout(3500)
  (W/'last-recovery-trace.json').write_text(json.dumps({'network':trace,'body':page.locator('body').inner_text(),'server_project':requests.get(u).json()},indent=2))
  expect(page.get_by_role('button',name='Preview my draft',exact=True)).to_be_enabled(timeout=15000)
  restored=requests.get(u).json();assert len(restored['assets'])==3 and restored['narration_id'] and restored['episode']['timings']['precision']=='provided-timed-units'
  assert requests.get(u+'/captions.srt').text==before_srt
  assert all(x['exists'] for x in requests.get(u+'/media-status').json()['assets'])
  assert not any(restored['review'].values())
  checks.append('After project JSON and uploaded copies disappear, reload recreates the setup and restores all three originals from browser cache without another file selection')
  with page.expect_response(lambda r:r.url.endswith('/episode/first-draft') and r.request.method=='POST') as resp:page.get_by_role('button',name='Preview my draft',exact=True).click()
  assert resp.value.status==200
  expect(page.locator('.video-frame video')).to_be_visible();expect(page.locator('.film-inspection-mark')).to_be_visible()
  checks.append('Recovered source links, exact captions and recording produce a real inspection preview; no sign-offs are invented')
  page.locator('button.setup-header-button').click()
  with page.expect_response(lambda r:r.url.endswith('/render') and r.request.method=='POST') as resp:page.get_by_role('button',name='Make downloadable inspection video',exact=True).click()
  assert resp.value.status==200,resp.value.text()
  expect(page.get_by_label('Rendered video preview',exact=True)).to_be_visible(timeout=120000)
  with page.expect_download() as dl:page.get_by_role('link',name='Download latest MP4',exact=True).click()
  dl.value.save_as(str(W/'full-browser-saved.mp4'))
  assert (W/'full-browser-saved.mp4').stat().st_size>1000
  checks.append('Normal full-browser context saves the completed MP4 successfully')
  rendered=requests.get(u).json()['exports'][0];download=u+'/exports/'+rendered['id']+'/download'
  outer=ctx.new_page();outer.on('pageerror',lambda e:errors.append(str(e)));console=[];outer.on('console',lambda m:console.append(m.text))
  outer.goto(B,wait_until='networkidle')
  outer.set_content(f'<iframe id="editor" sandbox="allow-scripts allow-forms allow-same-origin allow-modals allow-pointer-lock" src="{B}?project={pid}" style="width:1400px;height:1000px"></iframe>')
  frame=outer.frame_locator('#editor');expect(frame.get_by_role('link',name='Download latest MP4',exact=True)).to_be_visible(timeout=30000)
  await_download=[];outer.on('download',lambda d:await_download.append(d))
  frame.get_by_role('link',name='Download latest MP4',exact=True).click()
  expect(frame.get_by_role('heading',name='This preview frame blocks saving files',exact=True)).to_be_visible()
  expect(frame.get_by_label('Outside preview save address',exact=True)).to_have_value(download)
  checks.append('Exact Arena live-preview sandbox flags reproduce the restriction; Save now explains the block and exposes a direct outside-frame address instead of doing nothing')
  # Browser permission proof: a raw anchor with no app handling is also blocked.
  frame.locator('body').evaluate('''(body,url)=>{const a=document.createElement('a');a.id='raw-browser-download-proof';a.style.cssText='position:fixed;left:10px;top:10px;z-index:999999;background:white;color:black;padding:8px';a.href=url;a.download='proof.mp4';a.textContent='Raw sandbox download test';body.appendChild(a);}''',download)
  frame.locator('#raw-browser-download-proof').click(force=True)
  outer.wait_for_timeout(700)
  assert not await_download
  assert any('Download is disallowed' in text or 'sandbox' in text.lower() and 'download' in text.lower() for text in console),console
  checks.append('Chrome confirms a raw file-download anchor is disallowed by the sandbox, independently of file existence or review checkboxes')
  normal=ctx.new_page()
  with normal.expect_download() as dl:
   try:normal.goto(download)
   except Error:pass  # Attachment navigation intentionally becomes a download.
  dl.value.save_as(str(W/'direct-address-saved.mp4'))
  assert (W/'direct-address-saved.mp4').read_bytes()==(W/'full-browser-saved.mp4').read_bytes()
  checks.append('The same direct address outside the sandbox saves identical video bytes without a new render')
  assert not errors,errors
  browser.close()
 report={'version':'0.4.2','checks':checks,'count':len(checks),'browser_errors':errors,'sandbox_flags':'allow-scripts allow-forms allow-same-origin allow-modals allow-pointer-lock','downloads_granted':False,'source_of_embedding_config':'https://arena.ai/_next/static/immutable/chunks/3e0-f38uxk4ko.js','actual_case_rendered':False,'fixtures':'Only synthetic technical WAV/MP4/JPEG; no user-original recording/footage.'}
 (ROOT/'qa/frame-session-recovery-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 if pid:
  r=requests.request('DELETE',B+'/api/projects/'+pid+'/session',json={'confirm_download_saved':True});print('QA-only session cleanup:',r.status_code)
 # The simulated-lost server copies belong only to this known QA project.
 shutil.rmtree(backup,ignore_errors=True)
