"""
Data models for IBKR MCP Server.
"""

from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Position:
    """Represents a portfolio position."""
    
    symbol: str
    contract_type: str  # 'STK', 'OPT', 'FUT', etc.
    quantity: float
    market_price: float
    market_value: float
    average_cost: float
    unrealized_pnl: float
    realized_pnl: float
    account: str
    
    # Additional contract details
    currency: str = "USD"
    exchange: Optional[str] = None
    expiry: Optional[str] = None  # For options/futures
    strike: Optional[float] = None  # For options
    right: Optional[str] = None  # 'C' or 'P' for options
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "contract_type": self.contract_type,
            "quantity": self.quantity,
            "market_price": self.market_price,
            "market_value": self.market_value,
            "average_cost": self.average_cost,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "account": self.account,
            "currency": self.currency,
            "exchange": self.exchange,
            "expiry": self.expiry,
            "strike": self.strike,
            "right": self.right,
        }


@dataclass
class Portfolio:
    """Represents a complete portfolio."""
    
    account: str
    positions: List[Position]
    total_value: float
    total_cash: float
    buying_power: float
    day_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "account": self.account,
            "positions": [pos.to_dict() for pos in self.positions],
            "total_value": self.total_value,
            "total_cash": self.total_cash,
            "buying_power": self.buying_power,
            "day_pnl": self.day_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "timestamp": self.timestamp.isoformat(),
            "position_count": len(self.positions),
        }


@dataclass
class MarketData:
    """Represents market data for a symbol."""
    
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None
    
    # Additional fields
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "price": self.price,
            "bid": self.bid,
            "ask": self.ask,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "high": self.high,
            "low": self.low,
            "open": self.open,
            "close": self.close,
            "change": self.change,
            "change_percent": self.change_percent,
        }


@dataclass
class AccountSummary:
    """Represents account summary information."""
    
    account: str
    net_liquidation: float
    total_cash_value: float
    settled_cash: float
    accrued_cash: float
    buying_power: float
    equity_with_loan_value: float
    previous_day_equity_with_loan_value: float
    gross_position_value: float
    
    # Risk metrics
    reg_t_margin: float
    sma: float  # Special Memorandum Account
    init_margin_req: float
    maint_margin_req: float
    available_funds: float
    excess_liquidity: float
    
    currency: str = "USD"
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "account": self.account,
            "net_liquidation": self.net_liquidation,
            "total_cash_value": self.total_cash_value,
            "settled_cash": self.settled_cash,
            "accrued_cash": self.accrued_cash,
            "buying_power": self.buying_power,
            "equity_with_loan_value": self.equity_with_loan_value,
            "previous_day_equity_with_loan_value": self.previous_day_equity_with_loan_value,
            "gross_position_value": self.gross_position_value,
            "reg_t_margin": self.reg_t_margin,
            "sma": self.sma,
            "init_margin_req": self.init_margin_req,
            "maint_margin_req": self.maint_margin_req,
            "available_funds": self.available_funds,
            "excess_liquidity": self.excess_liquidity,
            "currency": self.currency,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class Order:
    """Represents an order (pending or filled)."""

    order_id: int
    client_id: int
    perm_id: int
    symbol: str
    contract_type: str  # 'STK', 'OPT', etc.
    action: str  # 'BUY' or 'SELL'
    order_type: str  # 'LMT', 'MKT', 'STP', etc.
    total_quantity: float
    filled_quantity: float
    remaining_quantity: float
    limit_price: Optional[float] = None
    aux_price: Optional[float] = None  # Stop price for stop orders
    status: str = ""  # 'Submitted', 'Filled', 'Cancelled', etc.

    # Option-specific fields
    expiry: Optional[str] = None
    strike: Optional[float] = None
    right: Optional[str] = None  # 'C' or 'P'

    # Timing
    time_in_force: str = "DAY"  # 'DAY', 'GTC', etc.
    parent_id: int = 0
    oca_group: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "order_id": self.order_id,
            "client_id": self.client_id,
            "perm_id": self.perm_id,
            "symbol": self.symbol,
            "contract_type": self.contract_type,
            "action": self.action,
            "order_type": self.order_type,
            "total_quantity": self.total_quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "limit_price": self.limit_price,
            "aux_price": self.aux_price,
            "status": self.status,
            "expiry": self.expiry,
            "strike": self.strike,
            "right": self.right,
            "time_in_force": self.time_in_force,
            "parent_id": self.parent_id,
            "oca_group": self.oca_group,
        }


@dataclass
class Trade:
    """Represents a trade (order with execution status)."""

    order_id: int
    contract_symbol: str
    contract_type: str
    action: str  # 'BUY' or 'SELL'
    order_type: str
    status: str  # 'Submitted', 'Filled', 'Cancelled', etc.
    total_quantity: float
    filled_quantity: float
    remaining_quantity: float
    avg_fill_price: float
    last_fill_price: float
    limit_price: Optional[float] = None

    # Option-specific fields
    expiry: Optional[str] = None
    strike: Optional[float] = None
    right: Optional[str] = None

    # Commission
    commission: float = 0.0
    realized_pnl: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "order_id": self.order_id,
            "contract_symbol": self.contract_symbol,
            "contract_type": self.contract_type,
            "action": self.action,
            "order_type": self.order_type,
            "status": self.status,
            "total_quantity": self.total_quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "avg_fill_price": self.avg_fill_price,
            "last_fill_price": self.last_fill_price,
            "limit_price": self.limit_price,
            "expiry": self.expiry,
            "strike": self.strike,
            "right": self.right,
            "commission": self.commission,
            "realized_pnl": self.realized_pnl,
        }


@dataclass
class Execution:
    """Represents an execution/fill."""

    exec_id: str
    order_id: int
    symbol: str
    contract_type: str
    action: str  # 'BOT' or 'SLD'
    quantity: float
    price: float
    time: datetime
    exchange: str

    # Option-specific fields
    expiry: Optional[str] = None
    strike: Optional[float] = None
    right: Optional[str] = None

    # Commission details
    commission: float = 0.0
    currency: str = "USD"
    realized_pnl: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "exec_id": self.exec_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "contract_type": self.contract_type,
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "time": self.time.isoformat() if self.time else None,
            "exchange": self.exchange,
            "expiry": self.expiry,
            "strike": self.strike,
            "right": self.right,
            "commission": self.commission,
            "currency": self.currency,
            "realized_pnl": self.realized_pnl,
        }


@dataclass
class OptionGreeks:
    """Represents option Greeks."""

    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    implied_volatility: Optional[float] = None
    underlying_price: Optional[float] = None
    option_price: Optional[float] = None
    pv_dividend: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
            "rho": self.rho,
            "implied_volatility": self.implied_volatility,
            "underlying_price": self.underlying_price,
            "option_price": self.option_price,
            "pv_dividend": self.pv_dividend,
        }


@dataclass
class OptionChainStrike:
    """Represents a single strike in an option chain."""

    strike: float
    expiry: str

    # Call data
    call_bid: Optional[float] = None
    call_ask: Optional[float] = None
    call_last: Optional[float] = None
    call_volume: Optional[int] = None
    call_open_interest: Optional[int] = None
    call_greeks: Optional[OptionGreeks] = None

    # Put data
    put_bid: Optional[float] = None
    put_ask: Optional[float] = None
    put_last: Optional[float] = None
    put_volume: Optional[int] = None
    put_open_interest: Optional[int] = None
    put_greeks: Optional[OptionGreeks] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "strike": self.strike,
            "expiry": self.expiry,
            "call": {
                "bid": self.call_bid,
                "ask": self.call_ask,
                "last": self.call_last,
                "volume": self.call_volume,
                "open_interest": self.call_open_interest,
                "greeks": self.call_greeks.to_dict() if self.call_greeks else None,
            },
            "put": {
                "bid": self.put_bid,
                "ask": self.put_ask,
                "last": self.put_last,
                "volume": self.put_volume,
                "open_interest": self.put_open_interest,
                "greeks": self.put_greeks.to_dict() if self.put_greeks else None,
            }
        }


@dataclass
class OptionChain:
    """Represents an option chain for a symbol."""

    symbol: str
    underlying_price: float
    expiry: str
    strikes: List[OptionChainStrike]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "underlying_price": self.underlying_price,
            "expiry": self.expiry,
            "strikes": [s.to_dict() for s in self.strikes],
            "strike_count": len(self.strikes),
            "timestamp": self.timestamp.isoformat(),
        } 