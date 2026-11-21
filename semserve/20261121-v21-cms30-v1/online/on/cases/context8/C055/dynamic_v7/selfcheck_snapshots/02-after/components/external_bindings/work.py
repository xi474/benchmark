def compute(payload):
    """Parse untrusted documents' coverage and intra-document anchors.

    Each valid key yields [source_index, declaration_position,
    [value_position, text, is_vault, source_trusted]] where positions are
    [source_name, line, column]. Only keys declared in untrusted sources are
    emitted; later definitions override earlier ones, and aliases resolve to
    the value position captured at definition time.
    """
    sources = payload["sources"]
    result = {}
    for idx, source in enumerate(sources):
        if source["trusted"]:
            continue
        anchors = {}
        for lineno, raw in enumerate(source["yaml"].split("\n"), start=1):
            line = raw
            if line == "---" or line.strip() == "":
                continue
            # Each line is exactly "key: value" (one space after colon).
            key, value = line.split(": ", 1)
            # Value position: first char after "key: " (may be & or !).
            value_col = len(key) + 3
            value_pos = [source["name"], lineno, value_col]

            text = value
            is_vault = False
            if value.startswith("&"):
                # "&name value" -> anchor definition
                rest = value[1:]
                name, _, anchored = rest.partition(" ")
                anchors[name] = [source["name"], lineno, value_col + 1 + len(name) + 1]
                text = anchored
                if anchored.startswith("!vault"):
                    is_vault = True
                    text = anchored[len("!vault"):].strip()
            elif value.startswith("*"):
                # "*name" -> alias reference to a previously defined anchor
                name = value[1:]
                value_pos = anchors[name]
                text = None  # resolved below from the anchored value
            elif value.startswith("!vault"):
                is_vault = True
                text = value[len("!vault"):].strip()

            if text is None:
                # Alias: recover the anchored text from the anchor's position.
                apos = value_pos
                aline = sources[idx]["yaml"].split("\n")[apos[1] - 1]
                avalue = aline.split(": ", 1)[1]
                if avalue.startswith("&"):
                    _, _, anchored = avalue[1:].partition(" ")
                    if anchored.startswith("!vault"):
                        is_vault = True
                        text = anchored[len("!vault"):].strip()
                    else:
                        text = anchored
                elif avalue.startswith("!vault"):
                    is_vault = True
                    text = avalue[len("!vault"):].strip()
                else:
                    text = avalue

            result[key] = [
                idx,
                [source["name"], lineno, 1],
                [value_pos, text, is_vault, source["trusted"]],
            ]
    return result
