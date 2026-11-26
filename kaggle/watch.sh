#!/bin/bash
# Watch the running Kaggle kernels; when one finishes, pull its output and push the next search kernel into the freed slot.
# usage: bash kaggle/watch.sh   (from the santa-2026 folder)
K="../../.venv/Scripts/kaggle"
export PYTHONIOENCODING=utf-8
declare -A NEXT=( [elf-calc-replan-0]=lns_1 [elf-calc-replan-1]=lns_2 [elf-calc-replan-2]=lns_3 [elf-calc-replan-3]=lns_q0 [elf-calc-search-0]= )
declare -A OUT=( [elf-calc-replan-0]=replan_0 [elf-calc-replan-1]=replan_1 [elf-calc-replan-2]=replan_2 [elf-calc-replan-3]=replan_3 [elf-calc-search-0]=search0_b )
left=${#NEXT[@]}
declare -A DONE
while [ $left -gt 0 ]; do
  for slug in "${!NEXT[@]}"; do
    [ -n "${DONE[$slug]}" ] && continue
    s=$($K kernels status shauryanadagoudra/$slug 2>&1 | tail -1)
    if echo "$s" | grep -qE "COMPLETE|ERROR|CANCEL"; then
      DONE[$slug]=1; left=$((left-1))
      d=work/kaggle_out/${OUT[$slug]}; mkdir -p $d
      $K kernels output shauryanadagoudra/$slug -p $d >/dev/null 2>&1
      echo "$(date -u +%H:%M) $slug finished ($s); pulled to $d: $(ls $d | tr '\n' ' ')"
      n=${NEXT[$slug]}
      if [ -n "$n" ]; then echo "$(date -u +%H:%M) push $n: $($K kernels push -p kaggle/$n 2>&1 | tail -1)"; fi
    fi
  done
  [ $left -gt 0 ] && sleep 300
done
echo "all handled"
