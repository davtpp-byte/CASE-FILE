from __future__ import annotations
import copy, json, re, shutil, threading, uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
import httpx
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, ImageOps
import ai, renderer, editorial, production, episode
from storage import (
    ROOT,
    DATA,
    LOCK,
    now,
    uid,
    atomic_json,
    get_project,
    save_project,
    projects,
    new_project,
    build_scenes,
    checkpoint,
    add_message,
    seed,
)

seed()
app = FastAPI(title="Casefile Studio", version="0.4.2", docs_url="/api/docs")
POOL = ThreadPoolExecutor(max_workers=4)
RENDER_LOCK = threading.Semaphore(1)
SESSIONS = {}
JOBS = {}
for path in (DATA / "jobs").glob("*.json"):
    try:
        j = json.loads(path.read_text())
        if j["status"] in ("queued", "running"):
            j.update(
                status="interrupted",
                message="Server restarted. Please run this operation again.",
            )
            atomic_json(path, j)
        JOBS[j["id"]] = j
    except (ValueError, KeyError):
        pass


@app.middleware("http")
async def session(request: Request, call_next):
    # An opaque browser-session header also works inside cross-site live-preview
    # iframes where third-party cookies are blocked. It never contains the API key.
    sid = request.headers.get("x-casefile-session") or request.cookies.get(
        "casefile_session"
    )
    fresh = not sid or not re.fullmatch(r"[a-f0-9]{32}", sid)
    if fresh:
        sid = uuid.uuid4().hex
    request.state.session = sid
    if (
        request.method in ("POST", "PATCH", "DELETE")
        and re.match(r"^/api/projects/[a-f0-9]{16}(?:/|$)", request.url.path)
        and not request.url.path.endswith("/production-plan")
    ):
        project_id = request.url.path.split("/")[3]
        if any(
            j["project_id"] == project_id
            and j["status"] in ("queued", "running")
            and j["kind"] != "render"
            for j in list(JOBS.values())
        ):
            return JSONResponse(
                {
                    "detail": "This project is read-only while its current AI/production operation runs. Wait for it to finish or cancel it."
                },
                status_code=409,
            )
    response = await call_next(request)
    if fresh and request.url.path.startswith("/api"):
        secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        response.set_cookie(
            "casefile_session",
            sid,
            httponly=True,
            samesite="strict",
            secure=secure,
            max_age=86400,
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def project_or_404(id):
    try:
        return get_project(id)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found.")


def config(request):
    cfg = SESSIONS.get(request.state.session)
    if not cfg or not cfg.get("key"):
        raise HTTPException(
            412,
            "Connect an AI API key in Settings first. Local editing and video rendering do not need one.",
        )
    return copy.deepcopy(cfg)


def public_config(request):
    cfg = SESSIONS.get(request.state.session, {})
    return {
        "connected": bool(cfg.get("key")),
        "model": cfg.get("model", "gpt-4.1"),
        "research_model": cfg.get("research_model", "gpt-4.1"),
        "speech_model": cfg.get("speech_model", "gpt-4o-mini-tts"),
        "voice": cfg.get("voice", "onyx"),
    }


def job_update(id, **fields):
    with LOCK:
        JOBS[id].update(fields, updated_at=now())
        atomic_json(DATA / "jobs" / f"{id}.json", JOBS[id])


def spawn(project_id, kind, work):
    with LOCK:
        if any(
            j["project_id"] == project_id and j["status"] in ("running", "queued")
            for j in JOBS.values()
        ):
            raise HTTPException(
                409,
                "An operation is already running for this project. Wait for it to finish or cancel it.",
            )
        id = uid()
        JOBS[id] = {
            "id": id,
            "project_id": project_id,
            "kind": kind,
            "status": "queued",
            "progress": 0,
            "message": "Queued",
            "cancel_requested": False,
            "created_at": now(),
            "updated_at": now(),
        }
        job_update(id)

    def run():
        try:
            job_update(id, status="running", message="Starting")
            progress = lambda percent, message: job_update(
                id, progress=percent, message=message
            )
            cancelled = lambda: JOBS[id].get("cancel_requested", False)
            result = work(progress, cancelled)
            if cancelled():
                job_update(
                    id,
                    status="cancelled",
                    message="Cancelled. Completed AI requests may still incur charges.",
                )
            else:
                job_update(
                    id,
                    status="done",
                    progress=100,
                    message="Complete",
                    result=result or {},
                )
        except Exception as e:
            message = str(e)
            job_update(
                id,
                status="cancelled" if JOBS[id].get("cancel_requested") else "error",
                message=message[:1600],
            )

    POOL.submit(run)
    return {"job_id": id}


def sanitize_scene(scene, asset_ids):
    out = {
        "id": scene.get("id")
        if re.fullmatch(r"[a-f0-9]{16}", str(scene.get("id", "")))
        else uid()
    }
    out.update(
        {
            k: str(scene.get(k, ""))[: (12000 if k == "narration" else 180)]
            for k in ["title", "chapter", "narration"]
        }
    )
    try:
        minimum = 1 / renderer.FPS if "guide_gap" in scene else 0.5
        out["duration"] = round(
            min(600, max(minimum, float(scene.get("duration", 5)))), 3
        )
        out["trim_start"] = max(0, min(21600, float(scene.get("trim_start", 0))))
        out["audio_start"] = max(0, min(21600, float(scene.get("audio_start", 0))))
        out["audio_duration"] = max(
            0.04, min(600, float(scene.get("audio_duration", out["duration"])))
        )
    except (ValueError, TypeError):
        raise HTTPException(422, "Scene timing must be a number.")
    if not isinstance(scene.get("source_ids", []), list):
        raise HTTPException(
            422, "Scene source references must be a list of S1-style IDs."
        )
    out["source_ids"] = list(
        dict.fromkeys(
            [
                str(ref).upper()
                for ref in scene.get("source_ids", [])
                if re.fullmatch(r"S\d+", str(ref), re.I)
            ]
            + editorial.source_ids(out["narration"])
        )
    )[:40]
    out["narration"] = editorial.strip_references(out["narration"])
    out["asset_id"] = (
        scene.get("asset_id") if scene.get("asset_id") in asset_ids else None
    )
    out["motion"] = (
        scene.get("motion")
        if scene.get("motion") in ["none", "slow-zoom", "pan-left"]
        else "slow-zoom"
    )
    out["transition"] = (
        scene.get("transition")
        if scene.get("transition") in ["none", "cut", "fade", "cross-dissolve"]
        else "none"
    )
    out["transition_duration"] = max(
        0.0, min(600.0, float(scene.get("transition_duration", 0) or 0))
    )
    out["show_title"] = bool(scene.get("show_title", True))
    out["timing"] = scene.get("timing", "estimated")[:30]
    for field in ("guide_cue_id", "guide_source_id", "source_label"):
        if field in scene:
            out[field] = str(scene[field] or "")[:240]
    if "guide_gap" in scene:
        out["guide_gap"] = bool(scene["guide_gap"])
    for field in ("inspection_only", "guide_unreviewed", "guide_alternative"):
        if field in scene:
            out[field] = scene[field] is True
    if "guide_primary_source_id" in scene:
        out["guide_primary_source_id"] = str(scene["guide_primary_source_id"])[:30]
    if "source_window_basis" in scene:
        out["source_window_basis"] = str(scene["source_window_basis"])[:240]
    if "source_crop_end" in scene:
        try:
            out["source_crop_end"] = max(0.0, float(scene["source_crop_end"]))
        except (ValueError, TypeError):
            out["source_crop_end"] = None
    out["captions_exact"] = scene.get("captions_exact") is True
    out["captions"] = []
    for c in scene.get("captions", [])[:500]:
        try:
            out["captions"].append(
                {
                    "start": max(0, float(c["start"])),
                    "end": max(0, float(c["end"])),
                    "text": str(c["text"])[:2000],
                }
            )
        except (ValueError, TypeError, KeyError):
            raise HTTPException(422, "Invalid caption timing.")
    return out


@app.get("/api/bootstrap")
def bootstrap(request: Request):
    return {
        "projects": projects(),
        "config": public_config(request),
        "capabilities": {
            "render": bool(shutil.which("ffmpeg")),
            "ai_requires_key": True,
            "single_workspace": True,
        },
    }


@app.get("/api/config")
def get_config(request: Request):
    return public_config(request)


@app.post("/api/config")
async def set_config(request: Request):
    data = await request.json()
    old = SESSIONS.get(request.state.session, {})
    key = str(data.get("key") or old.get("key", "")).strip()
    if not key:
        raise HTTPException(
            422, "Enter an API key in the private connection field, not in chat."
        )
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            result = await client.get(
                ai.BASE + "/models", headers={"Authorization": "Bearer " + key}
            )
        if result.status_code != 200:
            raise HTTPException(
                400,
                "The key could not be verified. Check the API key, account permissions, and provider billing.",
            )
    except httpx.HTTPError:
        raise HTTPException(
            502, "The AI provider could not be reached. Try again later."
        )
    cfg = {"key": key}
    for field, default in [
        ("model", "gpt-4.1"),
        ("research_model", "gpt-4.1"),
        ("speech_model", "gpt-4o-mini-tts"),
        ("voice", "onyx"),
    ]:
        val = str(data.get(field, old.get(field, default))).strip()
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,100}", val):
            raise HTTPException(422, "Invalid model or voice name.")
        cfg[field] = val
    SESSIONS[request.state.session] = cfg
    return public_config(request)


@app.delete("/api/config")
def disconnect(request: Request):
    SESSIONS.pop(request.state.session, None)
    return public_config(request)


class NewProject(BaseModel):
    title: str = Field(default="Untitled documentary", max_length=180)
    mode: Literal["topic", "script", "narration", "footage"] = "topic"
    target_minutes: int = Field(default=25, ge=20, le=40)


@app.post("/api/projects")
def create_project(data: NewProject):
    return new_project(data.title.strip(), data.mode, data.target_minutes)


@app.get("/api/projects/{id}")
def get_one(id: str):
    return project_or_404(id)


@app.get("/api/projects/{id}/media-status")
def media_status(id: str):
    p = project_or_404(id)
    result = []
    for asset in p.get("assets", []):
        try:
            file = (ROOT / asset.get("path", "")).resolve()
            exists = (
                bool(asset.get("path")) and file.is_relative_to(ROOT) and file.is_file()
            )
        except (OSError, ValueError):
            exists = False
        result.append(
            {key: asset.get(key) for key in ("id", "name", "size", "kind", "has_audio")}
            | {"exists": exists}
        )
    return {"assets": result}


@app.post("/api/projects/{id}/recover-empty")
async def recover_empty(id: str, request: Request):
    body = await request.json()
    if not re.fullmatch(r"[a-f0-9]{16}", id):
        raise HTTPException(422, "Invalid recovery project ID.")
    with LOCK:
        try:
            return get_project(id)
        except FileNotFoundError:
            pass
        mode = body.get("mode", "narration")
        if mode not in ("topic", "script", "narration", "footage"):
            mode = "narration"
        try:
            minutes = min(40, max(20, int(body.get("target_minutes", 25))))
        except (ValueError, TypeError):
            minutes = 25
        return new_project(
            str(body.get("title") or "Recovered working session")[:180],
            mode,
            minutes,
            project_id=id,
        )


@app.post("/api/projects/{id}/recovery-checkpoint")
def recovery_checkpoint(id: str):
    p = project_or_404(id)
    token = now().replace(":", "-").replace("+", "_")
    atomic_json(DATA / "recovery-backups" / f"{id}-{token}.json", p)
    return {"saved": True}


@app.post("/api/projects/{id}/reuse-timings")
async def reuse_timings(id: str, request: Request):
    body = await request.json()
    fingerprint = str(body.get("hash", ""))
    if not re.fullmatch(r"[a-f0-9]{64}", fingerprint):
        raise HTTPException(422, "Invalid timing fingerprint.")
    with LOCK:
        p = project_or_404(id)
        for path in (DATA / "projects").glob("*.json"):
            try:
                candidate = (
                    json.loads(path.read_text()).get("episode", {}).get("timings", {})
                )
            except (OSError, ValueError, AttributeError):
                continue
            if candidate.get("hash") == fingerprint:
                e = copy.deepcopy(episode.state(p))
                e["timings"] = copy.deepcopy(candidate)
                e.pop("timing_reviewed_digest", None)
                e.pop("transcript_reviewed_digest", None)
                p["episode"] = e
                p["review"]["picture"] = False
                return episode_result(p)
    raise HTTPException(
        404, "The original timing export is needed; no word clock was guessed."
    )


@app.post("/api/browser-session")
async def browser_session(request: Request):
    raw = await request.body()
    if len(raw) > 16000000:
        raise HTTPException(413, "Session diagnostic too large.")
    try:
        body = json.loads(raw)
    except ValueError:
        raise HTTPException(422, "Invalid session diagnostic.")
    if not isinstance(body, dict):
        raise HTTPException(422, "Invalid session diagnostic object.")
    source = body.get("snapshot")
    snapshot = None
    if isinstance(source, dict) and re.fullmatch(
        r"[a-f0-9]{16}", str(source.get("id", ""))
    ):
        keys = {
            "id",
            "title",
            "updated_at",
            "mode",
            "target_minutes",
            "script",
            "script_origin",
            "episode",
            "narration_id",
            "music_id",
            "music_volume",
            "look",
            "captions",
            "review",
            "scenes",
            "sources",
            "assets",
            "exports",
        }
        snapshot = {key: source[key] for key in keys if key in source}
        snapshot["assets"] = [
            {
                key: item.get(key)
                for key in (
                    "id",
                    "name",
                    "size",
                    "kind",
                    "duration",
                    "video_duration",
                    "has_audio",
                    "license",
                    "url",
                    "available_on_server",
                )
            }
            for item in source.get("assets", [])
            if isinstance(item, dict)
        ]
    parsed = urlparse(str(body.get("origin", "")))
    origin = (
        f"{parsed.scheme}://{parsed.netloc}"
        if parsed.scheme in ("http", "https") and parsed.netloc and not parsed.username
        else ""
    )
    record = {
        "observed_at": now(),
        "origin": origin,
        "frontend_version": str(body.get("version", ""))[:30],
        "backend_version": app.version,
        "snapshot": snapshot,
    }
    atomic_json(DATA / "browser-sessions" / f"{request.state.session}.json", record)
    if origin and not any(x in origin for x in ("127.0.0.1", "localhost")):
        print("Browser editor connected from " + origin, flush=True)
    return {"received": True, "backend_version": app.version}


@app.patch("/api/projects/{id}")
async def update_project(id: str, request: Request):
    changes = await request.json()
    with LOCK:
        p = project_or_404(id)
        allowed = {
            "title",
            "topic",
            "target_minutes",
            "script",
            "scenes",
            "look",
            "captions",
            "music_volume",
            "narration_id",
            "music_id",
            "review",
        }
        if set(changes) - allowed:
            raise HTTPException(422, "Unsupported project field.")
        if "script" in changes or "scenes" in changes:
            checkpoint(p)
        old_script = p["script"]
        old_story = [
            (x["id"], x["narration"], x.get("source_ids", [])) for x in p["scenes"]
        ]
        old_narration = {s["id"]: s["narration"] for s in p["scenes"]}
        for field in ["title", "topic", "script"]:
            if field in changes:
                p[field] = str(changes[field])[: 200000 if field == "script" else 180]
        if p["script"] != old_script:
            p["script_dirty"] = "scenes" not in changes
            p["review"]["facts"] = False
            p["script_approved_hash"] = None
        if "target_minutes" in changes:
            p["target_minutes"] = min(40, max(20, int(changes["target_minutes"])))
        if "scenes" in changes:
            if not isinstance(changes["scenes"], list) or len(changes["scenes"]) > 400:
                raise HTTPException(422, "A project can have up to 400 scenes.")
            p["scenes"] = [
                sanitize_scene(s, {a["id"] for a in p["assets"]})
                for s in changes["scenes"]
            ]
            rewritten = any(
                s["id"] in old_narration and s["narration"] != old_narration[s["id"]]
                for s in p["scenes"]
            )
            if rewritten:
                p["review"]["facts"] = False
                if "narration_id" not in changes:
                    p["narration_id"] = None
            if old_story != [
                (x["id"], x["narration"], x.get("source_ids", [])) for x in p["scenes"]
            ]:
                p["script_approved_hash"] = None
                if not p.get("script_dirty") or "script" in changes:
                    p["script"] = editorial.script_from_scenes(p["scenes"])
                    p["script_dirty"] = False
            p["review"]["picture"] = False
        if "look" in changes:
            if changes["look"] not in ["noir", "archive", "natural"]:
                raise HTTPException(422, "Unknown visual look.")
            p["look"] = changes["look"]
        if "captions" in changes:
            p["captions"] = bool(changes["captions"])
        if "music_volume" in changes:
            p["music_volume"] = min(0.5, max(0, float(changes["music_volume"])))
        for field in ["narration_id", "music_id"]:
            if field in changes:
                value = changes[field]
                if value is not None and not any(
                    a["id"] == value and a.get("has_audio", a["kind"] == "audio")
                    for a in p["assets"]
                ):
                    raise HTTPException(422, "Select an asset with an audio track.")
                if value != p.get(field):
                    p[field] = value
                    if field == "narration_id" and value:
                        cursor = 0
                        for s in p["scenes"]:
                            s.update(
                                audio_start=round(cursor, 3),
                                audio_duration=s["duration"],
                                timing="estimated",
                                captions=[],
                            )
                            cursor += s["duration"]
                    p["review"]["picture"] = False
        if "review" in changes:
            p["review"] = {
                k: bool(changes["review"].get(k, False))
                for k in ["facts", "rights", "disclosure", "picture"]
            }
        # Auto-rebuild the inspection timeline when scenes change on a
        # guide-driven project, so manual source assignments via the dropdown
        # are picked up without requiring a separate "Build" click.
        if "scenes" in changes and p.get("episode") and p["episode"].get("guide"):
            try:
                episode.build(p, allow_placeholders=True, inspection=True)
            except (ValueError, TypeError, KeyError):
                pass
        return save_project(p)


@app.post("/api/projects/{id}/undo")
def undo(id: str):
    with LOCK:
        p = project_or_404(id)
        if not p.get("undo"):
            raise HTTPException(
                400,
                "Nothing to undo yet. Timeline builds and saved edits create history.",
            )
        snapshot = p["undo"].pop()
        p.update(snapshot)
        if not editorial.script_approved(p):
            p["script_approved_hash"] = None
        add_message(p, "assistant", "Restored the previous saved edit.")
        return save_project(p)


@app.post("/api/projects/{id}/assemble")
def assemble(id: str):
    with LOCK:
        p = project_or_404(id)
        if (p.get("episode") or {}).get("guide"):
            raise HTTPException(
                400,
                "Use Episode setup to rebuild this guide-driven timeline. Generic filename/rotation assignment is disabled.",
            )
        checkpoint(p)
        try:
            # An amended script must not silently retain an out-of-date voice.
            if p["scenes"] and renderer.plain(p["script"]) != renderer.plain(
                "\n\n".join(s["narration"] for s in p["scenes"])
            ):
                p["narration_id"] = None
            scenes = build_scenes(p)
        except ValueError as e:
            raise HTTPException(400, str(e))
        p["scenes"] = scenes
        p["script_dirty"] = False
        p["review"]["picture"] = False
        add_message(
            p,
            "assistant",
            f"Assembled {len(scenes)} scenes from your script. Visuals use filename matching and rotation; review assignments and estimated caption timing before export.",
        )
        return save_project(p)


@app.post("/api/projects/{id}/upload")
async def upload(
    id: str,
    files: list[UploadFile] = File(...),
    episode_role: Literal["narration", "music", "sources"] | None = Form(default=None),
):
    p = project_or_404(id)
    if len(files) > 30:
        raise HTTPException(422, "Upload up to 30 files at a time.")
    folder = DATA / "media" / id
    folder.mkdir(parents=True, exist_ok=True)
    added = []
    script = None
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if episode_role and suffix in (".md", ".txt"):
            raise HTTPException(
                422,
                "This card accepts media only. Import script and guide documents in their separate cards.",
            )
        if suffix in (".md", ".txt") and p.get("episode"):
            raise HTTPException(
                422,
                "Use Episode setup's separate Script and Editing guide inputs; documents must not silently replace each other.",
            )
        allowed = {
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".mp4",
            ".mov",
            ".webm",
            ".mkv",
            ".mp3",
            ".wav",
            ".m4a",
            ".aac",
            ".ogg",
            ".flac",
            ".txt",
            ".md",
        }
        if suffix not in allowed:
            raise HTTPException(
                422,
                f"{file.filename}: unsupported format. Use images, video, audio, TXT, or Markdown.",
            )
        name = uid() + suffix
        path = folder / name
        size = 0
        try:
            with path.open("wb") as out:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > 512 * 1024 * 1024:
                        raise ValueError(
                            "Each file must be smaller than 512 MB in this prototype."
                        )
                    out.write(chunk)
            if suffix in [".txt", ".md"]:
                if size > 1000000:
                    raise ValueError("Text imports must be smaller than 1 MB.")
                script = path.read_text(encoding="utf-8-sig")[:200000]
                path.unlink()
                continue
            asset = {
                "id": uid(),
                "name": (file.filename or name)[:180],
                "path": str(path.relative_to(ROOT)),
                "url": f"/media/{id}/{name}",
                "size": size,
                "generated": False,
                "license": "",
                "thumbnail": None,
            }
            if suffix in [".png", ".jpg", ".jpeg", ".webp"]:
                with Image.open(path) as image:
                    image = ImageOps.exif_transpose(image)
                    image.load()
                    if image.width * image.height > 60000000:
                        raise ValueError(
                            "Image is too large. Resize it below 60 megapixels."
                        )
                    asset.update(
                        kind="image",
                        width=image.width,
                        height=image.height,
                        duration=0,
                        has_audio=False,
                    )
                    thumb = folder / (path.stem + "-thumb.jpg")
                    ImageOps.fit(image.convert("RGB"), (480, 270)).save(
                        thumb, quality=82
                    )
                asset["thumbnail"] = f"/media/{id}/{thumb.name}"
            else:
                info = await __import__("asyncio").to_thread(renderer.probe, path)
                asset.update(info, kind="video" if info["has_video"] else "audio")
                if info["duration"] > 21600:
                    raise ValueError("Media longer than six hours is not supported.")
                if asset["kind"] == "video":
                    thumb = folder / (path.stem + "-thumb.jpg")
                    await __import__("asyncio").to_thread(
                        renderer.thumbnail, path, thumb
                    )
                    asset["thumbnail"] = f"/media/{id}/{thumb.name}"
                if info["has_audio"]:
                    asset["waveform"] = await __import__("asyncio").to_thread(
                        renderer.waveform, path
                    )
            if episode_role in ("narration", "music") and not asset.get("has_audio"):
                raise ValueError(
                    "Narration and music require an actual audio track, not an image or silent video."
                )
            if episode_role == "sources" and asset["kind"] not in ("image", "video"):
                raise ValueError(
                    "The source-file input accepts uploaded images and videos. Keep music and narration in their own cards."
                )
            added.append(asset)
        except Exception as e:
            path.unlink(missing_ok=True)
            # Keep previously accepted files when a later file fails.
            with LOCK:
                latest = project_or_404(id)
                latest["assets"].extend(added)
                if script is not None:
                    latest["script"] = script
                save_project(latest)
            raise HTTPException(422, str(e)[:400])
        finally:
            await file.close()
    with LOCK:
        p = project_or_404(id)
        p["assets"].extend(added)
        if episode_role and not p.get("episode"):
            p["episode"] = copy.deepcopy(episode.state(p))
        if script is not None:
            checkpoint(p)
            p["script"] = script
            p["script_dirty"] = True
            p["script_origin"] = "user"
            p["script_approved_hash"] = None
            p["review"]["facts"] = False
        # Auto-rebuild the inspection timeline when media lands, so uploaded
        # source files are matched to gap scenes and cue crops are inherited.
        # No manual "First draft" click required.
        if p.get("episode") and p["episode"].get("guide"):
            try:
                episode.build(p, allow_placeholders=True, inspection=True)
            except (ValueError, TypeError, KeyError):
                # A failed rebuild must not block the upload itself. Assets are
                # already saved; the user can run First draft manually.
                pass
        return save_project(p)


@app.patch("/api/projects/{id}/assets/{asset_id}")
async def update_asset(id: str, asset_id: str, request: Request):
    body = await request.json()
    with LOCK:
        p = project_or_404(id)
        asset = next((a for a in p["assets"] if a["id"] == asset_id), None)
        if not asset:
            raise HTTPException(404, "Media not found.")
        for key in ["name", "license"]:
            if key in body:
                asset[key] = str(body[key])[: 1000 if key == "license" else 180]
        p["review"]["rights"] = False
        return save_project(p)


@app.delete("/api/projects/{id}/assets/{asset_id}")
def delete_asset(id: str, asset_id: str):
    with LOCK:
        p = project_or_404(id)
        if any(
            j["project_id"] == id and j["status"] in ("running", "queued")
            for j in JOBS.values()
        ):
            raise HTTPException(
                409, "Wait for the current operation before deleting media."
            )
        checkpoint(p)
        asset = next((a for a in p["assets"] if a["id"] == asset_id), None)
        if not asset:
            raise HTTPException(404, "Media not found.")
        p["assets"] = [a for a in p["assets"] if a["id"] != asset_id]
        for s in p["scenes"]:
            if s.get("asset_id") == asset_id:
                s["asset_id"] = None
        for key in ["narration_id", "music_id"]:
            if p.get(key) == asset_id:
                p[key] = None
        # Keep bytes for undo references and existing exported project manifests.
        p["review"]["picture"] = False
        return save_project(p)


@app.post("/api/projects/{id}/sources")
async def add_source(id: str, request: Request):
    data = await request.json()
    with LOCK:
        p = project_or_404(id)
        url = str(data.get("url", "")).strip()
        if url and (
            urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc
        ):
            raise HTTPException(
                422,
                "Use a complete http or https source URL, or leave it empty for an offline source.",
            )
        title = str(data.get("title", "")).strip()[:250]
        if not title:
            raise HTTPException(422, "Give the source a title.")
        n = (
            max(
                [
                    int(s["id"][1:])
                    for s in p["sources"]
                    if re.fullmatch(r"S\d+", s["id"])
                ]
                + [0]
            )
            + 1
        )
        p["sources"].append(
            {
                "id": f"S{n}",
                "title": title,
                "url": url[:2000],
                "notes": str(data.get("notes", ""))[:20000],
                "type": str(data.get("type", "Producer source"))[:80],
                "reviewed": False,
            }
        )
        p["review"]["facts"] = False
        return save_project(p)


@app.patch("/api/projects/{id}/sources/{source_id}")
async def patch_source(id: str, source_id: str, request: Request):
    data = await request.json()
    with LOCK:
        p = project_or_404(id)
        source = next((s for s in p["sources"] if s["id"] == source_id), None)
        if not source:
            raise HTTPException(404, "Source not found.")
        changed = False
        for field in ["title", "notes"]:
            if field in data:
                value = str(data[field])[:20000]
                changed = changed or value != source.get(field, "")
                source[field] = value
        if changed:
            source["reviewed"] = False
        if "reviewed" in data:
            source["reviewed"] = bool(data["reviewed"])
        if not editorial.script_approved(p):
            p["script_approved_hash"] = None
        p["review"]["facts"] = False
        return save_project(p)


@app.post("/api/projects/{id}/research")
def research(id: str, request: Request):
    p = project_or_404(id)
    cfg = config(request)
    if p.get("is_demo"):
        raise HTTPException(
            400,
            "Start a new project for real case research. The sample is intentionally fictional.",
        )
    if not p["topic"].strip():
        raise HTTPException(
            400, "Enter a case name, place, and any identifying context first."
        )

    def work(progress, cancelled):
        result = ai.research(cfg, p, progress)
        if not cancelled():
            with LOCK:
                latest = project_or_404(id)
                # Remap new source IDs and retain producer-added/previously reviewed sources.
                existing = latest["sources"]
                base = max(
                    [
                        int(s["id"][1:])
                        for s in existing
                        if re.fullmatch(r"S\d+", s["id"])
                    ]
                    + [0]
                )
                for n, source in enumerate(result["sources"]):
                    source["id"] = f"S{base + n + 1}"
                latest["research_report"] = result["research_report"]
                latest["sources"] = existing + result["sources"]
                latest["review"]["facts"] = False
                add_message(
                    latest,
                    "assistant",
                    "Research brief saved with source leads. Open the originals, add verified notes, and mark sources reviewed before drafting.",
                )
                save_project(latest)
        return {"sources": len(result["sources"])}

    return spawn(id, "research", work)


@app.post("/api/projects/{id}/draft")
def draft(id: str, request: Request):
    p = project_or_404(id)
    if (p.get("episode") or {}).get("guide"):
        raise HTTPException(
            400,
            "This guide-driven project preserves your supplied script and voice. Use Episode setup; destructive script/voice/transcript generation is disabled.",
        )
    cfg = config(request)
    if not any(s.get("reviewed") for s in p["sources"]):
        raise HTTPException(
            400,
            "Review at least one source in Research before drafting a factual script.",
        )

    def work(progress, cancelled):
        result = ai.draft_script(cfg, p, progress)
        if not cancelled():
            with LOCK:
                latest = project_or_404(id)
                checkpoint(latest)
                latest["script"] = result["script"]
                latest["script_origin"] = "ai"
                latest["script_approved_hash"] = None
                latest["narration_id"] = None
                latest["scenes"] = build_scenes(latest)
                latest["script_dirty"] = False
                latest["review"]["facts"] = False
                latest["review"]["picture"] = False
                add_message(
                    latest,
                    "assistant",
                    result.get(
                        "note",
                        "Draft ready. Review every claim and scene before publication.",
                    ),
                )
                save_project(latest)
        return {"draft_ready": True}

    return spawn(id, "script", work)


@app.post("/api/projects/{id}/narrate")
def narrate(id: str, request: Request):
    p = project_or_404(id)
    if (p.get("episode") or {}).get("guide"):
        raise HTTPException(
            400,
            "This guide-driven project preserves your supplied script and voice. Use Episode setup; destructive script/voice/transcript generation is disabled.",
        )
    cfg = config(request)
    if not p["scenes"]:
        raise HTTPException(400, "Build a timeline first.")
    if message := editorial.narration_gate(p):
        raise HTTPException(400, message)

    def work(progress, cancelled):
        asset, scenes = ai.generate_narration(cfg, p, progress, cancelled)
        if not cancelled():
            with LOCK:
                latest = project_or_404(id)
                checkpoint(latest)
                latest["assets"].append(asset)
                latest.update(narration_id=asset["id"], scenes=scenes)
                latest["review"]["disclosure"] = False
                latest["review"]["picture"] = False
                add_message(
                    latest,
                    "assistant",
                    "AI narration generated and aligned by scene. Caption timing inside each scene is estimated; transcribe the voice track for tighter timing. Disclose synthetic narration to viewers.",
                )
                save_project(latest)
        return {"narration_ready": True}

    return spawn(id, "narration", work)


@app.post("/api/projects/{id}/transcribe/{asset_id}")
def transcribe(id: str, asset_id: str, request: Request):
    p = project_or_404(id)
    if (p.get("episode") or {}).get("guide"):
        raise HTTPException(
            400,
            "This guide-driven project preserves your supplied script and voice. Use Episode setup; destructive script/voice/transcript generation is disabled.",
        )
    cfg = config(request)
    asset = next((a for a in p["assets"] if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(404, "Media not found.")

    def work(progress, cancelled):
        segments = ai.transcribe(cfg, p, asset, progress, cancelled)
        scenes = production.transcript_scenes(p, asset, segments)
        if not cancelled():
            with LOCK:
                latest = project_or_404(id)
                checkpoint(latest)
                latest.update(
                    scenes=scenes,
                    script="\n\n".join(s["narration"] for s in scenes),
                    script_dirty=False,
                    script_origin="transcript",
                    script_approved_hash=None,
                    narration_id=asset_id,
                )
                latest["review"]["picture"] = False
                latest["review"]["facts"] = False
                add_message(
                    latest,
                    "assistant",
                    "Transcription assembled into a source-aligned timeline. This replaces the previous timeline (Undo is available). Review recognition accuracy and every cut.",
                )
                save_project(latest)
        return {"scenes": len(scenes)}

    return spawn(id, "transcription", work)


def apply_plan(p, plan, ai_generated=False):
    if (p.get("episode") or {}).get("guide"):
        for op in plan.get("operations", []):
            if op.get("op") in ("move_scene", "delete_scene") or (
                op.get("op") == "update_scene"
                and set(op.get("fields", {}))
                - {"title", "show_title", "motion", "source_ids"}
            ):
                raise ValueError(
                    "This edit would change the preserved narration or guide timing. Change cue positions and source ranges in Episode setup, then rebuild. Look, caption, music-level, and source-annotation edits are supported without changing your voice."
                )
    checkpoint(p)
    narration_changed = False
    story_changed = False
    for op in plan.get("operations", [])[:500]:
        kind = op.get("op")
        if kind == "set_look" and op.get("value") in ("noir", "archive", "natural"):
            p["look"] = op["value"]
        elif kind == "set_captions":
            p["captions"] = bool(op.get("value"))
        elif kind == "set_music_volume":
            value = float(op.get("value"))
            if not __import__("math").isfinite(value) or not 0 <= value <= 0.5:
                raise ValueError("Music level must be between 0% and 50%.")
            p["music_volume"] = value
        elif kind in ("update_scene", "move_scene", "delete_scene"):
            scene = next(
                (s for s in p["scenes"] if s["id"] == op.get("scene_id")), None
            )
            if not scene:
                raise ValueError(
                    "The edit plan referenced a scene that does not exist. No edit was saved."
                )
            if kind == "delete_scene":
                story_changed = True
                p["scenes"].remove(scene)
            elif kind == "move_scene":
                story_changed = True
                p["scenes"].remove(scene)
                p["scenes"].insert(
                    min(len(p["scenes"]), max(0, int(op.get("index", 0)))), scene
                )
            else:
                fields = {
                    k: v
                    for k, v in op.get("fields", {}).items()
                    if k
                    in [
                        "title",
                        "chapter",
                        "duration",
                        "narration",
                        "show_title",
                        "motion",
                        "transition",
                        "asset_id",
                        "trim_start",
                        "source_ids",
                    ]
                }
                if "narration" in fields and fields["narration"] != scene["narration"]:
                    narration_changed = True
                    story_changed = True
                    fields["captions"] = []
                    fields["timing"] = "estimated"
                if "source_ids" in fields and fields["source_ids"] != scene.get(
                    "source_ids", []
                ):
                    story_changed = True
                scene.update(fields)
                scene.update(sanitize_scene(scene, {a["id"] for a in p["assets"]}))
        else:
            raise ValueError(
                "The AI requested an unsupported operation. No changes were saved."
            )
    if narration_changed:
        p["narration_id"] = None
        p["review"]["facts"] = False
    if story_changed:
        if p.get("script_dirty"):
            raise ValueError(
                "Apply or undo your unapplied script edits before making story-changing commands."
            )
        p["script"] = editorial.script_from_scenes(p["scenes"])
        p["script_dirty"] = False
        p["script_approved_hash"] = None
        if ai_generated:
            p["script_origin"] = "ai"
    p["review"]["picture"] = False
    return narration_changed


def local_plan(instruction, p):
    text = instruction.strip().lower()
    ops = []
    message = ""
    if re.search(r"(hide|disable|turn off|remove).*(caption|subtitle)", text):
        ops = [{"op": "set_captions", "value": False}]
        message = "Captions are off."
    elif re.search(r"(show|enable|turn on).*(caption|subtitle)", text):
        ops = [{"op": "set_captions", "value": True}]
        message = "Captions are on."
    elif re.search(r"(hide|remove|show|enable).*(all )?titles", text):
        show = bool(re.search(r"^(show|enable)", text))
        ops = [
            {"op": "update_scene", "scene_id": s["id"], "fields": {"show_title": show}}
            for s in p["scenes"]
        ]
        message = ("Showing" if show else "Hiding") + " scene titles."
    elif re.search(r"(archive|noir|natural) (look|style)", text) or re.search(
        r"(look|style).*\b(archive|noir|natural)\b", text
    ):
        look = next(x for x in ("archive", "noir", "natural") if x in text)
        ops = [{"op": "set_look", "value": look}]
        message = f"Applied the {look} look."
    elif match := re.search(r"(?:music|background).*?(\d+(?:\.\d+)?)\s*%", text):
        level = float(match[1])
        if not 0 <= level <= 50:
            raise ValueError("Music level must be between 0% and 50%.")
        ops = [{"op": "set_music_volume", "value": level / 100}]
        message = f"Music level is {level:g}%. It still ducks under narration; listen to the actual MP4."
    elif match := re.search(
        r"scene\s+(\d+).*?(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b", text
    ):
        index, duration = int(match[1]) - 1, float(match[2])
        if not 0 <= index < len(p["scenes"]):
            raise ValueError("That scene number does not exist.")
        ops = [
            {
                "op": "update_scene",
                "scene_id": p["scenes"][index]["id"],
                "fields": {"duration": duration},
            }
        ]
        message = f"Scene {index + 1} is now {duration:g} seconds. Existing voice audio is trimmed or padded to fit; check the cut."
    elif match := re.search(r"move scene (\d+) to (?:position )?(\d+)", text):
        src, dest = int(match[1]) - 1, int(match[2]) - 1
        if not 0 <= src < len(p["scenes"]) or not 0 <= dest < len(p["scenes"]):
            raise ValueError("That scene position does not exist.")
        ops = [{"op": "move_scene", "scene_id": p["scenes"][src]["id"], "index": dest}]
        message = f"Moved scene {src + 1} to position {dest + 1}, including its narration slice."
    if not ops:
        return None
    return {"operations": ops, "message": message}


@app.post("/api/projects/{id}/command")
async def command(id: str, request: Request):
    data = await request.json()
    instruction = str(data.get("instruction", "")).strip()[:3000]
    if not instruction:
        raise HTTPException(422, "Enter an editing instruction.")
    p = project_or_404(id)
    try:
        plan = local_plan(instruction, p)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if plan:
        with LOCK:
            p = project_or_404(id)
            try:
                apply_plan(p, plan)
            except (ValueError, TypeError) as e:
                raise HTTPException(400, str(e))
            add_message(p, "user", instruction)
            add_message(p, "assistant", plan["message"])
            return {"project": save_project(p)}
    cfg = config(request)

    def work(progress, cancelled):
        plan = ai.edit_plan(cfg, p, instruction, progress)
        if not cancelled():
            with LOCK:
                latest = project_or_404(id)
                changed = apply_plan(latest, plan, ai_generated=True)
                add_message(latest, "user", instruction)
                note = plan.get("message", "Edit plan applied.")
                if changed:
                    note += " Narration text changed: the previous voice track was detached. Re-record or regenerate it before export."
                add_message(latest, "assistant", note)
                save_project(latest)
        return {"edit_applied": True}

    return spawn(id, "direction", work)


class ExportOptions(BaseModel):
    resolution: Literal["480p", "720p", "1080p"] = "720p"
    draft: bool = True
    captions: bool = True
    allow_guided_gaps: bool = False
    allow_inspection: bool = False


@app.post("/api/projects/{id}/render")
def export(id: str, options: ExportOptions):
    p = project_or_404(id)
    if ((p.get("episode") or {}).get("plan") or {}).get("mode") == "inspection":
        if not options.draft or not options.allow_inspection:
            raise HTTPException(
                400,
                "This is an unreviewed inspection plan. Explicitly choose an inspection draft; final export requires actual reviews and a reviewed-plan rebuild.",
            )
    report = editorial.inspect(p)
    issues = [
        i
        for i in report["issues"]
        if i["blocks_draft"] or (not options.draft and i["blocks_final"])
    ]
    if issues:
        raise HTTPException(
            400, " ".join(i["title"] + ": " + i["detail"] for i in issues[:2])
        )
    if (
        options.draft
        and (p.get("episode") or {}).get("guide")
        and any(not s.get("asset_id") for s in p["scenes"])
        and not options.allow_guided_gaps
    ):
        raise HTTPException(
            400,
            "This guide plan has missing visual coverage. Explicitly allow marked gap cards for an internal review-only video; CASEFILE will not substitute or loop unrelated footage.",
        )
    return spawn(
        id,
        "render",
        lambda progress, cancelled: write_export(
            p, options.model_dump(), progress, cancelled
        ),
    )


def write_export(project, options, progress, cancelled):
    export_id = uid()
    folder = DATA / "exports" / export_id
    folder.mkdir(parents=True, exist_ok=True)
    with RENDER_LOCK:
        try:
            if cancelled():
                raise RuntimeError("Render cancelled before it started.")
            out = folder / "documentary.mp4"
            info = renderer.render(project, options, out, progress, cancelled)
            if cancelled():
                raise RuntimeError("Render cancelled. No output was published.")
            report = editorial.inspect(project)
            (folder / "captions.srt").write_text(renderer.project_srt(project))
            (folder / "sources.md").write_text(source_notes(project))
            (folder / "preflight.md").write_text(
                editorial.report_markdown(project, report)
            )
            (folder / "chapters.txt").write_text(editorial.chapter_text(project))
            (folder / "publication-notes.md").write_text(
                editorial.publication_notes(project)
            )
            if project.get("episode"):
                (folder / "episode-plan.md").write_text(episode.markdown(project))
            atomic_json(folder / "preflight.json", report)
            atomic_json(
                folder / "project.json",
                {k: v for k, v in project.items() if k != "undo"},
            )
            record = {
                "id": export_id,
                "title": project["title"],
                "created_at": now(),
                "draft": options["draft"],
                "url": f"/exports/{export_id}/documentary.mp4",
                "captions_url": f"/exports/{export_id}/captions.srt",
                "sources_url": f"/exports/{export_id}/sources.md",
                "preflight_url": f"/exports/{export_id}/preflight.md",
                "chapters_url": f"/exports/{export_id}/chapters.txt",
                "publication_url": f"/exports/{export_id}/publication-notes.md",
                **info,
            }
            if project.get("episode"):
                record["episode_plan_url"] = f"/exports/{export_id}/episode-plan.md"
                record["marked_gaps_allowed"] = options.get("allow_guided_gaps", False)
                record["inspection_only"] = (
                    (project.get("episode") or {}).get("plan") or {}
                ).get("mode") == "inspection"
            with LOCK:
                latest = project_or_404(project["id"])
                latest["exports"].insert(0, record)
                save_project(latest)
            return record
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise


class ProductionOptions(BaseModel):
    allow_paid: bool = False
    generate_voice: bool = False
    auto_assign_visuals: bool = True
    allow_placeholders: bool = False
    allow_silent: bool = False
    render: bool = True
    resolution: Literal["480p", "720p", "1080p"] = "720p"
    source_asset_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{16}$")
    max_voice_characters: int = Field(default=45000, ge=1000, le=90000)


@app.post("/api/projects/{id}/production-plan")
def production_plan(id: str, options: ProductionOptions, request: Request):
    p = project_or_404(id)
    if (p.get("episode") or {}).get("guide"):
        raise HTTPException(
            400,
            "Use Episode setup for this guide-driven project; generic footage rotation is disabled.",
        )
    return production.plan(
        p,
        production.Options(**options.model_dump()),
        public_config(request)["connected"],
    )


@app.post("/api/projects/{id}/produce")
def auto_produce(id: str, options: ProductionOptions, request: Request):
    p = project_or_404(id)
    if (p.get("episode") or {}).get("guide"):
        raise HTTPException(
            400,
            "This project follows an editing guide. Use Episode setup to build and render; generic footage rotation is disabled.",
        )
    cfg = copy.deepcopy(SESSIONS.get(request.state.session))
    opts = production.Options(**options.model_dump())
    return spawn(
        id,
        "production",
        lambda progress, cancelled: production.run(
            id, opts, cfg, progress, cancelled, write_export
        ),
    )


@app.post("/api/projects/{id}/approve-script")
async def approve_script(id: str, request: Request):
    body = await request.json()
    if body.get("acknowledge") is not True:
        raise HTTPException(
            400, "Explicitly confirm that you reviewed the script against its sources."
        )
    with LOCK:
        p = project_or_404(id)
        problems = editorial.script_problems(p)
        if not p.get("script", "").strip():
            raise HTTPException(400, "There is no script to approve.")
        if problems["unresolved"] or problems["unknown_sources"]:
            raise HTTPException(
                400,
                "Resolve unverified markers and broken source references before approving the AI script.",
            )
        if p.get("script_origin") == "ai" and not any(
            s.get("reviewed") for s in p.get("sources", [])
        ):
            raise HTTPException(
                400,
                "Review the original sources before approving an AI-generated factual script.",
            )
        used = {s["id"]: s for s in p.get("sources", [])}
        if any(
            not used[ref].get("reviewed")
            for ref in problems["references"]
            if ref in used
        ):
            raise HTTPException(
                400, "Review all cited sources before approving the script."
            )
        checkpoint(p)
        p["script_approved_hash"] = editorial.approval_fingerprint(p)
        add_message(
            p,
            "assistant",
            "Producer approved the script text for narration. This approval does not independently verify case facts or clear media rights.",
        )
        return save_project(p)


@app.get("/api/projects/{id}/preflight")
def preflight(id: str):
    return editorial.inspect(project_or_404(id))


@app.get("/api/projects/{id}/preflight.md")
def preflight_download(id: str):
    return PlainTextResponse(
        editorial.report_markdown(project_or_404(id)),
        headers={"Content-Disposition": 'attachment; filename="preflight.md"'},
    )


@app.get("/api/projects/{id}/chapters.txt")
def chapters_download(id: str):
    return PlainTextResponse(
        editorial.chapter_text(project_or_404(id)),
        headers={"Content-Disposition": 'attachment; filename="chapters.txt"'},
    )


def source_notes(p):
    text = f"# {p['title']}\n\nExported {now()}\n\n"
    if p.get("is_demo"):
        text += "**FICTIONAL DEMONSTRATION. All sample imagery is AI-generated illustration, not real evidence.**\n\n"
    text += "## Sources\n\n"
    for s in p["sources"]:
        text += f"### [{s['id']}] {s['title']}\n{s.get('url', 'Offline source')}\n\nReviewed: {s.get('reviewed', False)}\n\n{s.get('notes', '')}\n\n"
    text += "## Scene references\n\n"
    for n, scene in enumerate(p.get("scenes", [])):
        refs = ", ".join(scene.get("source_ids", [])) or "Not linked"
        text += f"- Scene {n + 1}: {scene.get('title', '')} — {refs}\n"
    text += "\n## Media rights notes\n\n"
    for a in p["assets"]:
        text += f"- {a['name']}: {a.get('license') or 'RIGHTS NOT DOCUMENTED'}\n"
    text += "\n## Editorial checklist\n\n" + "\n".join(
        f"- {k}: {v}" for k, v in p["review"].items()
    )
    text += "\n\nThis file records producer review, not independent legal clearance or fact verification.\n"
    return text


@app.get("/api/projects/{id}/captions.srt")
def captions_download(id: str):
    p = project_or_404(id)
    return PlainTextResponse(
        renderer.project_srt(p),
        headers={"Content-Disposition": 'attachment; filename="captions.srt"'},
    )


@app.get("/api/projects/{id}/sources.md")
def sources_download(id: str):
    return PlainTextResponse(
        source_notes(project_or_404(id)),
        headers={"Content-Disposition": 'attachment; filename="source-notes.md"'},
    )


@app.get("/api/projects/{id}/project.json")
def project_download(id: str):
    p = project_or_404(id)
    p.pop("undo", None)
    return JSONResponse(
        p,
        headers={"Content-Disposition": 'attachment; filename="casefile-project.json"'},
    )


class ClearSessionOptions(BaseModel):
    confirm_download_saved: bool = False


@app.delete("/api/projects/{id}/session")
def clear_session(id: str, options: ClearSessionOptions):
    """Explicit post-save cleanup. Never follows client paths or touches originals."""
    if not options.confirm_download_saved:
        raise HTTPException(
            422,
            "Confirm that you saved and checked the output/backups you need before clearing this temporary session.",
        )
    with LOCK:
        p = project_or_404(id)
        if p.get("is_demo"):
            raise HTTPException(
                400, "The shared fictional sample is not a user session to clear."
            )
        if any(
            j.get("project_id") == id and j.get("status") in ("running", "queued")
            for j in JOBS.values()
        ):
            raise HTTPException(
                409, "Finish or cancel the current job before clearing this session."
            )
        removals = []
        media = DATA / "media" / id
        if media.exists():
            if media.is_symlink() or not media.resolve().is_relative_to(
                (DATA / "media").resolve()
            ):
                raise HTTPException(
                    409, "Unsafe session media path; no files were cleared."
                )
            removals.append(media)
        for record in p.get("exports", []):
            eid = str(record.get("id", ""))
            if not re.fullmatch(r"[a-f0-9]{16}", eid):
                continue
            folder = DATA / "exports" / eid
            if not folder.exists():
                continue
            if folder.is_symlink() or not folder.resolve().is_relative_to(
                (DATA / "exports").resolve()
            ):
                raise HTTPException(409, "Unsafe export path; no files were cleared.")
            manifest = folder / "project.json"
            try:
                owner = json.loads(manifest.read_text()).get("id")
            except (OSError, ValueError):
                owner = None
            if owner == id:
                removals.append(folder)
        owned_jobs = [key for key, job in JOBS.items() if job.get("project_id") == id]
        for folder in removals:
            shutil.rmtree(folder)
        for key in owned_jobs:
            if re.fullmatch(r"[a-f0-9]{16}", key):
                (DATA / "jobs" / f"{key}.json").unlink(missing_ok=True)
            JOBS.pop(key, None)
        for file in (DATA / "recovery-backups").glob(f"{id}-*.json"):
            file.unlink(missing_ok=True)
        for file in (DATA / "browser-sessions").glob("*.json"):
            try:
                record = json.loads(file.read_text())
                if (record.get("snapshot") or {}).get("id") == id:
                    file.unlink(missing_ok=True)
            except (OSError, ValueError, AttributeError):
                pass
        (DATA / "projects" / f"{id}.json").unlink()
        return {
            "deleted": True,
            "project_id": id,
            "folders_removed": len(removals),
            "jobs_removed": len(owned_jobs),
            "original_computer_files": "untouched; only this server's working copies were cleared",
        }


@app.api_route(
    "/api/projects/{id}/exports/{export_id}/download", methods=["GET", "HEAD"]
)
def download_export(id: str, export_id: str):
    """Save a completed export; never render again, approve it or delete it."""
    p = project_or_404(id)
    if not re.fullmatch(r"[a-f0-9]{16}", export_id):
        raise HTTPException(404, "Rendered video not found.")
    record = next(
        (item for item in p.get("exports", []) if item.get("id") == export_id), None
    )
    if record is None:
        raise HTTPException(
            404, "This completed export does not belong to the selected project."
        )
    folder = (DATA / "exports" / export_id).resolve()
    if not folder.is_relative_to((DATA / "exports").resolve()):
        raise HTTPException(404, "Rendered video is unavailable.")
    file = (folder / "documentary.mp4").resolve()
    if not file.is_relative_to(folder) or not file.is_file():
        raise HTTPException(
            404,
            "The render record exists, but its MP4 is not available on this server. A project JSON backup does not contain the video bytes. Nothing was deleted by this download request.",
        )
    title = (
        re.sub(r"[^A-Za-z0-9 _-]", "", str(p.get("title", "Casefile-video"))).strip()[
            :110
        ]
        or "Casefile-video"
    )
    suffix = (
        "-unreviewed-inspection"
        if record.get("inspection_only")
        else "-review-draft"
        if record.get("draft")
        else ""
    )
    return FileResponse(
        file,
        media_type="video/mp4",
        filename=title + suffix + ".mp4",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@app.get("/api/projects/{id}/jobs")
def get_jobs(id: str):
    project_or_404(id)
    return sorted(
        [copy.deepcopy(j) for j in JOBS.values() if j["project_id"] == id],
        key=lambda j: j["created_at"],
        reverse=True,
    )[:25]


@app.post("/api/jobs/{id}/cancel")
def cancel(id: str):
    if id not in JOBS:
        raise HTTPException(404, "Job not found.")
    if JOBS[id]["status"] not in ("running", "queued"):
        raise HTTPException(400, "This operation has already finished.")
    job_update(
        id,
        cancel_requested=True,
        message="Cancellation requested; waiting for the current step to stop.",
    )
    return JOBS[id]


async def episode_json(request):
    try:
        data = await request.json()
    except ValueError:
        raise HTTPException(422, "Send a JSON object.")
    if not isinstance(data, dict):
        raise HTTPException(422, "Send a JSON object.")
    return data


class EpisodeDocument(BaseModel):
    role: Literal["script", "guide", "timings"]
    text: str = Field(max_length=32000000)
    filename: str = Field(default="document.md", max_length=200)


def episode_result(p):
    return {"project": save_project(p), "analysis": episode.analyze(p)}


@app.get("/api/projects/{id}/episode")
def episode_analysis(id: str):
    return episode.analyze(project_or_404(id))


@app.post("/api/projects/{id}/episode/import")
def episode_import(id: str, body: EpisodeDocument):
    with LOCK:
        p = project_or_404(id)
        checkpoint(p)
        try:
            episode.import_document(p, body.role, body.text, body.filename)
        except (ValueError, TypeError, KeyError) as e:
            raise HTTPException(422, str(e))
        return episode_result(p)


@app.patch("/api/projects/{id}/episode/source/{source_id}")
async def episode_source(id: str, source_id: str, request: Request):
    body = await episode_json(request)
    with LOCK:
        p = project_or_404(id)
        checkpoint(p)
        try:
            episode.bind_source(p, source_id, body)
            episode.resolve_automatic_source_links(p)
            # Auto-rebuild the inspection timeline after a source binding
            # changes, so assigned media is reflected in the plan and the
            # source_label stays aligned with the cue.
            if p.get("episode") and p["episode"].get("guide"):
                try:
                    episode.build(p, allow_placeholders=True, inspection=True)
                except (ValueError, TypeError, KeyError):
                    pass
        except (ValueError, TypeError, KeyError) as e:
            raise HTTPException(422, str(e))
        return episode_result(p)


@app.patch("/api/projects/{id}/episode/cue/{cue_id}")
async def episode_cue(id: str, cue_id: str, request: Request):
    body = await episode_json(request)
    with LOCK:
        p = project_or_404(id)
        checkpoint(p)
        try:
            episode.review_cue(p, cue_id, body)
        except (ValueError, TypeError, KeyError) as e:
            raise HTTPException(422, str(e))
        return episode_result(p)


@app.patch("/api/projects/{id}/episode/choice/{cue_id}")
async def episode_choice(id: str, cue_id: str, request: Request):
    body = await episode_json(request)
    with LOCK:
        p = project_or_404(id)
        checkpoint(p)
        try:
            episode.choose_source(p, cue_id, body)
            # Auto-rebuild the inspection timeline after a source choice
            # changes, so the selected media is reflected in the plan and the
            # source_label stays aligned with the cue.
            if p.get("episode") and p["episode"].get("guide"):
                try:
                    episode.build(p, allow_placeholders=True, inspection=True)
                except (ValueError, TypeError, KeyError):
                    pass
        except (ValueError, TypeError, KeyError) as e:
            raise HTTPException(422, str(e))
        return episode_result(p)


@app.patch("/api/projects/{id}/episode/options")
async def episode_options(id: str, request: Request):
    body = await episode_json(request)
    if not isinstance(body, dict) or set(body) - {
        "brief",
        "narration_id",
        "music_id",
        "music_volume",
        "captions",
        "confirm_timing",
        "confirm_transcript",
        "clear_timings",
    }:
        raise HTTPException(422, "Unsupported episode option.")
    with LOCK:
        p = project_or_404(id)
        checkpoint(p)
        e = copy.deepcopy(episode.state(p))
        if body.get("clear_timings") is True:
            e.pop("timings", None)
            e.pop("timing_reviewed_digest", None)
        if "brief" in body:
            e["brief"] = str(body["brief"])[:5000]
        for role in ("narration_id", "music_id"):
            if role in body:
                asset = next(
                    (
                        a
                        for a in p["assets"]
                        if a["id"] == body[role]
                        and a.get("has_audio", a["kind"] == "audio")
                    ),
                    None,
                )
                if body[role] is not None and not asset:
                    raise HTTPException(
                        422, "Choose an uploaded file with an audio track."
                    )
                if body[role] is not None and body[role] in {
                    b.get("asset_id") for b in e.get("bindings", {}).values()
                }:
                    raise HTTPException(
                        422,
                        "Keep source footage audio muted. Choose a separate finished narration/music file.",
                    )
                if p.get(role) != body[role]:
                    e.pop("timing_reviewed_digest", None)
                    if role == "narration_id":
                        for review in e.get("reviews", {}).values():
                            review.pop("narration_start", None)
                            if "narration_end" in review:
                                review.pop("narration_end", None)
                                review["reviewed"] = False
                p[role] = body[role]
        if p.get("narration_id") and p.get("narration_id") == p.get("music_id"):
            raise HTTPException(422, "Narration and music must be different files.")
        if "music_volume" in body:
            try:
                value = float(body["music_volume"])
                if not __import__("math").isfinite(value) or not 0 <= value <= 0.5:
                    raise ValueError()
                p["music_volume"] = value
            except (TypeError, ValueError):
                raise HTTPException(422, "Music level must be between 0 and 0.5.")
        if "captions" in body:
            p["captions"] = body["captions"] is True
        p["episode"] = e
        if body.get("confirm_timing") is True:
            report = episode.analyze(p)
            if (
                not report["has_voice"]
                or report["errors"]
                or not report["has_script"]
                or not report["has_guide"]
            ):
                raise HTTPException(
                    422,
                    "Upload the matching narration and resolve cue matching/timing errors before confirming.",
                )
            e["timing_reviewed_digest"] = episode.input_digest(p)
        elif "confirm_timing" in body:
            e.pop("timing_reviewed_digest", None)
        if body.get("confirm_transcript") is True:
            report = episode.analyze(p)
            if not report["has_voice"] or report["errors"]:
                raise HTTPException(
                    422,
                    "Upload the exact matching narration and resolve timing errors before confirming transcript review.",
                )
            e["transcript_reviewed_digest"] = episode.input_digest(p)
        elif "confirm_transcript" in body:
            e.pop("transcript_reviewed_digest", None)
        p["review"]["picture"] = False
        return episode_result(p)


@app.post("/api/projects/{id}/episode/autolink")
def episode_autolink(id: str):
    with LOCK:
        p = project_or_404(id)
        checkpoint(p)
        for source_id, asset_id in episode.suggestions(p).items():
            if (
                not episode.state(p)
                .get("bindings", {})
                .get(source_id, {})
                .get("asset_id")
            ):
                episode.bind_source(p, source_id, {"asset_id": asset_id})
        episode.resolve_automatic_source_links(p)
        return episode_result(p)


@app.post("/api/projects/{id}/episode/first-draft")
def first_draft(id: str):
    """One explicit inspection action: available files -> match -> build -> preview.

    Never records rights/context approval, invents missing footage, or requires
    final-publication sign-offs merely to see the selected source.
    """
    with LOCK:
        p = project_or_404(id)
        if p.get("is_demo"):
            raise HTTPException(
                422,
                "Start your own project rather than replacing the fictional sample.",
            )
        e = episode.state(p)
        if not e.get("script") or not e.get("guide"):
            raise HTTPException(
                422,
                "Add your narration script and editing guide first. They are separate inputs.",
            )
        available = set()
        for asset in p.get("assets", []):
            try:
                path = (ROOT / asset.get("path", "")).resolve()
                exists = (
                    bool(asset.get("path"))
                    and path.is_relative_to(ROOT)
                    and path.is_file()
                )
            except (ValueError, OSError):
                exists = False
            asset["available_on_server"] = exists
            if exists:
                available.add(asset["id"])
        options_project = {
            **p,
            "assets": [a for a in p["assets"] if a["id"] in available],
        }
        for sid, aid in episode.suggestions(options_project).items():
            bound = episode.state(p).get("bindings", {}).get(sid, {}).get("asset_id")
            if bound not in available:
                episode.bind_source(p, sid, {"asset_id": aid})
        corrections = episode.resolve_automatic_source_links(p)
        report = episode.analyze(p)
        if report["errors"]:
            raise HTTPException(422, " ".join(report["errors"]))
        if not report["inspection_cues"]:
            visuals = [a for a in p["assets"] if a["kind"] in ("image", "video")]
            if visuals and not any(a["id"] in available for a in visuals):
                raise HTTPException(
                    422,
                    "The source names are saved, but their uploaded copies are not available on this server. Your computer originals were not deleted. Add one original source photo/video to verify the preview; checking approvals cannot restore missing bytes.",
                )
            if not visuals:
                raise HTTPException(
                    422,
                    "Add at least one source photo or video first. We will not call an all-placeholder timeline a visual draft.",
                )
            raise HTTPException(
                422,
                "Files are present, but no guide placement can use them yet. Match a filename to its source ID or check the source-choice/range explanation in More settings. No approval checkboxes are needed for inspection.",
            )
        plan = e.get("plan") or {}
        used_missing = any(
            s.get("asset_id") and s["asset_id"] not in available
            for s in p.get("scenes", [])
        )
        reused = (
            report["plan_current"]
            and plan.get("mode") == "inspection"
            and not used_missing
            and any(s.get("asset_id") for s in p.get("scenes", []))
        )
        if not reused:
            checkpoint(p)
            try:
                episode.build(p, allow_placeholders=True, inspection=True)
            except (ValueError, TypeError, KeyError) as error:
                raise HTTPException(422, str(error))
        start = 0.0
        first = None
        for scene in p["scenes"]:
            if scene.get("asset_id"):
                first = {
                    "scene_id": scene["id"],
                    "time": start + min(1 / renderer.FPS, scene["duration"] / 2),
                }
                break
            start += scene["duration"]
        if first is None:
            raise HTTPException(
                422,
                "No real visual was produced. Check a linked file and its permitted range; the empty plan was not saved as a successful draft.",
            )
        result = episode_result(p)
        result["preview"] = first
        result["reused_current_plan"] = bool(reused)
        result["automatic_source_corrections"] = corrections
        return result


@app.post("/api/projects/{id}/episode/build")
async def episode_build(id: str, request: Request):
    body = await episode_json(request)
    with LOCK:
        p = project_or_404(id)
        checkpoint(p)
        try:
            episode.build(
                p,
                allow_placeholders=body.get("allow_placeholders") is True,
                inspection=body.get("inspection") is True,
            )
        except (ValueError, TypeError, KeyError) as e:
            raise HTTPException(422, str(e))
        return episode_result(p)


@app.get("/api/projects/{id}/episode/plan.md")
def episode_report(id: str):
    return PlainTextResponse(
        episode.markdown(project_or_404(id)),
        headers={"Content-Disposition": 'attachment; filename="episode-plan.md"'},
    )


app.mount("/assets", StaticFiles(directory=ROOT / "web/assets"), name="assets")
app.mount("/media", StaticFiles(directory=DATA / "media"), name="media")
app.mount("/exports", StaticFiles(directory=DATA / "exports"), name="exports")


@app.get("/{path:path}")
def index(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "API endpoint not found.")
    return FileResponse(ROOT / "web/index.html")
