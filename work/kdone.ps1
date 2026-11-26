# Search-batch finisher (Aside, 11-19). Idempotent; run every 30 min by an Aside routine.
# Waits until ALL of elf-calc-search-1..5 have finished, then once:
#   1. pulls every kernel's outputs into work/kaggle_out/<slug>_final_<MMDD_HHMM>/
#   2. compares every output program per ID against the best store (prints how many rows are strictly shorter)
#   3. imports them under the store lock (src/import_out.py: replay-validates, keeps only strictly shorter programs)
#   4. writes + submits the store if its total beats work/last_submitted.txt (src/submit_store.py)
#   5. refills the freed CPU slots with fresh-row polish kernels (work/kfresh.ps1)
# Marker: kaggle/fresh_state/search_batch_done.txt. Log: kaggle/fresh_state/kdone.log
$root = 'C:\Users\shaur\Kaggle ML\competitions\santa-2026'
Set-Location $root
Remove-Item env:PYTHONHOME -EA 0; Remove-Item env:PYTHONNOUSERSITE -EA 0
$env:PYTHONIOENCODING = 'utf-8'
$K = 'C:\Users\shaur\Kaggle ML\.venv\Scripts\kaggle.exe'
$py = 'C:\Users\shaur\Kaggle ML\.venv\Scripts\python.exe'
$st = "$root\kaggle\fresh_state"; New-Item -ItemType Directory -Force $st | Out-Null
function Log($m) { $l = "$(Get-Date -Format 'MM-dd HH:mm') $m"; $l | Out-File "$st\kdone.log" -Append; Write-Output $l }
if (Test-Path "$st\search_batch_done.txt") { Log "ALREADY DONE: $(Get-Content "$st\search_batch_done.txt")"; exit 0 }
$slugs = 1..5 | ForEach-Object { "elf-calc-search-$_" }
$stat = @{}; $waiting = @()
foreach ($s in $slugs) {
    $o = ((& $K kernels status "shauryanadagoudra/$s" 2>&1 | Select-Object -Last 1) -as [string]) -replace '.*KernelWorkerStatus\.', '' -replace '"', ''
    $stat[$s] = $o
    if ($o -notmatch 'COMPLETE|ERROR|CANCEL') { $waiting += "$s=$o" }
}
if ($waiting.Count) { Log "WAITING: $($waiting -join ' ') | done: $(($slugs | Where-Object { $stat[$_] -match 'COMPLETE|ERROR|CANCEL' }) -join ' ')"; exit 0 }
Log "ALL 5 FINISHED: $(($slugs | ForEach-Object { "$_=$($stat[$_])" }) -join ' ')"
# 1. pull
$files = @()
foreach ($s in $slugs) {
    # single downloader: reuse the folder kaggle/watch_pull.sh already made; download only if none exists
    $have = Get-ChildItem work\kaggle_out -Directory -Filter "${s}_*" | Where-Object { Get-ChildItem $_.FullName -Filter 'out_*.txt' -Recurse } | Sort-Object Name | Select-Object -Last 1
    if ($have) { $d = $have.FullName; Log "using existing download $($have.Name)" }
    else {
        $d = "work\kaggle_out\${s}_$((Get-Date).ToUniversalTime().ToString('MMdd_HHmm'))"
        New-Item -ItemType Directory -Force $d | Out-Null
        & $K kernels output "shauryanadagoudra/$s" -p $d 2>&1 | Out-Null
        Log "pulled $s -> $d : $((Get-ChildItem $d -Name -Recurse) -join ' ')"
    }
    $files += Get-ChildItem $d -Filter 'out_*.txt' -Recurse | ForEach-Object { $_.FullName }
}
if (-not $files) { Log "no out_*.txt files found in kernel outputs"; }
# 2. compare
$cmp = @'
import sys, json
sys.path.insert(0, 'src')
from elf import load, best_len, replay
P = load(); better = 0; gain = 0; invalid = 0; rows = 0; ids = set()
for fn in sys.argv[1:]:
    for line in open(fn):
        x = line.split()
        if not x or x[0] not in P: continue
        n = int(x[1]); prog = [[x[2+4*k], int(x[3+4*k]), int(x[4+4*k]), int(x[5+4*k])] for k in range(n)]
        rows += 1
        try: replay(P[x[0]], prog)
        except ValueError: invalid += 1; continue
        b = best_len(x[0])
        if n < b: better += 1; gain += b - n; ids.add(x[0])
print(f"compare: {rows} rows read, {invalid} invalid, {better} strictly shorter than the store on {len(ids)} ids, total gain {gain}")
'@
$cmp | Set-Content "$st\cmp.py" -Encoding utf8
if ($files) { Log (& $py -I "$st\cmp.py" @files 2>&1 | Select-Object -Last 1) }
# 3. import under the store lock
$t = 0; while (-not (New-Item -ItemType Directory work\store.lock -EA 0)) { Start-Sleep 20; $t++; if ($t -gt 90) { Log 'lock: taking over stale lock'; break } }
try {
    if ($files) { & $py src\import_out.py @files 2>&1 | ForEach-Object { Log "import: $_" } }
    # 4. submit if better
    & $py src\submit_store.py kaggle_search_batch 2>&1 | ForEach-Object { Log "submit: $_" }
} finally { Remove-Item work\store.lock -Recurse -Force -EA 0 }
Log "last_submitted now: $(Get-Content work\last_submitted.txt)"
# 5. refill CPU slots: CP-SAT structure recombination first, then fresh-row polish
& pwsh -NoProfile -File work\kcpsat.ps1 2>&1 | ForEach-Object { Log "kcpsat: $_" }
& pwsh -NoProfile -File work\kfresh.ps1 2>&1 | ForEach-Object { Log "kfresh: $_" }
"done $(Get-Date -Format 'MM-dd HH:mm'); last_submitted $(Get-Content work\last_submitted.txt)" | Set-Content "$st\search_batch_done.txt"
Log 'BATCH COMPLETE'
