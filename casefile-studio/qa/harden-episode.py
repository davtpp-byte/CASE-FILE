from pathlib import Path
p=Path('episode.py');s=p.read_text()
s=s.replace('(?=^[-#] |\\Z)', '(?=^- |^#{1,6}\\s|\\Z)')
s=s.replace('        last = start\n','        last = end\n')
s=s.replace('''    if not review.get("reviewed"):
''','''    if binding.get("rights_notes_hash") != digest(str(asset.get("license", "")).strip()):
        return False, asset, "The reuse notes changed. Reconfirm the recorded basis for this file."
    if not review.get("reviewed"):
''',1)
s=s.replace('''        binding["rights_confirmed"] = fields["rights_confirmed"] is True
''','''        binding["rights_confirmed"] = fields["rights_confirmed"] is True
        if binding["rights_confirmed"]:
            binding["rights_notes_hash"] = digest(str(a.get("license", "")).strip())
''',1)
a=s.index('def analyze(project):');b=s.index('\n\ndef review_cue(',a)
s=s[:a]+'''def analyze(project):
    e = state(project)
    script, guide, timing = e.get("script"), e.get("guide"), e.get("timings")
    voice = next((a for a in project.get("assets", []) if a["id"] == project.get("narration_id") and a.get("has_audio", a["kind"] == "audio") and float(a.get("duration", 0)) > 0), None)
    music = next((a for a in project.get("assets", []) if a["id"] == project.get("music_id")), None)
    total_words = (script or {}).get("word_count", 0)
    duration = float((voice or {}).get("duration") or max(total_words / 145 * 60, max((w["end"] for w in (timing or {}).get("words", [])), default=0)))
    ts = tokens(script["text"]) if script else []
    reference = [t[3] for t in ts]
    errors, placements = [], []
    points = {0: 0.0, len(ts): duration}
    timed = set()
    if timing and ts:
        for block in difflib.SequenceMatcher(None, reference, [w["normalized"] for w in timing["words"]], autojunk=len(ts)>1000).get_matching_blocks():
            for j in range(block.size):
                points[block.a+j] = timing["words"][block.b+j]["start"]
                timed.add(block.a+j)
        if len(timed) / max(1, len(ts)) < .7:
            errors.append("The timing file matches less than 70% of the script. Replace it with timings for this recording or remove it and use reviewed estimates.")
    sections = {section["key"]: section for section in (script or {}).get("sections", [])}
    last_word = {}
    for cue in (guide or {}).get("cues", []):
        item = copy.deepcopy(cue)
        section = sections.get(cue["chapter"])
        needles = [t[3] for t in tokens(cue["anchor"])]
        matches = []
        if section:
            lo, hi = section["word_start"], section["word_end"]
            for i in range(max(lo, last_word.get(cue["chapter"], lo)), hi-len(needles)+1):
                if reference[i:i+len(needles)] == needles:
                    matches.append(i)
        idx = matches[0] if len(matches) == 1 else None
        review = e.get("reviews", {}).get(cue["id"], {})
        item.update(matched=idx is not None, ambiguous=len(matches)>1, word_index=idx, review=review)
        if idx is not None:
            last_word[cue["chapter"]] = idx+1
            if "narration_start" in review:
                points[idx] = review["narration_start"]
            item["timing_source"] = "manual" if "narration_start" in review else "timing file" if idx in timed else "estimated"
        ready, asset, message = source_ready(project, cue)
        item.update(ready=ready, asset_id=(asset or {}).get("id"), status_detail=message)
        placements.append(item)
    ordered = sorted(points.items())
    if any(not math.isfinite(t) or t<0 or t>duration for _,t in ordered) or any(b[1] <= a[1] for a,b in zip(ordered, ordered[1:])):
        errors.append("Narration timing anchors are out of order or outside the audio duration. Correct the manual positions or the supplied timing file.")
    clock = [0.0]*len(ts)
    for (a,ta),(b,tb) in zip(ordered, ordered[1:]):
        for i in range(a,b):
            clock[i] = ta+(tb-ta)*(i-a)/max(1,b-a)
    for item in placements:
        idx = item["word_index"]
        item["narration_start"] = clock[idx] if idx is not None else None
        stop = item["review"].get("narration_end")
        if stop is not None and idx is not None and (stop<clock[idx]+.5 or stop>duration+1/FPS):
            errors.append(f"{item['id']}: the visual stop must be after its cue by at least half a second, and within the narration.")
    matched = sum(c["matched"] for c in placements)
    if script and guide and matched != len(placements):
        errors.append("Some At phrases are missing or ambiguous within their chapter. Do not guess their placement.")
    starts = [c["narration_start"] for c in placements if c["matched"]]
    if any(v>=duration for v in starts) or starts != sorted(starts):
        errors.append("Narration cue times are out of order or outside the audio duration.")
    if timing and voice and max(w["end"] for w in timing["words"])>duration+.05:
        errors.append("The timing file extends beyond the selected narration.")
    used = {c["source_id"] for c in placements}
    assets = {a["id"] for a in project.get("assets", []) if a["kind"] in ("image", "video")}
    bindings = e.get("bindings", {})
    return {
        "has_script": bool(script), "has_guide": bool(guide), "has_voice": bool(voice), "voice_id": (voice or {}).get("id"), "has_music": bool(music),
        "word_count": total_words, "duration": duration, "duration_estimated": not bool(voice),
        "sections": (script or {}).get("sections", []), "placements": placements, "cue_count": len(placements), "matched_cues": matched,
        "ready_cues": sum(c["ready"] for c in placements), "source_count": len((guide or {}).get("sources", [])), "used_source_count": len(used),
        "linked_source_count": sum(bindings.get(s, {}).get("asset_id") in assets for s in used), "suggestions": suggestions(project),
        "timing_word_match_percent": round(len(timed)/max(1,total_words)*100,1), "timing_reviewed": e.get("timing_reviewed_digest")==input_digest(project),
        "plan_current": bool(e.get("plan") and e["plan"].get("input_digest")==input_digest(project) and e["plan"].get("timeline_digest")==timeline_digest(project.get("scenes",[]))),
        "errors": errors, "boundaries": (guide or {}).get("boundaries"), "brief": e.get("brief", DEFAULT_BRIEF),
        "rights_disclaimer": "Source links and imported research claims are not permissions or independent verification. Source audio stays muted.", "word_clock": clock,
    }
''' + s[b:]
a=s.index('    target = round(report["duration"] * FPS)');s=s[:a]+s[a:].replace('    target = round(report["duration"] * FPS)','    target = math.ceil(report["duration"] * FPS - 1e-8)',1)
a=s.index('    # Piecewise timing anchors preserve');b=s.index('    events = ',a)
s=s[:a]+'''    # Use one monotone word clock for cue and chapter positions. Chapter estimates
    # must never compete with supplied word/segment times or manual anchors.
    clock = report["word_clock"]
''' + s[b:]
s=s.replace('''            if 0 < end - stop < 12:
                stop = end
''','''            if 0 < end - stop < 12:
                stop = end - 12
''',1)
s=s.replace('''                    ts[a][1] : (ts[b + 1][1] if b + 1 < N else len(script["text"]))
''','''                    (0 if a == 0 else ts[a][1]) : (ts[b + 1][1] if b + 1 < N else len(script["text"]))
''',1)
s=s.replace('''    assert sum(round(s["duration"] * FPS) for s in scenes) == target
    plan = {''','''    assert sum(round(s["duration"] * FPS) for s in scenes) == target
    if [t[3] for t in tokens(" ".join(s["narration"] for s in scenes))] != [t[3] for t in ts]:
        raise ValueError("The planned captions do not preserve every narration word in order. Review the cue timings.")
    if gap_frames and not allow_placeholders:
        raise ValueError("The approved clips do not cover the full timeline. Supply more coverage or explicitly allow marked gaps for a review-only plan.")
    plan = {''',1)
s=s.replace('''        "built_at": store.now(),''','''        "timeline_digest": timeline_digest(scenes),
        "built_at": store.now(),''',1)
a=s.index('\n\ndef issues(project):')
s=s[:a]+'''

def timeline_digest(scenes):
    # Frame-quantized times survive the general editor's millisecond sanitation.
    # Cosmetic look changes and factual source annotations are still permitted.
    result = []
    for scene in scenes:
        item = {k:scene.get(k) for k in ("asset_id","guide_cue_id","guide_source_id","source_label","guide_gap","chapter","transition")}
        item["narration"] = " ".join(scene.get("narration", "").split())
        for k in ("duration","audio_start","audio_duration"):
            item[k] = round(float(scene.get(k,0))*FPS)
        item["trim_start"] = round(float(scene.get("trim_start",0)),4)
        result.append(item)
    return digest(result)
''' + s[a:]
a=s.index('    if not e.get("plan"):',s.index('def issues(project):'))
s=s[:a]+'''    report = analyze(project)
    if not report["has_voice"]:
        add("episode_voice_missing", "Upload your finished narration before rendering", "The script can produce an estimated plan, not a silent documentary. Assign the audio in Episode setup; it will not be regenerated.", True)
    if report["errors"]:
        add("episode_timing_error", "Guide matching or timing needs correction", " ".join(report["errors"]), True)
    if project.get("narration_id") and project.get("narration_id")==project.get("music_id"):
        add("episode_audio_roles", "Voice and music must be separate files", "Assign each track to its own role in Episode setup.", True)
    if e.get("plan") and e["plan"].get("timeline_digest")!=timeline_digest(project.get("scenes",[])):
        add("episode_timeline_changed", "Guide cuts changed after planning", "Rebuild the episode plan. Manual shot moves/trims cannot bypass approved cue positions, care rules, or the full-narration guarantee.", True)
    cursor = 0.0
    continuous = bool(project.get("scenes"))
    for scene in project.get("scenes", []):
        duration = round(float(scene["duration"])*FPS)/FPS
        continuous = continuous and abs(float(scene.get("audio_start",-1))-cursor)<.003 and abs(float(scene.get("audio_duration",0))-duration)<.003
        cursor += duration
    if report["has_voice"] and (not continuous or cursor<report["duration"]-.001 or cursor>report["duration"]+1/FPS+.002):
        add("episode_narration_continuity", "The full original narration is not preserved", "Audio slices must start at zero, stay contiguous and in order, and cover the complete recording. Rebuild the guided plan.", True)
''' + s[a:]
p.write_text(s)
