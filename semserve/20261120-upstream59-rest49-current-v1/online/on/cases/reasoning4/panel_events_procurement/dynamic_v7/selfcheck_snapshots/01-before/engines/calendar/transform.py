import copy


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_finite_num(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    if isinstance(v, float):
        import math
        return math.isfinite(v)
    return False


def _require_int(v, name):
    if not _is_int(v):
        raise ValueError("invalid %s" % name)
    return v


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    payload = payloads[0]
    # If the object has exactly keys name/result, use result as business input.
    if isinstance(payload, dict) and set(payload.keys()) == {"name", "result"}:
        data = payload["result"]
    else:
        data = payload

    if not isinstance(data, dict):
        raise ValueError("input must be object")

    now = _require_int(data.get("now"), "now")
    duration = _require_int(data.get("duration"), "duration")
    gap = _require_int(data.get("gap"), "gap")
    if duration < 1:
        raise ValueError("duration must be >= 1")
    if gap < 0:
        raise ValueError("gap must be >= 0")

    windows = data.get("windows")
    busy = data.get("busy")
    if not isinstance(windows, list) or not isinstance(busy, list):
        raise ValueError("windows/busy must be lists")

    intervals = []
    for w in windows:
        if not isinstance(w, dict):
            raise ValueError("window must be object")
        start = _require_int(w.get("start"), "window.start")
        end = _require_int(w.get("end"), "window.end")
        if end <= start:
            raise ValueError("window end must be > start")
        intervals.append((start, end))

    busy_intervals = []
    for b in busy:
        if not isinstance(b, dict):
            raise ValueError("busy must be object")
        start = _require_int(b.get("start"), "busy.start")
        end = _require_int(b.get("end"), "busy.end")
        if end <= start:
            raise ValueError("busy end must be > start")
        busy_intervals.append((start, end))

    # Build free intervals: union of windows minus busy, excluding before now.
    # Merge windows union first.
    merged = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            if end > merged[-1][1]:
                merged[-1][1] = end

    # Subtract busy intervals.
    free = []
    for start, end in merged:
        cur = start
        for bs, be in sorted(busy_intervals):
            if be <= cur:
                continue
            if bs >= end:
                break
            if bs > cur:
                free.append((cur, min(bs, end)))
            cur = max(cur, be)
            if cur >= end:
                break
        if cur < end:
            free.append((cur, end))

    # Exclude times before now.
    free = [(max(s, now), e) for (s, e) in free if e > now]

    slots = []
    # First slot: earliest free interval that can hold duration.
    first = None
    for s, e in free:
        if e - s >= duration:
            first = (s, s + duration)
            break

    if first is None:
        return {"name": contract["name"], "result": {"slots": [], "complete": False}}

    slots.append({"start": first[0], "end": first[1]})

    # Second slot: earliest start >= first.end + gap.
    min_start = first[1] + gap
    second = None
    for s, e in free:
        candidate = max(s, min_start)
        if e - candidate >= duration:
            second = (candidate, candidate + duration)
            break

    if second is None:
        return {"name": contract["name"], "result": {"slots": slots, "complete": False}}

    slots.append({"start": second[0], "end": second[1]})
    return {"name": contract["name"], "result": {"slots": slots, "complete": True}}
