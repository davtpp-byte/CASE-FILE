# Casefile Studio v0.4.1
## A source-led documentary production workspace

A working **single-workspace prototype** for a browser-based, AI-assisted true-crime YouTube workflow, with **20–40 minute episode targets**. This is not yet a fully autonomous professional production service.

The app now has a dedicated **Episode setup** path for a finished voice + narration script + footage guide + music + actual source files. The original **Research → Script → Edit → Review & export** workspace remains available for the other starting modes.

## New in v0.4.1 — automatic guide fallback applied across projects

- Shared inspection preview/build/source-linking paths now normalize a guide-permitted alternative that was mistakenly assigned under its missing main source. Unique source-ID filenames auto-link without a separate matching step; a single applicable image alternative can resolve an unnamed manually added still. Ambiguous alternatives and explicit contextual restrictions are not replaced with random footage.
- The selected replacement keeps **its own source time ranges, label and Care**, while narration anchors and supplied caption timing remain unchanged. Main-source in/out/review approval is not transferred. No licensing/factual/context approval is inferred.
- This logic is guide-driven, with regression coverage for other source IDs and source ranges—not a Last Timeline project-ID patch. Calling Preview or inspection Build applies it automatically.
- Corrected the misleading header action: **Make video** starts a render; **Download MP4** serves the latest completed file. Completed downloads now have an attachment endpoint, accurate missing-file errors, byte-range support, and an outside-frame direct-link fallback. A download does not queue a job or clear the session.

Source in/out instructions are applied deterministically. Prose-only spatial/privacy instructions are still review requirements, not a claim of precise pixel cropping or independent visual verification. Actual uploaded originals and the correct matching recording remain necessary. Updating this app copy does not recover a different preview's missing 19-media working state.

## New in v0.4.0 — a simple first-draft path

**Choose files → Preview my draft → Make downloadable video.** The default Episode setup screen no longer leads with mode selectors, 44 sign-offs or a separate rebuild step. Detailed source choices and final-publication controls remain behind **More settings**.

- Quick source selection automatically links unique IDs, rebuilds inspection and opens the first real visual. The main preview action uses the newly returned project, not a stale React snapshot. Editing a blank/stale guide plan cannot silently count as a successful visual preview.
- Preview checks actual server file availability. Missing uploaded bytes are explained honestly, not treated as an approval problem. No usable source means an actionable error instead of a green all-placeholder success.
- Picture inspection can work before a narration recording is added; sound/export requires the matching recording. No speech is generated or silently substituted.
- The video action rebuilds as needed, renders an explicitly unreviewed draft with visible gap cards, opens the encoded player and exposes Download. Final-publication sign-offs do not block inspection.
- Project setup auto-saves to browser IndexedDB. A saved JSON can be downloaded even when all API calls fail. It contains **metadata/references, not media bytes**; browser/site storage is not a promise of cross-device or permanent recovery. A newer browser copy is not overwritten by older server metadata.
- Explicit finish-session cleanup removes this server's owned working copies and its local setup cache only after the user confirms downloads are saved. Computer originals are untouched.

A real S01 public-reference photo from the supplied guide is loaded in the prepared 44-cue case for internal source inspection, privacy-cropped to exclude the background child. Its documentary reuse is **not** cleared, no review is inferred, no actual narration has been received here, and no real-case documentary has been rendered. This does not restore the former 19-file session shown in screenshots.

## New in v0.3.6 — cross-case isolation

Shared features are not tied to The Last Timeline: alternatives, source selectors, imported timing/caption handling, inspection/final review controls, upload progress/limits, backup and explicit cleanup apply to future projects using supported guide structure.

The reusability audit removed a legacy magic `S02`/chapter-3 restriction. Source IDs have no global editorial meaning. Restrictions are now read from the current guide's whole-episode/chapter boundaries, source-library exclusions and placement Care, together with the producer's residential-imagery flag. The Last Timeline's actual S02 exclusion remains enforced because its own guide declares it; another case can use S02 for entirely different footage.

Fourteen cross-case regressions cover other source IDs, other chapters, whole-episode restrictions, source/placement exclusions and isolation between projects. This is not a claim of automatic semantic understanding of arbitrary prose or visual content. Clear rules and final human review are still required.

## New in v0.3.5 — validated against the updated 44-placement guide

- Markdown reference links ending in source IDs now retain **each source's own preview clock**. A semicolon, `alternative`, `alternatively`, optional extension and follow-up are no longer conflated.
- The funeral conditional correctly links its named portrait S01; trial alternatives use S17's 5–9s and 20–24s windows, not the FOX windows. Derived portrait/courtroom labels do not falsely identify a portrait as funeral video or generic court footage as Sinardi speaking.
- C34's ban on replacing a 2024 hearing with 2026 footage stays intact. S26's follow-up is recorded separately from S25, and S20 is an optional manual source, not a required download. The single-source slot does not silently auto-splice follow-ups.
- Original source Markdown/script/captions remain unchanged. The new prepared **The Last Timeline — updated 44-placement guide** case contains documents and timing metadata only: no recovered media, narration or real-case export is claimed.

The exact supplied guide is retained at `examples/the-last-timeline/editing-guide-44.md`; the earlier 43-placement example is not overwritten. Case-specific regression and browser audits are in QA. See the user-facing `The-Last-Timeline-Guide-Check.md` in the workspace root for the replacement table and next small real-file test.

## New in v0.3.4 — alternatives, clear reviews, real upload progress

- Guide-scoped **Automatic / Main / Alternative** selection per placement. A missing/unusable main can use a named, linked, guide-permitted alternative; user choices are validated against the guide. Text-only visual rules require an explicit matching choice rather than random substitution.
- Explicit placement/source-library alternative fields and positive local conditional rules are read. Negated/global research mentions do not become substitution permissions. Main/alternative source clocks, labels and review records stay separate.
- The counter now says **Final placement sign-offs** and explicitly explains that zero is okay for inspection. Timing/transcript/caption/placement controls have plain-language help; sign-offs do not perform synchronization or import visuals.
- **Real XHR upload progress** displays bytes and percentage, followed by a distinct media-processing phase. The bar is brought into view. Visible current limits: **512 MB per media file, 30 files per batch**; oversized/count-invalid selections are rejected before upload.
- Sub-second remaining gaps use millisecond display, not a misleading 0:00 label.

Read **[GUIDE-ALTERNATIVES.md](GUIDE-ALTERNATIVES.md)**. The actual updated 44-placement guide has not yet been supplied in this workspace; do not claim the user's two specific missing sources have been resolved from synthetic tests alone.

## New in v0.3.3 — see the edit before publication checks

- **Inspection draft** mode shows explicitly linked but unapproved source candidates instead of requiring legal/editorial sign-off before seeing any footage. Disclosures are visible in the timeline and burned into inspection MP4s; final export remains blocked until genuine reviews and a reviewed-plan rebuild.
- Source rows have a visible **Preview uploaded video/image** action. Unique source-ID filenames auto-link after upload, without inferring approvals.
- Valid source windows loop within their own scene to cover the narration span; playback never reads past the reviewed crop. Opening-source samples are explicitly disclosed, mismatched excerpt clocks are not guessed, and known restricted chapters/required stops remain blocked. Exact shot identity, privacy and other Care requirements still require human review.
- **View timeline** opens on the first real visual. **Review & export** plays the actual encoded MP4 inline before download.
- **Save backup** downloads current browser project metadata even if the API is unavailable. It does not contain media. Session cleanup requires explicit confirmation that downloads are saved and only removes that project's server-side copies/jobs/exports.
- Corrected the preflight warning that incorrectly labeled imported caption blocks as word-count estimates. Footage assignment is no longer mislabeled as factual source sign-off.

Read **[INSPECTION-WORKFLOW.md](INSPECTION-WORKFLOW.md)** for candidate selection, inspection versus reviewed exports, backup, and cleanup. This update does not claim to restore the user's previous 21-media working session or verify a real documentary's acoustic/editorial accuracy.

## New in v0.3.2 — easy-to-find timestamp input

- A dedicated **Narration timestamps (SRT / JSON)** panel is directly below the four audio/document cards, with a persistent **Upload SRT / JSON** button. It is no longer buried in Finished narration.
- A **SRT / JSON timestamps** shortcut at the top scrolls straight to it. Attached filenames explicitly say **Attached to this project**; imports are per episode.
- The Source files section explicitly states that guide links are references, **not automatically downloaded media**. Upload actual authorized footage/photos; full originals and original filenames can be used.
- The interface displays **v0.3.2**, and CSS/script URLs are versioned to make stale-browser-cache issues easier to spot.
- This is a code/UI update. No existing project, audio, guide, source binding, or export is automatically replaced. See **[TIMESTAMP-INPUTS.md](TIMESTAMP-INPUTS.md)**. The optional code-only updater preserves `data/` rather than replacing it with example data.

## New in v0.3.1 — CapCut timing + optional exact-caption track

- Import a full CapCut `draft_info.json` (up to 32 million characters), then its matching SRT, in either order. `.srt.md` uploads are accepted when their content is SRT. Only sanitized caption/timing data and an audio **basename** are retained; device IDs and local paths are not copied into the project.
- Relative word-unit milliseconds are placed on the segment's microsecond timeline. A date/phrase may be one timed unit: no interior start is labeled exact. Single-word substitutions are explicit **review candidates**, not approved matches or acoustic alignment.
- SRT blocks, including continuous-caption holds, are preserved in the sidecar. Burn-in caption fragments follow the same clock across visual cuts. Empty imported intervals never regenerate estimated captions. **Captions OFF changes visibility only**, not guide cuts or the narration clock.
- Transcript differences have a visible review panel and separate producer sign-off. Files with mismatched starts are rejected instead of globally shifted; mismatched recording duration is flagged instead of stretched.
- **The Last Timeline now has the two supplied timing exports loaded:** 390 caption blocks, 2,353 timed units, 43 proposed cue starts (35 normalized matches + 8 text-substitution candidates), a 15:03.533 exported clock, and a **56-scene all-gap timed plan**. Actual narration, music, and footage are still missing. Its original script/guide are unchanged; it is not a finished video.

See **[CAPCUT-TIMING.md](CAPCUT-TIMING.md)** for this input audit, limits, and the next required file.

## New in v0.3 — the supplied episode-pack workflow

Open **The Last Timeline → Episode setup** in the included workspace. Its user-supplied script and real-footage guide are already loaded in separate cards; **no narration, music, or source media has been supplied**. The two original uploads remain unchanged. See **[EPISODE-WORKFLOW.md](EPISODE-WORKFLOW.md)** for the practical, nontechnical walkthrough.

- Separate inputs for **finished narration, background music, narration script, editing guide, optional SRT/word timings, and actual source files**. A guide cannot silently overwrite the script.
- Local **At / Show / Preview / Label / Care** parsing in the supplied guide's format. The supplied pack has **2,366 spoken words, a hook + 12 chapters, 43/43 matching phrases, 24 references, and 15 sources used by placements**.
- Explicit source-ID bindings (including **S01**, not S1), filename suggestions, per-file reuse notes/attestations, and per-placement exact local in/out and Care/context reviews. No imported source or permission is automatically approved.
- Guide-aware planning: source/date labels, muted source audio, explicit stop requirements for context switches, residential-source restrictions in chapter 3, no unrelated substitutions, and **marked gap cards only for placements with no usable file** (a short crop loops within its own scene instead of being padded with unrelated footage).
- The uploaded voice is the continuous master. Guided renders require that real recording, preserve its full order/runtime, and reject stale plans, altered guide timing, unapproved sources, or out-of-range footage. Source files cannot masquerade as the voice/music role. There are no silent guide-documentary exports.
- Music loops and ducks under the voice. Local commands include **“set music to 8%”**, look changes, captions, and titles. Destructive guide timing/story commands are rejected; revise guide cues in Setup and rebuild instead.
- Plans without audio are allowed, but rendering stays disabled. The included **56-scene timed plan has no media**, uses the supplied CapCut clock rather than the historical 145-wpm estimate, and is not a documentary. The exact recording must still be uploaded and checked.
- The exported **frozen episode plan** records cue phrases, exact file windows, labels, Care rules, linked files, recorded reuse notes, and visual gaps alongside the existing handoff files.

**No AI key is needed for this path.** This version does not download YouTube/news footage, request licenses, semantically identify people/places, automatically crop/blur privacy details, or implement cleared broadcast inserts between narration paragraphs. Supply safe authorized files and review context yourself. Free-text editing-brief notes are recorded, not arbitrarily executed.

### Start with your supplied inputs

1. Open the live app, switch to **The Last Timeline**, and click **Episode setup**. A fresh browser normally opens this project by default.
2. Add your **finished narration** in card 1 and optional **background music** in card 2. The script and editing guide in cards 3 and 4 are already present.
3. Import the actual authorized source clips/photos. Match names such as `S03.mp4` or link each source manually. Record reuse notes and review each cue's exact local window, label, and Care instructions.
4. Check the proposed cue positions and transcript differences against the voice; optionally import the matching CapCut JSON + SRT, then **Preview / Rebuild episode plan**.
5. **View timeline** or **Create review video**. If coverage is incomplete, explicitly allow visibly marked gap cards for an internal review-only MP4. The app never invents the missing real footage.
6. Watch the whole MP4 and resolve factual, source, privacy/context, timing, rights, and picture/sound checks before considering a final export. Structural preflight and producer attestations are not independent verification or legal clearance.

For the next episode, use **New project → Narration + media** and supply the same separate inputs. Other guide formats need adaptation; the parser is not a general semantic understanding engine.

### Retained from v0.2

- **Produce draft:** a guided, resumable run from the material you have. It assembles scenes, fills missing visual assignments from your imports, reuses or explicitly generates narration, and queues a real review render.
- **Human review stops:** topic research stops for source review; AI-written scripts stop for producer approval before narration. No source is marked reviewed automatically.
- **Per-run paid consent:** paid work is off by default, needs a connected key and explicit approval for that run, and has a configurable narration-character ceiling. This is not a currency budget or a cap on other provider charges. Saved stages are reused on the next run; consent resets when reopening the production dialog.
- **Stronger preflight:** unresolved factual markers, missing source IDs, missing files or rights notes, narration bounds, script approval, and editorial sign-offs. Final rendering stays locked when blocking checks fail.
- **A portable claim trail:** `[S1]`, `[S1, S2]`, and related source references survive assembly and scene edits. Edit a scene's source IDs and chapter label in its inspector.
- **Publication handoff:** every new export includes its frozen preflight report, chapter draft, and publication checklist alongside the MP4, SRT, source notes, and project snapshot. These are aids for a producer—not a publishing or legal-clearance service.

### Explore the unchanged fictional sample

1. Open the **Casefile Studio** live preview.
2. Switch projects and explore **The Blackwater tapes**, the clearly labeled fictional sample. It contains AI-created illustrative scenery, no real case facts, and no spoken narration.
3. In **Edit**, select a scene, change its duration, drag a trim handle, or split it at the playhead.
4. Type **“use the archive look”** or **“set scene 2 to 12 seconds”** into the direction box. These commands work without an AI key. Undo restores the previous saved edit.
5. Open **Review & export**. A real, approximately 88-second **720p silent sample MP4** has already been rendered in this workspace and can be downloaded from the export history.
6. Open **Produce draft** to inspect the production path and deliberate review stops. Use **Preflight checks** in Review to see what still prevents a final export.
7. Create a **New project** for your actual material. Do not repurpose the fictional demo for real case research; its fictional disclosure is deliberately retained in rendered files.

## What works now

| Feature | Status / requirements |
|---|---|
| Project creation, autosave, and reload persistence | Local JSON files on the server |
| Four project entry points | Topic, finished script, narration + media, raw footage |
| Source library and producer review | Manual source links, offline records, producer-verified notes, scene-level source IDs |
| Guided production | Available-stage runner; pauses/resumes at source, script, media, consent, and connection gates |
| AI-script approval | Text + cited-source fingerprint; substantive text/source edits require fresh producer approval |
| Script-to-scene assembly | Local paragraph/sentence splitting, estimated timing at 145 wpm |
| Media import | Images, video, audio, TXT, and Markdown |
| Visual assignment | Episode Setup: exact guide source bindings + reviewed ranges; nonguide legacy assembly: filename matching/rotation |
| Scene editing | Reorder, duration, source in-point, split, left/right trim, titles, motion, transitions |
| Editable look | Noir, archive, natural |
| Captions | Guided imported SRT/CapCut blocks preserved; visibility optional. No-import fallback remains estimated. |
| Audio | Uploaded narration/music; actual waveform extraction; approximate browser playback |
| Render engine | Real FFmpeg H.264 MP4, 24 fps, 480p / 720p / 1080p, AAC when audio is present |
| Export audio processing | Guide: unchanged continuous voice with music ducking/looping/fades and mix limiting; legacy: also narration leveling |
| Scene/audio linkage | Guide projects: continuous preserved master; legacy nonguide projects: source slices follow scene reordering/trimming |
| Export artifacts | MP4, SRT, source/rights notes, project snapshot, preflight Markdown/JSON, chapters, and publication checklist |
| Draft/final gate | Watermarked drafts; editorial preflight required for final export; missing media blocks all renders |
| Local text commands | Captions, titles, look, music level; scene duration/move are restricted to nonguide projects |
| AI research, writing, narration, transcription, creative direction | Optional provider adapters; requires a separately billed API key |

**What is not automatic:** the app does not find and license a complete set of true-crime visuals or music. You must provide/clear the assets. It also does not independently verify case facts, do legal clearance, or reliably make every creative decision a professional editor would make.

## Optional AI connection

Open **Settings / Connect AI** and enter an **OpenAI API key in the app's private connection field**, not in the conversation.

- The API key is held in server memory for that browser session. It is never written to project JSON, media, export manifests, or browser storage.
- An opaque session token is stored in `sessionStorage`; this is not the API key. The same-origin session header supports embedded live previews where third-party cookies are blocked.
- Restarting the server disconnects the key. Disconnecting does not cancel an AI request already in progress.
- Account/model access and API billing are separate from any chat subscription.
- Research sends the topic to the provider's web-search tool. Writing/direction send the relevant text and asset metadata. Narration sends script text. Transcription sends the selected audio in compressed chunks.
- No paid AI calls were made while building the sample. Live paid-provider operations are **wired but not credential-tested**; adapter behavior is covered by mocked-response tests.

Defaults: Responses API with `gpt-4.1` for writing/editing and web research; `whisper-1` for segment-timed transcription; Speech API with `gpt-4o-mini-tts` / `onyx` for narration. Model fields are editable in Settings.

**Provider lifecycle warning:** the provider documentation retrieved on 23 October 2026 says the current Speech API model defaults are scheduled to shut down on **6 January 2027**. The narration adapter will need migration to the provider's replacement workflow before then; changing the model name alone may not be enough. The adapter lives in `ai.py`.

Provider references:
- https://developers.openai.com/api/docs/guides/tools-web-search
- https://developers.openai.com/api/docs/guides/text-to-speech
- https://developers.openai.com/api/docs/guides/speech-to-text

### Use legacy Produce draft (projects without an editing guide)

Open **Produce draft**, choose any source recording, and review the stage plan. **Fill missing visual assignments** preserves curated choices. Paid work and voice generation require separate explicit choices; the app never silently chooses paid narration. With no voice or visuals it stops, unless you explicitly allow a **silent picture draft** or **placeholder visuals** for review.

Click **Run available stages**. When the workflow pauses, use its **Open Research / Script / Edit / Settings** action to resolve the issue. Reopen Produce draft and approve any paid work needed for the next run. A finished run creates a watermarked MP4; it does not publish or clear the final review checks. Exports are snapshots, so rerun after making edits.

The following manual stage controls also remain available. Clicking a manual AI research/write/transcribe/narrate button directly requests provider work with the connected key; the guided run's paid-consent checkbox does not govern those separate manual actions.

### Workflow by starting material

**Topic only**
1. Enter a specific case name, location, and identifying context in Research.
2. Research the case with a connected API key.
3. Open original sources, record checked facts/context in the notes, and mark sources reviewed.
4. Draft from reviewed sources, then read and approve the AI script in Script before generating narration. The requested length is a target, not permission to pad with invented material.
5. Import licensed visuals and music. Review the scene assignments and source IDs.
6. Generate or upload narration; review the edit, run Preflight checks, and render.

**Finished script**
1. Paste the script or import a TXT/Markdown file.
2. Use blank lines between scene-sized paragraphs, usually 35–65 words.
3. Import your media, then Build timeline.
4. Add a voice track or generate narration. Generated voice lengths align the scene durations.

**Recorded narration + script / editing guide**
1. Use **Episode setup**, not Transcribe & assemble. See [EPISODE-WORKFLOW.md](EPISODE-WORKFLOW.md). No AI key is needed; import the script and guide separately and upload the finished voice/music.

**Recorded narration without an editing guide (legacy path)**
1. Use the existing media library to import files and select the voice track in the Audio panel or media details.
2. With an AI connection, use Transcribe & assemble for source-segment timing.
3. Alternatively, paste the matching script and build locally; timing is estimated and needs review.

**Raw footage / interview**
1. Import the recording.
2. Use Transcribe & assemble. This assembles a source-aligned timeline for the selected recording and replaces the current timeline; Undo is available.
3. Refine the sequence, add B-roll, and review every cut. This is not yet a multicamera editor or an automatic multi-interview documentary assembler.

## Run the source locally

Tested with Python 3.13, Node 20, and FFmpeg 7 on Linux. Python 3.11+ is recommended.

### 1. Install system tools

Install `ffmpeg` and `ffprobe`, with H.264, AAC, and libass/subtitle support. Install DejaVu Sans fonts for titles and captions.

Debian/Ubuntu:
```bash
sudo apt-get update
sudo apt-get install ffmpeg fonts-dejavu-core
```

### 2. Install Python dependencies
```bash
cd casefile-studio
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launch

The bundle includes prebuilt browser assets; Node is only needed to change/rebuild the UI.

```bash
./run.sh
# or:
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser. In a hosted preview, use its provided URL instead. The browser uses only relative API/media URLs—no browser-facing localhost backend calls.

### Rebuild the frontend
```bash
npm ci
npm run build
```
The frontend is React + Lucide icons, bundled by esbuild. Its font, CSS, scripts, and sample image are served locally; no CDN is needed at runtime.

### Docker (private local test)
```bash
docker build -t casefile-studio .
docker run --rm -p 127.0.0.1:8000:8000 -v casefile-data:/app/data casefile-studio
```

The Docker image excludes the workspace data. It creates the fictional demo on first run; render its sample export if you want one inside that installation.

## Tests and verification

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
```

**92 passing regression tests** cover the original editor plus guided production, paid-consent/connection safeguards, character caps, review stops, cancellation/error preservation, stage reuse, recording selection and source alignment, AI approval/invalidation, source preservation, missing rights/files, voice bounds, export artifacts, and real FFmpeg renders. Provider responses are mocked. New Episode tests parse both supplied documents, exercise explicit roles, permission/context/range guards, word/SRT clocks, stale-plan/tamper rejection, full contiguous narration, and guide labels. A real short guide render verifies that source audio is muted and the narration tail survives; the legacy integration test still verifies reordered narration by output frequency.

Optional browser smoke test against a running server:
```bash
python -m playwright install --with-deps chromium
python tests/browser_smoke.py
python tests/browser_production.py
python tests/browser_episode.py
```

**29 passing browser checks** (10 original + 8 legacy guided-production + 11 Episode Setup checks) cover the editor, real queued MP4 export/download, producer approval/invalidation, paid-stage gating, preflight navigation to a rights repair, final-export locking, automatic visual fill, frozen handoff downloads, persistence, and mobile layouts. No browser runtime errors were observed. The AI-origin text used to test approval UI is an explicitly simulated temporary fixture, not a live provider response.

Historical v0.2 long-form technical check (not rerun as a complete v0.3 guide-driven documentary):
```bash
python tests/long_render_check.py
```
A real **20-minute synthetic render passed in v0.2**: 60 scenes, 28,800 frames at 24 fps, 854×480 H.264/AAC, 12 video scenes, 8 moving-still scenes, captions, test-tone narration, and a music bed. Output duration was **1200.0 seconds**; the caption end and non-silent audio at the tail were verified. It took **207.94 seconds** on this sandbox for this particular media mix. This is **not** a 1080p performance promise, speech-sync assessment, real case documentary, production load test, or paid-provider validation. The test deletes its large synthetic fixtures/output after success and keeps `qa/long-form-validation.json`.

Also verified: the approximately 88-second 720p silent fictional demo, short real picture/audio test renders, and a short 1080p render. A complete **real 20–40 minute episode with live paid AI** still has **not** been end-to-end validated.

## Limits and professional-production work still needed

- **Single shared workspace, no user authentication.** Do not expose this prototype publicly or upload confidential evidence. Production needs authentication, per-user authorization, private object storage, signed downloads, retention/deletion controls, and an audit trail.
- Jobs run in a thread pool; one CPU render runs at a time. Interrupted jobs are marked after restart, not automatically resumed. Guided production can reuse already-saved stages when you explicitly run it again; it cannot recover an in-flight provider request. Cancellation/errors can still incur provider charges. Projects are read-only during non-render production jobs. A production system needs a durable queue, managed workers, quotas, and observability.
- CPU rendering can take substantial time for a 20–40 minute episode. The synthetic 480p test is only one measured media mix; no production performance or load guarantee is made.
- Import limit: **512 MB per file, 30 files per batch**. Project limit: **400 scenes**, up to **90 minutes** exported. Large camera masters may need external proxy/transcode storage.
- Supported output is **16:9**, up to **1080p**, at **24 fps**. No 4K, HDR, broadcast color management, multicam, ripple-edit parity with a professional NLE, or NLE interchange export is implemented.
- Browser monitor/mix is an approximate editing preview; the downloaded MP4 is authoritative. Export applies the selected subtitles/titles and music processing. Guide narration stays a continuous master; the legacy nonguide renderer also levels narration.
- Script-derived captions are estimated. Generated narration is scene-aligned, not word-aligned. Transcription gives source-segment alignment but still requires recognition/timing review.
- Creative AI narration rewrites detach the old voice track to avoid silently mismatching speech. Re-record or regenerate it.
- Build timeline is required after script-only edits; final export rejects unapplied script changes.
- Legacy automatic visual assignment is basic filename matching/rotation. Episode Setup uses the supplied guide IDs and reviewed source windows, but still does not semantically verify images, context, identities, or rights.
- Final export checks combine structural checks with producer attestations, **not** independent fact checking or legal clearance. Source links and rights notes do not prove truth or permission. The chapter draft may need grouping to meet YouTube chapter requirements; publication notes flag short/fewer-than-three chapter drafts.
- Media removed from a project is retained on disk so undo/history and existing manifests can still reference it. Production needs a deliberate retention/garbage-collection policy. Back up and delete the entire workspace data deliberately when appropriate.

## Project structure

```text
app.py                 FastAPI routes, sessions, jobs, shared export writer
storage.py             Atomic JSON persistence, scene assembly, demo seeding
renderer.py            FFmpeg rendering, audio processing, captions, media probing
ai.py                  Optional paid-provider adapters
production.py          Resumable guided stages, consent and review stops
editorial.py           Source trail, script approval, preflight, handoff notes
episode.py             Local guide/script/timing parsing, bindings, bounded planning
episodic workflow docs EPISODE-WORKFLOW.md + supplied examples/the-last-timeline/
web/src/main.jsx       React editing workspace
web/src/ProductionTools.jsx  Legacy guided production and preflight dialogs
web/src/EpisodeSetup.jsx     Separate-input guide-led Episode Setup screen
web/src/episode.css     Responsive Episode Setup additions
web/src/styles.css     Responsive local styles
web/src/production.css Guided production / editorial additions
web/assets/            Prebuilt UI, local font, illustrative sample image
data/projects/         Saved projects (no API keys)
data/media/            Uploaded/generated media
data/exports/          Actual MP4s and companion files
data/jobs/             Job status records
tests/                 API, production, browser, and long-form tests
qa/                    Verification reports (created by test runs)
```

The sample is fictional. Its AI-created scenery is illustrative, never case evidence. DM Sans is bundled under the SIL Open Font License; see `web/assets/FONT-LICENSE.txt`.
