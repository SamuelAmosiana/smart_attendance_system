/**
 * register.js — Logic for the student registration page
 */

// ── Capture Faces ──────────────────────────────────────────
(function initCapture() {
  const captureBtn  = document.getElementById("capture-btn");
  const statusEl    = document.getElementById("capture-status");
  const studentIdEl = document.getElementById("capture-student-id");
  const samplesEl   = document.getElementById("num-samples");

  if (!captureBtn) return;

  captureBtn.addEventListener("click", async () => {
    const studentId  = studentIdEl.value.trim();
    const numSamples = parseInt(samplesEl.value, 10);

    if (!studentId) {
      showStatus(statusEl, "Please enter a Student ID first.", "error");
      return;
    }

    captureBtn.disabled = true;
    captureBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Opening Webcam…';
    showStatus(statusEl, `Capturing ${numSamples} samples for ${studentId}. Check the webcam window.`, "info");

    try {
      const data = await apiPost("/api/capture-faces", {
        student_id  : studentId,
        num_samples : numSamples,
      });

      if (data.success) {
        showStatus(statusEl, `✔ ${data.message}`, "success");
      } else {
        showStatus(statusEl, `Error: ${data.message}`, "error");
      }
    } catch (err) {
      showStatus(statusEl, "Network error. Is the Flask server running?", "error");
    } finally {
      captureBtn.disabled = false;
      captureBtn.innerHTML = '<i class="bi bi-webcam-fill"></i> Capture Faces';
    }
  });

  // Auto-fill student ID from the registration form
  const regIdInput = document.getElementById("student_id");
  if (regIdInput) {
    regIdInput.addEventListener("input", () => {
      studentIdEl.value = regIdInput.value;
    });
  }
})();


// ── Encode Faces (from register page) ─────────────────────
(function initEncodeFromRegister() {
  const encBtn  = document.getElementById("encode-from-register-btn");
  const statEl  = document.getElementById("encode-status");

  if (!encBtn) return;

  encBtn.addEventListener("click", async () => {
    encBtn.disabled = true;
    encBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Encoding…';
    showStatus(statEl, "Running face encoding — please wait…", "info");

    try {
      const data = await apiPost("/api/encode-faces");

      if (data.success) {
        showStatus(statEl, `✔ ${data.message}`, "success");
      } else {
        showStatus(statEl, `Error: ${data.message}`, "error");
      }
    } catch (err) {
      showStatus(statEl, "Network error.", "error");
    } finally {
      encBtn.disabled = false;
      encBtn.innerHTML = '<i class="bi bi-cpu-fill"></i> Encode All Faces';
    }
  });
})();


// ── Delete Student (soft-delete via API) ───────────────────
(function initDeleteUser() {
  document.addEventListener("click", async (e) => {
    const btn = e.target.closest(".delete-user-btn");
    if (!btn) return;

    const userId = btn.dataset.id;
    const name   = btn.dataset.name;

    if (!confirm(`Remove student "${name}" from the system?\n\nThis is a soft-delete — the record will be hidden but not permanently erased.`)) {
      return;
    }

    try {
      const resp = await fetch(`/api/users/${userId}`, { method: "DELETE" });
      const data = await resp.json();

      if (data.success) {
        const row = document.getElementById(`row-${userId}`);
        if (row) {
          row.style.opacity = "0";
          row.style.transition = "opacity 0.4s";
          setTimeout(() => row.remove(), 400);
        }
      } else {
        alert("Failed to remove student: " + data.message);
      }
    } catch (err) {
      alert("Network error. Could not delete student.");
    }
  });
})();
