import ast


def _load_names(node):
    """Yield (name, line) for Load-context Name nodes in ordinary expressions."""
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            yield child.id, child.lineno


def _walk_ordinary(node):
    """Yield (name, line) for Load names, excluding annotations and strings."""
    if isinstance(node, ast.Name):
        if isinstance(node.ctx, ast.Load):
            yield node.id, node.lineno
        return
    if isinstance(node, ast.AnnAssign):
        # target is Store; value is ordinary; annotation excluded
        if node.value is not None:
            yield from _walk_ordinary(node.value)
        return
    if isinstance(node, ast.arg):
        # annotation excluded; arg has no ordinary children
        return
    if isinstance(node, ast.arguments):
        for default in node.defaults + node.kw_defaults:
            if default is not None:
                yield from _walk_ordinary(default)
        return
    if isinstance(node, ast.FunctionDef):
        # skip returns annotation and arg annotations; handle defaults/body
        for default in node.args.defaults + node.args.kw_defaults:
            if default is not None:
                yield from _walk_ordinary(default)
        for stmt in node.body:
            yield from _walk_ordinary(stmt)
        return
    if isinstance(node, ast.Constant):
        # strings and other constants produce no Load names
        return
    for child in ast.iter_child_nodes(node):
        yield from _walk_ordinary(child)


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict) or "source" not in payload:
        raise ValueError("missing source")
    source = payload["source"]
    if not isinstance(source, str):
        raise ValueError("source must be string")

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError("invalid source") from exc

    uses = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.decorator_list:
                raise ValueError("decorators not supported")
            # default values are in module scope
            for default in node.args.defaults + node.args.kw_defaults:
                if default is not None:
                    for name, line in _load_names(default):
                        uses.append({"scope": "module", "name": name, "line": line})
            for stmt in node.body:
                for name, line in _walk_ordinary(stmt):
                    uses.append({"scope": node.name, "name": name, "line": line})
        elif isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)):
            raise ValueError("unsupported definition")
        else:
            for name, line in _walk_ordinary(node):
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
