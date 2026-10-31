"""Deterministic editorial checks, reference preservation, and publication notes.

A check records structure and producer attestations, not whether a case claim is true.
"""

from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REFERENCE = re.compile(r"\[\s*(S\d+(?:(?:\s*[,;]\s*|\s+)S?\d+)*)\s*\]", re.I)
UNRESOLVED = re.compile(
    r"\[(?:NEEDS?\s+SOURCE|SOURCE\s+NEEDED|UNVERIFIED|FACT\s*CHECK|TODO|CITATION\s+NEEDED)(?:[^\]]*)\]",
    re.I,
)


def source_ids(text):
    found = []
    for group in REFERENCE.findall(text or ""):
        for number in re.findall(r"\d+", group):
            ref = "S" + number
            if ref not in found:
                found.append(ref)
    return found


def strip_references(text):
    return REFERENCE.sub("", text or "").strip()


def fingerprint(text):
    return hashlib.sha256(" ".join((text or "").split()).encode()).hexdigest()


def script_from_scenes(scenes):
    paragraphs = []
    for scene in scenes:
        text = strip_references(scene.get("narration", ""))
        refs = list(
            dict.fromkeys(
                scene.get("source_ids", []) + source_ids(scene.get("narration", ""))
            )
        )
        paragraphs.append(
            (
                text + (" " + " ".join(f"[{ref}]" for ref in refs) if refs else "")
            ).strip()
        )
    return "\n\n".join(paragraphs)


def approval_fingerprint(project):
    """Bind approval to both the text and its cited source context, including undo."""
    refs = set(source_ids(project.get("script", "")))
    sources = [
        s
        for s in project.get("sources", [])
        if s.get("id") in refs or (not refs and s.get("reviewed"))
    ]
    context = [
        {k: s.get(k) for k in ("id", "title", "url", "notes", "reviewed")}
        for s in sorted(sources, key=lambda s: s["id"])
    ]
    return fingerprint(
        json.dumps(
            {"script": " ".join(project.get("script", "").split()), "sources": context},
            sort_keys=True,
            ensure_ascii=False,
        )
    )


def script_approved(project):
    return project.get("script_origin") != "ai" or project.get(
        "script_approved_hash"
    ) == approval_fingerprint(project)


def script_problems(project):
    text = (
        project.get("script", "")
        + "\n"
        + "\n".join(s.get("narration", "") for s in project.get("scenes", []))
    )
    known = {s["id"] for s in project.get("sources", [])}
    refs = set(source_ids(text)) | {
        ref for s in project.get("scenes", []) for ref in s.get("source_ids", [])
    }
    return {
        "unresolved": sorted(set(UNRESOLVED.findall(text))),
        "unknown_sources": sorted(refs - known),
        "references": sorted(refs),
    }


def narration_gate(project):
    problems = script_problems(project)
    if problems["unresolved"]:
        return "Resolve the script's NEEDS SOURCE / unverified markers before generating paid narration."
    if problems["unknown_sources"]:
        return (
            "The script references sources that are not in the library: "
            + ", ".join(problems["unknown_sources"])
        )
    if not script_approved(project):
        return "Review and approve the AI-written script in Script before generating narration."
    if project.get("script_dirty"):
        return "Build the timeline to apply script changes before generating narration."
    return None


def inspect(project, check_files=True):
    scenes = project.get("scenes", [])
    assets = {a["id"]: a for a in project.get("assets", [])}
    sources = project.get("sources", [])
    review = project.get("review", {})
    items = []

    def add(
        code,
        title,
        detail,
        tab="review",
        severity="error",
        scene_id=None,
        draft_block=False,
        asset_id=None,
    ):
        items.append(
            {
                "code": code,
                "title": title,
                "detail": detail,
                "tab": tab,
                "severity": severity,
                "scene_id": scene_id,
                "asset_id": asset_id,
                "blocks_final": severity == "error",
                "blocks_draft": draft_block,
            }
        )

    duration = sum(float(s.get("duration", 0)) for s in scenes)
    if not scenes:
        add(
            "empty_timeline",
            "No timeline yet",
            "Build a scene sequence from a script or transcribed recording.",
            "script",
            draft_block=True,
        )
    if duration > 5400:
        add(
            "duration_limit",
            "Timeline exceeds 90 minutes",
            "Shorten the sequence before rendering in this version.",
            "edit",
            draft_block=True,
        )
    if len(scenes) > 400:
        add(
            "scene_limit",
            "More than 400 scenes",
            "Reduce the scene count before rendering.",
            "edit",
            draft_block=True,
        )
    if project.get("script_dirty"):
        add(
            "unapplied_script",
            "Script changes are not applied",
            "Rebuild the timeline, or undo the script changes. Existing edits have not changed.",
            "script",
        )
    if not script_approved(project):
        add(
            "script_approval",
            "AI script needs producer approval",
            "Read the script against the reviewed sources, then approve it for narration. This is not independent fact checking.",
            "script",
        )
    problems = script_problems(project)
    if problems["unresolved"]:
        add(
            "unresolved_claims",
            "Unresolved factual markers",
            "The script still contains: "
            + ", ".join(problems["unresolved"])
            + ". Resolve them before narration or publication.",
            "script",
        )
    if problems["unknown_sources"]:
        add(
            "unknown_sources",
            "Broken source references",
            "These cited sources are missing from the library: "
            + ", ".join(problems["unknown_sources"]),
            "research",
        )
    if not project.get("is_demo"):
        if not sources:
            add(
                "no_sources",
                "No case sources recorded",
                "Add the records, reporting, interviews, or producer notes supporting this episode.",
                "research",
            )
        else:
            not_reviewed = [s["id"] for s in sources if not s.get("reviewed")]
            if not_reviewed:
                add(
                    "source_review",
                    "Sources await review",
                    "Open the original, record verified notes, and review: "
                    + ", ".join(not_reviewed),
                    "research",
                )
            if not problems["references"]:
                add(
                    "unmapped_claims",
                    "No scene-level source links",
                    "Link scene narration to S1-style source IDs so the claim trail survives editing. Imported scripts still require a human factual review.",
                    "edit",
                    "warning",
                )
    unlinked = [
        str(i + 1)
        for i, scene in enumerate(scenes)
        if scene.get("narration", "").strip()
        and not scene.get("source_ids")
        and not source_ids(scene.get("narration", ""))
    ]
    if not project.get("is_demo") and problems["references"] and unlinked:
        add(
            "unlinked_scene_claims",
            "Some narration has no scene source link",
            "Check the claim trail in scenes "
            + ", ".join(unlinked[:24])
            + ". A source link records your attribution; it does not verify the claim.",
            "edit",
            "warning",
        )
    for field, title in [
        ("facts", "Facts and allegations"),
        ("rights", "Media and music rights"),
        ("disclosure", "AI and reconstruction disclosure"),
        ("picture", "Picture, sound, and pacing"),
    ]:
        if not review.get(field):
            add(
                "review_" + field,
                title + " not signed off",
                "Complete this producer attestation in Review after checking the material.",
            )

    voice = assets.get(project.get("narration_id"))
    music = assets.get(project.get("music_id"))
    if not voice:
        add(
            "no_narration",
            "No narration track assigned",
            "Upload a voice-over, use a source recording, or generate narration. A picture-only review draft is still possible.",
            "edit",
        )
    used = set()
    if voice:
        used.add(voice["id"])
    if music:
        used.add(music["id"])
    missing_visuals = []
    audio_overruns = []
    estimated = 0
    for index, scene in enumerate(scenes):
        media_id = scene.get("asset_id")
        if (
            not media_id
            or media_id not in assets
            or assets[media_id].get("kind") not in ("image", "video")
        ):
            missing_visuals.append(str(index + 1))
        else:
            used.add(media_id)
        if scene.get("timing") != "transcribed" and scene.get("narration"):
            estimated += 1
        if voice and voice.get("duration"):
            end = float(scene.get("audio_start", 0)) + min(
                float(scene.get("audio_duration", scene["duration"])),
                float(scene["duration"]),
            )
            if end > float(voice["duration"]) + 0.3:
                audio_overruns.append(str(index + 1))
    if missing_visuals:
        add(
            "missing_visuals",
            "Scenes need visuals",
            "Assign images or footage to scenes "
            + ", ".join(missing_visuals[:24])
            + ("…" if len(missing_visuals) > 24 else "")
            + ". Drafts may show VISUAL NEEDED cards.",
            "edit",
        )
    if audio_overruns:
        add(
            "audio_out_of_bounds",
            "Narration slices exceed the recording",
            "Scenes "
            + ", ".join(audio_overruns[:24])
            + " will contain padded silence. Check source in-points and narration duration.",
            "edit",
        )
    if estimated and project.get("captions", True):
        add(
            "estimated_captions",
            "Caption timing needs review",
            f"{estimated} scene(s) use estimated timing within the scene. Check the captions, or transcribe the voice for segment alignment.",
            "edit",
            "warning",
        )
    for id in sorted(used):
        asset = assets[id]
        if not str(asset.get("license", "")).strip():
            add(
                "rights_notes",
                "Rights notes missing: " + asset.get("name", id),
                "Document the owner, license/permission, and required attribution in the media library. Notes are a record, not legal clearance.",
                "edit",
                asset_id=id,
            )
        if check_files:
            try:
                path = (ROOT / asset.get("path", "")).resolve()
                exists = (
                    bool(asset.get("path"))
                    and path.is_relative_to(ROOT)
                    and path.is_file()
                )
            except (ValueError, OSError):
                exists = False
            if not exists:
                add(
                    "missing_media_file",
                    "Media file unavailable: " + asset.get("name", id),
                    "Re-upload or reassign the missing media. It cannot be decoded for this export.",
                    "edit",
                    draft_block=True,
                    asset_id=id,
                )
    if (
        scenes
        and not project.get("is_demo")
        and (
            duration < project.get("target_minutes", 25) * 60 * 0.75
            or duration > project.get("target_minutes", 25) * 60 * 1.25
        )
    ):
        add(
            "length_target",
            "Draft length differs from the target",
            f"The actual timeline is {timecode(duration)}; the target is {project.get('target_minutes', 25)} minutes. Do not pad the story with invented details or silent stretching.",
            "script",
            "warning",
        )
    if project.get("episode"):
        import episode

        for issue in episode.issues(project):
            add(
                issue["code"],
                issue["title"],
                issue["detail"],
                "setup",
                draft_block=issue["blocks_draft"],
            )
    errors = [i for i in items if i["blocks_final"]]
    warnings = [i for i in items if i["severity"] == "warning"]
    return {
        "project_id": project["id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration": round(duration, 3),
        "ready_for_final": not errors,
        "ready_for_draft": not any(i["blocks_draft"] for i in items),
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": items,
        "coverage": {
            "scenes": len(scenes),
            "scenes_with_references": sum(bool(s.get("source_ids")) for s in scenes),
            "references": problems["references"],
            "used_media": len(used),
        },
        "disclaimer": "Structural checks and producer attestations only. This report does not establish factual accuracy, copyright clearance, or legal safety.",
    }


def timecode(seconds):
    seconds = max(0, int(seconds))
    if seconds >= 3600:
        return f"{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"
    return f"{seconds // 60}:{seconds % 60:02d}"


def chapters(project):
    result = []
    cursor = 0
    last = None
    for scene in project.get("scenes", []):
        label = str(scene.get("chapter") or scene.get("title") or "Chapter").strip()
        if not result or label != last:
            result.append({"start": round(cursor, 3), "title": label})
            last = label
        cursor += float(scene["duration"])
    return result


def chapter_text(project):
    return (
        "\n".join(timecode(c["start"]) + " " + c["title"] for c in chapters(project))
        + "\n"
    )


def report_markdown(project, report=None):
    report = report or inspect(project)
    text = (
        f"# Preflight — {project['title']}\n\nGenerated: {report['generated_at']}\n\n"
    )
    text += f"Final export ready: {report['ready_for_final']}\n\n{report['errors']} blocking checks · {report['warnings']} warnings\n\n"
    for item in report["issues"]:
        text += f"## {'BLOCK' if item['blocks_final'] else 'WARN'} · {item['title']}\n\n{item['detail']}\n\n"
    text += "## Scene-to-source trail\n\n| Scene | Narration sources | Visual |\n|---|---|---|\n"
    assets = {a["id"]: a for a in project.get("assets", [])}
    for n, s in enumerate(project.get("scenes", [])):
        refs = ", ".join(s.get("source_ids", [])) or "Not linked"
        visual = (
            assets.get(s.get("asset_id"), {})
            .get("name", "Visual needed")
            .replace("|", "/")
        )
        title = s.get("title", "").replace("|", "/")
        text += f"| {n + 1}. {title} | {refs} | {visual} |\n"
    text += "\n" + report["disclaimer"] + "\n"
    return text


def publication_notes(project):
    markers = chapters(project)
    text = f"# Publication handoff — {project['title']}\n\n"
    text += "This is a producer checklist, not a guarantee that the video is ready to publish.\n\n"
    text += "## Chapter draft\n\n```text\n" + chapter_text(project) + "```\n\n"
    spans = [
        markers[i + 1]["start"] - c["start"]
        if i + 1 < len(markers)
        else sum(s["duration"] for s in project.get("scenes", [])) - c["start"]
        for i, c in enumerate(markers)
    ]
    if len(markers) < 3 or any(span < 10 for span in spans):
        text += "Chapter draft needs adjustment before use as automatic YouTube chapters: provide at least three chapters, starting at 0:00, with each section at least ten seconds long.\n\n"
    if project.get("is_demo"):
        text += "**Fictional demonstration. All sample imagery is AI-generated illustration, not real evidence.**\n\n"
    generated = [a for a in project.get("assets", []) if a.get("generated")]
    if generated:
        text += "## Synthetic-media disclosure\n\nSome assets are AI-generated. Disclose synthetic narration and label illustrative/reconstructed imagery; never imply it is authentic case evidence. Confirm the platform's current disclosure requirements before publication.\n\n"
    text += "## Required checks\n\n- Verify case facts, allegations, names, quotations, dates, and current legal status.\n- Confirm permissions, licenses, and all required credits.\n- Watch the complete rendered MP4; check captions, pacing, voice, and music.\n- Do not publish a REVIEW DRAFT or VISUAL NEEDED placeholder as a finished episode.\n\n"
    text += "See sources.md, preflight.md, and project.json for the source/rights trail and the exact export snapshot.\n"
    return text
