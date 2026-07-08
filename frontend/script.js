(function () {
  const TOPICS_KEY = "trendscope_topics";
  const DEFAULT_TOPICS = "AI, Machine Learning, Bitcoin, Climate Change";

  // Modern Cyberpunk color palette matching CSS variables
  const palette = ["#8b5cf6", "#06b6d4", "#ec4899", "#10b981", "#f97316", "#3b82f6", "#a855f7", "#14b8a6"];

  const chartText = {
    color: "#94a3b8",
  };

  const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: chartText.color, font: { family: "Outfit", size: 11 } },
      },
    },
    scales: {
      x: {
        ticks: { color: chartText.color, font: { family: "Plus Jakarta Sans" }, maxRotation: 45, minRotation: 0 },
        grid: { color: "rgba(255, 255, 255, 0.04)" },
      },
      y: {
        beginAtZero: true,
        ticks: { color: chartText.color, font: { family: "Plus Jakarta Sans" } },
        grid: { color: "rgba(255, 255, 255, 0.04)" },
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
    return sel && sel.value ? sel.value : "hbar";
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
          datasets: [{ data: V, backgroundColor: C, borderWidth: 1, borderColor: "rgba(0,0,0,0.3)" }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "right", labels: { color: chartText.color, boxWidth: 10, font: { family: "Plus Jakarta Sans", size: 10 } } },
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
      borderRadius: 6,
      borderWidth: 0,
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
      wrapEl.innerHTML = '<p class="empty" style="margin:0;padding:1.5rem">No records found.</p>';
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
          tw.innerHTML = '<p class="empty" style="margin:0;padding:1.5rem">No data available.</p>';
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
      empty.textContent = "No data cards for this source.";
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
        metaTxt = `Views: ${r.views != null ? Number(r.views).toLocaleString() : "—"}`;
      } else if (type === "hn") {
        metaTxt = `Score: ${r.score != null ? r.score : "—"}`;
      } else if (type === "tmdb") {
        metaTxt = `Rating: ${r.rating != null ? Number(r.rating).toFixed(1) : "—"}`;
      } else if (type === "crypto") {
        metaTxt = [r.symbol, r.rank != null ? `Rank ${r.rank}` : ""].filter(Boolean).join(" · ");
      } else if (type === "youtube") {
        metaTxt = `Views: ${r.views != null ? Number(r.views).toLocaleString() : "—"}`;
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
        desc.textContent = r.trend_direction ? `Trend Direction: ${r.trend_direction}` : "";
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
        a.textContent = "Open Link ↗";
        card.appendChild(a);
      }
      container.appendChild(card);
    });
  }

  // Synchronize Sidebar Status Console LEDs
  async function loadStatus() {
    try {
      const res = await fetch("/api/status");
      apiStatus = await res.json();
      
      const ledYt = document.getElementById("led-youtube");
      const ledTmdb = document.getElementById("led-tmdb");
      const ledWiki = document.getElementById("led-wiki");
      const ledHn = document.getElementById("led-hn");
      const ledCrypto = document.getElementById("led-coingecko");
      const ledGoogle = document.getElementById("led-google");
      
      if (ledYt) {
        ledYt.className = "led-indicator " + (apiStatus.youtube_configured ? "active" : "inactive");
      }
      if (ledTmdb) {
        ledTmdb.className = "led-indicator " + (apiStatus.tmdb_configured ? "active" : "inactive");
      }
      if (ledWiki) {
        ledWiki.className = "led-indicator " + (apiStatus.wikipedia_enabled ? "active" : "inactive");
      }
      if (ledHn) {
        ledHn.className = "led-indicator " + (apiStatus.hackernews_enabled ? "active" : "inactive");
      }
      if (ledCrypto) {
        ledCrypto.className = "led-indicator " + (apiStatus.coingecko_enabled ? "active" : "inactive");
      }
      if (ledGoogle) {
        ledGoogle.className = "led-indicator active";
      }

      setHint("hint-tmdb", apiStatus.tmdb_configured ? "" : "Set TMDB_API_KEY in your .env file to load movies and TV.");
      setHint("hint-youtube", apiStatus.youtube_configured ? "" : "Set YOUTUBE_API_KEY in your .env for charts and search.");
    } catch {
      document.querySelectorAll(".led-indicator").forEach((led) => {
        led.className = "led-indicator inactive";
      });
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

  // ML Predictor Keywords dropdown sync
  function updateMlKeywords() {
    const select = document.getElementById("mlKeywordSelect");
    if (!select) return;
    select.innerHTML = "";
    
    const topics = getTopicsRaw();
    const list = topics ? topics.split(",") : DEFAULT_TOPICS.split(",");
    
    list.forEach((item) => {
      const kw = item.trim();
      if (!kw) return;
      const opt = document.createElement("option");
      opt.value = kw;
      opt.textContent = kw;
      select.appendChild(opt);
    });
  }

  async function runPrediction() {
    const select = document.getElementById("mlKeywordSelect");
    const resultDiv = document.getElementById("mlPredictionResult");
    const msgDiv = document.getElementById("mlPredictorMessage");
    
    if (!select || !select.value) return;
    
    const kw = select.value.trim();
    const runBtn = document.getElementById("runMlPredictor");
    if (runBtn) {
      runBtn.disabled = true;
      runBtn.textContent = "Calculating Signal...";
    }
    
    try {
      const res = await fetch(`/api/predictions/google_spike?keyword=${encodeURIComponent(kw)}&delta=1.0`);
      const data = await res.json();
      
      if (runBtn) {
        runBtn.disabled = false;
        runBtn.textContent = "Calculate Spike Probability";
      }
      
      if (data.error) {
        if (resultDiv) resultDiv.style.display = "none";
        if (msgDiv) {
          msgDiv.style.display = "block";
          msgDiv.innerHTML = `⚠️ <strong>Model Error:</strong> ${data.error}<br><span style="font-size:0.8rem;opacity:0.8">Ensure the baseline predictor has been trained for this keyword. Run: <code>python -m src.ml.train_google_spike --keywords "${kw}"</code></span>`;
        }
        return;
      }
      
      // Success
      if (msgDiv) msgDiv.style.display = "none";
      if (resultDiv) resultDiv.style.display = "grid";
      
      const prob = data.spike_probability != null ? data.spike_probability : 0.0;
      const pct = Math.round(prob * 100);
      
      const fill = document.getElementById("mlDialFill");
      const probVal = document.getElementById("mlProbValue");
      const kwVal = document.getElementById("mlKeywordVal");
      const deltaVal = document.getElementById("mlDeltaVal");
      const modelVal = document.getElementById("mlModelVal");
      
      if (probVal) probVal.textContent = pct;
      if (kwVal) kwVal.textContent = data.keyword || kw;
      if (deltaVal) deltaVal.textContent = data.delta != null ? data.delta.toFixed(1) : "1.0";
      if (modelVal) {
        const file = data.model_path ? data.model_path.split(/[\\/]/).pop() : "google_spike_model.joblib";
        modelVal.textContent = file;
        modelVal.title = data.model_path || "";
      }
      
      if (fill) {
        // SVG circle radius is 60, circumference is 377
        const offset = 377 - (377 * pct) / 100;
        fill.style.strokeDashoffset = offset;
      }
    } catch (e) {
      if (runBtn) {
        runBtn.disabled = false;
        runBtn.textContent = "Calculate Spike Probability";
      }
      if (resultDiv) resultDiv.style.display = "none";
      if (msgDiv) {
        msgDiv.style.display = "block";
        msgDiv.textContent = "Prediction endpoint returned an invalid response. Ensure backend server is running.";
      }
    }
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
        return;
      }
      const labels = rows.map((r) => String(r.keyword || ""));
      const values = rows.map((r) => (typeof r.momentum === "number" ? r.momentum : 0));
      const colors = rows.map((r) =>
        r.trend_direction === "up" ? "#10b981" : r.trend_direction === "down" ? "#ef4444" : "#64748b"
      );
      renderViz("google", fmt, labels, values, "Momentum", {
        rows,
        columns: [
          { label: "Topic", key: "keyword" },
          { label: "Momentum", key: "momentum" },
          { label: "Latest Value", key: "latest_value" },
          { label: "Direction", key: "trend_direction" },
        ],
        colors,
      });
      renderGrid(document.getElementById("googleGrid"), rows, "google");
    } catch {
      renderGrid(document.getElementById("googleGrid"), [], "google");
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
          { label: "Official Site", key: "keyword", link: "linkout" },
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
        setHint("hint-wiki", "No Wikipedia articles matched current filters.");
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
          { label: "TMDB Page", key: "keyword", link: "url" },
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
        setHint("hint-crypto", "CoinGecko returned no data (rate limit or network).");
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
          { label: "Info Link", key: "keyword", link: "url" },
        ],
      });
      renderGrid(document.getElementById("cryptoGrid"), rows, "crypto");
    } catch {
      setHint("hint-crypto", "CoinGecko API is offline.");
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
        const msg = formatFetchErrorPayload(data) || `YouTube request failed.`;
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
        return;
      }
      const top = rows.slice(0, 12);
      const labels = top.map((r) => String(r.keyword || r.title || "").slice(0, 22));
      const values = top.map((r) => Number(r.views || 0));
      renderViz("yt", fmt, labels, values, "Views", {
        rows,
        columns: [
          { label: "Title", key: "keyword" },
          { label: "Views", key: "views" },
          { label: "Channel", key: "author" },
          { label: "Watch Video", key: "keyword", link: "url" },
        ],
      });
      renderGrid(document.getElementById("ytGrid"), rows, "youtube");
      window.setTimeout(resizeVisibleCharts, 100);
    } catch {
      setHint("hint-youtube", "YouTube communication error.");
      renderGrid(document.getElementById("ytGrid"), [], "youtube");
    }
  }

  function refreshAll() {
    saveTopics();
    updateMlKeywords();
    loadGoogle();
    loadTv();
    loadWiki();
    loadHn();
    loadTmdb();
    loadCrypto();
    loadYoutube();
  }

  const DASH_CARD_COLLAPSE_MS = 400;

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

    // ML Predictor Hooks
    document.getElementById("runMlPredictor")?.addEventListener("click", runPrediction);
    
    // Background snapshot run triggered by Retrain
    document.getElementById("refreshMlPredictor")?.addEventListener("click", async () => {
      const btn = document.getElementById("refreshMlPredictor");
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Snapshot in Progress...";
      try {
        const res = await fetch("/api/snapshots/run_google", { method: "POST" });
        if (res.ok) {
          const data = await res.json();
          alert(`Successfully executed Google Snapshot (ID: ${data.snapshot_id}). Note: To update ML models on this new snapshot data, run "python -m src.ml.train_google_spike" in your system terminal.`);
          updateMlKeywords();
        } else {
          alert("Could not start background snapshot run.");
        }
      } catch {
        alert("Server communication error.");
      } finally {
        btn.disabled = false;
        btn.textContent = originalText;
      }
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
