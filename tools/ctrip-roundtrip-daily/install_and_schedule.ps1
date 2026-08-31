$ErrorActionPreference='Stop'
$Dest=Join-Path $env:USERPROFILE 'CtripFareCheck'
$PyFile=Join-Path $Dest 'ctrip_roundtrip_qingdao_melbourne.py'
$Raw='https://raw.githubusercontent.com/StephenZYang/A/main/tools/ctrip-roundtrip-daily/ctrip_roundtrip_qingdao_melbourne.py'
$Venv=Join-Path $Dest '.venv'
$Python=Join-Path $Venv 'Scripts\python.exe'

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

Write-Host '[1/6] Downloading checker...'
Invoke-WebRequest -UseBasicParsing $Raw -OutFile $PyFile

if(-not (Get-Command py -ErrorAction SilentlyContinue)){
  throw 'Python launcher (py) not found. Reinstall Python 3.14 from python.org and enable the Python Launcher.'
}

# Verify that Python 3.14 is actually available through the launcher.
Write-Host '[2/6] Checking Python 3.14...'
& py -3.14 --version
if($LASTEXITCODE -ne 0){
  Write-Host 'Python 3.14 was not found via py -3.14. Available Python installations:'
  & py -0p
  throw 'Python 3.14 is not available through the Python launcher.'
}

# A venv can leave python.exe behind even when its base Python was removed/moved.
# Test the existing venv and rebuild it if it is broken.
$NeedRebuild=$true
if(Test-Path $Python){
  Write-Host 'Checking existing virtual environment...'
  & $Python --version 2>$null
  if($LASTEXITCODE -eq 0){
    $NeedRebuild=$false
  } else {
    Write-Host 'Existing virtual environment is broken. Rebuilding it...'
  }
}

if($NeedRebuild){
  if(Test-Path $Venv){
    Remove-Item -Recurse -Force $Venv
  }
  Write-Host '[3/6] Creating fresh Python 3.14 environment...'
  & py -3.14 -m venv $Venv
  if($LASTEXITCODE -ne 0){
    throw 'Failed to create the Python 3.14 virtual environment.'
  }
}

if(-not (Test-Path $Python)){
  throw 'Virtual environment python.exe was not created.'
}
& $Python --version
if($LASTEXITCODE -ne 0){
  throw 'Virtual environment Python cannot start.'
}

Write-Host '[4/6] Installing Selenium...'
& $Python -m pip install --upgrade pip
if($LASTEXITCODE -ne 0){throw 'pip upgrade failed.'}
& $Python -m pip install 'selenium>=4.20,<5'
if($LASTEXITCODE -ne 0){throw 'Selenium installation failed.'}

$Cmd=Join-Path $Dest 'run_daily.cmd'
Set-Content -Encoding ASCII $Cmd ('@echo off' + "`r`n" + 'cd /d "%USERPROFILE%\CtripFareCheck"' + "`r`n" + '"%USERPROFILE%\CtripFareCheck\.venv\Scripts\python.exe" "%USERPROFILE%\CtripFareCheck\ctrip_roundtrip_qingdao_melbourne.py"')

Write-Host '[5/6] Registering Windows daily task at 08:05...'
$TaskName='Ctrip TAO-MEL Daily Fare Check'
$Action=New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "'+$Cmd+'"') -WorkingDirectory $Dest
$Trigger=New-ScheduledTaskTrigger -Daily -At 8:05AM
$Principal=New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null

Write-Host '[6/6] Running once now...'
Write-Host 'If Ctrip asks for CAPTCHA/security verification, complete it manually in Edge.'
& $Cmd
if($LASTEXITCODE -ne 0){
  throw "The first fare check failed with exit code $LASTEXITCODE."
}

Write-Host "Installed successfully. Daily task: $TaskName"
Write-Host "Results: $Dest\results"
