import React, { useEffect, useState } from "react";
import {
  Sparkles,
  X,
  Check,
  CheckCircle2,
  Circle,
  ShieldCheck,
  Search,
  FileText,
  Clapperboard,
  Mic,
  Film,
  ArrowUpRight,
  ArrowRight,
  LockKeyhole,
  LoaderCircle,
  AlertTriangle,
  Info,
  Download,
  RefreshCw,
  Pause,
} from "lucide-react";
import "./production.css";

const duration = (seconds) =>
  `${Math.floor((seconds || 0) / 60)}:${String(Math.floor((seconds || 0) % 60)).padStart(2, "0")}`;
const names = {
  research: "Research",
  script: "Script",
  edit: "Edit",
  review: "Review",
  setup: "Episode setup",
  settings: "Settings",
};
function Shell({ title, kicker, onClose, children, className = "" }) {
  useEffect(() => {
    const f = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }, [onClose]);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`modal wide production-modal ${className}`}
      >
        <header className="modal-header">
          <div>
            <div className="eyebrow">{kicker}</div>
            <h2>{title}</h2>
          </div>
          <button
            className="icon-btn"
            aria-label="Close dialog"
            onClick={onClose}
          >
            <X size={17} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}
function Option({
  title,
  children,
  checked,
  onChange,
  disabled = false,
  label,
}) {
  return (
    <label className={`production-option ${disabled ? "disabled" : ""}`}>
      <input
        type="checkbox"
        aria-label={label || title}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <div>
        <b>{title}</b>
        <p>{children}</p>
      </div>
    </label>
  );
}
export function ProductionModal({
  project,
  config,
  jobs,
  api,
  onClose,
  onRun,
  onNavigate,
  onError,
  onConnect,
}) {
  const available = project.assets.filter(
    (a) => (a.has_audio || a.kind === "audio") && a.id !== project.music_id,
  );
  const [options, setOptions] = useState({
    allow_paid: false,
    generate_voice: false,
    auto_assign_visuals: true,
    allow_placeholders: false,
    allow_silent: false,
    render: true,
    resolution: "720p",
    source_asset_id:
      project.narration_id ||
      (["narration", "footage"].includes(project.mode) && available.length === 1
        ? available[0].id
        : null),
    max_voice_characters: 45000,
  });
  const [plan, setPlan] = useState(null),
    [loading, setLoading] = useState(true),
    [starting, setStarting] = useState(false),
    [refresh, setRefresh] = useState(0);
  const active = jobs.find((j) => ["queued", "running"].includes(j.status));
  const production = project.production;
  const change = (key, value) => setOptions((p) => ({ ...p, [key]: value }));
  useEffect(() => {
    let stopped = false;
    const timer = setTimeout(() => {
      setLoading(true);
      api(`/api/projects/${project.id}/production-plan`, "POST", options)
        .then((p) => {
          if (!stopped) setPlan(p);
        })
        .catch((e) => {
          if (!stopped) onError(e);
        })
        .finally(() => {
          if (!stopped) setLoading(false);
        });
    }, 150);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [project.updated_at, config.connected, options, refresh]);
  const icons = {
    research: Search,
    source_review: ShieldCheck,
    script: FileText,
    script_review: ShieldCheck,
    assembly: Clapperboard,
    narration: Mic,
    render: Film,
  };
  const run = async () => {
    setStarting(true);
    try {
      await onRun(options);
    } finally {
      setStarting(false);
    }
  };
  const paused = production?.status === "paused" && !active;
  return (
    <Shell
      title="From material to a review draft."
      kicker="GUIDED PRODUCTION · HUMAN REVIEW BUILT IN"
      onClose={onClose}
    >
      <div className="production-intro">
        <div className="production-emblem">
          <Sparkles size={23} />
        </div>
        <div>
          <h3>Run the available stages. Keep the important decisions.</h3>
          <p>
            Research and AI-written scripts pause for your review. This workflow
            never approves facts, clears copyright, or publishes a video.
          </p>
        </div>
        <span className="badge amber">DRAFT ONLY</span>
      </div>
      {active && (
        <div className="production-live">
          <div>
            <LoaderCircle size={15} className="spin" />
            <b>
              {active.kind === "production"
                ? "Production in progress"
                : "Another operation is running"}
            </b>
            <span>{active.progress}%</span>
          </div>
          <div className="progress-track">
            <div style={{ width: active.progress + "%" }} />
          </div>
          <p>{active.message}</p>
        </div>
      )}
      {paused && (
        <div className="production-pause">
          <Pause size={16} />
          <div>
            <b>Saved and paused for you</b>
            <p>{production.message}</p>
          </div>
          <button
            className="btn"
            onClick={() =>
              onNavigate({
                tab: production.next_tab || plan?.next_action?.tab || "script",
              })
            }
          >
            Open{" "}
            {names[production.next_tab || plan?.next_action?.tab] ||
              "workspace"}{" "}
            <ArrowUpRight size={13} />
          </button>
        </div>
      )}
      {production?.status === "complete" && !active && (
        <div className="production-success">
          <CheckCircle2 size={18} />
          <div>
            <b>Your last review draft is ready.</b>
            <p>
              Exports are saved snapshots. Watch the actual MP4 and check its
              sources and timing. Re-run production after edits to render the
              changes.
            </p>
          </div>
          <button className="btn" onClick={() => onNavigate({ tab: "review" })}>
            Open exports <ArrowUpRight size={13} />
          </button>
        </div>
      )}
      {production?.status === "error" && !active && (
        <div className="production-pause error">
          <AlertTriangle size={17} />
          <div>
            <b>The last run stopped with an error</b>
            <p>{production.message}</p>
          </div>
        </div>
      )}
      <div className="production-columns">
        <div className="production-roadmap">
          <div className="production-section-heading">
            <span>YOUR PRODUCTION PATH</span>
            <button
              aria-label="Refresh production plan"
              className="icon-btn"
              onClick={() => setRefresh((v) => v + 1)}
            >
              <RefreshCw size={13} className={loading ? "spin" : ""} />
            </button>
          </div>
          {plan ? (
            plan.steps.map((step, i) => {
              const Icon = icons[step.id] || Circle;
              return (
                <button
                  className={`production-step ${step.status}`}
                  key={step.id}
                  onClick={() => onNavigate({ tab: step.tab })}
                >
                  <div className="production-step-node">
                    {step.status === "done" ? (
                      <Check size={13} />
                    ) : (
                      <Icon size={14} />
                    )}
                  </div>
                  <div>
                    <div className="production-step-title">
                      <span>{String(i + 1).padStart(2, "0")}</span>
                      <h4>{step.title}</h4>
                      <small>
                        {step.status === "done"
                          ? "Ready"
                          : step.status === "provided"
                            ? "Provided"
                            : step.status === "review"
                              ? "Your review"
                              : step.status === "pending"
                                ? "Next"
                                : "Waiting"}
                      </small>
                    </div>
                    <p>{step.description}</p>
                  </div>
                </button>
              );
            })
          ) : (
            <div className="production-loading">
              <LoaderCircle size={22} className="spin" />
              Checking the project…
            </div>
          )}
          <div className="production-footnote">
            <ShieldCheck size={14} />
            <p>
              “Provided” means you supplied the material—not that the app
              verified it. Final exports still require the editorial and
              preflight checks.
            </p>
          </div>
        </div>
        <div className="production-config">
          <div className="production-section-heading">
            <span>THIS RUN</span>
            <span
              className={`production-connection ${config.connected ? "on" : ""}`}
            >
              <i />
              {config.connected ? "AI connected" : "Local only"}
            </span>
          </div>
          {available.length > 0 && (
            <label className="field">
              Recording / voice source
              <select
                aria-label="Production source recording"
                value={options.source_asset_id || ""}
                disabled={!!active}
                onChange={(e) =>
                  change("source_asset_id", e.target.value || null)
                }
              >
                <option value="">No recording selected</option>
                {available.map((a) => (
                  <option value={a.id} key={a.id}>
                    {a.name} · {duration(a.duration)}
                  </option>
                ))}
              </select>
            </label>
          )}
          <Option
            title="Fill missing visual assignments"
            checked={options.auto_assign_visuals}
            onChange={(v) => change("auto_assign_visuals", v)}
            disabled={!!active}
          >
            Use your imported media. Existing scene choices stay in place;
            review visual identity and suitability.
          </Option>
          <Option
            title="Generate missing narration"
            checked={options.generate_voice}
            onChange={(v) => change("generate_voice", v)}
            disabled={!!active}
          >
            Synthetic speech only if no voice is assigned. Requires a connected
            API and paid-stage approval.
          </Option>
          <div className="production-paid">
            <div className="production-paid-title">
              <LockKeyhole size={14} />
              <b>Paid-stage approval</b>
              {!config.connected && (
                <button onClick={onConnect}>
                  Connect AI <ArrowUpRight size={11} />
                </button>
              )}
            </div>
            <Option
              title="Allow paid AI stages in this run"
              checked={options.allow_paid}
              onChange={(v) => change("allow_paid", v)}
              disabled={!!active || !config.connected}
            >
              The provider may charge for research, writing, transcription, and
              requested voice generation. No price is guaranteed.
            </Option>
            <label className="field">
              Narration character cap
              <input
                aria-label="Narration character spending cap"
                type="number"
                min="1000"
                max="90000"
                step="1000"
                defaultValue={options.max_voice_characters}
                disabled={!!active}
                onBlur={(e) => {
                  const v = Math.max(
                    1000,
                    Math.min(90000, Number(e.target.value) || 45000),
                  );
                  e.target.value = v;
                  change("max_voice_characters", v);
                }}
              />
            </label>
            {plan?.paid_stages.length > 0 && (
              <p className="production-paid-preview">
                <Info size={11} />
                <span>
                  Potential next AI work: {plan.paid_stages.join("; ")}.
                </span>
              </p>
            )}
          </div>
          <div className="production-output">
            <label className="field">
              Draft resolution
              <select
                aria-label="Production draft resolution"
                value={options.resolution}
                disabled={!!active}
                onChange={(e) => change("resolution", e.target.value)}
              >
                <option value="480p">480p · Quick review</option>
                <option value="720p">720p · HD draft</option>
                <option value="1080p">1080p · Full HD</option>
              </select>
            </label>
            <details>
              <summary>Review-only exceptions</summary>
              <Option
                title="Allow placeholder visuals"
                checked={options.allow_placeholders}
                onChange={(v) => change("allow_placeholders", v)}
                disabled={!!active}
              >
                Missing visuals become visibly marked cards. This is not a
                finished documentary.
              </Option>
              <Option
                title="Allow a silent picture draft"
                checked={options.allow_silent}
                onChange={(v) => change("allow_silent", v)}
                disabled={!!active}
              >
                Render without a spoken voice when no narration is assigned.
              </Option>
            </details>
          </div>
        </div>
      </div>
      <div className="production-bottom-note">
        <Info size={13} />
        <span>
          {plan?.disclaimer ||
            "Your source material stays in the saved project between runs."}{" "}
          Keep confidential material out of this shared prototype.
        </span>
      </div>
      <div className="modal-footer production-footer">
        <div>
          <b>
            {project.scenes.length} scenes <span>·</span>{" "}
            {duration(project.scenes.reduce((n, s) => n + s.duration, 0))}{" "}
            assembled
          </b>
          <small>
            {project.target_minutes} min target · No automatic padding to hit
            the target
          </small>
        </div>
        {active ? (
          <button
            className="btn"
            onClick={async () => {
              try {
                await api(`/api/jobs/${active.id}/cancel`, "POST", {});
              } catch (e) {
                onError(e);
              }
            }}
          >
            Cancel operation
          </button>
        ) : (
          <button
            className="btn primary"
            aria-label="Run guided production"
            disabled={starting || loading || !plan}
            onClick={run}
          >
            {starting ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <Sparkles size={15} />
            )}{" "}
            Run available stages <ArrowRight size={14} />
          </button>
        )}
      </div>
    </Shell>
  );
}

export function PreflightModal({ project, api, onClose, onNavigate, onError }) {
  const [report, setReport] = useState(null),
    [filter, setFilter] = useState("all"),
    [refresh, setRefresh] = useState(0),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    let stopped = false;
    setLoading(true);
    api(`/api/projects/${project.id}/preflight`)
      .then((r) => {
        if (!stopped) setReport(r);
      })
      .catch((e) => {
        if (!stopped) onError(e);
      })
      .finally(() => {
        if (!stopped) setLoading(false);
      });
    return () => {
      stopped = true;
    };
  }, [project.updated_at, refresh]);
  const visible = (report?.issues || []).filter(
    (i) =>
      filter === "all" ||
      (filter === "blocking" ? i.blocks_final : i.severity === "warning"),
  );
  return (
    <Shell
      title="A check before the final cut."
      kicker="EDITORIAL & TECHNICAL PREFLIGHT"
      onClose={onClose}
      className="preflight-modal"
    >
      <div className="preflight-intro">
        <ShieldCheck size={20} />
        <p>
          These checks find structural problems and missing producer sign-offs.{" "}
          <b>
            They do not determine whether a case claim is true or media is
            legally cleared.
          </b>
        </p>
        <button
          className="icon-btn"
          aria-label="Refresh preflight"
          onClick={() => setRefresh((v) => v + 1)}
        >
          <RefreshCw size={15} className={loading ? "spin" : ""} />
        </button>
      </div>
      {report ? (
        <>
          <div className="preflight-stats">
            <div className={report.errors ? "blocked" : "clear"}>
              <b>{report.errors}</b>
              <span>Final-export blockers</span>
            </div>
            <div>
              <b>{report.warnings}</b>
              <span>Review warnings</span>
            </div>
            <div>
              <b>
                {report.coverage.scenes_with_references}
                <small> / {report.coverage.scenes}</small>
              </b>
              <span>Scenes linked to sources</span>
            </div>
          </div>
          <div className="preflight-filters">
            {[
              ["all", "All checks"],
              ["blocking", "Blocking"],
              ["warning", "Warnings"],
            ].map(([key, label]) => (
              <button
                key={key}
                className={key === filter ? "selected" : ""}
                onClick={() => setFilter(key)}
              >
                {label}
              </button>
            ))}
            <span>
              {report.ready_for_final
                ? "Structural checks complete"
                : !report.ready_for_draft
                  ? "Resolve technical blockers before any render"
                  : "A watermarked draft may still be available"}
            </span>
          </div>
          <div className="preflight-issues">
            {visible.length ? (
              visible.map((issue, i) => (
                <div
                  className={`preflight-issue ${issue.severity}`}
                  key={issue.code + i}
                >
                  <div className="preflight-issue-icon">
                    {issue.blocks_final ? (
                      <AlertTriangle size={17} />
                    ) : (
                      <Info size={17} />
                    )}
                  </div>
                  <div>
                    <div className="preflight-issue-heading">
                      <h3>{issue.title}</h3>
                      <span>
                        {issue.blocks_draft
                          ? "BLOCKS ALL EXPORTS"
                          : issue.blocks_final
                            ? "FINAL BLOCKER"
                            : "REVIEW"}
                      </span>
                    </div>
                    <p>{issue.detail}</p>
                  </div>
                  <button
                    className="text-link"
                    onClick={() =>
                      onNavigate({
                        ...issue,
                        tab: issue.tab,
                        media: ["rights_notes", "missing_media_file"].includes(
                          issue.code,
                        ),
                      })
                    }
                  >
                    Open {names[issue.tab]} <ArrowUpRight size={13} />
                  </button>
                </div>
              ))
            ) : (
              <div className="preflight-clear">
                <CheckCircle2 size={30} />
                <h3>
                  {filter === "all"
                    ? "No structural issues found."
                    : "No checks in this group."}
                </h3>
                <p>
                  Human factual, legal, and creative judgment is still required.
                </p>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="production-loading">
          <LoaderCircle className="spin" size={25} />
          Checking the current project…
        </div>
      )}
      <div className="preflight-snapshot-note">
        <Info size={12} />
        <p>
          This is the current project check. Every new video export includes its
          own frozen preflight report, source trail, chapter draft, and
          publication checklist.
        </p>
      </div>
      <div className="modal-footer">
        <a
          className="btn"
          href={`/api/projects/${project.id}/preflight.md`}
          download
        >
          <Download size={14} /> Download report
        </a>
        <button className="btn primary" onClick={onClose}>
          Back to the edit <ArrowUpRight size={13} />
        </button>
      </div>
    </Shell>
  );
}
