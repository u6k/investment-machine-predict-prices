import pandas as pd
import numpy as np


def execute():
    input_base_path = "local/stock_prices"
    output_base_path = "local/stock_prices_preprocessed"

    df_companies = pd.read_csv(f"{input_base_path}/companies.csv", index_col=0) \
        .sort_values("ticker_symbol") \
        .drop_duplicates() \
        .set_index("ticker_symbol")

    for ticker_symbol in df_companies.index:
        print(f"ticker_symbol: {ticker_symbol}")

        try:
            df_prices = pd.read_csv(f"{input_base_path}/stock_prices.{ticker_symbol}.csv", index_col=0) \
                .sort_values("date") \
                .drop_duplicates()
            df_prices["id"] = np.arange(len(df_prices))
            df_prices = df_prices.set_index("id")

            # Profit rate
            df_simulated = pd.read_csv(f"{input_base_path}/simulate_trade_2.{ticker_symbol}.csv", index_col=0)

            df_prices["end_id"] = df_simulated["end_id"]
            df_prices["sell_price"] = df_simulated["sell_price"]
            df_prices["profit"] = df_simulated["profit"]
            df_prices["profit_rate"] = df_simulated["profit_rate"]

            # Simple Moving Average
            for sma_len in [5, 10, 20, 40, 80]:
                df_prices[f"sma_{sma_len}"] = df_prices["adjusted_close_price"].rolling(sma_len).mean()

            # Momentum
            for momentum_len in [5, 10, 20, 40, 80]:
                df_prices[f"momentum_{momentum_len}"] = df_prices["adjusted_close_price"] - df_prices["adjusted_close_price"].shift(momentum_len-1)

            # ROC (Rate Of Change)
            for roc_len in [5, 10, 20, 40, 80]:
                df_prices[f"roc_{roc_len}"] = df_prices["adjusted_close_price"].pct_change(roc_len-1)

            # RSI
            for rsi_len in [5, 10, 14, 20, 40]:
                diff = df_prices["adjusted_close_price"].diff()
                diff = diff[1:]
                up, down = diff.copy(), diff.copy()
                up[up < 0] = 0
                down[down > 0] = 0
                up_sma = up.rolling(window=rsi_len, center=False).mean()
                down_sma = down.rolling(window=rsi_len, center=False).mean()
                rsi = up_sma / (up_sma - down_sma) * 100.0

                df_prices[f"rsi_{rsi_len}"] = rsi

            # Stochastic
            for stochastic_len in [5, 9, 20, 25, 40]:
                close = df_prices["close_price"]
                low = df_prices["low_price"]
                low_min = low.rolling(window=stochastic_len, center=False).min()
                high = df_prices["high_price"]
                high_max = high.rolling(window=stochastic_len, center=False).max()

                stochastic_k = ((close - low_min) / (high_max - low_min)) * 100
                stochastic_d = stochastic_k.rolling(window=3, center=False).mean()
                stochastic_sd = stochastic_d.rolling(window=3, center=False).mean()

                df_prices[f"stochastic_k_{stochastic_len}"] = stochastic_k
                df_prices[f"stochastic_d_{stochastic_len}"] = stochastic_d
                df_prices[f"stochastic_sd_{stochastic_len}"] = stochastic_sd

            # Save
            df_prices.to_csv(f"{output_base_path}/stock_prices.{ticker_symbol}.csv")
            df_companies.to_csv(f"{output_base_path}/companies.csv")
        except Exception as err:
            print(err)
