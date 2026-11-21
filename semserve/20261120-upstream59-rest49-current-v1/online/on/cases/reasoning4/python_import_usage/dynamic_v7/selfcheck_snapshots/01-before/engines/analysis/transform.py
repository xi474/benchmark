import ast


def _unwrap(payload):
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    source = _unwrap(payloads[0])
    ordinary = _unwrap(payloads[1])
    annotations = _unwrap(payloads[2])
    comments = _unwrap(payloads[3])

    if not isinstance(source, dict) or "source" not in source:
        raise ValueError("missing source")
    code = source["source"]
    if not isinstance(code, str):
        raise ValueError("source must be string")

    for label, payload in (("ordinary", ordinary), ("annotations", annotations), ("comments", comments)):
        if not isinstance(payload, dict) or "uses" not in payload:
            raise ValueError("missing uses in %s" % label)
        if not isinstance(payload["uses"], list):
            raise ValueError("uses must be list in %s" % label)

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError("invalid source") from exc

    # Collect imports and shadowing info per scope.
    # imports: list of dicts {scope, name, module, line, is_module}
    # shadowed: set of (scope, name) shadowed by param/assign Store (module scope only relevant)
    imports = []
    shadowed = set()

    def walk_scope(body, scope):
        for node in body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname is not None:
                        bind = alias.asname
                    else:
                        bind = alias.name.split(".")[0]
                    imports.append({
                        "scope": scope,
                        "name": bind,
                        "module": alias.name,
                        "line": node.lineno,
                        "is_module": True,
                    })
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    raise ValueError("relative import not supported")
                for alias in node.names:
                    if alias.name == "*":
                        raise ValueError("star import not supported")
                    bind = alias.asname if alias.asname is not None else alias.name
                    imports.append({
                        "scope": scope,
                        "name": bind,
                        "module": node.module,
                        "line": node.lineno,
                        "is_module": False,
                    })
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                raise ValueError("global/nonlocal not supported")
            elif isinstance(node, ast.FunctionDef):
                # function-local imports
                walk_scope(node.body, node.name)
                # shadowing: params and Store assignments inside function
                for arg in node.args.args + node.args.kwonlyargs:
                    shadowed.add((node.name, arg.arg))
                if node.args.vararg is not None:
                    shadowed.add((node.name, node.args.vararg.arg))
                if node.args.kwarg is not None:
                    shadowed.add((node.name, node.args.kwarg.arg))
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                        shadowed.add((node.name, sub.id))
            elif isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef)):
                raise ValueError("unsupported definition")
            else:
                # module-level Store assignments shadow module imports
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                        shadowed.add(("module", sub.id))

    walk_scope(tree.body, "module")

    # Check duplicate (scope, name) imports
    seen_imports = set()
    for imp in imports:
        key = (imp["scope"], imp["name"])
        if key in seen_imports:
            raise ValueError("duplicate import binding %s:%s" % key)
        seen_imports.add(key)

    # Build binding lookup: (scope, name) -> import entry
    binding = {}
    for imp in imports:
        binding[(imp["scope"], imp["name"])] = imp

    # Resolve each use to an import.
    # used_by order: ordinary, annotation, comment
    use_sources = [
        ("ordinary", ordinary["uses"]),
        ("annotation", annotations["uses"]),
        ("comment", comments["uses"]),
    ]

    used_by_map = {}  # (scope, name) -> list of source labels

    for label, uses in use_sources:
        for use in uses:
            scope = use["scope"]
            name = use["name"]
            # resolve binding
            resolved = None
            # function-local import takes priority
            if (scope, name) in binding:
                resolved = binding[(scope, name)]
            elif scope != "module" and (scope, name) in shadowed:
                # shadowed by param/assign, no fallback to module
                resolved = None
            elif (scope, name) in shadowed:
                # module scope shadowed
                resolved = None
            elif ("module", name) in binding:
                resolved = binding[("module", name)]

            if resolved is None:
                continue

            # module references only match module imports
            if resolved["is_module"] is False:
                # from-import binding; any use matches
                pass
            # For module imports (import a.b), the binding name is the top-level
            # module; a use of that name matches. Uses of deeper names (a.b.c)
            # are not Load names of a single Name node, so they won't appear.

            key = (resolved["scope"], resolved["name"])
            if label not in used_by_map.setdefault(key, []):
                used_by_map[key].append(label)

    # Build imports output
    imports_out = []
    for imp in sorted(imports, key=lambda x: (x["scope"], x["line"], x["name"])):
        key = (imp["scope"], imp["name"])
        used = used_by_map.get(key, [])
        imports_out.append({
            "scope": imp["scope"],
            "name": imp["name"],
            "module": imp["module"],
            "line": imp["line"],
            "used_by": used,
        })

    # unused: imports with empty used_by
    unused = sorted(
        "%s:%s" % (imp["scope"], imp["name"])
        for imp in imports
        if not used_by_map.get((imp["scope"], imp["name"]))
    )

    return {
        "name": contract["name"],
        "result": {"imports": imports_out, "unused": unused},
    }
