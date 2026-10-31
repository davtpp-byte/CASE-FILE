"""Real browser/XHR checks: missing-main alternative, explicit choices, honest upload progress.

Synthetic technical sources only. Keeps one small demo, never edits existing cases.
"""
from pathlib import Path
import sys,json,subprocess,wave
import requests,numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_capcut import draft,continuous_srt
BASE='http://127.0.0.1:8000';W=ROOT/'qa/alternative-upload-proof';W.mkdir(exist_ok=True)
checks=[];errors=[];pid=None;success=False;keep_demo='--temporary' not in sys.argv
raw=(ROOT/'tests/fixtures/synthetic-guide.md').read_text().replace('**Care:** Technical fixture, not actual footage.','**Alternative:** `S01` permitted synthetic portrait if the main source is missing. **Alternative label:** SYNTHETIC GUIDE ALTERNATIVE — NOT PRIMARY EVENT FOOTAGE **Care:** Technical fixture, not actual footage.')
(W/'synthetic-guide-with-alternative.md').write_text(raw)
(W/'draft_info.json').write_text(json.dumps(draft()));(W/'captions.srt').write_text(continuous_srt())
rate=16000;t=np.arange(round(rate*6.04))/rate
with wave.open(str(W/'SYNTHETIC-voice-tone.wav'),'wb') as f:
 f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes((np.sin(t*310*2*np.pi)*2600).astype('<i2').tobytes())
# A non-trivially sized real file makes genuine network byte events observable.
im=np.random.default_rng(41).integers(0,256,(512,512,3),dtype=np.uint8)
Image.fromarray(im).save(W/'S01-SYNTHETIC-noise-image.png')
try:
 r=requests.post(BASE+'/api/projects',json={'title':'Alternatives + upload feedback — SYNTHETIC DEMO','mode':'narration'});r.raise_for_status();pid=r.json()['id'];url=BASE+'/api/projects/'+pid
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'?project='+pid,wait_until='networkidle')
  for label,path in [('Upload narration script',ROOT/'tests/fixtures/synthetic-script.md'),('Upload editing guide',W/'synthetic-guide-with-alternative.md'),('Upload narration timings',W/'draft_info.json'),('Upload narration timings',W/'captions.srt')]:
   with page.expect_response(lambda r:r.url.endswith('/episode/import') and r.request.method=='POST') as resp:
    page.get_by_label(label,exact=True).set_input_files(str(path))
   assert resp.value.status==200,resp.value.text()
   expect(page.get_by_label(label,exact=True)).to_be_enabled()
  expect(page.get_by_text('512 MB maximum · one narration file at a time',exact=True)).to_be_visible()
  expect(page.get_by_text('Media limit: 512 MB per file · up to 30 files per batch. The limit is per file, not 512 MB for the whole batch.',exact=True)).to_be_visible()
  checks.append('Size/count limits are visible beside narration, music and source upload controls')
  with page.expect_response(lambda r:r.url.endswith('/episode/options') and r.request.method=='PATCH') as resp:
   page.get_by_label('Upload finished narration',exact=True).set_input_files(str(W/'SYNTHETIC-voice-tone.wav'))
  assert resp.value.status==200
  expect(page.get_by_label('Upload source footage',exact=True)).to_be_enabled()
  cdp=page.context.new_cdp_session(page);cdp.send('Network.enable')
  cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':80,'downloadThroughput':8192,'uploadThroughput':98304})
  page.get_by_label('Upload source footage',exact=True).set_input_files(str(W/'S01-SYNTHETIC-noise-image.png'))
  page.wait_for_function('''() => {const p=document.querySelector('.upload-progress.uploading progress');return p && p.value>0 && p.value<100;}''',timeout=30000)
  expect(page.locator('.upload-progress.uploading')).to_be_in_viewport(ratio=0.5)
  measured=page.locator('.upload-progress.uploading progress').evaluate('(e)=>e.value')
  assert 0<measured<100
  page.screenshot(path=str(W/'genuine-upload-progress.png'),full_page=True)
  checks.append('Real throttled XHR upload reports an intermediate byte-based percentage and transferred sizes, not a timer')
  expect(page.locator('.upload-progress.processing')).to_be_visible(timeout=30000)
  expect(page.locator('.upload-progress.processing')).to_contain_text('Transfer complete — processing media on the server')
  page.screenshot(path=str(W/'processing-after-transfer.png'),full_page=True)
  cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':0,'downloadThroughput':-1,'uploadThroughput':-1})
  expect(page.get_by_label('Upload source footage',exact=True)).to_be_enabled(timeout=30000)
  expect(page.locator('.upload-progress.done')).to_contain_text('Upload and media processing complete')
  checks.append('100% transfer is followed by a distinct processing state; completion waits for server metadata processing')
  a=requests.get(url+'/episode').json();p=requests.get(url).json()
  assert a['linked_source_count']==1 and a['used_source_count']==2 and a['alternative_cues']==1
  assert a['placements'][0]['source_id']=='S01' and a['placements'][0]['using_alternative']
  assert a['ready_cues']==0 and a['inspection_cues']==2
  assert not any(p['review'].values())
  expect(page.get_by_text('Final placement sign-offs',exact=False)).to_be_visible()
  expect(page.get_by_text('0 is okay for an inspection draft.',exact=True)).to_be_visible()
  checks.append('A missing S03 main automatically resolves to guide-permitted S01, with zero final sign-offs and no primary-file demand')
  cue=page.locator('.ep-cue').first;cue.locator(':scope > summary').click()
  picker=page.get_by_label('Source choice C01',exact=True)
  expect(picker).to_have_value('auto')
  expect(cue).to_contain_text('SYNTHETIC GUIDE ALTERNATIVE — NOT PRIMARY EVENT FOOTAGE')
  with page.expect_response(lambda r:r.url.endswith('/episode/choice/C01') and r.request.method=='PATCH') as resp:picker.select_option('primary')
  assert resp.value.status==200 and resp.value.json()['analysis']['placements'][0]['source_id']=='S03'
  with page.expect_response(lambda r:r.url.endswith('/episode/choice/C01') and r.request.method=='PATCH') as resp:picker.select_option('alternative:S01')
  assert resp.value.status==200 and resp.value.json()['analysis']['placements'][0]['source_id']=='S01'
  checks.append('Per-placement Automatic/Main/Alternative selector obeys the user and shows the alternative’s own label')
  # Leave the live demo in automatic fallback mode; do not fabricate reviews.
  picker.select_option('auto');expect(picker).to_be_enabled()
  p=requests.get(url).json();assert not p['episode']['reviews'] or not any(r.get('reviewed') for r in p['episode']['reviews'].values())
  expect(page.get_by_text('Before final export: your review acknowledgements',exact=True)).to_be_visible()
  expect(page.get_by_text('This records your listening review. It does not run synchronization or create footage.',exact=True)).to_be_visible()
  checks.append('Review checkboxes have plain-language purposes and explicitly state that they are not required for inspection')
  count=len(p['assets']);requests_seen=[]
  page.on('request',lambda r:requests_seen.append(r.url) if r.method=='POST' and r.url.endswith('/upload') else None)
  page.evaluate('Object.defineProperty(File.prototype,"size",{configurable:true,get(){return 513*1024*1024;}})')
  page.get_by_label('Upload source footage',exact=True).set_input_files(str(W/'S01-SYNTHETIC-noise-image.png'))
  expect(page.locator('.toast.error')).to_contain_text('limit is 512 MB per file')
  assert not requests_seen and len(requests.get(url).json()['assets'])==count
  page.evaluate('delete File.prototype.size')
  checks.append('Client rejects an oversized selection before sending any upload request, with a clear size-limit error')
  payload={'name':'tiny-synthetic.png','mimeType':'image/png','buffer':(W/'S01-SYNTHETIC-noise-image.png').read_bytes()[:100]}
  page.get_by_label('Upload source footage',exact=True).set_input_files([dict(payload,name=f'S{i:02d}-synthetic.png') for i in range(31)])
  expect(page.locator('.toast.error')).to_contain_text('up to 30 files per batch')
  assert not requests_seen
  checks.append('Client rejects a 31-file batch before upload; limits are per file and per batch, not hidden')
  with page.expect_response(lambda r:r.url.endswith('/episode/build') and r.request.method=='POST') as resp:
   page.get_by_role('button',name='Preview episode plan',exact=True).click()
  assert resp.value.status==200,resp.value.text()
  p=resp.value.json()['project'];assert p['episode']['plan']['unreviewed_cues']==2
  assert any(s.get('guide_alternative') and s['asset_id'] for s in p['scenes'])
  page.get_by_role('button',name='View timeline',exact=True).click()
  expect(page.locator('.video-frame img')).to_be_visible()
  expect(page.locator('.film-source-label')).to_contain_text('SYNTHETIC GUIDE ALTERNATIVE')
  checks.append('Inspection timeline displays the permitted replacement with its own label, not a gap or the missing source’s event label')
  page.screenshot(path=str(W/'alternative-in-timeline.png'),full_page=True)
  page.locator('button.setup-header-button').click()
  page.set_viewport_size({'width':390,'height':844});page.reload(wait_until='networkidle')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  expect(page.get_by_role('button',name='Save project backup',exact=True)).to_be_visible()
  page.screenshot(path=str(W/'mobile-upload-and-help.png'),full_page=True)
  checks.append('Mobile: upload/help/choice layout has no horizontal overflow and backup remains reachable')
  assert not errors,errors
  browser.close()
 success=True
 report={'version':'0.3.4','project_id':pid,'title':'Alternatives + upload feedback — SYNTHETIC DEMO','checks':checks,'count':len(checks),'browser_errors':errors,'intermediate_actual_upload_percent':measured,'source_downloads':0,'paid_provider_calls':0,'actual_user_guide':'Latest 44-placement guide not yet supplied; exact two missing sources are not claimed resolved.'}
 (ROOT/('qa/alternatives-uploads-browser-results.json' if keep_demo else 'qa/alternatives-uploads-browser-results-final.json')).write_text(json.dumps({**report,'temporary_fixture':not keep_demo},indent=2));print(json.dumps(report,indent=2))
finally:
 if pid and (not success or not keep_demo):
  r=requests.request('DELETE',BASE+'/api/projects/'+pid+'/session',json={'confirm_download_saved':True});print('QA-only fixture cleanup:',pid,r.status_code)
