"""
Interactive Brokers client wrapper using ib_async.
"""

import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from ib_async import IB, Stock, Option, Contract, PortfolioItem as IBPortfolio, AccountValue as IBAccountValue
from ib_async.objects import Position as IBPosition

from ibkr_mcp.config import IBKRConfig
from ibkr_mcp.models import Position, Portfolio, MarketData, AccountSummary

logger = logging.getLogger(__name__)


class IBKRClient:
    """Client for Interactive Brokers TWS API using ib_async."""
    
    def __init__(self, config: IBKRConfig):
        self.config = config
        self.ib = IB()
        self.connected = False
        self.account = None
        
    async def connect(self) -> bool:
        """Connect to Interactive Brokers TWS."""
        try:
            await self.ib.connectAsync(
                host=self.config.host,
                port=self.config.port,
                clientId=self.config.client_id,
                timeout=self.config.timeout
            )
            self.connected = True
            
            # Get account information
            await self._update_account_info()
            
            logger.info(f"Connected to IBKR TWS at {self.config.host}:{self.config.port}")
            logger.info(f"Using account: {self.account}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IBKR TWS: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Interactive Brokers TWS."""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR TWS")
    
    async def _update_account_info(self):
        """Update account information."""
        if self.config.account:
            self.account = self.config.account
        else:
            # Auto-detect account
            accounts = self.ib.managedAccounts()
            if accounts:
                self.account = accounts[0]
                logger.info(f"Auto-detected account: {self.account}")
            else:
                raise Exception("No accounts found")
    
    def _ensure_connected(self):
        """Ensure we're connected to TWS."""
        if not self.connected:
            raise Exception("Not connected to IBKR TWS. Call connect() first.")
    
    async def _request_market_data(self, contract) -> object:
        """Request market data for a contract and wait for response."""
        # Qualify the contract first
        self.ib.qualifyContracts(contract)
        
        # For MCP context, try getting existing ticker data first
        existing_tickers = [t for t in self.ib.tickers() if t.contract.symbol == contract.symbol]
        if existing_tickers:
            ticker = existing_tickers[0]
            # Check if the existing ticker has valid data
            if ticker.marketPrice() or ticker.last or ticker.close:
                return ticker
        
        # If no existing data, request market data snapshot
        ticker = self.ib.reqMktData(contract, '', True, False)  # snapshot=True
        
        # Wait for data to populate with proper checking
        import time
        max_wait = 5  # Maximum 5 seconds
        wait_interval = 0.2  # Check every 200ms
        elapsed = 0
        
        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval
            
            # Check if we have valid price data
            price = ticker.marketPrice() or ticker.last or ticker.close
            if price and price > 0:
                break
        
        # Cancel market data subscription
        self.ib.cancelMktData(contract)
        
        return ticker
    
    async def get_portfolio(self) -> Portfolio:
        """Get current portfolio."""
        self._ensure_connected()
        
        try:
            # Get portfolio items
            portfolio_items = self.ib.portfolio(self.account)
            
            # Get account values (filter out non-numeric values)
            account_values = {}
            for item in self.ib.accountValues(self.account):
                try:
                    account_values[item.tag] = float(item.value)
                except (ValueError, TypeError):
                    # Skip non-numeric values (like account IDs, currency codes, etc.)
                    continue
            
            # Convert portfolio items to our Position model
            positions = []
            for item in portfolio_items:
                position = self._convert_portfolio_item(item)
                positions.append(position)
            
            # Extract summary values
            total_value = account_values.get('NetLiquidation', 0.0)
            total_cash = account_values.get('TotalCashValue', 0.0)
            buying_power = account_values.get('BuyingPower', 0.0)
            day_pnl = account_values.get('DayPNL', 0.0)
            unrealized_pnl = account_values.get('UnrealizedPnL', 0.0)
            realized_pnl = account_values.get('RealizedPnL', 0.0)
            
            portfolio = Portfolio(
                account=self.account,
                positions=positions,
                total_value=total_value,
                total_cash=total_cash,
                buying_power=buying_power,
                day_pnl=day_pnl,
                unrealized_pnl=unrealized_pnl,
                realized_pnl=realized_pnl,
                timestamp=datetime.now()
            )
            
            return portfolio
            
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            raise
    
    def _convert_portfolio_item(self, item: IBPortfolio) -> Position:
        """Convert IB portfolio item to our Position model."""
        contract = item.contract
        
        # Determine contract type and extract details
        contract_type = contract.secType
        symbol = contract.symbol
        exchange = getattr(contract, 'exchange', None)
        currency = getattr(contract, 'currency', 'USD')
        
        # Option-specific fields
        expiry = None
        strike = None
        right = None
        
        if contract_type == 'OPT':
            expiry = getattr(contract, 'lastTradeDateOrContractMonth', None)
            strike = getattr(contract, 'strike', None)
            right = getattr(contract, 'right', None)
        
        return Position(
            symbol=symbol,
            contract_type=contract_type,
            quantity=float(item.position),
            market_price=float(item.marketPrice) if item.marketPrice else 0.0,
            market_value=float(item.marketValue) if item.marketValue else 0.0,
            average_cost=float(item.averageCost) if item.averageCost else 0.0,
            unrealized_pnl=float(item.unrealizedPNL) if item.unrealizedPNL else 0.0,
            realized_pnl=float(item.realizedPNL) if item.realizedPNL else 0.0,
            account=item.account,
            currency=currency,
            exchange=exchange,
            expiry=expiry,
            strike=strike,
            right=right
        )
    
    async def get_account_summary(self) -> AccountSummary:
        """Get account summary."""
        self._ensure_connected()
        
        try:
            # Get account values (filter out non-numeric values)
            account_values = {}
            for item in self.ib.accountValues(self.account):
                try:
                    account_values[item.tag] = float(item.value)
                except (ValueError, TypeError):
                    # Skip non-numeric values (like account IDs, currency codes, etc.)
                    continue
            
            summary = AccountSummary(
                account=self.account,
                net_liquidation=account_values.get('NetLiquidation', 0.0),
                total_cash_value=account_values.get('TotalCashValue', 0.0),
                settled_cash=account_values.get('SettledCash', 0.0),
                accrued_cash=account_values.get('AccruedCash', 0.0),
                buying_power=account_values.get('BuyingPower', 0.0),
                equity_with_loan_value=account_values.get('EquityWithLoanValue', 0.0),
                previous_day_equity_with_loan_value=account_values.get('PreviousDayEquityWithLoanValue', 0.0),
                gross_position_value=account_values.get('GrossPositionValue', 0.0),
                reg_t_margin=account_values.get('RegTMargin', 0.0),
                sma=account_values.get('SMA', 0.0),
                init_margin_req=account_values.get('InitMarginReq', 0.0),
                maint_margin_req=account_values.get('MaintMarginReq', 0.0),
                available_funds=account_values.get('AvailableFunds', 0.0),
                excess_liquidity=account_values.get('ExcessLiquidity', 0.0),
                timestamp=datetime.now()
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            raise
    
    async def get_stock_price(self, symbol: str, exchange: str = "SMART") -> MarketData:
        """Get current stock price."""
        self._ensure_connected()
        
        try:
            # Create stock contract with currency specified
            contract = Stock(symbol, exchange, currency='USD')
            
            # Request market data using shared method
            ticker = await self._request_market_data(contract)
            
            # Extract price data from ticker
            price = ticker.marketPrice() or ticker.close or ticker.last or 0.0
            bid = ticker.bid if ticker.bid and ticker.bid > 0 else None
            ask = ticker.ask if ticker.ask and ticker.ask > 0 else None
            volume = ticker.volume if ticker.volume and ticker.volume > 0 else None
            
            market_data = MarketData(
                symbol=symbol,
                price=float(price),
                bid=float(bid) if bid else None,
                ask=float(ask) if ask else None,
                volume=int(volume) if volume else None,
                timestamp=datetime.now()
            )
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting stock price for {symbol}: {e}")
            raise
    
    async def get_option_price(self, symbol: str, expiry: str, strike: float, right: str, exchange: str = "SMART") -> MarketData:
        """Get current option price."""
        self._ensure_connected()
        
        try:
            # Create option contract with proper format
            contract = Option(symbol, expiry, float(strike), right.upper(), exchange, currency='USD')
            
            # Log the contract details for debugging
            logger.info(f"Created option contract: {contract}")
            
            # Qualify the contract to ensure it's valid (with timeout)
            qualified_contracts = self.ib.qualifyContracts(contract)
            if not qualified_contracts:
                # Try alternative approach: use reqContractDetails
                logger.warning(f"Direct qualification failed, trying contract details lookup")
                contract_details = self.ib.reqContractDetails(contract)
                if not contract_details:
                    raise Exception(f"Option contract not found: {symbol} {expiry} {strike} {right}. Contract may not exist or be tradeable.")
                qualified_contract = contract_details[0].contract
            else:
                qualified_contract = qualified_contracts[0]
            
            logger.info(f"Using contract: {qualified_contract}")
            
            # Request market data for the qualified contract with shorter timeout
            ticker = self.ib.reqMktData(qualified_contract, '', True, False)  # snapshot=True
            
            # Reduced wait time to avoid MCP timeout
            import time
            max_wait = 5  # Reduced from 10 seconds
            wait_interval = 0.5  # Check every 500ms
            elapsed = 0
            
            while elapsed < max_wait:
                time.sleep(wait_interval)
                elapsed += wait_interval
                
                # Check if we have valid option price data
                price = ticker.marketPrice() or ticker.last or ticker.close
                if price and price > 0:
                    logger.info(f"Option data received: price={price}, bid={ticker.bid}, ask={ticker.ask}")
                    break
                    
                # Also check if bid/ask are available (sometimes more reliable for options)
                if ticker.bid and ticker.ask and ticker.bid > 0:
                    logger.info(f"Option bid/ask received: bid={ticker.bid}, ask={ticker.ask}")
                    break
                    
                # Check every 2 seconds if we should give up early
                if elapsed >= 2 and not (ticker.bid or ticker.ask or ticker.last):
                    logger.warning(f"No option data after {elapsed}s, option may not be actively traded")
            
            # Cancel market data subscription
            self.ib.cancelMktData(qualified_contract)
            
            # Extract price data from ticker
            price = ticker.marketPrice() or ticker.last or ticker.close
            
            # For options, if no market price, use mid-point of bid/ask
            if not price or price == 0:
                if ticker.bid and ticker.ask and ticker.bid > 0 and ticker.ask > 0:
                    price = (ticker.bid + ticker.ask) / 2
                    logger.info(f"Using bid/ask midpoint: {price}")
                else:
                    logger.warning(f"No price data available for option {symbol} {expiry} {strike} {right}")
            
            bid = ticker.bid if ticker.bid and ticker.bid > 0 else None
            ask = ticker.ask if ticker.ask and ticker.ask > 0 else None
            volume = ticker.volume if ticker.volume and ticker.volume > 0 else None
            
            option_symbol = f"{symbol}_{expiry}_{strike}_{right.upper()}"
            
            market_data = MarketData(
                symbol=option_symbol,
                price=float(price) if price else 0.0,
                bid=float(bid) if bid else None,
                ask=float(ask) if ask else None,
                volume=int(volume) if volume else None,
                timestamp=datetime.now()
            )
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error getting option price for {symbol}: {e}")
            raise
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect() 