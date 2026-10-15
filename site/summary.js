// Week summary infographic (one image for the whole week). Source of truth: window.TRENDS (trends with deck, themes, official_highlights).
(function () {
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const CAT = { model: "モデル", "dev-tool": "開発ツール", "local-runtime": "ローカル実行", hardware: "ハードウェア", research: "研究", "github-trending": "GitHub" };
  const COL = { model: "#7a3db8", "dev-tool": "#0b7285", "local-runtime": "#c2410c", hardware: "#2f6f3e", research: "#a1235b", "github-trending": "#475569" };
  const CONF = { high: "確度 高", medium: "確度 中", low: "確度 低" };

  window.renderSummary = function (D) {
    const pub = D.trends.filter(t => t.deck), th = (D.themes || []).slice(0, 4), hl = (D.official_highlights || []).length;
    const by = {};
    pub.forEach(t => { by[t.category] = (by[t.category] || 0) + 1; });
    const cats = Object.keys(by).sort((a, b) => by[b] - by[a]);
    const max = Math.max(1, ...Object.values(by));
    const vendors = new Set(pub.map(t => t.vendor).filter(Boolean)).size;
    const name = e => (D.trends.find(t => t.entity_id === e) || { keyword: e }).keyword;
    const w = D.window;
    return `<div class="sm">
      <div class="sm-head"><div><div class="sm-kick">AI Trend Radar</div><h1>今週の AI は、こんな 1 週間でした</h1></div><div class="sm-week">${esc(w.label)}<small>${esc(w.from)} 〜 ${esc(w.to)}</small></div></div>
      <div class="sm-body">
        <div class="sm-left">
          <div class="sm-nums"><div><b>${pub.length}</b><span>件を一次情報で確認</span></div><div><b>${hl}</b><span>件の公式発表</span></div><div><b>${vendors || "-"}</b><span>社・団体</span></div></div>
          <h2>分野の内訳</h2>
          ${cats.map(c => `<div class="sm-bar"><span class="n">${esc(CAT[c] || c)}</span><span class="t"><i style="width:${Math.round(by[c] / max * 100)}%;background:${COL[c] || "#475569"}"></i></span><span class="v">${by[c]}</span></div>`).join("")}
          <h2 class="sm-h2b">今週の主な出来事</h2>
          <ul class="sm-list">${pub.slice(0, 9).map(t => `<li><i style="background:${COL[t.category] || "#475569"}"></i><b>${esc(t.keyword)}</b> ${esc(((t.slides || [])[0] || {}).title || "")}</li>`).join("")}</ul>
        </div>
        <div class="sm-right">
          <h2>今週のテーマ <small>共通する背景の見立て(AI の解釈)</small></h2>
          <div class="sm-themes">${th.map((x, i) => `<div class="sm-th"><div class="no">${i + 1}</div><div><h3>${esc(x.title)} <em>${esc(CONF[x.confidence])}</em></h3><p>${esc(x.summary)}</p><p class="bgl">${esc(x.background[0])}</p><div class="ch">${x.entities.map(e => `<span>${esc(name(e))}</span>`).join("")}</div></div></div>`).join("") || `<div class="sm-th"><div><p>今週はテーマをまだ作成していません。</p></div></div>`}</div>
        </div>
      </div>
      <div class="sm-foot"><b>注目の項目</b> ${pub.slice(0, 8).map(t => `<span class="sm-pill" style="--c:${COL[t.category] || "#475569"}">${esc(t.keyword)}</span>`).join("")}</div>
    </div>`;
  };
})();
