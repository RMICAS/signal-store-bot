# Signal CLI Setup Guide for Windows

Complete guide to install and register signal-cli for your Signal Store Bot.

## Prerequisites

### Step 1: Install Java

signal-cli requires Java 11 or higher.

1. **Download Java:**
   - Go to: https://adoptium.net/temurin/releases/
   - Select:
     - Version: **17 LTS** or **21 LTS** (recommended)
     - Operating System: **Windows**
     - Architecture: **x64**
     - Package Type: **JDK** or **JRE**
   
2. **Install Java:**
   - Run the downloaded installer
   - Follow the installation wizard
   - Make sure to check "Add to PATH" if the option appears

3. **Verify Installation:**
   ```powershell
   java -version
   ```
   You should see something like: `openjdk version "17.0.x"` or similar

### Step 2: Install signal-cli

**Option A: Using the Installation Script (Recommended)**

1. Open PowerShell in the project directory
2. Run:
   ```powershell
   .\scripts\install_signal_cli.ps1
   ```

**Option B: Manual Installation**

1. **Download signal-cli:**
   - Go to: https://github.com/AsamK/signal-cli/releases
   - Download: `signal-cli-0.11.6.zip` (or latest version)

2. **Extract:**
   - Extract to a folder (e.g., `C:\signal-cli`)
   - Navigate to: `signal-cli-0.11.6\bin\`

3. **Add to PATH (Optional but Recommended):**
   - Copy the full path to `bin` folder (e.g., `C:\signal-cli\signal-cli-0.11.6\bin`)
   - Add to Windows PATH:
     - Search "Environment Variables" in Windows
     - Edit "Path" variable
     - Add the bin folder path

4. **Verify Installation:**
   ```powershell
   signal-cli --version
   ```
   Or if not in PATH:
   ```powershell
   C:\signal-cli\signal-cli-0.11.6\bin\signal-cli.exe --version
   ```

## Step 3: Register Your Phone Number

### Registration Process

1. **Start Registration:**
   ```powershell
   signal-cli -u +258841914996 register
   ```
   
   **Note:** If signal-cli is not in PATH, use full path:
   ```powershell
   C:\signal-cli\signal-cli-0.11.6\bin\signal-cli.exe -u +258841914996 register
   ```

2. **Wait for SMS:**
   - Signal will send an SMS verification code to +258841914996
   - This may take 1-2 minutes
   - The code will be a 6-digit number

3. **Verify with Code:**
   ```powershell
   signal-cli -u +258841914996 verify YOUR_6_DIGIT_CODE
   ```
   
   Example:
   ```powershell
   signal-cli -u +258841914996 verify 123456
   ```

4. **Verify Registration:**
   ```powershell
   signal-cli -u +258841914996 listAccounts
   ```
   
   You should see your phone number listed.

### Alternative: Link with Existing Signal Account

If you already have Signal on your phone, you can link signal-cli:

1. **Generate QR Code:**
   ```powershell
   signal-cli -u +258841914996 link -n "Signal Store Bot"
   ```
   
   This will display a QR code in the terminal.

2. **Scan with Signal App:**
   - Open Signal app on your phone
   - Go to: **Settings** → **Linked Devices** → **Link New Device**
   - Scan the QR code displayed in terminal

3. **Verify:**
   ```powershell
   signal-cli -u +258841914996 listAccounts
   ```

## Step 4: Test Your Setup

1. **Test Sending a Message:**
   ```powershell
   signal-cli -u +258841914996 send +RECIPIENT_NUMBER "Test message from bot"
   ```
   Replace `+RECIPIENT_NUMBER` with a phone number that has Signal.

2. **Test Receiving Messages:**
   ```powershell
   signal-cli -u +258841914996 receive
   ```
   This will check for new messages.

## Step 5: Start Your Bot

Once registration is complete:

```powershell
python start_scheduled.py
```

The bot will:
- Test the Signal connection automatically
- Start listening for messages during business hours (3 PM - 1 AM)
- Process orders and respond automatically

## Troubleshooting

### "signal-cli not found"
- Make sure signal-cli is installed
- Use full path: `C:\path\to\signal-cli.exe`
- Or add signal-cli to your PATH

### "Java not found"
- Install Java from https://adoptium.net/
- Restart PowerShell after installation
- Verify with: `java -version`

### "Registration failed"
- Make sure your phone number is correct (E.164 format: +258841914996)
- Check that you can receive SMS on that number
- Try the linking method instead if SMS doesn't work

### "Verification code expired"
- Request a new code by running `register` again
- Codes expire after a few minutes

### "Already registered"
- If the number is already registered, you may need to unregister first:
  ```powershell
  signal-cli -u +258841914996 unregister
  ```
- Then register again

## Need Help?

- Signal CLI Documentation: https://github.com/AsamK/signal-cli
- Signal CLI Issues: https://github.com/AsamK/signal-cli/issues

