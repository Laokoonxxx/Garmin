"""Shared activity filter — distance-aware minimum plausible running pace."""


def is_valid_running(dist_m, moving_s):
    """Return True if this activity could plausibly be running, given its distance
    and moving time. Rejects cycling-mislabeled-as-running (impossibly fast for the
    distance) and hikes/walks (too slow)."""
    if dist_m is None or moving_s is None:
        return False
    if dist_m <= 0 or moving_s <= 0:
        return False
    # Short activities: no pace filter (warm-up sprints, treadmill snippets)
    if dist_m <= 2000:
        return True
    if moving_s < 300:
        # 2+ km but < 5 min moving time = broken track
        return False
    km = dist_m / 1000.0
    pace_s = moving_s / km
    # Cutoffs anchored to user's personal records:
    #   5 km PR = 4:07/km   -> any activity >= 5 km must be slower than that
    #   HM PR  = 1:33 (4:24/km) -> any activity >= 10 km must be slower than that
    if km < 5:
        min_pace_s = 210   # 3:30/km — short sprints
    elif km < 10:
        min_pace_s = 247   # 4:07/km — 5 km PR
    else:
        min_pace_s = 264   # 4:24/km — 10 km / HM PR
    if pace_s < min_pace_s:
        return False
    if pace_s > 600:       # slower than 10:00/km = hike/walk
        return False
    return True
