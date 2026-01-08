import logging
import re
from typing import Dict, Any, Optional

from .orders import OrderManager
from .products import ProductManager

class MessageProcessor:
    def __init__(self, db):
        self.db = db
        self.order_manager = OrderManager(db)
        self.product_manager = ProductManager(db)
        self.logger = logging.getLogger(__name__)
        
        # Store pending orders being built (phone -> order_data)
        self.pending_orders = {}
        
        # Command patterns
        self.commands = {
            # Customer commands
            'help': self._handle_help,
            'start': self._handle_help,
            'products': self._handle_products,
            'order': self._handle_order,  # Legacy single-product order
            'neworder': self._handle_new_order,  # Start multi-product order
            'add': self._handle_add_item,
            'confirm': self._handle_confirm_order,
            'cancel': self._handle_cancel_order,
            'myorders': self._handle_my_orders,
            'hours': self._handle_hours,
            'contact': self._handle_contact,
            
            # Team commands
            'orders': self._handle_pending_orders,
            'stats': self._handle_stats,
            'status': self._handle_update_status,
            
            # Admin commands
            'addproduct': self._handle_add_product,
            'editproduct': self._handle_edit_product,
            'deleteproduct': self._handle_delete_product,
            'allproducts': self._handle_all_products,
            'restock': self._handle_restock,
            'chat': self._handle_admin_chat,
            'reply': self._handle_admin_reply,
            'conversations': self._handle_conversations
        }
    
    def process_message(self, phone_number: str, message: str) -> str:
        """Process incoming message and return response"""
        try:
            # Clean the message
            message = message.strip().lower()
            
            # Ensure user exists
            self._ensure_user_exists(phone_number)
            
            # Get user role
            user = self.db.get_user_by_phone(phone_number)
            user_role = user['role'] if user else 'customer'
            
            # Handle empty message
            if not message:
                return self._handle_help()
            
            # Check for command
            for command, handler in self.commands.items():
                if message.startswith(command):
                    # Check permissions for admin/team commands
                    if command in ['addproduct', 'editproduct', 'deleteproduct', 
                                 'allproducts', 'restock'] and user_role not in ['admin', 'team']:
                        return "❌ Access denied. Admin privileges required."
                    
                    if command in ['orders', 'stats', 'status'] and user_role not in ['admin', 'team']:
                        return "❌ Access denied. Team privileges required."
                    
                    return handler(phone_number, message, user_role)
            
            # No command matched
            return self._handle_unknown_command()
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            return "❌ An error occurred. Please try again."
    
    def _ensure_user_exists(self, phone_number: str):
        """Ensure user exists in database"""
        user = self.db.get_user_by_phone(phone_number)
        if not user:
            self.db.create_user(phone_number)
    
    def _handle_help(self, phone_number: str = None, message: str = None, 
                    user_role: str = 'customer') -> str:
        """Show help message"""
        response = "🛍️ *Signal Store Bot Help*\n\n"
        
        response += "*Customer Commands:*\n"
        response += "• `products` - View available products\n"
        response += "• `order [id] [qty] [name] [address]` - Quick single order\n"
        response += "• `neworder [name] [address]` - Start multi-product order\n"
        response += "• `add [product_id] [quantity]` - Add item to order\n"
        response += "• `confirm` - Confirm and place order\n"
        response += "• `cancel` - Cancel current order\n"
        response += "• `myorders` - View your orders\n"
        response += "• `hours` - Business hours\n"
        response += "• `contact` - Contact information\n\n"
        
        if user_role in ['team', 'admin']:
            response += "*Team Commands:*\n"
            response += "• `orders` - View pending orders\n"
            response += "• `stats` - Daily statistics\n"
            response += "• `status [order_id] [status]` - Update order status\n\n"
        
        if user_role == 'admin':
            response += "*Admin Commands:*\n"
            response += "• `addproduct name:desc:price:stock` - Add product\n"
            response += "• `editproduct id:name:desc:price:stock` - Edit product\n"
            response += "• `deleteproduct id` - Delete product\n"
            response += "• `allproducts` - View all products\n"
            response += "• `restock id quantity` - Restock product\n"
            response += "• `chat [phone]` - Start chat with customer\n"
            response += "• `reply [phone] [message]` - Reply to customer\n"
            response += "• `conversations` - View all conversations\n"
        
        return response
    
    def _handle_products(self, phone_number: str = None, message: str = None, 
                        user_role: str = 'customer') -> str:
        """Show available products"""
        products = self.product_manager.get_all_products()
        
        if not products:
            return "📦 No products available at the moment."
        
        response = "📦 *Available Products*\n\n"
        for product in products:
            response += f"*{product['id']}. {product['name']}*\n"
            response += f"   {product['description']}\n"
            response += f"   💰 ${product['price']:.2f}\n"
            response += f"   📦 Stock: {product['stock']}\n\n"
        
        response += "To order: `order [product_id] [quantity] [your_name] [delivery_address]`"
        return response
    
    def _handle_order(self, phone_number: str, message: str, 
                     user_role: str = 'customer') -> str:
        """Handle order command"""
        try:
            # Parse order command: order [product_id] [quantity] [name] [address]
            parts = message.split(' ', 4)
            if len(parts) < 5:
                return "❌ Usage: `order [product_id] [quantity] [your_name] [delivery_address]`\nExample: `order 1 2 John Doe 123 Main Street`"
            
            product_id = int(parts[1])
            quantity = int(parts[2])
            customer_name = parts[3]
            delivery_address = parts[4]
            
            # Validate quantity
            if quantity <= 0:
                return "❌ Quantity must be greater than 0"
            
            # Create order
            result = self.order_manager.create_order(
                phone_number, product_id, quantity, customer_name, delivery_address
            )
            
            if result['success']:
                order = result['order']
                response = "✅ *Order Placed Successfully!*\n\n"
                response += f"*Order ID:* {order['id']}\n"
                response += f"*Product:* {order['product_name']}\n"
                response += f"*Quantity:* {order['quantity']}\n"
                response += f"*Total:* ${order['total_price']:.2f}\n"
                response += f"*Delivery to:* {order['delivery_address']}\n\n"
                response += "Use `myorders` to check your order status."
                return response
            else:
                return f"❌ {result['message']}"
                
        except ValueError:
            return "❌ Invalid format. Usage: `order [product_id] [quantity] [your_name] [delivery_address]`"
        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            return "❌ Failed to create order. Please try again."
    
    def _handle_my_orders(self, phone_number: str, message: str = None, 
                         user_role: str = 'customer') -> str:
        """Show user's orders"""
        orders = self.order_manager.get_user_orders(phone_number)
        
        if not orders:
            return "📝 You haven't placed any orders yet."
        
        response = "📝 *Your Orders*\n\n"
        for order in orders:
            status_emoji = {
                'pending': '⏳',
                'confirmed': '✅',
                'preparing': '👨‍🍳',
                'delivered': '🚚',
                'cancelled': '❌'
            }.get(order['status'], '📦')
            
            response += f"*Order #{order['id']}* {status_emoji}\n"
            response += f"Product: {order['product_name']}\n"
            response += f"Qty: {order['quantity']} | Total: ${order['total_price']:.2f}\n"
            response += f"Status: {order['status'].title()}\n"
            response += f"Placed: {order['created_at'][:16]}\n\n"
        
        return response
    
    def _handle_hours(self, phone_number: str = None, message: str = None, 
                     user_role: str = 'customer') -> str:
        """Show business hours"""
        try:
            from config.settings import ALWAYS_OPEN, BUSINESS_HOURS
            
            if ALWAYS_OPEN:
                return "🕒 *Business Hours*\nAlways Open (24/7)\n\nWe're here to help you anytime!"
            
            # Get hours from settings
            start = BUSINESS_HOURS['start']
            end = BUSINESS_HOURS['end']
            start_str = start.strftime("%I:%M %p")
            end_str = end.strftime("%I:%M %p")
            
            # Handle overnight hours
            if end < start:
                return f"🕒 *Business Hours*\n{start_str} - {end_str} (Next Day)\n\nWe're closed from {end_str} to {start_str}."
            else:
                return f"🕒 *Business Hours*\n{start_str} - {end_str} (Daily)"
                
        except ImportError:
            # Fallback if settings not available
            return "🕒 *Business Hours*\nAlways Open (24/7)"
    
    def _handle_contact(self, phone_number: str = None, message: str = None, 
                       user_role: str = 'customer') -> str:
        """Show contact information"""
        from config.settings import URGENT_CONTACT
        
        response = "📞 *Contact Information*\n\n"
        response += "During business hours (3 PM - 1 AM), you can message us here.\n\n"
        
        if URGENT_CONTACT:
            response += f"🆘 For urgent matters outside business hours:\n{URGENT_CONTACT}"
        
        return response
    
    def _handle_pending_orders(self, phone_number: str, message: str = None, 
                              user_role: str = 'customer') -> str:
        """Show pending orders for team"""
        orders = self.db.get_pending_orders()
        
        if not orders:
            return "✅ No pending orders."
        
        response = "📋 *Pending Orders*\n\n"
        for order in orders:
            response += f"*Order #{order['id']}*\n"
            response += f"Customer: {order['customer_name']} ({order['customer_phone']})\n"
            response += f"Product: {order['product_name']}\n"
            response += f"Qty: {order['quantity']} | Total: ${order['total_price']:.2f}\n"
            response += f"Address: {order['delivery_address']}\n"
            response += f"Placed: {order['created_at'][:16]}\n\n"
        
        response += "Update status: `status [order_id] [new_status]`"
        return response
    
    def _handle_stats(self, phone_number: str, message: str = None, 
                     user_role: str = 'customer') -> str:
        """Show daily statistics"""
        stats = self.order_manager.get_daily_stats()
        
        response = "📊 *Daily Statistics*\n\n"
        response += f"Total Orders: {stats['total_orders']}\n"
        response += f"Pending: {stats['pending_orders']}\n"
        response += f"Completed: {stats['completed_orders']}\n"
        response += f"Total Revenue: ${stats['total_revenue']:.2f}\n"
        response += f"Average Order: ${stats['average_order_value']:.2f}"
        
        return response
    
    def _handle_update_status(self, phone_number: str, message: str, 
                            user_role: str = 'customer') -> str:
        """Update order status"""
        try:
            parts = message.split(' ', 2)
            if len(parts) < 3:
                return "❌ Usage: `status [order_id] [new_status]`\nStatuses: pending, confirmed, preparing, delivered, cancelled"
            
            order_id = int(parts[1])
            new_status = parts[2].lower()
            
            valid_statuses = ['pending', 'confirmed', 'preparing', 'delivered', 'cancelled']
            if new_status not in valid_statuses:
                return f"❌ Invalid status. Use: {', '.join(valid_statuses)}"
            
            success = self.order_manager.update_order_status(order_id, new_status, phone_number)
            
            if success:
                return f"✅ Order #{order_id} status updated to: {new_status}"
            else:
                return f"❌ Order #{order_id} not found"
                
        except ValueError:
            return "❌ Invalid format. Usage: `status [order_id] [new_status]`"
        except Exception as e:
            self.logger.error(f"Error updating order status: {e}")
            return "❌ Failed to update order status"
    
    def _handle_add_product(self, phone_number: str, message: str, 
                           user_role: str = 'customer') -> str:
        """Add new product"""
        try:
            # Format: addproduct name:description:price:stock
            parts = message.split(' ', 1)
            if len(parts) < 2:
                return "❌ Usage: `addproduct name:description:price:stock`\nExample: `addproduct Pizza:Delicious pizza:12.99:10`"
            
            product_data = parts[1].split(':', 3)
            if len(product_data) < 4:
                return "❌ Usage: `addproduct name:description:price:stock`"
            
            name = product_data[0].strip()
            description = product_data[1].strip()
            price = float(product_data[2].strip())
            stock = int(product_data[3].strip())
            
            product_id = self.product_manager.create_product(name, description, price, stock)
            
            if product_id:
                return f"✅ Product added successfully! ID: {product_id}"
            else:
                return "❌ Failed to add product"
                
        except ValueError:
            return "❌ Invalid format. Price and stock must be numbers."
        except Exception as e:
            self.logger.error(f"Error adding product: {e}")
            return "❌ Failed to add product"
    
    def _handle_edit_product(self, phone_number: str, message: str, 
                            user_role: str = 'customer') -> str:
        """Edit existing product"""
        try:
            # Format: editproduct id:name:description:price:stock
            parts = message.split(' ', 1)
            if len(parts) < 2:
                return "❌ Usage: `editproduct id:name:description:price:stock`"
            
            product_data = parts[1].split(':', 4)
            if len(product_data) < 5:
                return "❌ Usage: `editproduct id:name:description:price:stock`"
            
            product_id = int(product_data[0].strip())
            name = product_data[1].strip()
            description = product_data[2].strip()
            price = float(product_data[3].strip())
            stock = int(product_data[4].strip())
            
            success = self.product_manager.update_product(
                product_id, name, description, price, stock
            )
            
            if success:
                return f"✅ Product #{product_id} updated successfully!"
            else:
                return f"❌ Product #{product_id} not found"
                
        except ValueError:
            return "❌ Invalid format. ID, price and stock must be numbers."
        except Exception as e:
            self.logger.error(f"Error editing product: {e}")
            return "❌ Failed to edit product"
    
    def _handle_delete_product(self, phone_number: str, message: str, 
                              user_role: str = 'customer') -> str:
        """Delete product (soft delete)"""
        try:
            parts = message.split(' ', 1)
            if len(parts) < 2:
                return "❌ Usage: `deleteproduct [product_id]`"
            
            product_id = int(parts[1].strip())
            success = self.product_manager.delete_product(product_id)
            
            if success:
                return f"✅ Product #{product_id} deleted successfully!"
            else:
                return f"❌ Product #{product_id} not found"
                
        except ValueError:
            return "❌ Invalid product ID"
        except Exception as e:
            self.logger.error(f"Error deleting product: {e}")
            return "❌ Failed to delete product"
    
    def _handle_all_products(self, phone_number: str = None, message: str = None, 
                            user_role: str = 'customer') -> str:
        """Show all products including inactive"""
        products = self.db.get_all_products(active_only=False)
        
        if not products:
            return "📦 No products in database."
        
        response = "📦 *All Products*\n\n"
        for product in products:
            status = "✅ Active" if product['is_active'] else "❌ Inactive"
            response += f"*{product['id']}. {product['name']}* ({status})\n"
            response += f"   {product['description']}\n"
            response += f"   💰 ${product['price']:.2f} | 📦 {product['stock']} units\n\n"
        
        return response
    
    def _handle_restock(self, phone_number: str, message: str, 
                       user_role: str = 'customer') -> str:
        """Restock product"""
        try:
            parts = message.split(' ', 2)
            if len(parts) < 3:
                return "❌ Usage: `restock [product_id] [quantity]`"
            
            product_id = int(parts[1].strip())
            quantity = int(parts[2].strip())
            
            success = self.product_manager.restock_product(product_id, quantity)
            
            if success:
                return f"✅ Product #{product_id} restocked with {quantity} units!"
            else:
                return f"❌ Product #{product_id} not found"
                
        except ValueError:
            return "❌ Invalid format. Both product ID and quantity must be numbers."
        except Exception as e:
            self.logger.error(f"Error restocking product: {e}")
            return "❌ Failed to restock product"
    
    def _handle_new_order(self, phone_number: str, message: str, 
                         user_role: str = 'customer') -> str:
        """Start a new multi-product order"""
        try:
            parts = message.split(' ', 2)
            if len(parts) < 3:
                return "❌ Usage: `neworder [your_name] [delivery_address]`\nExample: `neworder John Doe 123 Main Street`"
            
            customer_name = parts[1]
            delivery_address = parts[2]
            
            # Initialize pending order
            self.pending_orders[phone_number] = {
                'customer_name': customer_name,
                'delivery_address': delivery_address,
                'items': []
            }
            
            response = "🛒 *New Order Started*\n\n"
            response += f"*Name:* {customer_name}\n"
            response += f"*Address:* {delivery_address}\n\n"
            response += "Add products with: `add [product_id] [quantity]`\n"
            response += "When done, type: `confirm`\n"
            response += "To cancel: `cancel`"
            
            return response
        except Exception as e:
            self.logger.error(f"Error starting new order: {e}")
            return "❌ Failed to start order. Please try again."
    
    def _handle_add_item(self, phone_number: str, message: str, 
                        user_role: str = 'customer') -> str:
        """Add item to pending order"""
        try:
            if phone_number not in self.pending_orders:
                return "❌ No order in progress. Start with: `neworder [name] [address]`"
            
            parts = message.split(' ', 2)
            if len(parts) < 3:
                return "❌ Usage: `add [product_id] [quantity]`\nExample: `add 1 2`"
            
            product_id = int(parts[1])
            quantity = int(parts[2])
            
            if quantity <= 0:
                return "❌ Quantity must be greater than 0"
            
            # Get product
            product = self.db.get_product_by_id(product_id)
            if not product:
                return f"❌ Product {product_id} not found"
            
            if product['stock'] < quantity:
                return f"❌ Insufficient stock. Only {product['stock']} available"
            
            # Add to pending order
            self.pending_orders[phone_number]['items'].append({
                'product_id': product_id,
                'quantity': quantity,
                'product_name': product['name'],
                'unit_price': product['price']
            })
            
            # Build summary
            order = self.pending_orders[phone_number]
            total = sum(item['unit_price'] * item['quantity'] for item in order['items'])
            
            response = f"✅ Added {product['name']} x{quantity}\n\n"
            response += "*Current Order:*\n"
            for item in order['items']:
                response += f"• {item['product_name']} x{item['quantity']} = ${item['unit_price'] * item['quantity']:.2f}\n"
            response += f"\n*Total: ${total:.2f}*\n\n"
            response += "Add more: `add [product_id] [quantity]`\n"
            response += "Confirm: `confirm` | Cancel: `cancel`"
            
            return response
        except ValueError:
            return "❌ Invalid format. Usage: `add [product_id] [quantity]`"
        except Exception as e:
            self.logger.error(f"Error adding item: {e}")
            return "❌ Failed to add item. Please try again."
    
    def _handle_confirm_order(self, phone_number: str, message: str = None, 
                             user_role: str = 'customer') -> str:
        """Confirm and place the order"""
        try:
            if phone_number not in self.pending_orders:
                return "❌ No order in progress. Start with: `neworder [name] [address]`"
            
            order_data = self.pending_orders[phone_number]
            
            if not order_data['items']:
                return "❌ No items in order. Add items with: `add [product_id] [quantity]`"
            
            # Convert to format expected by create_multi_product_order
            items = [{'product_id': item['product_id'], 'quantity': item['quantity']} 
                    for item in order_data['items']]
            
            # Create order
            result = self.order_manager.create_multi_product_order(
                phone_number,
                order_data['customer_name'],
                order_data['delivery_address'],
                items
            )
            
            # Clear pending order
            del self.pending_orders[phone_number]
            
            if result['success']:
                order = result['order']
                response = "✅ *Order Placed Successfully!*\n\n"
                response += f"*Order ID:* {order['id']}\n"
                response += f"*Items:* {len(order.get('items', []))}\n"
                for item in order.get('items', []):
                    response += f"  • {item['product_name']} x{item['quantity']} = ${item['subtotal']:.2f}\n"
                response += f"\n*Total:* ${order['total_price']:.2f}\n"
                response += f"*Delivery to:* {order['delivery_address']}\n\n"
                response += "Use `myorders` to check your order status."
                return response
            else:
                return f"❌ {result['message']}"
                
        except Exception as e:
            self.logger.error(f"Error confirming order: {e}")
            return "❌ Failed to place order. Please try again."
    
    def _handle_cancel_order(self, phone_number: str, message: str = None, 
                            user_role: str = 'customer') -> str:
        """Cancel pending order"""
        if phone_number not in self.pending_orders:
            return "❌ No order in progress."
        
        del self.pending_orders[phone_number]
        return "❌ Order cancelled. Start a new order with: `neworder [name] [address]`"
    
    def _handle_admin_chat(self, phone_number: str, message: str, 
                           user_role: str = 'customer') -> str:
        """Admin: Start or continue chat with customer"""
        if user_role not in ['admin', 'team']:
            return "❌ Access denied. Admin privileges required."
        
        try:
            parts = message.split(' ', 1)
            if len(parts) < 2:
                return "❌ Usage: `chat [customer_phone]`\nExample: `chat +1234567890`"
            
            customer_phone = parts[1].strip()
            
            # Get or create conversation
            conv_id = self.db.get_or_create_conversation(customer_phone, admin_phone=phone_number)
            
            if not conv_id:
                return "❌ Failed to create conversation"
            
            # Get recent messages
            messages = self.db.get_messages(limit=10, conversation_id=conv_id)
            
            response = f"💬 *Chat with {customer_phone}*\n\n"
            if messages:
                response += "*Recent messages:*\n"
                for msg in reversed(messages[-5:]):  # Show last 5
                    direction = "→" if msg['direction'] == 'outbound' else "←"
                    response += f"{direction} {msg['message_text'][:50]}...\n"
            else:
                response += "No messages yet.\n"
            
            response += "\nReply with: `reply [phone] [message]`"
            return response
            
        except Exception as e:
            self.logger.error(f"Error in admin chat: {e}")
            return "❌ Failed to start chat."
    
    def _handle_admin_reply(self, phone_number: str, message: str, 
                           user_role: str = 'customer') -> str:
        """Admin: Reply to customer (message will be sent via SignalBridge)"""
        if user_role not in ['admin', 'team']:
            return "❌ Access denied. Admin privileges required."
        
        try:
            parts = message.split(' ', 2)
            if len(parts) < 3:
                return "❌ Usage: `reply [customer_phone] [message]`\nExample: `reply +1234567890 Hello!`"
            
            customer_phone = parts[1].strip()
            reply_text = parts[2]
            
            # Get or create conversation
            conv_id = self.db.get_or_create_conversation(customer_phone, admin_phone=phone_number)
            
            # Return special format that start_scheduled.py will recognize
            # Format: "ADMIN_REPLY:[phone]:[message]"
            return f"ADMIN_REPLY:{customer_phone}:{reply_text}"
            
        except Exception as e:
            self.logger.error(f"Error in admin reply: {e}")
            return "❌ Failed to send reply."
    
    def _handle_conversations(self, phone_number: str, message: str = None, 
                             user_role: str = 'customer') -> str:
        """Admin: List all conversations"""
        if user_role not in ['admin', 'team']:
            return "❌ Access denied. Admin privileges required."
        
        try:
            conversations = self.db.get_conversations(status='active')
            
            if not conversations:
                return "📭 No active conversations."
            
            response = "💬 *Active Conversations*\n\n"
            for conv in conversations[:10]:  # Show first 10
                response += f"*{conv['customer_phone']}*\n"
                if conv['customer_name']:
                    response += f"  Name: {conv['customer_name']}\n"
                response += f"  Last: {conv['last_message_at'][:16]}\n\n"
            
            response += "Start chat: `chat [phone]`"
            return response
            
        except Exception as e:
            self.logger.error(f"Error listing conversations: {e}")
            return "❌ Failed to list conversations."
    
    def _handle_unknown_command(self) -> str:
        """Handle unknown commands"""
        # Check if user has pending order
        # This allows natural language during order building
        return "❌ Unknown command. Type `help` to see available commands."