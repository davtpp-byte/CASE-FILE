# Casefile Studio v0.3.2 — code-only update

**The hosted Arena preview is already updated. This ZIP is only for a separately downloaded installation.**

This update adds the separate Narration timestamps (SRT / JSON) panel, its gold upload button, a shortcut to it, and explicit source-download limitations. It includes the v0.3.1 CapCut reader. It is not a fresh installation and does not include example projects, actual recordings, or source footage.

## Safely update an existing v0.3.x installation

1. Stop your running app. Keep your existing `casefile-studio` folder; do not delete it.
2. Extract this ZIP into a separate temporary folder. **Do not use Finder's Replace-folder operation on your existing app**, which could remove unlisted data files.
3. In Terminal, run the updater with the path to the existing app folder. For example:

   `python3 apply_update.py "/path/to/your/casefile-studio"`

   On Windows, use `python` instead of `python3` if needed. Run this from the extracted update folder (the one containing apply_update.py).

   To validate without writing anything first, add `--check`.

4. The updater validates all fingerprints, backs up previous code under `.code-backups/`, and overlays only code/document files. **It never writes to or deletes anything inside `data/`**: projects, uploaded narration/media, exports and settings remain there. If validation fails, it stops before making changes.
5. Restart the app normally and refresh the browser. Under Episode setup, look just below the four input cards for **Narration timestamps (SRT / JSON)** and **Upload SRT / JSON**. The panel is marked **v0.3.2**.

Imports apply to the selected project. Upload the matching CapCut JSON and SRT one at a time, in either order. Hiding captions does not remove timing data.

**Actual footage/photos are still needed.** Editing-guide links are research references; this build does not automatically download them. Full authorized originals can be uploaded and cut from reviewed source windows; optional S03-style naming is a convenience, not a requirement.
