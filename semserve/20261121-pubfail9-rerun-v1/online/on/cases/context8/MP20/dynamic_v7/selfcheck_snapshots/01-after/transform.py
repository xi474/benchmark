"""Shared transform implementation for feature configuration components.

Each component's contract declares an ``operation``.  This module implements
the business rules for every operation and dispatches on ``contract["operation"]``.
"""

import copy
import json


def _canonical(value):
    """Compact canonical JSON string for an arbitrary finite JSON value."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _require_nonempty_str(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invalid %s" % what)
    return value


def _feature_schema(payloads, contract):
    if len(payloads) != 1:
        raise ValueError("feature_schema expects exactly one payload")
    data = payloads[0]
    if not isinstance(data, dict):
        raise ValueError("payload must be an object")

    flags = data.get("flags")
    segments = data.get("segments")
    if not isinstance(flags, list):
        raise ValueError("flags must be a list")
    if not isinstance(segments, list):
        raise ValueError("segments must be a list")

    flag_ids = set()
    for flag in flags:
        if not isinstance(flag, dict):
            raise ValueError("flag must be an object")
        fid = _require_nonempty_str(flag.get("id"), "flag id")
        if fid in flag_ids:
            raise ValueError("duplicate flag id")
        flag_ids.add(fid)

        variants = flag.get("variants")
        rules = flag.get("rules")
        if not isinstance(variants, list):
            raise ValueError("variants must be a list")
        if not isinstance(rules, list):
            raise ValueError("rules must be a list")

        variant_ids = set()
        for variant in variants:
            if not isinstance(variant, dict):
                raise ValueError("variant must be an object")
            vid = _require_nonempty_str(variant.get("id"), "variant id")
            if vid in variant_ids:
                raise ValueError("duplicate variant id")
            variant_ids.add(vid)
            if "attachment" not in variant:
                raise ValueError("variant missing attachment")

        rule_ids = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError("rule must be an object")
            rid = _require_nonempty_str(rule.get("id"), "rule id")
            if rid in rule_ids:
                raise ValueError("duplicate rule id")
            rule_ids.add(rid)
            _require_nonempty_str(rule.get("segment"), "rule segment")
            _require_nonempty_str(rule.get("variant"), "rule variant")

    segment_ids = set()
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError("segment must be an object")
        sid = _require_nonempty_str(segment.get("id"), "segment id")
        if sid in segment_ids:
            raise ValueError("duplicate segment id")
        segment_ids.add(sid)

    return {
        "flags": copy.deepcopy(flags),
        "segments": copy.deepcopy(segments),
    }


def _feature_attachments(payloads, contract):
    if len(payloads) != 1:
        raise ValueError("feature_attachments expects exactly one payload")
    data = payloads[0]
    if not isinstance(data, dict):
        raise ValueError("payload must be an object")

    flags = data.get("flags")
    if not isinstance(flags, list):
        raise ValueError("flags must be a list")

    attachments = {}
    for flag in flags:
        if not isinstance(flag, dict):
            raise ValueError("flag must be an object")
        fid = flag.get("id")
        variants = flag.get("variants")
        if not isinstance(variants, list):
            raise ValueError("variants must be a list")
        per_flag = {}
        for variant in variants:
            if not isinstance(variant, dict):
                raise ValueError("variant must be an object")
            vid = variant.get("id")
            attachment = variant.get("attachment")
            per_flag[vid] = {
                "value": copy.deepcopy(attachment),
                "canonical": _canonical(attachment),
            }
        attachments[fid] = per_flag

    return {"attachments": attachments}


def _feature_references(payloads, contract):
    if len(payloads) != 1:
        raise ValueError("feature_references expects exactly one payload")
    data = payloads[0]
    if not isinstance(data, dict):
        raise ValueError("payload must be an object")

    flags = data.get("flags", [])
    segments = data.get("segments", [])

    segment_ids = set()
    for segment in segments:
        if isinstance(segment, dict):
            segment_ids.add(segment.get("id"))

    # Collect (flag_id, rule_id) pairs sorted by flag id then rule id.
    ordered = []
    for flag in flags:
        if not isinstance(flag, dict):
            continue
        fid = flag.get("id")
        for rule in flag.get("rules", []):
            if not isinstance(rule, dict):
                continue
            ordered.append((fid, rule.get("id"), rule))

    ordered.sort(key=lambda t: (t[0], t[1]))

    # First pass: segment references.
    for fid, rid, rule in ordered:
        target = rule.get("segment")
        if target not in segment_ids:
            return {
                "ok": False,
                "error": {"kind": "segment", "flag": fid, "rule": rid, "target": target},
            }

    # Second pass: variant references (within owning flag).
    for fid, rid, rule in ordered:
        target = rule.get("variant")
        flag = next((f for f in flags if isinstance(f, dict) and f.get("id") == fid), None)
        variant_ids = set()
        if flag is not None:
            for variant in flag.get("variants", []):
                if isinstance(variant, dict):
                    variant_ids.add(variant.get("id"))
        if target not in variant_ids:
            return {
                "ok": False,
                "error": {"kind": "variant", "flag": fid, "rule": rid, "target": target},
            }

    return {"ok": True, "error": None}


def _feature_snapshot(payloads, contract):
    if len(payloads) != 4:
        raise ValueError("feature_snapshot expects exactly four payloads")
    original, schema, attachments, references = payloads

    if not isinstance(references, dict):
        raise ValueError("references must be an object")

    if references.get("ok") is not True:
        error = references.get("error")
        old_snapshot = original.get("old_snapshot") if isinstance(original, dict) else None
        return {
            "committed": False,
            "snapshot": copy.deepcopy(old_snapshot),
            "error": copy.deepcopy(error),
            "export": None,
        }

    flags = schema.get("flags", []) if isinstance(schema, dict) else []
    segments = schema.get("segments", []) if isinstance(schema, dict) else []
    att_map = attachments.get("attachments", {}) if isinstance(attachments, dict) else {}

    out_flags = []
    for flag in flags:
        if not isinstance(flag, dict):
            continue
        fid = flag.get("id")
        variants = flag.get("variants", [])
        rules = flag.get("rules", [])

        out_variants = []
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            vid = variant.get("id")
            attachment = None
            per_flag = att_map.get(fid, {})
            if isinstance(per_flag, dict) and vid in per_flag:
                entry = per_flag[vid]
                if isinstance(entry, dict):
                    attachment = entry.get("value")
            out_variants.append({"id": vid, "attachment": copy.deepcopy(attachment)})

        out_rules = []
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            out_rules.append(copy.deepcopy(rule))

        out_flags.append({"id": fid, "variants": out_variants, "rules": out_rules})

    out_segments = []
    for segment in segments:
        if isinstance(segment, dict):
            out_segments.append(copy.deepcopy(segment))

    snapshot = {"flags": out_flags, "segments": out_segments}
    return {
        "committed": True,
        "snapshot": snapshot,
        "error": None,
        "export": _canonical(snapshot),
    }


_OPERATIONS = {
    "feature_schema": _feature_schema,
    "feature_attachments": _feature_attachments,
    "feature_references": _feature_references,
    "feature_snapshot": _feature_snapshot,
}


def transform(payloads, contract):
    """Dispatch on contract["operation"] and return the wrapped result."""
    if not isinstance(contract, dict):
        raise ValueError("contract must be an object")
    operation = contract.get("operation")
    if operation not in _OPERATIONS:
        raise ValueError("unknown operation: %r" % (operation,))

    name = contract.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("contract name must be a non-empty string")

    if not isinstance(payloads, list):
        raise ValueError("payloads must be a list")

    result = _OPERATIONS[operation](payloads, contract)
    return {"name": name, "result": result}
