import pandas as pd

data_file = 'data/(incheon)ilayngilyangLogis(2025.10).xlsx'

print(f"Loading {data_file}...")
# Read first 10 rows without header to see the layout
df = pd.read_excel(data_file, header=None, nrows=10)

print(df.to_string())
