"""Shared release proof on a different guide: S03 -> S12, not Last Timeline IDs."""
from pathlib import Path
import sys,json,wave
import requests,numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from test_capcut import draft,continuous_srt
from test_episode import SCRIPT,GUIDE
B='http://127.0.0.1:8000';W=ROOT/'qa/applied-fallback-proof';W.mkdir(exist_ok=True)
Image.new('RGB',(854,480),'#225f3b').save(W/'S12-future-synthetic.jpg')
sr=16000;t=np.arange(round(sr*6.04))/sr
with wave.open(str(W/'synthetic-tone.wav'),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes((np.sin(t*310*2*np.pi)*2500).astype('<i2').tobytes())
raw=GUIDE.replace('**Care:** Technical fixture, not actual footage.','**Alternative:** S12 synthetic portrait. **Alternative label:** FUTURE GUIDE S12 — NOT PRIMARY FOOTAGE **Care:** Technical fixture, not actual footage.')
checks=[];errors=[];pid=None
try:
 r=requests.post(B+'/api/projects',json={'title':'Temporary future-guide fallback + download QA','mode':'narration'});r.raise_for_status();pid=r.json()['id'];u=B+'/api/projects/'+pid
 for role,text,name in [('script',SCRIPT,'script.md'),('guide',raw,'future-guide.md'),('timings',json.dumps(draft()),'draft_info.json'),('timings',continuous_srt(),'captions.srt')]:
  r=requests.post(u+'/episode/import',json={'role':role,'text':text,'filename':name});r.raise_for_status()
 with (W/'S12-future-synthetic.jpg').open('rb') as f:r=requests.post(u+'/upload',data={'episode_role':'sources'},files={'files':('S12-future-synthetic.jpg',f,'image/jpeg')});r.raise_for_status()
 aid=r.json()['assets'][0]['id']
 with (W/'synthetic-tone.wav').open('rb') as f:r=requests.post(u+'/upload',data={'episode_role':'narration'},files={'files':('synthetic-tone.wav',f,'audio/wav')});r.raise_for_status()
 audio=next(a for a in r.json()['assets'] if a['kind']=='audio');requests.patch(u+'/episode/options',json={'narration_id':audio['id']}).raise_for_status()
 # Same mistake as the screenshot, but with completely different source IDs.
 r=requests.patch(u+'/episode/source/S03',json={'asset_id':aid});r.raise_for_status();p=r.json()['project']
 assert p['episode']['bindings']['S03']['asset_id'] is None and p['episode']['bindings']['S12']['asset_id']==aid
 assert r.json()['analysis']['placements'][0]['source_id']=='S12'
 checks.append('A manually assigned replacement is automatically reclassified through the API using this future guide, without user remapping')
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1020},accept_downloads=True);page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(B+'?project='+pid,wait_until='networkidle')
  expect(page.get_by_role('button',name='Make video',exact=True)).to_be_visible()
  with page.expect_response(lambda r:r.url.endswith('/episode/first-draft') and r.request.method=='POST') as response:page.get_by_role('button',name='Preview my draft',exact=True).click()
  assert response.value.status==200
  expect(page.locator('.video-frame img')).to_be_visible();expect(page.locator('.film-source-label')).to_contain_text('FUTURE GUIDE S12')
  assert not any(requests.get(u).json()['review'].values())
  checks.append('One preview action displays the permitted alternate with its own label while all approval flags remain false')
  page.locator('button.setup-header-button').click()
  with page.expect_response(lambda r:r.url.endswith('/render') and r.request.method=='POST') as response:page.get_by_role('button',name='Make downloadable inspection video',exact=True).click()
  assert response.value.status==200,response.value.text()
  expect(page.get_by_label('Rendered video preview',exact=True)).to_be_visible(timeout=120000)
  page.get_by_role('button',name='Play rendered video',exact=True).click();page.wait_for_function('''() => document.querySelector('video[aria-label="Rendered video preview"]').currentTime > 0.6''');page.get_by_role('button',name='Pause rendered video',exact=True).click()
  checks.append('An actual synthetic inspection MP4 renders and plays inline with the resolved source')
  jobs=requests.get(u+'/jobs').json();before=[j['id'] for j in jobs]
  with page.expect_download() as dl:page.get_by_role('link',name='Download latest MP4',exact=True).click()
  dl.value.save_as(str(W/'completed-download.mp4'))
  assert (W/'completed-download.mp4').stat().st_size>1000
  assert [j['id'] for j in requests.get(u+'/jobs').json()]==before
  ex=requests.get(u).json()['exports'][0];response=requests.get(u+'/exports/'+ex['id']+'/download')
  assert response.headers['Content-Disposition'].startswith('attachment;') and response.content==(W/'completed-download.mp4').read_bytes()
  checks.append('Header Download MP4 saves the existing attachment with matching bytes and never queues another render')
  page.locator('.download-help summary').click()
  direct=page.get_by_label('Direct MP4 download link '+ex['id'],exact=True).input_value()
  assert direct==u+'/exports/'+ex['id']+'/download'
  assert requests.get(direct,headers={'Range':'bytes=0-7'}).status_code==206
  checks.append('A direct outside-frame download URL is exposed and supports byte ranges for browser fallback')
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  expect(page.get_by_role('link',name='Download latest MP4',exact=True)).to_be_visible()
  page.screenshot(path=str(W/'mobile-completed-download.png'),full_page=True)
  checks.append('Mobile keeps the completed-file download visible without horizontal overflow')
  assert not errors,errors;browser.close()
 report={'version':'0.4.1','checks':checks,'count':len(checks),'browser_errors':errors,'actual_user_project_modified':False,'fixtures':'Separate future-guide synthetic photo and continuous tone; no actual case narration/footage.'}
 (ROOT/'qa/applied-fallback-browser-results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 if pid:
  r=requests.request('DELETE',B+'/api/projects/'+pid+'/session',json={'confirm_download_saved':True});print('QA-only synthetic session cleanup:',r.status_code)
