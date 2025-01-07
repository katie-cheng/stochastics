import yfinance as yf

try:
    df = yf.download("AAPL", period="3mo", interval="1d")
    print(df.head())
except Exception as e:
    print("Error:", e)