import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Universal Live Ratio Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Universal Live Ratio Dashboard (Pro)")

# --- STATE MANAGEMENT ---
if 'asset_dict' not in st.session_state:
    st.session_state.asset_dict = {
        "Broad Market 500": "BSE-500.BO", 
        "Nifty 50": "^NSEI",
        "Nifty Bank": "^NSEBANK",
        "Nifty IT": "^CNXIT",
        "Nifty Pharma": "^CNXPHARMA",
        "Nifty Auto": "^CNXAUTO",
        "Nifty Metal": "^CNXMETAL",
        "Nifty Energy": "^CNXENERGY",
        "Gold": "GC=F",
        "S&P 500": "^GSPC"
    }

# --- SIDEBAR CONTROLS ---
st.sidebar.header("➕ Add New Asset")
with st.sidebar.form("add_ticker_form"):
    new_name = st.text_input("Asset Name (e.g., Tata Motors)")
    new_ticker = st.text_input("Yahoo Ticker (e.g., TATAMOTORS.NS)")
    submit_button = st.form_submit_button("Save to Dashboard")
    if submit_button and new_name and new_ticker:
        st.session_state.asset_dict[new_name] = new_ticker
        st.sidebar.success(f"✅ {new_name} added!")

st.sidebar.markdown("---")
st.sidebar.header("Chart Settings (Dynamic Screen)")

selected_asset_name = st.sidebar.selectbox("1. Select Asset (Numerator)", list(st.session_state.asset_dict.keys()), index=2)
benchmark_name = st.sidebar.selectbox("2. Select Benchmark (Denominator)", list(st.session_state.asset_dict.keys()), index=0)

chart_type = st.sidebar.selectbox("3. Chart Style", ("Candlestick", "Bar (OHLC)", "Hollow Candlestick", "Line"))
timeframe = st.sidebar.selectbox("4. Lookback Period", ("1 Month", "6 Months", "1 Year", "2 Years", "5 Years", "Max"), index=1)
interval_selection = st.sidebar.selectbox("5. Timeframe (Interval)", ("Daily", "Weekly", "Monthly"))

st.sidebar.markdown("---")
st.sidebar.header("📈 Technical Indicators")
selected_overlays = st.sidebar.multiselect("On-Chart Overlays", ["21 EMA", "50 SMA", "200 EMA", "AVWAP"])
selected_oscillators = st.sidebar.multiselect("Lower Pane Oscillators", ["RSI (14)", "MACD (12, 26, 9)"])

period_map = {"1 Month": "1mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y", "5 Years": "5y", "Max": "max"}
interval_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
selected_period = period_map[timeframe]
selected_interval = interval_map[interval_selection]


# --- MATH HELPERS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=900)
def fetch_yahoo_data(ticker, period, interval):
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty: return None
        if 'Volume' in data.columns: return data[['Open', 'High', 'Low', 'Close', 'Volume']]
        return data[['Open', 'High', 'Low', 'Close']]
    except: return None

# --- CHART RENDERING ENGINE (Reusable) ---
def render_chart(num_name, den_name, period_str, interval_str, c_type, overlays, oscillators, height=650):
    num_ticker = st.session_state.asset_dict[num_name]
    den_ticker = st.session_state.asset_dict[den_name]
    
    num_data = fetch_yahoo_data(num_ticker, period_str, interval_str)
    den_data = fetch_yahoo_data(den_ticker, period_str, interval_str)

    if num_data is None or den_data is None:
        return None

    if isinstance(num_data.columns, pd.MultiIndex):
        num_data.columns = num_data.columns.get_level_values(0)
        den_data.columns = den_data.columns.get_level_values(0)

    df = pd.merge(num_data, den_data, left_index=True, right_index=True, suffixes=('_num', '_den'))
    df.dropna(subset=['Close_num', 'Close_den'], inplace=True)

    if df.empty: return None

    # EXACT RATIO CALCULATION
    df['Ratio_Open'] = df['Open_num'] / df['Open_den']
    df['Ratio_High'] = df['High_num'] / df['High_den']
    df['Ratio_Low'] = df['Low_num'] / df['Low_den']
    df['Ratio_Close'] = df['Close_num'] / df['Close_den']
    c = df['Ratio_Close']
    
    # Indicators
    if "50 SMA" in overlays: df['50 SMA'] = c.rolling(window=50).mean()
    if "100 SMA" in overlays: df['100 SMA'] = c.rolling(window=100).mean()
    if "21 EMA" in overlays: df['21 EMA'] = c.ewm(span=21, adjust=False).mean()
    if "200 EMA" in overlays: df['200 EMA'] = c.ewm(span=200, adjust=False).mean()

    if "AVWAP" in overlays and 'Volume_num' in df.columns:
        typ_price = (df['Ratio_High'] + df['Ratio_Low'] + df['Ratio_Close']) / 3
        df['Cum_Vol'] = df['Volume_num'].cumsum()
        df['AVWAP'] = (typ_price * df['Volume_num']).cumsum() / df['Cum_Vol']

    if "RSI (14)" in oscillators: df['RSI'] = calculate_rsi(c, 14)
    if "MACD (12, 26, 9)" in oscillators:
        df['MACD_Line'] = c.ewm(span=12).mean() - c.ewm(span=26).mean()
        df['MACD_Signal'] = df['MACD_Line'].ewm(span=9).mean()
        df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']

    # Subplots
    num_rows = 1
    row_heights = [0.6] if oscillators else [1.0]
    if "RSI (14)" in oscillators: num_rows += 1; row_heights.append(0.2)
    if "MACD (12, 26, 9)" in oscillators: num_rows += 1; row_heights.append(0.2)
    row_heights = [h / sum(row_heights) for h in row_heights]

    fig = make_subplots(rows=num_rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)

    # TradingView Colors
    TV_GREEN, TV_RED, TV_BLUE, TV_GRID = '#089981', '#F23645', '#2962FF', '#E0E3EB'
    ind_colors = {"21 EMA": "#FF9800", "50 SMA": TV_BLUE, "200 EMA": "#F44336", "AVWAP": "#1E1E1E"}

    # Main Chart Trace
    if c_type == "Line":
        fig.add_trace(go.Scatter(x=df.index, y=df['Ratio_Close'], mode='lines', name='Ratio', line=dict(color=TV_BLUE, width=2)), row=1, col=1)
    elif c_type == "Bar (OHLC)":
        fig.add_trace(go.Ohlc(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], name='Ratio', increasing_line_color=TV_GREEN, decreasing_line_color=TV_RED), row=1, col=1)
    elif c_type == "Hollow Candlestick":
        fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], name='Ratio', increasing_line_color=TV_GREEN, increasing_fillcolor='rgba(0,0,0,0)', decreasing_line_color=TV_RED, decreasing_fillcolor='rgba(0,0,0,0)'), row=1, col=1)
    else: # Candlestick (Default)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], name='Ratio', increasing_line_color=TV_GREEN, increasing_fillcolor=TV_GREEN, decreasing_line_color=TV_RED, decreasing_fillcolor=TV_RED), row=1, col=1)

    # Overlays + Label Annotations
    for ind in overlays:
        if ind in df.columns:
            valid_data = df[ind].dropna()
            if not valid_data.empty:
                color = ind_colors.get(ind, '#000000')
                fig.add_trace(go.Scatter(x=df.index, y=df[ind], mode='lines', name=ind, line=dict(color=color, width=1.5)), row=1, col=1)
                
                last_idx = valid_data.index[-1]
                last_val = valid_data.iloc[-1]
                fig.add_annotation(
                    x=last_idx, y=last_val, text=f"{ind}",
                    font=dict(color="white", size=10),
                    bgcolor=color, bordercolor=color,
                    showarrow=True, arrowcolor=color, arrowhead=0,
                    ax=35, ay=0, row=1, col=1
                )

    # Oscillators
    current_row = 2
    if "RSI (14)" in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='#7E57C2')), row=current_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=TV_GRID, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=TV_GRID, row=current_row, col=1)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=current_row, col=1)
        current_row += 1
        
    if "MACD (12, 26, 9)" in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Line'], mode='lines', name='MACD', line=dict(color=TV_BLUE)), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], mode='lines', name='Sig', line=dict(color='#FF9800')), row=current_row, col=1)
        hist_colors = ['rgba(8,153,129,0.5)' if v >= 0 else 'rgba(242,54,69,0.5)' for v in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='Hist', marker_color=hist_colors), row=current_row, col=1)

    # DYNAMIC X-AXIS FORMATTING
    if period_str in ["1mo", "6mo"]:
        x_format = "%d %b %Y"
        d_tick = None
    else:
        x_format = "%b %Y"
        d_tick = "M1" if period_str == "1y" else "M3"

    # LAYOUT FORMATTING
    fig.update_layout(
        template="plotly_white", plot_bgcolor='white', paper_bgcolor='white',
        xaxis_rangeslider_visible=False, height=height, 
        margin=dict(l=10, r=80, t=30, b=20), 
        legend=dict(
            orientation="h", yanchor="top", y=0.99, xanchor="left", x=0.01,
            bgcolor="rgba(255, 255, 255, 0.7)", bordercolor=TV_GRID, borderwidth=1
        ),
        hovermode="x unified", dragmode="pan"
    )
    
    fig.update_xaxes(showgrid=True, gridcolor=TV_GRID, tickformat=x_format, dtick=d_tick)
    fig.update_yaxes(showgrid=True, gridcolor=TV_GRID, side="right", tickformat=".4f")

    return fig

# --- DUAL SCREEN TABS ---
tab1, tab2 = st.tabs(["🖥️ Static Sector Rotation", "🔍 Dynamic Explorer"])

# --- SCREEN 1
