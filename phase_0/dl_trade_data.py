import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

import pickle
import json
from datetime import datetime

from processor_Dataset import DatasetProcessor
from config_main import TICKER_LIST, FEATURE_TICKERS, TECHNICAL_INDICATORS_LIST, TIMEFRAME, trade_start_date, trade_end_date, no_candles_for_train


def main():
    print_config_variables()
    data_from_processor, price_array, tech_array, time_array, config, actual_features = process_data()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_folder = os.path.join(project_root, 'data', 'trade_data',
                               f'{TIMEFRAME}_{str(trade_start_date[2:10])}_{str(trade_end_date[2:10])}')
    os.makedirs(data_folder, exist_ok=True)

    _save_to_disk(data_from_processor, f"{data_folder}/data_from_processor")
    _save_to_disk(price_array, f"{data_folder}/price_array")
    _save_to_disk(tech_array, f"{data_folder}/tech_array")
    _save_to_disk(time_array, f"{data_folder}/time_array")
    _save_to_disk(config, f"{data_folder}/config")

    metadata = {
        "tickers": TICKER_LIST,
        "timeframe": TIMEFRAME,
        "start_date": trade_start_date,
        "end_date": trade_end_date,
        "candles": len(price_array),
        "features": actual_features,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(os.path.join(data_folder, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to {data_folder}/metadata.json")


def print_config_variables():
    print('\n')
    print('TIMEFRAME                  ', TIMEFRAME)
    print('TRADE_START_DATE           ', trade_start_date)
    print('TRADE_END_DATA             ', trade_end_date)
    print('TICKER LIST                ', TICKER_LIST, '\n')


def process_data():
    data_processor = DatasetProcessor()
    result = data_processor.run(TICKER_LIST, trade_start_date, trade_end_date, TIMEFRAME, TECHNICAL_INDICATORS_LIST,
                                if_vix=False, feature_tickers=FEATURE_TICKERS)
    actual_features = list(data_processor.tech_indicator_list) if data_processor.tech_indicator_list else TECHNICAL_INDICATORS_LIST
    return (*result, actual_features)


def _save_to_disk(data, file_path):
    with open(file_path, 'wb') as handle:
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    main()
