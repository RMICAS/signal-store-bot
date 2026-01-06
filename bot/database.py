import sqlite3
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class Database:
    def __init__(self, db_path: str = "data/store.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._create_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            with self._get_connection() as conn:
                # Users table (customers, team members, admins)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        phone_number TEXT UNIQUE NOT NULL,
                        role TEXT DEFAULT 'customer',
                        status TEXT DEFAULT 'active',
                        display_name TEXT,
                        privacy_consent BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Products table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        price DECIMAL(10,2) NOT NULL,
                        stock INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Orders table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_phone TEXT NOT NULL,
                        customer_name TEXT NOT NULL,
                        product_id INTEGER NOT NULL,
                        product_name TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        total_price DECIMAL(10,2) NOT NULL,
                        delivery_address TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        assigned_to TEXT,
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (product_id) REFERENCES products (id)
                    )
                ''')
                
                # Offline messages table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS offline_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        customer_phone TEXT NOT NULL,
                        message TEXT NOT NULL,
                        processed BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                self.logger.info("Database tables created/verified successfully")
                
        except Exception as e:
            self.logger.error(f"Error creating tables: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor"""
        with self._get_connection() as conn:
            return conn.execute(query, params)
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute many queries"""
        with self._get_connection() as conn:
            conn.executemany(query, params_list)
            conn.commit()
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch one row"""
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        pass  # SQLite handles connection closing automatically
    
    # User management methods
    def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user by phone number"""
        return self.fetch_one(
            "SELECT * FROM users WHERE phone_number = ?", 
            (phone_number,)
        )
    
    def create_user(self, phone_number: str, role: str = "customer", 
                   display_name: str = None) -> bool:
        """Create a new user"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO users (phone_number, role, display_name) VALUES (?, ?, ?)",
                    (phone_number, role, display_name)
                )
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            return False
    
    # Product management methods
    def get_all_products(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all products"""
        query = "SELECT * FROM products"
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY name"
        return self.fetch_all(query)
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get product by ID"""
        return self.fetch_one(
            "SELECT * FROM products WHERE id = ? AND is_active = TRUE", 
            (product_id,)
        )
    
    # Order management methods
    def create_order(self, order_data: Dict[str, Any]) -> bool:
        """Create a new order"""
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT INTO orders 
                    (customer_phone, customer_name, product_id, product_name, 
                     quantity, total_price, delivery_address, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order_data['customer_phone'],
                    order_data['customer_name'],
                    order_data['product_id'],
                    order_data['product_name'],
                    order_data['quantity'],
                    order_data['total_price'],
                    order_data['delivery_address'],
                    order_data.get('status', 'pending')
                ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            return False
    
    def get_orders_by_phone(self, phone_number: str) -> List[Dict[str, Any]]:
        """Get orders by customer phone"""
        return self.fetch_all(
            "SELECT * FROM orders WHERE customer_phone = ? ORDER BY created_at DESC",
            (phone_number,)
        )
    
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """Get all pending orders"""
        return self.fetch_all(
            "SELECT * FROM orders WHERE status = 'pending' ORDER BY created_at DESC"
        )
    
    # Offline messages management
    def save_offline_message(self, phone_number: str, message: str) -> bool:
        """Save offline message"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO offline_messages (customer_phone, message) VALUES (?, ?)",
                    (phone_number, message)
                )
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error saving offline message: {e}")
            return False
    
    def get_offline_messages(self, unprocessed_only: bool = True) -> List[Dict[str, Any]]:
        """Get offline messages"""
        query = "SELECT * FROM offline_messages"
        if unprocessed_only:
            query += " WHERE processed = FALSE"
        query += " ORDER BY created_at"
        return self.fetch_all(query)
    
    def mark_message_processed(self, message_id: int) -> bool:
        """Mark message as processed"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE offline_messages SET processed = TRUE WHERE id = ?",
                    (message_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error marking message processed: {e}")
            return False