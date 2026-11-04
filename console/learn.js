// Tab "Hiểu dự án": bản đồ dự án, đọc tài liệu có giải thích thuật ngữ khi di chuột, bảng thuật ngữ, tìm kiếm.
// Nội dung đọc thẳng từ docs/ qua /api/learn/*; bảng thuật ngữ từ docs/THUAT_NGU.md (console/learn.py).
(() => {
const $ = (id) => document.getElementById(id);
const el = (tag, { dataset, style, ...props } = {}, ...children) => {
  const e = Object.assign(document.createElement(tag), props);
  Object.assign(e.dataset, dataset || {});  // dataset chỉ đọc được, không gán thẳng bằng Object.assign
  if (style) for (const [k, v] of Object.entries(style)) e.style.setProperty(k, v);
  e.append(...children.filter(c => c !== null && c !== undefined && c !== ""));
  return e;
};
const getJson = async (url) => { const r = await fetch(url); if (!r.ok) throw new Error(r.status); return r.json(); };
const getText = async (url) => { const r = await fetch(url); if (!r.ok) throw new Error(r.status); return r.text(); };
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const slug = (s) => s.toLowerCase().replace(/<[^>]+>/g, "").replace(/[^\p{L}\p{N}\s-]/gu, "").trim().replace(/\s/g, "-");
const vn = (x) => Number.isInteger(x) ? String(x) : x.toFixed(3).replace(".", ",");
const KINDS = { nganh: "Thuật ngữ ngành", du_an: "Dự án đặt tên tiếng Việt", noi_bo: "Ký hiệu nội bộ" };

// Đánh dấu đã hiểu / đã đọc: chỉ để tiện cho người đọc, lưu trong trình duyệt; mất cũng không sao.
const store = {
  get(k) { try { return JSON.parse(localStorage.getItem("floodeye-learn-" + k) || "[]"); } catch { return []; } },
  set(k, v) { try { localStorage.setItem("floodeye-learn-" + k, JSON.stringify(v)); } catch { /* chế độ riêng tư */ } },
};
let doneStages = new Set(store.get("stages")), seenDocs = new Set(store.get("docs"));

let glossary = [], termRegex = null, aliasToEntry = new Map(), docs = [], docCache = new Map(), currentDoc = null;

// ---------------- Markdown (đủ cho tài liệu của dự án: tiêu đề, đoạn, danh sách, bảng, khối mã, trích dẫn) ----------------
function inline(text, base) {
  const codes = [];
  let s = esc(text).replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_, alt, url) => `<img alt="${alt}" src="${assetUrl(url, base)}">`)
       .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, t, url) => `<a class="lk" data-href="${url}">${t}</a>`)
       .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
       .replace(/(^|[^*\w])\*([^*\s][^*]*)\*(?!\w)/g, "$1<i>$2</i>");
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => {
    const c = codes[+i];
    const isPath = /^[\w./-]+\.(py|sh|yaml|yml|html|toml|md|js|css)$/.test(c) || /^[\w-]+\/[\w./-]+$/.test(c);
    return isPath ? `<code class="lk" data-src="${c}">${c}</code>` : `<code>${c}</code>`;
  });
}
function assetUrl(url, base) {
  if (/^https?:/.test(url)) return url;
  return "/api/learn/asset?path=" + encodeURIComponent(resolvePath(url, base));
}
function resolvePath(url, base) {
  const parts = base.split("/").slice(0, -1);
  for (const p of url.split("#")[0].split("/")) { if (p === "..") parts.pop(); else if (p && p !== ".") parts.push(p); }
  return parts.join("/");
}
function renderMarkdown(src, base) {
  const lines = src.replace(/\r/g, "").split("\n"), out = [];
  let i = 0;
  const isTable = (l) => /^\s*\|/.test(l);
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {
      const buf = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++; out.push(`<pre><code>${esc(buf.join("\n"))}</code></pre>`); continue;
    }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) { const t = inline(h[2], base); out.push(`<h${h[1].length} id="${slug(h[2])}">${t}</h${h[1].length}>`); i++; continue; }
    if (/^\s*(---|\*\*\*)\s*$/.test(line)) { out.push("<hr>"); i++; continue; }
    if (isTable(line) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
      // Tách cột theo "|", trừ "|" nằm trong `mã` hoặc viết "\|".
      const row = (l) => {
        const cells = [""]; let inCode = false;
        const s = l.trim().replace(/^\|/, "").replace(/\|$/, "");
        for (let k = 0; k < s.length; k++) {
          const ch = s[k];
          if (ch === "`") inCode = !inCode;
          if (ch === "\\" && s[k + 1] === "|") { cells[cells.length - 1] += "|"; k++; continue; }
          if (ch === "|" && !inCode) cells.push(""); else cells[cells.length - 1] += ch;
        }
        return cells.map(c => c.trim());
      };
      const head = row(line); i += 2;
      const body = [];
      while (i < lines.length && isTable(lines[i])) body.push(row(lines[i++]));
      out.push("<table><tr>" + head.map(c => `<th>${inline(c, base)}</th>`).join("") + "</tr>" +
        body.map(r => "<tr>" + r.map(c => `<td>${inline(c, base)}</td>`).join("") + "</tr>").join("") + "</table>");
      continue;
    }
    if (/^>\s?/.test(line)) {
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^>\s?/, ""));
      out.push(`<blockquote>${inline(buf.join(" "), base)}</blockquote>`); continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
      // Danh sách, lồng theo thụt lề; dòng tiếp nối (thụt lề, không có dấu đầu dòng) nối vào mục trước.
      const items = [];
      while (i < lines.length && (/^\s*([-*]|\d+\.)\s+/.test(lines[i]) || (/^\s{2,}\S/.test(lines[i]) && items.length))) {
        const m = lines[i].match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
        if (m) items.push({ depth: Math.floor(m[1].length / 2), ordered: /\d/.test(m[2]), text: m[3] });
        else items[items.length - 1].text += " " + lines[i].trim();
        i++;
      }
      let html = "", stack = [];
      for (const it of items) {
        while (stack.length > it.depth + 1) html += `</li></${stack.pop()}>`;
        if (stack.length < it.depth + 1) { const t = it.ordered ? "ol" : "ul"; html += `<${t}>`; stack.push(t); }
        else html += "</li>";
        html += `<li>${inline(it.text, base)}`;
      }
      while (stack.length) html += `</li></${stack.pop()}>`;
      out.push(html); continue;
    }
    if (!line.trim()) { i++; continue; }
    const buf = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|>|\s*([-*]|\d+\.)\s+)/.test(lines[i]) && !isTable(lines[i])) buf.push(lines[i++]);
    if (!buf.length) { buf.push(lines[i++]); }
    out.push(`<p>${inline(buf.join(" "), base)}</p>`);
  }
  return out.join("\n");
}

// ---------------- Thuật ngữ: gạch chân lần đầu trong mỗi mục, màu theo loại, di chuột để xem ----------------
const aliasPattern = (aliases) => aliases.map(a => a.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
const termRe = (aliases) => new RegExp(`(?<![\\p{L}\\p{N}_-])(${aliasPattern(aliases)})(?![\\p{L}\\p{N}_])`, "giu");
function buildTermRegex() {
  const aliases = [];
  glossary.forEach((e, idx) => e.aliases.forEach(a => { const k = a.toLowerCase(); if (!aliasToEntry.has(k)) { aliasToEntry.set(k, idx); aliases.push(a); } }));
  aliases.sort((a, b) => b.length - a.length);
  termRegex = termRe(aliases);
}
function markTerms(root) {
  if (!termRegex) return;
  // Mỗi mục h2 bắt đầu lại: thuật ngữ được gạch chân lần đầu trong mục đó (THUAT_NGU, quy tắc 1). Không gạch trong
  // tiêu đề, khối mã, liên kết.
  let seen = new Set();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      if (n.nodeType !== 1) return NodeFilter.FILTER_ACCEPT;
      if (/^(PRE|A|SCRIPT|STYLE|BUTTON)$/.test(n.tagName) || n.classList.contains("term") || n.classList.contains("lk") || n.classList.contains("noterm")) return NodeFilter.FILTER_REJECT;
      return n.tagName === "H2" ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
    },
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  for (const node of nodes) {
    if (node.nodeType === 1) { seen = new Set(); continue; }
    if (node.parentElement.closest("h1, h2, h3, h4")) continue;
    const text = node.nodeValue;
    termRegex.lastIndex = 0;
    let m, last = 0, frag = null;
    while ((m = termRegex.exec(text))) {
      const idx = aliasToEntry.get(m[1].toLowerCase());
      if (idx === undefined || seen.has(idx)) continue;
      seen.add(idx);
      frag = frag || document.createDocumentFragment();
      frag.append(text.slice(last, m.index), el("span", { className: "term " + glossary[idx].kind, textContent: m[1], tabIndex: 0, dataset: { k: idx } }));
      last = m.index + m[1].length;
    }
    if (frag) { frag.append(text.slice(last)); node.replaceWith(frag); }
  }
}
function kindBadge(kind) { return el("span", { className: "kind " + kind, textContent: KINDS[kind] }); }
function showTip(t) {
  const e = glossary[+t.dataset.k], tip = $("lTip");
  tip.replaceChildren(kindBadge(e.kind), el("div", { className: "tt", textContent: e.term }),
    e.english ? el("div", { className: "en", textContent: e.english }) : null,
    el("div", { textContent: e.meaning }),
    e.note ? el("div", { className: "note", textContent: e.note }) : null,
    el("div", { className: "more", textContent: "Bấm để xem thêm và những chỗ nhắc tới" }));
  const r = t.getBoundingClientRect();
  tip.style.display = "block";
  tip.style.left = Math.max(8, Math.min(r.left, innerWidth - 400)) + "px";
  tip.style.top = (r.bottom + 8 + tip.offsetHeight > innerHeight ? r.top - tip.offsetHeight - 8 : r.bottom + 8) + "px";
}
document.addEventListener("mouseover", (ev) => {
  const t = ev.target.closest(".term");
  if (t) showTip(t); else if ($("lTip")) $("lTip").style.display = "none";
});
document.addEventListener("focusin", (ev) => { const t = ev.target.closest && ev.target.closest(".term"); if (t) showTip(t); });
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") { $("lPanel").style.display = "none"; $("lTip").style.display = "none"; }
  if (ev.key === "Enter" && ev.target.classList && ev.target.classList.contains("term")) showTermPanel(+ev.target.dataset.k);
});
document.addEventListener("click", (ev) => {
  const t = ev.target.closest(".term");
  if (t) { showTermPanel(+t.dataset.k); return; }
  if (!ev.target.closest("#page-learn")) return;
  const a = ev.target.closest("[data-href]");
  if (a) { ev.preventDefault(); followLink(a.dataset.href); return; }
  const s = ev.target.closest("[data-src]");
  if (s) { openSource(s.dataset.src); return; }
  const d = ev.target.closest("[data-doc]");
  if (d) openDoc(d.dataset.doc, d.dataset.anchor);
});
async function showTermPanel(idx) {
  const e = glossary[idx], panel = $("lPanel");
  const re = termRe(e.aliases), where = [];
  for (const d of docs) { const n = ((await loadDoc(d.path)).match(re) || []).length; if (n) where.push([d, n]); }
  where.sort((a, b) => b[1] - a[1]);
  panel.replaceChildren(
    el("button", { className: "x", textContent: "✕", title: "Đóng (Esc)", onclick: () => (panel.style.display = "none") }),
    kindBadge(e.kind), el("h3", { textContent: e.term }),
    e.english ? el("div", { className: "hint", textContent: "Tiếng Anh: " + e.english }) : null,
    el("p", { textContent: e.meaning }),
    e.note ? el("p", { className: "hint", textContent: "Ghi chú: " + e.note }) : null,
    el("h4", { textContent: `Xuất hiện trong ${where.length} tài liệu` }),
    el("div", { className: "where" }, ...where.slice(0, 12).map(([d, n]) =>
      el("div", {}, el("a", { className: "lk", textContent: `${d.title} (${n} lần)`, onclick: () => openDoc(d.path, null, e.aliases[0]) })))));
  panel.style.display = "block";
}

// ---------------- Đọc tài liệu ----------------
async function loadDoc(path) {
  if (!docCache.has(path)) docCache.set(path, await getText("/api/learn/doc?path=" + encodeURIComponent(path)));
  return docCache.get(path);
}
function followLink(href) {
  if (/^https?:/.test(href)) { window.open(href, "_blank", "noopener"); return; }
  if (href.startsWith("#")) { scrollToAnchor(href.slice(1)); return; }
  const [file, anchor] = href.split("#");
  const target = resolvePath(file, currentDoc || "docs/x.md");
  if (/\.md$/.test(target) && docs.some(d => d.path === target)) openDoc(target, anchor);
  else openSource(target);
}
function scrollToAnchor(anchor) {
  const t = anchor && document.getElementById(decodeURIComponent(anchor));
  if (t) t.scrollIntoView({ block: "start" });
}
async function openDoc(path, anchor, highlight) {
  showView("lRead");
  currentDoc = path;
  seenDocs.add(path); store.set("docs", [...seenDocs]);
  renderDocList();
  const md = $("lDoc");
  md.replaceChildren(el("div", { className: "md", innerHTML: renderMarkdown(await loadDoc(path), path) }));
  markTerms(md.firstChild);
  $("lToc").replaceChildren(el("div", { className: "tt", textContent: "Trong trang này" }),
    ...[...md.querySelectorAll("h2, h3")].map(h => el("div", { className: h.tagName.toLowerCase(), textContent: h.textContent, onclick: () => h.scrollIntoView({ block: "start" }) })));
  md.scrollTop = 0;
  updateProgress();
  if (anchor) scrollToAnchor(anchor);
  else if (highlight) highlightFirst(md, highlight);
}
function updateProgress() {
  const d = $("lDoc"), max = d.scrollHeight - d.clientHeight;
  $("lProg").style.width = (max > 0 ? Math.min(100, 100 * d.scrollTop / max) : 100) + "%";
}
function highlightFirst(root, text) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const needle = text.toLowerCase();
  while (walker.nextNode()) {
    const n = walker.currentNode, i = n.nodeValue.toLowerCase().indexOf(needle);
    if (i < 0) continue;
    const mark = el("mark", { textContent: n.nodeValue.slice(i, i + text.length) });
    n.replaceWith(n.nodeValue.slice(0, i), mark, n.nodeValue.slice(i + text.length));
    mark.scrollIntoView({ block: "center" });
    return;
  }
}
async function openSource(path) {
  let text;
  try { text = await getText("/api/learn/source?path=" + encodeURIComponent(path)); }
  catch { alert("Không xem được " + path + " (chỉ xem được mã nguồn và cấu hình của dự án)"); return; }
  const back = document.querySelector(".lview.on")?.id || "lMap";
  showView("lSrc");
  $("lSrc").replaceChildren(el("div", { className: "srcview" },
    el("div", { className: "bar0" }, el("button", { className: "btn", textContent: "← Quay lại", onclick: () => showView(back === "lSrc" ? "lMap" : back) }), el("code", { textContent: path })),
    el("pre", { textContent: text })));
}
function renderDocList() {
  const item = (d) => el("div", { className: d.path === currentDoc ? "on" : "", dataset: { path: d.path }, onclick: () => openDoc(d.path) },
    el("span", { textContent: d.title }), seenDocs.has(d.path) ? el("span", { className: "seen", textContent: "✓", title: "Đã mở" }) : null);
  const main = docs.filter(d => !d.path.startsWith("docs/results/")), results = docs.filter(d => d.path.startsWith("docs/results/"));
  $("lDocList").replaceChildren(el("h5", { textContent: "Tài liệu chính" }), ...main.map(item), el("h5", { textContent: `Kết quả đã đo (${results.length})` }), ...results.map(item));
}

// ---------------- Bản đồ dự án ----------------
let mapData = null, allStages = [], rqFilter = null;
function stageCard(s, n) {
  return el("button", { className: "stage", dataset: { id: s.id }, style: { "--c": s.color }, onclick: () => showStage(s), title: s.title },
    n ? el("span", { className: "num", textContent: "0" + n }) : null,
    el("div", { className: "ico", textContent: s.icon }),
    el("b", { textContent: s.title.replace(/^\d+\.\s*/, "") }),
    el("span", { className: "sum", textContent: s.summary }),
    doneStages.has(s.id) ? el("span", { className: "done", textContent: "✓ đã hiểu" }) : null);
}
function ring() {
  const done = allStages.filter(s => doneStages.has(s.id)).length, total = allStages.length, c = 2 * Math.PI * 26;
  return el("div", { className: "ring", innerHTML:
    `<svg width="72" height="72" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="26" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="6"/>` +
    `<circle cx="32" cy="32" r="26" fill="none" stroke="#00d4a4" stroke-width="6" stroke-linecap="round" stroke-dasharray="${c * done / total} ${c}" transform="rotate(-90 32 32)"/>` +
    `<text x="32" y="37" text-anchor="middle" font-size="14" font-weight="600" fill="#fff">${done}/${total}</text></svg>` +
    `<b>khâu đã hiểu</b>` });
}
const RQS = [
  ["Câu hỏi 1", "Nhìn thấy người không?"],
  ["Câu hỏi 2", "Máy nhỏ chạy kịp không?"],
  ["Câu hỏi 3", "Báo đúng về trạm không?"],
];
function renderMap() {
  const flow = [];
  mapData.stages.forEach((s, i) => { if (i) flow.push(el("div", { className: "arrow", ariaHidden: "true" })); flow.push(stageCard(s, i + 1)); });
  $("lMap").replaceChildren(
    el("div", { className: "hero" },
      el("div", {},
        el("h2", { textContent: "FloodEye: từ camera trên drone tới đội cứu hộ" }),
        el("p", { textContent: "Đồ án trả lời ba câu hỏi theo đường đi của dữ liệu. Bấm một câu hỏi để xem khâu nào trả lời nó; bấm một khâu để xem nó làm gì, vì sao, kết quả đã có và file chứa nó." }),
        el("div", { className: "rqchips" }, ...RQS.map(([k, v]) => el("button", { className: "rqchip" + (rqFilter === k ? " on" : ""), textContent: `${k}: ${v}`, onclick: () => { rqFilter = rqFilter === k ? null : k; renderMap(); } })))),
      ring()),
    el("div", { className: "mapwrap" },
      el("div", { className: "sectionlabel", textContent: "Đường đi của dữ liệu" }),
      el("div", { className: "flow" }, ...flow),
      el("div", { className: "sectionlabel", style: { "margin-top": "26px" }, textContent: "Hai mảng nằm cạnh đường đi" }),
      el("div", { className: "sidebox" }, ...mapData.side.map(s => stageCard(s, 0))),
      el("div", { className: "detail", id: "lDetail" }, el("div", { className: "empty", textContent: "👆 Chọn một khâu ở trên để bắt đầu. Gợi ý: đi lần lượt từ khâu 1 tới khâu 6, mỗi ngày một khâu." }))));
  if (rqFilter) document.querySelectorAll("#lMap .stage").forEach(b => b.classList.toggle("dim", !allStages.find(s => s.id === b.dataset.id).rq.startsWith(rqFilter)));
}
function metricCard(m, color) {
  const bar = (cls, label, v) => el("div", { className: "bar " + cls },
    el("span", { className: "n", textContent: label, title: label }),
    el("div", { className: "track" }, el("div", { className: "fill", style: { width: (100 * v / m.max) + "%" } })),
    el("span", { className: "v", textContent: vn(v) + (m.unit || "") }));
  return el("div", { className: "metric", style: { "--c": color } },
    el("div", { className: "ml", textContent: m.label }),
    bar("a", m.a_label, m.a), bar("b", m.b_label, m.b),
    el("div", { className: "src" }, "Nguồn: ", el("a", { className: "lk", textContent: m.doc, dataset: { doc: m.doc } })));
}
function showStage(s) {
  document.querySelectorAll("#lMap .stage").forEach(b => b.classList.toggle("on", b.dataset.id === s.id));
  const i = allStages.findIndex(x => x.id === s.id), prev = allStages[i - 1], next = allStages[i + 1];
  const done = doneStages.has(s.id);
  const d = $("lDetail");
  d.style.setProperty("--c", s.color);
  d.replaceChildren(
    el("div", { className: "dhead" },
      el("div", { className: "ico", textContent: s.icon }),
      el("div", {}, el("h3", { textContent: s.title }), el("span", { className: "rq", textContent: s.rq })),
      el("div", { className: "acts" },
        el("button", { className: "btn" + (done ? " done" : ""), textContent: done ? "✓ Đã hiểu" : "Đánh dấu đã hiểu", onclick: () => {
          if (done) doneStages.delete(s.id); else doneStages.add(s.id);
          store.set("stages", [...doneStages]); renderMap(); showStage(s);
        } }))),
    el("div", { className: "dgrid" },
      el("div", { className: "dcell" }, el("h4", { textContent: "Làm gì" }), el("p", { innerHTML: inline(s.what, "docs/x.md") })),
      el("div", { className: "dcell" }, el("h4", { textContent: "Vì sao" }), el("p", { innerHTML: inline(s.why, "docs/x.md") })),
      el("div", { className: "dcell wide" }, el("h4", { textContent: "Kết quả đã có" }),
        s.metrics.length ? el("div", { className: "metrics" }, ...s.metrics.map(m => metricCard(m, s.color))) : null,
        el("ul", {}, ...s.results.map(r => el("li", {}, r.text + " ", el("a", { className: "lk", textContent: "→ " + r.doc.replace(/^docs\//, ""), dataset: { doc: r.doc } }))))),
      el("div", { className: "dcell" }, el("h4", { textContent: "File chứa nó (bấm để xem mã)" }),
        el("div", { className: "files" }, ...s.files.map(f => el("code", { className: "lk", textContent: f, dataset: { src: f } })))),
      el("div", { className: "dcell" }, el("h4", { textContent: "Đọc thêm" }),
        el("ul", {}, ...s.docs.map(r => el("li", {}, el("a", { className: "lk", textContent: r.text, dataset: { doc: r.doc } })))))),
    el("div", { className: "dnav" },
      prev ? el("button", { className: "btn", textContent: "← " + prev.title, onclick: () => showStage(prev) }) : el("span"),
      next ? el("button", { className: "btn primary", textContent: next.title + " →", onclick: () => showStage(next) }) : el("span")));
  markTerms(d);
  d.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}

// ---------------- Bảng thuật ngữ và tìm kiếm ----------------
let glossKind = null;
function renderGlossary(filter = "") {
  const f = filter.toLowerCase();
  const groups = new Map();
  glossary.forEach((e, idx) => {
    if (glossKind && e.kind !== glossKind) return;
    if (f && !(e.term + e.english + e.meaning + e.note).toLowerCase().includes(f)) return;
    if (!groups.has(e.section)) groups.set(e.section, []);
    groups.get(e.section).push([e, idx]);
  });
  const counts = Object.fromEntries(Object.keys(KINDS).map(k => [k, glossary.filter(e => e.kind === k).length]));
  $("lGloss").replaceChildren(
    el("div", { className: "chips" },
      el("button", { className: "chip" + (glossKind ? "" : " on"), textContent: `Tất cả (${glossary.length})`, onclick: () => { glossKind = null; renderGlossary($("lFilter").value); } }),
      ...Object.entries(KINDS).map(([k, v]) => el("button", { className: "chip" + (glossKind === k ? " on" : ""), onclick: () => { glossKind = k; renderGlossary($("lFilter").value); } },
        el("span", { className: "kind " + k, textContent: "●" }), ` ${v} (${counts[k]})`)),
      el("span", { className: "mapnote", style: { margin: "0 0 0 auto" }, textContent: "Đọc từ docs/THUAT_NGU.md; gõ vào ô tìm ở trên để lọc." })),
    ...[...groups].map(([section, list]) => el("div", { className: "ggroup" },
      el("h3", { textContent: section.replace(/^\d+\.\s*/, "") }),
      el("div", { className: "gcards" }, ...list.map(([e, idx]) => el("div", { className: "gcard " + e.kind, tabIndex: 0, onclick: () => showTermPanel(idx), onkeydown: (ev) => { if (ev.key === "Enter") showTermPanel(idx); } },
        el("b", { textContent: e.term }), e.english ? el("div", { className: "en", textContent: e.english }) : null, el("p", { textContent: e.meaning })))))));
}
async function search(q) {
  showView("lSearch");
  const needle = q.trim().toLowerCase();
  const hits = [];
  if (needle.length >= 2) {
    for (const d of docs) {
      let heading = d.title;
      (await loadDoc(d.path)).split("\n").forEach(l => {
        if (/^#{1,4}\s/.test(l)) heading = l.replace(/^#+\s/, "");
        if (l.toLowerCase().includes(needle)) hits.push({ d, heading, line: l.replace(/[|#*`]/g, " ").replace(/\s+/g, " ").trim() });
      });
    }
  }
  const show = (line) => {
    const i = line.toLowerCase().indexOf(needle), start = Math.max(0, i - 80);
    const cut = (start ? "…" : "") + line.slice(start, i + needle.length + 160);
    const j = cut.toLowerCase().indexOf(needle);
    return el("div", {}, cut.slice(0, j), el("mark", { textContent: cut.slice(j, j + needle.length) }), cut.slice(j + needle.length));
  };
  $("lSearch").replaceChildren(el("p", { className: "mapnote", textContent: `${hits.length} dòng chứa "${q}" trong ${new Set(hits.map(h => h.d.path)).size} tài liệu` + (hits.length > 300 ? " (hiện 300 dòng đầu)" : "") }),
    ...hits.slice(0, 300).map(h => el("div", { className: "hit", onclick: () => openDoc(h.d.path, null, q.trim()) },
      el("small", { textContent: `${h.d.title} › ${h.heading}` }), show(h.line))));
}

function showView(id) {
  document.querySelectorAll(".lview").forEach(v => v.classList.toggle("on", v.id === id));
  document.querySelectorAll(".lnav button").forEach(b => b.classList.toggle("on", b.dataset.view === id));
}

async function init() {
  const page = $("page-learn");
  page.replaceChildren(
    el("div", { className: "lnav" },
      el("button", { textContent: "🧭 Bản đồ dự án", dataset: { view: "lMap" }, onclick: () => { renderMap(); showView("lMap"); } }),
      el("button", { textContent: "📖 Đọc tài liệu", dataset: { view: "lRead" }, onclick: () => { if (!currentDoc) openDoc(docs[0].path); else showView("lRead"); } }),
      el("button", { textContent: "🔤 Thuật ngữ", dataset: { view: "lGloss" }, onclick: async () => { await loadGlossary(); renderGlossary($("lFilter").value); showView("lGloss"); } }),
      el("div", { className: "search" }, el("input", { id: "lFilter", type: "text", placeholder: "Tìm trong mọi tài liệu (Enter) hoặc lọc thuật ngữ…", ariaLabel: "Tìm kiếm",
        onkeydown: (ev) => { if (ev.key === "Enter") search(ev.target.value); },
        oninput: (ev) => { if ($("lGloss").classList.contains("on")) renderGlossary(ev.target.value); } }))),
    el("div", { className: "lbody" },
      el("div", { className: "lview on", id: "lMap" }),
      el("div", { className: "lview", id: "lRead" },
        el("div", { className: "dlist", id: "lDocList" }),
        el("div", { className: "docwrap" },
          el("div", { className: "progress" }, el("div", { id: "lProg" })),
          el("div", { className: "legend noterm" }, "Thuật ngữ gạch chân, di chuột để xem:",
            ...Object.entries(KINDS).map(([k, v]) => el("span", {}, el("i", { style: { "border-color": `var(--k-${k})`, "border-bottom-style": k === "noi_bo" ? "dotted" : "solid" } }), v))),
          el("div", { className: "doc", id: "lDoc", onscroll: updateProgress })),
        el("div", { className: "toc", id: "lToc" })),
      el("div", { className: "lview", id: "lGloss" }),
      el("div", { className: "lview", id: "lSearch" }),
      el("div", { className: "lview", id: "lSrc" })),
    el("div", { id: "lTip", role: "tooltip" }), el("div", { className: "panel", id: "lPanel" }));
  [mapData, docs] = await Promise.all([getJson("/api/learn/map"), getJson("/api/learn/docs")]);
  allStages = [...mapData.stages, ...mapData.side];
  await loadGlossary();
  renderDocList();
  renderMap();
  showView("lMap");
}
async function loadGlossary() {
  glossary = await getJson("/api/learn/glossary");
  aliasToEntry = new Map();
  buildTermRegex();
}

init();
})();
