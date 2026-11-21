import math


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_finite_number(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    if isinstance(v, float):
        return math.isfinite(v)
    return False


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    data = _unwrap(payloads[0])
    if not isinstance(data, dict):
        raise ValueError("input must be object")

    tracks = data.get("tracks")
    playlist = data.get("playlist")
    replacement = data.get("replacement")
    criteria = data.get("criteria")

    if not isinstance(tracks, list):
        raise ValueError("tracks must be list")
    if not isinstance(playlist, dict):
        raise ValueError("playlist must be object")
    if not isinstance(replacement, list):
        raise ValueError("replacement must be list")
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be object")

    # Build track map, validate each track.
    track_map = {}
    for t in tracks:
        if not isinstance(t, dict):
            raise ValueError("track must be object")
        tid = t.get("id")
        if not isinstance(tid, str):
            raise ValueError("track id must be str")
        if tid in track_map:
            raise ValueError("duplicate track id")
        title = t.get("title")
        artist = t.get("artist")
        path = t.get("path")
        duration = t.get("duration")
        if not isinstance(title, str):
            raise ValueError("title must be str")
        if not isinstance(artist, str):
            raise ValueError("artist must be str")
        if not isinstance(path, str):
            raise ValueError("path must be str")
        if not _is_finite_number(duration) or duration < 0:
            raise ValueError("duration must be non-negative finite number")
        if "\r" in title or "\n" in title:
            raise ValueError("title must not contain CR/LF")
        if "\r" in artist or "\n" in artist:
            raise ValueError("artist must not contain CR/LF")
        if "\r" in path or "\n" in path:
            raise ValueError("path must not contain CR/LF")
        track_map[tid] = t

    # Validate playlist fields.
    pid = playlist.get("id")
    name = playlist.get("name")
    track_ids = playlist.get("track_ids")
    track_count = playlist.get("track_count")
    duration = playlist.get("duration")
    if not isinstance(pid, str):
        raise ValueError("playlist id must be str")
    if not isinstance(name, str):
        raise ValueError("playlist name must be str")
    if "\r" in name or "\n" in name:
        raise ValueError("playlist name must not contain CR/LF")
    if not isinstance(track_ids, list):
        raise ValueError("track_ids must be list")
    if not _is_int(track_count):
        raise ValueError("track_count must be int")
    if not _is_finite_number(duration):
        raise ValueError("duration must be finite number")

    # Validate replacement ids.
    for rid in replacement:
        if not isinstance(rid, str):
            raise ValueError("replacement id must be str")
        if rid not in track_map:
            raise ValueError("unknown replacement id")

    new_tracks = [track_map[rid] for rid in replacement]
    new_duration = sum(track_map[rid]["duration"] for rid in replacement)

    result = {
        "playlist": {
            "id": pid,
            "name": name,
            "track_ids": list(replacement),
            "track_count": len(replacement),
            "duration": new_duration,
        },
        "tracks": new_tracks,
    }

    return {"name": contract["name"], "result": result}
