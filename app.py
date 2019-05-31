import argparse

import investment_stocks_predict_trend as app

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "subcommand", help="processing_by_company, top_companies, build_model, build_model_2")

    args = parser.parse_args()

    if args.subcommand == "processing_by_company":
        app.processing_by_company()
    elif args.subcommand == "top_companies":
        app.top_companies()
    elif args.subcommand == "build_model":
        app.build_model()
    elif args.subcommand == "build_models_2":
        app.build_models_2()
    else:
        raise Exception("unknown subcommand: " + args.subcommand)
