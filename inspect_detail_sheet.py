import pandas as pd

data_file = 'data/(incheon)ilayngilyangLogis(2025.10).xlsx'
sheet_name = '세부내역'

print(f"Loading {data_file} sheet '{sheet_name}'...")
try:
    df = pd.read_excel(data_file, sheet_name=sheet_name, nrows=5)
    print(df.columns.tolist())
    print(df.head().to_string())
except Exception as e:
    print(f"Error: {e}")
