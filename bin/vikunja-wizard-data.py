#!/usr/bin/env python3
"""
vikunja-wizard-data.py — fetch live data for the vikunja-wizard skill.

Usage:
  vikunja-wizard-data.py projects          # list all projects (JSON)
  vikunja-wizard-data.py users <search>    # search users (JSON)
  vikunja-wizard-data.py labels            # list all labels (JSON)
  vikunja-wizard-data.py teams             # list all teams (JSON)
  vikunja-wizard-data.py full              # projects + teams + labels (JSON)

Requires:
  - An unlocked Bitwarden session (for API token resolution via mcp-run.sh)
  - Or VIKUNJA_BMS_TOKEN set in the environment

Outputs JSON for machine consumption; the wizard skill reads this and
presents formatted output to the human.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
TENANTS_FILE = REPO_ROOT / "tenants-vikunja.local.json"

def resolve_token():
    """Get the BMS tenant API token, either from env or via mcp-run.sh."""
    if os.environ.get("VIKUNJA_BMS_TOKEN"):
        return os.environ["VIKUNJA_BMS_TOKEN"]

    # Try to resolve via mcp-run.sh
    try:
        env_script = subprocess.run(
            ["bash", str(REPO_ROOT / "mcp-run.sh"), "vikunja", "--print-env"],
            capture_output=True, text=True, timeout=30
        )
        if env_script.returncode == 0:
            for line in env_script.stdout.strip().split("\n"):
                if line.startswith("VIKUNJA_BMS_TOKEN="):
                    return line.split("=", 1)[1]
    except Exception:
        pass

    print(json.dumps({"error": "No VIKUNJA_BMS_TOKEN set and mcp-run.sh failed"}))
    sys.exit(1)

def load_tenants():
    if TENANTS_FILE.exists():
        return json.loads(TENANTS_FILE.read_text())
    return {}

def api_get(path, token):
    tenant = load_tenants().get("bms", {})
    base = tenant.get("base_url", "http://localhost:3456")
    url = f"{base.rstrip('/')}{path}"
    resp = __import__("requests").get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    resp.raise_for_status()
    return resp.json()

def cmd_projects():
    data = api_get("/api/v1/projects", resolve_token())
    out = []
    for p in data:
        out.append({
            "id": p.get("id"),
            "title": p.get("title"),
            "team_id": p.get("team_id"),
        })
    print(json.dumps(out, indent=2))

def cmd_users(search=""):
    token = resolve_token()
    path = f"/api/v1/users?s={search}" if search else "/api/v1/users"
    users = api_get(path, token)
    out = [{"username": u.get("username"), "display_name": u.get("display_name"), "id": u.get("id")} for u in users]
    print(json.dumps(out, indent=2))

def cmd_labels():
    labels = api_get("/api/v1/labels", resolve_token())
    out = [{"id": l.get("id"), "title": l.get("title", "").strip()} for l in labels]
    print(json.dumps(out, indent=2))

def cmd_teams():
    teams = api_get("/api/v1/teams", resolve_token())
    out = [{"id": t.get("id"), "name": t.get("name")} for t in teams]
    print(json.dumps(out, indent=2))

def cmd_full():
    token = resolve_token()
    out = {
        "projects": cmd_projects_json(token),
        "teams": cmd_teams_json(token),
        "labels": cmd_labels_json(token),
    }
    print(json.dumps(out, indent=2))

def cmd_projects_json(token):
    data = api_get("/api/v1/projects", token)
    return [{"id": p.get("id"), "title": p.get("title"), "team_id": p.get("team_id")} for p in data]

def cmd_teams_json(token):
    teams = api_get("/api/v1/teams", token)
    return [{"id": t.get("id"), "name": t.get("name")} for t in teams]

def cmd_labels_json(token):
    labels = api_get("/api/v1/labels", token)
    return [{"id": l.get("id"), "title": l.get("title", "").strip()} for l in labels]

def parse_relative_date(text):
    """Convert relative date text to ISO8601 timestamp."""
    now = datetime.utcnow()
    text = text.lower().strip()

    # "in X days/weeks/months"
    for unit, days in [("day", 1), ("week", 7), ("month", 30), ("year", 365)]:
        if unit in text:
            try:
                num = int(re.search(r'(\d+)', text).group(1))
                delta = timedelta(days=num * days)
                return (now + delta).strftime("%Y-%m-%dT00:00:00Z")
            except (AttributeError, ValueError):
                pass

    # "next <day>" — simple approximation
    days = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6}
    for day, target in days.items():
        if day in text:
            today = now.weekday()
            delta = (target - today) % 7
            if delta == 0:
                delta = 7  # next week if today matches
            return (now + timedelta(days=delta)).strftime("%Y-%m-%dT00:00:00Z")

    # "tomorrow"
    if "tomorrow" in text:
        return (now + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

    return None

if __name__ == "__main__":
    import re

    cmd = sys.argv[1] if len(sys.argv) > 1 else "full"
    search = sys.argv[2] if len(sys.argv) > 2 else ""

    {"projects": cmd_projects, "users": cmd_users, "labels": cmd_labels,
     "teams": cmd_teams, "full": cmd_full}.get(cmd, lambda: print(f"Unknown command: {cmd}\nUsage: {sys.argv[0]} <projects|users|labels|teams|full>"))()
