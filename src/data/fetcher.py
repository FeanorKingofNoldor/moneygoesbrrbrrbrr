import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import time


class OdinDataFetcher:
    """
    Fetches and calculates metrics for S&P 500 universe
    """
    
    def __init__(self):
        self.sp500_sources = [
            "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv",
            "https://datahub.io/core/s-and-p-500-companies/r/constituents.csv",
        ]
        self._ticker_cache = None
        self._cache_time = None
        self._cache_duration = 86400  # 24 hours
        
    def get_universe(self) -> List[str]:
        """
        Get complete S&P 500 ticker list with caching
        """
        # Check cache
        if self._ticker_cache and self._cache_time:
            if time.time() - self._cache_time < self._cache_duration:
                print(f"Using cached ticker list ({len(self._ticker_cache)} tickers)")
                return self._ticker_cache
        
        # Try primary sources
        for url in self.sp500_sources:
            try:
                print(f"Fetching S&P 500 list from {url}")
                df = pd.read_csv(url)
                
                # Handle different column names
                symbol_col = 'Symbol' if 'Symbol' in df.columns else 'symbol'
                tickers = df[symbol_col].tolist()
                
                # Clean tickers (BRK.B -> BRK-B for Yahoo)
                tickers = [str(t).replace('.', '-') for t in tickers]
                
                # Cache the result
                self._ticker_cache = tickers
                self._cache_time = time.time()
                
                print(f"Successfully fetched {len(tickers)} S&P 500 tickers")
                return tickers
                
            except Exception as e:
                print(f"Failed to fetch from {url}: {e}")
                continue
        
        # Fallback to hardcoded top 100
        print("Using fallback ticker list")
        return self.get_fallback_tickers()
    
    def get_fallback_tickers(self) -> List[str]:
        """
        Hardcoded top S&P 500 companies by weight
        Updated Dec 2024
        """
        return [
            # Top 50 by market cap
            'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'GOOG', 
            'BRK-B', 'LLY', 'AVGO', 'JPM', 'TSLA', 'UNH', 'XOM', 
            'V', 'PG', 'MA', 'JNJ', 'HD', 'COST', 'ABBV', 'WMT',
            'CVX', 'MRK', 'KO', 'PEP', 'NFLX', 'ADBE', 'CRM', 'CSCO',
            'ACN', 'TMO', 'ABT', 'LIN', 'DIS', 'VZ', 'INTC', 'WFC',
            'INTU', 'TXN', 'AMGN', 'PM', 'IBM', 'SPGI', 'NOW', 'UNP',
            'QCOM', 'NKE', 'HON', 'RTX', 'NEE', 'BMY', 'ORCL', 'COP'
        ]
    
    def fetch_all_sp500(self) -> pd.DataFrame:
        """
        Fetch data for entire S&P 500 universe
        Processes in batches to avoid timeout
        """
        tickers = self.get_universe()
        print(f"\nFetching data for {len(tickers)} S&P 500 stocks...")
        
        # Process in batches
        batch_size = 50
        all_metrics = []
        failed_tickers = []
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(tickers) + batch_size - 1) // batch_size
            
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} stocks)")
            
            try:
                # Download batch
                data = yf.download(
                    batch,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    auto_adjust=True,
                    threads=True
                )
                
                if not data.empty:
                    # Calculate metrics for each ticker in batch
                    batch_metrics = self.calculate_metrics(data, batch)
                    if not batch_metrics.empty:
                        all_metrics.append(batch_metrics)
                    
                    # Add small delay to be nice to Yahoo
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Error processing batch {batch_num}: {e}")
                failed_tickers.extend(batch)
                continue
        
        if failed_tickers:
            print(f"Failed to fetch {len(failed_tickers)} tickers: {failed_tickers[:10]}...")
        
        if all_metrics:
            final_df = pd.concat(all_metrics, ignore_index=True)
            print(f"Successfully processed {len(final_df)} stocks")
            return final_df
        else:
            print("No data fetched")
            return pd.DataFrame()
    
    def calculate_metrics(self, data: pd.DataFrame, tickers: List[str]) -> pd.DataFrame:
        """
        Calculate technical indicators and metrics for multiple tickers
        """
        results = []
        
        for ticker in tickers:
            try:
                # Extract ticker data
                if len(tickers) == 1:
                    ticker_data = data
                else:
                    # Handle multi-ticker download structure
                    try:
                        ticker_data = data.xs(ticker, level=1, axis=1)
                    except:
                        continue
                
                if ticker_data.empty or len(ticker_data) < 20:
                    continue
                
                # Get latest values
                latest = ticker_data.iloc[-1]
                
                # Basic metrics
                metrics = {
                    'symbol': ticker,
                    'price': latest['Close'],
                    'volume': latest['Volume'],
                    'dollar_volume': latest['Close'] * latest['Volume'],
                    
                    # Simple RSI(2) calculation
                    'rsi_2': self._calculate_rsi(ticker_data['Close'], 2),
                    
                    # ATR for stop loss calculation
                    'atr': self._calculate_atr(ticker_data),
                    
                    # Moving averages
                    'sma_20': ticker_data['Close'].rolling(20).mean().iloc[-1],
                    'sma_50': ticker_data['Close'].rolling(50).mean().iloc[-1] if len(ticker_data) >= 50 else np.nan,
                    
                    # Volume metrics
                    'avg_volume_20': ticker_data['Volume'].rolling(20).mean().iloc[-1],
                    'volume_ratio': latest['Volume'] / ticker_data['Volume'].rolling(20).mean().iloc[-1],
                    
                    # Price change
                    'change_1d': (latest['Close'] - ticker_data['Close'].iloc[-2]) / ticker_data['Close'].iloc[-2] * 100,
                    
                    # Rough market cap (would need shares outstanding for real)
                    'market_cap': latest['Close'] * latest['Volume'] * 1000  # Placeholder
                }
                
                # Quality score (simplified)
                metrics['quality_score'] = self._calculate_quality_score(metrics)
                
                results.append(metrics)
                
            except Exception as e:
                # Skip failed tickers silently
                continue
        
        return pd.DataFrame(results)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 2) -> float:
        """Calculate RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            if loss.iloc[-1] == 0:
                return 100.0
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        except:
            return 50.0
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high = data['High']
            low = data['Low']
            close = data['Close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean().iloc[-1]
            
            return float(atr)
        except:
            return 0.0
    
    def _calculate_quality_score(self, metrics: Dict) -> float:
        """Simple quality score (0-1)"""
        score = 0
        
        # Volume consistency (not too high, not too low)
        if 0.5 < metrics['volume_ratio'] < 2.0:
            score += 0.33
        
        # Not oversold
        if metrics['rsi_2'] > 30:
            score += 0.33
        
        # Price above 20-day average (momentum)
        if metrics['price'] > metrics['sma_20']:
            score += 0.34
        
        return score