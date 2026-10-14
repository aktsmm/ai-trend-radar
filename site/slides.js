// Renders one slide (slides[] JSON is the source of truth) to an HTML string. Used by site/index.html and site/slide.html (PNG build).
(function () {
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const md = s => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>");
  const ICONS = { // original, minimal line icons (no third-party assets)
    terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M12 15h5"/>',
    cycle: '<path d="M20 8a8 8 0 0 0-14-2M4 4v4h4M4 16a8 8 0 0 0 14 2M20 20v-4h-4"/>',
    plug: '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4"/>',
    shield: '<path d="M12 3l8 3v6c0 4.5-3.2 7.5-8 9-4.8-1.5-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    cloud: '<path d="M7 18a4 4 0 0 1-.5-8A6 6 0 0 1 18 9a4.5 4.5 0 0 1-.5 9z"/>',
    lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M4 18l5-5 4 4 3-3 4 4"/>',
    chip: '<rect x="7" y="7" width="10" height="10" rx="1"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/>',
    spark: '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/>',
    layers: '<path d="M12 3l9 5-9 5-9-5zM3 13l9 5 9-5"/>'
  };
  const VER = { verified: "検証済み", partially_verified: "一部検証", unverified: "未検証" };
  const icon = n => `<div class="icon"><svg viewBox="0 0 24 24">${ICONS[n] || ICONS.check}</svg></div>`;

  function panel(s) {
    if (s.diagram_type === "stat" && s.stat) {
      const n = [...s.stat.value].length, cls = n > 12 ? "xs" : n > 8 ? "sm" : "";
      return `<div class="panel">${icon(s.icon)}<div class="stat-value ${cls}">${esc(s.stat.value)}</div><div class="stat-label">${esc(s.stat.label)}</div></div>`;
    }
    if (s.diagram_type === "flow" && s.steps) {
      return `<div class="panel"><div class="steps">${s.steps.map(x => `<div class="step">${esc(x)}</div>`).join('<div class="arrow">▼</div>')}</div></div>`;
    }
    return "";
  }

  function infographic(t, s, i) {
    const ver = (t.verification && t.verification.status) || "unverified";
    const badge = t.trend_label === "baseline" ? "今週の注目" : "上昇中";
    const n = [...s.stat.value].length, cls = n > 12 ? "xs" : n > 8 ? "sm" : "";
    return `<div class="slide infog cat-${esc(t.category)}">
      <div class="head">
        <div class="chips"><span class="chip">${esc(t.category)}</span>${t.tags.slice(1).map(x => `<span class="chip alt">${esc(x)}</span>`).join("")}<span class="chip badge">${badge}</span><span class="pager">${esc(t.keyword)}</span></div>
        <h1>${esc(s.title)}</h1>
      </div>
      <div class="ibody">
        <div class="iside">
          <div class="panel">${icon(s.icon)}<div class="stat-value ${cls}">${esc(s.stat.value)}</div><div class="stat-label">${esc(s.stat.label)}</div></div>
          <div class="steps">${s.steps.map(x => `<div class="step">${esc(x)}</div>`).join('<div class="arrow">▼</div>')}</div>
        </div>
        <div class="points">${s.points.map((p, k) => `<div class="pt p${k}"><div class="ph">${esc(p.h)}</div><div class="pt-t">${md(p.t)}</div></div>`).join("")}</div>
      </div>
      <div class="foot"><span>公式:</span><span class="url">${esc(s.official_url)}</span>${s.source_date ? `<span class="date">出典日 ${esc(s.source_date)}</span>` : ""}<span class="ver ${ver}">${VER[ver] || ver}</span></div>
    </div>`;
  }

  window.renderSlide = function (t, i) {
    const s = t.slides[i];
    if (s.diagram_type === "infographic") return infographic(t, s, i);
    const two = s.diagram_type !== "checklist";
    const ver = (t.verification && t.verification.status) || "unverified";
    const date = s.source_date || "";
    const badge = t.trend_label === "baseline" ? "今週の注目" : "上昇中";
    const list = two
      ? `<ul class="bullets">${s.bullets.map(b => `<li>${md(b)}</li>`).join("")}</ul>`
      : `<ol class="cards n${s.bullets.length}">${s.bullets.map((b, k) => `<li><span class="num">${k + 1}</span><span>${md(b)}</span></li>`).join("")}</ol>`;
    return `<div class="slide cat-${esc(t.category)}">
      <div class="head">
        <div class="chips"><span class="chip">${esc(t.category)}</span>${t.tags.slice(1).map(x => `<span class="chip alt">${esc(x)}</span>`).join("")}<span class="chip badge">${badge}</span><span class="pager">${esc(t.keyword)} ・ ${i + 1}/${t.slides.length}</span></div>
        <h1>${esc(s.title)}</h1>
      </div>
      <div class="body ${two ? "" : "single"}">
        ${list}
        ${two ? panel(s) : ""}
      </div>
      <div class="foot"><span>公式:</span><span class="url">${esc(s.official_url)}</span>${date ? `<span class="date">出典日 ${esc(date)}</span>` : ""}<span class="ver ${ver}">${VER[ver] || ver}</span></div>
    </div>`;
  };
})();
