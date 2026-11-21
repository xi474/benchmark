import math
import re


_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _check_finite(value):
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        raise ValueError("non-finite number")
    return value


def _validate(value):
    if isinstance(value, dict):
        for k, v in value.items():
            _validate(k)
            _validate(v)
    elif isinstance(value, list):
        for item in value:
            _validate(item)
    elif isinstance(value, float):
        _check_finite(value)
    return value


def _balanced_parens(s):
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _parse_doc(doc):
    """Parse doc lines into a list of (name, type, description) directives."""
    entries = []
    for raw in doc.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith(":param "):
            rest = line[len(":param "):]
            # rest is either "name: desc" or "TYPE name: desc"
            m = re.match(r"^([^:]+?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", rest)
            if m:
                type_part, name, desc = m.group(1), m.group(2), m.group(3)
                if not _balanced_parens(type_part):
                    raise ValueError("unbalanced parens in type")
                entries.append((name, type_part, desc))
            else:
                m2 = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", rest)
                if not m2:
                    raise ValueError("bad param directive")
                name, desc = m2.group(1), m2.group(2)
                entries.append((name, None, desc))
        elif line.startswith(":type "):
            rest = line[len(":type "):]
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", rest)
            if not m:
                raise ValueError("bad type directive")
            name, type_part = m.group(1), m.group(2)
            if not _balanced_parens(type_part):
                raise ValueError("unbalanced parens in type")
            entries.append((name, type_part, None))
        # other lines ignored
    return entries


def transform(payloads, contract):
    if not isinstance(payloads, list):
        raise ValueError("payloads must be a list")
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    _validate(payloads)

    payload = payloads[0]
    # unwrap name/result wrapper if present
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    objects = payload["objects"]
    docs = {}
    for obj in objects:
        oid = obj["id"]
        doc = obj["doc"]
        entries = _parse_doc(doc)
        # build map
        params = {}  # name -> {type, description}
        for name, type_part, desc in entries:
            if type_part is not None and desc is not None:
                # :param TYPE name: desc
                if name in params:
                    raise ValueError("duplicate param")
                params[name] = {"type": type_part, "description": desc}
            elif type_part is not None and desc is None:
                # :type name: TYPE
                if name in params:
                    # explicit :type overrides inline TYPE
                    params[name]["type"] = type_part
                else:
                    params[name] = {"type": type_part, "description": ""}
            elif type_part is None and desc is not None:
                # :param name: desc
                if name in params:
                    raise ValueError("duplicate param")
                params[name] = {"type": None, "description": desc}
        # sort by name
        result = [
            {"name": n, "type": params[n]["type"], "description": params[n]["description"]}
            for n in sorted(params)
        ]
        docs[oid] = result
    return {"name": contract["name"], "result": {"docs": docs}}
