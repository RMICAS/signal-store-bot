import sqlite3
import logging
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional

from .database import Database
from .messaging import MessageProcessor
from .orders import OrderManager
from .products import ProductManager

class SignalStoreBot:
    def __init__(self, db_path: str = "data/store.db"):
        """Initialize the Signal Store Bot"""
        self.db = Database(db_path)
        self.message_processor = MessageProcessor(self.db)
        self.order_manager = OrderManager(self.db)
        self.product_manager = ProductManager(self.db)
        self.logger = logging.getLogger(__name__)
        
        # Initialize database and create sample products
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database and create sample products"""
        try:
            # Check if we need to create sample products
            products = self.product_manager.get_all_products()
            if not products:
                self.logger.info("Creating sample products...")
                from config.settings import SAMPLE_PRODUCTS
                for product_data in SAMPLE_PRODUCTS:
                    self.product_manager.create_product(
                        product_data["name"],
                        product_data["description"],
                        product_data["price"],
                        product_data["stock"]
                    )
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
    
    def is_business_hours(self) -> bool:
        """
        Check if current time is within business hours
        
        Returns:
            bool: True if within business hours, False otherwise
        """
        try:
            from config.settings import ALWAYS_OPEN, BUSINESS_HOURS
            
            # If always open, return True immediately
            if ALWAYS_OPEN:
                return True
            
            # Otherwise check against configured hours
            now = datetime.now().time()
            start_time = BUSINESS_HOURS['start']
            end_time = BUSINESS_HOURS['end']
            
            # Handle the overnight case (end time is next day)
            if start_time > end_time:
                # Current time is either after start_time OR before end_time
                return now >= start_time or now <= end_time
            else:
                # Normal time range
                return start_time <= now <= end_time
                
        except Exception as e:
            self.logger.error(f"Error checking business hours: {e}")
            return False
    
    def get_business_hours_display(self) -> str:
        """Get formatted business hours for display"""
        try:
            from config.settings import ALWAYS_OPEN
            if ALWAYS_OPEN:
                return "🕒 Business Hours: Always Open (24/7)"
        except ImportError:
            pass
        
        from config.settings import BUSINESS_HOURS
        start = BUSINESS_HOURS['start']
        end = BUSINESS_HOURS['end']
        start_str = start.strftime("%I:%M %p")
        end_str = end.strftime("%I:%M %p")
        return f"🕒 Business Hours: {start_str} - {end_str} (Daily)"
    
    def process_signal_message(self, phone_number: str, message: str) -> str:
        """
        Process incoming Signal message and return response
        """
        try:
            # Store original for logging
            original_phone = phone_number
            
            # 1. Check if it's a UUID
            import re
            is_uuid = re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', phone_number, re.IGNORECASE)
            
            if is_uuid:
                cleaned_phone = phone_number # Keep UUID as is
            else:
                # 2. Otherwise clean it like a phone number
                cleaned_phone = self._clean_phone_number(phone_number)
            
            if not cleaned_phone:
                self.logger.warning(f"⚠️  Could not clean phone number: {original_phone}")
                # Try to use original if it looks like a standard international number
                if phone_number and phone_number.strip().startswith('+'):
                    cleaned_phone = phone_number.strip()
                else:
                    return "❌ Invalid phone number format"
            
            # Check if store is open
            if not self.is_business_hours():
                return self._get_offline_response()
            
            # Process the message
            response = self.message_processor.process_message(cleaned_phone, message)
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
            return "❌ An error occurred while processing your message."

    def _clean_phone_number(self, phone_number: str) -> Optional[str]:
        """Clean and validate phone number format"""
        # If it contains letters (and isn't a UUID handled above), it's likely invalid
        # But we only want to strip characters from actual phone numbers
        cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        if cleaned.startswith('+') and 7 < len(cleaned) < 16:
            return cleaned
        return None
    
    def _get_offline_response(self) -> str:
        """Get response for when store is closed"""
        from config.settings import URGENT_CONTACT
        
        response = "🏪 Store Closed\n\n"
        response += self.get_business_hours_display() + "\n\n"
        response += "📨 Your message has been saved and will be processed when we open.\n\n"
        
        if URGENT_CONTACT:
            response += f"🆘 For urgent orders, contact: {URGENT_CONTACT}"
        
        return response
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily statistics for the business"""
        try:
            today = datetime.now().date()
            return self.order_manager.get_daily_stats(today)
        except Exception as e:
            self.logger.error(f"Error getting daily stats: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        self.db.close()

def main():
    """Test the bot functionality"""
    bot = SignalStoreBot()
    
    # Test messages
    test_phone = "+1234567890"
    test_messages = [
        "help",
        "products",
        "order 1 2 John Doe 123 Main St",
        "myorders"
    ]
    
    for msg in test_messages:
        print(f"Input: {msg}")
        response = bot.process_signal_message(test_phone, msg)
        print(f"Output: {response}")
        print("-" * 50)

if __name__ == "__main__":
    main()