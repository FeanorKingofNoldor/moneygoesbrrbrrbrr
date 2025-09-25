"""
Pattern Memory Injector
Injects pattern-based lessons into TradingAgents memory systems
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class PatternMemoryInjector:
    """
    Converts pattern performance into memories for TradingAgents agents
    Uses the exact format expected by the TradingAgents memory system
    """

    def __init__(self, memory_systems: Dict, pattern_db):
        """
        Args:
            memory_systems: Dict with agent memories from TradingAgents
                           Keys: 'bull_memory', 'bear_memory', 'trader_memory', etc.
            pattern_db: PatternDatabase instance
        """
        self.memories = memory_systems
        self.db = pattern_db

        # Track what we've injected to avoid duplicates
        self._injection_history = []
        self._max_history = 100

    def format_pattern_as_memory(self, pattern_data: Dict) -> Tuple[str, str]:
        """
        Convert pattern stats into (situation, recommendation) tuple
        This is EXACTLY what TradingAgents memory.add_situations() expects

        Args:
            pattern_data: Pattern statistics from database

        Returns:
            Tuple of (situation description, recommendation/lesson)
        """
        # Build situation - what the market looked like
        situation = self._build_situation_description(pattern_data)

        # Build recommendation based on performance
        recommendation = self._build_recommendation(pattern_data)

        return (situation, recommendation)

    def _build_situation_description(self, pattern: Dict) -> str:
        """Build market situation description"""

        # Extract components
        regime = pattern["market_regime"].replace("_", " ").title()
        strategy = pattern["strategy_type"].replace("_", " ")
        volume = pattern["volume_profile"]
        technical = pattern["technical_setup"]

        # Get recent market context if available
        vix_context = ""
        if "vix" in pattern:
            vix_context = f"VIX at {pattern['vix']:.1f}. "

        fear_greed_context = ""
        if "fear_greed" in pattern:
            fear_greed_context = f"Fear & Greed Index showing {pattern['fear_greed']}. "

        situation = f"""Market displayed {regime} regime conditions. {fear_greed_context}{vix_context}
Technical indicators suggested {strategy} setup with {technical} RSI conditions. 
Volume was {volume} relative to recent average. 
Pattern classification: {pattern['pattern_id']}"""

        return situation

    def _build_recommendation(self, pattern: Dict) -> str:
        """Build recommendation based on pattern performance"""

        win_rate = pattern["win_rate"]
        recent_win_rate = pattern["recent_win_rate"]
        expectancy = pattern["expectancy"]
        confidence = pattern["confidence_level"]
        momentum = pattern.get("momentum_score", 0)
        total_trades = pattern["total_trades"]

        # Determine recommendation strength
        if confidence == "low":
            strength = "LIMITED DATA WARNING: "
            confidence_note = f"Only {total_trades} historical trades. "
        elif confidence == "high":
            strength = "HIGH CONFIDENCE: "
            confidence_note = f"Based on {total_trades} trades. "
        else:
            strength = ""
            confidence_note = f"Moderate confidence from {total_trades} trades. "

        # Build performance-based recommendation
        if win_rate > 0.65 and recent_win_rate > 0.70:
            recommendation = f"""{strength}This pattern has been HIGHLY SUCCESSFUL with {win_rate:.1%} historical win rate.
Recent performance even stronger at {recent_win_rate:.1%}. {confidence_note}
INCREASE CONVICTION and consider LARGER POSITION SIZE up to 1.5x normal.
Expected value: {expectancy:.2%} per trade. Pattern momentum: IMPROVING."""

        elif win_rate > 0.55 and momentum > 0.05:
            recommendation = f"""{strength}This pattern shows POSITIVE EDGE with {win_rate:.1%} win rate.
Recent trend improving ({recent_win_rate:.1%} recently). {confidence_note}
Proceed with NORMAL TO HIGH conviction. Standard position sizing appropriate.
Expected value: {expectancy:.2%} per trade."""

        elif win_rate < 0.40 or recent_win_rate < 0.35:
            recommendation = f"""{strength}WARNING: This pattern is UNDERPERFORMING with only {win_rate:.1%} historical wins.
Recent performance concerning at {recent_win_rate:.1%}. {confidence_note}
REDUCE CONVICTION significantly. Consider HOLDING instead of BUYING.
If entering, use 50% normal position size. Expected loss: {expectancy:.2%}."""

        elif momentum < -0.15:
            recommendation = f"""{strength}CAUTION: Pattern showing DETERIORATION.
Historical {win_rate:.1%} win rate but recent only {recent_win_rate:.1%}. {confidence_note}
Pattern may be BREAKING DOWN. Reduce position size and tighten stops.
Monitor closely for regime change. Current expectancy: {expectancy:.2%}."""

        else:
            recommendation = f"""{strength}Pattern shows NEUTRAL performance with {win_rate:.1%} win rate.
Recent performance {recent_win_rate:.1%}. {confidence_note}
Use STANDARD conviction and position sizing. No edge detected.
Expected value near zero: {expectancy:.2%} per trade."""

        return recommendation

    def inject_pattern_batch(
        self, pattern_stats_list: List[Dict], injection_type: str = "scheduled"
    ):
        """
        Inject multiple pattern lessons at once

        Args:
            pattern_stats_list: List of pattern statistics
            injection_type: 'scheduled', 'real_time', or 'initialization'
        """
        logger.info(
            f"Injecting {len(pattern_stats_list)} pattern lessons ({injection_type})"
        )

        # Prepare memories for each agent type
        trader_memories = []
        bull_memories = []
        bear_memories = []
        risk_memories = []
        judge_memories = []

        for pattern in pattern_stats_list:
            # Skip if recently injected
            if self._was_recently_injected(pattern["pattern_id"]):
                continue

            situation, recommendation = self.format_pattern_as_memory(pattern)

            # Customize for different agent perspectives
            if pattern["win_rate"] > 0.60:
                # Bulls should know about winning patterns
                bull_msg = f"BULLISH PATTERN: {recommendation} Historical data strongly supports aggressive positioning."
                bull_memories.append((situation, bull_msg))

                # Judges need balanced view
                judge_msg = f"FAVORABLE PATTERN: {recommendation} Consider tilting bullish but maintain risk awareness."
                judge_memories.append((situation, judge_msg))

            elif pattern["win_rate"] < 0.45:
                # Bears should know about losing patterns
                bear_msg = f"BEARISH WARNING: {recommendation} Historical data suggests caution or avoidance."
                bear_memories.append((situation, bear_msg))

                # Risk managers especially need warnings
                risk_msg = f"HIGH RISK PATTERN: {recommendation} Implement strict risk controls or avoid entry."
                risk_memories.append((situation, risk_msg))

            # Traders get everything
            trader_memories.append((situation, recommendation))

            # Track injection
            self._record_injection(pattern["pattern_id"])

        # Inject into respective memories
        injection_count = 0

        if trader_memories and "trader_memory" in self.memories:
            self.memories["trader_memory"].add_situations(trader_memories)
            injection_count += len(trader_memories)
            logger.debug(f"Injected {len(trader_memories)} lessons into Trader memory")

        if bull_memories and "bull_memory" in self.memories:
            self.memories["bull_memory"].add_situations(bull_memories)
            injection_count += len(bull_memories)
            logger.debug(f"Injected {len(bull_memories)} lessons into Bull memory")

        if bear_memories and "bear_memory" in self.memories:
            self.memories["bear_memory"].add_situations(bear_memories)
            injection_count += len(bear_memories)
            logger.debug(f"Injected {len(bear_memories)} lessons into Bear memory")

        if risk_memories and "risk_manager_memory" in self.memories:
            self.memories["risk_manager_memory"].add_situations(risk_memories)
            injection_count += len(risk_memories)
            logger.debug(
                f"Injected {len(risk_memories)} lessons into Risk Manager memory"
            )

        if judge_memories and "invest_judge_memory" in self.memories:
            self.memories["invest_judge_memory"].add_situations(judge_memories)
            injection_count += len(judge_memories)
            logger.debug(f"Injected {len(judge_memories)} lessons into Judge memory")

        # Log the learning event
        if injection_count > 0:
            self._log_learning_event(pattern_stats_list, injection_type)

        logger.info(f"Total memories injected: {injection_count}")

        return injection_count

    def inject_single_pattern_outcome(self, pattern_id: str, outcome: Dict):
        """
        Inject immediate feedback when a pattern-based trade closes

        Args:
            pattern_id: Pattern that was traded
            outcome: Trade outcome with pnl, dates, etc.
        """
        # Build immediate feedback memory
        situation = f"""Just completed {outcome.get('strategy_type', 'position')} trade in {outcome.get('regime', 'current')} regime.
Entry indicators: RSI {outcome.get('rsi_at_entry', 'N/A')}, volume {outcome.get('volume_at_entry', 'N/A')}x normal.
Pattern ID: {pattern_id}. Held for {outcome.get('holding_days', 'N/A')} days."""

        if outcome["pnl_percent"] > 3.0:
            recommendation = f"""SUCCESSFUL PATTERN TRADE: +{outcome['pnl_percent']:.1%} return!
Pattern {pattern_id} continues performing excellently. INCREASE conviction on similar setups.
This validates the pattern's edge. Consider larger position next time."""

        elif outcome["pnl_percent"] > 0:
            recommendation = f"""Winning trade: +{outcome['pnl_percent']:.1%} return.
Pattern {pattern_id} performed as expected. Maintain current approach."""

        elif outcome["pnl_percent"] < -2.0:
            recommendation = f"""PATTERN FAILURE: {outcome['pnl_percent']:.1%} loss.
Pattern {pattern_id} did not work this time. Monitor for potential breakdown.
If pattern continues failing, reduce position size or avoid."""

        else:
            recommendation = f"""Minor loss: {outcome['pnl_percent']:.1%}.
Pattern {pattern_id} didn't work but loss contained. Continue monitoring performance."""

        # Add exit reason context
        if outcome.get("exit_reason"):
            recommendation += f" Exit trigger: {outcome['exit_reason']}."

        # Inject to all memories for immediate learning
        memory_entry = [(situation, recommendation)]

        injected_to = []
        for memory_name, memory in self.memories.items():
            try:
                memory.add_situations(memory_entry)
                injected_to.append(memory_name)
            except Exception as e:
                logger.warning(f"Failed to inject to {memory_name}: {e}")

        logger.info(f"Real-time feedback injected for pattern {pattern_id} outcome")

        # Log the immediate learning
        self.db.record_learning_event(
            lesson_type="immediate_outcome",
            patterns=[pattern_id],
            situation=situation,
            recommendation=recommendation,
            memory_systems=injected_to,
        )

        return len(injected_to) > 0

    def inject_regime_transition_lessons(
        self,
        from_regime: str,
        to_regime: str,
        breaking_patterns: List[str],
        emerging_patterns: List[str],
    ):
        """
        Inject lessons about regime transitions

        Args:
            from_regime: Previous market regime
            to_regime: New market regime
            breaking_patterns: Patterns that stopped working
            emerging_patterns: Patterns that started working
        """
        situation = f"""MARKET REGIME CHANGE DETECTED: Shifted from {from_regime} to {to_regime}.
This transition typically causes significant pattern performance changes.
Historical transitions show different strategies become optimal."""

        recommendation = f"""ADJUST STRATEGY for {to_regime} regime:
AVOID these breaking patterns: {', '.join(breaking_patterns[:3]) if breaking_patterns else 'None identified yet'}.
FAVOR these emerging patterns: {', '.join(emerging_patterns[:3]) if emerging_patterns else 'None identified yet'}.
Reduce position sizes during transition period until patterns stabilize.
Monitor pattern performance closely for next 5-10 trades."""

        # This is critical for all agents
        memory_entry = [(situation, recommendation)]

        for memory_name, memory in self.memories.items():
            try:
                memory.add_situations(memory_entry)
                logger.info(f"Regime transition lesson injected to {memory_name}")
            except Exception as e:
                logger.warning(f"Failed to inject regime lesson to {memory_name}: {e}")

        # Log the event
        self.db.record_learning_event(
            lesson_type="regime_transition",
            patterns=breaking_patterns + emerging_patterns,
            situation=situation,
            recommendation=recommendation,
            memory_systems=list(self.memories.keys()),
        )

    def _was_recently_injected(self, pattern_id: str) -> bool:
        """Check if pattern was recently injected to avoid duplicates"""
        return pattern_id in self._injection_history

    def _record_injection(self, pattern_id: str):
        """Track injection to prevent duplicates"""
        self._injection_history.append(pattern_id)
        if len(self._injection_history) > self._max_history:
            self._injection_history = self._injection_history[-self._max_history :]

    def _log_learning_event(self, patterns: List[Dict], injection_type: str):
        """Log learning event to database"""
        pattern_ids = [p["pattern_id"] for p in patterns]

        # Create summary
        avg_win_rate = (
            sum(p["win_rate"] for p in patterns) / len(patterns) if patterns else 0
        )
        situation_summary = f"{injection_type} learning from {len(patterns)} patterns"
        recommendation_summary = f"Average win rate: {avg_win_rate:.1%}"

        self.db.record_learning_event(
            lesson_type=injection_type,
            patterns=pattern_ids,
            situation=situation_summary,
            recommendation=recommendation_summary,
            memory_systems=list(self.memories.keys()),
        )

    def inject_tradingagents_compatible_memories(
            self, pattern_stats_list: List[Dict], current_market_data: Dict
        ):
            """
            Inject pattern memories in TradingAgents-compatible format

            Args:
                pattern_stats_list: Pattern statistics to inject
                current_market_data: Current market metrics for situation building
            """
            from src.patterns.memory_bridge import TradingAgentsMemoryBridge

            logger.info(
                f"Injecting {len(pattern_stats_list)} TradingAgents-compatible memories"
            )

            # Prepare memories for each agent
            all_memories = []

            for pattern in pattern_stats_list:
                # Format for TradingAgents
                situation, recommendation = (
                    TradingAgentsMemoryBridge.format_pattern_for_tradingagents(
                        pattern, current_market_data
                    )
                )

                # Customize for different agents
                if pattern["win_rate"] > 0.60:
                    # Bull perspective
                    bull_rec = f"BULLISH VIEW: {recommendation} Market conditions favor aggressive positioning."
                    if "bull_memory" in self.memories:
                        self.memories["bull_memory"].add_situations(
                            [(situation, bull_rec)]
                        )

                    # Research manager perspective
                    if "invest_judge_memory" in self.memories:
                        judge_rec = f"RESEARCH CONCLUSION: {recommendation} Data supports bullish stance."
                        self.memories["invest_judge_memory"].add_situations(
                            [(situation, judge_rec)]
                        )

                elif pattern["win_rate"] < 0.45:
                    # Bear perspective
                    bear_rec = f"BEARISH VIEW: {recommendation} Conditions suggest caution or short positions."
                    if "bear_memory" in self.memories:
                        self.memories["bear_memory"].add_situations(
                            [(situation, bear_rec)]
                        )

                    # Risk manager perspective
                    if "risk_manager_memory" in self.memories:
                        risk_rec = f"RISK WARNING: {recommendation} Implement tight risk controls."
                        self.memories["risk_manager_memory"].add_situations(
                            [(situation, risk_rec)]
                        )

                # Trader gets everything
                if "trader_memory" in self.memories:
                    trader_rec = f"TRADING DECISION: {recommendation}"
                    self.memories["trader_memory"].add_situations(
                        [(situation, trader_rec)]
                    )

                all_memories.append((situation, recommendation))

            logger.info(
                f"Injected {len(all_memories)} TradingAgents-compatible pattern memories"
            )
            return len(all_memories)

    def inject_closed_position_memories(self, position_data: Dict, pattern_stats: Dict):
        """
        Inject both specific trade and updated pattern memories when position closes
        
        Args:
            position_data: Closed position details with P&L
            pattern_stats: Updated pattern statistics after this trade
        """
        from src.patterns.memory_bridge import TradingAgentsMemoryBridge
        
        logger.info(f"Injecting memories for closed {position_data['symbol']} position")
        
        # Create hybrid memories (both trade-specific and pattern update)
        memories = TradingAgentsMemoryBridge.create_hybrid_memories(
            position_data, pattern_stats
        )
        
        # Inject to all agent memories
        injected_count = 0
        for situation, recommendation in memories:
            # Customize for different agents
            for agent_name, memory in self.memories.items():
                try:
                    if 'bull' in agent_name.lower() and position_data.get('pnl_percent', 0) > 0:
                        # Bulls learn from wins
                        memory.add_situations([(situation, f"BULLISH WIN: {recommendation}")])
                        injected_count += 1
                        
                    elif 'bear' in agent_name.lower() and position_data.get('pnl_percent', 0) < 0:
                        # Bears learn from losses
                        memory.add_situations([(situation, f"BEARISH VALIDATION: {recommendation}")])
                        injected_count += 1
                        
                    elif 'risk' in agent_name.lower() and abs(position_data.get('pnl_percent', 0)) > 3:
                        # Risk manager learns from large moves
                        memory.add_situations([(situation, f"RISK EVENT: {recommendation}")])
                        injected_count += 1
                        
                    else:
                        # Everyone gets the standard lesson
                        memory.add_situations([(situation, recommendation)])
                        injected_count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to inject to {agent_name}: {e}")
        
        # Log the learning event
        self.db.record_learning_event(
            lesson_type='position_closed',
            patterns=[position_data.get('pattern_id', 'unknown')],
            situation=f"Closed {position_data['symbol']} with {position_data.get('pnl_percent', 0):.2%} P&L",
            recommendation=f"Pattern {pattern_stats.get('win_rate', 0):.1%} win rate after {pattern_stats.get('total_trades', 0)} trades",
            memory_systems=list(self.memories.keys())
        )
        
        logger.info(f"Injected {injected_count} memories from closed position")
        return injected_count

    def inject_pattern_batch_with_context(self, pattern_stats_list: List[Dict], 
                                        recent_trades: List[Dict] = None):
        """
        Inject pattern memories with optional recent trade context
        
        Args:
            pattern_stats_list: Pattern statistics to inject
            recent_trades: Optional list of recent trades for context
        """
        from src.patterns.memory_bridge import TradingAgentsMemoryBridge
        
        logger.info(f"Injecting {len(pattern_stats_list)} patterns with trade context")
        
        memories_to_inject = []
        
        for pattern in pattern_stats_list:
            # Create base pattern memory
            current_metrics = {
                'rsi_2': 50,  # Default for batch injection
                'volume_ratio': 1.0,
                'atr': 1.0,
                'price_vs_sma20': 1.0
            }
            
            # Check if we have recent trades for this pattern
            pattern_trades = []
            if recent_trades:
                pattern_trades = [t for t in recent_trades 
                                if t.get('pattern_id') == pattern['pattern_id']]
            
            # Create pattern memory
            situation, recommendation = TradingAgentsMemoryBridge.create_pattern_memory(
                pattern, current_metrics
            )
            
            # Enhance with recent trade examples if available
            if pattern_trades:
                recent_examples = pattern_trades[:3]  # Last 3 trades
                trade_context = "\nRecent Examples: "
                for trade in recent_examples:
                    trade_context += f"{trade['symbol']} ({trade['pnl_percent']:+.1%}), "
                recommendation += trade_context.rstrip(', ')
            
            memories_to_inject.append((situation, recommendation))
        
        # Inject all memories
        for memory_name, memory in self.memories.items():
            try:
                memory.add_situations(memories_to_inject)
                logger.debug(f"Injected {len(memories_to_inject)} patterns to {memory_name}")
            except Exception as e:
                logger.warning(f"Failed to inject to {memory_name}: {e}")
        
        return len(memories_to_inject)