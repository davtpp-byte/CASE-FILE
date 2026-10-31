"""20-minute media-pipeline endurance check, not a real narrated documentary.

Run explicitly: python tests/long_render_check.py
Creates 60 x 20-second scenes, mixed stills/video/zoom, synthetic test-tone
narration and music, subtitles, and a real 24 fps H.264/AAC output. Fixtures
and the output MP4 are removed after success; the JSON report is retained.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json, shutil, subprocess, time, uuid
from PIL import Image, ImageEnhance
import numpy as np
import renderer

work = ROOT / "qa" / ("long-render-" + uuid.uuid4().hex[:8])
work.mkdir(parents=True)
start = time.monotonic()
seconds = 1200


def cmd(args):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *args],
        capture_output=True,
        check=True,
        timeout=180,
    )


voice = work / "synthetic-tone-master.wav"
music = work / "synthetic-bed.wav"
video = work / "synthetic-motion.mp4"
cmd(
    [
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:sample_rate=16000:duration={seconds}",
        "-af",
        "volume=0.2",
        str(voice),
    ]
)
cmd(
    [
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=165:sample_rate=16000:duration=12",
        "-af",
        "volume=0.12",
        str(music),
    ]
)
cmd(
    [
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=854x480:rate=24:duration=4",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-threads",
        "2",
        "-pix_fmt",
        "yuv420p",
        str(video),
    ]
)
base = (
    Image.open(ROOT / "web/assets/blackwater-road.jpg")
    .convert("RGB")
    .resize((1280, 720))
)
image = work / "illustrative-scenery.jpg"
base.save(image, quality=85)
image2 = work / "archive-treatment.jpg"
ImageEnhance.Color(base).enhance(0.1).save(image2, quality=85)


def asset(id, path, kind, duration=0, has_audio=False):
    return {
        "id": id,
        "name": path.name,
        "kind": kind,
        "path": str(path.relative_to(ROOT)),
        "duration": duration,
        "has_audio": has_audio,
        "license": "Synthetic endurance-test media only; no real case or human voice.",
    }


assets = [
    asset("a" * 16, image, "image"),
    asset("b" * 16, image2, "image"),
    asset("c" * 16, video, "video", 4),
    asset("d" * 16, voice, "audio", seconds, True),
    asset("e" * 16, music, "audio", 12, True),
]
scenes = []
for i in range(60):
    is_video = i % 5 == 0
    scenes.append(
        {
            "id": f"{i + 1:016x}",
            "title": f"Synthetic validation scene {i + 1:02d}",
            "chapter": f"Validation section {i // 10 + 1}",
            "narration": "This is a synthetic endurance test, not an actual case. The audio is a test tone, not narration.",
            "source_ids": [],
            "duration": 20,
            "audio_start": i * 20,
            "audio_duration": 20,
            "asset_id": "c" * 16 if is_video else ("a" * 16 if i % 2 else "b" * 16),
            "trim_start": i % 3 if is_video else 0,
            "motion": "none" if is_video or i % 6 else "slow-zoom",
            "transition": "fade" if i % 2 else "cut",
            "show_title": i % 10 == 0,
            "captions": [],
            "timing": "estimated",
        }
    )
p = {
    "id": "f" * 16,
    "title": "20-minute synthetic pipeline validation",
    "is_demo": True,
    "target_minutes": 20,
    "assets": assets,
    "scenes": scenes,
    "narration_id": "d" * 16,
    "music_id": "e" * 16,
    "music_volume": 0.10,
    "look": "natural",
    "captions": True,
    "sources": [],
    "review": {"facts": False, "rights": False, "disclosure": False, "picture": False},
    "script": "\n\n".join(s["narration"] for s in scenes),
}
out = work / "20-minute-validation.mp4"
print("Starting a real 20-minute, 60-scene 480p validation render.", flush=True)
last = -1


def progress(percent, message):
    global last
    if percent // 10 != last:
        print(f"{percent:3d}% {message}", flush=True)
        last = percent // 10


try:
    info = renderer.render(
        p,
        {"resolution": "480p", "draft": True, "captions": True},
        out,
        progress,
        lambda: False,
    )
    metadata = renderer.probe(out)
    probed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_frames,r_frame_rate",
            "-of",
            "json",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    stream = json.loads(probed.stdout)["streams"][0]
    assert abs(metadata["duration"] - seconds) < 0.15, metadata
    assert metadata["has_video"] and metadata["has_audio"]
    assert metadata["width"] == 854 and metadata["height"] == 480
    assert int(stream["nb_frames"]) == seconds * 24, stream
    assert stream["r_frame_rate"] == "24/1"
    tail = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            "1198",
            "-i",
            str(out),
            "-t",
            "1",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "8000",
            "-f",
            "f32le",
            "pipe:1",
        ],
        capture_output=True,
        check=True,
    )
    samples = np.frombuffer(tail.stdout, dtype=np.float32)
    assert len(samples) >= 7900 and float(np.max(np.abs(samples))) > 0.001
    srt = renderer.project_srt(p)
    assert "00:20:00,000" in srt
    report = {
        "passed": True,
        "test": "Synthetic long-form media pipeline",
        "video_seconds": metadata["duration"],
        "scene_count": 60,
        "video_frames": int(stream["nb_frames"]),
        "frame_rate": stream["r_frame_rate"],
        "resolution": "854x480",
        "has_audio": metadata["has_audio"],
        "output_bytes": out.stat().st_size,
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "scenes_with_video": sum(s["asset_id"] == "c" * 16 for s in scenes),
        "scenes_with_zoom": sum(s["motion"] == "slow-zoom" for s in scenes),
        "audio_tail_verified": True,
        "caption_end_verified": True,
        "scope": "Synthetic 20-minute technical render, not paid-provider validation, production load testing, or a professionally edited case documentary. Performance depends on media complexity and hardware.",
    }
    (ROOT / "qa/long-form-validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)
    shutil.rmtree(work)
except Exception:
    print("Validation failed; diagnostic files retained at " + str(work), flush=True)
    raise
