import argparse
from datetime import datetime
import pandas as pd

from app_logging import get_app_logger
import app_s3
from simulate_trade_base import SimulateTradeBase


class SimulateTrade6(SimulateTradeBase):
    def simulate_impl(self, ticker_symbol, s3_bucket, input_base_path, output_base_path):
        L = get_app_logger(f"{self._job_name}.simulate_impl.{ticker_symbol}")
        L.info(f"{self._job_name}.simulate_impl: {ticker_symbol}")

        result = {
            "ticker_symbol": ticker_symbol,
            "exception": None
        }

        sma_len_array = [5, 10]
        losscut_rate=0.98
        take_profit_rate=0.95

        minimum_profit_rate = 0.03

        try:
            # Load data
            df = app_s3.read_dataframe(s3_bucket, f"{input_base_path}/stock_prices.{ticker_symbol}.csv", index_col=0)

            # Preprocess
            for sma_len in sma_len_array:
                df[f"sma_{sma_len}"] = df["adjusted_close_price"].rolling(sma_len).mean()
                df[f"sma_{sma_len}_1"] = df[f"sma_{sma_len}"].shift(1)

            # Set signal
            target_id_array = df.query(f"(sma_{sma_len_array[0]}_1 < sma_{sma_len_array[1]}_1) and (sma_{sma_len_array[0]} >= sma_{sma_len_array[1]})").index
            for id in target_id_array:
                df.at[id, "signal"] = "buy"

            target_id_array = df.query(f"(sma_{sma_len_array[0]}_1 > sma_{sma_len_array[1]}_1) and (sma_{sma_len_array[0]} <= sma_{sma_len_array[1]})").index
            for id in target_id_array:
                df.at[id, "signal"] = "sell"

            # Simulate
            buy_id = None
            losscut_price=None
            take_profit_price=None
            take_profit=None

            for id in df.index[1:]:
                # Sell: take profit
                if take_profit:
                    buy_price = df.at[buy_id, "open_price"]
                    sell_price = df.at[id, "open_price"]
                    profit = sell_price - buy_price
                    profit_rate = profit / sell_price

                    df.at[buy_id, "result"]="take profit"
                    df.at[buy_id, "sell_id"] = id
                    df.at[buy_id, "buy_price"] = buy_price
                    df.at[buy_id, "sell_price"] = sell_price
                    df.at[buy_id, "profit"] = profit
                    df.at[buy_id, "profit_rate"] = profit_rate

                    buy_id = None
                    losscut_price=None
                    take_profit_price=None
                    take_profit=None

                # Sell: losscut
                if buy_id is not None and df.at[id, "low_price"] < losscut_price:
                    buy_price = df.at[buy_id, "open_price"]
                    sell_price = df.at[id, "open_price"]
                    profit = sell_price - buy_price
                    profit_rate = profit / sell_price

                    df.at[buy_id, "result"] = "losscut"
                    df.at[buy_id, "sell_id"] = id
                    df.at[buy_id, "buy_price"] = buy_price
                    df.at[buy_id, "sell_price"] = sell_price
                    df.at[buy_id, "profit"] = profit
                    df.at[buy_id, "profit_rate"] = profit_rate

                    buy_id = None
                    losscut_price=None
                    take_profit_price=None
                    take_profit=None

                # Flag: take profit
                if buy_id is not None and df.at[id, "high_price"] < take_profit_price:
                    take_profit=True

                # Buy
                if buy_id is None and df.at[id-1, "signal"] == "buy":
                    buy_id = id
                    losscut_price=df.at[id, "close_price"] * losscut_rate
                    take_profit_price=df.at[id, "high_price"] * take_profit_rate
                    take_profit=False

                # Sell
                if buy_id is not None and df.at[id-1, "signal"] == "sell":
                    buy_price = df.at[buy_id, "open_price"]
                    sell_price = df.at[id, "open_price"]
                    profit = sell_price - buy_price
                    profit_rate = profit / sell_price

                    df.at[buy_id, "result"] = "sell signal"
                    df.at[buy_id, "sell_id"] = id
                    df.at[buy_id, "buy_price"] = buy_price
                    df.at[buy_id, "sell_price"] = sell_price
                    df.at[buy_id, "profit"] = profit
                    df.at[buy_id, "profit_rate"] = profit_rate

                    buy_id = None
                    losscut_price=None
                    take_profit_price=None
                    take_profit=None

                # Update losscut/take profit price
                if buy_id is not None:
                    losscut_price_tmp=df.at[id, "close_price"] * losscut_rate
                    if losscut_price_tmp > losscut_price:
                        losscut_price = losscut_price_tmp

                    take_profit_price_tmp=df.at[id, "high_price"] * take_profit_rate
                    if take_profit_price_tmp > take_profit_price:
                        take_profit_price=take_profit_price_tmp

            # Labeling for predict
            df["predict_target"] = df["profit_rate"].shift(-1).apply(lambda r: 1 if r >= minimum_profit_rate else 0)

            # Save data
            app_s3.write_dataframe(df, s3_bucket, f"{output_base_path}/stock_prices.{ticker_symbol}.csv")
        except Exception as err:
            L.exception(f"ticker_symbol={ticker_symbol}, {err}")
            result["exception"] = err

        return result

    def forward_test_impl(self, ticker_symbol, start_date, end_date, s3_bucket, input_simulate_base_path, input_model_base_path, output_base_path):
        L = get_app_logger(f"{self._job_name}.forward_test_impl.{ticker_symbol}")
        L.info(f"{self._job_name}.forward_test_impl: {ticker_symbol}")

        result = {
            "ticker_symbol": ticker_symbol,
            "exception": None
        }

        try:
            # Load data
            clf = app_s3.read_sklearn_model(s3_bucket, f"{input_model_base_path}/model.{ticker_symbol}.joblib")
            df = app_s3.read_dataframe(s3_bucket, f"{input_simulate_base_path}/stock_prices.{ticker_symbol}.csv", index_col=0) \
                    .rename(columns={
                        "buy_price":"simulate_buy_price",
                        "sell_price":"simulate_sell_price",
                        "profit":"simulate_profit",
                        "profit_rate":"simulate_profit_rate"
                        })
            df_preprocess = app_s3.read_dataframe(s3_bucket, f"{input_model_base_path}/stock_prices.{ticker_symbol}.csv", index_col=0)




            # Predict
            target_period_ids = df_prices.query(f"'{start_date}' <= date <= '{end_date}'").index
            df_prices = df_prices.loc[target_period_ids[0]-1: target_period_ids[-1]]
            data = df_preprocessed.loc[target_period_ids[0]-1: target_period_ids[-1]].values
            df_prices = df_prices.assign(predict=clf.predict(data))

            # Backtest
            buy_id = None
            for id in target_period_ids:
                # Buy
                if df_prices.at[id-1, "signal"] == "buy" and df_prices.at[id-1, "predict"] == 1:
                    buy_id = id

                    df_prices.at[id, "action"] = "buy"

                # Sell
                if buy_id is not None and df_prices.at[id-1, "signal"] == "sell":
                    buy_price = df_prices.at[buy_id, "open_price"]
                    sell_price = df_prices.at[id, "open_price"]
                    profit = sell_price - buy_price
                    profit_rate = profit / sell_price

                    df_prices.at[id, "action"] = "sell"
                    df_prices.at[id, "buy_price"] = buy_price
                    df_prices.at[id, "sell_price"] = sell_price
                    df_prices.at[id, "profit"] = profit
                    df_prices.at[id, "profit_rate"] = profit_rate

                    buy_id = None

            app_s3.write_dataframe(df_prices, s3_bucket, f"{output_base_path}/stock_prices.{ticker_symbol}.csv")

        except Exception as err:
            L.exception(f"ticker_symbol={ticker_symbol}, {err}")
            result["exception"] = err

        return result

    def test_all(self, start_date, end_date, s3_bucket, base_path):
        L = get_app_logger("test_all")
        L.info("start")

        # Load data
        df_report = app_s3.read_dataframe(s3_bucket, f"{base_path}/report.csv", index_col=0)

        df_prices_dict = {}
        for ticker_symbol in df_report.query("trade_count>5").sort_values("profit_factor", ascending=False).head(50).index:
            if ticker_symbol in ["ni225", "topix", "djia"]:
                continue

            L.info(f"load data: {ticker_symbol}")

            df_prices = app_s3.read_dataframe(s3_bucket, f"{base_path}/stock_prices.{ticker_symbol}.csv", index_col=0)
            df_prices_dict[ticker_symbol] = df_prices

        df_action = pd.DataFrame(columns=["date", "ticker_symbol", "action", "price", "stocks", "profit", "profit_rate"])
        df_stocks = pd.DataFrame(columns=["buy_price", "buy_stocks", "open_price_latest"])
        df_result = pd.DataFrame(columns=["fund", "asset"])

        # Initialize
        fund = 100000
        asset = fund
        available_rate = 0.05
        total_available_rate = 0.5
        fee_rate = 0.001
        tax_rate = 0.21

        for date in self.date_range(start_date, end_date):
            date_str = date.strftime("%Y-%m-%d")
            L.info(f"test_all: {date_str}")

            # Sell
            for ticker_symbol in df_stocks.index:
                df_prices = df_prices_dict[ticker_symbol]

                if len(df_prices.query(f"date=='{date_str}'")) == 0:
                    continue

                prices_id = df_prices.query(f"date=='{date_str}'").index[0]

                if df_prices.at[prices_id-1, "action"] != "sell":
                    continue

                sell_price = df_prices.at[prices_id, "open_price"]

                buy_price = df_stocks.at[ticker_symbol, "buy_price"]
                buy_stocks = df_stocks.at[ticker_symbol, "buy_stocks"]

                profit = (sell_price - buy_price) * buy_stocks
                profit_rate = profit / (sell_price * buy_stocks)

                fund += sell_price * buy_stocks

                action_id = len(df_action)
                df_action.at[action_id, "date"] = date_str
                df_action.at[action_id, "ticker_symbol"] = ticker_symbol
                df_action.at[action_id, "action"] = "sell"
                df_action.at[action_id, "price"] = sell_price
                df_action.at[action_id, "stocks"] = buy_stocks
                df_action.at[action_id, "profit"] = profit
                df_action.at[action_id, "profit_rate"] = profit_rate

                fee_price = (sell_price * buy_stocks) * fee_rate
                fund -= fee_price

                action_id = len(df_action)
                df_action.at[action_id, "date"] = date_str
                df_action.at[action_id, "ticker_symbol"] = ticker_symbol
                df_action.at[action_id, "action"] = "fee"
                df_action.at[action_id, "price"] = fee_price
                df_action.at[action_id, "stocks"] = 1
                df_action.at[action_id, "profit"] = -1 * fee_price

                if profit > 0:
                    tax_price = profit * tax_rate
                    fund -= tax_price

                    action_id = len(df_action)
                    df_action.at[action_id, "date"] = date_str
                    df_action.at[action_id, "ticker_symbol"] = ticker_symbol
                    df_action.at[action_id, "action"] = "tax"
                    df_action.at[action_id, "price"] = tax_price
                    df_action.at[action_id, "stocks"] = 1
                    df_action.at[action_id, "profit"] = -1 * tax_price

                df_stocks = df_stocks.drop(ticker_symbol)

            # Buy
            for ticker_symbol in df_prices_dict.keys():
                df_prices = df_prices_dict[ticker_symbol]

                if len(df_prices.query(f"date=='{date_str}'")) == 0:
                    continue

                prices_id = df_prices.query(f"date=='{date_str}'").index[0]

                if df_prices.at[prices_id, "action"] != "buy":
                    continue

                buy_price = df_prices.at[prices_id, "open_price"]
                buy_stocks = asset * available_rate // buy_price

                if buy_stocks <= 0:
                    continue

                if (fund - buy_price * buy_stocks) < (asset * total_available_rate):
                    continue

                fund -= buy_price * buy_stocks

                action_id = len(df_action)
                df_action.at[action_id, "date"] = date_str
                df_action.at[action_id, "ticker_symbol"] = ticker_symbol
                df_action.at[action_id, "action"] = "buy"
                df_action.at[action_id, "price"] = buy_price
                df_action.at[action_id, "stocks"] = buy_stocks

                fee_price = (buy_price * buy_stocks) * fee_rate
                fund -= fee_price

                action_id = len(df_action)
                df_action.at[action_id, "date"] = date_str
                df_action.at[action_id, "ticker_symbol"] = ticker_symbol
                df_action.at[action_id, "action"] = "fee"
                df_action.at[action_id, "price"] = fee_price
                df_action.at[action_id, "stocks"] = 1
                df_action.at[action_id, "profit"] = -1 * fee_price

                df_stocks.at[ticker_symbol, "buy_price"] = buy_price
                df_stocks.at[ticker_symbol, "buy_stocks"] = buy_stocks
                df_stocks.at[ticker_symbol, "open_price_latest"] = buy_price

            # Turn end
            for ticker_symbol in df_stocks.index:
                df_prices = df_prices_dict[ticker_symbol]

                if len(df_prices.query(f"date=='{date_str}'")) == 0:
                    continue

                prices_id = df_prices.query(f"date=='{date_str}'").index[0]

                df_stocks.at[ticker_symbol, "open_price_latest"] = df_prices.at[prices_id, "open_price"]

            asset = fund
            for ticker_symbol in df_stocks.index:
                asset += df_stocks.at[ticker_symbol, "open_price_latest"] * df_stocks.at[ticker_symbol, "buy_stocks"]

            df_result.at[date_str, "fund"] = fund
            df_result.at[date_str, "asset"] = asset

            L.info(df_result.loc[date_str])

        app_s3.write_dataframe(df_action, s3_bucket, f"{base_path}/test_all.action.csv")
        app_s3.write_dataframe(df_result, s3_bucket, f"{base_path}/test_all.result.csv")

        L.info("finish")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", help="simulate, forward_test, or forward_test_all")
    parser.add_argument("--suffix", help="folder name suffix (default: test)", default="test")
    args = parser.parse_args()

    simulator = SimulateTrade6("simulate_trade_6")

    if args.task == "simulate":
        simulator.simulate(
            s3_bucket="u6k",
            input_base_path=f"ml-data/stocks/preprocess_1.{args.suffix}",
            output_base_path=f"ml-data/stocks/simulate_trade_6.{args.suffix}"
        )

        simulator.simulate_report(
            start_date="2018-01-01",
            end_date="2018-12-31",
            s3_bucket="u6k",
            base_path=f"ml-data/stocks/simulate_trade_6.{args.suffix}"
        )
    elif args.task == "forward_test":
        simulator.forward_test(
            start_date="2018-01-01",
            end_date="2018-12-31",
            s3_bucket="u6k",
            input_simulate_base_path=f"ml-data/stocks/simulate_trade_6.{args.suffix}",
            input_model_base_path=f"ml-data/stocks/predict_3.simulate_trade_6.{args.suffix}",
            output_base_path=f"ml-data/stocks/forward_test_6.{args.suffix}"
        )

        simulator.forward_test_report(
            start_date="2018-01-01",
            end_date="2018-12-31",
            s3_bucket="u6k",
        )
    elif args.task == "forward_test_all":
        simulator.forward_test_all(
            start_date=datetime(2018, 1, 1),
            end_date=datetime(2019, 1, 1),
            s3_bucket="u6k",
            base_path=f"ml-data/stocks/forward_test_6.{args.suffix}"
        )
    else:
        parser.print_help()
