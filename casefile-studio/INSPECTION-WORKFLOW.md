# Preview first, publication separately — v0.3.3

This update repairs the confusing distinction between **uploaded**, **linked**, **inspectable**, and **approved**. It does not restore missing files from an earlier preview session or certify a finished documentary.

## 1. See uploaded sources without signing anything off

In Episode setup, unique source-ID filenames such as `S03-report.mp4` now auto-link after import. Ambiguous matches remain unlinked. A visible **Preview uploaded video/image** button opens the actual source player before the rights controls. Viewing media does not approve its identity, reuse, factual context, privacy, or Care instructions.

If the file cannot load, the app says it may be unavailable from the current server or unsupported by the browser. Do not substitute approval checkmarks for a missing/undecodable file.

## 2. Build an unreviewed inspection draft

Select **Planning mode → Inspection draft**, then **Build / rebuild inspection draft**.

- Only sources explicitly linked to that guide source ID are candidates. No generic B-roll rotation, actors, invented evidence, or third-party downloads are introduced.
- Images can be shown without falsely marking the placement approved.
- Videos use valid manually entered local in/out points, or a guide preview window that fits the uploaded file. When neither exists, the opening five seconds are explicitly labeled a **source inspection sample**, not a guide-selected or approved documentary shot.
- A guide window that does not fit the uploaded file is not silently offset or stretched. Enter the correct local in/out range instead. Partial or invalid manual ranges are not guessed away.
- A source window can be saved with the approval checkbox **unticked**. This does not approve rights, identity or Care.
- Known chapter-3 residential restrictions and guide-required narration stop times remain enforced, including in inspection. Other identity/privacy/cropping/context requirements still require actual human viewing; inspection is not automated semantic verification.
- Source audio stays muted. Each scene's selected crop loops to fill that scene—never into other footage. Placements with no usable file stay marked gap cards; nothing is invented or substituted.
- The uploaded narration is continuous and unchanged. Matching timing exports place cues; caption display remains optional without changing the clock.

Click **View timeline** to open on the first available visual rather than an initial short gap. Playback from the beginning still preserves the complete narration.

## 3. Render, watch, then download

Choose a quick 480p inspection render. If there are known gaps, explicitly permit marked gap cards. The button states why it is disabled instead of leaving the reason implicit.

Inspection frames are permanently marked **UNREVIEWED INSPECTION — NOT FOR PUBLICATION**. Final export is rejected even if generic review boxes are ticked. Complete genuine source/placement/editorial checks and rebuild in **Reviewed plan** mode for a final-export candidate.

After rendering, Review & export contains an **inline player for the actual encoded MP4**, with Play/Pause controls. Watch it before downloading. Frozen timing/source/plan companions remain available. Successful rendering is not a guarantee of factual accuracy, editorial correctness, licensing, or perfect acoustic alignment.

## 4. Save a real project backup, not an app updater

**Save backup** in the header and **Project .json** in Review create the JSON from the live browser state, without needing the server API to answer. This helps preserve settings if the server becomes unavailable while the page is still open.

The JSON contains project settings and asset references, **not video/audio bytes**. Keep the original media on your computer. Download a backup before closing or refreshing a temporary session or requesting changes. The `Casefile-Studio-...-Update.zip` packages contain code, not working-project backups.

## 5. Explicit cleanup after saving

After downloading and checking the files you need, open **Clear temporary session after saving your downloads**. Confirm that you have saved them, then clear that session.

The server removes that project's working media copies, owned exports, job records and project record. It rejects cleanup during active jobs and does not follow arbitrary client paths, delete another project's exports, or touch original files on your computer. Clicking Download alone never triggers deletion; a browser download can be cancelled, so user confirmation is required.

## Verified proof — not the user's actual case

The retained **Inspection workflow demo — SYNTHETIC MEDIA** uses a moving test pattern, a clearly labeled technical image, fabricated timing fixtures and a duration-matched continuous tone. There is no real narration, case footage or verified spoken-word alignment in this demo.

The browser test imports these files, auto-links the two sources with zero approvals, shows their video in the timeline, renders and plays the encoded MP4 inline, downloads matching bytes, saves a project snapshot with API requests blocked, rejects final export, and checks mobile layout. Separate decoded-audio tests verify source sound is muted and caption ON/OFF exports retain the same audio.

Next acceptance step: the user's latest 44-placement guide, final narration and a small batch of actual authorized source files. This is still a prototype test, not a claim that the full 20–40 minute real-case workflow is perfect or deployed to a production hosting service.
