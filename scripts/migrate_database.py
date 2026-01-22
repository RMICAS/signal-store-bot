#!/usr/bin/env python3
"""
Database Migration Script
Adds support for multi-product orders and admin chat features
"""

import sqlite3
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database(db_path: str = "data/store.db"):
    """Add new tables for multi-product orders and admin chat"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        logger.info("Starting database migration...")
        
        # Create order_items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                subtotal DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        logger.info("✅ Created order_items table")
        
        # Create conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_phone TEXT NOT NULL,
                customer_name TEXT,
                admin_phone TEXT,
                status TEXT DEFAULT 'open',
                assigned_to TEXT,
                last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_admin_read_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("✅ Created conversations table")
        
        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                sender_phone TEXT NOT NULL,
                recipient_phone TEXT NOT NULL,
                message_text TEXT NOT NULL,
                direction TEXT NOT NULL,
                delivery_status TEXT,
                is_admin BOOLEAN DEFAULT FALSE,
                order_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations (id),
                FOREIGN KEY (order_id) REFERENCES orders (id)
            )
        ''')
        logger.info("✅ Created messages table")

        # Event log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                entity_type TEXT,
                entity_id TEXT,
                severity TEXT DEFAULT 'info',
                message TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("✅ Created event_logs table")

        # Quick replies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quick_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                template TEXT NOT NULL,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("✅ Created quick_replies table")

        # System status table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_status (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        logger.info("✅ Created system_status table")
        
        # Add total_items to orders if not exists
        try:
            cursor.execute('ALTER TABLE orders ADD COLUMN total_items INTEGER DEFAULT 1')
            logger.info("✅ Added total_items column to orders")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                logger.info("ℹ️  total_items column already exists")
            else:
                raise

        # Add payment_status to orders if not exists
        try:
            cursor.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'unpaid'")
            logger.info("✅ Added payment_status column to orders")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                logger.info("ℹ️  payment_status column already exists")
            else:
                raise
        
        # Add tags to users if not exists
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN tags TEXT')
            logger.info("✅ Added tags column to users")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                logger.info("ℹ️  tags column already exists")
            else:
                raise

        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_sender 
            ON messages(sender_phone)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_order_items_order 
            ON order_items(order_id)
        ''')
        logger.info("✅ Created indexes")
        
        conn.commit()
        conn.close()
        logger.info("✅ Database migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during migration: {e}")
        return False

if __name__ == "__main__":
    import os
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "store.db")
    migrate_database(db_path)

