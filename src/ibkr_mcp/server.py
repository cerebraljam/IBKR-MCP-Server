"""
IBKR MCP Server - Model Context Protocol server for Interactive Brokers TWS API.

This server provides tools, resources, and prompts for interacting with Interactive Brokers
TWS (Trader Workstation) via the ib_async library.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

import nest_asyncio
import mcp.types as types
from mcp.server.fastmcp import FastMCP

# Apply nest_asyncio to allow nested event loops
# This fixes "This event loop is already running" errors in MCP context
nest_asyncio.apply()

from ibkr_mcp.config import get_default_config, IBKRConfig
from ibkr_mcp.ibkr_client import IBKRClient
from ibkr_mcp.models import Portfolio, AccountSummary, MarketData, Order, Trade, Execution, OptionChain

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """Application context with IBKR client and configuration."""
    ibkr_client: IBKRClient
    config: IBKRConfig


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage IBKR connection lifecycle with type-safe context."""
    logger.info("Starting IBKR MCP Server...")
    
    # Initialize IBKR client
    config = get_default_config()
    ibkr_client = IBKRClient(config)
    
    try:
        # Connect to IBKR
        connected = await ibkr_client.connect()
        if not connected:
            logger.warning("Failed to connect to IBKR TWS - server will run in offline mode")
        else:
            logger.info(f"Connected to IBKR TWS (Paper: {config.is_paper})")
        
        yield AppContext(ibkr_client=ibkr_client, config=config)
        
    finally:
        # Cleanup
        if ibkr_client:
            await ibkr_client.disconnect()
        logger.info("IBKR MCP Server shutdown")


# Create MCP server with lifespan
mcp = FastMCP("IBKR-MCP-Server", lifespan=app_lifespan)


# Tools Implementation using @mcp.tool()

@mcp.tool()
async def get_portfolio() -> str:
    """Get the current portfolio with all positions, cash, and P&L information."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    try:
        portfolio = await ibkr_client.get_portfolio()
        return json.dumps(portfolio.to_dict(), indent=2)
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return f"Error getting portfolio: {str(e)}"


@mcp.tool()
async def get_account_summary() -> str:
    """Get account summary including cash balances, margin requirements, and key metrics."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    try:
        summary = await ibkr_client.get_account_summary()
        return json.dumps(summary.to_dict(), indent=2)
    except Exception as e:
        logger.error(f"Error getting account summary: {e}")
        return f"Error getting account summary: {str(e)}"


@mcp.tool()
async def get_stock_price(symbol: str, exchange: str = "SMART") -> str:
    """Get current stock price and market data.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
        exchange: Exchange to use (default: 'SMART' for best execution)
    """
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    try:
        market_data = await ibkr_client.get_stock_price(symbol.upper(), exchange)
        return json.dumps(market_data.to_dict(), indent=2)
    except Exception as e:
        logger.error(f"Error getting stock price for {symbol}: {e}")
        return f"Error getting stock price for {symbol}: {str(e)}"


@mcp.tool()
async def get_option_price(symbol: str, expiry: str, strike: float, right: str, exchange: str = "SMART") -> str:
    """Get current option price and market data.

    Args:
        symbol: Underlying stock symbol (e.g., 'AAPL')
        expiry: Option expiry date in YYYYMMDD format (e.g., '20241220')
        strike: Strike price (e.g., 150.0)
        right: Option type - 'C' for call, 'P' for put
        exchange: Exchange to use (default: 'SMART')
    """
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    # Validate right parameter
    if right.upper() not in ['C', 'P']:
        return "Error: 'right' must be 'C' for call or 'P' for put"

    try:
        market_data = await ibkr_client.get_option_price(
            symbol.upper(), expiry, float(strike), right.upper(), exchange
        )
        return json.dumps(market_data.to_dict(), indent=2)
    except Exception as e:
        logger.error(f"Error getting option price: {e}")
        return f"Error getting option price: {str(e)}"


@mcp.tool()
async def get_connection_status() -> str:
    """Get the current connection status and configuration."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return json.dumps({
            "connected": False,
            "error": "IBKR client not initialized"
        }, indent=2)

    try:
        # Check if connection is actually alive
        is_alive = ibkr_client.is_connection_alive()

        status = {
            "connected": ibkr_client.connected,
            "connection_alive": is_alive,
            "account": ibkr_client.account,
            "config": {
                "host": ibkr_client.config.host,
                "port": ibkr_client.config.port,
                "client_id": ibkr_client.config.client_id,
                "is_paper": ibkr_client.config.is_paper,
            },
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(status, indent=2)
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        return f"Error getting connection status: {str(e)}"


@mcp.tool()
async def get_orders(include_inactive: bool = False) -> str:
    """Get orders - pending orders by default, or all orders including filled/cancelled.

    Args:
        include_inactive: If True, include filled and cancelled orders. Default is False (only open orders).
    """
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    # Try to ensure connection (with auto-reconnect)
    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    try:
        orders = await ibkr_client.get_orders(include_inactive=include_inactive)
        result = {
            "order_count": len(orders),
            "include_inactive": include_inactive,
            "orders": [order.to_dict() for order in orders],
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return f"Error getting orders: {str(e)}"


@mcp.tool()
async def get_trades() -> str:
    """Get all trades with execution status, fill prices, and commission information."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    try:
        trades = await ibkr_client.get_trades()
        result = {
            "trade_count": len(trades),
            "trades": [trade.to_dict() for trade in trades],
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return f"Error getting trades: {str(e)}"


@mcp.tool()
async def get_executions() -> str:
    """Get execution/fill details including prices, commissions, and realized P&L."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    try:
        executions = await ibkr_client.get_executions()
        result = {
            "execution_count": len(executions),
            "executions": [ex.to_dict() for ex in executions],
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting executions: {e}")
        return f"Error getting executions: {str(e)}"


@mcp.tool()
async def cancel_order(order_id: int) -> str:
    """Cancel an open order by its order ID.

    Args:
        order_id: The order ID to cancel (found in get_orders output)
    """
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    try:
        success = await ibkr_client.cancel_order(order_id)
        if success:
            return json.dumps({
                "success": True,
                "message": f"Cancel request sent for order {order_id}",
                "timestamp": datetime.now().isoformat()
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "message": f"Order {order_id} not found in open orders",
                "timestamp": datetime.now().isoformat()
            }, indent=2)
    except Exception as e:
        logger.error(f"Error cancelling order {order_id}: {e}")
        return f"Error cancelling order: {str(e)}"


@mcp.tool()
async def get_option_chain(symbol: str, expiry: str, strike_count: int = 10, exchange: str = "SMART") -> str:
    """Get option chain with Greeks (delta, gamma, theta, vega, IV) for a symbol and expiration.

    Args:
        symbol: Underlying stock symbol (e.g., 'AAPL')
        expiry: Option expiry date in YYYYMMDD format (e.g., '20241220')
        strike_count: Number of strikes to return around ATM (default 10)
        exchange: Exchange to use (default: 'SMART')
    """
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    try:
        chain = await ibkr_client.get_option_chain(
            symbol.upper(),
            expiry,
            strike_range=strike_count,
            exchange=exchange
        )
        return json.dumps(chain.to_dict(), indent=2)
    except Exception as e:
        logger.error(f"Error getting option chain for {symbol}: {e}")
        return f"Error getting option chain: {str(e)}"


@mcp.tool()
async def get_option_expirations(symbol: str, exchange: str = "SMART") -> str:
    """Get available option expiration dates for a symbol.

    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        exchange: Exchange to use (default: 'SMART')
    """
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS and reconnection failed"

    try:
        expirations = await ibkr_client.get_option_expirations(symbol.upper(), exchange)
        result = {
            "symbol": symbol.upper(),
            "expiration_count": len(expirations),
            "expirations": expirations,
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting option expirations for {symbol}: {e}")
        return f"Error getting option expirations: {str(e)}"


# Resources Implementation

@mcp.resource("portfolio://current")
async def get_portfolio_resource() -> str:
    """Current portfolio as a resource for LLM context."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS"

    try:
        portfolio = await ibkr_client.get_portfolio()
        return f"Portfolio for account {portfolio.account}:\n\n" + json.dumps(portfolio.to_dict(), indent=2)
    except Exception as e:
        logger.error(f"Error reading portfolio resource: {e}")
        return f"Error reading portfolio resource: {str(e)}"


@mcp.resource("account://summary")
async def get_account_summary_resource() -> str:
    """Account summary as a resource for LLM context."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS"

    try:
        summary = await ibkr_client.get_account_summary()
        return f"Account summary for {summary.account}:\n\n" + json.dumps(summary.to_dict(), indent=2)
    except Exception as e:
        logger.error(f"Error reading account summary resource: {e}")
        return f"Error reading account summary resource: {str(e)}"


@mcp.resource("positions://all")
async def get_positions_resource() -> str:
    """All positions as a resource for LLM context."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS"

    try:
        portfolio = await ibkr_client.get_portfolio()
        positions_data = {
            "account": portfolio.account,
            "position_count": len(portfolio.positions),
            "positions": [pos.to_dict() for pos in portfolio.positions],
            "timestamp": portfolio.timestamp
        }
        return f"All positions for account {portfolio.account}:\n\n" + json.dumps(positions_data, indent=2)
    except Exception as e:
        logger.error(f"Error reading positions resource: {e}")
        return f"Error reading positions resource: {str(e)}"


@mcp.resource("orders://open")
async def get_open_orders_resource() -> str:
    """Open/pending orders as a resource for LLM context."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS"

    try:
        orders = await ibkr_client.get_orders(include_inactive=False)
        result = {
            "order_count": len(orders),
            "orders": [order.to_dict() for order in orders],
            "timestamp": datetime.now().isoformat()
        }
        return f"Open orders ({len(orders)} total):\n\n" + json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error reading orders resource: {e}")
        return f"Error reading orders resource: {str(e)}"


@mcp.resource("trades://today")
async def get_trades_resource() -> str:
    """Today's trades as a resource for LLM context."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client

    if not ibkr_client:
        return "Error: IBKR client not initialized"

    if not await ibkr_client.ensure_connected():
        return "Error: Not connected to IBKR TWS"

    try:
        trades = await ibkr_client.get_trades()
        result = {
            "trade_count": len(trades),
            "trades": [trade.to_dict() for trade in trades],
            "timestamp": datetime.now().isoformat()
        }
        return f"Today's trades ({len(trades)} total):\n\n" + json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error reading trades resource: {e}")
        return f"Error reading trades resource: {str(e)}"


# Prompts Implementation

@mcp.prompt("analyze_portfolio")
def analyze_portfolio_prompt() -> types.GetPromptResult:
    """Analyze the current portfolio performance and provide insights."""
    return types.GetPromptResult(
        description="Analyze the current portfolio performance and provide insights",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text="""Please analyze my current portfolio using the portfolio://current resource. 

Focus on:
1. Overall portfolio performance (P&L analysis)
2. Position sizes and risk concentration
3. Asset allocation breakdown
4. Any notable winners or losers
5. Recommendations for portfolio optimization

Use the get_portfolio() tool to get the latest data if needed."""
                )
            )
        ]
    )


@mcp.prompt("market_check")
def market_check_prompt(symbols: str = "") -> types.GetPromptResult:
    """Check current market prices for specified symbols.

    Args:
        symbols: Comma-separated list of symbols to check
    """
    return types.GetPromptResult(
        description="Check current market prices for specified symbols",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"""Please check the current market prices for these symbols: {symbols}

For each symbol:
1. Get the current price using get_stock_price()
2. Compare with any existing positions in my portfolio
3. Provide market insights or notable price movements

Use the portfolio://current resource to see if I have positions in these symbols."""
                )
            )
        ]
    )


@mcp.prompt("analyze_options")
def analyze_options_prompt(symbol: str = "") -> types.GetPromptResult:
    """Analyze options for a stock with Greeks and strategy suggestions.

    Args:
        symbol: Stock symbol to analyze options for
    """
    return types.GetPromptResult(
        description="Analyze options chain and Greeks for a symbol",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"""Please analyze the options for {symbol}:

1. First, get the current stock price using get_stock_price()
2. Get available expirations using get_option_expirations()
3. For the nearest weekly and monthly expiration, get the option chain using get_option_chain()

Analyze:
- Current implied volatility levels
- Key Greeks (delta, theta, gamma) at various strikes
- Identify notable put/call skew
- Suggest potential strategies based on the Greeks and IV

Focus on educational insights about what the Greeks tell us about these options."""
                )
            )
        ]
    )


@mcp.prompt("review_orders")
def review_orders_prompt() -> types.GetPromptResult:
    """Review current open orders and recent trades."""
    return types.GetPromptResult(
        description="Review open orders and recent trade activity",
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text="""Please review my current trading activity:

1. Get my open orders using get_orders()
2. Get my recent trades and executions using get_trades() and get_executions()

Provide:
- Summary of pending orders (what's waiting to fill)
- Summary of today's executed trades
- Total commissions paid
- Any realized P&L from today's trades

Use the orders://open and trades://today resources for context."""
                )
            )
        ]
    )


if __name__ == "__main__":
    # FastMCP handles the server setup automatically
    mcp.run() 