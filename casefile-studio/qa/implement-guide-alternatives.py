from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'episode.py';s=p.read_text();assert 'def resolve_cue(' not in s
# Recognize explicit alternative fields; never mine the global research intro for substitutes.
s=s.replace('''            for name, value in re.findall(
                r"\\*\\*(At|Show|Preview|Label|Care):\\*\\*\\s*(.*?)(?=\\s*\\*\\*(?:At|Show|Preview|Label|Care):\\*\\*|\\Z)",
                block,
                re.S,
            ):
                fields[name.lower()] = value.strip()''','''            field_names = r"At|Show|Preview|Label|Care|Alternatives?(?:[ _-]+(?:Label|Preview|Care))?|Fallback(?:[ _-]+(?:Label|Preview|Care))?|Alt(?:[ _-]+(?:Label|Preview|Care))?|If[ _-]+(?:unavailable|missing)"
            for name, value in re.findall(
                r"\\*\\*(" + field_names + r"):\\*\\*\\s*(.*?)(?=\\s*\\*\\*(?:" + field_names + r"):\\*\\*|\\Z)", block, re.S | re.I,
            ):
                key = re.sub(r"[ _-]+", "_", name.lower())
                key = re.sub(r"^(?:alternatives?|fallback|alt)(?=_|$)", "alternative", key)
                if key in ("if_unavailable", "if_missing"):
                    key = "alternative"
                fields[key] = value.strip()''',1)
needle='''            cues.append(cue)'''
new='''            alt_text = fields.get("alternative", "")
            # Also recognize a positive, local conditional in Show/Care. Negative
            # prohibitions and general 'alternative case footage' are not permissions.
            if not alt_text:
                for sentence in re.split(r"(?<=[.!?;])\\s+|\\n", fields.get("show", "") + " " + fields.get("care", "")):
                    if re.search(r"\\bif\\b.*(?:unavailable|missing|not available|cannot|can't).*(?:\\buse\\b|replace with|fallback)", sentence, re.I):
                        use = re.search(r"(?:\\buse\\b|replace with|fallback(?: to)?)\\s+(.*)", sentence, re.I)
                        if use and not re.search(r"(?:do not|don't|never)\\s+use", sentence, re.I):
                            alt_text += " " + use[1]
            # Explicit 'S03 or S04' in Preview is a choice; multiple references
            # without 'or/alternative' are not automatically interchangeable.
            if len(refs) > 1 and re.search(r"\\bor\\b|alternative|fallback", fields.get("preview", ""), re.I):
                alt_text += " " + " ".join(refs[1:])
            alt_preview = fields.get("alternative_preview", "")
            alt_ids = []
            for sentence in re.split(r"(?<=[.!?;])\\s+|\\n", alt_text + " " + alt_preview):
                if re.search(r"(?:do not|don't|never)\\s+(?:use|substitute)|not\\s+(?:an?\\s+)?(?:alternative|substitute)|not permitted", sentence, re.I):
                    continue
                alt_ids.extend(x.upper() for x in re.findall(r"\\bS\\d+\\b", sentence, re.I) if x.upper() != refs[0])
            alt_ids = list(dict.fromkeys(alt_ids))
            alt_windows = []
            for a, b in re.findall(r"(\\d+(?::\\d+){1,2})\\s*[–—-]\\s*(\\d+(?::\\d+){1,2})", alt_preview or alt_text):
                start, end = stamp(a), stamp(b)
                if end <= start:
                    raise ValueError(f"Placement {number} has a reversed alternative preview range.")
                alt_windows.append({"start": start, "end": end})
            alt_link = re.search(r"\\[[^\\]]+\\]\\((https?://[^\\s)]+)\\)", alt_preview or alt_text)
            cue["alternative_instructions"] = alt_text.strip()
            cue["alternatives"] = [{
                "source_id": sid, "label": fields.get("alternative_label", ""),
                "care": fields.get("alternative_care", ""),
                "instructions": alt_text.strip(),
                "suggested_windows": alt_windows if len(alt_ids) == 1 else [],
                "window_ambiguous": len(alt_ids) > 1 and bool(alt_windows),
                "reference_url": safe_url(alt_link[1]) if alt_link and len(alt_ids) == 1 else None,
            } for sid in alt_ids]
            cues.append(cue)'''
assert needle in s;s=s.replace(needle,new,1)
s=s.replace('''        "filename": filename[:200],
        "raw": raw,
        "sources": sources,''','''        "filename": filename[:200],
        "raw": raw,
        "parser_version": 2,
        "sources": sources,''',1)
# Include named alternatives that don't already have a source-library record.
s=s.replace('''    intro = raw.split("## Script-by-script placement")[0]''','''    for cue in cues:
        for option in cue.get("alternatives", []):
            if option["source_id"] not in known:
                sources.append({"id": option["source_id"], "title": option["source_id"],
                                "url": option.get("reference_url"), "notes": "Guide-named alternative; catalog entry missing.",
                                "rights_note": "Not established; choosing an alternative does not grant permission."})
                known.add(option["source_id"])
    intro = raw.split("## Script-by-script placement")[0]''',1)
# Keep old saved-plan fingerprints stable when there was no choice/parser-version field.
s=s.replace('''            "script": (e.get("script") or {}).get("hash"),''','''            **({"choices": e["choices"]} if e.get("choices") else {}),
            **({"guide_parser": e["guide"]["parser_version"]} if (e.get("guide") or {}).get("parser_version") else {}),
            "script": (e.get("script") or {}).get("hash"),''',1)
s=s.replace('def source_ready(project, cue):','def _source_ready(project, cue):',1)
s=s.replace('def inspection_candidate(project, cue):','def _inspection_candidate(project, cue):',1)
s=s.replace('''    ready, asset, reason = source_ready(project, cue)''','''    ready, asset, reason = _source_ready(project, cue)''',1)
# Reviewed/manual windows are tied to their actual source, never recycled into a fallback.
s=s.replace('''    if not review.get("reviewed"):
        return (''','''    if (review.get("source_id") not in (None, cue["source_id"]) or
        review.get("asset_id") not in (None, asset["id"]) or
        (cue.get("using_alternative") and not review.get("source_id"))):
        return False, asset, "Review this alternative's own source window, label and Care; primary-source approval cannot be reused."
    if not review.get("reviewed"):
        return (''',1)
s=s.replace('''    duration = float(asset.get("video_duration") or asset.get("duration", 0))
    if "in" in review''','''    duration = float(asset.get("video_duration") or asset.get("duration", 0))
    if (review.get("source_id") not in (None, cue["source_id"]) or review.get("asset_id") not in (None, asset["id"]) or (cue.get("using_alternative") and not review.get("source_id"))):
        review = {k: v for k, v in review.items() if k in ("narration_start", "narration_end")}
    if cue.get("window_ambiguous") and not ("in" in review and "out" in review):
        result["status"] = "The alternative has ambiguous source ranges. Select its own local in/out window."
        return result
    if "in" in review''',1)
helpers='''def source_options(project, cue):
    options = [{"source_id": cue.get("primary_source_id", cue["source_id"]), "kind": "primary", "label": cue.get("primary_label", cue.get("label", "")),
                "suggested_windows": cue.get("primary_windows", cue.get("suggested_windows", [])), "care": "", "instructions": "Main source specified by guide.", "reference_url": cue.get("primary_reference_url", cue.get("reference_url"))}]
    for alt in cue.get("alternatives", []):
        options.append({**alt, "kind": "alternative"})
    if cue.get("alternative_instructions") and not cue.get("alternatives"):
        # A textual portrait/footage rule does not authorize an automatic random
        # source. Only an explicit user choice from the guide catalog may resolve it.
        for source in (state(project).get("guide") or {}).get("sources", []):
            if source["id"] != options[0]["source_id"]:
                options.append({"source_id": source["id"], "kind": "alternative", "manual_only": True,
                                "label": "", "suggested_windows": [], "care": "", "reference_url": source.get("url"),
                                "instructions": cue["alternative_instructions"]})
    return options


def resolve_cue(project, cue):
    if cue.get("_resolved"):
        return cue
    options = source_options(project, cue)
    choice = state(project).get("choices", {}).get(cue["id"], {})
    mode = choice.get("mode", "auto")
    candidates = options[:1] if mode == "primary" else [o for o in options if o["source_id"] == choice.get("source_id") and o["kind"] == "alternative"] if mode == "alternative" else [o for o in options if not o.get("manual_only")]
    if not candidates:
        candidates = options[:1]
    resolved = []
    for option in candidates:
        item = copy.deepcopy(cue)
        alternate = option["kind"] == "alternative"
        item.update(_resolved=True, primary_source_id=cue["source_id"], primary_label=cue.get("label", ""),
                    primary_windows=cue.get("suggested_windows", []), primary_reference_url=cue.get("reference_url"),
                    source_id=option["source_id"], using_alternative=alternate, selection_mode=mode,
                    source_choices=options, suggested_windows=option.get("suggested_windows", []),
                    window_ambiguous=option.get("window_ambiguous", False), reference_url=option.get("reference_url"))
        if alternate:
            item["label"] = choice.get("label") or option.get("label") or f"GUIDE ALTERNATIVE {option['source_id']} — NOT PRIMARY EVENT FOOTAGE"
            item["care"] = cue.get("care", "") + "\\nAlternative instruction: " + option.get("instructions", "") + " " + option.get("care", "")
        preview = _inspection_candidate(project, item)
        item["selection_reason"] = "Main source available for inspection." if not alternate else "Guide-permitted alternative selected by user." if mode == "alternative" else "Main source missing/unusable; using a linked guide-permitted alternative."
        resolved.append(item)
        if mode != "auto" or preview["usable"]:
            return item
    result = resolved[0]
    if len(options) > 1:
        result["selection_reason"] = "No usable linked main or permitted automatic alternative; link a file or choose a guide-permitted option."
    return result


def source_ready(project, cue):
    return _source_ready(project, resolve_cue(project, cue))


def inspection_candidate(project, cue):
    return _inspection_candidate(project, resolve_cue(project, cue))


def choose_source(project, cue_id, fields):
    if set(fields) - {"mode", "source_id", "label"}:
        raise ValueError("Unsupported source-choice field.")
    e = copy.deepcopy(state(project))
    raw = next((c for c in (e.get("guide") or {}).get("cues", []) if c["id"] == cue_id), None)
    if not raw:
        raise ValueError("Unknown guide placement.")
    old = resolve_cue(project, raw)
    choice = e.setdefault("choices", {}).get(cue_id, {"mode": "auto"}).copy()
    choice.update(fields)
    if choice["mode"] not in ("auto", "primary", "alternative"):
        raise ValueError("Choose automatic, main or a guide-permitted alternative.")
    if choice["mode"] == "alternative":
        permitted = {o["source_id"] for o in source_options(project, raw) if o["kind"] == "alternative"}
        if choice.get("source_id") not in permitted:
            raise ValueError("This source is not an alternative permitted by this placement's guide.")
    else:
        choice.pop("source_id", None)
    if "label" in choice:
        choice["label"] = str(choice["label"]).strip()[:240]
    e["choices"][cue_id] = choice
    project["episode"] = e
    new = resolve_cue(project, raw)
    review = e.setdefault("reviews", {}).get(cue_id, {})
    if old["source_id"] != new["source_id"]:
        e["reviews"][cue_id] = {k: v for k, v in review.items() if k in ("narration_start", "narration_end")}
    elif old["label"] != new["label"]:
        review["reviewed"] = False
    e.pop("timing_reviewed_digest", None)
    project["review"]["picture"] = False
    project["review"]["rights"] = False
    return project


'''
s=s.replace('def analyze(project):',helpers+'def analyze(project):',1)
s=s.replace('''    for cue in (guide or {}).get("cues", []):
        item = copy.deepcopy(cue)''','''    for original in (guide or {}).get("cues", []):
        cue = resolve_cue(project, original)
        item = copy.deepcopy(cue)''',1)
s=s.replace('''    used = {c["source_id"] for c in placements}''','''    used = {c.get("primary_source_id", c["source_id"]) for c in placements}
    option_ids = {o["source_id"] for c in placements for o in c.get("source_choices", [])}''',1)
s=s.replace('''        "used_source_count": len(used),''','''        "used_source_count": len(used),
        "source_option_ids": sorted(option_ids),
        "alternative_cues": sum(c.get("using_alternative", False) for c in placements),
        "placements_with_files": sum(bool(c.get("asset_id")) for c in placements),''',1)
# Save ranges/reviews against their effective source and asset.
s=s.replace('''    existing = e.setdefault("reviews", {}).get(cue_id, {})
    for key, value in fields.items():''','''    existing = e.setdefault("reviews", {}).get(cue_id, {})
    selected = resolve_cue(project, cue)
    selected_binding = e.get("bindings", {}).get(selected["source_id"], {})
    existing.update(source_id=selected["source_id"], asset_id=selected_binding.get("asset_id"))
    for key, value in fields.items():''',1)
s=s.replace('''                if cue["source_id"] == source_id:
                    e.setdefault("reviews", {}).pop(cue["id"], None)''','''                if source_id in {o["source_id"] for o in source_options(project, cue)}:
                    e.setdefault("reviews", {}).pop(cue["id"], None)''',1)
# Carry the exact selected alternative into the frozen timeline/provenance.
s=s.replace('''            if inspection:
                scene.update(''','''            if cue and cue.get("using_alternative"):
                scene.update(guide_primary_source_id=cue["primary_source_id"], guide_alternative=True)
            if inspection:
                scene.update(''',1)
s=s.replace('''        for key in ("inspection_only", "guide_unreviewed", "source_window_basis"):''','''        for key in ("inspection_only", "guide_unreviewed", "source_window_basis", "guide_primary_source_id", "guide_alternative"):''',1)
s=s.replace('''        cue = cues.get(scene.get("guide_cue_id"))
        if not cue:''','''        cue = cues.get(scene.get("guide_cue_id"))
        if cue:
            cue = resolve_cue(project, cue)
        if not cue:''',1)
s=s.replace('''        ready, asset, message = source_ready(project, cue)
        candidate = inspection_candidate(project, cue) if inspection else None''','''        if scene.get("guide_source_id") != cue["source_id"]:
            add("episode_source_choice_changed", "Source choice no longer matches this cut", "Rebuild after changing main/alternative choice.", True)
            break
        ready, asset, message = source_ready(project, cue)
        candidate = inspection_candidate(project, cue) if inspection else None''',1)
s=s.replace('''        text += f"## {c['id']}''','''        if c.get("using_alternative"):
            text += f"Guide-permitted alternative: {c['source_id']} instead of {c['primary_source_id']}. {c['selection_reason']}\\n\\n"
        text += f"## {c['id']}''',1)
p.write_text(s)
p=ROOT/'app.py';s=p.read_text();s=s.replace('version="0.3.3"','version="0.3.4"',1)
s=s.replace('''    for field in ("inspection_only", "guide_unreviewed"):''','''    for field in ("inspection_only", "guide_unreviewed", "guide_alternative"):''',1)
s=s.replace('''    if "source_window_basis" in scene:''','''    if "guide_primary_source_id" in scene:
        out["guide_primary_source_id"] = str(scene["guide_primary_source_id"])[:30]
    if "source_window_basis" in scene:''',1)
at=s.index('@app.patch("/api/projects/{id}/episode/options")')
s=s[:at]+'''@app.patch("/api/projects/{id}/episode/choice/{cue_id}")
async def episode_choice(id: str, cue_id: str, request: Request):
    body = await episode_json(request)
    with LOCK:
        p = project_or_404(id)
        checkpoint(p)
        try:
            episode.choose_source(p, cue_id, body)
        except (ValueError, TypeError, KeyError) as e:
            raise HTTPException(422, str(e))
        return episode_result(p)


'''+s[at:];p.write_text(s)
print('Guide-scoped alternatives and explicit per-placement choice implemented. No saved project was imported or rebuilt.')
