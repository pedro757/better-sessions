#!/usr/bin/env python3
"""Builds the better-sessions demo inside the sandbox OpenCode (see env.sh). Never touches the real install."""
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

B = Path("/tmp/bs-demo")
PROJECT = str(B / "acme-web")
ENV = {
    **{k: v for k, v in os.environ.items() if k != "OPENCODE_CLI_CONFIG_CONTENT"},
    "XDG_CONFIG_HOME": str(B / "home/config"),
    "XDG_DATA_HOME": str(B / "home/data"),
    "XDG_STATE_HOME": str(B / "home/state"),
    "XDG_CACHE_HOME": str(B / "home/cache"),
}
DB = B / "home/data/opencode/opencode.db"
STATE = B / "home/state/opencode/latest/tui/plugin.better-sessions.state.json"
HOUR = 3600 * 1000
DAY = 24 * HOUR

QUESTION = {
    "questions": [
        {
            "question": "Which charting library should the dashboard use?",
            "header": "Charting library",
            "options": [
                {"label": "Recharts", "description": "React components, smallest change"},
                {"label": "ECharts", "description": "Fastest with large datasets"},
                {"label": "Chart.js", "description": "Canvas, already used on the marketing site"},
            ],
        }
    ]
}

# group: active (recent), settled (explicitly settled), auto (settled by 7 days of inactivity), snoozed.
PLAN = [
    # Backdated first.
    dict(group="settled", age=2.2 * HOUR, title="Bump dependencies to the latest minor versions"),
    dict(group="settled", age=3.1 * HOUR, title="Add OpenGraph images to blog posts"),
    dict(group="settled", age=1 * DAY + 2 * HOUR, title="Investigate slow dashboard queries"),
    dict(group="settled", age=1 * DAY + 5 * HOUR, title="Set up Playwright smoke tests"),
    dict(group="settled", age=2 * DAY + 1 * HOUR, title="Refactor the auth middleware"),
    dict(group="settled", age=3 * DAY + 3 * HOUR, title="Write a migration for user preferences"),
    dict(group="settled", age=3 * DAY + 6 * HOUR, title="Fix the timezone bug in invoices"),
    dict(group="settled", age=5 * DAY + 2 * HOUR, title="Add Sentry release tracking"),
    dict(group="auto", age=8 * DAY, title="Remove legacy feature flags"),
    dict(group="auto", age=9 * DAY + 4 * HOUR, title="Add pagination to the orders API"),
    dict(group="auto", age=12 * DAY, title="Translate the onboarding emails"),
    dict(group="auto", age=15 * DAY, title="Audit npm packages for vulnerabilities"),
    dict(group="auto", age=20 * DAY, title="Speed up the Docker builds"),
    dict(group="auto", age=26 * DAY, title="Create a public status page"),
    dict(group="auto", age=33 * DAY, title="Move product images to the CDN"),
    dict(group="snoozed", age=1 * DAY + 3 * HOUR, title="Upgrade to React 20 when it ships", snooze="monday"),
    dict(group="snoozed", age=6 * HOUR, title="Follow up on the Stripe webhook incident", snooze="tomorrow"),
    dict(group="snoozed", age=4 * HOUR, title="Review Lighthouse scores after the deploy", snooze=3 * HOUR),
    dict(group="snoozed", age=5 * HOUR, title="Check the nightly backup job", snooze=26 * HOUR),
    # Recent, in Active.
    dict(group="active", title="Try the new ESLint flat config"),
    dict(group="active", title="Explain how the caching layer works"),
    dict(group="active", title="Update the README install steps"),
    dict(group="active", title="Add dark mode to the settings page"),
    dict(group="active", kind="question", title="Pick a charting library for the dashboard"),
    dict(group="active", kind="permission", title="Fix the flaky login test in CI", command="pnpm vitest run auth --repeat 20"),
    dict(group="active", kind="background", title="Run the e2e suite against staging", command="sleep 7200"),
    dict(group="active", kind="slow", title="Migrate checkout to the new payments SDK"),
    dict(group="active", kind="slow", title="Add rate limiting to the public API"),
]


def prompt_of(item):
    return f"{item['title']}."


def api(*args, data=None):
    command = ["opencode", "api", *args]
    if data is not None:
        command += ["--data", json.dumps(data)]
    out = subprocess.run(command, env=ENV, capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise SystemExit(f"api {args} failed: {out.stderr or out.stdout}")
    return json.loads(out.stdout).get("data") if out.stdout.strip() else None


def write_scenarios():
    table = {}
    for item in PLAN:
        table[prompt_of(item)] = {
            "kind": item.get("kind", "quick"),
            "title": item["title"],
            "command": item.get("command"),
            "question_args": QUESTION,
            "reply": {
                "slow": "Reading the existing code paths first, then I'll make the change in small steps.",
                "background": "The e2e suite is running against staging in the background. I'll report back when it finishes.",
            }.get(item.get("kind", "quick"), "Done. The change is in place and the checks pass."),
        }
    # Follow-up message used by the "send a message" demo.
    table["Also add them to the docs pages"] = {"kind": "quick", "title": "Add OpenGraph images to blog posts", "reply": "Added them to the docs pages too."}
    (B / "mock/scenarios.json").write_text(json.dumps(table, indent=1))


def create(item):
    session = api("session.create", data={"location": {"directory": PROJECT}})
    api("session.prompt", "--param", f"sessionID={session['id']}", data={"text": prompt_of(item)})
    item["id"] = session["id"]
    return session["id"]


def wait_idle(ids, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        active = api("session.active") or {}
        if not any(i in active for i in ids):
            return
        time.sleep(1)
    raise SystemExit(f"sessions still busy: {[i for i in ids if i in (api('session.active') or {})]}")


def backdate(items):
    subprocess.run(["opencode", "service", "stop"], env=ENV, capture_output=True, timeout=60)
    time.sleep(2)
    now = int(time.time() * 1000)
    db = sqlite3.connect(DB)
    for item in items:
        row = db.execute("select time_updated from session_v2 where id = ?", (item["id"],)).fetchone()
        delta = row[0] - (now - int(item["age"]))
        item["updated"] = row[0] - delta
        for column in ("time_created", "time_updated", "time_busy", "time_idle", "time_viewed"):
            db.execute(f"update session_v2 set {column} = {column} - ? where id = ? and {column} is not null", (delta, item["id"]))
        for table in ("session_message", "session_part"):
            db.execute(f"update {table} set time_created = time_created - ?, time_updated = time_updated - ? where session_id = ?", (delta, delta, item["id"]))
    db.commit()
    db.close()


def wake_at(spec, now):
    t = time.localtime(now / 1000)
    if spec == "tomorrow":
        return int(time.mktime((t.tm_year, t.tm_mon, t.tm_mday + 1, 9, 0, 0, 0, 0, -1)) * 1000)
    if spec == "monday":
        days = (7 - t.tm_wday) % 7 or 7
        return int(time.mktime((t.tm_year, t.tm_mon, t.tm_mday + days, 9, 0, 0, 0, 0, -1)) * 1000)
    return now + int(spec)


def write_state():
    now = int(time.time() * 1000)
    sessions = {}
    for item in PLAN:
        if item["group"] == "settled":
            sessions[item["id"]] = {"state": "settled", "at": item["updated"] + 60_000}
        if item["group"] == "snoozed":
            sessions[item["id"]] = {"state": "snoozed", "at": item["updated"] + 60_000, "until": wake_at(item["snooze"], now)}
    state = {"version": 1, "sessions": sessions, "pins": [], "seeded": True}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state))
    (B / "baseline-state.json").write_text(json.dumps(state))
    (B / "plan.json").write_text(json.dumps(PLAN, indent=1))


def main():
    write_scenarios()
    old = [item for item in PLAN if "age" in item]
    ids = [create(item) for item in old]
    wait_idle(ids)
    backdate(old)
    recent = [item for item in PLAN if "age" not in item]
    for item in recent:
        create(item)
        time.sleep(1.2)
    time.sleep(5)
    write_state()
    print(json.dumps({item["title"]: item["id"] for item in PLAN}, indent=1))


if __name__ == "__main__":
    main()
