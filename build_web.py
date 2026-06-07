"""Build a self-contained HTML page with per-year run heatmaps and a live
settings panel (colors, thresholds, grid columns)."""
import json
import sys
from collections import defaultdict
from datetime import datetime

from filters import is_valid_running

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

IN = r"C:\Users\mares\Desktop\garmin\activities.json"
OUT_HTML = r"C:\Users\mares\Desktop\garmin\plan_web.html"
RUN_TAGS = {"running", "run", "9", "trail_running", "trail running", "treadmill_running"}


def main():
    acts = json.load(open(IN, encoding="utf-8"))
    by_year = defaultdict(list)
    for a in acts:
        sport = (a.get("sport") or "").strip().lower()
        if sport not in RUN_TAGS:
            continue
        dist_m = a["dist_m"]; moving_s = a["moving_s"] or 0
        if not is_valid_running(dist_m, moving_s):
            continue
        dt = datetime.fromisoformat(a["start"])
        d_km = dist_m / 1000.0
        if d_km < 0.5:
            continue
        pace_s = (moving_s / d_km) if (moving_s and d_km > 0) else 0
        if pace_s <= 0:
            continue
        by_year[dt.year].append({
            "date": dt.strftime("%Y-%m-%d"),
            "km": round(d_km, 3),
            "pace_s": round(pace_s, 1),
        })

    years_data = []
    for y in sorted(by_year.keys()):
        runs = sorted(by_year[y], key=lambda r: r["date"])
        total = sum(r["km"] for r in runs)
        if total < 1:
            continue
        years_data.append({"year": y, "total_km": round(total, 2), "runs": runs})

    data_json = json.dumps(years_data, ensure_ascii=False)

    html = HTML_TEMPLATE.replace("__DATA__", data_json)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {OUT_HTML} with {len(years_data)} years")
    for y in years_data:
        print(f"  {y['year']}: {len(y['runs'])} runs, {y['total_km']} km")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<title>Můj běžecký plán — heatmap</title>
<style>
  :root { font-family: system-ui, -apple-system, sans-serif; }
  body { margin: 0; background: #f5f5f5; color: #222; }
  header { background: #1e293b; color: #fff; padding: 16px 20px; }
  header h1 { margin: 0; font-size: 18px; font-weight: 600; }
  header .sub { font-size: 13px; opacity: .7; margin-top: 2px; }
  main { padding: 16px 20px 40px; max-width: 1700px; margin: 0 auto; }
  .settings {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    padding: 14px 16px; margin-bottom: 20px;
  }
  .settings h2 { margin: 0 0 10px; font-size: 14px; color: #475569; text-transform: uppercase; letter-spacing: .04em; }
  .tiers { display: grid; grid-template-columns: 70px 110px 1fr 32px; gap: 6px 10px; align-items: center; font-size: 13px; }
  .tiers .head { font-weight: 600; color: #64748b; font-size: 11px; text-transform: uppercase; }
  .tiers input[type="color"] { width: 60px; height: 28px; padding: 0; border: 1px solid #cbd5e1; border-radius: 4px; cursor: pointer; }
  .tiers input[type="text"] { width: 100%; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px; font-family: monospace; box-sizing: border-box; }
  .tiers .catch-all { font-style: italic; color: #94a3b8; font-family: monospace; font-size: 12px; padding-left: 6px; }
  .tiers .del-btn { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; border-radius: 4px; cursor: pointer; padding: 0; height: 28px; font-size: 14px; line-height: 1; }
  .tiers .del-btn:hover { background: #fecaca; }
  .tiers .del-btn:disabled { background: #f1f5f9; color: #cbd5e1; border-color: #e2e8f0; cursor: not-allowed; }
  .add-btn { margin-top: 8px; background: #ecfeff; color: #155e75; border: 1px dashed #67e8f9; padding: 6px 12px; border-radius: 4px; font-size: 13px; cursor: pointer; }
  .add-btn:hover { background: #cffafe; }
  .actions { margin-top: 12px; display: flex; gap: 10px; align-items: center; }
  .actions button { background: #1e293b; color: #fff; border: 0; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; }
  .actions button:hover { background: #334155; }
  .actions .grid-opt { font-size: 13px; color: #475569; }
  .actions .grid-opt input { width: 70px; padding: 4px 6px; border: 1px solid #cbd5e1; border-radius: 4px; font-family: monospace; }
  .year-block { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 18px; }
  .year-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
  .year-head h3 { margin: 0; font-size: 18px; }
  .year-head .stats { font-size: 13px; color: #64748b; }
  .grid { display: grid; gap: 1px; background: #eee; padding: 1px; border-radius: 2px; }
  .cell {
    background: #fff; aspect-ratio: 1 / 1; min-width: 14px;
    font-size: 9px; color: rgba(0,0,0,.35); text-align: center;
    line-height: 1; display: flex; align-items: center; justify-content: center;
    box-sizing: border-box; cursor: default; position: relative;
  }
  .cell.colored { color: #fff; font-weight: 600; text-shadow: 0 1px 1px rgba(0,0,0,.35); }
  .cell.end-r { box-shadow: inset -2px 0 0 #000; }
  .cell.end-b { box-shadow: inset 0 -2px 0 #000; }
  .cell.end-r.end-b { box-shadow: inset -2px 0 0 #000, inset 0 -2px 0 #000; }
  .tier-summary { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 10px; font-size: 12px; color: #475569; }
  .tier-summary .swatch { display: inline-block; width: 12px; height: 12px; border: 1px solid #ccc; vertical-align: middle; margin-right: 4px; }
  .overview { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 20px; }
  .overview h2 { margin: 0 0 10px; font-size: 14px; color: #475569; text-transform: uppercase; letter-spacing: .04em; }
  .overview table { border-collapse: collapse; font-size: 13px; width: 100%; }
  .overview th, .overview td { padding: 5px 8px; border-bottom: 1px solid #f1f5f9; text-align: right; }
  .overview th { background: #f8fafc; color: #334155; font-weight: 600; font-size: 12px; white-space: nowrap; }
  .overview th:first-child, .overview td:first-child { text-align: left; }
  .overview .swatch { display: inline-block; width: 10px; height: 10px; border: 1px solid #ccc; vertical-align: middle; margin-right: 4px; border-radius: 2px; }
  .overview tr.total { font-weight: 600; background: #f8fafc; }
  .overview tr.total td { border-top: 2px solid #cbd5e1; }
  .overview td.range { color: #94a3b8; font-size: 11px; font-weight: 400; text-align: right; }
  #tip {
    position: fixed; display: none; pointer-events: none; z-index: 99;
    background: #1e293b; color: #fff; padding: 6px 8px; border-radius: 4px;
    font-size: 12px; font-family: monospace; white-space: nowrap;
    box-shadow: 0 4px 10px rgba(0,0,0,.2);
  }

  /* ----- Print layout: A4 landscape, one year per page, only year + grid ----- */
  @media print {
    @page {
      size: A4 landscape;
      margin: 10mm 8mm 8mm 8mm;
    }
    html, body { background: #fff !important; margin: 0; padding: 0; color: #000; }
    /* Hide everything not part of the heatmap output */
    header,
    .settings,
    #overview,
    #tip,
    .actions,
    button,
    .add-btn {
      display: none !important;
    }
    /* Per-year tier summary kept for print, styled compactly */
    .tier-summary {
      margin-top: 4mm !important;
      gap: 2mm 6mm !important;
      font-size: 9pt !important;
      color: #000 !important;
      page-break-inside: avoid;
      break-inside: avoid;
    }
    .tier-summary .swatch {
      width: 10pt !important;
      height: 10pt !important;
      border: 0.5pt solid #000 !important;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
      color-adjust: exact !important;
    }
    .tier-summary span { white-space: nowrap; }
    main { padding: 0; max-width: none; margin: 0; }
    /* Each year on its own page */
    .year-block {
      page-break-before: always;
      break-before: page;
      page-break-inside: avoid;
      break-inside: avoid;
      background: #fff !important;
      border: none !important;
      box-shadow: none !important;
      padding: 0 !important;
      margin: 0 !important;
    }
    .year-block:first-of-type {
      page-break-before: avoid;
      break-before: auto;
    }
    .year-head {
      margin: 0 0 4mm 0;
      padding: 0 0 2mm 0;
      border-bottom: 1px solid #000;
      display: block;
    }
    .year-head h3 {
      font-size: 22pt; font-weight: 700; margin: 0;
    }
    .year-head .stats {
      font-size: 10pt; color: #444; margin-top: 1mm;
    }
    /* Grid: force colored cells to print, drop visual UI artefacts */
    .grid {
      gap: 0.5pt;
      padding: 0;
      background: transparent;
      border: 0;
      width: 100%;
    }
    .cell {
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
      color-adjust: exact !important;
      font-size: 4pt;
      min-width: 0;
      text-shadow: none !important;
    }
    .cell:not(.colored) {
      background: #fff !important;
      color: #999 !important;
    }
    /* End-of-run marker as real border so it prints reliably */
    .cell.end-r { box-shadow: none !important; border-right: 1.4pt solid #000 !important; }
    .cell.end-b { box-shadow: none !important; border-bottom: 1.4pt solid #000 !important; }
    .cell.end-r.end-b {
      border-right: 1.4pt solid #000 !important;
      border-bottom: 1.4pt solid #000 !important;
    }
  }
</style>
</head>
<body>
<header>
  <h1>Můj běžecký plán — heatmap</h1>
  <div class="sub">Každá buňka = 1 km. Každý běh = jeden barevný blok. Tlustá černá čára = konec běhu.</div>
</header>
<main>

<section class="settings">
  <h2>Nastavení barev a hranic (min/km)</h2>
  <div class="tiers" id="tiers">
    <div class="head">Barva</div>
    <div class="head">Hranice (min/km)</div>
    <div class="head">Popisek</div>
    <div class="head"></div>
  </div>
  <button id="add-tier" class="add-btn">+ Přidat kategorii</button>
  <div class="actions">
    <span class="grid-opt">Paleta: <select id="palette"></select></span>
    <span class="grid-opt">Sloupců v mřížce: <input type="number" id="cols" value="50" min="10" max="200" step="1"></span>
    <span class="grid-opt">Cílové km: <input type="number" id="goal" value="1000" min="100" max="5000" step="50"></span>
    <button id="reset">Reset</button>
  </div>
</section>

<section class="overview" id="overview">
  <h2>Souhrn — km podle kategorie a roku</h2>
  <div id="overview-body"></div>
</section>

<div id="years"></div>
<div id="tip"></div>

<script>
const DATA = __DATA__;

// Default tiers — slow -> fast
// 8-color palettes (slowest -> fastest). User can switch with the dropdown.
const PALETTES = {
  "Tlumená (default)":  ["#B7DDA8","#5BA66D","#E9C645","#E58B3D","#CF4A3A","#4A8FCC","#8B5BBF","#D85AA0"],
  "Pastelová":          ["#C8E6BA","#8FCB80","#F5E2A1","#F2BC81","#E18983","#86AED6","#B697D3","#E9A5C7"],
  "Spektrum":           ["#5E4FA2","#3288BD","#66C2A5","#ABDDA4","#FEE08B","#FDAE61","#F46D43","#D53E4F"],
  "Viridis":            ["#440154","#414487","#2A788E","#22A884","#7AD151","#FDE725","#FCA50A","#DC3977"],
  "Plazma":             ["#0D0887","#5C01A6","#9C179E","#CC4778","#ED7953","#FB9F3A","#FDCA26","#F0F921"],
  "Sunset":             ["#003F5C","#374C80","#7A5195","#BC5090","#EF5675","#FF764A","#FFA600","#FFD63A"],
  "Země":               ["#4F5D45","#6F8B5F","#A8B68C","#D6CC92","#D69E5B","#B85C39","#8A2F2A","#4E1A2E"],
  "Pevné (živé)":       ["#B5E61D","#2E8B2E","#FFD700","#FF8C00","#E81416","#2E70F0","#8A2BE2","#FF69B4"],
};
const DEFAULT_PALETTE_NAME = "Tlumená (default)";

// Tiers ordered slow → fast (top to bottom).
// Each tier has ONE field: `boundary` = the FASTER edge of this tier in "m:ss".
// A pace belongs to this tier when pace >= boundary (and is not claimed by a slower tier above).
// The LAST tier (fastest) has boundary = "" → catch-all, matches whatever no earlier tier did.
// This guarantees every pace falls into exactly one category.
const DEFAULT_TIERS = [
  {name: "světle zelená", boundary: "6:30", color: ""},
  {name: "zelená",        boundary: "6:00", color: ""},
  {name: "žlutá",         boundary: "5:45", color: ""},
  {name: "oranžová",      boundary: "5:30", color: ""},
  {name: "červená",       boundary: "5:20", color: ""},
  {name: "modrá",         boundary: "5:10", color: ""},
  {name: "fialová",       boundary: "5:00", color: ""},
  {name: "růžová",        boundary: "",     color: ""},
];
// Apply the default palette to the default tiers
PALETTES[DEFAULT_PALETTE_NAME].forEach((c, i) => { if (DEFAULT_TIERS[i]) DEFAULT_TIERS[i].color = c; });

function paceStrToSec(s) {
  if (!s || s === "—" || s === "-") return null;
  const m = String(s).trim().match(/^(\d+):(\d{1,2})$/);
  if (!m) return null;
  return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
}
function secToPaceStr(sec) {
  if (sec == null) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.round(sec - m * 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

let tiers = JSON.parse(JSON.stringify(DEFAULT_TIERS));

function tierForPace(paceSec) {
  // Walk tiers slow→fast (top→bottom). For each tier with a boundary,
  // return it if paceSec >= boundary. Anything not matched falls to the LAST tier.
  for (let i = 0; i < tiers.length - 1; i++) {
    const b = paceStrToSec(tiers[i].boundary);
    if (b == null) continue;
    if (paceSec >= b) return tiers[i];
  }
  return tiers[tiers.length - 1]; // catch-all (fastest)
}

function renderTierSettings() {
  const root = document.getElementById("tiers");
  // wipe except headers (first 4 nodes)
  while (root.children.length > 4) root.removeChild(root.lastChild);
  tiers.forEach((t, i) => {
    const isLast = (i === tiers.length - 1);

    const c = document.createElement("input");
    c.type = "color"; c.value = t.color || "#cccccc";
    c.addEventListener("input", e => { tiers[i].color = e.target.value; renderAll(); });
    root.appendChild(c);

    if (isLast) {
      const span = document.createElement("div");
      span.className = "catch-all";
      span.textContent = "vše rychlejší";
      root.appendChild(span);
    } else {
      const b = document.createElement("input");
      b.type = "text"; b.value = t.boundary; b.placeholder = "m:ss";
      b.addEventListener("change", e => {
        tiers[i].boundary = e.target.value.trim();
        renderAll();
      });
      root.appendChild(b);
    }

    const lbl = document.createElement("input");
    lbl.type = "text"; lbl.value = t.name;
    lbl.addEventListener("change", e => { tiers[i].name = e.target.value; renderAll(); });
    root.appendChild(lbl);

    const del = document.createElement("button");
    del.className = "del-btn"; del.textContent = "×"; del.title = "Smazat kategorii";
    if (tiers.length <= 2) del.disabled = true;
    del.addEventListener("click", () => {
      if (tiers.length <= 2) return;
      tiers.splice(i, 1);
      renderTierSettings(); renderAll();
    });
    root.appendChild(del);
  });
}

function addTier() {
  // Insert a new tier just BEFORE the catch-all (so catch-all stays last).
  // Default boundary: midpoint between previous tier's boundary and the catch-all's
  // (which has none) — fall back to "5:00" if uncertain.
  const lastBounded = tiers.length >= 2 ? paceStrToSec(tiers[tiers.length - 2].boundary) : null;
  let newBoundary = "5:00";
  if (lastBounded != null) {
    const cand = Math.max(60, lastBounded - 15);
    const m = Math.floor(cand / 60), s = cand % 60;
    newBoundary = `${m}:${s.toString().padStart(2, "0")}`;
  }
  const insertAt = tiers.length - 1;
  tiers.splice(insertAt, 0, {
    name: "nová",
    boundary: newBoundary,
    color: "#9ca3af",
  });
  renderTierSettings(); renderAll();
}

function buildPaintForYear(year) {
  // Allocate cells with cumulative rounding (same as Python script).
  const cells = [];
  let cumKm = 0, cumCells = 0;
  for (const r of year.runs) {
    cumKm += r.km;
    const newCum = Math.round(cumKm);
    const n = newCum - cumCells;
    cumCells = newCum;
    if (n <= 0) continue;
    const tier = tierForPace(r.pace_s);
    const tip = `${r.date}  ${r.km.toFixed(2)} km  ${secToPaceStr(r.pace_s)}/km`;
    for (let k = 0; k < n; k++) {
      cells.push({color: tier.color, tip, last: k === n - 1, tierName: tier.name});
    }
  }
  return cells;
}

function renderYear(year, cols, goalKm, outTierCounts) {
  const cells = buildPaintForYear(year);
  const totalCells = Math.max(goalKm, Math.ceil(cells.length / cols) * cols);

  const block = document.createElement("section");
  block.className = "year-block";

  const head = document.createElement("div");
  head.className = "year-head";
  head.innerHTML = `<h3>${year.year}</h3>
    <div class="stats">${year.runs.length} běhů · ${cells.length} km
      ${goalKm > 0 ? `· ${(cells.length/goalKm*100).toFixed(1)}% z ${goalKm} km` : ""}</div>`;
  block.appendChild(head);

  const grid = document.createElement("div");
  grid.className = "grid";
  grid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;

  // Count tiers
  const tierCounts = {};
  tiers.forEach(t => tierCounts[t.name] = 0);

  for (let i = 0; i < totalCells; i++) {
    const div = document.createElement("div");
    div.className = "cell";
    div.textContent = i + 1;
    if (i < cells.length) {
      const c = cells[i];
      div.classList.add("colored");
      div.style.background = c.color;
      div.dataset.tip = c.tip;
      tierCounts[c.tierName] = (tierCounts[c.tierName] || 0) + 1;
      const col = i % cols;
      if (c.last && i !== cells.length - 1) {
        if (col < cols - 1) div.classList.add("end-r");
        else div.classList.add("end-b");
      }
    }
    grid.appendChild(div);
  }
  block.appendChild(grid);

  // tier summary
  const sum = document.createElement("div");
  sum.className = "tier-summary";
  tiers.forEach((t, idx) => {
    const n = tierCounts[t.name] || 0;
    if (n === 0) return;
    const isLast = (idx === tiers.length - 1);
    let rangeLabel;
    if (isLast) {
      const prev = idx > 0 ? tiers[idx - 1].boundary : null;
      rangeLabel = prev ? `< ${prev}` : "vše";
    } else if (idx === 0) {
      rangeLabel = `≥ ${t.boundary}`;
    } else {
      rangeLabel = `${t.boundary}–${tiers[idx - 1].boundary}`;
    }
    const sp = document.createElement("span");
    sp.innerHTML = `<span class="swatch" style="background:${t.color}"></span>${t.name} (${rangeLabel}): <strong>${n} km</strong>`;
    sum.appendChild(sp);
  });
  if (totalCells > cells.length) {
    const sp = document.createElement("span");
    sp.innerHTML = `<span class="swatch" style="background:#fff"></span>prázdné: <strong>${totalCells - cells.length}</strong>`;
    sum.appendChild(sp);
  }
  block.appendChild(sum);

  if (outTierCounts) outTierCounts[year.year] = tierCounts;
  return block;
}

function tierRangeLabel(idx) {
  const t = tiers[idx];
  const isLast = (idx === tiers.length - 1);
  if (isLast) {
    const prev = idx > 0 ? tiers[idx - 1].boundary : "";
    return prev ? `< ${prev}` : "vše";
  }
  if (idx === 0) return `≥ ${t.boundary}`;
  return `${t.boundary}–${tiers[idx - 1].boundary}`;
}

function renderOverview(tierCountsByYear) {
  const root = document.getElementById("overview-body");
  root.innerHTML = "";

  const table = document.createElement("table");
  // Header row 1: category names with color swatch
  const thead = document.createElement("thead");
  const trH1 = document.createElement("tr");
  trH1.appendChild(Object.assign(document.createElement("th"), {textContent: "Rok"}));
  tiers.forEach(t => {
    const th = document.createElement("th");
    th.innerHTML = `<span class="swatch" style="background:${t.color}"></span>${t.name}`;
    trH1.appendChild(th);
  });
  trH1.appendChild(Object.assign(document.createElement("th"), {textContent: "Celkem"}));
  thead.appendChild(trH1);
  // Header row 2: ranges
  const trH2 = document.createElement("tr");
  trH2.appendChild(Object.assign(document.createElement("td"), {className: "range", textContent: ""}));
  tiers.forEach((t, idx) => {
    const td = document.createElement("td");
    td.className = "range";
    td.textContent = tierRangeLabel(idx);
    trH2.appendChild(td);
  });
  trH2.appendChild(Object.assign(document.createElement("td"), {className: "range", textContent: ""}));
  thead.appendChild(trH2);
  table.appendChild(thead);

  // Body rows: one per year, sorted ascending
  const tbody = document.createElement("tbody");
  const years = Object.keys(tierCountsByYear).map(y => parseInt(y, 10)).sort((a, b) => a - b);
  const tierTotals = tiers.map(() => 0);
  let grandTotal = 0;
  for (const y of years) {
    const counts = tierCountsByYear[y];
    const tr = document.createElement("tr");
    tr.appendChild(Object.assign(document.createElement("td"), {textContent: y}));
    let row_total = 0;
    tiers.forEach((t, i) => {
      const n = counts[t.name] || 0;
      tierTotals[i] += n;
      row_total += n;
      const td = document.createElement("td");
      td.textContent = n ? n : "—";
      if (n) td.style.color = "#0f172a";
      else td.style.color = "#cbd5e1";
      tr.appendChild(td);
    });
    grandTotal += row_total;
    const tdTot = document.createElement("td");
    tdTot.textContent = row_total;
    tdTot.style.fontWeight = "600";
    tr.appendChild(tdTot);
    tbody.appendChild(tr);
  }

  // Total row
  const trT = document.createElement("tr");
  trT.className = "total";
  trT.appendChild(Object.assign(document.createElement("td"), {textContent: "Celkem"}));
  tierTotals.forEach(n => {
    const td = document.createElement("td");
    td.textContent = n || "—";
    if (!n) td.style.color = "#cbd5e1";
    trT.appendChild(td);
  });
  trT.appendChild(Object.assign(document.createElement("td"), {textContent: grandTotal}));
  tbody.appendChild(trT);

  // Percent row
  const trP = document.createElement("tr");
  trP.appendChild(Object.assign(document.createElement("td"),
    {textContent: "% z celku", style: "color:#94a3b8;font-size:11px;"}));
  tierTotals.forEach(n => {
    const td = document.createElement("td");
    const pct = grandTotal ? (100 * n / grandTotal) : 0;
    td.textContent = grandTotal && n ? pct.toFixed(1) + " %" : "—";
    td.style.color = "#94a3b8";
    td.style.fontSize = "11px";
    trP.appendChild(td);
  });
  trP.appendChild(Object.assign(document.createElement("td"), {textContent: "100 %",
    style: "color:#94a3b8;font-size:11px;"}));
  tbody.appendChild(trP);

  table.appendChild(tbody);
  root.appendChild(table);
}

function renderAll() {
  const cols = parseInt(document.getElementById("cols").value, 10) || 50;
  const goal = parseInt(document.getElementById("goal").value, 10) || 1000;
  const root = document.getElementById("years");
  root.innerHTML = "";
  const counts = {};
  for (const y of DATA) root.appendChild(renderYear(y, cols, goal, counts));
  renderOverview(counts);
}

// Tooltip handling (event delegation)
const tip = document.getElementById("tip");
document.addEventListener("mousemove", e => {
  const c = e.target.closest && e.target.closest(".cell");
  if (c && c.dataset.tip) {
    tip.textContent = c.dataset.tip;
    tip.style.display = "block";
    tip.style.left = (e.clientX + 14) + "px";
    tip.style.top  = (e.clientY + 14) + "px";
  } else {
    tip.style.display = "none";
  }
});

document.getElementById("cols").addEventListener("input", renderAll);
document.getElementById("goal").addEventListener("input", renderAll);

// Build palette dropdown
const palSel = document.getElementById("palette");
Object.keys(PALETTES).forEach(name => {
  const opt = document.createElement("option");
  opt.value = name; opt.textContent = name;
  if (name === DEFAULT_PALETTE_NAME) opt.selected = true;
  palSel.appendChild(opt);
});
palSel.addEventListener("change", e => {
  const colors = PALETTES[e.target.value];
  if (!colors) return;
  tiers.forEach((t, i) => { t.color = colors[i % colors.length]; });
  renderTierSettings(); renderAll();
});

document.getElementById("add-tier").addEventListener("click", addTier);

document.getElementById("reset").addEventListener("click", () => {
  tiers = JSON.parse(JSON.stringify(DEFAULT_TIERS));
  document.getElementById("cols").value = 50;
  document.getElementById("goal").value = 1000;
  document.getElementById("palette").value = DEFAULT_PALETTE_NAME;
  renderTierSettings(); renderAll();
});

renderTierSettings();
renderAll();
</script>
</main>
</body>
</html>
"""


if __name__ == "__main__":
    main()
