const D = window.TRENDS, CATS = ["model","dev-tool","local-runtime","hardware","research","github-trending"];
let cat = "all", opener = null;
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const $ = id => document.getElementById(id);
const link = (u, label) => `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(label || u)}</a>`;
const published = D.trends.filter(t => t.deck), cands = D.trends.filter(t => !t.deck);
$("period").textContent = `対象期間 ${D.window.from} 〜 ${D.window.to}(${D.window.label}${D.window.partial ? "・集計途中" : ""}) / データ更新 ${D.last_successful_report_at.slice(0,16).replace("T"," ")} UTC` + (D.baseline.is_baseline ? ` / 蓄積 ${D.baseline.snapshots} 日分のため「今週の注目」表示` : "");

$("weekly").innerHTML = `<a href="downloads/weekly-${D.window.label}.pdf" download>今週の全ブリーフ PDF(表紙・目次つき)</a><a href="downloads/weekly-${D.window.label}.pptx" download>今週の全ブリーフ PowerPoint</a>`;
const f = $("filters");
["all", ...CATS].forEach(c => {
  const b = document.createElement("button");
  b.type = "button"; b.textContent = c === "all" ? "すべて" : c; b.dataset.c = c; b.setAttribute("aria-pressed", c === "all");
  b.onclick = () => { cat = c; render(); };
  f.appendChild(b);
});
$("q").oninput = render; $("cand").onchange = render;

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
  return `${t.keyword}の図解: ${s.title}。` + s.points.map(p => `${p.h}: ${p.t}`).join(" ");
}
function card(t) {
  const g = t.digest, k = t.deck, s = t.slides[0], id = esc(t.entity_id);
  const checked = t.verification.checks.map(c => c.retrieved_at).sort().pop();
  return `<article class="card" id="k-${id}" aria-labelledby="h-${id}">
    <span class="score" title="複数ソースでの言及の多さと新しさ(1位=100)">${t.score}<small> / 100</small></span>
    <div class="kicker"><span class="rank">#${t.rank}</span><strong>${esc(t.keyword)}</strong><span class="tag">${esc(t.category)}</span><span class="tag">${esc(t.kind)}</span>${t.tags.map(x => `<span class="tag">${esc(x)}</span>`).join("")}${badges(t)}</div>
    <h2 id="h-${id}">${esc(s.title)}</h2>
    <div class="sub">${esc(t.vendor || "")}${t.primary.published_at ? ` ・ 一次情報の公開 ${t.primary.published_at.slice(0, 10)}` : ""}${checked ? ` ・ 確認日 ${checked.slice(0, 10)}` : ""}</div>
    <div class="summary">${g.summary.map(x => `<p>${esc(x)}</p>`).join("")}</div>
    <div class="why">なぜ話題か: ${esc(g.why_trending)}${g.audience ? ` / 想定読者: ${esc(g.audience)}` : ""}</div>
    <div class="cols">${box("何が変わる", g.what_changes)}${box("嬉しいこと", g.benefits)}${box("注意点", g.caveats, "warn")}</div>
    <div class="row">
      <button type="button" class="info" data-e="${id}" aria-label="図解を拡大: ${esc(t.keyword)}"><img src="assets/slides/${id}.png" width="1280" height="720" loading="lazy" alt="${esc(altText(t))}"></button>
      <div class="side">
        <div class="dl" role="group" aria-label="ダウンロード"><a href="downloads/${id}.pdf" download>ブリーフ PDF(2 枚)</a><a href="downloads/${id}.pptx" download>ブリーフ PowerPoint(2 枚)</a></div>
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
  const list = published.filter(t => inCat(t) && inQ(t));
  $("latest").innerHTML = list.length ? list.map(card).join("") : `<div class="empty">条件に一致する掲載項目はありません。「観測候補」も確認してください。</div>`;
  const showAll = $("cand").checked || q || cat !== "all";
  const cl = cands.filter(t => inCat(t) && inQ(t));
  const rej = D.rejected_candidates || {};
  $("candlead").textContent = `自動収集で上位に入ったものの、公式の一次情報での確認や掲載価値の判断が済んでいない、または見送った項目です(${cands.length}件)。内容は未確認で、要約は載せていません。`;
  $("candlist").innerHTML = cl.length ? `<table class="cand"><thead><tr><th>順位</th><th>キーワード</th><th>カテゴリ</th><th>状態</th><th>一次ソース候補</th></tr></thead><tbody>${cl.map(t => `<tr><td>#${t.rank}</td><td>${esc(t.keyword)}</td><td>${esc(t.category)}</td><td>${rej[t.entity_id] ? "見送り: " + esc(rej[t.entity_id]) : "未確認(自動収集のみ)"}</td><td>${link(t.primary.url, t.primary.title.slice(0, 50))}</td></tr>`).join("")}</tbody></table>` : `<div class="empty">該当なし</div>`;
  $("candsum").textContent = `観測候補(未掲載) ${cands.length}件` + (cl.length !== cands.length ? ` / 条件に一致 ${cl.length}件` : "");
  $("cands").open = !!showAll && (!!q || $("cand").checked);
}
render();
const st = D.source_status, ng = Object.keys(st).filter(k => st[k].ok === false);
$("meta").textContent = `掲載 ${published.length} 件 / 観測候補 ${cands.length} 件 / 取得成功 ${Object.keys(st).length - ng.length}/${Object.keys(st).length}` + (ng.length ? `(取得できなかった: ${ng.join(", ")})` : "") + ` / 公開日が確認できず保留 ${D.pending.length} 件 / X 検索: ${D.x_integration.search && D.x_integration.search.ok ? "利用可" : "利用不可(ウォッチリストで補完)"}`;

const dlg = $("dlg");
$("latest").addEventListener("click", e => {
  const b = e.target.closest(".info"); if (!b) return;
  opener = b; $("dlgimg").src = b.querySelector("img").src; $("dlgimg").alt = b.querySelector("img").alt; dlg.showModal();
});
$("dlgclose").onclick = () => dlg.close();
dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
dlg.addEventListener("close", () => opener && opener.focus());
