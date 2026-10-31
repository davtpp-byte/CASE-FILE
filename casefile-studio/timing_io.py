"""Sanitized CapCut timing adapter and explicit, reviewable text alignment.

Reads local exports only. Never reads referenced media paths or retains device
IDs, material IDs, absolute paths, credentials, or the full CapCut project.
A supplied timed unit may contain several words: its interior starts are UNKNOWN.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import math
import re

NUMBER_WORDS = dict(
    zip(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety".split(),
        "0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 30 40 50 60 70 80 90".split(),
    )
)


def comparison_tokens(text):
    out = []
    # Preserve character coordinates. Only comparison changes number/ordinal
    # notation; the script, captions and voice are NEVER rewritten here.
    for m in re.finditer(
        r"[^\W\d_]+(?:[’'][^\W\d_]+)*|\d+(?:st|nd|rd|th)?", text, re.UNICODE
    ):
        value = m[0].lower().replace("’", "'")
        value = re.sub(r"^(\d+)(?:st|nd|rd|th)$", r"\1", value)
        out.append(
            {
                "value": NUMBER_WORDS.get(value, value),
                "raw": m[0],
                "char_start": m.start(),
                "char_end": m.end(),
            }
        )
    return out


def basename(value):
    return str(value).replace("\\", "/").rsplit("/", 1)[-1][:200]


def seconds(value, scale=1):
    try:
        result = float(value) / scale
    except (TypeError, ValueError, OverflowError):
        raise ValueError("CapCut timestamps must be numbers.")
    if not math.isfinite(result) or not 0 <= result <= 21600:
        raise ValueError("CapCut timestamps must be finite and within six hours.")
    return result


def is_capcut(data):
    return (
        isinstance(data, dict)
        and isinstance(data.get("tracks"), list)
        and isinstance(data.get("materials"), dict)
    )


def parse_capcut(data, filename, raw_hash):
    fps = float(data.get("fps", 30))
    if not math.isfinite(fps) or not 1 <= fps <= 240:
        raise ValueError("Unsupported CapCut frame rate.")
    frame = 1 / fps
    tracks = data["tracks"]
    if not all(
        isinstance(t, dict)
        and isinstance(t.get("segments", []), list)
        and all(isinstance(segment, dict) for segment in t.get("segments", []))
        for t in tracks
    ):
        raise ValueError("Malformed CapCut track/segment structure.")
    if not all(
        isinstance(data["materials"].get(key, []), list)
        and all(isinstance(m, dict) for m in data["materials"].get(key, []))
        for key in ("audios", "texts")
    ):
        raise ValueError("Malformed CapCut materials.")
    if len(tracks) > 2000:
        raise ValueError("Too many CapCut tracks.")
    audio_segments = [
        s for t in tracks if t.get("type") == "audio" for s in t.get("segments", [])
    ]
    if len(audio_segments) != 1:
        raise ValueError(
            "Use a narration-only CapCut draft with one continuous audio segment; music/source mixes cannot establish the narration clock."
        )
    audio = audio_segments[0]
    target = audio["target_timerange"]
    source = audio.get("source_timerange") or {}
    if (
        seconds(target["start"], 1e6) > 0.000001
        or seconds(source.get("start", 0), 1e6) > 0.000001
        or float(audio.get("speed", 1)) != 1
        or audio.get("reverse")
    ):
        raise ValueError(
            "CapCut narration must start at zero, untrimmed, at normal speed. Export timings for the exact final recording."
        )
    duration = seconds(target["duration"], 1e6)
    if duration <= 0:
        raise ValueError("The CapCut narration duration is empty.")
    audio_material = next(
        (
            m
            for m in data["materials"].get("audios", [])
            if m.get("id") == audio.get("material_id")
        ),
        {},
    )
    reference_name = basename(
        audio_material.get("path") or audio_material.get("name") or ""
    )
    text_materials = {m["id"]: m for m in data["materials"].get("texts", [])}
    segments = sorted(
        [s for t in tracks if t.get("type") == "text" for s in t.get("segments", [])],
        key=lambda s: s["target_timerange"]["start"],
    )
    if not segments or len(segments) > 20000:
        raise ValueError("No CapCut caption segments, or more than 20,000 segments.")
    units, captions = [], []
    ignored, rounding_count, max_overrun = 0, 0, 0.0
    for segment in segments:
        material = text_materials.get(segment.get("material_id"), {})
        words = material.get("words") or {}
        if not isinstance(words, dict):
            raise ValueError("Malformed CapCut word arrays.")
        if not words.get("text"):
            ignored += 1
            continue
        if float(segment.get("speed", 1)) != 1 or segment.get("reverse"):
            raise ValueError(
                "Retimed/reversed CapCut captions need a dedicated time transform; they are not supported."
            )
        tr = segment["target_timerange"]
        start = seconds(tr["start"], 1e6)
        span = seconds(tr["duration"], 1e6)
        end = start + span
        if span <= 0 or end > duration + frame + 0.001:
            raise ValueError("CapCut caption range is outside the narration timeline.")
        if captions and start < captions[-1]["end"] - 0.001:
            raise ValueError(
                "Overlapping CapCut caption tracks need review; use a single caption track."
            )
        content = material.get("content", "")
        content = json.loads(content) if isinstance(content, str) else content
        if not isinstance(content, dict):
            raise ValueError("Malformed CapCut caption content.")
        text = str(content.get("text", "")).strip()
        if not text or len(text) > 12000:
            raise ValueError("A CapCut caption is empty or too long.")
        arrays = [words.get(k, []) for k in ("text", "start_time", "end_time")]
        if (
            not all(isinstance(a, list) for a in arrays)
            or len({len(a) for a in arrays}) != 1
        ):
            raise ValueError(
                "CapCut word text/start/end arrays have different lengths."
            )
        caption_number = len(captions) + 1
        for value, a, b in zip(*arrays):
            value = str(value).strip()
            if not value:
                continue  # CapCut includes zero-length spacer entries.
            if len(value) > 12000:
                raise ValueError("A CapCut timed text unit is too long.")
            lo, hi = seconds(a, 1000), seconds(b, 1000)
            if hi <= lo or hi > span + frame + 0.001 or lo > span + frame:
                raise ValueError(
                    "A CapCut word range is outside its caption; no timestamp interpolation was applied."
                )
            if units and start + lo < units[-1]["start"] - 0.000001:
                raise ValueError("CapCut timed units are not in timeline order.")
            overrun = max(0, hi - span)
            rounding_count += overrun > 0.001
            max_overrun = max(max_overrun, overrun)
            # Retain raw provided unit bounds, including <= one frame of caption
            # rounding. Do not clamp them or manufacture interior word starts.
            units.append(
                {
                    "word": value,
                    "text": value,
                    "normalized": re.sub(r"[^\w]", "", value.lower().replace("’", "'")),
                    "start": start + lo,
                    "end": start + hi,
                    "caption": caption_number,
                    "start_exact": True,
                }
            )
        captions.append({"start": start, "end": end, "text": text})
    if not units or len(units) > 100000:
        raise ValueError(
            "No usable CapCut word timing arrays, or more than 100,000 timed units."
        )
    if units[-1]["end"] > duration + frame + 0.001:
        raise ValueError("CapCut word timings exceed the narration.")
    return {
        "filename": basename(filename),
        "words": units,
        "units": units,
        "captions": captions,
        "native_captions": captions,
        "captions_source": "capcut",
        "source_kind": "capcut",
        "precision": "provided-timed-units",
        "duration": duration,
        "fps": fps,
        "hash": raw_hash,
        "sources": [
            {"kind": "capcut", "filename": basename(filename), "hash": raw_hash}
        ],
        "audio_reference_filename": reference_name,
        "audio_verified": False,
        "ignored_untimed_text_segments": ignored,
        "grouped_units": sum(len(comparison_tokens(u["text"])) > 1 for u in units),
        "word_end_frame_rounding_count": rounding_count,
        "maximum_word_end_overrun_ms": round(max_overrun * 1000, 6),
    }


def combine(existing, incoming):
    """Pair matching CapCut word units with SRT caption holds in either order.

    Caption start agreement establishes compatibility, NOT acoustic verification.
    Different caption ends (continuous SRT holds) remain exactly as supplied.
    """
    if not existing or not incoming:
        return incoming
    if (
        existing.get("source_kind") == incoming.get("source_kind") == "capcut"
        and existing.get("captions_source") == "srt"
    ):
        srt_source = next(s for s in existing["sources"] if s["kind"] == "srt")
        return combine(
            incoming,
            {
                "source_kind": "srt",
                "captions": existing["captions"],
                "filename": srt_source["filename"],
                "sources": [srt_source],
            },
        )
    kinds = {existing.get("source_kind"), incoming.get("source_kind")}
    if kinds != {"capcut", "srt"}:
        return incoming
    capcut, srt = (
        (existing, incoming)
        if existing["source_kind"] == "capcut"
        else (incoming, existing)
    )
    a, b = capcut["native_captions"], srt["captions"]
    if len(a) != len(b) or any(
        abs(x["start"] - y["start"]) > 0.002 for x, y in zip(a, b)
    ):
        raise ValueError(
            "These CapCut/SRT files have different caption starts or counts. Remove the old timing pack first, or upload the matching exports; no global offset was guessed."
        )
    if b[-1]["end"] > capcut["duration"] + 0.05:
        raise ValueError("The SRT ends outside the CapCut narration timeline.")
    result = {
        **capcut,
        "captions": b,
        "captions_source": "srt",
        "filename": capcut["filename"] + " + " + srt["filename"],
        "sources": capcut["sources"][:1] + srt["sources"][:1],
        "caption_text_difference_count": sum(
            x["text"] != y["text"] for x, y in zip(a, b)
        ),
        "caption_end_hold_difference_count": sum(
            abs(x["end"] - y["end"]) > 0.002 for x, y in zip(a, b)
        ),
        "maximum_caption_end_hold_difference_seconds": max(
            abs(x["end"] - y["end"]) for x, y in zip(a, b)
        ),
    }
    result["hash"] = hashlib.sha256(
        json.dumps([s["hash"] for s in result["sources"]]).encode()
    ).hexdigest()
    return result


def align(script_text, script_words, timing):
    """Return exact lexical matches and explicitly marked substitution candidates.

    Sequence alignment proposes positions; it is not forced acoustic alignment.
    Only the FIRST token in a provided unit can have a supplied exact start.
    """
    reference = comparison_tokens(script_text)
    transcript = []
    for unit in timing["units"]:
        for n, t in enumerate(comparison_tokens(unit["text"])):
            transcript.append(
                {
                    **t,
                    "start": unit["start"],
                    "end": unit["end"],
                    "caption": unit["caption"],
                    "provided_start": n == 0,
                }
            )
    a = [t["value"] for t in reference]
    b = [t["value"] for t in transcript]
    matches, candidates, differences = {}, {}, []
    for tag, lo, hi, j, k in difflib.SequenceMatcher(
        None, a, b, autojunk=False
    ).get_opcodes():
        if tag == "equal":
            matches.update({lo + n: j + n for n in range(hi - lo)})
            continue
        differences.append(
            {
                "operation": tag,
                "script": " ".join(t["raw"] for t in reference[lo:hi]),
                "transcript": " ".join(t["raw"] for t in transcript[j:k]),
                "caption_number": transcript[j]["caption"]
                if j < len(transcript)
                else None,
                "start": transcript[j]["start"] if j < len(transcript) else None,
            }
        )
        if hi - lo == k - j:
            candidates.update({lo + n: j + n for n in range(hi - lo)})
    by_char = {t["char_start"]: i for i, t in enumerate(reference)}
    anchors = {}
    for word_index, word in enumerate(script_words):
        i = by_char.get(word[1])
        j = matches.get(i)
        review = False
        if j is None:
            j = candidates.get(i)
            review = j is not None
        if j is not None:
            t = transcript[j]
            if t["provided_start"]:
                anchors[word_index] = {
                    "start": t["start"],
                    "review_required": review,
                    "caption": t["caption"],
                    "transcript_token": t["raw"],
                }
    return {
        "anchors": anchors,
        "match_percent": round(len(matches) / max(1, len(a)) * 100, 1),
        "differences": differences,
        "difference_spans": len(differences),
        "comparison": "Normalized text alignment; not acoustic verification.",
    }
