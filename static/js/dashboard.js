/**
 * dashboard.js — Logic for the admin dashboard page
 */

// ── Encode Faces button ────────────────────────────────────
(function initEncode() {
  // Button on dashboard card
  const encodeBtn   = document.getElementById("encode-btn");
  const statusEl    = document.getElementById("recog-status");

  if (!encodeBtn || !statusEl) return;

  encodeBtn.addEventListener("click", async () => {
    encodeBtn.disabled = true;
    encodeBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Encoding…';
    showStatus(statusEl, "Encoding faces — this may take a minute on a slow CPU…", "info");

    try {
      const data = await apiPost("/api/encode-faces");

      if (data.success) {
        showStatus(
          statusEl,
          `✔ Done! ${data.message}`,
          "success"
        );
      } else {
        showStatus(statusEl, `Error: ${data.message}`, "error");
      }
    } catch (err) {
      showStatus(statusEl, "Network error. Is the Flask server running?", "error");
    } finally {
      encodeBtn.disabled = false;
      encodeBtn.innerHTML = '<i class="bi bi-cpu-fill"></i> Run Encoding';
    }
  });
})();


// ── Start Recognition button ───────────────────────────────
(function initStartRecognition() {
  // Both the sidebar link and the card button share the same handler
  const buttons = [
    document.getElementById("start-recog-btn"),
    document.getElementById("start-recognition-btn"),
  ];
  const statusEl = document.getElementById("recog-status");

  buttons.forEach((btn) => {
    if (!btn) return;

    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      if (statusEl) showStatus(statusEl, "Starting recognition… Check the webcam window on the server.", "info");

      try {
        const data = await apiPost("/api/start-recognition");
        if (data.success) {
          if (statusEl) showStatus(statusEl, `✔ ${data.message}`, "success");
        } else {
          if (statusEl) showStatus(statusEl, `Error: ${data.message}`, "error");
        }
      } catch (err) {
        if (statusEl) showStatus(statusEl, "Network error.", "error");
      }
    });
  });
})();


// ── Auto-refresh today's table every 30 seconds ────────────
(function autoRefreshToday() {
  const table = document.getElementById("today-table");
  if (!table) return;

  // Soft refresh — reload the page unobtrusively
  setInterval(() => {
    // Only refresh if the tab is visible
    if (document.visibilityState === "visible") {
      window.location.reload();
    }
  }, 30 * 1000);
})();
