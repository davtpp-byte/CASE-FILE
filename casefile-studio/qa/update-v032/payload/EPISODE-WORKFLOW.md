# Your episode pack → a guide-led first draft

## For the files you supplied

Open **The Last Timeline → Episode setup** in the live workspace. Your two original documents are already loaded in separate cards. The fictional sample is still a different project.

| Your input | What CASEFILE does with it |
|---|---|
| Finished narration, MP3/WAV/etc. | Uses the uploaded recording as the continuous audio master. It does not regenerate, rewrite, reorder, or stretch your voice. |
| Background music | Mixes your selected track below narration, with looping, fades, and ducking. The starting level is adjustable. |
| Narration script | Finds chapters and the words that trigger visual changes. It is not the editing guide. |
| Editing / footage guide | Maps **At → Show → Source ID → Label → Care** into planned placements. It is not narration to be read aloud. |
| Actual authorized source videos/photos | Provides the pixels that can be cut into the video. Web links alone do not provide these files or permissions. |
| Optional CapCut JSON + matching SRT | Native units place eligible cue starts; SRT preserves caption blocks/holds. Group interiors/SRT-only word cuts remain estimates. See CAPCUT-TIMING.md. |

**No AI key is needed for this workflow.** It uses documents and media you already have. Optional research, generation, and transcription elsewhere in the app are separate provider features.

## What your documents contain

- **2,366 spoken words**, a hook, and **12 chapters**.
- **43 guide placements**. All 43 anchor phrases match in their intended chapters.
- **24 reference sources**, of which **15** are used by those placements. The other nine are research/alternative sources, not nine extra automatic downloads.
- The subsequently supplied CapCut export declares **15:03.533**. This supersedes the historical 16:19 word-count estimate, but the actual audio file is still required. A 20–40 minute target never justifies stretching or inventing material.

The supplied-case project now contains a **56-scene timed, all-gap plan**, using 390 supplied caption blocks and the CapCut word units. All 43 cue starts have proposals; eight depend on text substitutions and need review. There is no actual voice, music, or footage attached; the MP3 filename inside the draft is only a reference. It cannot yet render the documentary. See **[CAPCUT-TIMING.md](CAPCUT-TIMING.md)**.

## The practical workflow

### 1. Add the audio you already generated

In card **1 · Finished narration**, choose your final narration file. In card **2 · Background music**, choose your music file, or leave music unassigned.

You do not need to press Generate narration, connect a provider, or buy another voice generation. The guide-driven path deliberately blocks destructive script/voice/transcript replacement.

Listen to both imported tracks. Record the required reuse basis in the media library before final clearance. A successful upload is not a license or a promise of correct loudness.

### 2. Link actual source files

The **Source files** list is taken from your guide. Upload the authorized originals or excerpts you can reuse.

- Name files like `S03.mp4` and `S01.jpg` and press **Match filenames**; or open a source row and select its file manually.
- A filename match only links the file. Ambiguous matches are left unassigned.
- Open each used source row. Record the permission/license or reviewed reuse basis, then confirm that it applies to that file.
- If the guide requires a tighter crop, removal of private details, or a blur, supply the prepared safe file. CASEFILE does not semantically inspect faces or automatically blur private material.

**This version does not download YouTube/news videos or obtain permissions.** Original links open for your research. Use authorized files supplied by the owner, a valid license/download, or another producer-reviewed lawful basis; the app does not decide that basis for you.

### 3. Review each phrase-triggered placement

The right-hand list says, in effect, **“when you say this phrase, show this source.”** Filter it by chapter if useful.

For each placement:

1. Read its **Show**, on-screen **Label**, and **Care** rules.
2. Watch the actual moving clip/photo in context—not just a thumbnail.
3. For video, enter exact **Clip in / Clip out** seconds in the uploaded file's own clock. The guide's online preview window is approximate. If you uploaded a four-second excerpt, its local in-point might be `0`, not `42`.
4. If needed, override the cue's start in the narration's clock. An explicit narration stop is required where the guide says to stop before a different account/event.
5. Save the placement review. After listening to the actual voice, confirm **I checked the cue positions against the actual narration**.

Rights review, factual/source review, visual-context review, and timing review are different checks. None is automatically cleared by importing a guide or pressing a checkbox.

### 4. Preview the episode plan

Press **Preview episode plan** (or **Rebuild episode plan** after changes).

CASEFILE places the source specified by each guide cue, applies its source/date label, and mutes source audio. A reviewed video range plays once. If it is too short for that narration span, the remaining time becomes a marked gap—it is not looped or filled with unrelated stock.

Approved stills may hold until the next cue/chapter boundary; use a narration stop to limit a hold. Coverage changes at chapter boundaries. The planner does not invent more footage or silently substitute another source.

Use **View timeline** to inspect the result. A short source clip is not expected to cover an entire paragraph. Where the guide leaves no adequate footage, add legitimate coverage through an explicitly revised guide or accept visible gap cards for an internal review version.

### 5. Make a review MP4

Upload the actual narration first. Choose **480p** for a quick technical check or **720p/1080p** for a larger draft. If coverage is incomplete, explicitly allow visibly marked missing-visual cards in a **review-only video**.

Press **Create review video**. The export appears in **Review & export**, together with a frozen episode plan, preflight report, captions, source notes, chapter draft, and project snapshot.

The browser monitor is approximate. Watch and listen to the entire downloaded MP4. A REVIEW DRAFT or VISUAL NEEDED card is not a publishable episode. Final export still requires factual, rights, context, timing, and picture/sound review; the app provides structural checks, not independent reporting or legal clearance.

## Your guide's important boundaries

The imported **Care** instructions and standing boundaries remain visible. In particular:

- No generic stock, actors, reenactments, graphic material, distress/grief spectacle, private phone contents, or identifying the unnamed third teenager.
- **Chapter 3: no residential-property imagery.** S02 and residence-tagged files are blocked there. The producer must also recognize untagged residential imagery.
- No detailed escape route or private home address. Privacy/cropping decisions require human review and safe input files.
- Date-label later-recorded/released material. Contextual reporting, briefings, and courtroom B-roll must not imply a different place, date, event, or exact verdict instant.
- April three-person surveillance must not be represented as the shooting or as the separately described 3:33/3:36 views. December business surveillance is escape footage, not killing footage.
- Source audio is muted. Cleared broadcast inserts between narration paragraphs are **not implemented** in this continuous-master workflow.

CASEFILE enforces IDs, reviewed ranges, source labels, certain explicit restrictions, and the preserved audio timeline. It cannot visually verify identity/context, establish truth, or grant reuse permission.

## Plain-language revisions

In **Edit → Direct your edit**, these work locally, one supported command at a time:

- `use the archive look`
- `use the natural look`
- `set music to 8%`
- `turn off captions`
- `hide all titles`

Guide-driven timing/story moves that would change your voice or bypass the approved cue positions are rejected. Revise the cue timings/ranges or the guide in **Episode setup**, then rebuild. The **Editing brief** is recorded producer guidance, not an arbitrary executable prompt.

## Starting your next episode

Choose **New project → Narration + media**, then supply the same separate inputs in **Episode setup**. You can start with only the two documents to inspect a plan and see the missing-material checklist. Other project entry modes—topic, script, raw footage—remain available in the existing workflow.

**Privacy:** this is a single shared prototype without authentication. Do not upload confidential evidence, private identities, or sensitive personal records. Professional deployment needs private storage and access controls.
