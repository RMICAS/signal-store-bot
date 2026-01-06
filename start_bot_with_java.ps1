# Signal Store Bot - Startup Script with Java Configuration
# This script sets JAVA_HOME and starts the bot

Write-Host "Starting Signal Store Bot..." -ForegroundColor Cyan

# Check if JAVA_HOME is set and valid
$useExistingJavaHome = $false
if ($env:JAVA_HOME) {
    if (-not (Test-Path $env:JAVA_HOME)) {
        Write-Host "Warning: JAVA_HOME is set to an invalid directory: $env:JAVA_HOME" -ForegroundColor Yellow
        Write-Host "Clearing invalid JAVA_HOME and auto-detecting Java 21..." -ForegroundColor Yellow
        $env:JAVA_HOME = $null
    } elseif ($env:JAVA_HOME -match "jdk-21") {
        Write-Host "JAVA_HOME is set to Java 21: $env:JAVA_HOME" -ForegroundColor Green
        $useExistingJavaHome = $true
    } else {
        Write-Host "Warning: JAVA_HOME points to non-Java 21 installation: $env:JAVA_HOME" -ForegroundColor Yellow
        Write-Host "Auto-detecting Java 21..." -ForegroundColor Yellow
        $env:JAVA_HOME = $null
    }
}

# Auto-detect Java 21 installation (only if not using existing valid JAVA_HOME)
if (-not $useExistingJavaHome) {
    $javaPaths = @(
        "C:\Program Files\Eclipse Adoptium\jdk-21.0.9.10-hotspot",
        "C:\Program Files\Java\jdk-21",
        "C:\Program Files\Eclipse Adoptium\jdk-21*"
    )

    $javaHome = $null
    foreach ($path in $javaPaths) {
        if (Test-Path $path) {
            $javaHome = (Resolve-Path $path).Path
            break
        }
    }

    # Try to find Java 21 in common locations
    if (-not $javaHome) {
        $java21Dirs = Get-ChildItem "C:\Program Files\Eclipse Adoptium\" -Directory -Filter "jdk-21*" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($java21Dirs) {
            $javaHome = $java21Dirs.FullName
        }
    }

    if ($javaHome) {
        $env:JAVA_HOME = $javaHome
        Write-Host "JAVA_HOME set to: $javaHome" -ForegroundColor Green
    } else {
        Write-Host "Warning: Could not auto-detect Java 21. Please set JAVA_HOME manually." -ForegroundColor Yellow
        Write-Host "Example: `$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.9.10-hotspot'" -ForegroundColor Yellow
    }
}

# Start the bot
Write-Host ""
Write-Host "Starting bot..." -ForegroundColor Cyan
python start_scheduled.py

