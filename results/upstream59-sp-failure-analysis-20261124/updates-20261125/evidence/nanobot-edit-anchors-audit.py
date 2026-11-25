"""Audit the provenance of edit_file anchors in 59 archived Nanobot attempts."""

import argparse
import hashlib
import json
import posixpath
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ARCHIVES = HERE.parents[2] / "upstream59-v21-native-traces-dsh-codex-nanobot-20261123/nanobot"
EVENTS = "agent/telemetry/events-v2.jsonl"
NUMBERED_LINE = re.compile(r"(?m)^\d+\| (.*)$")


def audit(archive_path):
    with zipfile.ZipFile(archive_path) as archive:
        case = json.loads(archive.read("case.json"))
        raw = archive.read(EVENTS)
    assert case["task"] == archive_path.stem and case["harness"] == "nanobot"
    pending, writes, reads, edits = {}, {}, defaultdict(list), []
    last_sequence = -1
    for line in raw.splitlines():
        event = json.loads(line)
        tool, kind, seq = event.get("tool_name"), event["event_type"], event["sequence"]
        if tool not in {"read_file", "write_file", "edit_file"}:
            continue
        if kind not in {"tool.started", "tool.finished", "tool.failed"}:
            continue
        assert event["source"] == "agent-native" and event["synthetic"] is False
        assert seq > last_sequence
        last_sequence = seq
        agent, payload = event["agent_id"], event["payload"]
        call = (agent, payload["tool_call_id"])
        if kind == "tool.started":
            arguments = payload["arguments"]
            path = posixpath.normpath(arguments["path"]).removeprefix("/app/")
            key = (agent, path)
            assert call not in pending
            pending[call] = (tool, seq, key, arguments)
            if tool == "edit_file":
                anchor = arguments["old_text"]
                previous = writes.get(key)
                matches = previous[2].count(anchor) if previous and anchor else None
                prior_reads = reads[key]
                edits.append({
                    "agent": agent, "path": path, "edit_start": seq,
                    "anchor_chars": len(anchor),
                    "anchor_sha256": hashlib.sha256(anchor.encode()).hexdigest(),
                    "latest_write_start": previous[0] if previous else None,
                    "latest_write_return": previous[1] if previous else None,
                    "occurrences_in_latest_write": matches,
                    "numbered_read_returns_before_edit": [n for n, _ in prior_reads],
                    "read_returns_containing_anchor": [
                        n for n, content in prior_reads if anchor and anchor in content
                    ],
                    "optional_edit_arguments": sorted(set(arguments) - {"path", "old_text", "new_text"}),
                })
            continue
        start_tool, start_seq, key, arguments = pending.pop(call)
        assert start_tool == tool
        if kind != "tool.finished":
            continue
        result = payload.get("result") or ""
        if tool == "write_file" and result.startswith("Successfully wrote "):
            writes[key] = (start_seq, seq, arguments["content"])
        elif tool == "read_file":
            lines = NUMBERED_LINE.findall(result)
            if lines:
                reads[key].append((seq, "\n".join(lines)))
    assert not pending
    return {
        "task": case["task"], "telemetry_sha256": hashlib.sha256(raw).hexdigest(),
        "edits": edits,
    }


def counts(edits):
    return {
        "edit_calls": len(edits),
        "prior_successful_write": sum(e["latest_write_return"] is not None for e in edits),
        "anchor_in_latest_write": sum((e["occurrences_in_latest_write"] or 0) > 0 for e in edits),
        "anchor_unique_in_latest_write": sum(e["occurrences_in_latest_write"] == 1 for e in edits),
        "unique_in_write_without_prior_numbered_read": sum(
            e["occurrences_in_latest_write"] == 1 and not e["numbered_read_returns_before_edit"]
            for e in edits
        ),
        "anchor_in_any_prior_numbered_read": sum(bool(e["read_returns_containing_anchor"]) for e in edits),
        "calls_with_optional_edit_arguments": sum(bool(e["optional_edit_arguments"]) for e in edits),
    }


def main():
    parser = argparse.ArgumentParser(description="Recompute and verify all 59 tasks against the recorded edit evidence.")
    parser.add_argument("--archives", type=Path, default=ARCHIVES,
                        help="Directory containing the 59 Nanobot trace ZIPs (defaults to the release repository layout)")
    args = parser.parse_args()
    archives = sorted(args.archives.glob("*.zip"))
    if len(archives) != 59:
        parser.error(f"Expected 59 Nanobot ZIPs at {args.archives}; found {len(archives)}. "
                     "Check out the trace directory or pass --archives PATH.")
    rows = [audit(path) for path in archives]
    assert len({row["task"] for row in rows}) == 59
    tasks_with = Counter()
    for row in rows:
        row["counts"] = counts(row["edits"])
        tasks_with.update({name: int(total > 0) for name, total in row["counts"].items()})
    summary = counts([edit for row in rows for edit in row["edits"]])
    report = {
        "population": "One selected attempt per task from the 59 frozen Nanobot ZIPs.",
        "events_member": EVENTS,
        "method": (
            "At each native edit_file start, match earlier completed results by task, agent and "
            "normalized POSIX path (/app/ aliases are workspace-relative). Compare the literal "
            "nonempty old_text to the latest write_file call whose return confirms a successful "
            "write. Count non-overlapping occurrences. For read_file, strip line-number prefixes "
            "and join the visible lines with LF. Empty files and unchanged-file summaries do not "
            "supply numbered content. These comparisons do not establish model memory, complete "
            "current disk contents, or test results."
        ),
        "summary": summary, "tasks_with": dict(tasks_with), "tasks": rows,
    }
    target = HERE / "nanobot-edit-anchors-59.json"
    if report != json.loads(target.read_text(encoding="utf-8-sig")):
        raise SystemExit("Verification failed: recomputed evidence differs from nanobot-edit-anchors-59.json.")
    print(json.dumps({"tasks": len(rows), "summary": summary, "tasks_with": tasks_with}))


if __name__ == "__main__":
    main()
