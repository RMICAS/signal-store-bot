#!/bin/bash

# Signal Store Bot - Signal CLI Installer
# This script installs signal-cli for Linux/Mac

set -e

echo "🚀 Installing signal-cli for Signal Store Bot..."

# Check if Java is installed
if ! command -v java &> /dev/null; then
    echo "❌ Java is required but not installed. Please install Java 11 or higher."
    exit 1
fi

# Create installation directory
mkdir -p signal-cli
cd signal-cli

# Download signal-cli
echo "📥 Downloading signal-cli..."
VERSION="0.11.6"
wget -q "https://github.com/AsamK/signal-cli/releases/download/v${VERSION}/signal-cli-${VERSION}.tar.gz"

# Extract
echo "📦 Extracting..."
tar xf signal-cli-${VERSION}.tar.gz

# Create symlink
sudo ln -sf "$(pwd)/signal-cli-${VERSION}/bin/signal-cli" /usr/local/bin/signal-cli

# Verify installation
if command -v signal-cli &> /dev/null; then
    echo "✅ signal-cli installed successfully!"
    echo "📋 Version: $(signal-cli --version)"
    echo ""
    echo "📝 Next steps:"
    echo "1. Register your bot's phone number:"
    echo "   signal-cli -u +375XXXXXXXXX register"
    echo "2. Verify with SMS code:"
    echo "   signal-cli -u +375XXXXXXXXX verify YOUR_CODE"
    echo "3. Test sending a message:"
    echo "   signal-cli -u +375XXXXXXXXX send +1234567890 'Test message'"
else
    echo "❌ Installation failed!"
    exit 1
fi