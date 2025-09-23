"""
ODIN Configuration
Research-validated thresholds from your documents
"""

# Market Regime Thresholds (from CNN Fear & Greed)
REGIME_THRESHOLDS = {
    'extreme_fear': (0, 25),
    'fear': (25, 45),
    'neutral': (45, 55),
    'greed': (55, 75),
    'extreme_greed': (75, 100)
}

# Position Size Multipliers by Regime
POSITION_MULTIPLIERS = {
    'extreme_fear': 1.5,
    'fear': 1.2,
    'neutral': 1.0,
    'greed': 0.8,
    'extreme_greed': 0.5
}

# Filter Percentiles by Regime (what % to keep)
FILTER_PERCENTILES = {
    'extreme_fear': 90,  # Top 10%
    'fear': 93,          # Top 7%
    'neutral': 95,       # Top 5%
    'greed': 97,         # Top 3%
    'extreme_greed': 99  # Top 1%
}

# Expected Win Rates (from research)
EXPECTED_WIN_RATES = {
    'extreme_fear': 0.80,  # 76-85%
    'fear': 0.70,          # 65-75%
    'neutral': 0.60,       # 55-65%
    'greed': 0.62,         # 58-65%
    'extreme_greed': 0.55  # 50-60%
}

# Stop Loss Multipliers (ATR-based)
STOP_LOSS_MULTIPLIERS = {
    'low_vol': 1.5,    # VIX < 15
    'normal': 2.5,     # VIX 15-30
    'high_vol': 3.0    # VIX > 30
}

# Data Settings
CACHE_DURATION = 900  # 15 minutes in seconds
MAX_CANDIDATES = 30   # Max stocks to analyze
EXPLORATION_RATIO = 0.15  # 15% random selection

# Filter Constraints
MIN_DOLLAR_VOLUME = 5_000_000
MIN_MARKET_CAP = 500_000_000
MIN_PRICE = 5.0
MAX_SPREAD_PCT = 2.0