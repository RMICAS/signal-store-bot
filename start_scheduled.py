#!/usr/bin/env python3
"""
Signal Store Bot - Always-On Version
Runs continuously without business hour restrictions.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add the bot directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from bot.main import SignalStoreBot

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
            
            if not BOT_PHONE_NUMBER or BOT_PHONE_NUMBER == "+375XXXXXXXXX":
                logging.warning("⚠️  BOT_PHONE_NUMBER not set in config/settings.py")
                return False
            
            try:
                self.signal_bridge = SignalBridge(BOT_PHONE_NUMBER)
                
                # Test connection (but don't fail if test fails - signal-cli might still work)
                if self.signal_bridge.test_connection():
                    logging.info(f"✅ Signal bridge initialized for {BOT_PHONE_NUMBER}")
                else:
                    logging.warning("⚠️  Signal connection test failed - but continuing anyway (signal-cli might still work)")
                
                # Return True if signal_bridge was created successfully
                return True
                    
            except RuntimeError as e:
                logging.error(f"❌ Signal bridge initialization failed: {e}")
                logging.info("💡 Make sure signal-cli is installed and bot phone is registered")
                return False
                
        except ImportError as e:
            logging.warning(f"⚠️  Signal bridge not available: {e}")
            return False
        except Exception as e:
            logging.error(f"❌ Unexpected error setting up Signal: {e}")
            return False
    
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
                        success = self.signal_bridge.send_message(
                            msg['customer_phone'], 
                            response
                        )
                        if success:
                            logging.info(f"📤 Sent response to offline message from {msg['customer_phone']}")
                        else:
                            logging.error(f"❌ Failed to send response to {msg['customer_phone']}")
                    
                    # Mark as processed
                    self.bot.db.mark_message_processed(msg['id'])
                    
        except Exception as e:
            logging.error(f"❌ Error processing offline messages: {e}")
    
    def message_callback(self, phone, message):
        """Handle incoming Signal messages"""
        try:
            logging.info(f"📨 Received message from {phone}: {message[:100]}")
            
            # Store original phone number before processing
            original_phone = phone
            
            # Process message through bot (this will clean the phone number internally)
            response = self.bot.process_signal_message(phone, message)
            
            if not response:
                logging.warning(f"⚠️  No response generated for message from {phone}")
                return
            
            # Send response back
            if self.signal_bridge:
                # Try to get cleaned phone number from bot, but fall back to original
                # The bot's _clean_phone_number might have cleaned it, but we need to send to original
                # since signal-cli expects the format it originally provided
                send_to_phone = original_phone
                
                # Try cleaning it ourselves to ensure proper format
                cleaned = self.bot._clean_phone_number(original_phone)
                if cleaned:
                    send_to_phone = cleaned
                else:
                    # If cleaning fails, try to fix it manually
                    send_to_phone = original_phone.strip()
                    if not send_to_phone.startswith('+'):
                        send_to_phone = '+' + send_to_phone.lstrip('+')
                
                success = self.signal_bridge.send_message(send_to_phone, response)
                if success:
                    logging.info(f"📤 Successfully sent response to {send_to_phone} (original: {original_phone})")
                else:
                    logging.error(f"❌ Failed to send response to {send_to_phone} (original: {original_phone})")
                    logging.error(f"   Response was: {response[:100]}...")
            else:
                logging.warning(f"⚠️  No signal_bridge available - cannot send response to {phone}")
                
        except Exception as e:
            logging.error(f"❌ Error processing message: {e}", exc_info=True)
            # Try to send error message to user
            if self.signal_bridge:
                try:
                    success = self.signal_bridge.send_message(
                        phone, 
                        "❌ An error occurred processing your message. Please try again later."
                    )
                    if not success:
                        logging.error(f"❌ Also failed to send error message to {phone}")
                except Exception as send_error:
                    logging.error(f"❌ Exception while sending error message: {send_error}")
    
    def run(self):
        """Main bot execution loop"""
        self.is_running = True
        
        logging.info("🚀 Starting Signal Store Bot (24/7 mode)")
        
        # Set up Signal integration
        signal_available = self.setup_signal_integration()
        
        if signal_available and self.signal_bridge:
            logging.info("🏪 Store is OPEN and always accepting messages")
            # Process any offline messages that may have been queued previously
            self.process_offline_messages()
            
            try:
                self.signal_bridge.listen_for_messages(self.message_callback)
                logging.info("👂 Listening for Signal messages...")
            except Exception as listen_error:
                logging.error(f"❌ Failed to start Signal listener: {listen_error}", exc_info=True)
                signal_available = False
        else:
            logging.info("💡 Signal integration not available - message sending/receiving disabled")
        
        try:
            while self.is_running:
                time.sleep(60)
        except KeyboardInterrupt:
            logging.info("🛑 Bot stopped by user")
            self.is_running = False
        except Exception as e:
            logging.error(f"❌ Error in main loop: {e}", exc_info=True)
        finally:
            if self.signal_bridge:
                self.signal_bridge.stop_listening()
            logging.info("🧹 Shutdown complete")

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