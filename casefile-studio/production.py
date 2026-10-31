"""A resumable guided draft workflow. Never auto-approves facts or publishes.

Every paid stage requires allow_paid AND a connected browser-session API key.
Research and AI writing deliberately pause for human review. Resuming a run
reuses saved stages rather than silently re-running paid generation.
"""

from __future__ import annotations
import copy
import re
from dataclasses import dataclass, asdict
from typing import Callable
import ai
import editorial
import storage as store


@dataclass
class Options:
    allow_paid: bool = False
    generate_voice: bool = False
    auto_assign_visuals: bool = True
    allow_placeholders: bool = False
    allow_silent: bool = False
    render: bool = True
    resolution: str = "720p"
    source_asset_id: str | None = None
    max_voice_characters: int = 45000


def recording(project, options):
    available = [
        a
        for a in project.get("assets", [])
        if a.get("has_audio", a.get("kind") == "audio")
        and a["id"] != project.get("music_id")
    ]
    chosen = options.source_asset_id or project.get("narration_id")
    if chosen:
        return next((a for a in available if a["id"] == chosen), None)
    if project.get("mode") in ("narration", "footage") and len(available) == 1:
        return available[0]
    return None


def plan(project, options=None, connected=False):
    options = options or Options()
    scenes = project.get("scenes", [])
    has_script = bool(
        project.get("script", "").strip()
        or any(s.get("narration", "").strip() for s in scenes)
    )
    sources = project.get("sources", [])
    reviewed = [s for s in sources if s.get("reviewed")]
    visuals = [a for a in project.get("assets", []) if a["kind"] in ("image", "video")]
    missing = sum(not s.get("asset_id") for s in scenes)
    voice = next(
        (
            a
            for a in project.get("assets", [])
            if a["id"] == project.get("narration_id")
        ),
        None,
    )
    audio = recording(project, options)
    problem = editorial.narration_gate(project) if has_script else None
    steps = [
        {
            "id": "research",
            "title": "Source the story",
            "description": "Web research produces source leads, not verified evidence.",
            "status": "done"
            if sources
            else "provided"
            if has_script or audio
            else "pending",
            "tab": "research",
        },
        {
            "id": "source_review",
            "title": "Review the source trail",
            "description": "A producer opens originals and records checked facts.",
            "status": "done"
            if reviewed or project.get("is_demo")
            else "review"
            if sources
            else "provided"
            if has_script or audio
            else "waiting",
            "tab": "research",
        },
        {
            "id": "script",
            "title": "Build the narration script",
            "description": "Use your script, transcribe a recording, or write from reviewed sources.",
            "status": "done"
            if has_script
            else "pending"
            if reviewed or audio
            else "waiting",
            "tab": "script",
        },
        {
            "id": "script_review",
            "title": "Approve AI-written narration",
            "description": "AI drafts pause here before any voice generation.",
            "status": "review"
            if has_script and not editorial.script_approved(project)
            else "done"
            if has_script
            else "waiting",
            "tab": "script",
        },
        {
            "id": "assembly",
            "title": "Assemble scenes and visuals",
            "description": "Build the sequence; assign your media without replacing curated choices.",
            "status": "done"
            if scenes and not project.get("script_dirty") and not missing
            else "pending"
            if has_script
            else "waiting",
            "tab": "edit",
        },
        {
            "id": "narration",
            "title": "Add the voice",
            "description": "Reuse recorded narration, or generate it only with your approval.",
            "status": "done" if voice else "pending" if has_script else "waiting",
            "tab": "edit",
        },
        {
            "id": "render",
            "title": "Render a review draft",
            "description": "Always watermarked. Sources, captions, and publication notes travel with it.",
            "status": "waiting",
            "tab": "review",
        },
    ]
    # Keep the render state separate from whether an older manual export exists.
    steps[-1]["status"] = (
        "done"
        if (project.get("production") or {}).get("status") == "complete"
        else "pending"
        if scenes
        else "waiting"
    )
    paid = []
    if not has_script:
        if audio:
            paid.append("Transcribe the selected recording")
        elif not sources:
            paid.append("Research the case on the web")
        elif reviewed:
            paid.append("Draft a script from reviewed sources")
    if options.generate_voice and not voice and has_script and not problem:
        paid.append("Generate synthetic narration")
    if not has_script:
        if audio:
            next_action = {
                "stage": "transcription",
                "title": "Transcribe your selected recording",
                "tab": "edit",
            }
        elif sources and not reviewed:
            next_action = {
                "stage": "source_review",
                "title": "Review sources and add verified notes",
                "tab": "research",
            }
        elif reviewed:
            next_action = {
                "stage": "script",
                "title": "Draft from reviewed sources",
                "tab": "script",
            }
        else:
            next_action = {
                "stage": "research",
                "title": "Research your case",
                "tab": "research",
            }
    elif problem:
        next_action = {"stage": "script_review", "title": problem, "tab": "script"}
    elif not scenes or project.get("script_dirty"):
        next_action = {
            "stage": "assembly",
            "title": "Assemble the script into scenes",
            "tab": "script",
        }
    elif missing and not visuals and not options.allow_placeholders:
        next_action = {
            "stage": "visuals",
            "title": "Import licensed visuals for the scenes",
            "tab": "edit",
        }
    elif (
        not voice
        and not audio
        and not options.generate_voice
        and not options.allow_silent
    ):
        next_action = {
            "stage": "narration",
            "title": "Assign a recording or enable AI narration",
            "tab": "edit",
        }
    else:
        next_action = {
            "stage": "render",
            "title": "Produce a watermarked review draft",
            "tab": "review",
        }
    words = len(
        re.findall(
            r"\b[\w’'-]+\b", editorial.strip_references(project.get("script", ""))
        )
    )
    return {
        "steps": steps,
        "next_action": next_action,
        "paid_stages": paid,
        "connected": connected,
        "spoken_words": words,
        "estimated_seconds": round(words / 145 * 60, 1),
        "scene_count": len(scenes),
        "missing_visuals": missing,
        "visual_assets": len(visuals),
        "voice_assigned": bool(voice),
        "recording_id": audio["id"] if audio else None,
        "options": asdict(options),
        "human_review_required": True,
        "disclaimer": "No fact verification, copyright clearance, visual sourcing, or publication is performed automatically.",
    }


def transcript_scenes(project, asset, segments):
    groups = []
    current = []
    for segment in segments:
        if segment["end"] <= segment["start"]:
            continue
        current.append(segment)
        if segment["end"] - current[0]["start"] >= 18:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    visuals = [
        a
        for a in project["assets"]
        if a["kind"] in ("image", "video") and a["id"] != asset["id"]
    ]
    scenes = []
    for i, group in enumerate(groups):
        start, end = group[0]["start"], group[-1]["end"]
        text = " ".join(s["text"] for s in group)
        scenes.append(
            {
                "id": store.uid(),
                "title": " ".join(text.split()[:8]).rstrip(".,"),
                "chapter": "Interview" if asset["kind"] == "video" else "Narration",
                "narration": text,
                "source_ids": [],
                "duration": max(0.5, round(end - start, 3)),
                "asset_id": asset["id"]
                if asset["kind"] == "video"
                else (visuals[i % len(visuals)]["id"] if visuals else None),
                "motion": "none" if asset["kind"] == "video" else "slow-zoom",
                "transition": "cut",
                "show_title": False,
                "trim_start": start if asset["kind"] == "video" else 0,
                "audio_start": start,
                "audio_duration": max(0.5, end - start),
                "timing": "transcribed",
                "captions": [
                    {
                        "start": max(0, s["start"] - start),
                        "end": max(0, s["end"] - start),
                        "text": s["text"],
                    }
                    for s in group
                ],
            }
        )
    if not scenes:
        raise ValueError(
            "No usable speech segments were returned. Your prior timeline was kept."
        )
    return scenes


def assign_missing_visuals(project):
    visuals = [a for a in project.get("assets", []) if a["kind"] in ("image", "video")]
    if not visuals:
        return copy.deepcopy(project.get("scenes", [])), 0
    scenes = copy.deepcopy(project.get("scenes", []))
    count = 0
    stop = {
        "the",
        "a",
        "of",
        "in",
        "an",
        "and",
        "to",
        "on",
        "at",
        "for",
        "this",
        "that",
    }
    for i, scene in enumerate(scenes):
        if scene.get("asset_id"):
            continue
        tokens = set(re.findall(r"\w+", scene.get("narration", "").lower())) - stop
        ranked = sorted(
            visuals,
            key=lambda a: len(tokens & set(re.findall(r"\w+", a["name"].lower()))),
            reverse=True,
        )
        best = ranked[0]
        if not tokens & set(re.findall(r"\w+", best["name"].lower())):
            best = visuals[i % len(visuals)]
        scene["asset_id"] = best["id"]
        scene["motion"] = "none" if best["kind"] == "video" else "slow-zoom"
        count += 1
    return scenes, count


class RunCancelled(Exception):
    pass


def run(
    project_id: str,
    options: Options,
    config: dict | None,
    progress: Callable,
    cancelled: Callable,
    export_fn: Callable,
):
    run_id = store.uid()
    completed = []

    def load():
        return store.get_project(project_id)

    def save(stage, message, fields=None, status="running", next_tab=None):
        with store.LOCK:
            project = load()
            if fields:
                project.update(fields)
            project["production"] = {
                "id": run_id,
                "status": status,
                "stage": stage,
                "next_tab": next_tab,
                "message": message,
                "completed_stages": list(completed),
                "updated_at": store.now(),
                "options": asdict(options),
            }
            if status in ("paused", "complete", "assembled"):
                store.add_message(project, "assistant", message)
            store.save_project(project)
        return project

    def check():
        if cancelled():
            raise RunCancelled()

    def pause(stage, message, tab):
        save(stage, message, status="paused", next_tab=tab)
        return {
            "outcome": "paused",
            "stage": stage,
            "message": message,
            "tab": tab,
            "run_id": run_id,
        }

    def allow_ai(stage):
        if not options.allow_paid:
            return pause(
                stage,
                "This stage needs paid AI approval. Enable paid stages only if you want the provider requests to run.",
                "settings",
            )
        if not config or not config.get("key"):
            return pause(
                stage,
                "Connect an AI API key in Settings. No paid request was sent.",
                "settings",
            )
        return None

    def scaled(start, end):
        return lambda value, message: progress(
            round(start + (end - start) * max(0, min(100, value)) / 100), message
        )

    with store.LOCK:
        initial = load()
        store.checkpoint(initial)
        store.save_project(initial)
    try:
        save("prepare", "Checking your starting material")
        progress(2, "Checking starting material and editorial gates")
        check()
        p = load()
        if not p.get("script", "").strip() and p.get("scenes"):
            p = save(
                "prepare",
                "Recovered narration from the existing scenes",
                {
                    "script": editorial.script_from_scenes(p["scenes"]),
                    "script_dirty": False,
                },
            )
        audio = recording(p, options)
        if options.source_asset_id and not audio:
            return pause(
                "recording",
                "The selected source recording is missing or has no audio track. Choose another asset.",
                "edit",
            )
        if not p.get("script", "").strip():
            if audio:
                blocked = allow_ai("transcription")
                if blocked:
                    return blocked
                save("transcription", "Transcribing the selected recording")
                segments = ai.transcribe(config, p, audio, scaled(5, 30), cancelled)
                check()
                scenes = transcript_scenes(p, audio, segments)
                completed.append("transcription")
                p = save(
                    "assembly",
                    "Assembled a source-aligned transcription",
                    {
                        "scenes": scenes,
                        "script": editorial.script_from_scenes(scenes),
                        "script_dirty": False,
                        "script_origin": "transcript",
                        "script_approved_hash": None,
                        "narration_id": audio["id"],
                        "review": {**p["review"], "facts": False, "picture": False},
                    },
                )
            else:
                if not p.get("sources"):
                    if p.get("is_demo"):
                        return pause(
                            "research",
                            "The sample is fictional. Start a new project to research an actual case.",
                            "research",
                        )
                    if not p.get("topic", "").strip():
                        return pause(
                            "research",
                            "Enter a specific case name and identifying context first.",
                            "research",
                        )
                    if p.get("mode") in ("narration", "footage"):
                        return pause(
                            "recording",
                            "Import your recording and choose it as the source. Multiple recordings need an explicit selection.",
                            "edit",
                        )
                    blocked = allow_ai("research")
                    if blocked:
                        return blocked
                    save("research", "Researching case source leads")
                    result = ai.research(config, p, scaled(5, 30))
                    check()
                    completed.append("research")
                    p = save(
                        "source_review",
                        "Research saved; original sources need producer review",
                        {
                            "research_report": result["research_report"],
                            "sources": result["sources"],
                            "review": {**p["review"], "facts": False},
                        },
                    )
                    return pause(
                        "source_review",
                        "Research is saved. Open the originals, add verified facts to source notes, and mark the sources you intend to use as reviewed. Nothing was auto-verified.",
                        "research",
                    )
                if not any(s.get("reviewed") for s in p["sources"]):
                    return pause(
                        "source_review",
                        "Review original sources and record checked facts before AI scriptwriting.",
                        "research",
                    )
                blocked = allow_ai("script")
                if blocked:
                    return blocked
                save("script", "Drafting from your reviewed sources")
                draft = ai.draft_script(config, p, scaled(8, 35))
                check()
                draft_project = {**p, "script": draft["script"], "narration_id": None}
                scenes = store.build_scenes(draft_project)
                completed.append("script")
                save(
                    "script_review",
                    "AI script saved for producer review",
                    {
                        "script": draft["script"],
                        "script_dirty": False,
                        "script_origin": "ai",
                        "script_approved_hash": None,
                        "scenes": scenes,
                        "narration_id": None,
                        "review": {**p["review"], "facts": False, "picture": False},
                    },
                )
                return pause(
                    "script_review",
                    "Your AI-written draft is saved. Read it against the sources and approve it in Script before narration. "
                    + draft.get("note", ""),
                    "script",
                )
        check()
        p = load()
        if not p.get("narration_id") and audio:
            scenes = copy.deepcopy(p.get("scenes", []))
            cursor = 0.0
            for scene in scenes:
                scene.update(
                    audio_start=round(cursor, 3),
                    audio_duration=scene["duration"],
                    timing="estimated",
                    captions=[],
                )
                cursor += scene["duration"]
            p = save(
                "narration",
                "Reusing your selected recording",
                {"narration_id": audio["id"], "scenes": scenes},
            )
        if not p.get("scenes") or p.get("script_dirty"):
            if p.get("scenes") and editorial.strip_references(
                p["script"]
            ) != editorial.strip_references(editorial.script_from_scenes(p["scenes"])):
                p["narration_id"] = None
            scenes = store.build_scenes(p)
            completed.append("assembly")
            p = save(
                "assembly",
                "Built the scene sequence",
                {
                    "scenes": scenes,
                    "script_dirty": False,
                    "narration_id": p.get("narration_id"),
                    "review": {**p["review"], "picture": False},
                },
            )
        gate = editorial.narration_gate(p)
        if gate:
            return pause("script_review", gate, "script")
        progress(38, "Checking scene visuals and narration")
        if options.auto_assign_visuals:
            scenes, count = assign_missing_visuals(p)
            if count:
                p = save(
                    "visuals",
                    f"Assigned {count} missing visuals; identity and suitability still need review",
                    {"scenes": scenes, "review": {**p["review"], "picture": False}},
                )
                completed.append("visuals")
        if (
            any(not s.get("asset_id") for s in p["scenes"])
            and not options.allow_placeholders
        ):
            return pause(
                "visuals",
                "Import and assign licensed visuals. The app will not invent case evidence or silently source unlicensed footage. You can explicitly allow placeholder cards for a review-only draft.",
                "edit",
            )
        check()
        p = load()
        if not p.get("narration_id"):
            if options.generate_voice:
                blocked = allow_ai("narration")
                if blocked:
                    return blocked
                characters = sum(
                    len(editorial.strip_references(s.get("narration", "")))
                    for s in p["scenes"]
                )
                if characters > options.max_voice_characters:
                    return pause(
                        "narration",
                        f"The script has {characters:,} voice characters, above this run's {options.max_voice_characters:,} character cap. Shorten it or explicitly raise the cap.",
                        "script",
                    )
                save("narration", "Generating explicitly approved synthetic narration")
                asset, scenes = ai.generate_narration(
                    config, p, scaled(40, 68), cancelled
                )
                check()
                completed.append("narration")
                p = save(
                    "narration",
                    "Narration saved and aligned by scene",
                    {
                        "assets": p["assets"] + [asset],
                        "narration_id": asset["id"],
                        "scenes": scenes,
                        "review": {
                            **p["review"],
                            "disclosure": False,
                            "picture": False,
                        },
                    },
                )
            elif not options.allow_silent:
                return pause(
                    "narration",
                    "Assign a voice recording, or explicitly enable AI narration. A silent picture-only draft is available only if you choose it.",
                    "edit",
                )
        check()
        p = load()
        report = editorial.inspect(p)
        if not report["ready_for_draft"]:
            problem = next(i for i in report["issues"] if i["blocks_draft"])
            return pause(
                "preflight", problem["title"] + ": " + problem["detail"], problem["tab"]
            )
        if not options.render:
            save(
                "review",
                "Sequence prepared. Review the scenes, voice, sources, and timing before rendering.",
                status="assembled",
            )
            return {
                "outcome": "assembled",
                "stage": "review",
                "tab": "edit",
                "message": "Sequence prepared; no render requested.",
                "run_id": run_id,
            }
        save("render", "Rendering a watermarked review draft")
        export = export_fn(
            p,
            {
                "resolution": options.resolution,
                "draft": True,
                "captions": p.get("captions", True),
            },
            scaled(70, 99),
            cancelled,
        )
        check()
        completed.append("render")
        save(
            "complete",
            "Review draft ready. Watch the rendered MP4 and complete factual, rights, disclosure, and editorial checks before any final export.",
            status="complete",
        )
        return {
            "outcome": "complete",
            "stage": "complete",
            "tab": "review",
            "message": "Your watermarked review draft is ready.",
            "run_id": run_id,
            "export_id": export["id"],
        }
    except RunCancelled:
        save(
            "cancelled",
            "Production cancelled. Saved stages are retained; completed provider requests may have incurred charges.",
            status="cancelled",
        )
        return {"outcome": "cancelled", "run_id": run_id}
    except Exception as exc:
        if cancelled():
            save(
                "cancelled",
                "Production cancelled. Saved stages are retained; completed provider requests may have incurred charges.",
                status="cancelled",
            )
        else:
            save("error", str(exc)[:1000], status="error")
        raise
