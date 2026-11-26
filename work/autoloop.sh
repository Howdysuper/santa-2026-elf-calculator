#!/bin/bash
# Every INTERVAL seconds (default 2 h), for ROUNDS rounds (default 12), starting now:
#   1. pull public Santa 2026 notebook outputs and program datasets that changed since the last pull (src/remerge.py; parses CSV only,
#      every program replay-validated) into the best store, without recomb (it finds ~0 on the current frontier and takes 25 min);
#   2. import our own solver outputs (local LNS runs and pulled Kaggle outputs);
#   3. submit the store if it beats the last submitted total (src/submit_store.py replays every program while writing).
# Store writes hold work/store.lock (work/lock.sh), shared with kaggle/watch_big.sh. Santa allows 100 submissions a day.
# usage (from santa-2026): bash work/autoloop.sh [ROUNDS] [INTERVAL]
PY=../../.venv/Scripts/python
export PYTHONIOENCODING=utf-8
. work/lock.sh
for r in $(seq 1 ${1:-12}); do
  echo "== $(date -u +%m-%d\ %H:%M) round $r"
  store_lock
  $PY src/remerge.py --no-submit --no-recomb --store-only 2>&1 | grep -v "^  skip"
  files=$(ls work/out_*lns.txt work/kaggle_out/*/out_*.txt 2>/dev/null)
  $PY src/import_out.py $files | grep -v "gain 0;"
  $PY src/submit_store.py remerge_own
  store_unlock
  sleep ${2:-7200}
done
echo "autoloop done"
