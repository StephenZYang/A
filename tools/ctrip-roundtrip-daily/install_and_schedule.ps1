$ErrorActionPreference='Stop'
$Dest=Join-Path $env:USERPROFILE 'CtripFareCheck'
$PyFile=Join-Path $Dest 'ctrip_roundtrip_qingdao_melbourne.py'
$Raw='https://raw.githubusercontent.com/StephenZYang/A/main/tools/ctrip-roundtrip-daily/ctrip_roundtrip_qingdao_melbourne.py'
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Write-Host '[1/5] Downloading checker...'
Invoke-WebRequest -UseBasicParsing $Raw -OutFile $PyFile
if(-not (Get-Command py -ErrorAction SilentlyContinue)){throw 'Python launcher (py) not found. Install Python 3.14 from python.org first.'}
$Venv=Join-Path $Dest '.venv'
if(-not (Test-Path (Join-Path $Venv 'Scripts\python.exe'))){
  Write-Host '[2/5] Creating Python environment...'
  & py -3.14 -m venv $Venv
  if($LASTEXITCODE -ne 0){& py -m venv $Venv}
}
$Python=Join-Path $Venv 'Scripts\python.exe'
Write-Host '[3/5] Installing Selenium...'
& $Python -m pip install --upgrade pip
& $Python -m pip install 'selenium>=4.20,<5'
$Cmd=Join-Path $Dest 'run_daily.cmd'
Set-Content -Encoding ASCII $Cmd ('@echo off' + "`r`n" + 'cd /d "%USERPROFILE%\CtripFareCheck"' + "`r`n" + '"%USERPROFILE%\CtripFareCheck\.venv\Scripts\python.exe" "%USERPROFILE%\CtripFareCheck\ctrip_roundtrip_qingdao_melbourne.py"')
Write-Host '[4/5] Registering Windows daily task at 08:05...'
$TaskName='Ctrip TAO-MEL Daily Fare Check'
$Action=New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "'+$Cmd+'"') -WorkingDirectory $Dest
$Trigger=New-ScheduledTaskTrigger -Daily -At 8:05AM
$Principal=New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null
Write-Host '[5/5] Running once now...'
Write-Host 'If Ctrip asks for CAPTCHA/security verification, complete it manually in Edge.'
& $Cmd
Write-Host "Installed. Daily task: $TaskName"
Write-Host "Results: $Dest\results"
