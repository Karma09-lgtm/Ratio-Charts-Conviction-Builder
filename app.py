import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
import feedparser
import json
import streamlit.components.v1 as components

# --- PAGE CONFIGURATION & TIMER START ---
st.set_page_config(page_title="Ratio Charts Conviction Builder", layout="wide", initial_sidebar_state="expanded")
start_time = time.time()

# --- PREMIUM TRADINGVIEW LIGHT-THEME CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fd; color: #131722; font-family: -apple-system, BlinkMacSystemFont, "Trebuchet MS", Roboto, Ubuntu, sans-serif; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
        background-color: #ffffff; border-radius: 8px; border: 1px solid #e0e3eb; padding: 12px; box-shadow: 0px 2px 4px rgba(19, 23, 34, 0.03);
    }
    
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; border-bottom: 2px solid #e0e3eb; gap: 20px; }
    .stTabs [data-baseweb="tab"] { color: #787b86; padding: 10px 5px; font-weight: 600; font-size: 1rem; }
    .stTabs [aria-selected="true"] { color: #2962FF !important; border-bottom: 2px solid #2962FF !important; }
    
    [data-testid="stMetricValue"] { font-size: 1.35rem !important; font-weight: 700; color: #131722; margin-top: -15px;}
    [data-testid="stMetricDelta"] { margin-top: -5px; }
    [data-testid="stMetricDelta"] svg { display: none; }
    
    [data-testid="stDataFrame"] { border: none !important; }
    [data-testid="stDataFrame"] div[data-testid="stCheckbox"] { display: none !important; }
    
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #f0f3fa; }
    ::-webkit-scrollbar-thumb { background: #c1c4cd; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #a1a5af; }
    
    h1, h2, h3, h4, h5, h6 { color: #131722 !important; font-weight: 600 !important; }
    hr { border-color: #e0e3eb; margin-top: 10px; margin-bottom: 10px;}
    
    .stButton > button { border: 1px solid #e0e3eb; background-color: #ffffff; color: #787b86; transition: 0.2s; width: 100%; border-radius: 6px; padding: 4px 8px; font-weight: 500;}
    .stButton > button:hover { border: 1px solid #2962FF; color: #2962FF; background-color: #f0f3fa;}
    .stButton > button:disabled { border: 1px solid #e0e3eb; background-color: #f8f9fd; color: #089981; font-weight: 600; opacity: 1; }
    
    .tear-sheet { font-size: 0.85rem; color: #787b86; display: flex; gap: 15px; margin-top: -10px; margin-bottom: 15px; padding: 10px; background: #f8f9fd; border-radius: 6px; border: 1px solid #e0e3eb;}
    .tear-val { font-weight: 700; color: #131722; }
    .share-btn { display: inline-block; padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; background: #ffffff; border: 1px solid #e0e3eb; color: #131722; text-decoration: none; font-size: 0.9rem; font-weight: 600; width: 100%; text-align: left; transition: 0.2s;}
    .share-btn:hover { background: #f0f3fa; border-color: #2962FF; color: #2962FF;}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
c_title, c_export = st.columns([8, 2])
with c_title: st.title("🌍 Ratio Charts Conviction Builder")
with c_export:
    st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
    with st.popover("📤 Share & Export", use_container_width=True):
        st.markdown("**Share Terminal Setup**")
        st.markdown("<a href='#' class='share-btn'>𝕏 &nbsp; Share on X</a>", unsafe_allow_html=True)

# --- CURRENCY MAPPING ---
CURRENCY_MAP = {
    "S&P 500": "$", "Nasdaq 100": "$", "Dow Jones": "$", "Russell 2000": "$", "VIX": "",
    "Broad Market 500 (IND)": "₹", "Nifty 50": "₹", "Nifty Bank": "₹", "Nifty IT": "₹", "Nifty Auto": "₹", "Nifty Pharma": "₹", "Nifty Metal": "₹", "Nifty Energy": "₹", "Nifty FMCG": "₹", "Nifty Realty": "₹", "Nifty PSU Bank": "₹",
    "Gold (Spot)": "$", "Silver": "$", "Crude Oil": "$", "Bitcoin": "$", "Ethereum": "$",
    "US 20+ Yr Treasury": "$", "US Tech ETF": "$", "US Fin ETF": "$", "US Healthcare ETF": "$", "US Energy ETF": "$", "Emerging Markets": "$",
    "FTSE 100": "£", "DAX": "€", "STOXX 50": "€", "Nikkei 225": "¥", "ASX 200": "A$"
}

# --- STATE MANAGEMENT ---
DEFAULT_ASSETS = {
    "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "Dow Jones": "^DJI", "Russell 2000": "^RUT", "VIX": "^VIX",
    "Broad Market 500 (IND)": "BSE-500.BO", "Nifty 50": "^NSEI", 
    "Nifty Bank": "^NSEBANK", "Nifty IT": "^CNXIT", "Nifty Auto": "^CNXAUTO", "Nifty Pharma": "^CNXPHARMA", 
    "Nifty Metal": "^CNXMETAL", "Nifty Energy": "^CNXENERGY", "Nifty FMCG": "^CNXFMCG", "Nifty Realty": "^CNXREALTY", "Nifty PSU Bank": "^CNXPSUBANK",
    "Gold (Spot)": "GC=F", "Silver": "SI=F", "Crude Oil": "CL=F", "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD",
    "US 20+ Yr Treasury": "TLT", "US Tech ETF": "XLK", "US Fin ETF": "XLF", "US Healthcare ETF": "XLV", "US Energy ETF": "XLE", "Emerging Markets": "EEM",
    "FTSE 100": "^FTSE", "DAX": "^GDAXI", "STOXX 50": "^STOXX50E", "Nikkei 225": "^N225", "ASX 200": "^AXJO"
}
DEFAULT_WATCHLISTS = {"⭐ Global Macro": {"S&P 500": "^GSPC", "DAX": "^GDAXI", "Nikkei 225": "^N225", "Gold (Spot)": "GC=F"}}

if 'asset_dict' not in st.session_state: st.session_state.asset_dict = DEFAULT_ASSETS.copy()
if 'watchlists' not in st.session_state: st.session_state.watchlists = DEFAULT_WATCHLISTS.copy()
if 'active_wl' not in st.session_state: st.session_state.active_wl = "⭐ Global Macro"
if 'target_num' not in st.session_state: st.session_state.target_num = "S&P 500"
if 'target_den' not in st.session_state: st.session_state.target_den = "None"
if 'target_period' not in st.session_state: st.session_state.target_period = "1y"
if 'fav_ratios' not in st.session_state: st.session_state.fav_ratios = [("Gold (Spot)", "S&P 500"), ("Nasdaq 100", "Russell 2000")]
if 'recent_ratios' not in st.session_state: st.session_state.recent_ratios = []

# --- SIDEBAR CONTROLS ---
st.sidebar.title("⚙️ Terminal Setup")

st.sidebar.markdown("**💻 Command Line**")
with st.sidebar.form(key="omni_form", clear_on_submit=True):
    col_cmd, col_btn = st.columns([3, 1])
    with col_cmd: omni_cmd = st.text_input("Command", placeholder="e.g. Nifty / Gold 1y", label_visibility="collapsed")
    with col_btn: omni_submit = st.form_submit_button("Go ⚡", use_container_width=True)

if omni_submit and omni_cmd:
    parts = omni_cmd.split('/')
    try:
        if len(parts) == 2:
            num_part, den_part_split = parts[0].strip(), parts[1].strip().rsplit(' ', 1)
            den_part = den_part_split[0]
            matched_num = next((k for k in st.session_state.asset_dict.keys() if num_part.lower() in k.lower()), None)
            matched_den = next((k for k in st.session_state.asset_dict.keys() if den_part.lower() in k.lower()), None)
            if matched_num: st.session_state.target_num = matched_num
            if matched_den: st.session_state.target_den = matched_den
            if len(den_part_split) > 1:
                tf = den_part_split[1].lower()
                if tf in ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]: st.session_state.target_period = tf
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
    except Exception: st.toast("Command error.", icon="⚠️")

with st.sidebar.expander("🧹 Data & History Management", expanded=False):
    st.caption("Wipe local cache and force fresh data pull.")
    del_timeframe = st.selectbox("Select History to Delete", ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time History"])
    if st.button("🗑️ Reset & Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cache cleared.", icon="✅")
        time.sleep(0.5)
        st.rerun()

st.sidebar.markdown("---")

with st.sidebar.expander("⚙️ Asset Selection", expanded=True):
    asset_options = ["None"] + list(st.session_state.asset_dict.keys())
    idx_num = asset_options.index(st.session_state.target_num) if st.session_state.target_num in asset_options else 1
    idx_den = asset_options.index(st.session_state.target_den) if st.session_state.target_den in asset_options else 0

    col_assets, col_inv = st.columns([5, 1])
    with col_assets:
        selected_num = st.selectbox("Numerator", asset_options, index=idx_num) 
        selected_den = st.selectbox("Denominator", asset_options, index=idx_den) 
        if selected_num != st.session_state.target_num or selected_den != st.session_state.target_den:
            st.session_state.target_num, st.session_state.target_den = selected_num, selected_den
            st.rerun()
    with col_inv:
        st.markdown("<div style='margin-top: 36px;'></div>", unsafe_allow_html=True)
        if st.button("🔄", help="Invert Ratio", use_container_width=True):
            st.session_state.target_num, st.session_state.target_den = st.session_state.target_den, st.session_state.target_num
            st.rerun()
            
    analysis_mode = st.radio("Analysis Mode", ["Ratio", "Correlation (20d)"], horizontal=True)

with st.sidebar.expander("⏱️ Time & Style", expanded=True):
    c1, c2 = st.columns(2)
    tf_options = ("1mo", "3mo", "6mo", "1y", "2y", "5y", "max")
    idx_tf = tf_options.index(st.session_state.target_period) if st.session_state.target_period in tf_options else 3
    with c1: 
        timeframe = st.selectbox("Data Fetch", tf_options, index=idx_tf)
        if timeframe != st.session_state.target_period:
            st.session_state.target_period = timeframe
            st.rerun()
    with c2: interval_selection = st.selectbox("Interval", ("1d", "1wk", "1mo"))
    chart_type = st.selectbox("Style", ("Candlestick", "Bar (OHLC)", "Line"))

with st.sidebar.expander("🎨 Drawing Toolbox (Dynamic Chart)", expanded=True):
    c_color, c_width = st.columns([1, 2])
    with c_color: draw_color = st.color_picker("Color", "#2962FF")
    with c_width: draw_width = st.slider("Thickness", 1, 5, 2)

with st.sidebar.expander("📈 Technicals & Overlays", expanded=True):
    show_volume = st.checkbox("Show Volume Bar", value=True)
    selected_overlays = st.multiselect("Overlays", ["21 EMA", "50 SMA", "200 EMA", "AVWAP"], default=["50 SMA"])
    selected_oscillators = st.multiselect("Oscillators", ["Volume", "RSI (14)", "MACD (12, 26, 9)", "Drawdown %"], default=["Volume"])

# --- DATA ENGINES ---
def format_large_number(num):
    if pd.isna(num): return "0"
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
        info = yf.Ticker(ticker_symbol).info
        if not info: return None
        return {
            "52W High": info.get("fiftyTwoWeekHigh", "N/A"), "52W Low": info.get("fiftyTwoWeekLow", "N/A"),
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
        return data.loc[:, ~data.columns.duplicated()]
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
                    results.append({"Asset": name, "Price": round(last, 2), "Chg %": round(((last - prev) / prev) * 100, 2)})
        return pd.DataFrame(results)
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_market_news(keyword="None"):
    urls = ["https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"]
    news, seen = [], set()
    base_kws = ['rate', 'yield', 'treasury', 'inflation', 'fed', 'bank', 'earnings']
    if keyword != "None": base_kws.append(keyword.lower().split(" ")[0]) 
    for url in urls:
        try:
            for entry in feedparser.parse(url).entries[:25]:
                t = entry.title.lower()
                if entry.title not in seen and any(kw in t for kw in base_kws):
                    tag = "🟢" if sum(1 for w in ['surge', 'jump', 'rise', 'gain'] if w in t) > sum(1 for w in ['plunge', 'drop', 'fall', 'cut'] if w in t) else "🔴"
                    news.append({"title": entry.title, "link": entry.link, "published": entry.get("published", "Recent"), "tag": tag})
                    seen.add(entry.title)
        except: continue
    return news[:10]


# --- UNIVERSAL TRADINGVIEW ENGINE ---
def generate_tv_html(num_name, den_name, period_str, interval_str, c_type, overlays, oscillators, show_vol, analysis_mode, show_hud=True, base_height=500, enable_drawing=False):
    if num_name == "None" and den_name == "None": 
        return "<div style='padding:20px; text-align:center; color:#787b86; font-family:sans-serif;'>No assets selected.</div>", base_height
    
    num_data = fetch_yahoo_data(st.session_state.asset_dict.get(num_name), period_str, interval_str) if num_name != "None" else None
    den_data = fetch_yahoo_data(st.session_state.asset_dict.get(den_name), period_str, interval_str) if den_name != "None" else None
    if (num_data is None and den_name == "None") or (den_data is None and num_name == "None"): 
        return "<div style='padding:20px; text-align:center; color:#f23645; font-family:sans-serif;'>Data unavailable.</div>", base_height

    base_df = num_data if num_data is not None else den_data
    if num_name == "None" or num_data is None:
        num_data = pd.DataFrame(1, index=base_df.index, columns=['Open', 'High', 'Low', 'Close'])
        if 'Volume' in base_df.columns: num_data['Volume'] = 1
    if den_name == "None" or den_data is None:
        den_data = pd.DataFrame(1, index=base_df.index, columns=['Open', 'High', 'Low', 'Close'])
        if 'Volume' in base_df.columns: den_data['Volume'] = 1

    df = pd.merge(num_data, den_data, left_index=True, right_index=True, suffixes=('_num', '_den')).dropna()
    if df.empty: return "<div style='padding:20px; text-align:center; color:#f23645; font-family:sans-serif;'>Data unavailable.</div>", base_height
    
    df = df[~df.index.duplicated(keep='first')].sort_index()
    df = df.replace([np.inf, -np.inf], np.nan)

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
        
    colors = {"21 EMA": "#FF9800", "50 SMA": "#2962FF", "200 EMA": "#F44336", "AVWAP": "#000000"}
    for ind in overlays:
        if ind == "50 SMA": df[ind] = df['Ratio_Close'].rolling(50).mean()
        if ind == "21 EMA": df[ind] = df['Ratio_Close'].ewm(span=21).mean()
        if ind == "200 EMA": df[ind] = df['Ratio_Close'].ewm(span=200).mean()
        if ind == "AVWAP" and 'Volume_num' in df.columns:
            df[ind] = ((df['Ratio_High'] + df['Ratio_Low'] + df['Ratio_Close'])/3 * df['Volume_num']).cumsum() / df['Volume_num'].cumsum()

    active_osc = [o for o in oscillators if o != "Volume"]
    for osc in active_osc:
        if osc == "RSI (14)": df['RSI'] = calculate_rsi(df['Ratio_Close'], 14)
        elif osc == "MACD (12, 26, 9)":
            df['MACD_Line'] = df['Ratio_Close'].ewm(span=12).mean() - df['Ratio_Close'].ewm(span=26).mean()
            df['MACD_Signal'] = df['MACD_Line'].ewm(span=9).mean()
            df['MACD_Hist'] = df['MACD_Line'] - df['MACD_Signal']
        elif osc == "Drawdown %":
            df['Peak'] = df['Ratio_Close'].cummax()
            df['Drawdown'] = ((df['Ratio_Close'] - df['Peak']) / df['Peak']) * 100

    if analysis_mode == "Correlation" or c_type == "Line":
        temp_main = df.dropna(subset=['Ratio_Close'])
        main_data = [{"time": d.strftime('%Y-%m-%d'), "value": float(row['Ratio_Close'])} for d, row in temp_main.iterrows()]
        c_type = "Line"
    else:
        temp_main = df.dropna(subset=['Ratio_Open', 'Ratio_High', 'Ratio_Low', 'Ratio_Close'])
        main_data = [{"time": d.strftime('%Y-%m-%d'), "open": float(row['Ratio_Open']), "high": float(row['Ratio_High']), "low": float(row['Ratio_Low']), "close": float(row['Ratio_Close'])} for d, row in temp_main.iterrows()]

    has_volume = "Volume" in oscillators and 'Volume_num' in df.columns
    vol_data = []
    if show_vol and has_volume:
        temp_vol = df.dropna(subset=['Volume_num'])
        for d, row in temp_vol.iterrows():
            c = '#08998180' if row.get('Ratio_Close', 0) >= row.get('Ratio_Open', 0) else '#f2364580'
            vol_data.append({"time": d.strftime('%Y-%m-%d'), "value": float(row['Volume_num']), "color": c})

    overlay_js = ""
    for ind in overlays:
        if ind in df.columns:
            temp_line = df.dropna(subset=[ind])
            line_data = [{"time": d.strftime('%Y-%m-%d'), "value": float(v)} for d, v in temp_line[ind].items()]
            overlay_js += f"const l_{ind.replace(' ', '')} = mainChart.addLineSeries({{ color: '{colors.get(ind, '#000')}', lineWidth: 2, title: '{ind}', crosshairMarkerVisible: false }}); l_{ind.replace(' ', '')}.setData({json.dumps(line_data)});\n"

    osc_js = ""
    for i, osc in enumerate(active_osc):
        div_id = f"subchart_{i}"
        if osc == "RSI (14)":
            temp_osc = df.dropna(subset=['RSI'])
            data = [{"time": d.strftime('%Y-%m-%d'), "value": float(v)} for d, v in temp_osc['RSI'].items()]
            osc_js += f"createSubchart('{div_id}', 'RSI', 'line', {json.dumps(data)}, '#7E57C2');\n"
        elif osc == "MACD (12, 26, 9)":
            temp_osc = df.dropna(subset=['MACD_Line', 'MACD_Signal', 'MACD_Hist'])
            m_line = [{"time": d.strftime('%Y-%m-%d'), "value": float(v)} for d, v in temp_osc['MACD_Line'].items()]
            m_sig = [{"time": d.strftime('%Y-%m-%d'), "value": float(v)} for d, v in temp_osc['MACD_Signal'].items()]
            m_hist = [{"time": d.strftime('%Y-%m-%d'), "value": float(v), "color": '#089981' if v>=0 else '#f23645'} for d, v in temp_osc['MACD_Hist'].items()]
            osc_js += f"createMacdChart('{div_id}', {json.dumps(m_line)}, {json.dumps(m_sig)}, {json.dumps(m_hist)});\n"
        elif osc == "Drawdown %":
            temp_osc = df.dropna(subset=['Drawdown'])
            data = [{"time": d.strftime('%Y-%m-%d'), "value": float(v)} for d, v in temp_osc['Drawdown'].items()]
            osc_js += f"createSubchart('{div_id}', 'Drawdown %', 'area', {json.dumps(data)}, '#f23645');\n"

    hud_display = "block" if show_hud else "none"
    title_text = f"{num_name}" + (f" / {den_name}" if den_name != "None" else "")

    # Inject custom drawing layer if requested
    drawing_html = ""
    drawing_js = ""
    if enable_drawing:
        drawing_html = """
        <div id="drawing-toolbar">
            <button onclick="setTool('pan')" id="btn-pan" class="active">🖐️ Pan</button>
            <button onclick="setTool('line')" id="btn-line">📏 Trendline</button>
            <button onclick="setTool('text')" id="btn-text">🔤 Text</button>
            <button onclick="setTool('eraser')" id="btn-eraser">🧽 Eraser</button>
            <button onclick="clearDrawings()">🗑️ Clear</button>
        </div>
        <canvas id="drawing-layer"></canvas>
        """
        drawing_js = f"""
        const canvas = document.getElementById('drawing-layer');
        const ctx = canvas.getContext('2d');
        let tool = 'pan';
        let drawings = [];
        let isDrawing = false;
        let startPoint = null;
        let currentMouse = null;
        let dColor = '{draw_color}';
        let dWidth = {draw_width};

        function setTool(t) {{
            tool = t;
            document.querySelectorAll('#drawing-toolbar button').forEach(b => b.classList.remove('active'));
            document.getElementById('btn-'+t).classList.add('active');
            canvas.style.pointerEvents = (t === 'pan') ? 'none' : 'auto';
        }}

        function clearDrawings() {{ drawings = []; redrawCanvas(); }}

        function getLogicalCoords(e) {{
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            return {{ 
                logical: mainChart.timeScale().coordinateToLogical(x), 
                price: mainSeries.coordinateToPrice(y) 
            }};
        }}

        canvas.addEventListener('mousedown', e => {{
            const pos = getLogicalCoords(e);
            if (tool === 'line') {{
                isDrawing = true;
                startPoint = pos;
            }} else if (tool === 'text') {{
                const txt = prompt("Enter text annotation:");
                if(txt) {{
                    drawings.push({{type: 'text', p: pos, text: txt, color: dColor}});
                    redrawCanvas();
                }}
                setTool('pan');
            }} else if (tool === 'eraser') {{
                const rect = canvas.getBoundingClientRect();
                const mx = e.clientX - rect.left;
                const my = e.clientY - rect.top;
                
                // Simple distance checking to erase
                drawings = drawings.filter(d => {{
                    if(d.type === 'text') {{
                        let px = mainChart.timeScale().logicalToCoordinate(d.p.logical);
                        let py = mainSeries.priceToCoordinate(d.p.price);
                        return Math.hypot(px-mx, py-my) > 20;
                    }} else if(d.type === 'line') {{
                        let x1 = mainChart.timeScale().logicalToCoordinate(d.p1.logical);
                        let y1 = mainSeries.priceToCoordinate(d.p1.price);
                        let x2 = mainChart.timeScale().logicalToCoordinate(d.p2.logical);
                        let y2 = mainSeries.priceToCoordinate(d.p2.price);
                        // Math to distance from point to line segment
                        let l2 = (x1-x2)*(x1-x2) + (y1-y2)*(y1-y2);
                        if (l2 == 0) return Math.hypot(x1-mx, y1-my) > 10;
                        let t = Math.max(0, Math.min(1, ((mx - x1) * (x2 - x1) + (my - y1) * (y2 - y1)) / l2));
                        let projX = x1 + t * (x2 - x1);
                        let projY = y1 + t * (y2 - y1);
                        return Math.hypot(mx - projX, my - projY) > 10;
                    }}
                    return true;
                }});
                redrawCanvas();
            }}
        }});

        canvas.addEventListener('mousemove', e => {{
            if(isDrawing && tool === 'line') {{
                currentMouse = getLogicalCoords(e);
            }}
        }});

        canvas.addEventListener('mouseup', e => {{
            if (isDrawing && tool === 'line') {{
                drawings.push({{type: 'line', p1: startPoint, p2: getLogicalCoords(e), color: dColor, width: dWidth}});
                isDrawing = false;
                startPoint = null;
                currentMouse = null;
                redrawCanvas();
                setTool('pan');
            }}
        }});

        function redrawCanvas() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            drawings.forEach(d => {{
                if (d.type === 'line') {{
                    let x1 = mainChart.timeScale().logicalToCoordinate(d.p1.logical);
                    let y1 = mainSeries.priceToCoordinate(d.p1.price);
                    let x2 = mainChart.timeScale().logicalToCoordinate(d.p2.logical);
                    let y2 = mainSeries.priceToCoordinate(d.p2.price);
                    if(x1 !== null && y1 !== null && x2 !== null && y2 !== null) {{
                        ctx.beginPath();
                        ctx.moveTo(x1, y1);
                        ctx.lineTo(x2, y2);
                        ctx.strokeStyle = d.color;
                        ctx.lineWidth = d.width;
                        ctx.stroke();
                    }}
                }} else if (d.type === 'text') {{
                    let x = mainChart.timeScale().logicalToCoordinate(d.p.logical);
                    let y = mainSeries.priceToCoordinate(d.p.price);
                    if(x !== null && y !== null) {{
                        ctx.font = "bold 14px sans-serif";
                        ctx.fillStyle = d.color;
                        ctx.fillText(d.text, x, y);
                    }}
                }}
            }});
            
            // Draw current active line
            if (isDrawing && startPoint && currentMouse) {{
                let x1 = mainChart.timeScale().logicalToCoordinate(startPoint.logical);
                let y1 = mainSeries.priceToCoordinate(startPoint.price);
                let x2 = mainChart.timeScale().logicalToCoordinate(currentMouse.logical);
                let y2 = mainSeries.priceToCoordinate(currentMouse.price);
                if(x1 !== null && y1 !== null && x2 !== null && y2 !== null) {{
                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                    ctx.strokeStyle = dColor;
                    ctx.lineWidth = dWidth;
                    ctx.stroke();
                }}
            }}
        }}

        // Animation loop keeps drawings perfectly anchored to the chart!
        function animate() {{
            redrawCanvas();
            requestAnimationFrame(animate);
        }}
        animate();
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; background: #ffffff; overflow: hidden; }}
            .chart-container {{ width: 100%; display: flex; flex-direction: column; position: relative; }}
            .pane {{ width: 100%; }}
            #main-chart-wrapper {{ position: relative; height: {base_height}px; width: 100%; }}
            #main-chart {{ height: 100%; width: 100%; }}
            .sub-chart {{ height: 160px; border-top: 1px solid #e0e3eb; }}
            .error-box {{ padding: 20px; color: #f23645; text-align: center; border: 1px solid #e0e3eb; border-radius: 6px; margin: 20px; background: #fffafb; }}
            #tv-legend {{ position: absolute; left: 12px; top: 12px; z-index: 100; font-size: 13px; font-weight: 500; color: #131722; background: rgba(255,255,255,0.85); padding: 6px 10px; border-radius: 4px; pointer-events: none; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: {hud_display}; }}
            #drawing-toolbar {{ position: absolute; right: 12px; top: 12px; z-index: 100; display: flex; gap: 4px; background: #fff; padding: 4px; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: 1px solid #e0e3eb; }}
            #drawing-toolbar button {{ border: none; background: transparent; cursor: pointer; padding: 6px 10px; font-size: 12px; border-radius: 4px; color: #787b86; font-weight: 600; transition: 0.2s; }}
            #drawing-toolbar button:hover {{ background: #f0f3fa; color: #2962FF; }}
            #drawing-toolbar button.active {{ background: #2962FF; color: #fff; }}
            #drawing-layer {{ position: absolute; top: 0; left: 0; z-index: 50; pointer-events: none; width: 100%; height: 100%; }}
        </style>
    </head>
    <body>
        <div id="wrapper" class="chart-container">
            <div id="main-chart-wrapper">
                <div id="tv-legend"><b>{title_text}</b><br><span id="legend-data">Hover over chart</span></div>
                {drawing_html}
                <div id="main-chart"></div>
            </div>
            {"".join([f'<div id="subchart_{i}" class="pane sub-chart"></div>' for i in range(len(active_osc))])}
        </div>

        <script>
            try {{
                const charts = [];
                const chartOptions = {{
                    layout: {{ backgroundColor: '#ffffff', textColor: '#131722' }},
                    grid: {{ vertLines: {{ color: '#f0f3fa' }}, horzLines: {{ color: '#f0f3fa' }} }},
                    timeScale: {{ borderColor: '#e0e3eb', rightOffset: 5, timeVisible: true }},
                    rightPriceScale: {{ borderColor: '#e0e3eb' }},
                    crosshair: {{ mode: 0 }}
                }};

                const mainChart = LightweightCharts.createChart(document.getElementById('main-chart'), chartOptions);
                charts.push(mainChart);
                
                let mainSeries;
                if('{c_type}' === 'Line') {{
                    mainSeries = mainChart.addLineSeries({{ color: '{'#E91E63' if analysis_mode == "Correlation" else '#2962FF'}', lineWidth: 2 }});
                }} else if ('{c_type}' === 'Bar (OHLC)') {{
                    mainSeries = mainChart.addBarSeries({{ upColor: '#089981', downColor: '#f23645', thinBars: false }});
                }} else {{
                    mainSeries = mainChart.addCandlestickSeries({{
                        upColor: '#089981', downColor: '#f23645', borderVisible: false,
                        wickUpColor: '#089981', wickDownColor: '#f23645'
                    }});
                }}
                mainSeries.setData({json.dumps(main_data)});

                if('{str(show_vol and has_volume).lower()}' === 'true') {{
                    const volumeSeries = mainChart.addHistogramSeries({{
                        color: '#26a69a', priceFormat: {{ type: 'volume' }},
                        priceScaleId: '', scaleMargins: {{ top: 0.85, bottom: 0 }}
                    }});
                    volumeSeries.setData({json.dumps(vol_data)});
                }}

                {overlay_js}

                function createSubchart(divId, title, type, data, color) {{
                    const container = document.getElementById(divId);
                    const chart = LightweightCharts.createChart(container, chartOptions);
                    charts.push(chart);
                    let series;
                    if(type === 'area') {{
                        series = chart.addAreaSeries({{ lineColor: color, topColor: color+'40', bottomColor: color+'00', title: title }});
                    }} else {{
                        series = chart.addLineSeries({{ color: color, lineWidth: 1.5, title: title }});
                        if (title === 'RSI') {{
                            chart.addLineSeries({{color: '#787b86', lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false}}).setData(data.map(d => ({{time: d.time, value: 70}})));
                            chart.addLineSeries({{color: '#787b86', lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false}}).setData(data.map(d => ({{time: d.time, value: 30}})));
                        }}
                    }}
                    series.setData(data);
                }}

                function createMacdChart(divId, lineData, sigData, histData) {{
                    const container = document.getElementById(divId);
                    const chart = LightweightCharts.createChart(container, chartOptions);
                    charts.push(chart);
                    const histSeries = chart.addHistogramSeries({{ priceScaleId: '', scaleMargins: {{ top: 0.1, bottom: 0.1 }} }});
                    histSeries.setData(histData);
                    const macdLine = chart.addLineSeries({{ color: '#2962FF', lineWidth: 1.5, title: 'MACD', crosshairMarkerVisible: false }});
                    macdLine.setData(lineData);
                    const sigLine = chart.addLineSeries({{ color: '#FF9800', lineWidth: 1.5, title: 'Sig', crosshairMarkerVisible: false }});
                    sigLine.setData(sigData);
                }}

                {osc_js}

                const legendData = document.getElementById('legend-data');
                mainChart.subscribeCrosshairMove(param => {{
                    if (param.time) {{
                        const data = param.seriesData.get(mainSeries);
                        if (data) {{
                            if (data.open !== undefined) {{
                                legendData.innerHTML = `O: ${{data.open.toFixed(2)}} H: ${{data.high.toFixed(2)}} L: ${{data.low.toFixed(2)}} C: ${{data.close.toFixed(2)}}`;
                            }} else {{
                                legendData.innerHTML = `Close: ${{data.value.toFixed(4)}}`;
                            }}
                        }}
                    }}
                }});

                if (charts.length > 1) {{
                    charts.forEach((chart, index) => {{
                        chart.timeScale().subscribeVisibleTimeRangeChange(range => {{
                            if (range !== null) {{
                                charts.forEach(c => {{ if (c !== chart) c.timeScale().setVisibleRange(range); }});
                            }}
                        }});
                        chart.subscribeCrosshairMove(param => {{
                            if (!param.point) return;
                            charts.forEach(c => {{
                                if (c !== chart) c.setCrosshairPosition(param.price, param.time, c.series()[0]);
                            }});
                        }});
                    }});
                }}
                
                {drawing_js}
                
                new ResizeObserver(entries => {{
                    if (entries.length === 0 || entries[0].target !== document.body) return;
                    
                    // Sync internal canvas size with DOM bounds
                    if ('{str(enable_drawing).lower()}' === 'true') {{
                        const wrp = document.getElementById('main-chart-wrapper');
                        const cvs = document.getElementById('drawing-layer');
                        cvs.width = wrp.clientWidth;
                        cvs.height = wrp.clientHeight;
                    }}
                    
                    charts.forEach((c, idx) => {{
                        const elem = document.getElementById(idx === 0 ? 'main-chart' : `subchart_${idx-1}`);
                        if(elem) c.applyOptions({{ width: elem.clientWidth }});
                    }});
                }}).observe(document.body);
            }} catch (error) {{
                document.getElementById('wrapper').innerHTML = "<div class='error-box'><b>Failed to render high-performance chart.</b><br>Insufficient data parameters.<br><i>" + error.message + "</i></div>";
            }}
        </script>
    </body>
    </html>
    """
    height_px = base_height + (160 * len(active_osc))
    return html, height_px

@st.dialog("📈 Full Screen Analysis", width="large")
def expand_chart_modal(num_name, den_name):
    title = f"{num_name}" if den_name == "None" else f"{num_name} / {den_name}"
    st.markdown(f"### {title}")
    with st.spinner("Loading High-Res TV Engine..."):
        html_payload, height_px = render_tv_chart(
            num_name, den_name, st.session_state.target_period, interval_selection, 
            chart_type, selected_overlays, selected_oscillators, show_volume, analysis_mode.split()[0], 
            show_hud=True, base_height=500, enable_drawing=True
        )
        if html_payload: components.html(html_payload, height=height_px, scrolling=False)


# --- MULTI-SCREEN TERMINAL TABS ---
tab1, tab2, tab3 = st.tabs(["🖥️ Macro Overview", "🔍 Dynamic Explorer", "🧮 Correlation Matrix"])

with tab1:
    st.subheader("🌐 Live Global Markets")
    top_indices = ["S&P 500", "Nasdaq 100", "DAX", "FTSE 100", "STOXX 50", "Nikkei 225", "ASX 200", "Nifty 50", "Gold (Spot)", "Crude Oil", "Bitcoin", "US 20+ Yr Treasury"]
    
    with st.spinner("Syncing Global Markets..."):
        for row in range(0, len(top_indices), 6):
            cols_top = st.columns(6)
            for col_idx in range(6):
                idx = row + col_idx
                if idx < len(top_indices):
                    idx_name = top_indices[idx]
                    ticker = st.session_state.asset_dict[idx_name]
                    curr = CURRENCY_MAP.get(idx_name, "")
                    
                    with cols_top[col_idx]:
                        with st.container(border=True):
                            c_title, c_mod, c_exp = st.columns([5, 2, 2])
                            c_title.markdown(f"<div style='font-size:0.85rem; font-weight:600; color:#787b86; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{idx_name}</div>", unsafe_allow_html=True)
                            if c_mod.button("⛶", key=f"top_mod_{idx_name}", help="Full Screen"): expand_chart_modal(idx_name, "None")
                            if c_exp.button("🔍", key=f"top_exp_{idx_name}", help="Analyze in Explorer"):
                                st.session_state.target_num = idx_name
                                st.session_state.target_den = "None"
                                st.rerun()
                                
                            data = fetch_yahoo_data(ticker, "5d", "1d")
                            if data is not None and not data.empty and len(data) >= 2:
                                try:
                                    last_close, prev_close = float(data['Close'].iloc[-1]), float(data['Close'].iloc[-2])
                                    pct_change = ((last_close - prev_close) / prev_close) * 100
                                    st.metric(label="val", value=f"{curr}{last_close:,.2f}", delta=f"{pct_change:.2f}%", label_visibility="collapsed")
                                except: st.metric(label="val", value="Error", label_visibility="collapsed")
                            else: st.metric(label="val", value="N/A", label_visibility="collapsed")
                    
    st.markdown("---")
    
    col_left, col_main, col_news = st.columns([2, 5, 2.5]) 
    
    with col_left:
        st.subheader("⭐ Favorites")
        if not st.session_state.fav_ratios: st.caption("No favorites saved yet.")
        for idx, (num, den) in enumerate(st.session_state.fav_ratios):
            with st.container(border=True):
                disp_text = f"**{num}**" if den == "None" else f"**{num}**<br><span style='color:#787b86;'>/ {den}</span>"
                st.markdown(disp_text, unsafe_allow_html=True)
                c1, c2 = st.columns([3, 1])
                if c1.button("🔍 Load", key=f"fav_load_{idx}", use_container_width=True):
                    st.session_state.target_num = num
                    st.session_state.target_den = den
                    st.rerun()
                if c2.button("❌", key=f"fav_del_{idx}", use_container_width=True):
                    st.session_state.fav_ratios.remove((num, den))
                    st.rerun()

    with col_main:
        macro_tabs = st.tabs(["🇮🇳 NSE", "🇺🇸 US", "🌍 Global", "🕒 Recent"])
        
        with macro_tabs[0]:
            nse_list = ["Nifty Bank", "Nifty IT", "Nifty Auto", "Nifty Pharma"]
            cols = st.columns(2)
            for idx, sec in enumerate(nse_list):
                with cols[idx % 2], st.container(border=True):
                    head1, head2, head3 = st.columns([6, 1.5, 1.5])
                    head1.markdown(f"**{sec}**")
                    if head2.button("⛶", key=f"btn_mod_nse_{idx}"): expand_chart_modal(sec, "Broad Market 500 (IND)")
                    if head3.button("🔍", key=f"btn_exp_nse_{idx}"):
                        st.session_state.target_num = sec
                        st.session_state.target_den = "Broad Market 500 (IND)"
                        st.rerun()
                    html_payload, height_px = render_tv_chart(sec, "Broad Market 500 (IND)", "6mo", "1d", "Candlestick", [], ["Volume"], True, "Ratio", show_hud=False, base_height=200, enable_drawing=False)
                    if html_payload: components.html(html_payload, height=height_px, scrolling=False)
                        
        with macro_tabs[1]:
            us_list = ["Nasdaq 100", "Russell 2000", "US Tech ETF", "US Healthcare ETF"]
            cols = st.columns(2)
            for idx, sec in enumerate(us_list):
                with cols[idx % 2], st.container(border=True):
                    head1, head2, head3 = st.columns([6, 1.5, 1.5])
                    head1.markdown(f"**{sec}**")
                    if head2.button("⛶", key=f"btn_mod_us_{idx}"): expand_chart_modal(sec, "S&P 500")
                    if head3.button("🔍", key=f"btn_exp_us_{idx}"):
                        st.session_state.target_num = sec
                        st.session_state.target_den = "S&P 500"
                        st.rerun()
                    html_payload, height_px = render_tv_chart(sec, "S&P 500", "6mo", "1d", "Candlestick", [], ["Volume"], True, "Ratio", show_hud=False, base_height=200, enable_drawing=False)
                    if html_payload: components.html(html_payload, height=height_px, scrolling=False)

        with macro_tabs[2]:
            macro_pairs = [("Gold (Spot)", "S&P 500", "Safe Haven vs Equity"), ("US 20+ Yr Treasury", "S&P 500", "Bonds vs Equity"), ("Emerging Markets", "S&P 500", "EM vs Developed"), ("Bitcoin", "Gold (Spot)", "Digital vs Gold")]
            cols = st.columns(2)
            for idx, (num, den, title) in enumerate(macro_pairs):
                with cols[idx % 2], st.container(border=True):
                    head1, head2, head3 = st.columns([6, 1.5, 1.5])
                    head1.markdown(f"**{title}**<br>({num} / {den})", unsafe_allow_html=True)
                    if head2.button("⛶", key=f"btn_mod_glb_{idx}"): expand_chart_modal(num, den)
                    if head3.button("🔍", key=f"btn_exp_glb_{idx}"):
                        st.session_state.target_num = num
                        st.session_state.target_den = den
                        st.rerun()
                    html_payload, height_px = render_tv_chart(num, den, "6mo", "1d", "Candlestick", [], ["Volume"], True, "Ratio", show_hud=False, base_height=220, enable_drawing=False)
                    if html_payload: components.html(html_payload, height=height_px, scrolling=False)
                    
        with macro_tabs[3]:
            if not st.session_state.recent_ratios: st.info("No recent charts. Analyze ratios in the Dynamic Explorer to see them here.")
            else:
                cols = st.columns(2)
                for idx, (num, den) in enumerate(st.session_state.recent_ratios):
                    with cols[idx % 2], st.container(border=True):
                        h1, h2, h3 = st.columns([6, 1.5, 1.5])
                        h1.markdown(f"**{num}** / {den}" if den != "None" else f"**{num}**")
                        if h2.button("⛶", key=f"rec_mod_{idx}"): expand_chart_modal(num, den)
                        if h3.button("🔍", key=f"rec_exp_{idx}"):
                            st.session_state.target_num = num
                            st.session_state.target_den = den
                            st.rerun()
                        html_payload, height_px = render_tv_chart(num, den, "6mo", "1d", "Candlestick", [], ["Volume"], True, "Ratio", show_hud=False, base_height=200, enable_drawing=False)
                        if html_payload: components.html(html_payload, height=height_px, scrolling=False)

    with col_news:
        st.subheader("📋 Watchlists")
        with st.container(border=True):
            active_wl = st.selectbox("Select", list(st.session_state.watchlists.keys()), index=list(st.session_state.watchlists.keys()).index(st.session_state.active_wl), label_visibility="collapsed", key="wl_sel")
            st.session_state.active_wl = active_wl
            
            wl_data = fetch_bulk_watchlist(st.session_state.watchlists[active_wl])
            if not wl_data.empty:
                df = pd.DataFrame(wl_data)
                df['Price'] = df.apply(lambda row: f"{CURRENCY_MAP.get(row['Asset'], '')}{row['Price']:.2f}", axis=1)
                styled_df = df.style.map(lambda x: 'color: #089981; font-weight: bold;' if x > 0 else 'color: #f23645; font-weight: bold;' if x < 0 else '', subset=['Chg %']).format({"Chg %": "{:+.2f}%"})
                event = st.dataframe(styled_df, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="wl_df")
                if len(event.selection.rows) > 0:
                    selected_asset = df.iloc[event.selection.rows[0]]["Asset"]
                    st.session_state.target_num = selected_asset
                    st.session_state.target_den = "None"
                    st.rerun()

        st.subheader("📰 Sentiment Feed")
        with st.container(border=True, height=350):
            news = fetch_market_news(st.session_state.target_num)
            for item in news:
                st.markdown(f"{item['tag']} **[{item['title']}]({item['link']})**")
                st.caption(f"🕒 {item.get('published', 'Recent').replace('+0000', '').strip()}")
                st.markdown("---")

# --- SCREEN 2: DYNAMIC EXPLORER ---
with tab2:
    col_dyn_main, col_dyn_news = st.columns([3, 1]) 
    
    with col_dyn_main:
        c1, c_save, c_full, c_clear = st.columns([3.5, 1.5, 1.5, 1.5])
        
        current_pair = (st.session_state.target_num, st.session_state.target_den)
        if current_pair in st.session_state.recent_ratios: st.session_state.recent_ratios.remove(current_pair)
        st.session_state.recent_ratios.insert(0, current_pair)
        st.session_state.recent_ratios = st.session_state.recent_ratios[:6]
        
        if st.session_state.target_num != "None":
            tkr = st.session_state.asset_dict[st.session_state.target_num]
            data = fetch_yahoo_data(tkr, "5d", "1d")
            curr = CURRENCY_MAP.get(st.session_state.target_num, "")
            if data is not None and not data.empty and len(data) >= 2:
                last_px, prev_px = data['Close'].iloc[-1], data['Close'].iloc[-2]
                pct_chg = ((last_px - prev_px) / prev_px) * 100
                clr = "#089981" if pct_chg >= 0 else "#f23645"
                sgn = "+" if pct_chg >= 0 else ""
                
                header_title = f"{st.session_state.target_num} / {st.session_state.target_den}" if st.session_state.target_den != "None" else f"{st.session_state.target_num}"
                c1.markdown(f"<h3 style='margin-bottom:0;'>{header_title} &nbsp;<span style='color:{clr}; font-size:1.3rem;'>{curr}{last_px:,.2f} ({sgn}{pct_chg:.2f}%)</span></h3>", unsafe_allow_html=True)
                
                if st.session_state.target_den == "None":
                    funds = fetch_fundamentals(tkr)
                    if funds:
                        st.markdown(f"""
                        <div class='tear-sheet'>
                            <div><span class='tear-val'>52W High:</span> {curr}{funds['52W High']}</div>
                            <div><span class='tear-val'>52W Low:</span> {curr}{funds['52W Low']}</div>
                            <div><span class='tear-val'>Mkt Cap:</span> {curr}{funds['Mkt Cap']}</div>
                            <div><span class='tear-val'>P/E (TTM):</span> {funds['P/E (TTM)']}</div>
                            <div><span class='tear-val'>Div Yield:</span> {funds['Div Yield']}</div>
                        </div>
                        """, unsafe_allow_html=True)
            else: c1.subheader(f"{st.session_state.target_num}")
        else: c1.subheader("No Assets Selected")
        
        with c_save:
            is_saved = current_pair in st.session_state.fav_ratios
            if is_saved:
                if st.button("❌ Unsave", use_container_width=True):
                    st.session_state.fav_ratios.remove(current_pair)
                    st.rerun()
            else:
                if st.button("⭐ Save Ratio", use_container_width=True):
                    st.session_state.fav_ratios.append(current_pair)
                    st.rerun()
                    
        with c_full:
            if st.button("⛶ Full Screen", use_container_width=True):
                expand_chart_modal(st.session_state.target_num, st.session_state.target_den)
                
        with c_clear:
            if st.button("🗑️ Clear", use_container_width=True): st.rerun()

        with st.spinner("Rendering WebGL Engine with Custom Drawing Tool..."):
            html_payload, height_px = render_tv_chart(
                st.session_state.target_num, st.session_state.target_den, 
                timeframe, interval_selection, chart_type, 
                selected_overlays, selected_oscillators, show_volume, analysis_mode.split()[0], 
                show_hud=True, base_height=500, enable_drawing=True
            )
            if html_payload: components.html(html_payload, height=height_px, scrolling=False)
            
        if st.session_state.target_num != "None":
            with st.expander("📅 Historical Seasonality Matrix (Monthly % Returns)", expanded=False):
                with st.spinner("Calculating Seasonality..."):
                    try:
                        s_data = fetch_yahoo_data(st.session_state.asset_dict[st.session_state.target_num], "5y", "1d")
                        if s_data is not None and not s_data.empty:
                            s_data['Year'] = s_data.index.year
                            s_data['Month'] = s_data.index.month
                            monthly_rtn = s_data.groupby(['Year', 'Month'])['Close'].apply(lambda x: (x.iloc[-1]/x.iloc[0] - 1)*100).unstack()
                            monthly_rtn.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                            
                            # Plotly exclusively retained for the Heatmap visualization
                            fig_sea = go.Figure(data=go.Heatmap(
                                z=monthly_rtn.values, x=monthly_rtn.columns, y=monthly_rtn.index,
                                colorscale=[[0, '#F23645'], [0.5, '#ffffff'], [1, '#089981']],
                                text=monthly_rtn.round(2).fillna("").astype(str) + "%", texttemplate="%{text}", textfont={"color":"#131722"},
                                zmid=0, showscale=False
                            ))
                            fig_sea.update_layout(height=250, margin=dict(l=10, r=10, t=30, b=10), template="plotly_white")
                            fig_sea.update_yaxes(autorange="reversed", type='category')
                            st.plotly_chart(fig_sea, use_container_width=True, config={'displayModeBar': False})
                    except: st.caption("Seasonality data unavailable.")

    with col_dyn_news:
        st.subheader("📋 Watchlists")
        with st.container(border=True):
            active_wl = st.selectbox("Select", list(st.session_state.watchlists.keys()), index=list(st.session_state.watchlists.keys()).index(st.session_state.active_wl), label_visibility="collapsed", key="wl_sel_dyn")
            st.session_state.active_wl = active_wl
            
            wl_data = fetch_bulk_watchlist(st.session_state.watchlists[active_wl])
            if not wl_data.empty:
                df = pd.DataFrame(wl_data)
                df['Price'] = df.apply(lambda row: f"{CURRENCY_MAP.get(row['Asset'], '')}{row['Price']:.2f}", axis=1)
                styled_df = df.style.map(lambda x: 'color: #089981; font-weight: bold;' if x > 0 else 'color: #f23645; font-weight: bold;' if x < 0 else '', subset=['Chg %']).format({"Chg %": "{:+.2f}%"})
                event = st.dataframe(styled_df, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key="wl_df_dyn")
                if len(event.selection.rows) > 0:
                    selected_asset = df.iloc[event.selection.rows[0]]["Asset"]
                    st.session_state.target_num = selected_asset
                    st.session_state.target_den = "None"
                    st.rerun()

        st.subheader("📰 Sentiment Feed")
        with st.container(border=True, height=350):
            news = fetch_market_news(st.session_state.target_num)
            for item in news:
                st.markdown(f"{item['tag']} **[{item['title']}]({item['link']})**")
                st.caption(f"🕒 {item.get('published', 'Recent').replace('+0000', '').strip()}")
                st.markdown("---")

# --- SCREEN 3: CORRELATION MATRIX ---
with tab3:
    st.subheader("🧮 Active Watchlist Correlation Matrix (6-Month Daily Returns)")
    st.caption(f"Analyzing cross-asset correlations for list: **{st.session_state.active_wl}**")
    
    with st.spinner("Processing Matrix..."):
        curr_wl = st.session_state.watchlists[st.session_state.active_wl]
        if len(curr_wl) < 2:
            st.warning("Please add at least 2 assets to your active watchlist to calculate correlation.")
        else:
            try:
                tkr_list = list(curr_wl.values())
                name_list = list(curr_wl.keys())
                
                raw_data = yf.download(tkr_list, period="6mo", interval="1d", progress=False)
                corr_data = pd.DataFrame()
                
                if isinstance(raw_data.columns, pd.MultiIndex):
                    if 'Close' in raw_data.columns.levels[0]:
                        corr_data = raw_data['Close']
                elif 'Close' in raw_data.columns:
                    corr_data = raw_data[['Close']]
                else:
                    corr_data = raw_data

                valid_names = []
                valid_tkrs = []
                for name, tk in curr_wl.items():
                    if tk in corr_data.columns:
                        valid_tkrs.append(tk)
                        valid_names.append(name)
                
                corr_data = corr_data[valid_tkrs]
                corr_data.columns = valid_names
                
                corr_matrix = corr_data.pct_change().corr().round(2)
                
                fig_corr = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values, x=corr_matrix.columns, y=corr_matrix.index,
                    colorscale=[[0, '#F23645'], [0.5, '#ffffff'], [1, '#089981']],
                    text=corr_matrix.values, texttemplate="%{text}",
                    zmin=-1, zmax=1, zmid=0
                ))
                fig_corr.update_layout(height=600, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10))
                fig_corr.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_corr, use_container_width=True, config={'displayModeBar': False})
            except Exception as e:
                st.error("Could not calculate correlation.")

# --- TELEMETRY ---
st.markdown("---")
latency = round(time.time() - start_time, 2)
st.caption(f"🟢 **System:** Online | ⏱️ **Latency:** {latency}s | 📡 **Engines:** YF API + TV WebGL Canvas | 🕒 **Sync:** {pd.Timestamp.now().strftime('%H:%M:%S UTC')} | 📦 **Assets:** {len(st.session_state.asset_dict)}")
