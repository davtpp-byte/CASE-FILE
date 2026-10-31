from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'web/src/main.jsx';s=p.read_text();assert 'sendUploadRequest' not in s
s=s.replace('''import EpisodeSetup from "./EpisodeSetup.jsx";''','''import EpisodeSetup from "./EpisodeSetup.jsx";
import { UploadProgress, validateUpload, sendUploadRequest, uploadLimits } from "./Uploads.jsx";''',1)
s=s.replace('''async function api(path, method = "GET", body) {
  const response''','''async function api(path, method = "GET", body, onUploadProgress) {
  if (onUploadProgress) return sendUploadRequest(path, method, body, browserSession, onUploadProgress);
  const response''',1)
s=s.replace('''    [uploading, setUploading] = useState(false),''','''    [uploading, setUploading] = useState(false),
    [uploadProgress, setUploadProgress] = useState(null),''',1)
s=s.replace('''    setUploading(true);
    try {
      await flushSave();
      const form''','''    setUploading(true);
    try {
      validateUpload(files);
      setUploadProgress({phase: "uploading", loaded: 0, total: 0, label: `${files.length} selected file(s)`});
      await flushSave();
      const form''',1)
s=s.replace('''      const p = await api(`/api/projects/${project.id}/upload`, "POST", form);''','''      const p = await api(`/api/projects/${project.id}/upload`, "POST", form,
        (progress) => setUploadProgress((old) => ({...old, ...progress})));''',1)
s=s.replace('''      notify(`${files.length} file${files.length > 1 ? "s" : ""} imported.`);
    } catch (e) {
      report(e);''','''      notify(`${files.length} file${files.length > 1 ? "s" : ""} imported.`);
    } catch (e) {
      setUploadProgress((old) => old ? {...old, phase: "error"} : null);
      report(e);''',1)
s=s.replace('''        {tab === "setup" && (''','''        {uploadProgress && <div className="global-upload-progress"><UploadProgress progress={uploadProgress} /></div>}
        {tab === "setup" && (''',1)
s=s.replace('''            <div className="media-grid"
''','''            <div className="media-grid"
''',1)
s=s.replace('''              {!assets.length && (
                <div''','''              <p className="media-upload-limits">Media limit: {uploadLimits}. TXT/Markdown imports: 1 MB.</p>
              {!assets.length && (
                <div''',1)
s=s.replace('''                    <small>Images, footage, audio, scripts</small>''','''                    <small>Media: 512 MB/file · 30 files/batch</small>''',1)
s=s.replace('''                <div className="checklist-note">''','''                {project.episode?.plan?.mode === "inspection" && <p className="inspection-final-help">These are final-publication sign-offs. You may leave all four unticked while viewing/rendering an inspection draft. They do not import footage or perform editing for you.</p>}
                <div className="checklist-note">''',1)
s=s.replace('v0.3.3','v0.3.4');p.write_text(s)

p=ROOT/'web/src/EpisodeSetup.jsx';s=p.read_text();s=s.replace('''import "./episode.css";''','''import "./episode.css";
import { UploadProgress, validateUpload, uploadLimits } from "./Uploads.jsx";''',1)
s=s.replace('''  className = "",
})''','''  className = "",
  limit = "",
})''',1)
s=s.replace('''  return (
    <label
      className={`ep-file-pick''','''  return (<>
    <label
      className={`ep-file-pick''',1)
s=s.replace('''    </label>
  );
}
function SavedCheck''','''    </label>
    {limit && <small className="upload-limit-hint">{limit}</small>}
  </>);
}
function SavedCheck''',1)
s=s.replace('''    [planningMode, setPlanningMode] = useState("inspection");''','''    [planningMode, setPlanningMode] = useState("inspection"),
    [transfer, setTransfer] = useState(null);''',1)
s=s.replace('''  async function media(role, files) {
    await action(''','''  async function media(role, files) {
    try { validateUpload(files); } catch (error) { onError(error); return; }
    setTransfer({role: role || "sources", label: `${files.length} selected file(s)`, loaded: 0, total: 0, phase: "uploading"});
    await action(''',1)
s=s.replace('''        const result = await api(
          `/api/projects/${project.id}/upload`,
          "POST",
          form,
        );''','''        let result;
        try {
          result = await api(`/api/projects/${project.id}/upload`, "POST", form,
            (progress) => setTransfer((old) => ({...old, ...progress})));
        } catch (error) {
          setTransfer((old) => ({...old, phase: "error"}));
          try { onProject(await api(`/api/projects/${project.id}`)); } catch {}
          throw error;
        }''',1)
# Limits/progress by the actual file pickers, not hidden on a distant page.
s=s.replace('''            label="Upload finished narration"
''','''            label="Upload finished narration"
            limit="512 MB maximum · one narration file at a time"
''',1)
s=s.replace('''          {audioAssets.length > 0 && (''','''          {transfer?.role === "narration_id" && <UploadProgress progress={transfer} />}
          {audioAssets.length > 0 && (''',1)
s=s.replace('''            label="Upload background music"
''','''            label="Upload background music"
            limit="512 MB maximum · one music file at a time"
''',1)
# Music has a second existing-track picker; anchor on its upload button's following content.
needle='''            {music ? "Replace music" : "Choose music file"}
          </FilePick>'''
if needle in s:s=s.replace(needle,needle+'''\n          {transfer?.role === "music_id" && <UploadProgress progress={transfer} />}''',1)
else:
 needle='''          <label className="ep-music-level">'''
 if needle in s:s=s.replace(needle,'''          {transfer?.role === "music_id" && <UploadProgress progress={transfer} />}
'''+needle,1)
s=s.replace('''          <div className="ep-source-tabs">''','''          <p className="upload-limit-hint">Media limit: {uploadLimits}. The limit is per file, not 512 MB for the whole batch.</p>
          {transfer?.role === "sources" && <UploadProgress progress={transfer} />}
          <div className="ep-source-tabs">''',1)
# Show both main and allowed alternative source rows.
s=s.replace('''  const used = new Set(placements.map((c) => c.source_id));''','''  const used = new Set(report?.source_option_ids || placements.map((c) => c.source_id));''',1)
s=s.replace('''            <span>Required source files linked</span>''','''            <span>Main files linked <small>Guide alternatives can cover missing mains.</small></span>''',1)
s=s.replace('''            <span>Placements producer-reviewed</span>''','''            <span>Final placement sign-offs <small>0 is okay for an inspection draft.</small></span>''',1)
s=s.replace('''              Used by guide ({report?.used_source_count || 0})''','''              Used by guide ({report?.source_option_ids?.length || report?.used_source_count || 0})''',1)
# Alternative rules and the actual source-choice control live in each placement.
needle='''        <div className="ep-cue-directive">
          <span>ON-SCREEN LABEL</span>'''
assert needle in s
s=s.replace(needle,'''        {(cue.source_choices?.length > 1 || cue.alternative_instructions) && <div className="ep-alternative-choice">
          <b>Source choice for this placement</b>
          {cue.alternative_instructions && <p><b>Guide's alternative instruction:</b> {cue.alternative_instructions}</p>}
          {cue.source_choices?.length > 1 ? <label className="field">Main or guide-permitted alternative
            <select aria-label={`Source choice ${cue.id}`} value={cue.selection_mode === "alternative" ? `alternative:${cue.source_id}` : cue.selection_mode || "auto"} disabled={disabled} onChange={(ev) => {
              const value=ev.target.value;
              save(`/episode/choice/${cue.id}`, "PATCH", value.startsWith("alternative:") ? {mode: "alternative", source_id: value.split(":")[1]} : {mode: value});
            }}>
              <option value="auto">Automatic · main, otherwise named guide alternative</option>
              <option value="primary">Main · {cue.primary_source_id}</option>
              {cue.source_choices.filter((o) => o.kind === "alternative").map((o) => <option key={o.source_id} value={`alternative:${o.source_id}`}>Alternative · {o.source_id}{o.manual_only ? " · choose only if it fits the guide's rule" : ""}</option>)}
            </select>
          </label> : <p>The guide names a non-file or unclear alternative. Its instruction is retained; no unrelated footage is chosen automatically. Clarify the permitted source or editorial graphic.</p>}
          <p>Selected: <b>{cue.source_id}{cue.using_alternative ? ` instead of ${cue.primary_source_id}` : " (main)"}</b>. {cue.selection_reason}</p>
          {cue.using_alternative && <label className="field">Alternative's own on-screen label
            <input aria-label={`Alternative label ${cue.id}`} key={cue.source_id + cue.label} defaultValue={cue.label} disabled={disabled} onBlur={(ev) => {if (ev.target.value !== cue.label) save(`/episode/choice/${cue.id}`, "PATCH", {label: ev.target.value});}} />
          </label>}
          <small>Changing sources does not change narration timing or grant reuse permission. Do not carry a primary event/date label onto a different alternative shot.</small>
        </div>}
'''+needle,1)
s=s.replace('''            Show captions (timing still needs review)''','''            <span><b>Show captions</b><small>Only shows/hides on-screen text. Imported timing and visual cue positions stay active.</small></span>''',1)
s=s.replace('''              type="checkbox"
              checked={project.captions}''','''              type="checkbox"
              aria-label="Show captions (timing still needs review)"
              checked={project.captions}''',1)
s=s.replace('''          <label className="ep-checkbox">
            <SavedCheck
              type="checkbox"
              aria-label="Narration cue timing reviewed"''','''          <div className="ep-final-review-title"><b>Before final export: your review acknowledgements</b><small>Not needed to view sources or build/render an unreviewed inspection draft. Leave unticked until you have actually checked.</small></div>
          <label className="ep-checkbox">
            <SavedCheck
              type="checkbox"
              aria-label="Narration cue timing reviewed"''',1)
s=s.replace('''            I checked the cue positions against the actual narration''','''            <span><b>I checked visual cue positions against the recording</b><small>This records your listening review. It does not run synchronization or create footage.</small></span>''',1)
s=s.replace('''              I compared the transcript differences with the audio and resolved
              caption/factual discrepancies''','''              <span><b>I checked transcript differences against the recording</b><small>Names, numbers and dates were compared with the actual voice. This does not automatically correct text; do not tick it just to preview.</small></span>''',1)
s=s.replace('''              Allow visibly marked missing-visual cards in a review-only video''','''              <b>Allow visible gap cards in this partial inspection video</b><small>Only permits placeholders where coverage is still missing. It does not approve footage or replace guide alternatives.</small>''',1)
s=s.replace('''                I reviewed the moving clip/photo, label, privacy restrictions,
                and Care instructions. I will not imply that contextual footage
                shows a different event.''','''                <b>I checked this visual for final use</b><small>I watched the selected clip/photo and checked its identity, event/date label, privacy and Care instructions. Not required just to see it in inspection.</small>''',1)
s=s.replace('v0.3.3','v0.3.4');p.write_text(s)
p=ROOT/'web/index.html';p.write_text(p.read_text().replace('v=0.3.3','v=0.3.4'))
for filename in ['package.json','package-lock.json']:
 p=ROOT/filename;d=json.loads(p.read_text());d['version']='0.3.4'
 if filename=='package-lock.json':d['packages']['']['version']='0.3.4'
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'web/src/episode.css';p.write_text(p.read_text()+'''
.upload-limit-hint { display: block; color: #bcb4a5; font-size: 11px; line-height: 1.7; margin: 7px 0 12px; }
.upload-progress { border: 1px solid #5d4c30; border-radius: 7px; background: #2c251b77; padding: 13px; margin: 12px 0; min-width: 0; }
.upload-progress > div { display: flex; justify-content: space-between; gap: 10px; font-size: 11px; color: #d9bc89; }
.upload-progress > div b { overflow-wrap: anywhere; font-weight: 550; }
.upload-progress progress { width: 100%; height: 7px; accent-color: #cdaa72; margin: 10px 0 7px; }
.upload-progress p { color: #b7b0a0; font-size: 10px; line-height: 1.7; }
.upload-progress.done { border-color: #3c5944; }.upload-progress.done > div { color: #a9c6ac; }
.upload-progress.error { border-color: #875748; }
.global-upload-progress { padding: 0 26px; }
.media-upload-limits { grid-column: 1 / -1; font-size: 11px; color: #bcb4a5; line-height: 1.7; margin: 0 0 10px; }
.ep-checkbox span small, .ep-checkbox > span > small { display: block; color: #9c9e95; font-size: 10px; line-height: 1.7; margin-top: 4px; }
.ep-checkbox b { font-weight: 500; }
.ep-final-review-title { grid-column: 1 / -1; border-top: 1px solid #39372f; padding-top: 15px; margin-top: 6px; }
.ep-final-review-title b { display: block; font-weight: 550; color: #d0b991; font-size: 12px; }
.ep-final-review-title small { display: block; font-size: 11px; color: #aaa699; line-height: 1.8; margin-top: 6px; }
.ep-overview span small { display: block; margin-top: 5px; color: #aaa18e; font-size: 9px; line-height: 1.6; }
.ep-alternative-choice { padding: 14px; border: 1px solid #574a34; background: #30281c55; border-radius: 6px; font-size: 11px; color: #c6b99e; }
.ep-alternative-choice > b { color: #ddc296; font-size: 12px; font-weight: 550; }
.ep-alternative-choice p { margin: 9px 0 !important; line-height: 1.8; }.ep-alternative-choice small { color: #a9a291; line-height: 1.8; font-size: 10px; }
.ep-alternative-choice .field { margin-top: 12px; }
.inspection-final-help { padding: 14px 18px; font-size: 11px; line-height: 1.8; color: #c6b28b; background: #2d261b55; border-top: 1px solid #4c412d; }
''')
print('Alternative choice controls, real upload events, explicit limits, and plain-language review help prepared.')
