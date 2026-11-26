#!/bin/bash
# One store round (same body as work/autoloop.sh): public re-merge, import own outputs, submit if better.
# usage (from santa-2026): bash work/oneround.sh
export PATH=/usr/bin:/bin:/mingw64/bin:$PATH
PY=../../.venv/Scripts/python
export PYTHONIOENCODING=utf-8
unset PYTHONHOME PYTHONNOUSERSITE
. work/lock.sh
echo "== $(date -u +%m-%d\ %H:%M) oneround"
store_lock
$PY src/remerge.py --no-submit --no-recomb --store-only 2>&1 | grep -v "^  skip"
files=$(ls work/out_*lns.txt work/kaggle_out/*/out_*.txt 2>/dev/null)
$PY src/import_out.py $files | grep -v "gain 0;"
$PY src/submit_store.py remerge_own
store_unlock
echo "oneround done"
