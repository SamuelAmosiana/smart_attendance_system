/**
 * attendance_log.js — Logic for the Attendance Log page
 */

// ── Export table to CSV ────────────────────────────────────
(function initCsvExport() {
  const exportBtn = document.getElementById("export-csv-btn");
  const table     = document.getElementById("log-table");

  if (!exportBtn || !table) return;

  exportBtn.addEventListener("click", () => {
    const rows = table.querySelectorAll("tr");
    const csvLines = [];

    rows.forEach((row) => {
      const cells = row.querySelectorAll("th, td");
      const line = Array.from(cells)
        .map((cell) => `"${cell.innerText.trim().replace(/"/g, '""')}"`)
        .join(",");
      csvLines.push(line);
    });

    const csvContent = csvLines.join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url  = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href     = url;
    link.download = `attendance_export_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  });
})();


// ── Table search / filter ──────────────────────────────────
(function initTableSearch() {
  const table = document.getElementById("log-table");
  if (!table) return;

  // Create a live search input above the table
  const wrapper = table.closest(".card-body");
  if (!wrapper) return;

  const searchInput = document.createElement("input");
  searchInput.type        = "text";
  searchInput.className   = "form-control";
  searchInput.placeholder = "Search by name or student ID…";
  searchInput.style.marginBottom = "1rem";
  searchInput.id = "log-search";

  wrapper.insertBefore(searchInput, wrapper.firstChild);

  searchInput.addEventListener("input", () => {
    const query = searchInput.value.toLowerCase();
    const rows  = table.querySelectorAll("tbody tr");

    rows.forEach((row) => {
      const text = row.innerText.toLowerCase();
      row.style.display = text.includes(query) ? "" : "none";
    });
  });
})();
