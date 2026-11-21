"""Implement the business transform. I/O helpers are supplied and editable here."""
from pathlib import Path
import json
import re
from runtime import build


def _extract_conf_chains(template_text):
    """Yield conf access chains (as dotted strings) from {{ ... }} expressions."""
    chains = []
    for match in re.finditer(r"\{\{(.*?)\}\}", template_text, flags=re.DOTALL):
        expr = match.group(1)
        # Find every identifier chain starting with `conf`.
        for m in re.finditer(r"\bconf\b", expr):
            start = m.start()
            chain = "conf"
            i = m.end()
            while i < len(expr):
                c = expr[i]
                if c == ".":
                    # attribute access: read identifier
                    j = i + 1
                    while j < len(expr) and (expr[j].isalnum() or expr[j] == "_"):
                        j += 1
                    if j == i + 1:
                        break
                    chain += "." + expr[i + 1:j]
                    i = j
                elif c == "[":
                    # subscript: read a static string literal
                    j = i + 1
                    while j < len(expr) and expr[j] in " \t":
                        j += 1
                    if j < len(expr) and expr[j] in "\"'":
                        quote = expr[j]
                        k = j + 1
                        while k < len(expr) and expr[k] != quote:
                            k += 1
                        if k < len(expr):
                            chain += "." + expr[j + 1:k]
                            i = k + 1
                            continue
                    break
                else:
                    break
            chains.append(chain)
    return chains


def _longest_option_prefix(chain, options):
    """Return the longest option that is a dotted prefix of the chain."""
    # The chain starts with the literal `conf` root; options are relative to it.
    if chain == "conf":
        rest = ""
    elif chain.startswith("conf."):
        rest = chain[len("conf."):]
    else:
        rest = chain
    best = None
    for opt in options:
        if rest == opt or rest.startswith(opt + "."):
            if best is None or len(opt) > len(best):
                best = opt
    return best


def transform(payload, contract):
    templates = payload["templates"]
    options = payload["options"]
    result = {}
    for tid, text in templates.items():
        keys = set()
        for chain in _extract_conf_chains(text):
            prefix = _longest_option_prefix(chain, options)
            if prefix is not None:
                keys.add(prefix)
        result[tid] = sorted(keys)
    return result


def load_payload(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_component(root, contract):
    return build(root, contract, transform)
