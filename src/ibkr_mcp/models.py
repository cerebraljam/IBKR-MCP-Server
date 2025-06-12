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