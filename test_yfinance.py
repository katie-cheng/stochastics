@app.route("/test_yfinance")
def test_yfinance():
    import yfinance as yf
    try:
        df = yf.download("AAPL", period="3mo", interval="1d")
        if df.empty:
            return "No data returned."
        return df.tail(1).to_html()  # Show the last row as HTML
    except Exception as e:
        return f"Error: {e}"