# Hosting Casefile Studio

_Short version: **Render runs the app. Netlify can only be a front door for it.**
You do not need to build a separate frontend — it already exists._

## 1. "Won't I need a frontend?"

You already have one. `casefile-studio/web/` is the React app, and the built
bundle is committed in `casefile-studio/web/assets/`. Today the Python server
(`casefile-studio/app.py`) does **three jobs at once**:

1. hands those frontend files to the browser,
2. answers all `/api/...` calls (projects, uploads, sign-off, downloads),
3. runs FFmpeg to render MP4s and saves everything in `casefile-studio/data/`.

So locally one server = the whole product. That is why there was never a
second "frontend server" to deploy.

```
Browser ──► Python server (FastAPI)
              ├─ serves the React files   (the frontend)
              ├─ /api, /media, /exports  (the backend)
              └─ FFmpeg + data/ on disk  (the engine + storage)
```

**Render** can run that whole server in a Docker container with a persistent
disk. **Netlify cannot**: it only serves static files and short-lived
JavaScript functions — no long-running Python process, no FFmpeg binary, no
writable disk for 90 MB exports. A Netlify-only deploy would show the UI with
every button broken.

The setup in this repo is therefore:

```
Option A (recommended):  Browser ──► Render  ── everything, one URL, one password

Option B (optional):     Browser ──► Netlify (static UI only)
                                     └─ proxies /api, /media, /exports ──► Render
                        (two URLs, two services, same password on both)
```

Both options are configured below. Start with **A**; only add **B** if you
want a Netlify-hosted domain in front of the same app.

---

## 2. Deploy on Render (the real deployment)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/davtpp-byte/CASE-FILE/tree/arena/3eee7def-case-file)

Or do it manually: **Render Dashboard → New → Blueprint →** connect GitHub,
pick `davtpp-byte/CASE-FILE` and the branch `arena/3eee7def-case-file`.

`render.yaml` (repo root) tells Render to create:

| Setting | Value | Why |
|---|---|---|
| Runtime | Docker, `casefile-studio/Dockerfile` | installs Python deps, FFmpeg and fonts |
| Plan | `1c-2g` (1 CPU / 2 GB, **paid**) | a persistent disk is not available on the free plan; 512 MB cannot render video |
| Disk | 20 GB at `/app/data` | projects, uploads, exports and jobs live here; everything outside it is erased on redeploy |
| Port | `PORT=8000` | the Dockerfile now respects `PORT` |
| Health check | `/api/health` | new endpoint, unauthenticated so Render can probe it |
| Password | `CASEFILE_USER`, `CASEFILE_PASSWORD` | you are prompted for these at deploy time; nothing is committed |

Steps:

1. Push this branch (already done for this session).
2. Click the button / create the Blueprint.
3. When Render asks for env values, choose a username and a **strong**
   `CASEFILE_PASSWORD`. Both are needed — the gate is off if either is missing.
4. Wait for the first build (a few minutes), then open
   `https://<your-service>.onrender.com`. The browser asks for the username
   and password, then the workspace loads.

**First boot is a clean installation.** The disk starts empty, so the app seeds
only the fictional "Blackwater tapes" demo. The committed `data/projects/*.json`
case files are deliberately **not** baked into the image, and their source
media was never in Git (originals live on the producer's Mac). To continue an
existing case on Render, re-upload its media there. Anything you create on
Render is kept on the disk across deploys and restarts — but download your
finished MP4s and project JSON as your own backup.

> If your Render site is pointed at `main` instead of this branch, merge these
> files into `main` first (or change the branch in Render → Settings). The
> Blueprint and Dockerfile only exist on `arena/3eee7def-case-file` until then.

### Render limits worth knowing

- Renders run inside the web process. A redeploy interrupts a render in flight;
  jobs are marked `interrupted` on restart and are not resumed.
- `1c-2g` is a sensible minimum for 480p work. 1080p and 20–40 minute episodes
  are slow; increase the plan to `2c-4g` or higher in `render.yaml` if needed.
- Disk size can be increased later, never decreased. A disk can only attach to
  one instance, so keep `numInstances: 1`.

---

## 3. Optional: Netlify as a static front door

Only do this **after** Render is live. In Netlify: **Add new site → Import an
existing project →** choose this repo and the same branch. Build settings come
from `netlify.toml` (base `casefile-studio`, publish `dist`, command
`npm run build:netlify`). No `npm install` is required — it copies the already
built UI bundle.

Set these site environment variables before deploying:

| Variable | Example | Required |
|---|---|---|
| `CASEFILE_API_ORIGIN` | `https://casefile-studio.onrender.com` | yes (no trailing slash) |
| `CASEFILE_USER` | same username as Render | recommended |
| `CASEFILE_PASSWORD` | same password as Render | recommended |

`scripts/build-netlify.mjs` generates `dist/_redirects` and `dist/_headers`:
`/api/*`, `/media/*` and `/exports/*` are proxied to Render with a status-200
rewrite, unknown paths fall back to `index.html`, and Netlify's `Basic-Auth`
header guards the static site. Using the **same credentials on both hosts**
means the browser's auth header also satisfies the Render gate on proxied API
calls. (`Basic-Auth` in `_headers` is not available on every Netlify plan; if
yours lacks it, use Netlify's Visitor access control, or just use the Render
URL directly.)

Caveats with this split:

- Netlify's proxy has a short timeout (~26 s) and is not a good path for 512 MB
  uploads. For large media, long renders and big downloads, open the Render URL
  directly. Keep the Netlify URL for viewing the UI and light work.
- Netlify's `Basic-Auth` header is a paid-plan feature. If your plan does not
  support it, leave `CASEFILE_USER` / `CASEFILE_PASSWORD` **unset on Netlify**
  (keep them on Render) and do real work at the Render URL, which stays gated.
  If proxied `/api` calls ever return 401, Netlify stripped the browser's
  `Authorization` header — same fix: use the Render URL directly.
- Two services to keep in sync. Both must stay on a branch that contains these
  config files.
- The "Deploy to Netlify" button copies a repo into a new one; prefer
  "Import an existing project" so this repository stays the source of truth.

---

## 4. The password gate (and what it is not)

`CASEFILE_USER` + `CASEFILE_PASSWORD` enable HTTP Basic auth on every route
except `/api/health`. With either unset — as in local development — the app
behaves exactly as before. The same check runs in the Docker container, so
there is nothing extra to configure in the image.

This is a **door lock, not user accounts**. Everyone who knows the password
shares one workspace and can see, upload or delete any case. The project's own
README still says: do not expose this prototype publicly or upload
confidential evidence. A real production deployment needs authentication,
per-user authorization, private object storage, signed downloads, retention
controls and an audit trail.

---

## 5. Files added for hosting

| File | Purpose |
|---|---|
| `render.yaml` | Render Blueprint: Docker service, paid plan, 20 GB disk, health check, password env vars |
| `casefile-studio/Dockerfile` | respects `PORT`, trusts proxy headers, installs `gosu` |
| `casefile-studio/docker-entrypoint.sh` | fixes persistent-disk ownership, then drops to the unprivileged `studio` user |
| `casefile-studio/.dockerignore` | keeps the 160 MB of case data / QA artifacts out of the build context |
| `casefile-studio/app.py` | `/api/health` + optional Basic-auth middleware |
| `netlify.toml` | static build settings for the optional front door |
| `casefile-studio/scripts/build-netlify.mjs` | builds `dist/` with proxy + auth rules from env vars |
| `casefile-studio/package.json` | `npm run build:netlify` |

Local run is unchanged:

```bash
cd casefile-studio
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```
