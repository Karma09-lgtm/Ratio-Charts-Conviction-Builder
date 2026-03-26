import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import feedparser

# --- PAGE CONFIGURATION & TIMER START ---
st.set_page_config(page_title="Ratio Charts Conviction Builder", layout="wide", initial_sidebar_state="expanded")
start_time = time.time()

st.title("🌍 Global Macro Ratio Dashboard (Pro)")

# --- MASSIVELY EXPANDED STATE MANAGEMENT ---
if 'asset_dict' not in st.session_state:
    st.session_state.asset_dict = {
        # --- INDIAN MARKETS (NSE/BSE) ---
        "Broad Market 500 (IND)": "BSE-500.BO", 
        "Nifty 50": "^NSEI",
        "Nifty Next 50": "^NN50",
        "Nifty Midcap 100": "^CRSLMID",
        "Nifty Smallcap 100": "^CNXSC",
        "Nifty Microcap 250": "^CRSLMIC",
        "BSE Sensex": "^BSESN",
        
        # --- INDIAN SECTORS ---
        "Nifty Auto": "^CNXAUTO",
        "Nifty Bank": "^NSEBANK",
        "Nifty Commodities": "^CNXCMDT",
        "Nifty Consumption": "^CNXCONSUM",
        "Nifty Energy": "^CNXENERGY",
        "Nifty Financial Services": "^CNXFIN",
        "Nifty FMCG": "^CNXFMCG",
        "Nifty Infrastructure": "^CNXINFRA",
        "Nifty IT": "^CNXIT",
        "Nifty Media": "^CNXMEDIA",
        "Nifty Metal": "^CNXMETAL",
        "Nifty Pharma": "^CNXPHARMA",
        "Nifty PSE": "^CNXPSE",
        "Nifty PSU Bank": "^CNXPSUBANK",
        "Nifty Private Bank": "^NIFTY_PVTMA.NS",
        "Nifty Realty": "^CNXREALTY",
        
        # --- US MAJOR INDICES ---
        "S&P 500 (US)": "^GSPC",
        "Nasdaq 100": "^NDX",
        "Dow Jones Industrial Average": "^DJI",
        "Russell 2000 (Small Caps)": "^RUT",
        "Nasdaq Composite": "^IXIC",
        "CBOE Volatility Index (VIX)": "^VIX",

        # --- US SECTOR ETFs (SPDR) ---
        "US Technology (XLK)": "XLK",
        "US Financials (XLF)": "XLF",
        "US Healthcare (XLV)": "XLV",
        "US Energy (XLE)": "XLE",
        "US Consumer Discretionary (XLY)": "XLY",
        "US Consumer Staples (XLP)": "XLP",
        "US Industrials (XLI)": "XLI",
        "US Utilities (XLU)": "XLU",
        "US Real Estate (XLRE)": "XLRE",
        "US Materials (XLB)": "XLB",
        "US Communication Services (XLC)": "XLC",

        # --- GLOBAL INDICES ---
        "FTSE 100 (UK)": "^FTSE",
        "DAX Performance Index (Germany)": "^GDAXI",
        "CAC 40 (France)": "^FCHI",
        "Nikkei 225 (Japan)": "^N225",
        "Hang Seng Index (Hong Kong)": "^HSI",
        "Shanghai Composite (China)": "000001.SS",
        "S&P/ASX 200 (Australia)": "^AXJO",
        
        # --- GLOBAL & THEMATIC ETFs ---
        "Emerging Markets (EEM)": "EEM",
        "Developed Markets ex-US (EFA)": "EFA",
        "All World Index (VT)": "VT",
        "ARK Innovation (ARKK)": "ARKK",
        "Semiconductors (SMH)": "SMH",
        "Gold Miners (GDX)": "GDX",
        "Cybersecurity (HACK)": "HACK",
        "Clean Energy (ICLN)": "ICLN",

        # --- FIXED INCOME & BONDS ---
        "US 20+ Year Treasury (TLT)": "TLT",
        "US 7-10 Year Treasury (IEF)": "IEF",
        "US 1-3 Year Treasury (SHY)": "SHY",
        "High Yield Corporate Bonds (HYG)": "HYG",
        "Investment Grade Corporate Bonds (LQD)": "LQD",
        
        # --- COMMODITIES (FUTURES/SPOT) ---
        "Gold (Spot)": "GC=F",
        "Silver (Spot)": "SI=F",
        "Copper": "HG=F",
        "Crude Oil (WTI)": "CL=F",
        "Brent Crude": "BZ=F",
        "Natural Gas": "NG=F",
        "Corn": "ZC=F",
        "Wheat": "ZW=F",

        # --- CRYPTOCURRENCY ---
        "Bitcoin (USD)": "BTC-USD",
        "Ethereum": "ETH-USD",
        "Solana": "SOL-USD"
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

# Use index positions to set initial defaults
selected_asset_name = st.sidebar.selectbox("1. Numerator", list(st.session_state
