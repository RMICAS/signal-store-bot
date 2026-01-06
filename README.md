# Signal Store Bot

A complete store management system that operates through Signal messaging.

## Features
- 📦 Product catalog management
- 🛒 Order processing via Signal
- 👥 Team collaboration
- ⏰ Business hours enforcement (3 PM - 1 AM)
- 📊 Order tracking and statistics
- 🔐 Role-based access control
- 📱 Full Signal messaging integration

## Business Hours
- **Open**: 3:00 PM - 1:00 AM Daily
- **Urgent Contact**: Available for after-hours emergencies

## Quick Start

### 1. Installation

#### Prerequisites
- Python 3.7 or higher
- Java 11 or higher (required for signal-cli)
- signal-cli (see installation below)

#### Install Python Dependencies
```bash
# Clone or download this project
cd signal-store-bot

# Install dependencies (uses standard library only)
pip install -r requirements.txt
```

#### Install signal-cli

**Linux/Mac:**
```bash
# Run the installation script
bash scripts/install_signal_cli.sh
```

**Windows (PowerShell):**
```powershell
# Run the installation script
.\scripts\install_signal_cli.ps1
```

**Manual Installation:**
1. Download signal-cli from [GitHub Releases](https://github.com/AsamK/signal-cli/releases)
2. Extract and add to your PATH
3. Verify: `signal-cli --version`

### 2. Signal Setup

#### Register Your Bot Phone Number
```bash
# Register the bot's phone number with Signal
signal-cli -u +YOUR_BOT_PHONE_NUMBER register

# Verify with SMS code you receive
signal-cli -u +YOUR_BOT_PHONE_NUMBER verify YOUR_CODE
```

#### Configure Settings
Edit `config/settings.py`:
```python
BOT_PHONE_NUMBER = "+1234567890"  # Your bot's Signal number
ADMIN_PHONE = "+1234567890"       # Your admin number
URGENT_CONTACT = "+1234567890"    # Contact for urgent orders
```

### 3. Run the Bot

#### Test Mode (without Signal)
```bash
# Test the bot functionality
python start_bot.py
```

#### Production Mode (with Signal integration)
```bash
# Start the bot with Signal integration and business hours
python start_scheduled.py
```

The bot will:
- Automatically open/close based on business hours (3 PM - 1 AM)
- Listen for Signal messages when open
- Save and process messages received outside business hours
- Handle all customer and team commands

## Usage

### Customer Commands
- `help` - Show available commands
- `products` - View available products
- `order [id] [qty] [name] [address]` - Place an order
- `myorders` - View your orders
- `hours` - Check business hours
- `contact` - Get contact information

### Team Commands (requires team/admin role)
- `orders` - View pending orders
- `stats` - Daily statistics
- `status [order_id] [status]` - Update order status

### Admin Commands (requires admin role)
- `addproduct name:desc:price:stock` - Add product
- `editproduct id:name:desc:price:stock` - Edit product
- `deleteproduct id` - Delete product
- `allproducts` - View all products
- `restock id quantity` - Restock product

## Architecture

- **bot/main.py** - Main bot logic and business hours
- **bot/signal_bridge.py** - Signal CLI integration
- **bot/messaging.py** - Message processing and commands
- **bot/orders.py** - Order management
- **bot/products.py** - Product management
- **bot/database.py** - SQLite database operations
- **start_scheduled.py** - Production runner with Signal integration
- **start_bot.py** - Test mode runner

## Troubleshooting

### signal-cli not found
- Make sure signal-cli is installed and in your PATH
- Check installation: `signal-cli --version`
- On Windows, use full path or add to PATH

### Bot not receiving messages
- Verify bot phone number is registered: `signal-cli -u +NUMBER listAccounts`
- Check if bot is listening (should see logs)
- Ensure business hours are active (3 PM - 1 AM)

### Connection issues
- Test Signal connection: The bot will test on startup
- Check Java installation: `java -version`
- Verify phone number format (E.164: +1234567890)

## License

This project is provided as-is for store management via Signal messaging.