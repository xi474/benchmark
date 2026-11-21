"""Shared transform: dispatch on contract operation.

Each operation validates its inputs, computes a result object, and returns the
wrapper {"name": contract["name"], "result": <result>}.  Inputs and the contract
are never mutated.
"""

import copy
import json
import math


def _canonical(obj):
    """Compact canonical JSON string used for canonical/export fields."""
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )


def _check_finite(value):
    """Raise ValueError if value contains NaN or Infinity anywhere."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite number is not allowed")
    elif isinstance(value, dict):
        for v in value.values():
            _check_finite(v)
    elif isinstance(value, list):
        for v in value:
            _check_finite(v)


def _nonempty_str(value):
    return isinstance(value, str) and value.strip() != ""


def _unwrap(payload):
    """If a payload object has exactly the keys name/result, its result is the
    business input; otherwise the object is interpreted as-is."""
    if isinstance(payload, dict) and set(payload) == {"name", "result"}:
        return payload["result"]
    return payload


def _validate_schema_input(payload):
    """Validate the shared feature_schema/feature_attachments input shape.

    Returns (flags, segments) as deep copies.  Only shape and basic types are
    checked here; dangling segment/variant references are not rejected.
    """
    data = _unwrap(payload)
    if not isinstance(data, dict):
        raise ValueError("schema input must be an object")
    for key in ("flags", "segments", "old_snapshot"):
        if key not in data:
            raise ValueError("schema input missing required field: %s" % key)
    flags = data["flags"]
    segments = data["segments"]
    old_snapshot = data["old_snapshot"]
    if not isinstance(flags, list):
        raise ValueError("flags must be a list")
    if not isinstance(segments, list):
        raise ValueError("segments must be a list")
    if not isinstance(old_snapshot, dict):
        raise ValueError("old_snapshot must be an object")
    _check_finite(old_snapshot)

    flag_ids = set()
    for flag in flags:
        if not isinstance(flag, dict):
            raise ValueError("flag must be an object")
        for key in ("id", "variants", "rules"):
            if key not in flag:
                raise ValueError("flag missing required field: %s" % key)
        fid = flag["id"]
        if not _nonempty_str(fid):
            raise ValueError("flag id must be a non-empty string")
        if fid in flag_ids:
            raise ValueError("duplicate flag id: %s" % fid)
        flag_ids.add(fid)

        variants = flag["variants"]
        rules = flag["rules"]
        if not isinstance(variants, list):
            raise ValueError("variants must be a list")
        if not isinstance(rules, list):
            raise ValueError("rules must be a list")

        variant_ids = set()
        for variant in variants:
            if not isinstance(variant, dict):
                raise ValueError("variant must be an object")
            for key in ("id", "attachment"):
                if key not in variant:
                    raise ValueError("variant missing required field: %s" % key)
            vid = variant["id"]
            if not _nonempty_str(vid):
                raise ValueError("variant id must be a non-empty string")
            if vid in variant_ids:
                raise ValueError("duplicate variant id: %s" % vid)
            variant_ids.add(vid)
            _check_finite(variant["attachment"])

        rule_ids = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError("rule must be an object")
            for key in ("id", "segment", "variant"):
                if key not in rule:
                    raise ValueError("rule missing required field: %s" % key)
            rid = rule["id"]
            if not _nonempty_str(rid):
                raise ValueError("rule id must be a non-empty string")
            if rid in rule_ids:
                raise ValueError("duplicate rule id: %s" % rid)
            rule_ids.add(rid)
            if not _nonempty_str(rule["segment"]):
                raise ValueError("rule segment must be a non-empty string")
            if not _nonempty_str(rule["variant"]):
                raise ValueError("rule variant must be a non-empty string")

    segment_ids = set()
    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError("segment must be an object")
        if "id" not in segment:
            raise ValueError("segment missing required field: id")
        sid = segment["id"]
        if not _nonempty_str(sid):
            raise ValueError("segment id must be a non-empty string")
        if sid in segment_ids:
            raise ValueError("duplicate segment id: %s" % sid)
        segment_ids.add(sid)

    return copy.deepcopy(flags), copy.deepcopy(segments)


def _feature_schema(payloads):
    flags, segments = _validate_schema_input(payloads[0])
    return {"flags": flags, "segments": segments}


def _feature_attachments(payloads):
    flags, _segments = _validate_schema_input(payloads[0])
    attachments = {}
    for flag in flags:
        fid = flag["id"]
        attachments[fid] = {}
        for variant in flag["variants"]:
            vid = variant["id"]
            value = variant["attachment"]
            attachments[fid][vid] = {
                "value": value,
                "canonical": _canonical(value),
            }
    return {"attachments": attachments}


def _feature_references(payloads):
    data = _unwrap(payloads[0])
    if not isinstance(data, dict):
        raise ValueError("references input must be an object")
    flags = data.get("flags")
    segments = data.get("segments")
    if not isinstance(flags, list) or not isinstance(segments, list):
        raise ValueError("references input missing flags/segments")

    segment_ids = set()
    for segment in segments:
        if isinstance(segment, dict) and "id" in segment:
            segment_ids.add(segment["id"])

    sorted_flags = sorted(
        flags, key=lambda f: f.get("id", "") if isinstance(f, dict) else ""
    )

    # Segment references first, sorted by flag/rule id.
    for flag in sorted_flags:
        if not isinstance(flag, dict):
            continue
        rules = flag.get("rules", [])
        if not isinstance(rules, list):
            rules = []
        for rule in sorted(
            rules, key=lambda r: r.get("id", "") if isinstance(r, dict) else ""
        ):
            if not isinstance(rule, dict):
                continue
            target = rule.get("segment")
            if target not in segment_ids:
                return {
                    "ok": False,
                    "error": {
                        "kind": "segment",
                        "flag": flag.get("id"),
                        "rule": rule.get("id"),
                        "target": target,
                    },
                }

    # Variant references, only within the owning flag.
    for flag in sorted_flags:
        if not isinstance(flag, dict):
            continue
        variant_ids = set()
        for variant in flag.get("variants", []):
            if isinstance(variant, dict) and "id" in variant:
                variant_ids.add(variant["id"])
        rules = flag.get("rules", [])
        if not isinstance(rules, list):
            rules = []
        for rule in sorted(
            rules, key=lambda r: r.get("id", "") if isinstance(r, dict) else ""
        ):
            if not isinstance(rule, dict):
                continue
            target = rule.get("variant")
            if target not in variant_ids:
                return {
                    "ok": False,
                    "error": {
                        "kind": "variant",
                        "flag": flag.get("id"),
                        "rule": rule.get("id"),
                        "target": target,
                    },
                }

    return {"ok": True, "error": None}


def _feature_snapshot(payloads):
    original = _unwrap(payloads[0])
    schema = _unwrap(payloads[1])
    attachments = _unwrap(payloads[2])
    references = _unwrap(payloads[3])

    if not isinstance(original, dict) or "old_snapshot" not in original:
        raise ValueError("snapshot original input missing old_snapshot")
    old_snapshot = original["old_snapshot"]

    if not isinstance(references, dict) or "ok" not in references:
        raise ValueError("references result invalid")

    if references.get("ok") is not True:
        return {
            "committed": False,
            "snapshot": copy.deepcopy(old_snapshot),
            "error": references.get("error"),
            "export": None,
        }

    if not isinstance(schema, dict):
        raise ValueError("schema result invalid")
    flags = schema.get("flags", [])
    segments = schema.get("segments", [])
    if not isinstance(flags, list) or not isinstance(segments, list):
        raise ValueError("schema result missing flags/segments")

    att = attachments.get("attachments", {}) if isinstance(attachments, dict) else {}

    out_flags = []
    for flag in sorted(
        flags, key=lambda f: f.get("id", "") if isinstance(f, dict) else ""
    ):
        if not isinstance(flag, dict):
            continue
        fid = flag["id"]
        out_variants = []
        for variant in sorted(
            flag.get("variants", []),
            key=lambda v: v.get("id", "") if isinstance(v, dict) else "",
        ):
            if not isinstance(variant, dict):
                continue
            vid = variant["id"]
            attachment = att.get(fid, {}).get(vid, {}).get("value")
            out_variants.append({"id": vid, "attachment": attachment})
        out_rules = []
        for rule in sorted(
            flag.get("rules", []),
            key=lambda r: r.get("id", "") if isinstance(r, dict) else "",
        ):
            if isinstance(rule, dict):
                out_rules.append(copy.deepcopy(rule))
        out_flags.append({"id": fid, "variants": out_variants, "rules": out_rules})

    out_segments = []
    for segment in sorted(
        segments, key=lambda s: s.get("id", "") if isinstance(s, dict) else ""
    ):
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
    if not isinstance(contract, dict):
        raise ValueError("contract must be an object")
    for key in ("name", "operation", "inputs"):
        if key not in contract:
            raise ValueError("contract missing required field: %s" % key)
    if not isinstance(contract["inputs"], list):
        raise ValueError("contract inputs must be a list")
    if not isinstance(payloads, list):
        raise ValueError("payloads must be a list")
    if len(payloads) != len(contract["inputs"]):
        raise ValueError("payload count does not match contract inputs")

    operation = contract["operation"]
    handler = _OPERATIONS.get(operation)
    if handler is None:
        raise ValueError("unknown operation: %s" % operation)

    result = handler(payloads)
    return {"name": contract["name"], "result": result}
