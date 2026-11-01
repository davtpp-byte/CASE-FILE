import React, { useState, useEffect, useRef, useMemo } from "react";
import { createRoot } from "react-dom/client";
import {
  Clapperboard,
  Search,
  FileText,
  ShieldCheck,
  Sparkles,
  Upload,
  Download,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Plus,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Volume2,
  VolumeX,
  Maximize2,
  Undo2,
  Layers,
  FolderOpen,
  Settings2,
  Music2,
  AudioLines,
  Film,
  Image as ImageIcon,
  X,
  ArrowUp,
  ArrowDown,
  Trash2,
  Check,
  CheckCircle2,
  Clock3,
  Link2,
  ExternalLink,
  LockKeyhole,
  CircleHelp,
  GripVertical,
  Info,
  AlertTriangle,
  LoaderCircle,
  Send,
  Mic,
  Monitor,
  ZoomIn,
  ZoomOut,
  Scissors,
  Scan,
  BookOpen,
  FileJson,
  MessageSquareText,
  PanelRight,
  Circle,
  RefreshCw,
} from "lucide-react";
import "./styles.css";
import EpisodeSetup from "./EpisodeSetup.jsx";
import { rememberSetup, cachedSetups, forgetSetup } from "./SessionBackup.js";
import {
  keepWorkingFiles,
  clearWorkingFiles,
  workingFiles,
  restoreWorkingSession,
  protectAvailableServerFiles,
} from "./MediaSession.js";
import {
  UploadProgress,
  validateUpload,
  sendUploadRequest,
  uploadLimits,
} from "./Uploads.jsx";
import { ProductionModal, PreflightModal } from "./ProductionTools.jsx";

function downloadProjectSnapshot(project, onBlocked) {
  const { undo, ...snapshot } = project;
  if (window.top !== window && onBlocked) {
    rememberSetup(project).catch(() => {});
    onBlocked({ kind: "setup", url: window.location.href });
    return;
  }
  snapshot._casefile_export = {
    version: "0.4.2",
    preview_origin: window.location.origin,
    exported_at: new Date().toISOString(),
    media_bytes_included: false,
  };
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "casefile-project.json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

const uid = () =>
  [...crypto.getRandomValues(new Uint8Array(8))]
    .map((n) => n.toString(16).padStart(2, "0"))
    .join("");
const tc = (seconds = 0, frames = false) => {
  let s = Math.max(0, Number(seconds) || 0);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s) % 60).padStart(2, "0")}${frames ? ":" + String(Math.floor((s % 1) * 24)).padStart(2, "0") : ""}`;
};
const wc = (text) => (text?.match(/\b[\w’'-]+\b/g) || []).length;
const bytes = (n) =>
  n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`;
const sum = (scenes) =>
  (scenes || []).reduce((n, s) => n + Number(s.duration || 0), 0);
const referencePattern = /\[\s*(S\d+(?:(?:\s*[,;]\s*|\s+)S?\d+)*)\s*\]/gi;
const clean = (s) => (s || "").replace(referencePattern, "").trim();
const scriptFromScenes = (scenes) =>
  scenes
    .map((s) => {
      const refs = [
        ...new Set([
          ...(s.source_ids || []),
          ...[...(s.narration || "").matchAll(referencePattern)].flatMap(
            (match) => (match[1].match(/\d+/g) || []).map((n) => "S" + n),
          ),
        ]),
      ];
      return (
        clean(s.narration) +
        (refs.length ? " " + refs.map((id) => `[${id}]`).join(" ") : "")
      ).trim();
    })
    .join("\n\n");
const elapsed = (date) => {
  const n = Math.round((Date.now() - new Date(date)) / 60000);
  return n < 1
    ? "Just now"
    : n < 60
      ? `${n}m ago`
      : new Date(date).toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
        });
};

let browserSession;
try {
  browserSession = sessionStorage.getItem("casefile-session");
  if (!browserSession) {
    browserSession = uid() + uid();
    sessionStorage.setItem("casefile-session", browserSession);
  }
} catch {
  browserSession = uid() + uid();
}
const preference = {
  get(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {}
  },
};
async function api(path, method = "GET", body, onUploadProgress) {
  if (onUploadProgress)
    return sendUploadRequest(
      path,
      method,
      body,
      browserSession,
      onUploadProgress,
    );
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: {
      "X-Casefile-Session": browserSession,
      ...(body && !(body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
    },
    body:
      body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });
  const type = response.headers.get("content-type") || "";
  const data = type.includes("json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const e = new Error(data?.detail || data || "Something went wrong.");
    e.status = response.status;
    throw e;
  }
  return data;
}
function Button({ icon: Icon, children, kind = "", className = "", ...props }) {
  return (
    <button className={`btn ${kind} ${className}`} {...props}>
      {Icon && <Icon size={15} />}
      <span>{children}</span>
    </button>
  );
}
function IconButton({ icon: Icon, label, className = "", ...props }) {
  return (
    <button
      className={`icon-btn ${className}`}
      title={label}
      aria-label={label}
      {...props}
    >
      <Icon size={16} />
    </button>
  );
}
function Badge({ children, tone = "" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
function Toggle({ checked, onChange, label }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      className={`toggle ${checked ? "on" : ""}`}
      onClick={() => onChange(!checked)}
    >
      <span />
    </button>
  );
}
function Empty({ icon: Icon = Layers, title, children, action }) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon size={24} />
      </div>
      <h3>{title}</h3>
      <p>{children}</p>
      {action}
    </div>
  );
}
function Modal({
  title,
  eyebrow,
  children,
  onClose,
  wide = false,
  className = "",
}) {
  useEffect(() => {
    const key = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
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
        className={`modal ${wide ? "wide" : ""} ${className}`}
      >
        <header className="modal-header">
          <div>
            {eyebrow && <div className="eyebrow">{eyebrow}</div>}
            <h2>{title}</h2>
          </div>
          <IconButton icon={X} label="Close dialog" onClick={onClose} />
        </header>
        {children}
      </section>
    </div>
  );
}
function Wave({ values = [], color = "#91b0ab" }) {
  if (!values.length) return null;
  return (
    <svg
      className="wave"
      viewBox={`0 0 ${values.length * 3} 30`}
      preserveAspectRatio="none"
      aria-label="Audio waveform"
    >
      {values.map((v, i) => (
        <line
          key={i}
          x1={i * 3 + 1}
          x2={i * 3 + 1}
          y1={15 - Math.max(0.6, v * 13)}
          y2={15 + Math.max(0.6, v * 13)}
          stroke={color}
          strokeWidth="1.7"
        />
      ))}
    </svg>
  );
}

function App() {
  const [project, setProject] = useState(null),
    [projectList, setProjectList] = useState([]),
    [config, setConfig] = useState({ connected: false });
  const [tab, setTab] = useState("edit"),
    [leftTab, setLeftTab] = useState("scenes"),
    [inspectorTab, setInspectorTab] = useState("scene");
  const [modal, setModal] = useState(null),
    [selectedId, setSelectedId] = useState(null),
    [time, setTime] = useState(0),
    [playing, setPlaying] = useState(false),
    [muted, setMuted] = useState(false);
  const [zoom, setZoom] = useState(1),
    [jobs, setJobs] = useState([]),
    [busy, setBusy] = useState(false),
    [uploading, setUploading] = useState(false),
    [uploadProgress, setUploadProgress] = useState(null),
    [savedBeforeClear, setSavedBeforeClear] = useState(false),
    [backupStatus, setBackupStatus] = useState("pending"),
    [recoveredSetup, setRecoveredSetup] = useState(null),
    [downloadGate, setDownloadGate] = useState(null),
    [saving, setSaving] = useState("saved"),
    [toast, setToast] = useState(null),
  [command, setCommand] = useState("");
  const [selectedTrack, setSelectedTrack] = useState(null),
    [mediaId, setMediaId] = useState(null),
    [frameSize, setFrameSize] = useState({ width: 640, height: 360 });
  const pending = useRef({}),
    saveTimer = useRef(null),
    savePromise = useRef(null),
    projectRef = useRef(null),
    toastTimer = useRef(null),
    watched = useRef(new Set()),
    initialPoll = useRef(true);
  const audioRef = useRef(null),
    musicRef = useRef(null),
    videoRef = useRef(null),
    screenRef = useRef(null),
    fileRef = useRef(null),
    timelineRef = useRef(null),
    playingRef = useRef(false),
    timeRef = useRef(0),
    dragId = useRef(null),
    messagesRef = useRef(null);
  projectRef.current = project;
  playingRef.current = playing;
  timeRef.current = time;
  const scenes = project?.scenes || [],
    assets = project?.assets || [],
    duration = sum(scenes),
    selected = scenes.find((s) => s.id === selectedId) || scenes[0];
  const offsets = useMemo(() => {
    let t = 0;
    return scenes.map((s) => {
      const n = t;
      t += s.duration;
      return n;
    });
  }, [scenes]);
  const activeIndex = Math.max(
    0,
    scenes.findIndex((s, i) => time < offsets[i] + s.duration),
  );
  const activeScene = scenes[activeIndex] || selected;
  const visual = assets.find((a) => a.id === activeScene?.asset_id),
    voice = assets.find((a) => a.id === project?.narration_id),
    music = assets.find((a) => a.id === project?.music_id);
  const activeJob = jobs.find((j) => ["running", "queued"].includes(j.status));
  const locked = busy || !!activeJob;
  const notify = (message, tone = "success") => {
    setToast({ message, tone });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 6500);
  };
  const report = (e) => {
    if (e.status === 412) setModal("settings");
    notify(e.message || String(e), "error");
  };
  const acceptProject = (p) => {
    rememberSetup(p)
      .then(setBackupStatus)
      .catch(() => setBackupStatus("unavailable"));
    setProject(p);
    preference.set("casefile-project", p.id);
  };

  useEffect(() => {
    (async () => {
      try {
        const saved = await cachedSetups().catch(() => []);
        api("/api/browser-session", "POST", {
          origin: window.location.origin,
          version: "0.4.2",
          snapshot: saved[0]?.project || null,
        }).catch(() => {});
        const b = await api("/api/bootstrap");
        setProjectList(b.projects);
        setConfig(b.config);
        const last = preference.get("casefile-project");
        const requested = new URLSearchParams(window.location.search).get(
          "project",
        );
        const id =
          b.projects.find((p) => p.id === requested)?.id ||
          b.projects.find((p) => p.id === last && !p.is_demo)?.id ||
          b.projects.find((p) => p.has_episode)?.id ||
          b.projects.find((p) => p.is_demo)?.id ||
          b.projects[0]?.id;
        if (id) {
          let p = await api("/api/projects/" + id);
          const cached =
            saved.find((entry) => entry.id === last) ||
            saved.find((entry) => entry.id === id);
          if (cached) {
            const files = await workingFiles(cached.id).catch(() => []);
            if (
              cached.id !== p.id ||
              (cached.project.updated_at || "") > (p.updated_at || "") ||
              files.length
            ) {
              const recovered = await restoreWorkingSession(
                cached.project,
                api,
                (progress) => setUploadProgress(progress),
              ).catch((error) => {
                console.warn("Working-session recovery:", error.message);
                return null;
              });
              if (recovered && !recovered.missing) p = recovered.project;
              else if (
                cached.id !== p.id ||
                (cached.project.updated_at || "") > (p.updated_at || "")
              )
                setRecoveredSetup(cached);
            }
          }
          acceptProject(p);
          if (p.episode || p.mode === "narration") setTab("setup");
          setSelectedId(p.scenes[0]?.id);
        }
      } catch (e) {
        const saved = await cachedSetups().catch(() => []);
        if (saved[0]) setRecoveredSetup(saved[0]);
        report(e);
      }
    })();
    return () => {
      clearTimeout(saveTimer.current);
      clearTimeout(toastTimer.current);
    };
  }, []);
  useEffect(() => {
    if (!project?.id) return;
    if (
      recoveredSetup?.project?.id === project.id &&
      (recoveredSetup.project.assets?.length || 0) >
        (project.assets?.length || 0)
    )
      return;
    const timer = setTimeout(
      () =>
        rememberSetup(project)
          .then((status) => {
            setBackupStatus(status);
            if (status !== "newer-saved-copy")
              api("/api/browser-session", "POST", {
                origin: window.location.origin,
                version: "0.4.2",
                snapshot: project,
              }).catch(() => {});
          })
          .catch(() => setBackupStatus("unavailable")),
      350,
    );
    return () => clearTimeout(timer);
  }, [project, recoveredSetup]);

  useEffect(() => {
    if (project?.id) protectAvailableServerFiles(project).catch(() => {});
  }, [project?.id, project?.assets?.map((asset) => asset.id).join(",")]);

  useEffect(() => {
    if (!project?.id) return;
    initialPoll.current = true;
    watched.current = new Set();
    let stopped = false;
    const poll = async () => {
      try {
        const list = await api(`/api/projects/${project.id}/jobs`);
        if (stopped) return;
        setJobs(list);
        if (initialPoll.current) {
          list
            .filter((j) => ["running", "queued"].includes(j.status))
            .forEach((j) => watched.current.add(j.id));
          initialPoll.current = false;
        }
        for (const job of list) {
          if (
            watched.current.has(job.id) &&
            !["running", "queued"].includes(job.status)
          ) {
            watched.current.delete(job.id);
            if (job.status === "done") {
              const p = await api(`/api/projects/${project.id}`);
              if (!stopped) {
                setProject((cur) =>
                  cur?.id === p.id ? { ...p, ...pending.current } : cur,
                );
                if (job.kind === "render")
                  notify("Your video export is ready to download.");
                else if (job.kind === "production")
                  notify(
                    (job.result?.message || "Production stage saved.").slice(
                      0,
                      240,
                    ),
                    job.result?.outcome === "complete" ? "success" : "info",
                  );
                else
                  notify("Operation complete. Your project has been updated.");
              }
            } else if (job.status === "error") notify(job.message, "error");
            else notify(job.message, "info");
          }
        }
      } catch (e) {
        if (!stopped) console.warn("Job status unavailable");
      }
    };
    poll();
    const timer = setInterval(poll, 1600);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [project?.id]);
  useEffect(() => {
    if (!screenRef.current || tab !== "edit") return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      let w = Math.min(width - 40, ((height - 12) * 16) / 9);
      setFrameSize({
        width: Math.max(180, w),
        height: Math.max(101, (w * 9) / 16),
      });
    });
    observer.observe(screenRef.current);
    return () => observer.disconnect();
  }, [tab, project?.id]);
  useEffect(() => {
    if (messagesRef.current)
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
  }, [project?.messages, inspectorTab]);
  useEffect(() => {
    const f = (e) => {
      if (
        ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(
          document.activeElement?.tagName,
        )
      )
        return;
      if (e.code === "Space" && tab === "edit") {
        e.preventDefault();
        setPlaying((v) => !v);
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        flushSave().catch(report);
      }
    };
    window.addEventListener("keydown", f);
    return () => window.removeEventListener("keydown", f);
  }, [tab]);
  useEffect(() => {
    if (!playing) return;
    let id,
      last = performance.now();
    const tick = (now) => {
      const dt = Math.min(0.15, (now - last) / 1000);
      last = now;
      setTime((t) => {
        if (t + dt >= duration) {
          setPlaying(false);
          return 0;
        }
        return t + dt;
      });
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [playing, duration]);
  useEffect(() => {
    if (playing && activeScene) setSelectedId(activeScene.id);
  }, [activeScene?.id, playing]);
  useEffect(() => {
    const local = time - (offsets[activeIndex] || 0),
      source = (activeScene?.audio_start || 0) + local;
    const a = audioRef.current,
      m = musicRef.current,
      v = videoRef.current;
    if (a) {
      a.muted = muted;
      a.volume = 1;
      const inSpeech =
        local < (activeScene?.audio_duration ?? activeScene?.duration ?? 0) &&
        source < (voice?.duration || Infinity);
      if (Math.abs(a.currentTime - source) > 0.3 && Number.isFinite(source))
        a.currentTime = Math.min(source, voice?.duration || source);
      if (playing && inSpeech) a.play().catch(() => {});
      else a.pause();
    }
    if (m) {
      m.muted = muted;
      m.volume = Math.min(0.5, project?.music_volume || 0);
      if (m.duration && Math.abs(m.currentTime - (time % m.duration)) > 0.4)
        m.currentTime = time % m.duration;
      if (playing) m.play().catch(() => {});
      else m.pause();
    }
    if (v) {
      const trimStart = activeScene?.trim_start || 0;
      const sceneDur = activeScene?.duration || 0;
      // Use the cue's original selected crop end when stored on the scene
      // (gap scenes inherit it from their matched cue), so preview loops
      // within the exact crop, not the gap duration or full source file.
      const sourceCropEnd = activeScene?.source_crop_end;
      const cropOut = sourceCropEnd
        ? Math.min(sourceCropEnd, v.duration || Infinity)
        : Math.min(trimStart + sceneDur, v.duration || Infinity);
      const cropDur = cropOut - trimStart;
      if (cropDur > 0) {
        // Loop the selected crop within the scene: wrap playback position
        // within the crop boundaries (trim_start to crop_out), not the whole
        // source file duration. Trim the last repetition at the scene end.
        const expected = trimStart + (local % cropDur);
        if (Number.isFinite(expected) && Math.abs(v.currentTime - expected) > 0.3)
          v.currentTime = expected;
      }
      if (playing) v.play().catch(() => {});
      else v.pause();
    }
  }, [
    time,
    playing,
    muted,
    activeScene?.id,
    voice?.id,
    music?.id,
    project?.music_volume,
    tab,
  ]);

  function queueSave(fields) {
    if (activeJob && activeJob.kind !== "render") {
      notify(
        "Wait for the current AI operation to finish before editing this project.",
        "info",
      );
      return;
    }
    setProject((cur) => ({
      ...cur,
      ...fields,
      ...(fields.script !== undefined
        ? { script_dirty: !fields.scenes, script_approved_hash: null }
        : {}),
    }));
    pending.current = { ...pending.current, ...fields };
    setSaving("pending");
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => flushSave().catch(report), 650);
  }
  async function flushSave() {
    clearTimeout(saveTimer.current);
    if (savePromise.current) await savePromise.current;
    if (!Object.keys(pending.current).length) return projectRef.current;
    const fields = pending.current,
      id = projectRef.current.id;
    pending.current = {};
    setSaving("saving");
    const task = (async () => {
      try {
        const p = await api("/api/projects/" + id, "PATCH", fields);
        if (projectRef.current?.id === id)
          setProject({ ...p, ...pending.current });
        setSaving(Object.keys(pending.current).length ? "pending" : "saved");
        return p;
      } catch (e) {
        pending.current = { ...fields, ...pending.current };
        setSaving("error");
        throw e;
      }
    })();
    savePromise.current = task;
    try {
      return await task;
    } finally {
      savePromise.current = null;
    }
  }
  async function openProject(id) {
    try {
      await flushSave();
      setPlaying(false);
      const p = await api("/api/projects/" + id);
      pending.current = {};
      acceptProject(p);
      setSelectedId(p.scenes[0]?.id);
      setTime(0);
      setJobs([]);
      setModal(null);
      setTab(
        p.episode || p.mode === "narration"
          ? "setup"
          : p.scenes.length
            ? "edit"
            : p.mode === "topic"
              ? "research"
              : p.mode === "script"
                ? "script"
                : "edit",
      );
    } catch (e) {
      report(e);
    }
  }
  async function refreshProjects() {
    try {
      const b = await api("/api/bootstrap");
      setProjectList(b.projects);
    } catch (e) {
      report(e);
    }
  }
  async function startOperation(path) {
    if (locked) return;
    setBusy(true);
    setPlaying(false);
    try {
      await flushSave();
      const result = await api(path, "POST", {});
      if (result.job_id) {
        watched.current.add(result.job_id);
        const list = await api(`/api/projects/${project.id}/jobs`);
        setJobs(list);
        notify("Operation started. You can follow its progress below.", "info");
      }
      return result;
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  async function doAssemble() {
    if (locked) return;
    setBusy(true);
    try {
      await flushSave();
      const p = await api(`/api/projects/${project.id}/assemble`, "POST", {});
      acceptProject(p);
      setSelectedId(p.scenes[0]?.id);
      setTime(0);
      setTab("edit");
      notify(
        `Built ${p.scenes.length} editable scenes. Check visuals and timing.`,
      );
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  async function uploadFiles(files) {
    if (!files?.length) return;
    setUploading(true);
    try {
      validateUpload(files);
      setUploadProgress({
        phase: "uploading",
        loaded: 0,
        total: 0,
        label: `${files.length} selected file(s)`,
      });
      await flushSave();
      const form = new FormData();
      [...files].forEach((f) => form.append("files", f));
      const p = await api(
        `/api/projects/${project.id}/upload`,
        "POST",
        form,
        (progress) => setUploadProgress((old) => ({ ...old, ...progress })),
      );
      await keepWorkingFiles(
        project.id,
        [...files].filter((file) => !/\.(md|txt|json|srt)$/i.test(file.name)),
        "auto",
      ).catch(() =>
        notify(
          "Browser could not keep a local working-file recovery copy. Keep your originals.",
          "info",
        ),
      );
      acceptProject(p);
      if ([...files].some((f) => /\.(txt|md)$/i.test(f.name))) setTab("script");
      notify(`${files.length} file${files.length > 1 ? "s" : ""} imported.`);
    } catch (e) {
      setUploadProgress((old) => (old ? { ...old, phase: "error" } : null));
      report(e);
      try {
        setProject(await api("/api/projects/" + project.id));
      } catch {}
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }
  function selectScene(scene, index) {
    setSelectedId(scene.id);
    setTime(offsets[index] || 0);
    setPlaying(false);
  }
  function selectVisualScene(scene, index) {
    selectScene(scene, index);
    setSelectedTrack({ kind: "visual", sceneId: scene.id });
  }
  function updateScene(fields) {
    if (!selected) return;
    const next = scenes.map((s) =>
      s.id === selected.id ? { ...s, ...fields } : s,
    );
    const changes = { scenes: next };
    if (fields.narration !== undefined) {
      changes.script = scriptFromScenes(next);
      if (voice) changes.narration_id = null;
      next.find((s) => s.id === selected.id).captions = [];
    }
    if (fields.source_ids !== undefined)
      changes.script = scriptFromScenes(next);
    queueSave(changes);
  }

  function currentOffset(index) {
    return offsets[index] || 0;
  }

  function trackLabel(kind) {
    return { visual: "Visuals V1", narration: "Narration A1", music: "Music A2" }[kind];
  }

  function trackIcon(kind) {
    return { visual: Film, narration: Mic, music: Music2 }[kind];
  }

  function trackFields(kind, scene) {
    switch (kind) {
      case "visual":
        return { asset: scene.asset_id, inPoint: scene.trim_start || 0, duration: scene.duration };
      case "narration":
        return { text: scene.narration || "", start: scene.audio_start || 0, duration: scene.audio_duration || scene.duration, volume: scene.narration_volume || 1 };
      default:
        return { id: scene.music_id || null, start: scene.music_start || 0, duration: scene.music_duration || scene.duration, volume: scene.music_volume || (project?.music_volume || 1) };
    }
  }

  function updateTrack(kind, fields) {
    if (!selected) return;
    const next = scenes.map((s) => {
      if (s.id !== selected.id) return s;
      const cur = trackFields(kind, s);
      const merged = { ...cur, ...fields };
      let out;
      if (kind === "visual") {
        out = { ...s, asset_id: merged.asset || null, trim_start: Math.max(0, merged.inPoint), duration: Math.max(0.5, merged.duration) };
      } else if (kind === "narration") {
        out = { ...s, narration: merged.text, audio_start: merged.start, audio_duration: Math.max(0.5, merged.duration), narration_volume: merged.volume };
      } else {
        out = { ...s, music_id: merged.id || null, music_start: merged.start, music_duration: Math.max(0.5, merged.duration), music_volume: merged.volume };
      }
      return out;
    });
    const changes = { scenes: next };
    if (kind !== "visual") changes.script = scriptFromScenes(next);
    queueSave(changes);
    notify(`${trackLabel(kind)} adjusted.`);
  }

  function deleteTrack(kind) {
    if (!selected) return;
    if (!window.confirm(`Remove ${trackLabel(kind)} from this scene?`)) return;
    const next = scenes.map((s) => {
      if (s.id !== selected.id) return s;
      if (kind === "visual") {
        const { asset_id, trim_start, ...rest } = s;
        return rest;
      }
      if (kind === "narration") {
        const { narration, audio_start, audio_duration, narration_volume, ...rest } = s;
        return rest;
      }
      const { music_id, music_start, music_duration, music_volume, ...rest } = s;
      return rest;
    });
    queueSave({ scenes: next, script: scriptFromScenes(next) });
    if (selectedTrack?.sceneId === selected.id) setSelectedTrack(null);
    notify(`${trackLabel(kind)} removed from scene.`);
  }

  function splitTrack(kind) {
    if (!selected || locked) return;
    const cut = Math.round((time - currentOffset(activeIndex)) * 1000) / 1000;
    if (cut < 0.5 || selected.duration - cut < 0.5) return;
    const s = selected;
    const words = (s.narration || "").split(/\s+/).filter(Boolean);
    const wordCut = Math.round((words.length * cut) / s.duration);
    const left = { ...s, duration: cut };
    const right = { ...s, id: uid(), duration: s.duration - cut, trim_start: (s.trim_start || 0) + cut, audio_start: (s.audio_start || 0) + cut, show_title: false };
    if (kind === "narration") {
      left.narration = words.slice(0, wordCut).join(" ");
      right.narration = words.slice(wordCut).join(" ");
      left.audio_duration = Math.min(s.audio_duration || s.duration, cut);
      right.audio_duration = Math.max(0.04, (s.audio_duration || s.duration) - cut);
      right.narration_volume = s.narration_volume;
    }
    if (kind === "music") {
      left.music_duration = Math.max(0.04, cut);
      right.music_start = (s.music_start || 0) + cut;
      right.music_duration = Math.max(0.04, (s.music_duration || s.duration) - cut);
      right.music_volume = s.music_volume;
    }
    if (kind === "visual") {
      right.captions = (s.captions || []).filter((c) => c.end > cut).map((c) => ({ ...c, start: Math.max(0, c.start - cut), end: c.end - cut }));
      left.captions = (s.captions || []).filter((c) => c.start < cut).map((c) => ({ ...c, end: Math.min(c.end, cut) }));
    }
    const next = [...scenes];
    next.splice(activeIndex, 1, left, right);
    queueSave({ scenes: next, script: scriptFromScenes(next) });
    setPlaying(false);
    setSelectedId(right.id);
    setSelectedTrack({ kind, sceneId: right.id });
    notify(`${trackLabel(kind)} split at playhead.`);
  }

  function addScene() {
    const s = {
      id: uid(),
      title: "New scene",
      chapter: "Case narrative",
      narration: "",
      source_ids: [],
      duration: 8,
      asset_id: null,
      motion: "slow-zoom",
      transition: "none",
      transition_duration: 0,
      show_title: true,
      trim_start: 0,
      audio_start: sum(scenes),
      audio_duration: 8,
      timing: "estimated",
      captions: [],
    };
    queueSave({ scenes: [...scenes, s] });
    setSelectedId(s.id);
    setTime(duration);
    setPlaying(false);
  }
  function moveScene(id, delta) {
    const list = [...scenes],
      i = list.findIndex((s) => s.id === id),
      j = i + delta;
    if (j < 0 || j >= list.length) return;
    [list[i], list[j]] = [list[j], list[i]];
    queueSave({ scenes: list });
    setPlaying(false);
    setTime(0);
  }
  function dropScene(target) {
    const list = [...scenes],
      i = list.findIndex((s) => s.id === dragId.current),
      j = list.findIndex((s) => s.id === target);
    if (i < 0 || i === j) return;
    const [s] = list.splice(i, 1);
    list.splice(j, 0, s);
    queueSave({ scenes: list });
    setPlaying(false);
    setTime(0);
  }
  function trimScene(event, scene, side) {
    event.preventDefault();
    event.stopPropagation();
    if (locked) return;
    setPlaying(false);
    const content = timelineRef.current?.querySelector(".timeline-content");
    if (!content || !duration) return;
    const pps = content.getBoundingClientRect().width / duration,
      startX = event.clientX,
      baseScenes = scenes;
    const update = (e) => {
      let delta = Math.round(((e.clientX - startX) / pps) * 10) / 10,
        fields;
      if (side === "right")
        fields = {
          duration: Math.max(0.5, Math.min(600, scene.duration + delta)),
        };
      else {
        delta = Math.max(
          -Math.min(scene.audio_start || 0, scene.trim_start || 0),
          Math.min(scene.duration - 0.5, delta),
        );
        fields = {
          duration: Math.max(0.5, Math.min(600, scene.duration - delta)),
          trim_start: Math.max(0, (scene.trim_start || 0) + delta),
          audio_start: Math.max(0, (scene.audio_start || 0) + delta),
          audio_duration: Math.max(
            0.04,
            (scene.audio_duration || scene.duration) - delta,
          ),
          captions: (scene.captions || [])
            .filter((c) => c.end > delta)
            .map((c) => ({
              ...c,
              start: Math.max(0, c.start - delta),
              end: Math.max(0, c.end - delta),
            })),
        };
      }
      queueSave({
        scenes: baseScenes.map((s) =>
          s.id === scene.id ? { ...s, ...fields } : s,
        ),
      });
    };
    const finish = () => {
      window.removeEventListener("pointermove", update);
      window.removeEventListener("pointerup", finish);
    };
    window.addEventListener("pointermove", update);
    window.addEventListener("pointerup", finish, { once: true });
  }
  function splitAtPlayhead() {
    if (!activeScene || locked) return;
    const cut = Math.round((time - offsets[activeIndex]) * 1000) / 1000;
    if (cut < 0.5 || activeScene.duration - cut < 0.5) return;
    const s = activeScene,
      words = s.narration.split(/\s+/).filter(Boolean),
      wordCut = Math.round((words.length * cut) / s.duration);
    const left = {
      ...s,
      duration: cut,
      narration: words.slice(0, wordCut).join(" "),
      audio_duration: Math.min(s.audio_duration || s.duration, cut),
      captions: (s.captions || [])
        .filter((c) => c.start < cut)
        .map((c) => ({ ...c, end: Math.min(c.end, cut) })),
    };
    const right = {
      ...s,
      id: uid(),
      title: s.title + " · continued",
      duration: s.duration - cut,
      narration: words.slice(wordCut).join(" "),
      show_title: false,
      trim_start: (s.trim_start || 0) + cut,
      audio_start: (s.audio_start || 0) + cut,
      audio_duration: Math.max(0.04, (s.audio_duration || s.duration) - cut),
      captions: (s.captions || [])
        .filter((c) => c.end > cut)
        .map((c) => ({
          ...c,
          start: Math.max(0, c.start - cut),
          end: c.end - cut,
        })),
    };
    const next = [...scenes];
    next.splice(activeIndex, 1, left, right);
    queueSave({
      scenes: next,
      script: scriptFromScenes(next),
      narration_id: project.narration_id,
    });
    setPlaying(false);
    setSelectedId(right.id);
    notify("Scene split at the playhead. Review the cut and captions.");
  }
  async function undo() {
    try {
      await flushSave();
      const p = await api(`/api/projects/${project.id}/undo`, "POST", {});
      acceptProject(p);
      setTime(0);
      setPlaying(false);
      notify("Previous saved edit restored.");
    } catch (e) {
      report(e);
    }
  }
  async function direct(e, text) {
    e?.preventDefault();
    const instruction = (text || command).trim();
    if (!instruction || locked) return;
    setBusy(true);
    try {
      await flushSave();
      const r = await api(`/api/projects/${project.id}/command`, "POST", {
        instruction,
      });
      setCommand("");
      setInspectorTab("director");
      if (r.project) {
        acceptProject(r.project);
        notify("Edit applied. Undo is available.");
      } else {
        watched.current.add(r.job_id);
        setJobs(await api(`/api/projects/${project.id}/jobs`));
      }
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  function requireAI(next) {
    if (!config.connected) {
      setModal("settings");
      notify(
        "Connect an AI service to use this feature. Local editing is already available.",
        "info",
      );
      return false;
    }
    if (next) setModal(next);
    return true;
  }
  function transcribeAsset(asset) {
    if (!requireAI()) return;
    if (
      window.confirm(
        "Send this audio to the AI service for transcription? This replaces the current timeline and may incur usage charges. Undo will be available.",
      )
    ) {
      setModal(null);
      startOperation(`/api/projects/${project.id}/transcribe/${asset.id}`);
    }
  }
  async function setSource(source, fields) {
    try {
      await flushSave();
      const p = await api(
        `/api/projects/${project.id}/sources/${source.id}`,
        "PATCH",
        fields,
      );
      acceptProject(p);
    } catch (e) {
      report(e);
    }
  }
  function seekTimeline(e) {
    const rect = e.currentTarget.getBoundingClientRect();
    setTime(
      Math.max(
        0,
        Math.min(duration, ((e.clientX - rect.left) / rect.width) * duration),
      ),
    );
    setPlaying(false);
  }
  async function makeFirstDraft({ render = false, resolution = "480p" } = {}) {
    if (locked || !project) return;
    setBusy(true);
    setPlaying(false);
    try {
      await flushSave();
      const saved = (await cachedSetups().catch(() => [])).find(
        (entry) => entry.id === project.id,
      );
      if (saved && (await workingFiles(project.id).catch(() => [])).length) {
        const recovered = await restoreWorkingSession(
          saved.project,
          api,
          (progress) => setUploadProgress(progress),
        );
        if (recovered.missing) setRecoveredSetup(saved);
        else if (recoveredSetup?.id === saved.id) setRecoveredSetup(null);
        if (recovered.restored)
          notify(
            `Recovered ${recovered.restored} working file(s) from this browser.`,
            "info",
          );
      }
      const response = await api(
        `/api/projects/${project.id}/episode/first-draft`,
        "POST",
        {},
      );
      const p = response.project;
      pending.current = {};
      acceptProject(p);
      setSelectedId(response.preview.scene_id);
      setTime(response.preview.time);
      setTab("edit");
      if (!render)
        notify(
          "Your preview is ready. The timeline now uses your available source files; no final approvals were inferred.",
        );
      if (render) {
        const track = p.assets.find(
          (a) => a.id === p.narration_id && a.available_on_server !== false,
        );
        if (!track)
          throw new Error(
            "Picture preview is ready. Add the matching narration recording to make a video with sound.",
          );
        const job = await api(`/api/projects/${p.id}/render`, "POST", {
          resolution,
          draft: true,
          captions: p.captions,
          allow_guided_gaps: true,
          allow_inspection: true,
        });
        watched.current.add(job.job_id);
        setJobs(await api(`/api/projects/${p.id}/jobs`));
        setTab("review");
        setModal(null);
        notify(
          "Making your inspection video. It includes clearly marked gaps where sources are missing.",
          "info",
        );
      }
    } catch (error) {
      report(error);
    } finally {
      setBusy(false);
    }
  }

  async function startRender(options) {
    setBusy(true);
    setPlaying(false);
    try {
      await flushSave();
      const result = await api(
        `/api/projects/${project.id}/render`,
        "POST",
        options,
      );
      watched.current.add(result.job_id);
      setJobs(await api(`/api/projects/${project.id}/jobs`));
      setModal(null);
      setTab("review");
      notify(
        "Rendering started. Long episodes can take a while on this CPU.",
        "info",
      );
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }

  async function openTool(name, targetTab) {
    try {
      await flushSave();
      setPlaying(false);
      if (targetTab) setTab(targetTab);
      setModal(name);
    } catch (e) {
      report(e);
    }
  }
  function navigateTool(action) {
    setPlaying(false);
    if (action.tab === "settings") {
      setModal("settings");
      return;
    }
    setTab(action.tab || "edit");
    if (action.scene_id) {
      const index = scenes.findIndex((s) => s.id === action.scene_id);
      if (index >= 0) {
        setSelectedId(action.scene_id);
        setTime(offsets[index] || 0);
      }
    }
    if (action.media) setMediaId(action.asset_id || assets[0]?.id || null);
    setModal(action.media ? "media" : null);
  }
  async function runProduction(options) {
    if (locked) return;
    setBusy(true);
    setPlaying(false);
    try {
      await flushSave();
      const result = await api(
        `/api/projects/${project.id}/produce`,
        "POST",
        options,
      );
      watched.current.add(result.job_id);
      const list = await api(`/api/projects/${project.id}/jobs`);
      setJobs(list);
      if (list.find((j) => j.id === result.job_id)?.status === "done")
        acceptProject(await api(`/api/projects/${project.id}`));
    } catch (e) {
      report(e);
    } finally {
      setBusy(false);
    }
  }
  async function approveScript() {
    if (locked) return;
    if (
      !window.confirm(
        "Confirm that you read this AI-written script against its original sources. This approves the text for narration; it does not certify factual accuracy or media rights.",
      )
    )
      return;
    try {
      await flushSave();
      acceptProject(
        await api(`/api/projects/${project.id}/approve-script`, "POST", {
          acknowledge: true,
        }),
      );
      notify(
        "Script text approved for narration. Final factual and rights review is still required.",
      );
    } catch (e) {
      report(e);
    }
  }
  function fullscreen() {
    const frame = document.querySelector(".video-frame");
    if (frame?.requestFullscreen)
      frame
        .requestFullscreen()
        .catch(() =>
          notify("Fullscreen is unavailable in this embedded preview.", "info"),
        );
  }

  if (!project)
    return (
      <div className="boot">
        <img src="/assets/favicon.svg" width="48" />
        <div className="brand-word">
          CASEFILE <span>STUDIO</span>
        </div>
        <LoaderCircle className="spin" size={20} />
        <p>{toast?.message || "Opening your documentary workspace…"}</p>
        {recoveredSetup && (
          <div className="recovery-notice">
            <b>A setup backup is saved in this browser</b>
            <p>
              {recoveredSetup.project.title} ·{" "}
              {recoveredSetup.project.assets?.length || 0} media references.
              Media bytes are not included.
            </p>
            <button
              className="btn primary"
              aria-label="Download recovered setup"
              onClick={() =>
                downloadProjectSnapshot(recoveredSetup.project, setDownloadGate)
              }
            >
              Download saved project setup
            </button>
          </div>
        )}
      </div>
    );

  function renderInspector() {
    return (
      <>
        <div className="inspector-tabs">
          {[
            ["scene", "Scene", Settings2],
            ["audio", "Audio", AudioLines],
            ["director", "Director", Sparkles],
          ].map(([key, label, Icon]) => (
            <button
              key={key}
              className={inspectorTab === key ? "active" : ""}
              onClick={() => setInspectorTab(key)}
            >
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>
        {inspectorTab === "scene" ? (
          <div className="inspector-content">
            {selected ? (
              <>
                <div className="section-label">
                  <span>
                    SCENE{" "}
                    {String(scenes.indexOf(selected) + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <IconButton
                      icon={ArrowUp}
                      label="Move scene earlier"
                      onClick={() => moveScene(selected.id, -1)}
                      disabled={scenes[0]?.id === selected.id}
                    />
                    <IconButton
                      icon={ArrowDown}
                      label="Move scene later"
                      onClick={() => moveScene(selected.id, 1)}
                      disabled={scenes.at(-1)?.id === selected.id}
                    />
                  </div>
                </div>
                <label className="field">
                  Scene title
                  <input
                    value={selected.title}
                    onChange={(e) => updateScene({ title: e.target.value })}
                  />
                </label>
                <div className="field-row">
                  <label className="field">
                    Duration
                    <div className="input-unit">
                      <input
                        aria-label="Scene duration"
                        type="number"
                        min="0.5"
                        max="600"
                        step="0.5"
                        value={selected.duration}
                        onChange={(e) =>
                          updateScene({
                            duration: Math.max(
                              0.5,
                              Math.min(600, Number(e.target.value) || 0.5),
                            ),
                          })
                        }
                      />
                      <span>sec</span>
                    </div>
                  </label>
                  <label className="field">
                    Transition
                    <select
                      value={selected.transition}
                      onChange={(e) =>
                        updateScene({ transition: e.target.value })
                      }
                    >
                      <option value="none">None</option>
                      <option value="cross-dissolve">Cross-dissolve</option>
                      <option value="fade">Fade to black</option>
                      <option value="cut">Cut</option>
                    </select>
                  </label>
                  {selected.transition !== "none" && selected.transition !== "cut" && (
                    <label className="field">
                      Transition duration
                      <div className="input-unit">
                        <input
                          aria-label="Transition duration"
                          type="number"
                          min="0"
                          max="600"
                          step="0.25"
                          value={selected.transition_duration ?? 0}
                          onChange={(e) =>
                            updateScene({
                              transition_duration: Math.max(
                                0,
                                Math.min(600, Number(e.target.value) || 0),
                              ),
                            })
                          }
                        />
                        <span>sec</span>
                      </div>
                    </label>
                  )}
                </div>
                <label className="field">
                  Visual source
                  <select
                    value={selected.asset_id || ""}
                    onChange={(e) =>
                      updateScene({ asset_id: e.target.value || null })
                    }
                  >
                    <option value="">No visual assigned</option>
                    {assets
                      .filter((a) => ["image", "video"].includes(a.kind))
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.name}
                        </option>
                      ))}
                  </select>
                </label>
                <button
                  className="text-link"
                  onClick={() => {
                    setMediaId(selected.asset_id);
                    setModal("media");
                  }}
                >
                  <Layers size={12} /> Browse media library{" "}
                  <ArrowUpRight size={12} />
                </button>
                <div className="inspector-divider" />
                <label className="field">
                  Camera movement
                  <select
                    value={selected.motion}
                    onChange={(e) => updateScene({ motion: e.target.value })}
                  >
                    <option value="slow-zoom">Slow push in</option>
                    <option value="pan-left">Gentle pan left</option>
                    <option value="none">Static / original video</option>
                  </select>
                </label>
                {assets.find((a) => a.id === selected.asset_id)?.kind ===
                  "video" && (
                  <label className="field">
                    Source in-point (seconds)
                    <input
                      type="number"
                      min="0"
                      value={selected.trim_start || 0}
                      onChange={(e) =>
                        updateScene({
                          trim_start: Math.max(0, Number(e.target.value) || 0),
                        })
                      }
                    />
                  </label>
                )}
                <div className="switch-line">
                  <span>Show scene title</span>
                  <Toggle
                    checked={selected.show_title}
                    onChange={(v) => updateScene({ show_title: v })}
                    label="Show scene title"
                  />
                </div>
                <div className="switch-line">
                  <span>Subtitles</span>
                  <Toggle
                    checked={project.captions}
                    onChange={(v) => queueSave({ captions: v })}
                    label="Subtitles"
                  />
                </div>
                <div className="inspector-divider" />
                <label className="field">
                  Source references
                  <input
                    aria-label="Scene source references"
                    key={
                      selected.id +
                      "refs" +
                      (selected.source_ids || []).join(",")
                    }
                    defaultValue={(selected.source_ids || []).join(", ")}
                    placeholder="S1, S2"
                    onBlur={(e) => {
                      const refs = e.target.value
                        .toUpperCase()
                        .split(/[,;\s]+/)
                        .filter(Boolean);
                      if (refs.some((ref) => !/^S\d+$/.test(ref))) {
                        notify(
                          "Use source IDs such as S1, S2. Add sources in Research first.",
                          "error",
                        );
                        return;
                      }
                      if (
                        JSON.stringify(refs) !==
                        JSON.stringify(selected.source_ids || [])
                      )
                        updateScene({ source_ids: [...new Set(refs)] });
                    }}
                  />
                </label>
                <p className="inspector-source-hint">
                  {project.sources.length
                    ? "Library: " + project.sources.map((x) => x.id).join(", ")
                    : "Add original records or notes in Research, then link their IDs here."}
                </p>
                <label className="field">
                  Chapter label
                  <input
                    aria-label="Scene chapter label"
                    value={selected.chapter || ""}
                    onChange={(e) => updateScene({ chapter: e.target.value })}
                  />
                </label>
                <label className="field">
                  Narration{" "}
                  <span className="field-note">
                    {wc(selected.narration)} words
                  </span>
                  <textarea
                    rows="5"
                    value={selected.narration}
                    placeholder="Add the narration for this scene…"
                    onChange={(e) => updateScene({ narration: e.target.value })}
                  />
                </label>
                <div className="micro-note">
                  <Clock3 size={12} />
                  {selected.timing === "imported-captions"
                    ? "Supplied caption timestamps · cue/audio review required"
                    : selected.timing === "transcribed"
                      ? "Source-aligned segment timing"
                      : selected.timing === "scene-aligned"
                        ? "Voice aligned by scene; captions estimated"
                        : "Estimated timing · review with narration"}
                </div>
                <div className="inspector-divider" />
                <label className="field">
                  Documentary look
                  <select
                    value={project.look}
                    onChange={(e) => queueSave({ look: e.target.value })}
                  >
                    <option value="noir">Noir — cool & restrained</option>
                    <option value="archive">Archive — desaturated</option>
                    <option value="natural">Natural — original color</option>
                  </select>
                </label>
                <button
                  className="danger-link"
                  onClick={() => {
                    if (
                      window.confirm("Remove this scene from the timeline?")
                    ) {
                      queueSave({
                        scenes: scenes.filter((s) => s.id !== selected.id),
                      });
                      setTime(0);
                      setSelectedId(null);
                    }
                  }}
                >
                  <Trash2 size={12} /> Remove scene
                </button>
                <div className="inspector-divider" />
                <div className="section-label">
                  <span>TRACKS</span>
                  <span className="track-pill">
                    {selectedTrack
                      ? trackLabel(selectedTrack.kind) + " · scene " + (scenes.indexOf(selected) + 1)
                      : "Click a clip on any timeline lane to select its track"}
                  </span>
                </div>
                {["visual", "narration", "music"].map((kind) => {
                  const f = trackFields(kind, selected);
                  const isSel = selectedTrack?.kind === kind && selectedTrack?.sceneId === selected.id;
                  const Icon = trackIcon(kind);
                  return (
                    <div key={kind} className="track-row">
                      <div className="track-row-head">
                        <Icon size={13} />
                        <span>{trackLabel(kind)}</span>
                        {isSel && <span className="track-active">selected</span>}
                        <button
                          className="icon-btn"
                          title="Split track clip at playhead"
                          onClick={() => splitTrack(kind)}
                          disabled={locked || !scenes.length}
                        >
                          <Scissors size={12} />
                        </button>
                        <button
                          className="danger-link"
                          onClick={() => deleteTrack(kind)}
                          disabled={locked}
                        >
                          <Trash2 size={11} /> Remove track
                        </button>
                      </div>
                      <div className="track-row-fields">
                        {kind === "visual" && (
                          <>
                            <label className="field">Source in-point (sec)
                              <input
                                type="number" min="0" step="0.5"
                                value={f.inPoint}
                                onChange={(e) =>
                                  updateTrack(kind, { inPoint: Math.max(0, Number(e.target.value) || 0) })
                                }
                              />
                            </label>
                            <label className="field">Duration (sec)
                              <input
                                type="number" min="0.5" step="0.5"
                                value={f.duration}
                                onChange={(e) =>
                                  updateTrack(kind, { duration: Math.max(0.5, Number(e.target.value) || 0.5) })
                                }
                              />
                            </label>
                          </>
                        )}
                        {kind === "narration" && (
                          <>
                            <label className="field">Narration text
                              <textarea
                                rows="2"
                                value={f.text}
                                onChange={(e) => updateTrack(kind, { text: e.target.value })}
                              />
                            </label>
                            <label className="field">Start (sec)
                              <input
                                type="number" min="0" step="0.5"
                                value={f.start}
                                onChange={(e) =>
                                  updateTrack(kind, { start: Math.max(0, Number(e.target.value) || 0) })
                                }
                              />
                            </label>
                            <label className="field">Duration (sec)
                              <input
                                type="number" min="0.5" step="0.5"
                                value={f.duration}
                                onChange={(e) =>
                                  updateTrack(kind, { duration: Math.max(0.5, Number(e.target.value) || 0.5) })
                                }
                              />
                            </label>
                            <label className="field">Volume
                              <input
                                className="range" type="range" min="0" max="200" step="5"
                                value={Math.round(f.volume * 100)}
                                onChange={(e) =>
                                  updateTrack(kind, { volume: Number(e.target.value) / 100 })
                                }
                              />
                              <span>{Math.round(f.volume * 100)}%</span>
                            </label>
                          </>
                        )}
                        {kind === "music" && (
                          <>
                            <label className="field">Music source
                              <select
                                value={f.id || ""}
                                onChange={(e) => updateTrack(kind, { id: e.target.value || null })}
                              >
                                <option value="">No music</option>
                                {assets
                                  .filter((a) => a.has_audio || a.kind === "audio")
                                  .map((a) => (
                                    <option key={a.id} value={a.id}>
                                      {a.name}
                                    </option>
                                  ))}
                              </select>
                            </label>
                            <label className="field">Start (sec)
                              <input
                                type="number" min="0" step="0.5"
                                value={f.start}
                                onChange={(e) =>
                                  updateTrack(kind, { start: Math.max(0, Number(e.target.value) || 0) })
                                }
                              />
                            </label>
                            <label className="field">Duration (sec)
                              <input
                                type="number" min="0.5" step="0.5"
                                value={f.duration}
                                onChange={(e) =>
                                  updateTrack(kind, { duration: Math.max(0.5, Number(e.target.value) || 0.5) })
                                }
                              />
                            </label>
                            <label className="field">Volume
                              <input
                                className="range" type="range" min="0" max="200" step="5"
                                value={Math.round(f.volume * 100)}
                                onChange={(e) =>
                                  updateTrack(kind, { volume: Number(e.target.value) / 100 })
                                }
                              />
                              <span>{Math.round(f.volume * 100)}%</span>
                            </label>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </>
            ) : (
              <Empty title="No scene selected">
                Build a timeline or add a scene to begin.
              </Empty>
            )}
          </div>
        ) : inspectorTab === "audio" ? (
          <div className="inspector-content">
            <div className="section-label">VOICE & SOUND</div>
            <label className="field">
              Narration track
              <select
                value={project.narration_id || ""}
                onChange={(e) =>
                  queueSave({ narration_id: e.target.value || null })
                }
              >
                <option value="">No narration assigned</option>
                {assets
                  .filter((a) => a.has_audio || a.kind === "audio")
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
              </select>
            </label>
            {voice && (
              <div className="audio-summary">
                <Mic size={15} />
                <span>
                  {tc(voice.duration)}
                  <small>
                    {voice.generated ? "AI-generated voice" : "Uploaded audio"}
                  </small>
                </span>
                <IconButton
                  icon={Play}
                  label="Preview voice track"
                  onClick={() => {
                    setMediaId(voice.id);
                    setModal("media");
                  }}
                />
              </div>
            )}
            <Button
              className="full"
              icon={Sparkles}
              disabled={locked}
              onClick={() => requireAI("narrate")}
            >
              Generate AI narration
            </Button>
            <button
              className="text-link centered"
              onClick={() => {
                setModal("media");
                fileRef.current.click();
              }}
            >
              <Upload size={12} /> Upload your own voice-over
            </button>
            {voice && (
              <Button
                className="full subtle"
                icon={AudioLines}
                disabled={locked}
                onClick={() => transcribeAsset(voice)}
              >
                Transcribe & align
              </Button>
            )}
            <div className="inspector-divider" />
            <label className="field">
              Background music
              <select
                value={project.music_id || ""}
                onChange={(e) =>
                  queueSave({ music_id: e.target.value || null })
                }
              >
                <option value="">No music assigned</option>
                {assets
                  .filter((a) => a.has_audio || a.kind === "audio")
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
              </select>
            </label>
            <label className="field">
              Music level{" "}
              <span className="field-note">
                {Math.round(project.music_volume * 100)}%
              </span>
              <input
                aria-label="Music level"
                className="range"
                type="range"
                min="0"
                max="50"
                value={Math.round(project.music_volume * 100)}
                onChange={(e) =>
                  queueSave({ music_volume: Number(e.target.value) / 100 })
                }
              />
            </label>
            <div className="feature-note">
              <ShieldCheck size={15} />
              <div>
                <b>Speech stays in front</b>
                <p>
                  Exports normalize narration and automatically duck music
                  underneath it.
                </p>
              </div>
            </div>
            <p className="micro-note block">
              Preview audio is approximate. Export applies the final mix. Supply
              music you have permission to use.
            </p>
          </div>
        ) : (
          <div className="director-panel">
            <div className="director-status">
              <span className="tiny-dot" />
              {config.connected
                ? "AI service connected"
                : "Local commands available"}
              <button onClick={() => setModal("settings")}>
                <Settings2 size={13} />
              </button>
            </div>
            <div className="messages" ref={messagesRef}>
              {project.messages.map((m, i) => (
                <div className={`message ${m.role}`} key={i}>
                  {m.role === "assistant" && (
                    <div className="message-author">
                      <Sparkles size={12} /> CASEFILE DIRECTOR
                    </div>
                  )}
                  <p>{m.text}</p>
                </div>
              ))}
            </div>
            <div className="director-footnote">
              <LockKeyhole size={12} /> Creative rewrites need an API
              connection. No automatic factual verification.
            </div>
          </div>
        )}
      </>
    );
  }

  return (
    <div className="app-shell">
      <aside className="rail">
        <button
          className="brand-mark"
          title="Casefile Studio"
          onClick={() => setTab("edit")}
        >
          <img src="/assets/favicon.svg" alt="Casefile Studio" />
        </button>
        <div className="rail-group">
          <IconButton
            icon={Sparkles}
            label={
              project.episode?.guide
                ? "Episode setup"
                : "Guided automatic production"
            }
            onClick={() =>
              project.episode?.guide
                ? (setTab("setup"), setPlaying(false))
                : openTool("production")
            }
          />
          <IconButton
            className={tab === "edit" ? "active" : ""}
            icon={Clapperboard}
            label="Editing workspace"
            onClick={() =>
              project.episode?.guide &&
              (!project.scenes.some((s) => s.asset_id) ||
                project.episode.plan?.mode === "inspection")
                ? makeFirstDraft()
                : setTab("edit")
            }
          />
          <IconButton
            icon={Layers}
            label="Media library"
            onClick={() => {
              setMediaId(null);
              setModal("media");
            }}
          />
          <IconButton
            icon={FolderOpen}
            label="Your projects"
            onClick={() => {
              refreshProjects();
              setModal("projects");
            }}
          />
          <IconButton
            className={tab === "review" ? "active" : ""}
            icon={Download}
            label="Exports and review"
            onClick={() => setTab("review")}
          />
        </div>
        <div className="rail-bottom">
          <IconButton
            icon={CircleHelp}
            label="How this workspace works"
            onClick={() => setModal("help")}
          />
          <IconButton
            icon={Settings2}
            label="Settings and AI connection"
            onClick={() => setModal("settings")}
          />
          <div
            className="workspace-avatar"
            title="Single workspace · working prototype"
          >
            CS
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="brand-word">
            CASEFILE <span>STUDIO</span>
            <i />
          </div>
          <div className="workspace-crumb">
            <span>Workspace</span>
            <ChevronRight size={12} />
            <span>Documentaries</span>
          </div>
          <div className="topbar-right">
            <span className="engine-status">
              <span className="tiny-dot" />
              Render engine ready
            </span>
            <button
              className={`connection ${config.connected ? "connected" : ""}`}
              onClick={() => setModal("settings")}
            >
              <Sparkles size={13} />
              {config.connected ? "AI connected" : "Connect AI"}
              <ChevronDown size={12} />
            </button>
          </div>
        </header>
        <div className="project-header">
          <div className="project-heading">
            <div className="project-kicker">
              <span className="eyebrow">DOCUMENTARY WORKSPACE</span>
              {project.is_demo && <Badge tone="demo">Fictional sample</Badge>}
            </div>
            <div className="title-row">
              <h1>{project.title}</h1>
              <button
                className="project-switch"
                aria-label="Switch project"
                onClick={() => {
                  refreshProjects();
                  setModal("projects");
                }}
              >
                <ChevronDown size={16} />
              </button>
            </div>
            <div className="project-meta">
              <span
                className={`save-state ${saving === "error" ? "error" : ""}`}
              >
                {saving === "saving" || saving === "pending" ? (
                  <LoaderCircle size={11} className="spin" />
                ) : saving === "error" ? (
                  <AlertTriangle size={11} />
                ) : (
                  <CheckCircle2 size={11} />
                )}{" "}
                {saving === "saved"
                  ? "All changes saved"
                  : saving === "error"
                    ? "Save failed — retry editing"
                    : "Saving changes…"}
              </span>
              <span className="meta-dot">·</span>
              <span>{project.target_minutes} min target</span>
              <span className="meta-dot">·</span>
              <span>
                {tc(duration)}{" "}
                {project.episode?.guide
                  ? voice
                    ? "planned"
                    : project.episode?.timings
                      ? "timed plan · audio missing"
                      : "estimated plan"
                  : "assembled"}
              </span>
            </div>
          </div>
          <div className="project-actions">
            <button
              className="btn backup-project-btn"
              aria-label="Save project backup"
              title="Save project settings now; no server connection needed. Media is not included."
              onClick={() => downloadProjectSnapshot(project, setDownloadGate)}
            >
              <FileJson size={14} />
              <span>Save backup</span>
            </button>
            <IconButton
              icon={Undo2}
              label="Undo last saved edit"
              onClick={undo}
              disabled={locked || !project.undo?.length}
            />
            <Button icon={Plus} onClick={() => setModal("new")}>
              New project
            </Button>
            <Button
              icon={Clapperboard}
              kind="setup-header-button"
              onClick={() => {
                setTab("setup");
                setPlaying(false);
              }}
            >
              Episode setup
            </Button>
            {!project.episode?.guide && (
              <Button
                icon={Sparkles}
                kind="produce"
                onClick={() => openTool("production")}
              >
                Produce draft
              </Button>
            )}
            {project.exports[0] ? (
              <a
                className="btn primary"
                aria-label="Download latest MP4"
                onClick={(ev) => {
                  if (window.top !== window) {
                    ev.preventDefault();
                    setDownloadGate({
                      kind: "video",
                      url: new URL(
                        `/api/projects/${project.id}/exports/${project.exports[0].id}/download`,
                        window.location.origin,
                      ).href,
                    });
                  }
                }}
                href={`/api/projects/${project.id}/exports/${project.exports[0].id}/download`}
                download
              >
                <Download size={14} /> Download MP4
              </a>
            ) : (
              <Button
                kind="primary"
                icon={Film}
                disabled={locked}
                onClick={() =>
                  project.episode?.guide
                    ? makeFirstDraft({ render: true })
                    : openTool("export", "review")
                }
              >
                {project.episode?.guide ? "Make video" : "Export video"}
              </Button>
            )}
          </div>
        </div>
        <nav className="stage-nav">
          {[
            ...(project.episode ||
            project.mode === "narration" ||
            tab === "setup"
              ? [["setup", "Episode setup", FolderOpen, null]]
              : []),
            ["research", "Research", Search, project.sources.length],
            ["script", "Script", FileText, null],
            ["edit", "Edit", Clapperboard, scenes.length],
            ["review", "Review & export", ShieldCheck, null],
          ].map(([key, label, Icon, count], i) => (
            <button
              key={key}
              className={`${tab === key ? "active" : ""} ${key === "setup" ? "setup-nav" : ""}`}
              onClick={() => {
                if (
                  key === "edit" &&
                  project.episode?.guide &&
                  (!project.scenes.some((s) => s.asset_id) ||
                    project.episode.plan?.mode === "inspection")
                ) {
                  makeFirstDraft();
                  return;
                }
                setTab(key);
                setPlaying(false);
              }}
            >
              <span className="step-number">0{i + 1}</span>
              <Icon size={14} />
              <span>{label}</span>
              {count > 0 && <span className="stage-count">{count}</span>}
            </button>
          ))}
          <div className="stage-nav-end">
            <span className="prototype-label">WORKING PROTOTYPE · v0.4.2</span>
            <span className="aspect-label">
              <Monitor size={12} /> 16:9 · YouTube
            </span>
          </div>
        </nav>

        {recoveredSetup && (
          <div className="recovery-notice">
            <b>A newer saved setup was found in this browser.</b>
            <p>
              {recoveredSetup.project.title} ·{" "}
              {recoveredSetup.project.assets?.length || 0} media references.
              Download this before continuing with an older server copy; media
              files are not inside this JSON.
            </p>
            <button
              className="btn"
              aria-label="Download recovered setup"
              onClick={() =>
                downloadProjectSnapshot(recoveredSetup.project, setDownloadGate)
              }
            >
              Save recovered setup
            </button>
            <button className="btn" onClick={() => setRecoveredSetup(null)}>
              Dismiss
            </button>
          </div>
        )}
        {uploadProgress && (
          <div className="global-upload-progress">
            <UploadProgress progress={uploadProgress} />
          </div>
        )}
        {tab === "setup" && (
          <EpisodeSetup
            key={project.id}
            project={project}
            api={api}
            locked={locked}
            onFlush={flushSave}
            onBusy={setBusy}
            onError={report}
            onNotify={notify}
            onProject={(p) => {
              acceptProject(p);
              if (!p.scenes.some((s) => s.id === selectedId)) {
                setSelectedId(p.scenes[0]?.id);
                setTime(0);
              }
            }}
            onNavigate={(next) => {
              setTab(next);
              setPlaying(false);
              if (next === "edit") {
                const firstVisual = project.scenes.findIndex(
                  (scene) => scene.asset_id,
                );
                if (firstVisual >= 0) {
                  setSelectedId(project.scenes[firstVisual].id);
                  setTime(
                    sum(project.scenes.slice(0, firstVisual)) +
                      Math.min(
                        1 / 24,
                        project.scenes[firstVisual].duration / 2,
                      ),
                  );
                }
              }
            }}
            onRender={startRender}
            onQuickDraft={makeFirstDraft}
            backupStatus={backupStatus}
            onNew={() => setModal("new")}
          />
        )}
        {tab === "edit" && (
          <div className="edit-grid">
            <section className="scene-panel">
              <div className="panel-tabs">
                <button
                  className={leftTab === "scenes" ? "active" : ""}
                  onClick={() => setLeftTab("scenes")}
                >
                  Scenes <span>{scenes.length}</span>
                </button>
                <button
                  className={leftTab === "assets" ? "active" : ""}
                  onClick={() => setLeftTab("assets")}
                >
                  Media <span>{assets.length}</span>
                </button>
                <IconButton
                  icon={Plus}
                  label={leftTab === "scenes" ? "Add scene" : "Upload media"}
                  onClick={() =>
                    leftTab === "scenes" ? addScene() : fileRef.current.click()
                  }
                />
              </div>
              <div className="scene-list">
                {leftTab === "scenes" ? (
                  scenes.length ? (
                    scenes.map((s, i) => {
                      const a = assets.find((a) => a.id === s.asset_id);
                      return (
                        <div
                          key={s.id}
                          role="button"
                          tabIndex={0}
                          draggable
                          className={`scene-card ${selected?.id === s.id ? "selected" : ""}`}
                          onClick={() => selectVisualScene(s, i)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") selectVisualScene(s, i);
                          }}
                          onDragStart={() => (dragId.current = s.id)}
                          onDragOver={(e) => e.preventDefault()}
                          onDrop={(e) => {
                            e.preventDefault();
                            dropScene(s.id);
                          }}
                        >
                          <div className="scene-card-top">
                            <span className="scene-number">
                              {String(i + 1).padStart(2, "0")}
                            </span>
                            <span className="scene-start">
                              {tc(offsets[i])}
                            </span>
                            <GripVertical size={12} />
                          </div>
                          <div className="scene-card-body">
                            <div
                              className={`scene-thumb look-${project.look}`}
                              style={
                                a?.thumbnail
                                  ? { backgroundImage: `url("${a.thumbnail}")` }
                                  : {}
                              }
                            >
                              {!a && <ImageIcon size={17} />}
                              <span>{Math.round(s.duration)}s</span>
                            </div>
                            <div className="scene-card-text">
                              <h3>{s.title}</h3>
                              <p>{s.chapter || "Scene"}</p>
                              {!s.asset_id && <small>Visual needed</small>}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <Empty
                      icon={Clapperboard}
                      title="Your timeline starts here"
                    >
                      Paste a script, import narration, or add your first scene.
                      <Button icon={Plus} onClick={addScene}>
                        Add scene
                      </Button>
                    </Empty>
                  )
                ) : (
                  <div className="mini-media-list">
                    <button
                      className="mini-upload"
                      onClick={() => fileRef.current.click()}
                    >
                      <Upload size={18} />
                      <span>
                        {uploading ? "Uploading…" : "Import your media"}
                      </span>
                      <small>Media: 512 MB/file · 30 files/batch</small>
                    </button>
                    {assets.map((a) => (
                      <button
                        key={a.id}
                        className="mini-media"
                        onClick={() => {
                          setMediaId(a.id);
                          setModal("media");
                        }}
                      >
                        {a.thumbnail ? (
                          <img src={a.thumbnail} alt="" />
                        ) : (
                          <div>
                            <AudioLines size={20} />
                          </div>
                        )}
                        <span>
                          {a.name}
                          <small>
                            {a.kind} ·{" "}
                            {a.duration
                              ? tc(a.duration)
                              : `${a.width}×${a.height}`}
                          </small>
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <footer className="scene-footer">
                <Info size={12} />
                {project.is_demo
                  ? "Sample imagery is AI-generated."
                  : "Drag scenes to reorder your edit."}
              </footer>
            </section>
            <section className="monitor-panel">
              <div className="monitor-header">
                <span>
                  <span className="monitor-dot" />
                  PROGRAM MONITOR
                </span>
                <div>
                  <Badge>
                    {project.is_demo ? "FICTIONAL DEMO" : "EDIT PREVIEW"}
                  </Badge>
                  <IconButton
                    className="mobile-inspector"
                    icon={PanelRight}
                    label="Open scene inspector"
                    onClick={() => setModal("inspector")}
                  />
                </div>
              </div>
              <div className="monitor-screen" ref={screenRef}>
                <div
                  className={`video-frame look-${project.look}`}
                  style={{ width: frameSize.width, height: frameSize.height }}
                >
                  {visual?.kind === "video" ? (
                    <video
                      key={visual.id}
                      ref={videoRef}
                      src={visual.url}
                      muted
                      playsInline
                      loop={false}
                      onLoadedMetadata={() => setTime((t) => t)}
                    />
                  ) : visual ? (
                    <img
                      src={visual.url}
                      alt={visual.name}
                      style={{
                        transform:
                          activeScene?.motion === "slow-zoom"
                            ? `scale(${1 + (0.075 * (time - (offsets[activeIndex] || 0))) / activeScene.duration})`
                            : activeScene?.motion === "pan-left"
                              ? `scale(1.08) translateX(${2 - (4 * (time - (offsets[activeIndex] || 0))) / activeScene.duration}%)`
                              : undefined,
                      }}
                    />
                  ) : (
                    <div className="missing-visual">
                      <ImageIcon size={30} />
                      <span>
                        {scenes.length
                          ? "Visual needed"
                          : "Your next story starts here"}
                      </span>
                      <button onClick={() => setModal("media")}>
                        Import media <ArrowUpRight size={12} />
                      </button>
                    </div>
                  )}
                  <div className="film-shade" />
                  {activeScene?.show_title && (
                    <div
                      className="film-title"
                      style={{
                        fontSize: Math.max(16, frameSize.width * 0.045),
                      }}
                    >
                      <div className="film-rule" />
                      <p>
                        {String(activeIndex + 1).padStart(2, "0")} /{" "}
                        {activeScene.chapter || "DOCUMENTARY"}
                      </p>
                      <h2>{activeScene.title}</h2>
                    </div>
                  )}
                  {activeScene?.inspection_only && (
                    <div className="film-inspection-mark">
                      UNREVIEWED INSPECTION · NOT FOR PUBLICATION
                    </div>
                  )}
                  {visual && activeScene?.source_label && (
                    <div
                      className="film-source-label"
                      style={{
                        fontSize: Math.max(9, frameSize.height * 0.018),
                      }}
                    >
                      {activeScene.source_label}
                    </div>
                  )}
                  {project.captions &&
                    (activeScene?.narration ||
                      activeScene?.captions?.length) && (
                      <div
                        className="film-captions"
                        style={{
                          fontSize: Math.max(11, frameSize.width * 0.019),
                        }}
                      >
                        {(() => {
                          const local = time - (offsets[activeIndex] || 0);
                          if (
                            activeScene.captions_exact ||
                            activeScene.captions?.length
                          )
                            return activeScene.captions.find(
                              (c) => local >= c.start && local < c.end,
                            )?.text;
                          const words = clean(activeScene.narration).split(
                            /\s+/,
                          );
                          const chunk = Math.min(
                            Math.floor(
                              ((local / activeScene.duration) * words.length) /
                                9,
                            ) * 9,
                            Math.max(0, words.length - 1),
                          );
                          return words.slice(chunk, chunk + 9).join(" ");
                        })()}
                      </div>
                    )}
                  {project.is_demo && (
                    <span className="film-disclosure">
                      FICTIONAL DEMO · AI ILLUSTRATION
                    </span>
                  )}
                  <div className="frame-corner tl" />
                  <div className="frame-corner br" />
                </div>
              </div>
              <div className="player-controls">
                <div className="player-volume">
                  <IconButton
                    icon={muted ? VolumeX : Volume2}
                    label={muted ? "Unmute preview" : "Mute preview"}
                    onClick={() => setMuted((v) => !v)}
                  />
                  <span>
                    {voice ? "Voice + picture" : "Picture preview · no voice"}
                  </span>
                </div>
                <div className="transport">
                  <IconButton
                    icon={SkipBack}
                    label="Previous scene"
                    onClick={() => {
                      const i = Math.max(0, activeIndex - 1);
                      setTime(offsets[i] || 0);
                      setSelectedId(scenes[i]?.id);
                    }}
                  />
                  <button
                    className="play-btn"
                    aria-label={playing ? "Pause preview" : "Play preview"}
                    onClick={() => setPlaying((v) => !v)}
                    disabled={!scenes.length}
                  >
                    {playing ? (
                      <Pause size={15} fill="currentColor" />
                    ) : (
                      <Play size={15} fill="currentColor" />
                    )}
                  </button>
                  <IconButton
                    icon={SkipForward}
                    label="Next scene"
                    onClick={() => {
                      const i = Math.min(scenes.length - 1, activeIndex + 1);
                      setTime(offsets[i] || 0);
                      setSelectedId(scenes[i]?.id);
                    }}
                  />
                  <div className="time-display">
                    <span>{tc(time, true)}</span>
                    <i>/</i>
                    {tc(duration, true)}
                  </div>
                </div>
                <IconButton
                  icon={Maximize2}
                  label="Fullscreen preview"
                  onClick={fullscreen}
                />
              </div>
              <form className="director-bar" onSubmit={direct}>
                <div className="director-symbol">
                  <Sparkles size={16} />
                </div>
                <div className="director-input">
                  <label htmlFor="direction">
                    DIRECT YOUR EDIT{" "}
                    <span>
                      {config.connected ? "AI connected" : "Local + AI-ready"}
                    </span>
                  </label>
                  <input
                    id="direction"
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    placeholder={
                      project.episode?.guide
                        ? "Try “set music to 8%” or “use the archive look”…"
                        : "Try “use the archive look” or “set scene 2 to 12 seconds”…"
                    }
                    disabled={locked}
                  />
                </div>
                <IconButton
                  icon={MessageSquareText}
                  label="Show direction history"
                  onClick={() => setInspectorTab("director")}
                />
                <button
                  className="send-btn"
                  type="submit"
                  aria-label="Apply editing instruction"
                  disabled={locked || !command.trim()}
                >
                  {busy ? (
                    <LoaderCircle className="spin" size={16} />
                  ) : (
                    <ArrowUpRight size={18} />
                  )}
                </button>
              </form>
            </section>
            <aside className="inspector">{renderInspector()}</aside>
            <section className="timeline">
              <div className="timeline-toolbar">
                <div>
                  <Layers size={14} />
                  <strong>Timeline</strong>
                  <span>{scenes.length} scenes</span>
                  <i>·</i>
                  <span>{tc(duration)}</span>
                </div>
                <div>
                    <button
                    className="timeline-tool selected"
                    title="Split scene at playhead"
                    aria-label="Split scene at playhead"
                    onClick={splitAtPlayhead}
                    disabled={
                      locked ||
                      !activeScene ||
                      time - (offsets[activeIndex] || 0) < 0.5 ||
                      activeScene.duration -
                        (time - (offsets[activeIndex] || 0)) <
                      0.5
                    }
                  >
                    <Scissors size={13} />
                    <span>Split</span>
                  </button>
                  {activeScene && (
                    <span className="toolbar-sep" />
                  )}
                  <div className="track-tools">
                      <button
                        className={`timeline-tool ${selectedTrack?.kind === 'visual' ? 'selected' : ''}`}
                        title="Edit Visuals track"
                        aria-label="Edit Visuals track"
                        onClick={() => setSelectedTrack({ kind: "visual", sceneId: selected.id })}
                        disabled={locked || !selected.asset_id}
                      >
                        <Film size={12} />
                        <span>V1</span>
                      </button>
                      <button
                        className={`timeline-tool ${selectedTrack?.kind === 'narration' ? 'selected' : ''}`}
                        title="Edit Narration track"
                        aria-label="Edit Narration track"
                        onClick={() => setSelectedTrack({ kind: "narration", sceneId: selected.id })}
                        disabled={locked}
                      >
                        <Mic size={12} />
                        <span>A1</span>
                      </button>
                      <button
                        className={`timeline-tool ${selectedTrack?.kind === 'music' ? 'selected' : ''}`}
                        title="Edit Music track"
                        aria-label="Edit Music track"
                        onClick={() => setSelectedTrack({ kind: "music", sceneId: selected.id })}
                        disabled={locked}
                      >
                        <Music2 size={12} />
                        <span>A2</span>
                      </button>
                      <button
                        className="timeline-tool danger"
                        title="Remove selected track from scene"
                        aria-label="Remove track from scene"
                        onClick={() => {
                          if (!selectedTrack || selectedTrack.sceneId !== selected.id) return;
                          deleteTrack(selectedTrack.kind);
                          setSelectedTrack(null);
                        }}
                        disabled={locked || !selectedTrack || selectedTrack.sceneId !== selected.id}
                      >
                        <Trash2 size={12} />
                        <span>Delete</span>
                      </button>
                    </div>
                  <span className="toolbar-sep" />
                  <IconButton
                    icon={ZoomOut}
                    label="Zoom timeline out"
                    onClick={() => setZoom((v) => Math.max(1, v - 0.25))}
                  />
                  <span className="zoom-label">{Math.round(zoom * 100)}%</span>
                  <IconButton
                    icon={ZoomIn}
                    label="Zoom timeline in"
                    onClick={() => setZoom((v) => Math.min(5, v + 0.25))}
                  />
                  <IconButton
                    icon={Scan}
                    label="Fit timeline"
                    onClick={() => setZoom(1)}
                  />
                </div>
              </div>
              <div className="timeline-lanes">
                <div className="track-labels">
                  <div className="ruler-spacer" />
                  <div className="track-label video">
                    <Film size={12} />
                    <span>Visuals</span>
                    <span className="track-tag">V1</span>
                  </div>
                  <div className="track-label">
                    <Mic size={12} />
                    <span>Narration</span>
                    <span className="track-tag">A1</span>
                  </div>
                  <div className="track-label">
                    <Music2 size={12} />
                    <span>Music</span>
                    <span className="track-tag">A2</span>
                  </div>
                </div>
                <div className="timeline-scroll" ref={timelineRef}>
                  <div
                    className="timeline-content"
                    style={{ width: `${zoom * 100}%` }}
                    onClick={seekTimeline}
                  >
                    <div className="ruler">
                      {Array.from(
                        { length: Math.max(6, Math.ceil(zoom * 7)) },
                        (_, i) => (
                          <span
                            key={i}
                            style={{
                              left: `${(i / Math.max(6, Math.ceil(zoom * 7))) * 100}%`,
                            }}
                          >
                            {tc(
                              (i / Math.max(6, Math.ceil(zoom * 7))) * duration,
                            )}
                          </span>
                        ),
                      )}
                    </div>
                    <div className="visual-lane">
                      {scenes.map((s, i) => {
                        const a = assets.find((a) => a.id === s.asset_id);
                        return (
                          <button
                            className={`clip ${selected?.id === s.id ? "selected" : ""}`}
                            key={s.id}
                            style={{
                              left: `${(offsets[i] / duration) * 100}%`,
                              width: `${(s.duration / duration) * 100}%`,
                              backgroundImage: a?.thumbnail
                                ? `linear-gradient(0deg,rgba(10,13,15,.75),rgba(10,13,15,.05)),url("${a.thumbnail}")`
                                : undefined,
                            }}
                            onClick={(e) => {
                              e.stopPropagation();
                              selectVisualScene(s, i);
                            }}
                          >
                            <span>
                              {String(i + 1).padStart(2, "0")} <i>{s.title}</i>
                            </span>
                            {selected?.id === s.id && (
                              <>
                                <b
                                  className="trim-handle left"
                                  title="Drag to trim start"
                                  onPointerDown={(e) => trimScene(e, s, "left")}
                                />
                                <b
                                  className="trim-handle right"
                                  title="Drag to trim end"
                                  onPointerDown={(e) =>
                                    trimScene(e, s, "right")
                                  }
                                />
                              </>
                            )}
                          </button>
                        );
                      })}
                    </div>
                    <div
                      className={`audio-lane voice-lane ${voice ? "has-audio" : ""}`}
                    >
                      {voice ? (
                        <>
                          {scenes.map((s, i) => {
                            const peaks = voice.waveform || [],
                              start = Math.floor(
                                ((s.audio_start || 0) / (voice.duration || 1)) *
                                  peaks.length,
                              ),
                              end = Math.ceil(
                                (((s.audio_start || 0) +
                                  Math.min(
                                    s.duration,
                                    s.audio_duration || s.duration,
                                  )) /
                                  (voice.duration || 1)) *
                                  peaks.length,
                              );
                            return (
                              <button
                                className="voice-region"
                                key={s.id}
                                style={{
                                  pointerEvents: "auto",
                                  left: `${(offsets[i] / duration) * 100}%`,
                                  width: `${(s.duration / duration) * 100}%`,
                                }}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setSelectedTrack({ kind: "narration", sceneId: s.id });
                                }}
                              >
                                <Wave
                                  values={peaks.slice(
                                    start,
                                    Math.max(start + 1, end),
                                  )}
                                />
                              </button>
                            );
                          })}
                          <span className="audio-lane-label">
                            <Mic size={10} />
                            {voice.name}
                          </span>
                        </>
                      ) : (
                        <span>
                          <Plus size={11} /> No narration — upload a track or
                          generate a voice
                        </span>
                      )}
                    </div>
                      <button
                        className={`audio-lane music-lane ${music ? "has-audio" : ""}`}
                        onClick={() => {
                          if (!selected) return;
                          setSelectedTrack({ kind: "music", sceneId: selected.id });
                        }}
                      >
                        {music ? (
                          <>
                            <Wave values={music.waveform} color="#c4ae7e" />
                            <span className="audio-lane-label">
                              <Music2 size={10} />
                              {music.name}
                            </span>
                          </>
                        ) : (
                          <span>
                            <Plus size={11} /> Add licensed background music
                          </span>
                        )}
                      </button>
                    {duration > 0 && (
                      <div
                        className="playhead"
                        style={{ left: `${(time / duration) * 100}%` }}
                      >
                        <span />
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="timeline-footer">
                <span>
                  <span className="tiny-dot amber" />
                  {voice
                    ? "Review the timing and mix before final export."
                    : project.episode?.timings
                      ? "Imported clock active; upload the exact matching narration."
                      : "Timing estimated at 145 wpm. Add narration for a complete draft."}
                </span>
                <span>
                  Space to play / pause <kbd>␣</kbd>
                </span>
              </div>
            </section>
          </div>
        )}

        {tab === "research" && (
          <main className="page research-page">
            <div className="page-heading">
              <div>
                <div className="eyebrow">01 / THE RESEARCH DESK</div>
                <h2>Start with the facts.</h2>
                <p>
                  Trace the record. Separate what is known from what is claimed.
                </p>
              </div>
              <Button icon={Plus} onClick={() => setModal("source")}>
                Add a source
              </Button>
            </div>
            {project.is_demo && (
              <div className="notice">
                <Info size={17} />
                <div>
                  <b>This is a fictional production study.</b> No real case
                  research is included. Create a new project to investigate a
                  topic.
                </div>
                <Button onClick={() => setModal("new")}>
                  New project <ArrowUpRight size={13} />
                </Button>
              </div>
            )}
            <div className="research-search-card">
              <label className="eyebrow" htmlFor="topic">
                CASE NAME OR TOPIC
              </label>
              <div className="case-search">
                <Search size={20} />
                <input
                  id="topic"
                  value={project.topic}
                  onChange={(e) => queueSave({ topic: e.target.value })}
                  placeholder="Case name, location, and any identifying context…"
                />
                <Button
                  kind="primary"
                  icon={Sparkles}
                  disabled={locked || project.is_demo}
                  onClick={() =>
                    startOperation(`/api/projects/${project.id}/research`)
                  }
                >
                  Research case
                </Button>
              </div>
              <p>
                <LockKeyhole size={12} /> Web research requires an AI
                connection. Results are source leads, not verified case facts.
              </p>
            </div>
            <div className="research-grid">
              <section className="content-card source-card">
                <div className="card-heading">
                  <h3>
                    <BookOpen size={16} /> Source library{" "}
                    <Badge>{project.sources.length}</Badge>
                  </h3>
                  <span>
                    {project.sources.filter((s) => s.reviewed).length} reviewed
                  </span>
                </div>
                {project.sources.length ? (
                  <div className="sources">
                    {project.sources.map((s) => (
                      <div className="source" key={s.id}>
                        <div className="source-top">
                          <Badge tone="source">{s.id}</Badge>
                          <span>{s.type}</span>
                          <button
                            className={`source-check ${s.reviewed ? "checked" : ""}`}
                            title="Mark as producer-reviewed"
                            onClick={() =>
                              setSource(s, { reviewed: !s.reviewed })
                            }
                          >
                            {s.reviewed ? (
                              <CheckCircle2 size={13} />
                            ) : (
                              <Circle size={13} />
                            )}{" "}
                            {s.reviewed ? "Reviewed" : "Needs review"}
                          </button>
                        </div>
                        <h4>
                          {s.url ? (
                            <a
                              href={s.url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              {s.title}
                              <ExternalLink size={12} />
                            </a>
                          ) : (
                            s.title
                          )}
                        </h4>
                        {s.url && (
                          <span className="source-domain">
                            {new URL(s.url).hostname}
                          </span>
                        )}
                        <label className="field">
                          Producer-verified notes
                          <textarea
                            key={s.id + "-" + s.reviewed}
                            defaultValue={s.notes}
                            placeholder="Record the facts you checked, dates, and relevant quotations…"
                            rows="3"
                            onBlur={(e) => {
                              if (e.target.value !== s.notes)
                                setSource(s, { notes: e.target.value });
                            }}
                          />
                        </label>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty icon={BookOpen} title="A story needs a source trail">
                    Add records, reporting, or interview notes. Review the
                    original before marking it verified.
                    <Button icon={Plus} onClick={() => setModal("source")}>
                      Add your first source
                    </Button>
                  </Empty>
                )}
              </section>
              <section className="content-card">
                <div className="card-heading">
                  <h3>
                    <FileText size={16} /> Research brief
                  </h3>
                  <Badge tone="amber">DRAFT</Badge>
                </div>
                {project.research_report ? (
                  <div className="research-report">
                    {project.research_report}
                  </div>
                ) : (
                  <Empty icon={Search} title="The brief comes next">
                    Research a case to collect a sourced chronology, legal
                    status, and questions to investigate.
                  </Empty>
                )}
                <div className="card-footer">
                  <Button
                    icon={Sparkles}
                    disabled={locked}
                    onClick={() => {
                      setTab("script");
                      startOperation(`/api/projects/${project.id}/draft`);
                    }}
                  >
                    Draft from reviewed sources
                  </Button>
                  <a
                    className="text-link"
                    href={`/api/projects/${project.id}/sources.md`}
                    download
                  >
                    <Download size={12} /> Export notes
                  </a>
                </div>
              </section>
            </div>
          </main>
        )}

        {tab === "script" && (
          <main className="page script-page">
            <div className="page-heading">
              <div>
                <div className="eyebrow">02 / THE STORY</div>
                <h2>Give the record a voice.</h2>
                <p>
                  A measured opening. A clear chronology. Room for the facts.
                </p>
              </div>
              <div className="page-actions">
                <Button icon={Upload} onClick={() => fileRef.current.click()}>
                  Import script
                </Button>
                <Button
                  kind="primary"
                  icon={Clapperboard}
                  disabled={locked || !project.script.trim()}
                  onClick={doAssemble}
                >
                  Build timeline
                </Button>
              </div>
            </div>
            {project.script_origin === "ai" &&
              !project.script_approved_hash && (
                <div className="script-approval-notice">
                  <ShieldCheck size={19} />
                  <div>
                    <b>AI-written draft: producer review required</b>
                    <p>
                      Read the narration against its cited sources, resolve
                      unverified details, and approve the text before generating
                      a voice.
                    </p>
                  </div>
                  <Button
                    icon={CheckCircle2}
                    kind="primary"
                    disabled={locked}
                    onClick={approveScript}
                  >
                    Approve for narration
                  </Button>
                </div>
              )}
            {project.script_origin === "ai" &&
              !!project.script_approved_hash && (
                <div className="script-approved-tag">
                  <CheckCircle2 size={13} /> Producer-approved for narration ·
                  Final factual and rights checks still apply
                </div>
              )}
            {project.script_dirty && (
              <div className="notice">
                <Info size={15} />
                <span>
                  Your script has unapplied changes. Build the timeline to apply
                  them; the existing edit is unchanged until then.
                </span>
              </div>
            )}
            <div className="script-layout">
              <section className="script-editor content-card">
                <div className="script-document-header">
                  <div>
                    <FileText size={16} />
                    <strong>Narration script</strong>
                    <Badge>EDITABLE</Badge>
                  </div>
                  <span>Blank lines separate scenes</span>
                </div>
                <textarea
                  aria-label="Documentary narration script"
                  className="script-textarea"
                  placeholder={
                    "Paste your script here…\n\nUse blank lines between paragraphs. Each paragraph becomes an editable scene.\n\nOr research a case and draft from reviewed sources."
                  }
                  value={project.script}
                  onChange={(e) => queueSave({ script: e.target.value })}
                  spellCheck
                />
                <div className="script-footer">
                  <span>
                    {wc(clean(project.script)).toLocaleString()} spoken words
                  </span>
                  <span>
                    <Clock3 size={12} />
                    {tc((wc(clean(project.script)) / 145) * 60)} estimated
                    voice-over
                  </span>
                  <span>{project.target_minutes} min target</span>
                </div>
              </section>
              <aside className="script-side">
                <div className="content-card script-guide">
                  <div className="mini-icon">
                    <Sparkles size={19} />
                  </div>
                  <h3>From script to first cut.</h3>
                  <p>
                    Build a scene sequence, then add footage and a voice track.
                    You keep control of every cut.
                  </p>
                  <ol>
                    <li>
                      <span>1</span>Write or paste your narration
                    </li>
                    <li>
                      <span>2</span>Import licensed visuals
                    </li>
                    <li>
                      <span>3</span>Build and review the timeline
                    </li>
                    <li>
                      <span>4</span>Record or generate a voice
                    </li>
                  </ol>
                  <Button
                    className="full"
                    icon={Sparkles}
                    disabled={locked}
                    onClick={() =>
                      startOperation(`/api/projects/${project.id}/draft`)
                    }
                  >
                    Draft from reviewed sources
                  </Button>
                  <small>
                    <LockKeyhole size={11} /> AI connection required
                  </small>
                </div>
                <div className="content-card script-stat">
                  <span className="eyebrow">EPISODE LENGTH</span>
                  <strong>{tc((wc(clean(project.script)) / 145) * 60)}</strong>
                  <p>
                    Based on 145 spoken words per minute. Actual length follows
                    the recorded voice.
                  </p>
                  <label className="field">
                    Target duration
                    <select
                      value={project.target_minutes}
                      onChange={(e) =>
                        queueSave({ target_minutes: Number(e.target.value) })
                      }
                    >
                      {[20, 25, 30, 35, 40].map((n) => (
                        <option key={n} value={n}>
                          {n} minutes · ~{(n * 145).toLocaleString()} words
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                {project.script.includes("[NEEDS SOURCE]") && (
                  <div className="notice warning">
                    <AlertTriangle size={16} />
                    <span>
                      This draft contains claims marked NEEDS SOURCE. Resolve
                      them before recording or publication.
                    </span>
                  </div>
                )}
              </aside>
            </div>
          </main>
        )}

        {tab === "review" && (
          <main className="page review-page">
            <div className="page-heading">
              <div>
                <div className="eyebrow">
                  {project.episode?.guide
                    ? "YOUR DRAFT VIDEO"
                    : "04 / THE FINAL CUT"}
                </div>
                <h2>
                  {project.episode?.guide
                    ? "Watch it. Save it. Then finish."
                    : "A final check. Then, the world."}
                </h2>
                <p>
                  Editorial care is part of the production—not an optional
                  extra.
                </p>
              </div>
              <div className="page-actions">
                <Button
                  icon={ShieldCheck}
                  onClick={() => openTool("preflight")}
                >
                  Preflight checks
                </Button>
                <Button
                  kind="primary"
                  icon={Download}
                  disabled={locked || !scenes.length}
                  onClick={() =>
                    project.episode?.guide
                      ? makeFirstDraft({ render: true })
                      : openTool("export")
                  }
                >
                  {project.episode?.guide
                    ? "Make updated draft video"
                    : "Render video"}
                </Button>
              </div>
            </div>
            <details
              className="advanced-publication"
              open={!project.episode?.guide}
            >
              <summary>
                Advanced: final publication checks and session cleanup
              </summary>
              <div className="review-grid">
                <section className="content-card checklist-card">
                  <div className="card-heading">
                    <h3>
                      <ShieldCheck size={17} /> Editorial review
                    </h3>
                    <Badge
                      tone={
                        Object.values(project.review).every(Boolean)
                          ? "green"
                          : ""
                      }
                    >
                      {Object.values(project.review).filter(Boolean).length} / 4
                      complete
                    </Badge>
                  </div>
                  {[
                    [
                      "facts",
                      "Facts & allegations",
                      "I checked names, dates, quotations, legal status, and the distinction between allegations and established facts.",
                    ],
                    [
                      "rights",
                      "Media & music rights",
                      "I have permission to use the footage, images, recordings, and music in this production.",
                    ],
                    [
                      "disclosure",
                      "Disclosure & context",
                      "AI narration and illustrative or reconstructed visuals are disclosed, and none is presented as authentic evidence.",
                    ],
                    [
                      "picture",
                      "Picture, sound & pacing",
                      "I watched the full edit, checked captions and transitions, and listened to the narration and music.",
                    ],
                  ].map(([key, title, description]) => (
                    <button
                      className={`review-check ${project.review[key] ? "checked" : ""}`}
                      key={key}
                      onClick={() =>
                        queueSave({
                          review: {
                            ...project.review,
                            [key]: !project.review[key],
                          },
                        })
                      }
                    >
                      <span className="check-box">
                        {project.review[key] && <Check size={14} />}
                      </span>
                      <span>
                        <b>{title}</b>
                        <p>{description}</p>
                      </span>
                    </button>
                  ))}
                  {project.episode?.plan?.mode === "inspection" && (
                    <p className="inspection-final-help">
                      These are final-publication sign-offs. You may leave all
                      four unticked while viewing/rendering an inspection draft.
                      They do not import footage or perform editing for you.
                    </p>
                  )}
                  <div className="checklist-note">
                    <Info size={14} /> These are producer attestations, not
                    independent factual verification or legal clearance.
                  </div>
                </section>
                <div className="review-summary">
                  <div
                    className="export-preview"
                    style={{
                      backgroundImage:
                        assets.find((a) => a.thumbnail)?.thumbnail ||
                        project.is_demo
                          ? `linear-gradient(0deg,rgba(11,15,18,.95),rgba(11,15,18,.05)),url("${assets.find((a) => a.thumbnail)?.thumbnail || "/assets/blackwater-road.jpg"}")`
                          : "linear-gradient(130deg,#26313a,#14191e)",
                    }}
                  >
                    <Badge>
                      {project.is_demo
                        ? "FICTIONAL SAMPLE"
                        : "YOUR DOCUMENTARY"}
                    </Badge>
                    <div>
                      <h3>{project.title}</h3>
                      <p>
                        {tc(duration)} <span>·</span> {scenes.length} scenes{" "}
                        <span>·</span> 16:9
                      </p>
                    </div>
                  </div>
                  <div className="content-card readiness">
                    <div>
                      <span>Visuals assigned</span>
                      <b>
                        {scenes.filter((s) => s.asset_id).length} /{" "}
                        {scenes.length}
                      </b>
                    </div>
                    <div>
                      <span>Narration</span>
                      <b className={!voice ? "text-amber" : ""}>
                        {voice
                          ? voice.generated
                            ? "AI voice assigned"
                            : "Recorded voice assigned"
                          : "Not assigned"}
                      </b>
                    </div>
                    <div>
                      <span>Sources reviewed</span>
                      <b>
                        {project.sources.filter((s) => s.reviewed).length} /{" "}
                        {project.sources.length}
                      </b>
                    </div>
                    <div>
                      <span>Engine</span>
                      <b>H.264 · AAC · 24 fps</b>
                    </div>
                  </div>
                  {!project.is_demo && (
                    <details className="session-cleanup">
                      <summary>
                        Clear temporary session after saving your downloads
                      </summary>
                      <p>
                        This removes this project's uploaded copies, jobs,
                        rendered files and project record from this server. It
                        does not delete originals on your computer. A download
                        click alone is not proof that a file was saved.
                      </p>
                      <label className="ep-checkbox">
                        <input
                          type="checkbox"
                          aria-label="I saved my output before clearing"
                          checked={savedBeforeClear}
                          onChange={(ev) =>
                            setSavedBeforeClear(ev.target.checked)
                          }
                        />
                        <span>
                          I have saved and checked the output/backups I need on
                          my computer.
                        </span>
                      </label>
                      <button
                        className="btn"
                        aria-label="Clear this temporary session"
                        disabled={locked || !savedBeforeClear}
                        onClick={async () => {
                          setBusy(true);
                          try {
                            await flushSave();
                            await api(
                              `/api/projects/${project.id}/session`,
                              "DELETE",
                              { confirm_download_saved: true },
                            );
                            pending.current = {};
                            await forgetSetup(project.id).catch(() => {});
                            await clearWorkingFiles(project.id).catch(() => {});
                            window.location.reload();
                          } catch (error) {
                            report(error);
                            setBusy(false);
                          }
                        }}
                      >
                        <Trash2 size={13} /> Clear this session's uploaded
                        copies and exports
                      </button>
                    </details>
                  )}
                  <div className="review-downloads">
                    <a
                      href="#project-backup"
                      aria-label="Save project backup"
                      onClick={(ev) => {
                        ev.preventDefault();
                        downloadProjectSnapshot(project, setDownloadGate);
                      }}
                    >
                      Save project backup (no server needed)
                    </a>
                    <a
                      href={`/api/projects/${project.id}/chapters.txt`}
                      download
                    >
                      <Clapperboard size={14} /> Chapters <Download size={12} />
                    </a>
                    <a
                      href={`/api/projects/${project.id}/captions.srt`}
                      download
                    >
                      <FileText size={14} /> Captions .srt{" "}
                      <Download size={12} />
                    </a>
                    <a href={`/api/projects/${project.id}/sources.md`} download>
                      <BookOpen size={14} /> Source notes <Download size={12} />
                    </a>
                    <a
                      href="#project-backup"
                      onClick={(ev) => {
                        ev.preventDefault();
                        downloadProjectSnapshot(project, setDownloadGate);
                      }}
                    >
                      <FileJson size={14} /> Project .json{" "}
                      <Download size={12} />
                    </a>
                  </div>
                </div>
              </div>
            </details>
            <section className="content-card exports-card">
              <div className="card-heading">
                <h3>
                  <Film size={17} /> Export history{" "}
                  <Badge>{project.exports.length}</Badge>
                </h3>
                <span>Real rendered files, ready to download</span>
              </div>
              {project.exports[0] && (
                <div className="rendered-preview">
                  <b>
                    {project.exports[0].inspection_only
                      ? "UNREVIEWED INSPECTION · "
                      : ""}
                    Watch the rendered video before downloading
                  </b>
                  <div className="rendered-preview-actions">
                    <button
                      className="btn"
                      aria-label="Play rendered video"
                      onClick={(ev) =>
                        ev.currentTarget
                          .closest(".rendered-preview")
                          .querySelector("video")
                          .play()
                          .catch(report)
                      }
                    >
                      <Play size={13} /> Play rendered video
                    </button>
                    <button
                      className="btn"
                      aria-label="Pause rendered video"
                      onClick={(ev) =>
                        ev.currentTarget
                          .closest(".rendered-preview")
                          .querySelector("video")
                          .pause()
                      }
                    >
                      <Pause size={13} /> Pause
                    </button>
                  </div>
                  <video
                    aria-label="Rendered video preview"
                    src={project.exports[0].url}
                    controls
                    playsInline
                    preload="metadata"
                  />
                  <p>
                    This is the encoded MP4, not just the timeline simulation.
                    Save the file to your computer before clearing this session.
                  </p>
                </div>
              )}
              {project.exports.length ? (
                <div className="export-list">
                  {project.exports.map((ex) => (
                    <div className="export-row" key={ex.id}>
                      <div className="export-file-icon">
                        <Film size={20} />
                      </div>
                      <div>
                        <h4>
                          {ex.title}.mp4{" "}
                          <Badge tone={ex.draft ? "amber" : "green"}>
                            {ex.inspection_only
                              ? "UNREVIEWED INSPECTION"
                              : ex.draft
                                ? "DRAFT"
                                : "FINAL"}
                          </Badge>
                        </h4>
                        <p>
                          {ex.resolution} · {tc(ex.duration)} · {bytes(ex.size)}{" "}
                          · {ex.audio ? "Audio included" : "Silent video"} ·{" "}
                          {elapsed(ex.created_at)}
                        </p>
                        {ex.preflight_url && (
                          <div className="export-companion-links">
                            <a href={ex.preflight_url} download>
                              Preflight report
                            </a>
                            <a href={ex.chapters_url} download>
                              Chapter draft
                            </a>
                            <a href={ex.publication_url} download>
                              Publication notes
                            </a>
                            {ex.episode_plan_url && (
                              <a href={ex.episode_plan_url} download>
                                Frozen episode plan
                              </a>
                            )}
                          </div>
                        )}
                      </div>
                      <a
                        className="btn"
                        onClick={(ev) => {
                          if (window.top !== window) {
                            ev.preventDefault();
                            setDownloadGate({
                              kind: "video",
                              url: new URL(
                                `/api/projects/${project.id}/exports/${ex.id}/download`,
                                window.location.origin,
                              ).href,
                            });
                          }
                        }}
                        href={`/api/projects/${project.id}/exports/${ex.id}/download`}
                        download={`${project.title.replace(/[^a-z0-9 -]/gi, "")}${ex.inspection_only ? "-unreviewed-inspection" : ""}.mp4`}
                      >
                        <Download size={14} /> Download
                      </a>
                      <details className="download-help">
                        <summary>Download not starting?</summary>
                        <p>
                          The preview frame may restrict downloads. Copy this
                          direct link and paste it into a new browser tab to
                          save the finished MP4. It does not start another
                          render.
                        </p>
                        <input
                          aria-label={`Direct MP4 download link ${ex.id}`}
                          readOnly
                          value={
                            new URL(
                              `/api/projects/${project.id}/exports/${ex.id}/download`,
                              window.location.origin,
                            ).href
                          }
                          onFocus={(ev) => ev.target.select()}
                        />
                        <a
                          href={`/api/projects/${project.id}/exports/${ex.id}/download`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          Open download outside the preview
                        </a>
                      </details>
                      <a
                        className="icon-btn"
                        href={ex.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Open rendered video"
                      >
                        <ExternalLink size={15} />
                      </a>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="exports-empty">
                  <Film size={24} />
                  <div>
                    <h4>Your first export belongs here.</h4>
                    <p>
                      Render a review draft at any point. Final exports require
                      the editorial checks.
                    </p>
                  </div>
                  <Button
                    icon={Download}
                    disabled={locked || !scenes.length}
                    onClick={() => openTool("export")}
                  >
                    Render a draft
                  </Button>
                </div>
              )}
            </section>
            {project.episode?.guide && project.exports.length > 0 && (
              <details className="simple-finish">
                <summary>
                  Finished downloading? Clear this temporary session.
                </summary>
                <p>
                  Only do this after saving and opening the output you need.
                  This deletes this session's server copies and browser setup
                  cache, not originals on your computer.
                </p>
                <label className="ep-checkbox">
                  <input
                    type="checkbox"
                    aria-label="Quick confirm downloads saved"
                    checked={savedBeforeClear}
                    onChange={(ev) => setSavedBeforeClear(ev.target.checked)}
                  />
                  <span>I saved and checked my downloads.</span>
                </label>
                <button
                  className="btn"
                  aria-label="Finish and clear session"
                  disabled={locked || !savedBeforeClear}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await flushSave();
                      await api(
                        `/api/projects/${project.id}/session`,
                        "DELETE",
                        { confirm_download_saved: true },
                      );
                      pending.current = {};
                      await forgetSetup(project.id).catch(() => {});
                      await clearWorkingFiles(project.id).catch(() => {});
                      window.location.reload();
                    } catch (error) {
                      report(error);
                      setBusy(false);
                    }
                  }}
                >
                  Clear this session
                </button>
              </details>
            )}
          </main>
        )}
      </div>
      {voice && <audio ref={audioRef} src={voice.url} preload="metadata" />}
      {music && (
        <audio ref={musicRef} src={music.url} preload="metadata" loop />
      )}
      <input
        ref={fileRef}
        type="file"
        hidden
        multiple
        accept=".png,.jpg,.jpeg,.webp,.mp4,.mov,.webm,.mkv,.mp3,.wav,.m4a,.aac,.ogg,.flac,.txt,.md"
        onChange={(e) => uploadFiles(e.target.files)}
      />
      {activeJob && (
        <div className="job-card">
          <div className="job-card-title">
            <LoaderCircle size={15} className="spin" />
            <b>
              {{
                render: "Rendering video",
                research: "Researching case",
                script: "Drafting script",
                narration: "Generating narration",
                transcription: "Transcribing audio",
                direction: "Applying direction",
                production: "Producing review draft",
              }[activeJob.kind] || "Working"}
            </b>
            <span>{activeJob.progress}%</span>
            <IconButton
              icon={X}
              label="Cancel current operation"
              onClick={async () => {
                try {
                  await api(`/api/jobs/${activeJob.id}/cancel`, "POST", {});
                  notify("Cancellation requested.", "info");
                } catch (e) {
                  report(e);
                }
              }}
            />
          </div>
          <div className="progress-track">
            <div style={{ width: activeJob.progress + "%" }} />
          </div>
          <p>{activeJob.message}</p>
        </div>
      )}
      {toast && (
        <div role="status" className={`toast ${toast.tone}`}>
          {toast.tone === "error" ? (
            <AlertTriangle size={17} />
          ) : toast.tone === "info" ? (
            <Info size={17} />
          ) : (
            <CheckCircle2 size={17} />
          )}
          <span>{toast.message}</span>
          <button
            aria-label="Dismiss notification"
            onClick={() => setToast(null)}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {modal === "new" && (
        <NewProjectModal
          onClose={() => setModal(null)}
          onCreate={async (data) => {
            try {
              await flushSave();
              const p = await api("/api/projects", "POST", data);
              pending.current = {};
              acceptProject(p);
              setTime(0);
              setSelectedId(null);
              setJobs([]);
              setModal(null);
              setTab(
                data.mode === "narration"
                  ? "setup"
                  : data.mode === "topic"
                    ? "research"
                    : data.mode === "script"
                      ? "script"
                      : "edit",
              );
              if (data.mode === "footage")
                setTimeout(() => setModal("media"), 50);
              notify("Project created. Start with your source material.");
            } catch (e) {
              report(e);
            }
          }}
        />
      )}
      {modal === "projects" && (
        <Modal
          title="Your documentaries"
          eyebrow="THE WORKSPACE"
          onClose={() => setModal(null)}
        >
          <div className="project-list-modal">
            {projectList.map((p) => (
              <button
                key={p.id}
                className={p.id === project.id ? "selected" : ""}
                onClick={() => openProject(p.id)}
              >
                <div className="project-folder">
                  <Clapperboard size={20} />
                </div>
                <span>
                  <b>{p.title}</b>
                  <small>
                    {p.is_demo
                      ? "Fictional sample"
                      : `${p.target_minutes} min target`}{" "}
                    · {elapsed(p.updated_at)}
                  </small>
                </span>
                {p.id === project.id ? (
                  <Check size={16} />
                ) : (
                  <ChevronRight size={16} />
                )}
              </button>
            ))}
          </div>
          <div className="modal-footer">
            <span>Projects are saved to this workspace.</span>
            <Button kind="primary" icon={Plus} onClick={() => setModal("new")}>
              New project
            </Button>
          </div>
        </Modal>
      )}
      {modal === "settings" && (
        <SettingsModal
          config={config}
          onClose={() => setModal(null)}
          onSaved={(c) => {
            setConfig(c);
            setModal(null);
            notify(
              c.connected
                ? "AI service connected. Provider usage charges may apply."
                : "AI service disconnected.",
            );
          }}
          onError={report}
        />
      )}
      {modal === "media" && (
        <Modal
          title="Your media library"
          eyebrow="THE MATERIAL"
          wide
          className="media-modal"
          onClose={() => setModal(null)}
        >
          <div className="media-modal-toolbar">
            <p>
              {assets.length} assets <span>·</span> Images, footage, voice &
              music
            </p>
            <Button
              kind="primary"
              icon={uploading ? LoaderCircle : Upload}
              disabled={uploading}
              onClick={() => fileRef.current.click()}
            >
              {uploading ? "Importing…" : "Import media"}
            </Button>
          </div>
          <div className="media-privacy">
            <LockKeyhole size={12} />
            <span>
              Shared prototype workspace · no user authentication. Use only
              non-sensitive test media.
            </span>
          </div>
          <div className="media-modal-body">
            <div
              className="media-grid"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                uploadFiles(e.dataTransfer.files);
              }}
            >
              <p className="media-upload-limits">
                Media limit: {uploadLimits}. TXT/Markdown imports: 1 MB.
              </p>
              {!assets.length && (
                <div
                  className="dropzone"
                  onClick={() => fileRef.current.click()}
                >
                  <Upload size={28} />
                  <h3>Bring your story material.</h3>
                  <p>Drop images, video, audio, or a TXT script here.</p>
                  <small>Up to 512 MB per file · 30 files per batch</small>
                </div>
              )}
              {assets.map((a) => (
                <button
                  className={`media-card ${mediaId === a.id ? "selected" : ""}`}
                  key={a.id}
                  onClick={() => setMediaId(a.id)}
                >
                  <div className="media-card-image">
                    {a.thumbnail ? (
                      <img src={a.thumbnail} alt="" />
                    ) : (
                      <div>
                        <AudioLines size={32} />
                        {a.waveform && <Wave values={a.waveform} />}
                      </div>
                    )}
                    <Badge>
                      {a.kind === "video" ? (
                        <Film size={10} />
                      ) : a.kind === "audio" ? (
                        <AudioLines size={10} />
                      ) : (
                        <ImageIcon size={10} />
                      )}{" "}
                      {a.duration ? tc(a.duration) : "IMAGE"}
                    </Badge>
                    {a.generated && (
                      <span className="ai-asset">
                        <Sparkles size={10} /> AI
                      </span>
                    )}
                  </div>
                  <strong>{a.name}</strong>
                  <small>
                    {bytes(a.size)} {a.width ? `· ${a.width}×${a.height}` : ""}
                  </small>
                </button>
              ))}
            </div>
            <div className="media-detail">
              {(() => {
                const a = assets.find((a) => a.id === mediaId);
                if (!a)
                  return (
                    <Empty icon={Layers} title="Select an asset">
                      Assign visuals, choose a voice track, or document usage
                      rights.
                    </Empty>
                  );
                return (
                  <>
                    <div className="section-label">ASSET DETAILS</div>
                    <h3>{a.name}</h3>
                    <Badge>
                      {a.generated ? "AI-GENERATED" : a.kind.toUpperCase()}
                    </Badge>
                    {a.kind === "video" && (
                      <video src={a.url} controls playsInline />
                    )}
                    {a.kind === "audio" && <audio src={a.url} controls />}
                    {a.kind === "image" && (
                      <img className="detail-image" src={a.url} alt={a.name} />
                    )}
                    <label className="field">
                      Rights & attribution notes
                      <textarea
                        key={a.id}
                        defaultValue={a.license}
                        rows="4"
                        placeholder="Owner, license, permission, and required credit…"
                        onBlur={async (e) => {
                          if (e.target.value === a.license) return;
                          try {
                            await flushSave();
                            acceptProject(
                              await api(
                                `/api/projects/${project.id}/assets/${a.id}`,
                                "PATCH",
                                { license: e.target.value },
                              ),
                            );
                          } catch (e) {
                            report(e);
                          }
                        }}
                      />
                    </label>
                    {["image", "video"].includes(a.kind) && (
                      <Button
                        className="full"
                        kind="primary"
                        icon={Check}
                        disabled={!selected}
                        onClick={() => {
                          updateScene({
                            asset_id: a.id,
                            motion: a.kind === "video" ? "none" : "slow-zoom",
                          });
                          notify("Visual assigned to the selected scene.");
                          setModal(null);
                        }}
                      >
                        Use in selected scene
                      </Button>
                    )}
                    {(a.has_audio || a.kind === "audio") && (
                      <>
                        <Button
                          className="full"
                          icon={Mic}
                          onClick={() => {
                            queueSave({ narration_id: a.id });
                            notify(
                              "Narration track assigned. Check alignment in the timeline.",
                            );
                          }}
                        >
                          Use as narration
                        </Button>
                        <Button
                          className="full"
                          icon={Music2}
                          onClick={() => {
                            queueSave({ music_id: a.id });
                            notify("Background music assigned.");
                          }}
                        >
                          Use as music
                        </Button>
                        <Button
                          className="full"
                          icon={Sparkles}
                          disabled={locked}
                          onClick={() => transcribeAsset(a)}
                        >
                          Transcribe & assemble
                        </Button>
                        <p className="micro-note block">
                          Transcription sends audio to your connected AI service
                          and replaces the current timeline.
                        </p>
                      </>
                    )}
                    <button
                      className="danger-link"
                      onClick={async () => {
                        if (
                          !window.confirm(
                            "Remove this asset from the project? Existing rendered exports are not changed.",
                          )
                        )
                          return;
                        try {
                          await flushSave();
                          acceptProject(
                            await api(
                              `/api/projects/${project.id}/assets/${a.id}`,
                              "DELETE",
                            ),
                          );
                          setMediaId(null);
                        } catch (e) {
                          report(e);
                        }
                      }}
                    >
                      <Trash2 size={12} /> Remove from project
                    </button>
                  </>
                );
              })()}
            </div>
          </div>
        </Modal>
      )}
      {modal === "source" && (
        <SourceModal
          onClose={() => setModal(null)}
          onSave={async (data) => {
            try {
              await flushSave();
              acceptProject(
                await api(`/api/projects/${project.id}/sources`, "POST", data),
              );
              setModal(null);
              notify(
                "Source added. Open the original and record verified notes.",
              );
            } catch (e) {
              report(e);
            }
          }}
        />
      )}
      {modal === "narrate" && (
        <Modal
          title="Give your script a voice."
          eyebrow="AI NARRATION"
          onClose={() => setModal(null)}
        >
          <div className="modal-body">
            <div className="narrate-icon">
              <AudioLines size={32} />
            </div>
            <p className="modal-lead">
              Generate narration for <b>{scenes.length} scenes</b> using the{" "}
              <b>{config.voice}</b> voice. Scene lengths will follow the
              generated audio.
            </p>
            <div className="info-grid">
              <div>
                <span>Spoken words</span>
                <b>
                  {wc(
                    scenes.map((s) => s.narration).join(" "),
                  ).toLocaleString()}
                </b>
              </div>
              <div>
                <span>Estimated duration</span>
                <b>
                  {tc(
                    (wc(scenes.map((s) => s.narration).join(" ")) / 145) * 60,
                  )}
                </b>
              </div>
            </div>
            <div className="notice warning">
              <AlertTriangle size={16} />
              <span>
                Your script is sent to the connected AI provider. Usage charges
                apply. The voice is synthetic; disclose it to viewers.
              </span>
            </div>
            <p className="micro-note block">
              Review the script before generation. This creates new audio and
              replaces the assigned narration. Change the model or voice in
              Settings.
            </p>
          </div>
          <div className="modal-footer">
            <Button onClick={() => setModal("settings")}>Voice settings</Button>
            <Button
              kind="primary"
              icon={Sparkles}
              disabled={locked}
              onClick={() => {
                setModal(null);
                startOperation(`/api/projects/${project.id}/narrate`);
              }}
            >
              Generate narration
            </Button>
          </div>
        </Modal>
      )}
      {modal === "production" && (
        <ProductionModal
          project={project}
          config={config}
          jobs={jobs}
          api={api}
          onClose={() => setModal(null)}
          onRun={runProduction}
          onNavigate={navigateTool}
          onError={report}
          onConnect={() => setModal("settings")}
        />
      )}
      {modal === "preflight" && (
        <PreflightModal
          project={project}
          api={api}
          onClose={() => setModal(null)}
          onNavigate={navigateTool}
          onError={report}
        />
      )}
      {downloadGate && (
        <Modal
          title="This preview frame blocks saving files"
          eyebrow="VIDEO READY — BROWSER RESTRICTION"
          onClose={() => setDownloadGate(null)}
        >
          <div className="modal-body">
            <p>
              The review checkboxes are not the problem. This embedded frame is
              not allowed to download files or open a new tab itself.
            </p>
            <p>
              <b>
                Copy the address below, open a normal browser tab, paste it in
                the address bar and press Enter.
              </b>{" "}
              {downloadGate.kind === "video"
                ? "It saves the existing MP4; no new render is started."
                : "It opens the full editor where Save backup can download normally."}
            </p>
            <input
              aria-label="Outside preview save address"
              className="outside-save-address"
              readOnly
              value={downloadGate.url}
              onFocus={(ev) => ev.target.select()}
            />
            <p>
              Your files are not deleted by opening this address. Finish-session
              cleanup still needs your confirmation.
            </p>
          </div>
        </Modal>
      )}
      {modal === "export" && (
        <ExportModal
          project={project}
          voice={voice}
          locked={locked}
          onPreflight={() => setModal("preflight")}
          onClose={() => setModal(null)}
          onExport={startRender}
        />
      )}
      {modal === "inspector" && (
        <Modal
          title="Your scene controls"
          onClose={() => setModal(null)}
          className="inspector-modal"
        >
          {renderInspector()}
        </Modal>
      )}
      {modal === "help" && (
        <Modal
          title="A thoughtful first cut."
          eyebrow="WELCOME TO CASEFILE"
          onClose={() => setModal(null)}
        >
          <div className="modal-body help-content">
            <p className="modal-lead">
              A working documentary editing prototype, built around your 20–40
              minute true-crime workflow.
            </p>
            <div>
              <FolderOpen size={18} />
              <section>
                <h3>Already have narration and an editing guide?</h3>
                <p>
                  Open Episode setup. Keep the finished voice, background music,
                  narration script, and footage guide in separate cards. Link
                  actual authorized source files to the guide's IDs, review the
                  exact clip windows and Care rules, then preview the plan. A
                  source URL is not footage or permission. No AI key is needed
                  for this path.
                </p>
                <button
                  className="btn"
                  onClick={() => {
                    setModal(null);
                    setPlaying(false);
                    setTab("setup");
                  }}
                >
                  Open Episode setup <ArrowUpRight size={12} />
                </button>
              </section>
            </div>
            <div>
              <Clapperboard size={18} />
              <section>
                <h3>Works without an AI key</h3>
                <p>
                  Saved projects, script-to-scene assembly, uploads, scene
                  controls, local text commands, captions, source notes, and
                  real FFmpeg video exports.
                </p>
              </section>
            </div>
            <div>
              <Sparkles size={18} />
              <section>
                <h3>Connect for AI production</h3>
                <p>
                  Web research with source leads, script drafts, synthetic
                  narration, audio transcription, and creative editing
                  instructions use a separately billed API key.
                </p>
              </section>
            </div>
            <div>
              <ShieldCheck size={18} />
              <section>
                <h3>The producer stays in control</h3>
                <p>
                  Review case facts, allegations, rights, captions, and pacing.
                  This app does not independently verify facts, obtain footage
                  licenses, or guarantee publication-ready results.
                </p>
              </section>
            </div>
            <div className="notice warning">
              <LockKeyhole size={16} />
              <span>
                Prototype: one shared workspace, without user authentication. Do
                not upload confidential evidence or sensitive personal files.
                Production deployment needs access controls, private storage,
                and a managed render queue.
              </span>
            </div>
          </div>
          <div className="modal-footer">
            <span>Space = play / pause · Edits save automatically</span>
            <Button kind="primary" onClick={() => setModal(null)}>
              Back to the story <ArrowUpRight size={13} />
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function NewProjectModal({ onClose, onCreate }) {
  const [title, setTitle] = useState(""),
    [mode, setMode] = useState("topic"),
    [minutes, setMinutes] = useState(25),
    [busy, setBusy] = useState(false);
  return (
    <Modal
      title="Every story starts somewhere."
      eyebrow="NEW DOCUMENTARY"
      onClose={onClose}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await onCreate({ title, mode, target_minutes: minutes });
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="modal-body">
          <label className="field large">
            Case name or working title
            <input
              autoFocus
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What story are you telling?"
              maxLength="180"
            />
          </label>
          <label className="field">What are you starting with?</label>
          <div className="start-modes">
            {[
              ["topic", "A case or topic", "Research, then write", Search],
              ["script", "A finished script", "Narrate & assemble", FileText],
              ["narration", "Narration + media", "Build around the voice", Mic],
              ["footage", "Raw footage", "Transcribe & shape", Film],
            ].map(([id, label, desc, Icon]) => (
              <button
                type="button"
                key={id}
                className={mode === id ? "selected" : ""}
                onClick={() => setMode(id)}
              >
                <Icon size={19} />
                <strong>{label}</strong>
                <span>{desc}</span>
                {mode === id && (
                  <CheckCircle2 size={14} className="mode-check" />
                )}
              </button>
            ))}
          </div>
          <label className="field">
            Target episode length
            <select
              value={minutes}
              onChange={(e) => setMinutes(Number(e.target.value))}
            >
              {[20, 25, 30, 35, 40].map((n) => (
                <option key={n} value={n}>
                  {n} minutes
                </option>
              ))}
            </select>
          </label>
          <p className="micro-note block">
            <Info size={12} /> AI research, writing, narration, and
            transcription need a connected API key. Bring footage and music you
            have the right to use.
          </p>
        </div>
        <div className="modal-footer">
          <Button type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            kind="primary"
            icon={busy ? LoaderCircle : ArrowUpRight}
            disabled={!title.trim() || busy}
            type="submit"
          >
            Create project
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function SettingsModal({ config, onClose, onSaved, onError }) {
  const [key, setKey] = useState(""),
    [values, setValues] = useState({ ...config }),
    [busy, setBusy] = useState(false);
  const field = (id, label, placeholder) => (
    <label className="field">
      {label}
      <input
        value={values[id] || ""}
        placeholder={placeholder}
        onChange={(e) => setValues({ ...values, [id]: e.target.value })}
      />
    </label>
  );
  return (
    <Modal
      title="Your production connections."
      eyebrow="WORKSPACE SETTINGS"
      onClose={onClose}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            const r = await api("/api/config", "POST", { ...values, key });
            setKey("");
            onSaved(r);
          } catch (e) {
            onError(e);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="modal-body">
          <div className="provider-card">
            <div className="provider-icon">
              <Sparkles size={23} />
            </div>
            <div>
              <h3>OpenAI API</h3>
              <p>Research, writing, speech & transcription</p>
            </div>
            <Badge tone={config.connected ? "green" : ""}>
              {config.connected ? "Connected" : "Not connected"}
            </Badge>
          </div>
          <label className="field">
            API key{" "}
            <span className="field-note">Private to this browser session</span>
            <input
              type="password"
              autoComplete="new-password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder={
                config.connected
                  ? "Leave blank to keep the connected key"
                  : "Enter your API key"
              }
            />
          </label>
          <div className="field-row">
            {field("model", "Writing / editing model", "gpt-4.1")}
            {field("research_model", "Web research model", "gpt-4.1")}
          </div>
          <div className="field-row">
            {field("speech_model", "Speech model", "gpt-4o-mini-tts")}
            <label className="field">
              Narrator voice
              <select
                value={values.voice || "onyx"}
                onChange={(e) =>
                  setValues({ ...values, voice: e.target.value })
                }
              >
                {[
                  "onyx",
                  "alloy",
                  "echo",
                  "fable",
                  "nova",
                  "shimmer",
                  "coral",
                  "sage",
                  "ash",
                ].map((v) => (
                  <option value={v} key={v}>
                    {v[0].toUpperCase() + v.slice(1)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="notice">
            <LockKeyhole size={16} />
            <span>
              Your key is held in server memory and never written to project
              files. Restarting the server disconnects it. API charges are
              separate from a chat subscription.
            </span>
          </div>
          <p className="micro-note block">
            Defaults are configurable; model access depends on your provider
            account. The current Speech API defaults are scheduled for
            retirement in January 2027 and will need a provider adapter update.
            No paid AI calls were made to produce the sample.
          </p>
          <div className="settings-local">
            <CheckCircle2 size={16} />
            <div>
              <b>Local editing & FFmpeg rendering</b>
              <p>Already available. No AI key needed.</p>
            </div>
            <Badge tone="green">Ready</Badge>
          </div>
        </div>
        <div className="modal-footer">
          {config.connected ? (
            <Button
              type="button"
              kind="danger"
              onClick={async () => {
                try {
                  onSaved(await api("/api/config", "DELETE"));
                } catch (e) {
                  onError(e);
                }
              }}
            >
              Disconnect
            </Button>
          ) : (
            <span>Use non-sensitive test material in this prototype.</span>
          )}
          <Button
            kind="primary"
            icon={busy ? LoaderCircle : LockKeyhole}
            disabled={busy || (!key && !config.connected)}
            type="submit"
          >
            {busy ? "Verifying…" : "Connect & verify"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function SourceModal({ onClose, onSave }) {
  const [values, setValues] = useState({
      title: "",
      url: "",
      notes: "",
      type: "Producer source",
    }),
    [busy, setBusy] = useState(false);
  return (
    <Modal
      title="Keep the source trail clear."
      eyebrow="ADD A SOURCE"
      onClose={onClose}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await onSave(values);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="modal-body">
          <label className="field">
            Source title
            <input
              autoFocus
              required
              value={values.title}
              onChange={(e) => setValues({ ...values, title: e.target.value })}
              placeholder="Court record, article, or interview…"
            />
          </label>
          <label className="field">
            Original URL{" "}
            <span className="field-note">Optional for offline records</span>
            <input
              type="url"
              value={values.url}
              onChange={(e) => setValues({ ...values, url: e.target.value })}
              placeholder="https://…"
            />
          </label>
          <label className="field">
            Source type
            <select
              value={values.type}
              onChange={(e) => setValues({ ...values, type: e.target.value })}
            >
              {[
                "Producer source",
                "Court / official record",
                "Reporting",
                "Interview / recording",
                "Archive / document",
              ].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="field">
            Verified facts & context
            <textarea
              rows="5"
              value={values.notes}
              onChange={(e) => setValues({ ...values, notes: e.target.value })}
              placeholder="Specific facts, dates, quotations, attribution, and uncertainties…"
            />
          </label>
          <p className="micro-note block">
            Adding a source does not mark it verified. Review the original, then
            mark it reviewed in the source library.
          </p>
        </div>
        <div className="modal-footer">
          <Button type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            kind="primary"
            icon={busy ? LoaderCircle : Plus}
            disabled={!values.title.trim() || busy}
          >
            Add source
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ExportModal({
  project,
  voice,
  onClose,
  onExport,
  locked,
  onPreflight,
}) {
  const [resolution, setResolution] = useState("720p"),
    [draft, setDraft] = useState(true),
    [captions, setCaptions] = useState(project.captions);
  const allReviewed = Object.values(project.review).every(Boolean);
  const inspectionPlan = project.episode?.plan?.mode === "inspection";
  const [allowGuideGaps, setAllowGuideGaps] = useState(false);
  const hasGuideGaps =
    !!project.episode?.guide && project.scenes.some((s) => !s.asset_id);
  const [preflight, setPreflight] = useState(null);
  const [preflightError, setPreflightError] = useState(false);
  useEffect(() => {
    let stopped = false;
    api(`/api/projects/${project.id}/preflight`)
      .then((r) => {
        if (!stopped) setPreflight(r);
      })
      .catch(() => {
        if (!stopped) setPreflightError(true);
      });
    return () => {
      stopped = true;
    };
  }, [project.updated_at]);
  return (
    <Modal
      title="Make the final cut real."
      eyebrow="RENDER & DOWNLOAD"
      onClose={onClose}
    >
      <div className="modal-body">
        <div className="export-spec">
          <div className="export-file-icon">
            <Film size={25} />
          </div>
          <div>
            <h3>{project.title}</h3>
            <p>
              {tc(sum(project.scenes))} · {project.scenes.length} scenes · 16:9
            </p>
          </div>
          <Badge>MP4</Badge>
        </div>
        <label className="field">
          Resolution
          <select
            aria-label="Export resolution"
            value={resolution}
            onChange={(e) => setResolution(e.target.value)}
          >
            <option value="480p">480p · Quick review render</option>
            <option value="720p">720p HD · Faster draft</option>
            <option value="1080p">1080p Full HD · Larger file</option>
          </select>
        </label>
        <div className="export-switch">
          <div>
            <b>Review draft</b>
            <p>
              Includes a visible draft watermark. Final exports require
              editorial review.
            </p>
          </div>
          <Toggle
            checked={draft}
            onChange={setDraft}
            label="Review draft watermark"
          />
        </div>
        <div className="export-switch">
          <div>
            <b>Burn in captions</b>
            <p>A separate SRT file is also saved with the export.</p>
          </div>
          <Toggle
            checked={captions}
            onChange={setCaptions}
            label="Burn in captions"
          />
        </div>
        {!voice && (
          <div className="notice warning">
            <VolumeX size={16} />
            <span>
              {project.episode?.guide ? (
                <>
                  <b>Upload your finished narration first.</b> A script-only
                  guide plan cannot render a video. Assign the recording in
                  Episode setup, card 1; it will not be regenerated.
                </>
              ) : (
                <>
                  <b>No narration assigned.</b> This draft will have no spoken
                  voice. Add a voice track in the Audio panel for a complete
                  episode.
                </>
              )}
            </span>
          </div>
        )}
        {draft && hasGuideGaps && (
          <label className="ep-checkbox" style={{ padding: "12px 0" }}>
            <input
              type="checkbox"
              aria-label="Allow marked guide gaps in review export"
              checked={allowGuideGaps}
              onChange={(ev) => setAllowGuideGaps(ev.target.checked)}
            />
            <span>
              I explicitly allow visibly marked missing-visual cards in this
              internal review-only video. No substitute footage will be invented
              or looped.
            </span>
          </label>
        )}
        {inspectionPlan && (
          <div className="notice warning">
            <AlertTriangle size={16} />
            <span>
              <b>Unreviewed inspection only.</b> This rendering is visibly
              marked and cannot be a final export. Complete real source reviews
              and rebuild a reviewed plan before publication.
            </span>
          </div>
        )}
        {!draft && !allReviewed && (
          <div className="notice warning">
            <ShieldCheck size={16} />
            <span>
              Complete all four editorial checks in Review before making a final
              export.
            </span>
          </div>
        )}
        {project.is_demo && (
          <p className="micro-note block">
            The fictional-demo disclosure is always included in this sample's
            renders.
          </p>
        )}
        <div className="preflight-summary-line">
          <ShieldCheck size={13} />
          <span>
            {preflight
              ? `${preflight.errors} final-export blockers · ${preflight.warnings} review warnings`
              : preflightError
                ? "Preflight unavailable. Final rendering remains locked."
                : "Checking export prerequisites…"}
          </span>
          <button onClick={onPreflight}>
            View checks <ArrowUpRight size={11} />
          </button>
        </div>
        <div className="render-details">
          <span>
            <Check size={12} /> H.264 video · 24 fps
          </span>
          <span>
            <Check size={12} />{" "}
            {project.episode?.guide
              ? "Preserved voice & music ducking"
              : "Audio leveling & music ducking"}
          </span>
          <span>
            <Check size={12} /> Downloadable MP4 + source notes
          </span>
        </div>
        <p className="micro-note block">
          Rendering runs on this server's CPU. A 20–40 minute episode may take a
          substantial amount of time. This prototype does not include GPU
          acceleration.
        </p>
      </div>
      <div className="modal-footer">
        <Button onClick={onClose}>Back to editing</Button>
        <Button
          kind="primary"
          icon={Download}
          disabled={
            locked ||
            !project.scenes.length ||
            !preflight ||
            (draft && hasGuideGaps && !allowGuideGaps) ||
            (preflight && !preflight.ready_for_draft) ||
            (!draft &&
              (inspectionPlan || !allReviewed || !preflight?.ready_for_final))
          }
          onClick={() =>
            onExport({
              resolution,
              draft,
              captions,
              allow_guided_gaps: allowGuideGaps,
              allow_inspection: inspectionPlan && draft,
            })
          }
        >
          Start render
        </Button>
      </div>
    </Modal>
  );
}

createRoot(document.getElementById("root")).render(<App />);
