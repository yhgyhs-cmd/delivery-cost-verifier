import pandas as pd

data_file = 'data/(incheon)ilayngilyangLogis(2025.9).xlsx'

print(f"Loading {data_file}...")
# Read first 5 rows
df = pd.read_excel(data_file, nrows=5)
print(df.columns.tolist())
print(df.head().to_string())
