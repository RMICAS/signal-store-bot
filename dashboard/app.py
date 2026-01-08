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

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from bot.database import Database
from bot.signal_bridge import SignalBridge
from config.settings import BOT_PHONE_NUMBER
import logging

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Initialize database and signal bridge
db = Database()
signal_bridge = None

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
    
    messages = db.get_messages(limit=limit, conversation_id=conversation_id)
    
    # Convert datetime objects to strings
    for msg in messages:
        if 'created_at' in msg:
            msg['created_at'] = str(msg['created_at'])
    
    return jsonify(messages)

@app.route('/api/conversations')
def get_conversations():
    """Get all conversations"""
    status = request.args.get('status', None)
    
    if status:
        conversations = db.fetch_all(
            "SELECT * FROM conversations WHERE status = ? ORDER BY last_message_at DESC",
            (status,)
        )
    else:
        conversations = db.get_conversations()
    
    # Convert datetime objects to strings
    for conv in conversations:
        if 'created_at' in conv:
            conv['created_at'] = str(conv['created_at'])
        if 'last_message_at' in conv:
            conv['last_message_at'] = str(conv['last_message_at'])
    
    return jsonify(conversations)

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
    orders = db.get_all_orders(status=status)
    
    # Add items to each order
    for order in orders:
        order['items'] = db.get_order_items(order['id'])
        if 'created_at' in order:
            order['created_at'] = str(order['created_at'])
        if 'updated_at' in order:
            order['updated_at'] = str(order['updated_at'])
    
    return jsonify(orders)

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
            conversation_id=conv_id
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

@app.route('/api/stats')
def get_stats():
    """Get dashboard statistics"""
    from datetime import date
    
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
        "SELECT COUNT(*) as count FROM conversations WHERE status = 'active'",
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

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, host='0.0.0.0', port=5001)

