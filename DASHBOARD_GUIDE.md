# Admin Dashboard & New Features Guide

## 🎉 New Features

### 1. Multi-Product Orders

Customers can now order multiple products in a single order!

**New Order Flow:**
```
neworder John Doe 123 Main Street
add 1 2
add 3 1
confirm
```

**Commands:**
- `neworder [name] [address]` - Start a new multi-product order
- `add [product_id] [quantity]` - Add a product to your order
- `confirm` - Place the order
- `cancel` - Cancel current order

**Legacy single-product order still works:**
```
order 1 2 John Doe 123 Main Street
```

### 2. Admin Chat with Customers

Admins can now chat directly with customers through Signal!

**Admin Commands:**
- `chat [customer_phone]` - Start/view conversation with customer
- `reply [customer_phone] [message]` - Send message to customer
- `conversations` - List all active conversations

**Example:**
```
chat +1234567890
reply +1234567890 Hello! Your order is ready for pickup.
```

### 3. Admin Dashboard (Web Interface)

A beautiful web dashboard for managing your store!

**Features:**
- View all orders and update their status
- See all customer conversations
- View and respond to messages
- Real-time statistics
- Send messages to customers directly from the dashboard

## 🚀 Setup Instructions

### 1. Install Dashboard Dependencies

```bash
pip install -r requirements.txt
```

Or:
```bash
pip install Flask flask-cors
```

### 2. Run Database Migration

The migration has already been run, but if you need to run it again:

```bash
python3 scripts/migrate_database.py
```

### 3. Start the Bot

In one terminal:
```bash
python3 start_scheduled.py
```

### 4. Start the Dashboard

In another terminal:
```bash
python3 start_dashboard.py
```

Then open your browser to: **http://localhost:5000**

## 📊 Dashboard Usage

### Orders Tab
- View all orders with their items
- Click "Confirm" or "Cancel" to update order status
- See order details including all products

### Conversations Tab
- Click on a conversation to view messages
- Type a message and click "Send" to reply to customers
- All messages are logged and visible

### Messages Tab
- View all inbound and outbound messages
- See which messages are from admins (marked with [ADMIN])
- Messages are color-coded: blue (inbound), green (outbound), orange (admin)

## 🔧 Configuration

### Setting Admin Users

To give a user admin privileges, update the database:

```python
from bot.database import Database
db = Database()
db.execute_query(
    "UPDATE users SET role = 'admin' WHERE phone_number = ?",
    ('+YOUR_PHONE_NUMBER',)
)
```

Or use SQLite directly:
```bash
sqlite3 data/store.db
UPDATE users SET role = 'admin' WHERE phone_number = '+YOUR_PHONE_NUMBER';
```

## 📝 Notes

- All messages are automatically logged to the database
- Conversations are created automatically when customers message
- The dashboard refreshes stats every 30 seconds
- Multi-product orders show all items in the dashboard
- Admin replies are marked and tracked separately

## 🐛 Troubleshooting

**Dashboard won't start:**
- Make sure Flask is installed: `pip install Flask flask-cors`
- Check if port 5000 is available
- Check logs for errors

**Messages not appearing:**
- Make sure the bot is running (`start_scheduled.py`)
- Check that messages are being logged (check `data/store.db`)

**Admin commands not working:**
- Verify your phone number has 'admin' role in the database
- Check bot logs for permission errors

