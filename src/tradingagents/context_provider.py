"""
Portfolio Context Provider
Handles portfolio data from both ODIN database and IBKR
"""

import logging
import pandas as pd
from typing import Dict, Optional
from datetime import datetime

from config.settings import (
    IBKR_HOST,
    IBKR_CLIENT_ID,
    DEFAULT_CASH,
    DEFAULT_PORTFOLIO_VALUE,
    DEFAULT_POSITIONS,
    DEFAULT_UNREALIZED_PNL,
    DEFAULT_RISK_UTILIZATION
)

logger = logging.getLogger(__name__)


class PortfolioContextProvider:
    """Provides portfolio context from ODIN database or IBKR"""

    def __init__(self, odin_database, use_ibkr=False, ibkr_port=4002):
        """
        Initialize portfolio context provider
        
        Args:
            odin_database: ODIN database instance
            use_ibkr: Whether to use IBKR for live data
            ibkr_port: IBKR port (4001=live, 4002=paper)
        """
        self.db = odin_database
        self.use_ibkr = use_ibkr
        self.ibkr_connector = None
        
        if use_ibkr:
            try:
                from src.brokers.ibkr_connector import IBKRPortfolioConnector
                self.ibkr_connector = IBKRPortfolioConnector(IBKR_HOST, ibkr_port, IBKR_CLIENT_ID)
                if self.ibkr_connector.connect_sync():
                    logger.info(f"Connected to IBKR on port {ibkr_port}")
                else:
                    logger.warning("Failed to connect to IBKR")
                    self.ibkr_connector = None
            except Exception as e:
                logger.error(f"IBKR setup failed: {e}")
                self.ibkr_connector = None

    def get_portfolio_context(self):
        """Get complete portfolio context"""
        try:
            odin_context = self._get_odin_context()
            
            if self.use_ibkr and self.ibkr_connector:
                ibkr_data = self._get_ibkr_context()
                if ibkr_data:
                    return self._merge_contexts(odin_context, ibkr_data)
            
            return odin_context
        except Exception as e:
            logger.error(f"Error getting portfolio context: {e}")
            return self._get_fallback_context()

    def _get_odin_context(self):
        """Get historical context from ODIN database"""
        try:
            recent_regime_query = """
            SELECT regime, timestamp, fear_greed_value, vix
            FROM regime_history 
            ORDER BY timestamp DESC 
            LIMIT 10
            """
            
            try:
                regime_df = pd.read_sql(recent_regime_query, self.db.conn)
                recent_regimes = regime_df.to_dict("records") if not regime_df.empty else []
            except:
                recent_regimes = []

            filter_query = """
            SELECT symbol, score, regime, timestamp
            FROM filter_results
            WHERE selected = 1
            ORDER BY timestamp DESC
            LIMIT 10
            """
            
            try:
                filter_df = pd.read_sql(filter_query, self.db.conn)
                recent_candidates = filter_df.to_dict("records") if not filter_df.empty else []
            except:
                recent_candidates = []

            return {
                "recent_regimes": recent_regimes,
                "recent_candidates": recent_candidates,
                "data_source": "ODIN_DB",
                "total_positions": 0,
                "current_positions": [],
                "cash_available": DEFAULT_CASH,
                "portfolio_value": DEFAULT_PORTFOLIO_VALUE,
                "unrealized_pnl": DEFAULT_UNREALIZED_PNL,
                "risk_utilization": DEFAULT_RISK_UTILIZATION,
            }
        except Exception as e:
            logger.error(f"Error getting ODIN context: {e}")
            return self._get_fallback_context()

    def _get_ibkr_context(self):
        """Get real portfolio data from IBKR"""
        try:
            logger.info("Fetching live portfolio data from IBKR...")
            portfolio_data = self.ibkr_connector.get_portfolio_data_sync()
            
            if not portfolio_data:
                return None

            positions = []
            for pos in portfolio_data["positions"]:
                if pos["position"] != 0:
                    positions.append({
                        "symbol": pos["symbol"],
                        "shares": pos["position"],
                        "market_value": pos["market_value"],
                        "average_cost": pos["average_cost"],
                        "unrealized_pnl": pos["unrealized_pnl"],
                        "unrealized_pnl_pct": pos.get("unrealized_pnl_pct", 0),
                        "source": "IBKR_LIVE",
                    })

            summary = portfolio_data["summary"]
            
            return {
                "current_positions": positions,
                "total_positions": summary["total_positions"],
                "cash_available": summary["total_cash"],
                "portfolio_value": summary["portfolio_value"],
                "net_liquidation": summary["net_liquidation"],
                "total_unrealized_pnl": summary["total_unrealized_pnl"],
                "largest_position": summary.get("largest_position"),
                "open_orders_count": summary["open_orders_count"],
                "risk_utilization": summary["risk_utilization"],
                "data_source": "IBKR",
                "timestamp": summary["last_updated"],
            }
        except Exception as e:
            logger.error(f"Error fetching IBKR data: {e}")
            return None

    def _merge_contexts(self, odin_context, ibkr_context):
        """Merge ODIN and IBKR contexts"""
        merged = ibkr_context.copy()
        merged.update({
            "recent_regimes": odin_context["recent_regimes"],
            "recent_candidates": odin_context["recent_candidates"],
            "data_source": "IBKR + ODIN",
        })
        
        if merged["current_positions"] and odin_context["recent_regimes"]:
            current_regime = odin_context["recent_regimes"][0]["regime"] if odin_context["recent_regimes"] else "neutral"
            merged["current_regime_analysis"] = self._analyze_positions_vs_regime(
                merged["current_positions"], current_regime
            )
        
        return merged

    def _analyze_positions_vs_regime(self, positions, regime):
        """Analyze how positions align with regime"""
        winners = [p for p in positions if p["unrealized_pnl"] > 0]
        losers = [p for p in positions if p["unrealized_pnl"] < 0]
        
        return {
            "total_positions": len(positions),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": len(winners) / len(positions) * 100 if positions else 0,
            "regime_alignment": self._check_regime_alignment(positions, regime),
        }

    def _check_regime_alignment(self, positions, regime):
        """Check if positions align with regime strategy"""
        return {
            "current_regime": regime,
            "strategy_suggestion": "mean_reversion" if regime in ["extreme_fear", "fear"] else "momentum",
            "position_count_vs_regime": "conservative" if len(positions) < 5 else "aggressive",
        }

    def _get_fallback_context(self):
        """Fallback context when everything fails"""
        return {
            "current_positions": [],
            "total_positions": DEFAULT_POSITIONS,
            "cash_available": DEFAULT_CASH,
            "portfolio_value": DEFAULT_PORTFOLIO_VALUE,
            "unrealized_pnl": DEFAULT_UNREALIZED_PNL,
            "risk_utilization": DEFAULT_RISK_UTILIZATION,
            "data_source": "FALLBACK",
            "timestamp": datetime.now().isoformat(),
        }