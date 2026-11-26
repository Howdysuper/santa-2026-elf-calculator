#!/bin/bash
# Every 2.5 h: import our own solver outputs (local LNS runs and pulled Kaggle outputs) into the best store, then submit the store
# if it beats the last submitted total (src/submit_store.py replays every program while writing). Own gains only: no public pulls.
# usage (from santa-2026): bash work/autosubmit.sh ROUNDS
PY=../../.venv/Scripts/python
export PYTHONIOENCODING=utf-8
for r in $(seq 1 ${1:-4}); do
  sleep 9000
  files=$(ls work/out_changed_lns.txt work/out_unchanged_lns.txt work/kaggle_out/*/out_*.txt 2>/dev/null)
  echo "== $(date -u +%H:%M) round $r"
  $PY src/import_out.py $files | grep -v "gain 0;"
  $PY src/submit_store.py own_search
done
echo "autosubmit done"
