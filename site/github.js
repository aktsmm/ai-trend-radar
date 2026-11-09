(() => {
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const num = n => (n == null ? "?" : Number(n).toLocaleString("ja-JP"));
  let data = null, tag = "";
  const list = document.getElementById("list"), weekSel = document.getElementById("week"), tagBox = document.getElementById("tags");

  const report = () => data.weeks.find(w => w.week === weekSel.value);

  function drawTags() {
    const r = report(), used = new Set(r.items.map(i => i.tag));
    const chips = [["", "すべて"], ...Object.entries(data.tags).filter(([k]) => used.has(k))];
    tagBox.innerHTML = chips.map(([k, label]) => `<button type="button" data-tag="${esc(k)}" aria-pressed="${k === tag}">${esc(label)}</button>`).join("");
  }

  function draw() {
    const r = report();
    document.getElementById("meta").textContent = `${r.week} / 取得 ${r.generated_at.slice(0, 10)} / ${r.items.length} 件(週間 Trending のうち AI 関連のみ、${r.excluded_count} 件は AI 以外などで除外)`;
    const rows = r.items.filter(i => !tag || i.tag === tag);
    list.innerHTML = rows.length ? rows.map(i => `<li class="gh-item"><span class="gh-rank" aria-label="${i.rank} 位">${i.rank}</span>
      <div><a href="${esc(i.url)}" rel="noopener"><b>${esc(i.repo)}</b></a> <span class="tag">${esc(data.tags[i.tag] || i.tag)}</span>
      <div class="gh-stars">今週 +${num(i.stars_week)} ★ / 累計 ${num(i.stars_total)} ★${i.language ? ` / ${esc(i.language)}` : ""}</div>
      ${i.one_liner ? `<p>${esc(i.one_liner)}</p>` : ""}${i.description ? `<p class="lead">${i.one_liner ? "原文: " : ""}${esc(i.description)}</p>` : ""}</div></li>`).join("") : "<li>該当する repo がありません。</li>";
  }

  fetch("api/v1/github.json").then(r => r.json()).then(d => {
    data = d;
    if (!d.weeks.length) { list.innerHTML = "<li>まだ集計がありません。</li>"; return; }
    weekSel.innerHTML = [...d.weeks].reverse().map(w => `<option value="${esc(w.week)}">${esc(w.week)}</option>`).join("");
    weekSel.value = d.latest_week;
    drawTags(); draw();
  }).catch(() => { list.innerHTML = "<li>api/v1/github.json を読み込めませんでした(file:// の場合は簡易サーバーで開いてください)。</li>"; });

  weekSel.addEventListener("change", () => { tag = ""; drawTags(); draw(); });
  tagBox.addEventListener("click", e => {
    const b = e.target.closest("button[data-tag]");
    if (b) { tag = b.dataset.tag; drawTags(); draw(); }
  });
})();
