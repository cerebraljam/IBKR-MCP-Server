# IBKR-MCP-Server

A comprehensive Model Context Protocol (MCP) Server for Interactive Brokers TWS API that enables AI assistants to access portfolio data, account information, real-time market prices, order management, and advanced options analytics with Greeks.

## Features

### Portfolio & Account Management
- `get_portfolio()` - Retrieve current portfolio with positions and P&L
- `get_account_summary()` - Get account balances, margin requirements, and key metrics
- `get_connection_status()` - Check connection health and auto-reconnect

### Market Data
- `get_stock_price(symbol)` - Look up current stock prices with bid/ask
- `get_option_price(symbol, expiry, strike, right)` - Get individual option prices
- `get_option_expirations(symbol)` - Get all available option expiration dates
- `get_option_chain(symbol, expiry, strike_count)` - Full option chain with Greeks (delta, gamma, theta, vega, IV)

### Order Management
- `get_orders(include_inactive)` - View pending orders or all orders (including filled/cancelled)
- `get_trades()` - View trades with execution status, fill prices, and commissions
- `get_executions()` - Get detailed execution/fill information with realized P&L
- `cancel_order(order_id)` - Cancel an open order by ID

### Advanced Features
- **Auto-Reconnection**: Automatically reconnects if TWS connection is lost (up to 3 attempts)
- **Options Greeks**: Full Greek calculations (delta, gamma, theta, vega, rho, implied volatility)
- **Commission Tracking**: Detailed commission and P&L reporting on executions
- **Resource Endpoints**: LLM-friendly resources for portfolio, orders, and trades

## Prerequisites

1. **Interactive Brokers Account** (Paper or Live)
2. **TWS (Trader Workstation)** or **IB Gateway** running
3. **Python 3.10+**

## Quick Start

### 1. Install Dependencies

```bash
# Clone and setup
git clone https://github.com/your-username/IBKR-MCP-Server.git
cd IBKR-MCP-Server

# Install with UV (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# Or with pip
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

### 2. Configure Connection

```bash
# Copy example config
cp env.example .env

# Edit .env file:
IBKR_HOST=127.0.0.1
IBKR_PORT=7497              # 7497 for paper, 7496 for live
IBKR_CLIENT_ID=1
IBKR_IS_PAPER=true          # true for paper, false for live
```

### 3. Configure TWS

In TWS, go to **Configure** → **Global Configuration** → **API** → **Settings**:
- ✅ **Enable ActiveX and Socket Clients**
- ✅ **Socket port**: 7497 (paper) or 7496 (live)
- ❌ **Read-Only API** (must be disabled)

### 4. Test Setup

```bash
# Run all tests
uv run python test_connection.py

# Run specific test groups
uv run python test_connection.py --basic    # Connection, portfolio, account
uv run python test_connection.py --orders   # Orders, trades, executions
uv run python test_connection.py --options  # Option chains and Greeks
```

### 5. Run Server

```bash
# Start the MCP server
uv run python src/ibkr_mcp/server.py
```

### 6. Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ibkr": {
      "command": "uv",
      "args": ["run", "python", "src/ibkr_mcp/server.py"],
      "cwd": "/path/to/IBKR-MCP-Server",
      "env": {
        "IBKR_PORT": "7497",
        "IBKR_IS_PAPER": "true"
      }
    }
  }
}
```

## Usage Examples

### Portfolio & Account
- "Analyze my current portfolio performance"
- "Show me my account summary with margin details"
- "What positions do I currently have?"

### Market Data & Options
- "What's the current price of AAPL and MSFT?"
- "Show me the option chain for AAPL with the nearest expiration"
- "What are the available expiration dates for SPY options?"
- "Analyze the Greeks for TSLA options - what's the implied volatility?"

### Order Management
- "Show me my pending orders"
- "What trades did I execute today?"
- "Show me my execution history with commissions"
- "How much did I pay in commissions today?"

### Advanced Analysis
- "Compare the delta and IV across different strikes for AAPL options"
- "Show me profitable options strategies based on current Greeks"
- "What's my total realized P&L from today's trades?"

### Built-in Prompts
Use these specialized prompts for guided workflows:
- `/analyze_options AAPL` - Comprehensive options analysis with Greeks
- `/review_orders` - Review pending orders and recent trades
- `/analyze_portfolio` - Deep dive into portfolio performance
- `/market_check AAPL,MSFT,GOOGL` - Check prices for multiple symbols

## MCP Resources

The server exposes these resources for LLM context:
- `portfolio://current` - Current portfolio snapshot
- `account://summary` - Account summary data
- `positions://all` - All positions list
- `orders://open` - Open/pending orders
- `trades://today` - Today's trades

## API Reference

### Data Models
- **Order** - Order information (ID, symbol, quantity, price, status)
- **Trade** - Trade with execution status and commission
- **Execution** - Individual fill with price and P&L
- **OptionGreeks** - Delta, gamma, theta, vega, rho, IV
- **OptionChain** - Complete option chain with strikes and Greeks

### Tool Parameters
```python
get_option_chain(
    symbol: str,           # e.g., "AAPL"
    expiry: str,          # YYYYMMDD format, e.g., "20241220"
    strike_count: int = 10,  # Number of strikes around ATM
    exchange: str = "SMART"
)

get_orders(
    include_inactive: bool = False  # Include filled/cancelled orders
)

cancel_order(
    order_id: int  # Order ID from get_orders()
)
```

## Troubleshooting

### Connection Issues
- Ensure TWS/IB Gateway is running
- Check API settings are enabled in TWS
- Verify correct port (7497 vs 7496)
- **Auto-reconnect**: The server automatically attempts to reconnect up to 3 times if connection is lost

### Permission Issues
- Disable "Read-Only API" in TWS settings
- Enable API in TWS global configuration

### Market Data Issues
- Some features require market data subscriptions in your IBKR account
- Options Greeks require live market data during trading hours
- Delayed data may show as $0.00 or None

## Contributing

This is a fork with enhancements. Original repository: [xiao81/IBKR-MCP-Server](https://github.com/xiao81/IBKR-MCP-Server)

### Key Enhancements in This Fork
- Order management (view, cancel)
- Trade and execution history
- Full option chain with Greeks
- Auto-reconnection logic
- Comprehensive test suite
- Additional MCP resources and prompts

## License

See LICENSE file for details.

---

⚠️ **Disclaimer**: This software is for educational purposes. Use at your own risk. Start with paper trading. Not affiliated with Interactive Brokers.
