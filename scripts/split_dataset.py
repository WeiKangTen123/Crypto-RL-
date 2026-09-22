import pandas as pd
import os
from pathlib import Path

def split_dataset_by_interval(base_dir='dataset'):
    """
    Splits the base OHLCV parquet files in the dataset directory 
    into subdirectories based on the 'interval' column.
    
    Structure: dataset/{coin}/spot_ohlcv.parquet -> dataset/{coin}/{interval}/spot_ohlcv.parquet
    """
    base_path = Path(base_dir)
    
    # Find all coin directories (e.g., BTC, ETH)
    coin_dirs = [d for d in base_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
    
    for coin_dir in coin_dirs:
        coin = coin_dir.name
        print(f"Processing {coin}...")
        
        input_file = coin_dir / 'spot_ohlcv.parquet'
        if not input_file.exists():
            print(f"  Warning: {input_file} not found. Skipping.")
            continue
            
        try:
            # Read the base data
            df = pd.read_parquet(input_file)
            
            if 'interval' not in df.columns:
                print(f"  Warning: 'interval' column not found in {input_file}. Cannot split.")
                continue

            # Group by interval and save
            for interval, group in df.groupby('interval'):
                print(f"  Saving interval: {interval}...")
                
                # Prepare output directory
                output_dir = coin_dir / str(interval)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                output_file = output_dir / 'spot_ohlcv.parquet'
                
                # Save the group as a separate parquet file
                group.to_parquet(output_file)
                print(f"  Saved to {output_file}")
                
        except Exception as e:
            print(f"  Error processing {coin}: {e}")

if __name__ == "__main__":
    # Check if pyarrow is installed
    try:
        import pyarrow
    except ImportError:
        print("Error: 'pyarrow' is required to read/write parquet files.")
        print("Please install it using: pip install pyarrow")
        exit(1)
        
    # Get the project root directory (one level up from this script)
    project_root = Path(__file__).parent.parent
    dataset_dir = project_root / 'dataset'
    
    split_dataset_by_interval(base_dir=dataset_dir)
