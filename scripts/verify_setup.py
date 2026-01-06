#!/usr/bin/env python3
"""
Verify Signal Store Bot Setup
Checks if all dependencies and configurations are correct
"""

import sys
import subprocess
import os
from pathlib import Path

def check_python():
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 7:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python 3.7+ required, found {version.major}.{version.minor}")
        return False

def check_java():
    """Check if Java is installed"""
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        print("✅ Java is installed")
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("❌ Java not found. Install Java 11+ from https://adoptium.net/")
        return False

def check_signal_cli():
    """Check if signal-cli is available"""
    candidates = ["signal-cli", "signal-cli.exe"]
    
    for candidate in candidates:
        try:
            result = subprocess.run(
                [candidate, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✅ signal-cli found: {result.stdout.strip()}")
                return True
        except:
            continue
    
    print("❌ signal-cli not found")
    print("   Install using: bash scripts/install_signal_cli.sh (Linux/Mac)")
    print("   or: .\\scripts\\install_signal_cli.ps1 (Windows)")
    return False

def check_config():
    """Check configuration file"""
    config_path = Path("config/settings.py")
    if not config_path.exists():
        print("❌ config/settings.py not found")
        return False
    
    # Read and check for placeholder values
    with open(config_path, 'r') as f:
        content = f.read()
        if "+375XXXXXXXXX" in content:
            print("⚠️  BOT_PHONE_NUMBER not configured in config/settings.py")
            return False
    
    print("✅ Configuration file exists")
    return True

def check_directories():
    """Check if required directories exist"""
    dirs = ["data", "logs", "bot", "config"]
    all_exist = True
    
    for dir_name in dirs:
        if Path(dir_name).exists():
            print(f"✅ {dir_name}/ directory exists")
        else:
            print(f"⚠️  {dir_name}/ directory missing (will be created on first run)")
            all_exist = False
    
    return True  # Not critical, will be created

def main():
    """Run all checks"""
    print("🔍 Verifying Signal Store Bot Setup...\n")
    
    checks = [
        ("Python", check_python),
        ("Java", check_java),
        ("signal-cli", check_signal_cli),
        ("Configuration", check_config),
        ("Directories", check_directories),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        results.append(check_func())
    
    print("\n" + "="*50)
    print("📊 Summary:")
    print("="*50)
    
    if all(results[:3]):  # Python, Java, signal-cli are critical
        print("✅ Core dependencies are ready!")
        print("\n📝 Next steps:")
        print("1. Register your bot phone: signal-cli -u +NUMBER register")
        print("2. Update config/settings.py with your phone numbers")
        print("3. Run: python start_scheduled.py")
    else:
        print("❌ Some dependencies are missing. Please install them first.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())







