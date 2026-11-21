def compute(payload):
    """解析受信任文档的覆盖和文档内锚点。

    每个有效键输出 [原源序号, 声明位置, [值位置, 文本, 是否密文, 来源是否可信]]；
    位置为 [源名, 行, 列]。
    """
    sources = payload["sources"]
    result = {}
    for idx, src in enumerate(sources):
        if src.get("trusted") is not True:
            continue
        anchors = {}
        for line_no, raw in enumerate(src["yaml"].split("\n"), start=1):
            line = raw.rstrip("\r")
            if line == "" or line == "---":
                continue
            colon = line.find(":")
            if colon == -1:
                continue
            key = line[:colon]
            if not key or not key.islower() or not key.isalpha():
                continue
            if colon + 1 >= len(line) or line[colon + 1] != " ":
                continue
            rest = line[colon + 2:]
            value_col = colon + 3  # 1-based column of the first value character

            anchor_name = None
            alias_name = None
            if rest.startswith("&"):
                sp = rest.find(" ")
                if sp == -1:
                    anchor_name = rest[1:]
                    text = ""
                else:
                    anchor_name = rest[1:sp]
                    text = rest[sp + 1:]
            elif rest.startswith("*"):
                alias_name = rest[1:]
                text = None
            else:
                text = rest

            if alias_name is not None:
                if alias_name not in anchors:
                    continue
                value_pos, text, is_vault, trusted = anchors[alias_name]
                value_pos = list(value_pos)
            else:
                is_vault = False
                if text.startswith("!vault "):
                    is_vault = True
                    text = text[len("!vault "):]
                trusted = src.get("trusted", False)
                value_pos = [src["name"], line_no, value_col]

            if anchor_name is not None:
                anchors[anchor_name] = [list(value_pos), text, is_vault, trusted]

            result[key] = [
                idx,
                [src["name"], line_no, 1],
                [value_pos, text, is_vault, trusted],
            ]
    return result
