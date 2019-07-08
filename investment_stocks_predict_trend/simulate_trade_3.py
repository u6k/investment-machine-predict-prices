import pandas as pd


def execute():
    input_base_path = "local/preprocess_1"
    output_base_path = "local/simulate_trade_3"

    # Load companies
    df_companies = pd.read_csv(f"{input_base_path}/companies.csv", index_col=0)
    df_companies_result = pd.DataFrame(columns=df_companies.columns)

    for ticker_symbol in df_companies.index:
        print(f"ticker_symbol={ticker_symbol}")

        df_companies_result.loc[ticker_symbol] = df_companies.loc[ticker_symbol]

        try:
            simulate_trade(ticker_symbol, input_base_path, output_base_path)
            df_companies_result.at[ticker_symbol, "message"] = ""
        except Exception as err:
            df_companies_result.at[ticker_symbol, "message"] = err.__str__()

        df_companies_result.to_csv(f"{output_base_path}/companies.csv")
        print(df_companies_result.loc[ticker_symbol])


def simulate_trade(ticker_symbol, input_base_path, output_base_path):
    df = pd.read_csv(f"{input_base_path}/stock_prices.{ticker_symbol}.csv", index_col=0)

    df["day_trade_profit_rate"] = df["close_price"] / df["open_price"]
    df["day_trade_profit_flag"] = df["day_trade_profit_rate"].apply(lambda r: 1 if r > 1.0 else 0)

    df.to_csv(f"{output_base_path}/stock_prices.{ticker_symbol}.csv")


if __name__ == "__main__":
    execute()
