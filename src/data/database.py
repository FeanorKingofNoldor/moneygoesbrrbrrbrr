"""
Database setup for ODIN
SQLite for development, PostgreSQL for production
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Optional
from config.settings import DATABASE_PATH


class OdinDatabase:
    """
    Simple database interface
    Using SQLite for now (auto-creates file)
    """
    
    def __init__(self, db_path=None):
        """Initialize database connection"""
        if db_path:
            self.db_path = db_path
        else:
            # Try multiple locations
            if os.path.exists("odin.db"):
                self.db_path = "odin.db"
            elif os.path.exists("../odin.db"):
                self.db_path = "../odin.db"
            else:
                # Create in current directory
                self.db_path = "odin.db"
        
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        """
        Create tables if they don't exist
        """
        self.conn = sqlite3.connect(self.db_path)
        
        # Drop and recreate for clean schema (development only)
        self.conn.execute("DROP TABLE IF EXISTS stock_metrics")
        
        # Stock metrics table - matching fetcher output
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_metrics (
            symbol TEXT,
            timestamp DATETIME,
            price REAL,
            volume INTEGER,
            dollar_volume REAL,
            market_cap REAL,
            
            -- Technical indicators from fetcher
            rsi_2 REAL,
            atr REAL,
            sma_20 REAL,
            sma_50 REAL,
            
            -- Volume metrics
            avg_volume_20 REAL,
            volume_ratio REAL,
            
            -- Other metrics
            change_1d REAL,
            quality_score REAL,
            
            PRIMARY KEY (symbol, timestamp)
        )
        """)
        
        # Regime history
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS regime_history (
            timestamp DATETIME PRIMARY KEY,
            regime TEXT,
            fear_greed_value INTEGER,
            vix REAL,
            strategy TEXT,
            expected_win_rate REAL
        )
        """)
        
        # Filter results (for tracking what we selected)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS filter_results (
            timestamp DATETIME,
            symbol TEXT,
            score REAL,
            regime TEXT,
            selected BOOLEAN,
            PRIMARY KEY (timestamp, symbol)
        )
        """)
        
        self.conn.commit()
    
    def insert_stock_metrics(self, df: pd.DataFrame):
        """
        Bulk insert stock metrics
        """
        # Only keep columns that exist in our schema
        columns_to_keep = [
            'symbol', 'price', 'volume', 'dollar_volume', 'market_cap',
            'rsi_2', 'atr', 'sma_20', 'sma_50', 'avg_volume_20',
            'volume_ratio', 'change_1d', 'quality_score'
        ]
        
        # Filter to only columns that exist
        df_filtered = df[[col for col in columns_to_keep if col in df.columns]]
        df_filtered['timestamp'] = datetime.now()
        
        df_filtered.to_sql('stock_metrics', self.conn, if_exists='append', index=False)
        self.conn.commit()
    
    def get_latest_metrics(self) -> pd.DataFrame:
        """
        Get most recent stock metrics for filtering
        """
        query = """
        SELECT * FROM stock_metrics
        WHERE timestamp = (SELECT MAX(timestamp) FROM stock_metrics)
        """
        return pd.read_sql(query, self.conn)
    
    def log_regime(self, regime_data: Dict):
        """
        Log regime for tracking
        """
        self.conn.execute("""
        INSERT INTO regime_history 
        (timestamp, regime, fear_greed_value, vix, strategy, expected_win_rate)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(),
            regime_data['regime'],
            regime_data['fear_greed_value'],
            regime_data['vix'],
            regime_data['strategy'],
            regime_data['expected_win_rate']
        ))
        self.conn.commit()
    
    def close(self):
        """Clean up connection"""
        if self.conn:
            self.conn.close()