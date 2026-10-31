"""Associate guide references with their own clocks and explicit editorial roles.

No downloads, licensing inference or independent identification. Original guide
text is retained by the caller; this only normalizes clearly linked choices.
"""

import re

REFERENCE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)\s*\(\s*`(S\d+)`\s*\)", re.I)
RANGE = re.compile(r"(\d+(?::\d+){1,2})\s*[–—-]\s*(\d+(?::\d+){1,2})")
MONTHS = {
    name[:3].lower(): name
    for name in [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
}


def _windows(text, stamp):
    result = []
    for a, b in RANGE.findall(text):
        start, end = stamp(a), stamp(b)
        if end <= start:
            raise ValueError("A linked source preview has a reversed range.")
        result.append({"start": start, "end": end})
    return result


def _context_label(cue, ref, catalog):
    original = cue.get("label", "")
    # These are explicitly neutral/shared labels, unlike a named person's label
    # or 'funeral' attached to a replacement portrait.
    if re.match(
        r"^(?:Courtroom coverage|Case courtroom footage|Sentencing)\s*\|",
        original,
        re.I,
    ):
        return original
    title = ref["title"]
    if re.search(r"portrait|photo|still image", title, re.I):
        return (
            "Portrait — not funeral footage"
            if re.search(r"funeral", original, re.I)
            else "Portrait — not footage of the narrated event"
        )
    if re.search(r"courtroom|court view", title, re.I):
        notes = (catalog.get(ref["source_id"]) or {}).get("notes", "")
        found = re.search(
            r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?:\d{1,2},?\s+)?(20\d{2})\b",
            notes,
            re.I,
        )
        return "Courtroom coverage" + (
            f" | {MONTHS[found[1][:3].lower()]} {found[2]}."
            if found
            else " — no speaker identified"
        )
    return f"GUIDE ALTERNATIVE {ref['source_id']} — NOT PRIMARY EVENT FOOTAGE"


def complete_reference_rules(cues, sources, stamp, safe_url):
    catalog = {source["id"]: source for source in sources}
    for cue in cues:
        raw = cue.get("preview_raw", "")
        matches = list(REFERENCE.finditer(raw))
        if not matches:
            continue  # Legacy ID-before-link guides keep their explicit parser data.
        references = []
        prior_end = 0
        for i, match in enumerate(matches):
            title, url, sid = match.groups()
            next_start = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
            # Ranges may be inside the link title or just after its source ID.
            windows = _windows(title + " " + raw[match.end() : next_start], stamp)
            references.append(
                {
                    "source_id": sid.upper(),
                    "title": title.strip(),
                    "reference_url": safe_url(url),
                    "suggested_windows": windows,
                    "connector": raw[prior_end : match.start()].strip(),
                }
            )
            prior_end = match.end()
        cue["reference_previews"] = references
        main = next(
            (ref for ref in references if ref["source_id"] == cue["source_id"]), None
        )
        if main:
            # Never use S26's source clock as an extra range inside S25, etc.
            cue["suggested_windows"] = main["suggested_windows"]
            cue["reference_url"] = main["reference_url"]
        alternatives = {a["source_id"]: a for a in cue.get("alternatives", [])}
        companions = []
        instructions = cue.get("alternative_instructions", "")
        for ref in references:
            sid = ref["source_id"]
            if sid == cue["source_id"]:
                continue
            connector = ref["connector"]
            prohibited = bool(
                re.search(
                    r"not\s+(?:an?\s+)?(?:alternative|substitute)|(?:do not|never)\s+(?:use|substitute)",
                    connector,
                    re.I,
                )
            )
            if prohibited:
                alternatives.pop(sid, None)
                cue.setdefault("excluded_preview_sources", []).append(sid)
                continue
            explicit = bool(
                re.search(r"\b(?:alternative|alternatively|or)\b", connector, re.I)
            )
            optional = bool(re.search(r"\boptional\b", connector, re.I))
            # C17: the positive fallback says 'portrait'; the explicitly linked
            # portrait is S01. Do not turn a semicolon-only follow-up into an alt.
            portrait_rule = bool(
                instructions
                and re.search(r"portrait|photo|image|still", instructions, re.I)
                and re.search(r"portrait|photo|still image", ref["title"], re.I)
            )
            if sid in alternatives or explicit or optional or portrait_rule:
                previous = alternatives.get(sid, {})
                text = (
                    previous.get("instructions")
                    or instructions
                    or (
                        "Optional guide source: " if optional else "Guide alternative: "
                    )
                    + ref["title"]
                )
                if not text.strip() or re.fullmatch(r"[S0-9\s,;]+", text):
                    text = (
                        "Optional guide source: "
                        if optional
                        else "Guide-listed alternative: "
                    ) + ref["title"]
                alternatives[sid] = {
                    **previous,
                    "source_id": sid,
                    "label": previous.get("label") or _context_label(cue, ref, catalog),
                    "care": previous.get("care", ""),
                    "instructions": text,
                    "suggested_windows": ref["suggested_windows"],
                    "reference_url": ref["reference_url"],
                    "window_ambiguous": False,
                    "media_kind": previous.get("media_kind")
                    or (
                        "image"
                        if re.search(r"portrait|photo|still image", ref["title"], re.I)
                        else "video"
                        if ref["suggested_windows"]
                        else None
                    ),
                    "manual_only": bool(previous.get("manual_only") or optional),
                    "optional": optional,
                }
            else:
                companions.append(
                    {
                        **ref,
                        "role": "optional follow-up, not an automatic replacement",
                        "instructions": cue.get("show", ""),
                    }
                )
        cue["alternatives"] = list(alternatives.values())
        if cue.get("excluded_preview_sources") and not alternatives:
            cue["alternative_permitted"] = False
            cue["alternative_visual_allowed"] = False
        cue["additional_previews"] = companions
        if alternatives:
            cue["alternative_permitted"] = True
            cue["alternative_visual_allowed"] = True
            if not cue.get("alternative_instructions"):
                cue["alternative_instructions"] = "Guide-listed choices: " + "; ".join(
                    ref["title"]
                    for ref in references
                    if ref["source_id"] in alternatives
                )


def restriction_reason(guide, cue, binding):
    """Return a restriction declared by THIS guide, never a magic source/chapter ID.

    Residence presence is producer-supplied; this is not image recognition. An
    explicit source-library exclusion also applies without a residence checkbox.
    """
    match = re.fullmatch(r"chapter-(\d+)", str(cue.get("chapter", "")))
    chapter = int(match[1]) if match else None
    clean = lambda text: re.sub(r"[*_`]", "", str(text or ""))
    residential = r"\bresiden\w*\b|\b(?:images?|imagery|footage|photos?|pictures?)\s+(?:of\s+)?(?:the\s+|a\s+)?(?:houses?|homes?)\b"
    negative = r"\bno\b|\bprohibit\w*\b|\b(?:must|do|may)\s+not\b|\bavoid\b"

    def forbids_residence(text):
        text = clean(text)
        return bool(
            re.search(residential, text, re.I)
            and re.search(negative, text, re.I)
            and not re.search(
                r"\bnot all\b|\bnot prohibited\b|\b(?:is|are) allowed\b", text, re.I
            )
        )

    boundaries = clean(guide.get("boundaries", ""))
    for clause in re.split(r"[.!?;\n]", boundaries):
        chapters = set()
        for scoped in re.finditer(
            r"\bchapters?\s+(\d+(?:\s*(?:,|and|or|&)\s*(?:chapters?\s+)?\d+)*)",
            clause,
            re.I,
        ):
            chapters.update(int(n) for n in re.findall(r"\d+", scoped[1]))
        if (
            not chapters
            and binding.get("contains_residence")
            and forbids_residence(clause)
        ):
            return "This guide prohibits residential-property imagery throughout the episode."
        if (
            chapter in chapters
            and binding.get("contains_residence")
            and forbids_residence(clause)
        ):
            return f"Chapter {chapter} prohibits residential-property imagery under this guide."
    source = next(
        (s for s in guide.get("sources", []) if s["id"] == cue["source_id"]), {}
    )
    notes = clean(source.get("notes", ""))
    for clause in re.split(r"[.!?;\n]", notes):
        exclusion = re.search(
            r"\b(?:do not|must not|never)\s+use\s+(?:(?:it|this (?:file|source|image|video)|S\d+)\s+)?in\s+chapters?\s+(\d+(?:\s*(?:,|and|or|&)\s*(?:chapter\s+)?\d+)*)",
            clause,
            re.I,
        )
        if exclusion and chapter in {int(n) for n in re.findall(r"\d+", exclusion[1])}:
            if re.search(r"residen\w*|houses?|homes?", notes, re.I):
                return f"Chapter {chapter} prohibits this residential-property source under its guide declaration."
            return f"Chapter {chapter} excludes source {cue['source_id']} under its guide declaration."
    if binding.get("contains_residence") and forbids_residence(cue.get("care", "")):
        return "This placement prohibits residential-property imagery under its Care instruction."
    return None
