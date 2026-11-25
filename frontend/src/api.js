// Thin fetch wrapper that normalises errors. Every call works on a dataset the user uploaded.
async function request(path, { method = "GET", body, raw = false } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";

  let res;
  try {
    res = await fetch(`/api${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new Error("Cannot reach the server. Is the Flask backend running?");
  }
  if (raw) {
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.error || "Download failed");
    }
    return res;
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const e = new Error(data.error || `Request failed (${res.status})`);
    e.status = res.status;
    throw e;
  }
  return data;
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Upload with real progress (fetch cannot report upload progress, XHR can). */
function uploadFile(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/datasets");
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(Math.round((100 * e.loaded) / e.total));
    xhr.onload = () => {
      let data = {};
      try { data = JSON.parse(xhr.responseText); } catch { /* not json */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new Error(data.error || `Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("Cannot reach the server. Is the Flask backend running?"));
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export const api = {
  uploadDataset: uploadFile,
  analyze: (id, body = {}) => request(`/datasets/${id}/analyze`, { method: "POST", body }),
  datasetStatus: (id) => request(`/datasets/${id}/status`),
  dataset: (id) => request(`/datasets/${id}`),
  datasets: () => request("/datasets"),
  deleteDataset: (id) => request(`/datasets/${id}`, { method: "DELETE" }),
  model: (id) => request(`/datasets/${id}/model`),
  predict: (id, body) => request(`/datasets/${id}/predict`, { method: "POST", body }),
  svd: (id) => request(`/datasets/${id}/svd`),
  usage: (id) => request(`/datasets/${id}/usage`),
  saveSystem: (id, body) => request(`/datasets/${id}/system`, { method: "POST", body }),
  predictions: (id) => request(`/datasets/${id}/predictions`),
  downloadReport: async (id, fmt) => {
    const res = await request(`/datasets/${id}/report/${fmt}`, { raw: true });
    saveBlob(await res.blob(), `irrigation_report.${fmt}`);
  },
};
