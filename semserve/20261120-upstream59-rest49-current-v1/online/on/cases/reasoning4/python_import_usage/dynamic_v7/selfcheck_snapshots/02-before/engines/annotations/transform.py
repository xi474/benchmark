import ast


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

    tree = _parse_module(code)
    uses = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            scope = node.name
            # parameter annotations and return annotation belong to module scope
            for arg in node.args.args + node.args.kwonlyargs:
                if arg.annotation is not None:
                    _collect(arg.annotation, "module", arg.annotation.lineno, uses)
            if node.args.vararg is not None and node.args.vararg.annotation is not None:
                _collect(node.args.vararg.annotation, "module",
                         node.args.vararg.annotation.lineno, uses)
            if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
                _collect(node.args.kwarg.annotation, "module",
                         node.args.kwarg.annotation.lineno, uses)
            if node.returns is not None:
                _collect(node.returns, "module", node.returns.lineno, uses)
            # function body AnnAssign annotations belong to the function scope
            for sub in ast.walk(node):
                if isinstance(sub, ast.AnnAssign) and sub.annotation is not None:
                    _collect(sub.annotation, scope, sub.annotation.lineno, uses)
        elif isinstance(node, ast.AnnAssign):
            # module-level AnnAssign
            if node.annotation is not None:
                _collect(node.annotation, "module", node.annotation.lineno, uses)

    # dedupe and sort by (scope, line, name)
    seen = set()
    result = []
    for u in sorted(uses, key=lambda x: (x["scope"], x["line"], x["name"])):
        key = (u["scope"], u["line"], u["name"])
        if key not in seen:
            seen.add(key)
            result.append(u)
    return {"name": contract["name"], "result": {"uses": result}}


def _parse_module(code):
    try:
        return ast.parse(code)
    except SyntaxError as e:
        raise ValueError("bad source: %s" % e)


def _collect(annotation, scope, line, uses):
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        # forward reference: reparse as expression
        try:
            expr = ast.parse(annotation.value, mode="eval")
        except SyntaxError:
            raise ValueError("bad forward annotation")
        _collect_expr(expr.body, scope, line, uses)
    else:
        _collect_expr(annotation, scope, line, uses)


def _collect_expr(node, scope, line, uses):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
            uses.append({"scope": scope, "name": sub.id, "line": line})
