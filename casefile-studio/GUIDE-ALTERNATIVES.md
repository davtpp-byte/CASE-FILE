# Main sources, permitted alternatives and upload feedback — v0.4.1

## A missing main file is not necessarily missing coverage

Automatic resolution is shared across current and future projects. When a permitted replacement was filed under a missing main (for example a portrait under a funeral-video slot), inspection normalizes the source link instead of requiring the user to remap IDs. No approval is created. This is filename/media-type-guided candidate selection, not semantic identity verification.

Each placement also has a source choice when the guide permits an alternative:

- **Automatic:** use the main source if it is available/usable for inspection; otherwise try a named, linked guide-permitted alternative.
- **Main:** insist on the main source. If it is missing, show that honestly rather than silently switching.
- **Alternative:** explicitly select one of the alternatives allowed for this placement, including when the main is present.

Availability does not imply permission. The app does not infer why a file is missing or mark licensing/factual/privacy checks complete because an alternative was chosen.

A source can be permitted as an alternative in one placement but inappropriate in another. There is no arbitrary source rotation. Global research text describing later courtroom material as an alternative for a later chapter does not authorize substituting it for an earlier hearing.

### What the importer recognizes

- Placement fields such as **Alternative**, **Alternatives**, **Fallback**, **Alt**, **If unavailable** or **If missing**.
- Associated **Alternative label**, **Alternative preview** and **Alternative care** fields.
- Explicit source-library alternative fields inherited by that main source's placements.
- Positive local rules such as “If S03 is unavailable, use S01 portrait instead.”
- Explicit `S03 ... or S04 ...` preview choices. Their source-video clock ranges stay separate.

Named choices can be selected automatically. A textual rule such as “use a permitted portrait” without a named source is shown but is **manual-only**: the user must select a guide-catalog source that actually satisfies the rule. A graphic-only or unclear instruction is retained and flagged, not treated as permission for unrelated video. Context-scoped/ambiguous rules are not silently applied everywhere. Known residential restrictions and required stop times still apply to the selected alternative.

For a guide previously imported by the old first-source-only parser, reimport the guide to read its alternative fields, then rebuild. You do not need to manually timecode narration in the guide. Its phrase anchors and the recording's timing exports still set the narration clock.

### Labels, source ranges and review are source-specific

The alternative does not inherit the main source's event/date caption or in/out window. It uses its own guide label/window when supplied. Otherwise a clearly identified alternative label is shown; ambiguous windows require a local selection or are disclosed inspection samples. Human context and privacy review is still necessary.

You can edit the alternative label in its placement. Switching sources invalidates the previous placement review/range while retaining narration timing. A previously reviewed main source does not automatically approve an alternative.

“Main files linked” is now labeled as exactly that—not a demand that every main must be downloaded. Placements using alternatives are counted separately. Final sign-offs can remain zero while inspecting.

## What the checkboxes mean

| Control | Meaning | Needed for first inspection? |
|---|---|---|
| Show captions | Show/hide text only; imported timing stays active. | Your preference. |
| Cue positions checked | You listened and checked the visual cut positions. Does not run sync. | No. |
| Transcript differences checked | You compared names/numbers/dates with the voice. Does not auto-correct text. | No. |
| Placement checked for final use | You checked this shot, its event/date label, privacy and Care. | No. |
| Reuse basis recorded | You documented the actual license/permission/reviewed legal basis. The app does not clear rights. | Not required just to view/inspect. |
| Contains residential property | Restriction flag: blocks use in prohibited chapters. Not an approval. | Set truthfully when applicable. |
| Allow visible gap cards | Permit placeholders in a deliberately partial inspection MP4. Does not approve content or replace an available guide alternative. | Only if actual gaps remain. |

Final-publication sign-offs are not editing-progress counters. **0/44 is not an error for an unreviewed inspection draft.** Never tick reviews merely to unlock a preview.

## Upload progress and limits

Current media upload limits are **512 MB per file**, **30 files per batch**. Narration/music cards take one selected track at a time. Limits are displayed beside the pickers. An oversized file or a 31-file selection is rejected on the client before sending.

The progress bar uses actual `XMLHttpRequest.upload` bytes-sent events, showing percentage and transferred sizes. It does not invent a percentage with a timer. After transfer reaches 100%, **Processing media on the server** is a separate state while decoding, waveform/thumbnail creation and the response finish. Only then is the upload complete.

If a later item fails after earlier files were accepted, the current media list is refreshed before retrying. Original computer files are never renamed or deleted. TXT/Markdown media-library imports have their separate 1 MB limit; narration-script, guide and timing inputs retain their document-specific parser limits.

These are current app limits, not a promise that every future hosting provider has identical request limits. No hosting migration or external database setup was performed for this functional update.

## Actual-case validation still pending

The attached original guide has 43 placements. The updated 44-placement version shown in the user's screenshots has not yet been supplied here. Synthetic tests prove the selection and upload behaviours; they do not establish that the two specific missing real-case sources have been resolved or licensed.
