#!/usr/bin/env python3
"""Resets the sandbox plugin state to the demo baseline before a recording. Usage: prep.py <tape>"""
import json
import sys
import time
from pathlib import Path

B = Path("/tmp/bs-demo")
STATE = B / "home/state/opencode/latest/tui/plugin.better-sessions.state.json"
plan = {item["title"]: item for item in json.loads((B / "plan.json").read_text())}
state = json.loads((B / "baseline-state.json").read_text())
now = int(time.time() * 1000)

backup = plan["Check the nightly backup job"]["id"]
# Baseline: wakes tomorrow afternoon.
state["sessions"][backup]["until"] = now + 23 * 3600 * 1000
if sys.argv[1:] == ["wake"]:
    # Ends a few seconds after launch; the plugin's first sweep (15 s after it starts) wakes it.
    state["sessions"][backup]["until"] = now + 8_000
STATE.write_text(json.dumps(state))
