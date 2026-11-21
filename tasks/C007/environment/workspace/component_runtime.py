"""Execute either independent component or assemble its two persisted artifacts."""
import argparse
from hashlib import sha256
from importlib import import_module
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")


UNITS = read(ROOT / "components.json")


def project(payload, fields):
    return {k: payload[k] for k in fields if k in payload}


def fingerprint(value):
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return sha256(text.encode("utf-8")).hexdigest()


def sample_matches(actual, expected, tolerance):
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) == type(expected) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        atol = tolerance.get("atol", 0) if isinstance(tolerance, dict) else tolerance
        rtol = tolerance.get("rtol", 0) if isinstance(tolerance, dict) else 0
        return math.isfinite(actual) and abs(actual - expected) <= atol + rtol * abs(expected)
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(sample_matches(actual[k], expected[k], tolerance) for k in actual)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(sample_matches(x, y, tolerance) for x, y in zip(actual, expected))
    return type(actual) == type(expected) and actual == expected


def evaluate_unit(name, payload):
    return import_module("components." + name + ".work").compute(payload)


def persist(name, payload):
    folder = ROOT / "components" / name
    # Invalidate the slot before running so a failed retry cannot reuse an old result.
    write(folder / "result.json", None)
    value = evaluate_unit(name, payload)
    record = dict(component=name, input_sha256=fingerprint(payload), value=value)
    write(folder / "result.json", record)
    return record


def assemble(payload):
    from integration import combine
    values = []
    for name, fields in UNITS.items():
        record = read(ROOT / "components" / name / "result.json")
        if not isinstance(record, dict) or record.get("component") != name or record.get("input_sha256") != fingerprint(project(payload, fields)):
            raise ValueError(f"{name} has no result for the given input")
        values.append(record["value"])
    return combine(payload, *values)


def transform(payload):
    from integration import combine
    values = [evaluate_unit(name, project(payload, fields)) for name, fields in UNITS.items()]
    return combine(payload, *values)


def build_component(input_path, output_path):
    payload = read(input_path)
    out = Path(output_path)
    if Path(input_path).resolve() == ROOT / "public_input.json" and out.resolve() == ROOT / "outputs/result.json":
        for name, fields in UNITS.items():
            persist(name, project(payload, fields))
        value = assemble(payload)
    else:
        value = transform(payload)
    out.parent.mkdir(parents=True, exist_ok=True)
    write(out, value)
    return value


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("action", choices=("run", "check", "join"))
    arg.add_argument("component", nargs="?", choices=tuple(UNITS))
    arg.add_argument("--input", type=Path, help="Full business input for run or join")
    arg.add_argument("--output", type=Path, default=ROOT / "outputs/result.json")
    args = arg.parse_args()
    if args.action == "join":
        if args.component:arg.error("join accepts no component")
        write(args.output, assemble(read(args.input or ROOT / "public_input.json")))
        return
    if not args.component:arg.error("select a component")
    name = args.component
    folder = ROOT / "components" / name
    if args.action == "check":
        if args.input:arg.error("check uses the component's public fixture")
        value = evaluate_unit(name, read(folder / "input.json"))
        # Compare the JSON representation: tuples and JSON arrays have the same wire form.
        normalized = json.loads(json.dumps(value, allow_nan=False))
        if not sample_matches(normalized, read(folder / "expected.json"), read(ROOT / "work_units.json")["sample_tolerance"]):
            raise SystemExit(f"{name}: failed public example")
        print(f"{name}: passed public example")
    else:
        payload = project(read(args.input), UNITS[name]) if args.input else read(folder / "input.json")
        persist(name, payload)


if __name__ == "__main__":
    main()
