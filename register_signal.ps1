# Signal Store Bot - Registration Helper Script
# This script sets JAVA_HOME and runs signal-cli registration commands

param(
    [Parameter(Mandatory=$false)]
    [string]$PhoneNumber = "+258841914996",
    
    [Parameter(Mandatory=$false)]
    [string]$Action = "register",
    
    [Parameter(Mandatory=$false)]
    [string]$Code = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Recipient = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Message = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Captcha = ""
)

Write-Host "Signal Store Bot - Registration Helper" -ForegroundColor Cyan
Write-Host ""

# Check if JAVA_HOME is set and valid
$useExistingJavaHome = $false
if ($env:JAVA_HOME) {
    # Remove trailing backslash if present
    $env:JAVA_HOME = $env:JAVA_HOME.TrimEnd('\')
    
    if (-not (Test-Path $env:JAVA_HOME)) {
        Write-Host "Warning: JAVA_HOME is set to an invalid directory: $env:JAVA_HOME" -ForegroundColor Yellow
        Write-Host "Clearing invalid JAVA_HOME and auto-detecting Java 21..." -ForegroundColor Yellow
        $env:JAVA_HOME = $null
    } elseif ($env:JAVA_HOME -match "jdk-21") {
        # Verify java.exe exists
        $javaExe = Join-Path $env:JAVA_HOME "bin\java.exe"
        if (Test-Path $javaExe) {
            Write-Host "JAVA_HOME is set to Java 21: $env:JAVA_HOME" -ForegroundColor Green
            $useExistingJavaHome = $true
        } else {
            Write-Host "Warning: Java executable not found in JAVA_HOME: $env:JAVA_HOME" -ForegroundColor Yellow
            Write-Host "Auto-detecting Java 21..." -ForegroundColor Yellow
            $env:JAVA_HOME = $null
        }
    } else {
        Write-Host "Warning: JAVA_HOME points to non-Java 21 installation: $env:JAVA_HOME" -ForegroundColor Yellow
        Write-Host "Auto-detecting Java 21..." -ForegroundColor Yellow
        $env:JAVA_HOME = $null
    }
}

# Auto-detect Java 21 installation (only if not using existing valid JAVA_HOME)
if (-not $useExistingJavaHome) {
    $javaHome = $null
    
    # Try specific paths first
    $javaPaths = @(
        "C:\Program Files\Eclipse Adoptium\jdk-21.0.9.10-hotspot",
        "C:\Program Files\Java\jdk-21"
    )

    foreach ($path in $javaPaths) {
        if (Test-Path $path) {
            $javaHome = (Resolve-Path $path).Path
            break
        }
    }

    # Try to find any Java 21 installation in Eclipse Adoptium directory
    if (-not $javaHome) {
        $adoptiumPath = "C:\Program Files\Eclipse Adoptium\"
        if (Test-Path $adoptiumPath) {
            $java21Dirs = Get-ChildItem $adoptiumPath -Directory -Filter "jdk-21*" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($java21Dirs) {
                $javaHome = $java21Dirs.FullName
            }
        }
    }
    
    # Also check Program Files (x86) for 32-bit installations
    if (-not $javaHome) {
        $adoptiumPath86 = "${env:ProgramFiles(x86)}\Eclipse Adoptium\"
        if (Test-Path $adoptiumPath86) {
            $java21Dirs = Get-ChildItem $adoptiumPath86 -Directory -Filter "jdk-21*" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($java21Dirs) {
                $javaHome = $java21Dirs.FullName
            }
        }
    }

    if ($javaHome) {
        # Remove trailing backslash if present
        $javaHome = $javaHome.TrimEnd('\')
        $env:JAVA_HOME = $javaHome
        
        # Verify java.exe exists
        $javaExe = Join-Path $javaHome "bin\java.exe"
        if (-not (Test-Path $javaExe)) {
            Write-Host "ERROR: Java executable not found at: $javaExe" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "JAVA_HOME set to: $javaHome" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Could not auto-detect Java 21. Please set JAVA_HOME manually." -ForegroundColor Red
        Write-Host "Example: `$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-21.0.9.10-hotspot'" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "Running signal-cli command..." -ForegroundColor Cyan
Write-Host ""

# Build the command
$signalCliPath = ".\signal-cli-0.13.22\bin\signal-cli.bat"
$commandArgs = @("-u", $PhoneNumber)

switch ($Action.ToLower()) {
    "register" {
        $commandArgs += "register"
        if ($Captcha) {
            $commandArgs += "--captcha", $Captcha
            Write-Host "Using captcha token for registration..." -ForegroundColor Yellow
        }
        Write-Host "Starting registration for $PhoneNumber..." -ForegroundColor Yellow
        Write-Host "You will receive an SMS verification code." -ForegroundColor Yellow
    }
    "verify" {
        if (-not $Code) {
            Write-Host "ERROR: Verification code is required for 'verify' action." -ForegroundColor Red
            Write-Host "Usage: .\register_signal.ps1 -Action verify -Code YOUR_CODE" -ForegroundColor Yellow
            exit 1
        }
        $commandArgs += "verify", $Code
        Write-Host "Verifying registration with code: $Code" -ForegroundColor Yellow
    }
    "receive" {
        $commandArgs += "receive"
        Write-Host "Checking for messages..." -ForegroundColor Yellow
    }
    "send" {
        if (-not $Recipient -or -not $Message) {
            Write-Host "ERROR: Recipient and message required for 'send' action." -ForegroundColor Red
            Write-Host "Usage: .\register_signal.ps1 -Action send -Recipient +1234567890 -Message 'Your message'" -ForegroundColor Yellow
            exit 1
        }
        $commandArgs += "send", $Recipient, $Message
        Write-Host "Sending message to $Recipient..." -ForegroundColor Yellow
    }
    default {
        Write-Host "ERROR: Unknown action '$Action'. Valid actions: register, verify, receive, send" -ForegroundColor Red
        exit 1
    }
}

# Execute signal-cli
Write-Host "Command: $signalCliPath $($commandArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

try {
    & $signalCliPath $commandArgs
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -and $exitCode -ne $null) {
        Write-Host ""
        Write-Host "Command exited with code: $exitCode" -ForegroundColor Red
        exit $exitCode
    }
} catch {
    Write-Host "ERROR: Failed to execute signal-cli" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

