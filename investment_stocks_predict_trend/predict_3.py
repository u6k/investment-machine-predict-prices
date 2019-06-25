import pandas as pd
from sklearn import ensemble, metrics, model_selection
# import joblib


def preprocess():
    input_base_path = "local/stock_prices_preprocessed"
    output_base_path = "local/predict_3"

    df_companies = pd.read_csv(f"{input_base_path}/companies.csv", index_col=0)
    df_companies = df_companies.query("data_size > 2500")
    df_companies.to_csv(f"{output_base_path}/companies.csv")

    for ticker_symbol in df_companies.index:
        print(ticker_symbol)

        df_prices_preprocessed = pd.read_csv(f"{input_base_path}/stock_prices.{ticker_symbol}.csv", index_col=0)
        df_prices_simulate_trade_2 = pd.read_csv(f"local/simulate_trade_2/result.{ticker_symbol}.csv", index_col=0)

        df_prices = pd.DataFrame()
        df_prices["id"] = df_prices_preprocessed.index
        df_prices = df_prices.set_index("id")
        df_prices["volume_change"] = df_prices_preprocessed["volume"].pct_change()
        df_prices["adjusted_close_price_change"] = df_prices_preprocessed["adjusted_close_price"].pct_change()
        df_prices["sma_5_change"] = df_prices_preprocessed["sma_5"].pct_change()
        df_prices["sma_10_change"] = df_prices_preprocessed["sma_10"].pct_change()
        df_prices["sma_20_change"] = df_prices_preprocessed["sma_20"].pct_change()
        df_prices["sma_40_change"] = df_prices_preprocessed["sma_40"].pct_change()
        df_prices["sma_80_change"] = df_prices_preprocessed["sma_80"].pct_change()
        df_prices["profit_rate"] = df_prices_simulate_trade_2["profit_rate"]
        df_prices["profit_flag"] = df_prices_simulate_trade_2["profit_rate"].apply(lambda r: 1 if r > 1.0 else 0)

        df_prices = df_prices.dropna()
        df_prices.to_csv(f"local/predict_3/input.{ticker_symbol}.csv")


def x_y_split(df_prices_preprocessed):
    x = df_prices_preprocessed.drop("profit_rate", axis=1).drop("profit_flag", axis=1).values
    y = df_prices_preprocessed["profit_flag"].values

    return x, y


def train():
    df_companies = pd.read_csv("local/predict_3/companies.csv", index_col=0)
    df_result = df_companies[["name", "data_size"]].copy()

    for ticker_symbol in df_companies.index:
        print(f"ticker_symbol={ticker_symbol}")

        try:
            df_input = pd.read_csv(f"local/predict_3/input.{ticker_symbol}.csv", index_col=0)

            df_train = df_input[:int(len(df_input)/4*3)]
            df_test = df_input[len(df_train):]
            print(f"df_input len={len(df_input)}")
            print(f"df_train len={len(df_train)}")
            print(f"df_test len={len(df_test)}")

            x_train, y_train = x_y_split(df_train)
            x_test, y_test = x_y_split(df_test)

            clf_best = model_fit(x_train, y_train)
            # joblib.dump(clf_best, f"local/predict_3/random_forest_classifier.{ticker_symbol}.joblib", compress=9)

            # clf = joblib.load(f"local/predict_3/random_forest_classifier.{ticker_symbol}.joblib")
            clf = clf_best
            df_result.at[ticker_symbol, "params"] = clf.get_params().__str__()

            ac_score = model_score(clf, x_test, y_test)
            print(f"ac_score={ac_score}")
            df_result.at[ticker_symbol, "ac_score"] = ac_score

            df_test_2 = df_test.query("profit_rate>1.0")
            print(f"df_test_2 len={len(df_test_2)}")

            x_test_2, y_test_2 = x_y_split(df_test_2)

            ac_score_2 = model_score(clf, x_test_2, y_test_2)
            print(f"ac_score_2={ac_score_2}")
            df_result.at[ticker_symbol, "ac_score_2"] = ac_score_2

            df_result.to_csv("local/predict_3/result.csv")
        except Exception as err:
            print(err)


def model_fit(x_train, y_train, experiment=None):
    parameters = {
        "n_estimators": [10, 100, 200, 500, 1000],
        "max_features": [1, "auto", None],
        "max_depth": [1, 5, 10, 20, 50, None]
    }

    if experiment is not None:
        experiment.log_parameters(parameters)

    clf = model_selection.GridSearchCV(ensemble.RandomForestClassifier(),
                                       parameters,
                                       n_jobs=-1,
                                       cv=5)

    clf.fit(x_train, y_train)

    best_params = clf.best_params_

    if experiment is not None:
        experiment.log_metrics(best_params)

    clf_best = clf.best_estimator_

    return clf_best


def model_score(clf_best, x_test, y_test, experiment=None):
    result = clf_best.predict(x_test)
    ac_score = metrics.accuracy_score(y_test, result)

    if experiment is not None:
        experiment.log_metric("accuracy_score", ac_score)

    return ac_score
