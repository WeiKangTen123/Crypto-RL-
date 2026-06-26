import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

import pickle
import json
from datetime import datetime

from config_main import (
    TICKER_LIST,
    FEATURE_TICKERS,
    TIMEFRAME,
    no_candles_for_train,
    no_candles_for_val,
    TECHNICAL_INDICATORS_LIST,
    TRAIN_START_DATE,
    VAL_END_DATE
)
from processor_Dataset import DatasetProcessor


def print_config_variables():
    print('\n')
    print('TIMEFRAME:                ', TIMEFRAME)
    print('no_candles_for_train:     ', no_candles_for_train)
    print('no_candles_for_val:       ', no_candles_for_val)
    print('TRAIN_START_DATE:         ', TRAIN_START_DATE)
    print('VAL_END_DATE:             ', VAL_END_DATE, '\n')
    print('TICKER LIST:              ', TICKER_LIST, '\n')


def process_data():
    DataProcessor = DatasetProcessor()
    data_from_processor, price_array, tech_array, time_array, config = DataProcessor.run(
        TICKER_LIST,
        TRAIN_START_DATE,
        VAL_END_DATE,
        TIMEFRAME,
        TECHNICAL_INDICATORS_LIST,
        if_vix=False,
        feature_tickers=FEATURE_TICKERS
    )
    actual_features = list(DataProcessor.tech_indicator_list) if DataProcessor.tech_indicator_list else TECHNICAL_INDICATORS_LIST
    return data_from_processor, price_array, tech_array, time_array, actual_features


def save_metadata(data_folder, price_array, actual_features):
    metadata = {
        "tickers": TICKER_LIST,
        "timeframe": TIMEFRAME,
        "start_date": TRAIN_START_DATE,
        "end_date": VAL_END_DATE,
        "candles": len(price_array),
        "features": actual_features,
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(os.path.join(data_folder, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Metadata saved to {data_folder}/metadata.json")


def _save_to_disk(data, file_path):
    with open(file_path, 'wb') as handle:
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)


def main():
    print_config_variables()
    data_from_processor, price_array, tech_array, time_array, actual_features = process_data()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_folder = os.path.join(project_root, 'data', f'{TIMEFRAME}_{no_candles_for_train + no_candles_for_val}')
    os.makedirs(data_folder, exist_ok=True)

    _save_to_disk(data_from_processor, f"{data_folder}/data_from_processor")
    _save_to_disk(price_array, f"{data_folder}/price_array")
    _save_to_disk(tech_array, f"{data_folder}/tech_array")
    _save_to_disk(time_array, f"{data_folder}/time_array")

    save_metadata(data_folder, price_array, actual_features)


if __name__ == "__main__":
    main()
