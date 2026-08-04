<#
.SYNOPSIS
    PowerShell front end for the visual description step: writes an account of
    what happens on screen, combining the picture with the transcript.

.DESCRIPTION
    Runs the same pipeline as Transcribe.ps1 but always with the description
    step switched on. Provided as a separate command because it is the slower
    and more expensive half, and because it is the one that needs an
    image-capable model to be configured.

    How it works: the recording is cut into windows of a couple of minutes. For
    each window an image model receives the video frames of that stretch
    together with the words spoken during it, and writes one paragraph. A final
    pass joins the paragraphs into one continuous account.

    Every claim carries a timecode pointing at the source video. Timecodes the
    model invents are detected and removed automatically, because a wrong one
    sends a reader to the wrong minute of a long recording.

    Which model does the describing is set by -VisionBackend. With 'auto' the
    first configured option wins, in this order: the Claude Code command line
    tool, then an Anthropic, OpenAI or Google Gemini API key from .env.

.PARAMETER FrameInterval
    Seconds between video frames. Lower catches more detail and costs
    proportionally more. Default is 10.

.PARAMETER Window
    Seconds of video described per request. Default is 120.

.EXAMPLE
    .\Narrate.ps1
    Describe every video in the inbox folder.

.EXAMPLE
    .\Narrate.ps1 -Resume
    Carry on where an interrupted run stopped. Sections already written are
    kept, and only the missing ones are requested again.

.EXAMPLE
    .\Narrate.ps1 -FrameInterval 5 -Window 60
    Twice the visual detail, at roughly twice the cost.

.EXAMPLE
    .\Narrate.ps1 -Start 00:12:00 -Duration 00:05:00 -VisionBackend gemini
    Describe a five-minute stretch using Google Gemini.
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromPipeline = $true, ValueFromPipelineByPropertyName = $true)]
    [Alias('FullName', 'Path')]
    [string]$Video,

    [ValidateRange(1, 600)]
    [int]$FrameInterval = -1,

    [ValidateRange(30, 900)]
    [int]$Window = -1,

    [ValidateSet('auto', 'claude-cli', 'anthropic', 'openai', 'gemini')]
    [string]$VisionBackend = 'auto',

    [ValidateSet('tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3')]
    [string]$Model,

    [string]$Language,

    [ValidateRange(-1, 20)]
    [int]$Speakers = -1,

    [ValidatePattern('^\d{1,2}:\d{2}(:\d{2})?$')]
    [string]$Start,

    [ValidatePattern('^\d{1,2}:\d{2}(:\d{2})?$')]
    [string]$Duration,

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
        $venv = Join-Path $RepoRoot '.venv\Scripts\python.exe'
        if (Test-Path -LiteralPath $venv) { return $venv }
        foreach ($candidate in @('python', 'py')) {
            $found = Get-Command $candidate -ErrorAction SilentlyContinue
            if ($found) { return $found.Source }
        }
        throw "Python was not found. Run init.cmd in $RepoRoot to install it."
    }

    $Python = Resolve-Python
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONUTF8 = '1'
}

process {
    # --describe is what makes this different from Transcribe.ps1.
    $arguments = @($EntryPoint, 'run', '--describe')

    if ($Video) {
        if (-not (Test-Path -LiteralPath $Video)) {
            throw "No such file: $Video"
        }
        $arguments += @('--file', (Resolve-Path -LiteralPath $Video).ProviderPath)
    }

    if ($FrameInterval -ge 1) { $arguments += @('--frame-interval', $FrameInterval) }
    if ($Window -ge 30) { $arguments += @('--window', $Window) }
    if ($VisionBackend -ne 'auto') { $arguments += @('--vision-backend', $VisionBackend) }
    if ($Model) { $arguments += @('--model', $Model) }
    if ($Language) { $arguments += @('--language', $Language) }
    if ($Speakers -ge 0) { $arguments += @('--speakers', $Speakers) }
    if ($Start) { $arguments += @('--start', $Start) }
    if ($Duration) { $arguments += @('--duration', $Duration) }
    if ($OutputFolder) { $arguments += @('--output', $OutputFolder) }
    if ($Resume) { $arguments += '--resume' }
    if ($KeepWork) { $arguments += '--keep-work' }
    if ($Quiet) { $arguments += '--quiet' }

    Write-Verbose "Running: $Python $($arguments -join ' ')"

    # See the note in Transcribe.ps1: with $ErrorActionPreference = 'Stop', a
    # native program writing a warning to stderr would abort the run.
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
