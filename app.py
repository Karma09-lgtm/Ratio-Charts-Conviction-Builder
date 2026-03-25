import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Universal Live Ratio Dashboard", layout="wide")
st.title("📊 Universal Live Ratio Dashboard (TradingView Edition)")
st.markdown("Build relative rotation charts with TradingView aesthetics and drawing tools.")

# --- STATE MANAGEMENT ---
if 'asset_dict' not in st.session_state:
    st.session_state.asset_dict = {
        "Broad Market 500 (Benchmark)": "BSE-500.BO", 
        "Nifty 50": "^NSEI",
        "Nifty Next 50": "^NN50",
        "Nifty Bank": "^NSEBANK",
        "Nifty Auto": "^CNXAUTO",
        "Nifty IT": "^CNXIT",
        "Nifty Metal": "^CNXMETAL",
        "Nifty Pharma": "^CNXPHARMA",
        "Nifty Energy": "^CNXENERGY",
        "Reliance Industries": "RELIANCE.NS",
        "Gold": "GC=F",
        "S&P 500": "^GSPC"
    }

# --- SIDEBAR: ADD CUSTOM CHARTS ---
st.sidebar.header("➕ Add New Asset")
with st.sidebar.form("add_ticker_form"):
    new_name = st.text_input("Asset Name (e.g., Tata Motors)")
    new_ticker = st.text_input("Yahoo Ticker (e.g., TATAMOTORS.NS)")
    submit_button = st.form_submit_button("Save to Dashboard")
    if submit_button and new_name and new_ticker:
        st.session_state.asset_dict[new_name] = new_ticker
        st.success(f"✅ {new_name} added successfully!")

st.sidebar.markdown("---")

# --- SIDEBAR: CHART CONTROLS ---
st.sidebar.header("Chart Settings")

selected_asset_name = st.sidebar.selectbox("1. Select Asset (Numerator)", list(st.session_state.asset_dict.keys()), index=1)
sector_ticker = st.session_state.asset_dict[selected_asset_name]

benchmark_name = st.sidebar.selectbox("2. Select Benchmark (Denominator)", list(st.session_state.asset_dict.keys()), index=0)
benchmark_ticker = st.session_state.asset_dict[benchmark_name]

chart_type = st.sidebar.selectbox("3. Chart Style", ("Candlestick", "Bar (OHLC)", "Hollow Candlestick", "Line"))
timeframe = st.sidebar.selectbox("4. Lookback Period", ("6 Months", "1 Year", "2 Years", "5 Years", "Max"), index=1)
interval_selection = st.sidebar.selectbox("5. Timeframe (Interval)", ("Daily", "Weekly", "Monthly"))
data_source = st.sidebar.radio("6. Live Data Feed", ("Yahoo Finance", "Investing.com (Unstable)"))

# --- SIDEBAR: TECHNICAL INDICATORS ---
st.sidebar.markdown("---")
st.sidebar.header("📈 Technical Indicators")
selected_overlays = st.sidebar.multiselect(
    "On-Chart Overlays",
    ["21 EMA", "50 SMA", "63 EMA", "100 SMA", "200 EMA", "30 WMA", "100 WMA", "200 WMA", "AVWAP"]
)

selected_oscillators = st.sidebar.multiselect(
    "Lower Pane Oscillators",
    ["RSI (14)", "MACD (12, 26, 9)"]
)

period_map = {"6 Months": "6mo", "1 Year": "1y", "2 Years": "2y", "5 Years": "5y", "Max": "max"}
interval_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
selected_period = period_map[timeframe]
selected_interval = interval_map[interval_selection]


# --- MATH HELPERS ---
def calculate_wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- DATA FETCHING ENGINES ---
@st.cache_data(ttl=900)
def fetch_yahoo_data(ticker, period, interval):
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty: return None
        if 'Volume' in data.columns:
            return data[['Open', 'High', 'Low', 'Close', 'Volume']]
        else:
            return data[['Open', 'High', 'Low', 'Close']]
    except Exception:
        return None

def get_data(ticker, period, interval, source):
    if source == "Yahoo Finance":
        return fetch_yahoo_data(ticker, period, interval)
    else:
        st.sidebar.error("Investing.com scrape blocked. Defaulting to Yahoo Data.")
        return fetch_yahoo_data(ticker, period, interval)

# --- CHART GENERATION & DATA EXPORT ---
st.markdown("---")
st.subheader(f"{selected_asset_name} / {benchmark_name} ({interval_selection})")

with st.spinner("Fetching data and generating TradingView visual..."):
    
    sector_data = get_data(sector_ticker, selected_period, selected_interval, data_source)
    benchmark_data = get_data(benchmark_ticker, selected_period, selected_interval, data_source)

    if sector_data is None and benchmark_data is None:
        st.error(f"⚠️ Failed to download data for both {sector_ticker} AND {benchmark_ticker}.")
    elif sector_data is None:
        st.error(f"⚠️ Failed to download data for Numerator: **{selected_asset_name} ({sector_ticker})**.")
    elif benchmark_data is None:
        st.error(f"⚠️ Failed to download data for Denominator: **{benchmark_name} ({benchmark_ticker})**.")
    
    elif sector_data is not None and benchmark_data is not None:
        if isinstance(sector_data.columns, pd.MultiIndex):
            sector_data.columns = sector_data.columns.get_level_values(0)
            benchmark_data.columns = benchmark_data.columns.get_level_values(0)

        df = pd.merge(sector_data, benchmark_data, left_index=True, right_index=True, suffixes=('_sec', '_bench'))
        df.dropna(subset=['Close_sec', 'Close_bench'], inplace=True)

        if not df.empty:
            df['Ratio_Open'] = df['Open_sec'] / df['Open_bench']
            df['Ratio_High'] = df['High_sec'] / df['High_bench']
            df['Ratio_Low'] = df['Low_sec'] / df['Low_bench']
            df['Ratio_Close'] = df['Close_sec'] / df['Close_bench']

            base_value = df['Ratio_Close'].iloc[0]
            for col in ['Ratio_Open', 'Ratio_High', 'Ratio_Low', 'Ratio_Close']:
                df[col] = (df[col] / base_value) * 100

            c = df['Ratio_Close']
            
            if "50 SMA" in selected_overlays: df['50 SMA'] = c.rolling(window=50).mean()
            if "100 SMA" in selected_overlays: df['100 SMA'] = c.rolling(window=100).mean()
            if "21 EMA" in selected_overlays: df['21 EMA'] = c.ewm(span=21, adjust=False).mean()
            if "63 EMA" in selected_overlays: df['63 EMA'] = c.ewm(span=63, adjust=False).mean()
            if "200 EMA" in selected_overlays: df['200 EMA'] = c.ewm(span=200, adjust=False).mean()
            if "30 WMA" in selected_overlays: df['30 WMA'] = calculate_wma(c, 30)
            if "100 WMA" in selected_overlays: df['100 WMA'] = calculate_wma(c, 100)
            if "200 WMA" in selected_overlays: df['200 WMA'] = calculate_wma(c, 200)

            if "AVWAP" in selected_overlays:
                if 'Volume_sec' in df.columns:
                    typical_price = (df['Ratio_High'] + df['Ratio_Low'] + df['Ratio_Close']) / 3
                    volume = df['Volume_sec']
                    df['Cum_Vol'] = volume.cumsum()
                    df['Cum_Vol_Price'] = (typical_price * volume).cumsum()
                    df['AVWAP'] = df['Cum_Vol_Price'] / df['Cum_Vol']

            if "RSI (14)" in selected_oscillators:
                df['RSI'] = calculate_rsi(c, 14)
                
            if "MACD (12, 26, 9)" in selected_oscillators:
                df['MACD_Line'] = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
                df['MACD_Signal'] = df['MACD_Line'].ewm(span=9, adjust=False).mean()
                df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']

            num_rows = 1
            row_heights = [0.6] if selected_oscillators else [1.0]
            
            if "RSI (14)" in selected_oscillators:
                num_rows += 1
                row_heights.append(0.2)
            if "MACD (12, 26, 9)" in selected_oscillators:
                num_rows += 1
                row_heights.append(0.2)

            total_height = sum(row_heights)
            row_heights = [h / total_height for h in row_heights]

            fig = make_subplots(
                rows=num_rows, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.03,
                row_heights=row_heights
            )

            # --- TRADINGVIEW COLORS ---
            TV_GREEN = '#089981'
            TV_RED = '#F23645'
            TV_BLUE = '#2962FF'
            TV_GRID = '#E0E3EB'

            # PLOT ROW 1: MAIN CHART
            if chart_type == "Line":
                fig.add_trace(go.Scatter(x=df.index, y=df['Ratio_Close'], mode='lines', name='Ratio', line=dict(color=TV_BLUE, width=2)), row=1, col=1)
            elif chart_type == "Bar (OHLC)":
                fig.add_trace(go.Ohlc(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], name='Ratio', increasing_line_color=TV_GREEN, decreasing_line_color=TV_RED), row=1, col=1)
            elif chart_type == "Hollow Candlestick":
                fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], name='Ratio', increasing_line_color=TV_GREEN, increasing_fillcolor='rgba(0,0,0,0)', decreasing_line_color=TV_RED, decreasing_fillcolor='rgba(0,0,0,0)'), row=1, col=1)
            else:
                fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], name='Ratio', increasing_line_color=TV_GREEN, increasing_fillcolor=TV_GREEN, decreasing_line_color=TV_RED, decreasing_fillcolor=TV_RED), row=1, col=1)

            colors = {"21 EMA": "#FF9800", "50 SMA": TV_BLUE, "63 EMA": "#E91E63", "100 SMA": "#9C27B0", "200 EMA": "#F44336", "30 WMA": "#4CAF50", "100 WMA": "#8BC34A", "200 WMA": "#FFEB3B", "AVWAP": "#000000"}
            for ind in selected_overlays:
                if ind in df.columns:
                    fig.add_trace(go.Scatter(x=df.index, y=df[ind], mode='lines', name=ind, line=dict(color=colors.get(ind, '#000000'), width=1.5), hoverinfo='y+name'), row=1, col=1)

            # PLOT ROW 2/3: OSCILLATORS
            current_row = 2
            if "RSI (14)" in selected_oscillators:
                fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI 14', line=dict(color='#7E57C2', width=1.5)), row=current_row, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color=TV_GRID, line_width=1.5, row=current_row, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color=TV_GRID, line_width=1.5, row=current_row, col=1)
                fig.update_yaxes(title_text="RSI", range=[0, 100], row=current_row, col=1)
                current_row += 1

            if "MACD (12, 26, 9)" in selected_oscillators:
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Line'], mode='lines', name='MACD', line=dict(color=TV_BLUE, width=1.5)), row=current_row, col=1)
                fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], mode='lines', name='Signal', line=dict(color='#FF9800', width=1.5)), row=current_row, col=1)
                hist_colors = ['rgba(8, 153, 129, 0.5)' if val >= 0 else 'rgba(242, 54, 69, 0.5)' for val in df['MACD_Hist']]
                fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Histogram', marker_color=hist_colors), row=current_row, col=1)
                fig.update_yaxes(title_text="MACD", row=current_row, col=1)

            # --- FORMAT LAYOUT (TRADINGVIEW STYLE) ---
            total_fig_height = 650 if num_rows == 1 else (800 if num_rows == 2 else 950)
            
            fig.update_layout(
                template="plotly_white", # Light theme
                plot_bgcolor='white',
                paper_bgcolor='white',
                xaxis_rangeslider_visible=False, 
                height=total_fig_height, 
                margin=dict(l=10, r=50, t=10, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                hovermode="x unified",
                # Enable structural drawing modes
                dragmode="pan" 
            )
            
            # Styling Axes like TradingView (Right side Y-axis, faint grid lines)
            fig.update_xaxes(
                showgrid=True, gridwidth=1, gridcolor=TV_GRID, zeroline=False,
                rangeslider_visible=False
            )
            fig.update_yaxes(
                showgrid=True, gridwidth=1, gridcolor=TV_GRID, zeroline=False,
                side="right", # Moves price to the right side
                tickformat=".2f"
            )
            
            # --- RENDER CHART WITH DRAWING CONFIG ---
            # This config injects the drawing tools into the modebar in the top right
            chart_config = {
                'modeBarButtonsToAdd': [
                    'drawline',       # For Trendlines and Horizontal Rays
                    'drawrect',       # For Box consolidation zones
                    'eraseshape'      # To delete drawings
                ],
                'displayModeBar': True,
                'displaylogo': False,
                'scrollZoom': True    # Allows scrolling to zoom like TradingView
            }

            st.plotly_chart(fig, use_container_width=True, config=chart_config)

            # --- EXPORT DATA SECTION ---
            st.markdown("---")
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.subheader("💾 Export Data")
                export_df = df.round(4) 
                csv_data = export_df.to_csv(index=True).encode('utf-8')
                
                safe_asset_name = selected_asset_name.replace(" ", "_")
                safe_bench_name = benchmark_name.replace(" ", "_")
                filename = f"{safe_asset_name}_vs_{safe_bench_name}_{interval_selection}.csv"
                
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv_data,
                    file_name=filename,
                    mime='text/csv',
                    use_container_width=True
                )

        else:
            st.error("⚠️ Data mismatch. The dates for these two assets do not align.")
