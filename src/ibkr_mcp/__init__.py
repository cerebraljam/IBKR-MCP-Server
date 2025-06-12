"""
IBKR MCP Server - Model Context Protocol server for Interactive Brokers TWS API.

This package provides MCP tools and resources for interacting with Interactive Brokers
through the TWS API using ib_async.
"""

__version__ = "0.1.0"
__author__ = "IBKR MCP Server"

from ibkr_mcp.server import mcp

__all__ = ["mcp"] 