# Quick Setup Guide

## Step 1: Install Java (Required)

signal-cli requires Java 11 or higher.

**Download Java:**
1. Go to: https://adoptium.net/temurin/releases/
2. Select:
   - **Version:** 17 LTS or 21 LTS
   - **Operating System:** Windows
   - **Architecture:** x64
   - **Package Type:** JDK (or JRE)
3. Download and run the installer
4. **Important:** Check "Add to PATH" during installation
5. **Restart PowerShell** after installation

**Verify:**
```powershell
java -version
```

## Step 2: Install signal-cli

Once Java is installed, run:

```powershell
.\scripts\install_signal_cli.ps1
```

Or manually:
1. Download from: https://github.com/AsamK/signal-cli/releases/download/v0.11.6/signal-cli-0.11.6.zip
2. Extract to a folder (e.g., `C:\signal-cli`)
3. Add `signal-cli-0.11.6\bin` to your PATH

## Step 3: Register Your Phone

```powershell
signal-cli -u +258841914996 register
# Wait for SMS code, then:
signal-cli -u +258841914996 verify YOUR_CODE
```

## Step 4: Run Bot

```powershell
python start_scheduled.py
```

