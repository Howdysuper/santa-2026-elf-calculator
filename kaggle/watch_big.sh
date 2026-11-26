#!/bin/bash
# Chain many-core search sessions: when elf-calc-search-big finishes, pull its outputs to work/kaggle_out/big_N (work/autoloop.sh
# imports them), refresh the input dataset from the best store, and push the kernel again on a TPU machine. NEXT = sessions to chain.
# usage (from santa-2026): bash kaggle/watch_big.sh NEXT
K=../../.venv/Scripts/kaggle; PY=../../.venv/Scripts/python
export PYTHONIOENCODING=utf-8
. work/lock.sh
slug=shauryanadagoudra/elf-calc-search-big
for n in $(seq 1 ${1:-1}); do
  until $K kernels status $slug 2>&1 | tail -1 | grep -qE "COMPLETE|ERROR|CANCEL"; do sleep 600; done
  d=work/kaggle_out/big_$(date -u +%m%d_%H%M); mkdir -p $d
  $K kernels output $slug -p $d >/dev/null 2>&1
  echo "$(date -u "+%m-%d %H:%M") session done ($($K kernels status $slug 2>&1 | tail -1)); pulled to $d: $(ls $d | tr '\n' ' ')"
  store_lock; $PY src/import_out.py $d/out_*.txt | tail -1
  $PY src/export.py kaggle/inputs; store_unlock
  (cd kaggle/inputs && ../../$K datasets version -p . -m "programs refresh" 2>&1 | tail -1)
  sleep 600
  echo "$(date -u +%H:%M) push: $($K kernels push -p kaggle/lns_big --accelerator TpuV5E8 2>&1 | tail -1)"
  sleep 300
done
until $K kernels status $slug 2>&1 | tail -1 | grep -qE "COMPLETE|ERROR|CANCEL"; do sleep 600; done
d=work/kaggle_out/big_$(date -u +%m%d_%H%M); mkdir -p $d; $K kernels output $slug -p $d >/dev/null 2>&1
echo "$(date -u "+%m-%d %H:%M") last session done; pulled to $d"
