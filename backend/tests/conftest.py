"""Make the `swingvision` package importable when pytest is run from anywhere
(e.g. `python -m pytest tests/` inside backend/, or from the repo root).

tools/ goes on the path too. The measurement scripts there decide what every
number in this project means — the gold-frame parity guard and the HUD matcher
have each already been wrong in a way that silently changed a published figure —
so they are testable code, not scratch scripts."""

import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

TOOLS_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)
