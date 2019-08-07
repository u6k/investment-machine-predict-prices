import argparse

from sklearn.svm import SVC
from sklearn import model_selection
from predict_base import PredictClassificationBase
import app_s3


class PredictClassification_5(PredictClassificationBase):
    def model_fit(self, x_train, y_train):
        # return SVC(C=100.0, kernel="rbf", gamma="scale", random_state=0).fit(x_train, y_train)
        params = {
            "C": [10.0, 20.0, 30.0, 40.0, 50.0],
            "kernel": ["rbf"],
            "gamma": ["scale"],
            "random_state": [0]
        }

        clf = model_selection.GridSearchCV(
            SVC(),
            params,
            cv=5,
            n_jobs=-1,
            verbose=1
        )

        clf.fit(x_train, y_train)

        print(f"best_params: {clf.best_params_}")

        clf_best = clf.best_estimator_

        return clf_best

    def model_predict(self, ticker_symbol, df_data):
        model = app_s3.read_sklearn_model(self._s3_bucket, f"{self._output_base_path}/model.{ticker_symbol}.joblib")

        df_data["predict"] = model.predict(df_data.values)

        return df_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate-group", help="simulate trade group")
    parser.add_argument("--suffix", help="folder name suffix (default: test)", default="test")
    args = parser.parse_args()

    pred = PredictClassification_5(
        job_name="predict_5",
        train_start_date="2008-01-01",
        train_end_date="2018-01-01",
        test_start_date="2018-01-01",
        test_end_date="2019-01-01",
        s3_bucket="u6k",
        input_preprocess_base_path=f"ml-data/stocks/preprocess_3.{args.suffix}",
        input_simulate_base_path=f"ml-data/stocks/simulate_trade_{args.simulate_group}.{args.suffix}",
        output_base_path=f"ml-data/stocks/predict_5.simulate_trade_{args.simulate_group}.{args.suffix}"
    )

    pred.train()
