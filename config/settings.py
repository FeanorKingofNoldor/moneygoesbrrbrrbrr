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

# Database path - main SQLite database for all ODIN data
DATABASE_PATH = PROJECT_ROOT / "data" / "odin.db"

# Data directories
DATA_DIR = PROJECT_ROOT / "data"         # General data storage
CACHE_DIR = PROJECT_ROOT / "cache"       # Temporary cache files
RESULTS_DIR = PROJECT_ROOT / "results"   # Analysis results and reports
LOGS_DIR = PROJECT_ROOT / "logs"         # Log files

# TradingAgents library path
TRADINGAGENTS_LIB_PATH = PROJECT_ROOT / "tradingagents_lib"

# Environment file for API keys
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
# PATTERN SYSTEM CONFIGURATION
# =============================================================================
# The pattern system classifies trades into categories and tracks their performance
# over time to identify which setups work best in different market conditions

# Pattern Classification Thresholds
# These determine how trades are categorized based on technical indicators
PATTERN_RSI_THRESHOLDS = {
    'oversold': 30,      # RSI below 30 = oversold (potential bounce)
    'overbought': 70     # RSI above 70 = overbought (potential reversal)
}

PATTERN_VOLUME_THRESHOLDS = {
    'low': 0.7,          # Volume < 70% of average (quiet trading)
    'high': 1.5,         # Volume > 150% of average (increased interest)
    'explosive': 2.5     # Volume > 250% of average (major event/breakout)
}

PATTERN_FEAR_GREED_THRESHOLDS = {
    'extreme_fear': 25,  # Market panic - often good for contrarian buys
    'fear': 45,          # Market worried - selective opportunities
    'neutral': 55,       # Market balanced - normal trading
    'greed': 75         # Market euphoric - be cautious
}

# Pattern Confidence Levels
# Based on sample size - more trades = more statistical confidence
PATTERN_CONFIDENCE_THRESHOLDS = {
    'high': 50,          # 50+ trades = high statistical confidence
    'medium': 20,        # 20-49 trades = moderate confidence
    'low': 0             # <20 trades = low confidence, be careful
}

# Pattern Performance Tracking
PATTERN_RECENT_TRADES_WINDOW = 20      # Track last 20 trades for momentum
PATTERN_MOMENTUM_THRESHOLD = 0.15      # 15% change = significant momentum shift
PATTERN_BREAKING_THRESHOLD = 0.40      # Win rate <40% = pattern likely broken
PATTERN_HOT_IMPROVEMENT = 0.10         # 10% recent improvement = "hot" pattern
PATTERN_STALE_DAYS = 30               # Deactivate patterns unused for 30 days

# Pattern Analysis Settings
PATTERN_MIN_TRADES_FOR_ANALYSIS = 20   # Need 20+ trades for reliable stats
PATTERN_MIN_TRADES_FOR_MEMORY = 10     # Need 10+ trades before teaching agents
PATTERN_LOOKBACK_DAYS = 30             # Analyze pattern performance over 30 days
PATTERN_LEARNING_TRIGGER = 20          # Run deep learning every 20 trades

# Dynamic Position Management (Pattern-based)
# Adjust stops and targets based on pattern performance
PATTERN_STOP_MULTIPLIERS = {
    'broken': 2.0,       # Tighter stop (2x ATR) for failing patterns
    'normal': 2.5,       # Standard stop (2.5x ATR)
    'hot': 3.0          # Wider stop (3x ATR) for winning patterns
}

PATTERN_TARGET_MULTIPLIERS = {
    'broken': 0.5,       # Take profits quicker (0.5x) on weak patterns
    'normal': 1.0,       # Standard profit target
    'hot': 1.5          # Let winners run (1.5x) on strong patterns
}

PATTERN_MAX_HOLD_DAYS = {
    'broken': 7,         # Exit broken patterns within 7 days
    'normal': 10,        # Standard 10-day holding period
    'hot': 14           # Give hot patterns 14 days to work
}

# Position sizing based on pattern confidence
# Example: High confidence pattern with 70% win rate → 1.5x position size
PATTERN_POSITION_SIZE_MULTIPLIERS = {
    'high_confidence': 1.5,     # Increase size by 50% for proven patterns
    'normal': 1.0,              # Standard position size
    'underperforming': 0.5      # Cut size by 50% for failing patterns
}

# Pattern Decay and Quality Settings
PATTERN_DECAY_RATE = 0.95              # Old trades weighted 5% less per week
PATTERN_MIN_WIN_RATE = 0.35            # Flag patterns winning <35% of time
PATTERN_TARGET_WIN_RATE = 0.60         # Aim for patterns with 60%+ win rate

# Weekly Pattern Analysis Schedule
PATTERN_WEEKLY_ANALYSIS_DAY = 6        # Run analysis on Sunday (0=Mon, 6=Sun)
PATTERN_ANALYSIS_HOUR = 18             # Run at 6 PM

# Pattern Memory Injection Settings
PATTERN_MEMORY_BATCH_SIZE = 50         # Process max 50 patterns at once
PATTERN_MEMORY_PRIORITY_PATTERNS = 10  # Focus on top 10 best patterns

# Pattern Categories (for classification)
# These define all possible pattern components
PATTERN_STRATEGY_TYPES = ['mean_reversion', 'momentum', 'breakout', 'bounce']
PATTERN_MARKET_REGIMES = ['extreme_fear', 'fear', 'neutral', 'greed', 'extreme_greed']
PATTERN_VOLUME_PROFILES = ['low', 'normal', 'high', 'explosive']
PATTERN_TECHNICAL_SETUPS = ['oversold', 'neutral', 'overbought']

# Pattern Tracker Cache Settings
# Cache pattern stats to avoid database hits
PATTERN_CACHE_TIMEOUT = 300            # Cache for 5 minutes
PATTERN_CACHE_CLEAN_INTERVAL = 3600    # Clean old cache entries hourly

# Pattern Alert Thresholds
# When to alert about pattern changes
PATTERN_BREAKDOWN_MIN_TRADES = 20      # Need 20+ trades before alerting
PATTERN_BREAKDOWN_WIN_RATE = 0.30      # Alert if win rate drops below 30%
PATTERN_HOT_MIN_TRADES = 10            # Need 10+ trades to identify "hot"
PATTERN_HOT_WIN_RATE = 0.80            # Win rate >80% = hot pattern alert

# Pattern Recommendation Thresholds
# Used to generate trading recommendations
PATTERN_HOT_RECENT_WIN = 0.70          # Recent 70%+ wins = "hot" pattern
PATTERN_HOT_MOMENTUM = 0.10            # 10%+ momentum = improving pattern
PATTERN_COLD_RECENT_WIN = 0.35         # Recent <35% wins = "cold" pattern
PATTERN_GOOD_EXPECTANCY = 0.02         # 2%+ expected value = profitable
PATTERN_BAD_EXPECTANCY = -0.01         # -1% expected value = losing pattern

# Momentum Description Thresholds
# How to describe pattern performance trends
PATTERN_MOMENTUM_STRONG_UP = 0.15      # +15% = "strongly improving"
PATTERN_MOMENTUM_UP = 0.05             # +5% = "improving"
PATTERN_MOMENTUM_STRONG_DOWN = -0.15   # -15% = "strongly declining"
PATTERN_MOMENTUM_DOWN = -0.05          # -5% = "declining"

# =============================================================================
# TRADINGAGENTS CONFIGURATION
# =============================================================================
# Settings for the TradingAgents AI framework

TRADINGAGENTS_CONFIG = {
    'llm_provider': 'openai',                    # LLM provider (openai/anthropic/google)
    'backend_url': 'https://api.openai.com/v1',  # API endpoint
    'deep_think_llm': 'gpt-4o-mini',             # Model for complex analysis
    'quick_think_llm': 'gpt-4o-mini',            # Model for quick decisions ($0.15/1M tokens)
    'max_debate_rounds': 1,                      # Rounds of agent debate (more = deeper analysis)
    'max_risk_discuss_rounds': 1,                # Risk assessment rounds
    'max_recur_limit': 100,                      # Max recursion depth
    'online_tools': True,                        # Use live data (False = cached only)
    'results_dir': str(RESULTS_DIR),
    'data_dir': str(DATA_DIR),
    'data_cache_dir': str(CACHE_DIR),
}

# =============================================================================
# INTERACTIVE BROKERS (IBKR) CONFIGURATION
# =============================================================================
# Settings for broker connection

IBKR_HOST = '127.0.0.1'        # IB Gateway host (localhost)
IBKR_PAPER_PORT = 4002         # Paper trading port (safe testing)
IBKR_LIVE_PORT = 4001          # Live trading port (real money)
IBKR_CLIENT_ID = 1             # Client ID (1-32, must be unique)
IBKR_ENABLED = True            # Master switch for IBKR
IBKR_CACHE_TIMEOUT = 60        # Cache portfolio data for 60 seconds

# Default to paper trading for safety
IBKR_DEFAULT_PORT = IBKR_PAPER_PORT

# =============================================================================
# PORTFOLIO DEFAULTS (Fallback values)
# =============================================================================
# Used when IBKR is unavailable

DEFAULT_CASH = 100000           # Starting cash balance
DEFAULT_PORTFOLIO_VALUE = 100000  # Total portfolio value
DEFAULT_POSITIONS = 0           # Number of open positions
DEFAULT_UNREALIZED_PNL = 0     # Unrealized P&L
DEFAULT_RISK_UTILIZATION = 0.0  # Risk used (0-1)

# =============================================================================
# ANALYSIS SETTINGS
# =============================================================================

DEFAULT_ANALYSIS_DATE = "2024-12-19"  # Default date for backtesting

# Batch processing
BATCH_SIZE = 50                # Process 50 stocks at a time
BATCH_TIMEOUT = 300            # 5 minutes timeout per batch

# =============================================================================
# MARKET REGIME SETTINGS
# =============================================================================
# Different strategies for different market conditions

REGIME_THRESHOLDS = {
    'extreme_fear': (0, 25),    # CNN F&G 0-25: Market panic
    'fear': (25, 45),           # CNN F&G 25-45: Market worried  
    'neutral': (45, 55),        # CNN F&G 45-55: Market balanced
    'greed': (55, 75),          # CNN F&G 55-75: Market optimistic
    'extreme_greed': (75, 100)  # CNN F&G 75-100: Market euphoric
}

# Position size multipliers by regime
# Example: In extreme fear, take 1.5x normal position (contrarian)
POSITION_MULTIPLIERS = {
    'extreme_fear': 1.5,        # Increase size in panic (buy fear)
    'fear': 1.2,                # Slightly increase in fear
    'neutral': 1.0,             # Normal position size
    'greed': 0.8,               # Reduce in greed (sell euphoria)
    'extreme_greed': 0.5        # Half size in extreme greed
}

# Filter strictness by regime
# Higher percentile = fewer, higher quality candidates
FILTER_PERCENTILES = {
    'extreme_fear': 90,         # Less strict in fear (more opportunities)
    'fear': 93,                 
    'neutral': 95,              # Normal strictness
    'greed': 97,                # More strict in greed
    'extreme_greed': 99         # Very strict in euphoria
}

# Expected win rates by regime (for position sizing)
EXPECTED_WIN_RATES = {
    'extreme_fear': 0.80,       # 80% win rate buying panic
    'fear': 0.70,               # 70% win rate in fear
    'neutral': 0.60,            # 60% baseline win rate
    'greed': 0.62,              # Slightly higher in greed
    'extreme_greed': 0.55       # Lower win rate at tops
}

# =============================================================================
# TRADING PARAMETERS
# =============================================================================

# Position sizing
MAX_POSITIONS = 5              # Maximum simultaneous positions
MAX_POSITION_SIZE_PCT = 20     # Max 20% of portfolio per position
BASE_RISK_PCT = 1              # Risk 1% of portfolio per trade

# Filter constraints (quality filters)
MIN_DOLLAR_VOLUME = 5_000_000  # Minimum $5M daily dollar volume
MIN_MARKET_CAP = 500_000_000   # Minimum $500M market cap
MIN_PRICE = 5.0                # Minimum $5 stock price
MAX_SPREAD_PCT = 2.0           # Maximum 2% bid-ask spread

# Data settings
CACHE_DURATION = 900           # Cache data for 15 minutes
MAX_CANDIDATES = 30            # Select top 30 candidates
EXPLORATION_RATIO = 0.15       # 15% exploration vs exploitation

# Stop loss multipliers (based on volatility)
STOP_LOSS_MULTIPLIERS = {
    'low_vol': 1.5,             # 1.5x ATR for low volatility
    'normal': 2.5,              # 2.5x ATR for normal volatility
    'high_vol': 3.0             # 3.0x ATR for high volatility
}

# =============================================================================
# CNN FEAR & GREED SETTINGS
# =============================================================================

CNN_FG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
CNN_FG_CACHE_DURATION = 900    # Cache for 15 minutes

# =============================================================================
# S&P 500 DATA SOURCE
# =============================================================================

SP500_CSV_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL = "INFO"              # Logging verbosity (DEBUG/INFO/WARNING/ERROR)
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = LOGS_DIR / f"odin_{datetime.now().strftime('%Y%m%d')}.log"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_tradingagents_config():
    """Get TradingAgents configuration dictionary"""
    return TRADINGAGENTS_CONFIG.copy()

def get_ibkr_config():
    """Get IBKR configuration dictionary"""
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