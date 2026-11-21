import ast


def _module_name(path):
    # path like "pkg/a.py" -> "pkg.a"; "__init__.py" -> ""
    if path.endswith(".py"):
        path = path[:-3]
    parts = [p for p in path.split("/") if p]
    if parts == ["__init__"]:
        return ""
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_of(path):
    # directory containing the module, as a dotted name ('' for root)
    parts = [p for p in path.split("/") if p]
    # drop the file name (last part)
    parts = parts[:-1]
    return ".".join(parts)


def _resolve_relative(package, level, target):
    # package is the dotted name of the directory containing the current file
    base_parts = package.split(".") if package else []
    if level > len(base_parts):
        raise ValueError("relative import beyond root")
    base = base_parts[: len(base_parts) - level + 1]
    if target:
        base = base + target.split(".")
    return ".".join(base)


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")
    raw = payloads[0]
    if isinstance(raw, dict) and set(raw) == {"name", "result"}:
        data = raw["result"]
    else:
        data = raw

    modules = data["modules"]
    entry = data["entry"]
    externals = data["externals"]
    aliases = data["aliases"]

    if entry not in modules:
        raise ValueError("entry not found")

    # build module name -> path map
    module_paths = {}
    for path in modules:
        name = _module_name(path)
        module_paths[name] = path

    imports = {}
    for path, src in modules.items():
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            raise ValueError("invalid source") from e
        deps = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    deps.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level > 0:
                    # relative import
                    package = _package_of(path)
                    target = node.module
                    if target is None:
                        # from . import b  -> target is the imported name
                        target = node.names[0].name if node.names else ""
                    resolved = _resolve_relative(package, node.level, target)
                    # try X.y exists as local module
                    if resolved in module_paths:
                        deps.add(resolved)
                    else:
                        # depend on X (first segment)
                        deps.add(resolved.split(".")[0])
                else:
                    # absolute from X import y
                    mod = node.module
                    if mod is None:
                        continue
                    # try X.y exists as local module
                    candidate = mod
                    if node.names:
                        candidate = mod + "." + node.names[0].name
                    if candidate in module_paths:
                        deps.add(candidate)
                    else:
                        deps.add(mod)
        imports[path] = sorted(deps)

    return {"name": contract["name"], "result": {"imports": imports, "module_paths": module_paths}}
