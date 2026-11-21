import math
from decimal import Decimal, ROUND_HALF_UP


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    data = payloads[0]
    if isinstance(data, dict) and set(data) == {"name", "result"}:
        data = data["result"]
    if not isinstance(data, dict):
        raise ValueError("input must be an object")

    playlist = data.get("playlist")
    tracks = data.get("tracks")
    if not isinstance(playlist, dict) or not isinstance(tracks, list):
        raise ValueError("missing playlist or tracks")

    name = playlist.get("name")
    if not isinstance(name, str):
        raise ValueError("playlist.name must be str")
    if "\r" in name or "\n" in name:
        raise ValueError("playlist.name must not contain CR/LF")

    track_map = {}
    for t in tracks:
        if not isinstance(t, dict):
            raise ValueError("track must be object")
        tid = t.get("id")
        if not isinstance(tid, str):
            raise ValueError("track.id must be str")
        track_map[tid] = t

    lines = ["#EXTM3U", "#PLAYLIST:" + name]
    for tid in playlist.get("track_ids", []):
        t = track_map.get(tid)
        if t is None:
            raise ValueError("unknown track id")
        duration = t.get("duration")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise ValueError("track.duration must be number")
        if not math.isfinite(duration):
            raise ValueError("track.duration must be finite")
        seconds = int(Decimal(str(duration)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        artist = t.get("artist", "")
        title = t.get("title", "")
        path = t.get("path", "")
        if not isinstance(artist, str) or not isinstance(title, str) or not isinstance(path, str):
            raise ValueError("track fields must be str")
        if "\r" in artist or "\n" in artist or "\r" in title or "\n" in title or "\r" in path or "\n" in path:
            raise ValueError("track fields must not contain CR/LF")
        lines.append("#EXTINF:%d,%s - %s" % (seconds, artist, title))
        lines.append(path)

    return {"name": contract["name"], "result": {"m3u": "\n".join(lines) + "\n"}}
