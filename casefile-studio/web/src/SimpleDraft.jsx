import React, { useState } from "react";
import {
  Mic,
  FolderOpen,
  FileText,
  Clock3,
  Play,
  Film,
  CheckCircle2,
} from "lucide-react";
import { UploadProgress, uploadLimits } from "./Uploads.jsx";

function Pick({
  label,
  accept,
  multiple = false,
  onFiles,
  disabled,
  children,
}) {
  return (
    <label className={`quick-pick ${disabled ? "disabled" : ""}`}>
      <input
        type="file"
        aria-label={label}
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={(ev) => {
          const f = [...ev.target.files];
          ev.target.value = "";
          if (f.length) onFiles(f);
        }}
      />
      {children}
    </label>
  );
}

export default function SimpleDraft({
  project,
  busy,
  onMedia,
  onImport,
  onPreview,
  onOptions,
  progress,
  backupStatus,
}) {
  const [quality, setQuality] = useState("480p");
  const e = project.episode || {};
  const docs = !!(e.script && e.guide);
  const voice = project.assets.find((a) => a.id === project.narration_id);
  const visuals = project.assets.filter((a) =>
    ["image", "video"].includes(a.kind),
  );
  const canPreview = docs && visuals.length > 0 && !project.is_demo;
  return (
    <section className="simple-draft" aria-label="Make your first draft">
      {window.top !== window && (
        <div className="embedded-download-warning">
          <b>This embedded preview blocks file downloads.</b>
          <p>
            Use the full editor in a normal browser tab for saving. Right-click
            the link and choose Open Link in New Tab if the preview blocks a
            normal click.
          </p>
          <a
            href={window.location.href}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open full editor
          </a>
          <input
            aria-label="Full editor address"
            readOnly
            value={window.location.href}
            onFocus={(ev) => ev.target.select()}
          />
        </div>
      )}
      <div className="simple-draft-heading">
        <div>
          <span className="eyebrow">ADD FILES → PREVIEW → DOWNLOAD</span>
          <h3>Your first draft, without the checklist.</h3>
        </div>
        <span className="simple-local-save">
          {backupStatus === "saved"
            ? "Setup auto-saved in this browser"
            : backupStatus === "unavailable"
              ? "Browser backup unavailable — use Save backup"
              : backupStatus === "newer-saved-copy"
                ? "A newer browser setup backup is protected"
                : "Automatic setup backup · media not included"}
        </span>
      </div>
      <p className="simple-intro">
        Choose your files. We match source IDs, rebuild the inspection timeline
        and open the first real visual. No final-publication sign-offs are
        needed to preview.
      </p>
      <div className="simple-files">
        <div className="simple-file">
          <Mic size={19} />
          <div>
            <b>Narration</b>
            <small>
              {voice
                ? voice.name
                : "Add your finished recording for sound and video export."}
            </small>
          </div>
          <Pick
            label="Quick add narration"
            accept="audio/*,.mp3,.wav,.m4a,.flac"
            disabled={busy || project.is_demo}
            onFiles={(f) => onMedia("narration_id", f, true)}
          >
            {voice ? "Replace recording" : "Choose recording"}
          </Pick>
          <span className="simple-file-limit">512 MB per file</span>
        </div>
        <div className="simple-file">
          <FolderOpen size={19} />
          <div>
            <b>Footage & photos</b>
            <small>
              {visuals.length
                ? `${visuals.length} visual file(s) in this saved session.`
                : "Start with one source photo or video. No need for a big batch first."}
            </small>
          </div>
          <Pick
            label="Quick add footage or photos"
            accept="video/*,image/*,.mp4,.mov,.webm,.jpg,.jpeg,.png"
            multiple
            disabled={busy || project.is_demo}
            onFiles={(f) => onMedia(null, f, true)}
          >
            Choose source files
          </Pick>
          <span className="simple-file-limit">{uploadLimits}</span>
        </div>
      </div>
      {!docs && (
        <div className="simple-docs">
          {!e.script && (
            <Pick
              label="Quick add narration script"
              accept=".md,.txt"
              disabled={busy || project.is_demo}
              onFiles={(f) => onImport("script", f)}
            >
              <FileText size={14} /> Choose narration script
            </Pick>
          )}
          {!e.guide && (
            <Pick
              label="Quick add editing guide"
              accept=".md,.txt"
              disabled={busy || project.is_demo}
              onFiles={(f) => onImport("guide", f)}
            >
              <FileText size={14} /> Choose editing guide
            </Pick>
          )}
          <small>
            Script and guide stay separate. The guide tells us which source to
            show at each phrase.
          </small>
        </div>
      )}
      {docs && (
        <div className="simple-ready">
          <CheckCircle2 size={13} />
          {e.script.word_count.toLocaleString()} script words ·{" "}
          {e.guide.cues.length} guide placements ·{" "}
          {e.timings
            ? `${e.timings.captions?.length || 0} timed caption blocks`
            : "no timing file yet"}
        </div>
      )}
      <details className="quick-timings" open={!e.timings}>
        <summary>
          {e.timings
            ? "Timing attached · add or replace matching SRT / JSON"
            : "Optional: add SRT / word-timing JSON"}
        </summary>
        <Pick
          label="Quick add timing file"
          accept=".srt,.json,.vtt,.md"
          disabled={busy || project.is_demo}
          onFiles={(f) => onImport("timings", f)}
        >
          <Clock3 size={13} /> Choose SRT / word-timing JSON
        </Pick>
        <small>
          Add the matching exports one after the other. Captions remain
          optional.
        </small>
      </details>
      <UploadProgress progress={progress} />
      <div className="simple-draft-actions">
        <button
          className="btn primary simple-preview"
          aria-label="Preview my draft"
          disabled={busy || !canPreview}
          onClick={() => onPreview({ render: false })}
        >
          <Play size={16} />
          {busy ? "Preparing…" : "Preview my draft"}
        </button>
        <button
          className="btn"
          aria-label="Make downloadable inspection video"
          disabled={busy || !canPreview || !voice}
          onClick={() => onPreview({ render: true, resolution: quality })}
        >
          <Film size={14} /> Make downloadable video
        </button>
        <select
          aria-label="Quick draft quality"
          value={quality}
          onChange={(ev) => setQuality(ev.target.value)}
          disabled={busy}
        >
          <option value="480p">480p · quick check</option>
          <option value="720p">720p · HD draft</option>
          <option value="1080p">1080p · full HD</option>
        </select>
      </div>
      <p className="simple-next" aria-live="polite">
        {!docs
          ? "Add the script and editing guide above first."
          : !visuals.length
            ? "Add at least one photo or video. A linked name alone is not a preview."
            : !voice
              ? "Picture preview is available now. Add your matching recording for narration and MP4 export."
              : "Ready to preview. You do not need to rebuild separately or tick review acknowledgements."}
      </p>
      <div className="simple-settings">
        <label>
          <input
            type="checkbox"
            aria-label="Quick show captions"
            checked={project.captions}
            disabled={busy || project.is_demo}
            onChange={(ev) => onOptions(ev.target.checked)}
          />{" "}
          Show captions
        </label>
        <span>
          Inspection videos are marked UNREVIEWED and include visible cards for
          any missing coverage. Originals on your computer are not changed.
        </span>
      </div>
    </section>
  );
}
