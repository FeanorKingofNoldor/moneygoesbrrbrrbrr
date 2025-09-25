"""
Pattern-Enhanced Wrapper for TradingAgents Integration
Adds pattern intelligence to TradingAgents without modifying core code
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime

from src.patterns import (
    PatternClassifier,
    PatternTracker,
    PatternDatabase,
    PatternMemoryInjector
)
from src.patterns.analyzer import PatternAnalyzer

logger = logging.getLogger(__name__)


class PatternEnhancedWrapper:
    """
    Wrapper that seamlessly integrates pattern intelligence with TradingAgents
    """
    
    def __init__(self, base_tradingagents_wrapper, db_connection):
        """
        Args:
            base_tradingagents_wrapper: Existing OdinTradingAgentsWrapper
            db_connection: Database connection for pattern system
        """
        self.base_wrapper = base_tradingagents_wrapper
        
        # Initialize pattern system
        self.pattern_db = PatternDatabase(db_connection)
        self.classifier = PatternClassifier(self.pattern_db)
        self.tracker = PatternTracker(self.pattern_db)
        
        # Get memory systems from TradingAgents
        memory_systems = self._extract_memory_systems()
        self.memory_injector = PatternMemoryInjector(memory_systems, self.pattern_db)
        
        # Initialize analyzer
        self.analyzer = PatternAnalyzer(
            self.pattern_db,
            self.tracker,
            self.memory_injector
        )
        
        logger.info("Pattern-enhanced wrapper initialized")
    
    def _extract_memory_systems(self) -> Dict:
        """Extract memory systems from TradingAgents graph"""
        try:
            # Access the graph's memory systems
            graph = self.base_wrapper.graph
            
            memories = {}
            if hasattr(graph, 'trader_memory'):
                memories['trader_memory'] = graph.trader_memory
            if hasattr(graph, 'bull_memory'):
                memories['bull_memory'] = graph.bull_memory
            if hasattr(graph, 'bear_memory'):
                memories['bear_memory'] = graph.bear_memory
            if hasattr(graph, 'risk_manager_memory'):
                memories['risk_manager_memory'] = graph.risk_manager_memory
            if hasattr(graph, 'invest_judge_memory'):
                memories['invest_judge_memory'] = graph.invest_judge_memory
            
            logger.info(f"Extracted {len(memories)} memory systems from TradingAgents")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to extract memory systems: {e}")
            return {}
    
    def analyze_with_patterns(self, symbol: str, stock_metrics: Dict, 
                            regime_data: Dict, batch_id: str) -> Dict:
        """
        Enhanced analysis with pattern intelligence
        UPDATED to inject real-time pattern context
        """
        # Step 1: Classify the pattern
        pattern_result = self.classifier.classify_trade(stock_metrics, regime_data)
        pattern_id = pattern_result['pattern_id']
        
        # Step 2: Get pattern statistics
        pattern_context = self.tracker.get_pattern_context(pattern_id)
        
        # Step 3: Inject pattern memory for THIS SPECIFIC TRADE
        if pattern_context.get('exists'):
            pattern_stats = self.pattern_db.get_pattern_stats(pattern_id)
            if pattern_stats:
                # Add current market data to pattern
                pattern_stats['fear_greed'] = regime_data.get('fear_greed_value')
                pattern_stats['vix'] = regime_data.get('vix', 20)
                
                # Inject memory in real-time for this analysis
                self.memory_injector.inject_tradingagents_compatible_memories(
                    [pattern_stats], stock_metrics
                )
                logger.debug(f"Injected real-time pattern memory for {symbol}")
        
        # Step 4: Call base TradingAgents (will now use the injected memory)
        result = self.base_wrapper.analyze_stock(
            symbol=symbol,
            date=datetime.now().strftime('%Y-%m-%d')
        )
        
        # Step 5: Enhance result with pattern data
        result['pattern_id'] = pattern_id
        result['pattern_context'] = pattern_context
        result['pattern_components'] = pattern_result['components']
        
        # Step 6: Track entry if it's a BUY
        if result.get('decision') == 'BUY':
            entry_data = {
                'batch_id': batch_id,
                'symbol': symbol,
                'entry_price': stock_metrics.get('close'),
                'rsi_2': stock_metrics.get('rsi_2'),
                'volume_ratio': stock_metrics.get('volume_ratio'),
                'atr': stock_metrics.get('atr'),
                'vix': regime_data.get('vix'),
                'fear_greed_value': regime_data.get('fear_greed_value'),
                'decision': result['decision'],
                'conviction_score': result.get('conviction_score', 50)
            }
            self.tracker.track_entry(pattern_id, entry_data)
        
        return result
    
    def close_position_with_pattern(self, position_data: Dict) -> Dict:
        """
        Handle position close with pattern tracking
        
        Args:
            position_data: Complete position information
            
        Returns:
            Close results with pattern analysis
        """
        pattern_id = position_data.get('pattern_id')
        
        if pattern_id:
            # Track the exit
            exit_data = {
                'batch_id': position_data['batch_id'],
                'symbol': position_data['symbol'],
                'exit_date': position_data['exit_date'],
                'exit_price': position_data['exit_price'],
                'exit_reason': position_data['exit_reason'],
                'holding_days': position_data['holding_days'],
                'pnl_percent': position_data['pnl_percent'],
                'max_gain_percent': position_data.get('max_gain_percent'),
                'max_drawdown_percent': position_data.get('max_drawdown_percent')
            }
            
            self.tracker.track_exit(pattern_id, exit_data)
            
            # Analyze for immediate learning
            analysis = self.analyzer.analyze_closed_position(position_data)
            
            return {
                'pattern_tracked': True,
                'pattern_id': pattern_id,
                'analysis': analysis
            }
        
        return {'pattern_tracked': False}
    
    def run_pattern_learning(self, frequency: str = 'weekly') -> Dict:
        """
        Run pattern learning process
        
        Args:
            frequency: 'daily' or 'weekly'
            
        Returns:
            Learning results
        """
        if frequency == 'weekly':
            return self.analyzer.run_weekly_analysis()
        elif frequency == 'daily':
            return self.analyzer.run_daily_check()
        else:
            logger.error(f"Unknown frequency: {frequency}")
            return {'error': 'Invalid frequency'}
    
    def get_pattern_report(self) -> Dict:
        """Get comprehensive pattern performance report"""
        return self.tracker.get_pattern_report()
    
# In PatternEnhancedWrapper class, update the initialize method:

def initialize_pattern_memories(self, min_trades: int = 10):
    """
    Initialize memories with existing pattern knowledge
    ENHANCED to use TradingAgents-compatible format
    """
    logger.info("Initializing TradingAgents-compatible pattern memories")
    
    # Get patterns with sufficient history
    patterns = self.pattern_db.get_top_patterns(limit=50, min_trades=min_trades)
    
    if patterns:
        # Get current market data for context
        current_market = {
            'rsi_2': 50,  # Default values for initialization
            'volume_ratio': 1.0,
            'atr': 1.0,
            'price_vs_sma20': 1.0,
            'vix': 20,
            'fear_greed': 50
        }
        
        # Use the new compatible injection method
        injected = self.memory_injector.inject_tradingagents_compatible_memories(
            patterns, current_market
        )
        
        logger.info(f"Initialized with {len(patterns)} patterns, {injected} memories")
        return injected
    
    logger.info("No patterns with sufficient history for initialization")
    return 0
