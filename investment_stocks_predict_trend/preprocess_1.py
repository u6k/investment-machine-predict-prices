import joblib
import numpy as np
import pandas as pd

from app_logging import get_app_logger
import app_s3


def execute():
    L = get_app_logger(__name__)
    L.info("start")

    s3_bucket = "u6k"
    input_base_path = "ml-data/stocks/stock_prices"
    output_base_path = "ml-data/stocks/preprocess_1.test"

    df_companies = app_s3.read_dataframe(s3_bucket, f"{input_base_path}/companies.csv", index_col=0) \
        .sort_values("ticker_symbol") \
        .dropna() \
        .drop_duplicates() \
        .set_index("ticker_symbol")
    df_companies_result = pd.DataFrame(columns=df_companies.columns)

    results = joblib.Parallel(n_jobs=-1)([joblib.delayed(preprocess)(ticker_symbol, s3_bucket, input_base_path, output_base_path) for ticker_symbol in df_companies.index])

    for result in results:
        if result["exception"] is not None:
            continue

        ticker_symbol = result["ticker_symbol"]
        df_companies_result.loc[ticker_symbol] = df_companies.loc[ticker_symbol]

    app_s3.write_dataframe(df_companies_result, s3_bucket, f"{output_base_path}/companies.csv")

    L.info("finish")


def preprocess(ticker_symbol, s3_bucket, input_base_path, output_base_path):
    L = get_app_logger(f"preprocess_1.{ticker_symbol}")
    L.info(f"preprocess_1: {ticker_symbol}")

    result = {
        "ticker_symbol": ticker_symbol,
        "exception": None
    }

    try:
        # Load data
        df = app_s3.read_dataframe(s3_bucket, f"{input_base_path}/stock_prices.{ticker_symbol}.csv", index_col=0)

        # Preprocess
        df = df.sort_values("date") \
            .dropna() \
            .drop_duplicates()
        df = df.assign(id=np.arange(len(df)))
        df = df.set_index("id")

        # Save data
        app_s3.write_dataframe(df, s3_bucket, f"{output_base_path}/stock_prices.{ticker_symbol}.csv")
    except Exception as err:
        L.exception(f"ticker_symbol={ticker_symbol}, {err}")
        result["exception"] = err

    return result


if __name__ == "__main__":
    execute()
