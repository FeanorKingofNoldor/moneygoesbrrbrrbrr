# src/tradingagents/wrapper.py

import sys
import os
from pathlib import Path

# Add to imports
from config.settings import (
    TRADINGAGENTS_LIB_PATH,
    TRADINGAGENTS_CONFIG,
    IBKR_DEFAULT_PORT,
    IBKR_ENABLED,
    DEFAULT_CASH,
    DEFAULT_PORTFOLIO_VALUE,
    DEFAULT_ANALYSIS_DATE,
    load_api_keys_from_env
)

sys.path.append(str(TRADINGAGENTS_LIB_PATH))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from src.regime.detector import OdinRegimeDetector


class PortfolioContextProvider:
    """
    Provides portfolio context from IBKR account and ODIN database for TradingAgents
    """

    def __init__(
        self, odin_database, use_ibkr=True, ibkr_host="127.0.0.1", ibkr_port=4001
    ):
        """
        Initialize portfolio context provider

        Args:
            odin_database: ODIN database instance
            use_ibkr: Whether to use IBKR for real portfolio data
            ibkr_host: IBKR Gateway host
            ibkr_port: IBKR Gateway port (4001 for live, 4002 for paper)
        """
        self.db = odin_database
        self.use_ibkr = use_ibkr

        # Initialize IBKR connector if requested
        self.ibkr_connector = None
        if use_ibkr:
            try:
                self.ibkr_connector = IBKRPortfolioConnector(ibkr_host, ibkr_port)
                print(f"✓ IBKR Portfolio Connector initialized (port {ibkr_port})")
            except ImportError as e:
                print(f"⚠ IBKR connector not available: {e}")
                print("  Install with: pip install ib_async")
                self.use_ibkr = False
            except Exception as e:
                print(f"⚠ IBKR connector failed: {e}")
                self.use_ibkr = False

    def get_portfolio_context(self):
        """
        Get current portfolio context for TradingAgents
        Combines IBKR real data with ODIN historical data
        """
        try:
            # Get ODIN historical data first
            odin_context = self._get_odin_context()

            # Get IBKR real-time portfolio data if available
            if self.use_ibkr and self.ibkr_connector:
                ibkr_data = self._get_ibkr_context()
                if ibkr_data:
                    # Merge IBKR data with ODIN context
                    return self._merge_contexts(odin_context, ibkr_data)

            # Fallback to ODIN-only context
            return odin_context

        except Exception as e:
            print(f"Error getting portfolio context: {e}")
            return self._get_fallback_context()

    def _get_ibkr_context(self):
        """Get real portfolio data from IBKR"""
        try:
            print("Fetching live portfolio data from IBKR...")
            portfolio_data = self.ibkr_connector.get_portfolio_data_sync()

            if not portfolio_data:
                print("No IBKR data received")
                return None

            # Transform IBKR data for TradingAgents
            positions = []
            for pos in portfolio_data["positions"]:
                if pos["position"] != 0:  # Only active positions
                    positions.append(
                        {
                            "symbol": pos["symbol"],
                            "shares": pos["position"],
                            "market_value": pos["market_value"],
                            "average_cost": pos["average_cost"],
                            "unrealized_pnl": pos["unrealized_pnl"],
                            "unrealized_pnl_pct": pos.get("unrealized_pnl_pct", 0),
                            "source": "IBKR_LIVE",
                        }
                    )

            # Get account summary
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
            print(f"Error fetching IBKR portfolio data: {e}")
            return None

    def _get_odin_context(self):
        """Get historical context from ODIN database"""
        try:
            # Get recent regime history for context
            recent_regime_query = """
            SELECT regime, timestamp, fear_greed_value, vix
            FROM regime_history 
            ORDER BY timestamp DESC 
            LIMIT 10
            """

            try:
                regime_df = pd.read_sql(recent_regime_query, self.db.conn)
                recent_regimes = (
                    regime_df.to_dict("records") if not regime_df.empty else []
                )
            except:
                recent_regimes = []

            # Get latest filter results for context
            filter_query = """
            SELECT symbol, score, regime, timestamp
            FROM filter_results
            WHERE selected = 1
            ORDER BY timestamp DESC
            LIMIT 10
            """

            try:
                filter_df = pd.read_sql(filter_query, self.db.conn)
                recent_candidates = (
                    filter_df.to_dict("records") if not filter_df.empty else []
                )
            except:
                recent_candidates = []

            return {
                "recent_regimes": recent_regimes,
                "recent_candidates": recent_candidates,
                "data_source": "ODIN_DB",
                "total_positions": 0,
                "current_positions": [],
                "cash_available": 100000,
                "portfolio_value": 100000,
                "unrealized_pnl": 0,
                "risk_utilization": 0,
            }

        except Exception as e:
            print(f"Error getting ODIN context: {e}")
            return {
                "recent_regimes": [],
                "recent_candidates": [],
                "data_source": "ODIN_DB",
            }

    def _merge_contexts(self, odin_context, ibkr_context):
        """Merge ODIN and IBKR contexts"""
        merged = ibkr_context.copy()
        merged.update(
            {
                "recent_regimes": odin_context["recent_regimes"],
                "recent_candidates": odin_context["recent_candidates"],
                "data_source": "IBKR + ODIN",
            }
        )

        # Add regime analysis of current positions
        if merged["current_positions"] and odin_context["recent_regimes"]:
            current_regime = (
                odin_context["recent_regimes"][0]["regime"]
                if odin_context["recent_regimes"]
                else "neutral"
            )
            merged["current_regime_analysis"] = self._analyze_positions_vs_regime(
                merged["current_positions"], current_regime
            )

        return merged

    def _analyze_positions_vs_regime(self, positions, regime):
        """Analyze how current positions align with regime strategy"""
        winners = [p for p in positions if p["unrealized_pnl"] > 0]
        losers = [p for p in positions if p["unrealized_pnl"] < 0]

        return {
            "total_positions": len(positions),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": len(winners) / len(positions) * 100 if positions else 0,
            "avg_winner_pct": (
                sum(p["unrealized_pnl_pct"] for p in winners) / len(winners)
                if winners
                else 0
            ),
            "avg_loser_pct": (
                sum(p["unrealized_pnl_pct"] for p in losers) / len(losers)
                if losers
                else 0
            ),
            "regime_alignment": self._check_regime_alignment(positions, regime),
        }

    def _check_regime_alignment(self, positions, regime):
        """Check if positions align with current regime strategy"""
        # This would need more sophisticated analysis
        # For now, just return basic info
        return {
            "current_regime": regime,
            "strategy_suggestion": (
                "mean_reversion" if regime in ["extreme_fear", "fear"] else "momentum"
            ),
            "position_count_vs_regime": (
                "conservative" if len(positions) < 5 else "aggressive"
            ),
        }


    def _get_fallback_context(self):
        """Fallback context when everything else fails"""
        return {
            "current_positions": [],
            "total_positions": 0,
            "recent_regimes": [],
            "recent_candidates": [],
            "cash_available": DEFAULT_CASH,
            "portfolio_value": DEFAULT_PORTFOLIO_VALUE,
            "unrealized_pnl": 0,
            "risk_utilization": 0.0,
            "data_source": "FALLBACK",
            "timestamp": datetime.now().isoformat(),
        }


class OdinTradingAgentsWrapper:
    def __init__(
        self, odin_database, use_ibkr=None, ibkr_port=None
    ):
        """
        Initialize ODIN TradingAgents wrapper with IBKR integration

        Args:
            odin_database: ODIN database instance
            use_ibkr: Whether to use IBKR for live portfolio data (None = use config default)
            ibkr_port: 4001 for live trading, 4002 for paper trading (None = use config default)
        """
        # Import config settings
        from config.settings import (
            TRADINGAGENTS_CONFIG,
            TRADINGAGENTS_LIB_PATH,
            IBKR_ENABLED,
            IBKR_DEFAULT_PORT,
            ENV_FILE_PATH,
            load_api_keys_from_env
        )
        
        # Use config defaults if not specified
        self.use_ibkr = use_ibkr if use_ibkr is not None else IBKR_ENABLED
        self.ibkr_port = ibkr_port if ibkr_port is not None else IBKR_DEFAULT_PORT
        
        # Load API keys - enhanced error handling
        try:
            openai_key, finnhub_key = load_api_keys_from_env()
            
            # Fallback to manual parsing if load function didn't work
            if not openai_key or not finnhub_key:
                env_path = ENV_FILE_PATH or os.path.join(
                    os.path.dirname(__file__), "../../tradingagents_lib/.env"
                )
                
                if os.path.exists(env_path):
                    with open(env_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("OPENAI_API_KEY="):
                                openai_key = openai_key or line.split("=", 1)[1]
                            elif line.startswith("FINNHUB_API_KEY="):
                                finnhub_key = finnhub_key or line.split("=", 1)[1]
            
            if not openai_key:
                raise ValueError("OPENAI_API_KEY not found in .env file or environment!")
            if not finnhub_key:
                raise ValueError("FINNHUB_API_KEY not found in .env file or environment!")
            
            # Set environment variables if not already set
            if not os.environ.get("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = openai_key
            if not os.environ.get("FINNHUB_API_KEY"):
                os.environ["FINNHUB_API_KEY"] = finnhub_key
            
            print(f"Loaded OpenAI key ending in: {openai_key[-10:]}")
            
        except Exception as e:
            print(f"Warning: Error loading API keys: {e}")
            # Continue if keys are already in environment
            if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("FINNHUB_API_KEY"):
                raise
        
        # Get config from settings - use centralized configuration
        self.config = TRADINGAGENTS_CONFIG.copy()
        
        # FIX: Add the missing project_dir that TradingAgents needs
        self.config['project_dir'] = str(TRADINGAGENTS_LIB_PATH)
        
        # Allow runtime overrides if needed (backward compatibility)
        self.config.update({
            "llm_provider": self.config.get("llm_provider", "openai"),
            "backend_url": self.config.get("backend_url", "https://api.openai.com/v1"),
            "deep_think_llm": self.config.get("deep_think_llm", "gpt-4o-mini"),
            "quick_think_llm": self.config.get("quick_think_llm", "gpt-4o-mini"),
            "online_tools": self.config.get("online_tools", True),
            "max_debate_rounds": self.config.get("max_debate_rounds", 1),
        })
        
        # Initialize ODIN components
        self.regime_detector = OdinRegimeDetector()
        self.portfolio_provider = PortfolioContextProvider(
            odin_database, use_ibkr=self.use_ibkr, ibkr_port=self.ibkr_port
        )
        
        # Initialize TradingAgents with config
        self.graph = TradingAgentsGraph(debug=True, config=self.config)
        
        # Print setup info
        mode = "LIVE" if self.ibkr_port == 4001 else "PAPER"
        ibkr_status = "ENABLED" if self.use_ibkr else "DISABLED"
        print(f"ODIN Setup: IBKR {ibkr_status}, Mode: {mode} (port {self.ibkr_port})")

    def analyze_stock(self, symbol, date=None, market_context=None):
        """
        Analyze a stock using TradingAgents with market and portfolio context
        
        Args:
            symbol: Stock ticker symbol
            date: Analysis date (None = use default from config)
            market_context: Optional market regime context
        """
        from config.settings import DEFAULT_ANALYSIS_DATE
        
        if date is None:
            date = DEFAULT_ANALYSIS_DATE
        
        print(f"\nAnalyzing {symbol} for {date}...")

        # Get regime and portfolio context BEFORE analysis
        if market_context is None:
            regime_context = self.regime_detector.get_current_regime()
        else:
            regime_context = market_context

        portfolio_context = self.portfolio_provider.get_portfolio_context()

        print(
            f"Market Regime: {regime_context['regime']} (F&G: {regime_context['fear_greed_value']})"
        )
        print(
            f"Portfolio: {portfolio_context['total_positions']} positions, "
            f"${portfolio_context.get('cash_available', 0):,.0f} cash"
        )

        if portfolio_context.get("data_source") == "IBKR + ODIN":
            total_pnl = portfolio_context.get("total_unrealized_pnl", 0)
            print(
                f"Live P&L: ${total_pnl:+,.0f}, "
                f"Largest: {portfolio_context.get('largest_position', 'N/A')}"
            )

        # Create enhanced prompt context for TradingAgents
        enhanced_context = f"""
    MARKET REGIME CONTEXT:
    - Current Regime: {regime_context['regime']} ({regime_context.get('fear_greed_text', '')})
    - CNN Fear & Greed Index: {regime_context['fear_greed_value']}/100
    - VIX Level: {regime_context['vix']:.2f}
    - Recommended Strategy: {regime_context['strategy']}
    - Expected Win Rate: {regime_context['expected_win_rate']:.1%}
    - Position Size Multiplier: {regime_context['position_multiplier']}x

    PORTFOLIO CONTEXT:
    - Current Positions: {portfolio_context['total_positions']}
    - Risk Utilization: {portfolio_context.get('risk_utilization', 0):.1%}
    - Available Cash: ${portfolio_context.get('cash_available', 0):,}
    - Portfolio Value: ${portfolio_context.get('portfolio_value', 0):,}
    - Data Source: {portfolio_context.get('data_source', 'Unknown')}"""

        # Add live portfolio performance if available
        if "current_regime_analysis" in portfolio_context:
            analysis = portfolio_context["current_regime_analysis"]
            enhanced_context += f"""

    CURRENT PERFORMANCE:
    - Win Rate: {analysis['win_rate']:.1f}% ({analysis['winners']}/{analysis['total_positions']})
    - Avg Winner: {analysis['avg_winner_pct']:+.1f}%
    - Avg Loser: {analysis['avg_loser_pct']:+.1f}%
    - Regime Alignment: {analysis['regime_alignment']['strategy_suggestion']}"""

        enhanced_context += f"""

    TRADING GUIDANCE:
    Given the {regime_context['regime']} regime, focus on {regime_context['strategy']} strategies.
    Consider this context when analyzing {symbol} for position trading (3-10 day hold).
    """

        # Pass the context to TradingAgents WITH market context
        result, decision = self.graph.propagate(symbol, date)

        # Enhance the result with ODIN context
        enhanced_result = {
            "symbol": symbol,
            "decision": decision,
            "raw_result": result,
            "regime_context": regime_context,
            "portfolio_context": portfolio_context,
            "odin_enhancement": enhanced_context,
        }

        return enhanced_result

    def get_portfolio_summary(self):
        """Get a summary of current portfolio for monitoring"""
        context = self.portfolio_provider.get_portfolio_context()
        regime = self.regime_detector.get_current_regime()

        print(f"\n{'='*60}")
        print(
            f"ODIN PORTFOLIO SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print(f"{'='*60}")
        print(f"Data Source: {context.get('data_source', 'Unknown')}")
        print(f"Market Regime: {regime['regime']} (F&G: {regime['fear_greed_value']})")
        print(f"Strategy: {regime['strategy']}")
        print(f"\nPORTFOLIO:")
        print(f"  Total Positions: {context.get('total_positions', 0)}")
        print(f"  Cash Available: ${context.get('cash_available', 0):,.2f}")
        print(f"  Portfolio Value: ${context.get('portfolio_value', 0):,.2f}")
        print(f"  Risk Utilization: {context.get('risk_utilization', 0):.1%}")

        if context.get("total_unrealized_pnl"):
            print(f"  Unrealized P&L: ${context['total_unrealized_pnl']:+,.2f}")

        # Show top positions if available
        if context.get("current_positions"):
            positions = context["current_positions"][:5]  # Top 5
            print(f"\nTOP POSITIONS:")
            for i, pos in enumerate(positions, 1):
                pnl_pct = pos.get("unrealized_pnl_pct", 0)
                market_value = pos.get("market_value", 0)
                print(f"  {i}. {pos['symbol']}: ${market_value:,.0f} ({pnl_pct:+.1f}%)")

        return context
    