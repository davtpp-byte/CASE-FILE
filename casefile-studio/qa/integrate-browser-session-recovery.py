from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
p=R/'web/src/main.jsx';s=p.read_text();assert 'restoreWorkingSession' not in s
s=s.replace('''import { rememberSetup, cachedSetups, forgetSetup } from "./SessionBackup.js";''','''import { rememberSetup, cachedSetups, forgetSetup } from "./SessionBackup.js";
import { keepWorkingFiles, clearWorkingFiles, workingFiles, restoreWorkingSession } from "./MediaSession.js";''',1)
s=s.replace('''        const saved = await cachedSetups().catch(() => []);
        const b = await api("/api/bootstrap");''','''        const saved = await cachedSetups().catch(() => []);
        api("/api/browser-session", "POST", {origin: window.location.origin, version: "0.4.2", snapshot: saved[0]?.project || null}).catch(() => {});
        const b = await api("/api/bootstrap");''',1)
s=s.replace('''          const p = await api("/api/projects/" + id);
          const cached =''','''          let p = await api("/api/projects/" + id);
          const cached =''',1)
a=s.index('''          if (
            cached &&
            (cached.id !== p.id''');b=s.index('''          acceptProject(p);''',a)
s=s[:a]+'''          if (cached) {
            const files=await workingFiles(cached.id).catch(()=>[]);
            if (cached.id !== p.id || (cached.project.updated_at||"") > (p.updated_at||"") || files.length) {
              const recovered=await restoreWorkingSession(cached.project,api,(progress)=>setUploadProgress(progress)).catch(()=>null);
              if (recovered && !recovered.missing) p=recovered.project;
              else if (cached.id !== p.id || (cached.project.updated_at||"") > (p.updated_at||"")) setRecoveredSetup(cached);
            }
          }
'''+s[b:]
# Mirror the live browser setup for actual diagnosis, without requiring downloads/copying.
s=s.replace('''rememberSetup(project)
          .then(setBackupStatus)''','''rememberSetup(project)
          .then((status) => { setBackupStatus(status); if(status!=="newer-saved-copy") api("/api/browser-session","POST",{origin:window.location.origin,version:"0.4.2",snapshot:project}).catch(()=>{}); })''',1)
# All accepted generic media are also protected in the local working-file cache.
s=s.replace('''      acceptProject(p);
      if ([...files].some''','''      await keepWorkingFiles(project.id,[...files].filter((file)=>!/\\.(md|txt|json|srt)$/i.test(file.name)),"auto").catch(()=>notify("Browser could not keep a local working-file recovery copy. Keep your originals.","info"));
      acceptProject(p);
      if ([...files].some''',1)
needle='''      const response = await api(
        `/api/projects/${project.id}/episode/first-draft`,''';assert needle in s
s=s.replace(needle,'''      const saved = (await cachedSetups().catch(()=>[])).find((entry)=>entry.id===project.id);
      if (saved && (await workingFiles(project.id).catch(()=>[])).length) {
        const recovered = await restoreWorkingSession(saved.project,api,(progress)=>setUploadProgress(progress));
        if(recovered.restored) notify(`Recovered ${recovered.restored} working file(s) from this browser.`,"info");
      }
      const response = await api(
        `/api/projects/${project.id}/episode/first-draft`,''',1)
# Clear the temporary media cache only after explicit completion confirmation.
s=s.replace('''await forgetSetup(project.id).catch(() => {});''','''await forgetSetup(project.id).catch(() => {});
                            await clearWorkingFiles(project.id).catch(() => {});''')
# Users can restore cached metadata's original files with one normal multi-select.
needle='''            <button
              className="btn"
              onClick={() => setRecoveredSetup(null)}'''
if needle in s:
 s=s.replace(needle,'''            <label className="quick-pick"><input type="file" aria-label="Restore original session files" multiple accept="audio/*,video/*,image/*" onChange={async(ev)=>{
              const files=[...ev.target.files];ev.target.value="";if(!files.length)return;
              setBusy(true);try{await keepWorkingFiles(recoveredSetup.id,files,"auto");const result=await restoreWorkingSession(recoveredSetup.project,api,(p)=>setUploadProgress(p));acceptProject(result.project);setRecoveredSetup(result.missing?recoveredSetup:null);notify(result.missing?`${result.missing} original file(s) are still needed.`:"Working files restored; preview is ready.","info");}catch(error){report(error);}finally{setBusy(false);}
            }}/>Restore original files</label>
'''+needle,1)
s=s.replace('v0.4.1','v0.4.2').replace('version: "0.4.1"','version: "0.4.2"');p.write_text(s)
p=R/'web/src/EpisodeSetup.jsx';s=p.read_text();s=s.replace('''import SimpleDraft from "./SimpleDraft.jsx";''','''import SimpleDraft from "./SimpleDraft.jsx";
import { keepWorkingFiles } from "./MediaSession.js";''',1)
a=s.index('''  async function importDocument(role, files) {''');b=s.index('''  async function media(''',a)
s=s[:a]+'''  async function importDocument(role, files) {
    const file=files[0];
    await action(async()=>{
      const response=await api(`/api/projects/${project.id}/episode/import`,"POST",{role,text:await file.text(),filename:file.name});
      await keepWorkingFiles(project.id,[file],role).catch(()=>onNotify("Browser recovery cache is unavailable; keep the original inputs."));
      return response;
    },`${role === "guide" ? "Editing guide" : role === "script" ? "Narration script" : "Timing file"} imported separately.`);
  }
'''+s[b:]
needle='''        if (role) {
          const old = new Set(project.assets.map((a) => a.id));''';assert needle in s
s=s.replace(needle,'''        await keepWorkingFiles(project.id,files,role||"sources").catch(()=>onNotify("Browser could not keep a local recovery copy; retain your computer originals."));
'''+needle,1)
s=s.replace('v0.4.1','v0.4.2');p.write_text(s)
p=R/'web/src/SimpleDraft.jsx';s=p.read_text();needle='''      <div className="simple-draft-heading">''';assert needle in s
s=s.replace(needle,'''      {window.top !== window && <div className="embedded-download-warning"><b>This embedded preview blocks file downloads.</b><p>Use the full editor in a normal browser tab for saving. Right-click the link and choose Open Link in New Tab if the preview blocks a normal click.</p><a href={window.location.href} target="_blank" rel="noopener noreferrer">Open full editor</a><input aria-label="Full editor address" readOnly value={window.location.href} onFocus={(ev)=>ev.target.select()}/></div>}
'''+needle,1)
s=s.replace('''        No final-publication sign-offs are needed to preview.''','''        No final-publication sign-offs are needed to preview. Selected originals are temporarily cached in this browser for working-session recovery and cleared when you finish.''',1);p.write_text(s)
p=R/'web/src/episode.css';p.write_text(p.read_text()+'''\n.embedded-download-warning { border:1px solid #8a6838;background:#34291b;border-radius:7px;padding:14px;color:#dfc28e;font-size:12px;line-height:1.7;margin-bottom:20px; }.embedded-download-warning p{color:#bdb29d;font-size:11px;margin:7px 0;}.embedded-download-warning a{display:inline-block;background:#c9a772;color:#1d1a14;font-size:11px;border-radius:5px;padding:9px 12px;font-weight:600;}.embedded-download-warning input{display:block;margin-top:10px;width:100%;box-sizing:border-box;font-size:10px;color:#bdb7a7;background:#1b1d1e;border:1px solid #4c4637;border-radius:4px;padding:8px;}\n''')
p=R/'app.py';p.write_text(p.read_text().replace('version="0.4.1"','version="0.4.2"',1))
p=R/'web/index.html';p.write_text(p.read_text().replace('v=0.4.1','v=0.4.2'))
for name in ['package.json','package-lock.json']:
 p=R/name;v=json.loads(p.read_text());v['version']='0.4.2'
 if name=='package-lock.json':v['packages']['']['version']='0.4.2'
 p.write_text(json.dumps(v,indent=2)+'\n')
print('Browser-local original cache, recover/replay, automatic live-session diagnostics and embedded-save warning integrated.')
