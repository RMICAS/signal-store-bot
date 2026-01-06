import logging
from typing import Dict, Any, List, Optional

class ProductManager:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def get_all_products(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all products"""
        try:
            return self.db.get_all_products(active_only)
        except Exception as e:
            self.logger.error(f"Error getting products: {e}")
            return []
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get product by ID"""
        try:
            return self.db.get_product_by_id(product_id)
        except Exception as e:
            self.logger.error(f"Error getting product: {e}")
            return None
    
    def create_product(self, name: str, description: str, price: float, stock: int) -> Optional[int]:
        """Create a new product"""
        try:
            with self.db._get_connection() as conn:
                cursor = conn.execute(
                    "INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)",
                    (name, description, price, stock)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"Error creating product: {e}")
            return None
    
    def update_product(self, product_id: int, name: str, description: str, 
                      price: float, stock: int) -> bool:
        """Update existing product"""
        try:
            with self.db._get_connection() as conn:
                result = conn.execute(
                    "UPDATE products SET name = ?, description = ?, price = ?, stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (name, description, price, stock, product_id)
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating product: {e}")
            return False
    
    def delete_product(self, product_id: int) -> bool:
        """Soft delete product"""
        try:
            with self.db._get_connection() as conn:
                result = conn.execute(
                    "UPDATE products SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (product_id,)
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting product: {e}")
            return False
    
    def restock_product(self, product_id: int, quantity: int) -> bool:
        """Restock product"""
        try:
            with self.db._get_connection() as conn:
                result = conn.execute(
                    "UPDATE products SET stock = stock + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (quantity, product_id)
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error restocking product: {e}")
            return False
    
    def update_stock(self, product_id: int, new_stock: int) -> bool:
        """Update product stock"""
        try:
            with self.db._get_connection() as conn:
                result = conn.execute(
                    "UPDATE products SET stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_stock, product_id)
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating stock: {e}")
            return False