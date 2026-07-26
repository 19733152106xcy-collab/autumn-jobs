$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$url = "http://127.0.0.1:8765"
$healthUrl = "$url/data/update_status.json"

function Test-JobSiteRunning {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (-not (Test-Path $python)) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Python environment not found. Install the project dependencies first.",
        "2027 Autumn Jobs",
        "OK",
        "Error"
    ) | Out-Null
    exit 1
}

if (-not (Test-JobSiteRunning)) {
    $runtimeDir = Join-Path $projectRoot "data\runtime"
    New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
    Start-Process -FilePath $python `
        -ArgumentList "-m", "http.server", "8765", "--directory", "site" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $runtimeDir "site-server.log") `
        -RedirectStandardError (Join-Path $runtimeDir "site-server-error.log")

    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        Start-Sleep -Milliseconds 250
        if (Test-JobSiteRunning) { break }
    }
}

$refreshUrl = "$url/?refresh=$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())"
Start-Process $refreshUrl
