import ast


def _unparse(node):
    return ast.unparse(node)


def _parse_signature(sig):
    # Wrap as a function definition to reuse Python's parser.
    src = "def " + sig + ":\n    pass\n"
    tree = ast.parse(src)
    func = tree.body[0]
    args = func.args
    params = []

    # positional-only
    for a in args.posonlyargs:
        params.append({
            "name": a.arg,
            "kind": "posonly",
            "annotation": _unparse(a.annotation) if a.annotation is not None else None,
            "default": _unparse(args.defaults[len(args.defaults) - len(args.posonlyargs) + args.posonlyargs.index(a)]) if args.posonlyargs.index(a) >= len(args.posonlyargs) - len(args.defaults) else None,
        })

    # positional-or-keyword
    n_pos = len(args.args)
    n_defaults = len(args.defaults)
    for i, a in enumerate(args.args):
        has_default = i >= n_pos - n_defaults
        params.append({
            "name": a.arg,
            "kind": "positional",
            "annotation": _unparse(a.annotation) if a.annotation is not None else None,
            "default": _unparse(args.defaults[i - (n_pos - n_defaults)]) if has_default else None,
        })

    if args.vararg is not None:
        params.append({
            "name": args.vararg.arg,
            "kind": "vararg",
            "annotation": _unparse(args.vararg.annotation) if args.vararg.annotation is not None else None,
            "default": None,
        })

    # keyword-only
    for i, a in enumerate(args.kwonlyargs):
        has_default = i >= len(args.kwonlyargs) - len(args.kw_defaults)
        params.append({
            "name": a.arg,
            "kind": "kwonly",
            "annotation": _unparse(a.annotation) if a.annotation is not None else None,
            "default": _unparse(args.kw_defaults[i - (len(args.kwonlyargs) - len(args.kw_defaults))]) if has_default and args.kw_defaults[i - (len(args.kwonlyargs) - len(args.kw_defaults))] is not None else None,
        })

    if args.kwarg is not None:
        params.append({
            "name": args.kwarg.arg,
            "kind": "kwarg",
            "annotation": _unparse(args.kwarg.annotation) if args.kwarg.annotation is not None else None,
            "default": None,
        })

    returns = _unparse(func.returns) if func.returns is not None else None
    return func.name, params, returns


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    payload = payloads[0]
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    overloads = payload["overloads"]
    out = []
    for sig in overloads:
        name, params, returns = _parse_signature(sig)
        out.append({"name": name, "parameters": params, "returns": returns})
    return {"name": contract["name"], "result": {"overloads": out}}
