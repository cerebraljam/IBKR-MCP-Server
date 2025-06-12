#!/usr/bin/env python3
"""
Simple test script to validate IBKR MCP Server setup.
Run this before using the MCP server to ensure everything is configured correctly.
"""

import asyncio
import sys
import logging
from src.ibkr_mcp.config import get_default_config
from src.ibkr_mcp.ibkr_client import IBKRClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_ibkr_connection():
    """Test IBKR connection and basic functionality."""
    
    print("🚀 IBKR MCP Server Connection Test")
    print("=" * 50)
    
    try:
        # Load configuration
        print("📋 Loading configuration...")
        config = get_default_config()
        print(f"   Host: {config.host}")
        print(f"   Port: {config.port}")
        print(f"   Client ID: {config.client_id}")
        print(f"   Paper Trading: {config.is_paper}")
        print()
        
        # Test connection
        print("🔌 Connecting to IBKR TWS...")
        async with IBKRClient(config) as client:
            print(f"✅ Connected successfully!")
            print(f"   Account: {client.account}")
            print()
            
            # Test portfolio access
            print("📊 Testing portfolio access...")
            try:
                portfolio = await client.get_portfolio()
                print(f"✅ Portfolio retrieved successfully")
                print(f"   Account: {portfolio.account}")
                print(f"   Positions: {len(portfolio.positions)}")
                print(f"   Total Value: ${portfolio.total_value:,.2f}")
                print(f"   Cash: ${portfolio.total_cash:,.2f}")
                print()
                
                # Show first few positions if any
                if portfolio.positions:
                    print("📈 Sample positions:")
                    for i, pos in enumerate(portfolio.positions[:3]):
                        print(f"   {i+1}. {pos.symbol} ({pos.contract_type}): {pos.quantity} @ ${pos.market_price:.2f}")
                    if len(portfolio.positions) > 3:
                        print(f"   ... and {len(portfolio.positions) - 3} more positions")
                else:
                    print("   No positions found (empty portfolio)")
                print()
                
            except Exception as e:
                print(f"❌ Portfolio access failed: {e}")
                return False
                
            # Test account summary
            print("💰 Testing account summary...")
            try:
                summary = await client.get_account_summary()
                print(f"✅ Account summary retrieved successfully")
                print(f"   Net Liquidation: ${summary.net_liquidation:,.2f}")
                print(f"   Buying Power: ${summary.buying_power:,.2f}")
                print(f"   Available Funds: ${summary.available_funds:,.2f}")
                print()
            except Exception as e:
                print(f"❌ Account summary failed: {e}")
                return False
                
            # Test market data (optional - might fail if no data subscription)
            print("📈 Testing market data (AAPL)...")
            try:
                market_data = await client.get_stock_price("AAPL")
                print(f"✅ Market data retrieved successfully")
                print(f"   AAPL Price: ${market_data.price:.2f}")
                if market_data.bid and market_data.ask:
                    print(f"   Bid/Ask: ${market_data.bid:.2f} / ${market_data.ask:.2f}")
                print()
            except Exception as e:
                print(f"⚠️  Market data test failed (this is often expected): {e}")
                print("   Note: Market data may require subscriptions in TWS")
                print()
                
        print("🎉 All tests completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Run the MCP server: mcp dev src/ibkr_mcp/server.py")
        print("   2. Or integrate with Claude Desktop")
        print("   3. Start exploring your portfolio with AI!")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure TWS or IB Gateway is running")
        print("   2. Check API settings are enabled in TWS")
        print("   3. Verify port settings (7497 for paper, 7496 for live)")
        print("   4. Check firewall settings")
        print("   5. Ensure you're logged into your account")
        return False


def check_prerequisites():
    """Check if prerequisites are installed."""
    print("🔍 Checking prerequisites...")
    
    try:
        import ib_async
        print(f"✅ ib_async version: {ib_async.__version__}")
    except ImportError:
        print("❌ ib_async not found. Run: pip install ib_async")
        return False
        
    try:
        import mcp
        print(f"✅ mcp package found")
    except ImportError:
        print("❌ mcp not found. Run: pip install mcp[cli]")
        return False
        
    try:
        import pydantic
        print(f"✅ pydantic version: {pydantic.__version__}")
    except ImportError:
        print("❌ pydantic not found. Run: pip install pydantic")
        return False
        
    print()
    return True


async def main():
    """Main test function."""
    print("IBKR MCP Server - Connection Test")
    print("=" * 40)
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites check failed. Please install missing packages.")
        sys.exit(1)
    
    # Test IBKR connection
    success = await test_ibkr_connection()
    
    if success:
        print("\n🎉 Setup validation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Setup validation failed. Please check the troubleshooting steps.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 