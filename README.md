# vp hangs when the terminal doesn't answer DA1

Minimal reproduction for a vite-plus bug. Before it runs a command, `vp` asks the terminal for its colors. When `COLORTERM=truecolor` is set, it writes `OSC 10`, `OSC 4;4`, `OSC 4;5` and a `DA1` query (`ESC [ c`) to the terminal, then waits for the replies. If the terminal never answers `DA1`, `vp` waits forever: the command never starts and nothing is printed after the queries.

`probe.py` runs `vp run hello` inside a pseudo-terminal it controls, so it can decide which queries get an answer. It needs only Python 3 and a global `vp` on `PATH`. It runs no `install` step.

## Run it

```sh
python3 probe.py silent      # no answers: hangs, killed after 10s
python3 probe.py colors      # answers the color queries, not DA1: hangs
python3 probe.py responder   # answers the color queries and DA1: runs the task
python3 probe.py dumb        # TERM=dumb, so vp skips the query: runs the task
python3 probe.py devnull     # stdin is /dev/null: runs the task
```

Expected output with vp v1.8.0 on macOS:

```text
silent: HANG, no exit after 10s
  output so far: b'\x1b]10;?\x07\x1b]4;4;?\x07\x1b]4;5;?\x07\x1b[c'
colors: HANG, no exit after 10s
  output so far: b'\x1b]10;?\x07\x1b]4;4;?\x07\x1b]4;5;?\x07\x1b[c'
responder: exited 0 after 0.1s, task ran
dumb: exited 0 after 0.1s, task ran
devnull: exited 0 after 0.1s, task ran
```

A second argument changes the timeout, for example `python3 probe.py silent 30`.

## What it shows

- The hang depends only on the `DA1` reply. Answering the color queries alone does not end the wait, and answering `DA1` alone does.
- The wait has no working timeout: `silent` is still waiting when it is killed.
- `COLORTERM=truecolor` is what makes `vp` send the queries. Without it, `vp` prints the plain header and runs the task.

## Where this happens

Terminals embedded in desktop apps can set `COLORTERM=truecolor` without answering `DA1`. In one such terminal, every `vp run <task>` hangs before the task starts, and the only workarounds are `TERM=dumb` or redirecting stdin.
