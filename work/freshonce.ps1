# One bounded fresh-row polish round (Aside, 11-19): export the store, find rows changed since the previous freshonce export,
# run lns3 on them (6 threads) with a total budget of ~40 min, output work/out_fresh_rN_lns.txt (imported by the merge round).
# Exec sessions expire after ~1 h, so keep each call under that. usage: pwsh -NoProfile -File work\freshonce.ps1 [MINUTES] [THREADS]
param([int]$Minutes = 40, [int]$Threads = 6)
Remove-Item env:PYTHONHOME -EA 0; Remove-Item env:PYTHONNOUSERSITE -EA 0
$env:PYTHONIOENCODING = 'utf-8'
Set-Location 'C:\Users\shaur\Kaggle ML\competitions\santa-2026'
$py = '..\..\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force work\fresh | Out-Null
$log = 'work\fresh\freshloop.log'
function Log($m) { "$(Get-Date -Format 'MM-dd HH:mm') $m" | Tee-Object -FilePath $log -Append }
$prev = 'work\cur6\programs.txt'; if (Test-Path work\fresh\prev.txt) { $prev = Get-Content work\fresh\prev.txt }
$rot = 0; if (Test-Path work\fresh\rot.txt) { $rot = [int](Get-Content work\fresh\rot.txt) }
$n = 1; while (Test-Path "work\fresh\r$n") { $n++ }
$t = 0; while (-not (New-Item -ItemType Directory work\store.lock -EA 0)) { Start-Sleep 20; $t++; if ($t -gt 90) { Log 'lock: taking over a stale lock'; break } }
try { & $py src\export.py "work\fresh\r$n" | Out-Null } finally { Remove-Item work\store.lock -Recurse -Force -EA 0 }
$cur = "work\fresh\r$n\programs.txt"
$old = @{}; Get-Content $prev | ForEach-Object { $p = $_.Split(' ', 2); $old[$p[0]] = $p[1] }
$changed = @(); Get-Content $cur | ForEach-Object { $p = $_.Split(' ', 2); if ($old[$p[0]] -ne $p[1]) { $changed += $p[0] } }
$ids = [System.Collections.Generic.List[string]]::new(); if (Test-Path work\fresh\pending.txt) { Get-Content work\fresh\pending.txt | ForEach-Object { if ($_ -and -not $ids.Contains($_)) { $ids.Add($_) } } }; $changed | ForEach-Object { if (-not $ids.Contains($_)) { $ids.Add($_) } }
$all = Get-Content "work\fresh\r$n\puzzles.txt" | ForEach-Object { $_.Split(' ')[0] }
while ($ids.Count -lt 36) { $id = $all[$rot % $all.Count]; $rot++; if (-not $ids.Contains($id)) { $ids.Add($id) } }
$rot | Set-Content work\fresh\rot.txt
$sec = [int]($Minutes * 60 * $Threads / $ids.Count)
if ($sec -lt 60) { # too many changed rows for the budget: take a slice now, the rest stays for later rounds
    $take = [int]($Minutes * 60 * $Threads / 60); $ids | Select-Object -Skip $take | Set-Content work\fresh\pending.txt; $ids = [System.Collections.Generic.List[string]]($ids | Select-Object -First $take); $sec = 60
} else { Set-Content work\fresh\pending.txt -Value @() }
$cur | Set-Content work\fresh\prev.txt
if ($sec -gt 600) { $sec = 600 }
$set = @{}; $ids | ForEach-Object { $set[$_] = 1 }
Get-Content "work\fresh\r$n\puzzles.txt" | Where-Object { $set[$_.Split(' ')[0]] } | Set-Content "work\fresh\p_r$n.txt"
if ($n % 2 -eq 0) { $env:CUTPROB = '25'; $env:WMAX = '5' } else { Remove-Item env:CUTPROB -EA 0; Remove-Item env:WMAX -EA 0 }
Log "freshonce r$n changed $($changed.Count) rows, running $($ids.Count) at $sec s, cut '$($env:CUTPROB)'"
& work\lns3n.exe "work\fresh\p_r$n.txt" $cur "work\out_fresh_r${n}_lns.txt" $sec $Threads (7000 + $n) 2> "work\fresh\lns_r$n.log"
$g = (Select-String -Path "work\fresh\lns_r$n.log" -Pattern '^scored_' | Measure-Object).Count
Log "freshonce r$n done: $g improved rows; $((Get-Content "work\fresh\lns_r$n.log" -Tail 1))"
"freshonce done"
