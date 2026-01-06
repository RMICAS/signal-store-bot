#!/usr/bin/env python3
"""
Signal Store Bot - Main Entry Point
Run this for testing without Signal integration
"""

import os
import sys
import logging
from pathlib import Path

# Add the bot directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from bot.main import SignalStoreBot
from config.settings import ADMIN_PHONE, URGENT_CONTACT

def setup_logging():
    """Set up logging configuration"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main function to start the bot"""
    print("🚀 Starting Signal Store Bot...")
    print(f"📞 Admin: {ADMIN_PHONE}")
    print(f"🆘 Urgent Contact: {URGENT_CONTACT}")
    print("⏰ Business Hours: 3:00 PM - 1:00 AM")
    print("-" * 50)
    
    setup_logging()
    
    # Initialize the bot
    bot = SignalStoreBot()
    
    print("🤖 Bot initialized successfully!")
    print("💾 Database ready")
    print("📦 Sample products loaded")
    print("\n🎯 Testing bot commands...")
    print("-" * 30)
    
    # Test the bot with sample messages
    test_phone = "+1234567890"
    test_messages = [
        "help",
        "products",
        "order 1 2 John Test 123 Main St",
        "myorders",
        "hours"
    ]
    
    for message in test_messages:
        print(f"📨 Test: {message}")
        response = bot.process_signal_message(test_phone, message)
        print(f"🤖 Response: {response}")
        print("-" * 20)
    
    print("\n✅ Bot is ready for Signal integration!")
    print("🔧 Next steps:")
    print("1. Install signal-cli (see scripts/install_signal_cli.sh)")
    print("2. Register your bot's phone number with Signal")
    print("3. Update config/settings.py with your numbers")
    print("4. Run: python start_scheduled.py")

if __name__ == "__main__":
    main()