<#
.SYNOPSIS
    Installs everything VideoScribe needs on Windows.

.DESCRIPTION
    Checks for each requirement and installs only what is missing:

      1. Python 3.9 or newer      (via winget, if absent)
      2. ffmpeg                   (via winget, if absent)
      3. Python packages          (pip install -r requirements.txt)
      4. Folders                  (inbox, output)
      5. Personal settings file   (.env, copied from .env.example)

    Then it reports what the computer can handle and which transcription model
    suits it.

    Nothing is installed without saying so first. Run with -WhatIf to see the
    plan without changing anything.

.EXAMPLE
    .\init.ps1
    Normal setup.

.EXAMPLE
    .\init.ps1 -WhatIf
    Show what would be installed, change nothing.

.EXAMPLE
    .\init.ps1 -SkipPython
    Use the Python already on this machine even if it looks old.
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # Do not attempt to install or upgrade Python.
    [switch]$SkipPython,

    # Do not attempt to install ffmpeg.
    [switch]$SkipFFmpeg,

    # Install Python packages for the current user only.
    [switch]$UserInstall,

    # Interface language. Omit to be asked; useful for unattended installs.
    [ValidateSet('en', 'es')]
    [string]$Language
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$MinimumPython = [version]'3.9'

# --- Small output helpers --------------------------------------------------
$script:StepNumber = 0
$script:TotalSteps = 5

function Write-Step($text) {
    $script:StepNumber++
    Write-Host ""
    Write-Host "[$script:StepNumber/$script:TotalSteps] $text" -ForegroundColor Cyan
}
function Write-Ok($text) { Write-Host "      [ok]   $text" -ForegroundColor Green }
function Write-Info($text) { Write-Host "      $text" -ForegroundColor DarkGray }
function Write-Warn($text) { Write-Host "      [!]    $text" -ForegroundColor Yellow }
function Write-Fail($text) { Write-Host "      [fail] $text" -ForegroundColor Red }

function Write-Banner($text) {
    Write-Host ""
    Write-Host ("=" * 70)
    Write-Host " $text"
    Write-Host ("=" * 70)
}

function Test-Command($name) {
    return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Install-WithWinget($packageId, $friendlyName) {
    <#
      Installs a package with winget, returning $true on success. winget is
      present on Windows 10 21H2 and later; when it is missing we can only
      print a link.
    #>
    if (-not (Test-Command 'winget')) {
        Write-Fail "$friendlyName is missing and winget is not available to install it."
        Write-Info "Install it by hand, then run this script again."
        return $false
    }
    if (-not $PSCmdlet.ShouldProcess($friendlyName, "install with winget")) {
        return $false
    }
    Write-Info "Installing $friendlyName ... this can take a few minutes."
    winget install --id $packageId --accept-source-agreements --accept-package-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "winget could not install $friendlyName (exit code $LASTEXITCODE)."
        return $false
    }
    # A fresh install is not on the PATH of this already-running shell.
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
    return $true
}

Write-Banner "VIDEOSCRIBE SETUP"
Write-Host " This installs the programs needed to turn a video into a document."
Write-Host " It only installs what is missing."

# --- 0. Language -----------------------------------------------------------
# Asked first, and skipped when there is no console to answer from, so an
# unattended run never blocks waiting for input.
$script:UiLanguage = $Language
if (-not $script:UiLanguage -and -not [Console]::IsInputRedirected -and $PSCmdlet.ShouldProcess('language', 'ask')) {
    Write-Banner "SELECT LANGUAGE  /  SELECCIONA IDIOMA"
    Write-Host "  1) English"
    Write-Host "  2) Espanol (Spanish)"
    Write-Host ""
    $answer = Read-Host "  Pick a number / Elige un numero [1]"
    $script:UiLanguage = if ($answer -eq '2') { 'es' } else { 'en' }
}
if (-not $script:UiLanguage) { $script:UiLanguage = 'en' }

# --- 1. Python -------------------------------------------------------------
Write-Step "Checking Python"

$python = $null
foreach ($candidate in @('python', 'py')) {
    if (Test-Command $candidate) {
        try {
            $raw = & $candidate -c "import sys; print('.'.join(str(n) for n in sys.version_info[:3]))" 2>$null
            if ($raw -and [version]$raw -ge $MinimumPython) {
                $python = $candidate
                Write-Ok "Python $raw found at $((Get-Command $candidate).Source)"
                break
            }
            elseif ($raw) {
                Write-Warn "Python $raw is older than the required $MinimumPython."
            }
        }
        catch { }
    }
}

if (-not $python) {
    if ($SkipPython) {
        Write-Fail "No suitable Python found and -SkipPython was given."
        exit 1
    }
    Write-Warn "Python $MinimumPython or newer is not installed."
    if (Install-WithWinget 'Python.Python.3.12' 'Python 3.12') {
        $python = 'python'
        Write-Ok "Python installed."
        Write-Warn "Close this window and run init.cmd again so Windows picks up the new PATH."
        exit 0
    }
    Write-Info "Download it from https://www.python.org/downloads/"
    Write-Info "Tick 'Add python.exe to PATH' during installation."
    exit 1
}

# --- 2. ffmpeg -------------------------------------------------------------
Write-Step "Checking ffmpeg"

$ffmpegFound = Test-Command 'ffmpeg'
if (-not $ffmpegFound) {
    # It is often installed but not on the PATH; look in the usual places.
    $hints = @(
        'C:\ffmpeg\bin\ffmpeg.exe'
        'C:\ffmpeg\*\bin\ffmpeg.exe'
        'C:\Program Files\ffmpeg\bin\ffmpeg.exe'
        "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\*\*\bin\ffmpeg.exe"
    )
    foreach ($hint in $hints) {
        $hit = Get-ChildItem -Path $hint -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) {
            Write-Ok "ffmpeg found at $($hit.FullName)"
            Write-Info "It is not on your PATH, so it will be recorded in .env instead."
            $script:FFmpegPath = $hit.FullName
            $ffmpegFound = $true
            break
        }
    }
}
else {
    Write-Ok "ffmpeg found at $((Get-Command ffmpeg).Source)"
}

if (-not $ffmpegFound) {
    if ($SkipFFmpeg) {
        Write-Warn "ffmpeg is missing and -SkipFFmpeg was given. Nothing will work without it."
    }
    elseif (Install-WithWinget 'Gyan.FFmpeg' 'ffmpeg') {
        Write-Ok "ffmpeg installed."
        Write-Warn "You may need to reopen this window before ffmpeg is on the PATH."
    }
    else {
        Write-Info "Download it from https://www.gyan.dev/ffmpeg/builds/ and add its"
        Write-Info "bin folder to your PATH, or set VIDEOSCRIBE_FFMPEG in .env"
    }
}

# --- 3. Python packages ----------------------------------------------------
Write-Step "Installing Python packages"

$requirements = Join-Path $RepoRoot 'requirements.txt'
if (-not (Test-Path -LiteralPath $requirements)) {
    Write-Fail "requirements.txt is missing from $RepoRoot"
    exit 1
}

if ($PSCmdlet.ShouldProcess('Python packages', 'pip install')) {
    Write-Info "This downloads a few hundred megabytes the first time."
    $pipArgs = @('-m', 'pip', 'install', '--disable-pip-version-check', '-r', $requirements)
    if ($UserInstall) { $pipArgs += '--user' }

    & $python @pipArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "pip failed with exit code $LASTEXITCODE."
        Write-Info "If it mentions permissions, run this script again with -UserInstall"
        exit 1
    }
    Write-Ok "Packages installed."
}

# --- 4. Folders ------------------------------------------------------------
Write-Step "Creating folders"

foreach ($folder in @('inbox', 'output')) {
    $path = Join-Path $RepoRoot $folder
    if (Test-Path -LiteralPath $path) {
        Write-Info "$folder already exists"
    }
    elseif ($PSCmdlet.ShouldProcess($path, 'create folder')) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Ok "$folder created"
    }
}

# --- 5. Personal settings --------------------------------------------------
Write-Step "Setting up your personal settings file"

$envFile = Join-Path $RepoRoot '.env'
$envExample = Join-Path $RepoRoot '.env.example'

if (Test-Path -LiteralPath $envFile) {
    Write-Info ".env already exists; leaving it untouched"
}
elseif ((Test-Path -LiteralPath $envExample) -and
        $PSCmdlet.ShouldProcess($envFile, 'create from .env.example')) {
    Copy-Item -LiteralPath $envExample -Destination $envFile
    Write-Ok ".env created from the example"
}

# Record the language chosen at the start, plus the speech and written-output
# languages it implies, so the first real run starts in the right language.
if ((Test-Path -LiteralPath $envFile) -and $PSCmdlet.ShouldProcess($envFile, 'set language')) {
    $speech = if ($script:UiLanguage -eq 'es') { 'es' } else { 'en' }
    $written = if ($script:UiLanguage -eq 'es') { 'Spanish' } else { 'English' }

    $lines = Get-Content -LiteralPath $envFile
    $settings = @{
        'VIDEOSCRIBE_UI_LANGUAGE'        = $script:UiLanguage
        'VIDEOSCRIBE_LANGUAGE'           = $speech
        'VIDEOSCRIBE_NARRATION_LANGUAGE' = $written
    }
    foreach ($name in $settings.Keys) {
        $pattern = "^\s*$name\s*="
        if ($lines -match $pattern) {
            $lines = $lines -replace "$pattern.*", "$name=$($settings[$name])"
        }
        else {
            $lines += "$name=$($settings[$name])"
        }
    }
    Set-Content -LiteralPath $envFile -Value $lines -Encoding UTF8
    Write-Ok "Language set to $script:UiLanguage (speech $speech, written accounts $written)"
}

if ($script:FFmpegPath -and (Test-Path -LiteralPath $envFile)) {
    $content = Get-Content -LiteralPath $envFile -Raw
    if ($content -notmatch '(?m)^\s*VIDEOSCRIBE_FFMPEG\s*=\s*\S') {
        Add-Content -LiteralPath $envFile -Value "`nVIDEOSCRIBE_FFMPEG=$($script:FFmpegPath)"
        Write-Ok "Recorded the ffmpeg location in .env"
    }
}

# --- Report ----------------------------------------------------------------
Write-Banner "CHECKING YOUR COMPUTER"
& $python (Join-Path $RepoRoot 'videoscribe.py') doctor

Write-Banner "SETUP FINISHED"
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Green
Write-Host ""
Write-Host "    1. Copy your video files into the 'inbox' folder"
Write-Host "    2. Double-click  run.cmd   (or type:  python videoscribe.py)"
Write-Host ""
Write-Host "  Results appear in the 'output' folder, one subfolder per video."
Write-Host ""
