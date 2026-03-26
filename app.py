import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import feedparser

# --- PAGE CONFIGURATION & TIMER START ---
st.set_page_config(page_title="Ratio Charts Conviction Builder", layout="wide", initial_sidebar_state="collapsed")
start_time = time.time()

# --- PREMIUM TRADINGVIEW LIGHT-THEME CSS ---
st.markdown("""
<style>
    /* Base Theme & Font (TradingView Light) */
    .stApp {
        background-color: #ffffff; 
        color: #131722;
        font-family: -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif;
    }
    
    /* Hide Default Chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Elegant Containers & Cards */
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: #ffffff;
        border-radius: 6px;
        border: 1px solid #e0e3eb;
        padding: 10px;
        box-shadow: 0px 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Sleek Expander/Tabs */
    .stTabs [data-baseweb="tab-list"] { background-color: #ffffff; border-bottom: 2px solid #e0e3eb; gap: 10px; }
    .stTabs [data-baseweb="tab"] { color: #787b86; padding: 10px 15px; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #2962FF !important; border-bottom: 2px solid #2962FF !important; }
    
    /* Metric Styling */
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; font-weight: 700; color: #131722;}
    [data-testid="stMetricDelta"] svg { display: none; } /* Hide arrow, rely on color */
    
    /* Dataframes (Watchlist) */
    [data-testid="stDataFrame"] { border: none !important; }
    
    /* Scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #f0f3fa; }
    ::-webkit-scrollbar-thumb { background: #c1c4cd; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #a1a5af; }
    
    /* Headers & Text */
    h1, h2, h3, h4, h5, h6 { color: #131722 !important; font-weight: 600 !important; }
    p, span, div { color: #131722; }
    hr { border-color: #e0e3eb; margin-top: 10px; margin-bottom: 10px;}
    
    /* Custom button styling for the expand icon */
    .stButton > button { border: 1px solid #e0e3eb; background-color: transparent; color: #787b86; transition: 0.3s;}
    .stButton > button:hover { border: 1px solid #2962FF; color: #2962FF; background-color: #f0f3fa;}
</style>
""", unsafe_allow_html=True)

st.title("🌍 Ratio Charts Conviction Builder")

# --- STATE MANAGEMENT (ASSETS & WATCHLISTS) ---
if 'asset_dict' not in st.session_state:
    st.session_state.asset_dict = {
        "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Dow Jones": "^DJI", "Russell 2000": "^RUT", "VIX": "^VIX",
        "Broad Market 500 (IND)": "BSE-500.BO", "Nifty 50": "^NSEI", 
        "Nifty Bank": "^NSEBANK", "Nifty IT": "^CNXIT", "Nifty Auto": "^CNXAUTO", "Nifty Pharma": "^CNXPHARMA", 
        "Nifty Metal": "^CNXMETAL", "Nifty Energy": "^CNXENERGY", "Nifty FMCG": "^CNXFMCG", "Nifty Realty": "^CNXREALTY", "Nifty PSU Bank": "^CNXPSUBANK",
        "Gold (Spot)": "GC=F", "Silver": "SI=F", "Crude Oil": "CL=F", "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD",
        "US 20+ Yr Treasury": "TLT", "US Tech ETF": "XLK", "US Fin ETF": "XLF", "US Healthcare ETF": "XLV", "US Energy ETF": "XLE", "Emerging Markets": "EEM"
    }

if 'watchlists' not in st.session_state:
    st.session_state.watchlists = {
        "⭐ My Favorites": {"S&P 500": "^GSPC", "Nifty 50": "^NSEI", "Gold (Spot)": "GC=F", "Bitcoin": "BTC-USD"},
        "🔥 Tech Watch": {"Nasdaq 100": "^NDX", "US Tech ETF": "XLK", "Nifty IT": "^CNXIT"}
    }
if 'active_wl' not in st.session_state:
    st.session_state.active_wl = "⭐ My Favorites"

# --- SIDEBAR CONTROLS ---
st.sidebar.title("⚙️ Builder Settings")

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
st.sidebar.header("📊 Dynamic Chart Settings")
asset_options = ["None"] + list(st.session_state.asset_dict.keys())
selected_asset_name = st.sidebar.selectbox("Numerator", asset_options, index=1) 
benchmark_name = st.sidebar.selectbox("Denominator", asset_options, index=0) 

c1, c2 = st.sidebar.columns(2)
with c1: timeframe = st.selectbox("Lookback", ("1mo", "3mo", "6mo", "1y", "2y", "5y", "max"), index=2)
with c2: interval_selection = st.selectbox("Interval", ("1d", "1wk", "1mo"))
chart_type = st.sidebar.selectbox("Style", ("Candlestick", "Bar (OHLC)", "Line"))

st.sidebar.markdown("---")
st.sidebar.header("📈 Indicators & Features")
show_volume = st.sidebar.checkbox("Show Volume Bar", value=True)
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
        data = yf.download(tkrs, period="5d", interval="1d", progress=False)
        
        if isinstance(data.columns, pd.MultiIndex):
            if 'Close' in data.columns.levels[0]: data = data['Close']
            else: return pd.DataFrame()
        else:
            if 'Close' in data.columns: data = data[['Close']].rename(columns={'Close': tkrs[0]})
            else: return pd.DataFrame()
            
        results = []
        for name, tk in tickers_dict.items():
            if tk in data.columns:
                col = data[tk].dropna()
                if len(col) >= 2:
                    last, prev = col.iloc[-1], col.iloc[-2]
                    chg = ((last - prev) / prev) * 100
                    results.append({"Asset": name, "Price": round(last, 2), "Chg %": round(chg, 2)})
                elif len(col) == 1:
                    results.append({"Asset": name, "Price": round(col.iloc[-1], 2), "Chg %": 0.00})
        return pd.DataFrame(results)
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_market_news():
    feed_urls = ["https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"]
    news_items, seen = [], set()
    current_time = time.time()
    target_keywords = ['rate', 'yield', 'treasury', 'inflation', 'cpi', 'fed', 'rbi', 'bank', 'earnings', 'revenue', 'acquire', 'merger', 'war', 'tariff', 'geopolitic']
    
    for url in feed_urls:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:25]:
                # 24-Hour News Filter Logic
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_time = time.mktime(entry.published_parsed)
                    if current_time - pub_time > 86400: # Skip if older than 24 hours (86,400 seconds)
                        continue 
                
                if entry.title not in seen and any(kw in entry.title.lower() for kw in target_keywords):
                    pub_date = entry.get("published", entry.get("pubDate", "Recent"))
                    news_items.append({"title": entry.title, "link": entry.link, "published": pub_date})
                    seen.add(entry.title)
        except: continue
    return news_items[:15]

# --- TRADINGVIEW CHART ENGINE ---
TV_CONFIG = {
    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape'],
    'displayModeBar': True,
    'displaylogo': False,
    'scrollZoom': True
}

def render_chart(num_name, den_name, period_str, interval_str, c_type, overlays, oscillators, show_vol=True, height=650):
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

    # Structure Subplots dynamically
    has_volume = 'Volume_num' in df.columns and show_vol
    num_rows = 1 + (1 if has_volume else 0) + len(oscillators)
    
    row_heights = [0.6]
    if has_volume: row_heights.append(0.15)
    row_heights.extend([0.15] * len(oscillators))
    row_heights = [h / sum(row_heights) for h in row_heights] # Normalize
    
    fig = make_subplots(rows=num_rows, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=row_heights)

    TV_GREEN, TV_RED, TV_BLUE, TV_GRID, BG = '#089981', '#f23645', '#2962FF', '#e0e3eb', '#ffffff'

    # 1. Price Candlesticks
    if c_type == "Line": fig.add_trace(go.Scatter(x=df.index, y=c, line=dict(color=TV_BLUE, width=1.5)), row=1, col=1)
    elif c_type == "Bar (OHLC)": fig.add_trace(go.Ohlc(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=c, increasing_line_color=TV_GREEN, decreasing_line_color=TV_RED), row=1, col=1)
    else: fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=c, increasing_line_color=TV_GREEN, increasing_fillcolor=TV_GREEN, decreasing_line_color=TV_RED, decreasing_fillcolor=TV_RED), row=1, col=1)

    colors = {"21 EMA": "#FF9800", "50 SMA": "#2962FF", "200 EMA": "#F44336", "AVWAP": "#000000"}
    for ind in overlays:
        if ind in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[ind], line=dict(color=colors.get(ind, '#000'), width=1)), row=1, col=1)

    curr_row = 2
    
    # 2. Volume Bar Chart (Green/Red based on candle close)
    if has_volume:
        vol_colors = ['rgba(8, 153, 129, 0.5)' if row['Ratio_Close'] >= row['Ratio_Open'] else 'rgba(242, 54, 69, 0.5)' for _, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume_num'], marker_color=vol_colors, name="Volume"), row=curr_row, col=1)
        fig.update_yaxes(title_text="Vol", row=curr_row, col=1, showgrid=False)
        curr_row += 1

    # 3. Oscillators
    if "RSI (14)" in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#7E57C2', width=1)), row=curr_row, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color='#787b86', row=curr_row, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color='#787b86', row=curr_row, col=1)
        fig.update_yaxes(range=[0, 100], title_text="RSI", row=curr_row, col=1); curr_row += 1
        
    if "MACD (12, 26, 9)" in oscillators:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Line'], line=dict(color=TV_BLUE, width=1)), row=curr_row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='#FF9800', width=1)), row=curr_row, col=1)
        hc = [TV_GREEN if v >= 0 else TV_RED for v in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=hc), row=curr_row, col=1)
        fig.update_yaxes(title_text="MACD", row=curr_row, col=1)

    # Layout Formatting
    fig.update_layout(
        template="plotly_white", plot_bgcolor=BG, paper_bgcolor=BG,
        xaxis_rangeslider_visible=False, height=height, margin=dict(l=10, r=45, t=10, b=10), showlegend=False,
        hovermode="x unified", dragmode="pan", font=dict(color="#131722", size=11)
    )
    
    x_format, d_tick = ("%d %b %Y", None) if period_str in ["1mo", "3mo", "6mo"] else ("%b %Y", "M1" if period_str == "1y" else "M3")
    
    # Enable TradingView Style Crosshairs (Spike Lines) on all axes
    fig.update_xaxes(
        showgrid=True, gridcolor=TV_GRID, tickformat=x_format, dtick=d_tick,
        showspikes=True, spikecolor="#787b86", spikesnap="cursor", spikemode="across", spikethickness=1, spikedash="dash"
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=TV_GRID, side="right", tickformat=".2f" if den_name == "None" else ".4f",
        showspikes=True, spikecolor="#787b86", spikesnap="cursor", spikemode="across", spikethickness=1, spikedash="dash"
    )
    return fig

# --- MODAL: FULL SCREEN CHART VIEWER ---
@st.dialog("📈 Full Screen Analysis", width="large")
def expand_chart_modal(num_name, den_name):
    title = f"{num_name}" if den_name == "None" else f"{num_name} / {den_name}"
    st.markdown(f"### {title}")
    
    with st.spinner("Loading High-Res Interactive Engine..."):
        fig = render_chart(num_name, den_name, "1y", "1d", "Candlestick", ["50 SMA", "200 EMA"], ["RSI (14)"], show_vol=True, height=650)
        if fig:
            st.plotly_chart(fig, use_container_width=True, config=TV_CONFIG)


# --- REUSABLE PANELS ---
def render_watchlist(key_prefix):
    st.subheader("📋 Watchlists")
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            active_wl = st.selectbox(
                "Select Watchlist", 
                list(st.session_state.watchlists.keys()), 
                index=list(st.session_state.watchlists.keys()).index(st.session_state.active_wl), 
                label_visibility="collapsed",
                key=f"{key_prefix}_sel_wl"
            )
            st.session_state.active_wl = active_wl
        with col2:
            with st.popover("⚙️"):
                new_wl = st.text_input("New List Name", key=f"{key_prefix}_new_wl")
                if st.button("Create", key=f"{key_prefix}_btn_create") and new_wl:
                    st.session_state.watchlists[new_wl] = {}
                    st.session_state.active_wl = new_wl
                    st.rerun()
                if st.button("Delete Current", key=f"{key_prefix}_btn_del"):
                    if len(st.session_state.watchlists) > 1:
                        del st.session_state.watchlists[active_wl]
                        st.session_state.active_wl = list(st.session_state.watchlists.keys())[0]
                        st.rerun()

        c_add, c_rem = st.columns(2)
        with c_add:
            with st.popover("➕ Add"):
                sel_add = st.selectbox("Asset", list(st.session_state.asset_dict.keys()), key=f"{key_prefix}_sel_add")
                if st.button("Add", key=f"{key_prefix}_btn_add"):
                    st.session_state.watchlists[active_wl][sel_add] = st.session_state.asset_dict[sel_add]
                    st.rerun()
        with c_rem:
            with st.popover("➖ Remove"):
                if st.session_state.watchlists[active_wl]:
                    rem_sel = st.selectbox("Asset", list(st.session_state.watchlists[active_wl].keys()), key=f"{key_prefix}_sel_rem")
                    if st.button("Drop", key=f"{key_prefix}_btn_drop"):
                        del st.session_state.watchlists[active_wl][rem_sel]
                        st.rerun()
                else: st.caption("Empty List")

        wl_data = fetch_bulk_watchlist(st.session_state.watchlists[active_wl])
        if not wl_data.empty:
            df = pd.DataFrame(wl_data)
            styled_df = df.style.map(lambda x: 'color: #089981; font-weight: bold;' if x > 0 else 'color: #f23645; font-weight: bold;' if x < 0 else '', subset=['Chg %']).format({"Price": "{:.2f}", "Chg %": "{:+.2f}%"})
            st.dataframe(styled_df, hide_index=True, use_container_width=True)
        else:
            st.caption("No data or empty watchlist.")

def render_news_feed(height):
    st.subheader("📰 Recent Market News")
    with st.container(border=True, height=height):
        news = fetch_market_news()
        if not news: st.info("No updates in the last 24 hours matching criteria.")
        else:
            for item in news:
                st.markdown(f"**[{item['title']}]({item['link']})**")
                pub_str = item.get('published', 'Recent').replace('+0000', '').strip()
                st.caption(f"🕒 {pub_str}")
                st.markdown("---")


# --- DUAL SCREEN TABS ---
tab1, tab2 = st.tabs(["🖥️ Macro Overview (Grid)", "🔍 Dynamic Explorer"])

# --- SCREEN 1: THE MACRO GRID ---
with tab1:
    st.subheader("🌐 Live Global Markets")
    top_indices = ["S&P 500", "Nasdaq 100", "Nifty 50", "Gold (Spot)", "Bitcoin", "Crude Oil"]
    cols_top = st.columns(len(top_indices))
    
    for i, idx_name in enumerate(top_indices):
        with cols_top[i]:
            ticker = st.session_state.asset_dict[idx_name]
            data = fetch_yahoo_data(ticker, "5d", "1d")
            
            if data is not None and not data.empty and len(data) >= 2:
                try:
                    last_close = float(data['Close'].iloc[-1])
                    prev_close = float(data['Close'].iloc[-2])
                    pct_change = ((last_close - prev_close) / prev_close) * 100
                    st.metric(label=idx_name, value=f"{last_close:,.2f}", delta=f"{pct_change:.2f}%")
                except Exception:
                    st.metric(label=idx_name, value="Data Error")
            else:
                st.metric(label=idx_name, value="N/A")
            
            with st.expander("📊 Chart"):
                top_fig = render_chart(idx_name, "None", "1mo", "1d", "Candlestick", [], [], show_vol=True, height=250)
                if top_fig: 
                    top_fig.update_layout(margin=dict(l=10, r=40, t=10, b=10))
                    st.plotly_chart(top_fig, use_container_width=True, key=f"top_{i}", config=TV_CONFIG)
                    
    st.markdown("---")
    
    col_main, col_news = st.columns([3, 1]) 
    
    with col_main:
        macro_tabs = st.tabs(["🇮🇳 NSE Sectors", "🇺🇸 US Markets", "🌍 Global Assets & Yields"])
        
        with macro_tabs[0]:
            st.caption("Benchmark: Broad Market 500 (IND)")
            nse_list = ["Nifty Bank", "Nifty IT", "Nifty Auto", "Nifty Pharma", "Nifty Metal", "Nifty Energy", "Nifty FMCG", "Nifty Realty", "Nifty PSU Bank"]
            cols = st.columns(3)
            with st.spinner("Fetching NSE Data..."):
                for idx, sec in enumerate(nse_list):
                    with cols[idx % 3], st.container(border=True):
                        head1, head2 = st.columns([4, 1])
                        head1.markdown(f"**{sec}**")
                        if head2.button("🗖", key=f"btn_nse_{idx}", help="Open Full Interactive Chart"): 
                            expand_chart_modal(sec, "Broad Market 500 (IND)")
                            
                        fig = render_chart(sec, "Broad Market 500 (IND)", "6mo", "1d", "Candlestick", [], [], show_vol=True, height=300)
                        if fig: st.plotly_chart(fig, use_container_width=True, key=f"nse_c_{idx}", config=TV_CONFIG)
                        
        with macro_tabs[1]:
            st.caption("Benchmark: S&P 500")
            us_list = ["Nasdaq 100", "Russell 2000", "US Tech ETF", "US Fin ETF", "US Healthcare ETF", "US Energy ETF"]
            cols = st.columns(3)
            with st.spinner("Fetching US Data..."):
                for idx, sec in enumerate(us_list):
                    with cols[idx % 3], st.container(border=True):
                        head1, head2 = st.columns([4, 1])
                        head1.markdown(f"**{sec}**")
                        if head2.button("🗖", key=f"btn_us_{idx}", help="Open Full Interactive Chart"): 
                            expand_chart_modal(sec, "S&P 500")
                            
                        fig = render_chart(sec, "S&P 500", "6mo", "1d", "Candlestick", [], [], show_vol=True, height=300)
                        if fig: st.plotly_chart(fig, use_container_width=True, key=f"us_c_{idx}", config=TV_CONFIG)

        with macro_tabs[2]:
            st.caption("Ratios measuring Risk-On vs Risk-Off behaviors")
            macro_pairs = [
                ("Gold (Spot)", "S&P 500", "Safe Haven vs Equity"),
                ("US 20+ Yr Treasury", "S&P 500", "Bonds vs Equity"),
                ("Emerging Markets", "S&P 500", "EM vs Developed"),
                ("Bitcoin", "Gold (Spot)", "Digital vs Physical Gold")
            ]
            cols = st.columns(2)
            with st.spinner("Fetching Macro Data..."):
                for idx, (num, den, title) in enumerate(macro_pairs):
                    with cols[idx % 2], st.container(border=True):
                        head1, head2 = st.columns([6, 1])
                        head1.markdown(f"**{title}**<br>({num} / {den})", unsafe_allow_html=True)
                        if head2.button("🗖", key=f"btn_glb_{idx}", help="Open Full Interactive Chart"): 
                            expand_chart_modal(num, den)
                            
                        fig = render_chart(num, den, "6mo", "1d", "Candlestick", [], [], show_vol=True, height=320)
                        if fig: st.plotly_chart(fig, use_container_width=True, key=f"glb_c_{idx}", config=TV_CONFIG)

    with col_news:
        render_watchlist(key_prefix="tab1")
        st.markdown("<br>", unsafe_allow_html=True)
        render_news_feed(height=650)

# --- SCREEN 2: DYNAMIC EXPLORER ---
with tab2:
    col_dyn_main, col_dyn_news = st.columns([3, 1]) 
    
    with col_dyn_main:
        c1, c2 = st.columns([4, 1])
        
        if benchmark_name == "None" and selected_asset_name != "None":
            c1.subheader(f"Raw Price: {selected_asset_name}")
        elif selected_asset_name == "None" and benchmark_name != "None":
            c1.subheader(f"Inverse Price: 1 / {benchmark_name}")
        elif selected_asset_name == "None" and benchmark_name == "None":
            c1.subheader("No Assets Selected")
        else:
            c1.subheader(f"Ratio: {selected_asset_name} / {benchmark_name}")
            
        if c2.button("🔄 Clear Drawings"): st.rerun()

        with st.spinner("Rendering Chart..."), st.container(border=True):
            fig = render_chart(selected_asset_name, benchmark_name, timeframe, interval_selection, chart_type, selected_overlays, selected_oscillators, show_vol=show_volume, height=700)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config=TV_CONFIG)
            elif selected_asset_name == "None" and benchmark_name == "None":
                st.info("Please select an asset in the sidebar to begin charting.")
                    
    with col_dyn_news:
        render_watchlist(key_prefix="tab2")
        st.markdown("<br>", unsafe_allow_html=True)
        render_news_feed(height=400)

# --- TELEMETRY ---
st.markdown("---")
latency = round(time.time() - start_time, 2)
st.caption(f"🟢 **System:** Online | ⏱️ **Latency:** {latency}s | 📡 **Engines:** YF API + RSS | 🕒 **Sync:** {pd.Timestamp.now().strftime('%H:%M:%S UTC')} | 📦 **Assets:** {len(st.session_state.asset_dict)}")
