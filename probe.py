"""Run `vp run hello` in a pseudo-terminal and report whether it finishes.

Modes:
  silent     the terminal never answers queries (the bug)
  responder  the terminal answers the color queries and DA1, like most terminals do
  colors     the terminal answers the color queries but not DA1
  da1        the terminal answers DA1 but not the color queries
  dumb       TERM=dumb, so vp skips the query
  devnull    stdin is /dev/null instead of the terminal

Usage: python3 probe.py [silent|responder|colors|da1|dumb|devnull] [timeout-seconds]
"""

import os
import pty
import re
import select
import signal
import sys
import time

MODE = sys.argv[1] if len(sys.argv) > 1 else "silent"
TIMEOUT = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0

# Queries vp writes to the terminal, and replies a typical terminal sends back.
OSC_QUERY = re.compile(rb"\x1b\](10|11|4;\d+);\?(\x07|\x1b\\)")
DA1_QUERY = re.compile(rb"\x1b\[0?c")


def reply(query: bytes) -> bytes:
    out = b""
    if MODE != "da1":
        for match in OSC_QUERY.finditer(query):
            out += b"\x1b]" + match.group(1) + b";rgb:8080/8080/8080\x1b\\"
    if MODE in ("responder", "da1") and DA1_QUERY.search(query):
        out += b"\x1b[?62;22c"
    return out


def main() -> int:
    # vp only queries terminal colors when COLORTERM says the terminal is truecolor.
    env = dict(
        os.environ,
        TERM="dumb" if MODE == "dumb" else "xterm-256color",
        COLORTERM="truecolor",
    )
    # VP_BIN points the probe at another vp binary, such as a local debug build.
    command = [os.environ.get("VP_BIN", "vp"), "run", "hello"]

    pid, fd = pty.fork()
    if pid == 0:
        if MODE == "devnull":
            devnull = os.open(os.devnull, os.O_RDONLY)
            os.dup2(devnull, 0)
        os.execvpe(command[0], command, env)

    output = b""
    deadline = time.monotonic() + TIMEOUT
    status = None
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if ready:
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                chunk = b""
            output += chunk
            if MODE in ("responder", "colors", "da1") and chunk:
                answer = reply(chunk)
                if answer:
                    os.write(fd, answer)
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            break
        status = None

    elapsed = TIMEOUT - max(0.0, deadline - time.monotonic())
    if status is None:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        print(f"{MODE}: HANG, no exit after {TIMEOUT:.0f}s")
        print(f"  output so far: {output!r}")
        return 1

    task_ran = b"hello from the task" in output
    print(
        f"{MODE}: exited {os.waitstatus_to_exitcode(status)} after {elapsed:.1f}s,"
        f" task {'ran' if task_ran else 'did NOT run'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
