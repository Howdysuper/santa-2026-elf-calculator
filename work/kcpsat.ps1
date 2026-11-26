# Kaggle CP-SAT structure-recombination manager (Aside, 11-19). Idempotent; run hourly (routine) and by kdone.ps1.
#  1. pulls finished elf-calc-cpsat-K outputs into work/kaggle_out/<slug>_<MMDD_HHMM>/ (only downloader for these slugs)
#  2. if a batch CPU slot is free and a cpsat slug is free: refresh the private dataset elf-calc-cpsat-inputs
#     (store export under the lock, public variants, hubs, ids), wait until Kaggle reports it ready, push elf-calc-cpsat-K.
# Log: kaggle/fresh_state/kcpsat.log
$root = 'C:\Users\shaur\Kaggle ML\competitions\santa-2026'
Set-Location $root
Remove-Item env:PYTHONHOME -EA 0; Remove-Item env:PYTHONNOUSERSITE -EA 0
$env:PYTHONIOENCODING = 'utf-8'
$K = 'C:\Users\shaur\Kaggle ML\.venv\Scripts\kaggle.exe'
$py = 'C:\Users\shaur\Kaggle ML\.venv\Scripts\python.exe'
$st = "$root\kaggle\fresh_state"; New-Item -ItemType Directory -Force $st | Out-Null
function Log($m) { $l = "$(Get-Date -Format 'MM-dd HH:mm') $m"; $l | Out-File "$st\kcpsat.log" -Append; Write-Output $l }
$NPARTS = 2
$all = @(1..5 | ForEach-Object { "elf-calc-search-$_" }) + @(0..4 | ForEach-Object { "elf-calc-fresh-$_" }) + @(0..($NPARTS - 1) | ForEach-Object { "elf-calc-cpsat-$_" })
$busy = 0; $free = @()
foreach ($s in $all) {
    $o = (& $K kernels status "shauryanadagoudra/$s" 2>&1 | Select-Object -Last 1) -as [string]
    $pushed = Test-Path "$st\pushed_$s.txt"
    if ($o -match 'RUNNING|QUEUED') { $busy++; continue }
    if ($s -notlike 'elf-calc-cpsat-*') { if ($pushed -and $o -notmatch 'COMPLETE|ERROR|CANCEL|404|not found') { $busy++ }; continue }
    if ($o -match 'COMPLETE|ERROR|CANCEL') {
        $tag = Get-Content "$st\pushed_$s.txt" -EA 0; $key = "$s@$tag"
        $done = (Test-Path "$st\pulled.txt") -and (Select-String -Path "$st\pulled.txt" -SimpleMatch $key -Quiet)
        if (-not $done) {
            $d = "work\kaggle_out\${s}_$((Get-Date).ToUniversalTime().ToString('MMdd_HHmm'))"; New-Item -ItemType Directory -Force $d | Out-Null
            & $K kernels output "shauryanadagoudra/$s" -p $d 2>&1 | Out-Null
            $key | Out-File "$st\pulled.txt" -Append
            Log "pulled $s -> $d : $((Get-ChildItem $d -Name) -join ' ')"
        }
        $free += $s
    } elseif (-not $pushed) { $free += $s }
    else { $busy++; Log "$s status unclear ('$o'): counted as busy" }
}
Log "batch CPU busy $busy, free cpsat slugs: $($free -join ' ')"
if (Test-Path "$st\cpsat_nopush.txt") { Log 'pushes paused (kaggle/fresh_state/cpsat_nopush.txt): pull only'; exit 0 }
if ($busy -ge 5 -or $free.Count -eq 0) { exit 0 }
# ---- refresh dataset ----
$dd = "$root\kaggle\cpsat_inputs"; New-Item -ItemType Directory -Force $dd | Out-Null
Copy-Item src\cpsat_recomb.py, src\elf.py, data\puzzles.csv, work\hubs_all.txt, work\var_all.json $dd -Force
$t = 0; while (-not (New-Item -ItemType Directory work\store.lock -EA 0)) { Start-Sleep 20; $t++; if ($t -gt 90) { Log 'lock: taking over a stale lock'; break } }
try { & $py src\export.py work\cpsat_export | Out-Null } finally { Remove-Item work\store.lock -Recurse -Force -EA 0 }
Copy-Item work\cpsat_export\programs.txt $dd -Force
# ids: structured families first (shared, multiplicative, mixed), each ordered by instructions per target (costliest first)
$fam = Import-Csv research\generator\scored_family.csv
$ord = @()
foreach ($f in 'shared', 'multiplicative', 'mixed') { $ord += $fam | Where-Object { $_.family -eq $f } | Sort-Object { - [double]$_.per_target } | ForEach-Object { $_.id } }
$ord | Set-Content "$dd\cpsat_ids.txt"
if (-not (Test-Path "$dd\dataset-metadata.json")) {
    '{"title": "elf-calc-cpsat-inputs", "id": "shauryanadagoudra/elf-calc-cpsat-inputs", "licenses": [{"name": "CC0-1.0"}], "isPrivate": true}' | Set-Content "$dd\dataset-metadata.json"
}
$tUp = (Get-Date).ToUniversalTime().AddSeconds(-90)
$exists = (& $K datasets list -m --csv 2>&1 | Select-String '^shauryanadagoudra/elf-calc-cpsat-inputs,') -ne $null
Push-Location $dd
if ($exists) { $o = & $K datasets version -p . -r zip -m "cpsat inputs $(Get-Date -Format 'MM-dd HH:mm')" 2>&1 | Select-Object -Last 1 }
else { $o = & $K datasets create -p . -r zip 2>&1 | Select-Object -Last 1 }
Pop-Location
Log "dataset: $o"
$ready = $false
for ($w = 0; $w -lt 45 -and -not $ready; $w++) {
    Start-Sleep 20
    $stt = (& $K datasets status shauryanadagoudra/elf-calc-cpsat-inputs 2>&1 | Select-Object -Last 1) -as [string]
    $row = & $K datasets list -m --csv 2>&1 | Select-String '^shauryanadagoudra/elf-calc-cpsat-inputs,' | Select-Object -First 1
    $lu = if ($row) { [datetime]::Parse($row.Line.Split(',')[3]) } else { [datetime]::MinValue }
    if ($stt.Trim() -eq 'ready' -and $lu -ge $tUp) { $ready = $true }
}
if (-not $ready) { Log 'cpsat dataset not reported ready after 15 min: not pushing'; exit 0 }
$nk = [Math]::Min($free.Count, 5 - $busy)
for ($q = 0; $q -lt $nk; $q++) {
    $s = $free[$q]; $part = [int]($s.Split('-')[-1])
    $dir = "kaggle\$s"; New-Item -ItemType Directory -Force $dir | Out-Null
    (Get-Content kaggle\cpsat_run.py -Raw).Replace('__PART__', "$part").Replace('__NPARTS__', "$NPARTS") | Set-Content "$dir\run.py" -Encoding utf8
    $meta = @{ id = "shauryanadagoudra/$s"; title = ($s -replace '-', ' '); code_file = 'run.py'; language = 'python'; kernel_type = 'script';
               is_private = $true; enable_gpu = $false; enable_tpu = $false; enable_internet = $false;
               dataset_sources = @('shauryanadagoudra/elf-calc-cpsat-inputs'); competition_sources = @(); kernel_sources = @(); model_sources = @() }
    $meta | ConvertTo-Json | Set-Content "$dir\kernel-metadata.json" -Encoding utf8
    $o = & $K kernels push -p $dir 2>&1 | Select-Object -Last 1
    if ($o -match 'successfully pushed') { Get-Date -Format 'MMddHHmm' | Set-Content "$st\pushed_$s.txt" }
    Log "pushed ${s} (part $part of $NPARTS) -> $o"
}
