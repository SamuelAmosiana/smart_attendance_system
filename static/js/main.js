/**
 * main.js — Shared utilities used across all pages
 */

// ── Live clock on dashboard ────────────────────────────────
(function initClock() {
  const clockEl = document.getElementById("clock");
  if (!clockEl) return;

  function tick() {
    const now = new Date();
    const hh  = String(now.getHours()).padStart(2, "0");
    const mm  = String(now.getMinutes()).padStart(2, "0");
    const ss  = String(now.getSeconds()).padStart(2, "0");
    clockEl.textContent = `${hh}:${mm}:${ss}`;
  }

  tick();
  setInterval(tick, 1000);
})();


// ── Sidebar toggle (mobile) ────────────────────────────────
(function initSidebar() {
  const toggle  = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");

  if (!toggle || !sidebar) return;

  toggle.addEventListener("click", () => {
    sidebar.classList.toggle("open");
  });

  // Close sidebar when clicking outside on mobile
  document.addEventListener("click", (e) => {
    if (
      window.innerWidth <= 768 &&
      sidebar.classList.contains("open") &&
      !sidebar.contains(e.target) &&
      e.target !== toggle
    ) {
      sidebar.classList.remove("open");
    }
  });
})();


// ── Password toggle on login page ─────────────────────────
(function initPasswordToggle() {
  const btn  = document.getElementById("toggle-pw");
  const icon = document.getElementById("toggle-pw-icon");
  const input = document.getElementById("password");

  if (!btn || !input) return;

  btn.addEventListener("click", () => {
    const isHidden = input.type === "password";
    input.type = isHidden ? "text" : "password";
    icon.className = isHidden ? "bi bi-eye-slash-fill" : "bi bi-eye-fill";
  });
})();


// ── Jinja2 enumerate polyfill ──────────────────────────────
// Jinja2 doesn't have enumerate by default unless you pass it.
// We handle row numbering directly in the template with loop.index.
// This file is a placeholder for that note.


// ── Generic API helper ─────────────────────────────────────
window.apiPost = async function (url, body = {}) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return resp.json();
};


// ── Show a status element with message ────────────────────
window.showStatus = function (el, message, type = "info") {
  el.className = `capture-status ${type}`;
  el.innerHTML = `<i class="bi bi-${type === 'success' ? 'check-circle' : type === 'error' ? 'x-circle' : 'info-circle'}-fill"></i> ${message}`;
  el.classList.remove("hidden");
};
