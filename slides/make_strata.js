const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
const JP = "Yu Gothic", NAVY = "14213D", INK = "1B2333", ACC = "FCA311", TEAL = "1B9AAA", PALE = "F4F1EA", MUTED = "5B6578";

const s = p.addSlide();
s.background = { color: PALE };

// header band
s.addShape(p.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 1.55, fill: { color: NAVY } });
s.addText("今週の新顔", { x: 0.5, y: 0.22, w: 2.2, h: 0.36, fontFace: JP, fontSize: 13, bold: true, color: NAVY, fill: { color: ACC }, align: "center", margin: 0 });
s.addText("local-llm", { x: 2.85, y: 0.22, w: 1.4, h: 0.36, fontFace: JP, fontSize: 13, color: "FFFFFF", fill: { color: TEAL }, align: "center", margin: 0 });
s.addText("tools", { x: 4.4, y: 0.22, w: 1.0, h: 0.36, fontFace: JP, fontSize: 13, color: "FFFFFF", fill: { color: TEAL }, align: "center", margin: 0 });
s.addText("Strata ― 巨大AIを「手元のゲーミングPC」で動かす推論エンジン", { x: 0.5, y: 0.7, w: 12.3, h: 0.7, fontFace: JP, fontSize: 28, bold: true, color: "FFFFFF", margin: 0 });

// left: how it works
s.addText("何をするもの?", { x: 0.5, y: 1.8, w: 6, h: 0.4, fontFace: JP, fontSize: 20, bold: true, color: INK, margin: 0 });
s.addText("数百B級の巨大MoEモデルは普通VRAMに載らない。Strataは「いま使う専門家(expert)だけ」を速い場所に置き、残りを遅い場所へ退避して動かす。", { x: 0.5, y: 2.2, w: 6.2, h: 0.85, fontFace: JP, fontSize: 14, color: INK, margin: 0, valign: "top" });
const tiers = [
  ["GPU (VRAM)", "よく使う専門家", "最速", "1B2F5C"],
  ["メインRAM", "次に使いそうな専門家", "中速", "1B9AAA"],
  ["NVMe SSD", "残り全部", "低速", "7A869A"],
];
tiers.forEach((t, i) => {
  const y = 3.2 + i * 0.95;
  s.addShape(p.ShapeType.roundRect, { x: 0.5, y, w: 6.2, h: 0.78, fill: { color: "FFFFFF" }, line: { color: t[3], width: 2 }, rectRadius: 0.1 });
  s.addShape(p.ShapeType.rect, { x: 0.5, y: y + 0.08, w: 0.14, h: 0.62, fill: { color: t[3] }, line: { color: t[3], width: 0 } });
  s.addText(t[0], { x: 0.85, y, w: 2.1, h: 0.78, fontFace: JP, fontSize: 16, bold: true, color: t[3], valign: "middle", margin: 0 });
  s.addText(t[1], { x: 2.95, y, w: 2.5, h: 0.78, fontFace: JP, fontSize: 14, color: INK, valign: "middle", margin: 0 });
  s.addText(t[2], { x: 5.55, y, w: 1.0, h: 0.78, fontFace: JP, fontSize: 14, bold: true, color: MUTED, align: "right", valign: "middle", margin: 0 });
});
s.addText("会話の流れに合わせて、専門家を置き場所の間で入れ替える", { x: 0.5, y: 6.05, w: 6.2, h: 0.35, fontFace: JP, fontSize: 12, italic: true, color: MUTED, margin: 0 });

// right: why buzzing
s.addText("なぜバズった?", { x: 7.2, y: 1.8, w: 5.6, h: 0.4, fontFace: JP, fontSize: 20, bold: true, color: INK, margin: 0 });
const why = [
  ["1", "数字が刺さった", "RTX 3060 12GB+RAM 16GBで約21 tok/s、RTX 5090で30 tok/s超の報告。「家で動く」衝撃"],
  ["2", "派生が連鎖した", "Strata派生のBasalt(2.6倍)、NVFP4版、Rust版、Project Maya。新モデル(GLM-5.3 / Qwen3.8)と同時に拡散"],
  ["3", "議論・炎上も", "Claude共著の履歴を書き換えた疑い、未監査バイナリを取得するsetup.shへの懸念"],
];
why.forEach((w, i) => {
  const y = 2.3 + i * 1.28;
  s.addShape(p.ShapeType.ellipse, { x: 7.2, y: y + 0.05, w: 0.55, h: 0.55, fill: { color: ACC }, line: { color: ACC, width: 0 } });
  s.addText(w[0], { x: 7.2, y: y + 0.05, w: 0.55, h: 0.55, fontFace: JP, fontSize: 18, bold: true, color: NAVY, align: "center", valign: "middle", margin: 0 });
  s.addText(w[1], { x: 7.95, y, w: 4.9, h: 0.38, fontFace: JP, fontSize: 16, bold: true, color: INK, margin: 0 });
  s.addText(w[2], { x: 7.95, y: y + 0.38, w: 4.9, h: 0.82, fontFace: JP, fontSize: 13, color: INK, margin: 0, valign: "top" });
});

// stat strip
const stats = [["約21 tok/s", "RTX 3060 12GB環境の報告"], ["2.6x", "派生Basaltの速度比"], ["321B", "動かす対象(GLM-5.3-Flash)"]];
stats.forEach((st, i) => {
  const x = 7.2 + i * 1.95;
  s.addShape(p.ShapeType.rect, { x, y: 5.95, w: 1.8, h: 0.9, fill: { color: NAVY }, line: { color: NAVY, width: 0 } });
  s.addText(st[0], { x, y: 5.98, w: 1.8, h: 0.45, fontFace: JP, fontSize: 18, bold: true, color: ACC, align: "center", margin: 0 });
  s.addText(st[1], { x: x + 0.05, y: 6.42, w: 1.7, h: 0.4, fontFace: JP, fontSize: 10, color: "FFFFFF", align: "center", valign: "top", margin: 0 });
});

// footer
s.addText("公式: github.com/Niko1221/Strata ／ 根拠: r/LocalLLaMA 週間TOP(2026-10-07〜13)、GitHub新規リポジトリ。速度は投稿者の自己申告で未検証", { x: 0.5, y: 6.95, w: 12.3, h: 0.35, fontFace: JP, fontSize: 10, color: MUTED, margin: 0 });

p.writeFile({ fileName: "slides/strata-1.pptx" }).then(() => console.log("written"));
