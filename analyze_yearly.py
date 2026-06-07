"""Per-year, per-month breakdown: km + records for 1mi, 5k, 10k, HM, M."""
import json
from collections import defaultdict
from datetime import datetime

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import importlib.util
spec = importlib.util.spec_from_file_location("analyze", r"C:\Users\mares\Desktop\garmin\analyze.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
TARGETS = mod.TARGETS
clean_series = mod.clean_series
best_time_for_distance = mod.best_time_for_distance
SANITY_MIN_S = mod.SANITY_MIN_S
fmt_time = mod.fmt_time
RUN_TAGS = {"running", "run", "9", "trail_running", "trail running", "treadmill_running"}

IN = r"C:\Users\mares\Desktop\garmin\activities.json"
OUT_TXT = r"C:\Users\mares\Desktop\garmin\prehled_rocni.txt"

CZ_MONTHS = ["leden","únor","březen","duben","květen","červen",
             "červenec","srpen","září","říjen","listopad","prosinec"]


def main():
    acts = json.load(open(IN, encoding="utf-8"))

    monthly_km = defaultdict(float)              # (year, month) -> km
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
        key = (dt.year, dt.month)
        monthly_km[key] += dist_m / 1000.0
        raw = [(float(t), float(d)) for t, d in (a.get("series") or [])]
        series = clean_series(raw)
        for name, dist in TARGETS:
            bt = best_time_for_distance(series, dist)
            if bt is None or bt < SANITY_MIN_S[name]:
                continue
            cur = monthly_best[key][name]
            if cur is None or bt < cur:
                monthly_best[key][name] = bt

    years = sorted({k[0] for k in monthly_km.keys()})
    lines = []
    lines.append("PŘEHLED BĚHU PO ROCÍCH A MĚSÍCÍCH")
    lines.append("=" * 96)

    for y in years:
        lines.append("")
        lines.append(f"# {y}")
        lines.append("-" * 96)
        lines.append(f"{'Měsíc':<11} {'Km':>7}  {'1 míle':>8} {'5 km':>8} {'10 km':>8} {'Půlmar.':>10} {'Maraton':>10}")
        lines.append("-" * 96)
        year_total = 0.0
        for m in range(1, 13):
            key = (y, m)
            km = monthly_km.get(key, 0.0)
            year_total += km
            b = monthly_best.get(key, {n: None for n, _ in TARGETS})
            month_label = f"{CZ_MONTHS[m-1]:<10}"
            if km == 0:
                lines.append(f"{month_label}  {'-':>7}  {'-':>8} {'-':>8} {'-':>8} {'-':>10} {'-':>10}")
            else:
                lines.append(
                    f"{month_label}  {km:>7.1f}  "
                    f"{fmt_time(b['1 míle (1609m)']):>8} "
                    f"{fmt_time(b['5 km']):>8} "
                    f"{fmt_time(b['10 km']):>8} "
                    f"{fmt_time(b['Půlmaraton 21.1km']):>10} "
                    f"{fmt_time(b['Maraton 42.2km']):>10}"
                )
        lines.append("-" * 96)
        lines.append(f"{'CELKEM ' + str(y):<11} {year_total:>7.1f} km")

    out = "\n".join(lines)
    print(out)
    open(OUT_TXT, "w", encoding="utf-8").write(out)


if __name__ == "__main__":
    main()
