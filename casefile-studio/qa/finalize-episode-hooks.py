from pathlib import Path

def rep(s,a,b,n=1):
 assert a in s,a[:120]
 return s.replace(a,b,n)
f=Path('renderer.py');s=f.read_text()
s=rep(s,'    return {\n        "duration": float(','''    return {
        "video_duration": float(video["duration"]) if video and video.get("duration") not in (None,"N/A") else None,
        "audio_duration": float(audio["duration"]) if audio and audio.get("duration") not in (None,"N/A") else None,
        "duration": float(''')
s=rep(s,'''    if not shutil.which("ffmpeg"):
''','''    if (project.get("episode") or {}).get("guide"):
        import episode
        blocked = [i for i in episode.issues(project) if i["blocks_draft"]]
        if blocked:
            raise ValueError(" ".join(i["title"]+": "+i["detail"] for i in blocked[:2]))
    if not shutil.which("ffmpeg"):
''')
s=rep(s,'''            if asset and asset.get("kind") == "video":
                command += [
                    "-stream_loop",
                    "-1",
                    "-ss",''','''            if asset and asset.get("kind") == "video":
                if not scene.get("guide_cue_id"):
                    command += ["-stream_loop", "-1"]
                command += [
                    "-ss",''')
s=rep(s,'''        if voice_index is not None:
            # Slice the master voice by scene before concatenating,''','''        if voice_index is not None and (project.get("episode") or {}).get("guide"):
            # Guide projects retain the continuous uploaded recording, not a sequence
            # of regenerated or rearranged snippets. Only the last frame is padded.
            af.append(f"[{voice_index}:a]asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,apad,atrim=duration={total}[voice]")
        elif voice_index is not None:
            # Slice the master voice by scene before concatenating,''')
f.write_text(s)
f=Path('episode.py');s=f.read_text()
s=rep(s,'end > float(asset.get("duration", 0)) + 0.05','end > float(asset.get("video_duration") or asset.get("duration", 0)) + 0.001')
s=rep(s,'''        parsed = parse_script(raw, filename)
        e["script"] = parsed''','''        parsed = parse_script(raw, filename)
        if e.get("script") and e["script"]["hash"] != parsed["hash"]:
            e["reviews"] = {}
        e["script"] = parsed''')
f.write_text(s)
f=Path('app.py');s=f.read_text()
s=rep(s,'from fastapi import FastAPI, HTTPException, Request, UploadFile, File','from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form')
s=rep(s,'''        p = project_or_404(id)
        checkpoint(p)
        try:
            # An amended script''','''        p = project_or_404(id)
        if (p.get("episode") or {}).get("guide"):
            raise HTTPException(400, "Use Episode setup to rebuild this guide-driven timeline. Generic filename/rotation assignment is disabled.")
        checkpoint(p)
        try:
            # An amended script''')
s=rep(s,'''async def upload(id: str, files: list[UploadFile] = File(...)):''','''async def upload(id: str, files: list[UploadFile] = File(...), episode_role: Literal["narration", "music", "sources"] | None = Form(default=None)):''')
s=rep(s,'''        if suffix in (".md", ".txt") and p.get("episode"):''','''        if episode_role and suffix in (".md", ".txt"):
            raise HTTPException(422, "This card accepts media only. Import script and guide documents in their separate cards.")
        if suffix in (".md", ".txt") and p.get("episode"):''')
s=rep(s,'''            added.append(asset)
''','''            if episode_role in ("narration", "music") and not asset.get("has_audio"):
                raise ValueError("Narration and music require an actual audio track, not an image or silent video.")
            if episode_role == "sources" and asset["kind"] not in ("image", "video"):
                raise ValueError("The source-file input accepts uploaded images and videos. Keep music and narration in their own cards.")
            added.append(asset)
''')
s=rep(s,'''        p["assets"].extend(added)
        if script is not None:''','''        p["assets"].extend(added)
        if episode_role and not p.get("episode"):
            p["episode"] = copy.deepcopy(episode.state(p))
        if script is not None:''')
for name in ('draft', 'narrate','transcribe'):
 a=f'''def {name}(id: str, '''
 pos=s.index(a);end=s.index('\n    cfg = config(request)',pos)
 s=s[:end]+'''
    if (p.get("episode") or {}).get("guide"):
        raise HTTPException(400, "This guide-driven project preserves your supplied script and voice. Use Episode setup; destructive script/voice/transcript generation is disabled.")'''+s[end:]
s=rep(s,'''        "confirm_timing",
''','''        "confirm_timing",
        "clear_timings",
''')
s=rep(s,'''        e = copy.deepcopy(episode.state(p))
        if "brief" in body:''','''        e = copy.deepcopy(episode.state(p))
        if body.get("clear_timings") is True:
            e.pop("timings", None)
            e.pop("timing_reviewed_digest", None)
        if "brief" in body:''')
s=rep(s,'''                if p.get(role) != body[role]:
                    e.pop("timing_reviewed_digest", None)
''','''                if p.get(role) != body[role]:
                    e.pop("timing_reviewed_digest", None)
                    if role == "narration_id":
                        for review in e.get("reviews", {}).values():
                            review.pop("narration_start", None)
                            if "narration_end" in review:
                                review.pop("narration_end", None)
                                review["reviewed"] = False
''')
pos=s.index('\n\nclass EpisodeDocument(')
s=s[:pos]+'''

async def episode_json(request):
    try:
        data = await request.json()
    except ValueError:
        raise HTTPException(422, "Send a JSON object.")
    if not isinstance(data, dict):
        raise HTTPException(422, "Send a JSON object.")
    return data
''' + s[pos:]
# Only the new routes; preserve the older APIs' public contracts.
pos=s.index('async def episode_source(');s=s[:pos]+s[pos:].replace('body = await request.json()', 'body = await episode_json(request)')
f.write_text(s)
f=Path('web/src/EpisodeSetup.jsx');s=f.read_text()
s=rep(s,'        const form = new FormData();','''        const form = new FormData();
        form.append("episode_role", role==="narration_id"?"narration":role==="music_id"?"music":"sources");''')
s=rep(s,'''            {e.timings ? e.timings.filename : "Add optional timing file"}
          </FilePick>''','''            {e.timings ? e.timings.filename : "Add optional timing file"}
          </FilePick>
          {e.timings && <button className="ep-clear-timings" disabled={disabled} onClick={()=>save("/episode/options","PATCH",{clear_timings:true})}>Remove timing file · use estimates</button>}
          {e.timings && <p className="ep-small">{report?.timing_word_match_percent??0}% of script words matched. Segment timings are interpolated; they are not exact word alignment.</p>}''')
f.write_text(s)
f=Path('web/src/ProductionTools.jsx');s=f.read_text();s=rep(s,'  review: "Review",','  review: "Review",\n  setup: "Episode setup",');f.write_text(s)
