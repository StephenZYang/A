$ErrorActionPreference='Stop'

$Dest=Join-Path $env:USERPROFILE 'CtripFareCheck'
$PyFile=Join-Path $Dest 'ctrip_roundtrip_qingdao_melbourne.py'
$Raw='https://raw.githubusercontent.com/StephenZYang/A/da38c075f10daebb08132bec0ed40e2bf0368deb/tools/ctrip-roundtrip-daily/ctrip_roundtrip_qingdao_melbourne.py'
$Venv=Join-Path $Dest '.venv'
$Python=Join-Path $Venv 'Scripts\python.exe'
$RepoDir=Join-Path $Dest 'repo_sync'

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

Write-Host '[1/8] Downloading checker...'
Invoke-WebRequest -UseBasicParsing $Raw -OutFile $PyFile

if(-not (Get-Command py -ErrorAction SilentlyContinue)){
  throw 'Python launcher (py) not found. Reinstall Python 3.14 from python.org and enable the Python Launcher.'
}

Write-Host '[2/8] Checking Python 3.14...'
& py -3.14 --version
if($LASTEXITCODE -ne 0){
  Write-Host 'Python 3.14 was not found via py -3.14. Available Python installations:'
  & py -0p
  throw 'Python 3.14 is not available through the Python launcher.'
}

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
  if(Test-Path $Venv){Remove-Item -Recurse -Force $Venv}
  Write-Host '[3/8] Creating fresh Python 3.14 environment...'
  & py -3.14 -m venv $Venv
  if($LASTEXITCODE -ne 0){throw 'Failed to create the Python 3.14 virtual environment.'}
}

if(-not (Test-Path $Python)){throw 'Virtual environment python.exe was not created.'}
& $Python --version
if($LASTEXITCODE -ne 0){throw 'Virtual environment Python cannot start.'}

Write-Host '[4/8] Installing Selenium...'
& $Python -m pip install --upgrade pip
if($LASTEXITCODE -ne 0){throw 'pip upgrade failed.'}
& $Python -m pip install 'selenium>=4.20,<5'
if($LASTEXITCODE -ne 0){throw 'Selenium installation failed.'}

Write-Host '[5/8] Preparing Git and GitHub CLI...'
function Refresh-Path {
  $machine=[Environment]::GetEnvironmentVariable('Path','Machine')
  $user=[Environment]::GetEnvironmentVariable('Path','User')
  $env:Path="$machine;$user"
}

if(-not (Get-Command git -ErrorAction SilentlyContinue)){
  if(-not (Get-Command winget -ErrorAction SilentlyContinue)){
    throw 'Git is not installed and winget is unavailable. Install Git for Windows, then run this installer again.'
  }
  Write-Host 'Installing Git for Windows...'
  & winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
  Refresh-Path
}
if(-not (Get-Command git -ErrorAction SilentlyContinue)){
  throw 'Git installation was not detected. Restart PowerShell and run this installer again.'
}

if(-not (Get-Command gh -ErrorAction SilentlyContinue)){
  if(-not (Get-Command winget -ErrorAction SilentlyContinue)){
    throw 'GitHub CLI is not installed and winget is unavailable. Install GitHub CLI, then run this installer again.'
  }
  Write-Host 'Installing GitHub CLI...'
  & winget install --id GitHub.cli -e --accept-package-agreements --accept-source-agreements
  Refresh-Path
}
if(-not (Get-Command gh -ErrorAction SilentlyContinue)){
  throw 'GitHub CLI installation was not detected. Restart PowerShell and run this installer again.'
}

Write-Host '[6/8] Connecting GitHub for automatic result upload...'
& gh auth status *> $null
if($LASTEXITCODE -ne 0){
  Write-Host 'One-time GitHub authorization is required. A browser/device login may open.'
  & gh auth login --hostname github.com --git-protocol https --web
  if($LASTEXITCODE -ne 0){throw 'GitHub login failed.'}
}
& gh auth setup-git
if($LASTEXITCODE -ne 0){throw 'Could not configure Git authentication.'}

if(-not (Test-Path (Join-Path $RepoDir '.git'))){
  if(Test-Path $RepoDir){Remove-Item -Recurse -Force $RepoDir}
  & gh repo clone StephenZYang/A $RepoDir
  if($LASTEXITCODE -ne 0){throw 'Could not clone StephenZYang/A for fare result synchronization.'}
} else {
  & git -C $RepoDir pull --rebase origin main
}

$Cmd=Join-Path $Dest 'run_daily.cmd'
$CmdText = @'
@echo off
set CTRIP_AUTOMATED=1
cd /d "%USERPROFILE%\CtripFareCheck"
"%USERPROFILE%\CtripFareCheck\.venv\Scripts\python.exe" "%USERPROFILE%\CtripFareCheck\ctrip_roundtrip_qingdao_melbourne.py"
'@
Set-Content -Encoding ASCII $Cmd $CmdText

Write-Host '[7/8] Registering Windows daily task at 08:05...'
$OldTaskName='Ctrip TAO-MEL Daily Fare Check'
$TaskName='Ctrip MEL-TAO Daily Fare Check'
if(Get-ScheduledTask -TaskName $OldTaskName -ErrorAction SilentlyContinue){
  Unregister-ScheduledTask -TaskName $OldTaskName -Confirm:$false
}
$Action=New-ScheduledTaskAction -Execute 'cmd.exe' -Argument ('/c "'+$Cmd+'"') -WorkingDirectory $Dest
$Trigger=New-ScheduledTaskTrigger -Daily -At 8:05AM
$Principal=New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force | Out-Null

Write-Host '[8/8] Running first check now...'
Write-Host 'Route: 2027-02-01 MEL -> TAO; 2027-02-14 TAO -> MEL'
Write-Host 'If Ctrip asks for CAPTCHA/security verification, complete it manually in Edge.'
& $Python $PyFile
if($LASTEXITCODE -ne 0){
  throw "The first fare check failed with exit code $LASTEXITCODE."
}

Write-Host ''
Write-Host 'Installed successfully.'
Write-Host "Windows daily task: $TaskName at 08:05"
Write-Host "Local results: $Dest\results"
Write-Host 'GitHub status file: StephenZYang/A/flight-monitor/MEL-TAO/latest.json'
Write-Host 'ChatGPT will read the synced status after the daily check.'
