import json


def combine(payload, left, right):
    """Combine the two component JSON values under the business contract in TASK.md."""
    sources = payload["sources"]
    tags = payload.get("tags", False)
    keys = payload.get("keys", {})

    # Merge the two component outputs. Each maps key -> [src_idx, decl_pos, [val_pos, text, is_vault, trusted]].
    # Override order follows source order; later definitions win.
    merged = {}
    for key, entry in left.items():
        merged[key] = entry
    for key, entry in right.items():
        merged[key] = entry

    # Build the final override view ordered by source index, then by declaration line.
    # left/right already reflect per-document override, but a key may appear in both
    # (trusted and untrusted). The later source index wins.
    final = {}
    for key, entry in merged.items():
        src_idx = entry[0]
        if key not in final or src_idx >= final[key][0]:
            final[key] = entry

    # Determine vault resolution.
    # For each final entry, if is_vault:
    #   tags=True -> keep ciphertext, trusted=False, render="[sealed]"
    #   tags=False -> replace with keys[id] plaintext, trusted=True; if missing -> sealed
    sealed = False
    resolved = {}
    for key, entry in final.items():
        src_idx, decl_pos, (val_pos, text, is_vault, trusted) = entry
        if is_vault:
            if tags:
                resolved[key] = [src_idx, decl_pos, [val_pos, text, True, False]]
            else:
                if text not in keys:
                    sealed = True
                else:
                    resolved[key] = [src_idx, decl_pos, [val_pos, keys[text], False, True]]
        else:
            resolved[key] = entry

    if sealed:
        return {"status": "sealed"}

    # Render: recursively replace ${key} with the render of the final override view.
    # trusted plain values or unsealed values are rendered; untrusted plain values keep raw text.
    render_cache = {}

    def render_value(key):
        if key in render_cache:
            return render_cache[key]
        render_cache[key] = None  # guard against cycles (spec says acyclic)
        src_idx, decl_pos, (val_pos, text, is_vault, trusted) = resolved[key]
        if is_vault:
            # unsealed vault: text is plaintext, trusted=True
            out = text
        elif trusted:
            out = render_text(text)
        else:
            out = text
        render_cache[key] = out
        return out

    def render_text(text):
        result = []
        i = 0
        n = len(text)
        while i < n:
            if text[i] == "$" and i + 1 < n and text[i + 1] == "{":
                j = text.find("}", i + 2)
                if j != -1:
                    ref = text[i + 2:j]
                    if ref in resolved:
                        result.append(render_value(ref))
                        i = j + 1
                        continue
            result.append(text[i])
            i += 1
        return "".join(result)

    entries = []
    for key in sorted(resolved):
        src_idx, decl_pos, (val_pos, text, is_vault, trusted) = resolved[key]
        render = render_value(key)
        entries.append([key, decl_pos, val_pos, trusted, render])

    # Build dump: key: <optional !vault >JSON-string, newline-terminated.
    lines = []
    for key in sorted(resolved):
        src_idx, decl_pos, (val_pos, text, is_vault, trusted) = resolved[key]
        prefix = key + ": "
        if is_vault:
            prefix += "!vault "
        lines.append(prefix + json.dumps(text, ensure_ascii=False))
    dump = "\n".join(lines) + "\n"

    return {"status": "ok", "entries": entries, "dump": dump}
