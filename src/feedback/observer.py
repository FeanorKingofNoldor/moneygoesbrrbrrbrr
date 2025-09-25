"""
Observation System for ODIN Feedback Loop
Tracks all decisions and outcomes without making adjustments
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class PerformanceObserver:
    """
    Observes and records all system decisions and their outcomes
    No adjustments - just pure observation until we have 100+ trades
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.create_observation_tables()
    
    def create_observation_tables(self):
        """Create tables for tracking observations"""
        
        # Main observation table
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_date DATE,
            symbol TEXT NOT NULL,
            
            -- What happened in our pipeline
            passed_filter BOOLEAN,
            filter_score REAL,
            filter_layer TEXT,  -- Which layer selected/rejected it
            analyzed_by_tradingagents BOOLEAN,
            tradingagents_decision TEXT,
            tradingagents_conviction REAL,
            selected_by_portfolio_constructor BOOLEAN,
            
            -- Entry context
            entry_date DATE,
            entry_price REAL,
            regime_at_entry TEXT,
            vix_at_entry REAL,
            rsi_at_entry REAL,
            volume_ratio_at_entry REAL,
            
            -- What actually happened
            executed BOOLEAN,
            exit_date DATE,
            exit_price REAL,
            holding_days INTEGER,
            pnl_dollars REAL,
            pnl_percent REAL,
            max_gain_percent REAL,
            max_drawdown_percent REAL,
            exit_reason TEXT,
            
            -- Classification
            outcome_category TEXT,  -- 'big_win', 'win', 'neutral', 'loss', 'big_loss'
            was_correct_decision BOOLEAN,
            
            -- Metadata
            batch_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(symbol, entry_date)
        )
        """)
        
        # Missed opportunities table
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS missed_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE,
            symbol TEXT,
            reason_missed TEXT,  -- 'filtered_out', 'no_buy_signal', 'not_selected'
            potential_gain_percent REAL,
            filter_score REAL,
            would_have_been_profitable BOOLEAN,
            notes TEXT
        )
        """)
        
        # Daily summary stats
        self.db.execute("""
        CREATE TABLE IF NOT EXISTS daily_observations (
            date DATE PRIMARY KEY,
            total_filtered INTEGER,
            total_analyzed INTEGER,
            buy_signals INTEGER,
            sell_signals INTEGER,
            hold_signals INTEGER,
            positions_entered INTEGER,
            positions_exited INTEGER,
            
            -- Accuracy metrics
            correct_decisions INTEGER,
            incorrect_decisions INTEGER,
            
            -- Performance
            avg_pnl_percent REAL,
            win_rate REAL,
            
            -- Regime
            regime TEXT,
            fear_greed_value INTEGER,
            vix REAL
        )
        """)
        
        self.db.commit()
        logger.info("Observation tables created/verified")
    
    def record_pipeline_decision(self, batch_id: str, symbol: str, stage: str, data: Dict):
        """
        Record what happened at each stage of the pipeline
        
        Args:
            batch_id: Batch identifier
            symbol: Stock symbol
            stage: 'filter' | 'tradingagents' | 'portfolio_constructor' | 'execution'
            data: Stage-specific data
        """
        try:
            # Check if observation exists
            existing = self.db.execute("""
                SELECT id FROM observations 
                WHERE symbol = ? AND observation_date = date('now')
            """, (symbol,)).fetchone()
            
            if existing:
                observation_id = existing[0]
                # Update existing observation
                self._update_observation(observation_id, stage, data)
            else:
                # Create new observation
                self._create_observation(batch_id, symbol, stage, data)
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to record observation for {symbol}: {e}")
    
    def _create_observation(self, batch_id: str, symbol: str, stage: str, data: Dict):
        """Create a new observation entry"""
        
        if stage == 'filter':
            self.db.execute("""
                INSERT INTO observations 
                (batch_id, symbol, observation_date, passed_filter, filter_score, 
                 filter_layer, rsi_at_entry, volume_ratio_at_entry)
                VALUES (?, ?, date('now'), ?, ?, ?, ?, ?)
            """, (
                batch_id,
                symbol,
                data.get('passed', False),
                data.get('score', 0),
                data.get('layer', 'unknown'),
                data.get('rsi_2', 0),
                data.get('volume_ratio', 0)
            ))
    
    def _update_observation(self, observation_id: int, stage: str, data: Dict):
        """Update an existing observation"""
        
        if stage == 'tradingagents':
            self.db.execute("""
                UPDATE observations 
                SET analyzed_by_tradingagents = 1,
                    tradingagents_decision = ?,
                    tradingagents_conviction = ?
                WHERE id = ?
            """, (
                data.get('decision', 'HOLD'),
                data.get('conviction', 50),
                observation_id
            ))
        
        elif stage == 'portfolio_constructor':
            self.db.execute("""
                UPDATE observations 
                SET selected_by_portfolio_constructor = ?
                WHERE id = ?
            """, (
                data.get('selected', False),
                observation_id
            ))
        
        elif stage == 'execution':
            self.db.execute("""
                UPDATE observations 
                SET executed = 1,
                    entry_date = date('now'),
                    entry_price = ?,
                    regime_at_entry = ?
                WHERE id = ?
            """, (
                data.get('entry_price', 0),
                data.get('regime', 'unknown'),
                observation_id
            ))
    
    def update_position_outcome(self, symbol: str, exit_data: Dict):
        """
        Update observation with actual outcome after position closes
        
        Args:
            symbol: Stock symbol
            exit_data: Exit price, date, pnl, etc.
        """
        try:
            # Calculate outcome category
            pnl_pct = exit_data.get('pnl_percent', 0)
            if pnl_pct > 5:
                category = 'big_win'
            elif pnl_pct > 2:
                category = 'win'
            elif pnl_pct > -2:
                category = 'neutral'
            elif pnl_pct > -5:
                category = 'loss'
            else:
                category = 'big_loss'
            
            # Determine if decision was correct
            decision = self.db.execute("""
                SELECT tradingagents_decision FROM observations
                WHERE symbol = ? AND exit_date IS NULL
                ORDER BY entry_date DESC LIMIT 1
            """, (symbol,)).fetchone()
            
            was_correct = False
            if decision:
                if decision[0] == 'BUY' and pnl_pct > 2:
                    was_correct = True
                elif decision[0] == 'SELL' and pnl_pct < -2:
                    was_correct = True  # We avoided a loss
                elif decision[0] == 'HOLD' and abs(pnl_pct) < 2:
                    was_correct = True
            
            # Update observation
            self.db.execute("""
                UPDATE observations
                SET exit_date = ?,
                    exit_price = ?,
                    holding_days = ?,
                    pnl_percent = ?,
                    pnl_dollars = ?,
                    exit_reason = ?,
                    outcome_category = ?,
                    was_correct_decision = ?
                WHERE symbol = ? AND exit_date IS NULL
            """, (
                exit_data['exit_date'],
                exit_data['exit_price'],
                exit_data.get('holding_days', 0),
                pnl_pct,
                exit_data.get('pnl_dollars', 0),
                exit_data.get('exit_reason', 'unknown'),
                category,
                was_correct,
                symbol
            ))
            
            self.db.commit()
            logger.info(f"Updated outcome for {symbol}: {category} ({pnl_pct:.2f}%)")
            
        except Exception as e:
            logger.error(f"Failed to update outcome for {symbol}: {e}")
    
    def record_missed_opportunity(self, symbol: str, reason: str, data: Dict):
        """
        Record stocks that we should have bought but didn't
        """
        # This runs after we see what happened to stocks we didn't select
        self.db.execute("""
            INSERT INTO missed_opportunities
            (date, symbol, reason_missed, potential_gain_percent, 
             filter_score, would_have_been_profitable, notes)
            VALUES (date('now'), ?, ?, ?, ?, ?, ?)
        """, (
            symbol,
            reason,  # 'filtered_out', 'no_buy_signal', 'not_selected'
            data.get('potential_gain', 0),
            data.get('filter_score', 0),
            data.get('potential_gain', 0) > 3,  # Would have been profitable?
            json.dumps(data.get('notes', {}))
        ))
        self.db.commit()
    
    def generate_observation_report(self, lookback_days: int = 30) -> Dict:
        """
        Generate a comprehensive observation report
        NO RECOMMENDATIONS - just observations
        """
        report = {
            'period_days': lookback_days,
            'total_observations': 0,
            'patterns': {},
            'metrics': {}
        }
        
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # Basic counts
        report['total_observations'] = self.db.execute("""
            SELECT COUNT(*) FROM observations 
            WHERE observation_date > ?
        """, (cutoff_date,)).fetchone()[0]
        
        if report['total_observations'] < 10:
            report['message'] = "Insufficient data for meaningful observations"
            return report
        
        # Filter effectiveness
        filter_stats = pd.read_sql("""
            SELECT 
                passed_filter,
                AVG(CASE WHEN pnl_percent > 2 THEN 1 ELSE 0 END) as win_rate,
                AVG(pnl_percent) as avg_return,
                COUNT(*) as count
            FROM observations
            WHERE observation_date > ? AND pnl_percent IS NOT NULL
            GROUP BY passed_filter
        """, self.db, params=[cutoff_date])
        
        if not filter_stats.empty:
            report['patterns']['filter_effectiveness'] = filter_stats.to_dict('records')
        
        # TradingAgents accuracy
        decision_accuracy = pd.read_sql("""
            SELECT 
                tradingagents_decision,
                AVG(CASE WHEN was_correct_decision THEN 1 ELSE 0 END) as accuracy,
                AVG(tradingagents_conviction) as avg_conviction,
                AVG(pnl_percent) as avg_return,
                COUNT(*) as count
            FROM observations
            WHERE observation_date > ? 
                AND tradingagents_decision IS NOT NULL
                AND pnl_percent IS NOT NULL
            GROUP BY tradingagents_decision
        """, self.db, params=[cutoff_date])
        
        if not decision_accuracy.empty:
            report['patterns']['decision_accuracy'] = decision_accuracy.to_dict('records')
        
        # Regime performance
        regime_stats = pd.read_sql("""
            SELECT 
                regime_at_entry,
                AVG(pnl_percent) as avg_return,
                AVG(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END) as win_rate,
                COUNT(*) as trades
            FROM observations
            WHERE observation_date > ? AND regime_at_entry IS NOT NULL
            GROUP BY regime_at_entry
        """, self.db, params=[cutoff_date])
        
        if not regime_stats.empty:
            report['patterns']['regime_performance'] = regime_stats.to_dict('records')
        
        # Conviction correlation
        conviction_correlation = pd.read_sql("""
            SELECT 
                CASE 
                    WHEN tradingagents_conviction >= 80 THEN 'Very High (80+)'
                    WHEN tradingagents_conviction >= 60 THEN 'High (60-80)'
                    WHEN tradingagents_conviction >= 40 THEN 'Medium (40-60)'
                    ELSE 'Low (<40)'
                END as conviction_range,
                AVG(pnl_percent) as avg_return,
                COUNT(*) as count
            FROM observations
            WHERE observation_date > ? 
                AND tradingagents_conviction IS NOT NULL
                AND pnl_percent IS NOT NULL
            GROUP BY conviction_range
            ORDER BY tradingagents_conviction DESC
        """, self.db, params=[cutoff_date])
        
        if not conviction_correlation.empty:
            report['patterns']['conviction_correlation'] = conviction_correlation.to_dict('records')
        
        # Missed opportunities
        missed = pd.read_sql("""
            SELECT 
                reason_missed,
                AVG(potential_gain_percent) as avg_missed_gain,
                COUNT(*) as count
            FROM missed_opportunities
            WHERE date > ? AND would_have_been_profitable = 1
            GROUP BY reason_missed
        """, self.db, params=[cutoff_date])
        
        if not missed.empty:
            report['patterns']['missed_opportunities'] = missed.to_dict('records')
        
        return report
    
    def print_observation_summary(self):
        """Print a human-readable observation summary"""
        
        total_trades = self.db.execute("""
            SELECT COUNT(*) FROM observations WHERE executed = 1
        """).fetchone()[0]
        
        print(f"\n{'='*60}")
        print(f"OBSERVATION SUMMARY - {total_trades} Total Trades")
        print(f"{'='*60}")
        
        if total_trades < 10:
            print("Need at least 10 trades for meaningful observations")
            return
        
        # Recent performance
        recent = self.generate_observation_report(30)
        
        if 'patterns' in recent:
            print("\n📊 OBSERVED PATTERNS (Last 30 Days):")
            
            # Filter effectiveness
            if 'filter_effectiveness' in recent['patterns']:
                print("\n  Filter Effectiveness:")
                for row in recent['patterns']['filter_effectiveness']:
                    status = "Passed" if row['passed_filter'] else "Failed"
                    print(f"    {status} Filter: {row['win_rate']:.1%} win rate, "
                          f"{row['avg_return']:.2f}% avg return ({row['count']} trades)")
            
            # Decision accuracy
            if 'decision_accuracy' in recent['patterns']:
                print("\n  TradingAgents Decision Accuracy:")
                for row in recent['patterns']['decision_accuracy']:
                    print(f"    {row['tradingagents_decision']}: "
                          f"{row['accuracy']:.1%} accurate, "
                          f"{row['avg_return']:.2f}% avg return ({row['count']} trades)")
            
            # Conviction correlation
            if 'conviction_correlation' in recent['patterns']:
                print("\n  Conviction Score Correlation:")
                for row in recent['patterns']['conviction_correlation']:
                    print(f"    {row['conviction_range']}: "
                          f"{row['avg_return']:.2f}% avg return ({row['count']} trades)")
        
        print(f"\n{'='*60}")
        print("📝 No adjustments until 100+ trades completed")
        print(f"   Progress: {total_trades}/100")
        print(f"{'='*60}\n")


# Integration functions for main pipeline
def integrate_observer_with_pipeline(batch_processor, observer):
    """
    Monkey-patch the batch processor to record observations
    """
    original_process_batch = batch_processor.process_batch
    
    def observed_process_batch(candidates, regime_data, portfolio_context=None):
        # Record filter decisions
        for _, row in candidates.iterrows():
            observer.record_pipeline_decision(
                batch_id=f"batch_{datetime.now().strftime('%Y%m%d')}",
                symbol=row['symbol'],
                stage='filter',
                data={
                    'passed': True,
                    'score': row['score'],
                    'layer': 'final',
                    'rsi_2': row['rsi_2'],
                    'volume_ratio': row['volume_ratio']
                }
            )
        
        # Run original process
        result = original_process_batch(candidates, regime_data, portfolio_context)
        
        # Record TradingAgents and selection decisions
        # This would need to be added to the batch processor
        
        return result
    
    batch_processor.process_batch = observed_process_batch