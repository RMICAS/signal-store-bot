#!/usr/bin/env python3
"""
Admin Dashboard API
Flask REST API for managing orders, messages, and conversations
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, jsonify, request, render_template, Response
from flask_cors import CORS
from bot.database import Database
from bot.products import ProductManager
from bot.signal_bridge import SignalBridge
from config.settings import BOT_PHONE_NUMBER
import logging
from datetime import datetime, date, timedelta
import csv
import io

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Initialize database and signal bridge
db = Database()
signal_bridge = None
product_manager = ProductManager(db)

try:
    signal_bridge = SignalBridge(BOT_PHONE_NUMBER)
except Exception as e:
    logging.warning(f"Could not initialize SignalBridge: {e}")

@app.route('/')
def index():
    """Serve dashboard HTML"""
    return render_template('dashboard.html')

@app.route('/api/messages')
def get_messages():
    """Get all messages"""
    limit = request.args.get('limit', 100, type=int)
    conversation_id = request.args.get('conversation_id', type=int)
    direction = request.args.get('direction')
    q = request.args.get('q')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = "SELECT * FROM messages"
    clauses = []
    params = []
    if conversation_id:
        clauses.append("conversation_id = ?")
        params.append(conversation_id)
    if direction:
        clauses.append("direction = ?")
        params.append(direction)
    if q:
        clauses.append("message_text LIKE ?")
        params.append(f"%{q}%")
    if date_from:
        clauses.append("DATE(created_at) >= DATE(?)")
        params.append(date_from)
    if date_to:
        clauses.append("DATE(created_at) <= DATE(?)")
        params.append(date_to)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    messages = db.fetch_all(query, tuple(params))
    
    # Convert datetime objects to strings
    for msg in messages:
        if 'created_at' in msg:
            msg['created_at'] = str(msg['created_at'])
    
    return jsonify(messages)

@app.route('/api/inbox')
def get_inbox():
    """Live inbox with unread counts and SLA timers"""
    conversations = db.fetch_all('''
        SELECT c.*,
               COALESCE(u.display_name, c.customer_name) AS customer_name,
               m.message_text AS last_message_text,
               m.direction AS last_message_direction,
               m.created_at AS last_message_time
        FROM conversations c
        LEFT JOIN users u ON u.phone_number = c.customer_phone
        LEFT JOIN messages m ON m.id = (
            SELECT id FROM messages
            WHERE conversation_id = c.id
            ORDER BY created_at DESC
            LIMIT 1
        )
        ORDER BY c.last_message_at DESC
    ''')
    now = datetime.utcnow()
    for conv in conversations:
        if conv.get('status') == 'active':
            conv['status'] = 'open'
        if 'last_message_at' in conv and conv['last_message_at']:
            try:
                last_time = datetime.fromisoformat(str(conv['last_message_at']))
                conv['sla_seconds'] = int((now - last_time).total_seconds())
            except Exception:
                conv['sla_seconds'] = None
        else:
            conv['sla_seconds'] = None

        if 'last_admin_read_at' in conv and conv['last_admin_read_at']:
            unread = db.fetch_one(
                "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ? AND direction = 'inbound' AND created_at > ?",
                (conv['id'], conv['last_admin_read_at'])
            )['count']
        else:
            unread = db.fetch_one(
                "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ? AND direction = 'inbound'",
                (conv['id'],)
            )['count']
        conv['unread_count'] = unread
        if 'created_at' in conv:
            conv['created_at'] = str(conv['created_at'])
        if 'last_message_at' in conv:
            conv['last_message_at'] = str(conv['last_message_at'])
        if 'last_admin_read_at' in conv:
            conv['last_admin_read_at'] = str(conv['last_admin_read_at']) if conv['last_admin_read_at'] else None
    return jsonify(conversations)

@app.route('/api/conversations')
def get_conversations():
    """Get all conversations"""
    status = request.args.get('status', None)
    
    if status:
        conversations = db.fetch_all(
            "SELECT c.*, COALESCE(u.display_name, c.customer_name) AS customer_name "
            "FROM conversations c LEFT JOIN users u ON u.phone_number = c.customer_phone "
            "WHERE c.status = ? ORDER BY c.last_message_at DESC",
            (status,)
        )
    else:
        conversations = db.fetch_all(
            "SELECT c.*, COALESCE(u.display_name, c.customer_name) AS customer_name "
            "FROM conversations c LEFT JOIN users u ON u.phone_number = c.customer_phone "
            "ORDER BY c.last_message_at DESC"
        )
    
    # Convert datetime objects to strings
    for conv in conversations:
        if 'created_at' in conv:
            conv['created_at'] = str(conv['created_at'])
        if 'last_message_at' in conv:
            conv['last_message_at'] = str(conv['last_message_at'])
    
    return jsonify(conversations)

@app.route('/api/conversations/<int:conversation_id>/status', methods=['PUT'])
def update_conversation_status(conversation_id):
    """Update conversation status/assignment"""
    data = request.json or {}
    status = data.get('status')
    assigned_to = data.get('assigned_to')
    updated = db.update_conversation_metadata(
        conversation_id,
        status=status,
        assigned_to=assigned_to
    )
    if updated:
        db.log_event(
            event_type="conversation_status_updated",
            entity_type="conversation",
            entity_id=str(conversation_id),
            message=f"Conversation updated to {status}",
            metadata={"assigned_to": assigned_to}
        )
    return jsonify({'success': updated})

@app.route('/api/conversations/<int:conversation_id>/read', methods=['POST'])
def mark_conversation_read(conversation_id):
    """Mark conversation as read by admin"""
    updated = db.update_conversation_metadata(conversation_id, mark_read=True)
    return jsonify({'success': updated})

@app.route('/api/conversations/<int:conversation_id>/messages')
def get_conversation_messages(conversation_id):
    """Get messages for a specific conversation"""
    limit = request.args.get('limit', 50, type=int)
    messages = db.get_messages(limit=limit, conversation_id=conversation_id)
    
    # Convert datetime objects to strings
    for msg in messages:
        if 'created_at' in msg:
            msg['created_at'] = str(msg['created_at'])
    
    return jsonify(messages)

@app.route('/api/orders')
def get_orders():
    """Get all orders"""
    status = request.args.get('status', None)
    payment_status = request.args.get('payment_status', None)
    q = request.args.get('q')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    min_total = request.args.get('min_total', type=float)
    max_total = request.args.get('max_total', type=float)
    query = "SELECT * FROM orders"
    clauses = []
    params = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if payment_status:
        clauses.append("payment_status = ?")
        params.append(payment_status)
    if q:
        clauses.append("(customer_name LIKE ? OR customer_phone LIKE ? OR product_name LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if date_from:
        clauses.append("DATE(created_at) >= DATE(?)")
        params.append(date_from)
    if date_to:
        clauses.append("DATE(created_at) <= DATE(?)")
        params.append(date_to)
    if min_total is not None:
        clauses.append("total_price >= ?")
        params.append(min_total)
    if max_total is not None:
        clauses.append("total_price <= ?")
        params.append(max_total)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"
    orders = db.fetch_all(query, tuple(params))
    
    # Add items to each order
    for order in orders:
        order['items'] = db.get_order_items(order['id'])
        if 'created_at' in order:
            order['created_at'] = str(order['created_at'])
        if 'updated_at' in order:
            order['updated_at'] = str(order['updated_at'])
    
    return jsonify(orders)

@app.route('/api/orders/bulk_status', methods=['PUT'])
def bulk_update_order_status():
    """Bulk update order status"""
    data = request.json or {}
    ids = data.get('ids', [])
    status = data.get('status')
    assigned_to = data.get('assigned_to')
    if not ids or not status:
        return jsonify({'success': False, 'error': 'ids and status required'}), 400
    params_list = [(status, assigned_to, order_id) for order_id in ids]
    try:
        db.execute_many(
            "UPDATE orders SET status = ?, assigned_to = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            params_list
        )
        for order_id in ids:
            db.log_event(
                event_type="order_status_updated",
                entity_type="order",
                entity_id=str(order_id),
                message=f"Order status updated to {status}",
                metadata={"assigned_to": assigned_to, "bulk": True}
            )
            if signal_bridge and status in {'confirmed'}:
                order = db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
                if order:
                    message_text = f"✅ Your order #{order_id} has been confirmed. We'll keep you updated."
                    sent = signal_bridge.send_message(order['customer_phone'], message_text)
                    if sent:
                        conv_id = db.get_or_create_conversation(order['customer_phone'])
                        db.log_message(
                            sender_phone=BOT_PHONE_NUMBER,
                            recipient_phone=order['customer_phone'],
                            message_text=message_text,
                            direction='outbound',
                            is_admin=True,
                            conversation_id=conv_id,
                            delivery_status="sent"
                        )
                    else:
                        db.log_event(
                            event_type="send_error",
                            entity_type="order",
                            entity_id=str(order_id),
                            severity="error",
                            message="Failed to send bulk order confirmation message",
                            metadata={"status": status}
                        )
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error in bulk update: {e}")
        return jsonify({'success': False}), 500

@app.route('/api/orders/<int:order_id>/assign', methods=['PUT'])
def assign_driver(order_id):
    """Assign a driver to an order"""
    data = request.json or {}
    driver_phone = data.get('driver_phone')
    if not driver_phone:
        return jsonify({'success': False, 'error': 'driver_phone required'}), 400
    cursor = db.execute_query(
        "UPDATE orders SET assigned_to = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (driver_phone, 'assigned', order_id)
    )
    success = cursor.rowcount > 0
    if success:
        order = db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        driver = db.get_user_by_phone(driver_phone)
        if order and signal_bridge:
            driver_name = driver.get('display_name') if driver else None
            driver_message = (
                f"🚚 New delivery assigned: Order #{order_id}\n"
                f"Customer: {order.get('customer_name')}\n"
                f"Phone: {order.get('customer_phone')}\n"
                f"Address: {order.get('delivery_address')}"
            )
            signal_bridge.send_message(driver_phone, driver_message)
            customer_message = (
                f"🚚 A driver has been assigned to your order #{order_id}.\n"
                f"Driver: {driver_name or driver_phone}"
            )
            signal_bridge.send_message(order.get('customer_phone'), customer_message)
        db.log_event(
            event_type="order_assigned",
            entity_type="order",
            entity_id=str(order_id),
            message="Driver assigned to order",
            metadata={"driver_phone": driver_phone}
        )
    return jsonify({'success': bool(success)})

@app.route('/api/orders/<int:order_id>/payment', methods=['PUT'])
def update_payment_status(order_id):
    """Update payment status"""
    data = request.json or {}
    status = data.get('payment_status')
    if status not in {'unpaid', 'paid', 'partial', 'refunded'}:
        return jsonify({'success': False, 'error': 'invalid status'}), 400
    cursor = db.execute_query(
        "UPDATE orders SET payment_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, order_id)
    )
    if cursor.rowcount > 0:
        db.log_event(
            event_type="payment_status_updated",
            entity_type="order",
            entity_id=str(order_id),
            message=f"Payment status updated to {status}"
        )
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/orders/<int:order_id>')
def get_order(order_id):
    """Get specific order with items"""
    order = db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    order['items'] = db.get_order_items(order_id)
    if 'created_at' in order:
        order['created_at'] = str(order['created_at'])
    if 'updated_at' in order:
        order['updated_at'] = str(order['updated_at'])
    
    return jsonify(order)

@app.route('/api/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status"""
    data = request.json
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    success = db.execute_query(
        "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_status, order_id)
    )
    
    if success:
        order = db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        if order and signal_bridge and new_status in {'confirmed'}:
            message_text = f"✅ Your order #{order_id} has been confirmed. We'll keep you updated."
            sent = signal_bridge.send_message(order['customer_phone'], message_text)
            if sent:
                conv_id = db.get_or_create_conversation(order['customer_phone'])
                db.log_message(
                    sender_phone=BOT_PHONE_NUMBER,
                    recipient_phone=order['customer_phone'],
                    message_text=message_text,
                    direction='outbound',
                    is_admin=True,
                    conversation_id=conv_id,
                    delivery_status="sent"
                )
            else:
                db.log_event(
                    event_type="send_error",
                    entity_type="order",
                    entity_id=str(order_id),
                    severity="error",
                    message="Failed to send order confirmation message",
                    metadata={"status": new_status}
                )
        db.log_event(
            event_type="order_status_updated",
            entity_type="order",
            entity_id=str(order_id),
            message=f"Order status updated to {new_status}",
            metadata={"source": "dashboard"}
        )
        return jsonify({'success': True, 'message': 'Order status updated'})
    else:
        return jsonify({'error': 'Failed to update order status'}), 500

@app.route('/api/send', methods=['POST'])
def send_message():
    """Admin sends message to customer"""
    if not signal_bridge:
        return jsonify({'error': 'Signal bridge not available'}), 503
    
    data = request.json
    recipient = data.get('recipient')
    message_text = data.get('message')
    
    if not recipient or not message_text:
        return jsonify({'error': 'Recipient and message are required'}), 400
    
    success = signal_bridge.send_message(recipient, message_text)
    
    # Log message
    if success:
        conv_id = db.get_or_create_conversation(recipient)
        db.log_message(
            sender_phone=BOT_PHONE_NUMBER,
            recipient_phone=recipient,
            message_text=message_text,
            direction='outbound',
            is_admin=True,
            conversation_id=conv_id,
            delivery_status="sent"
        )
        db.log_event(
            event_type="admin_message_sent",
            entity_type="conversation",
            entity_id=str(conv_id),
            message="Admin message sent",
            metadata={"recipient": recipient}
        )
    else:
        db.log_event(
            event_type="send_error",
            entity_type="conversation",
            entity_id=recipient,
            severity="error",
            message="Failed to send admin message",
            metadata={"recipient": recipient}
        )
    
    return jsonify({'success': success})

@app.route('/api/products')
def get_products():
    """Get all products"""
    products = db.get_all_products(active_only=False)
    
    for product in products:
        if 'created_at' in product:
            product['created_at'] = str(product['created_at'])
        if 'updated_at' in product:
            product['updated_at'] = str(product['updated_at'])
    
    return jsonify(products)

@app.route('/api/products', methods=['POST'])
def create_product():
    """Create a new product"""
    data = request.json or {}
    name = data.get('name')
    description = data.get('description', '')
    price = data.get('price')
    stock = data.get('stock', 0)
    if not name or price is None:
        return jsonify({'success': False, 'error': 'name and price required'}), 400
    product_id = product_manager.create_product(name, description, float(price), int(stock))
    if product_id:
        db.log_event(
            event_type="product_created",
            entity_type="product",
            entity_id=str(product_id),
            message="Product created",
            metadata={"name": name}
        )
        return jsonify({'success': True, 'id': product_id})
    return jsonify({'success': False}), 500

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update product fields"""
    data = request.json or {}
    name = data.get('name')
    description = data.get('description', '')
    price = data.get('price')
    stock = data.get('stock')
    is_active = data.get('is_active')
    if name is not None and price is not None and stock is not None:
        success = product_manager.update_product(product_id, name, description, float(price), int(stock))
    else:
        success = False
    if is_active is not None:
        db.execute_query(
            "UPDATE products SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (bool(is_active), product_id)
        )
        success = True
    if success:
        db.log_event(
            event_type="product_updated",
            entity_type="product",
            entity_id=str(product_id),
            message="Product updated",
            metadata={"name": name}
        )
    return jsonify({'success': success})

@app.route('/api/products/<int:product_id>/stock', methods=['PUT'])
def update_product_stock(product_id):
    """Set or restock product stock"""
    data = request.json or {}
    delta = data.get('delta')
    stock = data.get('stock')
    success = False
    if delta is not None:
        success = product_manager.restock_product(product_id, int(delta))
    elif stock is not None:
        success = product_manager.update_stock(product_id, int(stock))
    if success:
        db.log_event(
            event_type="product_stock_updated",
            entity_type="product",
            entity_id=str(product_id),
            message="Product stock updated",
            metadata={"delta": delta, "stock": stock}
        )
    return jsonify({'success': success})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Deactivate product"""
    success = product_manager.delete_product(product_id)
    if success:
        db.log_event(
            event_type="product_deleted",
            entity_type="product",
            entity_id=str(product_id),
            message="Product deactivated"
        )
    return jsonify({'success': success})

@app.route('/api/stats')
def get_stats():
    """Get dashboard statistics"""
    today = date.today()
    
    # Get today's stats
    total_orders = db.fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE DATE(created_at) = ?",
        (today.strftime('%Y-%m-%d'),)
    )['count']
    
    pending_orders = db.fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE status = 'pending'",
        ()
    )['count']
    
    active_conversations = db.fetch_one(
        "SELECT COUNT(*) as count FROM conversations WHERE status IN ('open', 'active', 'pending')",
        ()
    )['count']
    
    today_revenue = db.fetch_one(
        "SELECT SUM(total_price) as total FROM orders WHERE DATE(created_at) = ? AND status = 'delivered'",
        (today.strftime('%Y-%m-%d'),)
    )['total'] or 0
    
    return jsonify({
        'total_orders_today': total_orders,
        'pending_orders': pending_orders,
        'active_conversations': active_conversations,
        'today_revenue': float(today_revenue)
    })

@app.route('/api/analytics')
def get_analytics():
    """Business and order intelligence"""
    today = date.today()
    week_start = today - timedelta(days=6)
    funnel = {
        'pending': db.fetch_one("SELECT COUNT(*) as count FROM orders WHERE status = 'pending'")['count'],
        'confirmed': db.fetch_one("SELECT COUNT(*) as count FROM orders WHERE status = 'confirmed'")['count'],
        'delivered': db.fetch_one("SELECT COUNT(*) as count FROM orders WHERE status = 'delivered'")['count'],
        'cancelled': db.fetch_one("SELECT COUNT(*) as count FROM orders WHERE status = 'cancelled'")['count']
    }
    funnel['pending_to_confirmed'] = (funnel['confirmed'] / funnel['pending']) if funnel['pending'] else 0
    funnel['confirmed_to_delivered'] = (funnel['delivered'] / funnel['confirmed']) if funnel['confirmed'] else 0

    daily = db.fetch_all(
        "SELECT DATE(created_at) as day, SUM(total_price) as total FROM orders "
        "WHERE DATE(created_at) >= ? AND status = 'delivered' GROUP BY DATE(created_at) ORDER BY day",
        (week_start.strftime('%Y-%m-%d'),)
    )
    week_total = sum([row['total'] or 0 for row in daily])
    week_orders = db.fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE DATE(created_at) >= ? AND status = 'delivered'",
        (week_start.strftime('%Y-%m-%d'),)
    )['count']
    avg_order = week_total / week_orders if week_orders else 0

    top_products = []
    try:
        top_products = db.fetch_all(
            "SELECT product_name, SUM(quantity) as sales_count, SUM(subtotal) as revenue "
            "FROM order_items GROUP BY product_name ORDER BY revenue DESC LIMIT 5"
        )
    except Exception:
        top_products = db.fetch_all(
            "SELECT product_name, SUM(quantity) as sales_count, SUM(total_price) as revenue "
            "FROM orders GROUP BY product_name ORDER BY revenue DESC LIMIT 5"
        )

    low_stock = db.fetch_all(
        "SELECT id, name, stock FROM products WHERE stock <= ? ORDER BY stock ASC",
        (request.args.get('low_stock', 5, type=int),)
    )

    return jsonify({
        'funnel': funnel,
        'revenue': {
            'daily': daily,
            'week_total': float(week_total),
            'average_order_value': float(avg_order)
        },
        'top_products': top_products,
        'low_stock': low_stock
    })

@app.route('/api/customers')
def get_customers():
    """List customers with summary stats"""
    status = request.args.get('status')
    q = request.args.get('q')
    customers = db.list_customers(status=status, q=q)
    enriched = []
    for customer in customers:
        phone = customer['phone_number']
        stats = db.fetch_one(
            "SELECT COUNT(*) as orders_count, SUM(total_price) as revenue FROM orders WHERE customer_phone = ?",
            (phone,)
        )
        last_contact = db.fetch_one(
            "SELECT MAX(created_at) as last_contact FROM messages WHERE sender_phone = ? OR recipient_phone = ?",
            (phone, phone)
        )
        enriched.append({
            **customer,
            'orders_count': stats['orders_count'] if stats else 0,
            'lifetime_value': float(stats['revenue'] or 0) if stats else 0,
            'last_contact': last_contact['last_contact'] if last_contact else None
        })
    return jsonify(enriched)

@app.route('/api/customers/<phone_number>')
def get_customer_profile(phone_number):
    """Customer profile view"""
    profile = db.get_customer_profile(phone_number)
    return jsonify(profile)

@app.route('/api/customers/<phone_number>/tags', methods=['PUT'])
def update_customer_tags(phone_number):
    data = request.json or {}
    tags = data.get('tags', '')
    success = db.update_user_tags(phone_number, tags)
    return jsonify({'success': success})

@app.route('/api/customers/<phone_number>/status', methods=['PUT'])
def update_customer_status(phone_number):
    data = request.json or {}
    status = data.get('status', 'active')
    success = db.set_user_status(phone_number, status)
    if success:
        db.log_event(
            event_type="user_status_updated",
            entity_type="user",
            entity_id=phone_number,
            message=f"User status set to {status}"
        )
    return jsonify({'success': success})

@app.route('/api/drivers', methods=['GET', 'POST'])
def drivers():
    if request.method == 'GET':
        status = request.args.get('status')
        return jsonify(db.list_users_by_role('driver', status=status))
    data = request.json or {}
    phone = data.get('phone')
    name = data.get('name', '')
    if not phone:
        return jsonify({'success': False, 'error': 'phone required'}), 400
    db.create_user(phone, role='driver', display_name=name or None)
    if name:
        db.set_user_display_name(phone, name)
    db.set_user_status(phone, 'active')
    db.log_event(
        event_type="driver_created",
        entity_type="driver",
        entity_id=phone,
        message="Driver created"
    )
    return jsonify({'success': True})

@app.route('/api/drivers/<phone_number>', methods=['PUT', 'DELETE'])
def update_driver(phone_number):
    if request.method == 'DELETE':
        success = db.set_user_status(phone_number, 'inactive')
        if success:
            db.log_event(
                event_type="driver_deactivated",
                entity_type="driver",
                entity_id=phone_number,
                message="Driver deactivated"
            )
        return jsonify({'success': success})
    data = request.json or {}
    name = data.get('name')
    status = data.get('status')
    success = True
    if name is not None:
        success = db.set_user_display_name(phone_number, name)
    if status is not None:
        success = db.set_user_status(phone_number, status)
    if success:
        db.log_event(
            event_type="driver_updated",
            entity_type="driver",
            entity_id=phone_number,
            message="Driver updated",
            metadata={"status": status, "name": name}
        )
    return jsonify({'success': success})

@app.route('/api/drivers/<phone_number>/profile')
def driver_profile(phone_number):
    driver = db.get_user_by_phone(phone_number)
    orders = db.fetch_all(
        "SELECT * FROM orders WHERE assigned_to = ? AND status IN ('assigned', 'out_for_delivery', 'arrived') ORDER BY updated_at DESC",
        (phone_number,)
    )
    return jsonify({'driver': driver, 'orders': orders})

def _update_trip_status(order_id: int, status: str) -> bool:
    cursor = db.execute_query(
        "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, order_id)
    )
    return cursor.rowcount > 0

@app.route('/api/drivers/<phone_number>/trip/start', methods=['POST'])
def driver_trip_start(phone_number):
    data = request.json or {}
    order_id = data.get('order_id')
    if not order_id:
        return jsonify({'success': False, 'error': 'order_id required'}), 400
    success = _update_trip_status(order_id, 'out_for_delivery')
    if success:
        db.log_event(
            event_type="trip_started",
            entity_type="order",
            entity_id=str(order_id),
            message="Trip started",
            metadata={"driver_phone": phone_number}
        )
    if success and signal_bridge:
        order = db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        driver = db.get_user_by_phone(phone_number)
        driver_name = driver.get('display_name') if driver else phone_number
        if order:
            signal_bridge.send_message(
                order.get('customer_phone'),
                f"🚚 Your driver is on the way for order #{order_id}.\nDriver: {driver_name}"
            )
            signal_bridge.send_message(
                phone_number,
                f"✅ Trip started for order #{order_id}."
            )
    return jsonify({'success': success})

@app.route('/api/drivers/<phone_number>/trip/arrived', methods=['POST'])
def driver_trip_arrived(phone_number):
    data = request.json or {}
    order_id = data.get('order_id')
    if not order_id:
        return jsonify({'success': False, 'error': 'order_id required'}), 400
    success = _update_trip_status(order_id, 'arrived')
    if success:
        db.log_event(
            event_type="trip_arrived",
            entity_type="order",
            entity_id=str(order_id),
            message="Driver arrived",
            metadata={"driver_phone": phone_number}
        )
    if success and signal_bridge:
        order = db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        if order:
            signal_bridge.send_message(
                order.get('customer_phone'),
                f"📍 Your driver has arrived for order #{order_id}."
            )
            signal_bridge.send_message(
                phone_number,
                f"📍 Marked arrived for order #{order_id}."
            )
    return jsonify({'success': success})

@app.route('/api/drivers/<phone_number>/trip/complete', methods=['POST'])
def driver_trip_complete(phone_number):
    data = request.json or {}
    order_id = data.get('order_id')
    if not order_id:
        return jsonify({'success': False, 'error': 'order_id required'}), 400
    success = _update_trip_status(order_id, 'delivered')
    if success:
        db.log_event(
            event_type="trip_completed",
            entity_type="order",
            entity_id=str(order_id),
            message="Trip completed",
            metadata={"driver_phone": phone_number}
        )
    if success and signal_bridge:
        order = db.fetch_one("SELECT * FROM orders WHERE id = ?", (order_id,))
        if order:
            signal_bridge.send_message(
                order.get('customer_phone'),
                f"✅ Delivered order #{order_id}. Please reply YES if you received your order."
            )
            signal_bridge.send_message(
                phone_number,
                f"✅ Marked delivered for order #{order_id}."
            )
    return jsonify({'success': success})

@app.route('/api/blocklist')
def get_blocklist():
    blocked = db.list_customers(status='blocked')
    return jsonify(blocked)

@app.route('/api/quick_replies', methods=['GET', 'POST', 'DELETE'])
def quick_replies():
    if request.method == 'GET':
        replies = db.get_quick_replies()
        if not replies:
            seeds = [
                ("Order confirmed", "✅ Your order #{order_id} is confirmed. We’ll keep you updated."),
                ("Driver assigned", "🚚 A driver has been assigned to your order #{order_id}."),
                ("Driver on the way", "🚚 Your driver is on the way for order #{order_id}. Driver: {driver_name}"),
                ("Driver arrived", "📍 Your driver has arrived for order #{order_id}."),
                ("Delivered", "✅ Delivered order #{order_id}. Please reply YES if you received your order."),
                ("Payment received", "💳 Payment received. Thank you!"),
                ("Payment pending", "⚠️ Payment is still pending. Let us know if you need help."),
                ("Address confirmation", "📍 Please confirm your delivery address: {address}")
            ]
            for title, template in seeds:
                db.create_quick_reply(title, template, created_by="system")
            replies = db.get_quick_replies()
        return jsonify(replies)
    if request.method == 'POST':
        data = request.json or {}
        success = db.create_quick_reply(data.get('title', ''), data.get('template', ''), data.get('created_by'))
        return jsonify({'success': success})
    if request.method == 'DELETE':
        reply_id = request.args.get('id', type=int)
        success = db.delete_quick_reply(reply_id) if reply_id else False
        return jsonify({'success': success})

@app.route('/api/system/health')
def get_system_health():
    """Bot health and queue metrics"""
    bridge_status = 'unavailable'
    if signal_bridge:
        bridge_status = 'available'
    status_entries = {entry['key']: entry['value'] for entry in db.get_system_status()}
    offline_count = len(db.get_offline_messages())
    error_count = db.fetch_one(
        "SELECT COUNT(*) as count FROM event_logs WHERE severity = 'error' AND created_at >= DATETIME('now', '-1 day')"
    )['count']
    return jsonify({
        'signal_bridge': bridge_status,
        'last_heartbeat': status_entries.get('last_heartbeat'),
        'bot_status': status_entries.get('bot_status'),
        'offline_queue': offline_count,
        'error_count_24h': error_count
    })

@app.route('/api/automation/events')
def get_automation_events():
    events = db.get_events(limit=request.args.get('limit', 20, type=int), event_type='automation')
    return jsonify(events)

@app.route('/api/audit')
def get_audit_log():
    limit = request.args.get('limit', 50, type=int)
    event_type = request.args.get('event_type')
    severity = request.args.get('severity')
    return jsonify(db.get_events(limit=limit, event_type=event_type, severity=severity))

def _mask_phone(phone: str) -> str:
    if not phone:
        return phone
    if len(phone) <= 4:
        return "*" * len(phone)
    return phone[:2] + "*" * (len(phone) - 4) + phone[-2:]

@app.route('/api/export/orders')
def export_orders():
    """Export orders as CSV"""
    anonymize = request.args.get('anonymize', 'false').lower() == 'true'
    orders = db.get_all_orders()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'customer_name', 'customer_phone', 'product_name', 'quantity', 'total_price', 'status', 'created_at'])
    for order in orders:
        name = order['customer_name']
        phone = order['customer_phone']
        if anonymize:
            name = "Customer"
            phone = _mask_phone(phone)
        writer.writerow([order['id'], name, phone, order['product_name'], order['quantity'], order['total_price'], order['status'], order['created_at']])
    return Response(output.getvalue(), mimetype='text/csv')

@app.route('/api/export/messages')
def export_messages():
    """Export messages as CSV"""
    anonymize = request.args.get('anonymize', 'false').lower() == 'true'
    messages = db.get_messages(limit=1000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'conversation_id', 'sender_phone', 'recipient_phone', 'direction', 'delivery_status', 'message_text', 'created_at'])
    for msg in messages:
        sender = msg['sender_phone']
        recipient = msg['recipient_phone']
        if anonymize:
            sender = _mask_phone(sender)
            recipient = _mask_phone(recipient)
        writer.writerow([msg['id'], msg['conversation_id'], sender, recipient, msg['direction'], msg.get('delivery_status'), msg['message_text'], msg['created_at']])
    return Response(output.getvalue(), mimetype='text/csv')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, host='0.0.0.0', port=5001)

