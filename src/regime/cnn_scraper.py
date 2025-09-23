"""
Custom CNN Fear & Greed Index scraper
Since the package doesn't support Python 3.13
"""

import requests
import json
from typing import Dict


class CNNFearGreedIndex:
    """
    Fetches CNN Fear & Greed Index without the broken package
    """
    
    def __init__(self):
        self.url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        
    def get_fear_and_greed_index(self) -> Dict:
        """
        Fetch the Fear & Greed data from CNN
        """
        try:
            # Add headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://www.cnn.com/',
            }
            
            response = requests.get(self.url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # The API structure: data -> fear_and_greed -> score
                if 'fear_and_greed' in data:
                    fg_data = data['fear_and_greed']
                    current_value = fg_data.get('score', 50)
                    
                    # Debug print to see what we got
                    print(f"Successfully fetched CNN F&G: {current_value}")
                else:
                    # Print what keys we actually got
                    print(f"Unexpected API structure. Keys: {list(data.keys())}")
                    # Try direct score access
                    current_value = data.get('score', 50)
                
                # Convert to integer
                current_value = round(float(current_value))
                
                # Determine text label
                if current_value < 25:
                    text = "Extreme Fear"
                elif current_value < 45:
                    text = "Fear"
                elif current_value < 55:
                    text = "Neutral"
                elif current_value < 75:
                    text = "Greed"
                else:
                    text = "Extreme Greed"
                
                return {
                    'value': current_value,
                    'text': text
                }
            else:
                print(f"API returned status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        # Fallback based on VIX if we can't get CNN
        print("CNN API failed, using VIX-based estimate")
        try:
            import yfinance as yf
            vix = yf.Ticker("^VIX").info['regularMarketPrice']
            
            if vix < 15:
                return {'value': 65, 'text': 'Greed'}
            elif vix < 20:
                return {'value': 50, 'text': 'Neutral'}
            elif vix < 30:
                return {'value': 35, 'text': 'Fear'}
            else:
                return {'value': 15, 'text': 'Extreme Fear'}
        except:
            return {'value': 50, 'text': 'Neutral'}
    
    def get_complete_report(self):
        """Compatibility method"""
        data = self.get_fear_and_greed_index()
        return {'fear_greed': data}