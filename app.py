import argparse
import os
from comet_ml import Experiment
from investment_stocks_predict_trend import select_company
from investment_stocks_predict_trend import random_forest_1
from investment_stocks_predict_trend import random_forest_2
from investment_stocks_predict_trend import agent_1
from investment_stocks_predict_trend import agent_2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("subcommand")

    args = parser.parse_args()

    if args.subcommand == "select_company.preprocessing":
        select_company.preprocessing()
    elif args.subcommand == "select_company.top":
        select_company.top()
    elif args.subcommand == "random_forest_1.scores":
        random_forest_1.scores()
    elif args.subcommand == "random_forest_2.scores":
        random_forest_2.scores()
    elif args.subcommand == "agent_1":
        experiment = Experiment(api_key=os.environ["COMET_ML_API_KEY"],
                                project_name="agent_1")
        agent_1.execute(experiment)
        experiment.end()
    elif args.subcommand == "agent_2":
        experiment = Experiment(api_key=os.environ["COMET_ML_API_KEY"],
                                project_name="agent_2")
        agent_2.execute(experiment)
        experiment.end()
    else:
        raise Exception("unknown subcommand: " + args.subcommand)
