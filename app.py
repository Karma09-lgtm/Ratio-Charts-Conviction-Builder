import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import feedparser

# --- PAGE CONFIGURATION & TIMER ---
st.set_page_config(page_title="Global Macro Terminal", layout="wide", initial_sidebar_state="collapsed")
start_time = time.time()

# --- PREMIUM TRADINGVIEW-STYLE CSS ---
st.markdown("""
<style>
    /* Base Theme & Font */
    .stApp {
        background-color: #131722; /* TradingView Classic Dark Background */
        color: #d1d4dc;
        font-family: -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif;
    }
    
    /* Hide Default Chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Elegant Containers & Cards */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: #1e222d;
        border-radius: 6px;
        border: 1px solid #2a2e39;
        padding: 10px;
    }
    
    /* Sleek Expander/Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #131722; border-bottom: 2px solid #2a2e39; gap: 10px; }
    .stTabs [data-baseweb="tab"] { color: #787b86; padding: 10px 15px; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #2962FF !important; border-bottom: 2px solid #2962FF !important; }
    
    /* Metric Styling */
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; font-weight: 700; color: #d1d4dc;}
    [data-testid="stMetricDelta"] svg { display: none; } /* Hide arrow, rely on color */
    
    /* Dataframes (Watchlist) */
    [data-testid="stDataFrame"] { border: none !important; }
    
    /* Scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #131722; }
    ::-webkit-scrollbar-thumb { background: #2a2e39; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #363a45; }
    
    /* Headers */
    h1, h2, h3 { color: #ffffff !important; font-weight: 600 !important; }
    hr { border-color: #2a2e39; margin-top: 10px; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT (ASSETS & WATCHLISTS) ---
if 'asset_dict' not in st.session_state:
    st.session_state.asset_dict = {
        "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Dow Jones": "^DJI", "Russell 2000": "^RUT", "VIX": "^VIX",
        "Broad Market 500 (IND)": "BSE-500.BO", "Nifty 50": "^NSEI", "Nifty Bank": "^NSEBANK", "Nifty IT": "^CNXIT",
        "Gold (Spot)": "GC=F", "Silver": "SI=F", "Crude Oil": "CL=F", "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD",
        "US 20+ Yr Treasury": "TLT", "US Tech ETF": "XLK", "US Fin ETF": "XLF", "Emerging Markets": "EEM"
    }

if 'watchlists' not in st.session_state:
    st.session_state.watchlists = {
        "⭐ My Favorites": {"S&P 500": "^GSPC", "Nifty 50": "^NSEI", "Gold (Spot)": "GC=F", "Bitcoin": "BTC-USD"},
        "🔥 Tech Watch": {"Nasdaq 100": "^NDX", "US Tech ETF": "XLK", "Nifty IT": "^CNXIT"}
    }
if 'active_wl' not in st.session_state:
    st.session_state.active_wl = "⭐ My Favorites"

# --- SIDEBAR CONTROLS ---
st.sidebar.title("⚙️ Terminal Settings")

with st.sidebar.expander("📝 Watchlist Manager", expanded=False):
    st.caption("Create or Delete Watchlists")
    new_wl_name = st.text_input("New Watchlist Name")
    if st.button("Create Watchlist") and new_name:
        st.session_state.watchlists[new_wl_name] = {}
        st.session_state.active_wl = new_wl_name
        st.rerun()
    if st.button("Delete Current Watchlist") and len(st.session_state.watchlists) > 1:
        del st.session_state.watchlists[st.session_state.active_wl]
        st.session_state.active_wl = list(st.session_state.watchlists.keys())[0]
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📊 Chart Engine")
asset_options = ["None"] + list(st.session_state.asset_dict.keys())
selected_asset_name = st.sidebar.selectbox("Numerator", asset_options, index=1) 
benchmark_name = st.sidebar.selectbox("Denominator", asset_options, index=0) 

c1, c2 = st.sidebar.columns(2)
with c1: timeframe = st.selectbox("Lookback", ("1mo", "3mo", "6mo", "1y", "2y", "5y", "max"), index=2)
with c2: interval_selection = st.selectbox("Interval", ("1d", "1wk", "1mo"))
chart_type = st.sidebar.selectbox("Style", ("Candlestick", "Bar (OHLC)", "Line"))

st.sidebar.markdown("---")
st.sidebar.header("📈 Indicators")
selected_overlays = st.sidebar.multiselect("Overlays", ["21 EMA", "50 SMA", "200 EMA", "AVWAP"], default=["50 SMA"])
selected_oscillators = st.sidebar.multiselect("Oscillators", ["RSI (14)", "MACD (12, 26, 9)"])

# --- HELPERS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    return 100 - (100 / (1 + gain / loss))

@st.cache_data(ttl=900)
def fetch_yahoo_data(ticker, period, interval):
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False)
        if data.empty: return None
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        data = data.loc[:, ~data.columns.duplicated()]
        return data
    except: return None

@st.cache_data(ttl=300)
def fetch_bulk_watchlist(tickers_dict):
    if not tickers_dict: return pd.DataFrame()
    tkrs = list(tickers_dict.values())
    try:
        data = yf.download(tkrs, period="5d", interval="1d", progress=False)['Close']
        if isinstance(data, pd.Series): data = data.to_frame()
        
        results = []
        for name, tk in tickers_dict.items():
            if tk in data.columns:
                col = data[tk].dropna()
                if len(col) >= 2:
                    last, prev = col.iloc[-1], col.iloc[-2]
                    chg = ((last - prev) / prev) * 100
                    results.append({"Asset": name, "Price": round(last, 2), "Chg %": round(chg, 2)})
        return pd.DataFrame(results)
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_market_news():
    feed_urls = ["https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"]
    news_items, seen = [], set()
    for url in feed_urls:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:10]: # Limit for speed
                if entry.title not in seen:
                    news_items.append({"title": entry.title, "link": entry.link})
                    seen.add(entry.title)
        except: continue
    return news_items[:12]

# --- CHART ENGINE ---
def render_chart(num_name, den_name, period_str, interval_str, c_type, overlays, oscillators, height=650):
    if num_name == "None" and den_name == "None": return None
    num_data = fetch_yahoo_data(st.session_state.asset_dict.get(num_name), period_str, interval_str) if num_name != "None" else None
    den_data = fetch_yahoo_data(st.session_state.asset_dict.get(den_name), period_str, interval_str) if den_name != "None" else None

    if (num_data is None and den_name == "None") or (den_data is None and num_name == "None"): return None

    base_df = num_data if num_data is not None else den_data
    if num_name == "None" or num_data is None:
        num_data = pd.DataFrame(1, index=base_df.index, columns=['Open', 'High', 'Low', 'Close'])
        if 'Volume' in base_df.columns: num_data['Volume'] = 1
    if den_name == "None" or den_data is None:
        den_data = pd.DataFrame(1, index=base_df.index, columns=['Open', 'High', 'Low', 'Close'])
        if 'Volume' in base_df.columns: den_data['Volume'] = 1

    df = pd.merge(num_data, den_data, left_index=True, right_index=True, suffixes=('_num', '_den')).dropna()
    if df.empty: return None

    df['Ratio_Open'] = df['Open_num'] / df['Open_den']
    df['Ratio_High'] = df['High_num'] / df['High_den']
    df['Ratio_Low'] = df['Low_num'] / df['Low_den']
    df['Ratio_Close'] = df['Close_num'] / df['Close_den']
    c = df['Ratio_Close']
    
    if "50 SMA" in overlays: df['50 SMA'] = c.rolling(50).mean()
    if "21 EMA" in overlays: df['21 EMA'] = c.ewm(span=21).mean()
    if "200 EMA" in overlays: df['200 EMA'] = c.ewm(span=200).mean()
    if "AVWAP" in overlays and 'Volume_num' in df.columns:
        typ_price = (df['Ratio_High'] + df['Ratio_Low'] + df['Ratio_Close']) / 3
        df['AVWAP'] = (typ_price * df['Volume_num']).cumsum() / df['Volume_num'].cumsum()

    if "RSI (14)" in oscillators: df['RSI'] = calculate_rsi(c, 14)
    if "MACD (12, 26, 9)" in oscillators:
        df['MACD_Line'] = c.ewm(span=12).mean() - c.ewm(span=26).mean()
        df['MACD_Signal'] = df['MACD_Line'].ewm(span=9).mean()
        df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']

    num_rows = 1 + len(oscillators)
    row_heights = [0.7] + [0.15] * len(oscillators) if oscillators else [1.0]
    fig = make_subplots(rows=num_rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=row_heights)

    TV_GREEN, TV_RED, TV_BLUE, TV_GRID, BG = '#089981', '#f23645', '#2962FF', '#2a2e39', '#131722'

    if c_type == "Line": fig.add_trace(go.Scatter(x=df.index, y=c, line=dict(color=TV_BLUE, width=1.5)), row=1, col=1)
    elif c_type == "Bar (OHLC)": fig.add_trace(go.Ohlc(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=c, increasing_line_color=TV_GREEN, decreasing_line_color=TV_RED), row=1, col=1)
    else: fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=c, increasing_line_color=TV_GREEN, increasing_fillcolor=TV_GREEN, decreasing_line_color=TV_RED, decreasing_fillcolor=TV_RED), row=1, col=1)

    colors = {"21 EMA": "#FF9800", "50 SMA": "#2962FF", "200 EMA": "#F44336", "AVWAP": "#FFFFFF"}
    for ind in overlays:
        if ind in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[ind], line=dict(color=colors.get(ind, '#fff'), width=1)), row=1, col=1)

    curr = 2
    if "RSI (14)" in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#7E57C2', width=1)), row=curr, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color='#787b86', row=curr, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color='#787b86', row=curr, col=1)
        fig.update_yaxes(range=[0, 100], row=curr, col=1); curr += 1
    if "MACD (12, 26, 9)" in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Line'], line=dict(color=TV_BLUE, width=1)), row=curr, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='#FF9800', width=1)), row=curr, col=1)
        hc = [TV_GREEN if v >= 0 else TV_RED for v in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=hc), row=curr, col=1)

    fig.update_layout(
        template="plotly_dark", plot_bgcolor=BG, paper_bgcolor=BG,
        xaxis_rangeslider_visible=False, height=height, margin=dict(l=0, r=45, t=10, b=0), showlegend=False,
        hovermode="x unified", dragmode="pan", font=dict(color="#787b86", size=11)
    )
    fig.update_xaxes(showgrid=True, gridcolor=TV_GRID, tickformat="%d %b '%y")
    fig.update_yaxes(showgrid=True, gridcolor=TV_GRID, side="right", tickformat=".2f" if den_name == "None" else ".4f")
    return fig

# --- LAYOUT CONSTRUCTION ---
# Create a 75/25 split for the entire terminal
col_main, col_panel = st.columns([3, 1], gap="medium")

with col_main:
    # Top Action Bar
    t1, t2 = st.columns([3, 1])
    if benchmark_name == "None": t1.markdown(f"### {selected_asset_name}")
    else: t1.markdown(f"### {selected_asset_name} / {benchmark_name}")
    
    if t2.button("🗑️ Clear Screen Drawings", use_container_width=True): st.rerun()

    # Main Chart
    with st.spinner("Compiling Market Data..."):
        fig = render_chart(selected_asset_name, benchmark_name, timeframe, interval_selection, chart_type, selected_overlays, selected_oscillators, height=750)
        if fig:
            cfg = {'modeBarButtonsToAdd': ['drawline', 'drawrect', 'eraseshape'], 'displaylogo': False, 'scrollZoom': True}
            st.plotly_chart(fig, use_container_width=True, config=cfg)

with col_panel:
    # --- 📋 WATCHLIST WIDGET ---
    st.markdown("#### 📋 Watchlist")
    
    # Watchlist Selector
    active_wl = st.selectbox("Select List", list(st.session_state.watchlists.keys()), index=list(st.session_state.watchlists.keys()).index(st.session_state.active_wl), label_visibility="collapsed")
    st.session_state.active_wl = active_wl
    
    # Watchlist Data
    wl_df = fetch_bulk_watchlist(st.session_state.watchlists[active_wl])
    if not wl_df.empty:
        # Style the dataframe (Green for positive, Red for negative)
        def color_chg(val):
            color = '#089981' if val > 0 else '#f23645' if val < 0 else '#787b86'
            return f'color: {color}; font-weight: bold;'
        
        styled_df = wl_df.style.applymap(color_chg, subset=['Chg %']).format({"Price": "{:.2f}", "Chg %": "{:+.2f}%"})
        st.dataframe(styled_df, hide_index=True, use_container_width=True, height=200)
    else:
        st.caption("Watchlist is empty or data unavailable.")

    # Add to Watchlist Inline Form
    with st.popover("➕ Add Symbol to Watchlist", use_container_width=True):
        add_asset = st.selectbox("Select from Database", ["Custom"] + list(st.session_state.asset_dict.keys()))
        if add_asset == "Custom":
            custom_name = st.text_input("Name")
            custom_tkr = st.text_input("Yahoo Ticker")
            if st.button("Add Custom") and custom_name and custom_tkr:
                st.session_state.watchlists[active_wl][custom_name] = custom_tkr
                st.rerun()
        else:
            if st.button("Add to List"):
                st.session_state.watchlists[active_wl][add_asset] = st.session_state.asset_dict[add_asset]
                st.rerun()
                
    with st.popover("➖ Remove Symbol", use_container_width=True):
        if st.session_state.watchlists[active_wl]:
            rem_asset = st.selectbox("Select to Remove", list(st.session_state.watchlists[active_wl].keys()))
            if st.button("Remove"):
                del st.session_state.watchlists[active_wl][rem_asset]
                st.rerun()
        else: st.caption("List is empty.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- 📰 LIVE NEWS FEED ---
    st.markdown("#### 📰 Terminal Feed")
    with st.container(height=420, border=False):
        news = fetch_market_news()
        if not news: st.caption("Awaiting news pulses...")
        else:
            for item in news:
                st.markdown(f"<a href='{item['link']}' style='color: #d1d4dc; text-decoration: none; font-size: 0.9rem;'>{item['title']}</a>", unsafe_allow_html=True)
                st.markdown("<hr style='margin: 8px 0px; border-color: #2a2e39;'>", unsafe_allow_html=True)

# --- SYSTEM FOOTER ---
st.markdown("---")
st.caption(f"⚡ **System Latency:** {round(time.time() - start_time, 2)}s | 📡 **Data Providers:** YF API, WSJ, CNBC | 🔒 **Connection:** Secure")
