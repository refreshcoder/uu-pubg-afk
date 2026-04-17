$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Test-Admin {
  $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
  Write-Host 'Run PowerShell as Administrator, otherwise in-game keyboard/mouse may not work.' -ForegroundColor Yellow
}

function Get-PythonCmd {
  if (Get-Command python -ErrorAction SilentlyContinue) {
    return 'python'
  }
  if (Get-Command py -ErrorAction SilentlyContinue) {
    return 'py'
  }
  if (Get-Command python3 -ErrorAction SilentlyContinue) {
    return 'python3'
  }
  return $null
}

function Install-Python {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    & winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    return
  }

  $tmp = Join-Path $env:TEMP 'python-installer'
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  $installer = Join-Path $tmp 'python-3.11.9-amd64.exe'
  $url = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
  Invoke-WebRequest -Uri $url -OutFile $installer
  Start-Process -FilePath $installer -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_test=0' -Wait
}

$python = Get-PythonCmd
if (-not $python) {
  Write-Host 'Python not found. Installing...' -ForegroundColor Yellow
  Install-Python
  $machinePath = [System.Environment]::GetEnvironmentVariable('Path', [System.EnvironmentVariableTarget]::Machine)
  $userPath = [System.Environment]::GetEnvironmentVariable('Path', [System.EnvironmentVariableTarget]::User)
  $env:Path = $machinePath + ';' + $userPath
  $python = Get-PythonCmd
}

if (-not $python) {
  throw 'Python install/detect failed. Please install Python 3.10+ and retry.'
}

$venvDir = Join-Path $ScriptDir 'venv_win'
if (-not (Test-Path $venvDir)) {
  & $python -m venv $venvDir
}

$venvPython = Join-Path $venvDir 'Scripts\python.exe'

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $ScriptDir "requirements.txt")

Write-Host 'Dependencies installed. Launching script...' -ForegroundColor Green
& $venvPython (Join-Path $ScriptDir 'uu_pubg_afk.py')
