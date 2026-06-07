"""Analyze parsed activities:
- Monthly total running distance.
- Best moving-time record per month over 1 mile, 5km, 10km, 21.0975km, 42.195km.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone

IN = r"C:\Users\mares\Desktop\garmin\activities.json"
OUT_TXT = r"C:\Users\mares\Desktop\garmin\prehled.txt"

TARGETS = [
    ("1 míle (1609m)", 1609.34),
    ("5 km",            5000.0),
    ("10 km",          10000.0),
    ("Půlmaraton 21.1km", 21097.5),
    ("Maraton 42.2km",  42195.0),
]


PAUSE_GAP_S = 30.0     # leg time gap above this = pause, skip leg time
MAX_SPEED_MPS = 7.0    # leg avg speed above this = GPS glitch, skip the leg distance too


def clean_series(raw):
    """raw: list of (abs_timestamp_s, cum_dist_m). Returns cleaned cumulative
    (moving_time_s, cum_dist_m) series — pauses excluded from time, GPS-glitch
    legs excluded from both time and distance.
    """
    if not raw:
        return []
    out = [(0.0, 0.0)]
    cum_t = 0.0
    cum_d = 0.0
    for i in range(1, len(raw)):
        dt = raw[i][0] - raw[i-1][0]
        dd = raw[i][1] - raw[i-1][1]
        if dt <= 0 or dd < 0:
            continue
        # Pause: keep distance contribution at zero (you weren't moving)
        if dt > PAUSE_GAP_S:
            continue
        if dd > 0 and (dd / dt) > MAX_SPEED_MPS:
            # GPS glitch: skip leg entirely
            continue
        cum_t += dt
        cum_d += dd
        out.append((cum_t, cum_d))
    return out


def best_time_for_distance(series, target_m):
    """series: cleaned (moving_time_s, cum_dist_m). Best rolling target_m window."""
    n = len(series)
    if n < 2:
        return None
    if series[-1][1] - series[0][1] < target_m:
        return None
    j = 0
    best = None
    for i in range(n):
        if j < i + 1:
            j = i + 1
        while j < n and (series[j][1] - series[i][1]) < target_m:
            j += 1
        if j >= n:
            break
        t_prev, d_prev = series[j-1]
        t_next, d_next = series[j]
        d_at_i = series[i][1]
        want = d_at_i + target_m
        if d_next <= d_prev:
            t_target = t_next
        else:
            frac = (want - d_prev) / (d_next - d_prev)
            frac = max(0.0, min(1.0, frac))
            t_target = t_prev + frac * (t_next - t_prev)
        dt = t_target - series[i][0]
        if dt > 0 and (best is None or dt < best):
            best = dt
    return best


# World-record-ish sanity caps (anything faster is rejected as a glitch)
SANITY_MIN_S = {
    "1 míle (1609m)":        14*60 + 30,   # WR is 3:43, but for amateur even 4:30 mile is elite; cap at WR-ish for safety
    "5 km":                  12*60 + 30,
    "10 km":                 26*60 + 0,
    "Půlmaraton 21.1km":     57*60 + 0,
    "Maraton 42.2km":      2*60*60 + 0,
}
# Make caps consistent: minimum plausible time per distance (in seconds)
SANITY_MIN_S["1 míle (1609m)"]      = 3*60 + 40    # WR 3:43
SANITY_MIN_S["5 km"]                = 12*60 + 30
SANITY_MIN_S["10 km"]               = 26*60 + 0
SANITY_MIN_S["Půlmaraton 21.1km"]   = 57*60 + 0
SANITY_MIN_S["Maraton 42.2km"]      = 2*60*60 + 0


def fmt_time(s):
    if s is None:
        return "-"
    s = round(s)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"


def main():
    with open(IN, "r", encoding="utf-8") as f:
        acts = json.load(f)
    print(f"Activities loaded: {len(acts)}")

    # sport stats
    sport_counts = defaultdict(int)
    for a in acts:
        sport_counts[a.get("sport") or "?"] += 1
    print("Sport counts:", dict(sport_counts))

    # Running sports — Strava GPX uses <type>9</type> = run, but actually it varies.
    # GPX type field in Strava export is the activity type number. Let's look.
    # Better: include records where sport matches running OR src is gpx and contains run hints.
    # We'll classify by sport string; FIT uses 'running'.
    # For GPX with numeric type: '9' is Run in Strava (per docs). '1' = ride, etc.
    RUN_TAGS = {"running", "run", "9", "trail_running", "trail running", "treadmill_running"}

    monthly_km = defaultdict(float)
    monthly_best = defaultdict(lambda: {name: None for name, _ in TARGETS})
    monthly_best_src = defaultdict(lambda: {name: None for name, _ in TARGETS})

    skipped_nonrun_pace = 0
    for a in acts:
        sport = (a.get("sport") or "").strip().lower()
        if sport not in RUN_TAGS:
            continue
        # Reject activities whose avg moving pace is impossibly fast for running
        # (these are cycling activities mis-tagged as 'running' in the source data).
        dist_m = a["dist_m"]
        moving_s = a["moving_s"] or 0
        if dist_m > 2000 and moving_s > 300:
            pace_min_per_km = (moving_s / 60.0) / (dist_m / 1000.0)
            if pace_min_per_km < 4.5:
                skipped_nonrun_pace += 1
                continue
            if pace_min_per_km > 10.0:
                # slower than ~6 km/h average → hike / walk, not running
                skipped_nonrun_pace += 1
                continue
        start = datetime.fromisoformat(a["start"])
        ym = start.strftime("%Y-%m")
        dist_km = a["dist_m"] / 1000.0
        monthly_km[ym] += dist_km

        raw_series = a.get("series") or []
        raw_series = [(float(t), float(d)) for t, d in raw_series]
        series = clean_series(raw_series)
        for name, dist in TARGETS:
            bt = best_time_for_distance(series, dist)
            if bt is None:
                continue
            if bt < SANITY_MIN_S[name]:
                continue
            cur = monthly_best[ym][name]
            if cur is None or bt < cur:
                monthly_best[ym][name] = bt
                monthly_best_src[ym][name] = a["src"]

    months = sorted(monthly_km.keys())
    print(f"Months with running: {len(months)}, skipped (suspected cycling): {skipped_nonrun_pace}")

    lines = []
    lines.append("PŘEHLED BĚHU - měsíční nájezd a osobní rekordy")
    lines.append("=" * 100)
    header = f"{'Měsíc':<10} {'Km':>8}  {'1 míle':>8} {'5 km':>8} {'10 km':>8} {'Půlmar.':>10} {'Maraton':>10}"
    lines.append(header)
    lines.append("-" * 100)
    total_km = 0.0
    yearly_km = defaultdict(float)
    for ym in months:
        km = monthly_km[ym]
        total_km += km
        yearly_km[ym[:4]] += km
        b = monthly_best[ym]
        row = (
            f"{ym:<10} "
            f"{km:>8.1f}  "
            f"{fmt_time(b['1 míle (1609m)']):>8} "
            f"{fmt_time(b['5 km']):>8} "
            f"{fmt_time(b['10 km']):>8} "
            f"{fmt_time(b['Půlmaraton 21.1km']):>10} "
            f"{fmt_time(b['Maraton 42.2km']):>10}"
        )
        lines.append(row)
    lines.append("-" * 100)
    lines.append(f"CELKEM: {total_km:.1f} km")
    lines.append("")
    lines.append("Roční součty:")
    for y in sorted(yearly_km):
        lines.append(f"  {y}: {yearly_km[y]:.1f} km")

    # Overall PRs
    lines.append("")
    lines.append("Absolutní rekordy:")
    for name, dist in TARGETS:
        best = None; best_ym = None; best_src = None
        for ym in months:
            t = monthly_best[ym][name]
            if t is not None and (best is None or t < best):
                best = t; best_ym = ym; best_src = monthly_best_src[ym][name]
        lines.append(f"  {name:<22} {fmt_time(best):>10}   ({best_ym}, {best_src})")

    out = "\n".join(lines)
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(out)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(out)


if __name__ == "__main__":
    main()
