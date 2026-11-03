import React, { useEffect, useRef, useState } from "react";
import {
  Mic,
  Music2,
  FileText,
  Clapperboard,
  Upload,
  Check,
  CheckCircle2,
  ArrowRight,
  ArrowUpRight,
  ShieldCheck,
  AlertTriangle,
  ExternalLink,
  Link2,
  LoaderCircle,
  Film,
  Download,
  ChevronDown,
  Play,
  Clock3,
  VolumeX,
  FolderOpen,
  Info,
  RefreshCw,
} from "lucide-react";
import "./episode.css";
import SimpleDraft from "./SimpleDraft.jsx";
import { keepWorkingFiles } from "./MediaSession.js";
import { UploadProgress, validateUpload, uploadLimits } from "./Uploads.jsx";
const tc = (n) => {
  n = Math.max(0, Number(n) || 0);
  return `${Math.floor(n / 60)}:${String(Math.floor(n % 60)).padStart(2, "0")}`;
};
const tcMs = (n) => {
  const ms = Math.round(Math.max(0, Number(n) || 0) * 1000);
  return `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}.${String(ms % 1000).padStart(3, "0")}`;
};
const percent = (n) => `${Math.round(n || 0)}%`;
function FilePick({
  label,
  accept,
  multiple = false,
  onFiles,
  disabled = false,
  children,
  className = "",
  limit = "",
}) {
  return (
    <>
      <label
        className={`ep-file-pick ${className} ${disabled ? "disabled" : ""}`}
      >
        <input
          aria-label={label}
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          onChange={(e) => {
            const files = [...e.target.files];
            e.target.value = "";
            if (files.length) onFiles(files);
          }}
        />
        {children || (
          <>
            <Upload size={14} />
            {label}
          </>
        )}
      </label>
      {limit && <small className="upload-limit-hint">{limit}</small>}
    </>
  );
}
function SavedCheck({ checked, onChange, ...props }) {
  const [pending, setPending] = useState(null);
  return (
    <input
      {...props}
      type="checkbox"
      checked={pending ?? checked}
      onChange={(ev) => {
        setPending(ev.target.checked);
        Promise.resolve(onChange(ev)).then(
          () => setPending(null),
          () => setPending(null),
        );
      }}
    />
  );
}
function Material({ number, icon: Icon, title, status, ready, children }) {
  return (
    <section className={`ep-material ${ready ? "ready" : ""}`}>
      <div className="ep-material-head">
        <span className="ep-material-number">0{number}</span>
        <div className="ep-material-icon">
          <Icon size={19} />
        </div>
        <div>
          <h3>{title}</h3>
          <span>{status}</span>
        </div>
        {ready ? (
          <CheckCircle2 size={16} className="ep-check" />
        ) : (
          <span className="ep-missing-dot" />
        )}
      </div>
      <div className="ep-material-body">{children}</div>
    </section>
  );
}
function SourceRow({
  source,
  project,
  expanded,
  onExpand,
  save,
  disabled,
  replacements = [],
  optional = false,
}) {
  const binding = project.episode?.bindings?.[source.id] || {};
  const assets = project.assets.filter((a) =>
    ["image", "video"].includes(a.kind),
  );
  const file = assets.find((a) => a.id === binding.asset_id);
  const row = useRef(null);
  const [previewError, setPreviewError] = useState(false);
  useEffect(() => setPreviewError(false), [file?.id]);
  useEffect(() => {
    if (expanded)
      row.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [expanded]);
  return (
    <div ref={row} className={`ep-source ${expanded ? "expanded" : ""}`}>
      <button className="ep-source-summary" onClick={onExpand}>
        <span className={`ep-id ${file ? "linked" : ""}`}>{source.id}</span>
        <div>
          <b>{source.title}</b>
          <small>
            {file
              ? file.name
              : replacements.length
                ? `Guide alternative ${[...new Set(replacements.map((c) => c.source_id))].join(", ")} selected for ${replacements.length} placement(s)`
                : optional
                  ? "Optional guide source · not required for main coverage"
                  : "Reference link only · actual file needed"}
          </small>
        </div>
        {binding.rights_confirmed ? (
          <ShieldCheck size={14} />
        ) : file ? (
          <Link2 size={14} />
        ) : (
          <Upload size={13} />
        )}
        <ChevronDown size={13} />
      </button>
      {file && !expanded && (
        <button
          className="ep-preview-source"
          aria-label={`Preview source ${source.id}`}
          onClick={onExpand}
        >
          <Play size={12} /> Preview uploaded {file.kind} · no sign-off required
        </button>
      )}
      {expanded && (
        <div className="ep-source-detail">
          <a href={source.url} target="_blank" rel="noreferrer noopener">
            <ExternalLink size={12} /> Open original reference{" "}
            <ArrowUpRight size={11} />
          </a>
          <p className="ep-rights-note">
            <ShieldCheck size={13} />
            <span>{source.rights_note}</span>
          </p>
          <label className="field">
            Actual uploaded file
            <select
              aria-label={`File for ${source.id}`}
              disabled={disabled}
              value={binding.asset_id || ""}
              onChange={(e) =>
                save(`/episode/source/${source.id}`, "PATCH", {
                  asset_id: e.target.value || null,
                })
              }
            >
              <option value="">Not linked — do not substitute</option>
              {assets.map((a) => (
                <option value={a.id} key={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </label>
          {file && (
            <>
              <p className="ep-preview-note">
                SOURCE INSPECTION · viewing this file does not approve its
                identity, context or reuse.
              </p>
              {file.kind === "video" ? (
                <video
                  aria-label={`Review source ${source.id}`}
                  src={file.url}
                  onError={() => setPreviewError(true)}
                  controls
                  muted
                  playsInline
                  preload="metadata"
                />
              ) : (
                <img
                  src={file.url}
                  onError={() => setPreviewError(true)}
                  alt={`Uploaded file linked by producer to ${source.id}`}
                />
              )}
              {previewError && (
                <p className="ep-inline-warning" role="alert">
                  This file cannot be loaded from the current server or decoded
                  by this browser. Keep your original; save a project backup
                  before refreshing. Missing file bytes and unsupported formats
                  need repair, not false approval checkmarks.
                </p>
              )}
              <label className="field">
                Permission / license or reviewed reuse basis
                <textarea
                  aria-label={`Rights notes for ${source.id}`}
                  key={file.id + file.license}
                  defaultValue={file.license || ""}
                  rows={3}
                  disabled={disabled}
                  placeholder="Owner, permitted use, credit, written permission or reviewed legal basis; include any embedded media."
                  onBlur={(e) => {
                    if (e.target.value !== (file.license || ""))
                      save(`/episode/source/${source.id}`, "PATCH", {
                        license: e.target.value,
                      });
                  }}
                />
              </label>
              <label className="ep-checkbox">
                <SavedCheck
                  type="checkbox"
                  aria-label={`Rights basis recorded for ${source.id}`}
                  checked={!!binding.rights_confirmed}
                  disabled={disabled || !file.license?.trim()}
                  onChange={(e) =>
                    save(`/episode/source/${source.id}`, "PATCH", {
                      rights_confirmed: e.target.checked,
                    })
                  }
                />
                <span>
                  <b>I recorded this file's reuse basis for final use</b>
                  <small>
                    Tick only after documenting the actual license, permission
                    or reviewed legal basis. Not required to watch the file or
                    build an inspection draft; CASEFILE has not cleared it for
                    you.
                  </small>
                </span>
              </label>
              <label className="ep-checkbox">
                <SavedCheck
                  type="checkbox"
                  aria-label={`Residential imagery in ${source.id}`}
                  checked={!!binding.contains_residence}
                  disabled={disabled}
                  onChange={(e) =>
                    save(`/episode/source/${source.id}`, "PATCH", {
                      contains_residence: e.target.checked,
                    })
                  }
                />
                <span>
                  <b>This file contains houses or residential property</b>
                  <small>
                    This is a restriction flag, not an approval. It blocks use
                    in chapters that prohibit residential imagery.
                  </small>
                </span>
              </label>
            </>
          )}
          <p className="ep-small">
            A matching filename only links a file. It does not verify who/what
            is shown or grant permission. Supply pre-cropped or blurred media
            where the guide requires it.
          </p>
        </div>
      )}
    </div>
  );
}
function Cue({
  cue,
  project,
  disabled,
  save,
  onListen,
  onSource,
  inspection = false,
}) {
  const review = project.episode?.reviews?.[cue.id] || {};
  const file = project.assets.find((a) => a.id === cue.asset_id);
  const [values, setValues] = useState({
    in: review.in ?? "",
    out: review.out ?? "",
    narration_start: review.narration_start ?? "",
    narration_end: review.narration_end ?? "",
    reviewed: !!review.reviewed,
  });
  useEffect(
    () =>
      setValues({
        in: review.in ?? "",
        out: review.out ?? "",
        narration_start: review.narration_start ?? "",
        narration_end: review.narration_end ?? "",
        reviewed: !!review.reviewed,
      }),
    [JSON.stringify(review), cue.asset_id],
  );
  const set = (k, v) => setValues((p) => ({ ...p, [k]: v }));
  function apply() {
    const data = { reviewed: values.reviewed };
    for (const k of ["in", "out", "narration_start", "narration_end"])
      data[k] = values[k] === "" ? null : Number(values[k]);
    return save(`/episode/cue/${cue.id}`, "PATCH", data);
  }
  return (
    <details className={`ep-cue ${cue.ready ? "ready" : ""}`}>
      <summary>
        <span className="ep-cue-no">{cue.id}</span>
        <div>
          <div className="ep-cue-top">
            <small>{cue.chapter_label}</small>
            <span>
              {cue.source_id}
              {cue.using_alternative
                ? ` · alternative for ${cue.primary_source_id}`
                : ""}
            </span>
            <span
              className={
                cue.timing_source?.includes("estimate") ||
                cue.timing_review_required
                  ? "estimated"
                  : ""
              }
            >
              <Clock3 size={10} />
              {cue.narration_start == null
                ? "Unmatched"
                : tcMs(cue.narration_start)}
              {cue.timing_review_required
                ? " · text review"
                : cue.timing_source?.includes("estimate")
                  ? " est."
                  : ""}
            </span>
          </div>
          <h4>“{cue.anchor}”</h4>
          <p>
            {cue.ready
              ? "Producer-reviewed source window"
              : inspection
                ? cue.inspection_ready
                  ? "Available in inspection mode · not approved"
                  : cue.inspection_status
                : cue.status_detail}
          </p>
        </div>
        {cue.ready ? <CheckCircle2 size={15} /> : <ChevronDown size={14} />}
      </summary>
      <div className="ep-cue-body">
        <div className="ep-cue-directive">
          <span>
            {cue.using_alternative
              ? "SHOW · SELECTED GUIDE ALTERNATIVE"
              : "SHOW"}
          </span>
          <p>
            {cue.using_alternative
              ? cue.source_choices?.find((o) => o.source_id === cue.source_id)
                  ?.instructions ||
                cue.alternative_instructions ||
                cue.show
              : cue.show}
          </p>
        </div>
        {(cue.source_choices?.length > 1 || cue.alternative_instructions) && (
          <div className="ep-alternative-choice">
            <b>Source choice for this placement</b>
            {cue.alternative_instructions && (
              <p>
                <b>Guide's alternative instruction:</b>{" "}
                {cue.alternative_instructions}
              </p>
            )}
            {cue.source_choices?.length > 1 ? (
              <label className="field">
                Main or guide-permitted alternative
                <select
                  aria-label={`Source choice ${cue.id}`}
                  value={
                    cue.selection_mode === "alternative"
                      ? `alternative:${cue.source_id}`
                      : cue.selection_mode || "auto"
                  }
                  disabled={disabled}
                  onChange={(ev) => {
                    const value = ev.target.value;
                    save(
                      `/episode/choice/${cue.id}`,
                      "PATCH",
                      value.startsWith("alternative:")
                        ? {
                            mode: "alternative",
                            source_id: value.split(":")[1],
                          }
                        : { mode: value },
                    );
                  }}
                >
                  <option value="auto">
                    Automatic · main, otherwise named guide alternative
                  </option>
                  <option value="primary">
                    Main · {cue.primary_source_id} —{" "}
                    {project.episode?.guide?.sources?.find(
                      (s) => s.id === cue.primary_source_id,
                    )?.title || "guide source"}
                  </option>
                  {cue.source_choices
                    .filter((o) => o.kind === "alternative")
                    .map((o) => (
                      <option
                        key={o.source_id}
                        value={`alternative:${o.source_id}`}
                      >
                        {o.optional ? "Optional guide source" : "Alternative"} ·{" "}
                        {o.source_id} —{" "}
                        {project.episode?.guide?.sources?.find(
                          (s) => s.id === o.source_id,
                        )?.title || "guide alternative"}
                        {o.manual_only
                          ? " · choose only if it fits the guide's rule"
                          : ""}
                      </option>
                    ))}
                </select>
              </label>
            ) : (
              <p>
                The guide names a non-file or unclear alternative. Its
                instruction is retained; no unrelated footage is chosen
                automatically. Clarify the permitted source or editorial
                graphic.
              </p>
            )}
            <p>
              Selected:{" "}
              <b>
                {cue.source_id}
                {cue.using_alternative
                  ? ` instead of ${cue.primary_source_id}`
                  : " (main)"}
              </b>
              . {cue.selection_reason}
            </p>
            {cue.using_alternative && (
              <label className="field">
                Alternative's own on-screen label
                <input
                  aria-label={`Alternative label ${cue.id}`}
                  key={cue.source_id + cue.label}
                  defaultValue={cue.label}
                  disabled={disabled}
                  onBlur={(ev) => {
                    if (ev.target.value !== cue.label)
                      save(`/episode/choice/${cue.id}`, "PATCH", {
                        label: ev.target.value,
                      });
                  }}
                />
              </label>
            )}
            <small>
              Changing sources does not change narration timing or grant reuse
              permission. Do not carry a primary event/date label onto a
              different alternative shot.
            </small>
          </div>
        )}
        {!!cue.additional_previews?.length && (
          <div className="ep-companion-note">
            <b>Additional guide follow-up · separate source clock</b>
            {cue.additional_previews.map((ref) => (
              <p key={ref.source_id}>
                {ref.source_id}: {ref.title}. The guide describes a follow-up,
                not an automatic replacement. This single-source slot does not
                silently splice it or use its timestamps on the main file.
              </p>
            ))}
          </div>
        )}
        <div className="ep-cue-directive">
          <span>ON-SCREEN LABEL</span>
          <p className="ep-label-preview">{cue.label}</p>
        </div>
        <div className="ep-care">
          <ShieldCheck size={14} />
          <div>
            <b>CARE · REQUIRED CONTEXT</b>
            <p>{cue.care}</p>
          </div>
        </div>
        <div className="ep-cue-reference">
          <button onClick={() => onSource(cue.source_id)}>
            <FolderOpen size={12} /> {cue.source_id} source file{" "}
            <ArrowRight size={11} />
          </button>
          {cue.reference_url && (
            <a
              href={cue.reference_url}
              target="_blank"
              rel="noreferrer noopener"
            >
              Reference preview <ArrowUpRight size={11} />
            </a>
          )}
          <button
            disabled={!project.narration_id || cue.narration_start == null}
            onClick={() => onListen(cue.narration_start)}
          >
            <Play size={11} /> Listen at cue
          </button>
        </div>
        <p className="ep-small">
          {cue.suggested_windows.length
            ? `Guide preview: ${cue.suggested_windows.map((w) => `${tc(w.start)}–${tc(w.end)}`).join(" or ")} (approximate). `
            : ""}
          Review the actual uploaded file. Enter its own file-clock in/out
          points; an extracted excerpt may start at 0:00.
        </p>
        {cue.inspection_ready && !cue.ready && (
          <p className="ep-inspection-window">
            <b>Inspection candidate, not approval:</b> {cue.inspection_basis}
            {cue.inspection_window
              ? ` · local source ${tcMs(cue.inspection_window.in)}–${tcMs(cue.inspection_window.out)}`
              : ""}
            . Identity, privacy and Care still need review.
          </p>
        )}
        {!file ? (
          <div className="ep-inline-warning">
            <Upload size={13} /> Link the actual source file first. A web link
            is not a video file.
          </div>
        ) : (
          <>
            {file.kind === "video" && (
              <div className="ep-time-grid">
                <label className="field">
                  Clip in (seconds)
                  <input
                    aria-label={`Clip in ${cue.id}`}
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder={String(cue.suggested_windows[0]?.start ?? 0)}
                    value={values.in}
                    onChange={(e) => set("in", e.target.value)}
                    disabled={disabled}
                  />
                </label>
                <label className="field">
                  Clip out (seconds)
                  <input
                    aria-label={`Clip out ${cue.id}`}
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder={String(cue.suggested_windows[0]?.end ?? "")}
                    value={values.out}
                    onChange={(e) => set("out", e.target.value)}
                    disabled={disabled}
                  />
                </label>
              </div>
            )}
            <details className="ep-cue-timing">
              <summary>
                Narration cue timing{" "}
                {cue.requires_stop ? "· stop time required" : ""}
              </summary>
              <div className="ep-time-grid">
                <label className="field">
                  Start in narration (seconds)
                  <input
                    aria-label={`Narration start ${cue.id}`}
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder={String(
                      Math.round((cue.narration_start || 0) * 100) / 100,
                    )}
                    value={values.narration_start}
                    onChange={(e) => set("narration_start", e.target.value)}
                    disabled={disabled}
                  />
                </label>
                <label className="field">
                  Stop showing this visual (seconds)
                  {cue.requires_stop && (
                    <b className="ep-required">Required by guide</b>
                  )}
                  <input
                    aria-label={`Narration stop ${cue.id}`}
                    type="number"
                    min="0"
                    step="0.01"
                    value={values.narration_end}
                    onChange={(e) => set("narration_end", e.target.value)}
                    disabled={disabled}
                  />
                </label>
              </div>
              <p className="ep-small">
                These use the narration audio's clock, not the source video's
                clock. Blank start keeps the planned position. An explicit stop
                prevents a contextual clip bleeding into the next account.
              </p>
            </details>
            <label className="ep-checkbox">
              <input
                type="checkbox"
                aria-label={`Reviewed placement ${cue.id}`}
                checked={values.reviewed}
                disabled={disabled}
                onChange={(e) => set("reviewed", e.target.checked)}
              />
              <span>
                <b>I checked this visual for final use</b>
                <small>
                  I watched the selected clip/photo and checked its identity,
                  event/date label, privacy and Care instructions. Not required
                  just to see it in inspection.
                </small>
              </span>
            </label>
            <p className="ep-small">
              For inspection, you may save a source window with the approval box
              unticked. That does not approve its reuse, identity or Care.
            </p>
            <button
              className="btn"
              aria-label="Save placement review"
              disabled={disabled}
              onClick={apply}
            >
              <Check size={12} />{" "}
              {values.reviewed
                ? "Save placement review"
                : "Save window without approval"}
            </button>
          </>
        )}
      </div>
    </details>
  );
}
export default function EpisodeSetup({
  project,
  api,
  locked,
  onFlush,
  onProject,
  onBusy,
  onError,
  onNotify,
  onNavigate,
  onRender,
  onNew,
  onQuickDraft,
  backupStatus,
}) {
  const e = project.episode || {};
  const guide = e.guide;
  const script = e.script;
  const [report, setReport] = useState(null),
    [working, setWorking] = useState(false),
    [chapter, setChapter] = useState("all"),
    [showAll, setShowAll] = useState(false),
    [sourceOpen, setSourceOpen] = useState(null),
    [gaps, setGaps] = useState(false),
    [resolution, setResolution] = useState("720p"),
    [planningMode, setPlanningMode] = useState(e.plan?.mode || "inspection"),
    [transfer, setTransfer] = useState(null),
    [advancedOpen, setAdvancedOpen] = useState(false);
  const audio = useRef(null),
    sourcePanel = useRef(null),
    timingPanel = useRef(null);
  const disabled = locked || working;
  const voice = project.assets.find((a) => a.id === project.narration_id),
    music = project.assets.find((a) => a.id === project.music_id);
  const audioAssets = project.assets.filter(
    (a) =>
      a.kind === "audio" ||
      (a.has_audio && [project.narration_id, project.music_id].includes(a.id)),
  );
  useEffect(() => {
    let stopped = false;
    api(`/api/projects/${project.id}/episode`)
      .then((r) => {
        if (!stopped) setReport(r);
      })
      .catch((err) => {
        if (!stopped) onError(err);
      });
    return () => {
      stopped = true;
    };
  }, [project.id, project.updated_at]);
  async function action(fn, message) {
    if (disabled) return;
    setWorking(true);
    onBusy(true);
    try {
      await onFlush();
      const r = await fn();
      const p = r.project || r;
      onProject(p);
      if (r.analysis) setReport(r.analysis);
      if (message) onNotify(message);
      return r;
    } catch (err) {
      onError(err);
    } finally {
      setWorking(false);
      onBusy(false);
    }
  }
  const save = (path, method, body) =>
    action(() => api(`/api/projects/${project.id}${path}`, method, body));
  async function importDocument(role, files) {
    const file = files[0];
    await action(
      async () => {
        const response = await api(
          `/api/projects/${project.id}/episode/import`,
          "POST",
          { role, text: await file.text(), filename: file.name },
        );
        await keepWorkingFiles(project.id, [file], role).catch(() =>
          onNotify(
            "Browser recovery cache is unavailable; keep the original inputs.",
          ),
        );
        return response;
      },
      `${role === "guide" ? "Editing guide" : role === "script" ? "Narration script" : "Timing file"} imported separately.`,
    );
  }
  async function media(role, files, autoPreview = false) {
    try {
      validateUpload(files);
    } catch (error) {
      setTransfer({
        role: role || "sources",
        label: "Selection not uploaded",
        phase: "error",
        loaded: 0,
        total: 0,
      });
      onError(error);
      return;
    }
    setTransfer({
      role: role || "sources",
      label: `${files.length} selected file(s)`,
      loaded: 0,
      total: 0,
      phase: "uploading",
    });
    const uploaded = await action(
      async () => {
        const form = new FormData();
        form.append(
          "episode_role",
          role === "narration_id"
            ? "narration"
            : role === "music_id"
              ? "music"
              : "sources",
        );
        files.forEach((f) => form.append("files", f));
        let result;
        try {
          result = await api(
            `/api/projects/${project.id}/upload`,
            "POST",
            form,
            (progress) => setTransfer((old) => ({ ...old, ...progress })),
          );
        } catch (error) {
          setTransfer((old) => ({ ...old, phase: "error" }));
          try {
            onProject(await api(`/api/projects/${project.id}`));
          } catch {}
          throw error;
        }
        await keepWorkingFiles(project.id, files, role || "sources").catch(() =>
          onNotify(
            "Browser could not keep a local recovery copy; retain your computer originals.",
          ),
        );
        if (role) {
          const old = new Set(project.assets.map((a) => a.id));
          const asset = result.assets.find(
            (a) => !old.has(a.id) && (a.has_audio || a.kind === "audio"),
          );
          if (!asset) throw new Error("Choose an audio file for this role.");
          return api(`/api/projects/${project.id}/episode/options`, "PATCH", {
            [role]: asset.id,
          });
        }
        if (guide)
          return api(
            `/api/projects/${project.id}/episode/autolink`,
            "POST",
            {},
          );
        return result;
      },
      role === "narration_id"
        ? "Your finished narration is assigned. It will not be regenerated."
        : role === "music_id"
          ? "Background music is assigned."
          : "Files imported; unique source-ID filenames linked automatically. Preview them below; no approvals were inferred.",
    );
    if (autoPreview && uploaded && ready && onQuickDraft) {
      const candidate =
        uploaded.analysis || (await api(`/api/projects/${project.id}/episode`));
      if (candidate.inspection_cues > 0) await onQuickDraft({ render: false });
    }
  }
  function listen(time) {
    if (audio.current) {
      audio.current.currentTime = time;
      audio.current.play().catch(onError);
    }
  }
  const placements = report?.placements || [];
  const used = new Set(
    report?.source_option_ids || placements.map((c) => c.source_id),
  );
  const sources = (guide?.sources || []).filter(
    (s) => showAll || used.has(s.id),
  );
  const plan = e.plan;
  const inspection = planningMode === "inspection";
  const modeMatches = !!plan && (plan.mode || "reviewed") === planningMode;
  const ready =
    report?.has_script && report?.has_guide && !report.errors.length;
  return (
    <main className="episode-setup">
      <div className="ep-hero">
        <div>
          <div className="eyebrow">YOUR MATERIAL → A GUIDE-LED EDIT</div>
          <h2>Your voice. Your guide. One draft.</h2>
          <p>
            Upload the audio you already made. Tell CASEFILE what to show with
            your editing guide—not a random footage search.
          </p>
        </div>
        <div className="ep-local">
          <CheckCircle2 size={13} /> No AI key needed to preview your files
        </div>
      </div>
      <div className="ep-flow">
        <span>
          <b>01</b> Add files
        </span>
        <ArrowRight size={13} />
        <span>
          <b>02</b> Preview your draft
        </span>
        <ArrowRight size={13} />
        <span>
          <b>03</b> Download when ready
        </span>
      </div>
      <SimpleDraft
        project={project}
        busy={disabled}
        onMedia={media}
        onImport={importDocument}
        onPreview={onQuickDraft}
        onOptions={(captions) =>
          save("/episode/options", "PATCH", { captions })
        }
        progress={!advancedOpen ? transfer : null}
        backupStatus={backupStatus}
      />
      <button
        className="advanced-setup-toggle"
        aria-label="More settings"
        aria-expanded={advancedOpen}
        onClick={() => setAdvancedOpen(!advancedOpen)}
      >
        <ChevronDown size={14} />{" "}
        {advancedOpen
          ? "Hide detailed settings"
          : "More settings: documents, source choices and final checks"}
      </button>
      <div className="detailed-episode-settings" hidden={!advancedOpen}>
        {project.is_demo && (
          <div className="ep-demo-warning">
            <Info size={17} />
            <div>
              <b>Start a new project for your own episode.</b>
              <p>
                The current sample is fictional; it cannot be turned into a real
                case by replacing its script.
              </p>
            </div>
            <button className="btn" onClick={onNew}>
              New project <ArrowRight size={12} />
            </button>
          </div>
        )}
        <fieldset
          disabled={disabled || project.is_demo}
          className="ep-materials"
        >
          <Material
            number={1}
            icon={Mic}
            title="Finished narration"
            ready={!!voice}
            status={
              voice
                ? `${tc(voice.duration)} · uploaded voice`
                : "Upload the MP3 / WAV you generated"
            }
          >
            {voice ? (
              <>
                <div className="ep-file-name">
                  <Mic size={13} />
                  {voice.name}
                </div>
                <audio
                  ref={audio}
                  src={voice.url}
                  controls
                  preload="metadata"
                />
              </>
            ) : (
              <div className="ep-empty-asset">
                <Mic size={25} />
                <b>Your narration is the backbone.</b>
                <span>
                  We use your audio unchanged—no new voice generation.
                </span>
              </div>
            )}
            <FilePick
              label="Upload finished narration"
              limit="512 MB maximum · one narration file at a time"
              accept="audio/*,.mp3,.wav,.m4a,.flac"
              disabled={disabled || project.is_demo}
              onFiles={(f) => media("narration_id", f)}
            >
              <Upload size={13} />
              {voice ? "Replace narration" : "Choose narration file"}
            </FilePick>
            {transfer?.role === "narration_id" && (
              <UploadProgress progress={transfer} />
            )}
            {audioAssets.length > 0 && (
              <label className="ep-select-existing">
                Or choose an imported track
                <select
                  aria-label="Episode narration track"
                  value={project.narration_id || ""}
                  onChange={(ev) =>
                    save("/episode/options", "PATCH", {
                      narration_id: ev.target.value || null,
                    })
                  }
                >
                  <option value="">Not assigned</option>
                  {audioAssets
                    .filter((a) => a.id !== project.music_id)
                    .map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                </select>
              </label>
            )}
            <button
              className="ep-inline-link"
              type="button"
              onClick={() =>
                timingPanel.current?.scrollIntoView({
                  behavior: "smooth",
                  block: "center",
                })
              }
            >
              <Clock3 size={12} /> Add SRT / JSON in the timestamps panel below{" "}
              <ArrowRight size={11} />
            </button>
          </Material>
          <Material
            number={2}
            icon={Music2}
            title="Background music"
            ready={!!music}
            status={
              music
                ? "Assigned · mixed below the voice"
                : "Optional · use music you can reuse"
            }
          >
            {music ? (
              <>
                <div className="ep-file-name">
                  <Music2 size={13} />
                  {music.name}
                </div>
                <audio src={music.url} controls preload="metadata" />
              </>
            ) : (
              <div className="ep-empty-asset">
                <Music2 size={25} />
                <b>A quiet bed, not another voice.</b>
                <span>
                  Music loops and ducks under narration in the export.
                </span>
              </div>
            )}
            <FilePick
              label="Upload background music"
              limit="512 MB maximum · one music file at a time"
              accept="audio/*,.mp3,.wav,.m4a,.flac"
              disabled={disabled || project.is_demo}
              onFiles={(f) => media("music_id", f)}
            >
              <Upload size={13} />
              {music ? "Replace music" : "Choose music file"}
            </FilePick>
            {transfer?.role === "music_id" && (
              <UploadProgress progress={transfer} />
            )}
            {audioAssets.length > 0 && (
              <label className="ep-select-existing">
                Or choose an imported track
                <select
                  aria-label="Episode music track"
                  value={project.music_id || ""}
                  onChange={(ev) =>
                    save("/episode/options", "PATCH", {
                      music_id: ev.target.value || null,
                    })
                  }
                >
                  <option value="">No background music</option>
                  {audioAssets
                    .filter((a) => a.id !== project.narration_id)
                    .map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name}
                      </option>
                    ))}
                </select>
              </label>
            )}
            <label className="field ep-music-level">
              Music level <b>{percent(project.music_volume * 100)}</b>
              <input
                aria-label="Episode music level"
                type="range"
                min="0"
                max="50"
                defaultValue={Math.round(project.music_volume * 100)}
                key={Math.round(project.music_volume * 100)}
                onPointerUp={(ev) =>
                  save("/episode/options", "PATCH", {
                    music_volume: Number(ev.target.value) / 100,
                  })
                }
                onKeyUp={(ev) => {
                  if (
                    ["ArrowLeft", "ArrowRight", "Home", "End"].includes(ev.key)
                  )
                    save("/episode/options", "PATCH", {
                      music_volume: Number(ev.target.value) / 100,
                    });
                }}
              />
            </label>
            <p className="ep-small">
              Starting level only. Listen to the actual MP4; this is not a
              loudness guarantee.
            </p>
          </Material>
          <Material
            number={3}
            icon={FileText}
            title="Narration script"
            ready={!!script}
            status={
              script
                ? `${script.word_count.toLocaleString()} words · ${script.sections.length} sections`
                : "The exact words spoken in your audio"
            }
          >
            {script ? (
              <div className="ep-document-summary">
                <FileText size={28} />
                <b>{script.filename}</b>
                <span>
                  Chapter headings are structure—not spoken narration.
                </span>
                <p>{script.sections[0]?.text.slice(0, 158)}…</p>
              </div>
            ) : (
              <div className="ep-empty-asset">
                <FileText size={25} />
                <b>Bring the script used for your voice.</b>
                <span>Blank lines and chapter headings are supported.</span>
              </div>
            )}
            <FilePick
              label="Upload narration script"
              accept=".md,.txt"
              disabled={disabled || project.is_demo}
              onFiles={(f) => importDocument("script", f)}
            >
              <Upload size={13} />
              {script ? "Replace script" : "Choose script document"}
            </FilePick>
            <p className="ep-small">
              Without a timing file, cuts are estimated from the script and the
              audio's actual length. Never pad the story to hit a target.
            </p>
          </Material>
          <Material
            number={4}
            icon={Clapperboard}
            title="Editing / footage guide"
            ready={!!guide}
            status={
              guide
                ? `${report?.cue_count ?? guide.cues.length} placements · ${guide.sources.length} references`
                : "At → Show → Source → Label → Care"
            }
          >
            {guide ? (
              <div className="ep-document-summary">
                <Clapperboard size={28} />
                <b>{guide.filename}</b>
                <span className="ep-matched">
                  <CheckCircle2 size={12} />
                  {report?.matched_cues ?? 0} /{" "}
                  {report?.cue_count ?? guide.cues.length} phrases matched in
                  their chapter
                </span>
                <p>
                  Use the specified source at the specified phrase. Missing
                  files stay marked—not replaced by generic stock.
                </p>
              </div>
            ) : (
              <div className="ep-empty-asset">
                <Clapperboard size={25} />
                <b>This is your editing directive.</b>
                <span>
                  Use the same format as your supplied real-footage guide.
                </span>
              </div>
            )}
            <FilePick
              label="Upload editing guide"
              accept=".md,.txt"
              disabled={disabled || project.is_demo}
              onFiles={(f) => importDocument("guide", f)}
            >
              <Upload size={13} />
              {guide ? "Replace editing guide" : "Choose editing guide"}
            </FilePick>
            <p className="ep-small">
              This is a separate document. Its links do not import media; actual
              footage/photos are added in Source files below.
            </p>
          </Material>
        </fieldset>
        <section
          className="ep-timestamp-panel"
          id="ep-timestamps"
          ref={timingPanel}
          aria-label="Narration timestamps"
        >
          <div className="ep-timestamp-head">
            <div className="ep-timestamp-heading">
              <Clock3 size={21} />
              <div>
                <span className="eyebrow">
                  05 / OPTIONAL TIMING INPUT · v0.4.2
                </span>
                <h3>Narration timestamps (SRT / JSON)</h3>
              </div>
            </div>
            <span className="ep-timestamp-status">
              {e.timings ? "Timing files attached" : "No timing files attached"}
            </span>
          </div>
          <div className="ep-timestamp-layout">
            <div className="ep-timestamp-controls">
              {" "}
              <p className="ep-small">
                Choose the CapCut draft JSON and matching SRT one after the
                other, in either order. Use exports from the exact narration
                recording. JSON supplies word-unit boundaries; SRT preserves
                caption holds.
              </p>
              <FilePick
                label="Upload narration timings"
                accept=".srt,.vtt,.json,.md"
                disabled={disabled || project.is_demo}
                onFiles={(f) => importDocument("timings", f)}
                className="ep-timestamp-upload"
              >
                <Upload size={16} /> Upload SRT / JSON
              </FilePick>
              {e.timings && (
                <p className="ep-timestamp-files">
                  <b>Attached to this project:</b>{" "}
                  {e.timings.sources?.length
                    ? e.timings.sources
                        .map((source) => source.filename)
                        .join(" + ")
                    : e.timings.filename}
                </p>
              )}
              {e.timings && (
                <button
                  className="ep-clear-timings"
                  disabled={disabled}
                  onClick={() =>
                    save("/episode/options", "PATCH", { clear_timings: true })
                  }
                >
                  Remove timing file · use estimates
                </button>
              )}
            </div>
            <div className="ep-timestamp-detail">
              {" "}
              {e.timings && (
                <div
                  className="ep-timing-summary"
                  aria-label="Imported timing summary"
                >
                  <p className="ep-small">
                    <b>
                      {report?.timing_word_match_percent ?? 0}% normalized
                      transcript match.
                    </b>{" "}
                    {e.timings.source_kind === "capcut"
                      ? `${e.timings.words.length.toLocaleString()} supplied timing units; ${e.timings.grouped_units} include multiple comparison tokens. Grouped interiors have no supplied word starts; cuts there remain estimated.`
                      : e.timings.precision === "word"
                        ? "Supplied word timestamps; audio review still required."
                        : "Word positions inside segments are estimates, not exact word alignment."}
                  </p>
                  {!!report?.imported_caption_count && (
                    <p className="ep-small">
                      {report.imported_caption_count} supplied caption blocks
                      preserved
                      {e.timings.captions_source === "srt"
                        ? " from SRT"
                        : " from CapCut"}
                      . Hiding captions does not remove this clock.
                    </p>
                  )}
                  {e.timings.audio_reference_filename && !report?.has_voice && (
                    <p className="ep-timing-pending">
                      Audio referenced, not uploaded:{" "}
                      <b>{e.timings.audio_reference_filename}</b>
                    </p>
                  )}
                  {!!report?.timing_candidate_cues?.length && (
                    <p className="ep-timing-pending">
                      Cue-start text substitutions need review:{" "}
                      {report.timing_candidate_cues.join(", ")}. These are
                      proposals, not verified alignment.
                    </p>
                  )}
                  {!!report?.transcript_comparison?.difference_spans && (
                    <details className="ep-transcript-audit">
                      <summary>
                        Review transcript differences (
                        {report.transcript_comparison.difference_spans})
                      </summary>
                      <p className="ep-small">
                        Comparison spans include formatting and apparent ASR
                        differences—not confirmed spoken errors. Compare with
                        the audio; no script, voice, or caption text was
                        corrected automatically. Correct captions in your source
                        export and re-upload the matching SRT if needed.
                      </p>
                      <div
                        className="ep-difference-list"
                        tabIndex={0}
                        aria-label="Transcript differences"
                      >
                        {report.transcript_comparison.differences.map(
                          (d, i) => (
                            <div key={i}>
                              <small>
                                {d.start == null
                                  ? "End of transcript"
                                  : tcMs(d.start)}{" "}
                                · caption {d.caption_number ?? "—"}
                              </small>
                              <p>
                                <b>Script:</b> {d.script || "[no text]"}
                              </p>
                              <p>
                                <b>Timing transcript:</b>{" "}
                                {d.transcript || "[no text]"}
                              </p>
                            </div>
                          ),
                        )}
                      </div>
                    </details>
                  )}
                  {!!report?.imported_caption_count && (
                    <a
                      className="ep-small"
                      href={`/api/projects/${project.id}/captions.srt`}
                      download
                    >
                      Download supplied caption track
                    </a>
                  )}
                </div>
              )}
              {!e.timings && (
                <div className="ep-timing-empty">
                  <b>Place visuals using the narration clock.</b>
                  <p>
                    Import timings here—not in the script, guide, or footage
                    upload. SRT alone timestamps caption blocks; interior word
                    positions remain estimates without matching word-unit data.
                  </p>
                </div>
              )}
              <p className="ep-timestamp-note">
                Captions are optional. Turning their display off does not remove
                timing data or move your visuals.
              </p>
            </div>
          </div>
        </section>
        {report && (
          <div className="ep-overview">
            <div>
              <b>
                {report.duration_basis === "timing-export"
                  ? tcMs(report.duration)
                  : tc(report.duration)}
              </b>
              <span>
                {report.duration_basis === "timing-export"
                  ? "Timing-export length · audio missing"
                  : report.duration_estimated
                    ? "Estimated spoken length"
                    : "Actual narration length"}
              </span>
            </div>
            <div>
              <b>
                {report.matched_cues}
                <small> / {report.cue_count}</small>
              </b>
              <span>Guide phrases matched</span>
            </div>
            <div>
              <b>
                {report.linked_source_count}
                <small> / {report.used_source_count}</small>
              </b>
              <span>
                Main files linked{" "}
                <small>Guide alternatives can cover missing mains.</small>
              </span>
            </div>
            <div>
              <b>
                {report.ready_cues}
                <small> / {report.cue_count}</small>
              </b>
              <span>
                Final placement sign-offs{" "}
                <small>0 is okay for an inspection draft.</small>
              </span>
            </div>
          </div>
        )}
        {report &&
          (report.placements_with_files || report.linked_source_count) > 0 && (
            <div className="ep-inspection-help" role="note">
              <Play size={18} />
              <div>
                <b>
                  {report.linked_source_count} main files linked ·{" "}
                  {report.alternative_cues || 0} placements using guide
                  alternatives · {report.inspection_cues} placements inspectable
                  · {report.ready_cues} placements approved
                </b>
                <p>
                  Preview any linked file below without signing it off. Build an
                  inspection draft to see unreviewed candidates on the timeline.
                  Images use their source link; videos use valid local/guide
                  windows or a clearly disclosed opening sample. Known
                  prohibited chapters and required stop times stay blocked.
                  Rights, identity and Care are never auto-approved.
                </p>
              </div>
            </div>
          )}
        <div className="ep-boundaries">
          <ShieldCheck size={19} />
          <div>
            <b>THE GUIDE'S BOUNDARIES STAY WITH THE EDIT</b>
            <p>
              {guide?.boundaries ||
                "Import the guide to carry its source, privacy, context, and no-substitution rules into the edit."}
            </p>
            <small>
              CASEFILE can enforce source IDs and approved ranges. You must
              review visual identity, privacy, cropping, context, and rights;
              these are not verified by the app.
            </small>
          </div>
        </div>
        {report?.errors.length > 0 && (
          <div className="ep-errors">
            <AlertTriangle size={17} />
            <div>
              {report.errors.map((err) => (
                <p key={err}>{err}</p>
              ))}
            </div>
          </div>
        )}
        <div className="ep-workbench">
          <section className="ep-source-panel" ref={sourcePanel}>
            <div className="ep-section-head">
              <div>
                <span className="eyebrow">02 / SOURCE FILES</span>
                <h3>Links tell us where. Files let us edit.</h3>
              </div>
              <span className="ep-count">
                {report?.used_source_count || 0} used
              </span>
            </div>
            <p className="ep-panel-intro">
              Upload the authorized originals or excerpts. Keep their original
              filenames and link them here, or optionally use names like{" "}
              <code>S03.mp4</code> and <code>S01.jpg</code> for filename
              matching. Matching never confirms permission.
            </p>
            <div className="ep-media-required" role="note">
              <Download size={17} />
              <div>
                <b>Guide links are references—not imported footage.</b>
                <p>
                  Automatic link downloads are not available in this build.
                  Upload the actual authorized video/photos. Full originals are
                  fine; the editor cuts your reviewed source windows, so you do
                  not need to pre-trim each clip.
                </p>
              </div>
            </div>
            <div className="ep-source-actions">
              <FilePick
                label="Upload source footage"
                accept="video/*,image/*,.mp4,.mov,.jpg,.png"
                multiple
                disabled={disabled || project.is_demo}
                onFiles={(f) => media(null, f)}
              >
                <Upload size={13} /> Upload footage / photos
              </FilePick>
              <button
                className="btn"
                disabled={disabled || !guide}
                onClick={() =>
                  action(
                    () =>
                      api(
                        `/api/projects/${project.id}/episode/autolink`,
                        "POST",
                        {},
                      ),
                    "Unambiguous filename matches linked. Source approvals remain yours.",
                  )
                }
              >
                <Link2 size={13} /> Match filenames
              </button>
            </div>
            <p className="upload-limit-hint">
              Media limit: {uploadLimits}. The limit is per file, not 512 MB for
              the whole batch.
            </p>
            {transfer?.role === "sources" && (
              <UploadProgress progress={transfer} />
            )}
            <div className="ep-source-tabs">
              <button
                className={!showAll ? "selected" : ""}
                onClick={() => setShowAll(false)}
              >
                Used by guide (
                {report?.source_option_ids?.length ||
                  report?.used_source_count ||
                  0}
                )
              </button>
              <button
                className={showAll ? "selected" : ""}
                onClick={() => setShowAll(true)}
              >
                All references ({guide?.sources.length || 0})
              </button>
            </div>
            <div
              className="ep-source-scroll"
              role="region"
              aria-label="Source files checklist"
              tabIndex={0}
            >
              {!guide ? (
                <div className="ep-empty-list">
                  <FolderOpen size={27} />
                  <p>
                    Your source checklist appears after importing the guide.
                  </p>
                </div>
              ) : (
                sources.map((source) => (
                  <SourceRow
                    key={source.id}
                    source={source}
                    optional={
                      !placements.some(
                        (c) =>
                          (c.primary_source_id || c.source_id) === source.id,
                      )
                    }
                    replacements={placements.filter(
                      (c) =>
                        c.using_alternative &&
                        c.primary_source_id === source.id,
                    )}
                    project={project}
                    expanded={sourceOpen === source.id}
                    onExpand={() =>
                      setSourceOpen(sourceOpen === source.id ? null : source.id)
                    }
                    save={save}
                    disabled={disabled}
                  />
                ))
              )}
            </div>
            <div className="ep-acquisition-note">
              <ExternalLink size={14} />
              <p>
                Web and YouTube links are research references, not imported
                footage. This workflow does not download third-party videos,
                request licenses, or assume that a public posting grants reuse
                rights.
              </p>
            </div>
          </section>
          <section className="ep-cue-panel">
            <div className="ep-section-head">
              <div>
                <span className="eyebrow">03 / GUIDE PLACEMENTS</span>
                <h3>When you say this, show that.</h3>
              </div>
              <select
                aria-label="Filter guide chapter"
                value={chapter}
                onChange={(ev) => setChapter(ev.target.value)}
              >
                <option value="all">All chapters</option>
                {report?.sections.map((s) => (
                  <option value={s.key} key={s.key}>
                    {s.title}
                  </option>
                ))}
              </select>
            </div>
            <div className="ep-cue-explainer">
              <VolumeX size={15} />
              <p>
                Source audio is muted. Each scene loops its own selected crop
                to fill the narration span; the final repetition is trimmed at
                the scene's end. Source/date labels travel into the render.
              </p>
            </div>
            <div
              className="ep-cue-scroll"
              role="region"
              aria-label="Guide cue list"
              tabIndex={0}
            >
              {!placements.length ? (
                <div className="ep-empty-list">
                  <Clapperboard size={29} />
                  <p>Import both documents to see phrase-to-footage matches.</p>
                </div>
              ) : (
                placements
                  .filter((c) => chapter === "all" || c.chapter === chapter)
                  .map((c) => (
                    <Cue
                      key={c.id}
                      cue={c}
                      inspection={inspection}
                      project={project}
                      disabled={disabled}
                      save={save}
                      onListen={listen}
                      onSource={(id) => {
                        setSourceOpen(id);
                        sourcePanel.current?.scrollIntoView({
                          behavior: "smooth",
                          block: "start",
                        });
                      }}
                    />
                  ))
              )}
            </div>
          </section>
        </div>
        <section className="ep-brief">
          <div>
            <FileText size={18} />
            <h3>Editing brief</h3>
            <span>Saved producer notes—not an arbitrary executable prompt</span>
          </div>
          <textarea
            aria-label="Episode editing brief"
            key={project.id + "brief"}
            defaultValue={
              e.brief ||
              "Keep my narration unchanged. Follow the supplied footage guide. Mute source audio; put music underneath the voice. Do not substitute unrelated material."
            }
            rows={3}
            disabled={disabled || project.is_demo}
            onBlur={(ev) => {
              if (ev.target.value !== e.brief)
                save("/episode/options", "PATCH", { brief: ev.target.value });
            }}
          />
          <div className="ep-brief-controls">
            <label className="ep-checkbox">
              <SavedCheck
                type="checkbox"
                aria-label="Show captions (timing still needs review)"
                checked={project.captions}
                disabled={disabled || project.is_demo}
                onChange={(ev) =>
                  save("/episode/options", "PATCH", {
                    captions: ev.target.checked,
                  })
                }
              />{" "}
              <span>
                <b>Show captions</b>
                <small>
                  Only shows/hides on-screen text. Imported timing and visual
                  cue positions stay active.
                </small>
              </span>
            </label>
            <div className="ep-final-review-title">
              <b>Before final export: your review acknowledgements</b>
              <small>
                Not needed to view sources or build/render an unreviewed
                inspection draft. Leave unticked until you have actually
                checked.
              </small>
            </div>
            <label className="ep-checkbox">
              <SavedCheck
                type="checkbox"
                aria-label="Narration cue timing reviewed"
                checked={!!report?.timing_reviewed}
                disabled={disabled || !voice || !ready}
                onChange={(ev) =>
                  save("/episode/options", "PATCH", {
                    confirm_timing: ev.target.checked,
                  })
                }
              />{" "}
              <span>
                <b>I checked visual cue positions against the recording</b>
                <small>
                  This records your listening review. It does not run
                  synchronization or create footage.
                </small>
              </span>
            </label>
            {!!report?.transcript_comparison?.difference_spans && (
              <label className="ep-checkbox">
                <SavedCheck
                  type="checkbox"
                  aria-label="Timing transcript differences reviewed"
                  checked={!!report?.transcript_reviewed}
                  disabled={disabled || !voice || !ready}
                  onChange={(ev) =>
                    save("/episode/options", "PATCH", {
                      confirm_transcript: ev.target.checked,
                    })
                  }
                />{" "}
                <span>
                  <b>I checked transcript differences against the recording</b>
                  <small>
                    Names, numbers and dates were compared with the actual
                    voice. This does not automatically correct text; do not tick
                    it just to preview.
                  </small>
                </span>
              </label>
            )}
          </div>
          <p className="ep-small">
            The structured guide controls this build. For supported visual
            revisions after planning, use Direct your edit; free-text notes
            above do not silently change shots, voice, or timing.
          </p>
        </section>
        {plan && (
          <div className="ep-plan-result">
            <div>
              <CheckCircle2 size={18} />
              <div>
                <b>
                  {plan.mode === "inspection" ? "UNREVIEWED INSPECTION · " : ""}
                  {plan.scene_count} scenes planned · {tc(plan.duration)} ·{" "}
                  {plan.has_voice
                    ? "voice preserved"
                    : e.timings
                      ? "timed plan · audio missing"
                      : "script-only estimate"}
                </b>
                <p>
                  {plan.gap_seconds > 0
                    ? `${plan.gap_seconds < 1 ? tcMs(plan.gap_seconds) : tc(plan.gap_seconds)} still needs reviewed visual coverage. Missing media is visibly marked—not invented.`
                    : "The planned source windows cover this timeline. Watch every cut before final review."}
                  {!report?.plan_current
                    ? " Setup changed: rebuild before rendering."
                    : ""}
                </p>
              </div>
            </div>
            <button className="btn" onClick={() => onNavigate("edit")}>
              <Film size={13} /> View timeline
            </button>
          </div>
        )}
        <div className="ep-create" id="ep-create">
          <div className="ep-create-copy">
            <span className="eyebrow">04 / MAKE THE DRAFT</span>
            <h3>See the edit first. Clear publication separately.</h3>
            <p>
              {voice
                ? "Your uploaded recording sets the runtime. The app will not regenerate or shorten it."
                : "Add your finished narration in card 1 to enable video rendering. You can inspect the episode plan now."}
            </p>
            <label className="field ep-mode-field">
              Planning mode
              <select
                aria-label="Guide planning mode"
                value={planningMode}
                onChange={(ev) => setPlanningMode(ev.target.value)}
                disabled={disabled}
              >
                <option value="inspection">
                  Inspection draft · unreviewed linked media
                </option>
                <option value="reviewed">
                  Reviewed plan · approved placements only
                </option>
              </select>
            </label>
            <p className="ep-mode-explanation">
              {inspection
                ? "Internal inspection only. Candidate footage is visibly marked UNREVIEWED and cannot be exported as a final video. Source sound stays muted; a short crop loops within its own scene, never into other footage."
                : "Only genuinely reviewed source windows appear. Anything missing approval remains a marked gap; final release still requires all real editorial checks."}
            </p>
            <label className="ep-checkbox">
              <input
                type="checkbox"
                aria-label="Allow marked visual gaps"
                checked={gaps}
                onChange={(ev) => setGaps(ev.target.checked)}
                disabled={disabled}
              />
              <span>
                <b>Allow visible gap cards in this partial inspection video</b>
                <small>
                  Only permits placeholders where coverage is still missing. It
                  does not approve footage or replace guide alternatives.
                </small>
              </span>
            </label>
          </div>
          <div className="ep-create-actions">
            <label className="field">
              Review resolution
              <select
                aria-label="Guide draft resolution"
                value={resolution}
                onChange={(ev) => setResolution(ev.target.value)}
                disabled={disabled}
              >
                <option value="480p">480p · quick check</option>
                <option value="720p">720p · HD draft</option>
                <option value="1080p">1080p · full HD</option>
              </select>
            </label>
            <button
              className="btn"
              aria-label="Preview episode plan"
              disabled={disabled || !ready || project.is_demo}
              onClick={() =>
                action(
                  () =>
                    api(`/api/projects/${project.id}/episode/build`, "POST", {
                      allow_placeholders: true,
                      inspection,
                    }),
                  inspection
                    ? "Unreviewed inspection timeline built. Your voice is unchanged; no rights or Care approvals were inferred."
                    : "Reviewed guide timeline built. Your original audio stays unchanged.",
                )
              }
            >
              <Clapperboard size={14} />
              {inspection
                ? "Build / rebuild inspection draft"
                : plan
                  ? "Rebuild reviewed plan"
                  : "Build reviewed plan"}
            </button>
            <button
              className="btn primary"
              aria-label="Create guided review video"
              disabled={
                disabled ||
                !voice ||
                !report?.plan_current ||
                !modeMatches ||
                (!gaps && plan?.gap_seconds > 0)
              }
              onClick={() =>
                onRender({
                  resolution,
                  draft: true,
                  captions: project.captions,
                  allow_guided_gaps: gaps,
                  allow_inspection: inspection,
                })
              }
            >
              {working ? (
                <LoaderCircle size={15} className="spin" />
              ) : (
                <Film size={15} />
              )}{" "}
              {inspection ? "Render inspection MP4" : "Create review video"}{" "}
              <ArrowRight size={13} />
            </button>
            <p className="ep-render-reason" aria-live="polite">
              {!voice
                ? "Add the matching narration to render; a plan can be inspected now."
                : !report?.plan_current || !modeMatches
                  ? "Build / rebuild in the selected mode before rendering."
                  : !gaps && plan?.gap_seconds > 0
                    ? `${plan.gap_seconds < 1 ? tcMs(plan.gap_seconds) : tc(plan.gap_seconds)} of marked gaps remain. Allow those cards for an internal preview, or supply more coverage.`
                    : "Ready for an internal draft. Publication checks do not block source inspection."}
            </p>
          </div>
        </div>
        <footer className="ep-footer">
          <span>
            <ShieldCheck size={12} /> Shared prototype: do not upload
            confidential evidence. No automatic publishing or legal clearance.
          </span>
          <a href={`/api/projects/${project.id}/episode/plan.md`} download>
            <Download size={12} /> Download episode plan
          </a>
        </footer>
      </div>
    </main>
  );
}
