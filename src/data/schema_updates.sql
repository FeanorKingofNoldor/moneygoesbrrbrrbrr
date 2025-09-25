-- Run this to update your database schema
-- This adds tables for portfolio construction and performance tracking

-- Store complete TradingAgents analysis results
CREATE TABLE IF NOT EXISTS tradingagents_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    analysis_date DATE,
    
    -- Decision from TradingAgents
    decision TEXT,  -- BUY/SELL/HOLD
    conviction_score REAL,
    
    -- From Trader agent
    position_size_pct REAL,
    entry_price REAL,
    stop_loss REAL,
    target_price REAL,
    expected_return REAL,
    risk_reward_ratio REAL,
    time_horizon INTEGER,  -- days
    
    -- From Risk Manager
    risk_score REAL,
    risk_assessment TEXT,
    
    -- Context
    regime TEXT,
    fear_greed_value INTEGER,
    vix REAL,
    rsi_2 REAL,
    atr REAL,
    volume_ratio REAL,
    filter_score REAL,
    sector TEXT,
    
    -- Full text from agents
    trader_analysis TEXT,
    risk_manager_analysis TEXT,
    full_debate_history TEXT,
    
    -- Timestamps
    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(batch_id, symbol)
);

-- Final portfolio selections
CREATE TABLE IF NOT EXISTS portfolio_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    selection_date DATE,
    symbol TEXT NOT NULL,
    
    -- Selection details
    rank INTEGER,  -- 1-5
    selected BOOLEAN DEFAULT 1,
    position_size_pct REAL,
    position_size_dollars REAL,
    
    -- Why selected/excluded
    selection_reason TEXT,
    excluded_symbols TEXT,  -- JSON of what wasn't selected
    
    -- Context at selection
    available_capital REAL,
    total_positions INTEGER,
    
    selected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(batch_id, symbol)
);

-- Track actual performance (feedback loop)
CREATE TABLE IF NOT EXISTS position_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    
    -- Entry
    entry_date DATE,
    entry_price REAL,
    shares INTEGER,
    position_value REAL,
    
    -- Exit
    exit_date DATE,
    exit_price REAL,
    exit_reason TEXT,  -- 'target', 'stop_loss', 'time_limit', 'regime_change'
    holding_days INTEGER,
    
    -- Performance
    pnl_dollars REAL,
    pnl_percent REAL,
    max_gain_percent REAL,
    max_drawdown_percent REAL,
    
    -- Decision tracking
    was_selected BOOLEAN,  -- Did portfolio constructor select it?
    tradingagents_conviction REAL,
    actual_performance_category TEXT,  -- 'winner', 'loser', 'neutral'
    
    -- Market context during holding
    regime_at_entry TEXT,
    regime_at_exit TEXT,
    
    closed_at DATETIME,
    FOREIGN KEY (batch_id, symbol) REFERENCES tradingagents_analysis_results(batch_id, symbol)
);

-- Feedback analysis table
CREATE TABLE IF NOT EXISTS feedback_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_date DATE,
    
    -- What we selected
    selected_stocks_performance REAL,  -- Avg return of selected
    
    -- What we didn't select
    excluded_buys_performance REAL,  -- Avg return of excluded BUYs
    excluded_holds_performance REAL,  -- Avg return of HOLDs
    
    -- Regret metrics
    best_excluded_symbol TEXT,
    best_excluded_return REAL,
    worst_selected_symbol TEXT,
    worst_selected_return REAL,
    
    -- Decision quality
    selection_accuracy REAL,  -- % of correct selections
    tradingagents_accuracy REAL,  -- % of correct BUY/HOLD decisions
    
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_batch_id ON tradingagents_analysis_results(batch_id);
CREATE INDEX IF NOT EXISTS idx_symbol ON tradingagents_analysis_results(symbol);
CREATE INDEX IF NOT EXISTS idx_batch_symbol ON position_tracking(batch_id, symbol);