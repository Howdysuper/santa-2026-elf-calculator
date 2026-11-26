# One bounded local CP-SAT structure-recombination batch (Aside, 11-20). Walks a rotating pointer through the structured
# puzzle list (kaggle/cpsat_inputs/cpsat_ids.txt: shared, multiplicative, mixed, costliest per target first), MINUTES budget,
# SEC per puzzle, 8 CP-SAT workers. Gains (replay-validated, 48 registers) -> work/out_cpsat_lns.txt, imported by the merge round.
# usage: pwsh -NoProfile -File work\cpsonce.ps1 [MINUTES=25] [SEC=90]
param([int]$Minutes = 25, [int]$Sec = 90)
Remove-Item env:PYTHONHOME -EA 0; Remove-Item env:PYTHONNOUSERSITE -EA 0
$env:PYTHONIOENCODING = 'utf-8'
$root = 'C:\Users\shaur\Kaggle ML\competitions\santa-2026'; Set-Location $root
$py = '..\..\.venv\Scripts\python.exe'
$ids = Get-Content kaggle\cpsat_inputs\cpsat_ids.txt | Where-Object { $_ }
$ptrF = 'work\fresh\cps_ptr.txt'; $ptr = 0; if (Test-Path $ptrF) { $ptr = [int](Get-Content $ptrF) }
$n = [Math]::Max(1, [int]($Minutes * 60 / ($Sec + 10)))
# rows whose best program changed since the previous cpsonce export come first (pending queue), then the rotating list
$structSet = @{}; $ids | ForEach-Object { $structSet[$_] = 1 }
$t = 0; while (-not (New-Item -ItemType Directory work\store.lock -EA 0)) { Start-Sleep 20; $t++; if ($t -gt 90) { break } }
try { & $py src\export.py work\fresh\cps_cur | Out-Null } finally { Remove-Item work\store.lock -Recurse -Force -EA 0 }
$queue = [System.Collections.Generic.List[string]]::new()
if (Test-Path work\fresh\cps_pending.txt) { Get-Content work\fresh\cps_pending.txt | Where-Object { $_ } | ForEach-Object { if (-not $queue.Contains($_)) { $queue.Add($_) } } }
if (Test-Path work\fresh\cps_prev.txt) {
    $old2 = @{}; Get-Content work\fresh\cps_prev.txt | ForEach-Object { $p = $_.Split(' ', 2); $old2[$p[0]] = $p[1] }
    Get-Content work\fresh\cps_cur\programs.txt | ForEach-Object { $p = $_.Split(' ', 2); if ($structSet[$p[0]] -and $old2[$p[0]] -ne $p[1] -and -not $queue.Contains($p[0])) { $queue.Add($p[0]) } }
}
Copy-Item work\fresh\cps_cur\programs.txt work\fresh\cps_prev.txt -Force
$batch = @($queue | Select-Object -First $n)
$queue | Select-Object -Skip $n | Set-Content work\fresh\cps_pending.txt
$fill = $n - $batch.Count
for ($i = 0; $i -lt $fill; $i++) { $batch += $ids[($ptr + $i) % $ids.Count] }
($ptr + $fill) % $ids.Count | Set-Content $ptrF
$batch | Set-Content work\fresh\p_cps.txt
$env:PYTHONPATH = "$root\ortools_lib"; $env:STRUCT = '1'
"$(Get-Date -Format 'MM-dd HH:mm') cpsonce: $n puzzles ($($n - $fill) freshly changed, $fill from list #$ptr; pending $([Math]::Max(0, $queue.Count - $n)))" | Tee-Object -FilePath work\fresh\cpsonce.log -Append
$out = & $py src\cpsat_recomb.py work\var_all.json work\fresh\p_cps.txt work\out_cpsat_lns.txt $Sec 8 1.3 2>&1
$out | Out-File work\fresh\cpsonce.log -Append
$g = @($out | Select-String ' -> (\d+) ' | Where-Object { $_.Line -match 'best (\d+) -> (\d+)' -and [int]$matches[2] -lt [int]$matches[1] })
"$(Get-Date -Format 'MM-dd HH:mm') cpsonce done: $($g.Count) puzzles improved: $(($g | ForEach-Object { ($_.Line -split ' ')[0..3] -join ' ' }) -join '; ')" | Tee-Object -FilePath work\fresh\cpsonce.log -Append
