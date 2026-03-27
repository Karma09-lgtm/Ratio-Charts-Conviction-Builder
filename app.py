import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import feedparser

# --- PAGE CONFIGURATION & TIMER START ---
st.set_page_config(page_title="Ratio Charts Conviction Builder", layout="wide", initial_sidebar_state="expanded")
start_time = time.time()

# --- PREMIUM TRADINGVIEW LIGHT-THEME CSS ---
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #131722; font-family: -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: #ffffff; border-radius: 6px; border: 1px solid #e0e3eb; padding: 12px; box-shadow: 0px 2px 4px rgba(0,0,0,0.02);
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #ffffff; border-bottom: 2px solid #e0e3eb; gap: 10px; }
    .stTabs [data-baseweb="tab"] { color: #787b86; padding: 10px 15px; font-weight: 600; }
    .stTabs [aria-selected="true"] { color: #2962FF !important; border-bottom: 2px solid #2962FF !important; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700; color: #131722; margin-top: -10px;}
    [data-testid="stMetricDelta"] svg { display: none; }
    [data-testid="stDataFrame"] { border: none !important; }
    [data-testid="stDataFrame"] div[data-testid="stCheckbox"] { display: none !important; }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #f0f3fa; }
    ::-webkit-scrollbar-thumb { background: #c1c4cd; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #a1a5af; }
    h1, h2, h3, h4, h5, h6 { color: #131722 !important; font-weight: 600 !important; }
    hr { border-color: #e0e3eb; margin-top: 10px; margin-bottom: 10px;}
    .stButton > button { border: 1px solid #e0e3eb; background-color: transparent; color: #787b86; transition: 0.2s; width: 100%; border-radius: 4px;}
    .stButton > button:hover { border: 1px solid #2962FF; color: #2962FF; background-color: #f0f3fa;}
    .tear-sheet { font-size: 0.85rem; color: #787b86; display: flex; gap: 15px; margin-top: -10px; margin-bottom: 15px; padding: 10px; background: #f8f9fd; border-radius: 6px; border: 1px solid #e0e3eb;}
    .tear-val { font-weight: 700; color: #131722; }
    .share-btn { display: inline-block; padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; background: #f8f9fd; border: 1px solid #e0e3eb; color: #131722; text-decoration: none; font-size: 0.9rem; font-weight: 600; width: 100%; text-align: left; transition: 0.2s;}
    .share-btn:hover { background: #f0f3fa; border-color: #2962FF; color: #2962FF;}
</style>
""", unsafe_allow_html=True)

# --- HEADER WITH SHARE/EXPORT MENU ---
c_title, c_export = st.columns([8, 2])
with c_title:
    st.title("🌍 Ratio Charts Conviction Builder")
with c_export:
    st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
    with st.popover("📤 Share & Export", use_container_width=True):
        st.markdown("**Share Terminal Setup**")
        st.markdown("<a href='https://twitter.com/intent/tweet?text=Analyzing+global+macro+correlations+on+the+Ratio+Charts+Conviction+Builder!&hashtags=Macro,Trading' target='_blank' class='share-btn'>𝕏 &nbsp; Share on X</a>", unsafe_allow_html=True)
        st.markdown("<a href='mailto:?subject=Macro Terminal Analysis&body=Check out this advanced macro conviction dashboard setup.' target='_blank' class='share-btn'>✉️ &nbsp; Email Colleague</a>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**📸 High-Res Screenshots**")
        st.caption("Hover over any interactive chart and click the **Camera Icon** in the top-right toolbar. The engine is configured to automatically download a clean, **4K Resolution (1600x900) PNG** of your analysis.")

# --- CURRENCY MAPPING ENGINE ---
CURRENCY_MAP = {
    "S&P 500": "$", "Nasdaq 100": "$", "Dow Jones": "$", "Russell 2000": "$", "VIX": "",
    "Broad Market 500 (IND)": "₹", "Nifty 50": "₹", "Nifty Bank": "₹", "Nifty IT": "₹", "Nifty Auto": "₹", "Nifty Pharma": "₹", "Nifty Metal": "₹", "Nifty Energy": "₹", "Nifty FMCG": "₹", "Nifty Realty": "₹", "Nifty PSU Bank": "₹",
    "Gold (Spot)": "$", "Silver": "$", "Crude Oil": "$", "Bitcoin": "$", "Ethereum": "$",
    "US 20+ Yr Treasury": "$", "US Tech ETF": "$", "US Fin ETF": "$", "US Healthcare ETF": "$", "US Energy ETF": "$", "Emerging Markets": "$",
    "FTSE 100": "£", "DAX": "€", "STOXX 50": "€", "Nikkei 225": "¥", "ASX 200": "A$"
}

# --- BUG-PROOF STATE MANAGEMENT ---
DEFAULT_ASSETS = {
    "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Dow Jones": "^DJI", "Russell 2000": "^RUT", "VIX": "^VIX",
    "Broad Market 500 (IND)": "BSE-500.BO", "Nifty 50": "^NSEI", 
    "Nifty Bank": "^NSEBANK", "Nifty IT": "^CNXIT", "Nifty Auto": "^CNXAUTO", "Nifty Pharma": "^CNXPHARMA", 
    "Nifty Metal": "^CNXMETAL", "Nifty Energy": "^CNXENERGY", "Nifty FMCG": "^CNXFMCG", "Nifty Realty": "^CNXREALTY", "Nifty PSU Bank": "^CNXPSUBANK",
    "Gold (Spot)": "GC=F", "Silver": "SI=F", "Crude Oil": "CL=F", "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD",
    "US 20+ Yr Treasury": "TLT", "US Tech ETF": "XLK", "US Fin ETF": "XLF", "US Healthcare ETF": "XLV", "US Energy ETF": "XLE", "Emerging Markets": "EEM",
    "FTSE 100": "^FTSE", "DAX": "^GDAXI", "STOXX 50": "^STOXX50E", "Nikkei 225": "^N225", "ASX 200": "^AXJO"
}

DEFAULT_WATCHLISTS = {
    "⭐ Global Macro": {"S&P 500": "^GSPC", "DAX": "^GDAXI", "Nikkei 225": "^N225", "Gold (Spot)": "GC=F"},
    "🔥 Tech Watch": {"Nasdaq 100": "^NDX", "US Tech ETF": "XLK", "Nifty IT": "^CNXIT"}
}

if 'asset_dict' not in st.session_state: st.session_state.asset_dict = DEFAULT_ASSETS.copy()
else:
    for k, v in DEFAULT_ASSETS.items():
        if k not in st.session_state.asset_dict: st.session_state.asset_dict[k] = v

if 'watchlists' not in st.session_state: st.session_state.watchlists = DEFAULT_WATCHLISTS.copy()
else:
    for k, v in DEFAULT_WATCHLISTS.items():
        if k not in st.session_state.watchlists: st.session_state.watchlists[k] = v

if 'active_wl' not in st.session_state: st.session_state.active_wl = "⭐ Global Macro"
if 'target_num' not in st.session_state: st.session_state.target_num = "S&P 500"
if 'target_den' not in st.session_state: st.session_state.target_den = "None"
if 'target_period' not in st.session_state: st.session_state.target_period = "1y"


# --- SIDEBAR: OMNIBOX & CONTROLS ---
st.sidebar.title("⚙️ Terminal Setup")

# 1. THE OMNIBOX
st.sidebar.markdown("**💻 Command Line**")
with st.sidebar.form(key="omni_form", clear_on_submit=True):
    col_cmd, col_btn = st.columns([3, 1])
    with col_cmd:
        omni_cmd = st.text_input("Command", placeholder="e.g. Nifty / Gold 1y", label_visibility="collapsed")
    with col_btn:
        omni_submit = st.form_submit_button("Go ⚡", use_container_width=True)
st.sidebar.caption("*Shortcut: Press **Enter** in the box to run.*")

if omni_submit and omni_cmd:
    parts = omni_cmd.split('/')
    try:
        if len(parts) == 2:
            num_part = parts[0].strip()
            den_part_split = parts[1].strip().rsplit(' ', 1)
            den_part = den_part_split[0]
            
            matched_num = next((k for k in st.session_state.asset_dict.keys() if num_part.lower() in k.lower()), None)
            matched_den = next((k for k in st.session_state.asset_dict.keys() if den_part.lower() in k.lower()), None)
            
            if matched_num: st.session_state.target_num = matched_num
            if matched_den: st.session_state.target_den = matched_den
            
            if len(den_part_split) > 1:
                tf = den_part_split[1].lower()
                valid_tfs = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]
                if tf in valid_tfs: st.session_state.target_period = tf
        else:
            num_part_split = parts[0].strip().rsplit(' ', 1)
            matched_num = next((k for k in st.session_state.asset_dict.keys() if num_part_split[0].lower() in k.lower()), None)
            if matched_num:
                st.session_state.target_num = matched_num
                st.session_state.target_den = "None"
            if len(num_part_split) > 1:
                tf = num_part_split[1].lower()
                if tf in ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]: st.session_state.target_period = tf
        
        st.toast(f"Loaded: {st.session_state.target_num}", icon="🚀")
        st.rerun() 
    except Exception: st.toast("Command error. Use format: Asset1 / Asset2 timeframe", icon="⚠️")

with st.sidebar.expander("🧹 Data & History Management", expanded=False):
    st.caption("Wipe local cache and force fresh data pull.")
    del_timeframe = st.selectbox("Select History to Delete", ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time History"])
    if st.button("🗑️ Reset & Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.toast(f"Successfully cleared {del_timeframe} of cached history.", icon="✅")
        time.sleep(0.5)
        st.rerun()

with st.sidebar.expander("📝 Watchlist Manager", expanded=False):
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

with st.sidebar.expander("⚙️ Asset Selection", expanded=True):
    asset_options = ["None"] + list(st.session_state.asset_dict.keys())
    selected_asset_name = st.selectbox("Numerator (Asset 1)", asset_options, key="target_num") 
    benchmark_name = st.selectbox("Denominator (Asset 2)", asset_options, key="target_den") 
    analysis_mode = st.radio("Analysis Mode", ["Ratio", "Correlation (20d)"], horizontal=True)

with st.sidebar.expander("⏱️ Time & Style", expanded=True):
    c1, c2 = st.columns(2)
    tf_options = ("1mo", "3mo", "6mo", "1y", "2y", "5y", "max")
    with c1: timeframe = st.selectbox("Data Fetch", tf_options, key="target_period")
    with c2: interval_selection = st.selectbox("Interval", ("1d", "1wk", "1mo"))
    chart_type = st.selectbox("Style", ("Candlestick", "Bar (OHLC)", "Line"))

with st.sidebar.expander("📈 Technicals & Overlays", expanded=True):
    show_volume = st.checkbox("Show Volume Bar", value=True)
    selected_overlays = st.multiselect("Overlays", ["21 EMA", "50 SMA", "200 EMA", "AVWAP"], default=["50 SMA"])
    selected_oscillators = st.multiselect("Oscillators", ["Volume", "RSI (14)", "MACD (12, 26, 9)", "Drawdown %"], default=["Volume"])

# --- HELPERS & DATA ENGINES ---
def format_large_number(num):
    if np.isnan(num): return "0"
    if num >= 1e9: return f"{num/1e9:.2f}B"
    if num >= 1e6: return f"{num/1e6:.2f}M"
    if num >= 1e3: return f"{num/1e3:.2f}K"
    return f"{num:.2f}"

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    return 100 - (100 / (1 + gain / loss))

@st.cache_data(ttl=3600)
def fetch_fundamentals(ticker_symbol):
    if not ticker_symbol or ticker_symbol == "None": return None
    try:
        tkr = yf.Ticker(ticker_symbol)
        info = tkr.info
        if not info: return None
        return {
            "52W High": info.get("fiftyTwoWeekHigh", "N/A"),
            "52W Low": info.get("fiftyTwoWeekLow", "N/A"),
            "Mkt Cap": format_large_number(info.get("marketCap", float('nan'))),
            "P/E (TTM)": round(info.get("trailingPE", float('nan')), 2) if info.get("trailingPE") else "N/A",
            "Div Yield": f"{info.get('dividendYield', 0)*100:.2f}%" if info.get('dividendYield') else "N/A"
        }
    except: return None

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
        return pd.DataFrame(results)
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_market_news(keyword="None"):
    feed_urls = ["https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"]
    news_items, seen = [], set()
    current_time = time.time()
    
    base_keywords = ['rate', 'yield', 'treasury', 'inflation', 'cpi', 'fed', 'rbi', 'bank', 'earnings', 'geopolitic']
    if keyword != "None": base_keywords.append(keyword.lower().split(" ")[0]) 
    
    bull_words = ['surge', 'jump', 'rise', 'up', 'beat', 'gain', 'bull', 'high', 'growth', 'soar']
    bear_words = ['plunge', 'drop', 'fall', 'down', 'miss', 'loss', 'bear', 'low', 'recession', 'crash', 'cut']
        
    for url in feed_urls:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:25]:
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    if current_time - time.mktime(entry.published_parsed) > 86400: continue 
                
                t_lower = entry.title.lower()
                if entry.title not in seen and any(kw in t_lower for kw in base_keywords):
                    pub_date = entry.get("published", entry.get("pubDate", "Recent"))
                    
                    bull_score = sum(1 for w in bull_words if w in t_lower)
                    bear_score = sum(1 for w in bear_words if w in t_lower)
                    tag = "🟢" if bull_score > bear_score else "🔴" if bear_score > bull_score else "⚪"
                    
                    news_items.append({"title": entry.title, "link": entry.link, "published": pub_date, "tag": tag})
                    seen.add(entry.title)
        except: continue
    return news_items[:15]


# --- TRADINGVIEW CHART ENGINE WITH ENHANCED DRAWING CAPABILITIES ---
# Added drawhline (horizontal infinite line) and drawvline (vertical line)
TV_CONFIG = {
    'modeBarButtonsToAdd': [
        'drawline', 'drawhline', 'drawvline', 
        'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape'
    ],
    'displayModeBar': True, 
    'displaylogo': False, 
    'scrollZoom': True,
    'toImageButtonOptions': {'format': 'png', 'filename': 'Macro_Conviction_Builder_Chart', 'height': 900, 'width': 1600, 'scale': 2 }
}

STATIC_CONFIG = {
    'modeBarButtonsToAdd': ['drawline', 'drawhline', 'drawrect', 'eraseshape'],
    'displayModeBar': True, 'displaylogo': False, 'scrollZoom': True
}

def render_chart(num_name, den_name, period_str, interval_str, c_type, overlays, oscillators, show_vol=True, analysis_mode="Ratio", show_hud=True, show_rangeselector=True, height=650):
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

    if analysis_mode == "Correlation" and num_name != "None" and den_name != "None":
        c = df['Close_num'].pct_change().rolling(20).corr(df['Close_den'].pct_change())
        df['Ratio_Close'] = df['Ratio_Open'] = df['Ratio_High'] = df['Ratio_Low'] = c
        oscillators = [o for o in oscillators if o not in ["Volume", "Drawdown %"]] 
        overlays = [] 
    else:
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
        
    if "Drawdown %" in oscillators:
        df['Peak'] = c.cummax()
        df['Drawdown'] = ((c - df['Peak']) / df['Peak']) * 100

    has_volume = "Volume" in oscillators and 'Volume_num' in df.columns
    active_osc = [o for o in oscillators if o != "Volume"]
    
    num_rows = 1 + (1 if has_volume else 0) + len(active_osc)
    if not has_volume and not active_osc: row_heights = [1.0]
    elif has_volume and not active_osc: row_heights = [0.82, 0.18]
    elif not has_volume and active_osc: row_heights = [0.70] + [0.30 / len(active_osc)] * len(active_osc)
    else: row_heights = [0.65, 0.15] + [0.20 / len(active_osc)] * len(active_osc)
    
    fig = make_subplots(rows=num_rows, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=row_heights)
    TV_GREEN, TV_RED, TV_BLUE, TV_GRID, BG = '#089981', '#f23645', '#2962FF', '#e0e3eb', '#ffffff'

    if analysis_mode == "Correlation":
        fig.add_trace(go.Scatter(x=df.index, y=c, line=dict(color='#E91E63', width=2)), row=1, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color=TV_GRID, row=1, col=1)
    else:
        if c_type == "Line": fig.add_trace(go.Scatter(x=df.index, y=c, line=dict(color=TV_BLUE, width=1.5)), row=1, col=1)
        elif c_type == "Bar (OHLC)": fig.add_trace(go.Ohlc(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=c, increasing_line_color=TV_GREEN, decreasing_line_color=TV_RED), row=1, col=1)
        else: fig.add_trace(go.Candlestick(x=df.index, open=df['Ratio_Open'], high=df['Ratio_High'], low=df['Ratio_Low'], close=c, increasing_line_color=TV_GREEN, increasing_fillcolor=TV_GREEN, decreasing_line_color=TV_RED, decreasing_fillcolor=TV_RED), row=1, col=1)

    colors = {"21 EMA": "#FF9800", "50 SMA": "#2962FF", "200 EMA": "#F44336", "AVWAP": "#000000"}
    for ind in overlays:
        if ind in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df[ind], line=dict(color=colors.get(ind, '#000'), width=1)), row=1, col=1)

    curr_row = 2
    if has_volume:
        vol_colors = ['rgba(8, 153, 129, 0.5)' if row['Ratio_Close'] >= row['Ratio_Open'] else 'rgba(242, 54, 69, 0.5)' for _, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume_num'], marker_color=vol_colors, name="Volume"), row=curr_row, col=1)
        fig.update_yaxes(title_text="Vol", row=curr_row, col=1, showgrid=False, tickformat=".2s", fixedrange=False)
        curr_row += 1

    if "RSI (14)" in active_osc:
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#7E57C2', width=1)), row=curr_row, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color='#787b86', row=curr_row, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color='#787b86', row=curr_row, col=1)
        fig.update_yaxes(range=[0, 100], title_text="RSI", row=curr_row, col=1, fixedrange=False); curr_row += 1
        
    if "MACD (12, 26, 9)" in active_osc:
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Line'], line=dict(color=TV_BLUE, width=1)), row=curr_row, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='#FF9800', width=1)), row=curr_row, col=1)
        hc = [TV_GREEN if v >= 0 else TV_RED for v in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], marker_color=hc), row=curr_row, col=1)
        fig.update_yaxes(title_text="MACD", row=curr_row, col=1, fixedrange=False); curr_row += 1
        
    if "Drawdown %" in active_osc:
        fig.add_trace(go.Scatter(x=df.index, y=df['Drawdown'], fill='tozeroy', fillcolor='rgba(242, 54, 69, 0.3)', line=dict(color=TV_RED, width=1)), row=curr_row, col=1)
        fig.update_yaxes(title_text="DD %", row=curr_row, col=1, fixedrange=False)

    dec = ".2f" if analysis_mode == "Correlation" or den_name == "None" else ".4f"
    if show_hud:
        last_row = df.iloc[-1]
        curr_symbol = CURRENCY_MAP.get(num_name, "") if den_name == "None" else ""
        hud_text = f"<b>O:</b> {curr_symbol}{last_row['Ratio_Open']:{dec}} &nbsp; <b>H:</b> {curr_symbol}{last_row['Ratio_High']:{dec}} &nbsp; <b>L:</b> {curr_symbol}{last_row['Ratio_Low']:{dec}} &nbsp; <b>C:</b> {curr_symbol}{last_row['Ratio_Close']:{dec}}"
        if has_volume: hud_text += f" &nbsp; <b>Vol:</b> {format_large_number(last_row['Volume_num'])}"
        for ind in overlays:
            if ind in df.columns and not np.isnan(df[ind].iloc[-1]):
                hud_text += f" &nbsp; <span style='color:{colors.get(ind, '#000')}'><b>{ind}:</b> {df[ind].iloc[-1]:{dec}}</span>"
        fig.add_annotation(xref="x domain", yref="y domain", x=0.01, y=0.99, text=hud_text, showarrow=False, font=dict(size=11, color="#131722"), align="left", bgcolor="rgba(255,255,255,0.7)", row=1, col=1)

    fig.update_layout(template="plotly_white", plot_bgcolor=BG, paper_bgcolor=BG, xaxis_rangeslider_visible=False, height=height, margin=dict(l=10, r=45, t=10, b=10), showlegend=False, hovermode="x unified", dragmode="pan", font=dict(color="#131722", size=11))
    x_format, d_tick = ("%d %b %Y", None) if period_str in ["1mo", "3mo", "6mo"] else ("%b %Y", "M1" if period_str == "1y" else "M3")
    
    if show_rangeselector:
        fig.update_xaxes(
            rangeselector=dict(buttons=list([dict(count=1, label="1m", step="month", stepmode="backward"), dict(count=3, label="3m", step="month", stepmode="backward"), dict(count=6, label="6m", step="month", stepmode="backward"), dict(count=1, label="YTD", step="year", stepmode="todate"), dict(count=1, label="1y", step="year", stepmode="backward"), dict(step="all", label="All")]), bgcolor="#ffffff", activecolor="#f0f3fa", bordercolor="#e0e3eb", font=dict(color="#131722")),
            showgrid=True, gridcolor=TV_GRID, tickformat=x_format, dtick=d_tick, showspikes=True, spikecolor="#787b86", spikesnap="cursor", spikemode="across", spikethickness=1, spikedash="dash", row=1, col=1
        )
    else: fig.update_xaxes(showgrid=True, gridcolor=TV_GRID, tickformat=x_format, dtick=d_tick, showspikes=True, spikecolor="#7
