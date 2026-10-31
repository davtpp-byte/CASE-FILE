from __future__ import annotations
import json, re, threading, uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LOCK = threading.RLock()


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid.uuid4().hex[:16]


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    temp.replace(path)


def get_project(id):
    if not re.fullmatch(r"[a-f0-9]{16}", id):
        raise FileNotFoundError("Project not found")
    with LOCK:
        return json.loads((DATA / "projects" / f"{id}.json").read_text())


def save_project(project):
    with LOCK:
        project["updated_at"] = now()
        atomic_json(DATA / "projects" / f"{project['id']}.json", project)
    return project


def patch_project(id, changes):
    with LOCK:
        p = get_project(id)
        p.update(changes)
        return save_project(p)


def projects():
    result = []
    for path in (DATA / "projects").glob("*.json"):
        p = json.loads(path.read_text())
        result.append(
            {
                "has_episode": bool(p.get("episode")),
                **{
                    k: p.get(k)
                    for k in (
                        "id",
                        "title",
                        "topic",
                        "mode",
                        "target_minutes",
                        "is_demo",
                        "updated_at",
                    )
                },
            }
        )
    return sorted(result, key=lambda x: x["updated_at"], reverse=True)


def new_project(title, mode="topic", minutes=25, project_id=None):
    if project_id is not None and (
        not re.fullmatch(r"[a-f0-9]{16}", project_id)
        or (DATA / "projects" / f"{project_id}.json").exists()
    ):
        raise ValueError("Recovery project ID is invalid or already exists.")
    project = {
        "id": project_id or uid(),
        "title": title or "Untitled documentary",
        "topic": title or "",
        "mode": mode,
        "target_minutes": minutes,
        "script": "",
        "script_dirty": False,
        "script_origin": "user",
        "script_approved_hash": None,
        "production": None,
        "research_report": "",
        "sources": [],
        "scenes": [],
        "assets": [],
        "exports": [],
        "messages": [],
        "narration_id": None,
        "music_id": None,
        "music_volume": 0.12,
        "look": "noir",
        "captions": True,
        "review": {
            "facts": False,
            "rights": False,
            "disclosure": False,
            "picture": False,
        },
        "is_demo": False,
        "created_at": now(),
        "updated_at": now(),
    }
    return save_project(project)


def word_count(text):
    return len(re.findall(r"\b[\w’'-]+\b", text))


def checkpoint(project):
    fields = [
        "script",
        "script_dirty",
        "script_origin",
        "script_approved_hash",
        "scenes",
        "assets",
        "look",
        "captions",
        "narration_id",
        "music_id",
        "music_volume",
        "review",
        "episode",
    ]
    history = project.get("undo", [])[-7:]
    history.append({k: __import__("copy").deepcopy(project.get(k)) for k in fields})
    project["undo"] = history


def add_message(project, role, text):
    project["messages"] = (
        project.get("messages", []) + [{"role": role, "text": text, "at": now()}]
    )[-24:]


def build_scenes(project, script=None):
    from editorial import source_ids, strip_references

    script = project.get("script", "") if script is None else script
    paragraphs = [x.strip() for x in re.split(r"\n\s*\n", script) if x.strip()]
    chunks = []
    for paragraph in paragraphs:
        refs = source_ids(paragraph)
        text = strip_references(paragraph)
        # Long unpunctuated paragraphs are bounded too, so a scene fits the TTS adapter.
        sentences = re.split(r"(?<=[.!?])\s+", text)
        group = []
        for sentence in sentences:
            words = sentence.split()
            while words:
                room = 65 - len(group)
                group.extend(words[:room])
                words = words[room:]
                if len(group) >= 65:
                    chunks.append((" ".join(group), refs))
                    group = []
        if group:
            chunks.append((" ".join(group), refs))
    if not chunks:
        raise ValueError("Paste or generate a script first. Paragraphs become scenes.")
    if len(chunks) > 400:
        raise ValueError("This version supports up to 400 scenes per project.")
    visuals = [a for a in project["assets"] if a["kind"] in ("image", "video")]
    narration = next(
        (a for a in project["assets"] if a["id"] == project.get("narration_id")), None
    )
    durations = [max(3, word_count(text) / 145 * 60) for text, _ in chunks]
    if narration and narration.get("duration"):
        scale = narration["duration"] / sum(durations)
        durations = [max(0.5, d * scale) for d in durations]
    result = []
    cursor = 0.0
    for i, ((text, refs), duration) in enumerate(zip(chunks, durations)):
        words = set(re.findall(r"\w+", text.lower()))
        ranked = sorted(
            visuals,
            key=lambda a: len(words & set(re.findall(r"\w+", a["name"].lower()))),
            reverse=True,
        )
        chosen = (
            ranked[0]
            if ranked and words & set(re.findall(r"\w+", ranked[0]["name"].lower()))
            else (visuals[i % len(visuals)] if visuals else None)
        )
        title = " ".join(re.sub(r"^#+\s*", "", text).split()[:8]).rstrip(".,:;")
        length = round(min(600, max(0.5, duration)), 3)
        result.append(
            {
                "id": uid(),
                "title": title or f"Scene {i + 1}",
                "chapter": "Opening" if i == 0 else "Case narrative",
                "narration": text,
                "source_ids": list(refs),
                "duration": length,
                "asset_id": chosen["id"] if chosen else None,
                "motion": "slow-zoom"
                if not chosen or chosen["kind"] == "image"
                else "none",
                "transition": "fade",
                "show_title": i == 0,
                "trim_start": 0,
                "audio_start": round(cursor, 3),
                "audio_duration": length,
                "timing": "estimated",
                "captions": [],
            }
        )
        cursor += length
    return result


def seed():
    for sub in ["projects", "media", "exports", "jobs"]:
        (DATA / sub).mkdir(parents=True, exist_ok=True)
    if list((DATA / "projects").glob("*.json")):
        return
    p = new_project("The Blackwater tapes", "script", 25)
    p["is_demo"] = True
    media = DATA / "media" / p["id"]
    media.mkdir(parents=True, exist_ok=True)
    original = Image.open(ROOT / "web/assets/blackwater-road.jpg").convert("RGB")
    # The variations are crops of the same explicitly AI-created illustrative image.
    variants = [
        original,
        ImageOps.fit(original, original.size, centering=(0.75, 0.45)),
        ImageEnhance.Color(original).enhance(0.18),
    ]
    names = [
        "Blackwater road · AI illustration",
        "River at dusk · AI illustration",
        "Archive treatment · AI illustration",
    ]
    for i, image in enumerate(variants):
        if i == 1:
            w, h = original.size
            image = original.crop(
                (int(w * 0.28), int(h * 0.25), int(w * 0.95), int(h * 0.92))
            ).resize(original.size)
        path = media / f"demo-{i}.jpg"
        image.save(path, quality=87)
        p["assets"].append(
            {
                "id": uid(),
                "name": names[i],
                "kind": "image",
                "path": str(path.relative_to(ROOT)),
                "url": f"/media/{p['id']}/demo-{i}.jpg",
                "thumbnail": f"/media/{p['id']}/demo-{i}.jpg",
                "width": image.width,
                "height": image.height,
                "duration": 0,
                "has_audio": False,
                "license": "AI-generated illustrative demo; not documentary evidence.",
                "generated": True,
                "size": path.stat().st_size,
            }
        )
    scenes = [
        (
            "The road to Blackwater",
            "Opening",
            "On the edge of a quiet town, a road disappears into the trees. In this fictional documentary study, that road is our opening image. It sets a mood, but it is not evidence of a real event.",
        ),
        (
            "A town after dark",
            "Setting the scene",
            "An establishing shot can make a place feel familiar before the story begins. The river, the distant light, and the surrounding forest are all illustrative. No actual town, person, or investigation is being represented here.",
        ),
        (
            "The first unanswered question",
            "The central question",
            "A careful documentary distinguishes what is known from what is merely suggested. Before introducing a question, the editor should establish its source. Suspense should come from the documented sequence, not from invented claims or misleading images.",
        ),
        (
            "Following the paper trail",
            "The record",
            "Court records, contemporaneous reporting, and attributed interviews can form the spine of a researched episode. Each quotation needs context. Every factual claim should lead back to a source that a producer has actually checked.",
        ),
        (
            "What the record can tell us",
            "Context and perspective",
            "Good pacing leaves room for a viewer to understand the evidence. Quiet transitions, clear date cards, and an unobtrusive score can support the narration without sensationalizing the people whose lives a real story would concern.",
        ),
        (
            "The story is yours to build",
            "Closing",
            "This short sample demonstrates the editing workspace rather than a finished investigation. Start a new project with a topic, a script, narration, or footage. Review the facts, confirm your media rights, and shape the final episode yourself.",
        ),
    ]
    p["script"] = "\n\n".join(s[2] for s in scenes)
    p["scenes"] = build_scenes(p)
    for i, (scene, (title, chapter, _)) in enumerate(zip(p["scenes"], scenes)):
        scene.update(
            {
                "title": title,
                "chapter": chapter,
                "asset_id": p["assets"][i % 3]["id"],
                "show_title": i in (0, 3, 5),
            }
        )
    p["research_report"] = (
        "FICTIONAL DEMONSTRATION\n\nThis sample contains no researched case facts. All imagery is AI-generated illustrative scenery. Replace the sample with a real project and review each source before publication."
    )
    p["messages"] = [
        {
            "role": "assistant",
            "text": "Your edit, your direction. Try “hide all titles”, “use the archive look”, or “set scene 2 to 12 seconds”. These work locally. Creative rewrites and case research need an AI connection.",
        }
    ]
    save_project(p)
