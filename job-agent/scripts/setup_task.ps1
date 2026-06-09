# 매일 오전 8시에 채용 취합을 실행하는 Windows 작업 스케줄러 등록.
# PowerShell에서 1회 실행:  powershell -ExecutionPolicy Bypass -File scripts\setup_task.ps1
# 시간 변경: -At 파라미터 수정. 제거:  Unregister-ScheduledTask -TaskName "JobAgentDaily"

$ErrorActionPreference = "Stop"
$runBat = Join-Path $PSScriptRoot "run.bat"

$action  = New-ScheduledTaskAction -Execute $runBat
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
# 노트북이 배터리일 때도 실행, 깨어있을 때만(없으면 다음 로그인 시 1회 보충)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "JobAgentDaily" -Action $action -Trigger $trigger `
    -Settings $settings -Description "맞춤 채용 공고 일일 취합" -Force

Write-Host "[OK] 'JobAgentDaily' 작업 등록 완료 — 매일 08:00 실행"
Write-Host "     즉시 테스트:  Start-ScheduledTask -TaskName JobAgentDaily"
Write-Host "     로그 확인:    job-agent\data\run.log"
