import re


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _unwrap(payload):
    # When an input object has exactly keys name/result, only its result is
    # the business input; other objects are interpreted as-is.
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def _qualify_type(type_str, aliases):
    """Replace standalone identifiers (not adjacent to a dot) with aliases."""
    if type_str is None:
        return None
    out = []
    i = 0
    n = len(type_str)
    while i < n:
        ch = type_str[i]
        if ch.isalpha() or ch == "_":
            j = i
            while j < n and (type_str[j].isalnum() or type_str[j] == "_"):
                j += 1
            ident = type_str[i:j]
            # Not preceded by a dot and not followed by a dot -> standalone.
            preceded_by_dot = i > 0 and type_str[i - 1] == "."
            followed_by_dot = j < n and type_str[j] == "."
            if (not preceded_by_dot) and (not followed_by_dot) and ident in aliases:
                out.append(aliases[ident])
            else:
                out.append(ident)
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def transform(payloads, contract):
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count mismatch")

    sig_payload = _unwrap(payloads[0])
    param_payload = _unwrap(payloads[1])
    inherit_payload = _unwrap(payloads[2])

    overloads = sig_payload["overloads"]
    docs = param_payload["docs"]
    provider = inherit_payload["provider"]
    namespace = inherit_payload["namespace"]
    aliases = inherit_payload["aliases"]

    if provider is None:
        parameters = []
    else:
        provider_docs = docs.get(provider, [])
        parameters = []
        for entry in provider_docs:
            parameters.append(
                {
                    "name": entry["name"],
                    "type": _qualify_type(entry["type"], aliases),
                    "description": entry["description"],
                }
            )

    return {
        "name": contract["name"],
        "result": {
            "overloads": overloads,
            "provider": provider,
            "namespace": namespace,
            "parameters": parameters,
        },
    }
