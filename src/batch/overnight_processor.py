"""
Overnight batch processor for ODIN
Runs complete analysis pipeline when market is closed
"""

import time
import pandas as pd
from datetime import datetime, time as dt_time
import schedule
from typing import List, Dict

from src.regime.detector import OdinRegimeDetector
from src.data.database import OdinDatabase
from src.data.fetcher import OdinDataFetcher
from src.filtering.filter import OdinFilter


class OvernightProcessor:
    """
    Handles overnight batch processing
    Designed to run 8 PM - 5 AM
    """
    
    def __init__(self):
        self.db = OdinDatabase()
        self.regime_detector = OdinRegimeDetector()
        self.fetcher = OdinDataFetcher()
        self.filter = OdinFilter(self.db)
        
    def run_overnight_batch(self):
        """
        Complete overnight processing pipeline
        """
        start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"ODIN OVERNIGHT BATCH - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        try:
            # Step 1: Detect current regime
            print("\n[1/4] Detecting Market Regime...")
            regime = self.regime_detector.get_current_regime()
            print(f"   Regime: {regime['regime'].upper()}")
            print(f"   Strategy: {regime['strategy']}")
            print(f"   Expected Win Rate: {regime['expected_win_rate']:.1%}")
            self.db.log_regime(regime)
            
            # Step 2: Fetch all S&P 500 data
            print("\n[2/4] Fetching S&P 500 Data...")
            metrics = self.fetcher.fetch_all_sp500()
            
            if metrics.empty:
                print("   ⚠ No data fetched - aborting")
                return None
                
            print(f"   ✓ Fetched {len(metrics)} stocks")
            self.db.insert_stock_metrics(metrics)
            
            # Step 3: Run filtering
            print("\n[3/4] Running 3-Layer Filter...")
            candidates = self.filter.run_full_filter(regime)
            
            if candidates.empty:
                print("   ⚠ No candidates selected")
                return None
            
            # Step 4: Prepare for TradingAgents
            print(f"\n[4/4] Preparing {len(candidates)} candidates for TradingAgents...")
            self.prepare_tradingagents_queue(candidates, regime)
            
            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"\n{'='*60}")
            print(f"BATCH COMPLETE - Duration: {duration:.1f} seconds")
            print(f"Candidates ready for TradingAgents analysis")
            print(f"{'='*60}\n")
            
            return candidates
            
        except Exception as e:
            print(f"\n❌ Batch failed: {e}")
            return None
    
    def prepare_tradingagents_queue(self, candidates: pd.DataFrame, regime: Dict):
        """
        Prepare candidates for TradingAgents analysis
        Save to queue table for processing
        """
        # Create queue table if not exists
        self.db.conn.execute("""
        CREATE TABLE IF NOT EXISTS tradingagents_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            queued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            regime TEXT,
            filter_score REAL,
            rsi_2 REAL,
            volume_ratio REAL,
            price REAL,
            atr REAL,
            processed BOOLEAN DEFAULT 0,
            conviction_score REAL,
            recommendation TEXT,
            processed_at DATETIME
        )
        """)
        
        # Clear old queue
        self.db.conn.execute("DELETE FROM tradingagents_queue WHERE processed = 0")
        
        # Insert new candidates
        for _, row in candidates.iterrows():
            self.db.conn.execute("""
            INSERT INTO tradingagents_queue 
            (symbol, regime, filter_score, rsi_2, volume_ratio, price, atr)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row['symbol'],
                regime['regime'],
                row['score'],
                row['rsi_2'],
                row['volume_ratio'],
                row['price'],
                row['atr']
            ))
        
        self.db.conn.commit()
        print(f"   ✓ {len(candidates)} stocks queued for TradingAgents")
        
    def is_market_closed(self) -> bool:
        """
        Check if market is closed
        NYSE hours: 9:30 AM - 4:00 PM ET
        """
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        # Weekend
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            return True
        
        # Before 9:30 AM or after 4:00 PM ET (adjust for your timezone)
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        
        return current_time < market_open or current_time > market_close
    
    def schedule_overnight_runs(self):
        """
        Schedule overnight batch to run at specific times
        """
        # Run at 8 PM for overnight processing
        schedule.every().day.at("20:00").do(self.run_overnight_batch)
        
        # Optional: Run again at 2 AM for updated data
        schedule.every().day.at("02:00").do(self.run_overnight_batch)
        
        # Pre-market preparation at 8 AM
        schedule.every().day.at("08:00").do(self.prepare_morning_trades)
        
        print("Overnight processor scheduled:")
        print("  - 8:00 PM: Full S&P 500 analysis")
        print("  - 2:00 AM: Update analysis")
        print("  - 8:00 AM: Prepare morning trades")
    
    def prepare_morning_trades(self):
        """
        Review TradingAgents results and prepare execution list
        """
        print("\n" + "="*60)
        print("MORNING TRADE PREPARATION")
        print("="*60)
        
        # Get processed candidates with conviction scores
        query = """
        SELECT * FROM tradingagents_queue 
        WHERE processed = 1 AND conviction_score > 70
        ORDER BY conviction_score DESC
        """
        
        df = pd.read_sql(query, self.db.conn)
        
        if df.empty:
            print("No high-conviction trades for today")
            return
        
        print(f"\nHigh Conviction Trades (>70):")
        for _, row in df.iterrows():
            print(f"  {row['symbol']}: {row['conviction_score']:.1f} - {row['recommendation']}")
        
        # Save to execution table
        self.db.conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_queue (
            symbol TEXT PRIMARY KEY,
            action TEXT,
            conviction REAL,
            target_shares INTEGER,
            limit_price REAL,
            stop_loss REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Clear and populate
        self.db.conn.execute("DELETE FROM execution_queue")
        
        for _, row in df.iterrows():
            # Calculate stop loss (2.5x ATR)
            stop_loss = row['price'] - (2.5 * row['atr'])
            
            self.db.conn.execute("""
            INSERT INTO execution_queue 
            (symbol, action, conviction, stop_loss)
            VALUES (?, ?, ?, ?)
            """, (
                row['symbol'],
                row['recommendation'],
                row['conviction_score'],
                stop_loss
            ))
        
        self.db.conn.commit()
        print(f"\n✓ {len(df)} trades ready for execution at market open")


# Main execution
if __name__ == "__main__":
    processor = OvernightProcessor()
    
    # For testing, run immediately
    processor.run_overnight_batch()
    
    # For production, use scheduler
    # processor.schedule_overnight_runs()
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)