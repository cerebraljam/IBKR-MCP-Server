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
from ibkr_mcp.models import (
    Position, Portfolio, MarketData, AccountSummary,
    Order, Trade, Execution, OptionGreeks, OptionChain, OptionChainStrike
)

logger = logging.getLogger(__name__)


class IBKRClient:
    """Client for Interactive Brokers TWS API using ib_async."""

    def __init__(self, config: IBKRConfig):
        self.config = config
        self.ib = IB()
        self.connected = False
        self.account = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        
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

    def is_connection_alive(self) -> bool:
        """Check if the connection to TWS is actually alive."""
        if not self.connected:
            return False
        try:
            # Check if the IB connection is still active
            return self.ib.isConnected()
        except Exception:
            return False

    async def ensure_connected(self) -> bool:
        """Ensure connection is alive, reconnect if needed."""
        if self.is_connection_alive():
            self._reconnect_attempts = 0
            return True

        # Connection is dead, try to reconnect
        logger.warning("Connection lost to IBKR TWS, attempting to reconnect...")
        self.connected = False

        while self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            logger.info(f"Reconnection attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}")

            try:
                # Disconnect cleanly first
                try:
                    self.ib.disconnect()
                except Exception:
                    pass

                # Create fresh IB instance
                self.ib = IB()

                # Try to reconnect
                success = await self.connect()
                if success:
                    logger.info("Successfully reconnected to IBKR TWS")
                    self._reconnect_attempts = 0
                    return True

            except Exception as e:
                logger.error(f"Reconnection attempt {self._reconnect_attempts} failed: {e}")

            # Wait before next attempt
            await asyncio.sleep(2)

        logger.error("Failed to reconnect after maximum attempts")
        return False
    
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
            # Create stock contract
            contract = Stock(symbol, exchange)
            
            # Request market data
            self.ib.reqMktData(contract, '', False, False)
            
            # Wait for ticker data
            await asyncio.sleep(2)  # Give time for data to arrive
            
            ticker = self.ib.reqTicker(contract)
            
            # Cancel market data subscription
            self.ib.cancelMktData(contract)
            
            # Extract price data
            price = ticker.marketPrice() or ticker.close or 0.0
            bid = ticker.bid if ticker.bid > 0 else None
            ask = ticker.ask if ticker.ask > 0 else None
            volume = ticker.volume if ticker.volume > 0 else None
            
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
            # Create option contract
            contract = Option(symbol, expiry, strike, right, exchange)
            
            # Request market data
            self.ib.reqMktData(contract, '', False, False)
            
            # Wait for ticker data
            await asyncio.sleep(2)
            
            ticker = self.ib.reqTicker(contract)
            
            # Cancel market data subscription
            self.ib.cancelMktData(contract)
            
            # Extract price data
            price = ticker.marketPrice() or ticker.close or 0.0
            bid = ticker.bid if ticker.bid > 0 else None
            ask = ticker.ask if ticker.ask > 0 else None
            volume = ticker.volume if ticker.volume > 0 else None
            
            option_symbol = f"{symbol}_{expiry}_{strike}_{right}"
            
            market_data = MarketData(
                symbol=option_symbol,
                price=float(price),
                bid=float(bid) if bid else None,
                ask=float(ask) if ask else None,
                volume=int(volume) if volume else None,
                timestamp=datetime.now()
            )
            
            return market_data

        except Exception as e:
            logger.error(f"Error getting option price for {symbol}: {e}")
            raise

    async def get_orders(self, include_inactive: bool = False) -> List[Order]:
        """Get all orders (open and optionally inactive/filled)."""
        self._ensure_connected()

        try:
            orders = []

            if include_inactive:
                # Get all orders including filled/cancelled
                ib_trades = self.ib.trades()
            else:
                # Get only open/pending orders
                ib_trades = self.ib.openTrades()

            for trade in ib_trades:
                order = self._convert_trade_to_order(trade)
                orders.append(order)

            return orders

        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            raise

    def _convert_trade_to_order(self, trade) -> Order:
        """Convert an ib_async Trade object to our Order model."""
        contract = trade.contract
        ib_order = trade.order
        order_status = trade.orderStatus

        # Extract option-specific fields
        expiry = None
        strike = None
        right = None
        if contract.secType == 'OPT':
            expiry = getattr(contract, 'lastTradeDateOrContractMonth', None)
            strike = getattr(contract, 'strike', None)
            right = getattr(contract, 'right', None)

        return Order(
            order_id=ib_order.orderId,
            client_id=ib_order.clientId,
            perm_id=ib_order.permId,
            symbol=contract.symbol,
            contract_type=contract.secType,
            action=ib_order.action,
            order_type=ib_order.orderType,
            total_quantity=float(ib_order.totalQuantity),
            filled_quantity=float(order_status.filled) if order_status.filled else 0.0,
            remaining_quantity=float(order_status.remaining) if order_status.remaining else float(ib_order.totalQuantity),
            limit_price=float(ib_order.lmtPrice) if ib_order.lmtPrice else None,
            aux_price=float(ib_order.auxPrice) if ib_order.auxPrice else None,
            status=order_status.status,
            expiry=expiry,
            strike=strike,
            right=right,
            time_in_force=ib_order.tif,
            parent_id=ib_order.parentId,
            oca_group=ib_order.ocaGroup or "",
        )

    async def get_trades(self) -> List[Trade]:
        """Get all trades with execution information."""
        self._ensure_connected()

        try:
            trades = []
            ib_trades = self.ib.trades()

            for ib_trade in ib_trades:
                trade = self._convert_to_trade(ib_trade)
                trades.append(trade)

            return trades

        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            raise

    def _convert_to_trade(self, ib_trade) -> Trade:
        """Convert an ib_async Trade object to our Trade model."""
        contract = ib_trade.contract
        order = ib_trade.order
        order_status = ib_trade.orderStatus

        # Extract option-specific fields
        expiry = None
        strike = None
        right = None
        if contract.secType == 'OPT':
            expiry = getattr(contract, 'lastTradeDateOrContractMonth', None)
            strike = getattr(contract, 'strike', None)
            right = getattr(contract, 'right', None)

        # Calculate commission from fills
        total_commission = 0.0
        total_realized_pnl = 0.0
        for fill in ib_trade.fills:
            if fill.commissionReport:
                total_commission += float(fill.commissionReport.commission) if fill.commissionReport.commission else 0.0
                total_realized_pnl += float(fill.commissionReport.realizedPNL) if fill.commissionReport.realizedPNL else 0.0

        return Trade(
            order_id=order.orderId,
            contract_symbol=contract.symbol,
            contract_type=contract.secType,
            action=order.action,
            order_type=order.orderType,
            status=order_status.status,
            total_quantity=float(order.totalQuantity),
            filled_quantity=float(order_status.filled) if order_status.filled else 0.0,
            remaining_quantity=float(order_status.remaining) if order_status.remaining else 0.0,
            avg_fill_price=float(order_status.avgFillPrice) if order_status.avgFillPrice else 0.0,
            last_fill_price=float(order_status.lastFillPrice) if order_status.lastFillPrice else 0.0,
            limit_price=float(order.lmtPrice) if order.lmtPrice else None,
            expiry=expiry,
            strike=strike,
            right=right,
            commission=total_commission,
            realized_pnl=total_realized_pnl,
        )

    async def get_executions(self) -> List[Execution]:
        """Get execution/fill details."""
        self._ensure_connected()

        try:
            executions = []
            fills = self.ib.fills()

            for fill in fills:
                execution = self._convert_fill_to_execution(fill)
                executions.append(execution)

            return executions

        except Exception as e:
            logger.error(f"Error getting executions: {e}")
            raise

    def _convert_fill_to_execution(self, fill) -> Execution:
        """Convert an ib_async Fill object to our Execution model."""
        contract = fill.contract
        execution = fill.execution
        commission_report = fill.commissionReport

        # Extract option-specific fields
        expiry = None
        strike = None
        right = None
        if contract.secType == 'OPT':
            expiry = getattr(contract, 'lastTradeDateOrContractMonth', None)
            strike = getattr(contract, 'strike', None)
            right = getattr(contract, 'right', None)

        # Parse execution time
        exec_time = datetime.now()
        if execution.time:
            try:
                exec_time = datetime.strptime(str(execution.time), '%Y%m%d %H:%M:%S')
            except (ValueError, TypeError):
                exec_time = datetime.now()

        return Execution(
            exec_id=execution.execId,
            order_id=execution.orderId,
            symbol=contract.symbol,
            contract_type=contract.secType,
            action=execution.side,  # 'BOT' or 'SLD'
            quantity=float(execution.shares),
            price=float(execution.price),
            time=exec_time,
            exchange=execution.exchange,
            expiry=expiry,
            strike=strike,
            right=right,
            commission=float(commission_report.commission) if commission_report and commission_report.commission else 0.0,
            currency=commission_report.currency if commission_report else "USD",
            realized_pnl=float(commission_report.realizedPNL) if commission_report and commission_report.realizedPNL else 0.0,
        )

    async def cancel_order(self, order_id: int) -> bool:
        """Cancel an order by order ID."""
        self._ensure_connected()

        try:
            # Find the trade with this order ID
            ib_trades = self.ib.openTrades()
            target_trade = None

            for trade in ib_trades:
                if trade.order.orderId == order_id:
                    target_trade = trade
                    break

            if not target_trade:
                logger.warning(f"Order {order_id} not found in open orders")
                return False

            # Cancel the order
            self.ib.cancelOrder(target_trade.order)
            logger.info(f"Cancel request sent for order {order_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            raise

    async def get_option_chain(
        self,
        symbol: str,
        expiry: str,
        strike_range: int = 10,
        exchange: str = "SMART"
    ) -> OptionChain:
        """Get option chain with Greeks for a symbol and expiry."""
        self._ensure_connected()

        try:
            # First get the underlying stock price
            stock = Stock(symbol, exchange, currency='USD')
            self.ib.qualifyContracts(stock)

            # Get underlying price
            stock_ticker = await self._request_market_data(stock)
            underlying_price = stock_ticker.marketPrice() or stock_ticker.last or stock_ticker.close or 0.0

            # Get option chain parameters
            chains = self.ib.reqSecDefOptParams(symbol, '', stock.secType, stock.conId)

            if not chains:
                raise Exception(f"No option chains found for {symbol}")

            # Find the chain for our exchange
            chain = None
            for c in chains:
                if c.exchange == exchange or exchange == "SMART":
                    chain = c
                    break

            if not chain:
                chain = chains[0]  # Use first available

            # Find strikes around the current price
            all_strikes = sorted(chain.strikes)
            atm_index = min(range(len(all_strikes)), key=lambda i: abs(all_strikes[i] - underlying_price))

            start_idx = max(0, atm_index - strike_range // 2)
            end_idx = min(len(all_strikes), atm_index + strike_range // 2 + 1)
            selected_strikes = all_strikes[start_idx:end_idx]

            # Build option chain with Greeks
            strikes_data = []

            for strike in selected_strikes:
                strike_data = OptionChainStrike(strike=strike, expiry=expiry)

                # Get call data
                try:
                    call_contract = Option(symbol, expiry, strike, 'C', exchange, currency='USD')
                    qualified = self.ib.qualifyContracts(call_contract)
                    if qualified:
                        call_ticker = self.ib.reqMktData(call_contract, '', True, False)

                        import time
                        time.sleep(0.5)  # Brief wait for data

                        strike_data.call_bid = float(call_ticker.bid) if call_ticker.bid and call_ticker.bid > 0 else None
                        strike_data.call_ask = float(call_ticker.ask) if call_ticker.ask and call_ticker.ask > 0 else None
                        strike_data.call_last = float(call_ticker.last) if call_ticker.last and call_ticker.last > 0 else None
                        strike_data.call_volume = int(call_ticker.volume) if call_ticker.volume else None

                        # Get Greeks from modelGreeks
                        if call_ticker.modelGreeks:
                            greeks = call_ticker.modelGreeks
                            strike_data.call_greeks = OptionGreeks(
                                delta=greeks.delta,
                                gamma=greeks.gamma,
                                theta=greeks.theta,
                                vega=greeks.vega,
                                implied_volatility=greeks.impliedVol,
                                underlying_price=greeks.undPrice,
                                option_price=greeks.optPrice,
                                pv_dividend=greeks.pvDividend,
                            )

                        self.ib.cancelMktData(call_contract)
                except Exception as e:
                    logger.warning(f"Error getting call data for strike {strike}: {e}")

                # Get put data
                try:
                    put_contract = Option(symbol, expiry, strike, 'P', exchange, currency='USD')
                    qualified = self.ib.qualifyContracts(put_contract)
                    if qualified:
                        put_ticker = self.ib.reqMktData(put_contract, '', True, False)

                        import time
                        time.sleep(0.5)  # Brief wait for data

                        strike_data.put_bid = float(put_ticker.bid) if put_ticker.bid and put_ticker.bid > 0 else None
                        strike_data.put_ask = float(put_ticker.ask) if put_ticker.ask and put_ticker.ask > 0 else None
                        strike_data.put_last = float(put_ticker.last) if put_ticker.last and put_ticker.last > 0 else None
                        strike_data.put_volume = int(put_ticker.volume) if put_ticker.volume else None

                        # Get Greeks from modelGreeks
                        if put_ticker.modelGreeks:
                            greeks = put_ticker.modelGreeks
                            strike_data.put_greeks = OptionGreeks(
                                delta=greeks.delta,
                                gamma=greeks.gamma,
                                theta=greeks.theta,
                                vega=greeks.vega,
                                implied_volatility=greeks.impliedVol,
                                underlying_price=greeks.undPrice,
                                option_price=greeks.optPrice,
                                pv_dividend=greeks.pvDividend,
                            )

                        self.ib.cancelMktData(put_contract)
                except Exception as e:
                    logger.warning(f"Error getting put data for strike {strike}: {e}")

                strikes_data.append(strike_data)

            return OptionChain(
                symbol=symbol,
                underlying_price=float(underlying_price),
                expiry=expiry,
                strikes=strikes_data,
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {e}")
            raise

    async def get_option_expirations(self, symbol: str, exchange: str = "SMART") -> List[str]:
        """Get available option expiration dates for a symbol."""
        self._ensure_connected()

        try:
            stock = Stock(symbol, exchange, currency='USD')
            self.ib.qualifyContracts(stock)

            chains = self.ib.reqSecDefOptParams(symbol, '', stock.secType, stock.conId)

            if not chains:
                return []

            # Collect all unique expirations
            expirations = set()
            for chain in chains:
                expirations.update(chain.expirations)

            return sorted(list(expirations))

        except Exception as e:
            logger.error(f"Error getting option expirations for {symbol}: {e}")
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect() 