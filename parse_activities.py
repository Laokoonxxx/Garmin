"""Parse all Strava activity files: GPX, FIT, FIT.GZ.
Extract: date, sport, total distance, total moving time, trackpoints (t, cum_dist).
Output: JSON file with one record per activity.
"""
import os
import gzip
import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import fitparse

ACT_DIR = r"C:\Users\mares\Desktop\garmin\extracted\activities"
OUT = r"C:\Users\mares\Desktop\garmin\activities.json"

NS = {"g": "http://www.topografix.com/GPX/1/1",
      "g0": "http://www.topografix.com/GPX/1/0"}


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1 = math.radians(lat1); p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def parse_iso(s):
    if s is None:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        # microseconds variants
        if "." in s:
            base, rest = s.split(".", 1)
            tz = ""
            for sign in ("+", "-"):
                idx = rest.find(sign)
                if idx > 0:
                    tz = rest[idx:]
                    break
            return datetime.fromisoformat(base + tz)
        raise


def parse_gpx(path):
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return None
    root = tree.getroot()
    # detect namespace
    tag = root.tag
    if tag.startswith("{"):
        ns_uri = tag[1:].split("}")[0]
        ns = {"g": ns_uri}
    else:
        ns = {"g": ""}

    # Sport / type
    sport = None
    trk = root.find("g:trk", ns)
    if trk is not None:
        t = trk.find("g:type", ns)
        if t is not None and t.text:
            sport = t.text.strip().lower()
        name = trk.find("g:name", ns)
        name_txt = name.text if (name is not None and name.text) else None
    else:
        name_txt = None

    # Collect trackpoints with time
    pts = []
    if trk is not None:
        for seg in trk.findall("g:trkseg", ns):
            for p in seg.findall("g:trkpt", ns):
                lat = float(p.get("lat"))
                lon = float(p.get("lon"))
                te = p.find("g:time", ns)
                if te is None or not te.text:
                    continue
                t = parse_iso(te.text)
                pts.append((t, lat, lon))

    if len(pts) < 2:
        return None

    # cumulative distance, moving time (ignore pauses > 30s)
    cum = 0.0
    series = [(pts[0][0], 0.0)]
    moving_t = 0.0
    for i in range(1, len(pts)):
        dt = (pts[i][0] - pts[i-1][0]).total_seconds()
        d = haversine(pts[i-1][1], pts[i-1][2], pts[i][1], pts[i][2])
        cum += d
        series.append((pts[i][0], cum))
        if 0 < dt <= 30:
            moving_t += dt

    return {
        "src": os.path.basename(path),
        "sport": sport,
        "name": name_txt,
        "start": pts[0][0].astimezone(timezone.utc).isoformat(),
        "dist_m": cum,
        "moving_s": moving_t,
        "elapsed_s": (pts[-1][0] - pts[0][0]).total_seconds(),
        "series": [(t.timestamp(), round(d, 1)) for t, d in series],
    }


def parse_fit(path):
    # path can be .fit or .fit.gz
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rb") as f:
                data = f.read()
            ff = fitparse.FitFile(data)
        else:
            ff = fitparse.FitFile(path)
        ff.parse()
    except Exception:
        return None

    sport = None
    session_dist = None
    session_moving = None
    session_elapsed = None
    start_time = None

    for msg in ff.get_messages(["sport", "session"]):
        for f in msg:
            if f.name == "sport" and f.value:
                sport = str(f.value).lower()
            elif f.name == "total_distance" and f.value is not None:
                session_dist = float(f.value)
            elif f.name == "total_timer_time" and f.value is not None:
                session_moving = float(f.value)
            elif f.name == "total_elapsed_time" and f.value is not None:
                session_elapsed = float(f.value)
            elif f.name == "start_time" and f.value is not None:
                start_time = f.value

    # records
    series = []
    last_dt = None
    last_dist = None
    for msg in ff.get_messages("record"):
        ts = None; dist = None
        for f in msg:
            if f.name == "timestamp" and f.value is not None:
                ts = f.value
            elif f.name == "distance" and f.value is not None:
                dist = float(f.value)
        if ts is not None and dist is not None:
            if not isinstance(ts, datetime):
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            series.append((ts.timestamp(), dist))
            if start_time is None:
                start_time = ts

    if start_time is None and series:
        start_time = datetime.fromtimestamp(series[0][0], tz=timezone.utc)
    if start_time is None:
        return None
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    # fallback distance from series
    if session_dist is None and series:
        session_dist = series[-1][1]

    if session_dist is None or session_dist < 50:
        return None

    return {
        "src": os.path.basename(path),
        "sport": sport,
        "name": None,
        "start": start_time.astimezone(timezone.utc).isoformat(),
        "dist_m": session_dist,
        "moving_s": session_moving or 0.0,
        "elapsed_s": session_elapsed or 0.0,
        "series": series,
    }


def main():
    files = sorted(os.listdir(ACT_DIR))
    out = []
    bad = 0
    for i, fname in enumerate(files):
        path = os.path.join(ACT_DIR, fname)
        low = fname.lower()
        try:
            if low.endswith(".gpx"):
                r = parse_gpx(path)
            elif low.endswith(".fit") or low.endswith(".fit.gz"):
                r = parse_fit(path)
            else:
                continue
        except Exception as e:
            r = None
            bad += 1
        if r is not None:
            out.append(r)
        if (i + 1) % 100 == 0:
            print(f"{i+1}/{len(files)} parsed, kept={len(out)} bad={bad}")
    print(f"Total: {len(out)} parsed, {bad} errors")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
