# Register Your Phone Number with Signal

Your phone number `+258841914996` needs to be registered with Signal before the bot can work.

## Registration Steps

### Step 1: Start Registration

Open PowerShell in this directory and run:

```powershell
.\register_signal.ps1
```

Or manually specify the phone number:

```powershell
.\register_signal.ps1 -PhoneNumber +258841914996
```

**Note:** The script automatically detects and sets JAVA_HOME to Java 21, so you don't need to set it manually.

This will send an SMS verification code to your phone number.

### Step 2: Verify with SMS Code

After receiving the SMS code, run:

```powershell
.\register_signal.ps1 -Action verify -Code YOUR_CODE
```

Replace `YOUR_CODE` with the 6-digit code you received via SMS.

### Step 3: Verify Registration

Check if registration was successful:

```powershell
.\register_signal.ps1 -Action receive
```

If you see no errors, registration is complete!

### Step 4: Test Sending a Message

Test sending a message to yourself or another number:

```powershell
.\register_signal.ps1 -Action send -Recipient +RECIPIENT_NUMBER -Message "Test message"
```

## Manual Method (Alternative)

If you prefer to run signal-cli directly, you can set JAVA_HOME manually:

```powershell
# Set JAVA_HOME (if not already set)
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-21.0.9.10-hotspot"

# Start registration
.\signal-cli-0.13.22\bin\signal-cli.bat -u +258841914996 register
```

## Alternative: Link with Signal Desktop

If you prefer, you can link signal-cli with your Signal Desktop app:

```powershell
.\signal-cli-0.13.22\bin\signal-cli.bat -u +258841914996 link --name "Signal Store Bot"
```

This will generate a QR code that you can scan with Signal Desktop.

## After Registration

Once registered, you can start your bot:

```powershell
.\start_bot_with_java.ps1
```

Or manually:

```powershell
$env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-21.0.9.10-hotspot"
python start_scheduled.py
```

## Troubleshooting

- **"User is not registered"**: Complete the registration steps above
- **"JAVA_HOME is invalid"**: Make sure JAVA_HOME points to Java 21 installation
- **"SMS code not received"**: Check your phone number and try again after a few minutes

