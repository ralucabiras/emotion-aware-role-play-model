param(
    [Parameter(Mandatory = $true)]
    [string]$Destination,
    [string]$Bucket = "affectlab-research-raluca-biras"
)

$ErrorActionPreference = "Stop"
$resolved = [System.IO.Path]::GetFullPath($Destination)
if ([System.IO.Path]::GetPathRoot($resolved) -eq $resolved) {
    throw "Destination must not be a filesystem root"
}

$text = Join-Path $resolved "text"
$audio = Join-Path $resolved "audio"
New-Item -ItemType Directory -Force -Path $text, $audio | Out-Null
gcloud storage rsync --recursive "gs://$Bucket/models/iemocap-benchmark4-final-v1/text/model" $text
if ($LASTEXITCODE -ne 0) { throw "Text model synchronization failed" }
gcloud storage rsync --recursive "gs://$Bucket/models/iemocap-benchmark4-final-v1/audio/model" $audio
if ($LASTEXITCODE -ne 0) { throw "Audio model synchronization failed" }

Write-Output "Models synchronized to $resolved"
Write-Output "Set MULTIMODAL_TEXT_MODEL_DIR=$text"
Write-Output "Set MULTIMODAL_AUDIO_MODEL_DIR=$audio"
