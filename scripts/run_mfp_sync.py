from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"
DEFAULT_TIMEZONE = "America/Indiana/Indianapolis"


def env_default(key: str, fallback: str | None = None) -> str | None:
    value = os.getenv(key)
    if value is not None:
        return value
    if ENV_PATH.exists():
        for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            env_key, env_value = line.split("=", 1)
            if env_key.strip() == key:
                return env_value.strip().strip('"').strip("'")
    return fallback


def in_sync_window(now: datetime) -> bool:
    if now.hour < 8:
        return False
    if now.hour > 23:
        return False
    if now.hour == 23 and now.minute > 30:
        return False
    return True


def main() -> int:
    timezone_name = env_default("CANONICAL_TIMEZONE", DEFAULT_TIMEZONE) or DEFAULT_TIMEZONE
    now = datetime.now(ZoneInfo(timezone_name))
    if not in_sync_window(now):
        print(f"[{now.isoformat()}] Skipping MyFitnessPal sync outside the 8:00 AM-11:30 PM window.")
        return 0

    python_bin = env_default("MFP_SYNC_PYTHON", str(REPO_ROOT / ".venv/bin/python3")) or sys.executable
    bridge_script = REPO_ROOT / "scripts" / "mfp_bridge.py"
    sync_window_days = env_default("MFP_SYNC_WINDOW_DAYS", "3") or "3"

    command = [python_bin, str(bridge_script), "--days", sync_window_days]
    browser = env_default("MFP_BROWSER")
    if browser:
        command.extend(["--browser", browser])

    print(f"[{now.isoformat()}] Running MyFitnessPal sync with a {sync_window_days}-day refresh window.")
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
