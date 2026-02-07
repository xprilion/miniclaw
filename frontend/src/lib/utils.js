// Utility functions for the MiniClaw frontend

let loadingBarTimer = null

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;")
}

export function parseJsonSafe(text) {
  if (!text || !text.trim()) return {}
  try {
    return JSON.parse(text)
  } catch {
    return { raw: text }
  }
}

export function loadingStart() {
  const bar = document.getElementById("miniclaw-loading-bar")
  if (!bar) return
  bar.classList.remove("miniclaw-loading-done")
  bar.classList.add("miniclaw-loading")
  bar.style.width = "0%"
  if (loadingBarTimer) clearTimeout(loadingBarTimer)
  loadingBarTimer = setTimeout(() => {
    bar.style.width = "30%"
  }, 50)
}

export function loadingDone() {
  const bar = document.getElementById("miniclaw-loading-bar")
  if (!bar) return
  if (loadingBarTimer) {
    clearTimeout(loadingBarTimer)
    loadingBarTimer = null
  }
  bar.style.width = "100%"
  bar.classList.remove("miniclaw-loading")
  bar.classList.add("miniclaw-loading-done")
  setTimeout(() => {
    bar.classList.remove("miniclaw-loading-done")
    bar.style.width = "0%"
  }, 300)
}

export async function api(path, options = {}) {
  loadingStart()
  try {
    const response = await fetch(path, {
      ...options,
      headers: {
        ...(options.headers || {}),
      },
    })
    const text = await response.text()
    const data = parseJsonSafe(text)
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `Request failed (${response.status})`)
    }
    return data
  } finally {
    loadingDone()
  }
}

export function showStatus(message, kind = "", elementId = "statusLine") {
  const status = document.getElementById(elementId)
  if (!status) return

  status.classList.remove("status-success", "status-error", "status-info")
  status.classList.add("status-line")

  status.textContent = message || ""
  if (!message) return

  if (kind === "success") {
    status.classList.add("status-success")
    return
  }
  if (kind === "error") {
    status.classList.add("status-error")
    return
  }
  status.classList.add("status-info")
}