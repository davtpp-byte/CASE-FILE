"""Guide-driven episode setup: local document parsing and bounded visual planning.

No provider calls, URL downloads, factual verification, or automatic rights clearance.
Uploaded narration remains the audio master. Links are references, not media files.
"""

from __future__ import annotations
import copy
import difflib
import hashlib
import json
import math
import re
import unicodedata
from urllib.parse import urlparse, parse_qs
import storage as store
import timing_io

FPS = 24
WORD = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
DEFAULT_BRIEF = "Keep my narration unchanged. Follow the editing guide, mute source audio, and put music underneath my voice. Use only linked, producer-reviewed source files. Keep missing visuals visibly marked."


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def norm(word):
    return re.sub(
        r"[^\w]", "", unicodedata.normalize("NFKC", word).lower().replace("’", "'")
    )


def tokens(text):
    return [
        (m.group(), m.start(), m.end(), norm(m.group())) for m in WORD.finditer(text)
    ]


def spoken(text):
    text = re.sub(r"\\([\\`*_{}\[\]()#+.!-])", r"\1", text)
    return text.replace("**", "").strip()


def chapter_key(title):
    match = re.search(r"\bCHAPTER\s+(\d+)\b", title, re.I)
    return "chapter-" + str(int(match[1])) if match else "hook"


def parse_script(raw, filename="script.md"):
    if len(raw) > 200000:
        raise ValueError("The script exceeds 200,000 characters.")
    if re.search(r"\*\*At:\*\*", raw) and re.search(
        r"Script-by-script placement", raw, re.I
    ):
        raise ValueError(
            "This is an editing guide, not narration. Import it in the Editing guide card."
        )
    sections = []
    title = "Opening"
    key = "hook"
    lines = []

    def append():
        body = spoken("\n".join(lines)).strip()
        if body:
            sections.append({"key": key, "title": title, "text": body})

    for line in raw.splitlines():
        clean = line.strip().strip("#* ").strip()
        if re.fullmatch(
            r"(?:OPENING\s+)?HOOK|CHAPTER\s+\d+(?:\s*[—–:-].*)?", clean, re.I
        ):
            append()
            title = clean
            key = chapter_key(clean)
            lines = []
        else:
            lines.append(line)
    append()
    if not sections:
        raise ValueError("The narration script is empty.")
    if len({s["key"] for s in sections}) != len(sections):
        raise ValueError("Use a unique heading for each chapter.")
    full = ""
    cursor = 0
    for section in sections:
        if full:
            full += "\n\n"
        section["char_start"] = len(full)
        section["word_start"] = cursor
        full += section["text"]
        cursor += len(tokens(section["text"]))
        section["word_end"] = cursor
    return {
        "filename": filename[:200],
        "raw": raw,
        "text": full,
        "sections": sections,
        "word_count": cursor,
        "hash": digest(full),
    }


def safe_url(value):
    try:
        p = urlparse(value)
    except ValueError:
        raise ValueError("A source contains an invalid URL.")
    if p.scheme not in ("http", "https") or not p.netloc:
        raise ValueError("Source links must be http/https reference URLs.")
    return value


def stamp(value):
    parts = value.strip().replace(",", ".").split(":")
    if len(parts) not in (2, 3):
        raise ValueError("Use minutes:seconds or hours:minutes:seconds.")
    numbers = [float(v) for v in parts]
    result = sum(v * 60 ** (len(numbers) - i - 1) for i, v in enumerate(numbers))
    if not math.isfinite(result) or result < 0:
        raise ValueError("Timestamps must be finite and nonnegative.")
    return result


def parse_guide(raw, filename="editing-guide.md"):
    if len(raw) > 500000:
        raise ValueError("The editing guide exceeds 500,000 characters.")
    sources = []
    for match in re.finditer(
        r"^- \*\*(S\d+)\s*[—–-]\s*\[([^\]]+)\]\((https?://[^\s)]+)\)\*\*(.*?)(?=^- |^#{1,6}\s|\Z)",
        raw,
        re.M | re.S,
    ):
        sid, title, url, notes = match.groups()
        rights = re.search(r"\*\*Rights:\*\*\s*(.*)", notes, re.S)
        sources.append(
            {
                "id": sid.upper(),
                "title": title.strip(),
                "url": safe_url(url),
                "notes": notes.strip(),
                "rights_note": rights[1].strip()
                if rights
                else "Not established in the guide.",
            }
        )
    cues = []
    for chapter, body in re.findall(
        r"^###\s+(HOOK|CHAPTER\s+\d+)\s*\n(.*?)(?=^### |^## |\Z)", raw, re.M | re.S
    ):
        for number, block in re.findall(
            r"^(\d+)\.\s+(\*\*At:\*\*.*?)(?=^\d+\.\s+\*\*At:|\Z)", body, re.M | re.S
        ):
            fields = {}
            for name, value in re.findall(
                r"\*\*(At|Show|Preview|Label|Care):\*\*\s*(.*?)(?=\s*\*\*(?:At|Show|Preview|Label|Care):\*\*|\Z)",
                block,
                re.S,
            ):
                fields[name.lower()] = value.strip()
            anchor = fields.get("at", "").strip('“”" ')
            if not anchor:
                raise ValueError("Every placement needs a quoted At phrase.")
            refs = list(
                dict.fromkeys(re.findall(r"`(S\d+)`", fields.get("preview", "")))
            )
            link = re.search(
                r"\[[^\]]+\]\((https?://[^\s)]+)\)", fields.get("preview", "")
            )
            if not refs:
                raise ValueError(f"Placement {number} has no source ID.")
            windows = []
            for a, b in re.findall(
                r"(\d+(?::\d+){1,2})\s*[–—-]\s*(\d+(?::\d+){1,2})",
                fields.get("preview", ""),
            ):
                start, end = stamp(a), stamp(b)
                if end <= start:
                    raise ValueError(
                        f"Placement {number} has a reversed preview range."
                    )
                windows.append({"start": start, "end": end})
            cue = {
                "id": "C" + str(int(number)).zfill(2),
                "number": int(number),
                "chapter": chapter_key(chapter),
                "chapter_label": chapter,
                "anchor": anchor,
                "show": fields.get("show", ""),
                "label": fields.get("label", ""),
                "care": fields.get("care", ""),
                "source_ids": refs,
                "source_id": refs[0],
                "reference_url": safe_url(link[1]) if link else None,
                "suggested_windows": windows,
                "approximate": True,
                "requires_stop": bool(
                    re.search(
                        r"stop\s+(?:it\s+)?before",
                        fields.get("show", "") + " " + fields.get("care", ""),
                        re.I,
                    )
                ),
            }
            cues.append(cue)
    if not cues:
        raise ValueError(
            "No placements found. Use chapter headings and numbered At / Show / Preview / Label / Care entries, as in your supplied guide."
        )
    if len(cues) > 300 or len(sources) > 200:
        raise ValueError("This version supports 300 guide placements and 200 sources.")
    if len({c["id"] for c in cues}) != len(cues):
        raise ValueError("Placement numbers must be unique.")
    if len({s["id"] for s in sources}) != len(sources):
        raise ValueError("Source IDs must be unique.")
    # Preserve exact IDs, including S01. Never silently turn S01 into S1.
    known = {s["id"] for s in sources}
    for cue in cues:
        if cue["source_id"] not in known:
            sources.append(
                {
                    "id": cue["source_id"],
                    "title": cue["source_id"],
                    "url": cue["reference_url"],
                    "notes": "Source referenced by placement; catalog entry missing.",
                    "rights_note": "Not established.",
                }
            )
            known.add(cue["source_id"])
    intro = raw.split("## Script-by-script placement")[0]
    boundaries = re.search(
        r"\*\*Standing boundaries:\*\*\s*(.*?)(?:\n\n|\Z)", intro, re.S
    )
    return {
        "filename": filename[:200],
        "raw": raw,
        "sources": sources,
        "cues": cues,
        "boundaries": boundaries[1].strip()
        if boundaries
        else "Review all Care instructions before using source material.",
        "hash": digest(raw),
    }


def parse_timings(raw, filename):
    if len(raw) > 32000000:
        raise ValueError("Timing exports are limited to 32 million characters.")
    raw = raw.lstrip("\ufeff")
    entries = []
    source_kind = "json"
    if filename.lower().endswith(".json"):
        data = json.loads(raw)
        if timing_io.is_capcut(data):
            return timing_io.parse_capcut(data, filename, digest(raw))
        entries = (
            data.get("words", data.get("segments", []))
            if isinstance(data, dict)
            else data
        )
        if not isinstance(entries, list):
            raise ValueError("Timing JSON needs a words or segments list.")
    else:
        source_kind = "srt"
        for a, b, text in re.findall(
            r"(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\Z)",
            raw,
            re.S,
        ):
            entries.append(
                {
                    "start": stamp(a),
                    "end": stamp(b),
                    "text": re.sub(r"<[^>]+>", "", text).strip(),
                }
            )
    if not entries or len(entries) > 20000:
        raise ValueError("No usable timing entries, or more than 20,000 entries.")
    words = []
    last = 0
    for entry in entries:
        start, end = float(entry["start"]), float(entry["end"])
        if (
            not all(math.isfinite(v) for v in (start, end))
            or start < last - 0.01
            or end <= start
            or end > 21600
        ):
            raise ValueError(
                "Timing entries must be ordered, finite, and within six hours."
            )
        ts = tokens(str(entry.get("word", entry.get("text", ""))))
        n = len(ts)
        for i, t in enumerate(ts):
            words.append(
                {
                    "word": t[0],
                    "normalized": t[3],
                    "start": start + (end - start) * i / max(1, n),
                    "end": start + (end - start) * (i + 1) / max(1, n),
                }
            )
        last = end
    if not words:
        raise ValueError("The timing file contains no words.")
    return {
        "filename": timing_io.basename(filename),
        "words": words,
        "source_kind": source_kind,
        "duration": max(w["end"] for w in words),
        "captions": [
            {
                "start": float(e["start"]),
                "end": float(e["end"]),
                "text": str(e.get("text", e.get("word", ""))).strip(),
            }
            for e in entries
        ]
        if source_kind == "srt"
        else [],
        "captions_source": "srt" if source_kind == "srt" else None,
        "sources": [
            {
                "kind": source_kind,
                "filename": timing_io.basename(filename),
                "hash": digest(raw),
            }
        ],
        "hash": digest(raw),
        "precision": "word"
        if all("word" in e and len(tokens(str(e["word"]))) == 1 for e in entries)
        else "segment-interpolated",
    }


def state(project):
    return project.get("episode") or {
        "brief": DEFAULT_BRIEF,
        "bindings": {},
        "reviews": {},
    }


def import_document(project, role, raw, filename):
    if project.get("is_demo"):
        raise ValueError(
            "Create a new project; do not replace the fictional sample with a real case."
        )
    e = copy.deepcopy(state(project))
    if role == "script":
        parsed = parse_script(raw, filename)
        if e.get("script") and e["script"]["hash"] != parsed["hash"]:
            e["reviews"] = {}
        e["script"] = parsed
        project["script"] = parsed["text"]
        project["script_origin"] = "user"
        project["script_dirty"] = True
        project["script_approved_hash"] = None
    elif role == "guide":
        parsed = parse_guide(raw, filename)
        if parsed["hash"] != (e.get("guide") or {}).get("hash"):
            e["reviews"] = {}
        e["guide"] = parsed
        # Import as unreviewed reference records, not independently checked facts or licenses.
        existing = {s["id"]: s for s in project.get("sources", [])}
        for source in parsed["sources"]:
            if source["id"] not in existing:
                project["sources"].append(
                    {
                        "id": source["id"],
                        "title": source["title"],
                        "url": source["url"] or "",
                        "notes": "Imported from your editing guide; not independently verified by CASEFILE.\n"
                        + source["notes"],
                        "reviewed": False,
                        "origin": "editing-guide",
                    }
                )
            elif existing[source["id"]].get("url") != source.get("url"):
                raise ValueError(
                    "Source ID "
                    + source["id"]
                    + " already means a different source. Import this production pack into a new project."
                )
    elif role == "timings":
        e["timings"] = timing_io.combine(e.get("timings"), parse_timings(raw, filename))
    else:
        raise ValueError("Choose script, guide, or timings explicitly.")
    e.pop("timing_reviewed_digest", None)
    project["episode"] = e
    project["review"] = {**project["review"], "facts": False, "picture": False}
    return project


def input_digest(project):
    e = state(project)
    voice = next(
        (
            a
            for a in project.get("assets", [])
            if a["id"] == project.get("narration_id")
        ),
        None,
    )
    return digest(
        {
            "script": (e.get("script") or {}).get("hash"),
            "guide": (e.get("guide") or {}).get("hash"),
            "timings": (e.get("timings") or {}).get("hash"),
            "voice": (voice or {}).get("id"),
            "duration": (voice or {}).get("duration"),
            "bindings": e.get("bindings", {}),
            "reviews": e.get("reviews", {}),
            "linked_files": [
                {
                    "id": a["id"],
                    "kind": a.get("kind"),
                    "duration": a.get("duration"),
                    "video_duration": a.get("video_duration"),
                    "license": a.get("license", ""),
                }
                for a in project.get("assets", [])
                if a["id"]
                in {b.get("asset_id") for b in e.get("bindings", {}).values()}
            ],
        }
    )


def suggestions(project):
    e = state(project)
    assets = [a for a in project.get("assets", []) if a["kind"] in ("image", "video")]
    result = {}
    for source in (e.get("guide") or {}).get("sources", []):
        sid = source["id"]
        url = urlparse(source.get("url") or "")
        video_id = parse_qs(url.query).get("v", [None])[0]
        basename = url.path.rsplit("/", 1)[-1]
        candidates = [
            a["id"]
            for a in assets
            if re.search(
                r"(?<![A-Za-z0-9])" + re.escape(sid) + r"(?![A-Za-z0-9])",
                a["name"],
                re.I,
            )
            or (video_id and video_id in a["name"])
            or (basename and basename.lower() == a["name"].lower())
        ]
        if len(candidates) == 1:
            result[sid] = candidates[0]
    return result


def source_ready(project, cue):
    e = state(project)
    binding = e.get("bindings", {}).get(cue["source_id"], {})
    review = e.get("reviews", {}).get(cue["id"], {})
    asset = next(
        (a for a in project.get("assets", []) if a["id"] == binding.get("asset_id")),
        None,
    )
    if not asset or asset["kind"] not in ("image", "video"):
        return False, asset, "Upload and link the actual source file."
    if asset["id"] in (project.get("narration_id"), project.get("music_id")):
        return (
            False,
            asset,
            "Keep source footage audio muted. Assign separate finished narration/music files.",
        )
    if not binding.get("rights_confirmed") or not str(asset.get("license", "")).strip():
        return (
            False,
            asset,
            "Record your reuse basis and confirm it for the linked file.",
        )
    if binding.get("rights_notes_hash") != digest(
        str(asset.get("license", "")).strip()
    ):
        return (
            False,
            asset,
            "The reuse notes changed. Reconfirm the recorded basis for this file.",
        )
    if not review.get("reviewed"):
        return (
            False,
            asset,
            "Review this placement, its label, and all Care instructions.",
        )
    if cue.get("requires_stop") and review.get("narration_end") is None:
        return (
            False,
            asset,
            "This placement needs an explicit stop time in your narration.",
        )
    if cue["chapter"] == "chapter-3" and (
        cue["source_id"] == "S02" or binding.get("contains_residence")
    ):
        return False, asset, "Chapter 3 prohibits residential-property imagery."
    if asset["kind"] == "video":
        start, end = review.get("in"), review.get("out")
        if start is None or end is None:
            return (
                False,
                asset,
                "Approve exact in/out points in the uploaded file, not approximate web preview times.",
            )
        if (
            end - start < 0.5
            or start < 0
            or end
            > float(asset.get("video_duration") or asset.get("duration", 0)) + 0.001
        ):
            return (
                False,
                asset,
                "The approved window is outside this uploaded video or shorter than half a second.",
            )
    return (
        True,
        asset,
        "Producer-reviewed file and placement; not independently verified.",
    )


def analyze(project):
    e = state(project)
    script, guide, timing = e.get("script"), e.get("guide"), e.get("timings")
    voice = next(
        (
            a
            for a in project.get("assets", [])
            if a["id"] == project.get("narration_id")
            and a.get("has_audio", a["kind"] == "audio")
            and float(a.get("duration", 0)) > 0
        ),
        None,
    )
    music = next(
        (a for a in project.get("assets", []) if a["id"] == project.get("music_id")),
        None,
    )
    total_words = (script or {}).get("word_count", 0)
    duration = float(
        (voice or {}).get("duration")
        or (timing or {}).get("duration")
        or total_words / 145 * 60
    )
    duration_basis = (
        "recording" if voice else "timing-export" if timing else "script-estimate"
    )
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
            None,
            reference,
            [w["normalized"] for w in timing["words"]],
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
    sections = {
        section["key"]: section for section in (script or {}).get("sections", [])
    }
    last_word = {}
    for cue in (guide or {}).get("cues", []):
        item = copy.deepcopy(cue)
        section = sections.get(cue["chapter"])
        needles = [t[3] for t in tokens(cue["anchor"])]
        matches = []
        if section:
            lo, hi = section["word_start"], section["word_end"]
            for i in range(
                max(lo, last_word.get(cue["chapter"], lo)), hi - len(needles) + 1
            ):
                if reference[i : i + len(needles)] == needles:
                    matches.append(i)
        idx = matches[0] if len(matches) == 1 else None
        review = e.get("reviews", {}).get(cue["id"], {})
        item.update(
            matched=idx is not None,
            ambiguous=len(matches) > 1,
            word_index=idx,
            review=review,
        )
        if idx is not None:
            last_word[cue["chapter"]] = idx + 1
            if "narration_start" in review:
                points[idx] = review["narration_start"]
            item["timing_review_required"] = (
                idx in candidates and "narration_start" not in review
            )
            item["timing_source"] = (
                "manual"
                if "narration_start" in review
                else "word boundary; text review"
                if idx in candidates
                else "provided word boundary"
                if alignment and idx in timed
                else "timing file (segment estimate)"
                if idx in timed and timing.get("precision") == "segment-interpolated"
                else "timing file"
                if idx in timed
                else "estimated"
            )
        ready, asset, message = source_ready(project, cue)
        item.update(
            ready=ready, asset_id=(asset or {}).get("id"), status_detail=message
        )
        placements.append(item)
    ordered = sorted(points.items())
    if any(not math.isfinite(t) or t < 0 or t > duration for _, t in ordered) or any(
        b[1] <= a[1] for a, b in zip(ordered, ordered[1:])
    ):
        errors.append(
            "Narration timing anchors are out of order or outside the audio duration. Correct the manual positions or the supplied timing file."
        )
    clock = [0.0] * len(ts)
    for (a, ta), (b, tb) in zip(ordered, ordered[1:]):
        for i in range(a, b):
            clock[i] = ta + (tb - ta) * (i - a) / max(1, b - a)
    for item in placements:
        idx = item["word_index"]
        item["narration_start"] = clock[idx] if idx is not None else None
        stop = item["review"].get("narration_end")
        if (
            stop is not None
            and idx is not None
            and (stop < clock[idx] + 0.5 or stop > duration + 1 / FPS)
        ):
            errors.append(
                f"{item['id']}: the visual stop must be after its cue by at least half a second, and within the narration."
            )
    matched = sum(c["matched"] for c in placements)
    if script and guide and matched != len(placements):
        errors.append(
            "Some At phrases are missing or ambiguous within their chapter. Do not guess their placement."
        )
    starts = [c["narration_start"] for c in placements if c["matched"]]
    if any(v >= duration for v in starts) or starts != sorted(starts):
        errors.append(
            "Narration cue times are out of order or outside the audio duration."
        )
    if (
        timing
        and voice
        and timing.get("source_kind") == "capcut"
        and abs(timing["duration"] - duration) > 0.05
    ):
        errors.append(
            "The recording duration differs from the CapCut narration timeline by more than 50 ms. Upload the exact matching recording or re-export its timings; no offset/stretch was guessed."
        )
    if timing and voice and max(w["end"] for w in timing["words"]) > duration + 0.05:
        errors.append("The timing file extends beyond the selected narration.")
    used = {c["source_id"] for c in placements}
    assets = {
        a["id"] for a in project.get("assets", []) if a["kind"] in ("image", "video")
    }
    bindings = e.get("bindings", {})
    return {
        "has_script": bool(script),
        "has_guide": bool(guide),
        "has_voice": bool(voice),
        "voice_id": (voice or {}).get("id"),
        "has_music": bool(music),
        "word_count": total_words,
        "duration": duration,
        "duration_estimated": not bool(voice),
        "duration_basis": duration_basis,
        "timing_precision": (timing or {}).get("precision"),
        "transcript_reviewed": e.get("transcript_reviewed_digest")
        == input_digest(project),
        "imported_caption_count": len((timing or {}).get("captions", [])),
        "transcript_comparison": {
            k: v for k, v in (alignment or {}).items() if k != "anchors"
        },
        "timing_candidate_cues": [
            c["id"] for c in placements if c.get("timing_review_required")
        ],
        "sections": (script or {}).get("sections", []),
        "placements": placements,
        "cue_count": len(placements),
        "matched_cues": matched,
        "ready_cues": sum(c["ready"] for c in placements),
        "source_count": len((guide or {}).get("sources", [])),
        "used_source_count": len(used),
        "linked_source_count": sum(
            bindings.get(s, {}).get("asset_id") in assets for s in used
        ),
        "suggestions": suggestions(project),
        "timing_word_match_percent": word_match_percent,
        "timing_reviewed": e.get("timing_reviewed_digest") == input_digest(project),
        "plan_current": bool(
            e.get("plan")
            and e["plan"].get("input_digest") == input_digest(project)
            and e["plan"].get("timeline_digest")
            == timeline_digest(project.get("scenes", []))
        ),
        "errors": errors,
        "boundaries": (guide or {}).get("boundaries"),
        "brief": e.get("brief", DEFAULT_BRIEF),
        "rights_disclaimer": "Source links and imported research claims are not permissions or independent verification. Source audio stays muted.",
        "word_clock": clock,
    }


def review_cue(project, cue_id, fields):
    e = copy.deepcopy(state(project))
    cue = next(
        (c for c in (e.get("guide") or {}).get("cues", []) if c["id"] == cue_id), None
    )
    if not cue:
        raise ValueError("Unknown guide placement.")
    allowed = {"reviewed", "in", "out", "narration_start", "narration_end"}
    if set(fields) - allowed:
        raise ValueError("Unsupported placement review field.")
    existing = e.setdefault("reviews", {}).get(cue_id, {})
    for key, value in fields.items():
        if key == "reviewed":
            existing[key] = value is True
        elif value is None:
            existing.pop(key, None)
        else:
            v = float(value)
            if not math.isfinite(v) or v < 0 or v > 21600:
                raise ValueError("Timestamps must be between zero and six hours.")
            existing[key] = v
    e["reviews"][cue_id] = existing
    project["episode"] = e
    if existing.get("reviewed"):
        okay, _, message = source_ready(project, cue)
        if not okay:
            raise ValueError(message)
    e.pop("timing_reviewed_digest", None)
    project["review"]["picture"] = False
    return project


def bind_source(project, source_id, fields):
    e = copy.deepcopy(state(project))
    if source_id not in {s["id"] for s in (e.get("guide") or {}).get("sources", [])}:
        raise ValueError("Unknown guide source.")
    if set(fields) - {"asset_id", "rights_confirmed", "license", "contains_residence"}:
        raise ValueError("Unsupported source binding field.")
    binding = e.setdefault("bindings", {}).get(source_id, {})
    if "asset_id" in fields:
        a = next(
            (
                a
                for a in project.get("assets", [])
                if a["id"] == fields["asset_id"] and a["kind"] in ("image", "video")
            ),
            None,
        )
        if fields["asset_id"] is not None and not a:
            raise ValueError("Choose an uploaded image/video file.")
        if binding.get("asset_id") != fields["asset_id"]:
            binding = {"asset_id": fields["asset_id"], "rights_confirmed": False}
            for cue in e["guide"]["cues"]:
                if cue["source_id"] == source_id:
                    e.setdefault("reviews", {}).pop(cue["id"], None)
    a = next(
        (a for a in project.get("assets", []) if a["id"] == binding.get("asset_id")),
        None,
    )
    if "license" in fields:
        if not a:
            raise ValueError("Link a source file before recording its rights notes.")
        a["license"] = str(fields["license"])[:10000]
        binding["rights_confirmed"] = False
    if "rights_confirmed" in fields:
        if fields["rights_confirmed"] and (
            not a or not str(a.get("license", "")).strip()
        ):
            raise ValueError(
                "Record the permission/license or reviewed reuse basis before confirming it."
            )
        binding["rights_confirmed"] = fields["rights_confirmed"] is True
        if binding["rights_confirmed"]:
            binding["rights_notes_hash"] = digest(str(a.get("license", "")).strip())
    if "contains_residence" in fields:
        binding["contains_residence"] = fields["contains_residence"] is True
    e["bindings"][source_id] = binding
    e.pop("timing_reviewed_digest", None)
    project["episode"] = e
    project["review"]["rights"] = False
    project["review"]["picture"] = False
    return project


def build(project, allow_placeholders=False):
    report = analyze(project)
    e = state(project)
    if not report["has_script"] or not report["has_guide"]:
        raise ValueError(
            "Import the narration script and editing guide in their separate cards first."
        )
    if report["errors"]:
        raise ValueError(" ".join(report["errors"]))
    if report["cue_count"] != report["ready_cues"] and not allow_placeholders:
        raise ValueError(
            "Some source files or placement approvals are missing. Resolve them or explicitly allow marked gaps for a review-only plan."
        )
    target = math.ceil(report["duration"] * FPS - 1e-8)
    if target < 12 or target > 5400 * FPS:
        raise ValueError(
            "The episode duration must be between half a second and 90 minutes."
        )
    script = e["script"]
    ts = tokens(script["text"])
    N = len(ts)
    # Use one monotone word clock for cue and chapter positions. Chapter estimates
    # must never compete with supplied word/segment times or manual anchors.
    clock = report["word_clock"]
    events = {0: {"chapter": script["sections"][0], "cue": None}}
    for section in script["sections"]:
        frame = round(clock[section["word_start"]] * FPS)
        events[frame] = {"chapter": section, "cue": None}
    for cue in report["placements"]:
        frame = round(cue["narration_start"] * FPS)
        section = next(s for s in script["sections"] if s["key"] == cue["chapter"])
        if frame in events and events[frame].get("cue"):
            raise ValueError(
                "Two guide cues have the same frame. Set distinct narration start times."
            )
        events[frame] = {"chapter": section, "cue": cue}
    boundaries = sorted(set(events) | {target})
    scenes = []
    gap_frames = 0

    def push(start, end, chapter, cue, asset=None, trim=0, source_label=""):
        nonlocal gap_frames
        if end <= start:
            return
        cursor = start
        while cursor < end:
            stop = min(end, cursor + 30 * FPS)
            indices = [i for i, t in enumerate(clock) if cursor / FPS <= t < stop / FPS]
            if indices:
                a, b = indices[0], indices[-1]
                text = script["text"][
                    (0 if a == 0 else ts[a][1]) : (
                        ts[b + 1][1] if b + 1 < N else len(script["text"])
                    )
                ].strip()
            else:
                text = ""
            scene = {
                "id": store.uid(),
                "title": (
                    cue["anchor"][:75]
                    if cue
                    else "Visual needed before the next guide cue"
                ),
                "chapter": chapter["title"],
                "narration": text,
                "source_ids": [],
                "duration": (stop - cursor) / FPS,
                "audio_start": cursor / FPS,
                "audio_duration": (stop - cursor) / FPS,
                "asset_id": asset["id"] if asset else None,
                "trim_start": trim + (cursor - start) / FPS
                if asset and asset["kind"] == "video"
                else 0,
                "motion": "slow-zoom" if asset and asset["kind"] == "image" else "none",
                "transition": "cut",
                "show_title": False,
                "timing": "imported-captions"
                if (e.get("timings") or {}).get("captions")
                else "estimated",
                "captions_exact": bool((e.get("timings") or {}).get("captions")),
                "captions": [
                    {
                        "start": max(c["start"], cursor / FPS) - cursor / FPS,
                        "end": min(c["end"], stop / FPS) - cursor / FPS,
                        "text": c["text"],
                    }
                    for c in (e.get("timings") or {}).get("captions", [])
                    if c["start"] < stop / FPS and c["end"] > cursor / FPS
                ],
                "guide_cue_id": cue["id"] if cue else None,
                "guide_source_id": cue["source_id"] if cue else None,
                "guide_gap": not bool(asset),
                "source_label": source_label if asset else "",
            }
            scenes.append(scene)
            if not asset:
                gap_frames += stop - cursor
            cursor = stop

    for start, end in zip(boundaries, boundaries[1:]):
        event = events[start]
        cue = event["cue"]
        chapter = event["chapter"]
        if not cue or not cue["ready"]:
            push(start, end, chapter, cue)
            continue
        asset = next(a for a in project["assets"] if a["id"] == cue["asset_id"])
        review = cue["review"]
        visual_end = end
        if review.get("narration_end") is not None:
            visual_end = min(end, round(review["narration_end"] * FPS))
        trim = 0
        if asset["kind"] == "video":
            trim = review["in"]
            visual_end = min(
                visual_end, start + math.floor((review["out"] - trim) * FPS + 0.001)
            )
        if visual_end - start < 12:
            push(start, end, chapter, cue)
            continue
        push(start, visual_end, chapter, cue, asset, trim, cue["label"])
        push(visual_end, end, chapter, cue)
    if len(scenes) > 400:
        raise ValueError(
            "This plan exceeds 400 scenes. Shorten the material or revise the guide."
        )
    assert sum(round(s["duration"] * FPS) for s in scenes) == target
    if [t[3] for t in tokens(" ".join(s["narration"] for s in scenes))] != [
        t[3] for t in ts
    ]:
        raise ValueError(
            "The planned captions do not preserve every narration word in order. Review the cue timings."
        )
    if gap_frames and not allow_placeholders:
        raise ValueError(
            "The approved clips do not cover the full timeline. Supply more coverage or explicitly allow marked gaps for a review-only plan."
        )
    plan = {
        "input_digest": input_digest(project),
        "timeline_digest": timeline_digest(scenes),
        "built_at": store.now(),
        "duration": target / FPS,
        "scene_count": len(scenes),
        "gap_seconds": gap_frames / FPS,
        "visual_seconds": (target - gap_frames) / FPS,
        "preserves_narration": True,
        "source_audio": "muted",
        "timing": "provided caption timestamps; guide cue review required"
        if (e.get("timings") or {}).get("captions")
        else "guide anchors; caption timing remains estimated",
        "has_voice": report["has_voice"],
    }
    project["episode"] = {**e, "plan": plan}
    project["scenes"] = scenes
    project["script_dirty"] = False
    project["review"]["picture"] = False
    return plan


def timeline_digest(scenes):
    # Frame-quantized times survive the general editor's millisecond sanitation.
    # Cosmetic look changes and factual source annotations are still permitted.
    result = []
    for scene in scenes:
        item = {
            k: scene.get(k)
            for k in (
                "asset_id",
                "guide_cue_id",
                "guide_source_id",
                "source_label",
                "guide_gap",
                "chapter",
                "transition",
            )
        }
        for key in ("guide_cue_id", "guide_source_id", "source_label"):
            item[key] = str(item[key] or "")
        item["narration"] = " ".join(scene.get("narration", "").split())
        for k in ("duration", "audio_start", "audio_duration"):
            item[k] = round(float(scene.get(k, 0)) * FPS)
        item["trim_start"] = round(float(scene.get("trim_start", 0)), 4)
        if scene.get("captions_exact"):
            item["captions_exact"] = True
            item["captions"] = [
                {
                    "start": round(float(c["start"]), 6),
                    "end": round(float(c["end"]), 6),
                    "text": c["text"],
                }
                for c in scene.get("captions", [])
            ]
        result.append(item)
    return digest(result)


def issues(project):
    e = project.get("episode")
    if not e or not e.get("guide"):
        return []
    result = []

    def add(code, title, detail, blocks_draft=False):
        result.append(
            {
                "code": code,
                "title": title,
                "detail": detail,
                "blocks_draft": blocks_draft,
            }
        )

    report = analyze(project)
    if not report["has_voice"]:
        add(
            "episode_voice_missing",
            "Upload your finished narration before rendering",
            "The script can produce an estimated plan, not a silent documentary. Assign the audio in Episode setup; it will not be regenerated.",
            True,
        )
    if report["errors"]:
        add(
            "episode_timing_error",
            "Guide matching or timing needs correction",
            " ".join(report["errors"]),
            True,
        )
    if project.get("narration_id") and project.get("narration_id") == project.get(
        "music_id"
    ):
        add(
            "episode_audio_roles",
            "Voice and music must be separate files",
            "Assign each track to its own role in Episode setup.",
            True,
        )
    bound_ids = {b.get("asset_id") for b in e.get("bindings", {}).values()} - {None}
    if bound_ids & {project.get("narration_id"), project.get("music_id")}:
        add(
            "episode_source_audio_role",
            "A source file is assigned to a voice/music role",
            "Source audio must stay muted in this workflow. Assign your separate finished narration and background music.",
            True,
        )
    if e.get("plan") and e["plan"].get("timeline_digest") != timeline_digest(
        project.get("scenes", [])
    ):
        add(
            "episode_timeline_changed",
            "Guide cuts changed after planning",
            "Rebuild the episode plan. Manual shot moves/trims cannot bypass approved cue positions, care rules, or the full-narration guarantee.",
            True,
        )
    cursor = 0.0
    continuous = bool(project.get("scenes"))
    for scene in project.get("scenes", []):
        duration = round(float(scene["duration"]) * FPS) / FPS
        continuous = (
            continuous
            and abs(float(scene.get("audio_start", -1)) - cursor) < 0.003
            and abs(float(scene.get("audio_duration", 0)) - duration) < 0.003
        )
        cursor += duration
    if report["has_voice"] and (
        not continuous
        or cursor < report["duration"] - 0.001
        or cursor > report["duration"] + 1 / FPS + 0.002
    ):
        add(
            "episode_narration_continuity",
            "The full original narration is not preserved",
            "Audio slices must start at zero, stay contiguous and in order, and cover the complete recording. Rebuild the guided plan.",
            True,
        )
    if not e.get("plan"):
        add(
            "episode_plan_missing",
            "Guide timeline not built",
            "Use Episode setup to build the source-aware timeline.",
            True,
        )
    elif e["plan"].get("input_digest") != input_digest(project):
        add(
            "episode_plan_stale",
            "Guide setup changed after the plan",
            "Rebuild the guided timeline before rendering the changes.",
            True,
        )
    from editorial import strip_references

    if e.get("script") and [
        t[3] for t in tokens(strip_references(project.get("script", "")))
    ] != [t[3] for t in tokens(e["script"]["text"])]:
        add(
            "episode_script_changed",
            "Script no longer matches the imported narration script",
            "Re-import the matching script and rebuild; CASEFILE will not silently rewrite your voice.",
            True,
        )
    if report.get("transcript_comparison", {}).get("difference_spans") and e.get(
        "transcript_reviewed_digest"
    ) != input_digest(project):
        add(
            "episode_transcript_differences",
            "Timing transcript differs from your script",
            f"{report['transcript_comparison']['difference_spans']} comparison spans need review (not confirmed spoken errors). Names, numbers and {len(report['timing_candidate_cues'])} cue-start substitution candidates must be checked against the audio. No text was automatically corrected.",
        )
    if e.get("timing_reviewed_digest") != input_digest(project):
        add(
            "episode_timing_review",
            "Narration cue positions need review",
            "Check guide cuts against your actual recording. Script-only timings are estimates; optional word/SRT timings help but still need review.",
        )
    gaps = sum(
        s["duration"] for s in project.get("scenes", []) if not s.get("asset_id")
    )
    if gaps:
        add(
            "episode_visual_gaps",
            "Guide footage still has gaps",
            f"{gaps:.1f} seconds need usable files, reviewed ranges, or an explicitly revised guide. Drafts show marked cards, not random replacement footage.",
        )
    cues = {c["id"]: c for c in e["guide"]["cues"]}
    for scene in project.get("scenes", []):
        if not scene.get("asset_id"):
            continue
        cue = cues.get(scene.get("guide_cue_id"))
        if not cue:
            add(
                "episode_unguided_visual",
                "A visual is not linked to a guide cue",
                "Return to Episode setup; no arbitrary footage substitution in this guide-driven project.",
                True,
            )
            break
        ready, asset, message = source_ready(project, cue)
        if not ready or not asset or asset["id"] != scene.get("asset_id"):
            add(
                "episode_unapproved_source",
                "A scene uses an unapproved guide file",
                message,
                True,
            )
            break
        if scene.get("source_label") != cue["label"]:
            add(
                "episode_source_label",
                "Source/date label changed",
                "Rebuild or restore the guide label before rendering this material.",
                True,
            )
            break
        if asset["kind"] == "video":
            review = e["reviews"][cue["id"]]
            start = float(scene.get("trim_start", 0))
            end = start + float(scene["duration"])
            if start < review["in"] - 0.025 or end > review["out"] + 0.025:
                add(
                    "episode_source_bounds",
                    "A cut exceeds its approved source window",
                    "Short clips cannot be silently looped or extended beyond the reviewed range.",
                    True,
                )
                break
    return result


def markdown(project):
    r = analyze(project)
    e = state(project)
    text = f"# Episode setup — {project['title']}\n\n{r['word_count']} spoken words · {r['matched_cues']}/{r['cue_count']} cue matches · {r['source_count']} reference links · {r['used_source_count']} sources used by placements\n\n"
    text += "Your original narration is the audio master. Source audio is muted. No URLs were downloaded, rights cleared, or case facts independently verified.\n\n"
    assets = {a["id"]: a for a in project.get("assets", [])}
    voice = assets.get(project.get("narration_id"), {})
    music = assets.get(project.get("music_id"), {})
    text += f"Narration: {voice.get('name', 'NOT SUPPLIED')} · {r['duration_basis']} {r['duration']:.2f}s\n\nMusic: {music.get('name', 'not assigned')} · starting mix level {project.get('music_volume', 0.12) * 100:g}%\n\n"
    timing = e.get("timings") or {}
    if timing:
        files = ", ".join(source["filename"] for source in timing.get("sources", []))
        text += f"## Imported timing pack\n\nFiles: {files or timing.get('filename')}\n\nPrecision: {timing.get('precision')} · {len(timing.get('words', []))} timing entries · {r['imported_caption_count']} supplied caption blocks. Captions remain on the same clock when hidden.\n\n"
        if timing.get("source_kind") == "capcut":
            text += f"CapCut timeline: {timing['duration']:.6f}s at {timing['fps']:g} fps. The output uses {FPS} fps; cuts are rounded to the nearest output frame. Grouped interiors have no supplied word starts; any such cue is estimated, never labeled exact.\n\nReferenced audio (not embedded): {timing.get('audio_reference_filename') or 'not named'}. Audio matching still requires the actual recording and review; matching duration alone is not acoustic verification.\n\n"
            text += f"Normalized text match: {r['timing_word_match_percent']:g}%. Comparison spans requiring review: {r['transcript_comparison'].get('difference_spans', 0)} (not confirmed spoken errors). Cue-start substitution candidates: {', '.join(r['timing_candidate_cues']) or 'none'}. No caption, script, or voice text was automatically corrected.\n\n"
            if timing.get("caption_end_hold_difference_count"):
                text += f"Continuous SRT caption ends retained: {timing['caption_end_hold_difference_count']} differ from native text-segment ends; matching starts were preserved without an offset.\n\n"
    plan = e.get("plan")
    if plan:
        text += f"Plan: {plan['scene_count']} scenes · {plan['duration']:.2f}s · {plan['gap_seconds']:.2f}s marked visual gaps · {'current' if r['plan_current'] else 'STALE: rebuild required'}\n\n"
    text += (
        "## Standing boundaries\n\n"
        + str(r["boundaries"] or "Import an editing guide.")
        + "\n\n"
    )
    text += (
        "## Editing brief (recorded for the producer, not an arbitrary executable prompt)\n\n"
        + e.get("brief", DEFAULT_BRIEF)
        + "\n\n"
    )
    for c in r["placements"]:
        t = (
            f"{c['narration_start']:.2f}s"
            if c["narration_start"] is not None
            else "UNMATCHED"
        )
        file = assets.get(c.get("asset_id"), {})
        review = c["review"]
        window = (
            f"{review['in']:.3f}s–{review['out']:.3f}s in the uploaded file"
            if file.get("kind") == "video"
            and review.get("in") is not None
            and review.get("out") is not None
            else "not applicable (image)"
            if file.get("kind") == "image"
            else "NOT APPROVED"
        )
        stop = (
            f"{review['narration_end']:.3f}s"
            if review.get("narration_end") is not None
            else "next guide/chapter boundary or clip end; see Care"
        )
        text += f"## {c['id']} · {c['chapter_label']} · {c['source_id']}\n\nAt: {c['anchor']}\n\nNarration position: {t} ({c.get('timing_source', 'unmatched')}); visual stop: {stop}\n\nShow: {c['show']}\n\nLabel: {c['label']}\n\nCare: {c['care']}\n\nUploaded file: {file.get('name', 'NOT LINKED')}\n\nApproved local window: {window}\n\nStatus: {c['status_detail']}\n\nRecorded reuse basis (producer supplied, not app clearance): {file.get('license') or 'NOT RECORDED'}\n\nReference: {c.get('reference_url') or ''}\n\n"
    return text
