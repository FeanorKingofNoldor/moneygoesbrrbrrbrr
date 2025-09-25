# config/settings.py
"""
ODIN Configuration - Complete Settings
All configuration in one place - no hardcoded values elsewhere
"""

import os
from pathlib import Path
from datetime import datetime

# =============================================================================
# PATHS AND DIRECTORIES
# =============================================================================

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Database
DATABASE_PATH = PROJECT_ROOT / "data" / "odin.db"  # Was hardcoded as "odin_dev.db"

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = PROJECT_ROOT / "cache"
RESULTS_DIR = PROJECT_ROOT / "results"
LOGS_DIR = PROJECT_ROOT / "logs"

# TradingAgents library path
TRADINGAGENTS_LIB_PATH = PROJECT_ROOT / "tradingagents_lib"

# Environment file
ENV_FILE_PATH = TRADINGAGENTS_LIB_PATH / ".env"

# =============================================================================
# API KEYS AND AUTHENTICATION
# =============================================================================

# These will be loaded from environment or .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")

# =============================================================================
# TRADINGAGENTS CONFIGURATION
# =============================================================================

TRADINGAGENTS_CONFIG = {
    'llm_provider': 'openai',
    'backend_url': 'https://api.openai.com/v1',
    'deep_think_llm': 'gpt-4o-mini',  # Was hardcoded in wrapper.py
    'quick_think_llm': 'gpt-4o-mini',  # $0.15 per 1M input tokens
    'max_debate_rounds': 1,  # Was hardcoded as 1
    'max_risk_discuss_rounds': 1,
    'max_recur_limit': 100,
    'online_tools': True,
    'results_dir': str(RESULTS_DIR),
    'data_dir': str(DATA_DIR),
    'data_cache_dir': str(CACHE_DIR),
}

# =============================================================================
# INTERACTIVE BROKERS (IBKR) CONFIGURATION
# =============================================================================

IBKR_HOST = '127.0.0.1'  # Was hardcoded in ibkr_connector.py
IBKR_PAPER_PORT = 4002   # Paper trading port (was hardcoded)
IBKR_LIVE_PORT = 4001    # Live trading port
IBKR_CLIENT_ID = 1       # Was hardcoded in ibkr_connector.py
IBKR_ENABLED = True      # Enable/disable IBKR integration
IBKR_CACHE_TIMEOUT = 60  # Seconds - was hardcoded in ibkr_connector.py

# Default to paper trading for safety
IBKR_DEFAULT_PORT = IBKR_PAPER_PORT

# =============================================================================
# PORTFOLIO DEFAULTS (Fallback values)
# =============================================================================

# Was hardcoded as 100000 in wrapper.py _get_fallback_context()
DEFAULT_CASH = 100000
DEFAULT_PORTFOLIO_VALUE = 100000
DEFAULT_POSITIONS = 0
DEFAULT_UNREALIZED_PNL = 0
DEFAULT_RISK_UTILIZATION = 0.0

# =============================================================================
# ANALYSIS SETTINGS
# =============================================================================

# Default analysis date if none provided
DEFAULT_ANALYSIS_DATE = "2024-12-19"  # Was hardcoded in wrapper.py

# Batch processing
BATCH_SIZE = 50  # For processing multiple stocks
BATCH_TIMEOUT = 300  # Seconds per batch

# =============================================================================
# MARKET REGIME SETTINGS (Your existing settings)
# =============================================================================

REGIME_THRESHOLDS = {
    'extreme_fear': (0, 25),
    'fear': (25, 45),
    'neutral': (45, 55),
    'greed': (55, 75),
    'extreme_greed': (75, 100)
}

POSITION_MULTIPLIERS = {
    'extreme_fear': 1.5,
    'fear': 1.2,
    'neutral': 1.0,
    'greed': 0.8,
    'extreme_greed': 0.5
}

FILTER_PERCENTILES = {
    'extreme_fear': 90,
    'fear': 93,
    'neutral': 95,
    'greed': 97,
    'extreme_greed': 99
}

EXPECTED_WIN_RATES = {
    'extreme_fear': 0.80,
    'fear': 0.70,
    'neutral': 0.60,
    'greed': 0.62,
    'extreme_greed': 0.55
}

# =============================================================================
# TRADING PARAMETERS
# =============================================================================

# Position sizing
MAX_POSITIONS = 5            # Was referenced but not centralized
MAX_POSITION_SIZE_PCT = 20   # Max 20% per position
BASE_RISK_PCT = 1            # 1% base risk per trade

# Filter constraints (your existing)
MIN_DOLLAR_VOLUME = 5_000_000
MIN_MARKET_CAP = 500_000_000
MIN_PRICE = 5.0
MAX_SPREAD_PCT = 2.0

# Data settings (your existing)
CACHE_DURATION = 900  # 15 minutes in seconds
MAX_CANDIDATES = 30
EXPLORATION_RATIO = 0.15

# Stop loss settings (your existing)
STOP_LOSS_MULTIPLIERS = {
    'low_vol': 1.5,
    'normal': 2.5,
    'high_vol': 3.0
}

# =============================================================================
# CNN FEAR & GREED SETTINGS
# =============================================================================

CNN_FG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_FG_CACHE_DURATION = 900  # 15 minutes

# =============================================================================
# S&P 500 DATA SOURCE
# =============================================================================

SP500_CSV_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / f"odin_{datetime.now().strftime('%Y%m%d')}.log"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_tradingagents_config():
    """Get TradingAgents configuration"""
    return TRADINGAGENTS_CONFIG.copy()

def get_ibkr_config():
    """Get IBKR configuration"""
    return {
        'host': IBKR_HOST,
        'port': IBKR_DEFAULT_PORT,
        'client_id': IBKR_CLIENT_ID,
        'enabled': IBKR_ENABLED,
        'cache_timeout': IBKR_CACHE_TIMEOUT
    }

def load_api_keys_from_env():
    """Load API keys from .env file if not in environment"""
    global OPENAI_API_KEY, FINNHUB_API_KEY
    
    if not OPENAI_API_KEY or not FINNHUB_API_KEY:
        if ENV_FILE_PATH.exists():
            with open(ENV_FILE_PATH, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("OPENAI_API_KEY="):
                        OPENAI_API_KEY = line.split("=", 1)[1]
                        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
                    elif line.startswith("FINNHUB_API_KEY="):
                        FINNHUB_API_KEY = line.split("=", 1)[1]
                        os.environ["FINNHUB_API_KEY"] = FINNHUB_API_KEY
    
    return OPENAI_API_KEY, FINNHUB_API_KEY

# Load API keys on import
load_api_keys_from_env()