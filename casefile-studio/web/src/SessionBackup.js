// Browser-local setup safety net. Does NOT store audio/video bytes or provider keys.
const DB_NAME = "casefile-studio-setup-backups";
const STORE = "projects";
function database() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () =>
      request.result.createObjectStore(STORE, { keyPath: "id" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(request.error || new Error("Browser backup unavailable"));
  });
}
export async function cachedSetups() {
  const db = await database();
  try {
    return await new Promise((resolve, reject) => {
      const request = db.transaction(STORE).objectStore(STORE).getAll();
      request.onsuccess = () =>
        resolve(request.result.sort((a, b) => b.saved_at - a.saved_at));
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}
export async function rememberSetup(project) {
  if (!project?.id || project.is_demo) return "not-needed";
  const { undo, ...snapshot } = project;
  const db = await database();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      const store = tx.objectStore(STORE);
      const get = store.get(project.id);
      let protectedNewer = false;
      get.onsuccess = () => {
        const prior = get.result;
        if (
          prior &&
          (prior.project.updated_at || "") > (snapshot.updated_at || "")
        ) {
          protectedNewer = true;
          return;
        }
        store.put({ id: snapshot.id, saved_at: Date.now(), project: snapshot });
      };
      tx.oncomplete = () =>
        resolve(protectedNewer ? "newer-saved-copy" : "saved");
      tx.onerror = () =>
        reject(tx.error || new Error("Could not save browser setup backup"));
    });
  } finally {
    db.close();
  }
}
export async function forgetSetup(id) {
  const db = await database();
  try {
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
