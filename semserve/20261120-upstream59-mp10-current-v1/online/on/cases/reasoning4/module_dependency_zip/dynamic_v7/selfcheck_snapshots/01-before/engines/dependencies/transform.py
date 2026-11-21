def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count does not match contract inputs")

    modules_payload = payloads[0]
    scan_payload = payloads[1]

    # Unwrap name/result envelope when the object keys are exactly name/result.
    def business_input(obj):
        if isinstance(obj, dict) and set(obj) == {"name", "result"}:
            return obj["result"]
        return obj

    modules = business_input(modules_payload)
    scan = business_input(scan_payload)

    if not isinstance(modules, dict) or "modules" not in modules:
        raise ValueError("missing modules")
    if not isinstance(scan, dict):
        raise ValueError("invalid scan result")

    module_map = modules["modules"]
    entry = modules["entry"]
    externals = modules.get("externals", [])
    aliases = modules.get("aliases", {})

    imports = scan.get("imports", {})
    module_paths = scan.get("module_paths", {})

    if entry not in module_map:
        raise ValueError("entry module missing")

    # Build path -> module name mapping from scan.
    path_to_name = {}
    for name, path in module_paths.items():
        path_to_name[path] = name

    def parent_packages(path):
        # Return all parent package __init__.py paths that exist.
        parts = path.split("/")
        parents = []
        for i in range(1, len(parts)):
            pkg_path = "/".join(parts[:i]) + "/__init__.py"
            if pkg_path in module_map:
                parents.append(pkg_path)
        return parents

    def is_external(name):
        if name in externals:
            return True
        first = name.split(".", 1)[0]
        return first in externals

    def resolve_alias(name):
        return aliases.get(name, name)

    # BFS over local modules.
    paths = set()
    external = set()
    queue = [entry]
    visited = set()

    while queue:
        path = queue.pop(0)
        if path in visited:
            continue
        visited.add(path)
        paths.add(path)
        for p in parent_packages(path):
            paths.add(p)

        for dep in imports.get(path, []):
            resolved = resolve_alias(dep)
            if resolved in module_paths:
                # local module
                dep_path = module_paths[resolved]
                if dep_path not in visited:
                    queue.append(dep_path)
            else:
                # external module
                if not is_external(resolved):
                    raise ValueError("unknown module: %s" % resolved)
                external.add(resolved)

    return {
        "name": contract["name"],
        "result": {
            "paths": sorted(paths),
            "external": sorted(external),
        },
    }
