"""
IBKR MCP Server - Model Context Protocol server for Interactive Brokers TWS API.

This server provides tools, resources, and prompts for interacting with Interactive Brokers
TWS (Trader Workstation) via the ib_async library.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from datetime import datetime
from collections.abc import AsyncIterator

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from ibkr_mcp.config import get_default_config, IBKRConfig
from ibkr_mcp.ibkr_client import IBKRClient
from ibkr_mcp.models import Portfolio, AccountSummary, MarketData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global IBKR client instance
ibkr_client: Optional[IBKRClient] = None


@asynccontextmanager
async def server_lifespan(server: Server) -> AsyncIterator[Dict[str, Any]]:
    """Manage IBKR connection lifecycle."""
    global ibkr_client
    
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
        
        yield {"ibkr_client": ibkr_client, "config": config}
        
    finally:
        # Cleanup
        if ibkr_client:
            await ibkr_client.disconnect()
        logger.info("IBKR MCP Server shutdown")


# Create MCP server with lifespan management
server = Server("IBKR-MCP-Server", lifespan=server_lifespan)


# Tools Implementation

@server.call_tool()
async def get_portfolio(name: str, arguments: dict) -> list[types.TextContent]:
    """Get the current portfolio with all positions, cash, and P&L information."""
    global ibkr_client
    
    if name != "get_portfolio":
        raise ValueError(f"Unknown tool: {name}")
    
    if not ibkr_client or not ibkr_client.connected:
        return [types.TextContent(type="text", text="Error: Not connected to IBKR TWS")]
    
    try:
        portfolio = await ibkr_client.get_portfolio()
        result = json.dumps(portfolio.to_dict(), indent=2)
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return [types.TextContent(type="text", text=f"Error getting portfolio: {str(e)}")]


@server.call_tool()
async def get_account_summary(name: str, arguments: dict) -> list[types.TextContent]:
    """Get account summary including cash balances, margin requirements, and key metrics."""
    global ibkr_client
    
    if name != "get_account_summary":
        raise ValueError(f"Unknown tool: {name}")
    
    if not ibkr_client or not ibkr_client.connected:
        return [types.TextContent(type="text", text="Error: Not connected to IBKR TWS")]
    
    try:
        summary = await ibkr_client.get_account_summary()
        result = json.dumps(summary.to_dict(), indent=2)
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Error getting account summary: {e}")
        return [types.TextContent(type="text", text=f"Error getting account summary: {str(e)}")]


@server.call_tool()
async def get_stock_price(name: str, arguments: dict) -> list[types.TextContent]:
    """Get current stock price and market data."""
    global ibkr_client
    
    if name != "get_stock_price":
        raise ValueError(f"Unknown tool: {name}")
    
    if not ibkr_client or not ibkr_client.connected:
        return [types.TextContent(type="text", text="Error: Not connected to IBKR TWS")]
    
    symbol = arguments.get("symbol")
    exchange = arguments.get("exchange", "SMART")
    
    if not symbol:
        return [types.TextContent(type="text", text="Error: 'symbol' argument is required")]
    
    try:
        market_data = await ibkr_client.get_stock_price(symbol.upper(), exchange)
        result = json.dumps(market_data.to_dict(), indent=2)
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Error getting stock price for {symbol}: {e}")
        return [types.TextContent(type="text", text=f"Error getting stock price for {symbol}: {str(e)}")]


@server.call_tool()
async def get_option_price(name: str, arguments: dict) -> list[types.TextContent]:
    """Get current option price and market data."""
    global ibkr_client
    
    if name != "get_option_price":
        raise ValueError(f"Unknown tool: {name}")
    
    if not ibkr_client or not ibkr_client.connected:
        return [types.TextContent(type="text", text="Error: Not connected to IBKR TWS")]
    
    symbol = arguments.get("symbol")
    expiry = arguments.get("expiry")
    strike = arguments.get("strike")
    right = arguments.get("right")
    exchange = arguments.get("exchange", "SMART")
    
    if not all([symbol, expiry, strike, right]):
        return [types.TextContent(type="text", text="Error: 'symbol', 'expiry', 'strike', and 'right' arguments are required")]
    
    # Validate right parameter
    if right.upper() not in ['C', 'P']:
        return [types.TextContent(type="text", text="Error: 'right' must be 'C' for call or 'P' for put")]
    
    try:
        market_data = await ibkr_client.get_option_price(
            symbol.upper(), expiry, float(strike), right.upper(), exchange
        )
        result = json.dumps(market_data.to_dict(), indent=2)
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Error getting option price: {e}")
        return [types.TextContent(type="text", text=f"Error getting option price: {str(e)}")]


@server.call_tool()
async def get_connection_status(name: str, arguments: dict) -> list[types.TextContent]:
    """Get the current connection status and configuration."""
    global ibkr_client
    
    if name != "get_connection_status":
        raise ValueError(f"Unknown tool: {name}")
    
    if not ibkr_client:
        result = json.dumps({
            "connected": False,
            "error": "IBKR client not initialized"
        }, indent=2)
        return [types.TextContent(type="text", text=result)]
    
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
        result = json.dumps(status, indent=2)
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        return [types.TextContent(type="text", text=f"Error getting connection status: {str(e)}")]


# List Tools Handler

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="get_portfolio",
            description="Get the current portfolio with all positions, cash, and P&L information",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_account_summary",
            description="Get account summary including cash balances, margin requirements, and key metrics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_stock_price",
            description="Get current stock price and market data",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., 'AAPL', 'MSFT')"
                    },
                    "exchange": {
                        "type": "string",
                        "description": "Exchange to use (default: 'SMART' for best execution)",
                        "default": "SMART"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_option_price",
            description="Get current option price and market data",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Underlying stock symbol (e.g., 'AAPL')"
                    },
                    "expiry": {
                        "type": "string",
                        "description": "Option expiry date in YYYYMMDD format (e.g., '20241220')"
                    },
                    "strike": {
                        "type": "number",
                        "description": "Strike price (e.g., 150.0)"
                    },
                    "right": {
                        "type": "string",
                        "description": "Option type - 'C' for call, 'P' for put"
                    },
                    "exchange": {
                        "type": "string",
                        "description": "Exchange to use (default: 'SMART')",
                        "default": "SMART"
                    }
                },
                "required": ["symbol", "expiry", "strike", "right"]
            }
        ),
        types.Tool(
            name="get_connection_status",
            description="Get the current connection status and configuration",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


# Resources Implementation

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Handle resource requests."""
    global ibkr_client
    
    if not ibkr_client or not ibkr_client.connected:
        return "Error: Not connected to IBKR TWS"
    
    try:
        if uri == "portfolio://current":
            portfolio = await ibkr_client.get_portfolio()
            return f"Portfolio for account {portfolio.account}:\n\n" + json.dumps(portfolio.to_dict(), indent=2)
        
        elif uri == "account://summary":
            summary = await ibkr_client.get_account_summary()
            return f"Account summary for {summary.account}:\n\n" + json.dumps(summary.to_dict(), indent=2)
        
        elif uri == "positions://all":
            portfolio = await ibkr_client.get_portfolio()
            positions_data = {
                "account": portfolio.account,
                "position_count": len(portfolio.positions),
                "positions": [pos.to_dict() for pos in portfolio.positions],
                "timestamp": portfolio.timestamp
            }
            return f"All positions for account {portfolio.account}:\n\n" + json.dumps(positions_data, indent=2)
        
        else:
            raise ValueError(f"Unknown resource: {uri}")
            
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        return f"Error reading resource {uri}: {str(e)}"


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available resources."""
    return [
        types.Resource(
            uri="portfolio://current",
            name="Current Portfolio",
            description="Current portfolio as a resource for LLM context",
            mimeType="application/json"
        ),
        types.Resource(
            uri="account://summary",
            name="Account Summary",
            description="Account summary as a resource for LLM context",
            mimeType="application/json"
        ),
        types.Resource(
            uri="positions://all",
            name="All Positions",
            description="All positions as a resource for LLM context",
            mimeType="application/json"
        )
    ]


# Prompts Implementation

@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
    """Handle prompt requests."""
    if name == "analyze_portfolio":
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
    
    elif name == "market_check":
        symbols = arguments.get("symbols", "") if arguments else ""
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
    
    else:
        raise ValueError(f"Unknown prompt: {name}")


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """List available prompts."""
    return [
        types.Prompt(
            name="analyze_portfolio",
            description="Analyze the current portfolio performance and provide insights",
            arguments=[]
        ),
        types.Prompt(
            name="market_check",
            description="Check current market prices for specified symbols",
            arguments=[
                types.PromptArgument(
                    name="symbols",
                    description="Comma-separated list of symbols to check",
                    required=True
                )
            ]
        )
    ]


async def run():
    """Run the MCP server using stdio transport."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="IBKR-MCP-Server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run()) 