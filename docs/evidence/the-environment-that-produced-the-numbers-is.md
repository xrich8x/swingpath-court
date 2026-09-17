# The environment that produced the numbers is written down (tools/freeze_env.py)

> Evidence for the `the-environment-that-produced-the-numbers-is` row in [docs/STATE.md](../STATE.md) (What has worked).
> Text preserved verbatim from SCOREBOARD.md at the 2026-08-26 split.

Review finding P2-2. `requirements*.txt` carry only `>=` bounds, so a fresh install resolves a different stack than every figure here was measured on. RECORDS rather than pins — hard-pinning this stack breaks fresh installs, and *what was it measured on* is the question that needed answering. **It immediately exposed something nobody had recorded: the two venvs that both produce published numbers are not the same stack.** `.venv` runs opencv **4.13.0.92** / torch 2.12.1+cpu / ultralytics 8.4.75; `.venv-train` runs opencv **5.0.0.93** / torch 2.11.0+cu128 / ultralytics 8.4.87 — an opencv MAJOR version apart, on top of the intended cpu/cuda split. So a `.venv` number and a `.venv-train` number differ by device AND by libraries, and no experiment here has ever separated the two. `--check` mode fails if the file drifts from the machine. | 2026-08-17
