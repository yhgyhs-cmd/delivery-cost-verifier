import pandas as pd
import os

# result_file = 'results/verified_(incheon)ilayngilyangLogis(2025.9).xlsx' 
# Let's check the new file specifically as the user mentioned "new raw data"
result_file = 'results/verified_(incheon)ilayngilyangLogis(2025.11).xlsx'

if not os.path.exists(result_file):
    print(f"File not found: {result_file}")
    exit()

print(f"Loading {result_file}...")
df = pd.read_excel(result_file)

print(f"Total rows: {len(df)}")
mismatches = df[df['검증결과'] == 'Mismatch']
print(f"Total mismatches: {len(mismatches)}")

if len(mismatches) > 0:
    print("\n--- Top 5 Mismatches ---")
    cols_to_show = ['수취주소', '무게', '발송금액', '예상요금', '차액', '비고_검증']
    # Check if columns exist before printing
    valid_cols = [c for c in cols_to_show if c in df.columns]
    print(mismatches[valid_cols].head().to_string())

    print("\n--- Mismatch Remarks Distribution ---")
    print(mismatches['비고_검증'].value_counts())

    print("\n--- Average Difference ---")
    print(f"Mean Diff: {mismatches['차액'].mean()}")
    print(f"Min Diff: {mismatches['차액'].min()}")
    print(f"Max Diff: {mismatches['차액'].max()}")
    
    # Check for potential shifting issues or non-numeric weights
    print("\n--- Data Type Check (Weight) ---")
    print(df['무게'].dtype)
    non_numeric_weights = df[pd.to_numeric(df['무게'], errors='coerce').isna()]
    if not non_numeric_weights.empty:
        print(f"Found {len(non_numeric_weights)} rows with non-numeric weights:")
        print(non_numeric_weights[['무게']].head())

else:
    print("No mismatches found!")
