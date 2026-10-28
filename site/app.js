const D = window.TRENDS, CATS = ["model","dev-tool","local-runtime","hardware","research","github-trending"];
let cat = "all", opener = null;
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const $ = id => document.getElementById(id);
const link = (u, label) => `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(label || u)}</a>`;
const published = D.trends.filter(t => t.deck), cands = D.trends.filter(t => !t.deck);
const ageDays = (Date.now() - Date.parse(D.last_successful_report_at)) / 86400000;
if (ageDays > 9 && !location.pathname.includes("/w/")) { const w = document.createElement("p"); w.className = "stale"; w.setAttribute("role", "alert"); w.textContent = `注意: データの最終更新が ${Math.floor(ageDays)} 日前です。取得または更新が止まっている可能性があります(最新の状態は api/v1/health.json)。`; document.querySelector("main").prepend(w); }
$("period").textContent = `対象期間 ${D.window.from} 〜 ${D.window.to}(${D.window.label}${D.window.partial ? "・集計途中" : ""}) / データ更新 ${D.last_successful_report_at.slice(0,16).replace("T"," ")} UTC` + (D.baseline.is_baseline ? ` / 蓄積 ${D.baseline.snapshots} 日分のため「今週の注目」表示` : "");

const f = $("filters");
["all", ...CATS].forEach(c => {
  const b = document.createElement("button");
  b.type = "button"; b.textContent = c === "all" ? "すべて" : c; b.dataset.c = c; b.setAttribute("aria-pressed", c === "all");
  b.onclick = () => { cat = c; render(); };
  f.appendChild(b);
});
$("q").oninput = render; $("cand").onchange = render;
const excluded = new Set();  // unchecked cards; everything visible is checked by default
let lastSig = "";
[...new Set(published.map(t => t.kind))].sort().forEach(k => $("kindSel").add(new Option(`種類: ${k}`, k)));
[...new Set(published.map(t => t.vendor).filter(Boolean))].sort().forEach(v => $("vendorSel").add(new Option(`提供元: ${v}`, v)));
$("kindSel").onchange = $("vendorSel").onchange = render;

const hay = t => [t.keyword, t.vendor, t.category, ...(t.tags || []), t.digest ? t.digest.summary.join(" ") : t.summary].join(" ").toLowerCase();
const box = (h, items, cls) => items && items.length ? `<div class="box ${cls || ""}"><h3>${h}</h3><ul>${items.map(x => `<li>${esc(x)}</li>`).join("")}</ul></div>` : "";
function badges(t) {
  const v = t.verification.status;
  const urls = t.official_urls.map(u => t.url_checks && t.url_checks[u]).filter(Boolean);
  const okAll = urls.length && urls.every(c => c.status === 200);
  const when = okAll ? urls.map(c => c.checked_at).sort().pop().slice(0, 10) : "";
  return `<span class="badge ${v === "verified" ? "ok" : v === "partially_verified" ? "part" : "no"}">${{verified:"一次情報確認済み",partially_verified:"一部確認",unverified:"未確認"}[v]}</span>` +
         (okAll ? `<span class="badge link">リンク到達確認 ${when}</span>` : "");
}
function altText(t) {
  const s = t.slides[0];
  return `${t.display || t.keyword}の図解: ${s.title}。` + s.points.map(p => `${p.h}: ${p.t}`).join(" ");
}
function card(t) {
  const g = t.digest, k = t.deck, s = t.slides[0], id = esc(t.entity_id);
  const checked = t.verification.checks.map(c => c.retrieved_at).sort().pop();
  return `<article class="card" id="k-${id}" aria-labelledby="h-${id}">
    <label class="sel"><input type="checkbox" class="selbox" data-id="${id}"${excluded.has(t.entity_id) ? "" : " checked"}> PDF / PowerPoint に含める</label>
    <span class="score" title="複数ソースでの言及の多さと新しさ(1位=100)">${t.score}<small> / 100</small></span>
    <div class="kicker"><span class="rank">#${t.rank}</span><strong>${esc(t.display || t.keyword)}</strong><span class="tag">${esc(t.category)}</span><span class="tag">${esc(t.kind)}</span>${t.tags.map(x => `<span class="tag">${esc(x)}</span>`).join("")}${badges(t)}</div>
    <h2 id="h-${id}">${(t.official_urls || [])[0] ? `<a class="tl" href="${esc(t.official_urls[0])}" rel="noopener" title="公式の発表を開く">${esc(s.title)}</a>` : esc(s.title)}</h2>
    <div class="sub">${esc(t.vendor || "")}${t.primary.published_at ? ` ・ 一次情報の公開 ${t.primary.published_at.slice(0, 10)}` : ""}${checked ? ` ・ 確認日 ${checked.slice(0, 10)}` : ""}</div>
    <div class="summary">${g.summary.map(x => `<p>${esc(x)}</p>`).join("")}</div>
    <div class="why">なぜ話題か: ${esc(g.why_trending)}${g.audience ? ` / 想定読者: ${esc(g.audience)}` : ""}</div>
    <div class="cols">${box("何が変わる", g.what_changes)}${box("嬉しいこと", g.benefits)}${box("注意点", g.caveats, "warn")}</div>
    <div class="row">
      <button type="button" class="info" data-e="${id}" aria-label="図解を拡大: ${esc(t.display || t.keyword)}"><img src="assets/slides/${id}.png" width="1280" height="720" loading="lazy" alt="${esc(altText(t))}"></button>
      <div class="side">
        <h3>出典 <small>(確認に使った一次情報)</small></h3>
        <ul>${k.sources.map(x => `<li>[${esc(x.id)}] ${esc(x.publisher)}: ${link(x.url, x.title)}${x.date ? ` (${esc(x.date)})` : ""}</li>`).join("")}</ul>
        <h3>公式 URL</h3>
        <ul>${t.official_urls.map(u => `<li>${link(u)}</li>`).join("")}</ul>
        <h3>話題の根拠 <small>(今週の言及。順位付けの材料)</small></h3>
        <ul>${t.sources.slice(0, 5).map(x => `<li>${link(x.url, x.name + ": " + x.title.slice(0, 40))}</li>`).join("")}</ul>
        ${(t.jp_reactions || []).length ? `<h3>日本語の反応 <small>(Zenn・Qiita・はてブ。表示のみで順位には使っていません)</small></h3><ul>${t.jp_reactions.map(x => `<li>${esc(x.site)}: ${link(x.url, x.title)}${x.date ? ` (${esc(x.date)})` : ""}</li>`).join("")}</ul>` : ""}
      </div>
    </div>
  </article>`;
}
function render() {
  [...f.children].forEach(b => b.setAttribute("aria-pressed", b.dataset.c === cat));
  const q = $("q").value.trim().toLowerCase(), inCat = t => cat === "all" || t.category === cat, inQ = t => !q || hay(t).includes(q);
  const kindF = $("kindSel").value, vendF = $("vendorSel").value;
  const list = published.filter(t => inCat(t) && inQ(t) && (!kindF || t.kind === kindF) && (!vendF || t.vendor === vendF));
  const sig = [cat, q, kindF, vendF].join("|");
  if (sig !== lastSig) { excluded.clear(); lastSig = sig; }  // a new filter starts with everything checked
  window.__visible = list.map(t => t.entity_id);
  queueMicrotask(syncBar);  // after the cards are drawn
  $("latest").innerHTML = list.length ? list.map(card).join("") : `<div class="empty">条件に一致する掲載項目はありません。「観測候補」も確認してください。</div>`;
  const showAll = $("cand").checked || q || cat !== "all";
  const cl = cands.filter(t => inCat(t) && inQ(t));
  const rej = D.rejected_candidates || {};
  const pend = (D.pending || []).filter(p => !q || p.keyword.toLowerCase().includes(q));
  $("candlead").textContent = `自動収集で上位に入ったものの、公式の一次情報での確認や掲載価値の判断が済んでいない、または見送った項目です(${cands.length}件)。内容は未確認で、要約は載せていません。`;
  $("candlist").innerHTML = cl.length ? `<table class="cand"><thead><tr><th>順位</th><th>キーワード</th><th>カテゴリ</th><th>状態</th><th>一次ソース候補</th></tr></thead><tbody>${cl.map(t => `<tr><td>#${t.rank}</td><td>${esc(t.keyword)}</td><td>${esc(t.category)}</td><td>${rej[t.entity_id] ? "見送り: " + esc(rej[t.entity_id]) : "未調査(自動収集のみ・今週の digest で調査予定)"}</td><td>${link(t.primary.url, t.primary.title.slice(0, 50))}</td></tr>`).join("")}</tbody></table>` : `<div class="empty">該当なし</div>`;
  if (pend.length) $("candlist").innerHTML += `<p class="lead">一次ソースの公開日を期間内に確認できず保留(${pend.length}件): ${pend.map(p => esc(p.keyword)).join(" / ")}</p>`;
  $("candsum").textContent = `観測候補(未掲載) ${cands.length}件` + (cl.length !== cands.length ? ` / 条件に一致 ${cl.length}件` : "");
  $("cands").open = !!showAll && (!!q || $("cand").checked);
}
const TH = D.themes || [], byId = Object.fromEntries(D.trends.map(t => [t.entity_id, t]));
if (TH.length) {
  $("themes").hidden = false;
  const alt = `${D.window.label} の 1 週間のまとめ。テーマ: ${TH.map(x => x.title).join(" / ")}`;
  $("themelist").innerHTML = `<button type="button" class="info wide" aria-label="週のまとめ図を拡大"><img src="assets/summary.png" width="1280" height="720" alt="${esc(alt)}"></button>` + TH.map(th => `<div class="theme"><h3>${esc(th.title)}<span class="conf">確度: ${{high:"高",medium:"中",low:"低"}[th.confidence]}</span></h3>
    <div>${esc(th.summary)}</div>
    <div class="bg"><strong>背景の見立て</strong><ul>${th.background.map(b => `<li>${esc(b)}</li>`).join("")}</ul></div>
    <details class="ev"><summary>根拠にした項目と出典</summary><div class="chips">${th.signals.map(s => `<a href="#k-${esc(s.entity)}" title="${esc(s.note)}">${esc((byId[s.entity] || {keyword: s.entity}).keyword)}</a>`).join("")}<span class="src">出典: ${th.refs.map((u, i) => link(u, `[${i + 1}]`)).join(" ")}</span></div></details></div>`).join("");
}
const hl = D.official_highlights || [];
$("hlsum").textContent = `今週の公式発表(タイトルのみ) ${hl.length}件`;
try { const k = "trendradar.hl.open", el = $("hl"); if (localStorage.getItem(k) === "0") el.open = false; el.addEventListener("toggle", () => localStorage.setItem(k, el.open ? "1" : "0")); } catch (e) { /* storage unavailable: keep the default */ }
$("hllist").innerHTML = hl.length ? `<table class="cand"><thead><tr><th>日付</th><th>発表元</th><th>タイトル</th></tr></thead><tbody>${hl.map(x => `<tr><td>${esc(x.date)}</td><td>${esc(x.vendor)}</td><td>${link(x.url, x.title)}</td></tr>`).join("")}</tbody></table>` : `<div class="empty">該当なし</div>`;
render();
function chosen() { return (window.__visible || []).filter(id => !excluded.has(id)); }
function syncBar() {
  const n = chosen().length;
  $("selcount").textContent = `${n} / ${(window.__visible || []).length} 件`;
  $("dlpdf").disabled = $("dlpptx").disabled = n === 0;
  document.querySelectorAll(".selbox").forEach(c => { c.checked = !excluded.has(c.dataset.id); });
}
$("latest").addEventListener("change", e => { const c = e.target.closest(".selbox"); if (!c) return; c.checked ? excluded.delete(c.dataset.id) : excluded.add(c.dataset.id); syncBar(); });
$("selall").onclick = () => { excluded.clear(); syncBar(); };
$("selnone").onclick = () => { (window.__visible || []).forEach(i => excluded.add(i)); syncBar(); };
async function runDownload(kind, btn) {
  const ids = D.trends.filter(t => t.deck && chosen().includes(t.entity_id)).map(t => t.entity_id), old = btn.textContent;
  btn.disabled = true; btn.textContent = "作成中…";
  try { await BriefDownload.download(kind, ids, "", D.window.label); }
  catch (err) { alert("ダウンロードに失敗しました: " + err.message); }
  finally { btn.textContent = old; syncBar(); }
}
$("dlpdf").onclick = e => runDownload("pdf", e.currentTarget); $("dlpptx").onclick = e => runDownload("pptx", e.currentTarget);
syncBar();
const st = D.source_status, ng = Object.keys(st).filter(k => st[k].ok === false);
// Week switcher: prev / next week plus recent weeks (from the static API; stays hidden when it cannot be read, e.g. file://)
(async () => {
  const inWeek = location.pathname.includes("/w/"), root = inWeek ? "../../" : "";
  try {
    const ix = await (await fetch(root + "api/v1/index.json")).json();
    const ws = ix.weeks.filter(w => w.published > 0 || w.week === D.window.label), i = ws.findIndex(w => w.week === D.window.label);
    if (ws.length < 2 || i < 0) return;
    const tag = (w, text) => `<a href="${esc(root + w.page)}">${text}</a>`;
    const prev = ws[i - 1], next = ws[i + 1];
    $("weeknav").innerHTML = (prev ? tag(prev, `← 前の週 ${esc(prev.week)}`) : `<span class="off">← 前の週</span>`) +
      `<span class="here">${esc(D.window.label)}${i === ws.length - 1 ? "(最新)" : ""}</span>` +
      (next ? tag(next, `次の週 ${esc(next.week)} →`) : `<span class="off">次の週 →</span>`) +
      `<span class="all">${ws.slice().reverse().slice(0, 6).map(w => w.week === D.window.label ? `<b>${esc(w.week)}</b>` : tag(w, esc(w.week))).join(" ")} ・ <a href="${root}archive.html">すべてのアーカイブ</a></span>`;
    $("weeknav").hidden = false;
  } catch (e) { /* offline or file://: the header menu still links to the archive */ }
})();
$("statusbar").innerHTML = `<b>${esc(D.window.label)}</b> ・ 掲載 <b>${published.length}</b> 件 ・ 観測候補 ${cands.length} 件 ・ 週次レポート ${Math.floor(ageDays) < 1 ? "24 時間以内" : Math.floor(ageDays) + " 日前"} ・ 収集元 ${Object.keys(st).length - ng.length}/${Object.keys(st).length}${ng.length ? ` <span class="ng">(未取得 ${ng.length})</span>` : ""} ・ <a href="about.html">しくみと運用状況</a>`;
$("meta").textContent = `掲載 ${published.length} 件 / 観測候補 ${cands.length} 件 / 取得成功 ${Object.keys(st).length - ng.length}/${Object.keys(st).length}` + (ng.length ? `(取得できなかった: ${ng.join(", ")})` : "") + ` / 公開日が確認できず保留 ${D.pending.length} 件 / X 検索: ${D.x_integration.search && D.x_integration.search.ok ? "利用可" : "利用不可(ウォッチリストで補完)"}`;

const dlg = $("dlg");
document.addEventListener("click", e => {
  const b = e.target.closest(".info"); if (!b) return;
  opener = b; $("dlgimg").src = b.querySelector("img").src; $("dlgimg").alt = b.querySelector("img").alt; dlg.showModal();
});
$("dlgclose").onclick = () => dlg.close();
dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
dlg.addEventListener("close", () => opener && opener.focus());
