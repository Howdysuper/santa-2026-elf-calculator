# Fresh-row polish loop (Aside, 11-19). After each store change (new public merge), export the store, find the rows whose
# program changed since the previous export, and run lns3 on them (6 threads, ~1.8 h budget). Top up with a rotating slice
# of other rows when few changed. Output files work/out_fresh_rN_lns.txt are imported by work/autoloop.sh (pattern out_*lns.txt).
# usage (persistent session): pwsh -NoProfile -File work\freshloop.ps1 [ROUNDS] [THREADS]
param([int]$Rounds = 200, [int]$Threads = 6)
Remove-Item env:PYTHONHOME -EA 0; Remove-Item env:PYTHONNOUSERSITE -EA 0
$env:PYTHONIOENCODING = 'utf-8'
Set-Location 'C:\Users\shaur\Kaggle ML\competitions\santa-2026'
$py = '..\..\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force work\fresh | Out-Null
$log = 'work\fresh\freshloop.log'
function Log($m) { "$(Get-Date -Format 'MM-dd HH:mm') $m" | Tee-Object -FilePath $log -Append }
$prev = 'work\cur6\programs.txt'
if (Test-Path work\fresh\prev.txt) { $prev = Get-Content work\fresh\prev.txt }
$rot = 0; if (Test-Path work\fresh\rot.txt) { $rot = [int](Get-Content work\fresh\rot.txt) }
for ($r = 1; $r -le $Rounds; $r++) {
    $n = 1; while (Test-Path "work\fresh\r$n") { $n++ }
    while (Test-Path work\store.lock) { Start-Sleep 30 }
    & $py src\export.py "work\fresh\r$n" | Out-Null
    $cur = "work\fresh\r$n\programs.txt"
    $old = @{}; Get-Content $prev | ForEach-Object { $p = $_.Split(' ', 3); $old[$p[0]] = $p[1] + ' ' + $p[2].GetHashCode() }
    $changed = @(); Get-Content $cur | ForEach-Object { $p = $_.Split(' ', 3); if ($old[$p[0]] -ne ($p[1] + ' ' + $p[2].GetHashCode())) { $changed += $p[0] } }
    $ids = [System.Collections.Generic.List[string]]::new(); $changed | ForEach-Object { $ids.Add($_) }
    $all = Get-Content work\fresh\r$n\puzzles.txt | ForEach-Object { $_.Split(' ')[0] }
    while ($ids.Count -lt 60) { $id = $all[$rot % $all.Count]; $rot++; if (-not $ids.Contains($id)) { $ids.Add($id) } }
    $rot | Set-Content work\fresh\rot.txt
    $set = @{}; $ids | ForEach-Object { $set[$_] = 1 }
    Get-Content "work\fresh\r$n\puzzles.txt" | Where-Object { $set[$_.Split(' ')[0]] } | Set-Content "work\fresh\p_r$n.txt"
    $sec = [Math]::Max(120, [Math]::Min(600, [int](6500 * $Threads / $ids.Count)))
    if ($n % 2 -eq 0) { $env:CUTPROB = '25'; $env:WMAX = '5' } else { Remove-Item env:CUTPROB -EA 0; Remove-Item env:WMAX -EA 0 }
    Log "round $n changed $($changed.Count) rows total $($ids.Count) sec $sec cut $($env:CUTPROB)"
    $prev = $cur; $prev | Set-Content work\fresh\prev.txt
    & work\lns3.exe "work\fresh\p_r$n.txt" $cur "work\out_fresh_r${n}_lns.txt" $sec $Threads (7000 + $n) 2> "work\fresh\lns_r$n.log"
    $g = (Select-String -Path "work\fresh\lns_r$n.log" -Pattern '->' | Measure-Object).Count
    Log "round $n done: $g improved rows; $((Get-Content "work\fresh\lns_r$n.log" -Tail 1))"
    # wait for the next store change (submission) or at most 30 min more
    $t0 = (Get-Item work\last_submitted.txt).LastWriteTime; $waited = 0
    while ((Get-Item work\last_submitted.txt).LastWriteTime -eq $t0 -and $waited -lt 1800) { Start-Sleep 60; $waited += 60 }
}
