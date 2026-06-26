import pandas as pd
import os

assets = ["BTC", "ETH", "BNB", "SOL", "XRP"]
tfs = ["1h", "4h"]

for asset in assets:
    for tf in tfs:
        path = f"dataset/{asset}/{tf}/spot_ohlcv.parquet"
        if os.path.exists(path):
            try:
                df = pd.read_parquet(path)
                has_col = 'taker_buy_base_vol' in df.columns
                if has_col:
                    nulls = df['taker_buy_base_vol'].isnull().sum()
                    zeros = (df['taker_buy_base_vol'] == 0).sum()
                    latest = df.index.max()
                    print(f"{path}: taker_buy_base_vol exists: True, Nulls: {nulls}, Zeros: {zeros}, Latest: {latest}")
                else:
                    print(f"{path}: taker_buy_base_vol exists: False")
            except Exception as e:
                print(f"{path}: Error reading: {e}")
        else:
            print(f"{path}: File does not exist")
