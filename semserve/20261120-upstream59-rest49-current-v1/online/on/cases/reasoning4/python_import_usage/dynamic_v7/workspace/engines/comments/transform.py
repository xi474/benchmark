import ast


def _load_names(node):
    names = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            names.append(n.id)
    return names


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    source = payloads[0]
    if isinstance(source, dict) and set(source) == {"name", "result"}:
        source = source["result"]
    if not isinstance(source, dict) or "source" not in source:
        raise ValueError("missing source")
    code = source["source"]
    if not isinstance(code, str):
        raise ValueError("source must be string")

    tree = ast.parse(code, type_comments=True)
    uses = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.type_comment is not None:
                raise ValueError("function signature type comment")
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.With, ast.AsyncWith)):
            if getattr(node, "type_comment", None) is not None:
                raise ValueError("for/with type comment")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        tc = getattr(node, "type_comment", None)
        if not tc:
            continue
        # only "# type: expr" comments; "# type: ignore" has no expression
        expr_text = tc.strip()
        if not expr_text or expr_text == "ignore":
            continue
        try:
            expr = ast.parse(expr_text, mode="eval").body
        except SyntaxError as e:
            raise ValueError("bad type comment expression") from e
        line = node.lineno
        for name in _load_names(expr):
            uses.append({"scope": "module", "name": name, "line": line})

    # dedupe and sort by (scope, line, name)
    seen = set()
    result = []
    for u in sorted(uses, key=lambda x: (x["scope"], x["line"], x["name"])):
        key = (u["scope"], u["line"], u["name"])
        if key not in seen:
            seen.add(key)
            result.append(u)

    return {"name": contract["name"], "result": {"uses": result}}
