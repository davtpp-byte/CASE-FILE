# Where to import timestamps — v0.3.2

## SRT / CapCut JSON

1. Select **your working project** and open **Episode setup**.
2. Click **SRT / JSON timestamps** near the top, or scroll just below the four audio/document cards.
3. The full-width **Narration timestamps (SRT / JSON)** panel has a gold **Upload SRT / JSON** button.
4. Choose `draft_info.json` and the matching SRT **one at a time, in either order**. An SRT saved with a `.srt.md` suffix is accepted by content.
5. Read **Attached to this project** and the imported timing summary to confirm both files are present.

Imports are **per project**, not shared across every episode. The previously preloaded The Last Timeline example has its own timing pack. Another working project needs its own imports, even if it uses the same script.

CapCut draft files reference audio; they do not upload the recording. Use the exact matching narration MP3/WAV in **Finished narration**. A grouped date/phrase does not supply an individual start for every interior word. SRT-only word positions remain estimates. Review the actual sound and the transcript differences.

**Captions remain optional:** hiding text does not remove its timing clock or move the guide cuts.

## Footage / photos

**The guide's links are references, not imported media. This build does not automatically download footage from those links.**

Use **Source files → Upload footage / photos** to import actual authorized clips and images. Then link each reference source to its file and review its local source-video in/out range, reuse basis, date/context label, and Care instructions.

- Full originals are usable within the upload limits; no need to manually pre-trim every shot.
- You can keep original filenames and link manually. Names such as `S03.mp4` are optional conveniences for filename matching, not a requirement.
- The narration clock determines **when** footage appears. The source-video in/out clock determines **which part** is shown.
- Links, uploaded files, or checkboxes do not establish licenses, factual accuracy, visual identity, or context. Missing coverage stays marked, not replaced with invented evidence.

## Seeing the update

The interface now displays **v0.3.2** beside WORKING PROTOTYPE. Use the refresh arrow in the Casefile Studio preview. If necessary, hard-refresh the browser. The script/CSS URLs include a version query to avoid retaining old cached bundles.

Restarting the hosted preview does **not** replace code in a separately downloaded installation. For an existing installation, use the **code-only v0.3.2 update** rather than replacing its data folder with a preloaded example. The code updater never writes inside `data/`, which contains your projects, uploads, and exports.
