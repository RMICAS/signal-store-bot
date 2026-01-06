# Signal Store Bot - Signal CLI Installer for Windows
# This script installs signal-cli for Windows

Write-Host "Installing signal-cli for Signal Store Bot..." -ForegroundColor Cyan

# Check if Java is installed
try {
    $javaVersion = java -version 2>&1
    Write-Host "Java found" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Java is required but not installed. Please install Java 11 or higher." -ForegroundColor Red
    Write-Host "   Download from: https://adoptium.net/" -ForegroundColor Yellow
    exit 1
}

# Create installation directory
$installDir = Join-Path $PSScriptRoot "..\signal-cli"
New-Item -ItemType Directory -Force -Path $installDir | Out-Null
Set-Location $installDir

# Download signal-cli
Write-Host "Downloading signal-cli..." -ForegroundColor Cyan
# Try multiple versions in order
$versions = @("0.12.0", "0.11.6", "0.11.5", "0.11.4")
$version = $null
$url = $null
$zipFile = $null

foreach ($v in $versions) {
    $testUrl = "https://github.com/AsamK/signal-cli/releases/download/v${v}/signal-cli-${v}.zip"
    Write-Host "Trying version $v..." -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri $testUrl -Method Head -UseBasicParsing -ErrorAction Stop
        $version = $v
        $url = $testUrl
        $zipFile = "signal-cli-${v}.zip"
        Write-Host "Found version $v, downloading..." -ForegroundColor Green
        break
    } catch {
        # Version not found, try next
        continue
    }
}

if (-not $version) {
    Write-Host "ERROR: Could not find any available signal-cli version" -ForegroundColor Red
    Write-Host "Please check: https://github.com/AsamK/signal-cli/releases" -ForegroundColor Yellow
    exit 1
}

try {
    Invoke-WebRequest -Uri $url -OutFile $zipFile -UseBasicParsing -ErrorAction Stop
    Write-Host "Download complete" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to download signal-cli" -ForegroundColor Red
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Extract
Write-Host "Extracting..." -ForegroundColor Cyan
Expand-Archive -Path $zipFile -DestinationPath . -Force
Remove-Item $zipFile

# Find signal-cli executable
$signalCliPath = Get-ChildItem -Path "signal-cli-${version}" -Recurse -Filter "signal-cli.exe" | Select-Object -First 1

if ($signalCliPath) {
    $fullPath = $signalCliPath.FullName
    Write-Host "signal-cli extracted to: $fullPath" -ForegroundColor Green
    
    # Add to PATH for current session
    $env:Path += ";$($signalCliPath.DirectoryName)"
    
    Write-Host ""
    Write-Host "signal-cli installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. signal-cli is installed at:" -ForegroundColor White
    Write-Host "   $($signalCliPath.DirectoryName)" -ForegroundColor Gray
    Write-Host "   (The bot will auto-detect this location)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Register your bot phone number:" -ForegroundColor White
    Write-Host "   signal-cli.exe -u +258841914996 register" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Verify with SMS code:" -ForegroundColor White
    Write-Host "   signal-cli.exe -u +258841914996 verify YOUR_CODE" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. Test sending a message:" -ForegroundColor White
    Write-Host '   signal-cli.exe -u +258841914996 send +RECIPIENT_NUMBER "Test message"' -ForegroundColor Gray
    Write-Host ""
    Write-Host "5. Update config/settings.py with your BOT_PHONE_NUMBER" -ForegroundColor White
} else {
    Write-Host "ERROR: signal-cli.exe not found in extracted files!" -ForegroundColor Red
    exit 1
}

