# IBKR-MCP-Server

A Model Context Protocol (MCP) Server for Interactive Brokers TWS API that enables AI assistants to access portfolio data, account information, and real-time market prices.

## Features

- `get_portfolio()` - Retrieve current portfolio with positions and P&L
- `get_account_summary()` - Get account balances and key metrics
- `get_stock_price(symbol)` - Look up current stock prices
- `get_option_price(symbol, expiry, strike, right)` - Get option prices

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
# Test connection
uv run python test_connection.py
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

- "Analyze my current portfolio performance"
- "What's the current price of AAPL and MSFT?"
- "Show me my account summary"

## Troubleshooting

**Connection Issues:**
- Ensure TWS/IB Gateway is running
- Check API settings are enabled in TWS
- Verify correct port (7497 vs 7496)

**Permission Issues:**
- Disable "Read-Only API" in TWS settings
- Enable API in TWS global configuration

---

⚠️ **Disclaimer**: This software is for educational purposes. Use at your own risk. Start with paper trading.
