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

import mcp.types as types
from mcp.server.fastmcp import FastMCP

from ibkr_mcp.config import get_default_config, IBKRConfig
from ibkr_mcp.ibkr_client import IBKRClient
from ibkr_mcp.models import Portfolio, AccountSummary, MarketData

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
    
    if not ibkr_client or not ibkr_client.connected:
        return "Error: Not connected to IBKR TWS"
    
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
    
    if not ibkr_client or not ibkr_client.connected:
        return "Error: Not connected to IBKR TWS"
    
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
    
    if not ibkr_client or not ibkr_client.connected:
        return "Error: Not connected to IBKR TWS"
    
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
    
    if not ibkr_client or not ibkr_client.connected:
        return "Error: Not connected to IBKR TWS"
    
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
def get_connection_status() -> str:
    """Get the current connection status and configuration."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client
    
    if not ibkr_client:
        return json.dumps({
            "connected": False,
            "error": "IBKR client not initialized"
        }, indent=2)
    
    try:
        status = {
            "connected": ibkr_client.connected,
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


# Resources Implementation

@mcp.resource("portfolio://current")
async def get_portfolio_resource() -> str:
    """Current portfolio as a resource for LLM context."""
    ctx = mcp.get_context()
    ibkr_client = ctx.request_context.lifespan_context.ibkr_client
    
    if not ibkr_client or not ibkr_client.connected:
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
    
    if not ibkr_client or not ibkr_client.connected:
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
    
    if not ibkr_client or not ibkr_client.connected:
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


if __name__ == "__main__":
    # FastMCP handles the server setup automatically
    mcp.run() 