#!/usr/bin/env python3
"""
Comprehensive test script to validate IBKR MCP Server setup.
Run this before using the MCP server to ensure everything is configured correctly.

Usage:
    python test_connection.py           # Run all tests
    python test_connection.py --basic   # Run basic tests only
    python test_connection.py --orders  # Run order-related tests
    python test_connection.py --options # Run options-related tests
"""

import asyncio
import sys
import logging
import argparse
from datetime import datetime, timedelta
from src.ibkr_mcp.config import get_default_config
from src.ibkr_mcp.ibkr_client import IBKRClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestResults:
    """Track test results."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []

    def add_pass(self, name: str, details: str = ""):
        self.passed += 1
        self.results.append(("PASS", name, details))

    def add_fail(self, name: str, error: str):
        self.failed += 1
        self.results.append(("FAIL", name, error))

    def add_skip(self, name: str, reason: str):
        self.skipped += 1
        self.results.append(("SKIP", name, reason))

    def summary(self):
        return f"Passed: {self.passed}, Failed: {self.failed}, Skipped: {self.skipped}"


async def test_connection(client: IBKRClient, results: TestResults):
    """Test basic connection."""
    print("\n🔌 Testing connection...")

    try:
        is_alive = client.is_connection_alive()
        if is_alive:
            results.add_pass("Connection alive check", f"Account: {client.account}")
            print(f"   ✅ Connection is alive (Account: {client.account})")
        else:
            results.add_fail("Connection alive check", "Connection not alive")
            print("   ❌ Connection is not alive")
    except Exception as e:
        results.add_fail("Connection alive check", str(e))
        print(f"   ❌ Error: {e}")


async def test_portfolio(client: IBKRClient, results: TestResults):
    """Test portfolio access."""
    print("\n📊 Testing portfolio access...")

    try:
        portfolio = await client.get_portfolio()
        results.add_pass(
            "Portfolio access",
            f"{len(portfolio.positions)} positions, ${portfolio.total_value:,.2f} value"
        )
        print(f"   ✅ Portfolio retrieved successfully")
        print(f"      Positions: {len(portfolio.positions)}")
        print(f"      Total Value: ${portfolio.total_value:,.2f}")
        print(f"      Cash: ${portfolio.total_cash:,.2f}")

        if portfolio.positions:
            print("      Sample positions:")
            for i, pos in enumerate(portfolio.positions[:3]):
                print(f"        {i+1}. {pos.symbol} ({pos.contract_type}): {pos.quantity} @ ${pos.market_price:.2f}")
            if len(portfolio.positions) > 3:
                print(f"        ... and {len(portfolio.positions) - 3} more")

    except Exception as e:
        results.add_fail("Portfolio access", str(e))
        print(f"   ❌ Failed: {e}")


async def test_account_summary(client: IBKRClient, results: TestResults):
    """Test account summary."""
    print("\n💰 Testing account summary...")

    try:
        summary = await client.get_account_summary()
        results.add_pass(
            "Account summary",
            f"Net Liq: ${summary.net_liquidation:,.2f}"
        )
        print(f"   ✅ Account summary retrieved successfully")
        print(f"      Net Liquidation: ${summary.net_liquidation:,.2f}")
        print(f"      Buying Power: ${summary.buying_power:,.2f}")
        print(f"      Available Funds: ${summary.available_funds:,.2f}")
        print(f"      Margin Req: ${summary.maint_margin_req:,.2f}")

    except Exception as e:
        results.add_fail("Account summary", str(e))
        print(f"   ❌ Failed: {e}")


async def test_stock_price(client: IBKRClient, results: TestResults, symbol: str = "AAPL"):
    """Test stock price retrieval."""
    print(f"\n📈 Testing stock price ({symbol})...")

    try:
        market_data = await client.get_stock_price(symbol)
        if market_data.price > 0:
            results.add_pass("Stock price", f"{symbol}: ${market_data.price:.2f}")
            print(f"   ✅ {symbol} Price: ${market_data.price:.2f}")
            if market_data.bid and market_data.ask:
                print(f"      Bid/Ask: ${market_data.bid:.2f} / ${market_data.ask:.2f}")
        else:
            results.add_skip("Stock price", "No price data (market may be closed)")
            print(f"   ⚠️  No price data available (market may be closed)")

    except Exception as e:
        results.add_fail("Stock price", str(e))
        print(f"   ❌ Failed: {e}")


async def test_orders(client: IBKRClient, results: TestResults):
    """Test orders retrieval."""
    print("\n📋 Testing orders retrieval...")

    try:
        # Test open orders
        open_orders = await client.get_orders(include_inactive=False)
        results.add_pass("Open orders", f"{len(open_orders)} open orders")
        print(f"   ✅ Open orders: {len(open_orders)}")

        if open_orders:
            print("      Sample orders:")
            for i, order in enumerate(open_orders[:3]):
                print(f"        {i+1}. {order.action} {order.total_quantity} {order.symbol} @ {order.limit_price or 'MKT'} ({order.status})")

        # Test all orders (including filled/cancelled)
        all_orders = await client.get_orders(include_inactive=True)
        results.add_pass("All orders", f"{len(all_orders)} total orders")
        print(f"   ✅ All orders (including inactive): {len(all_orders)}")

    except Exception as e:
        results.add_fail("Orders retrieval", str(e))
        print(f"   ❌ Failed: {e}")


async def test_trades(client: IBKRClient, results: TestResults):
    """Test trades retrieval."""
    print("\n📊 Testing trades retrieval...")

    try:
        trades = await client.get_trades()
        results.add_pass("Trades", f"{len(trades)} trades")
        print(f"   ✅ Trades retrieved: {len(trades)}")

        if trades:
            print("      Sample trades:")
            for i, trade in enumerate(trades[:3]):
                print(f"        {i+1}. {trade.action} {trade.total_quantity} {trade.contract_symbol} - {trade.status}")
                if trade.avg_fill_price:
                    print(f"           Avg fill: ${trade.avg_fill_price:.2f}")

    except Exception as e:
        results.add_fail("Trades retrieval", str(e))
        print(f"   ❌ Failed: {e}")


async def test_executions(client: IBKRClient, results: TestResults):
    """Test executions retrieval."""
    print("\n📝 Testing executions retrieval...")

    try:
        executions = await client.get_executions()
        results.add_pass("Executions", f"{len(executions)} executions")
        print(f"   ✅ Executions retrieved: {len(executions)}")

        if executions:
            total_commission = sum(ex.commission for ex in executions)
            total_pnl = sum(ex.realized_pnl for ex in executions if ex.realized_pnl)
            print(f"      Total commission: ${total_commission:.2f}")
            print(f"      Total realized P&L: ${total_pnl:.2f}")

            print("      Sample executions:")
            for i, ex in enumerate(executions[:3]):
                print(f"        {i+1}. {ex.action} {ex.quantity} {ex.symbol} @ ${ex.price:.2f}")

    except Exception as e:
        results.add_fail("Executions retrieval", str(e))
        print(f"   ❌ Failed: {e}")


async def test_option_expirations(client: IBKRClient, results: TestResults, symbol: str = "AAPL"):
    """Test option expirations retrieval."""
    print(f"\n📅 Testing option expirations ({symbol})...")

    try:
        expirations = await client.get_option_expirations(symbol)
        if expirations:
            results.add_pass("Option expirations", f"{len(expirations)} expirations for {symbol}")
            print(f"   ✅ Found {len(expirations)} expiration dates")
            print(f"      Next 5 expirations: {expirations[:5]}")
            return expirations
        else:
            results.add_skip("Option expirations", f"No expirations found for {symbol}")
            print(f"   ⚠️  No expirations found")
            return []

    except Exception as e:
        results.add_fail("Option expirations", str(e))
        print(f"   ❌ Failed: {e}")
        return []


async def test_option_chain(client: IBKRClient, results: TestResults, symbol: str = "AAPL", expiry: str = None):
    """Test option chain retrieval with Greeks."""
    print(f"\n🔗 Testing option chain ({symbol})...")

    if not expiry:
        # Get the first available expiration
        expirations = await client.get_option_expirations(symbol)
        if not expirations:
            results.add_skip("Option chain", "No expirations available")
            print("   ⚠️  Skipped: No expirations available")
            return
        expiry = expirations[0]

    print(f"      Using expiry: {expiry}")

    try:
        chain = await client.get_option_chain(symbol, expiry, strike_range=6)
        results.add_pass(
            "Option chain",
            f"{len(chain.strikes)} strikes, underlying ${chain.underlying_price:.2f}"
        )
        print(f"   ✅ Option chain retrieved")
        print(f"      Underlying price: ${chain.underlying_price:.2f}")
        print(f"      Strikes retrieved: {len(chain.strikes)}")

        # Show sample strikes with Greeks
        if chain.strikes:
            print("      Sample strikes with Greeks:")
            for strike_data in chain.strikes[:3]:
                print(f"        Strike ${strike_data.strike}:")

                # Call info
                if strike_data.call_bid or strike_data.call_ask:
                    call_mid = ((strike_data.call_bid or 0) + (strike_data.call_ask or 0)) / 2
                    print(f"          CALL: ${call_mid:.2f}", end="")
                    if strike_data.call_greeks:
                        g = strike_data.call_greeks
                        print(f" | Delta: {g.delta:.3f}" if g.delta else "", end="")
                        print(f" | IV: {g.implied_volatility:.1%}" if g.implied_volatility else "", end="")
                    print()

                # Put info
                if strike_data.put_bid or strike_data.put_ask:
                    put_mid = ((strike_data.put_bid or 0) + (strike_data.put_ask or 0)) / 2
                    print(f"          PUT:  ${put_mid:.2f}", end="")
                    if strike_data.put_greeks:
                        g = strike_data.put_greeks
                        print(f" | Delta: {g.delta:.3f}" if g.delta else "", end="")
                        print(f" | IV: {g.implied_volatility:.1%}" if g.implied_volatility else "", end="")
                    print()

    except Exception as e:
        results.add_fail("Option chain", str(e))
        print(f"   ❌ Failed: {e}")


async def test_option_price(client: IBKRClient, results: TestResults, symbol: str = "AAPL"):
    """Test single option price retrieval."""
    print(f"\n💵 Testing single option price ({symbol})...")

    try:
        # Get expirations first
        expirations = await client.get_option_expirations(symbol)
        if not expirations:
            results.add_skip("Option price", "No expirations available")
            print("   ⚠️  Skipped: No expirations available")
            return

        # Get underlying price to find ATM strike
        stock_data = await client.get_stock_price(symbol)
        underlying_price = stock_data.price

        # Use first expiration and round strike to nearest 5
        expiry = expirations[0]
        strike = round(underlying_price / 5) * 5

        print(f"      Testing {symbol} {expiry} ${strike} Call")

        option_data = await client.get_option_price(symbol, expiry, strike, 'C')
        if option_data.price > 0:
            results.add_pass("Option price", f"${option_data.price:.2f}")
            print(f"   ✅ Option price: ${option_data.price:.2f}")
            if option_data.bid and option_data.ask:
                print(f"      Bid/Ask: ${option_data.bid:.2f} / ${option_data.ask:.2f}")
        else:
            results.add_skip("Option price", "No price data available")
            print("   ⚠️  No price data (option may be illiquid)")

    except Exception as e:
        results.add_fail("Option price", str(e))
        print(f"   ❌ Failed: {e}")


async def test_reconnection(client: IBKRClient, results: TestResults):
    """Test reconnection logic."""
    print("\n🔄 Testing reconnection logic...")

    try:
        # Test ensure_connected when already connected
        was_connected = await client.ensure_connected()
        if was_connected:
            results.add_pass("Reconnection (already connected)", "Connection maintained")
            print("   ✅ ensure_connected() works when already connected")
        else:
            results.add_fail("Reconnection", "Failed to maintain connection")
            print("   ❌ ensure_connected() failed")

    except Exception as e:
        results.add_fail("Reconnection", str(e))
        print(f"   ❌ Failed: {e}")


async def run_basic_tests(client: IBKRClient, results: TestResults):
    """Run basic connection and portfolio tests."""
    await test_connection(client, results)
    await test_portfolio(client, results)
    await test_account_summary(client, results)
    await test_stock_price(client, results)


async def run_order_tests(client: IBKRClient, results: TestResults):
    """Run order-related tests."""
    await test_orders(client, results)
    await test_trades(client, results)
    await test_executions(client, results)


async def run_option_tests(client: IBKRClient, results: TestResults, symbol: str = "AAPL"):
    """Run option-related tests."""
    await test_option_expirations(client, results, symbol)
    await test_option_chain(client, results, symbol)
    await test_option_price(client, results, symbol)


async def run_all_tests(client: IBKRClient, results: TestResults):
    """Run all tests."""
    await run_basic_tests(client, results)
    await run_order_tests(client, results)
    await run_option_tests(client, results)
    await test_reconnection(client, results)


def check_prerequisites():
    """Check if prerequisites are installed."""
    print("🔍 Checking prerequisites...")

    try:
        import ib_async
        print(f"   ✅ ib_async version: {ib_async.__version__}")
    except ImportError:
        print("   ❌ ib_async not found. Run: pip install ib_async")
        return False

    try:
        import mcp
        print(f"   ✅ mcp package found")
    except ImportError:
        print("   ❌ mcp not found. Run: pip install mcp[cli]")
        return False

    try:
        import pydantic
        print(f"   ✅ pydantic version: {pydantic.__version__}")
    except ImportError:
        print("   ❌ pydantic not found. Run: pip install pydantic")
        return False

    print()
    return True


async def main(test_type: str = "all"):
    """Main test function."""
    print("=" * 60)
    print("    IBKR MCP Server - Comprehensive Test Suite")
    print("=" * 60)
    print()

    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites check failed. Please install missing packages.")
        return 1

    results = TestResults()

    try:
        # Load configuration
        print("📋 Loading configuration...")
        config = get_default_config()
        print(f"   Host: {config.host}")
        print(f"   Port: {config.port}")
        print(f"   Client ID: {config.client_id}")
        print(f"   Paper Trading: {config.is_paper}")

        # Connect and run tests
        print("\n🔌 Connecting to IBKR TWS...")
        async with IBKRClient(config) as client:
            print(f"   ✅ Connected to account: {client.account}")

            if test_type == "basic":
                await run_basic_tests(client, results)
            elif test_type == "orders":
                await run_order_tests(client, results)
            elif test_type == "options":
                await run_option_tests(client, results)
            else:
                await run_all_tests(client, results)

    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure TWS or IB Gateway is running")
        print("   2. Check API settings are enabled in TWS")
        print("   3. Verify port settings (7497 for paper, 7496 for live)")
        print("   4. Check firewall settings")
        print("   5. Ensure you're logged into your account")
<<<<<<< HEAD
        return 1

    # Print summary
    print("\n" + "=" * 60)
    print("    Test Results Summary")
    print("=" * 60)
    print(f"\n   {results.summary()}")
    print()

    if results.failed > 0:
        print("   Failed tests:")
        for status, name, detail in results.results:
            if status == "FAIL":
                print(f"     ❌ {name}: {detail}")
        print()

    if results.skipped > 0:
        print("   Skipped tests:")
        for status, name, detail in results.results:
            if status == "SKIP":
                print(f"     ⚠️  {name}: {detail}")
        print()

    if results.failed == 0:
        print("🎉 All tests passed!")
        print("\n📝 Next steps:")
        print("   1. Restart Claude Desktop to load the updated MCP server")
        print("   2. Try asking Claude to show your orders or analyze options")
        print("   3. Use the new prompts: analyze_options, review_orders")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IBKR MCP Server Test Suite")
    parser.add_argument("--basic", action="store_true", help="Run basic tests only")
    parser.add_argument("--orders", action="store_true", help="Run order-related tests only")
    parser.add_argument("--options", action="store_true", help="Run options-related tests only")
    args = parser.parse_args()

    if args.basic:
        test_type = "basic"
    elif args.orders:
        test_type = "orders"
    elif args.options:
        test_type = "options"
    else:
        test_type = "all"

    exit_code = asyncio.run(main(test_type))
    sys.exit(exit_code) 
=======
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
>>>>>>> parent of 8c60732 (fixed get stock price)
