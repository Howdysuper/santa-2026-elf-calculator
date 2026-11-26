#!/bin/bash
# Pull each listed kernel's outputs to work/kaggle_out/<slug>_<MMDD_HHMM> when it finishes (work/autoloop.sh imports them).
# usage (from santa-2026): bash kaggle/watch_pull.sh SLUG [SLUG ...]
K=../../.venv/Scripts/kaggle
export PYTHONIOENCODING=utf-8
declare -A DONE; left=$#
while [ $left -gt 0 ]; do
  for slug in "$@"; do
    [ -n "${DONE[$slug]}" ] && continue
    s=$($K kernels status shauryanadagoudra/$slug 2>&1 | tail -1)
    if echo "$s" | grep -qE "COMPLETE|ERROR|CANCEL"; then
      DONE[$slug]=1; left=$((left-1))
      d=work/kaggle_out/${slug}_$(date -u +%m%d_%H%M); mkdir -p $d
      $K kernels output shauryanadagoudra/$slug -p $d >/dev/null 2>&1
      echo "$(date -u +%H:%M) $slug finished ($s); pulled to $d: $(ls $d | tr '\n' ' ')"
    fi
  done
  [ $left -gt 0 ] && sleep 600
done
echo "all pulled"
