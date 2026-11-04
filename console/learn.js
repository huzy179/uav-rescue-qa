// Tab "Hiểu dự án": bản đồ dự án, đọc tài liệu có giải thích thuật ngữ khi di chuột, bảng thuật ngữ, tìm kiếm.
// Nội dung đọc thẳng từ docs/ qua /api/learn/*; bảng thuật ngữ từ docs/THUAT_NGU.md (console/learn.py).
(() => {
const $ = (id) => document.getElementById(id);
const el = (tag, { dataset, ...props } = {}, ...children) => {
  const e = Object.assign(document.createElement(tag), props);
  Object.assign(e.dataset, dataset || {});  // dataset chỉ đọc được, không gán thẳng bằng Object.assign
  e.append(...children);
  return e;
};
const getJson = async (url) => { const r = await fetch(url); if (!r.ok) throw new Error(r.status); return r.json(); };
const getText = async (url) => { const r = await fetch(url); if (!r.ok) throw new Error(r.status); return r.text(); };
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const slug = (s) => s.toLowerCase().replace(/<[^>]+>/g, "").replace(/[^\p{L}\p{N}\s-]/gu, "").trim().replace(/\s/g, "-");

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

// ---------------- Thuật ngữ: gạch chân lần đầu trong mỗi mục, di chuột để xem ----------------
function buildTermRegex() {
  const aliases = [];
  glossary.forEach((e, idx) => e.aliases.forEach(a => { const k = a.toLowerCase(); if (!aliasToEntry.has(k)) { aliasToEntry.set(k, idx); aliases.push(a); } }));
  aliases.sort((a, b) => b.length - a.length);
  const pattern = aliases.map(a => a.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  termRegex = new RegExp(`(?<![\\p{L}\\p{N}_-])(${pattern})(?![\\p{L}\\p{N}_])`, "giu");
}
function markTerms(root) {
  if (!termRegex) return;
  // Mỗi mục h2 bắt đầu lại: thuật ngữ được gạch chân lần đầu trong mục đó (THUAT_NGU, quy tắc 1). Không gạch trong
  // tiêu đề, khối mã, liên kết.
  let seen = new Set();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      if (n.nodeType !== 1) return NodeFilter.FILTER_ACCEPT;
      if (/^(PRE|A|SCRIPT|STYLE)$/.test(n.tagName) || n.classList.contains("term") || n.classList.contains("lk")) return NodeFilter.FILTER_REJECT;
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
      frag.append(text.slice(last, m.index), el("span", { className: "term", textContent: m[1], dataset: { k: idx } }));
      last = m.index + m[1].length;
    }
    if (frag) { frag.append(text.slice(last)); node.replaceWith(frag); }
  }
}
function tipHtml(e) {
  return `<b>${esc(e.term)}</b>${e.english ? ` <i>(${esc(e.english)})</i>` : ""}<br>${esc(e.meaning)}` +
    (e.note ? `<br><i>${esc(e.note)}</i>` : "") + `<br><i>Bấm để xem thêm</i>`;
}
document.addEventListener("mouseover", (ev) => {
  const t = ev.target.closest(".term"), tip = $("lTip");
  if (!t) { tip.style.display = "none"; return; }
  tip.innerHTML = tipHtml(glossary[+t.dataset.k]);
  const r = t.getBoundingClientRect();
  tip.style.display = "block";
  tip.style.left = Math.min(r.left, innerWidth - 400) + "px";
  tip.style.top = (r.bottom + 6 + tip.offsetHeight > innerHeight ? r.top - tip.offsetHeight - 6 : r.bottom + 6) + "px";
});
document.addEventListener("click", (ev) => {
  const t = ev.target.closest(".term");
  if (t) { showTermPanel(+t.dataset.k); return; }
  const a = ev.target.closest("[data-href]");
  if (a && a.closest("#page-learn")) { ev.preventDefault(); followLink(a.dataset.href); return; }
  const s = ev.target.closest("[data-src]");
  if (s && s.closest("#page-learn")) openSource(s.dataset.src);
  const d = ev.target.closest("[data-doc]");
  if (d && d.closest("#page-learn")) openDoc(d.dataset.doc, d.dataset.anchor);
});
async function showTermPanel(idx) {
  const e = glossary[idx], panel = $("lPanel");
  const where = [];
  const re = new RegExp(`(?<![\\p{L}\\p{N}_-])(${e.aliases.map(a => a.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})(?![\\p{L}\\p{N}_])`, "giu");
  for (const d of docs) { const txt = await loadDoc(d.path); const n = (txt.match(re) || []).length; if (n) where.push([d, n]); }
  where.sort((a, b) => b[1] - a[1]);
  panel.replaceChildren(
    el("span", { className: "x", textContent: "✕", onclick: () => (panel.style.display = "none") }),
    el("h3", { textContent: e.term }),
    e.english ? el("div", { className: "hint", textContent: "Tiếng Anh: " + e.english }) : "",
    el("p", { textContent: e.meaning }),
    e.note ? el("p", { className: "hint", textContent: "Ghi chú: " + e.note }) : "",
    el("div", { className: "hint", textContent: "Nhóm: " + e.section }),
    el("h4", { textContent: `Xuất hiện trong ${where.length} tài liệu` }),
    ...where.slice(0, 12).map(([d, n]) => el("div", {}, el("a", { className: "lk", textContent: `${d.title} (${n})`, onclick: () => { openDoc(d.path, null, e.aliases[0]); } }))),
  );
  panel.style.display = "block";
}

// ---------------- Đọc tài liệu ----------------
async function loadDoc(path) {
  if (!docCache.has(path)) docCache.set(path, await getText("/api/learn/doc?path=" + encodeURIComponent(path)));
  return docCache.get(path);
}
function followLink(href) {
  if (/^https?:/.test(href)) { window.open(href, "_blank"); return; }
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
  document.querySelectorAll("#lDocList div").forEach(d => d.classList.toggle("on", d.dataset.path === path));
  const md = $("lDoc");
  md.replaceChildren(el("div", { className: "md", innerHTML: renderMarkdown(await loadDoc(path), path) }));
  markTerms(md.firstChild);
  $("lToc").replaceChildren(el("b", { textContent: "Mục lục" }),
    ...[...md.querySelectorAll("h2, h3")].map(h => el("div", { className: h.tagName.toLowerCase(), textContent: h.textContent, onclick: () => h.scrollIntoView({ block: "start" }) })));
  md.scrollTop = 0;
  if (anchor) scrollToAnchor(anchor);
  else if (highlight) highlightFirst(md, highlight);
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
  showView("lSrc");
  $("lSrc").replaceChildren(el("div", { className: "srcview" },
    el("div", {}, el("a", { className: "lk", textContent: "← quay lại", onclick: () => showView(currentDoc ? "lRead" : "lMap") }), "  ", el("b", { textContent: path })),
    el("pre", { textContent: text })));
}

// ---------------- Bản đồ dự án ----------------
function stageBox(s) { return el("div", { className: "stage", dataset: { id: s.id }, onclick: () => showStage(s) }, el("b", { textContent: s.title }), el("small", { textContent: s.rq })); }
let mapData = null;
function renderMap() {
  const flow = [];
  mapData.stages.forEach((s, i) => { if (i) flow.push(el("div", { className: "arrow", textContent: "→" })); flow.push(stageBox(s)); });
  $("lMap").replaceChildren(
    el("p", { className: "mapnote", textContent: "Đường đi của dữ liệu từ camera trên UAV tới bản đồ của đội cứu hộ. Bấm vào một khâu để xem khâu đó làm gì, vì sao, kết quả đã có và file nào chứa nó. Hai ô viền đứt là hai mảng nằm cạnh đường đi." }),
    el("div", { className: "flow" }, ...flow),
    el("div", { className: "sidebox" }, ...mapData.side.map(stageBox)),
    el("div", { className: "detail", id: "lDetail" }, el("span", { className: "hint", textContent: "Chọn một khâu ở trên." })));
}
function showStage(s) {
  document.querySelectorAll(".stage").forEach(b => b.classList.toggle("on", b.dataset.id === s.id));
  const d = $("lDetail");
  d.replaceChildren(
    el("h3", { textContent: s.title }), el("span", { className: "rq", textContent: s.rq }),
    el("h4", { textContent: "Làm gì" }), el("p", { innerHTML: inline(s.what, "docs/x.md") }),
    el("h4", { textContent: "Vì sao" }), el("p", { innerHTML: inline(s.why, "docs/x.md") }),
    el("h4", { textContent: "Kết quả đã có" }),
    el("ul", {}, ...s.results.map(r => el("li", {}, r.text + " ", el("a", { className: "lk", textContent: "(" + r.doc + ")", dataset: { doc: r.doc } })))),
    el("h4", { textContent: "File chứa nó (bấm để xem mã)" }),
    el("div", {}, ...s.files.flatMap(f => [el("code", { className: "lk", textContent: f, dataset: { src: f } }), " "])),
    el("h4", { textContent: "Đọc thêm" }),
    el("ul", {}, ...s.docs.map(r => el("li", {}, el("a", { className: "lk", textContent: r.text, dataset: { doc: r.doc } })))));
  markTerms(d);
}

// ---------------- Bảng thuật ngữ và tìm kiếm ----------------
function renderGlossary(filter = "") {
  const f = filter.toLowerCase();
  const rows = [], bySection = new Map();
  glossary.forEach((e, idx) => { if (!bySection.has(e.section)) bySection.set(e.section, []); bySection.get(e.section).push([e, idx]); });
  for (const [section, list] of bySection) {
    const shown = list.filter(([e]) => !f || (e.term + e.english + e.meaning + e.note).toLowerCase().includes(f));
    if (!shown.length) continue;
    rows.push(el("h3", { textContent: section }), el("table", {},
      el("tr", {}, ...["Dùng trong tài liệu", "Tiếng Anh", "Nghĩa", "Ghi chú"].map(h => el("th", { textContent: h }))),
      ...shown.map(([e, idx]) => el("tr", { className: f ? "hit" : "" },
        el("td", {}, el("a", { className: "lk", textContent: e.term, onclick: () => showTermPanel(idx) })),
        el("td", { textContent: e.english }), el("td", { textContent: e.meaning }), el("td", { textContent: e.note })))));
  }
  $("lGloss").replaceChildren(el("p", { className: "mapnote", textContent: "Đọc từ docs/THUAT_NGU.md; sửa file đó rồi bấm lại tab này là thấy." }), ...rows);
}
async function search(q) {
  showView("lSearch");
  const needle = q.trim().toLowerCase();
  const hits = [];
  if (needle.length >= 2) {
    for (const d of docs) {
      const lines = (await loadDoc(d.path)).split("\n");
      let heading = d.title;
      lines.forEach(l => {
        if (/^#{1,4}\s/.test(l)) heading = l.replace(/^#+\s/, "");
        if (l.toLowerCase().includes(needle)) hits.push({ d, heading, line: l.replace(/[|#*`]/g, " ").trim() });
      });
    }
  }
  $("lSearch").replaceChildren(el("p", { className: "mapnote", textContent: `${hits.length} dòng chứa "${q}"` + (hits.length > 300 ? " (hiện 300 dòng đầu)" : "") }),
    ...hits.slice(0, 300).map(h => el("div", { className: "hit", onclick: () => openDoc(h.d.path, null, q.trim()) },
      el("small", { textContent: `${h.d.title} › ${h.heading}` }), el("div", { textContent: h.line.slice(0, 240) }))));
}

function showView(id) {
  document.querySelectorAll(".lview").forEach(v => v.classList.toggle("on", v.id === id));
  document.querySelectorAll(".lnav button").forEach(b => b.classList.toggle("on", b.dataset.view === id));
}

async function init() {
  const page = $("page-learn");
  page.replaceChildren(
    el("div", { className: "lnav" },
      el("button", { textContent: "Bản đồ dự án", dataset: { view: "lMap" }, onclick: () => showView("lMap") }),
      el("button", { textContent: "Đọc tài liệu", dataset: { view: "lRead" }, onclick: () => { if (!currentDoc) openDoc(docs[0].path); else showView("lRead"); } }),
      el("button", { textContent: "Thuật ngữ", dataset: { view: "lGloss" }, onclick: async () => { await loadGlossary(); renderGlossary($("lFilter").value); showView("lGloss"); } }),
      el("input", { id: "lFilter", type: "text", placeholder: "Tìm trong mọi tài liệu (Enter) hoặc lọc thuật ngữ…",
        onkeydown: (ev) => { if (ev.key === "Enter") search(ev.target.value); },
        oninput: (ev) => { if ($("lGloss").classList.contains("on")) renderGlossary(ev.target.value); } })),
    el("div", { className: "lbody" },
      el("div", { className: "lview on", id: "lMap" }),
      el("div", { className: "lview", id: "lRead" }, el("div", { className: "dlist", id: "lDocList" }), el("div", { className: "doc", id: "lDoc" }), el("div", { className: "toc", id: "lToc" })),
      el("div", { className: "lview", id: "lGloss" }),
      el("div", { className: "lview", id: "lSearch" }),
      el("div", { className: "lview", id: "lSrc" })),
    el("div", { id: "lTip" }), el("div", { className: "panel", id: "lPanel" }));
  [mapData, docs] = await Promise.all([getJson("/api/learn/map"), getJson("/api/learn/docs")]);
  await loadGlossary();
  const main = docs.filter(d => !d.path.startsWith("docs/results/")), results = docs.filter(d => d.path.startsWith("docs/results/"));
  $("lDocList").replaceChildren(el("h5", { textContent: "Tài liệu chính" }), ...main.map(docItem), el("h5", { textContent: "Kết quả đã đo" }), ...results.map(docItem));
  renderMap();
  showView("lMap");
}
function docItem(d) { return el("div", { textContent: d.title, dataset: { path: d.path }, onclick: () => openDoc(d.path) }); }
async function loadGlossary() {
  glossary = await getJson("/api/learn/glossary");
  aliasToEntry = new Map();
  buildTermRegex();
}

init();
})();
