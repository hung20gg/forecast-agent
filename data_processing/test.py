import pandas as pd
df = pd.read_parquet(r"C:\Users\Admin\data\finance\train.parquet")
print(df.head())