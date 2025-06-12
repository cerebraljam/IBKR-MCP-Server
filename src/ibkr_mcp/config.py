"""
Configuration management for IBKR MCP Server.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class IBKRConfig:
    """Configuration for IBKR connection."""
    
    # Connection settings
    host: str = "127.0.0.1"
    port: int = 7497  # Default paper trading port
    client_id: int = 1
    
    # Account settings
    account: Optional[str] = None  # Will be auto-detected if None
    is_paper: bool = True
    
    # Connection timeout
    timeout: float = 10.0
    
    @classmethod
    def from_env(cls) -> "IBKRConfig":
        """Create config from environment variables."""
        return cls(
            host=os.getenv("IBKR_HOST", "127.0.0.1"),
            port=int(os.getenv("IBKR_PORT", "7497")),  # 7497 for paper, 7496 for live
            client_id=int(os.getenv("IBKR_CLIENT_ID", "1")),
            account=os.getenv("IBKR_ACCOUNT"),
            is_paper=os.getenv("IBKR_IS_PAPER", "true").lower() == "true",
            timeout=float(os.getenv("IBKR_TIMEOUT", "10.0")),
        )
    
    @classmethod
    def for_paper_trading(cls, client_id: int = 1) -> "IBKRConfig":
        """Create config for paper trading."""
        return cls(
            host="127.0.0.1",
            port=7497,
            client_id=client_id,
            is_paper=True,
        )
    
    @classmethod
    def for_live_trading(cls, client_id: int = 1, account: Optional[str] = None) -> "IBKRConfig":
        """Create config for live trading."""
        return cls(
            host="127.0.0.1",
            port=7496,
            client_id=client_id,
            account=account,
            is_paper=False,
        )


def get_default_config() -> IBKRConfig:
    """Get the default configuration."""
    # Try to load from environment first
    try:
        return IBKRConfig.from_env()
    except Exception:
        # Fall back to paper trading
        return IBKRConfig.for_paper_trading() 