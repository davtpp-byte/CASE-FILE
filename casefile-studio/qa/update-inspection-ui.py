from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'web/src/EpisodeSetup.jsx';s=p.read_text();assert 'Guide planning mode' not in s
s=s.replace('''    [resolution, setResolution] = useState("720p");''','''    [resolution, setResolution] = useState("720p"),
    [planningMode, setPlanningMode] = useState("inspection");''',1)
s=s.replace('''  const row = useRef(null);
  useEffect(() => {''','''  const row = useRef(null);
  const [previewError, setPreviewError] = useState(false);
  useEffect(() => setPreviewError(false), [file?.id]);
  useEffect(() => {''',1)
s=s.replace('''      {expanded && (
        <div className="ep-source-detail">''','''      {file && !expanded && <button className="ep-preview-source" aria-label={`Preview source ${source.id}`} onClick={onExpand}>
        <Play size={12} /> Preview uploaded {file.kind} · no sign-off required
      </button>}
      {expanded && (
        <div className="ep-source-detail">''',1)
s=s.replace('''              {file.kind === "video" ? (
                <video''','''              <p className="ep-preview-note">SOURCE INSPECTION · viewing this file does not approve its identity, context or reuse.</p>
              {file.kind === "video" ? (
                <video''',1)
s=s.replace('''                  src={file.url}
                  controls''','''                  src={file.url}
                  onError={() => setPreviewError(true)}
                  controls''',1)
s=s.replace('''                  src={file.url}
                  alt={`Uploaded file linked by producer to ${source.id}`}''','''                  src={file.url}
                  onError={() => setPreviewError(true)}
                  alt={`Uploaded file linked by producer to ${source.id}`}''',1)
s=s.replace('''              <label className="field">
                Permission / license''','''              {previewError && <p className="ep-inline-warning" role="alert">This file cannot be loaded from the current server or decoded by this browser. Keep your original; save a project backup before refreshing. Missing file bytes and unsupported formats need repair, not false approval checkmarks.</p>}
              <label className="field">
                Permission / license''',1)
s=s.replace('''            {cue.ready ? "Producer-reviewed source window" : cue.status_detail}''','''            {cue.ready ? "Producer-reviewed source window" : cue.inspection_ready ? "Available in inspection mode · not approved" : cue.status_detail}''',1)
s=s.replace('''        return result;
      },
      role === "narration_id"''','''        if (guide) return api(`/api/projects/${project.id}/episode/autolink`, "POST", {});
        return result;
      },
      role === "narration_id"''',1)
s=s.replace('''          : "Source files imported. Match filenames or link them below.",''','''          : "Files imported; unique source-ID filenames linked automatically. Preview them below; no approvals were inferred.",''',1)
s=s.replace('''  const plan = e.plan;
  const ready =''','''  const plan = e.plan;
  const inspection = planningMode === "inspection";
  const modeMatches = !!plan && (plan.mode || "reviewed") === planningMode;
  const ready =''',1)
s=s.replace('''      <div className="ep-boundaries">''','''      {report && report.linked_source_count > 0 && <div className="ep-inspection-help" role="note">
        <Play size={18} /><div><b>{report.linked_source_count} source files linked · {report.inspection_cues} placements inspectable · {report.ready_cues} placements approved</b>
        <p>Preview any linked file below without signing it off. Build an inspection draft to see unreviewed candidates on the timeline. Images use their source link; videos use valid local/guide windows or a clearly disclosed opening sample. Known prohibited chapters and required stop times stay blocked. Rights, identity and Care are never auto-approved.</p></div>
      </div>}
      <div className="ep-boundaries">''',1)
s=s.replace('''          <h3>A plan first. A real MP4 when your audio is ready.</h3>''','''          <h3>See the edit first. Clear publication separately.</h3>''',1)
s=s.replace('''          <label className="ep-checkbox">
            <input
              type="checkbox"
              aria-label="Allow marked visual gaps"''','''          <label className="field ep-mode-field">Planning mode
            <select aria-label="Guide planning mode" value={planningMode} onChange={(ev) => setPlanningMode(ev.target.value)} disabled={disabled}>
              <option value="inspection">Inspection draft · unreviewed linked media</option>
              <option value="reviewed">Reviewed plan · approved placements only</option>
            </select>
          </label>
          <p className="ep-mode-explanation">{inspection ? "Internal inspection only. Candidate footage is visibly marked UNREVIEWED and cannot be exported as a final video. Source sound stays muted; short windows do not loop." : "Only genuinely reviewed source windows appear. Anything missing approval remains a marked gap; final release still requires all real editorial checks."}</p>
          <label className="ep-checkbox">
            <input
              type="checkbox"
              aria-label="Allow marked visual gaps"''',1)
s=s.replace('''                    allow_placeholders: true,
                  }),''','''                    allow_placeholders: true,
                    inspection,
                  }),''',1)
s=s.replace('''                "Guide-based timeline built. Your original audio stays unchanged.",''','''                inspection ? "Unreviewed inspection timeline built. Your voice is unchanged; no rights or Care approvals were inferred." : "Reviewed guide timeline built. Your original audio stays unchanged.",''',1)
s=s.replace('''            {plan ? "Rebuild episode plan" : "Preview episode plan"}''','''            {inspection ? "Build / rebuild inspection draft" : plan ? "Rebuild reviewed plan" : "Build reviewed plan"}''',1)
s=s.replace('''              !report?.plan_current ||
              (!gaps && plan?.gap_seconds > 0)''','''              !report?.plan_current ||
              !modeMatches ||
              (!gaps && plan?.gap_seconds > 0)''',1)
s=s.replace('''                allow_guided_gaps: gaps,
              })''','''                allow_guided_gaps: gaps,
                allow_inspection: inspection,
              })''',1)
s=s.replace('''            Create review video <ArrowRight size={13} />''','''            {inspection ? "Render inspection MP4" : "Create review video"} <ArrowRight size={13} />''',1)
s=s.replace('''        </div>
      </div>
      <footer className="ep-footer">''','''          <p className="ep-render-reason" role="status">{!voice ? "Add the matching narration to render; a plan can be inspected now." : !report?.plan_current || !modeMatches ? "Build / rebuild in the selected mode before rendering." : !gaps && plan?.gap_seconds > 0 ? `${tc(plan.gap_seconds)} of marked gaps remain. Allow those cards for an internal preview, or supply more coverage.` : "Ready for an internal draft. Publication checks do not block source inspection."}</p>
        </div>
      </div>
      <footer className="ep-footer">''',1)
s=s.replace('''            {plan.scene_count} scenes planned ·''','''            {plan.mode === "inspection" ? "UNREVIEWED INSPECTION · " : ""}{plan.scene_count} scenes planned ·''',1)
s=s.replace('v0.3.2','v0.3.3')
p.write_text(s)

p=ROOT/'web/src/main.jsx';s=p.read_text();assert 'function downloadProjectSnapshot(' not in s
at=s.index('const uid = () =>')
s=s[:at]+'''function downloadProjectSnapshot(project) {
  const { undo, ...snapshot } = project;
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a"); link.href = url; link.download = "casefile-project.json";
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

'''+s[at:]
s=s.replace('''    [uploading, setUploading] = useState(false),''','''    [uploading, setUploading] = useState(false),
    [savedBeforeClear, setSavedBeforeClear] = useState(false),''',1)
s=s.replace('''                  <a href={`/api/projects/${project.id}/project.json`} download>''','''                  <a href="#project-backup" onClick={(ev) => { ev.preventDefault(); downloadProjectSnapshot(project); }}>''',1)
s=s.replace('''                  {visual && activeScene?.source_label && (''','''                  {activeScene?.inspection_only && <div className="film-inspection-mark">UNREVIEWED INSPECTION · NOT FOR PUBLICATION</div>}
                  {visual && activeScene?.source_label && (''',1)
# A backup is available while editing, even if the server is offline or rendering.
s=s.replace('''          <div className="header-actions">''','''          <div className="header-actions">
            <button className="btn backup-project-btn" aria-label="Save project backup" onClick={() => downloadProjectSnapshot(project)}><FileJson size={14} /> Save backup</button>''',1)
# If the exact header name changed, place a backup alongside the episode setup button.
if 'aria-label="Save project backup"' not in s:
 needle='''              <div className="review-downloads">'''
 assert needle in s
 s=s.replace(needle,'''              <div className="review-downloads">
                <a href="#project-backup" aria-label="Save project backup" onClick={(ev) => { ev.preventDefault(); downloadProjectSnapshot(project); }}>Save project backup (no server needed)</a>''',1)
s=s.replace('''              <div className="review-downloads">''','''              {!project.is_demo && <details className="session-cleanup">
                <summary>Clear temporary session after saving your downloads</summary>
                <p>This removes this project's uploaded copies, jobs, rendered files and project record from this server. It does not delete originals on your computer. A download click alone is not proof that a file was saved.</p>
                <label className="ep-checkbox"><input type="checkbox" aria-label="I saved my output before clearing" checked={savedBeforeClear} onChange={(ev) => setSavedBeforeClear(ev.target.checked)} /><span>I have saved and checked the output/backups I need on my computer.</span></label>
                <button className="btn" aria-label="Clear this temporary session" disabled={locked || !savedBeforeClear} onClick={async () => {
                  setBusy(true);
                  try { await flushSave(); await api(`/api/projects/${project.id}/session`, "DELETE", {confirm_download_saved: true}); pending.current = {}; window.location.reload(); }
                  catch (error) { report(error); setBusy(false); }
                }}><Trash2 size={13} /> Clear this session's uploaded copies and exports</button>
              </details>}
              <div className="review-downloads">''',1)
s=s.replace('''  const allReviewed = Object.values(project.review).every(Boolean);''','''  const allReviewed = Object.values(project.review).every(Boolean);
  const inspectionPlan = project.episode?.plan?.mode === "inspection";''',1)
s=s.replace('''        {!draft && !allReviewed && (''','''        {inspectionPlan && <div className="notice warning"><AlertTriangle size={16} /><span><b>Unreviewed inspection only.</b> This rendering is visibly marked and cannot be a final export. Complete real source reviews and rebuild a reviewed plan before publication.</span></div>}
        {!draft && !allReviewed && (''',1)
s=s.replace('''            (!draft && (!allReviewed || !preflight?.ready_for_final))''','''            (!draft && (inspectionPlan || !allReviewed || !preflight?.ready_for_final))''',1)
s=s.replace('''              allow_guided_gaps: allowGuideGaps,
            })''','''              allow_guided_gaps: allowGuideGaps,
              allow_inspection: inspectionPlan && draft,
            })''',1)
s=s.replace('v0.3.2','v0.3.3')
p.write_text(s)
p=ROOT/'web/src/ProductionTools.jsx';s=p.read_text().replace('''{report.coverage.scenes_with_references}''','''{report.coverage.scenes_with_visuals ?? 0}''',1).replace('''<span>Scenes linked to sources</span>''','''<span>Scenes with visuals · not factual sign-off</span>''',1);p.write_text(s)
p=ROOT/'web/index.html';p.write_text(p.read_text().replace('v=0.3.2','v=0.3.3'))
for filename in ['package.json','package-lock.json']:
 p=ROOT/filename;d=json.loads(p.read_text());d['version']='0.3.3'
 if filename=='package-lock.json':d['packages']['']['version']='0.3.3'
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'web/src/episode.css';p.write_text(p.read_text()+'''
.ep-preview-source { width: 100%; display: flex; align-items: center; gap: 7px; border: 0; border-top: 1px solid #34332d; background: #29261e66; color: #d1b17b; font-size: 10px; padding: 10px 13px; text-align: left; cursor: pointer; }
.ep-preview-source:hover { background: #3b322344; }
.ep-preview-note { color: #c5ac83; font-size: 10px; line-height: 1.7; border-left: 2px solid #9b7947; padding-left: 8px; }
.ep-inspection-help { display: flex; gap: 13px; padding: 18px 20px; margin: 18px 0; border: 1px solid #5b4930; border-radius: 8px; background: #30271b44; color: #d4b47d; }
.ep-inspection-help > svg { flex-shrink: 0; margin-top: 2px; }
.ep-inspection-help b { font-size: 12px; font-weight: 550; }
.ep-inspection-help p { font-size: 11px; line-height: 1.85; color: #aba390; margin-top: 7px; }
.ep-mode-field { margin-top: 15px; max-width: 460px; }
.ep-mode-explanation, .ep-render-reason { color: #b7a381; font-size: 11px; line-height: 1.8; margin-top: 10px !important; }
.film-inspection-mark { position: absolute; z-index: 5; top: 0; left: 0; right: 0; background: #241b0df2; color: #ecc57f; padding: 8px 10px; text-align: center; font-size: 10px; letter-spacing: .6px; pointer-events: none; }
.session-cleanup { border: 1px solid #504034; border-radius: 7px; padding: 14px; margin: 16px 0; font-size: 11px; }
.session-cleanup summary { cursor: pointer; color: #cdb087; }
.session-cleanup p { color: #aaa398; line-height: 1.8; margin: 12px 0; }
.session-cleanup > .btn { margin-top: 12px; }
''')
print('Inspection UI, client-only project backup, and cleanup controls prepared.')
