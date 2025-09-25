"""
ODIN TradingAgents Coordinator
Complete orchestration of TradingAgents with ODIN context
"""

import sys
import os
from datetime import datetime
import logging

from tradingagents_lib.tradingagents.graph.trading_graph import TradingAgentsGraph
from src.regime.detector import OdinRegimeDetector
from src.tradingagents.context_provider import PortfolioContextProvider
from config.settings import (
    TRADINGAGENTS_CONFIG,
    TRADINGAGENTS_LIB_PATH,
    IBKR_ENABLED,
    IBKR_DEFAULT_PORT,
    ENV_FILE_PATH,
    DEFAULT_ANALYSIS_DATE,
    load_api_keys_from_env
)

logger = logging.getLogger(__name__)


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