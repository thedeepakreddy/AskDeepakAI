import pandas as pd
import glob

for file in glob.glob('datasets/*/*.parquet'):
    try:
        df = pd.read_parquet(file)
        print(f"\n--- {file} ---")
        print("Columns:", list(df.columns))
        print("Row 0:")
        row = df.head(1).to_dict('records')[0]
        for k, v in row.items():
            print(f"  {k}: {str(v)[:200]}...")
    except Exception as e:
        print(f"Error reading {file}: {e}")
