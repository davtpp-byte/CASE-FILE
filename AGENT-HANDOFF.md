# Agent handoff — Casefile Studio

State as of 2026-11-03. Read this before working in the repo.

## What this is

Casefile Studio: a documentary production tool. FastAPI backend
(`casefile-studio/app.py` + `episode.py`, `editorial.py`, `storage.py`),
React frontend (`casefile-studio/web/`, built bundle committed in
`web/assets/`). Version **0.4.13** (bump in `app.py`, `package.json`, and
both `?v=` refs in `web/index.html` together).

## Running it

```bash
cd casefile-studio
# ffmpeg must be on PATH. In a fresh sandbox, fetch it once:
#   pip download ffmpeg-binaries==1.1.0 --no-deps  (unpack into a dir on PATH)
.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Tests (239 passing at handoff; browser/long-render ones are slow-path):

```bash
PATH=<ffmpeg-dir>:$PATH .venv/bin/python -m pytest tests/ -q \
  --ignore=tests/browser_episode.py --ignore=tests/browser_production.py \
  --ignore=tests/browser_smoke.py --ignore=tests/long_render_check.py
```

Frontend rebuild after editing `web/src/`: `npm install && npm run build`
inside `casefile-studio/`, then restart the server. Browsers cache the
bundle — version bumps exist so a plain refresh picks it up.

## Data conventions

- `data/projects/*.json` — project state, **committed**.
- `data/exports/<id>/` — rendered outputs, **committed** (each ~90 MB MP4;
  keep individual files under GitHub's 100 MB limit).
- `data/media/<project-id>/` — uploaded source files, **not in git**
  (ignored). Originals live on the producer's Mac. A fresh clone cannot
  re-render without re-uploading media.
- `data/jobs/` — render job records, committed.
- `data/browser-sessions/`, `data/recovery-backups/` — ignored, transient.

## Current project state

| Project | id | State |
|---|---|---|
| **Bismilah** | `1a5bbba59d244274` | Producer-signed-off, reviewed plan, **final (no-banner) 480p export done**: `data/exports/1a938f1e9bf64f99/` |
| Tampa… | `4791316c6fae4722` | earlier project |
| Blackwater (demo) | `1b06752858c94e67` | demo |

Also in the repo root: `Bismilah-unreviewed-inspection.mp4` — the same
episode as an inspection draft **with** the burned-in disclosure banner
(pending the producer's confirmation to delete). Git tag `NyRA-Backup` +
GitHub Release of the same name = pre-sign-off backup point.

History note: the original Bismilah entry (`8e7a2f9d34074b1b`) was
deleted by a "clear session" action; `1a5bbba59d244274` (the former NyRA
Backup copy) is the live project and was repaired to point at its own
media copies. Do not resurrect the old id.

## Behavior rules that matter

- **Guide loop rule #8** (`episode.guide.raw` is authoritative over docs):
  gap scenes inherit the cue's selected crop and loop it to fill the
  scene — own beginning, final repetition trimmed, picture only, no
  substitutions/speed/freeze/spill. Never remove this.
- **Producer sign-off**: `POST /api/projects/{id}/signoff {"confirmed":true}`
  marks sources reviewed, notes reuse responsibility, approves placements,
  rebuilds the reviewed plan, confirms digests, ticks attestations, covers
  a sub-0.25 s lead-in. It is the producer's explicit click — never flip
  these flags silently server-side. Tests: `tests/test_signoff.py`.
- **Inspection banner**: drafts (`draft:true`) and inspection-mode plans
  always burn it in. Only a reviewed plan + attestations + preflight-clean
  final render omits it. Never bypass the banner for unreviewed content.
- **"Clear session"** (`DELETE /api/projects/{id}/session`) deletes the
  project, its media, and its exports from the server. It is destructive;
  the producer has been burned by it once.

## Frontend anchors (web/src/main.jsx)

`api()` ~line 172; `acceptProject()` ~line 394; Review & export tab:
sign-off button + confirm modal in the Editorial review card; "Make final
video" button in the page header (opens ExportModal with the draft toggle
off; 480p/720p/1080p choice). ExportModal ~line 4842.
