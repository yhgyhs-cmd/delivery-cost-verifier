import pandas as pd

data_file = 'data/(incheon)ilayngilyangLogis(2025.10).xlsx'

print(f"Loading {data_file}...")
xls = pd.ExcelFile(data_file)
print(f"Sheet names: {xls.sheet_names}")
