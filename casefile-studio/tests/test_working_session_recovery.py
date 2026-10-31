"""Session repair is scoped, parser-driven and never accepts client media paths."""
from pathlib import Path
import json
import pytest
from PIL import Image
import app as server
import storage
import episode
from test_capcut import imported


def test_recover_empty_reuses_requested_valid_id_without_overwriting_existing(isolated):
    c,_=isolated;id=storage.uid()
    r=c.post(f'/api/projects/{id}/recover-empty',json={'title':'Recovered synthetic','mode':'narration','target_minutes':25})
    assert r.status_code==200 and r.json()['id']==id
    again=c.post(f'/api/projects/{id}/recover-empty',json={'title':'Do not overwrite'})
    assert again.status_code==200 and again.json()['title']=='Recovered synthetic'
    assert c.post('/api/projects/not-an-id/recover-empty',json={}).status_code==422


def test_media_status_checks_registered_files_and_rejects_outside_paths(isolated):
    c,root=isolated;p=storage.new_project('Status QA','narration')
    f=root/'photo.jpg';Image.new('RGB',(20,20),'green').save(f)
    p['assets']=[{'id':storage.uid(),'name':'existing.jpg','path':str(f.relative_to(storage.ROOT)),'kind':'image','size':f.stat().st_size}, {'id':storage.uid(),'name':'missing.jpg','path':str((root/'missing.jpg').relative_to(storage.ROOT)),'kind':'image'}, {'id':storage.uid(),'name':'outside','path':'/etc/passwd','kind':'image'}]
    storage.save_project(p);before=storage.get_project(p['id'])
    r=c.get(f'/api/projects/{p["id"]}/media-status');assert r.status_code==200
    assert [a['exists'] for a in r.json()['assets']]==[True,False,False]
    assert all('path' not in a for a in r.json()['assets'])
    assert storage.get_project(p['id'])==before


def test_recovery_checkpoint_preserves_server_copy_before_document_replay(isolated):
    c,_=isolated;p=storage.new_project('Before recovery','narration')
    assert c.post(f'/api/projects/{p["id"]}/recovery-checkpoint',json={}).status_code==200
    files=list((server.DATA/'recovery-backups').glob(p['id']+'-*.json'))
    assert len(files)==1 and json.loads(files[0].read_text())['title']=='Before recovery'


def test_only_already_validated_server_timing_pack_can_be_reused(isolated):
    c,_=isolated;source=imported();storage.save_project(source)
    p=storage.new_project('Timing recovery target','narration');h=source['episode']['timings']['hash']
    r=c.post(f'/api/projects/{p["id"]}/reuse-timings',json={'hash':h});assert r.status_code==200
    assert r.json()['project']['episode']['timings']==source['episode']['timings']
    assert not any(r.json()['project']['review'].values())
    assert c.post(f'/api/projects/{p["id"]}/reuse-timings',json={'hash':'../private'}).status_code==422
    assert c.post(f'/api/projects/{p["id"]}/reuse-timings',json={'hash':'0'*64}).status_code==404


def test_automatic_browser_diagnostic_omits_credentials_paths_and_undo(isolated):
    c,_=isolated;p=storage.new_project('Session report','narration')
    snapshot={**p,'undo':['do not store'],'key':'DO-NOT-STORE','config':{'key':'DO-NOT-STORE'},'assets':[{'id':storage.uid(),'name':'S01.jpg','path':'/private/local/path','kind':'image','url':'/media/source.jpg'}]}
    r=c.post('/api/browser-session',headers={'X-Casefile-Session':'a'*32},json={'origin':'https://preview.example.org/path?token=DO-NOT-STORE','version':'0.4.2','snapshot':snapshot})
    assert r.status_code==200
    f=server.DATA/'browser-sessions'/('a'*32+'.json');record=json.loads(f.read_text())
    assert record['origin']=='https://preview.example.org'
    assert 'DO-NOT-STORE' not in f.read_text() and 'path' not in record['snapshot']['assets'][0]
    assert 'undo' not in record['snapshot'] and 'config' not in record['snapshot']
    assert c.post('/api/browser-session',json=[]).status_code==422


def test_finish_clears_its_recovery_backups_and_diagnostics_not_other_projects(isolated):
    c,_=isolated;p=storage.new_project('Clear own recovery','narration');other=storage.new_project('Keep other','narration')
    for project in [p,other]:
        c.post(f'/api/projects/{project["id"]}/recovery-checkpoint',json={})
    c.post('/api/browser-session',headers={'X-Casefile-Session':'a'*32},json={'origin':'https://one.example','snapshot':p})
    c.post('/api/browser-session',headers={'X-Casefile-Session':'b'*32},json={'origin':'https://two.example','snapshot':other})
    r=c.request('DELETE',f'/api/projects/{p["id"]}/session',json={'confirm_download_saved':True});assert r.status_code==200
    assert not list((server.DATA/'recovery-backups').glob(p['id']+'-*.json'))
    assert list((server.DATA/'recovery-backups').glob(other['id']+'-*.json'))
    assert not (server.DATA/'browser-sessions'/('a'*32+'.json')).exists()
    assert (server.DATA/'browser-sessions'/('b'*32+'.json')).exists()
