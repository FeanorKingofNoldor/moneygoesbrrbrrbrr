class PortfolioContextProvider:
    def __init__(self, odin_database):
        self.db = odin_database
        
    def get_portfolio_context(self):
        """Get current portfolio state for TradingAgents"""
        
        # Query current positions from your ODIN database
        positions = self.db.get_current_positions()
        
        return {
            'total_positions': len(positions),
            'available_capital': self.db.get_available_cash(),
            'total_portfolio_value': self.db.get_total_value(),
            'sector_exposure': self.db.get_sector_breakdown(),
            'current_risk': self.db.calculate_total_risk(),
            'recent_pnl': self.db.get_recent_performance()
        }