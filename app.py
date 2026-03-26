import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import feedparser

# --- PAGE CONFIGURATION & TIMER ---
st.set_page_config(page_title="Global Macro Terminal", layout="wide", initial_sidebar_state="expanded")
start_time = time.time()

# --- CUSTOM CSS FOR PROFESSIONAL VIBE ---
st.markdown("""
<style>
    /* Hide default Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Live Pulse Animation */
    .pulse-dot {
        height: 12px; width: 12px;
        background-color: #00ffcc;
        border-radius: 50%; display: inline-block;
        box-shadow: 0 0 10px #00ffcc;
        animation: pulse-animation 2s infinite;
        margin-right: 8px;
    }
    @keyframes pulse-animation {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 204, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 255, 204, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 204, 0); }
    }
    
    /* Smooth Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap;
        background-color: transparent; border-radius: 4px 4px 0px 0px;
        gap: 1px; padding-top: 10px; padding-bottom: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if 'asset_dict' not in st.session_state:
    st.session_state.asset_dict = {
        "Broad Market 500 (IND)": "BSE-500.BO", "Nifty 50": "^NSEI", "Nifty Next 50": "^NN50",
        "Nifty Midcap 100": "^CRSLMID", "Nifty Smallcap 100": "^CNXSC", "Nifty Microcap 250": "^CRSLMIC",
        "BSE Sensex": "^BSESN", "Nifty Auto": "^CNXAUTO", "Nifty Bank": "^NSEBANK", 
        "Nifty Commodities": "^CNXCMDT", "Nifty Energy": "^CNXENERGY", "Nifty IT": "^CNXIT", 
        "Nifty Metal": "^CNXMETAL", "Nifty Pharma": "^CNXPHARMA", "Nifty PSU Bank": "^CNXPSUBANK",
        "S&P 500 (US)": "^GSPC", "Nasdaq 100": "^NDX", "Dow Jones Ind Avg": "^DJI",
        "Russell 2000 (Small Caps)": "^RUT", "CBOE Volatility (VIX)": "^VIX",
        "US Technology (XLK)": "XLK", "US Financials (XLF)": "XLF", "US Healthcare (XLV)": "XLV",
        "US Energy (XLE)": "XLE", "FTSE 100 (UK)": "^FTSE", "DAX (Germany)": "^GDAXI",
        "Nikkei 225 (Japan)": "^N225", "Emerging Markets (EEM)": "EEM", "All World Index (VT)": "VT",
        "US 20+ Yr Treasury (TLT)": "TLT", "High Yield Bonds (HYG)": "HYG",
        "Gold (Spot)": "GC=F", "Silver (Spot)": "SI=F", "Crude Oil (WTI)": "CL=F", "Bitcoin (USD)": "BTC-USD"
    }

# --- SIDEBAR: THEME & CONTROLS ---
st.sidebar.title("⚙️ Terminal Setup")

# Theme Toggle
theme_choice = st.sidebar.radio("UI Theme", ["Dark Mode", "Light Mode"], horizontal=True)
is_dark = theme_choice == "Dark Mode"

st.sidebar.markdown("---")
st.sidebar.header("➕ Add Custom Ticker")
with st.sidebar.form("add_ticker_form"):
    new_name = st.text_input("Name (e.g., Reliance)")
    new_ticker = st.text_input("Yahoo Ticker (e.g., RELIANCE.NS)")
    if st.form_submit_button("Save to Dashboard") and new_name and new_ticker:
        st.session_state.asset_dict[new_name] = new_ticker
        st.sidebar.success(f"✅ Added!")

st.sidebar.markdown("---")
st.sidebar.header("📊 Dynamic Chart Settings")
asset_options = ["None"] + list(st.session_state.asset_dict.keys())

selected_asset_name = st.sidebar.selectbox("Numerator (Asset 1)", asset_options, index=2) 
benchmark_name = st.sidebar.selectbox("Denominator (Asset 2)", asset_options, index=1) 

col_s1, col_s2 = st.sidebar.columns(2)
with col_s1: timeframe = st.selectbox("Lookback", ("1 Month", "6 Months", "1 Year", "2 Years", "5 Years", "Max"), index=1)
with col_s2: interval_selection = st.selectbox("Interval", ("Daily", "Weekly", "Monthly"))
chart_type = st.sidebar.selectbox("Chart Style", ("Candlestick", "Bar (OHLC)", "Hollow Candlestick", "Line"))

# Advanced Indicators tucked away cleanly
with st.sidebar.expander("🛠️ Advanced Indicators", expanded=False):
    selected_overlays = st.multiselect("Overlays", ["21 EMA", "50 SMA", "63 EMA", "100 SMA", "200 EMA", "30 WMA", "100 WMA", "200 WMA", "AVWAP"])
    selected_oscillators = st.multiselect("Oscillators", ["RSI (14)", "MACD (12, 26, 9)"])

period_map = {"1 Month": "1mo", "6 Months": "6mo", "1 Year": "1y", "2 Years": "2y", "5 Years": "5y", "Max": "max"}
interval_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
selected_period = period_map[timeframe]
selected_interval = interval_map[interval_selection]

# --- MATH & NEWS HELPERS ---
def calculate_wma(series, length):
    weights = np.arange(1, length + 1)
    return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

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
        if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
        data = data.loc[:, ~data.columns.duplicated()]
        if 'Volume' in data.columns: return data[['Open', 'High', 'Low', 'Close', 'Volume']]
        return data[['Open', 'High', 'Low', 'Close']]
    except: return None

@st.cache_data(ttl=600)
def fetch_market_news():
    feed_urls = ["https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"]
    target_keywords = ['rate', 'yield', 'treasury', 'inflation', 'cpi', 'fed', 'rbi', 'bank', 'earnings', 'revenue', 'acquire', 'merger', 'war', 'tariff', 'geopolitic']
    news_items = []
    for url in feed_urls:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries:
                if any(kw in entry.title.lower() for kw in target_keywords):
                    news_items.append({"title": entry.title, "link": entry.link, "published": entry.get("published", "")})
        except: continue
    unique_news, seen = [], set()
    for item in news_items:
        if item["title"] not in seen:
            unique_news.append(item); seen.add(item["title"])
    return unique_news[:15]

# --- CHART RENDERING ENGINE (THEME AWARE) ---
def render_chart(num_name, den_name, period_str, interval_str, c_type, overlays, oscillators, height=650):
    if num_name == "None" and den_name == "None": return None

    num_data = None
    if num_name != "None":
        num_ticker = st.session_state.asset_dict.get(num_name)
        if num_ticker: num_data = fetch_yahoo_data(num_ticker, period_str, interval_str)

    den_data = None
    if den_name != "None":
        den_ticker = st.session_state.asset_dict.get(den_name)
        if den_ticker: den_data = fetch_yahoo_data(den_ticker, period_str, interval_str)

    if (num_data is None and den_name == "None") or (den_data is None and num_name == "None") or (num_data is None and den_data is None): return None

    base_df = num_data if num_data is not None else den_data
    if num_name == "None" or num_data is None:
        num_data = pd.DataFrame(1, index=base_df.index, columns=['Open', 'High', 'Low', 'Close'])
        if 'Volume' in base_df.columns: num_data['Volume'] = 1
    if den_name == "None" or den_data is None:
        den_data = pd.DataFrame(1, index=base_df.index, columns=['Open', 'High', 'Low', 'Close'])
        if 'Volume' in base_df.columns: den_data['Volume'] = 1

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
    if "63 EMA" in overlays: df['63 EMA'] = c.ewm(span=63, adjust=False).mean()
    if "200 EMA" in overlays: df['200 EMA'] = c.ewm(span=200, adjust=False).mean()
    if "30 WMA" in overlays: df['30 WMA'] = calculate_wma(c, 30)
    if "100 WMA" in overlays: df['100 WMA'] = calculate_wma(c, 100)
    if "200 WMA" in overlays: df['200 WMA'] = calculate_wma(c, 200)
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

    # Dynamic Theme Colors
    TV_GREEN, TV_RED = '#089981', '#F23645'
    TV_BLUE = '#2962FF' if not is_dark else '#337ab7'
    TV_GRID = '#2B2B2B' if is_dark else '#E0E3EB'
    BG_COLOR = 'rgba(0,0,0,0)' # Transparent to inherit Streamlit's container color
    TEXT_COLOR = '#FFFFFF' if is_dark else '#000000'

    ind_colors = {
        "21 EMA": "#FF9800", "50 SMA": TV_BLUE, "63 EMA": "#E91E63", 
        "100 SMA": "#9C27B0", "200 EMA": "#F44336", "30 WMA": "#4CAF50", 
        "100 WMA": "#8BC34A", "200 WMA": "#FFEB3B", "AVWAP": "#FFFFFF" if is_dark else "#1E1E1E"
    }

    if c_type == "Line": fig.add_trace(go.Scatter(x=df.index, y=df['Ratio_Close'], mode='lines', line=dict(color=TV_BLUE, width=2)), row=1, col=1)
    elif c_type == "Bar (OHLC)": fig.add_trace(go.Ohlc(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], increasing_line_color=TV_GREEN, decreasing_line_color=TV_RED), row=1, col=1)
    elif c_type == "Hollow Candlestick": fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], increasing_line_color=TV_GREEN, increasing_fillcolor='rgba(0,0,0,0)', decreasing_line_color=TV_RED, decreasing_fillcolor='rgba(0,0,0,0)'), row=1, col=1)
    else: fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=df['Ratio_Close'], increasing_line_color=TV_GREEN, increasing_fillcolor=TV_GREEN, decreasing_line_color=TV_RED, decreasing_fillcolor=TV_RED), row=1, col=1)

    for ind in overlays:
        if ind in df.columns:
            valid_data = df[ind].dropna()
            if not valid_data.empty:
                color = ind_colors.get(ind, '#888888')
                fig.add_trace(go.Scatter(x=df.index, y=df[ind], mode='lines', line=dict(color=color, width=1.5)), row=1, col=1)
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

    # Apply Theme Template
    template = "plotly_dark" if is_dark else "plotly_white"
    
    fig.update_layout(
        template=template, plot_bgcolor=BG_COLOR, paper_bgcolor=BG_COLOR, font=dict(color=TEXT_COLOR),
        xaxis_rangeslider_visible=False, height=height, margin=dict(l=10, r=80, t=10, b=20), showlegend=False, hovermode="x unified", dragmode="pan"
    )
    fig.update_xaxes(showgrid=True, gridcolor=TV_GRID, tickformat=x_format, dtick=d_tick)
    fig.update_yaxes(showgrid=True, gridcolor=TV_GRID, side="right", tickformat=".2f" if den_name == "None" else ".4f")

    return fig

def render_news_feed(height):
    st.subheader("📰 Market Intelligence")
    with st.container(border=True, height=height):
        news = fetch_market_news()
        if not news: st.info("Scanning for news...")
        else:
            for item in news:
                st.markdown(f"**[{item['title']}]({item['link']})**")
                st.caption(f"🕒 {item['published'].replace('+0000', '').strip()}")
                st.markdown("---")

# --- MAIN APP LAYOUT ---
st.markdown("<h1 style='text-align: left;'><span class='pulse-dot'></span>Global Macro Terminal</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📊 Market Overview (Grid)", "🔍 Advanced Explorer"])

# --- SCREEN 1: THE MACRO GRID ---
with tab1:
    top_indices = ["S&P 500 (US)", "Nasdaq 100", "Nifty 50", "Gold (Spot)", "Bitcoin (USD)", "Crude Oil (WTI)"]
    cols_top = st.columns(len(top_indices))
    
    for i, idx_name in enumerate(top_indices):
        with cols_top[i]:
            with st.container(border=True): # Wrap metric in a card
                ticker = st.session_state.asset_dict[idx_name]
                data = fetch_yahoo_data(ticker, "5d", "1d")
                
                if data is not None and not data.empty and len(data) >= 2:
                    try:
                        last_close, prev_close = float(data['Close'].iloc[-1]), float(data['Close'].iloc[-2])
                        pct_change = ((last_close - prev_close) / prev_close) * 100
                        st.metric(label=idx_name, value=f"{last_close:,.2f}", delta=f"{pct_change:.2f}%")
                    except Exception: st.metric(label=idx_name, value="Data Error")
                else: st.metric(label=idx_name, value="N/A")
                
                with st.expander("Show Chart"):
                    top_fig = render_chart(idx_name, "None", "1mo", "1d", "Line", [], [], height=180)
                    if top_fig: 
                        top_fig.update_layout(margin=dict(l=0, r=40, t=0, b=0))
                        st.plotly_chart(top_fig, use_container_width=True, key=f"top_{i}")
                    
    st.markdown("<br>", unsafe_allow_html=True)
    col_main, col_news = st.columns([3, 1]) 
    
    with col_main:
        macro_tabs = st.tabs(["🇮🇳 India (NSE)", "🇺🇸 United States", "🌍 Global & Rates"])
        
        with macro_tabs[0]:
            st.caption("Benchmark: Broad Market 500 (IND)")
            nse_list = ["Nifty Bank", "Nifty IT", "Nifty Auto", "Nifty Pharma", "Nifty Metal", "Nifty Energy", "Nifty FMCG", "Nifty Realty", "Nifty PSU Bank"]
            cols = st.columns(3)
            with st.spinner("Fetching NSE..."):
                for idx, sec in enumerate(nse_list):
                    with cols[idx % 3], st.container(border=True):
                        st.markdown(f"**{sec}**")
                        fig = render_chart(sec, "Broad Market 500 (IND)", "6mo", "1d", "Candlestick", [], [], height=250)
                        if fig: st.plotly_chart(fig, use_container_width=True, key=f"nse_{idx}")
                        
        with macro_tabs[1]:
            st.caption("Benchmark: S&P 500 (US)")
            us_list = ["Nasdaq 100", "Russell 2000 (Small Caps)", "US Technology (XLK)", "US Financials (XLF)", "US Healthcare (XLV)", "US Energy (XLE)"]
            cols = st.columns(3)
            with st.spinner("Fetching US..."):
                for idx, sec in enumerate(us_list):
                    with cols[idx % 3], st.container(border=True):
                        st.markdown(f"**{sec}**")
                        fig = render_chart(sec, "S&P 500 (US)", "6mo", "1d", "Candlestick", [], [], height=250)
                        if fig: st.plotly_chart(fig, use_container_width=True, key=f"us_{idx}")

        with macro_tabs[2]:
            st.caption("Risk Sentiments & Yield Spreads")
            macro_pairs = [("Gold (Spot)", "S&P 500 (US)", "Safe Haven vs Equity"), ("US 20+ Yr Treasury (TLT)", "S&P 500 (US)", "Bonds vs Equity"), ("Emerging Markets (EEM)", "S&P 500 (US)", "EM vs Developed"), ("High Yield Bonds (HYG)", "US 20+ Yr Treasury (TLT)", "Credit Risk Profile")]
            cols = st.columns(2)
            with st.spinner("Fetching Global Data..."):
                for idx, (num, den, title) in enumerate(macro_pairs):
                    with cols[idx % 2], st.container(border=True):
                        st.markdown(f"**{title}** ({num} / {den})")
                        fig = render_chart(num, den, "6mo", "1d", "Line", [], [], height=280)
                        if fig: st.plotly_chart(fig, use_container_width=True, key=f"glb_{idx}")

    with col_news: render_news_feed(height=950)

# --- SCREEN 2: DYNAMIC EXPLORER ---
with tab2:
    col_dyn_main, col_dyn_news = st.columns([3, 1]) 
    
    with col_dyn_main:
        c1, c2 = st.columns([4, 1])
        if benchmark_name == "None" and selected_asset_name != "None": c1.subheader(f"Asset: {selected_asset_name}")
        elif selected_asset_name == "None" and benchmark_name != "None": c1.subheader(f"Inverse: 1 / {benchmark_name}")
        elif selected_asset_name == "None" and benchmark_name == "None": c1.subheader("Awaiting Input...")
        else: c1.subheader(f"Ratio: {selected_asset_name} / {benchmark_name}")
            
        if c2.button("🔄 Clear Drawings"): st.rerun()

        with st.spinner("Analyzing data..."), st.container(border=True):
            fig = render_chart(selected_asset_name, benchmark_name, selected_period, selected_interval, chart_type, selected_overlays, selected_oscillators, height=750)
            if fig:
                config = {'modeBarButtonsToAdd': ['drawline', 'drawrect', 'eraseshape'], 'displayModeBar': True, 'displaylogo': False, 'scrollZoom': True}
                st.plotly_chart(fig, use_container_width=True, config=config)
            elif selected_asset_name == "None" and benchmark_name == "None": st.info("Use the sidebar to configure your chart.")
                    
    with col_dyn_news: render_news_feed(height=840)

# --- TELEMETRY FOOTER ---
st.markdown("---")
st.caption(f"🟢 **System Online** | ⏱️ **Engine Latency:** {round(time.time() - start_time, 2)}s | 📡 **API Routing:** Active | 🕒 **Sync:** {pd.Timestamp.now().strftime('%H:%M:%S UTC')}")
