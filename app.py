import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests

# -------------------------------------------------------
# PAGE SETUP
# -------------------------------------------------------
st.set_page_config(
    page_title="Undervalued Growth Stock Screener",
    layout="wide"
)

st.title("📊 Undervalued Growth Stocks Screener (S&P 500)")
st.caption("Find stocks that are cheap, growing, and financially strong")

# -------------------------------------------------------
# SIDEBAR FILTERS
# -------------------------------------------------------
st.sidebar.header("🔧 Screening Filters")

max_pe = st.sidebar.slider("Max Trailing P/E", 5, 30, 18)
max_forward_pe = st.sidebar.slider("Max Forward P/E", 5, 30, 15)
max_peg = st.sidebar.slider("Max PEG Ratio", 0.5, 3.0, 1.2)
min_roe = st.sidebar.slider("Min ROE (%)", 0, 30, 8)
min_upside = st.sidebar.slider("Min Analyst Upside (%)", 0, 50, 15)

run_button = st.sidebar.button("🚀 Run Screener")

# -------------------------------------------------------
# LOAD S&P 500 TICKERS (403-SAFE METHOD)
# -------------------------------------------------------
@st.cache_data
def load_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    return tables[0]["Symbol"].tolist()

# -------------------------------------------------------
# FETCH STOCK DATA
# -------------------------------------------------------
def fetch_stock_metrics(ticker):
    try:
        info = yf.Ticker(ticker).info

        market_cap = info.get("marketCap")
        free_cashflow = info.get("freeCashflow")

        return {
            "Ticker": ticker,
            "Company": info.get("longName", ""),
            "Sector": info.get("sector", ""),
            "Trailing P/E": info.get("trailingPE"),
            "Forward P/E": info.get("forwardPE"),
            "PEG Ratio": info.get("pegRatio"),
            "ROE %": info.get("returnOnEquity") * 100 if info.get("returnOnEquity") else np.nan,
            "Debt/Equity": info.get("debtToEquity"),
            "Earnings Growth %": info.get("earningsGrowth") * 100 if info.get("earningsGrowth") else np.nan,
            "Revenue Growth %": info.get("revenueGrowth") * 100 if info.get("revenueGrowth") else np.nan,
            "Rec Score": info.get("recommendationMean"),
            "Upside %": (
                (info.get("targetMeanPrice") - info.get("currentPrice"))
                / info.get("currentPrice") * 100
                if info.get("targetMeanPrice") and info.get("currentPrice")
                else np.nan
            ),
        }
    except:
        return None

# -------------------------------------------------------
# MAIN LOGIC
# -------------------------------------------------------
if run_button:
    tickers = load_sp500_tickers()
    results = []

    progress = st.progress(0)
    status = st.empty()

    for i, ticker in enumerate(tickers):
        status.text(f"Scanning {ticker} ({i+1}/{len(tickers)})")

        data = fetch_stock_metrics(ticker)
        if data:
            undervalued = (
                (data["Trailing P/E"] and data["Trailing P/E"] < max_pe)
                or (data["Forward P/E"] and data["Forward P/E"] < max_forward_pe)
                or (data["PEG Ratio"] and data["PEG Ratio"] < max_peg)
            )

            growth = (
                (data["Earnings Growth %"] and data["Earnings Growth %"] > 8)
                or (data["Revenue Growth %"] and data["Revenue Growth %"] > 5)
                or (data["Upside %"] and data["Upside %"] > min_upside)
            )

            quality = (
                (data["ROE %"] and data["ROE %"] > min_roe)
                and (data["Debt/Equity"] and data["Debt/Equity"] < 150)
                and (data["Rec Score"] and data["Rec Score"] < 2.8)
            )

            if undervalued and growth and quality:
                results.append(data)

        progress.progress((i + 1) / len(tickers))

    df = pd.DataFrame(results)

    if not df.empty:
        df["Value Score"] = (
            df["PEG Ratio"].fillna(999) * 0.4
            + df["Trailing P/E"].fillna(999) * 0.3
            - df["Upside %"].fillna(0) * 0.3
        )

        df = df.sort_values("Value Score").reset_index(drop=True)

        st.success(f"✅ Found {len(df)} undervalued growth stocks")

        st.dataframe(
            df[
                ["Ticker", "Company", "Sector", "Trailing P/E",
                 "PEG Ratio", "Earnings Growth %", "Upside %", "ROE %"]
            ].round(2),
            use_container_width=True
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Results (CSV)",
            csv,
            "undervalued_growth_sp500_stocks.csv",
            "text/csv"
        )
    else:
        st.warning("No stocks matched the criteria. Try relaxing filters.")
