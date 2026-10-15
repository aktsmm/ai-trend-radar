// Renders the 2-slide downloadable brief (deck/1) to HTML. Used by site/deck.html (PDF / PNG build). Source of truth: t.deck.
(function () {
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const md = s => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>");
  const VER = { verified: "検証済み", partially_verified: "一部検証", unverified: "未検証" };
  const ICONS = {
    terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M12 15h5"/>',
    cloud: '<path d="M7 18a4 4 0 0 1-.5-8A6 6 0 0 1 18 9a4.5 4.5 0 0 1-.5 9z"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M4 18l5-5 4 4 3-3 4 4"/>',
    spark: '<path d="M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"/>',
    chip: '<rect x="7" y="7" width="10" height="10" rx="1"/><path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4"/>',
    layers: '<path d="M12 3l9 5-9 5-9-5zM3 13l9 5 9-5"/>', check: '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    plug: '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4"/>', shield: '<path d="M12 3l8 3v6c0 4.5-3.2 7.5-8 9-4.8-1.5-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>'
  };
  const ic = n => `<div class="d-icon"><svg viewBox="0 0 24 24">${ICONS[n] || ICONS.check}</svg></div>`;

  function head(t, n, title) {
    const label = t.trend_label === "baseline" ? "今週の注目" : "上昇中";
    return `<div class="d-head"><div class="d-chips"><span class="d-chip">${esc(t.category)}</span>${t.vendor ? `<span class="d-chip alt">${esc(t.vendor)}</span>` : ""}<span class="d-chip badge">${label}</span><span class="d-pager">${esc(t.keyword)} ・ ${n}/2</span></div><h1>${esc(title)}</h1></div>`;
  }
  function foot(t, refs) {
    const ver = (t.verification && t.verification.status) || "unverified";
    const src = t.deck.sources.filter(s => refs.includes(s.id));
    return `<div class="d-foot"><div class="d-src">${src.map(s => `<div><b>[${esc(s.id)}]</b> ${esc(s.title)} <span class="u">${esc(s.url)}</span>${s.date ? ` <span class="dt">(${esc(s.date)})</span>` : ""}</div>`).join("")}</div><div class="d-ver ${ver}">${VER[ver]}<small>要約は自動生成+一次情報で確認</small></div></div>`;
  }
  function slide1(t) {
    const o = t.deck.overview, s = t.slides[0] || {};
    const n = [...o.stat.value].length, cls = n > 12 ? "xs" : n > 8 ? "sm" : "";
    return `<div class="dslide cat-${esc(t.category)}">${head(t, 1, s.title || t.keyword)}
      <div class="d-take">${esc(o.takeaway)}</div>
      <div class="d-body s1">
        <div class="d-col"><div class="d-panel">${ic(s.icon)}<div class="d-stat ${cls}">${esc(o.stat.value)}</div><div class="d-statl">${esc(o.stat.label)}</div></div>
          <div class="d-flow"><h3>しくみ</h3>${o.steps.map(x => `<div class="d-step">${esc(x)}</div>`).join('<div class="d-arrow">▼</div>')}</div></div>
        <div class="d-col"><h2>何が変わる・何が起きた</h2>${o.changes.map((c, i) => `<div class="d-card"><span class="d-num">${i + 1}</span><span>${md(c)}</span></div>`).join("")}</div>
        <div class="d-col"><h2>要点</h2><table class="d-facts">${o.facts.map(f => `<tr><th>${esc(f.k)}</th><td>${esc(f.v)}</td></tr>`).join("")}</table></div>
      </div>${foot(t, o.refs)}</div>`;
  }
  function slide2(t) {
    const m = t.deck.impact;
    return `<div class="dslide cat-${esc(t.category)}">${head(t, 2, `${(t.slides[0] || {}).title || t.keyword}`)}
      <div class="d-aud"><b>想定する人</b> ${esc(m.audience)}</div>
      <div class="d-body s2">
        <div class="d-box"><h2>嬉しいこと</h2><ul>${m.benefits.map(x => `<li>${md(x)}</li>`).join("")}</ul></div>
        <div class="d-box"><h2>使い方・始め方</h2><ol>${m.how_to.map(x => `<li>${md(x)}</li>`).join("")}</ol></div>
        <div class="d-box warn"><h2>注意点・制限</h2><ul>${m.caveats.map(x => `<li>${md(x)}</li>`).join("")}</ul></div>
        <div class="d-box"><h2>用語メモ</h2><dl>${m.terms.map(x => `<dt>${esc(x.t)}</dt><dd>${esc(x.d)}</dd>`).join("")}</dl></div>
      </div>${foot(t, m.refs)}</div>`;
  }
  function cover(D, n) {
    return `<div class="dslide cover"><div class="cv-main"><div class="cv-kicker">AI Trend Radar</div><h1>今週の AI トレンド・ブリーフ</h1>
      <div class="cv-sub">${esc(D.window.label)} ・ ${esc(D.window.from)} 〜 ${esc(D.window.to)}</div>
      <div class="cv-stat"><b>${n}</b> 件を一次情報で確認して掲載</div></div>
      <div class="cv-note">各キーワード 2 枚(概要 / 影響・使い方)。内容は公式の一次情報で確認したもので、要約は AI の下書きを照合して掲載しています。ベンダーが発表した数字は独自には検証していません。</div></div>`;
  }
  function toc(D, list) {
    return `<div class="dslide toc"><div class="d-head"><h1>目次</h1></div><div class="toc-body">${list.map((t, i) => `<div class="toc-row"><span class="toc-no">${i + 1}</span><span class="toc-kw">${esc(t.keyword)}</span><span class="d-chip alt">${esc(t.category)}</span><span class="toc-tk">${esc((t.slides[0] || {}).title || t.deck.overview.takeaway)}</span><span class="toc-pg">p.${3 + i * 2}</span></div>`).join("")}</div></div>`;
  }
  window.renderWeekly = (D, list) => cover(D, list.length) + toc(D, list) + list.map(t => renderDeck(t, 0) + renderDeck(t, 1)).join("");
  window.renderDeck = (t, n) => (n === 0 ? slide1(t) : slide2(t));
})();
