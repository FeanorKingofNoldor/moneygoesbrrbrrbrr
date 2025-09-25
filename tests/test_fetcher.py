from src.data.fetcher import OdinDataFetcher

# Test the fetcher
fetcher = OdinDataFetcher()

# Get universe
tickers = fetcher.get_universe()
print(f"Got {len(tickers)} tickers")

# Fetch data for first 10
test_tickers = tickers[:10]
data = fetcher.fetch_bulk_data(test_tickers)

if not data.empty:
    metrics = fetcher.calculate_metrics(data, test_tickers)
    print("\nSample metrics:")
    print(metrics[['symbol', 'price', 'rsi_2', 'volume_ratio', 'quality_score']].head())