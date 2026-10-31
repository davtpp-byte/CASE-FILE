from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'episode.py';s=p.read_text();a=s.index('def resolve_automatic_source_links(');b=s.index('\ndef build(',a)
s=s[:a]+'''def resolve_automatic_source_links(project):
    """Resolve available guide choices, including files placed under the wrong main.

    Guide IDs and rules are project-local. Filenames are source-ID hints, not
    identity or rights verification. Inferred candidates remain unapproved.
    """
    guide = state(project).get("guide") or {}
    known = {source["id"] for source in guide.get("sources", [])}
    assets = {asset["id"]: asset for asset in project.get("assets", [])
              if asset.get("kind") in ("image", "video") and asset.get("available_on_server") is not False}
    # A permitted alternative that has been uploaded should not need a separate
    # matching click. Preserve an existing usable explicit binding, not a ghost.
    eligible = {**project, "assets": list(assets.values())}
    for sid, aid in suggestions(eligible).items():
        existing = state(project).get("bindings", {}).get(sid, {}).get("asset_id")
        if existing not in assets:
            bind_source(project, sid, {"asset_id": aid})
    changes = []
    handled = set()
    for cue in guide.get("cues", []):
        primary = cue["source_id"]
        if primary in handled:
            continue
        binding = state(project).get("bindings", {}).get(primary, {})
        asset = assets.get(binding.get("asset_id"))
        if not asset:
            continue
        options = [o for o in source_options(project, cue) if o["kind"] == "alternative" and not o.get("manual_only")]
        hints = {x.upper() for x in re.findall(r"(?<![A-Za-z0-9])(S\\d+)(?![A-Za-z0-9])", asset.get("name", ""), re.I)} & known
        candidates = [o for o in options if hints == {o["source_id"]}]
        if not candidates and not hints:
            reference = next((r for r in cue.get("reference_previews", []) if r["source_id"] == primary), None)
            if reference and reference.get("suggested_windows") and asset["kind"] == "image":
                kind_options = [o for o in options if o.get("media_kind") == "image"]
                same_file = [o for o in kind_options if state(project).get("bindings", {}).get(o["source_id"], {}).get("asset_id") == asset["id"]]
                candidates = same_file or (kind_options if len({o["source_id"] for o in kind_options}) == 1 else [])
        permitted = {o["source_id"] for o in candidates}
        if len(permitted) == 1:
            alternative = next(iter(permitted))
            affected = [c["id"] for c in guide["cues"] if c["source_id"] == primary and alternative in {o["source_id"] for o in source_options(project, c) if o["kind"] == "alternative"}]
            bind_source(project, alternative, {"asset_id": asset["id"]})
            bind_source(project, primary, {"asset_id": None})
            changes.append({"main_source": primary, "alternative_source": alternative, "asset_id": asset["id"], "placements": affected,
                            "action": "use_guide_alternative", "reason": "An uploaded guide-permitted alternative was filed as the main; its own ranges, label and Care apply. Identity/reuse remain unapproved."})
            handled.add(primary)
    if changes:
        e = state(project)
        e["automatic_source_resolution"] = (e.get("automatic_source_resolution", []) + changes)[-20:]
    return changes

''' +s[b:];p.write_text(s)
p=ROOT/'app.py';s=p.read_text();s=s.replace('version="0.4.0"','version="0.4.1"',1)
s=s.replace('''            episode.bind_source(p, source_id, body)
        except''','''            episode.bind_source(p, source_id, body)
            episode.resolve_automatic_source_links(p)
        except''',1)
needle='''                episode.bind_source(p, source_id, {"asset_id": asset_id})
        return episode_result(p)''';assert needle in s;s=s.replace(needle,'''                episode.bind_source(p, source_id, {"asset_id": asset_id})
        episode.resolve_automatic_source_links(p)
        return episode_result(p)''',1)
at=s.index('@app.get("/api/projects/{id}/jobs")')
s=s[:at]+'''@app.api_route("/api/projects/{id}/exports/{export_id}/download", methods=["GET", "HEAD"])
def download_export(id: str, export_id: str):
    """Save a completed export; never render again, approve it or delete it."""
    p = project_or_404(id)
    if not re.fullmatch(r"[a-f0-9]{16}", export_id):
        raise HTTPException(404, "Rendered video not found.")
    record = next((item for item in p.get("exports", []) if item.get("id") == export_id), None)
    if record is None:
        raise HTTPException(404, "This completed export does not belong to the selected project.")
    folder = (DATA / "exports" / export_id).resolve()
    if not folder.is_relative_to((DATA / "exports").resolve()):
        raise HTTPException(404, "Rendered video is unavailable.")
    file = (folder / "documentary.mp4").resolve()
    if not file.is_relative_to(folder) or not file.is_file():
        raise HTTPException(404, "The render record exists, but its MP4 is not available on this server. A project JSON backup does not contain the video bytes. Nothing was deleted by this download request.")
    title = re.sub(r"[^A-Za-z0-9 _-]", "", str(p.get("title", "Casefile-video"))).strip()[:110] or "Casefile-video"
    suffix = "-unreviewed-inspection" if record.get("inspection_only") else "-review-draft" if record.get("draft") else ""
    return FileResponse(file, media_type="video/mp4", filename=title + suffix + ".mp4", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


'''+s[at:];p.write_text(s)

p=ROOT/'web/src/main.jsx';s=p.read_text();a=s.index('''            <Button
              kind="primary"
              icon={Download}
              onClick={() =>
                project.episode?.guide''');b=s.index('''            </Button>''',a)+len('''            </Button>''')
s=s[:a]+'''            {project.exports[0] ? <a className="btn primary" aria-label="Download latest MP4" href={`/api/projects/${project.id}/exports/${project.exports[0].id}/download`} download><Download size={14}/> Download MP4</a> : <Button kind="primary" icon={Film} disabled={locked} onClick={() => project.episode?.guide ? makeFirstDraft({render:true}) : openTool("export", "review")}>{project.episode?.guide ? "Make video" : "Export video"}</Button>}'''+s[b:]
s=s.replace('''                        href={ex.url}
                        download=''', '''                        href={`/api/projects/${project.id}/exports/${ex.id}/download`}
                        download=''',1)
# A completed render has an explicit direct link when the embedding browser blocks downloads.
needle='''                      <a
                        className="icon-btn"
                        href={ex.url}''';assert needle in s
s=s.replace(needle,'''                      <details className="download-help"><summary>Download not starting?</summary><p>The preview frame may restrict downloads. Copy this direct link and paste it into a new browser tab to save the finished MP4. It does not start another render.</p><input aria-label={`Direct MP4 download link ${ex.id}`} readOnly value={new URL(`/api/projects/${project.id}/exports/${ex.id}/download`, window.location.origin).href} onFocus={(ev)=>ev.target.select()}/><a href={`/api/projects/${project.id}/exports/${ex.id}/download`} target="_blank" rel="noopener noreferrer">Open download outside the preview</a></details>
'''+needle,1)
s=s.replace('version: "0.4.0"','version: "0.4.1"').replace('v0.4.0','v0.4.1');p.write_text(s)
p=ROOT/'web/src/EpisodeSetup.jsx';p.write_text(p.read_text().replace('v0.4.0','v0.4.1'))
p=ROOT/'web/index.html';p.write_text(p.read_text().replace('v=0.4.0','v=0.4.1'))
for name in ['package.json','package-lock.json']:
 p=ROOT/name;d=json.loads(p.read_text());d['version']='0.4.1'
 if name=='package-lock.json':d['packages']['']['version']='0.4.1'
 p.write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'web/src/episode.css';p.write_text(p.read_text()+'''\n.download-help { font-size:10px; color:#bca77f; max-width:260px; }.download-help summary{cursor:pointer;}.download-help p{line-height:1.8;margin:8px 0;}.download-help input{width:100%;font-size:10px;padding:8px;background:#171a1c;border:1px solid #494436;border-radius:4px;color:#d7c6a5;}.download-help > a{display:block;margin-top:8px;color:#d0b17d;}\n''')
print('Shared fallback correction and completed-file download controls applied to source; no case-specific hard-coded replacements.')
