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
}) {
  return (
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
function SourceRow({ source, project, expanded, onExpand, save, disabled }) {
  const binding = project.episode?.bindings?.[source.id] || {};
  const assets = project.assets.filter((a) =>
    ["image", "video"].includes(a.kind),
  );
  const file = assets.find((a) => a.id === binding.asset_id);
  const row = useRef(null);
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
            {file ? file.name : "Reference link only · actual file needed"}
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
              {file.kind === "video" ? (
                <video
                  aria-label={`Review source ${source.id}`}
                  src={file.url}
                  controls
                  muted
                  playsInline
                  preload="metadata"
                />
              ) : (
                <img
                  src={file.url}
                  alt={`Uploaded file linked by producer to ${source.id}`}
                />
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
                  I have recorded the reuse basis for this file. CASEFILE has
                  not cleared it for me.
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
                  This file contains residential-property imagery. Do not use it
                  in restricted chapters.
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
function Cue({ cue, project, disabled, save, onListen, onSource }) {
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
            <span>{cue.source_id}</span>
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
            {cue.ready ? "Producer-reviewed source window" : cue.status_detail}
          </p>
        </div>
        {cue.ready ? <CheckCircle2 size={15} /> : <ChevronDown size={14} />}
      </summary>
      <div className="ep-cue-body">
        <div className="ep-cue-directive">
          <span>SHOW</span>
          <p>{cue.show}</p>
        </div>
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
                I reviewed the moving clip/photo, label, privacy restrictions,
                and Care instructions. I will not imply that contextual footage
                shows a different event.
              </span>
            </label>
            <button className="btn" disabled={disabled} onClick={apply}>
              <Check size={12} /> Save placement review
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
    [resolution, setResolution] = useState("720p");
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
      async () =>
        api(`/api/projects/${project.id}/episode/import`, "POST", {
          role,
          text: await file.text(),
          filename: file.name,
        }),
      `${role === "guide" ? "Editing guide" : role === "script" ? "Narration script" : "Timing file"} imported separately.`,
    );
  }
  async function media(role, files) {
    await action(
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
        const result = await api(
          `/api/projects/${project.id}/upload`,
          "POST",
          form,
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
        return result;
      },
      role === "narration_id"
        ? "Your finished narration is assigned. It will not be regenerated."
        : role === "music_id"
          ? "Background music is assigned."
          : "Source files imported. Match filenames or link them below.",
    );
  }
  function listen(time) {
    if (audio.current) {
      audio.current.currentTime = time;
      audio.current.play().catch(onError);
    }
  }
  const placements = report?.placements || [];
  const used = new Set(placements.map((c) => c.source_id));
  const sources = (guide?.sources || []).filter(
    (s) => showAll || used.has(s.id),
  );
  const plan = e.plan;
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
        <div className="ep-hero-actions">
          <button
            className="btn ep-timing-jump"
            aria-label="Go to timestamp uploader"
            onClick={() =>
              timingPanel.current?.scrollIntoView({
                behavior: "smooth",
                block: "center",
              })
            }
          >
            <Clock3 size={13} /> SRT / JSON timestamps <ArrowRight size={12} />
          </button>
          <button
            className="btn"
            onClick={() =>
              document
                .getElementById("ep-create")
                .scrollIntoView({ behavior: "smooth", block: "center" })
            }
          >
            Plan & draft <ArrowRight size={12} />
          </button>
          <span className="ep-local">
            <CheckCircle2 size={13} /> No AI key needed for this setup
          </span>
        </div>
      </div>
      <div className="ep-flow">
        <span>
          <b>01</b> Add your audio & documents
        </span>
        <ArrowRight size={13} />
        <span>
          <b>02</b> Link the real source files
        </span>
        <ArrowRight size={13} />
        <span>
          <b>03</b> Review cues & make a draft
        </span>
      </div>
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
      <fieldset disabled={disabled || project.is_demo} className="ep-materials">
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
              <audio ref={audio} src={voice.url} controls preload="metadata" />
            </>
          ) : (
            <div className="ep-empty-asset">
              <Mic size={25} />
              <b>Your narration is the backbone.</b>
              <span>We use your audio unchanged—no new voice generation.</span>
            </div>
          )}
          <FilePick
            label="Upload finished narration"
            accept="audio/*,.mp3,.wav,.m4a,.flac"
            disabled={disabled || project.is_demo}
            onFiles={(f) => media("narration_id", f)}
          >
            <Upload size={13} />
            {voice ? "Replace narration" : "Choose narration file"}
          </FilePick>
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
              <span>Music loops and ducks under narration in the export.</span>
            </div>
          )}
          <FilePick
            label="Upload background music"
            accept="audio/*,.mp3,.wav,.m4a,.flac"
            disabled={disabled || project.is_demo}
            onFiles={(f) => media("music_id", f)}
          >
            <Upload size={13} />
            {music ? "Replace music" : "Choose music file"}
          </FilePick>
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
                if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(ev.key))
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
              <span>Chapter headings are structure—not spoken narration.</span>
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
                Use the specified source at the specified phrase. Missing files
                stay marked—not replaced by generic stock.
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
                05 / OPTIONAL TIMING INPUT · v0.3.2
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
              Choose the CapCut draft JSON and matching SRT one after the other,
              in either order. Use exports from the exact narration recording.
              JSON supplies word-unit boundaries; SRT preserves caption holds.
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
                      differences—not confirmed spoken errors. Compare with the
                      audio; no script, voice, or caption text was corrected
                      automatically. Correct captions in your source export and
                      re-upload the matching SRT if needed.
                    </p>
                    <div
                      className="ep-difference-list"
                      tabIndex={0}
                      aria-label="Transcript differences"
                    >
                      {report.transcript_comparison.differences.map((d, i) => (
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
                      ))}
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
            <span>Required source files linked</span>
          </div>
          <div>
            <b>
              {report.ready_cues}
              <small> / {report.cue_count}</small>
            </b>
            <span>Placements producer-reviewed</span>
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
            CASEFILE can enforce source IDs and approved ranges. You must review
            visual identity, privacy, cropping, context, and rights; these are
            not verified by the app.
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
            <code>S03.mp4</code> and <code>S01.jpg</code> for filename matching.
            Matching never confirms permission.
          </p>
          <div className="ep-media-required" role="note">
            <Download size={17} />
            <div>
              <b>Guide links are references—not imported footage.</b>
              <p>
                Automatic link downloads are not available in this build. Upload
                the actual authorized video/photos. Full originals are fine; the
                editor cuts your reviewed source windows, so you do not need to
                pre-trim each clip.
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
          <div className="ep-source-tabs">
            <button
              className={!showAll ? "selected" : ""}
              onClick={() => setShowAll(false)}
            >
              Used by guide ({report?.used_source_count || 0})
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
                <p>Your source checklist appears after importing the guide.</p>
              </div>
            ) : (
              sources.map((source) => (
                <SourceRow
                  key={source.id}
                  source={source}
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
              Source audio is muted. Approved video ranges play once; short
              ranges leave marked gaps instead of being silently looped.
              Source/date labels travel into the render.
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
              checked={project.captions}
              disabled={disabled || project.is_demo}
              onChange={(ev) =>
                save("/episode/options", "PATCH", {
                  captions: ev.target.checked,
                })
              }
            />{" "}
            Show captions (timing still needs review)
          </label>
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
            I checked the cue positions against the actual narration
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
              I compared the transcript differences with the audio and resolved
              caption/factual discrepancies
            </label>
          )}
        </div>
        <p className="ep-small">
          The structured guide controls this build. For supported visual
          revisions after planning, use Direct your edit; free-text notes above
          do not silently change shots, voice, or timing.
        </p>
      </section>
      {plan && (
        <div className="ep-plan-result">
          <div>
            <CheckCircle2 size={18} />
            <div>
              <b>
                {plan.scene_count} scenes planned · {tc(plan.duration)} ·{" "}
                {plan.has_voice
                  ? "voice preserved"
                  : e.timings
                    ? "timed plan · audio missing"
                    : "script-only estimate"}
              </b>
              <p>
                {plan.gap_seconds > 0
                  ? `${tc(plan.gap_seconds)} still needs reviewed visual coverage. Missing media is visibly marked—not invented.`
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
          <h3>A plan first. A real MP4 when your audio is ready.</h3>
          <p>
            {voice
              ? "Your uploaded recording sets the runtime. The app will not regenerate or shorten it."
              : "Add your finished narration in card 1 to enable video rendering. You can inspect the episode plan now."}
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
              Allow visibly marked missing-visual cards in a review-only video
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
                  }),
                "Guide-based timeline built. Your original audio stays unchanged.",
              )
            }
          >
            <Clapperboard size={14} />
            {plan ? "Rebuild episode plan" : "Preview episode plan"}
          </button>
          <button
            className="btn primary"
            aria-label="Create guided review video"
            disabled={
              disabled ||
              !voice ||
              !report?.plan_current ||
              (!gaps && plan?.gap_seconds > 0)
            }
            onClick={() =>
              onRender({
                resolution,
                draft: true,
                captions: project.captions,
                allow_guided_gaps: gaps,
              })
            }
          >
            {working ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <Film size={15} />
            )}{" "}
            Create review video <ArrowRight size={13} />
          </button>
        </div>
      </div>
      <footer className="ep-footer">
        <span>
          <ShieldCheck size={12} /> Shared prototype: do not upload confidential
          evidence. No automatic publishing or legal clearance.
        </span>
        <a href={`/api/projects/${project.id}/episode/plan.md`} download>
          <Download size={12} /> Download episode plan
        </a>
      </footer>
    </main>
  );
}
