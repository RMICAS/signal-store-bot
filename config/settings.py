"""
Configuration settings for Signal Store Bot
"""

from datetime import time
import platform

# Signal Configuration
BOT_PHONE_NUMBER = "+351922282749"  # Your bot's Signal number
ADMIN_PHONE = "+351922282749"       # Your admin number
URGENT_CONTACT = "+351922282749"    # Contact for urgent orders

# Business Hours - Set to always open (24/7)
# To set specific hours, change ALWAYS_OPEN to False and set start/end times
ALWAYS_OPEN = True
BUSINESS_HOURS = {
    "start": time(0, 0),   # 12:00 AM (midnight)
    "end": time(23, 59)   # 11:59 PM (end of day)
}

# Signal-cli behavior tweaks
# Set to True to force JSON mode, False to force plain-text, or None to auto-detect.
ENABLE_SIGNAL_JSON_RECEIVE = True

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