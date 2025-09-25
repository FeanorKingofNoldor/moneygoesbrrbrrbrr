"""
Portfolio Constructor Module
Selects optimal portfolio from TradingAgents analysis results
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from langchain_openai import ChatOpenAI
import logging

logger = logging.getLogger(__name__)


class PortfolioConstructor:
    """
    Constructs optimal portfolio from TradingAgents batch analysis results
    """
    
    def __init__(self, db_connection, config: Optional[Dict] = None):
        """
        Initialize Portfolio Constructor
        
        Args:
            db_connection: SQLite database connection
            config: LLM configuration dictionary
        """
        self.db = db_connection
        
        # Default config for your local LLM
        if config is None:
            config = {
                'llm_provider': 'openai',
                'backend_url': 'http://localhost:8000/v1',  # Your Tesla V100 endpoint
                'model': 'gpt-4o-mini',  # Or your local model
                'temperature': 0.2,  # Lower for consistency
                'max_tokens': 3000
            }
        
        self.config = config
        self.llm = ChatOpenAI(
            model=config['model'],
            base_url=config['backend_url'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens']
        )
    
    def construct_portfolio(
        self,
        batch_id: str,
        max_positions: int = 5,
        portfolio_context: Optional[Dict] = None,
        regime_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Main method to construct optimal portfolio
        
        Args:
            batch_id: Unique identifier for this analysis batch
            max_positions: Maximum number of positions to select
            portfolio_context: Current portfolio state
            regime_data: Current market regime information
            
        Returns:
            Dictionary with selections and excluded candidates
        """
        logger.info(f"Constructing portfolio for batch {batch_id}")
        
        # Get all candidates from TradingAgents analysis
        all_candidates = self._fetch_analysis_results(batch_id)
        
        if not all_candidates:
            logger.warning(f"No analysis results found for batch {batch_id}")
            return {"selections": [], "excluded": []}
        
        # Separate BUY recommendations
        buy_candidates = [c for c in all_candidates if c['decision'] == 'BUY']
        other_candidates = [c for c in all_candidates if c['decision'] != 'BUY']
        
        logger.info(f"Found {len(buy_candidates)} BUY, {len(other_candidates)} HOLD/SELL")
        
        # If we have fewer BUYs than slots, take them all
        if len(buy_candidates) <= max_positions:
            selections = buy_candidates
            excluded = other_candidates
            reason = "All BUY signals selected (fewer than max positions)"
        else:
            # Apply quantitative pre-filtering
            filtered = self._apply_quantitative_filters(
                buy_candidates, 
                portfolio_context
            )
            
            # Use LLM for final selection
            selections, excluded = self._llm_selection(
                filtered,
                max_positions,
                portfolio_context,
                regime_data
            )
            
            # Add non-BUY candidates to excluded
            excluded.extend(other_candidates)
        
        # Calculate position sizes
        selections = self._calculate_position_sizes(
            selections,
            portfolio_context
        )
        
        # Save to database
        self._save_selections(batch_id, selections, excluded)
        
        # Return results
        return {
            "batch_id": batch_id,
            "selections": selections,
            "excluded": excluded,
            "timestamp": datetime.now().isoformat()
        }
    
    def _fetch_analysis_results(self, batch_id: str) -> List[Dict]:
        """Fetch all TradingAgents analysis results for a batch"""
        query = """
        SELECT 
            symbol,
            decision,
            conviction_score,
            position_size_pct,
            entry_price,
            stop_loss,
            target_price,
            expected_return,
            risk_reward_ratio,
            risk_score,
            regime,
            rsi_2,
            atr,
            volume_ratio,
            filter_score,
            sector,
            trader_analysis,
            risk_manager_analysis
        FROM tradingagents_analysis_results
        WHERE batch_id = ?
        ORDER BY conviction_score DESC
        """
        
        df = pd.read_sql(query, self.db, params=[batch_id])
        return df.to_dict('records')
    
    def _apply_quantitative_filters(
        self, 
        candidates: List[Dict],
        portfolio_context: Optional[Dict]
    ) -> List[Dict]:
        """Apply rule-based filtering before LLM selection"""
        df = pd.DataFrame(candidates)
        
        # Filter 1: Remove very low conviction (unless not enough candidates)
        if len(df) > 10:
            df = df[df['conviction_score'] >= 65]
        
        # Filter 2: Remove poor liquidity
        df = df[df['volume_ratio'] >= 1.0]
        
        # Filter 3: Sector diversification (max 2 per sector)
        sector_counts = {}
        filtered_indices = []
        
        for idx, row in df.sort_values('conviction_score', ascending=False).iterrows():
            sector = row.get('sector', 'Unknown')
            if sector_counts.get(sector, 0) < 2:
                filtered_indices.append(idx)
                sector_counts[sector] = sector_counts.get(sector, 0) + 1
        
        df_filtered = df.loc[filtered_indices]
        
        # Filter 4: Risk-reward balance
        df_filtered['risk_adjusted_score'] = (
            df_filtered['conviction_score'] * 
            df_filtered['risk_reward_ratio'] / 
            (df_filtered['risk_score'] + 1)
        )
        
        # Sort by risk-adjusted score
        df_filtered = df_filtered.sort_values('risk_adjusted_score', ascending=False)
        
        logger.info(f"Filtered {len(candidates)} to {len(df_filtered)} candidates")
        return df_filtered.to_dict('records')
    
    def _llm_selection(
        self,
        candidates: List[Dict],
        max_positions: int,
        portfolio_context: Optional[Dict],
        regime_data: Optional[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """Use LLM to make final selection"""
        
        if portfolio_context is None:
            portfolio_context = {}
        if regime_data is None:
            regime_data = {}
        
        # Prepare candidate summaries
        candidate_summaries = []
        for c in candidates[:15]:  # Limit to top 15 for LLM context
            summary = {
                "symbol": c['symbol'],
                "conviction": c['conviction_score'],
                "expected_return": round(c['expected_return'] * 100, 1),
                "risk_reward": round(c['risk_reward_ratio'], 2),
                "risk_score": c['risk_score'],
                "volume_ratio": round(c['volume_ratio'], 2),
                "sector": c.get('sector', 'Unknown'),
                "rsi": round(c['rsi_2'], 1)
            }
            candidate_summaries.append(summary)
        
        prompt = self._build_selection_prompt(
            candidate_summaries,
            max_positions,
            portfolio_context,
            regime_data
        )
        
        # Get LLM response
        messages = [
            {"role": "system", "content": "You are a portfolio construction specialist focused on risk-adjusted returns and diversification."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        # Parse response
        try:
            result = json.loads(response.content)
            selected_symbols = [s['symbol'] for s in result['selections']]
            
            # Separate selected and excluded
            selections = [c for c in candidates if c['symbol'] in selected_symbols]
            excluded = [c for c in candidates if c['symbol'] not in selected_symbols]
            
            # Add selection reasons
            for sel in selections:
                for res_sel in result['selections']:
                    if res_sel['symbol'] == sel['symbol']:
                        sel['selection_reason'] = res_sel.get('reason', '')
                        sel['rank'] = res_sel.get('rank', 0)
            
            for exc in excluded:
                for res_exc in result.get('excluded', []):
                    if res_exc['symbol'] == exc['symbol']:
                        exc['exclusion_reason'] = res_exc.get('reason', '')
            
            return selections, excluded
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Fallback to simple selection
            return candidates[:max_positions], candidates[max_positions:]
    
    def _build_selection_prompt(
        self,
        candidates: List[Dict],
        max_positions: int,
        portfolio_context: Dict,
        regime_data: Dict
    ) -> str:
        """Build the prompt for LLM selection"""
        
        prompt = f"""You are a portfolio construction specialist for position trading (3-10 day holds).

MARKET CONTEXT:
- Current Regime: {regime_data.get('regime', 'Unknown')} (CNN F&G: {regime_data.get('fear_greed_value', 'N/A')})
- VIX: {regime_data.get('vix', 'N/A')}
- Strategy: {regime_data.get('strategy', 'Unknown')}
- Expected Win Rate: {regime_data.get('expected_win_rate', 'N/A')}

PORTFOLIO CONTEXT:
- Available Capital: ${portfolio_context.get('cash_available', 100000):,.0f}
- Current Positions: {portfolio_context.get('total_positions', 0)}
- Current P&L: {portfolio_context.get('unrealized_pnl_pct', 0):+.1f}%

TASK: Select EXACTLY {max_positions} stocks from these {len(candidates)} BUY recommendations.

CANDIDATES (all passed TradingAgents analysis):
{json.dumps(candidates, indent=2)}

SELECTION CRITERIA (in order of importance):
1. Risk-Adjusted Return: Conviction × Expected Return ÷ Risk Score
2. Regime Fit: Prioritize stocks matching {regime_data.get('regime', 'current')} regime
3. Diversification: Maximum 2 stocks per sector
4. Liquidity: Higher volume ratios for easy entry/exit
5. Technical Setup: Consider RSI levels for entry timing

For {regime_data.get('regime', 'NEUTRAL')} regime:
- FEAR: Prioritize oversold bounces (low RSI, high conviction)
- GREED: Focus on momentum continuation (high volume, strong sectors)
- NEUTRAL: Balance between value and momentum

OUTPUT FORMAT (JSON only, no other text):
{{
    "selections": [
        {{
            "symbol": "AAPL",
            "rank": 1,
            "reason": "Highest risk-adjusted score with strong volume"
        }},
        ... (exactly {max_positions} stocks)
    ],
    "excluded": [
        {{
            "symbol": "MSFT",
            "reason": "Sector overlap with AAPL, lower conviction"
        }},
        ... (remaining stocks)
    ]
}}

Select exactly {max_positions} stocks. Be specific in exclusion reasons."""

        return prompt
    
    def _calculate_position_sizes(
        self,
        selections: List[Dict],
        portfolio_context: Optional[Dict]
    ) -> List[Dict]:
        """Calculate position sizes for selected stocks"""
        
        if not portfolio_context:
            portfolio_context = {'cash_available': 100000}
        
        available_capital = portfolio_context.get('cash_available', 100000)
        
        # Weight by conviction score
        total_conviction = sum(s['conviction_score'] for s in selections)
        
        for stock in selections:
            # Base allocation proportional to conviction
            weight = stock['conviction_score'] / total_conviction
            
            # Apply min/max constraints
            weight = max(0.15, min(0.35, weight))  # 15-35% per position
            
            stock['position_size_pct'] = round(weight * 100, 1)
            stock['position_size_dollars'] = round(available_capital * weight, 2)
            stock['shares'] = int(stock['position_size_dollars'] / stock['entry_price'])
        
        # Normalize to ensure adds to 100%
        total_pct = sum(s['position_size_pct'] for s in selections)
        if total_pct != 100:
            factor = 100 / total_pct
            for stock in selections:
                stock['position_size_pct'] = round(stock['position_size_pct'] * factor, 1)
        
        return selections
    
    def _save_selections(
        self,
        batch_id: str,
        selections: List[Dict],
        excluded: List[Dict]
    ):
        """Save portfolio selections to database"""
        
        # Save selections
        for i, stock in enumerate(selections, 1):
            self.db.execute("""
            INSERT OR REPLACE INTO portfolio_selections
            (batch_id, selection_date, symbol, rank, selected,
             position_size_pct, position_size_dollars, selection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                datetime.now().date(),
                stock['symbol'],
                stock.get('rank', i),
                1,  # selected = True
                stock['position_size_pct'],
                stock['position_size_dollars'],
                stock.get('selection_reason', '')
            ))
        
        # Save excluded with reasons
        excluded_data = json.dumps([
            {
                'symbol': e['symbol'],
                'conviction': e['conviction_score'],
                'reason': e.get('exclusion_reason', 'Not selected')
            }
            for e in excluded
        ])
        
        if selections:
            self.db.execute("""
            UPDATE portfolio_selections
            SET excluded_symbols = ?
            WHERE batch_id = ? AND symbol = ?
            """, (excluded_data, batch_id, selections[0]['symbol']))
        
        self.db.commit()
        logger.info(f"Saved {len(selections)} selections, {len(excluded)} excluded")