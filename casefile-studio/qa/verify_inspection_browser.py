"""Browser-to-real-MP4 proof using synthetic sources only; no real-case media.

Keeps one clearly labeled technical demo on success. Never imports into, renders,
clears or modifies either existing user/example project.
"""
from pathlib import Path
import sys,json,subprocess,wave,hashlib
import requests
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))
from test_capcut import draft,continuous_srt

BASE='http://127.0.0.1:8000';WORK=ROOT/'qa/inspection-proof';WORK.mkdir(exist_ok=True)
checks=[];errors=[];pid=None;success=False

def write_tone(path,seconds,hz):
 sr=16000;samples=(np.sin(np.arange(round(sr*seconds))*2*np.pi*hz/sr)*2600).astype('<i2')
 with wave.open(str(path),'wb') as f:f.setparams((1,2,sr,0,'NONE','not compressed'));f.writeframes(samples.tobytes())

write_tone(WORK/'SYNTHETIC-narration-tone.wav',6.04,310)
subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=size=854x480:rate=24:duration=4','-f','lavfi','-i','sine=frequency=990:sample_rate=16000:duration=4','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(WORK/'S03-SYNTHETIC-source.mp4')],check=True,timeout=30)
im=Image.new('RGB',(854,480),'#28643c');draw=ImageDraw.Draw(im)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',28)
draw.text((55,165),'S01 — SYNTHETIC TECHNICAL IMAGE',font=font,fill='white')
draw.text((55,215),'NOT CASE EVIDENCE',font=font,fill='white');im.save(WORK/'S01-SYNTHETIC-photo.jpg')
(WORK/'draft_info.json').write_text(json.dumps(draft()))
(WORK/'captions.srt').write_text(continuous_srt())
(WORK/'synthetic-guide.md').write_text((ROOT/'tests/fixtures/synthetic-guide.md').read_text().replace('around 0:01–0:02', 'around 0:01–0:04'))
try:
 r=requests.post(BASE+'/api/projects',json={'title':'Inspection workflow demo — SYNTHETIC MEDIA','mode':'narration'});r.raise_for_status();pid=r.json()['id'];url=BASE+'/api/projects/'+pid
 (WORK/'project-id.txt').write_text(pid)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1020},accept_downloads=True)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'?project='+pid,wait_until='networkidle')
  expect(page.get_by_role('heading',name='Inspection workflow demo — SYNTHETIC MEDIA',exact=True)).to_be_visible()
  for label,path in [('Upload narration script',ROOT/'tests/fixtures/synthetic-script.md'),('Upload editing guide',WORK/'synthetic-guide.md'),('Upload narration timings',WORK/'draft_info.json'),('Upload narration timings',WORK/'captions.srt')]:
   with page.expect_response(lambda r:r.url.endswith('/episode/import') and r.request.method=='POST') as response:
    page.get_by_label(label,exact=True).set_input_files(str(path))
   assert response.value.status==200,response.value.text()
   expect(page.get_by_label(label,exact=True)).to_be_enabled()
  with page.expect_response(lambda r:r.url.endswith('/episode/options') and r.request.method=='PATCH') as response:
   page.get_by_label('Upload finished narration',exact=True).set_input_files(str(WORK/'SYNTHETIC-narration-tone.wav'))
  assert response.value.status==200,response.value.text()
  expect(page.get_by_label('Upload source footage',exact=True)).to_be_enabled()
  with page.expect_response(lambda r:r.url.endswith('/episode/autolink') and r.request.method=='POST') as response:
   page.get_by_label('Upload source footage',exact=True).set_input_files([str(WORK/'S03-SYNTHETIC-source.mp4'),str(WORK/'S01-SYNTHETIC-photo.jpg')])
  assert response.value.status==200,response.value.text()
  expect(page.get_by_role('button',name='Preview source S03',exact=True)).to_be_visible()
  p=requests.get(url).json()
  assert len(p['assets'])==3 and len(p['episode']['bindings'])==2
  assert not any(p['review'].values()) and not any(b.get('rights_confirmed') for b in p['episode']['bindings'].values())
  checks.append('Synthetic timing files, duration-matched technical audio and two source files import through browser; unique source IDs auto-link without approving anything')
  page.get_by_role('button',name='Preview source S03',exact=True).click()
  source=page.get_by_label('Review source S03',exact=True)
  expect(source).to_be_visible()
  page.wait_for_function('''() => {const v=document.querySelector('video[aria-label="Review source S03"]'); return v && v.readyState>=2 && v.videoWidth>0;}''')
  assert source.evaluate('(v)=>v.muted && !v.loop && v.duration===4')
  checks.append('A real uploaded video plays in source inspection with zero rights/placement sign-offs')
  expect(page.get_by_label('Guide planning mode',exact=True)).to_have_value('inspection')
  with page.expect_response(lambda r:r.url.endswith('/episode/build') and r.request.method=='POST') as response:
   page.get_by_role('button',name='Preview episode plan',exact=True).click()
  assert response.value.status==200,response.value.text()
  p=response.value.json()['project']
  assert p['episode']['plan']['mode']=='inspection' and p['episode']['plan']['visual_seconds']>3
  assert all(s['inspection_only'] for s in p['scenes'])
  assert not any(p['review'].values()) and not p['episode']['reviews']
  checks.append('Inspection build places actual linked media on the narration clock, preserves short-window gaps and keeps every approval false')
  page.get_by_role('button',name='View timeline',exact=True).click()
  expect(page.locator('.video-frame video')).to_be_visible()
  expect(page.locator('.film-inspection-mark')).to_be_visible()
  expect(page.locator('.film-source-label')).to_contain_text('SYNTHETIC TEST PATTERN')
  page.wait_for_function('''() => {const v=document.querySelector('.video-frame video'); return v && v.readyState>=2 && v.currentTime>=1;}''')
  assert page.locator('.video-frame video').evaluate('(v)=>v.muted && !v.loop')
  page.get_by_role('button',name='Play preview',exact=True).click()
  expect(page.get_by_role('button',name='Pause preview',exact=True)).to_be_visible()
  page.get_by_role('button',name='Pause preview',exact=True).click()
  page.screenshot(path=str(WORK/'timeline-desktop.png'),full_page=True)
  checks.append('View timeline seeks to the first real visual, not the initial gap; playback, source label and unreviewed disclosure are visible')
  # Prove a project snapshot download can work without any server API response.
  page.route('**/api/**',lambda route:route.abort())
  with page.expect_download() as dl:
   page.get_by_role('button',name='Save project backup',exact=True).click()
  dl.value.save_as(str(WORK/'browser-project-backup.json'))
  snapshot=json.loads((WORK/'browser-project-backup.json').read_text())
  assert snapshot['id']==pid and len(snapshot['assets'])==3 and 'undo' not in snapshot
  page.unroute('**/api/**')
  checks.append('Save backup downloads the live browser project even with every API request blocked; no video render is needed')
  page.locator('button.setup-header-button').click()
  page.get_by_label('Guide draft resolution',exact=True).select_option('480p')
  expect(page.get_by_role('button',name='Create guided review video',exact=True)).to_be_disabled()
  page.get_by_label('Allow marked visual gaps',exact=True).check()
  with page.expect_response(lambda r:r.url.endswith('/render') and r.request.method=='POST') as response:
   page.get_by_role('button',name='Create guided review video',exact=True).click()
  assert response.value.status==200,response.value.text()
  assert response.value.request.post_data_json['allow_inspection'] is True
  expect(page.get_by_label('Rendered video preview',exact=True)).to_be_visible(timeout=120000)
  page.wait_for_function('''() => {const v=document.querySelector('video[aria-label="Rendered video preview"]'); return v && v.readyState>=2 && v.videoWidth>0;}''')
  rendered=page.get_by_label('Rendered video preview',exact=True)
  assert rendered.evaluate('(v)=>v.duration>6 && v.controls')
  page.get_by_role('button',name='Play rendered video',exact=True).click()
  page.wait_for_function('''() => {const v=document.querySelector('video[aria-label="Rendered video preview"]'); return v && v.currentTime>0.5 && !v.paused;}''')
  page.get_by_role('button',name='Pause rendered video',exact=True).click()
  checks.append('The browser starts a real inspection render; the encoded MP4 plays and pauses inline before download despite final-only blockers')
  link=page.locator('.export-row a.btn').first
  if link.count()==0:link=page.get_by_role('link',name='Download',exact=True).first
  with page.expect_download() as dl:link.click()
  proof=ROOT.parent/'Casefile-Studio-Inspection-Proof.mp4';dl.value.save_as(str(proof))
  ex=requests.get(url).json()['exports'][0]
  assert proof.read_bytes()==requests.get(BASE+ex['url']).content
  assert requests.get(BASE+ex['url'],headers={'Range':'bytes=0-1023'}).status_code==206
  assert requests.get(BASE+ex['captions_url']).text==continuous_srt()
  assert ex['inspection_only'] and ex['audio']
  checks.append('Downloaded MP4 matches server bytes; range playback, frozen exact SRT and inspection-only export metadata pass')
  r=requests.post(url+'/render',json={'resolution':'480p','draft':False,'allow_inspection':True})
  assert r.status_code==400
  p=requests.get(url).json();assert not any(p['review'].values()) and not p['episode']['reviews']
  checks.append('Final export is rejected and no factual, rights, picture, cue or transcript approval was fabricated')
  page.screenshot(path=str(WORK/'rendered-desktop.png'),full_page=True)
  cleanup=page.locator('.session-cleanup');cleanup.locator('summary').click()
  expect(page.get_by_role('button',name='Clear this temporary session',exact=True)).to_be_disabled()
  checks.append('Temporary-session deletion remains disabled until the user explicitly confirms their downloads are saved')
  page.set_viewport_size({'width':390,'height':844})
  page.reload(wait_until='networkidle')
  expect(page.get_by_role('button',name='Save project backup',exact=True)).to_be_visible()
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
  page.screenshot(path=str(WORK/'setup-mobile.png'),full_page=True)
  page.get_by_role('button',name='View timeline',exact=True).click()
  expect(page.locator('.film-inspection-mark')).to_be_visible()
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
  checks.append('390 px mobile: backup remains reachable and setup/timeline have no horizontal overflow')
  assert not errors,errors
  browser.close()
 success=True
 report={'project_id':pid,'title':'Inspection workflow demo — SYNTHETIC MEDIA','version':'0.3.4','checks':checks,'count':len(checks),'browser_errors':errors,'proof_video':'/home/user/Casefile-Studio-Inspection-Proof.mp4','source_downloads':0,'paid_provider_calls':0,'actual_case_media':'None; generated technical tone, moving test pattern and labeled color image only.'}
 (ROOT/'qa/inspection-browser-results.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
finally:
 if pid and not success:
  r=requests.request('DELETE',BASE+'/api/projects/'+pid+'/session',json={'confirm_download_saved':True})
  print('Failed QA-only project cleanup:',pid,r.status_code)
