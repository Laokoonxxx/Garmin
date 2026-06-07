"""2026 only — transposed: columns = months (leden..červen), rows = metrics."""
import json
import importlib.util
import sys
from collections import defaultdict
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

spec = importlib.util.spec_from_file_location("analyze", r"C:\Users\mares\Desktop\garmin\analyze.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
TARGETS = mod.TARGETS
clean_series = mod.clean_series
best_time_for_distance = mod.best_time_for_distance
SANITY_MIN_S = mod.SANITY_MIN_S
fmt_time = mod.fmt_time

RUN_TAGS = {"running", "run", "9", "trail_running", "trail running", "treadmill_running"}
IN = r"C:\Users\mares\Desktop\garmin\activities.json"
OUT_TXT = r"C:\Users\mares\Desktop\garmin\prehled_2026.txt"

YEAR = 2026
CZ_MONTHS = ["leden","únor","březen","duben","květen","červen",
             "červenec","srpen","září","říjen","listopad","prosinec"]


def main():
    acts = json.load(open(IN, encoding="utf-8"))
    monthly_km = defaultdict(float)
    monthly_best = defaultdict(lambda: {n: None for n, _ in TARGETS})

    for a in acts:
        sport = (a.get("sport") or "").strip().lower()
        if sport not in RUN_TAGS:
            continue
        dist_m = a["dist_m"]; moving_s = a["moving_s"] or 0
        if dist_m > 2000 and moving_s > 300:
            pace = (moving_s/60.0) / (dist_m/1000.0)
            if pace < 4.5 or pace > 10.0:
                continue
        dt = datetime.fromisoformat(a["start"])
        if dt.year != YEAR:
            continue
        m = dt.month
        monthly_km[m] += dist_m / 1000.0
        raw = [(float(t), float(d)) for t, d in (a.get("series") or [])]
        series = clean_series(raw)
        for name, dist in TARGETS:
            bt = best_time_for_distance(series, dist)
            if bt is None or bt < SANITY_MIN_S[name]:
                continue
            cur = monthly_best[m][name]
            if cur is None or bt < cur:
                monthly_best[m][name] = bt

    months_to_show = list(range(1, 7))  # leden..červen

    def row(label, cells):
        return f"{label:<12} " + " ".join(f"{c:>10}" for c in cells)

    lines = []
    lines.append(f"PŘEHLED BĚHU {YEAR} — měsíce ve sloupcích")
    lines.append("=" * (12 + 1 + 11 * len(months_to_show)))
    header = [CZ_MONTHS[m-1] for m in months_to_show]
    lines.append(row("", header))
    lines.append("-" * (12 + 1 + 11 * len(months_to_show)))

    # Km row
    km_cells = [f"{monthly_km.get(m, 0.0):.1f}" if monthly_km.get(m, 0.0) else "-" for m in months_to_show]
    lines.append(row("Km", km_cells))

    # Records rows
    label_map = {
        "1 míle (1609m)":     "1 míle",
        "5 km":               "5 km",
        "10 km":              "10 km",
        "Půlmaraton 21.1km":  "Půlmaraton",
        "Maraton 42.2km":     "Maraton",
    }
    for name, _ in TARGETS:
        cells = [fmt_time(monthly_best.get(m, {}).get(name)) for m in months_to_show]
        lines.append(row(label_map[name], cells))

    lines.append("-" * (12 + 1 + 11 * len(months_to_show)))
    total_km = sum(monthly_km.get(m, 0.0) for m in months_to_show)
    lines.append(f"CELKEM {YEAR} (leden-červen): {total_km:.1f} km")

    out = "\n".join(lines)
    print(out)
    open(OUT_TXT, "w", encoding="utf-8").write(out)


if __name__ == "__main__":
    main()
