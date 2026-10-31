from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'episode.py';s=p.read_text();needle='''    if not asset or asset.get("kind") not in ("image", "video"):
        return result''';assert needle in s;s=s.replace(needle,needle+'''
    if asset.get("available_on_server") is False:
        result["status"] = "The uploaded copy is unavailable on this server. A linked name is not file bytes; choose the original again."
        return result''',1);p.write_text(s)
p=ROOT/'app.py';s=p.read_text();assert '/episode/first-draft' not in s
at=s.index('@app.post("/api/projects/{id}/episode/build")')
s=s[:at]+'''@app.post("/api/projects/{id}/episode/first-draft")
def first_draft(id: str):
    """One explicit inspection action: available files -> match -> build -> preview.

    Never records rights/context approval, invents missing footage, or requires
    final-publication sign-offs merely to see the selected source.
    """
    with LOCK:
        p = project_or_404(id)
        if p.get("is_demo"):
            raise HTTPException(422, "Start your own project rather than replacing the fictional sample.")
        e = episode.state(p)
        if not e.get("script") or not e.get("guide"):
            raise HTTPException(422, "Add your narration script and editing guide first. They are separate inputs.")
        available = set()
        for asset in p.get("assets", []):
            try:
                path = (ROOT / asset.get("path", "")).resolve()
                exists = bool(asset.get("path")) and path.is_relative_to(ROOT) and path.is_file()
            except (ValueError, OSError):
                exists = False
            asset["available_on_server"] = exists
            if exists:
                available.add(asset["id"])
        options_project = {**p, "assets": [a for a in p["assets"] if a["id"] in available]}
        for sid, aid in episode.suggestions(options_project).items():
            bound = episode.state(p).get("bindings", {}).get(sid, {}).get("asset_id")
            if bound not in available:
                episode.bind_source(p, sid, {"asset_id": aid})
        report = episode.analyze(p)
        if report["errors"]:
            raise HTTPException(422, " ".join(report["errors"]))
        if not report["inspection_cues"]:
            visuals = [a for a in p["assets"] if a["kind"] in ("image", "video")]
            if visuals and not any(a["id"] in available for a in visuals):
                raise HTTPException(422, "The source names are saved, but their uploaded copies are not available on this server. Your computer originals were not deleted. Add one original source photo/video to verify the preview; checking approvals cannot restore missing bytes.")
            if not visuals:
                raise HTTPException(422, "Add at least one source photo or video first. We will not call an all-placeholder timeline a visual draft.")
            raise HTTPException(422, "Files are present, but no guide placement can use them yet. Match a filename to its source ID or check the source-choice/range explanation in More settings. No approval checkboxes are needed for inspection.")
        plan = e.get("plan") or {}
        used_missing = any(s.get("asset_id") and s["asset_id"] not in available for s in p.get("scenes", []))
        reused = report["plan_current"] and plan.get("mode") == "inspection" and not used_missing and any(s.get("asset_id") for s in p.get("scenes", []))
        if not reused:
            checkpoint(p)
            try:
                episode.build(p, allow_placeholders=True, inspection=True)
            except (ValueError, TypeError, KeyError) as error:
                raise HTTPException(422, str(error))
        start = 0.0
        first = None
        for scene in p["scenes"]:
            if scene.get("asset_id"):
                first = {"scene_id": scene["id"], "time": start + min(1 / renderer.FPS, scene["duration"] / 2)}
                break
            start += scene["duration"]
        if first is None:
            raise HTTPException(422, "No real visual was produced. Check a linked file and its permitted range; the empty plan was not saved as a successful draft.")
        result = episode_result(p)
        result["preview"] = first
        result["reused_current_plan"] = bool(reused)
        return result


'''+s[at:];s=s.replace('version="0.3.6"','version="0.4.0"',1);p.write_text(s)

p=ROOT/'web/src/EpisodeSetup.jsx';s=p.read_text();assert 'SimpleDraft' not in s
s=s.replace('''import "./episode.css";''','''import "./episode.css";
import SimpleDraft from "./SimpleDraft.jsx";''',1)
s=s.replace('''  onRender,
  onNew,''','''  onRender,
  onNew,
  onQuickDraft,
  backupStatus,''',1)
s=s.replace('''    [transfer, setTransfer] = useState(null);''','''    [transfer, setTransfer] = useState(null),
    [advancedOpen, setAdvancedOpen] = useState(false);''',1)
s=s.replace('''  async function media(role, files) {''','''  async function media(role, files, autoPreview = false) {''',1)
# Only quick-file picks auto-open preview; detailed/power-user controls stay stable.
start=s.index('  async function media(');end=s.index('\n  function listen(',start);chunk=s[start:end]
chunk=chunk.replace('''    await action(''','''    const uploaded = await action(''',1)
chunk=chunk.replace('''    );
  }''','''    );
    if (autoPreview && uploaded && ready && onQuickDraft) {
      const candidate = uploaded.analysis || (await api(`/api/projects/${project.id}/episode`));
      if (candidate.inspection_cues > 0) await onQuickDraft({render: false});
    }
  }''',1)
s=s[:start]+chunk+s[end:]
# Replace the hero's non-obvious scroll buttons with a simple informational badge.
a=s.index('        <div className="ep-hero-actions">');b=s.index('      <div className="ep-flow">',a)
s=s[:a]+'''        <div className="ep-local"><CheckCircle2 size={13} /> No AI key needed to preview your files</div>
      </div>
'''+s[b:]
s=s.replace('''          <b>01</b> Add your audio & documents''','''          <b>01</b> Add files''',1).replace('''          <b>02</b> Link the real source files''','''          <b>02</b> Preview your draft''',1).replace('''          <b>03</b> Review cues & make a draft''','''          <b>03</b> Download when ready''',1)
needle='''      {project.is_demo && (''';assert needle in s
s=s.replace(needle,'''      <SimpleDraft project={project} busy={disabled} onMedia={media} onImport={importDocument} onPreview={onQuickDraft} onOptions={(captions) => save("/episode/options", "PATCH", {captions})} progress={!advancedOpen ? transfer : null} backupStatus={backupStatus}/>
      <button className="advanced-setup-toggle" aria-label="More settings" aria-expanded={advancedOpen} onClick={() => setAdvancedOpen(!advancedOpen)}><ChevronDown size={14} /> {advancedOpen ? "Hide detailed settings" : "More settings: documents, source choices and final checks"}</button>
      <div className="detailed-episode-settings" hidden={!advancedOpen}>
'''+needle,1)
s=s.replace('''      </footer>
    </main>''','''      </footer>
      </div>
    </main>''',1);s=s.replace('v0.3.6','v0.4.0');p.write_text(s)

p=ROOT/'web/src/main.jsx';s=p.read_text();assert 'rememberSetup' not in s
s=s.replace('''import EpisodeSetup from "./EpisodeSetup.jsx";''','''import EpisodeSetup from "./EpisodeSetup.jsx";
import { rememberSetup, cachedSetups, forgetSetup } from "./SessionBackup.js";''',1)
s=s.replace('''    [savedBeforeClear, setSavedBeforeClear] = useState(false),''','''    [savedBeforeClear, setSavedBeforeClear] = useState(false),
    [backupStatus, setBackupStatus] = useState("pending"),
    [recoveredSetup, setRecoveredSetup] = useState(null),''',1)
# Cache setup automatically, never replacing a newer cached setup with an older server copy.
needle='''  useEffect(() => {
    if (!project?.id) return;
    initialPoll.current = true;''';assert needle in s
s=s.replace(needle,'''  useEffect(() => {
    if (!project?.id) return;
    const timer = setTimeout(() => rememberSetup(project).then(setBackupStatus).catch(() => setBackupStatus("unavailable")), 350);
    return () => clearTimeout(timer);
  }, [project]);

'''+needle,1)
s=s.replace('''        const b = await api("/api/bootstrap");
        setProjectList''','''        const saved = await cachedSetups().catch(() => []);
        const b = await api("/api/bootstrap");
        setProjectList''',1)
s=s.replace('''          const p = await api("/api/projects/" + id);
          acceptProject(p);''','''          const p = await api("/api/projects/" + id);
          const cached = saved.find((entry) => entry.id === last) || saved.find((entry) => entry.id === id);
          if (cached && (cached.id !== p.id || (cached.project.updated_at || "") > (p.updated_at || ""))) setRecoveredSetup(cached);
          acceptProject(p);''',1)
# On an API outage, expose a cached setup download, never pretend its media is recovered.
needle='''      } catch (e) {
        report(e);
      }
    })();''';assert needle in s
s=s.replace(needle,'''      } catch (e) {
        const saved = await cachedSetups().catch(() => []);
        if (saved[0]) setRecoveredSetup(saved[0]);
        report(e);
      }
    })();''',1)
# One root callback uses the NEW response project, not the stale render closure.
at=s.index('  async function startRender(options) {')
s=s[:at]+'''  async function makeFirstDraft({render = false, resolution = "480p"} = {}) {
    if (locked || !project) return;
    setBusy(true); setPlaying(false);
    try {
      await flushSave();
      const response = await api(`/api/projects/${project.id}/episode/first-draft`, "POST", {});
      const p = response.project;
      pending.current = {}; acceptProject(p);
      setSelectedId(response.preview.scene_id); setTime(response.preview.time);
      setTab("edit");
      if (!render) notify("Your preview is ready. The timeline now uses your available source files; no final approvals were inferred.");
      if (render) {
        const track = p.assets.find((a) => a.id === p.narration_id && a.available_on_server !== false);
        if (!track) throw new Error("Picture preview is ready. Add the matching narration recording to make a video with sound.");
        const job = await api(`/api/projects/${p.id}/render`, "POST", {resolution, draft: true, captions: p.captions, allow_guided_gaps: true, allow_inspection: true});
        watched.current.add(job.job_id); setJobs(await api(`/api/projects/${p.id}/jobs`));
        setTab("review"); setModal(null);
        notify("Making your inspection video. It includes clearly marked gaps where sources are missing.", "info");
      }
    } catch (error) { report(error); }
    finally { setBusy(false); }
  }

'''+s[at:]
# Make the existing Edit tab fix the stale/all-gap plan rather than show it again.
needle='''              onClick={() => {
                setTab(key);''';assert needle in s
s=s.replace(needle,'''              onClick={() => {
                if (key === "edit" && project.episode?.guide && (!project.scenes.some((s) => s.asset_id) || project.episode.plan?.mode === "inspection")) { makeFirstDraft(); return; }
                setTab(key);''',1)
# Header download for guided projects is an explicit inspection action; old exports remain advanced.
s=s.replace('''              onClick={() => openTool("export", "review")}
            >
              Export video''','''              onClick={() => project.episode?.guide ? makeFirstDraft({render: true}) : openTool("export", "review")}
            >
              {project.episode?.guide ? "Download draft" : "Export video"}''',1)
s=s.replace('''            onRender={startRender}
            onNew={''','''            onRender={startRender}
            onQuickDraft={makeFirstDraft}
            backupStatus={backupStatus}
            onNew={''',1)
# Show browser recovery and a simple download even when bootstrap/API is unavailable.
s=s.replace('''        <p>{toast?.message || "Opening your documentary workspace…"}</p>''','''        <p>{toast?.message || "Opening your documentary workspace…"}</p>
        {recoveredSetup && <div className="recovery-notice"><b>A setup backup is saved in this browser</b><p>{recoveredSetup.project.title} · {recoveredSetup.project.assets?.length || 0} media references. Media bytes are not included.</p><button className="btn primary" aria-label="Download recovered setup" onClick={() => downloadProjectSnapshot(recoveredSetup.project)}>Download saved project setup</button></div>}''',1)
s=s.replace('''        {uploadProgress && (''','''        {recoveredSetup && <div className="recovery-notice"><b>A newer saved setup was found in this browser.</b><p>{recoveredSetup.project.title} · {recoveredSetup.project.assets?.length || 0} media references. Download this before continuing with an older server copy; media files are not inside this JSON.</p><button className="btn" aria-label="Download recovered setup" onClick={() => downloadProjectSnapshot(recoveredSetup.project)}>Save recovered setup</button><button className="btn" onClick={() => setRecoveredSetup(null)}>Dismiss</button></div>}
        {uploadProgress && (''',1)
# Publication checks are secondary in review; the actual MP4 remains directly below.
s=s.replace('''                <div className="eyebrow">04 / THE FINAL CUT</div>
                <h2>A final check. Then, the world.</h2>''','''                <div className="eyebrow">{project.episode?.guide ? "YOUR DRAFT VIDEO" : "04 / THE FINAL CUT"}</div>
                <h2>{project.episode?.guide ? "Watch it. Save it. Then finish." : "A final check. Then, the world."}</h2>''',1)
s=s.replace('''                  onClick={() => openTool("export")}
                >
                  Render video''','''                  onClick={() => project.episode?.guide ? makeFirstDraft({render: true}) : openTool("export")}
                >
                  {project.episode?.guide ? "Make updated draft video" : "Render video"}''',1)
s=s.replace('''            <div className="review-grid">''','''            <details className="advanced-publication" open={!project.episode?.guide}><summary>Advanced: final publication checks and session cleanup</summary>
            <div className="review-grid">''',1)
s=s.replace('''            <section className="content-card exports-card">''','''            </details>
            <section className="content-card exports-card">''',1)
s=s.replace('''                          pending.current = {};
                          window.location.reload();''','''                          pending.current = {};
                          await forgetSetup(project.id).catch(() => {});
                          window.location.reload();''',1)
s=s.replace('v0.3.6','v0.4.0');p.write_text(s)
for name in ['package.json','package-lock.json']:
 p=ROOT/name;d=json.loads(p.read_text());d['version']='0.4.0'
 if name=='package-lock.json':d['packages']['']['version']='0.4.0'
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'web/index.html';p.write_text(p.read_text().replace('v=0.3.6','v=0.4.0'))
print('One-action inspection workflow and automatic browser setup backup implemented. Existing projects were not imported/rebuilt.')
