// Download: fetch the selected briefs, then build a PDF (JPEG pages) or an editable PPTX (slide XML merged into template.pptx).
// No external libraries: PDF writer, ZIP reader/writer and no encryption.
(function () {
  const enc = new TextEncoder(), dec = new TextDecoder();
  const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const cat = parts => { const n = parts.reduce((a, p) => a + p.length, 0), o = new Uint8Array(n); let i = 0; parts.forEach(p => { o.set(p, i); i += p.length; }); return o; };

  // ---- PDF (each page = one JPEG, 960x540 pt = 16:9) ----
  function jpegSize(u) {
    for (let i = 2; i < u.length;) {
      if (u[i] !== 0xFF) { i++; continue; }
      const m = u[i + 1], len = (u[i + 2] << 8) | u[i + 3];
      if (m >= 0xC0 && m <= 0xCF && m !== 0xC4 && m !== 0xC8 && m !== 0xCC) return { h: (u[i + 5] << 8) | u[i + 6], w: (u[i + 7] << 8) | u[i + 8] };
      i += 2 + len;
    }
    throw new Error("bad jpeg");
  }
  function buildPdf(jpegs) {
    const objs = [], add = b => { objs.push(b); return objs.length; };
    const n = jpegs.length, first = 3;  // 1 = catalog, 2 = pages; each page uses 3 objects (page, content, image)
    const kids = jpegs.map((_, i) => `${first + i * 3} 0 R`).join(" ");
    add(enc.encode("<< /Type /Catalog /Pages 2 0 R >>"));
    add(enc.encode(`<< /Type /Pages /Kids [${kids}] /Count ${n} >>`));
    jpegs.forEach((j, i) => {
      const { w, h } = jpegSize(j), id = first + i * 3;
      add(enc.encode(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 960 540] /Resources << /XObject << /Im0 ${id + 2} 0 R >> >> /Contents ${id + 1} 0 R >>`));
      const c = enc.encode("q 960 0 0 540 0 0 cm /Im0 Do Q");
      add(cat([enc.encode(`<< /Length ${c.length} >>\nstream\n`), c, enc.encode("\nendstream")]));
      add(cat([enc.encode(`<< /Type /XObject /Subtype /Image /Width ${w} /Height ${h} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${j.length} >>\nstream\n`), j, enc.encode("\nendstream")]));
    });
    const parts = [enc.encode("%PDF-1.4\n")], off = [];
    let pos = parts[0].length;
    objs.forEach((o, i) => { const head = enc.encode(`${i + 1} 0 obj\n`), tail = enc.encode("\nendobj\n"); off.push(pos); parts.push(head, o, tail); pos += head.length + o.length + tail.length; });
    const xref = `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n` + off.map(o => String(o).padStart(10, "0") + " 00000 n \n").join("");
    parts.push(enc.encode(xref + `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${pos}\n%%EOF\n`));
    return cat(parts);
  }

  // ---- ZIP (read: stored/deflate; write: stored) ----
  const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  const crc32 = u => { let c = 0xFFFFFFFF; for (let i = 0; i < u.length; i++) c = CRC[(c ^ u[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
  async function inflateRaw(u) {
    const ds = new DecompressionStream("deflate-raw"), w = ds.writable.getWriter(); w.write(u); w.close();
    return new Uint8Array(await new Response(ds.readable).arrayBuffer());
  }
  async function unzip(buf) {
    const u = new Uint8Array(buf), v = new DataView(u.buffer, u.byteOffset, u.byteLength);
    let e = u.length - 22; while (e >= 0 && v.getUint32(e, true) !== 0x06054b50) e--;
    const n = v.getUint16(e + 10, true); let p = v.getUint32(e + 16, true); const files = {};
    for (let i = 0; i < n; i++) {
      const method = v.getUint16(p + 10, true), csz = v.getUint32(p + 20, true), nl = v.getUint16(p + 28, true), el = v.getUint16(p + 30, true), cl = v.getUint16(p + 32, true), lo = v.getUint32(p + 42, true);
      const name = dec.decode(u.subarray(p + 46, p + 46 + nl));
      const ln = v.getUint16(lo + 26, true), le = v.getUint16(lo + 28, true), ds = lo + 30 + ln + le, raw = u.subarray(ds, ds + csz);
      if (!name.endsWith("/")) files[name] = method === 0 ? raw : await inflateRaw(raw);
      p += 46 + nl + el + cl;
    }
    return files;
  }
  function zip(files) {
    const parts = [], cd = []; let pos = 0;
    for (const [name, data] of Object.entries(files)) {
      const nm = enc.encode(name), crc = crc32(data), h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(8, 0, true); h.setUint32(14, crc, true); h.setUint32(18, data.length, true); h.setUint32(22, data.length, true); h.setUint16(26, nm.length, true);
      parts.push(new Uint8Array(h.buffer), nm, data);
      const c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint32(16, crc, true); c.setUint32(20, data.length, true); c.setUint32(24, data.length, true); c.setUint16(28, nm.length, true); c.setUint32(42, pos, true);
      cd.push(new Uint8Array(c.buffer), nm);
      pos += 30 + nm.length + data.length;
    }
    const cdBytes = cat(cd), end = new DataView(new ArrayBuffer(22)), cnt = Object.keys(files).length;
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, cnt, true); end.setUint16(10, cnt, true); end.setUint32(12, cdBytes.length, true); end.setUint32(16, pos, true);
    return cat([...parts, cdBytes, new Uint8Array(end.buffer)]);
  }

  // ---- PPTX: slide XML (from python-pptx, shapes only) merged into the empty template ----
  async function buildPptx(slideXmls, templateBuf) {
    const f = await unzip(templateBuf), txt = k => dec.decode(f[k]);
    const layoutRel = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout7.xml"/></Relationships>';
    let ct = txt("[Content_Types].xml"), rels = txt("ppt/_rels/presentation.xml.rels"), pres = txt("ppt/presentation.xml"), ids = "";
    slideXmls.forEach((x, i) => {
      const n = i + 1;
      f[`ppt/slides/slide${n}.xml`] = enc.encode(x); f[`ppt/slides/_rels/slide${n}.xml.rels`] = enc.encode(layoutRel);
      ct = ct.replace("</Types>", `<Override PartName="/ppt/slides/slide${n}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/></Types>`);
      rels = rels.replace("</Relationships>", `<Relationship Id="rId${100 + n}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide${n}.xml"/></Relationships>`);
      ids += `<p:sldId id="${255 + n}" r:id="rId${100 + n}"/>`;
    });
    pres = pres.replace("</p:sldMasterIdLst>", `</p:sldMasterIdLst><p:sldIdLst>${ids}</p:sldIdLst>`);
    f["[Content_Types].xml"] = enc.encode(ct); f["ppt/_rels/presentation.xml.rels"] = enc.encode(rels); f["ppt/presentation.xml"] = enc.encode(pres);
    return zip(f);
  }

  function save(bytes, name, mime) {
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([bytes], { type: mime })); a.download = name; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000);
  }

  // ids: selected entity ids in display order. Returns after the download starts.
  async function download(kind, ids, base, label) {
    const items = [];
    for (const id of ids) {
      const r = await fetch(`${base}briefs/${id}.json`); if (!r.ok) throw new Error("missing " + id);
      items.push(await r.json());
    }
    if (kind === "pdf") save(buildPdf(items.flatMap(i => i.pages.map(b64))), `ai-trend-radar-${label}.pdf`, "application/pdf");
    else save(await buildPptx(items.flatMap(i => i.slides), await (await fetch(base + "template.pptx")).arrayBuffer()), `ai-trend-radar-${label}.pptx`, "application/vnd.openxmlformats-officedocument.presentationml.presentation");
  }
  window.BriefDownload = { download, buildPdf, buildPptx };
})();
