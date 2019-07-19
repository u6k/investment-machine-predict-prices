from simulate_trade_6 import SimulateTrade6


if __name__ == "__main__":
    s3_bucket = "u6k"
    input_prices_base_path = "ml-data/stocks/preprocess_1.test"
    input_preprocess_base_path = "ml-data/stocks/preprocess_7.test"
    input_model_base_path = "ml-data/stocks/predict_3_preprocess_7.test"
    output_base_path = "ml-data/stocks/simulate_trade_6_backtest.test"

    start_date = "2018-01-01"
    end_date = "2018-12-31"

    SimulateTrade6().backtest_singles(
        start_date,
        end_date,
        s3_bucket,
        input_prices_base_path,
        input_preprocess_base_path,
        input_model_base_path,
        output_base_path
    )

    SimulateTrade6().report_singles(
        s3_bucket,
        output_base_path
    )

    SimulateTrade6().backtest_all(
        s3_bucket,
        output_base_path
    )
