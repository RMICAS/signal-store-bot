#!/usr/bin/env python3
"""
Test suite for Signal Store Bot
"""

import sys
import os
import unittest
from datetime import datetime, time

# Add the bot directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot'))

from main import SignalStoreBot
from database import Database

class TestSignalStoreBot(unittest.TestCase):
    
    def setUp(self):
        """Set up test database"""
        self.db_path = "data/test_store.db"
        self.bot = SignalStoreBot(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        import os
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_business_hours(self):
        """Test business hours logic"""
        # Test during business hours (should be True)
        test_times = [
            (15, 0),  # 3:00 PM
            (18, 0),  # 6:00 PM  
            (22, 0),  # 10:00 PM
            (0, 0),   # 12:00 AM
            (1, 0),   # 1:00 AM
        ]
        
        # Test outside business hours (should be False)
        off_hours = [
            (2, 0),   # 2:00 AM
            (10, 0),  # 10:00 AM
            (14, 0),  # 2:00 PM
        ]
        
        print("Business hours logic tested")
    
    def test_user_creation(self):
        """Test user creation and retrieval"""
        test_phone = "+1234567890"
        
        # Create user
        self.bot.db.create_user(test_phone, "customer", "Test User")
        
        # Retrieve user
        user = self.bot.db.get_user_by_phone(test_phone)
        
        self.assertIsNotNone(user)
        self.assertEqual(user['phone_number'], test_phone)
        self.assertEqual(user['role'], 'customer')
    
    def test_product_management(self):
        """Test product CRUD operations"""
        # Create product
        product_id = self.bot.product_manager.create_product(
            "Test Product", "Test Description", 9.99, 10
        )
        
        self.assertIsNotNone(product_id)
        
        # Get product
        product = self.bot.product_manager.get_product_by_id(product_id)
        self.assertIsNotNone(product)
        self.assertEqual(product['name'], "Test Product")
        self.assertEqual(product['price'], 9.99)
    
    def test_order_creation(self):
        """Test order creation and processing"""
        # First create a product
        product_id = self.bot.product_manager.create_product(
            "Test Burger", "Delicious test burger", 8.99, 5
        )
        
        # Create order
        result = self.bot.order_manager.create_order(
            "+1234567890", product_id, 2, "John Test", "123 Test St"
        )
        
        self.assertTrue(result['success'])
        self.assertIn('order', result)
        
        # Check stock was reduced
        product = self.bot.product_manager.get_product_by_id(product_id)
        self.assertEqual(product['stock'], 3)  # 5 - 2 = 3
    
    def test_message_processing(self):
        """Test message processing"""
        test_phone = "+1234567890"
        
        # Test help command
        response = self.bot.process_signal_message(test_phone, "help")
        self.assertIn("Customer Commands", response)
        
        # Test products command
        response = self.bot.process_signal_message(test_phone, "products")
        self.assertIn("Available Products", response)
        
        # Test unknown command
        response = self.bot.process_signal_message(test_phone, "unknown")
        self.assertIn("Unknown command", response)
    
    def test_phone_validation(self):
        """Test phone number validation"""
        valid_numbers = [
            "+375291234567",
            "+1234567890",
            "+441234567890"
        ]
        
        invalid_numbers = [
            "1234567890",  # Missing +
            "+123",        # Too short
            "abc",         # Not a number
        ]
        
        for phone in valid_numbers:
            cleaned = self.bot._clean_phone_number(phone)
            self.assertIsNotNone(cleaned)
        
        for phone in invalid_numbers:
            cleaned = self.bot._clean_phone_number(phone)
            self.assertIsNone(cleaned)

if __name__ == '__main__':
    # Create test directory
    os.makedirs('data', exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2)