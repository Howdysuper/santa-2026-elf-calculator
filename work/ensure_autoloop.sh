#!/bin/bash
# Check-then-start for the merge loop (replaces the removed supervisor.ps1 / chain_autoloop.ps1).
#   bash work/ensure_autoloop.sh          start work/autoloop.sh 120 7200 now, only if no autoloop.sh is running
#   bash work/ensure_autoloop.sh --wait   wait (polling every 2 min) until the running loop ends, then start a new one
# Run it from santa-2026 in a shell whose processes survive (Claude Code / your own terminal), e.g.
#   nohup bash work/ensure_autoloop.sh --wait > work/ensure_autoloop.log 2>&1 &
# Never more than one loop: the check is repeated right before starting, and every store write also holds work/store.lock.
export PATH=/usr/bin:/bin:/mingw64/bin:$PATH
count() { powershell.exe -NoProfile -Command "@(Get-CimInstance Win32_Process | Where-Object { \$_.Name -eq 'bash.exe' -and \$_.CommandLine -match 'autoloop\.sh' -and \$_.CommandLine -notmatch 'ensure_autoloop' }).Count" | tr -d '\r'; }
if [ "$1" = "--wait" ]; then
  while [ "$(count)" != "0" ]; do sleep 120; done
  echo "$(date -u +%m-%d\ %H:%M) old loop ended"
fi
if [ "$(count)" != "0" ]; then echo "$(date -u +%m-%d\ %H:%M) a loop is already running: not starting another"; exit 0; fi
echo "$(date -u +%m-%d\ %H:%M) starting work/autoloop.sh 120 7200"
exec bash work/autoloop.sh 120 7200
