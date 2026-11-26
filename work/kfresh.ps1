# Kaggle fresh-row polish manager (Aside, 11-19). Idempotent; run every ~2 h (by the Aside routine).
#  1. pull outputs of finished kernels (elf-calc-search-1..5, elf-calc-fresh-0..4) into work/kaggle_out/<slug>_<MMDD_HHMM>/
#     (work/autoloop.sh or work/oneround.sh imports them)
#  2. if fewer than 5 CPU kernels are running/queued and a fresh slug is free: export the best store to kaggle/inputs,
#     version the private dataset, and push elf-calc-fresh-K on the rows changed since the previous push (top-up rotating).
# State: kaggle/fresh_state/ (snap.txt = programs at last push, pulled.txt, rot.txt). Log: kaggle/fresh_state/kfresh.log
$root = 'C:\Users\shaur\Kaggle ML\competitions\santa-2026'
Set-Location $root
Remove-Item env:PYTHONHOME -EA 0; Remove-Item env:PYTHONNOUSERSITE -EA 0
$env:PYTHONIOENCODING = 'utf-8'
$K = 'C:\Users\shaur\Kaggle ML\.venv\Scripts\kaggle.exe'
$py = 'C:\Users\shaur\Kaggle ML\.venv\Scripts\python.exe'
$st = "$root\kaggle\fresh_state"; New-Item -ItemType Directory -Force $st | Out-Null
function Log($m) { $l = "$(Get-Date -Format 'MM-dd HH:mm') $m"; $l | Out-File "$st\kfresh.log" -Append; Write-Output $l }
$pulled = @{}; if (Test-Path "$st\pulled.txt") { Get-Content "$st\pulled.txt" | ForEach-Object { $pulled[$_] = 1 } }
$slugs = @('elf-calc-search-1','elf-calc-search-2','elf-calc-search-3','elf-calc-search-4','elf-calc-search-5',
           'elf-calc-fresh-0','elf-calc-fresh-1','elf-calc-fresh-2','elf-calc-fresh-3','elf-calc-fresh-4')
$busy = 0; $free = @()
foreach ($s in $slugs) {
    $o = (& $K kernels status "shauryanadagoudra/$s" 2>&1 | Select-Object -Last 1) -as [string]
    $pushTag = if (Test-Path "$st\pushed_$s.txt") { Get-Content "$st\pushed_$s.txt" } else { 'orig' }
    if ($o -match 'RUNNING|QUEUED') { $busy++; continue }
    if ($o -match 'COMPLETE|ERROR|CANCEL') {
        $key = "$s@$pushTag"
        if ($s -like 'elf-calc-fresh-*' -and -not $pulled[$key]) {
            $d = "work\kaggle_out\${s}_$((Get-Date).ToUniversalTime().ToString('MMdd_HHmm'))"
            New-Item -ItemType Directory -Force $d | Out-Null
            & $K kernels output "shauryanadagoudra/$s" -p $d 2>&1 | Out-Null
            $key | Out-File "$st\pulled.txt" -Append; $pulled[$key] = 1
            Log "pulled $s ($($o -replace '.*status ','')) -> $d : $((Get-ChildItem $d -Name) -join ' ')"
        }
        if ($s -like 'elf-calc-fresh-*') { $free += $s }
    } elseif ($s -like 'elf-calc-fresh-*' -and -not (Test-Path "$st\pushed_$s.txt")) { $free += $s }   # never pushed yet (404)
    elseif ($s -like 'elf-calc-fresh-*') { $busy++; Log "$s status unclear ('$o'): counted as busy" }
}
Log "kernels busy $busy, free fresh slugs: $($free -join ' ')"
if ($busy -ge 5 -or $free.Count -eq 0) { exit 0 }
# ---- export store and diff against the snapshot of the previous push ----
$t = 0; while (-not (New-Item -ItemType Directory work\store.lock -EA 0)) { Start-Sleep 20; $t++; if ($t -gt 90) { Log 'lock: taking over a stale lock'; break } }
try { & $py src\export.py kaggle\inputs | Out-Null } finally { Remove-Item work\store.lock -Recurse -Force -EA 0 }
$cur = "kaggle\inputs\programs.txt"
$old = @{}; if (Test-Path "$st\snap.txt") { Get-Content "$st\snap.txt" | ForEach-Object { $p = $_.Split(' ', 2); $old[$p[0]] = $p[1] } }
$changed = @(); Get-Content $cur | ForEach-Object { $p = $_.Split(' ', 2); if ($old[$p[0]] -ne $p[1]) { $changed += $p[0] } }
if (-not (Test-Path "$st\snap.txt")) { $changed = @() }   # first run: no baseline, use rotation only
$all = Get-Content kaggle\inputs\puzzles.txt | ForEach-Object { $_.Split(' ')[0] }
$rot = 0; if (Test-Path "$st\rot.txt") { $rot = [int](Get-Content "$st\rot.txt") }
$nk = [Math]::Min($free.Count, 5 - $busy)
$ids = [System.Collections.Generic.List[string]]::new(); $changed | ForEach-Object { $ids.Add($_) }
$want = [Math]::Max($ids.Count, 70 * $nk)
while ($ids.Count -lt $want) { $id = $all[$rot % $all.Count]; $rot++; if (-not $ids.Contains($id)) { $ids.Add($id) } }
$rot | Set-Content "$st\rot.txt"
$tUp = (Get-Date).ToUniversalTime().AddSeconds(-90)
Push-Location kaggle\inputs
& $K datasets version -p . -m "programs fresh $(Get-Date -Format 'MM-dd HH:mm')" 2>&1 | Select-Object -Last 1 | ForEach-Object { Log "dataset: $_" }
Pop-Location
$ready = $false
for ($w = 0; $w -lt 45 -and -not $ready; $w++) {
    Start-Sleep 20
    $stt = (& $K datasets status shauryanadagoudra/elf-calc-search-inputs 2>&1 | Select-Object -Last 1) -as [string]
    $row = & $K datasets list -m --csv 2>&1 | Select-String '^shauryanadagoudra/elf-calc-search-inputs,' | Select-Object -First 1
    $lu = if ($row) { [datetime]::Parse($row.Line.Split(',')[3]) } else { [datetime]::MinValue }
    if ($stt.Trim() -eq 'ready' -and $lu -ge $tUp) { $ready = $true }
}
if (-not $ready) { Log 'dataset new version not reported ready after 15 min: not pushing kernels this round'; exit 0 }
Log "dataset version ready (lastUpdated >= $($tUp.ToString('HH:mm:ss')) UTC)"
$pushedAny = $false
# ---- split ids over nk kernels and push ----
for ($q = 0; $q -lt $nk; $q++) {
    $s = $free[$q]; $part = @(); for ($i = $q; $i -lt $ids.Count; $i += $nk) { $part += $ids[$i] }
    $dir = "kaggle\$s"; New-Item -ItemType Directory -Force $dir | Out-Null
    $seed = Get-Random -Minimum 1000 -Maximum 99999
    $cut = if ($q % 2 -eq 1) { 'CUTPROB="25", WMAX="5", ' } else { '' }
    $run = @"
# Elf calculator: local search over the rows that changed most recently (fresh public merges), $($part.Count) rows.
import glob, os, subprocess, time
src = glob.glob("/kaggle/input/**/lns.cpp", recursive=True)[0]
base = os.path.dirname(src)
W = "/kaggle/working"
subprocess.run(["g++", "-O3", "-march=native", "-std=c++17", "-pthread", "-o", W + "/lns", src], check=True)
IDS = set("$($part -join ' ')".split())
mine = [l for l in open(base + "/puzzles.txt").read().splitlines() if l.split()[0] in IDS]
open(W + "/p.txt", "w").write(chr(10).join(mine) + chr(10))
th = os.cpu_count() or 4
sec = min(1200.0, 10.5 * 3600 * th / max(1, len(mine)))
print("puzzles", len(mine), "threads", th, "sec", round(sec), flush=True)
t0 = time.time()
r = subprocess.run([W + "/lns", W + "/p.txt", base + "/programs.txt", W + "/out_fresh_lns.txt", f"{sec:.0f}", str(th), "$seed"],
                   env=dict(os.environ, BEAMW="10", $cut))
print("exit", r.returncode, "hours", round((time.time() - t0) / 3600, 2), flush=True)
"@
    $run | Set-Content "$dir\run.py" -Encoding utf8
    $meta = @{ id = "shauryanadagoudra/$s"; title = ($s -replace '-', ' '); code_file = 'run.py'; language = 'python'; kernel_type = 'script';
               is_private = $true; enable_gpu = $false; enable_tpu = $false; enable_internet = $false;
               dataset_sources = @('shauryanadagoudra/elf-calc-search-inputs'); competition_sources = @(); kernel_sources = @(); model_sources = @() }
    $meta | ConvertTo-Json | Set-Content "$dir\kernel-metadata.json" -Encoding utf8
    $o = & $K kernels push -p $dir 2>&1 | Select-Object -Last 1
    if ($o -match 'successfully pushed') { $pushedAny = $true; $tag = Get-Date -Format 'MMddHHmm'; $tag | Set-Content "$st\pushed_$s.txt" }
    Log "pushed ${s}: $($part.Count) rows (changed $($changed.Count)), seed $seed $cut -> $o"
}
if ($pushedAny) { Copy-Item $cur "$st\snap.txt" -Force } else { Log 'no kernel pushed: snapshot not advanced' }
