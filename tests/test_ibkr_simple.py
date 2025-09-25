#!/usr/bin/env python3
"""
Simple test for IBKR connection
Run this first to verify your IBKR setup
"""

from src.brokers.ibkr_connector import IBKRPortfolioConnector, test_ibkr_connection


def quick_test():
    """Quick test of IBKR connection"""
    print("IBKR Quick Connection Test")
    print("=" * 30)
    
    # Test paper trading connection
    print("Testing Paper Trading (port 4002)...")
    connector = IBKRPortfolioConnector(port=4002)
    
    if connector.connect_sync():
        print("✓ Connected successfully!")
        
        # Get basic portfolio info
        data = connector.get_portfolio_data_sync()
        
        print(f"\nAccount Summary:")
        print(f"  Cash: ${data['summary']['total_cash']:,.2f}")
        print(f"  Portfolio: ${data['summary']['portfolio_value']:,.2f}")
        print(f"  Total: ${data['summary']['net_liquidation']:,.2f}")
        print(f"  Positions: {data['summary']['total_positions']}")
        
        if data['positions']:
            print(f"\nPositions:")
            for pos in data['positions'][:5]:  # Show first 5
                print(f"  {pos['symbol']}: {pos['position']:,.0f} @ ${pos['market_price']:.2f}")
        
        print(f"\n✓ Portfolio data retrieved successfully!")
        return True
    else:
        print("✗ Failed to connect")
        print("\nTroubleshooting:")
        print("1. Is IB Gateway running?")
        print("2. Is it configured for API access?")
        print("3. Is port 4002 correct for paper trading?")
        print("4. Are you logged into your paper trading account?")
        return False


if __name__ == "__main__":
    # Run the quick test
    success = quick_test()
    
    if success:
        print("\n🎉 IBKR integration is working!")
        print("You can now run the full ODIN test with:")
        print("python test_ibkr_integration.py")
    else:
        print("\n❌ IBKR setup needs attention")
        print("\nSetup Steps:")
        print("1. Download IB Gateway from Interactive Brokers")
        print("2. Login with your paper trading account")
        print("3. Go to Configure -> Settings -> API -> Settings")
        print("4. Check 'Enable ActiveX and Socket Clients'")
        print("5. Set Socket port to 4002")
        print("6. Click OK and restart IB Gateway")
        print("7. Run this test again")