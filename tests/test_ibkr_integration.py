#!/usr/bin/env python3
"""
Test script for ODIN with IBKR portfolio integration
"""

from src.data.database import OdinDatabase
from src.tradingagents.wrapper import OdinTradingAgentsWrapper


def test_ibkr_integration():
    """
    Test the complete ODIN system with IBKR portfolio integration
    """
    print("Testing ODIN with IBKR Integration")
    print("=" * 50)
    
    # Initialize database
    db = OdinDatabase()
    
    # Test 1: Paper trading setup (port 4002)
    print("\n1. Testing Paper Trading Setup...")
    try:
        wrapper_paper = OdinTradingAgentsWrapper(
            odin_database=db,
            use_ibkr=True,
            ibkr_port=4002  # Paper trading
        )
        
        # Get portfolio summary
        portfolio_data = wrapper_paper.get_portfolio_summary()
        print("✓ Paper trading setup successful")
        
    except Exception as e:
        print(f"⚠ Paper trading setup failed: {e}")
        print("Make sure IB Gateway is running on port 4002 (paper trading)")
        
        # Fallback to non-IBKR mode
        print("\nFalling back to database-only mode...")
        wrapper_paper = OdinTradingAgentsWrapper(
            odin_database=db,
            use_ibkr=False
        )
        portfolio_data = wrapper_paper.get_portfolio_summary()
    
    # Test 2: Analyze a stock with portfolio context
    print("\n2. Testing Stock Analysis with Portfolio Context...")
    try:
        result = wrapper_paper.analyze_stock("AAPL", "2024-12-19")
        
        print(f"Analysis Result for {result['symbol']}:")
        print(f"  Decision: {result['decision']}")
        print(f"  Market Regime: {result['regime_context']['regime']}")
        print(f"  Portfolio Positions: {result['portfolio_context']['total_positions']}")
        print(f"  Data Source: {result['portfolio_context'].get('data_source', 'Unknown')}")
        
        print("✓ Stock analysis with context successful")
        
    except Exception as e:
        print(f"⚠ Stock analysis failed: {e}")
    
    # Test 3: Live trading setup (only if you want to test with real money)
    print("\n3. Live Trading Setup (Optional - Commented Out)")
    print("# Uncomment to test live trading (port 4001)")
    print("# wrapper_live = OdinTradingAgentsWrapper(db, use_ibkr=True, ibkr_port=4001)")


def test_portfolio_data_flow():
    """
    Test the data flow from IBKR through ODIN to TradingAgents
    """
    print("\n" + "="*60)
    print("TESTING PORTFOLIO DATA FLOW")
    print("="*60)
    
    db = OdinDatabase()
    
    # Create wrapper with detailed logging
    wrapper = OdinTradingAgentsWrapper(db, use_ibkr=True, ibkr_port=4002)
    
    # Step 1: Check regime detection
    print("\nStep 1: Market Regime Detection")
    regime = wrapper.regime_detector.get_current_regime()
    print(f"  Regime: {regime['regime']}")
    print(f"  Fear & Greed: {regime['fear_greed_value']}")
    print(f"  Strategy: {regime['strategy']}")
    
    # Step 2: Check portfolio context
    print("\nStep 2: Portfolio Context")
    portfolio = wrapper.portfolio_provider.get_portfolio_context()
    print(f"  Data Source: {portfolio.get('data_source', 'Unknown')}")
    print(f"  Positions: {portfolio.get('total_positions', 0)}")
    print(f"  Cash: ${portfolio.get('cash_available', 0):,.2f}")
    
    if portfolio.get('current_positions'):
        print("  Current Positions:")
        for pos in portfolio['current_positions'][:3]:
            print(f"    {pos['symbol']}: {pos.get('shares', 0):,.0f} shares")
    
    # Step 3: Test enhanced analysis
    print("\nStep 3: Enhanced TradingAgents Analysis")
    print("Context that will be provided to TradingAgents:")
    print("-" * 40)
    
    # Show the enhanced context that would be passed
    enhanced_context = f"""
Market Regime: {regime['regime']} 
Portfolio: {portfolio.get('total_positions', 0)} positions
Strategy Focus: {regime['strategy']}
Available Cash: ${portfolio.get('cash_available', 0):,.0f}
"""
    print(enhanced_context)
    
    return wrapper


def setup_ibkr_connection():
    """
    Helper to set up IBKR connection
    """
    print("\nIBKR Connection Setup Guide:")
    print("=" * 40)
    print("1. Download and install IB Gateway or TWS")
    print("2. Configure API settings:")
    print("   - Enable ActiveX and Socket Clients")
    print("   - Socket port: 4002 (paper) or 4001 (live)")
    print("   - Master API client ID: Leave blank")
    print("   - Read-Only API: No (for trading)")
    print("3. Start IB Gateway with paper trading account")
    print("4. Run this test script")
    print("\nPorts:")
    print("  4002 = Paper Trading")
    print("  4001 = Live Trading")
    print("\nFor first time setup, always start with paper trading!")


if __name__ == "__main__":
    # Show setup guide
    setup_ibkr_connection()
    
    # Run tests
    test_ibkr_integration()
    
    # Test detailed data flow
    try:
        test_wrapper = test_portfolio_data_flow()
        
        # Optional: Analyze a specific stock
        print("\n" + "="*60)
        print("OPTIONAL: Full Analysis Test")
        print("="*60)
        
        choice = input("\nRun full TradingAgents analysis? (y/n): ")
        if choice.lower() == 'y':
            symbol = input("Enter stock symbol (default AAPL): ").strip() or "AAPL"
            
            print(f"\nAnalyzing {symbol} with full ODIN context...")
            result = test_wrapper.analyze_stock(symbol)
            
            print(f"\nFinal Result:")
            print(f"  Symbol: {result['symbol']}")
            print(f"  Decision: {result['decision']}")
            print(f"  Context Source: {result['portfolio_context'].get('data_source')}")
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed: {e}")
        print("Check that IB Gateway is running and configured correctly")
    
    print("\nTest complete!")