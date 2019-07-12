import joblib
import pandas as pd

from app_logging import get_app_logger


def execute():
    L = get_app_logger()
    L.info("start")

    input_base_path_preprocess = "local/preprocess_2"
    input_base_path_simulate = "local/simulate_trade_4"
    output_base_path = "local/preprocess_5"

    train_start_date = "2008-01-01"
    train_end_date = "2017-12-31"
    test_start_date = "2018-01-01"
    test_end_date = "2018-12-31"

    df_companies = pd.read_csv(f"{input_base_path_preprocess}/companies.csv", index_col=0)
    df_companies_result = pd.DataFrame(columns=df_companies.columns)

    results = joblib.Parallel(n_jobs=-1)([joblib.delayed(preprocess)(ticker_symbol, input_base_path_preprocess, input_base_path_simulate, output_base_path) for ticker_symbol in df_companies.index])
    results = joblib.Parallel(n_jobs=-1)([joblib.delayed(train_test_split)(ticker_symbol, output_base_path, train_start_date, train_end_date, test_start_date, test_end_date) for ticker_symbol in df_companies.index])

    for result in results:
        ticker_symbol = result[0]
        message = result[1]

        df_companies_result.loc[ticker_symbol] = df_companies.loc[ticker_symbol]
        df_companies_result.at[ticker_symbol, "message"] = message

    df_companies_result.to_csv(f"{output_base_path}/companies.csv")
    L.info("finish")


def preprocess(ticker_symbol, input_base_path_preprocess, input_base_path_simulate, output_base_path):
    L = get_app_logger(f"preprocess.{ticker_symbol}")
    L.info(f"preprocess: {ticker_symbol}")

    try:
        df_preprocess = pd.read_csv(f"{input_base_path_preprocess}/stock_prices.{ticker_symbol}.csv", index_col=0)
        df_simulate = pd.read_csv(f"{input_base_path_simulate}/stock_prices.{ticker_symbol}.csv", index_col=0)

        df = df_preprocess[[
            "date",
            "volume_change_minmax",
            "adjusted_close_price_change_minmax",
            "sma_5_minmax",
            "sma_10_minmax",
            "sma_20_minmax",
            "sma_40_minmax",
            "sma_80_minmax",
            "momentum_5_minmax",
            "momentum_10_minmax",
            "momentum_20_minmax",
            "momentum_40_minmax",
            "momentum_80_minmax",
            "roc_5_minmax",
            "roc_10_minmax",
            "roc_20_minmax",
            "roc_40_minmax",
            "roc_80_minmax",
            "rsi_5_minmax",
            "rsi_10_minmax",
            "rsi_14_minmax",
            "rsi_20_minmax",
            "rsi_40_minmax",
            "stochastic_k_5_minmax",
            "stochastic_d_5_minmax",
            "stochastic_sd_5_minmax",
            "stochastic_k_9_minmax",
            "stochastic_d_9_minmax",
            "stochastic_sd_9_minmax",
            "stochastic_k_20_minmax",
            "stochastic_d_20_minmax",
            "stochastic_sd_20_minmax",
            "stochastic_k_25_minmax",
            "stochastic_d_25_minmax",
            "stochastic_sd_25_minmax",
            "stochastic_k_40_minmax",
            "stochastic_d_40_minmax",
            "stochastic_sd_40_minmax"
        ]].copy()

        df["predict_target_value"] = df_simulate["profit_rate"]
        df["predict_target_label"] = df["predict_target_value"].apply(lambda v: 1 if v > 0.0 else 0)

        df.to_csv(f"{output_base_path}/stock_prices.{ticker_symbol}.csv")

        message = ""
    except Exception as err:
        L.exception(err)
        message = err.__str__()

    return (ticker_symbol, message)


def train_test_split(ticker_symbol, base_path, train_start_date, train_end_date, test_start_date, test_end_date):
    L = get_app_logger(f"train_test_split.{ticker_symbol}")
    L.info(f"train_test_split: {ticker_symbol}")

    try:
        df = pd.read_csv(f"{base_path}/stock_prices.{ticker_symbol}.csv", index_col=0) \
            .dropna()

        if len(df.query(f"date < '{train_start_date}'")) == 0 or len(df.query(f"date > '{test_end_date}'")) == 0:
            raise Exception("little data")

        train_start_id = df.query(f"'{train_start_date}' <= date <= '{train_end_date}'").index[0]
        train_end_id = df.query(f"'{train_start_date}' <= date <= '{train_end_date}'").index[-1]
        test_start_id = df.query(f"'{test_start_date}' <= date <= '{test_end_date}'").index[0]
        test_end_id = df.query(f"'{test_start_date}' <= date <= '{test_end_date}'").index[-1]

        df_data_train = df.loc[train_start_id: train_end_id].drop(["date", "predict_target_value", "predict_target_label"], axis=1)
        df_data_test = df.loc[test_start_id: test_end_id].drop(["date", "predict_target_value", "predict_target_label"], axis=1)
        df_target_train = df.loc[train_start_id: train_end_id][["predict_target_value", "predict_target_label"]]
        df_target_test = df.loc[test_start_id: test_end_id][["predict_target_value", "predict_target_label"]]

        df_data_train.to_csv(f"{base_path}/stock_prices.{ticker_symbol}.data_train.csv")
        df_data_test.to_csv(f"{base_path}/stock_prices.{ticker_symbol}.data_test.csv")
        df_target_train.to_csv(f"{base_path}/stock_prices.{ticker_symbol}.target_train.csv")
        df_target_test.to_csv(f"{base_path}/stock_prices.{ticker_symbol}.target_test.csv")

        message = ""
    except Exception as err:
        L.exception(err)
        message = err.__str__()

    return (ticker_symbol, message)


if __name__ == "__main__":
    execute()
