import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import feedparser

# --- PAGE CONFIGURATION & TIMER START ---
st.set_page_config(page_title="Global Macro Ratio Dashboard", layout="wide", initial_sidebar_state="expanded")
start_time = time.time()

st.title("🌍 Global Macro Ratio Dashboard (Pro)")

# --- EXTENDED STATE MANAGEMENT (NSE, NYSE, ETFs) ---
if 'asset_dict' not in st.session_state:
    st.session_state.asset_dict = {
        # Benchmarks
        "Broad Market 500 (IND)": "BSE-500.BO", 
        "S&P 500 (US)": "^GSPC",
        "Nasdaq 100": "^NDX",
        
        # NSE Sectors
        "Nifty 50": "^NSEI",
        "Nifty Auto": "^CNXAUTO",
        "Nifty Bank": "^NSEBANK",
        "Nifty Commodities": "^CNXCMDT",
        "Nifty Energy": "^CNXENERGY",
        "Nifty FMCG": "^CNXFMCG",
        "Nifty IT": "^CNXIT",
        "Nifty Metal": "^CNXMETAL",
        "Nifty Pharma": "^CNXPHARMA",
        "Nifty PSU Bank": "^CNXPSUBANK",
        "Nifty Realty": "^CNXREALTY",
        
        # US Markets & Sectors (NYSE/Nasdaq ETFs)
        "Dow Jones Ind. Avg": "^DJI",
        "Russell 2000 (Small Cap)": "^RUT",
        "US Tech (XLK)": "XLK",
        "US Financials (XLF)": "XLF",
        "US Healthcare (XLV)": "XLV",
        "US Energy (XLE)": "XLE",
        "US Consumer Discretionary (XLY)": "XLY",
        "US Industrials (XLI)": "XLI",
        
        # Global Asset Classes (ETFs & Spot)
        "Gold (Spot)": "GC=F",
        "Silver (Spot)": "SI=F",
        "Crude Oil (WTI)": "CL=F",
        "US 20+ Year Treasuries (TLT)": "TLT",
        "US 7-10 Year Treasuries (IEF)": "IEF",
        "Real Estate (VNQ)": "VNQ",
        "Emerging Markets (EEM)": "EEM",
        "Bitcoin (USD)": "BTC-USD"
    }

# --- SIDEBAR CONTROLS ---
st.sidebar.header("➕ Add Custom Ticker")
with st.sidebar.form("add_ticker_form"):
    new_name = st.text_input("Name (e.g., Reliance)")
    new_ticker = st.text_input("Yahoo Ticker (e.g., RELIANCE.NS)")
    if st.form_submit_button("Save to Dashboard") and new_name and new_ticker:
        st.session_state.asset_dict[new_name] = new_ticker
        st.sidebar.success(f"✅ {new_name} added!")

st.sidebar.markdown("---")
st.sidebar.header("Chart Settings (Dynamic Screen)")

selected_asset_name = st.sidebar.selectbox("1. Numerator", list(st.session_state.asset_dict.keys()), index=3)
benchmark_name = st.sidebar.selectbox("2. Denominator", list(st.session_state.asset_dict.keys()), index=0)

chart_type = st.sidebar.selectbox("3. Style", ("Candlestick", "Bar (OHLC)", "Hollow Candlestick", "Line"))
timeframe = st.sidebar.selectbox("4. Lookback", ("1 Month", "6 Months", "1 Year", "2 Years", "5 Years", "Max"), index=1)
interval_selection = st.sidebar.selectbox("5. Interval", ("Daily", "Weekly", "Monthly"))

st.sidebar.markdown("---")
st.sidebar.header("📈 Indicators")
selected_overlays = st.sidebar.multiselect("Overlays", ["21 EMA", "50 SMA", "200 EMA", "AVWAP"])
selected_oscillators = st.sidebar.multiselect("Oscillators", ["RSI (14)", "MACD (12, 26, 9)"])

period_map = {"1 Month": "1mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y", "5 Years": "5y", "Max": "max"}
interval_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
selected_period = period_map[timeframe]
selected_interval = interval_map[interval_selection]

# --- MATH & NEWS HELPERS ---
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

@st.cache_data(ttl=600)
def fetch_market_news():
    feed_urls = [
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", 
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", 
    ]
    target_keywords = ['rate', 'yield', 'treasury', 'inflation', 'cpi', 'fed', 'rbi', 'bank', 'earnings', 'revenue', 'acquire', 'merger', 'war', 'tariff', 'geopolitic']
    news_items = []
    for url in feed_urls:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries:
                if any(kw in entry.title.lower() for kw in target_keywords):
                    news_items.append({"title": entry.title, "link": entry.link, "published": entry.get("published", "")})
        except: continue
    
    unique_news = []
    seen = set()
    for item in news_items:
        if item["title"] not in seen:
            unique_news.append(item)
            seen.add(item["title"])
    return unique_news[:15]

# --- CHART RENDERING ENGINE ---
def render_chart(num_name, den_name, period_str, interval_str, c_type, overlays, oscillators, height=650):
    num_ticker = st.session_state.asset_dict.get(num_name)
    den_ticker = st.session_state.asset_dict.get(den_name)
    
    if not num_ticker or not den_ticker: return None
    
    num_data = fetch_yahoo_data(num_ticker, period_str, interval_str)
    den_data = fetch_yahoo_data(den_ticker, period_str, interval_str)

    if num_data is None or den_data is None: return None

    if isinstance(num_data.columns, pd.MultiIndex):
        num_data.columns = num_data.columns.get_level_values(0)
        den_data.columns = den_data.columns.get_level_values(0)

    df = pd.merge(num_data, den_data, left_index=True, right_index=True, suffixes=('_num', '_den'))
    df.dropna(subset=['Close_num', 'Close_den'], inplace=True)
    if df.empty: return None

    df['Ratio_Open'] = df['Open_num'] / df['Open_den']
    df['Ratio_High'] = df['High_num'] / df['High_den']
    df['Ratio_Low'] = df['Low_num'] / df['Low_den']
    df['Ratio_Close'] = df['Close_num'] / df['Close_den']
    c = df['Ratio_Close']
    
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

    num_rows = 1 + len(oscillators)
    row_heights = [0.6] + [0.2] * len(oscillators) if oscillators else [1.0]
    row_heights = [h / sum(row_heights) for h in row_heights]

    fig = make_subplots(rows=num_rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)

    TV_GREEN, TV_RED, TV_BLUE, TV_GRID = '#089981', '#F23645', '#2962FF', '#E0E3EB'
    ind_colors = {"21 EMA": "#FF9800", "50 SMA": TV_BLUE, "200 EMA": "#F44336", "AVWAP": "#1E1E1E"}

    if c_type == "Line":
        fig.add_trace(go.Scatter(x=df.index, y=df['Ratio_Close'], mode='lines', name='Ratio', line=dict(color=TV_BLUE, width=2)), row=1, col=1)
    elif c_type == "Bar (OHLC)":
        fig.add_trace(go.Ohlc(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], increasing_line_color=TV_GREEN, decreasing_line_color=TV_RED), row=1, col=1)
    elif c_type == "Hollow Candlestick":
        fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], increasing_line_color=TV_GREEN, increasing_fillcolor='rgba(0,0,0,0)', decreasing_line_color=TV_RED, decreasing_fillcolor='rgba(0,0,0,0)'), row=1, col=1)
    else:
        fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], increasing_line_color=TV_GREEN, increasing_fillcolor=TV_GREEN, decreasing_line_color=TV_RED, decreasing_fillcolor=TV_RED), row=1, col=1)

    for ind in overlays:
        if ind in df.columns:
            valid_data = df[ind].dropna()
            if not valid_data.empty:
                color = ind_colors.get(ind, '#000000')
                fig.add_trace(go.Scatter(x=df.index, y=df[ind], mode='lines', name=ind, line=dict(color=color, width=1.5)), row=1, col=1)
                fig.add_annotation(x=valid_data.index[-1], y=valid_data.iloc[-1], text=f"{ind}", font=dict(color="white", size=10), bgcolor=color, bordercolor=color, showarrow=True, arrowcolor=color, arrowhead=0, ax=35, ay=0, row=1, col=1)

    curr = 2
    if "RSI (14)" in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', line=dict(color='#7E57C2')), row=curr, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color=TV_GRID, row=curr, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color=TV_GRID, row=curr, col=1)
        fig.update_yaxes(title_text="RSI", range=[0, 100], row=curr, col=1); curr += 1
    if "MACD (12, 26, 9)" in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Line'], mode='lines', line=dict(color=TV_BLUE)), row=curr, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], mode='lines', line=dict(color='#FF9800')), row=curr, col=1)
        hist_colors = ['rgba(8,153,129,0.5)' if v >= 0 else 'rgba(242,54,69,0.5)' for v in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=hist_colors), row=curr, col=1)

    x_format, d_tick = ("%d %b %Y", None) if period_str in ["1mo", "6mo"] else ("%b %Y", "M1" if period_str == "1y" else "M3")

    fig.update_layout(
        template="plotly_white", plot_bgcolor='white', paper_bgcolor='white', xaxis_rangeslider_visible=False, height=height, 
        margin=dict(l=10, r=80, t=10, b=20), showlegend=False, hovermode="x unified", dragmode="pan"
    )
    fig.update_xaxes(showgrid=True, gridcolor=TV_GRID, tickformat=x_format, dtick=d_tick)
    fig.update_yaxes(showgrid=True, gridcolor=TV_GRID, side="right", tickformat=".4f")

    return fig

def render_news_feed(height):
    st.subheader("📰 Global Macro News")
    with st.container(border=True, height=height):
        news = fetch_market_news()
        if not news: st.info("No relevant news fetched.")
        else:
            for item in news:
                st.markdown(f"**[{item['title']}]({item['link']})**")
                st.caption(f"🕒 {item['published'].replace('+0000', '').strip()}")
                st.markdown("---")

# --- DUAL SCREEN TABS ---
tab1, tab2 = st.tabs(["🖥️ Macro Overview (Grid)", "🔍 Dynamic Explorer"])

# --- SCREEN 1: THE MACRO GRID ---
with tab1:
    col_main, col_news = st.columns([3, 1]) 
    
    with col_main:
        # Nested tabs prevent API spam by only loading what the user clicks
        macro_tabs = st.tabs(["🇮🇳 NSE Sectors", "🇺🇸 US Markets", "🌍 Global Assets & Yields"])
        
        with macro_tabs[0]:
            st.caption("Benchmark: Broad Market 500 (IND)")
            nse_list = ["Nifty Bank", "Nifty IT", "Nifty Auto", "Nifty Pharma", "Nifty Metal", "Nifty Energy", "Nifty FMCG", "Nifty Realty", "Nifty PSU Bank"]
            cols = st.columns(3)
            with st.spinner("Fetching NSE Data..."):
                for idx, sec in enumerate(nse_list):
                    with cols[idx % 3], st.container(border=True):
                        st.markdown(f"**{sec}**")
                        fig = render_chart(sec, "Broad Market 500 (IND)", "6mo", "1d", "Candlestick", [], [], height=250)
                        if fig: st.plotly_chart(fig, use_container_width=True, key=f"nse_{idx}")
                        
        with macro_tabs[1]:
            st.caption("Benchmark: S&P 500 (US)")
            us_list = ["Nasdaq 100", "Russell 2000 (Small Cap)", "US Tech (XLK)", "US Financials (XLF)", "US Healthcare (XLV)", "US Energy (XLE)"]
            cols = st.columns(3)
            with st.spinner("Fetching US Data..."):
                for idx, sec in enumerate(us_list):
                    with cols[idx % 3], st.container(border=True):
                        st.markdown(f"**{sec}**")
                        fig = render_chart(sec, "S&P 500 (US)", "6mo", "1d", "Candlestick", [], [], height=250)
                        if fig: st.plotly_chart(fig, use_container_width=True, key=f"us_{idx}")

        with macro_tabs[2]:
            st.caption("Ratios measuring Risk-On vs Risk-Off behaviors")
            # Custom pairs for macro insights
            macro_pairs = [
                ("Gold (Spot)", "S&P 500 (US)", "Safe Haven vs Equity"),
                ("US 20+ Year Treasuries (TLT)", "S&P 500 (US)", "Bonds vs Equity"),
                ("Emerging Markets (EEM)", "S&P 500 (US)", "EM vs Developed"),
                ("Bitcoin (USD)", "Gold (Spot)", "Digital vs Physical Gold")
            ]
            cols = st.columns(2)
            with st.spinner("Fetching Macro Data..."):
                for idx, (num, den, title) in enumerate(macro_pairs):
                    with cols[idx % 2], st.container(border=True):
                        st.markdown(f"**{title}** ({num} / {den})")
                        fig = render_chart(num, den, "6mo", "1d", "Line", [], [], height=280)
                        if fig: st.plotly_chart(fig, use_container_width=True, key=f"glb_{idx}")

    with col_news:
        render_news_feed(height=950)

# --- SCREEN 2: DYNAMIC EXPLORER ---
with tab2:
    col_dyn_main, col_dyn_news = st.columns([3, 1]) 
    
    with col_dyn_main:
        c1, c2 = st.columns([4, 1])
        c1.subheader(f"{selected_asset_name} / {benchmark_name}")
        if c2.button("🔄 Clear Drawings"): st.rerun()

        with st.spinner("Rendering Chart..."), st.container(border=True):
            fig = render_chart(selected_asset_name, benchmark_name, selected_period, selected_interval, chart_type, selected_overlays, selected_oscillators, height=700)
            if fig:
                config = {'modeBarButtonsToAdd': ['drawline', 'drawrect', 'eraseshape'], 'displayModeBar': True, 'displaylogo': False, 'scrollZoom': True}
                st.plotly_chart(fig, use_container_width=True, config=config)
                    
    with col_dyn_news:
        render_news_feed(height=780)

# --- TELEMETRY ---
st.markdown("---")
latency = round(time.time() - start_time, 2)
st.caption(f"🟢 **System:** Online | ⏱️ **Latency:** {latency}s | 📡 **Engines:** YF API + RSS | 🕒 **Sync:** {pd.Timestamp.now().strftime('%H:%M:%S UTC')} | 📦 **Assets:** {len(st.session_state.asset_dict)}")
