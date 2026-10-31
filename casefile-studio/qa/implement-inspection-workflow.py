from pathlib import Path

root=Path(__file__).resolve().parents[1]
p=root/'episode.py';s=p.read_text();assert 'def inspection_candidate(' not in s
helper='''def inspection_candidate(project, cue):
    """An explicitly unapproved source sample for inspection, never publication.

    Known guide/role restrictions and manually entered bounds still apply. We
    do not assert identity, factual context, licensing, privacy, or shot quality.
    """
    e = state(project)
    binding = e.get("bindings", {}).get(cue["source_id"], {})
    review = e.get("reviews", {}).get(cue["id"], {})
    ready, asset, reason = source_ready(project, cue)
    result = {"usable": False, "asset_id": (asset or {}).get("id"),
              "window": None, "basis": "", "status": reason, "reviewed": ready}
    if not asset or asset.get("kind") not in ("image", "video"):
        return result
    if asset["id"] in (project.get("narration_id"), project.get("music_id")):
        result["status"] = "Keep narration/music separate from muted source footage."
        return result
    if cue["chapter"] == "chapter-3" and (cue["source_id"] == "S02" or binding.get("contains_residence")):
        result["status"] = "Chapter 3 prohibits residential-property imagery, including in inspection."
        return result
    if cue.get("requires_stop") and review.get("narration_end") is None:
        result["status"] = "The guide requires an explicit narration stop before this source can appear, including in inspection."
        return result
    if asset["kind"] == "image":
        result.update(usable=True, basis="reviewed photo" if ready else "unreviewed linked photo",
                      status="Inspectable only; placement and reuse remain unapproved." if not ready else reason)
        return result
    duration = float(asset.get("video_duration") or asset.get("duration", 0))
    if "in" in review or "out" in review:
        start, end = review.get("in"), review.get("out")
        basis = "reviewed source window" if ready else "manually entered, unapproved source window"
        if start is None or end is None:
            result["status"] = "Complete both local source in/out values; partial manual bounds will not be guessed."
            return result
    elif cue.get("suggested_windows"):
        fit = next((w for w in cue["suggested_windows"] if 0 <= w["start"] < w["end"] <= duration + 0.001 and w["end"]-w["start"] >= 0.5), None)
        if not fit:
            result["status"] = "Guide preview times do not fit this uploaded file. Set its local source in/out; no excerpt offset was guessed."
            return result
        start, end = fit["start"], fit["end"]
        basis = "approximate guide preview window; unapproved"
    else:
        start, end = 0.0, min(duration, 5.0)
        basis = "opening source sample only; not a guide-selected or approved shot"
    if not all(math.isfinite(float(t)) for t in (start, end)) or start < 0 or end-start < 0.5 or end > duration + 0.001:
        result["status"] = "Source window is outside this file or shorter than half a second."
        return result
    result.update(usable=True, window={"in": float(start), "out": float(end)}, basis=basis,
                  status="Inspectable only; identity, source window, Care, and reuse still need human review." if not ready else reason)
    return result


'''
s=s.replace('def analyze(project):',helper+'def analyze(project):',1)
s=s.replace('''        placements.append(item)''','''        candidate = inspection_candidate(project, cue)
        item.update(inspection_ready=candidate["usable"], inspection_status=candidate["status"],
                    inspection_window=candidate["window"], inspection_basis=candidate["basis"])
        placements.append(item)''',1)
s=s.replace('''        "ready_cues": sum(c["ready"] for c in placements),''','''        "ready_cues": sum(c["ready"] for c in placements),
        "inspection_cues": sum(c["inspection_ready"] for c in placements),''',1)
s=s.replace('def build(project, allow_placeholders=False):','def build(project, allow_placeholders=False, inspection=False):',1)
s=s.replace('''    if report["cue_count"] != report["ready_cues"] and not allow_placeholders:''','''    available = report["inspection_cues"] if inspection else report["ready_cues"]
    if report["cue_count"] != available and not allow_placeholders:''',1)
s=s.replace('''    def push(start, end, chapter, cue, asset=None, trim=0, source_label=""):''','''    def push(start, end, chapter, cue, asset=None, trim=0, source_label="", unreviewed=False, window_basis=""):''',1)
s=s.replace('''            scenes.append(scene)''','''            if inspection:
                scene.update(inspection_only=True, guide_unreviewed=bool(asset and unreviewed), source_window_basis=window_basis if asset else "")
            scenes.append(scene)''',1)
s=s.replace('''        if not cue or not cue["ready"]:
            push(start, end, chapter, cue)
            continue
        asset = next(a for a in project["assets"] if a["id"] == cue["asset_id"])
        review = cue["review"]''','''        candidate = inspection_candidate(project, cue) if cue and inspection else None
        if not cue or not (candidate["usable"] if inspection else cue["ready"]):
            push(start, end, chapter, cue)
            continue
        asset = next(a for a in project["assets"] if a["id"] == cue["asset_id"])
        review = cue["review"]
        window = candidate["window"] if inspection else review''',1)
s=s.replace('''            trim = review["in"]
            visual_end = min(
                visual_end, start + math.floor((review["out"] - trim) * FPS + 0.001)
            )''','''            trim = window["in"]
            visual_end = min(
                visual_end, start + math.floor((window["out"] - trim) * FPS + 0.001)
            )''',1)
s=s.replace('''        push(start, visual_end, chapter, cue, asset, trim, cue["label"])''','''        push(start, visual_end, chapter, cue, asset, trim, cue["label"],
             unreviewed=not cue["ready"], window_basis=candidate["basis"] if inspection else "")''',1)
s=s.replace('''        "has_voice": report["has_voice"],
    }
    project["episode"]''','''        "has_voice": report["has_voice"],
        "mode": "inspection" if inspection else "reviewed",
        "unreviewed_cues": len({s["guide_cue_id"] for s in scenes if s.get("guide_unreviewed")}),
    }
    project["episode"]''',1)
s=s.replace('''        item["trim_start"] = round(float(scene.get("trim_start", 0)), 4)''','''        item["trim_start"] = round(float(scene.get("trim_start", 0)), 4)
        for key in ("inspection_only", "guide_unreviewed", "source_window_basis"):
            if key in scene:
                item[key] = scene[key]''',1)
s=s.replace('''    report = analyze(project)
    if not report["has_voice"]:''','''    report = analyze(project)
    inspection = (e.get("plan") or {}).get("mode") == "inspection"
    if inspection:
        add("episode_inspection_only", "Inspection draft — not publication cleared",
            "This plan can preview unreviewed linked media. No reuse, identity, Care, factual, or picture approval is implied. Complete real reviews and build a reviewed plan before final export.")
    if not report["has_voice"]:''',1)
s=s.replace('''        ready, asset, message = source_ready(project, cue)
        if not ready or not asset or asset["id"] != scene.get("asset_id"):''','''        ready, asset, message = source_ready(project, cue)
        candidate = inspection_candidate(project, cue) if inspection else None
        usable = candidate["usable"] if inspection else ready
        if inspection and not scene.get("inspection_only"):
            add("episode_inspection_marking", "Inspection disclosure removed", "Rebuild the inspection plan; its unapproved status must stay visible.", True)
            break
        if not inspection and (scene.get("inspection_only") or scene.get("guide_unreviewed")):
            add("episode_inspection_marking", "Inspection visuals require a reviewed rebuild", "Do not remove disclosures to bypass review. Build a reviewed plan after actual source sign-off.", True)
            break
        if not usable or not asset or asset["id"] != scene.get("asset_id"):''',1)
s=s.replace('''                message,
                True,
            )
            break
        if scene.get("source_label")''','''                candidate["status"] if inspection else message,
                True,
            )
            break
        if scene.get("source_label")''',1)
s=s.replace('''            review = e["reviews"][cue["id"]]
            start = float(scene.get("trim_start", 0))''','''            review = candidate["window"] if inspection else e["reviews"][cue["id"]]
            start = float(scene.get("trim_start", 0))''',1)
s=s.replace('''    if plan:
        text += f"Plan:''','''    if plan and plan.get("mode") == "inspection":
        text += "**UNREVIEWED INSPECTION ONLY — NOT FOR PUBLICATION.** Linked files may use approximate guide windows or opening samples. No source, Care, identity, reuse or factual approval is inferred. Known restricted chapters and required stop times still apply.\\n\\n"
    if plan:
        text += f"Plan:''',1)
p.write_text(s)

p=root/'app.py';s=p.read_text();s=s.replace('version="0.3.2"','version="0.3.3"',1)
s=s.replace('''    out["captions_exact"] = scene.get("captions_exact") is True''','''    for field in ("inspection_only", "guide_unreviewed"):
        if field in scene:
            out[field] = scene[field] is True
    if "source_window_basis" in scene:
        out["source_window_basis"] = str(scene["source_window_basis"])[:240]
    out["captions_exact"] = scene.get("captions_exact") is True''',1)
s=s.replace('''    allow_guided_gaps: bool = False
''','''    allow_guided_gaps: bool = False
    allow_inspection: bool = False
''',1)
s=s.replace('''    p = project_or_404(id)
    report = editorial.inspect(p)
    issues = [''','''    p = project_or_404(id)
    if ((p.get("episode") or {}).get("plan") or {}).get("mode") == "inspection":
        if not options.draft or not options.allow_inspection:
            raise HTTPException(400, "This is an unreviewed inspection plan. Explicitly choose an inspection draft; final export requires actual reviews and a reviewed-plan rebuild.")
    report = editorial.inspect(p)
    issues = [''',1)
s=s.replace('''            episode.build(p, allow_placeholders=body.get("allow_placeholders") is True)''','''            episode.build(p, allow_placeholders=body.get("allow_placeholders") is True,
                          inspection=body.get("inspection") is True)''',1)
p.write_text(s)

p=root/'renderer.py';s=p.read_text();s=s.replace('''        else ("REVIEW DRAFT" if draft else "")''','''        else ("UNREVIEWED INSPECTION" if scene.get("inspection_only") else "REVIEW DRAFT" if draft else "")''',1)
s=s.replace('''    if scene.get("source_label") and scene.get("asset_id"):''','''    if scene.get("inspection_only"):
        d.rectangle((0, 0, width, height * 0.058), fill=(34, 25, 13, 245))
        d.text((width * 0.025, height * 0.014), "UNREVIEWED INSPECTION — NOT FOR PUBLICATION", font=get_font(height * 0.023, True), fill=(236, 197, 127, 255))
    if scene.get("source_label") and scene.get("asset_id"):''',1)
s=s.replace('''        import episode

        blocked =''','''        import episode

        if ((project.get("episode") or {}).get("plan") or {}).get("mode") == "inspection" and (not options.get("draft", True) or not options.get("allow_inspection")):
            raise ValueError("Inspection rendering requires explicit inspection-draft consent; it cannot produce a publication-cleared export.")
        blocked =''',1);p.write_text(s)

p=root/'editorial.py';s=p.read_text();s=s.replace('''            "used_media": len(used),''','''            "used_media": len(used),
            "scenes_with_visuals": sum(s.get("asset_id") in assets and assets[s["asset_id"]].get("kind") in ("image", "video") for s in scenes),
            "unreviewed_visuals": sum(bool(s.get("guide_unreviewed")) for s in scenes),''',1);p.write_text(s)
print('Core inspection workflow applied. Existing projects were not rebuilt or imported.')
