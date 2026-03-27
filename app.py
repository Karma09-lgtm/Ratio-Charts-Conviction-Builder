import yfinance as yf
import pandas as pd
import time

# Re-using our test universes from Phase 1
US_TICKERS = ['AAPL', 'MSFT', 'NVDA', 'META', 'AMZN', 'GOOGL', 'TSLA', 'JPM', 'V', 'WMT']
INDIA_TICKERS = ['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS', 'SBI.NS']

def calculate_live_breadth(baseline_csv, tickers, market_name):
    """
    Loads historical baselines, fetches the live price, and calculates current market breadth.
    """
    print(f"[{market_name}] Loading baselines and fetching live prices...")
    
    # 1. Load the heavy lifting from Phase 1
    try:
        baseline_df = pd.read_csv(baseline_csv, index_col=0)
    except FileNotFoundError:
        print(f"Error: {baseline_csv} not found. Please run Phase 1 first.")
        return None

    # 2. Fetch LIVE prices (Lightweight call)
    # Using interval="1m" gets us the most recent intraday price point quickly
    live_data = yf.download(tickers, period="1d", interval="1m", progress=False)
    
    if len(tickers) > 1:
        # Get the very last row (the latest minute's closing price)
        live_prices = live_data['Close'].iloc[-1] 
    else:
        live_prices = pd.Series({tickers[0]: live_data['Close'].iloc[-1]})
        
    # 3. Combine live prices with our historical baseline
    live_df = baseline_df.copy()
    live_df['Live_Price'] = live_prices

    # 4. Calculate Live Breadth Metrics (The Aggregates)
    # We use .mean() * 100 to quickly get the percentage of True values
    pct_above_50 = (live_df['Live_Price'] > live_df['50_SMA']).mean() * 100
    pct_above_150 = (live_df['Live_Price'] > live_df['150_SMA']).mean() * 100
    pct_above_200 = (live_df['Live_Price'] > live_df['200_SMA']).mean() * 100

    # Live Stage Analysis
    pct_stage_2 = ((live_df['Live_Price'] > live_df['30W_EMA']) & 
                   (live_df['30W_EMA'] > live_df['30W_EMA_1M_Ago'])).mean() * 100
                    
    pct_stage_4 = ((live_df['Live_Price'] < live_df['30W_EMA']) & 
                   (live_df['30W_EMA'] < live_df['30W_EMA_1M_Ago'])).mean() * 100

    # 5. Package the results for the UI
    metrics = {
        "Market": market_name,
        "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "% > 50 SMA": round(pct_above_50, 2),
        "% > 150 SMA": round(pct_above_150, 2),
        "% > 200 SMA": round(pct_above_200, 2),
        "% in Stage 2": round(pct_stage_2, 2),
        "% in Stage 4": round(pct_stage_4, 2)
    }
    
    return metrics

def run_live_loop():
    """Simulates a live polling environment updating every 60 seconds."""
    print("Starting Live Breadth Monitor. Press Ctrl+C to stop.\n" + "-"*50)
    
    try:
        while True:
            # Calculate for US
            us_metrics = calculate_live_breadth("us_breadth_baseline.csv", US_TICKERS, "US Market")
            
            # Calculate for India
            india_metrics = calculate_live_breadth("india_breadth_baseline.csv", INDIA_TICKERS, "Indian Market")
            
            # Print to terminal (In Phase 3, this data goes to Streamlit instead)
            if us_metrics and india_metrics:
                print("\n--- LIVE BREADTH UPDATE ---")
                print(f"Time: {us_metrics['Timestamp']}")
                print(f"US Market    | > 200 SMA: {us_metrics['% > 200 SMA']}% | Stage 2: {us_metrics['% in Stage 2']}% | Stage 4: {us_metrics['% in Stage 4']}%")
                print(f"India Market | > 200 SMA: {india_metrics['% > 200 SMA']}% | Stage 2: {india_metrics['% in Stage 2']}% | Stage 4: {india_metrics['% in Stage 4']}%")
                print("-" * 25)
            
            # Wait 60 seconds before polling again to respect API rate limits
            print("Waiting 60 seconds for next update...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\nLive Monitor stopped by user.")

if __name__ == "__main__":
    run_live_loop()
