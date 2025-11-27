"""
Configuration settings for Signal Store Bot
"""

# Signal Configuration
BOT_PHONE_NUMBER = "+375XXXXXXXXX"  # Your bot's Signal number
ADMIN_PHONE = "+375291234567"       # Your admin number
URGENT_CONTACT = "+375291234567"    # Contact for urgent orders

# Business Hours (3:00 PM - 1:00 AM)
from datetime import time
BUSINESS_HOURS = {
    "start": time(15, 0),  # 3:00 PM
    "end": time(1, 0)      # 1:00 AM (next day)
}

# Database Configuration
DATABASE_PATH = "data/store.db"

# Application Settings
APP_NAME = "Signal Store Bot"
VERSION = "1.0.0"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Sample Products (will be created on first run)
SAMPLE_PRODUCTS = [
    {
        "name": "Pizza Margherita",
        "description": "Classic pizza with tomato sauce and mozzarella",
        "price": 12.99,
        "stock": 20
    },
    {
        "name": "Chicken Burger",
        "description": "Juicy chicken burger with fries",
        "price": 8.99,
        "stock": 15
    },
    {
        "name": "Caesar Salad",
        "description": "Fresh salad with chicken and Caesar dressing",
        "price": 7.99,
        "stock": 10
    },
    {
        "name": "Chocolate Cake",
        "description": "Rich chocolate cake slice",
        "price": 4.99,
        "stock": 8
    }
]