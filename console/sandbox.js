// Sân thử mô phỏng (console/sandbox.py): form tham số, câu hỏi "nếu… thì sao" dựng sẵn, chạy, bảng so sánh các lần.
// Dùng các hàm chung của index.html: $, el, get, vn.
(() => {
  const LABELS = {
    alt_m: "Độ cao bay (m)", speed_mps: "Tốc độ bay (m/s)", pattern: "Đường bay", leg_m: "Chiều dài mỗi đường (m)",
    duration_s: "Thời gian bay (s)", n_people: "Số người", gps_sigma_m: "Nhiễu GPS σ (m)", yaw_bias_deg: "Lệch la bàn (°)", yaw_calib: "Tự hiệu chỉnh la bàn",
    recall_model: "Mô hình", target_person_px: "Thu nhỏ theo độ cao về (px)", fps: "Khung xử lý mỗi giây",
    device: "Thiết bị giả lập", net_loss: "Mất gói (0–0,8)", outage_start_s: "Mất sóng từ giây", outage_len_s: "Mất sóng trong (s)",
    link_probe: "Thăm dò đường truyền", render: "Vẽ ảnh tổng hợp (có video)", realtime_speed: "Tốc độ phát (0 = nhanh nhất)",
    seed: "Seed", label: "Ghi chú",
  };
  const CHOICES = {
    pattern: [["zigzag", "quét luống cày"], ["straight", "bay thẳng"]],
    recall_model: [["E2c", "E2c (tinh chỉnh)"], ["E1", "E1 (gốc COCO)"]],
  };
  const METRIC_LABELS = {
    n_people: "Số người", missed_rate: "Tỉ lệ bỏ sót", false_alarms_per_min: "Báo nhầm / phút", merge_errors: "Gộp nhầm",
    split_errors: "Tách nhầm", time_to_alert_s_median: "Tới cảnh báo (s, trung vị)", position_error_m_median: "Sai số vị trí (m, trung vị)",
    within_reported_radius_95: "Trong vùng tìm 95%", delivery_delay_s_max: "Trễ gửi lớn nhất (s)", lost_rate: "Mất cảnh báo",
    frames_processed: "Khung đã xử lý",
  };
  // Mỗi câu hỏi hay gặp ở buổi bảo vệ là một bộ thay đổi so với mặc định.
  const PRESETS = [
    ["Bay cao 120 m thì sao?", { alt_m: 120, label: "bay 120 m" }],
    ["Dùng mô hình gốc (chưa tinh chỉnh)?", { recall_model: "E1", label: "mô hình gốc E1" }],
    ["Bay thấp 30 m, có thu nhỏ theo độ cao?", { alt_m: 30, target_person_px: 10, label: "30 m, thu nhỏ 10 px" }],
    ["Mất sóng 30 s giữa chuyến?", { outage_start_s: 40, outage_len_s: 30, label: "mất sóng 30 s" }],
    ["Mất sóng 30 s, không thăm dò đường truyền?", { outage_start_s: 40, outage_len_s: 30, link_probe: false, label: "mất sóng, không thăm dò" }],
    ["GPS kém (σ 5 m), la bàn lệch 5°?", { gps_sigma_m: 5, yaw_bias_deg: 5, label: "GPS kém" }],
    ["Thiết bị yếu (Orin Nano), 8 khung/giây?", { device: "orin_nano_super", fps: 8, label: "Orin Nano 8 khung/giây" }],
    ["Bay nhanh 15 m/s?", { speed_mps: 15, label: "15 m/s" }],
    ["La bàn lệch 10° ở 100 m, không hiệu chỉnh?", { alt_m: 100, yaw_bias_deg: 10, label: "la bàn lệch 10°" }],
    ["La bàn lệch 10° ở 100 m, drone tự hiệu chỉnh?", { alt_m: 100, yaw_bias_deg: 10, yaw_calib: true, label: "la bàn lệch 10°, tự hiệu chỉnh" }],
  ];
  let opts = null, timer = null, shown = null;
  const page = $("page-sandbox");
  // Đếm (người, khung, gộp, tách) in số nguyên; tỉ lệ và thời gian luôn ba chữ số thập phân như docs/results.
  const COUNTS = new Set(["n_people", "merge_errors", "split_errors", "frames_processed"]);
  const fmtNum = (x, key) => x === null || x === undefined ? "–" : COUNTS.has(key) || (key === undefined && Number.isInteger(x)) ? String(x) : vn(x, 3);
  const fmtVal = (k, v) => v === null || v === undefined || v === "" ? "–" : typeof v === "boolean" ? (v ? "có" : "không")
    : CHOICES[k] ? (CHOICES[k].find(c => c[0] === v) || [v, v])[1] : typeof v === "number" ? fmtNum(v) : String(v);

  function input(key, spec, value) {
    if (CHOICES[key]) return el("select", { id: "sb_" + key }, ...CHOICES[key].map(([v, t]) => el("option", { value: v, textContent: t, selected: v === value })));
    if (key === "device") return el("select", { id: "sb_device" }, el("option", { value: "", textContent: "không giả lập (máy chạy demo)" }),
      ...opts.devices.map(d => el("option", { value: d, textContent: d, selected: d === value })));
    if (spec.type === "boolean") return el("input", { id: "sb_" + key, type: "checkbox", checked: !!value });
    const range = spec.anyOf ? spec.anyOf.find(x => x.type) : spec;
    if (range.type === "string") return el("input", { id: "sb_" + key, type: "text", value: value ?? "", maxLength: range.maxLength || 60 });
    const box = el("input", { id: "sb_" + key, type: "number", value: value ?? "", step: range.type === "integer" ? 1 : "any" });
    if (range.minimum !== undefined) box.min = range.minimum;
    if (range.maximum !== undefined) box.max = range.maximum;
    if (spec.anyOf) box.placeholder = "trống: tắt";
    return box;
  }

  function readForm() {
    const req = {};
    for (const [key, spec] of Object.entries(opts.fields)) {
      const box = $("sb_" + key);
      if (!box) continue;
      if (box.type === "checkbox") req[key] = box.checked;
      else if (box.tagName === "SELECT") req[key] = box.value === "" ? null : box.value;
      else if (box.type === "number") req[key] = box.value === "" ? (spec.anyOf ? null : opts.defaults[key]) : Number(box.value);
      else req[key] = box.value;
    }
    return req;
  }
  function fillForm(values) {
    for (const [key, v] of Object.entries(values)) {
      const box = $("sb_" + key);
      if (!box) continue;
      if (box.type === "checkbox") box.checked = !!v; else box.value = v ?? "";
    }
  }

  async function start() {
    const msg = $("sbMsg");
    msg.textContent = "";
    const r = await fetch("/api/sandbox", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(readForm()) });
    const body = await r.json();
    if (!r.ok) { msg.textContent = typeof body.detail === "string" ? body.detail : body.detail.map(d => `${LABELS[d.loc.at(-1)] || d.loc.at(-1)}: ${d.msg}`).join("; "); return; }
    shown = body.id;
    refresh();
  }

  function groundLink(req) {
    if (!opts.ground_url) return null;
    const live = req && req.render && req.realtime_speed > 0 ? `?video=${encodeURIComponent(opts.live_url)}` : "";
    return el("a", { className: "sbbtn", href: opts.ground_url + "/" + live, target: "_blank", rel: "noopener", textContent: "Mở màn hình điều phối ↗" });
  }

  function statusCard(run) {
    const st = run.status || {};
    const cls = st.state === "done" ? "ok" : st.state === "error" ? "err" : "run";
    return el("div", { className: "sbcard" },
      el("div", { className: "sbhead" }, el("b", { textContent: run.request.label || run.id }), el("span", { className: "sbstate " + cls, textContent: st.phase || "" })),
      el("div", { className: "sbrow" }, groundLink(run.request) || "", el("span", { className: "hint", textContent: run.id })),
      run.metrics ? metricsGrid(run.metrics) : "",
      el("details", {}, el("summary", { textContent: "Lệnh đã chạy và log" }), el("pre", { textContent: run.commands + "\n" + run.log_tail })));
  }
  function metricsGrid(m) {
    return el("div", { className: "sbgrid" }, ...Object.entries(METRIC_LABELS).map(([k, t]) =>
      el("div", { className: "sbm" }, el("span", { textContent: t }), el("b", { textContent: fmtNum(m[k], k) }))));
  }

  function compareTable(cmp) {
    if (!cmp.rows.length) return el("p", { className: "hint", textContent: "Chưa có lần chạy nào xong." });
    const head = ["Lần chạy", ...cmp.param_keys.map(k => LABELS[k] || k), ...cmp.metric_keys.map(k => METRIC_LABELS[k] || k)];
    return el("div", { className: "sbtablewrap" }, el("table", { className: "sbtable" },
      el("thead", {}, el("tr", {}, ...head.map((h, i) => el("th", { textContent: h, className: i > cmp.param_keys.length ? "m" : "" })))),
      el("tbody", {}, ...cmp.rows.map(r => el("tr", { className: r.id === shown ? "on" : "", onclick: () => { shown = r.id; refresh(); } },
        el("td", { textContent: r.label || r.id }),
        ...cmp.param_keys.map(k => el("td", { textContent: fmtVal(k, r.params[k]) })),
        ...cmp.metric_keys.map(k => el("td", { className: "m", textContent: fmtNum(r.metrics[k], k) })))))));
  }

  async function refresh() {
    clearTimeout(timer);
    const data = await get("/api/sandbox");
    const current = data.runs.find(r => r.id === (shown || data.running)) || data.runs[0];
    $("sbStatus").replaceChildren(current ? statusCard(current) : el("p", { className: "hint", textContent: "Chưa chạy lần nào. Chọn một câu hỏi hoặc chỉnh tham số rồi bấm Chạy." }));
    $("sbCompare").replaceChildren(compareTable(data.compare));
    $("sbStart").disabled = !!data.running;
    if (data.running) timer = setTimeout(refresh, 1500);
  }

  async function init() {
    opts = await get("/api/sandbox/options");
    const order = ["label", "alt_m", "speed_mps", "pattern", "leg_m", "duration_s", "n_people", "recall_model", "target_person_px", "fps",
      "device", "gps_sigma_m", "yaw_bias_deg", "yaw_calib", "net_loss", "outage_start_s", "outage_len_s", "link_probe", "render", "realtime_speed", "seed"];
    const fields = order.map(k => el("div", { className: "sbfield" + (opts.fields[k].type === "boolean" ? " chk" : "") },
      el("label", { htmlFor: "sb_" + k, textContent: LABELS[k] || k }), input(k, opts.fields[k], opts.defaults[k])));
    page.replaceChildren(
      el("div", { className: "side sbside" },
        el("h3", { textContent: "Câu hỏi \"nếu… thì sao\"" }),
        el("div", { className: "sbpresets" }, ...PRESETS.map(([q, change]) => el("button", { className: "sbchip", textContent: q,
          onclick: () => { fillForm({ ...opts.defaults, ...change }); $("sbMsg").textContent = "Đã chỉnh form theo câu hỏi; bấm Chạy."; } }))),
        el("h3", { textContent: "Tham số" }),
        ...fields,
        el("button", { className: "primary", id: "sbStart", textContent: "Chạy", onclick: start }),
        el("button", { className: "sbchip", textContent: "Về mặc định", onclick: () => fillForm(opts.defaults) }),
        el("p", { className: "hint", id: "sbMsg" }),
        el("p", { className: "hint", textContent: "Mô phỏng: người đặt sẵn, phát hiện giả theo recall theo cỡ người đo của mô hình (E6 thử trên SeaDronesSee), ảnh tổng hợp chỉ để xem. Mỗi lần chạy xoá dữ liệu cũ của trạm mặt đất." })),
      el("div", { className: "sbmain" },
        el("h3", { textContent: "Lần chạy" }), el("div", { id: "sbStatus" }),
        el("h3", { textContent: "So sánh các lần chạy" }),
        el("p", { className: "hint", textContent: "Chỉ hiện tham số khác nhau giữa các lần. Số do eval/rq3_metrics.py tính từ log trong runs/sandbox/<mã>/edge; mô phỏng, một seed mỗi lần: dùng để thấy xu hướng, không thay cho bảng nhiều seed trong docs/results." }),
        el("div", { id: "sbCompare" })));
    refresh();
  }

  document.querySelector('.tab[data-page="sandbox"]').addEventListener("click", () => { if (!opts) init(); else refresh(); });
})();
