import math


def _reject_non_finite(value):
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("non-finite number")
    elif isinstance(value, dict):
        for v in value.values():
            _reject_non_finite(v)
    elif isinstance(value, list):
        for v in value:
            _reject_non_finite(v)


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count does not match contract inputs")

    modules_payload = payloads[0]
    scan_payload = payloads[1]

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

    _reject_non_finite(modules)
    _reject_non_finite(scan)

    module_map = modules["modules"]
    entry = modules["entry"]
    externals = modules.get("externals", [])
    aliases = modules.get("aliases", {})

    imports = scan.get("imports", {})
    module_paths = scan.get("module_paths", {})

    if entry not in module_map:
        raise ValueError("entry module missing")

    path_to_name = {}
    for name, path in module_paths.items():
        path_to_name[path] = name

    def parent_packages(path):
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
                dep_path = module_paths[resolved]
                if dep_path not in visited:
                    queue.append(dep_path)
            else:
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
