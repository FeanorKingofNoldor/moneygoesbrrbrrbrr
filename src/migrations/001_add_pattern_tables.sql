-- Pattern-Based Feedback System Database Migration
-- Run this to add pattern tracking tables to your ODIN database
-- Author: ODIN Pattern System
-- Version: 1.0.1 - Fixed to handle missing tables

-- ============================================
-- First, ensure base tables exist (if not already created)
-- ============================================

-- Create base tables if they don't exist
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
    
    -- Pattern fields (will be added below if table exists)
    -- pattern_id TEXT,
    -- pattern_components TEXT,
    
    -- Timestamps
    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(batch_id, symbol)
);

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
    exit_reason TEXT,
    holding_days INTEGER,
    
    -- Performance
    pnl_dollars REAL,
    pnl_percent REAL,
    max_gain_percent REAL,
    max_drawdown_percent REAL,
    
    -- Decision tracking
    was_selected BOOLEAN,
    executed BOOLEAN,
    tradingagents_decision TEXT,
    tradingagents_conviction REAL,
    actual_performance_category TEXT,
    
    -- Market context
    regime_at_entry TEXT,
    regime_at_exit TEXT,
    
    -- Pattern fields (will be added below)
    -- pattern_id TEXT,
    -- pattern_confidence TEXT,
    
    closed_at DATETIME,
    FOREIGN KEY (batch_id, symbol) REFERENCES tradingagents_analysis_results(batch_id, symbol)
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    observation_date DATE,
    symbol TEXT NOT NULL,
    
    -- Pipeline tracking
    passed_filter BOOLEAN,
    filter_score REAL,
    filter_layer TEXT,
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
    
    -- Outcomes
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
    outcome_category TEXT,
    was_correct_decision BOOLEAN,
    
    -- Pattern fields (will be added below)
    -- pattern_id TEXT,
    -- pattern_win_rate REAL,
    -- pattern_expectancy REAL,
    
    -- Metadata
    batch_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(symbol, entry_date)
);

-- ============================================
-- Table 1: Pattern Definitions and Performance
-- ============================================
CREATE TABLE IF NOT EXISTS trade_patterns (
    pattern_id TEXT PRIMARY KEY,
    
    -- Pattern Components
    strategy_type TEXT NOT NULL,
    market_regime TEXT NOT NULL,
    volume_profile TEXT NOT NULL,
    technical_setup TEXT NOT NULL,
    
    -- Performance Metrics (All-time)
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    avg_win_percent REAL DEFAULT 0.0,
    avg_loss_percent REAL DEFAULT 0.0,
    expectancy REAL DEFAULT 0.0,
    profit_factor REAL DEFAULT 0.0,
    
    -- Recent Performance (Rolling 20 trades)
    recent_trades TEXT,
    recent_win_rate REAL DEFAULT 0.0,
    recent_avg_return REAL DEFAULT 0.0,
    momentum_score REAL DEFAULT 0.0,
    
    -- Statistical Confidence
    confidence_level TEXT DEFAULT 'low',
    sharpe_ratio REAL,
    max_drawdown_percent REAL,
    
    -- Metadata
    first_seen_date DATE,
    last_traded_date DATE,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    
    CHECK (strategy_type IN ('mean_reversion', 'momentum', 'breakout', 'bounce')),
    CHECK (market_regime IN ('extreme_fear', 'fear', 'neutral', 'greed', 'extreme_greed')),
    CHECK (volume_profile IN ('low', 'normal', 'high', 'explosive')),
    CHECK (technical_setup IN ('oversold', 'neutral', 'overbought')),
    CHECK (confidence_level IN ('low', 'medium', 'high'))
);

CREATE INDEX IF NOT EXISTS idx_pattern_strategy ON trade_patterns(strategy_type);
CREATE INDEX IF NOT EXISTS idx_pattern_regime ON trade_patterns(market_regime);
CREATE INDEX IF NOT EXISTS idx_pattern_performance ON trade_patterns(expectancy DESC);
CREATE INDEX IF NOT EXISTS idx_pattern_confidence ON trade_patterns(confidence_level, win_rate);

-- ============================================
-- Table 2: Pattern History (Individual Trades)
-- ============================================
CREATE TABLE IF NOT EXISTS pattern_trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id TEXT NOT NULL,
    
    -- Trade Identifiers
    batch_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    
    -- Entry Context
    entry_date DATE NOT NULL,
    entry_price REAL NOT NULL,
    entry_rsi REAL,
    entry_volume_ratio REAL,
    entry_atr REAL,
    entry_vix REAL,
    entry_fear_greed INTEGER,
    
    -- Exit Information
    exit_date DATE,
    exit_price REAL,
    exit_reason TEXT,
    
    -- Performance
    holding_days INTEGER,
    pnl_percent REAL,
    max_gain_percent REAL,
    max_drawdown_percent REAL,
    
    -- Decision Tracking
    tradingagents_decision TEXT,
    tradingagents_conviction REAL,
    position_size_pct REAL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (pattern_id) REFERENCES trade_patterns(pattern_id)
    -- Removed FK to tradingagents_analysis_results as it might not have all records
);

CREATE INDEX IF NOT EXISTS idx_pattern_history_pattern ON pattern_trade_history(pattern_id);
CREATE INDEX IF NOT EXISTS idx_pattern_history_date ON pattern_trade_history(entry_date);
CREATE INDEX IF NOT EXISTS idx_pattern_history_symbol ON pattern_trade_history(symbol);

-- ============================================
-- Table 3: Pattern Regime Transitions
-- ============================================
CREATE TABLE IF NOT EXISTS pattern_regime_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transition_date DATE NOT NULL,
    
    from_regime TEXT NOT NULL,
    to_regime TEXT NOT NULL,
    
    patterns_broken TEXT,
    patterns_emerged TEXT,
    
    avg_performance_before REAL,
    avg_performance_after REAL,
    
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Table 4: Pattern Learning Log
-- ============================================
CREATE TABLE IF NOT EXISTS pattern_learning_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learning_date DATE NOT NULL,
    
    lesson_type TEXT NOT NULL,
    pattern_ids_affected TEXT,
    
    situation TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    
    injected_to_memories TEXT,
    
    trades_before_lesson INTEGER,
    avg_performance_before REAL,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Table 5: Pattern Correlations
-- ============================================
CREATE TABLE IF NOT EXISTS pattern_correlations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id_1 TEXT NOT NULL,
    pattern_id_2 TEXT NOT NULL,
    
    correlation_coefficient REAL,
    trades_together INTEGER,
    win_rate_together REAL,
    
    relationship_type TEXT,
    
    last_calculated DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (pattern_id_1) REFERENCES trade_patterns(pattern_id),
    FOREIGN KEY (pattern_id_2) REFERENCES trade_patterns(pattern_id),
    UNIQUE(pattern_id_1, pattern_id_2)
);

-- ============================================
-- Safe Column Additions (Check if columns exist first)
-- ============================================

-- SQLite doesn't support IF NOT EXISTS for columns, so we need to be careful
-- These will fail silently if columns already exist

-- Try to add pattern columns to tradingagents_analysis_results
ALTER TABLE tradingagents_analysis_results ADD COLUMN pattern_id TEXT;
ALTER TABLE tradingagents_analysis_results ADD COLUMN pattern_components TEXT;

-- Try to add pattern columns to position_tracking
ALTER TABLE position_tracking ADD COLUMN pattern_id TEXT;
ALTER TABLE position_tracking ADD COLUMN pattern_confidence TEXT;

-- Try to add pattern columns to observations
ALTER TABLE observations ADD COLUMN pattern_id TEXT;
ALTER TABLE observations ADD COLUMN pattern_win_rate REAL;
ALTER TABLE observations ADD COLUMN pattern_expectancy REAL;

-- ============================================
-- Views for Monitoring
-- ============================================

CREATE VIEW IF NOT EXISTS v_pattern_performance AS
SELECT 
    p.pattern_id,
    p.strategy_type,
    p.market_regime,
    p.volume_profile,
    p.technical_setup,
    p.total_trades,
    p.win_rate,
    p.recent_win_rate,
    p.expectancy,
    p.momentum_score,
    p.confidence_level,
    p.last_traded_date,
    CASE 
        WHEN p.recent_win_rate > p.win_rate * 1.1 THEN 'improving'
        WHEN p.recent_win_rate < p.win_rate * 0.9 THEN 'declining'
        ELSE 'stable'
    END as trend
FROM trade_patterns p
WHERE p.is_active = 1
ORDER BY p.expectancy DESC;

CREATE VIEW IF NOT EXISTS v_regime_patterns AS
SELECT 
    market_regime,
    strategy_type,
    COUNT(*) as pattern_count,
    AVG(win_rate) as avg_win_rate,
    AVG(expectancy) as avg_expectancy,
    SUM(total_trades) as total_trades
FROM trade_patterns
WHERE is_active = 1
GROUP BY market_regime, strategy_type
ORDER BY market_regime, avg_expectancy DESC;

-- ============================================
-- Migration Tracking
-- ============================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO schema_migrations (version, name) 
VALUES (1, 'add_pattern_tables');