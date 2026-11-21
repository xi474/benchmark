"""Combine the two component values into the C031 PTY-bash result.

left  = key_sequences value: list of hex strings, one per step.
right = session_config value: dict with rc, timeout, markers.
"""
import os
import pty
import select
import signal
import tempfile
import time


def _normalize(data):
    # CRLF -> LF, then drop any remaining isolated CR.
    data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def _read_until(fd, marker, timeout):
    """Read from fd until marker appears (or EOF), returning (bytes, eof)."""
    buf = b""
    deadline = time.monotonic() + timeout
    while True:
        if marker is not None and marker.encode("utf-8") in buf:
            return buf, False
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return buf, False
        r, _, _ = select.select([fd], [], [], remaining)
        if not r:
            return buf, False
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            return buf, True
        if not chunk:
            return buf, True
        buf += chunk


def combine(payload, left, right):
    rc = right["rc"]
    timeout = right.get("timeout", 4)
    markers = right.get("markers", [])
    steps = payload["steps"]

    # Fresh temp dir as HOME for this session.
    home = tempfile.mkdtemp(prefix="c031_")
    os.chmod(home, 0o700)
    hushlogin = os.path.join(home, ".hushlogin")
    with open(hushlogin, "w", encoding="utf-8") as fh:
        fh.write("")

    rcfile = os.path.join(home, "rcfile")
    with open(rcfile, "w", encoding="utf-8") as fh:
        fh.write(rc)

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
            ["bash", "--noprofile", "--rcfile", rcfile, "-i"],
            env,
        )

    chunks = []
    closed = False
    try:
        # Initial read until first PROMPT>.
        initial, eof = _read_until(fd, "PROMPT> ", timeout)
        chunks.append(_normalize(initial).decode("utf-8", "replace"))
        if eof:
            closed = True
            return {"chunks": chunks, "closed": closed}

        for i, step in enumerate(steps):
            data = bytes.fromhex(left[i])
            os.write(fd, data)
            marker = markers[i] if i < len(markers) else None
            out, eof = _read_until(fd, marker, timeout)
            chunks.append(_normalize(out).decode("utf-8", "replace"))
            if eof:
                closed = True
                break
    finally:
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.waitpid(pid, 0)
        except (ChildProcessError, OSError):
            pass

    return {"chunks": chunks, "closed": closed}
