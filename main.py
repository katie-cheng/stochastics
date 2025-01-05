import tkinter as tk
from tkinter import ttk
import os
import yfinance as yf
import pandas as pd

##############################
# Settings
##############################
SYMBOLS_FILE = "symbols.txt"  # where symbols are saved
LOOKBACK = 14                 # standard Stochastic lookback

##############################
# Stochastic Calculation
##############################
def calculate_stochastic(df, lookback=14):
    """
    Compute a *slow* Stochastic (14,3,3):
      1) Stoch_%K_raw = 100 * (Close - LowestLow) / (HighestHigh - LowestLow)
      2) Stoch_%K_slow = 3-day SMA of Stoch_%K_raw
      3) Stoch_%D_slow = 3-day SMA of Stoch_%K_slow
    """
    df = df.copy()

    # 1) Raw (Fast) %K
    df['LowestLow'] = df['Low'].rolling(window=lookback).min()
    df['HighestHigh'] = df['High'].rolling(window=lookback).max()
    df['Stoch_%K_raw'] = 100 * (df['Close'] - df['LowestLow']) / (df['HighestHigh'] - df['LowestLow'])

    # 2) Slow %K
    df['Stoch_%K_slow'] = df['Stoch_%K_raw'].rolling(window=3).mean()

    # 3) Slow %D
    df['Stoch_%D_slow'] = df['Stoch_%K_slow'].rolling(window=3).mean()

    return df



##############################
# Symbol Persistence
##############################
def load_symbols():
    """Load symbols from SYMBOLS_FILE into a list."""
    if not os.path.exists(SYMBOLS_FILE):
        return []
    with open(SYMBOLS_FILE, "r") as f:
        lines = f.read().splitlines()
    symbols = [line.strip().upper() for line in lines if line.strip()]
    return symbols

def save_symbols(symbols_list):
    """Save symbols to SYMBOLS_FILE (one per line)."""
    with open(SYMBOLS_FILE, "w") as f:
        for sym in symbols_list:
            f.write(sym.upper() + "\n")

##############################
# Fetch & Process
##############################
def fetch_data_for_symbol(symbol):
    """
    Downloads daily data, renames 'Price' -> 'Low' if needed,
    calculates a 14,3,3 slow Stochastic, and returns
    (latest_close, latest_stoch_slow, day_diff).
    """
    try:
        df = yf.download(symbol, period="3mo", interval="1d")
    except Exception as e:
        print(f"Error downloading data for {symbol}: {e}")
        return (None, None, None)

    if df.empty:
        print(f"No data returned for {symbol}.")
        return (None, None, None)

    # If multi-index, slice out the single ticker level
    if isinstance(df.columns, pd.MultiIndex):
        try:
            df = df.xs(symbol, axis=1, level=-1, drop_level=True)
        except KeyError:
            print(f"KeyError slicing multi-index for {symbol}")
            return (None, None, None)

    # ---- IMPORTANT: Rename if "Low" is missing but "Price" is present ----
    cols = set(df.columns)
    if "Low" not in cols and "Price" in cols:
        print(f"Renaming 'Price' -> 'Low' for {symbol} ...")
        df.rename(columns={"Price": "Low"}, inplace=True)

    # Check for required columns
    needed = {'Open', 'High', 'Low', 'Close'}
    if not needed.issubset(df.columns):
        print(f"Missing columns for {symbol}. Needed: {needed}. Found: {df.columns}")
        return (None, None, None)

    # Calculate slow stoch
    df = calculate_stochastic(df, lookback=14)

    # We want the day-over-day difference in 'Stoch_%K_slow'
    # Make sure there's at least 2 rows
    if len(df) < 2:
        print(f"Not enough rows for day-over-day stoch for {symbol}.")
        return (None, None, None)

    latest_row = df.iloc[-1]
    prev_row = df.iloc[-2]

    latest_close = latest_row.get("Close", float('nan'))
    latest_slow_k = latest_row.get("Stoch_%K_slow", float('nan'))
    prev_slow_k = prev_row.get("Stoch_%K_slow", float('nan'))

    if pd.isna(latest_slow_k) or pd.isna(prev_slow_k):
        print(f"Stoch is NaN for {symbol} (slow stoch), possibly insufficient data.")
        return (latest_close, latest_slow_k, None)

    # Day-over-day difference
    stoch_diff = latest_slow_k - prev_slow_k

    return (latest_close, latest_slow_k, stoch_diff)

##############################
# Tkinter GUI
##############################
class StochasticsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stochastics (14) Tracker")

        # Main container
        container = ttk.Frame(self, padding="10")
        container.pack(fill="both", expand=True)

        # Load saved symbols
        self.symbols = load_symbols()

        # Row 0: Symbol entry + Buttons
        lbl = ttk.Label(container, text="Add Symbol:")
        lbl.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.symbol_entry = ttk.Entry(container, width=15)
        self.symbol_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        add_btn = ttk.Button(container, text="Add", command=self.add_symbol)
        add_btn.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        refresh_btn = ttk.Button(container, text="Refresh Data", command=self.refresh_data)
        refresh_btn.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Row 1: Table (Treeview)
        self.tree = ttk.Treeview(
            container,
            columns=("symbol", "price", "stoch", "diff"),
            show="headings",
            height=15
        )
        self.tree.heading("symbol", text="Symbol")
        self.tree.heading("price", text="Price")
        self.tree.heading("stoch", text="Stoch (14)")
        self.tree.heading("diff", text="ΔStoch (Day)")

        self.tree.column("symbol", width=80, anchor="center")
        self.tree.column("price", width=100, anchor="e")
        self.tree.column("stoch", width=100, anchor="e")
        self.tree.column("diff", width=100, anchor="e")

        self.tree.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)

        # Make row 1 expand
        container.rowconfigure(1, weight=1)
        container.columnconfigure(1, weight=1)

        # Initial load
        self.refresh_data()

    def add_symbol(self):
        """Add a new symbol to the list, save, and refresh."""
        new_sym = self.symbol_entry.get().strip().upper()
        if not new_sym:
            return
        if new_sym not in self.symbols:
            self.symbols.append(new_sym)
            save_symbols(self.symbols)
        self.symbol_entry.delete(0, tk.END)
        self.refresh_data()

    def refresh_data(self):
        """Fetch data for all symbols and update the tree."""
        # Clear existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        for sym in self.symbols:
            close_price, stoch_val, stoch_diff = fetch_data_for_symbol(sym)

            # Convert to strings for display
            if close_price is None or pd.isna(close_price):
                close_str = "N/A"
            else:
                close_str = f"{close_price:.2f}"

            if stoch_val is None or pd.isna(stoch_val):
                stoch_str = "N/A"
            else:
                stoch_str = f"{stoch_val:.2f}"

            if stoch_diff is None or pd.isna(stoch_diff):
                diff_str = "N/A"
            else:
                # Include sign (+/-)
                diff_str = f"{stoch_diff:+.2f}"

            # Insert into the table
            self.tree.insert("", tk.END, values=(sym, close_str, stoch_str, diff_str))

def main():
    app = StochasticsApp()
    app.mainloop()

if __name__ == "__main__":
    main()