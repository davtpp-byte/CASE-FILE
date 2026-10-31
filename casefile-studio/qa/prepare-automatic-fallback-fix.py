from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'episode.py';s=p.read_text();assert 'def resolve_automatic_source_links(' not in s
at=s.index('def build(project, allow_placeholders=False, inspection=False):')
helper='''def resolve_automatic_source_links(project):
    """Recover guide alternatives incorrectly filed under an unavailable main.

    This is not semantic image identification or licensing. It uses an explicit
    guide-permitted alternative plus a unique source-ID filename, or an already
    linked same-file alternative of the declared media type. No random substitutes.
    """
    e = state(project)
    guide = e.get("guide") or {}
    known = {item["id"] for item in guide.get("sources", [])}
    assets = {a["id"]: a for a in project.get("assets", []) if a.get("kind") in ("image", "video") and a.get("available_on_server") is not False}
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
        alternatives = [o for o in source_options(project, cue) if o["kind"] == "alternative" and not o.get("manual_only")]
        if not alternatives:
            continue
        hints = {x.upper() for x in re.findall(r"(?<![A-Za-z0-9])(S\\d+)(?![A-Za-z0-9])", asset.get("name", ""), re.I)} & known
        candidates = [o for o in alternatives if hints == {o["source_id"]}]
        if not candidates:
            main = next((r for r in cue.get("reference_previews", []) if r["source_id"] == primary), None)
            expects_video = bool(main and main.get("suggested_windows"))
            if expects_video and asset["kind"] == "image":
                candidates = [o for o in alternatives if o.get("media_kind") == "image" and state(project).get("bindings", {}).get(o["source_id"], {}).get("asset_id") == asset["id"]]
        ids = {o["source_id"] for o in candidates}
        if len(ids) != 1:
            continue
        alternative = next(iter(ids))
        affected = [c["id"] for c in guide["cues"] if c["source_id"] == primary and alternative in {o["source_id"] for o in source_options(project, c) if o["kind"] == "alternative"}]
        # A replacement's own source identity is preserved, so its own windows,
        # labels and Care are used. Main approval/ranges never transfer to it.
        bind_source(project, alternative, {"asset_id": asset["id"]})
        bind_source(project, primary, {"asset_id": None})
        changes.append({"main_source": primary, "alternative_source": alternative, "asset_id": asset["id"], "placements": affected,
                        "reason": "Guide-permitted alternative file was incorrectly linked as the main; resolved automatically without approving reuse or changing narration."})
        handled.add(primary)
    if changes:
        updated = state(project)
        updated["automatic_source_resolution"] = (updated.get("automatic_source_resolution", []) + changes)[-20:]
    return changes


'''
s=s[:at]+helper+s[at:]
s=s.replace('''def build(project, allow_placeholders=False, inspection=False):
    report = analyze(project)''','''def build(project, allow_placeholders=False, inspection=False):
    if inspection:
        resolve_automatic_source_links(project)
    report = analyze(project)''',1)
# Preserve the narration clock if the file/source link changes; only visual review expires.
old='''                if source_id in {
                    o["source_id"] for o in source_options(project, cue)
                }:
                    e.setdefault("reviews", {}).pop(cue["id"], None)'''
if old not in s:
 old='''                if source_id in {o["source_id"] for o in source_options(project, cue)}:
                    e.setdefault("reviews", {}).pop(cue["id"], None)'''
assert old in s
s=s.replace(old,'''                if source_id in {o["source_id"] for o in source_options(project, cue)}:
                    prior = e.setdefault("reviews", {}).get(cue["id"], {})
                    clock_only = {k: v for k, v in prior.items() if k in ("narration_start", "narration_end")}
                    if clock_only:
                        e["reviews"][cue["id"]] = clock_only
                    else:
                        e["reviews"].pop(cue["id"], None)''',1)
p.write_text(s)
p=ROOT/'app.py';s=p.read_text();needle='''        report = episode.analyze(p)
        if report["errors"]:''';assert needle in s;s=s.replace(needle,'''        corrections = episode.resolve_automatic_source_links(p)
        report = episode.analyze(p)
        if report["errors"]:''',1)
s=s.replace('''        result["reused_current_plan"] = bool(reused)
        return result''','''        result["reused_current_plan"] = bool(reused)
        result["automatic_source_corrections"] = corrections
        return result''',1);p.write_text(s)
print('Automatic guide-permitted correction prepared; no live project or runtime was changed.')
