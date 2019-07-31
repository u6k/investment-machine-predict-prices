import argparse

from sklearn.svm import SVC
from predict_base import PredictClassificationBase
import app_s3


class PredictClassification_5(PredictClassificationBase):
    def model_fit(self, x_train, y_train):
        return SVC(gamma="scale").fit(x_train, y_train)

    def model_predict(self, ticker_symbol, df_data):
        model = app_s3.read_sklearn_model(self._s3_bucket, f"{self._output_base_path}/model.{ticker_symbol}.joblib")

        pred = model.predict(df_data.values)

        return pred


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate-group", help="simulate trade group")
    parser.add_argument("--suffix", help="folder name suffix (default: test)", default="test")
    args = parser.parse_args()

    pred = PredictClassification_5(
        job_name="predict_5",
        train_start_date="2008-01-01",
        train_end_date="2017-12-31",
        test_start_date="2018-01-01",
        test_end_date="2018-12-31",
        s3_bucket="u6k",
        input_preprocess_base_path=f"ml-data/stocks/preprocess_3.{args.suffix}",
        input_simulate_base_path=f"ml-data/stocks/simulate_trade_{args.simulate_group}.{args.suffix}",
        output_base_path=f"ml-data/stocks/predict_5.simulate_trade_{args.simulate_group}.{args.suffix}"
    )

    pred.train()
