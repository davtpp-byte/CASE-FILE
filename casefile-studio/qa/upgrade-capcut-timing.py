"""One-shot v0.3.1 patch; not an application dependency."""
from pathlib import Path
p=Path('episode.py');s=p.read_text().replace('import storage as store','import storage as store\nimport timing_io')
s=s.replace('def parse_timings(raw, filename):\n    entries = []','def parse_timings(raw, filename):\n    if len(raw) > 32000000:\n        raise ValueError("Timing exports are limited to 32 million characters.")\n    raw = raw.lstrip("\\ufeff")\n    entries = []\n    source_kind = "json"')
s=s.replace('        data = json.loads(raw)\n        entries = (','        data = json.loads(raw)\n        if timing_io.is_capcut(data):\n            return timing_io.parse_capcut(data, filename, digest(raw))\n        entries = (',1)
s=s.replace('    else:\n        for a, b, text in re.findall(', '    else:\n        source_kind = "srt"\n        for a, b, text in re.findall(',1)
s=s.replace('"text": re.sub(r"<[^>]+>", "", text),','"text": re.sub(r"<[^>]+>", "", text).strip(),',1)
s=s.replace('    return {\n        "filename": filename[:200],\n        "words": words,\n        "hash": digest(raw),','    return {\n        "filename": timing_io.basename(filename),\n        "words": words,\n        "source_kind": source_kind,\n        "duration": max(w["end"] for w in words),\n        "captions": [{"start": float(e["start"]), "end": float(e["end"]), "text": str(e.get("text", e.get("word", ""))).strip()} for e in entries] if source_kind == "srt" else [],\n        "captions_source": "srt" if source_kind == "srt" else None,\n        "sources": [{"kind": source_kind, "filename": timing_io.basename(filename), "hash": digest(raw)}],\n        "hash": digest(raw),',1)
s=s.replace('        e["timings"] = parse_timings(raw, filename)','        e["timings"] = timing_io.combine(e.get("timings"), parse_timings(raw, filename))',1)
a=s.index('    duration = float(\n',s.index('def analyze('));b=s.index('    sections = {',a)
s=s[:a]+'''    duration = float((voice or {}).get("duration") or (timing or {}).get("duration") or total_words / 145 * 60)
    duration_basis = "recording" if voice else "timing-export" if timing else "script-estimate"
    ts = tokens(script["text"]) if script else []
    reference = [t[3] for t in ts]
    errors, placements = [], []
    points = {0: 0.0, len(ts): duration}
    timed = set()
    alignment = None
    candidates = {}
    word_match_percent = 0.0
    if timing and ts and timing.get("source_kind") == "capcut":
        alignment = timing_io.align(script["text"], ts, timing)
        for i, anchor in alignment["anchors"].items():
            points[i] = anchor["start"]
            timed.add(i)
            if anchor["review_required"]:
                candidates[i] = anchor
        word_match_percent = alignment["match_percent"]
    elif timing and ts:
        for block in difflib.SequenceMatcher(
            None, reference, [w["normalized"] for w in timing["words"]],
            autojunk=len(ts) > 1000,
        ).get_matching_blocks():
            for j in range(block.size):
                points[block.a + j] = timing["words"][block.b + j]["start"]
                timed.add(block.a + j)
        word_match_percent = round(len(timed) / max(1, len(ts)) * 100, 1)
    if timing and ts and word_match_percent < 70:
        errors.append(
            "The timing file matches less than 70% of the script. Replace it with timings for this recording or remove it and use reviewed estimates."
        )
''' +s[b:]
a=s.index('            item["timing_source"] = (',s.index('def analyze('));b=s.index('        ready, asset, message',a)
s=s[:a]+'''            item["timing_review_required"] = idx in candidates and "narration_start" not in review
            item["timing_source"] = (
                "manual" if "narration_start" in review
                else "word boundary; text review" if idx in candidates
                else "provided word boundary" if alignment and idx in timed
                else "timing file (segment estimate)" if idx in timed and timing.get("precision") == "segment-interpolated"
                else "timing file" if idx in timed
                else "estimated"
            )
''' +s[b:]
s=s.replace('        "duration_estimated": not bool(voice),','        "duration_estimated": not bool(voice),\n        "duration_basis": duration_basis,\n        "timing_precision": (timing or {}).get("precision"),\n        "imported_caption_count": len((timing or {}).get("captions", [])),\n        "transcript_comparison": {k: v for k, v in (alignment or {}).items() if k != "anchors"},\n        "timing_candidate_cues": [c["id"] for c in placements if c.get("timing_review_required")],',1)
s=s.replace('"timing_word_match_percent": round(len(timed) / max(1, total_words) * 100, 1),','"timing_word_match_percent": word_match_percent,',1)
s=s.replace('        if end - start < 12:\n            raise ValueError(\n                "A planned cut is shorter than half a second. Adjust the cue or approved window."\n            )\n','',1)
s=s.replace('            if 0 < end - stop < 12:\n                stop = end - 12\n','',1)
s=s.replace('                "timing": "estimated",\n                "captions": [],','''                "timing": "imported-captions" if (e.get("timings") or {}).get("captions") else "estimated",
                "captions_exact": bool((e.get("timings") or {}).get("captions")),
                "captions": [
                    {"start": max(c["start"], cursor / FPS) - cursor / FPS,
                     "end": min(c["end"], stop / FPS) - cursor / FPS,
                     "text": c["text"]}
                    for c in (e.get("timings") or {}).get("captions", [])
                    if c["start"] < stop / FPS and c["end"] > cursor / FPS
                ],''',1)
s=s.replace('        if 0 < end - visual_end < 12:\n            visual_end = max(start, visual_end - 12)\n','',1)
s=s.replace('"timing": "guide anchors; caption timing remains estimated",','"timing": "provided caption timestamps; guide cue review required" if (e.get("timings") or {}).get("captions") else "guide anchors; caption timing remains estimated",',1)
s=s.replace('        item["trim_start"] = round(float(scene.get("trim_start", 0)), 4)','''        item["trim_start"] = round(float(scene.get("trim_start", 0)), 4)
        if scene.get("captions_exact"):
            item["captions_exact"] = True
            item["captions"] = [{"start": round(float(c["start"]), 6), "end": round(float(c["end"]), 6), "text": c["text"]} for c in scene.get("captions", [])]''',1)
s=s.replace('    if e.get("timing_reviewed_digest") != input_digest(project):','''    if report.get("transcript_comparison", {}).get("difference_spans") and e.get("timing_reviewed_digest") != input_digest(project):
        add("episode_transcript_differences", "Timing transcript differs from your script",
            f"{report['transcript_comparison']['difference_spans']} comparison spans need review (not confirmed spoken errors). Names, numbers and {len(report['timing_candidate_cues'])} cue-start substitution candidates must be checked against the audio. No text was automatically corrected.")
    if e.get("timing_reviewed_digest") != input_digest(project):''',1)
s=s.replace("{'estimated script duration' if r['duration_estimated'] else 'uploaded recording duration'}", "{r['duration_basis']}")
p.write_text(s)
p=Path('app.py');s=p.read_text().replace('version="0.3.0"','version="0.3.1"',1).replace('text: str = Field(max_length=1000000)','text: str = Field(max_length=32000000)',1)
s=s.replace('        out["duration"] = round(min(600, max(0.5, float(scene.get("duration", 5)))), 3)','        minimum = 1 / renderer.FPS if "guide_gap" in scene else 0.5\n        out["duration"] = round(min(600, max(minimum, float(scene.get("duration", 5)))), 3)',1)
s=s.replace('    out["captions"] = []\n    for c in scene.get','    out["captions_exact"] = scene.get("captions_exact") is True\n    out["captions"] = []\n    for c in scene.get',1)
p.write_text(s)
p=Path('renderer.py');s=p.read_text().replace('    if scene.get("captions"):\n','    if scene.get("captions_exact") or scene.get("captions"):\n',1)
s=s.replace('            for c in scene["captions"]','            for c in scene.get("captions", [])',1)
s=s.replace('def project_srt(project):\n    cues, offset = [], 0.0','''def project_srt(project):
    e = project.get("episode") or {}
    imported = (e.get("timings") or {}).get("captions")
    if e.get("guide") and imported:
        # Export the global supplied caption track once, not repeated fragments
        # split by visual cuts. Independent of whether burn-in captions are ON.
        return "\\n".join(f"{i}\\n{srt_time(c['start'])} --> {srt_time(c['end'])}\\n{c['text']}\\n" for i, c in enumerate(imported, 1))
    cues, offset = [], 0.0''',1)
p.write_text(s)
