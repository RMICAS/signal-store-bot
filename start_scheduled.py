#!/usr/bin/env python3
"""
Signal Store Bot - Scheduled Version
Run this for production with business hours enforcement
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime, time as dt_time
from pathlib import Path

# Add the bot directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from bot.main import SignalStoreBot
from config.settings import BUSINESS_HOURS

class ScheduledBot:
    def __init__(self):
        self.bot = SignalStoreBot()
        self.is_running = False
        self.signal_bridge = None
        
    def setup_signal_integration(self):
        """Set up Signal messaging bridge"""
        try:
            # Import and initialize Signal bridge
            from bot.signal_bridge import SignalBridge
            from config.settings import BOT_PHONE_NUMBER
            
            if BOT_PHONE_NUMBER:
                self.signal_bridge = SignalBridge(BOT_PHONE_NUMBER)
                logging.info(f"✅ Signal bridge initialized for {BOT_PHONE_NUMBER}")
                return True
            else:
                logging.warning("⚠️  BOT_PHONE_NUMBER not set in config")
                return False
                
        except ImportError:
            logging.warning("⚠️  Signal bridge not available - running in test mode")
            return False
    
    def is_business_hours(self):
        """Check if current time is within business hours"""
        now = datetime.now().time()
        start = BUSINESS_HOURS['start']
        end = BUSINESS_HOURS['end']
        
        # Handle overnight hours (end time is next day)
        if end < start:
            return now >= start or now <= end
        else:
            return start <= now <= end
    
    def process_offline_messages(self):
        """Process messages received outside business hours"""
        try:
            offline_messages = self.bot.db.get_offline_messages()
            if offline_messages:
                logging.info(f"📨 Processing {len(offline_messages)} offline messages")
                
                for msg in offline_messages:
                    response = self.bot.process_signal_message(
                        msg['customer_phone'], 
                        msg['message']
                    )
                    
                    # Send response if Signal is available
                    if self.signal_bridge:
                        self.signal_bridge.send_message(
                            msg['customer_phone'], 
                            response
                        )
                    
                    # Mark as processed
                    self.bot.db.mark_message_processed(msg['id'])
                    
        except Exception as e:
            logging.error(f"❌ Error processing offline messages: {e}")
    
    def start_business_day(self):
        """Start business day operations"""
        logging.info("🏪 Starting business day - Store is OPEN")
        
        # Process any offline messages from after-hours
        self.process_offline_messages()
        
        # Start Signal listening if available
        if self.signal_bridge:
            self.signal_bridge.listen_for_messages(self.message_callback)
            logging.info("👂 Listening for Signal messages...")
    
    def end_business_day(self):
        """End business day operations"""
        logging.info("🚪 Ending business day - Store is CLOSED")
        
        # Stop Signal listening
        if self.signal_bridge:
            self.signal_bridge.stop_listening()
    
    def message_callback(self, phone, message):
        """Handle incoming Signal messages"""
        try:
            logging.info(f"📨 Received message from {phone}: {message}")
            
            # Process message through bot
            response = self.bot.process_signal_message(phone, message)
            
            # Send response back
            if self.signal_bridge and response:
                self.signal_bridge.send_message(phone, response)
                logging.info(f"📤 Sent response to {phone}")
                
        except Exception as e:
            logging.error(f"❌ Error processing message: {e}")
    
    def run(self):
        """Main bot execution loop"""
        self.is_running = True
        last_business_status = None
        
        logging.info("🚀 Starting Scheduled Signal Store Bot")
        
        # Set up Signal integration
        signal_available = self.setup_signal_integration()
        
        if not signal_available:
            logging.info("💡 Running in test mode - Signal integration not available")
        
        while self.is_running:
            try:
                current_business_status = self.is_business_hours()
                
                # Check if business status changed
                if last_business_status != current_business_status:
                    if current_business_status:
                        self.start_business_day()
                    else:
                        self.end_business_day()
                    
                    last_business_status = current_business_status
                
                # Sleep for 1 minute before checking again
                time.sleep(60)
                
            except KeyboardInterrupt:
                logging.info("🛑 Bot stopped by user")
                self.is_running = False
            except Exception as e:
                logging.error(f"❌ Error in main loop: {e}")
                time.sleep(60)  # Wait before retrying
        
        # Cleanup
        self.end_business_day()

def main():
    """Main function"""
    # Set up logging
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create data directory
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # Start the bot
    bot = ScheduledBot()
    bot.run()

if __name__ == "__main__":
    main()