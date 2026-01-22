import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional

class OrderManager:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    def create_order(self, customer_phone: str, product_id: int, quantity: int,
                    customer_name: str, delivery_address: str) -> Dict[str, Any]:
        """Create a new order"""
        try:
            # Get product details
            product = self.db.get_product_by_id(product_id)
            if not product:
                return {
                    'success': False,
                    'message': 'Product not found'
                }
            
            # Check stock availability
            if product['stock'] < quantity:
                return {
                    'success': False,
                    'message': f'Insufficient stock. Only {product["stock"]} available'
                }
            
            # Calculate total price
            total_price = product['price'] * quantity
            
            # Create order data
            order_data = {
                'customer_phone': customer_phone,
                'customer_name': customer_name,
                'product_id': product_id,
                'product_name': product['name'],
                'quantity': quantity,
                'total_price': total_price,
                'delivery_address': delivery_address,
                'status': 'pending'
            }
            
            # Save order to database
            success = self.db.create_order(order_data)
            
            if success:
                self.db.set_user_display_name(customer_phone, customer_name)
                self.db.update_conversation_customer_name(customer_phone, customer_name)

                # Update product stock
                new_stock = product['stock'] - quantity
                self.db.execute_query(
                    "UPDATE products SET stock = ? WHERE id = ?",
                    (new_stock, product_id)
                )
                
                # Get the created order
                orders = self.db.get_orders_by_phone(customer_phone)
                latest_order = orders[0] if orders else order_data

                self.db.log_event(
                    event_type="order_created",
                    entity_type="order",
                    entity_id=str(latest_order.get("id", "")),
                    message="Order created",
                    metadata={
                        "customer_phone": customer_phone,
                        "total_price": float(latest_order.get("total_price", 0))
                    }
                )
                
                return {
                    'success': True,
                    'order': latest_order,
                    'message': 'Order created successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to create order'
                }
                
        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            return {
                'success': False,
                'message': 'An error occurred while creating order'
            }
    
    def get_user_orders(self, phone_number: str) -> List[Dict[str, Any]]:
        """Get all orders for a user"""
        try:
            return self.db.get_orders_by_phone(phone_number)
        except Exception as e:
            self.logger.error(f"Error getting user orders: {e}")
            return []
    
    def update_order_status(self, order_id: int, new_status: str, 
                           updated_by: str = None) -> bool:
        """Update order status"""
        try:
            with self.db._get_connection() as conn:
                result = conn.execute(
                    "UPDATE orders SET status = ?, assigned_to = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_status, updated_by, order_id)
                )
                conn.commit()
                if result.rowcount > 0:
                    self.db.log_event(
                        event_type="order_status_updated",
                        entity_type="order",
                        entity_id=str(order_id),
                        message=f"Order status updated to {new_status}",
                        metadata={"updated_by": updated_by}
                    )
                return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating order status: {e}")
            return False
    
    def get_daily_stats(self, target_date: date = None) -> Dict[str, Any]:
        """Get daily statistics"""
        if target_date is None:
            target_date = datetime.now().date()
        
        try:
            # Convert date to string for SQL query
            date_str = target_date.strftime('%Y-%m-%d')
            
            # Get total orders for the day
            total_orders = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM orders WHERE DATE(created_at) = ?",
                (date_str,)
            )['count']
            
            # Get pending orders
            pending_orders = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM orders WHERE DATE(created_at) = ? AND status = 'pending'",
                (date_str,)
            )['count']
            
            # Get completed orders (delivered)
            completed_orders = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM orders WHERE DATE(created_at) = ? AND status = 'delivered'",
                (date_str,)
            )['count']
            
            # Get total revenue
            revenue_result = self.db.fetch_one(
                "SELECT SUM(total_price) as total FROM orders WHERE DATE(created_at) = ? AND status = 'delivered'",
                (date_str,)
            )
            total_revenue = revenue_result['total'] or 0
            
            # Calculate average order value
            average_order_value = total_revenue / completed_orders if completed_orders > 0 else 0
            
            return {
                'total_orders': total_orders,
                'pending_orders': pending_orders,
                'completed_orders': completed_orders,
                'total_revenue': total_revenue,
                'average_order_value': average_order_value,
                'date': date_str
            }
            
        except Exception as e:
            self.logger.error(f"Error getting daily stats: {e}")
            return {
                'total_orders': 0,
                'pending_orders': 0,
                'completed_orders': 0,
                'total_revenue': 0,
                'average_order_value': 0,
                'date': target_date.strftime('%Y-%m-%d')
            }
    
    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        try:
            return self.db.fetch_one(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,)
            )
        except Exception as e:
            self.logger.error(f"Error getting order: {e}")
            return None
    
    def create_multi_product_order(self, customer_phone: str, customer_name: str,
                                   delivery_address: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create order with multiple products
        items: [{'product_id': 1, 'quantity': 2}, {'product_id': 3, 'quantity': 1}]
        """
        try:
            if not items:
                return {'success': False, 'message': 'No items in order'}
            
            total_price = 0
            order_items = []
            
            # Validate all products and calculate totals
            for item in items:
                product = self.db.get_product_by_id(item['product_id'])
                if not product:
                    return {'success': False, 'message': f"Product {item['product_id']} not found"}
                
                if product['stock'] < item['quantity']:
                    return {'success': False, 
                           'message': f"Insufficient stock for {product['name']}. Only {product['stock']} available"}
                
                subtotal = product['price'] * item['quantity']
                total_price += subtotal
                
                order_items.append({
                    'product_id': item['product_id'],
                    'product_name': product['name'],
                    'quantity': item['quantity'],
                    'unit_price': product['price'],
                    'subtotal': subtotal
                })
            
            # Create order record
            order_data = {
                'customer_phone': customer_phone,
                'customer_name': customer_name,
                'product_id': order_items[0]['product_id'],  # First product for backward compat
                'product_name': f"{len(order_items)} items",  # Summary
                'quantity': sum(item['quantity'] for item in order_items),
                'total_price': total_price,
                'delivery_address': delivery_address,
                'status': 'pending',
                'total_items': len(order_items)
            }
            
            order_id = self.db.create_order_with_items(order_data, order_items)
            
            if not order_id:
                return {'success': False, 'message': 'Failed to create order'}
            
            # Update stock for all products
            for item in order_items:
                product = self.db.get_product_by_id(item['product_id'])
                new_stock = product['stock'] - item['quantity']
                self.db.execute_query(
                    "UPDATE products SET stock = ? WHERE id = ?",
                    (new_stock, item['product_id'])
                )

            self.db.set_user_display_name(customer_phone, customer_name)
            self.db.update_conversation_customer_name(customer_phone, customer_name)
            
            # Get the created order with items
            order = self.db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
            order['items'] = self.db.get_order_items(order_id)

            self.db.log_event(
                event_type="order_created",
                entity_type="order",
                entity_id=str(order_id),
                message="Order created (multi-item)",
                metadata={
                    "customer_phone": customer_phone,
                    "total_price": float(order.get("total_price", 0)),
                    "total_items": len(order.get("items", []))
                }
            )
            
            return {
                'success': True,
                'order': order,
                'message': 'Order created successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Error creating multi-product order: {e}")
            return {'success': False, 'message': f'An error occurred: {str(e)}'}
    
    def get_order_with_items(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order with all its items"""
        try:
            order = self.db.fetch_one(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,)
            )
            if order:
                order['items'] = self.db.get_order_items(order_id)
            return order
        except Exception as e:
            self.logger.error(f"Error getting order with items: {e}")
            return None