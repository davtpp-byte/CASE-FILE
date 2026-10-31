import React from "react";

export const MAX_FILE_BYTES = 512 * 1024 * 1024;
export const MAX_UPLOAD_FILES = 30;
export const uploadLimits = "512 MB per file · up to 30 files per batch";
export const fileSize = (bytes = 0) =>
  bytes >= 1048576
    ? `${(bytes / 1048576).toFixed(1)} MB`
    : `${Math.round(bytes / 1024)} KB`;

export function validateUpload(files) {
  const list = Array.from(files || []);
  if (list.length > MAX_UPLOAD_FILES)
    throw new Error(
      `Choose up to ${MAX_UPLOAD_FILES} files per batch. Nothing was uploaded.`,
    );
  const tooLarge = list.find((file) => file.size > MAX_FILE_BYTES);
  if (tooLarge)
    throw new Error(
      `${tooLarge.name} is ${fileSize(tooLarge.size)}. The limit is 512 MB per file. Nothing was uploaded; use a smaller copy, not a different filename.`,
    );
  return list;
}

// XMLHttpRequest upload events report bytes sent; no timers invent a percentage.
// Reaching 100% means transfer finished, NOT that server analysis has finished.
export function sendUploadRequest(path, method, body, session, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, path);
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-Casefile-Session", session);
    if (!(body instanceof FormData))
      xhr.setRequestHeader("Content-Type", "application/json");
    let last = { loaded: 0, total: 0, phase: "uploading" };
    onProgress(last);
    xhr.upload.onprogress = (event) => {
      last = {
        loaded: event.loaded,
        total: event.lengthComputable ? event.total : 0,
        phase: "uploading",
      };
      onProgress(last);
    };
    xhr.upload.onload = () => onProgress({ ...last, phase: "processing" });
    xhr.onerror = () =>
      reject(
        new Error(
          "Upload interrupted or the server could not be reached. Keep your original files. Check the media list before retrying, because a completed file may already have been accepted.",
        ),
      );
    xhr.onabort = () =>
      reject(
        new Error(
          "Upload cancelled. Check the media list before retrying; original files on your computer were not changed.",
        ),
      );
    xhr.onload = () => {
      let result;
      try {
        result = (xhr.getResponseHeader("Content-Type") || "").includes("json")
          ? JSON.parse(xhr.responseText)
          : xhr.responseText;
      } catch {
        reject(
          new Error(
            "The server returned an unreadable upload response. Keep your originals and save a project backup.",
          ),
        );
        return;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        const detail = result?.detail || result || "Upload failed.";
        const error = new Error(
          typeof detail === "string" ? detail : JSON.stringify(detail),
        );
        error.status = xhr.status;
        reject(error);
        return;
      }
      onProgress({ ...last, phase: "done" });
      resolve(result);
    };
    xhr.send(body instanceof FormData ? body : JSON.stringify(body));
  });
}

export function UploadProgress({ progress }) {
  const panel = React.useRef(null);
  React.useEffect(() => {
    if (progress?.phase === "uploading")
      panel.current?.scrollIntoView({ block: "nearest", behavior: "auto" });
  }, [progress?.phase]);
  if (!progress) return null;
  const percent =
    progress.total > 0
      ? Math.min(100, Math.round((progress.loaded / progress.total) * 100))
      : null;
  const active = progress.phase === "uploading";
  const message =
    progress.phase === "processing"
      ? "Transfer complete — processing media on the server…"
      : progress.phase === "done"
        ? "Upload and media processing complete."
        : progress.phase === "error"
          ? "Upload did not finish successfully. Check the error and media list before retrying."
          : "Uploading selected files…";
  return (
    <section
      className={`upload-progress ${progress.phase}`}
      ref={panel}
      aria-label="Upload progress"
    >
      <div>
        <b>{progress.label || "Media upload"}</b>
        <span>
          {active && percent !== null
            ? `${percent}%`
            : progress.phase === "processing"
              ? "Processing"
              : progress.phase === "done"
                ? "Complete"
                : progress.phase === "error"
                  ? "Error"
                  : "Sending"}
        </span>
      </div>
      <progress
        aria-label="Bytes uploaded"
        max={100}
        value={
          active && percent !== null
            ? percent
            : progress.phase === "done"
              ? 100
              : progress.phase === "error"
                ? 0
                : undefined
        }
      />
      <p aria-live="polite">
        {message}
        {active && progress.loaded > 0
          ? ` ${fileSize(progress.loaded)}${progress.total > 0 ? ` of ${fileSize(progress.total)}` : ""} sent.`
          : ""}
      </p>
    </section>
  );
}
