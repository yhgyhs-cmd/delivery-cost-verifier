import os
import pandas as pd

DATA_DIR = 'data'

def inspect_header():
    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith('.xlsx') and not file.startswith('~$') and '운임표' not in file:
                file_path = os.path.join(root, file)
                print(f"Inspecting: {file_path}")
                try:
                    xls = pd.ExcelFile(file_path)
                    print(f"Sheet Names: {xls.sheet_names}")
                    
                    target_sheet = 0
                    if '세부내역' in xls.sheet_names:
                        target_sheet = '세부내역'
                        print(f"Targeting sheet: {target_sheet}")
                    
                    df = pd.read_excel(file_path, sheet_name=target_sheet, header=0, nrows=5)
                    print(f"--- Top 5 rows of {file} ({target_sheet}) ---")
                    print("Columns:", list(df.columns))
                    return
                except Exception as e:
                    print(f"Error reading {file}: {e}")

if __name__ == "__main__":
    inspect_header()
