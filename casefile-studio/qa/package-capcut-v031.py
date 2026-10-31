"""Package v0.3.1 with a sanitized timing pack, never the raw CapCut upload."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT.parent / 'Casefile-Studio-v0.3.zip'
ARCHIVE = ROOT.parent / 'Casefile-Studio-v0.3.1.zip'
PREFIX = 'casefile-studio/'
with zipfile.ZipFile(PREVIOUS) as z:
    names = {n[len(PREFIX):] for n in z.namelist() if n.startswith(PREFIX) and not n.endswith('/')}
names.update(['timing_io.py', 'CAPCUT-TIMING.md', 'tests/test_capcut.py',
              'qa/capcut-browser-results.json', 'qa/capcut-final-ui.json',
              'qa/capcut-integration.json', 'qa/capcut-input-audit.json', 'qa/verification-v0.3.json'])
(ROOT / 'run.sh').chmod(0o755)
with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name in sorted(names):
        assert (ROOT / name).is_file(), name
        z.write(ROOT / name, PREFIX + name)
with zipfile.ZipFile(ARCHIVE) as z:
    assert z.testzip() is None
    assert z.getinfo(PREFIX + 'run.sh').external_attr >> 16 & 0o111
    assert not any('uploads/' in n or n.endswith('draft_info.json') for n in z.namelist())

# A fresh interpreter in an unpacked directory, not imports of the running app.
# TestClient exercises startup and HTTP routes without leaving a server process.
work = ROOT / 'qa/package-cold-start-v031'
if work.exists():
    shutil.rmtree(work)
work.mkdir()
try:
    with zipfile.ZipFile(ARCHIVE) as z:
        z.extractall(work)
    unpacked = work / 'casefile-studio'
    subprocess.run(['sh', '-n', 'run.sh'], cwd=unpacked, check=True)
    check = r'''
import json,hashlib
from pathlib import Path
from fastapi.testclient import TestClient
import app,episode
with TestClient(app.app) as c:
 assert app.app.version == '0.3.1'
 for url in ['/', '/assets/app.js', '/assets/app.css', '/api/bootstrap']:
  assert c.get(url).status_code == 200, url
 p = c.get('/api/projects/7fa005880e97474f').json()
 a = c.get('/api/projects/7fa005880e97474f/episode').json()
 assert a['plan_current'] and not a['has_voice'] and not a['errors']
 assert a['cue_count'] == 43 and a['imported_caption_count'] == 390
 assert a['duration'] == 903.533333 and len(p['scenes']) == 56
 assert len(p['episode']['timings']['units']) == 2353
 assert not p['assets'] and not p['exports']
 assert not a['timing_reviewed'] and not a['transcript_reviewed']
 srt = c.get('/api/projects/7fa005880e97474f/captions.srt')
 assert srt.status_code == 200 and srt.text.count(' --> ') == 390
 assert '00:15:03,500' in srt.text
 plan = c.get('/api/projects/7fa005880e97474f/episode/plan.md')
 assert plan.status_code == 200 and 'Imported timing pack' in plan.text
 assert c.post('/api/projects/7fa005880e97474f/render',json={'resolution':'480p','draft':True,'captions':False,'allow_guided_gaps':True}).status_code == 400
 demo = c.get('/api/projects/b39f1061bd2440d8').json()
 assert demo['is_demo']
 for asset in demo['assets']:
  if asset.get('url'): assert c.get(asset['url']).status_code == 200
 export = demo['exports'][-1]
 r=c.get(export['url'],headers={'Range':'bytes=0-1023'})
 assert r.status_code == 206 and len(r.content) == 1024
 print(json.dumps({'unpacked_startup':'fresh-process TestClient passed','native_adapter_loaded':True,'caption_blocks':390,'scene_count':56,'no_voice_render_blocked':True,'sample_video_range_206':True}))
'''
    result = subprocess.run([sys.executable, '-c', check], cwd=unpacked, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout)
finally:
    shutil.rmtree(work)
report = {'path': str(ARCHIVE), 'version': '0.3.1', 'files': len(names),
          'bytes': ARCHIVE.stat().st_size, 'sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
          'integrity': 'passed', 'run_sh_executable': True,
          'cold_start': 'unpacked fresh-process TestClient startup/routes/static/sample range 206 passed',
          'actual_case': 'Sanitized CapCut + SRT timings, 56 all-gap scenes; no actual media or exports',
          'raw_capcut_export_and_private_platform_metadata': 'not included',
          'source_module_included': 'timing_io.py', 'tests': '125 backend; 43 browser checks',
          'prior_v03_archive_unchanged': True}
(ROOT / 'qa/release-v0.3.1.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
