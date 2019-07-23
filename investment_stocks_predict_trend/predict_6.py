import argparse
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, r2_score
from keras.models import Sequential
from keras.layers import Conv1D, MaxPooling1D, GlobalMaxPooling1D
from keras.callbacks import EarlyStopping

from app_logging import get_app_logger
import app_s3
from predict_base import PredictClassificationBase


class PredictClassification_5(PredictClassificationBase):
    def preprocess_impl(self, ticker_symbol):
        L = get_app_logger(f"preprocess.{ticker_symbol}")
        L.info(f"predict preprocess_6: {ticker_symbol}")

        result = {
            "ticker_symbol": ticker_symbol,
            "exception": None
        }

        period = 20

        try:
            # Load data
            df_preprocess = app_s3.read_dataframe(self._s3_bucket, f"{self._input_preprocess_base_path}/stock_prices.{ticker_symbol}.csv", index_col=0)

            # Preprocess
            df = df_preprocess[[
                "date",
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "adjusted_close_price",
                "volume"
            ]].copy()

            df["profit"] = df["close_price"]-df["open_price"]
            df["profit_minmax"] = MinMaxScaler().fit_transform(df["profit"].values.reshape(-1, 1))

            for i in range(0, period):
                df[f"profit_minmax_{i}"] = df["profit_minmax"].shift(i)

            df["predict_target"] = df["profit_minmax"].shift(-1)

            df = df.drop(["profit", "profit_minmax"], axis=1)

            df = df.dropna()

            # Save data
            app_s3.write_dataframe(df, self._s3_bucket, f"{self._output_base_path}/stock_prices.{ticker_symbol}.csv")
        except Exception as err:
            L.exception(f"ticker_symbol={ticker_symbol}, {err}")
            result["exception"] = err

        return result

    def train(self):
        L = get_app_logger("train_6")
        L.info("start")

        df_companies = app_s3.read_dataframe(self._s3_bucket, f"{self._input_preprocess_base_path}/companies.csv", index_col=0)
        df_result = pd.DataFrame(columns=df_companies.columns)

        for ticker_symbol in df_companies.index:
            result = self.train_impl(ticker_symbol)

            if result["exception"] is not None:
                continue

            ticker_symbol = result["ticker_symbol"]
            scores = result["scores"]

            df_result.loc[ticker_symbol] = df_companies.loc[ticker_symbol]
            for key in scores.keys():
                df_result.at[ticker_symbol, key] = scores[key]

        app_s3.write_dataframe(df_result, self._s3_bucket, f"{self._output_base_path}/report.csv")

        L.info("finish")

    def train_impl(self, ticker_symbol):
        L = get_app_logger(ticker_symbol)
        L.info(f"train_6: {ticker_symbol}")

        result = {
            "ticker_symbol": ticker_symbol,
            "exception": None,
            "scores": None
        }

        try:
            x_train, x_test, y_train, y_test = self.train_test_split(ticker_symbol)

            model = self.model_fit(x_train, y_train)
            app_s3.write_keras_model(model, self._s3_bucket, f"{self._output_base_path}/model.{ticker_symbol}")

            result["scores"] = self.model_score(model, x_test, y_test)
        except Exception as err:
            L.exception(f"ticker_symbol={ticker_symbol}, {err}")
            result["exception"] = err

        return result

    def model_fit(self, x_train, y_train):
        x = x_train.reshape(len(x_train), len(x_train[0]), 1)
        y = y_train

        model = Sequential()
        model.add(Conv1D(filters=8, kernel_size=20, padding="same", input_shape=(20, 1), activation="relu"))
        model.add(MaxPooling1D(2, padding="same"))
        model.add(Conv1D(filters=8, kernel_size=20, padding="same", activation="relu"))
        model.add(MaxPooling1D(2, padding="same"))
        model.add(Conv1D(filters=1, kernel_size=10, padding="same", activation="relu"))
        model.add(GlobalMaxPooling1D())

        model.compile(loss="mse", optimizer="adam")

        model.fit(x, y, batch_size=128, epochs=100, verbose=0, validation_split=0.1, callbacks=[EarlyStopping(patience=10)])

        return model

    def model_score(self, model, x_test, y_test):
        x = x_test.reshape(len(x_test), len(x_test[0]), 1)

        y_pred = model.predict(x, batch_size=100, verbose=0)

        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        return {
            "rmse": rmse,
            "r2": r2
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="preprocess, or train")
    parser.add_argument("--suffix", help="folder name suffix (default: test)", default="test")
    args = parser.parse_args()

    pred = PredictClassification_5(
        train_start_date="2008-01-01",
        train_end_date="2017-12-31",
        test_start_date="2018-01-01",
        test_end_date="2018-12-31",
        s3_bucket="u6k",
        input_preprocess_base_path=f"ml-data/stocks/preprocess_1.{args.suffix}",
        input_simulate_base_path=None,
        output_base_path=f"ml-data/stocks/predict_6.{args.suffix}"
    )

    if args.task == "preprocess":
        pred.preprocess()
    elif args.task == "train":
        pred.train()
    else:
        parser.print_help()
