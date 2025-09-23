"""
Market Regime Detection using CNN Fear & Greed Index
Using custom scraper for Python 3.13 compatibility
"""

import time
import json
from datetime import datetime
from typing import Dict, Optional

import yfinance as yf

# Use our custom scraper instead
from src.regime.cnn_scraper import CNNFearGreedIndex

from config.settings import (
    REGIME_THRESHOLDS,
    POSITION_MULTIPLIERS,
    FILTER_PERCENTILES,
    EXPECTED_WIN_RATES,
    CACHE_DURATION,
)


class OdinRegimeDetector:
    """
    Fetches market regime from professional sources
    """

    def __init__(self):
        self.cnn_client = CNNFearGreedIndex()  # Our custom scraper
        self.cache = {}
        self.cache_duration = CACHE_DURATION

    def get_current_regime(self) -> Dict:
        """
        Main method - returns complete regime analysis
        """
        # Get Fear & Greed (with caching)
        fg_data = self._get_fear_greed_cached()

        # Get VIX for confirmation
        vix = self._get_vix()

        # Interpret into trading regime
        regime = self._interpret_regime(fg_data["value"], vix)

        # Add metadata
        regime.update(
            {
                "fear_greed_value": fg_data["value"],
                "fear_greed_text": fg_data.get("text", ""),
                "vix": vix,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return regime

    def _get_fear_greed_cached(self) -> Dict:
        """
        Fetch CNN Fear & Greed with caching
        """
        cache_key = "fear_greed"

        # Check cache
        if cache_key in self.cache:
            cached_time = self.cache[cache_key]["timestamp"]
            if time.time() - cached_time < self.cache_duration:
                print(f"Using cached Fear & Greed data")
                return self.cache[cache_key]["data"]

        # Fetch fresh
        try:
            print("Fetching fresh CNN Fear & Greed...")
            data = self.cnn_client.get_fear_and_greed_index()

            # Cache it
            self.cache[cache_key] = {"data": data, "timestamp": time.time()}

            return data

        except Exception as e:
            print(f"Error fetching CNN Fear & Greed: {e}")
            print("Falling back to VIX-based regime")
            return self._vix_fallback_regime()

    def _get_vix(self) -> float:
        """
        Get current VIX level
        """
        try:
            vix = yf.Ticker("^VIX")
            return vix.info["regularMarketPrice"]
        except:
            return 20.0  # Default to normal if unavailable

    def _vix_fallback_regime(self) -> Dict:
        """
        Fallback regime detection using only VIX
        """
        vix = self._get_vix()

        if vix < 15:
            return {"value": 65, "text": "Greed"}
        elif vix < 20:
            return {"value": 50, "text": "Neutral"}
        elif vix < 30:
            return {"value": 35, "text": "Fear"}
        else:
            return {"value": 15, "text": "Extreme Fear"}

    def _interpret_regime(self, fear_greed_value: float, vix: float) -> Dict:
        """
        Convert Fear & Greed + VIX into trading regime
        Based on your research findings
        """
        # Determine base regime from Fear & Greed
        regime_name = None
        for regime, (min_val, max_val) in REGIME_THRESHOLDS.items():
            if min_val <= fear_greed_value < max_val:
                regime_name = regime
                break

        if not regime_name:
            regime_name = "neutral"

        # Build regime dict
        regime_dict = {
            "regime": regime_name,
            "position_multiplier": POSITION_MULTIPLIERS[regime_name],
            "filter_percentile": FILTER_PERCENTILES[regime_name],
            "expected_win_rate": EXPECTED_WIN_RATES[regime_name],
        }

        # Determine strategy
        if regime_name in ["extreme_fear", "fear"]:
            regime_dict["strategy"] = "mean_reversion"
        elif regime_name in ["greed", "extreme_greed"]:
            regime_dict["strategy"] = "momentum"
        else:
            regime_dict["strategy"] = "mixed"

        # VIX override for extreme conditions
        if vix > 30:
            regime_dict["strategy"] = "mean_reversion"
            regime_dict["expected_win_rate"] = max(
                0.80, regime_dict["expected_win_rate"]
            )
            regime_dict["volatility_regime"] = "high"
        elif vix < 15:
            regime_dict["volatility_regime"] = "low"
        else:
            regime_dict["volatility_regime"] = "normal"

        return regime_dict
