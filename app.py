import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Strategic Alpha Ratio Dashboard", layout="wide")
st.title("📈 Live Market Ratio & Rotation Dashboard")
st.markdown("Interactive ratio charts tracking sector rotation, global capital flows, and asset allocation.")

# --- SIDEBAR: TIMEFRAME SELECTION ---
st.sidebar.header("Settings")
timeframe = st.sidebar.selectbox(
    "Select Timeframe", 
    ("6 Months", "1 Year", "2 Years", "5 Years", "Max")
)

# Map selection to yfinance period strings
period_map = {
    "6 Months": "6mo",
    "1 Year": "1y",
    "2 Years": "2y",
    "5 Years": "5y",
    "Max": "max"
}
selected_period = period_map[timeframe]

# --- DATA FETCHING FUNCTION ---
@st.cache_data(ttl=3600) # Cache data for 1 hour to speed up reloads
def fetch_data(ticker, period):
    try:
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            return None
        # Return the 'Close' price series
        return data['Close']
    except Exception as e:
        return None

# --- CHART PLOTTING FUNCTION ---
def plot_ratio_chart(title, ticker1, name1, ticker2, name2, period):
    data1 = fetch_data(ticker1, period)
    data2 = fetch_data(ticker2, period)
    
    if data1 is None or data2 is None:
        st.warning(f"⚠️ Could not fetch data for {title}. Yahoo Finance might be missing this ticker.")
        return

    # Align dates and drop missing values
    df = pd.merge(data1, data2, left_index=True, right_index=True, suffixes=(f'_{name1}', f'_{name2}'))
    df.dropna(inplace=True)
    
    # Calculate the ratio (Asset 1 / Asset 2)
    col1 = df.columns[0]
    col2 = df.columns[1]
    df['Ratio'] = df[col1] / df[col2]
    
    # Normalize ratio to base 100 at the start of the timeframe for clear visual comparison
    df['Normalized_Ratio'] = (df['Ratio'] / df['Ratio'].iloc[0]) * 100

    # Create an interactive Plotly chart
    fig = px.line(
        df, 
        x=df.index, 
        y='Normalized_Ratio', 
        title=f"{title} ({name1} / {name2}) - Base 100",
        labels={'Normalized_Ratio': 'Relative Performance', 'index': 'Date'},
        template="plotly_dark"
    )
    fig.update_traces(line_color='#00ffcc', line_width=2)
    fig.update_layout(xaxis_title="", hovermode="x unified")
    
    st.plotly_chart(fig, use_container_width=True)

# --- DASHBOARD LAYOUT & CHARTS ---

st.markdown("---")
st.header("1. Asset Allocation & Alternatives")
col1, col2 = st.columns(2)
with col1:
    plot_ratio_chart("Gold vs Equities", "GC=F", "Gold", "^NSEI", "Nifty 50", selected_period)
with col2:
    plot_ratio_chart("Bitcoin vs Gold", "BTC-USD", "Bitcoin", "GC=F", "Gold", selected_period)

st.markdown("---")
st.header("2. Indian Sector Rotation (Relative to Nifty 50)")
col3, col4 = st.columns(2)
with col3:
    plot_ratio_chart("Pharma Strength", "^CNXPHARMA", "Nifty Pharma", "^NSEI", "Nifty 50", selected_period)
    plot_ratio_chart("PSU Bank Strength", "^CNXPSUBANK", "Nifty PSU Bank", "^NSEBANK", "Nifty Bank", selected_period)
with col4:
    plot_ratio_chart("Metal Strength", "^CNXMETAL", "Nifty Metal", "^NSEI", "Nifty 50", selected_period)
    plot_ratio_chart("Smallcap vs Largecap", "^CNXSC", "Nifty Smallcap 100", "^NSEI", "Nifty 50", selected_period)

st.markdown("---")
st.header("3. Global & Country Rotation")
col5, col6 = st.columns(2)
with col5:
    plot_ratio_chart("Emerging Markets vs US", "EEM", "Emerging Mkts", "^GSPC", "S&P 500", selected_period)
with col6:
    plot_ratio_chart("Latin America vs Emerging Mkts", "ILF", "LatAm ETF", "EEM", "Emerging Mkts", selected_period)

st.markdown("---")
st.header("4. Fear Indicator (Absolute)")
# VIX doesn't need a ratio, just the raw data
vix_data = fetch_data("^INDIAVIX", selected_period)
if vix_data is not None:
    fig_vix = px.line(vix_data, title="India VIX (Volatility / Fear Index)", template="plotly_dark")
    fig_vix.update_traces(line_color='#ff3366')
    fig_vix.update_layout(showlegend=False, xaxis_title="")
    st.plotly_chart(fig_vix, use_container_width=True)
else:
    st.warning("⚠️ Could not fetch India VIX data.")