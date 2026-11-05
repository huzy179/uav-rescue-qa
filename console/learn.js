// Tab "Hiểu dự án": bản đồ dự án, đọc tài liệu có giải thích thuật ngữ khi di chuột, bảng thuật ngữ, thẻ ghi nhớ, tìm kiếm.
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
const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

// Biểu tượng vẽ bằng SVG (không phụ thuộc phông emoji của máy).
const ICONS = {
  camera: '<path d="M4 7h3l2-3h6l2 3h3v12H4z"/><circle cx="12" cy="13" r="4"/>',
  detect: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  georef: '<path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
  confirm: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5"/>',
  send: '<path d="M4.5 10a10 10 0 0 1 15 0"/><path d="M7.5 13a6 6 0 0 1 9 0"/><circle cx="12" cy="17" r="1.5"/>',
  ground: '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z"/><path d="M9 4v14M15 6v14"/>',
  edge: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  data: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  map: '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
  book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/>',
  gloss: '<path d="M4 7V5h16v2M9 19h6M12 5v14"/>',
  cards: '<rect x="3" y="6" width="14" height="14" rx="2"/><path d="M7 3h12a2 2 0 0 1 2 2v12"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
  bulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
  quiz: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14"/><path d="M12 17.5h.01"/>',
  up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  code: '<path d="M14 3H6v18h12V7z"/><path d="M14 3v4h4"/><path d="M10 12l-2 2 2 2M14 12l2 2-2 2"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
  why: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
};
// replaceChildren không bỏ null như el(): lọc trước, nếu không sẽ hiện chữ "null".
const fill = (node, ...kids) => node.replaceChildren(...kids.filter(c => c !== null && c !== undefined && c !== ""));
const icon = (name) => { const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("class", "i"); s.setAttribute("aria-hidden", "true"); s.innerHTML = ICONS[name] || ICONS.info; return s; };

// Đánh dấu, chế độ màu: chỉ để tiện cho người đọc, lưu trong trình duyệt; mất cũng không sao.
const store = {
  get(k, d) { try { const v = localStorage.getItem("floodeye-learn-" + k); return v === null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("floodeye-learn-" + k, JSON.stringify(v)); } catch { /* chế độ riêng tư */ } },
};
let doneStages = new Set(store.get("stages", [])), seenDocs = new Set(store.get("docs", [])), theme = store.get("theme", "dark");

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
// Đoạn mở đầu bằng các nhãn này (TONG_QUAN, THUAT_TOAN) hiện thành hộp màu.
const CALLOUTS = [[/^<b>Làm gì/, "co-lam"], [/^<b>Vì sao/, "co-vi"], [/^<b>Cách khác/, "co-khac"], [/^<b>Trạng thái/, "co-trang"],
  [/^<b>Ở đâu/, "co-o"], [/^<b>(Ghi chú|Lưu ý|Cảnh báo|Rủi ro)/, "co-ghi"]];
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
    const p = inline(buf.join(" "), base), co = CALLOUTS.find(([re]) => re.test(p));
    out.push(co ? `<p class="co ${co[1]}">${p}</p>` : `<p>${p}</p>`);
  }
  return out.join("\n");
}

// ---------------- Thuật ngữ: tô màu lần đầu trong mỗi mục, màu theo loại, di chuột để xem ----------------
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
  // Mỗi mục h2 bắt đầu lại: thuật ngữ được tô lần đầu trong mục đó (THUAT_NGU, quy tắc 1). Không tô trong tiêu đề,
  // khối mã, liên kết, nút.
  let seen = new Set();
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode(n) {
      if (n.nodeType !== 1) return NodeFilter.FILTER_ACCEPT;
      if (/^(PRE|A|SCRIPT|STYLE|BUTTON|svg)$/i.test(n.tagName) || n.classList.contains("term") || n.classList.contains("lk") || n.classList.contains("noterm")) return NodeFilter.FILTER_REJECT;
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
  if (!e) return;
  fill(tip, kindBadge(e.kind), el("div", { className: "tt", textContent: e.term }),
    e.english ? el("div", { className: "en", textContent: e.english }) : null,
    el("div", { textContent: e.meaning }),
    e.note ? el("div", { className: "note", textContent: e.note }) : null,
    el("div", { className: "more", textContent: "Bấm để xem thêm và những chỗ nhắc tới" }));
  const r = t.getBoundingClientRect();
  tip.style.display = "block";
  tip.style.left = Math.max(8, Math.min(r.left, innerWidth - tip.offsetWidth - 8)) + "px";
  tip.style.top = (r.bottom + 8 + tip.offsetHeight > innerHeight ? Math.max(8, r.top - tip.offsetHeight - 8) : r.bottom + 8) + "px";
}
const hideTip = () => { if ($("lTip")) $("lTip").style.display = "none"; };
document.addEventListener("mouseover", (ev) => { const t = ev.target.closest && ev.target.closest(".term"); if (t) showTip(t); else hideTip(); });
document.addEventListener("focusin", (ev) => { const t = ev.target.closest && ev.target.closest(".term"); if (t) showTip(t); else hideTip(); });
document.addEventListener("scroll", hideTip, true);
document.addEventListener("keydown", (ev) => {
  if (!$("page-learn") || !$("page-learn").classList.contains("on")) return;
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName);
  if (ev.key === "Escape") { $("lPanel").style.display = "none"; hideTip(); if (typing) document.activeElement.blur(); }
  if (ev.key === "/" && !typing) { ev.preventDefault(); $("lFilter").focus(); }
  if (ev.key === "Enter" && ev.target.classList && ev.target.classList.contains("term")) showTermPanel(+ev.target.dataset.k);
  if ($("lCards").classList.contains("on") && !typing) {
    if (ev.key === " ") { ev.preventDefault(); $("fcard")?.classList.toggle("flip"); }
    if (ev.key === "ArrowRight") nextCard(true);
    if (ev.key === "ArrowLeft") nextCard(false);
  }
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
  hideTip();
  const re = termRe(e.aliases), where = [];
  for (const d of docs) { const n = ((await loadDoc(d.path)).match(re) || []).length; if (n) where.push([d, n]); }
  where.sort((a, b) => b[1] - a[1]);
  fill(panel,
    el("button", { className: "x", textContent: "✕", title: "Đóng (Esc)", ariaLabel: "Đóng", onclick: () => (panel.style.display = "none") }),
    kindBadge(e.kind), el("h3", { textContent: e.term }),
    e.english ? el("div", { className: "phint", textContent: "Tiếng Anh: " + e.english }) : null,
    el("p", { textContent: e.meaning }),
    e.note ? el("p", { className: "phint", textContent: "Ghi chú: " + e.note }) : null,
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
const minutes = (text) => Math.max(1, Math.round(text.split(/\s+/).length / 200));  // khoảng 200 từ mỗi phút
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
  const heads = [...md.querySelectorAll("h2, h3")];
  $("lToc").replaceChildren(el("div", { className: "tt", textContent: "Trong trang này" }),
    ...heads.map((h, k) => el("div", { className: "ti " + h.tagName.toLowerCase(), textContent: h.textContent, dataset: { k }, onclick: () => h.scrollIntoView({ block: "start" }) })));
  md.style.scrollBehavior = "auto"; md.scrollTop = 0; md.style.scrollBehavior = "";
  onDocScroll();
  if (anchor) scrollToAnchor(anchor);
  else if (highlight) highlightFirst(md, highlight);
}
function onDocScroll() {
  const d = $("lDoc"), max = d.scrollHeight - d.clientHeight;
  $("lProg").style.width = (max > 0 ? Math.min(100, 100 * d.scrollTop / max) : 100) + "%";
  $("lTop").classList.toggle("show", d.scrollTop > 600);
  // Mục lục sáng mục đang đọc.
  const heads = [...d.querySelectorAll("h2, h3")], top = d.getBoundingClientRect().top + 80;
  let cur = -1;
  heads.forEach((h, k) => { if (h.getBoundingClientRect().top <= top) cur = k; });
  document.querySelectorAll("#lToc .ti").forEach(t => t.classList.toggle("on", +t.dataset.k === cur));
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
    el("div", { className: "bar0" }, el("button", { className: "btn", onclick: () => showView(back === "lSrc" ? "lMap" : back) }, "← Quay lại"), icon("code"), el("code", { textContent: path })),
    el("pre", { textContent: text })));
}
function renderDocList() {
  const item = (d) => el("div", { className: "di" + (d.path === currentDoc ? " on" : ""), dataset: { path: d.path }, tabIndex: 0, onclick: () => openDoc(d.path),
    onkeydown: (ev) => { if (ev.key === "Enter") openDoc(d.path); } },
    el("span", { textContent: d.title }),
    el("span", { className: "meta" }, seenDocs.has(d.path) ? el("span", { className: "seen", textContent: "✓ " }) : null, d.minutes ? `${d.minutes} ph` : ""));
  const main = docs.filter(d => !d.path.startsWith("docs/results/")), results = docs.filter(d => d.path.startsWith("docs/results/"));
  $("lDocList").replaceChildren(el("h5", { textContent: "Tài liệu chính" }), ...main.map(item), el("h5", { textContent: `Kết quả đã đo (${results.length})` }), ...results.map(item));
}

// ---------------- Bản đồ dự án ----------------
let mapData = null, allStages = [], rqFilter = null;
function stageCard(s, n) {
  return el("button", { className: "stage", dataset: { id: s.id }, style: { "--c": s.color }, onclick: () => showStage(s), title: s.title },
    n ? el("span", { className: "num", textContent: String(n).padStart(2, "0") }) : null,
    el("div", { className: "ico" }, icon(s.id)),
    el("div", {}, el("b", { textContent: s.title.replace(/^\d+\.\s*/, "") }), el("span", { className: "sum", textContent: s.summary }),
      doneStages.has(s.id) ? el("span", { className: "done" }, icon("check"), "đã hiểu") : null));
}
function ring() {
  const done = allStages.filter(s => doneStages.has(s.id)).length, total = allStages.length, c = 2 * Math.PI * 26;
  return el("div", { className: "ring", innerHTML:
    `<svg width="76" height="76" viewBox="0 0 64 64" role="img" aria-label="${done} trên ${total} khâu đã hiểu"><circle cx="32" cy="32" r="26" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="6"/>` +
    `<circle cx="32" cy="32" r="26" fill="none" stroke="#34e0b4" stroke-width="6" stroke-linecap="round" stroke-dasharray="${c * done / total} ${c}" transform="rotate(-90 32 32)"/>` +
    `<text x="32" y="37" text-anchor="middle" font-size="14" font-weight="600" fill="#fff">${done}/${total}</text></svg>khâu đã hiểu` });
}
const RQS = [["Câu hỏi 1", "Nhìn thấy người không?"], ["Câu hỏi 2", "Máy nhỏ chạy kịp không?"], ["Câu hỏi 3", "Báo đúng về trạm không?"]];
function renderMap(keepDetail) {
  const flow = [];
  mapData.stages.forEach((s, i) => { if (i) flow.push(el("div", { className: "arrow", ariaHidden: "true" })); flow.push(stageCard(s, i + 1)); });
  const detail = keepDetail && $("lDetail") ? $("lDetail") : el("div", { className: "detail", id: "lDetail" },
    el("div", { className: "dempty" }, icon("info"), "Chọn một khâu ở trên để bắt đầu. Gợi ý: đi lần lượt từ khâu 1 tới khâu 6, mỗi ngày một khâu; cuối mỗi khâu có câu hỏi tự kiểm tra."));
  $("lMap").replaceChildren(
    el("div", { className: "hero" },
      el("div", {},
        el("h2", { textContent: "FloodEye: từ camera trên drone tới đội cứu hộ" }),
        el("p", { textContent: "Đồ án trả lời ba câu hỏi theo đường đi của dữ liệu. Bấm một câu hỏi để thấy khâu nào trả lời nó; bấm một khâu để xem nó làm gì, vì sao, kết quả đã có, file chứa nó và tự kiểm tra." }),
        el("div", { className: "rqchips" }, ...RQS.map(([k, v]) => el("button", { className: "rqchip" + (rqFilter === k ? " on" : ""), textContent: `${k}: ${v}`, onclick: () => { rqFilter = rqFilter === k ? null : k; renderMap(true); } })),
          el("button", { className: "rqchip more", onclick: async () => { showView("lQuest"); await renderQuestions(rqFilter ? "RQ" + rqFilter.slice(-1) : null); } }, "Xem các câu hỏi con →"))),
      ring()),
    el("div", { className: "mapwrap" },
      el("div", { className: "sectionlabel", textContent: "Đường đi của dữ liệu" }),
      el("div", { className: "flow" }, ...flow),
      el("div", { className: "sectionlabel", style: { "margin-top": "26px" }, textContent: "Hai mảng nằm cạnh đường đi" }),
      el("div", { className: "sidebox" }, ...mapData.side.map(s => stageCard(s, 0))),
      detail));
  if (rqFilter) document.querySelectorAll("#lMap .stage").forEach(b => b.classList.toggle("dim", !allStages.find(s => s.id === b.dataset.id).rq.startsWith(rqFilter)));
  const on = $("lDetail").dataset.id;
  if (on) document.querySelectorAll("#lMap .stage").forEach(b => b.classList.toggle("on", b.dataset.id === on));
}
function metricCard(m, color) {
  const bar = (cls, label, v) => el("div", { className: "bar " + cls },
    el("span", { className: "n", textContent: label, title: label }),
    el("div", { className: "track" }, el("div", { className: "fill", style: { width: "0%" }, dataset: { w: (100 * v / m.max) + "%" } })),
    el("span", { className: "v", textContent: vn(v) + (m.unit || "") }));
  return el("div", { className: "metric noterm", style: { "--c": color } },
    el("div", { className: "ml", textContent: m.label }),
    bar("a", m.a_label, m.a), bar("b", m.b_label, m.b),
    el("div", { className: "src" }, "Nguồn: ", el("a", { className: "lk", textContent: m.doc, dataset: { doc: m.doc } })));
}
function quizItem(q, n) {
  const box = el("div", { className: "qa" });
  const btn = el("button", { className: "q", ariaExpanded: "false", onclick: () => { const open = box.classList.toggle("open"); btn.setAttribute("aria-expanded", open); btn.querySelector(".hint2").textContent = open ? "ẩn" : "xem đáp án"; } },
    el("span", { className: "n", textContent: n }), el("span", { textContent: q.q }), el("span", { className: "hint2", textContent: "xem đáp án" }));
  box.append(btn, el("div", { className: "a" }, q.a, el("a", { className: "lk src", textContent: "Nguồn: " + q.doc, dataset: { doc: q.doc } })));
  return box;
}
function showStage(s) {
  const i = allStages.findIndex(x => x.id === s.id), prev = allStages[i - 1], next = allStages[i + 1];
  const done = doneStages.has(s.id);
  const d = $("lDetail");
  d.dataset.id = s.id;
  document.querySelectorAll("#lMap .stage").forEach(b => b.classList.toggle("on", b.dataset.id === s.id));
  d.style.setProperty("--c", s.color);
  d.replaceChildren(
    el("div", { className: "dhead" },
      el("div", { className: "ico" }, icon(s.id)),
      el("div", {}, el("h3", { textContent: s.title }), el("span", { className: "rq", textContent: s.rq })),
      el("div", { className: "acts" },
        el("button", { className: "btn" + (done ? " done" : ""), onclick: () => {
          if (done) doneStages.delete(s.id); else doneStages.add(s.id);
          store.set("stages", [...doneStages]); renderMap(true); showStage(s);
        } }, icon("check"), done ? "Đã hiểu" : "Đánh dấu đã hiểu"))),
    el("p", { className: "analogy" }, icon("bulb"), el("span", {}, el("b", { textContent: "Hình dung: " }), s.analogy)),
    el("div", { className: "dgrid" },
      el("div", { className: "dcell" }, el("h4", {}, icon("info"), "Làm gì"), el("p", { innerHTML: inline(s.what, "docs/x.md") })),
      el("div", { className: "dcell" }, el("h4", {}, icon("why"), "Vì sao"), el("p", { innerHTML: inline(s.why, "docs/x.md") })),
      el("div", { className: "dcell wide" }, el("h4", {}, icon("chart"), "Kết quả đã có"),
        s.metrics.length ? el("div", { className: "metrics" }, ...s.metrics.map(m => metricCard(m, s.color))) : null,
        el("ul", {}, ...s.results.map(r => el("li", {}, r.text + " ", el("a", { className: "lk", textContent: "→ " + r.doc.replace(/^docs\//, ""), dataset: { doc: r.doc } }))))),
      el("div", { className: "dcell wide" }, el("h4", {}, icon("quiz"), `Tự kiểm tra (${s.quiz.length} câu)`),
        el("div", { className: "quiz noterm" }, ...s.quiz.map((q, k) => quizItem(q, k + 1)))),
      el("div", { className: "dcell" }, el("h4", {}, icon("code"), "File chứa nó (bấm để xem mã)"),
        el("div", { className: "files" }, ...s.files.map(f => el("code", { className: "lk", textContent: f, dataset: { src: f } })))),
      el("div", { className: "dcell" }, el("h4", {}, icon("book"), "Đọc thêm"),
        el("ul", {}, ...s.docs.map(r => el("li", {}, el("a", { className: "lk", textContent: r.text, dataset: { doc: r.doc } })))))),
    el("div", { className: "dnav" },
      prev ? el("button", { className: "btn", textContent: "← " + prev.title, onclick: () => showStage(prev) }) : el("span"),
      next ? el("button", { className: "btn primary", textContent: next.title + " →", onclick: () => showStage(next) }) : el("span")));
  markTerms(d);
  requestAnimationFrame(() => d.querySelectorAll(".fill").forEach(f => (f.style.width = f.dataset.w)));
  d.scrollIntoView({ block: "start", behavior: reduceMotion() ? "auto" : "smooth" });
}

// ---------------- Bảng thuật ngữ, thẻ ghi nhớ, tìm kiếm ----------------
let glossKind = null;
function kindChips(onPick, current, withAll = true) {
  const counts = Object.fromEntries(Object.keys(KINDS).map(k => [k, glossary.filter(e => e.kind === k).length]));
  return [
    withAll ? el("button", { className: "chip" + (current ? "" : " on"), textContent: `Tất cả (${glossary.length})`, onclick: () => onPick(null) }) : null,
    ...Object.entries(KINDS).map(([k, v]) => el("button", { className: "chip" + (current === k ? " on" : ""), onclick: () => onPick(k) },
      el("span", { className: "dot", style: { background: `var(--k-${k})` } }), `${v} (${counts[k]})`)),
  ];
}
function renderGlossary(filter = "") {
  const f = filter.toLowerCase(), groups = new Map();
  glossary.forEach((e, idx) => {
    if (glossKind && e.kind !== glossKind) return;
    if (f && !(e.term + e.english + e.meaning + e.note).toLowerCase().includes(f)) return;
    if (!groups.has(e.section)) groups.set(e.section, []);
    groups.get(e.section).push([e, idx]);
  });
  $("lGloss").replaceChildren(
    el("div", { className: "chips" }, ...kindChips((k) => { glossKind = k; renderGlossary($("lFilter").value); }, glossKind),
      el("span", { className: "mapnote", style: { margin: "0 0 0 auto" }, textContent: "Đọc từ docs/THUAT_NGU.md; gõ vào ô tìm ở trên để lọc." })),
    ...(groups.size ? [] : [el("p", { className: "mapnote", textContent: "Không có thuật ngữ nào khớp." })]),
    ...[...groups].map(([section, list]) => el("div", { className: "ggroup" },
      el("h3", { textContent: section.replace(/^\d+\.\s*/, "") }),
      el("div", { className: "gcards" }, ...list.map(([e, idx]) => el("div", { className: "gcard " + e.kind, tabIndex: 0, onclick: () => showTermPanel(idx), onkeydown: (ev) => { if (ev.key === "Enter") showTermPanel(idx); } },
        el("b", { textContent: e.term }), e.english ? el("div", { className: "en", textContent: e.english }) : null, el("p", { textContent: e.meaning })))))));
}
// Thẻ ghi nhớ: mặt trước là thuật ngữ, lật ra nghĩa; "Đã nhớ" thì bỏ khỏi lượt ôn.
let cardKind = null, cardOrder = [], cardPos = 0, known = new Set(store.get("known", []));
function deck() { return glossary.map((e, i) => i).filter(i => (!cardKind || glossary[i].kind === cardKind) && !known.has(glossary[i].term)); }
function shuffle() { cardOrder = deck().sort(() => Math.random() - 0.5); cardPos = 0; }
function nextCard(fwd) { if (!cardOrder.length) return; cardPos = (cardPos + (fwd ? 1 : cardOrder.length - 1)) % cardOrder.length; renderCards(); }
function renderCards() {
  if (!cardOrder.length) shuffle();
  const total = glossary.filter(e => !cardKind || e.kind === cardKind).length, left = deck().length;
  const head = el("div", { className: "chips" }, ...kindChips((k) => { cardKind = k; shuffle(); renderCards(); }, cardKind),
    el("span", { className: "mapnote", style: { margin: "0 0 0 auto" }, textContent: "Phím cách: lật · ← →: thẻ trước, sau" }));
  if (!cardOrder.length) {
    $("lCards").replaceChildren(head, el("div", { className: "flash" }, el("div", { className: "fside", style: { position: "static", height: "220px" } },
      el("div", { className: "big", textContent: "Đã nhớ hết nhóm này" }), el("div", { className: "mean", textContent: `${total} thuật ngữ.` }),
      el("button", { className: "btn primary", textContent: "Ôn lại từ đầu", onclick: () => { glossary.forEach(e => { if (!cardKind || e.kind === cardKind) known.delete(e.term); }); store.set("known", [...known]); shuffle(); renderCards(); } }))));
    return;
  }
  const e = glossary[cardOrder[cardPos]];
  const card = el("div", { className: "fcard", id: "fcard", tabIndex: 0, onclick: () => card.classList.toggle("flip") },
    el("div", { className: "fside" }, kindBadge(e.kind), el("div", { className: "big", textContent: e.term }), e.english ? el("div", { className: "en", textContent: e.english }) : null, el("div", { className: "tap", textContent: "Bấm để lật" })),
    el("div", { className: "fside back" }, el("div", { className: "big", style: { "font-size": "20px" }, textContent: e.term }), el("div", { className: "mean", textContent: e.meaning }), e.note ? el("div", { className: "en", textContent: e.note }) : null));
  $("lCards").replaceChildren(head,
    el("div", { className: "flash" }, card,
      el("div", { className: "fctl" },
        el("button", { className: "btn", textContent: "← Thẻ trước", onclick: () => nextCard(false) }),
        el("button", { className: "btn", textContent: "Chưa nhớ, xem tiếp", onclick: () => nextCard(true) }),
        el("button", { className: "btn done", onclick: () => { known.add(e.term); store.set("known", [...known]); cardOrder.splice(cardPos, 1); if (cardPos >= cardOrder.length) cardPos = 0; renderCards(); } }, icon("check"), "Đã nhớ")),
      el("div", { className: "fstat", textContent: `Thẻ ${cardPos + 1}/${cardOrder.length} · đã nhớ ${total - left}/${total}` })));
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
  $("lSearch").replaceChildren(el("p", { className: "mapnote", textContent: needle.length < 2 ? "Gõ ít nhất 2 ký tự rồi Enter." : `${hits.length} dòng chứa "${q.trim()}" trong ${new Set(hits.map(h => h.d.path)).size} tài liệu` + (hits.length > 300 ? " (hiện 300 dòng đầu)" : "") }),
    ...hits.slice(0, 300).map(h => el("div", { className: "hit", tabIndex: 0, onclick: () => openDoc(h.d.path, null, q.trim()), onkeydown: (ev) => { if (ev.key === "Enter") openDoc(h.d.path, null, q.trim()); } },
      el("small", { textContent: `${h.d.title} › ${h.heading}` }), show(h.line))));
}

// ---------------- Câu hỏi nghiên cứu (TONG_QUAN mục 1.3) ----------------
const RQ_COLORS = { RQ1: "var(--blue)", RQ2: "var(--amber)", RQ3: "var(--violet)" };
const STATUS = { done: "Đã có câu trả lời", tool: "Có công cụ, chưa có bảng", wait: "Đang chờ" };
function goStage(name) {
  const s = allStages.find(x => x.title.replace(/^\d+\.\s*/, "") === name);
  if (!s) return;
  showView("lMap"); showStage(s);
}
async function renderQuestions(focus) {
  const data = await getJson("/api/learn/questions");
  const count = (kind) => data.questions.reduce((n, q) => n + q.subs.filter(s => s.kind === kind).length, 0);
  const total = data.questions.reduce((n, q) => n + q.subs.length, 0);
  const card = (q) => {
    const done = q.subs.filter(s => s.kind === "done").length;
    return el("section", { className: "rqcard", id: "rq-" + q.id, style: { "--c": RQ_COLORS[q.id] || "var(--blue)" } },
      el("div", { className: "rqhead" },
        el("span", { className: "rqid noterm", textContent: q.id }),
        el("div", {}, el("h3", { textContent: q.title.replace(/^RQ\d\.\s*/, "") }),
          el("p", { className: "official" }, el("span", { className: "tag", textContent: "Theo đề cương" }), q.text)),
        el("div", { className: "rqprog" },
          el("div", { className: "num", textContent: `${done}/${q.subs.length}` }), el("div", { className: "lbl", textContent: "câu hỏi con đã có câu trả lời" }),
          el("div", { className: "track" }, el("div", { className: "fill", style: { width: (100 * done / q.subs.length) + "%" } })))),
      el("div", { className: "subs" }, ...q.subs.map(s => el("div", { className: "sub " + s.kind },
        el("span", { className: "sid", textContent: s.id }),
        el("div", { className: "sbody" },
          el("div", { className: "sq", textContent: s.question }),
          el("div", { className: "show" }, el("b", { textContent: "Trả lời bằng: " }), s.how),
          el("div", { className: "smeta noterm" },
            el("button", { className: "stagechip", title: "Mở khâu này trên bản đồ", onclick: () => goStage(s.stage) }, icon("map"), s.stage),
            ...s.sources.map(src => src.doc ? el("a", { className: "lk", textContent: src.name, dataset: { doc: src.doc } }) : el("span", { textContent: src.name })))),
        el("span", { className: "pill noterm " + s.kind, title: STATUS[s.kind] }, s.status)))));
  };
  $("lQuest").replaceChildren(
    el("div", { className: "qhero" },
      el("div", {}, el("h2", { textContent: "Ba câu hỏi nghiên cứu và các câu hỏi con" }),
        el("p", { textContent: "Ba câu hỏi chính theo đề cương. Mỗi câu chia thành các câu hỏi con đo được, ghi rõ trả lời bằng phép đo nào, thuộc khâu nào trên bản đồ, đã có kết quả chưa. Đọc từ TONG_QUAN mục 1.3 (đề xuất 6/11, chờ cô)." })),
      el("div", { className: "qstat" },
        ...Object.entries(STATUS).map(([k, v]) => el("div", { className: "qs " + k }, el("b", { textContent: count(k) }), el("span", { textContent: v }))),
        el("div", { className: "qs" }, el("b", { textContent: total }), el("span", { textContent: "câu hỏi con" })))),
    el("div", { className: "qwrap" },
      el("div", { className: "thesis" }, icon("bulb"), el("div", {}, el("div", { className: "tt", textContent: "Luận điểm xuyên suốt" }), el("p", { innerHTML: inline(data.thesis, "docs/x.md") }))),
      ...data.questions.map(card)));
  markTerms($("lQuest"));
  if (focus) $("rq-" + focus)?.scrollIntoView({ block: "start" });
}

function showView(id) {
  document.querySelectorAll(".lview").forEach(v => v.classList.toggle("on", v.id === id));
  document.querySelectorAll(".lnav .nb[data-view]").forEach(b => b.classList.toggle("on", b.dataset.view === id));
  $("lPanel").style.display = "none"; hideTip();
}
function applyTheme() {
  $("page-learn").classList.toggle("light", theme === "light");
  document.body.classList.toggle("theme-dark", theme === "dark");
  document.body.classList.toggle("theme-light", theme === "light");
  const b = $("lTheme");
  if (b) { b.replaceChildren(icon(theme === "dark" ? "sun" : "moon")); b.title = theme === "dark" ? "Chuyển sang nền sáng" : "Chuyển sang nền tối"; b.ariaLabel = b.title; }
}
// Thanh tab chung của console đổi màu theo khi đang ở tab "Hiểu dự án".
function syncBody() { document.body.classList.toggle("learn-on", $("page-learn").classList.contains("on")); }
document.querySelectorAll(".tab").forEach(t => t.addEventListener("click", () => setTimeout(syncBody)));

async function init() {
  const page = $("page-learn");
  const navBtn = (view, ic, label, onclick) => el("button", { className: "nb", dataset: { view }, onclick }, icon(ic), el("span", { className: "lbl", textContent: label }));
  page.replaceChildren(
    el("div", { className: "lnav" },
      navBtn("lMap", "map", "Bản đồ dự án", () => { showView("lMap"); }),
      navBtn("lRead", "book", "Đọc tài liệu", () => { if (!currentDoc) openDoc(docs[0].path); else showView("lRead"); }),
      navBtn("lGloss", "gloss", "Thuật ngữ", async () => { await loadGlossary(); renderGlossary($("lFilter").value); showView("lGloss"); }),
      navBtn("lQuest", "quiz", "Câu hỏi", () => { showView("lQuest"); renderQuestions(); }),
      navBtn("lCards", "cards", "Thẻ ghi nhớ", () => { renderCards(); showView("lCards"); }),
      el("div", { className: "search" }, icon("search"),
        el("input", { id: "lFilter", type: "search", placeholder: "Tìm trong mọi tài liệu, Enter", ariaLabel: "Tìm trong mọi tài liệu",
          onkeydown: (ev) => { if (ev.key === "Enter") search(ev.target.value); },
          oninput: (ev) => { if ($("lGloss").classList.contains("on")) renderGlossary(ev.target.value); } }),
        el("kbd", { textContent: "/" })),
      el("button", { className: "nb theme", id: "lTheme", onclick: () => { theme = theme === "dark" ? "light" : "dark"; store.set("theme", theme); applyTheme(); } })),
    el("div", { className: "lbody" },
      el("div", { className: "lview on", id: "lMap" }),
      el("div", { className: "lview", id: "lRead" },
        el("div", { className: "dlist", id: "lDocList" }),
        el("div", { className: "docwrap" },
          el("div", { className: "progress" }, el("div", { id: "lProg" })),
          el("div", { className: "tlegend" }, "Từ tô màu là thuật ngữ, di chuột hoặc bấm để xem:",
            ...Object.entries(KINDS).map(([k, v]) => el("span", { className: "lg" }, el("span", { className: "sw", style: { color: `var(--k-${k})` }, textContent: "Aa" }), v))),
          el("div", { className: "doc", id: "lDoc", onscroll: onDocScroll }),
          el("button", { className: "totop", id: "lTop", title: "Lên đầu trang", ariaLabel: "Lên đầu trang", onclick: () => ($("lDoc").scrollTop = 0) }, icon("up"))),
        el("div", { className: "toc", id: "lToc" })),
      el("div", { className: "lview", id: "lGloss" }),
      el("div", { className: "lview", id: "lQuest" }),
      el("div", { className: "lview", id: "lCards" }),
      el("div", { className: "lview", id: "lSearch" }),
      el("div", { className: "lview", id: "lSrc" })),
    el("div", { id: "lTip", role: "tooltip" }), el("div", { className: "panel", id: "lPanel", role: "dialog" }));
  applyTheme(); syncBody();
  [mapData, docs] = await Promise.all([getJson("/api/learn/map"), getJson("/api/learn/docs")]);
  allStages = [...mapData.stages, ...mapData.side];
  await loadGlossary();
  renderDocList();
  renderMap();
  showView("lMap");
  // Thời gian đọc ước tính, tính sau khi trang đã hiện.
  for (const d of docs) d.minutes = minutes(await loadDoc(d.path));
  renderDocList();
}
async function loadGlossary() {
  glossary = await getJson("/api/learn/glossary");
  aliasToEntry = new Map();
  buildTermRegex();
}

init();
})();
