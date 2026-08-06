param(
    [string]$Voice = "Microsoft Zira Desktop",
    [int]$Rate = 1
)

$ErrorActionPreference = "Stop"
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$scriptPath = Join-Path $repoPath "video\script.json"
$buildPath = Join-Path $repoPath "video\build"
$outputPath = Join-Path $repoPath "video\proofline-keeper-demo.mp4"
$ffmpeg = (Get-Command ffmpeg -ErrorAction Stop).Source
$ffprobe = (Get-Command ffprobe -ErrorAction Stop).Source

python (Join-Path $PSScriptRoot "render_demo_slides.py")
if ($LASTEXITCODE -ne 0) { throw "Slide rendering failed." }

Add-Type -AssemblyName System.Speech
$segments = Get-Content -LiteralPath $scriptPath -Raw | ConvertFrom-Json
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($Voice)
$synth.Rate = $Rate

$audioFiles = @()
$durations = @()
for ($index = 0; $index -lt $segments.Count; $index++) {
    $audioPath = Join-Path $buildPath ("segment-{0:D2}.wav" -f ($index + 1))
    $synth.SetOutputToWaveFile($audioPath)
    $synth.Speak($segments[$index].narration)
    $synth.SetOutputToNull()
    $duration = [double](& $ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $audioPath)
    $audioFiles += $audioPath
    $durations += $duration
}
$synth.Dispose()

$audioConcatPath = Join-Path $buildPath "audio-concat.txt"
$audioLines = $audioFiles | ForEach-Object { "file '$($_.Replace("'", "''"))'" }
[IO.File]::WriteAllLines($audioConcatPath, $audioLines, [Text.UTF8Encoding]::new($false))
$narrationPath = Join-Path $buildPath "narration.wav"
& $ffmpeg -y -v error -f concat -safe 0 -i $audioConcatPath -c copy $narrationPath
if ($LASTEXITCODE -ne 0) { throw "Narration concatenation failed." }

function Format-AssTime([double]$Seconds) {
    $span = [TimeSpan]::FromSeconds($Seconds)
    return "{0}:{1:D2}:{2:D2}.{3:D2}" -f [int]$span.TotalHours, $span.Minutes, $span.Seconds, [int]($span.Milliseconds / 10)
}

function Escape-AssText([string]$Text) {
    return $Text.Replace("\", "\\").Replace("{", "\{").Replace("}", "\}").Replace("`r", " ").Replace("`n", " ")
}

$assPath = Join-Path $buildPath "captions.ass"
$assLines = [Collections.Generic.List[string]]::new()
$assLines.Add("[Script Info]")
$assLines.Add("ScriptType: v4.00+")
$assLines.Add("PlayResX: 1920")
$assLines.Add("PlayResY: 1080")
$assLines.Add("")
$assLines.Add("[V4+ Styles]")
$assLines.Add("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
$assLines.Add("Style: Caption,Segoe UI,37,&H00FFFFFF,&H000000FF,&H00101A2D,&HC0101A2D,0,0,0,0,100,100,0,0,3,1,0,2,170,170,112,1")
$assLines.Add("")
$assLines.Add("[Events]")
$assLines.Add("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

$cursor = 0.0
for ($index = 0; $index -lt $segments.Count; $index++) {
    $segmentStart = $cursor
    $segmentEnd = $cursor + $durations[$index]
    $sentences = [regex]::Split($segments[$index].narration.Trim(), "(?<=[.!?])\s+") | Where-Object { $_.Trim() }
    $weights = $sentences | ForEach-Object { [Math]::Max($_.Length, 1) }
    $weightTotal = ($weights | Measure-Object -Sum).Sum
    $captionCursor = $segmentStart
    for ($sentenceIndex = 0; $sentenceIndex -lt $sentences.Count; $sentenceIndex++) {
        $share = $durations[$index] * ($weights[$sentenceIndex] / $weightTotal)
        $captionEnd = if ($sentenceIndex -eq $sentences.Count - 1) { $segmentEnd } else { $captionCursor + $share }
        $assLines.Add("Dialogue: 0,$(Format-AssTime $captionCursor),$(Format-AssTime $captionEnd),Caption,,0,0,0,,$(Escape-AssText $sentences[$sentenceIndex])")
        $captionCursor = $captionEnd
    }
    $cursor = $segmentEnd
}
[IO.File]::WriteAllLines($assPath, $assLines, [Text.UTF8Encoding]::new($false))

$slideConcatPath = Join-Path $buildPath "slides-concat.txt"
$slideLines = [Collections.Generic.List[string]]::new()
for ($index = 0; $index -lt $segments.Count; $index++) {
    $slidePath = (Join-Path $buildPath ("slide-{0:D2}.png" -f ($index + 1))).Replace("\", "/")
    $slideLines.Add("file '$slidePath'")
    $slideLines.Add("duration $($durations[$index].ToString([Globalization.CultureInfo]::InvariantCulture))")
}
$lastSlide = (Join-Path $buildPath ("slide-{0:D2}.png" -f $segments.Count)).Replace("\", "/")
$slideLines.Add("file '$lastSlide'")
[IO.File]::WriteAllLines($slideConcatPath, $slideLines, [Text.UTF8Encoding]::new($false))

$filter = "fps=24,format=yuv420p,subtitles=video/build/captions.ass"
& $ffmpeg -y -v error -f concat -safe 0 -i $slideConcatPath -i $narrationPath -vf $filter -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 192k -shortest -movflags +faststart $outputPath
if ($LASTEXITCODE -ne 0) { throw "Demo video rendering failed." }

$videoDuration = [double](& $ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $outputPath)
$videoSize = (Get-Item -LiteralPath $outputPath).Length
[pscustomobject]@{
    output = $outputPath
    duration_seconds = [Math]::Round($videoDuration, 2)
    size_bytes = $videoSize
    segments = $segments.Count
    voice = $Voice
    rate = $Rate
} | ConvertTo-Json
