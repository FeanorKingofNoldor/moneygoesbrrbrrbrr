"""
Pattern Analysis and Learning Engine
Orchestrates pattern analysis and triggers memory updates
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import json

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """
    Analyzes pattern performance and generates learning events
    """
    
    def __init__(self, pattern_db, pattern_tracker, memory_injector):
        """
        Args:
            pattern_db: PatternDatabase instance
            pattern_tracker: PatternTracker instance
            memory_injector: PatternMemoryInjector instance
        """
        self.db = pattern_db
        self.tracker = pattern_tracker
        self.injector = memory_injector
        
        # Track analysis history
        self.last_weekly_analysis = None
        self.last_regime = None
    
    def run_weekly_analysis(self) -> Dict:
        """
        Main weekly analysis process
        Identifies patterns to learn from and injects into memory
        
        Returns:
            Analysis summary
        """
        logger.info("Starting weekly pattern analysis")
        
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'patterns_analyzed': 0,
            'lessons_generated': 0,
            'memories_injected': 0,
            'findings': {}
        }
        
        try:
            # 1. Identify top performing patterns
            top_patterns = self.db.get_top_patterns(limit=10, min_trades=20)
            analysis_results['findings']['top_patterns'] = len(top_patterns)
            
            # 2. Identify breaking patterns
            breaking_patterns = self.db.get_breaking_patterns(threshold=0.40)
            analysis_results['findings']['breaking_patterns'] = len(breaking_patterns)
            
            # 3. Identify hot patterns
            hot_patterns = self.db.get_hot_patterns(min_improvement=0.10)
            analysis_results['findings']['hot_patterns'] = len(hot_patterns)
            
            # 4. Combine and prioritize patterns for learning
            patterns_to_learn = self._prioritize_patterns(
                top_patterns, breaking_patterns, hot_patterns
            )
            analysis_results['patterns_analyzed'] = len(patterns_to_learn)
            
            # 5. Inject lessons into memory
            if patterns_to_learn:
                injected = self.injector.inject_pattern_batch(
                    patterns_to_learn, 
                    injection_type='weekly_analysis'
                )
                analysis_results['memories_injected'] = injected
            
            # 6. Check for regime transitions
            regime_analysis = self._analyze_regime_transitions()
            if regime_analysis:
                analysis_results['findings']['regime_transition'] = regime_analysis
            
            # 7. Generate summary report
            analysis_results['summary'] = self._generate_analysis_summary(
                top_patterns, breaking_patterns, hot_patterns
            )
            
            # 8. Clean up stale patterns
            deactivated = self.db.deactivate_stale_patterns(days_inactive=30)
            analysis_results['patterns_deactivated'] = deactivated
            
            self.last_weekly_analysis = datetime.now()
            logger.info(f"Weekly analysis complete: {analysis_results['memories_injected']} memories injected")
            
        except Exception as e:
            logger.error(f"Weekly analysis failed: {e}")
            analysis_results['error'] = str(e)
        
        return analysis_results
    
    def run_daily_check(self) -> Dict:
        """
        Lighter daily analysis for critical pattern changes
        
        Returns:
            Check results
        """
        logger.debug("Running daily pattern check")
        
        check_results = {
            'timestamp': datetime.now().isoformat(),
            'alerts': [],
            'actions_taken': []
        }
        
        # Check for critically breaking patterns
        critical_patterns = self.db.get_breaking_patterns(threshold=0.30, min_trades=10)
        
        for pattern in critical_patterns:
            if pattern['recent_win_rate'] < 0.25:
                alert = {
                    'type': 'critical_breakdown',
                    'pattern_id': pattern['pattern_id'],
                    'win_rate': pattern['recent_win_rate'],
                    'message': f"Pattern {pattern['pattern_id']} critically underperforming"
                }
                check_results['alerts'].append(alert)
                
                # Inject immediate warning
                self.injector.inject_pattern_batch(
                    [pattern],
                    injection_type='critical_alert'
                )
                check_results['actions_taken'].append(f"Injected warning for {pattern['pattern_id']}")
        
        # Check for suddenly hot patterns
        hot_patterns = self.db.get_hot_patterns(min_improvement=0.20)
        
        for pattern in hot_patterns:
            if pattern['recent_win_rate'] > 0.80:
                alert = {
                    'type': 'hot_pattern',
                    'pattern_id': pattern['pattern_id'],
                    'win_rate': pattern['recent_win_rate'],
                    'message': f"Pattern {pattern['pattern_id']} showing exceptional performance"
                }
                check_results['alerts'].append(alert)
        
        return check_results
    
    def analyze_closed_position(self, position_data: Dict) -> Dict:
        """
        Analyze a closed position and trigger immediate learning if needed
        
        Args:
            position_data: Complete position information including pattern_id
            
        Returns:
            Analysis results
        """
        pattern_id = position_data.get('pattern_id')
        if not pattern_id:
            return {'error': 'No pattern_id in position data'}
        
        analysis = {
            'pattern_id': pattern_id,
            'pnl_percent': position_data['pnl_percent'],
            'lessons_generated': False
        }
        
        # Get pattern stats
        pattern_stats = self.db.get_pattern_stats(pattern_id)
        if not pattern_stats:
            return {'error': f'Pattern {pattern_id} not found'}
        
        # Determine if outcome was surprising
        expected_win_rate = pattern_stats['win_rate']
        actual_won = position_data['pnl_percent'] > 0
        
        # Check for surprising outcomes
        if expected_win_rate > 0.70 and not actual_won:
            # High confidence pattern failed
            logger.warning(f"High confidence pattern {pattern_id} failed unexpectedly")
            
            outcome_data = {
                'strategy_type': pattern_stats['strategy_type'],
                'regime': pattern_stats['market_regime'],
                'rsi_at_entry': position_data.get('rsi_at_entry'),
                'volume_at_entry': position_data.get('volume_ratio_at_entry'),
                'holding_days': position_data.get('holding_days'),
                'pnl_percent': position_data['pnl_percent'],
                'exit_reason': position_data.get('exit_reason')
            }
            
            # Inject immediate learning
            self.injector.inject_single_pattern_outcome(pattern_id, outcome_data)
            analysis['lessons_generated'] = True
            analysis['lesson_type'] = 'unexpected_failure'
            
        elif expected_win_rate < 0.30 and actual_won and position_data['pnl_percent'] > 3.0:
            # Low confidence pattern succeeded big
            logger.info(f"Low confidence pattern {pattern_id} succeeded unexpectedly")
            
            outcome_data = {
                'strategy_type': pattern_stats['strategy_type'],
                'regime': pattern_stats['market_regime'],
                'rsi_at_entry': position_data.get('rsi_at_entry'),
                'volume_at_entry': position_data.get('volume_ratio_at_entry'),
                'holding_days': position_data.get('holding_days'),
                'pnl_percent': position_data['pnl_percent'],
                'exit_reason': position_data.get('exit_reason')
            }
            
            # Inject immediate learning
            self.injector.inject_single_pattern_outcome(pattern_id, outcome_data)
            analysis['lessons_generated'] = True
            analysis['lesson_type'] = 'unexpected_success'
        
        return analysis
    
    def _prioritize_patterns(self, top: List, breaking: List, hot: List) -> List[Dict]:
        """
        Prioritize which patterns to learn from
        
        Returns:
            Prioritized list of patterns for memory injection
        """
        # Use a set to avoid duplicates
        seen_patterns = set()
        prioritized = []
        
        # Priority 1: Breaking patterns (need immediate attention)
        for pattern in breaking:
            if pattern['pattern_id'] not in seen_patterns:
                pattern['priority'] = 'critical'
                prioritized.append(pattern)
                seen_patterns.add(pattern['pattern_id'])
        
        # Priority 2: Hot patterns (capitalize on success)
        for pattern in hot:
            if pattern['pattern_id'] not in seen_patterns:
                pattern['priority'] = 'high'
                prioritized.append(pattern)
                seen_patterns.add(pattern['pattern_id'])
        
        # Priority 3: Top patterns (reinforce what works)
        for pattern in top[:5]:  # Limit to top 5
            if pattern['pattern_id'] not in seen_patterns:
                pattern['priority'] = 'normal'
                prioritized.append(pattern)
                seen_patterns.add(pattern['pattern_id'])
        
        logger.info(f"Prioritized {len(prioritized)} patterns for learning")
        
        return prioritized
    
    def _analyze_regime_transitions(self) -> Optional[Dict]:
        """
        Check if regime has changed and analyze impact
        
        Returns:
            Regime transition analysis or None
        """
        # Get current regime from recent trades
        recent_trades = pd.read_sql("""
            SELECT regime_at_entry, COUNT(*) as count
            FROM position_tracking
            WHERE entry_date > date('now', '-7 days')
            GROUP BY regime_at_entry
            ORDER BY count DESC
            LIMIT 1
        """, self.db.conn)
        
        if recent_trades.empty:
            return None
        
        current_regime = recent_trades.iloc[0]['regime_at_entry']
        
        if self.last_regime and current_regime != self.last_regime:
            # Regime changed!
            logger.info(f"Regime transition detected: {self.last_regime} → {current_regime}")
            
            # Analyze pattern performance changes
            old_patterns = self.db.get_regime_patterns(self.last_regime)
            new_patterns = self.db.get_regime_patterns(current_regime)
            
            # Find patterns that might break
            breaking = []
            for pattern in old_patterns:
                if pattern['win_rate'] > 0.60:
                    breaking.append(pattern['pattern_id'])
            
            # Find patterns that might emerge
            emerging = []
            for pattern in new_patterns:
                if pattern['win_rate'] > 0.60:
                    emerging.append(pattern['pattern_id'])
            
            # Inject regime transition lesson
            self.injector.inject_regime_transition_lessons(
                self.last_regime,
                current_regime,
                breaking[:5],  # Top 5 at risk
                emerging[:5]   # Top 5 opportunities
            )
            
            self.last_regime = current_regime
            
            return {
                'from_regime': self.last_regime,
                'to_regime': current_regime,
                'patterns_at_risk': len(breaking),
                'patterns_emerging': len(emerging)
            }
        
        self.last_regime = current_regime
        return None
    
    def _generate_analysis_summary(self, top: List, breaking: List, hot: List) -> str:
        """Generate human-readable summary"""
        
        summary_parts = []
        
        if top:
            best = top[0]
            summary_parts.append(
                f"Best pattern: {best['pattern_id']} with {best['win_rate']:.1%} win rate"
            )
        
        if breaking:
            worst = breaking[0]
            summary_parts.append(
                f"Worst breakdown: {worst['pattern_id']} dropped to {worst['recent_win_rate']:.1%}"
            )
        
        if hot:
            hottest = hot[0]
            summary_parts.append(
                f"Hottest pattern: {hottest['pattern_id']} improved by {hottest['momentum_score']:.1%}"
            )
        
        return ". ".join(summary_parts) if summary_parts else "No significant patterns found"
    
    def get_pattern_recommendations(self, current_candidates: List[Dict]) -> Dict:
        """
        Get pattern-based recommendations for current candidates
        
        Args:
            current_candidates: List of stocks being considered
            
        Returns:
            Recommendations by symbol
        """
        recommendations = {}
        
        for candidate in current_candidates:
            symbol = candidate['symbol']
            pattern_id = candidate.get('pattern_id')
            
            if not pattern_id:
                recommendations[symbol] = {
                    'pattern_exists': False,
                    'recommendation': 'No pattern classification available'
                }
                continue
            
            # Get pattern context
            context = self.tracker.get_pattern_context(pattern_id)
            
            recommendations[symbol] = {
                'pattern_exists': True,
                'pattern_id': pattern_id,
                'win_rate': context.get('win_rate', 0),
                'expectancy': context.get('expectancy', 0),
                'confidence': context.get('confidence', 'low'),
                'recommendation': context.get('recommendation', 'No specific recommendation')
            }
        
        return recommendations