"""C031: real interactive bash terminal with control keys.

Public contract (TASK.md):
  * transform(payload) -> {"chunks": [...], "closed": bool}
  * load_payload(input_path) -> object
  * build_component(input_path, output_path) -> result (also writes UTF-8 JSON)
"""

import json
import os
import pty
import select
import signal
import tempfile
import time

KEY_MAP = {
    "Enter": b"\r",
    "C-c": b"\x03",
    "C-d": b"\x04",
    "C-u": b"\x15",
    "Tab": b"\x09",
    "Backspace": b"\x7f",
}


def _normalize(data):
    """Normalize CRLF/CR to LF and drop stray CR bytes."""
    text = data.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def _read_until(fd, marker, timeout):
    """Read from fd until marker appears in the accumulated text or EOF.

    Returns (text, eof).  When marker is found, the marker and any bytes that
    arrived in the same burst are kept in the returned text.
    """
    buf = b""
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        r, _, _ = select.select([fd], [], [], remaining)
        if not r:
            break
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            return _normalize(buf), True
        buf += chunk
        text = _normalize(buf)
        if marker is not None and marker in text:
            return text, False
    return _normalize(buf), False


def transform(payload):
    steps = payload.get("steps", [])
    startup = payload.get("startup", "")
    timeout = payload.get("timeout_seconds", 4)

    tmpdir = tempfile.mkdtemp(prefix="c031_")
    home = tmpdir
    rcfile = os.path.join(tmpdir, "rcfile")
    hushlogin = os.path.join(tmpdir, ".hushlogin")

    # Pre-create empty .hushlogin to suppress login banner.
    with open(hushlogin, "w", encoding="utf-8") as f:
        f.write("")

    rc_lines = [
        "PS1='PROMPT> '",
        "PS2='CONT> '",
        "HISTFILE=/dev/null",
    ]
    if startup:
        rc_lines.append(startup)
    with open(rcfile, "w", encoding="utf-8") as f:
        f.write("\n".join(rc_lines) + "\n")

    env = dict(os.environ)
    env["HOME"] = home
    env["TERM"] = "dumb"
    env["LC_ALL"] = "C"
    env["HISTFILE"] = "/dev/null"

    pid, fd = pty.fork()
    if pid == 0:
        # Child: exec bash.
        os.chdir(home)
        os.environ.clear()
        os.environ.update(env)
        os.execvpe(
            "/bin/bash",
            ["/bin/bash", "--noprofile", "--rcfile", rcfile, "-i"],
            env,
        )

    chunks = []
    closed = False

    try:
        # Initial read: wait for PROMPT>.
        text, eof = _read_until(fd, "PROMPT> ", timeout)
        chunks.append(text)
        if eof:
            closed = True
            return {"chunks": chunks, "closed": closed}

        for step in steps:
            keys = step.get("keys", [])
            until = step.get("until")
            data = b"".join(
                KEY_MAP.get(k, k.encode("utf-8")) for k in keys
            )
            os.write(fd, data)
            text, eof = _read_until(fd, until, timeout)
            chunks.append(text)
            if eof:
                closed = True
                break

        return {"chunks": chunks, "closed": closed}
    finally:
        # Clean up the process group and PTY.
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.waitpid(pid, 0)
        except (ChildProcessError, OSError):
            pass


def load_payload(input_path):
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_component(input_path, output_path):
    payload = load_payload(input_path)
    result = transform(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result
