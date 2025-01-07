from flask import Flask, render_template, request, redirect, url_for
import os
import yfinance as yf

app = Flask(__name__)

SYMBOLS_FILE = "symbols.txt"
LOOKBACK = 14

# Function to calculate stochastic
def calculate_stochastic(df, lookback=14):
    df['LowestLow'] = df['Low'].rolling(window=lookback).min()
    df['HighestHigh'] = df['High'].rolling(window=lookback).max()
    df['Stoch_%K_raw'] = 100 * (df['Close'] - df['LowestLow']) / (df['HighestHigh'] - df['LowestLow'])
    df['Stoch_%K_slow'] = df['Stoch_%K_raw'].rolling(window=3).mean()
    return df

def fetch_data_for_symbol(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d")
        if df.empty:
            return (symbol, None, None, None)
        df = calculate_stochastic(df)
        latest_close = df['Close'].iloc[-1]
        latest_stoch_k = df['Stoch_%K_slow'].iloc[-1]
        return (symbol, latest_close, latest_stoch_k)
    except Exception as e:
        return (symbol, None, None)

def load_symbols():
    if not os.path.exists(SYMBOLS_FILE):
        return []
    with open(SYMBOLS_FILE, "r") as f:
        return [line.strip().upper() for line in f.readlines()]

def save_symbols(symbols):
    with open(SYMBOLS_FILE, "w") as f:
        f.write("\n".join(symbols))

@app.route("/")
def index():
    symbols = load_symbols()
    data = [fetch_data_for_symbol(sym) for sym in symbols]
    return render_template("index.html", data=data)

@app.route("/add", methods=["POST"])
def add_symbol():
    symbol = request.form.get("symbol").strip().upper()
    if symbol:
        symbols = load_symbols()
        if symbol not in symbols:
            symbols.append(symbol)
            save_symbols(symbols)
    return redirect(url_for("index"))

@app.route("/delete/<symbol>")
def delete_symbol(symbol):
    symbols = load_symbols()
    symbols = [s for s in symbols if s != symbol]
    save_symbols(symbols)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)