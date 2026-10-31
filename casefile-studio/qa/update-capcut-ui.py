from pathlib import Path
p=Path('episode.py');s=p.read_text()
s=s.replace('if all("word" in e for e in entries)','if all("word" in e and len(tokens(str(e["word"]))) == 1 for e in entries)',1)
s=s.replace('    if timing and voice and max(w["end"] for w in timing["words"]) > duration + 0.05:', '''    if timing and voice and timing.get("source_kind") == "capcut" and abs(timing["duration"] - duration) > 0.05:
        errors.append("The recording duration differs from the CapCut narration timeline by more than 50 ms. Upload the exact matching recording or re-export its timings; no offset/stretch was guessed.")
    if timing and voice and max(w["end"] for w in timing["words"]) > duration + 0.05:''',1)
s=s.replace('        "timing_precision": (timing or {}).get("precision"),','        "timing_precision": (timing or {}).get("precision"),\n        "transcript_reviewed": e.get("transcript_reviewed_digest") == input_digest(project),',1)
s=s.replace('and e.get("timing_reviewed_digest") != input_digest(project)\n    ):','and e.get("transcript_reviewed_digest") != input_digest(project)\n    ):',1)
p.write_text(s)
p=Path('app.py');s=p.read_text().replace('        "confirm_timing",','        "confirm_timing",\n        "confirm_transcript",',1)
s=s.replace('        p["review"]["picture"] = False\n        return episode_result(p)\n\n\n@app.post("/api/projects/{id}/episode/autolink")','''        if body.get("confirm_transcript") is True:
            report = episode.analyze(p)
            if not report["has_voice"] or report["errors"]:
                raise HTTPException(422, "Upload the exact matching narration and resolve timing errors before confirming transcript review.")
            e["transcript_reviewed_digest"] = episode.input_digest(p)
        elif "confirm_transcript" in body:
            e.pop("transcript_reviewed_digest", None)
        p["review"]["picture"] = False
        return episode_result(p)


@app.post("/api/projects/{id}/episode/autolink")''',1)
p.write_text(s)
p=Path('renderer.py');s=p.read_text().replace('if options.get("captions", True) and scene.get("narration"):','if options.get("captions", True) and (scene.get("narration") or scene.get("captions")):',1);p.write_text(s)
p=Path('web/src/EpisodeSetup.jsx');s=p.read_text()
s=s.replace('className={cue.timing_source === "estimated" ? "estimated" : ""}','className={cue.timing_source?.includes("estimate") || cue.timing_review_required ? "estimated" : ""}',1)
s=s.replace('{cue.timing_source === "estimated" ? " est." : ""}','{cue.timing_review_required ? " · text review" : cue.timing_source?.includes("estimate") ? " est." : ""}',1)
s=s.replace('''            Optional: upload your narration's SRT or word-timing JSON for better
            cue alignment.''','''            Optional: upload CapCut draft JSON and the matching SRT, one after
            the other (either order). Word units place cuts; SRT preserves caption
            holds. SRT alone cannot provide interior word starts.''',1)
s=s.replace('accept=".srt,.vtt,.json"','accept=".srt,.vtt,.json,.md"',1)
a=s.index('          {e.timings && (\n            <p className="ep-small">');b=s.index('\n        </Material>',a)
s=s[:a]+'''          {e.timings && (
            <div className="ep-timing-summary" aria-label="Imported timing summary">
              <p className="ep-small">
                <b>{report?.timing_word_match_percent ?? 0}% normalized transcript match.</b>{" "}
                {e.timings.source_kind === "capcut"
                  ? `${e.timings.words.length.toLocaleString()} supplied timing units; ${e.timings.grouped_units} include multiple comparison tokens. No interior word times invented.`
                  : e.timings.precision === "word"
                    ? "Supplied word timestamps; audio review still required."
                    : "Word positions inside segments are estimates, not exact word alignment."}
              </p>
              {!!report?.imported_caption_count && <p className="ep-small">
                {report.imported_caption_count} supplied caption blocks preserved
                {e.timings.captions_source === "srt" ? " from SRT" : " from CapCut"}.
                Hiding captions does not remove this clock.
              </p>}
              {e.timings.audio_reference_filename && !report?.has_voice &&
                <p className="ep-timing-pending">Audio referenced, not uploaded: <b>{e.timings.audio_reference_filename}</b></p>}
              {!!report?.timing_candidate_cues?.length && <p className="ep-timing-pending">
                Cue-start text substitutions need review: {report.timing_candidate_cues.join(", ")}. These are proposals, not verified alignment.
              </p>}
              {!!report?.transcript_comparison?.difference_spans && <details className="ep-transcript-audit">
                <summary>Review transcript differences ({report.transcript_comparison.difference_spans})</summary>
                <p className="ep-small">Comparison spans include formatting and apparent ASR differences—not confirmed spoken errors. Compare with the audio; no script, voice, or caption text was corrected automatically. Correct captions in your source export and re-upload the matching SRT if needed.</p>
                <div className="ep-difference-list" tabIndex={0} aria-label="Transcript differences">
                  {report.transcript_comparison.differences.map((d, i) => <div key={i}>
                    <small>{d.start == null ? "End of transcript" : tc(d.start)} · caption {d.caption_number ?? "—"}</small>
                    <p><b>Script:</b> {d.script || "[no text]"}</p>
                    <p><b>Timing transcript:</b> {d.transcript || "[no text]"}</p>
                  </div>)}
                </div>
              </details>}
              {!!report?.imported_caption_count && <a className="ep-small" href={`/api/projects/${project.id}/captions.srt`} download>Download supplied caption track</a>}
            </div>
          )}''' +s[b:]
s=s.replace('''{report.duration_estimated
                ? "Estimated spoken length"
                : "Actual narration length"}''','''{report.duration_basis === "timing-export"
                ? "Timing-export length · audio missing"
                : report.duration_estimated ? "Estimated spoken length" : "Actual narration length"}''',1)
s=s.replace('''            I checked the cue positions against the actual narration
          </label>''','''            I checked the cue positions against the actual narration
          </label>
          {!!report?.transcript_comparison?.difference_spans && <label className="ep-checkbox">
            <SavedCheck
              type="checkbox"
              aria-label="Timing transcript differences reviewed"
              checked={!!report?.transcript_reviewed}
              disabled={disabled || !voice || !ready}
              onChange={(ev) => save("/episode/options", "PATCH", { confirm_transcript: ev.target.checked })}
            />{" "}
            I compared the transcript differences with the audio and resolved caption/factual discrepancies
          </label>}''',1)
p.write_text(s)
p=Path('web/src/main.jsx');s=p.read_text()
s=s.replace('''{selected.timing === "transcribed"
                    ? "Source-aligned segment timing"''','''{selected.timing === "imported-captions"
                    ? "Supplied caption timestamps · cue/audio review required"
                    : selected.timing === "transcribed"
                    ? "Source-aligned segment timing"''',1)
s=s.replace('''                    : "estimated plan"
                  : "assembled"}''','''                    : project.episode?.timings ? "timed plan · audio missing" : "estimated plan"
                  : "assembled"}''',1)
s=s.replace('{project.captions && activeScene?.narration && (','{project.captions && (activeScene?.narration || activeScene?.captions?.length) && (',1)
s=s.replace('if (activeScene.captions?.length)\n','if (activeScene.captions_exact || activeScene.captions?.length)\n',1)
s=s.replace('''                    : "Timing estimated at 145 wpm. Add narration for a complete draft."}''','''                    : project.episode?.timings ? "Imported clock active; upload the exact matching narration." : "Timing estimated at 145 wpm. Add narration for a complete draft."}''',1)
p.write_text(s)
p=Path('web/src/episode.css');s=p.read_text()+'''
.ep-timing-summary { border-top: 1px solid #34332f; margin-top: 14px; padding-top: 4px; overflow-wrap: anywhere; }
.ep-timing-summary b { color: #d0c6b5; }
.ep-timing-pending { color: #d0ac78; font-size: 10px; line-height: 1.65; margin: 10px 0; }
.ep-transcript-audit { margin: 14px 0; font-size: 10px; color: #c9b99f; }
.ep-transcript-audit summary { cursor: pointer; line-height: 1.6; }
.ep-difference-list { max-height: 260px; overflow: auto; margin-top: 10px; border: 1px solid #39362f; border-radius: 5px; padding: 0 10px; outline-offset: 3px; }
.ep-difference-list > div { padding: 10px 0; border-bottom: 1px solid #34332f; }
.ep-difference-list small { color: #a58e6a; }
.ep-difference-list p { color: #b9b5ad; font-size: 10px; line-height: 1.6; margin: 5px 0; }
''';p.write_text(s)
