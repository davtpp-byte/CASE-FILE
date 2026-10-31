// Temporary browser-side originals for this working session. Never a cloud DB.
// Files stay in this browser/site until Finish session clears them.
const NAME = "casefile-studio-working-files";
async function db() {
  return await new Promise((resolve, reject) => {
    const r = indexedDB.open(NAME, 1);
    r.onupgradeneeded = () =>
      r.result.createObjectStore("files", { keyPath: "key" });
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
export async function keepWorkingFiles(id, files, role) {
  const d = await db();
  try {
    await new Promise((resolve, reject) => {
      const tx = d.transaction("files", "readwrite");
      for (const f of files)
        tx.objectStore("files").put({
          key: `${id}:${role}:${f.name}`,
          project_id: id,
          role,
          name: f.name,
          size: f.size,
          type: f.type,
          last_modified: f.lastModified || 0,
          selected_at: Date.now(),
          blob: f,
        });
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    d.close();
  }
}
export async function workingFiles(id) {
  const d = await db();
  try {
    return await new Promise((resolve, reject) => {
      const r = d.transaction("files").objectStore("files").getAll();
      r.onsuccess = () =>
        resolve(
          r.result
            .filter((x) => x.project_id === id)
            .sort((a, b) => a.selected_at - b.selected_at),
        );
      r.onerror = () => reject(r.error);
    });
  } finally {
    d.close();
  }
}
export async function clearWorkingFiles(id) {
  const rows = await workingFiles(id),
    d = await db();
  try {
    await new Promise((resolve, reject) => {
      const tx = d.transaction("files", "readwrite");
      for (const row of rows) tx.objectStore("files").delete(row.key);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    d.close();
  }
}

export async function restoreWorkingSession(snapshot, api, progress) {
  const id = snapshot.id,
    rows = await workingFiles(id),
    media = rows.filter((x) =>
      ["sources", "narration_id", "music_id", "auto"].includes(x.role),
    );
  let server;
  try {
    server = await api(`/api/projects/${id}`);
  } catch (e) {
    if (e.status !== 404) throw e;
    server = await api(`/api/projects/${id}/recover-empty`, "POST", {
      title: snapshot.title,
      mode: snapshot.mode,
      target_minutes: snapshot.target_minutes,
    });
  }
  const status = await api(`/api/projects/${id}/media-status`);
  const expected = snapshot.assets || [];
  const needsFiles = expected.some(
    (a) =>
      !status.assets.some(
        (s) => s.exists && s.name === a.name && s.size === a.size,
      ),
  );
  if (needsFiles && !media.length)
    return {
      project: server,
      restored: 0,
      missing: expected.length,
      protectedSnapshot: snapshot,
    };
  const older = (snapshot.updated_at || "") > (server.updated_at || "");
  if (!needsFiles && !older && server.episode?.script && server.episode?.guide)
    return {
      project: server,
      restored: 0,
      missing: 0,
      protectedSnapshot: null,
    };
  if (older || !server.episode?.script || !server.episode?.guide) {
    await api(`/api/projects/${id}/recovery-checkpoint`, "POST", {});
    const scriptRow = rows.filter((row) => row.role === "script").at(-1);
    const guideRow = rows.filter((row) => row.role === "guide").at(-1);
    const scriptText = scriptRow
      ? await scriptRow.blob.text()
      : snapshot.episode?.script?.raw;
    const guideText = guideRow
      ? await guideRow.blob.text()
      : snapshot.episode?.guide?.raw;
    if (scriptText)
      await api(`/api/projects/${id}/episode/import`, "POST", {
        role: "script",
        text: scriptText,
        filename:
          scriptRow?.name ||
          snapshot.episode?.script?.filename ||
          "recovered-script.md",
      });
    if (guideText)
      await api(`/api/projects/${id}/episode/import`, "POST", {
        role: "guide",
        text: guideText,
        filename:
          guideRow?.name ||
          snapshot.episode?.guide?.filename ||
          "recovered-guide.md",
      });
    const timing = rows.filter((x) => x.role === "timings");
    if (timing.length) {
      for (const row of timing)
        await api(`/api/projects/${id}/episode/import`, "POST", {
          role: "timings",
          text: await row.blob.text(),
          filename: row.name,
        });
    } else if (snapshot.episode?.timings?.hash) {
      await api(`/api/projects/${id}/reuse-timings`, "POST", {
        hash: snapshot.episode.timings.hash,
      }).catch(() => {});
    }
  }
  let restored = 0,
    oldToNew = {},
    recoveredRoles = {};
  for (const row of media) {
    let current = (await api(`/api/projects/${id}/media-status`)).assets;
    let asset = current.find(
      (a) => a.exists && a.name === row.name && a.size === row.size,
    );
    if (!asset) {
      const file = new File([row.blob], row.name, {
        type: row.type,
        lastModified: row.last_modified,
      });
      const form = new FormData();
      form.append("files", file);
      const original = expected.find(
        (a) => a.name === row.name && a.size === row.size,
      );
      let role = row.role;
      if (role === "auto")
        role =
          original?.id === snapshot.narration_id
            ? "narration_id"
            : original?.id === snapshot.music_id
              ? "music_id"
              : "sources";
      form.append(
        "episode_role",
        role === "narration_id"
          ? "narration"
          : role === "music_id"
            ? "music"
            : "sources",
      );
      const known = new Set(current.map((a) => a.id));
      const p = await api(`/api/projects/${id}/upload`, "POST", form, (p) =>
        progress?.({ ...p, label: `Recovering ${row.name}` }),
      );
      asset = p.assets.find(
        (a) => !known.has(a.id) && a.name === row.name && a.size === row.size,
      );
      restored++;
    }
    if (asset && row.role === "narration_id")
      recoveredRoles.narration_id = asset.id;
    if (asset && row.role === "music_id") recoveredRoles.music_id = asset.id;
    if (asset)
      for (const a of expected.filter(
        (a) => a.name === row.name && a.size === row.size,
      ))
        oldToNew[a.id] = asset.id;
  }
  server = await api(`/api/projects/${id}`);
  for (const a of expected) {
    if (!oldToNew[a.id] && status.assets.some((s) => s.id === a.id && s.exists))
      oldToNew[a.id] = a.id;
  }
  for (const [sid, binding] of Object.entries(
    snapshot.episode?.bindings || {},
  )) {
    const mapped = oldToNew[binding.asset_id];
    if (mapped && server.episode?.bindings?.[sid]?.asset_id !== mapped)
      await api(`/api/projects/${id}/episode/source/${sid}`, "PATCH", {
        asset_id: mapped,
        contains_residence: !!binding.contains_residence,
      });
  }
  const options = { ...recoveredRoles };
  for (const role of ["narration_id", "music_id"]) {
    if (oldToNew[snapshot[role]]) options[role] = oldToNew[snapshot[role]];
  }
  if (Object.keys(options).length)
    await api(`/api/projects/${id}/episode/options`, "PATCH", options);
  if (older || restored) {
    for (const [cid, choice] of Object.entries(snapshot.episode?.choices || {}))
      await api(
        `/api/projects/${id}/episode/choice/${cid}`,
        "PATCH",
        choice,
      ).catch(() => {});
    for (const [cid, review] of Object.entries(
      snapshot.episode?.reviews || {},
    )) {
      const draft = { reviewed: false };
      for (const key of ["in", "out", "narration_start", "narration_end"])
        if (Number.isFinite(review[key])) draft[key] = review[key];
      if (Object.keys(draft).length > 1)
        await api(
          `/api/projects/${id}/episode/cue/${cid}`,
          "PATCH",
          draft,
        ).catch(() => {});
    }
    await api(`/api/projects/${id}`, "PATCH", {
      title: snapshot.title,
      captions: snapshot.captions !== false,
      look: snapshot.look || "noir",
      music_volume: snapshot.music_volume ?? 0.12,
    });
  }
  const latest = await api(`/api/projects/${id}/media-status`);
  const missing = expected.filter(
    (a) =>
      !latest.assets.some(
        (s) => s.exists && s.name === a.name && s.size === a.size,
      ),
  ).length;
  return {
    project: await api(`/api/projects/${id}`),
    restored,
    missing,
    protectedSnapshot: missing ? snapshot : null,
  };
}

export async function protectAvailableServerFiles(project) {
  if (!project?.id || project.is_demo) return;
  const cached = await workingFiles(project.id);
  for (const asset of project.assets || []) {
    if (
      !["image", "video", "audio"].includes(asset.kind) ||
      !asset.url ||
      asset.available_on_server === false
    )
      continue;
    if (
      cached.some((row) => row.name === asset.name && row.size === asset.size)
    )
      continue;
    const url = new URL(asset.url, window.location.origin);
    if (url.origin !== window.location.origin) continue;
    try {
      const response = await fetch(url.href, { credentials: "same-origin" });
      if (!response.ok) continue;
      const blob = await response.blob();
      if (blob.size !== asset.size) continue;
      const role =
        asset.id === project.narration_id
          ? "narration_id"
          : asset.id === project.music_id
            ? "music_id"
            : "sources";
      const file = new File([blob], asset.name, { type: blob.type });
      await keepWorkingFiles(project.id, [file], role);
    } catch {
      /* A missing/cancelled fetch is not a successful backup. Originals stay on disk. */
    }
  }
}
