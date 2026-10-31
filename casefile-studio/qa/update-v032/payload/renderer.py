"""Deterministic FFmpeg renderer. No AI calls, shell interpolation, or remote media."""

from __future__ import annotations
import json, shutil, subprocess, tempfile, textwrap
from pathlib import Path
from typing import Callable
from editorial import strip_references
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FPS = 24
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def plain(text: str) -> str:
    return strip_references(text)


def probe(path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=40,
    )
    if result.returncode:
        raise ValueError(
            "This media file could not be decoded. Try MP4, WAV, MP3, PNG, or JPEG."
        )
    data = json.loads(result.stdout)
    video = next(
        (
            s
            for s in data.get("streams", [])
            if s["codec_type"] == "video"
            and not s.get("disposition", {}).get("attached_pic")
        ),
        None,
    )
    audio = next(
        (s for s in data.get("streams", []) if s["codec_type"] == "audio"), None
    )
    return {
        "video_duration": float(video["duration"])
        if video and video.get("duration") not in (None, "N/A")
        else None,
        "audio_duration": float(audio["duration"])
        if audio and audio.get("duration") not in (None, "N/A")
        else None,
        "duration": float(
            data.get("format", {}).get("duration")
            or (video or audio or {}).get("duration")
            or 0
        ),
        "width": (video or {}).get("width"),
        "height": (video or {}).get("height"),
        "has_audio": bool(audio),
        "has_video": bool(video),
    }


def waveform(path: Path, bins=160):
    out = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "800",
            "-f",
            "f32le",
            "pipe:1",
        ],
        capture_output=True,
        timeout=120,
    )
    samples = np.frombuffer(out.stdout, dtype=np.float32)
    if len(samples) == 0:
        return []
    values = np.array(
        [
            float(np.max(np.abs(c))) if len(c) else 0
            for c in np.array_split(samples, bins)
        ]
    )
    return (values / max(float(values.max()), 0.001)).round(3).tolist()


def thumbnail(path: Path, out: Path):
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=480:270:force_original_aspect_ratio=increase,crop=480:270",
            str(out),
        ],
        capture_output=True,
        timeout=40,
        check=True,
    )


def scene_captions(scene: dict):
    duration = float(scene.get("duration", 5))
    if scene.get("captions_exact") or scene.get("captions"):
        return [
            {
                "start": max(0, float(c["start"])),
                "end": min(duration, float(c["end"])),
                "text": plain(c["text"]),
            }
            for c in scene.get("captions", [])
            if float(c["start"]) < duration and float(c["end"]) > float(c["start"])
        ]
    words = plain(scene.get("narration", "")).split()
    if not words:
        return []
    groups = [words[i : i + 9] for i in range(0, len(words), 9)]
    cursor = 0
    cues = []
    for g in groups:
        start = duration * cursor / len(words)
        cursor += len(g)
        cues.append(
            {"start": start, "end": duration * cursor / len(words), "text": " ".join(g)}
        )
    return cues


def srt_time(sec):
    ms = round(sec * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def project_srt(project):
    e = project.get("episode") or {}
    imported = (e.get("timings") or {}).get("captions")
    if e.get("guide") and imported:
        # Export the global supplied caption track once, not repeated fragments
        # split by visual cuts. Independent of whether burn-in captions are ON.
        return "\n".join(
            f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n"
            for i, c in enumerate(imported, 1)
        )
    cues, offset = [], 0.0
    for scene in project.get("scenes", []):
        for c in scene_captions(scene):
            cues.append(
                f"{len(cues) + 1}\n{srt_time(offset + c['start'])} --> {srt_time(offset + c['end'])}\n{c['text']}\n"
            )
        offset += scene["duration"]
    return "\n".join(cues)


def ass_time(sec):
    cs = round(sec * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def write_ass(scene, path, width, height):
    font_size = int(height * 0.039)
    content = f"""[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,DejaVu Sans,{font_size},&H00FFFFFF,&H000000FF,&H70000000,&H90000000,0,0,0,0,100,100,0,0,3,2,0,2,80,80,{int(height * 0.075)},1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    for cue in scene_captions(scene):
        text = (
            cue["text"]
            .replace("\\", "")
            .replace("{", "")
            .replace("}", "")
            .replace("\n", " ")
        )
        content += f"Dialogue: 0,{ass_time(cue['start'])},{ass_time(cue['end'])},Default,,0,0,0,,{text}\n"
    path.write_text(content)


def get_font(size, bold=False):
    try:
        return ImageFont.truetype(BOLD if bold else FONT, max(10, int(size)))
    except OSError:
        return ImageFont.load_default()


def overlay_image(project, scene, index, width, height, draft):
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    if scene.get("show_title", True):
        for y in range(int(height * 0.4)):
            alpha = round(155 * (1 - y / (height * 0.4)) ** 1.5)
            d.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
        x, y = int(width * 0.055), int(height * 0.07)
        d.rectangle((x, y, x + int(width * 0.025), y + 3), fill=(214, 164, 96, 255))
        label = (
            f"{index + 1:02d}  /  {scene.get('chapter', 'DOCUMENTARY').upper()[:45]}"
        )
        d.text(
            (x, y + int(height * 0.023)),
            label,
            font=get_font(height * 0.018, True),
            fill=(212, 188, 151, 255),
        )
        title = "\n".join(textwrap.wrap(scene.get("title", "Untitled scene"), width=40))
        d.multiline_text(
            (x, y + int(height * 0.062)),
            title,
            font=get_font(height * 0.05, True),
            fill=(244, 242, 235, 255),
            spacing=8,
        )
    mark = (
        "FICTIONAL DEMO · AI ILLUSTRATION"
        if project.get("is_demo")
        else ("REVIEW DRAFT" if draft else "")
    )
    if mark:
        f = get_font(height * 0.014)
        box = d.textbbox((0, 0), mark, font=f)
        tw = box[2] - box[0]
        d.rounded_rectangle(
            (
                width - tw - width * 0.045,
                height * 0.935,
                width - width * 0.025,
                height * 0.973,
            ),
            radius=3,
            fill=(0, 0, 0, 150),
        )
        d.text(
            (width - tw - width * 0.035, height * 0.942),
            mark,
            font=f,
            fill=(220, 211, 191, 230),
        )
    if scene.get("source_label") and scene.get("asset_id"):
        label = str(scene["source_label"])[:180]
        font = get_font(height * 0.018)
        lines = textwrap.wrap(label, width=76)
        x, y = int(width * 0.045), int(height * 0.76)
        line_height = int(height * 0.026)
        box_width = max(
            (d.textbbox((0, 0), line, font=font)[2] for line in lines[:2]), default=0
        )
        d.rounded_rectangle(
            (
                x - 8,
                y - 5,
                min(width * 0.93, x + box_width + 9),
                y + line_height * min(2, len(lines)) + 6,
            ),
            radius=3,
            fill=(0, 0, 0, 190),
        )
        for i, line in enumerate(lines[:2]):
            d.text((x, y + i * line_height), line, font=font, fill=(241, 237, 226, 255))
    return image


def run(cmd, cancelled: Callable[[], bool]):
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        while True:
            try:
                _, err = proc.communicate(timeout=1)
                if proc.returncode:
                    raise RuntimeError(
                        "Render failed: " + err.decode(errors="replace")[-1400:]
                    )
                return
            except subprocess.TimeoutExpired:
                if cancelled():
                    proc.terminate()
                    try:
                        proc.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.communicate()
                    raise RuntimeError("Cancelled by you. No output was published.")
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()


def asset_path(asset):
    p = (ROOT / asset["path"]).resolve()
    if not p.is_relative_to(ROOT) or not p.exists():
        raise ValueError(
            "A referenced media file is missing. Re-upload it before rendering."
        )
    return p


def render(
    project: dict, options: dict, out: Path, progress: Callable, cancelled: Callable
):
    if (project.get("episode") or {}).get("guide"):
        import episode

        blocked = [i for i in episode.issues(project) if i["blocks_draft"]]
        if blocked:
            raise ValueError(
                " ".join(i["title"] + ": " + i["detail"] for i in blocked[:2])
            )
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is not installed on the server.")
    scenes = project.get("scenes", [])
    if not scenes:
        raise ValueError("Build a timeline first.")
    width, height = {"480p": (854, 480), "720p": (1280, 720), "1080p": (1920, 1080)}[
        options["resolution"]
    ]
    assets = {a["id"]: a for a in project.get("assets", [])}
    draft = options.get("draft", True)
    total = sum(round(float(s["duration"]) * FPS) / FPS for s in scenes)
    with tempfile.TemporaryDirectory(prefix="casefile-render-") as folder:
        work = Path(folder)
        placeholder = work / "placeholder.png"
        im = Image.new("RGB", (width, height), "#151c22")
        draw = ImageDraw.Draw(im)
        draw.text(
            (width * 0.055, height * 0.67),
            "VISUAL NEEDED",
            fill="#ad997a",
            font=get_font(height * 0.025, True),
        )
        draw.text(
            (width * 0.055, height * 0.73),
            "Add a licensed image or video to this scene.",
            fill="#71808a",
            font=get_font(height * 0.02),
        )
        im.save(placeholder)
        clips = []
        for i, scene in enumerate(scenes):
            if cancelled():
                raise RuntimeError("Cancelled by you. No output was published.")
            duration = round(float(scene["duration"]) * FPS) / FPS
            frames = round(duration * FPS)
            progress(
                5 + int(79 * i / len(scenes)),
                f"Rendering scene {i + 1} of {len(scenes)} · {scene.get('title', '')}",
            )
            asset = assets.get(scene.get("asset_id"))
            src = (
                asset_path(asset)
                if asset and asset.get("kind") in ("image", "video")
                else placeholder
            )
            overlay = work / f"overlay{i}.png"
            overlay_image(project, scene, i, width, height, draft).save(overlay)
            outclip = work / f"{i:04d}.mp4"
            command = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-filter_complex_threads",
                "1",
            ]
            motion = scene.get("motion", "slow-zoom")
            if asset and asset.get("kind") == "video":
                if not scene.get("guide_cue_id"):
                    command += ["-stream_loop", "-1"]
                command += [
                    "-ss",
                    str(max(0, scene.get("trim_start", 0))),
                    "-i",
                    str(src),
                ]
                vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={FPS},setpts=PTS-STARTPTS,setsar=1"
            elif motion != "none":
                command += ["-i", str(src)]
                z = (
                    f"1+0.075*on/{max(1, frames - 1)}"
                    if motion == "slow-zoom"
                    else "1.08"
                )
                xp = (
                    "iw/2-iw/zoom/2"
                    if motion == "slow-zoom"
                    else f"(iw-iw/zoom)*(1-on/{max(1, frames - 1)})"
                )
                vf = f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,crop={width * 2}:{height * 2},zoompan=z='{z}':x='{xp}':y='ih/2-ih/zoom/2':d={frames}:s={width}x{height}:fps={FPS},setsar=1"
            else:
                command += ["-loop", "1", "-framerate", str(FPS), "-i", str(src)]
                vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1"
            look = project.get("look", "noir")
            if look == "noir":
                vf += ",eq=saturation=0.72:contrast=1.05:brightness=-0.015"
            elif look == "archive":
                vf += ",eq=saturation=0.2:contrast=1.03"
            command += ["-i", str(overlay)]
            filters = f"[0:v]{vf}[base];[base][1:v]overlay=0:0:format=auto"
            if options.get("captions", True) and (
                scene.get("narration") or scene.get("captions")
            ):
                ass = work / f"{i}.ass"
                write_ass(scene, ass, width, height)
                filters += f",subtitles='{ass.as_posix()}'"
            if scene.get("transition", "fade") == "fade" and duration >= 1:
                filters += f",fade=t=in:st=0:d=0.25,fade=t=out:st={max(0, duration - 0.25):.3f}:d=0.25"
            filters += ",format=yuv420p[v]"
            command += [
                "-filter_complex",
                filters,
                "-map",
                "[v]",
                "-an",
                "-frames:v",
                str(frames),
                "-r",
                str(FPS),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-threads",
                "2",
                "-video_track_timescale",
                "12288",
                str(outclip),
            ]
            run(command, cancelled)
            clips.append(outclip)
        progress(86, "Assembling the timeline")
        listing = work / "concat.txt"
        listing.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips))
        stitched = work / "picture.mp4"
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(listing),
                "-c",
                "copy",
                str(stitched),
            ],
            cancelled,
        )
        progress(92, "Mixing audio and preparing the MP4")
        narration = assets.get(project.get("narration_id"))
        music = assets.get(project.get("music_id"))
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-filter_complex_threads",
            "1",
            "-i",
            str(stitched),
        ]
        inputs = 1
        voice_index = music_index = None
        if narration and narration.get("has_audio", narration.get("kind") == "audio"):
            voice_index = inputs
            command += ["-i", str(asset_path(narration))]
            inputs += 1
        if music:
            music_index = inputs
            command += ["-stream_loop", "-1", "-i", str(asset_path(music))]
        volume = min(0.5, max(0, float(project.get("music_volume", 0.12))))
        af = []
        if voice_index is not None and (project.get("episode") or {}).get("guide"):
            # Guide projects retain the continuous uploaded recording, not a sequence
            # of regenerated or rearranged snippets. Only the last frame is padded.
            af.append(
                f"[{voice_index}:a]asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,apad,atrim=duration={total}[voice]"
            )
        elif voice_index is not None:
            # Slice the master voice by scene before concatenating, so scene reorder
            # and trimming affect the narration as well as the picture.
            labels = "".join(f"[vs{i}]" for i in range(len(scenes)))
            af.append(f"[{voice_index}:a]asplit={len(scenes)}{labels}")
            cursor = 0.0
            for i, scene in enumerate(scenes):
                start = max(0, float(scene.get("audio_start", cursor)))
                length = max(
                    0.04,
                    min(
                        float(scene.get("audio_duration", scene["duration"])),
                        float(scene["duration"]),
                    ),
                )
                duration = round(float(scene["duration"]) * FPS) / FPS
                af.append(
                    f"[vs{i}]atrim=start={start}:end={start + length},asetpts=PTS-STARTPTS,apad,atrim=duration={duration}[va{i}]"
                )
                cursor += float(scene["duration"])
            joined = "".join(f"[va{i}]" for i in range(len(scenes)))
            af.append(
                f"{joined}concat=n={len(scenes)}:v=0:a=1,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11[voice]"
            )
        if music_index is not None:
            af.append(
                f"[{music_index}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,atrim=duration={total},asetpts=PTS-STARTPTS,volume={volume},afade=t=in:d=1.5,afade=t=out:st={max(0, total - 2)}:d=2[bed]"
            )
        if voice_index is not None and music_index is not None:
            af += [
                "[voice]asplit=2[main][side]",
                "[bed][side]sidechaincompress=threshold=0.03:ratio=8:attack=30:release=800[ducked]",
                "[main][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[aout]",
            ]
            audio = "[aout]"
        elif voice_index is not None:
            audio = "[voice]"
        elif music_index is not None:
            audio = "[bed]"
        else:
            audio = None
        command += ["-map", "0:v:0", "-c:v", "copy"]
        if audio:
            command += [
                "-filter_complex",
                ";".join(af),
                "-map",
                audio,
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
            ]
        command += ["-t", str(total), "-movflags", "+faststart", str(out)]
        run(command, cancelled)
        progress(99, "Writing captions and export notes")
    if (project.get("episode") or {}).get("guide"):
        finished = probe(out)
        video_seconds = finished.get("video_duration") or finished["duration"]
        audio_seconds = finished.get("audio_duration") or finished["duration"]
        if (
            not finished["has_audio"]
            or abs(video_seconds - total) > 1 / FPS + 0.01
            or audio_seconds < total - 0.05
        ):
            raise RuntimeError(
                "The rendered video/audio does not cover the complete planned narration. No export was accepted; inspect the source files and retry."
            )
    return {
        "duration": total,
        "resolution": options["resolution"],
        "audio": bool(audio),
        "size": out.stat().st_size,
    }
