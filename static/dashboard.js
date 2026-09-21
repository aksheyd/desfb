(() => {
  const state = {
    temp: Number(document.getElementById("temp").value),
    taxon: "birds",
    q: "",
    sortKey: "Danger Level",
    sortDir: "desc",
    rows: [],
    barChart: null,
    histChart: null,
  };

  const el = {
    temp: document.getElementById("temp"),
    tempOut: document.getElementById("temp-out"),
    changeVal: document.getElementById("change-val"),
    cards: document.getElementById("cards"),
    tabs: document.getElementById("taxon-tabs"),
    search: document.getElementById("search"),
    tbody: document.querySelector("#species-table tbody"),
    rowCount: document.getElementById("row-count"),
    status: document.getElementById("refresh-status"),
    meta: document.getElementById("meta-box"),
    btnRefresh: document.getElementById("btn-refresh"),
    btnRestore: document.getElementById("btn-restore"),
  };

  function setStatus(msg, kind) {
    el.status.textContent = msg || "";
    el.status.className = "status" + (kind ? " " + kind : "");
  }

  async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || data.message || res.statusText);
    return data;
  }

  function dangerClass(v) {
    if (v >= 100) return "danger-high";
    if (v >= 50) return "danger-mid";
    return "";
  }

  function renderCards(summary) {
    const cards = summary.groups.map(
      (g) => `<article class="card">
        <div class="label">${g.label}</div>
        <div class="value">${g.count}</div>
        <div class="sub">avg danger ${g.avg_danger} · max ${g.max_danger}</div>
      </article>`
    );
    cards.push(`<article class="card">
      <div class="label">≥100 (“extinct” in toy model)</div>
      <div class="value">${summary.extinctish_total}</div>
      <div class="sub">changeVal ${summary.change_val} at ${summary.temp_f} °F</div>
    </article>`);
    el.cards.innerHTML = cards.join("");
    el.changeVal.textContent = `Toy changeVal = ${summary.change_val} (baseline ${summary.baseline_f} °F). ${summary.note}`;
    el.meta.textContent = JSON.stringify(summary.refresh_meta || {}, null, 2);

    const labels = summary.groups.map((g) => g.label);
    const avgs = summary.groups.map((g) => g.avg_danger);
    const ctx = document.getElementById("bar-chart");
    if (state.barChart) state.barChart.destroy();
    state.barChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{ label: "Avg Danger Level", data: avgs, backgroundColor: "#3dbb7a" }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { color: "#9db0c7" }, grid: { color: "#2a3a4f" } },
          x: { ticks: { color: "#9db0c7" }, grid: { display: false } },
        },
      },
    });
  }

  function renderTabs(summary) {
    el.tabs.innerHTML = summary.groups
      .map(
        (g) =>
          `<button type="button" data-key="${g.key}" class="${
            g.key === state.taxon ? "active" : ""
          }">${g.label} (${g.count})</button>`
      )
      .join("");
    el.tabs.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.taxon = btn.dataset.key;
        loadTaxa();
        el.tabs.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === btn));
      });
    });
  }

  function sortedRows() {
    const rows = [...state.rows];
    const key = state.sortKey;
    const dir = state.sortDir === "asc" ? 1 : -1;
    rows.sort((a, b) => {
      let av = a[key];
      let bv = b[key];
      if (key === "Danger Level" || key === "Obs Count") {
        av = Number(av) || 0;
        bv = Number(bv) || 0;
        return (av - bv) * dir;
      }
      return String(av ?? "").localeCompare(String(bv ?? ""), undefined, { sensitivity: "base" }) * dir;
    });
    return rows;
  }

  function renderTable() {
    const rows = sortedRows();
    el.rowCount.textContent = `${rows.length} rows`;
    el.tbody.innerHTML = rows
      .map((r) => {
        const d = Number(r["Danger Level"]) || 0;
        return `<tr>
          <td>${escapeHtml(r["Common Name"])}</td>
          <td><em>${escapeHtml(r["Scientific Name"])}</em></td>
          <td class="${dangerClass(d)}">${d}</td>
          <td>${escapeHtml(r["Occurrence"] || "")}</td>
          <td>${escapeHtml(r["Classification"] || "")}</td>
          <td>${escapeHtml(r["Federal"] || "")}</td>
          <td>${escapeHtml(r["State"] || "")}</td>
          <td>${escapeHtml(r["Obs Count"] ?? "")}</td>
        </tr>`;
      })
      .join("");

    const values = rows.map((r) => Number(r["Danger Level"]) || 0);
    const bins = binDanger(values);
    const ctx = document.getElementById("hist-chart");
    if (state.histChart) state.histChart.destroy();
    state.histChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: bins.labels,
        datasets: [{ label: "Species", data: bins.counts, backgroundColor: "#4ea1ff" }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { color: "#9db0c7" }, grid: { color: "#2a3a4f" } },
          x: { ticks: { color: "#9db0c7" }, grid: { display: false } },
        },
      },
    });
  }

  function binDanger(values) {
    const edges = [0, 10, 25, 50, 75, 100, 200];
    const labels = ["0–9", "10–24", "25–49", "50–74", "75–99", "≥100"];
    const counts = labels.map(() => 0);
    for (const v of values) {
      let i = edges.findIndex((e, idx) => idx < edges.length - 1 && v >= edges[idx] && v < edges[idx + 1]);
      if (i < 0) i = labels.length - 1;
      counts[i] += 1;
    }
    return { labels, counts };
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  async function loadSummary() {
    const summary = await fetchJSON(`/api/summary?temp=${state.temp}`);
    renderCards(summary);
    renderTabs(summary);
  }

  async function loadTaxa() {
    const q = encodeURIComponent(state.q);
    const data = await fetchJSON(`/api/taxa/${state.taxon}?temp=${state.temp}&q=${q}`);
    state.rows = data.rows || [];
    renderTable();
  }

  async function reloadAll() {
    await loadSummary();
    await loadTaxa();
  }

  async function doRefresh(bundledOnly) {
    el.btnRefresh.disabled = true;
    el.btnRestore.disabled = true;
    setStatus(bundledOnly ? "Restoring bundled CSVs…" : "Refreshing from iNaturalist…", "");
    try {
      const meta = await fetchJSON("/api/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bundled_only: bundledOnly }),
      });
      const mode = meta.mode || "?";
      setStatus(
        meta.ok
          ? `Refresh OK (${mode}). ${meta.message || ""}`
          : `Refresh reported failure.`,
        meta.ok ? "ok" : "error"
      );
      await reloadAll();
    } catch (err) {
      setStatus(`Refresh failed: ${err.message}`, "error");
    } finally {
      el.btnRefresh.disabled = false;
      el.btnRestore.disabled = false;
    }
  }

  el.temp.addEventListener("input", () => {
    state.temp = Number(el.temp.value);
    el.tempOut.textContent = String(state.temp);
  });
  el.temp.addEventListener("change", () => reloadAll());

  let searchTimer;
  el.search.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.q = el.search.value.trim();
      loadTaxa();
    }, 200);
  });

  document.querySelectorAll("#species-table th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (state.sortKey === key) {
        state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      } else {
        state.sortKey = key;
        state.sortDir = key === "Danger Level" || key === "Obs Count" ? "desc" : "asc";
      }
      renderTable();
    });
  });

  el.btnRefresh.addEventListener("click", () => doRefresh(false));
  el.btnRestore.addEventListener("click", () => doRefresh(true));

  reloadAll().catch((err) => setStatus(`Load failed: ${err.message}`, "error"));
})();
