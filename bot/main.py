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
        Check if current time is within business hours (3:00 PM - 1:00 AM)
        
        Returns:
            bool: True if within business hours, False otherwise
        """
        try:
            now = datetime.now().time()
            start_time = time(15, 0)  # 3:00 PM
            end_time = time(1, 0)     # 1:00 AM
            
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
        return "🕒 Business Hours: 3:00 PM - 1:00 AM (Daily)"
    
    def process_signal_message(self, phone_number: str, message: str) -> str:
        """
        Process incoming Signal message and return response
        
        Args:
            phone_number: Sender's phone number
            message: Incoming message text
            
        Returns:
            str: Response message
        """
        try:
            # Clean and validate phone number
            phone_number = self._clean_phone_number(phone_number)
            if not phone_number:
                return "❌ Invalid phone number format"
            
            # Check if store is open
            if not self.is_business_hours():
                return self._get_offline_response()
            
            # Process the message
            response = self.message_processor.process_message(phone_number, message)
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return "❌ An error occurred while processing your message. Please try again."
    
    def _clean_phone_number(self, phone_number: str) -> Optional[str]:
        """Clean and validate phone number format"""
        # Remove any non-digit characters except +
        cleaned = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        
        # Basic validation - should start with + and have reasonable length
        if cleaned.startswith('+') and len(cleaned) > 7 and len(cleaned) < 16:
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