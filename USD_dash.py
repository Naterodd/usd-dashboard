import streamlit as st
import pandas as pd
import yfinance as yf
from pytrends.request import TrendReq
from datetime import datetime
import numpy as np
from fredapi import Fred

# -------------------- Page Config --------------------
st.set_page_config(page_title="USD Dashboard", layout="wide")

# -------------------- Sidebar Controls --------------------
st.sidebar.title("Dashboard Settings")
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2010-01-01"))
end_date = st.sidebar.date_input("End Date", value=datetime.today())

st.title("🇺🇸 U.S. Dollar Economic Dashboard")
st.markdown("Tracking indicators related to the strength and perception of the U.S. Dollar.")

# -------------------- Helper: RSI --------------------
def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = -delta.clip(upper=0).rolling(window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# -------------------- FRED API Setup --------------------
FRED_API_KEY = "07b2c0e6debee8197995cddb614ff624"  # <-- Replace this with your FRED API key
fred = Fred(api_key=FRED_API_KEY)

# -------------------- 1. Inflation: CPI --------------------
st.subheader("Inflation: CPI (Monthly Change in Basis Points)")
try:
    cpi = fred.get_series('CPIAUCSL', observation_start=start_date, observation_end=end_date)
    cpi = cpi.to_frame(name='CPIAUCSL')
    cpi['MoM Change (bps)'] = cpi['CPIAUCSL'].pct_change() * 10_000
    st.line_chart(cpi['MoM Change (bps)'].dropna())
except Exception as e:
    st.error(f"Error loading CPI data: {e}")

# -------------------- 2. Debt as % of GDP --------------------
st.subheader("U.S. Federal Debt as % of GDP")
try:
    debt_gdp = fred.get_series('GFDEGDQ188S', observation_start=start_date, observation_end=end_date)
    debt_gdp = debt_gdp.to_frame(name='Debt/GDP (%)')
    st.line_chart(debt_gdp)
except Exception as e:
    st.error(f"Error loading Debt/GDP data: {e}")

# -------------------- 3. UUP ETF --------------------
st.subheader("Dollar Index Proxy (UUP ETF)")
try:
    uup = yf.download('UUP', start=start_date, end=end_date, auto_adjust=True)
    if isinstance(uup, pd.DataFrame) and not uup.empty:
        if isinstance(uup.columns, pd.MultiIndex):
            if 'Close' in uup.columns.get_level_values(0):
                uup = uup['Close']
            else:
                uup = uup.iloc[:, 0]
        else:
            uup = uup['Close']
        uup.name = 'UUP'
        st.line_chart(uup)
    else:
        st.warning("No UUP data returned or data format unexpected.")
except Exception as e:
    st.error(f"Error loading UUP data: {e}")

# -------------------- 4. ICE Dollar Index (DXY) --------------------
st.subheader("ICE Dollar Index (DXY)")
try:
    dxy = yf.download('DX-Y.NYB', start=start_date, end=end_date)
    if dxy.empty:
        st.warning("No data returned for DXY.")
    else:
        if isinstance(dxy.columns, pd.MultiIndex):
            if 'Adj Close' in dxy.columns.get_level_values(0):
                dxy = dxy['Adj Close']
            elif 'Close' in dxy.columns.get_level_values(0):
                dxy = dxy['Close']
            else:
                raise ValueError("Neither 'Adj Close' nor 'Close' found.")
        else:
            if 'Adj Close' in dxy.columns:
                dxy = dxy[['Adj Close']]
            elif 'Close' in dxy.columns:
                dxy = dxy[['Close']]
            else:
                raise ValueError("Neither 'Adj Close' nor 'Close' found.")
        dxy = dxy.rename(columns={dxy.columns[0]: 'DXY'})
        st.line_chart(dxy)
except Exception as e:
    st.error(f"Error loading DXY data: {e}")

# -------------------- 5. 2-Year Treasury Yield --------------------
st.subheader("2-Year U.S. Treasury Yield (%)")
try:
    twoy = fred.get_series('DGS2', observation_start=start_date, observation_end=end_date)
    twoy = twoy.to_frame(name='2-Year Treasury Yield (%)')
    st.line_chart(twoy)
except Exception as e:
    st.error(f"Error loading 2-Year Treasury Yield: {e}")

# -------------------- 6. Trade Weighted USD + RSI --------------------
st.subheader("Trade Weighted U.S. Dollar Index (Broad) + RSI")
try:
    trade_weighted = fred.get_series('DTWEXBGS', observation_start=start_date, observation_end=end_date)
    trade_weighted = trade_weighted.to_frame(name='DTWEXBGS')
    trade_weighted['RSI'] = compute_rsi(trade_weighted['DTWEXBGS'])
    st.line_chart(trade_weighted)
except Exception as e:
    st.error(f"Error loading Trade Weighted USD data: {e}")

# -------------------- 7. US GDP Growth vs World GDP Growth --------------------
st.subheader("GDP Growth: U.S. vs World")
try:
    from pandas_datareader import wb  # keep wb import only for World Bank data
    
    us_gdp = wb.download(indicator='NY.GDP.MKTP.KD.ZG', country='US', start=start_date.year, end=end_date.year)
    world_gdp = wb.download(indicator='NY.GDP.MKTP.KD.ZG', country='WLD', start=start_date.year, end=end_date.year)

    us_gdp = us_gdp.reset_index()
    world_gdp = world_gdp.reset_index()

    us_gdp = us_gdp.rename(columns={'NY.GDP.MKTP.KD.ZG': 'US GDP Growth'})
    world_gdp = world_gdp.rename(columns={'NY.GDP.MKTP.KD.ZG': 'World GDP Growth'})

    merged_gdp = pd.merge(
        us_gdp[['year', 'US GDP Growth']],
        world_gdp[['year', 'World GDP Growth']],
        on='year'
    )

    merged_gdp['date'] = pd.to_datetime(merged_gdp['year'], format='%Y')
    merged_gdp.set_index('date', inplace=True)
    merged_gdp.drop(columns=['year'], inplace=True)

    st.line_chart(merged_gdp)
except Exception as e:
    st.error(f"Error loading GDP growth data: {e}")

# -------------------- 8. Google Trends --------------------
st.subheader("Google Search Trends: 'US Dollar'")
try:
    pytrends = TrendReq()
    timeframe_str = f"{start_date.strftime('%Y-%m-%d')} {end_date.strftime('%Y-%m-%d')}"
    pytrends.build_payload(['US dollar'], timeframe=timeframe_str)
    trends_data = pytrends.interest_over_time().drop(columns=['isPartial'], errors='ignore')
    st.line_chart(trends_data)
except Exception as e:
    st.error(f"Error loading Google Trends: {e}")

# -------------------- Footer --------------------
st.caption("📊 Data Sources: FRED (via fredapi), Yahoo Finance, Google Trends, World Bank")
