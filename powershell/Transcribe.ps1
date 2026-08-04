<#
.SYNOPSIS
    PowerShell front end for VideoScribe: turns a video into an MP3 and a
    transcript with the speakers told apart.

.DESCRIPTION
    This is the PowerShell way into the same engine the Python command line
    uses. It exists so Windows users can work with familiar parameters, tab
    completion and pipeline input instead of POSIX-style flags.

    A note on what is and is not duplicated: speech recognition and the
    acoustic speaker separation are Python, because there is no PowerShell
    speech model. This script validates the request, resolves paths and hands
    the work to the videoscribe package, so both front ends always agree
    rather than drifting apart over time.

    For the full set of options see:  python videoscribe.py run --help

.PARAMETER Video
    A video file. Without this, every video in the inbox folder is processed.

.PARAMETER Model
    Transcription model. Bigger is more accurate and slower.
    Run Show-VideoScribeModels.ps1 to see timings for this computer.

.PARAMETER Language
    Two-letter language code such as es or en, or 'auto' to detect it.

.PARAMETER Speakers
    How many people speak. 0 asks the program to work it out, which is
    unreliable in noisy recordings.

.PARAMETER Describe
    Also write an account of what is visible on screen. Needs an image-capable
    model to be configured; see the README.

.PARAMETER Resume
    Reuse whatever a previous run produced and only redo what is missing.

.EXAMPLE
    .\Transcribe.ps1
    Process every video in the inbox folder using the settings in config.json.

.EXAMPLE
    .\Transcribe.ps1 -Model medium -Speakers 2
    More accurate, and forced to exactly two speakers.

.EXAMPLE
    .\Transcribe.ps1 -Video "C:\cases\hearing.mp4" -Describe
    One file, including a description of what happens on screen.

.EXAMPLE
    .\Transcribe.ps1 -Start 00:12:00 -Duration 00:03:00 -Model tiny
    A three-minute sample, for checking quality before committing to a long run.

.EXAMPLE
    Get-ChildItem C:\cases\*.mp4 | .\Transcribe.ps1 -Model medium
    Process several files from the pipeline.
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromPipeline = $true, ValueFromPipelineByPropertyName = $true)]
    [Alias('FullName', 'Path')]
    [string]$Video,

    [ValidateSet('tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3')]
    [string]$Model,

    [string]$Language,

    # -1 means "not supplied"; 0 is a real value meaning "work it out".
    [ValidateRange(-1, 20)]
    [int]$Speakers = -1,

    [ValidateRange(-1, 20)]
    [int]$MaxSpeakers = -1,

    [switch]$Describe,

    [ValidatePattern('^\d{1,2}:\d{2}(:\d{2})?$')]
    [string]$Start,

    [ValidatePattern('^\d{1,2}:\d{2}(:\d{2})?$')]
    [string]$Duration,

    [ValidateSet('auto', 'claude-cli', 'anthropic', 'openai', 'gemini')]
    [string]$VisionBackend = 'auto',

    [switch]$Resume,

    [switch]$KeepWork,

    [string]$OutputFolder,

    [switch]$Quiet
)

begin {
    $ErrorActionPreference = 'Stop'
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
    $EntryPoint = Join-Path $RepoRoot 'videoscribe.py'

    if (-not (Test-Path -LiteralPath $EntryPoint)) {
        throw "Cannot find videoscribe.py. Expected it at: $EntryPoint"
    }

    function Resolve-Python {
        <#
          Prefer the private environment created by the installer, then
          whatever Python is on the PATH.
        #>
        $venv = Join-Path $RepoRoot '.venv\Scripts\python.exe'
        if (Test-Path -LiteralPath $venv) { return $venv }

        foreach ($candidate in @('python', 'py')) {
            $found = Get-Command $candidate -ErrorAction SilentlyContinue
            if ($found) { return $found.Source }
        }
        throw "Python was not found. Run init.cmd in $RepoRoot to install it."
    }

    $Python = Resolve-Python

    # Python writes UTF-8; without these the console mangles accented text.
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONUTF8 = '1'
}

process {
    $arguments = @($EntryPoint, 'run')

    if ($Video) {
        if (-not (Test-Path -LiteralPath $Video)) {
            throw "No such file: $Video"
        }
        $arguments += @('--file', (Resolve-Path -LiteralPath $Video).ProviderPath)
    }

    if ($Model) { $arguments += @('--model', $Model) }
    if ($Language) { $arguments += @('--language', $Language) }
    if ($Speakers -ge 0) { $arguments += @('--speakers', $Speakers) }
    if ($MaxSpeakers -ge 2) { $arguments += @('--max-speakers', $MaxSpeakers) }
    if ($Start) { $arguments += @('--start', $Start) }
    if ($Duration) { $arguments += @('--duration', $Duration) }
    if ($OutputFolder) { $arguments += @('--output', $OutputFolder) }
    if ($VisionBackend -ne 'auto') { $arguments += @('--vision-backend', $VisionBackend) }
    if ($Describe) { $arguments += '--describe' }
    if ($Resume) { $arguments += '--resume' }
    if ($KeepWork) { $arguments += '--keep-work' }
    if ($Quiet) { $arguments += '--quiet' }

    Write-Verbose "Running: $Python $($arguments -join ' ')"

    # In Windows PowerShell, $ErrorActionPreference = 'Stop' turns any line a
    # native program writes to stderr into a terminating error -- even a
    # harmless warning. Relax it for the call itself and judge the result by
    # the exit code instead, which is the only reliable signal.
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Python @arguments
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Error "VideoScribe finished with exit code $LASTEXITCODE. See the messages above."
        exit $LASTEXITCODE
    }
}
