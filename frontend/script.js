(function () {
  const TOPICS_KEY = "trendscope_topics";
  const DEFAULT_TOPICS = "AI, Machine Learning, Bitcoin, Climate Change";

  const palette = ["#a855f7", "#22d3ee", "#f472b6", "#fbbf24", "#34d399", "#60a5fa", "#c084fc", "#2dd4bf"];

  const chartText = {
    color: "#94a3b8",
  };

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: "#94a3b8", font: { size: 11 } },
      },
    },
    scales: {
      x: {
        ticks: { color: chartText.color, maxRotation: 45, minRotation: 0 },
        grid: { color: "rgba(148,163,184,0.08)" },
      },
      y: {
        beginAtZero: true,
        ticks: { color: chartText.color },
        grid: { color: "rgba(148,163,184,0.08)" },
      },
    },
  };

  const charts = {};
  let apiStatus = {};

  function getTopicsRaw() {
    const el = document.getElementById("topicInput");
    return (el && el.value) ? el.value.trim() : "";
  }

  function appendParam(url, paramName, value) {
    const t = (value || "").trim();
    if (!t) return url;
    const sep = url.includes("?") ? "&" : "?";
    return url + sep + paramName + "=" + encodeURIComponent(t);
  }

  function loadTopicsFromStorage() {
    const el = document.getElementById("topicInput");
    if (!el) return;
    try {
      const s = localStorage.getItem(TOPICS_KEY);
      el.value = s || DEFAULT_TOPICS;
    } catch {
      el.value = DEFAULT_TOPICS;
    }
  }

  function saveTopics() {
    try {
      localStorage.setItem(TOPICS_KEY, getTopicsRaw() || DEFAULT_TOPICS);
    } catch (_) {}
  }

  function setAppStatus(msg, ok) {
    const el = document.getElementById("appStatus");
    if (!el) return;
    el.style.display = "inline-block";
    el.textContent = msg;
    el.className = "status-badge " + (ok ? "ok" : "error");
  }

  function setHint(id, text) {
    const el = document.getElementById(id);
    if (!el) return;
    if (text) {
      el.hidden = false;
      el.textContent = text;
    } else {
      el.hidden = true;
      el.textContent = "";
    }
  }

  function formatFetchErrorPayload(data) {
    if (!data || typeof data !== "object") return null;
    if (typeof data.error === "string" && data.error) return data.error;
    const d = data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length && typeof d[0]?.msg === "string") {
      return d.map((x) => x.msg).join("; ");
    }
    return null;
  }

  function getFormat(panel) {
    const sel = document.querySelector(`.fmt-select[data-panel="${panel}"]`);
    return sel && sel.value ? sel.value : "bar";
  }

  function toggleVizPanel(panel, format) {
    const cw = document.querySelector(`[data-chart-wrap="${panel}"]`);
    const tw = document.querySelector(`[data-table-wrap="${panel}"]`);
    if (!cw || !tw) return;
    const isTable = format === "table";
    cw.classList.toggle("hidden", isTable);
    tw.classList.toggle("hidden", !isTable);
  }

  function destroyChart(key) {
    if (charts[key]) {
      charts[key].destroy();
      delete charts[key];
    }
  }

  function buildChart(panelKey, format, labels, values, datasetLabel, colors) {
    const idMap = {
      google: "googleChart",
      tv: "tvChart",
      wiki: "wikiChart",
      hn: "hnChart",
      tmdb: "tmdbChart",
      crypto: "cryptoChart",
      yt: "ytChart",
    };
    const canvas = document.getElementById(idMap[panelKey]);
    if (!canvas || !labels || !labels.length) {
      destroyChart(panelKey);
      return;
    }

    const n = Math.min(labels.length, format === "doughnut" ? 8 : 12);
    const L = labels.slice(0, n);
    const V = values.slice(0, n);
    const C = colors || L.map((_, i) => palette[i % palette.length]);

    destroyChart(panelKey);

    if (format === "doughnut") {
      charts[panelKey] = new Chart(canvas.getContext("2d"), {
        type: "doughnut",
        data: {
          labels: L,
          datasets: [{ data: V, backgroundColor: C, borderWidth: 0 }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "right", labels: { color: "#94a3b8", boxWidth: 12, font: { size: 10 } } },
          },
        },
      });
      return;
    }

    const horizontal = format === "hbar";
    const type = "bar";
    const ds = {
      label: datasetLabel,
      data: V,
      backgroundColor: C,
      borderRadius: 4,
    };

    const opts = JSON.parse(JSON.stringify(chartDefaults));
    if (horizontal) {
      opts.indexAxis = "y";
      opts.scales.x.beginAtZero = true;
    }

    charts[panelKey] = new Chart(canvas.getContext("2d"), {
      type,
      data: { labels: L, datasets: [ds] },
      options: {
        ...opts,
        plugins: { ...opts.plugins, legend: { display: false } },
      },
    });
  }

  function renderTable(wrapEl, columns, rows) {
    if (!wrapEl) return;
    wrapEl.innerHTML = "";
    if (!rows || !rows.length) {
      wrapEl.innerHTML = '<p class="empty" style="margin:0;padding:1rem">No rows.</p>';
      return;
    }
    const table = document.createElement("table");
    table.className = "data-table";
    const thead = document.createElement("thead");
    const trh = document.createElement("tr");
    columns.forEach((c) => {
      const th = document.createElement("th");
      th.textContent = c.label;
      trh.appendChild(th);
    });
    thead.appendChild(trh);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    rows.slice(0, 25).forEach((r) => {
      const tr = document.createElement("tr");
      columns.forEach((c) => {
        const td = document.createElement("td");
        if (c.link && r[c.link]) {
          const a = document.createElement("a");
          a.href = r[c.link];
          a.target = "_blank";
          a.rel = "noopener";
          a.textContent = r[c.key] != null ? String(r[c.key]) : "—";
          td.appendChild(a);
        } else {
          td.textContent = r[c.key] != null && r[c.key] !== "" ? String(r[c.key]) : "—";
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrapEl.appendChild(table);
  }

  function renderViz(panelKey, format, labels, values, datasetLabel, tableSpec) {
    toggleVizPanel(panelKey, format);
    const tw = document.querySelector(`[data-table-wrap="${panelKey}"]`);
    if (format === "table") {
      destroyChart(panelKey);
      if (tw) {
        if (tableSpec && tableSpec.columns) {
          renderTable(tw, tableSpec.columns, tableSpec.rows || []);
        } else {
          tw.innerHTML = '<p class="empty" style="margin:0;padding:1rem">No data.</p>';
        }
      }
      return;
    }
    buildChart(panelKey, format, labels, values, datasetLabel, tableSpec && tableSpec.colors);
  }

  function renderGrid(container, rows, type) {
    if (!container) return;
    container.innerHTML = "";
    if (!rows || !rows.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "No data for this source.";
      container.appendChild(empty);
      return;
    }
    rows.slice(0, 12).forEach((r) => {
      const card = document.createElement("div");
      card.className = "card";
      const title = document.createElement("div");
      title.className = "card-title";
      title.textContent = r.keyword || r.title || "—";
      const meta = document.createElement("div");
      meta.className = "card-meta";
      let metaTxt = "";
      if (type === "google") {
        metaTxt = `Momentum: ${typeof r.momentum === "number" ? r.momentum : "—"} | Latest: ${r.latest_value != null ? r.latest_value : "—"}`;
      } else if (type === "wiki") {
        metaTxt = `Views: ${r.views != null ? r.views : "—"}`;
      } else if (type === "hn") {
        metaTxt = `Score: ${r.score != null ? r.score : "—"}`;
      } else if (type === "tmdb") {
        metaTxt = `Rating: ${r.rating != null ? Number(r.rating).toFixed(1) : "—"}`;
      } else if (type === "crypto") {
        metaTxt = [r.symbol, r.rank != null ? `Rank ${r.rank}` : ""].filter(Boolean).join(" · ");
      } else if (type === "youtube") {
        metaTxt = `Views: ${r.views != null ? r.views : "—"}`;
      } else if (type === "tv") {
        metaTxt =
          r.rating != null
            ? `Rating: ${typeof r.rating === "number" && r.rating.toFixed ? r.rating.toFixed(2) : r.rating}`
            : `Count: ${r.count || 0}`;
      }
      meta.textContent = metaTxt;
      const desc = document.createElement("div");
      desc.className = "card-desc";
      if (type === "tv") {
        const s = r.summary || r.genres || r.latest_title || "";
        desc.textContent = s.length > 140 ? s.slice(0, 140) + "…" : s;
      } else if (type === "tmdb") {
        desc.textContent = (r.overview || "").slice(0, 140);
      } else if (type === "google") {
        desc.textContent = r.trend_direction ? `Trend: ${r.trend_direction}` : "";
      }
      card.appendChild(title);
      card.appendChild(meta);
      card.appendChild(desc);
      const linkUrl = r.url || r.official_site || r.latest_url;
      if (linkUrl && type !== "google") {
        const a = document.createElement("a");
        a.href = linkUrl;
        a.target = "_blank";
        a.rel = "noopener";
        a.className = "card-link";
        a.textContent = "Open";
        card.appendChild(a);
      }
      container.appendChild(card);
    });
  }

  async function loadStatus() {
    const strip = document.getElementById("statusStrip");
    try {
      const res = await fetch("/api/status");
      apiStatus = await res.json();
      if (strip) {
        strip.textContent = [
          apiStatus.youtube_configured ? "YouTube ready" : "YouTube: add key",
          apiStatus.tmdb_configured ? "TMDB ready" : "TMDB: add key",
        ].join(" · ");
      }
      setHint("hint-tmdb", apiStatus.tmdb_configured ? "" : "Set TMDB_API_KEY in your .env file to load movies and TV.");
      setHint("hint-youtube", apiStatus.youtube_configured ? "" : "Set YOUTUBE_API_KEY in your .env for charts and search.");
    } catch {
      if (strip) strip.textContent = "Status unavailable";
    }
  }

  async function loadPresets() {
    const presetSel = document.getElementById("googlePreset");
    const ytPreset = document.getElementById("ytPreset");
    try {
      const res = await fetch("/api/google_presets");
      const data = await res.json();
      const presets = data && Array.isArray(data.presets) ? data.presets : [];
      [presetSel, ytPreset].forEach((sel) => {
        if (!sel) return;
        sel.innerHTML = "";
        presets.forEach((p) => {
          const opt = document.createElement("option");
          opt.value = p;
          opt.textContent = p;
          sel.appendChild(opt);
        });
        if (sel.options.length) sel.selectedIndex = 0;
      });
    } catch (_) {}
  }

  function syncYtPresetWrap() {
    const mode = document.getElementById("ytMode");
    const wrap = document.getElementById("ytPresetWrap");
    if (!mode || !wrap) return;
    wrap.style.display = mode.value === "search" ? "" : "none";
  }

  async function loadGoogle() {
    const preset = document.getElementById("googlePreset")?.value || "";
    const timeframe = document.getElementById("googleTimeframe")?.value || "now 7-d";
    const geo = document.getElementById("googleGeo")?.value || "";
    const fmt = getFormat("google");
    try {
      let url = `/api/google_trends?preset=${encodeURIComponent(preset)}&timeframe=${encodeURIComponent(timeframe)}&geo=${encodeURIComponent(geo)}&lookback=4`;
      url = appendParam(url, "keywords", getTopicsRaw());
      const res = await fetch(url);
      const rows = await res.json();
      if (!Array.isArray(rows) || !rows.length) {
        destroyChart("google");
        renderViz("google", fmt, [], [], "Momentum", null);
        renderGrid(document.getElementById("googleGrid"), [], "google");
        setAppStatus("Google: no data", false);
        return;
      }
      const labels = rows.map((r) => String(r.keyword || ""));
      const values = rows.map((r) => (typeof r.momentum === "number" ? r.momentum : 0));
      const colors = rows.map((r) =>
        r.trend_direction === "up" ? "#34d399" : r.trend_direction === "down" ? "#f87171" : "#64748b"
      );
      renderViz("google", fmt, labels, values, "Momentum", {
        rows,
        columns: [
          { label: "Topic", key: "keyword" },
          { label: "Momentum", key: "momentum" },
          { label: "Latest", key: "latest_value" },
          { label: "Direction", key: "trend_direction" },
        ],
        colors,
      });
      renderGrid(document.getElementById("googleGrid"), rows, "google");
      setAppStatus("Connected", true);
    } catch {
      renderGrid(document.getElementById("googleGrid"), [], "google");
      setAppStatus("Error", false);
    }
  }

  async function loadTv() {
    const fmt = getFormat("tv");
    try {
      const url = appendParam("/api/tv_trends", "topics", getTopicsRaw());
      const res = await fetch(url);
      const rows = await res.json();
      if (!Array.isArray(rows)) {
        destroyChart("tv");
        toggleVizPanel("tv", fmt);
        renderGrid(document.getElementById("tvGrid"), [], "tv");
        return;
      }
      const top = rows.slice(0, 12);
      const labels = top.map((r) => String(r.keyword || "").slice(0, 28));
      const values = top.map((r) =>
        r.rating != null ? Number(r.rating) : Number(r.count || 0)
      );
      const lab = top.some((r) => r.rating != null) ? "Rating" : "Count";
      const tableRows = rows.map((r) => ({
        ...r,
        metric: r.rating != null ? r.rating : (r.count != null ? r.count : "—"),
        linkout: r.official_site || r.latest_url || "",
      }));
      renderViz("tv", fmt, labels, values, lab, {
        rows: tableRows,
        columns: [
          { label: "Title", key: "keyword" },
          { label: lab, key: "metric" },
          { label: "Open", key: "keyword", link: "linkout" },
        ],
      });
      renderGrid(document.getElementById("tvGrid"), rows, "tv");
    } catch {
      renderGrid(document.getElementById("tvGrid"), [], "tv");
    }
  }

  async function loadWiki() {
    const fmt = getFormat("wiki");
    try {
      const res = await fetch(appendParam("/api/wiki_trends?limit=40", "topics", getTopicsRaw()));
      const rows = await res.json();
      setHint("hint-wiki", "");
      if (!Array.isArray(rows) || !rows.length) {
        setHint("hint-wiki", "No Wikipedia data returned. Check your network or try again later.");
        destroyChart("wiki");
        toggleVizPanel("wiki", fmt);
        renderGrid(document.getElementById("wikiGrid"), [], "wiki");
        return;
      }
      const top = rows.slice(0, 12);
      const labels = top.map((r) => String(r.keyword || "").slice(0, 22));
      const values = top.map((r) => Number(r.views || 0));
      renderViz("wiki", fmt, labels, values, "Views", {
        rows,
        columns: [
          { label: "Article", key: "keyword" },
          { label: "Views", key: "views" },
          { label: "Rank", key: "rank" },
        ],
      });
      renderGrid(document.getElementById("wikiGrid"), rows, "wiki");
    } catch {
      setHint("hint-wiki", "Wikipedia request failed.");
      renderGrid(document.getElementById("wikiGrid"), [], "wiki");
    }
  }

  async function loadHn() {
    const fmt = getFormat("hn");
    try {
      const res = await fetch(appendParam("/api/hn_trends?limit=40", "topics", getTopicsRaw()));
      const rows = await res.json();
      if (!Array.isArray(rows) || !rows.length) {
        destroyChart("hn");
        toggleVizPanel("hn", fmt);
        renderGrid(document.getElementById("hnGrid"), [], "hn");
        return;
      }
      const top = rows.slice(0, 12);
      const labels = top.map((r) => String(r.keyword || "").slice(0, 20));
      const values = top.map((r) => Number(r.score || 0));
      renderViz("hn", fmt, labels, values, "Score", {
        rows,
        columns: [
          { label: "Story", key: "keyword" },
          { label: "Score", key: "score" },
          { label: "Open", key: "keyword", link: "url" },
        ],
      });
      renderGrid(document.getElementById("hnGrid"), rows, "hn");
    } catch {
      renderGrid(document.getElementById("hnGrid"), [], "hn");
    }
  }

  async function loadTmdb() {
    const kind = document.getElementById("tmdbKind")?.value || "movie";
    const fmt = getFormat("tmdb");
    try {
      let u = `/api/movie_trends?kind=${encodeURIComponent(kind)}&limit=24`;
      u = appendParam(u, "topics", getTopicsRaw());
      const res = await fetch(u);
      const rows = await res.json();
      if (!apiStatus.tmdb_configured) {
        destroyChart("tmdb");
        toggleVizPanel("tmdb", fmt);
        renderGrid(document.getElementById("tmdbGrid"), [], "tmdb");
        return;
      }
      if (!Array.isArray(rows) || !rows.length) {
        destroyChart("tmdb");
        toggleVizPanel("tmdb", fmt);
        renderGrid(document.getElementById("tmdbGrid"), [], "tmdb");
        return;
      }
      const top = rows.slice(0, 12);
      const labels = top.map((r) => String(r.keyword || "").slice(0, 22));
      const values = top.map((r) => Number(r.rating != null ? r.rating : 0));
      renderViz("tmdb", fmt, labels, values, "Rating", {
        rows,
        columns: [
          { label: "Title", key: "keyword" },
          { label: "Rating", key: "rating" },
          { label: "Votes", key: "votes" },
          { label: "TMDB", key: "keyword", link: "url" },
        ],
      });
      renderGrid(document.getElementById("tmdbGrid"), rows, "tmdb");
    } catch {
      renderGrid(document.getElementById("tmdbGrid"), [], "tmdb");
    }
  }

  async function loadCrypto() {
    const fmt = getFormat("crypto");
    try {
      const res = await fetch(appendParam("/api/crypto_trends?limit=22", "topics", getTopicsRaw()));
      const rows = await res.json();
      setHint("hint-crypto", "");
      if (!Array.isArray(rows) || !rows.length) {
        setHint("hint-crypto", "CoinGecko returned no data (rate limit or network). Retry in a minute.");
        destroyChart("crypto");
        toggleVizPanel("crypto", fmt);
        renderGrid(document.getElementById("cryptoGrid"), [], "crypto");
        return;
      }
      const top = rows.slice(0, 12);
      const labels = top.map((r) => String(r.keyword || r.symbol || "").slice(0, 18));
      const values = top.map((r) => Math.max(1, Number(r.score || 1)));
      renderViz("crypto", fmt, labels, values, "Score", {
        rows,
        columns: [
          { label: "Name", key: "keyword" },
          { label: "Symbol", key: "symbol" },
          { label: "Rank", key: "rank" },
          { label: "Link", key: "keyword", link: "url" },
        ],
      });
      renderGrid(document.getElementById("cryptoGrid"), rows, "crypto");
    } catch {
      setHint("hint-crypto", "CoinGecko request failed.");
      renderGrid(document.getElementById("cryptoGrid"), [], "crypto");
    }
  }

  async function loadYoutube() {
    syncYtPresetWrap();
    const mode = document.getElementById("ytMode")?.value || "trending";
    const region = document.getElementById("ytRegion")?.value || "US";
    const preset = document.getElementById("ytPreset")?.value || "";
    const fmt = getFormat("yt");
    const topics = getTopicsRaw();
    if (!apiStatus.youtube_configured) {
      setHint("hint-youtube", "Set YOUTUBE_API_KEY in .env (project root) and restart the server.");
      destroyChart("yt");
      toggleVizPanel("yt", fmt);
      renderGrid(document.getElementById("ytGrid"), [], "youtube");
      return;
    }
    try {
      let url = `/api/youtube_trends?mode=${encodeURIComponent(mode)}&region=${encodeURIComponent(region)}&max_results=24`;
      if (mode === "search") {
        url += `&days=30`;
        if (topics) {
          url += `&keywords=${encodeURIComponent(topics)}`;
        } else if (preset) {
          url += `&preset=${encodeURIComponent(preset)}`;
        }
      }
      const res = await fetch(url);
      let data = {};
      try {
        data = await res.json();
      } catch (_) {
        data = {};
      }
      if (!res.ok) {
        const msg = formatFetchErrorPayload(data) || `YouTube request failed (${res.status}).`;
        setHint("hint-youtube", msg);
        destroyChart("yt");
        toggleVizPanel("yt", fmt);
        renderGrid(document.getElementById("ytGrid"), [], "youtube");
        return;
      }
      const rows = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
      const apiErr = typeof data?.error === "string" && data.error ? data.error : null;
      setHint("hint-youtube", apiErr || "");
      if (!Array.isArray(rows) || !rows.length) {
        destroyChart("yt");
        toggleVizPanel("yt", fmt);
        renderGrid(document.getElementById("ytGrid"), [], "youtube");
        if (!apiErr) {
          setHint(
            "hint-youtube",
            mode === "search"
              ? "No videos returned for these keywords in the last 30 days. Switch to Most popular, change topics, or check the server terminal for API errors."
              : "No trending videos returned for this region (quota, API error, or key restrictions—see message above if any)."
          );
        }
        return;
      }
      setHint("hint-youtube", "");
      const top = rows.slice(0, 12);
      const labels = top.map((r) => String(r.keyword || r.title || "").slice(0, 22));
      const values = top.map((r) => Number(r.views || 0));
      renderViz("yt", fmt, labels, values, "Views", {
        rows,
        columns: [
          { label: "Title", key: "keyword" },
          { label: "Views", key: "views" },
          { label: "Channel", key: "author" },
          { label: "Watch", key: "keyword", link: "url" },
        ],
      });
      renderGrid(document.getElementById("ytGrid"), rows, "youtube");
      window.setTimeout(resizeVisibleCharts, 100);
    } catch {
      setHint("hint-youtube", "Request failed. Check the server is running and try again.");
      renderGrid(document.getElementById("ytGrid"), [], "youtube");
    }
  }

  function refreshAll() {
    saveTopics();
    loadGoogle();
    loadTv();
    loadWiki();
    loadHn();
    loadTmdb();
    loadCrypto();
    loadYoutube();
  }

  const DASH_CARD_COLLAPSE_MS = 380;

  function resizeVisibleCharts() {
    Object.keys(charts).forEach((k) => {
      const c = charts[k];
      if (c && typeof c.resize === "function") {
        try {
          c.resize();
        } catch (e) {
          /* ignore */
        }
      }
    });
  }

  function syncDashboardCardAria(card) {
    const btn = card.querySelector(".dash-card-toggle");
    if (!btn) return;
    const expanded = !card.classList.contains("is-collapsed");
    btn.setAttribute("aria-expanded", expanded ? "true" : "false");
  }

  function scheduleChartResize() {
    window.setTimeout(resizeVisibleCharts, DASH_CARD_COLLAPSE_MS);
  }

  function initDashboardCollapsibles() {
    document.querySelectorAll("[data-dashboard-card]").forEach((card) => {
      syncDashboardCardAria(card);
    });

    document.querySelector(".dashboard-grid")?.addEventListener("click", (e) => {
      const toggle = e.target.closest(".dash-card-toggle");
      if (!toggle) return;
      const card = toggle.closest("[data-dashboard-card]");
      if (!card) return;
      card.classList.toggle("is-collapsed");
      syncDashboardCardAria(card);
      if (!card.classList.contains("is-collapsed")) scheduleChartResize();
    });

    document.getElementById("expandAllCards")?.addEventListener("click", () => {
      document.querySelectorAll("[data-dashboard-card]").forEach((card) => {
        card.classList.remove("is-collapsed");
        syncDashboardCardAria(card);
      });
      scheduleChartResize();
    });

    document.getElementById("collapseAllCards")?.addEventListener("click", () => {
      document.querySelectorAll("[data-dashboard-card]").forEach((card) => {
        card.classList.add("is-collapsed");
        syncDashboardCardAria(card);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadTopicsFromStorage();
    initDashboardCollapsibles();
    loadStatus().then(() => {
      loadPresets().then(() => {
        refreshAll();
      });
    });

    document.getElementById("applyTopics")?.addEventListener("click", refreshAll);
    document.getElementById("resetTopics")?.addEventListener("click", () => {
      const el = document.getElementById("topicInput");
      if (el) el.value = DEFAULT_TOPICS;
      refreshAll();
    });

    document.getElementById("googleApply")?.addEventListener("click", loadGoogle);
    document.getElementById("tmdbApply")?.addEventListener("click", loadTmdb);
    document.getElementById("ytApply")?.addEventListener("click", loadYoutube);
    document.getElementById("ytMode")?.addEventListener("change", () => {
      syncYtPresetWrap();
      loadYoutube();
    });

    document.querySelectorAll(".fmt-select").forEach((sel) => {
      sel.addEventListener("change", () => {
        const panel = sel.getAttribute("data-panel");
        const map = {
          google: loadGoogle,
          tv: loadTv,
          wiki: loadWiki,
          hn: loadHn,
          tmdb: loadTmdb,
          crypto: loadCrypto,
          yt: loadYoutube,
        };
        if (panel && map[panel]) map[panel]();
      });
    });

    document.querySelectorAll("[data-refresh]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const k = btn.getAttribute("data-refresh");
        const map = {
          google: loadGoogle,
          tv: loadTv,
          wiki: loadWiki,
          hn: loadHn,
          tmdb: loadTmdb,
          crypto: loadCrypto,
          yt: loadYoutube,
        };
        if (k && map[k]) map[k]();
      });
    });
  });
})();
