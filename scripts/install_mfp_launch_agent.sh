#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
LOG_DIR="${HOME}/Library/Logs/FitnessHub"
LABEL="com.fitnesshub.mfp-sync"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/${LABEL}.plist"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python3}"
RUNNER_PATH="${REPO_ROOT}/scripts/run_mfp_sync.py"

mkdir -p "${LAUNCH_AGENTS_DIR}" "${LOG_DIR}"

cat > "${PLIST_PATH}" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
      <string>${PYTHON_BIN}</string>
      <string>${RUNNER_PATH}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${REPO_ROOT}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>1800</integer>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/mfp-sync.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/mfp-sync.error.log</string>
  </dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)" "${PLIST_PATH}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "${PLIST_PATH}"
launchctl enable "gui/$(id -u)/${LABEL}"

echo "Installed ${LABEL}"
echo "plist: ${PLIST_PATH}"
echo "stdout log: ${LOG_DIR}/mfp-sync.log"
echo "stderr log: ${LOG_DIR}/mfp-sync.error.log"
