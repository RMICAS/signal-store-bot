#!/bin/bash

# Signal Store Bot Setup Script
# Sets up the Python environment and dependencies

set -e

echo "🚀 Setting up Signal Store Bot..."

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "📦 Installing dependencies..."
source venv/bin/activate

# Install requirements
pip install --upgrade pip

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs

# Test the bot
echo "🧪 Testing the bot..."
python start_bot.py

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🎯 Next steps:"
echo "1. Edit config/settings.py with your phone numbers"
echo "2. Install signal-cli: ./scripts/install_signal_cli.sh"
echo "3. Register your bot's Signal number"
echo "4. Run: python start_scheduled.py"
echo ""
echo "📖 For more details, see README.md"