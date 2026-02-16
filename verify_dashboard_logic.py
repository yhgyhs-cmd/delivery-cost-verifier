import pandas as pd
import os
from datetime import datetime

# Mock data creation
data = [
    {'법인': 'TFSS', '결과': '✅ 일치', '차액': 0, '검증일시': datetime(2023, 10, 1).date()},
    {'법인': 'TFSS', '결과': '❌ 불일치', '차액': 1000, '검증일시': datetime(2023, 10, 2).date()},
    {'법인': 'TFSK', '결과': '✅ 일치', '차액': 0, '검증일시': datetime(2023, 10, 3).date()},
    {'법인': 'FSK', '결과': '❌ 불일치', '차액': 500, '검증일시': datetime(2023, 10, 4).date()},
]
df = pd.DataFrame(data)

print("Original DF:")
print(df)

# Test Filtering Logic
entities = ["TFSS", "TFSK", "FSK", "전체"]

for entity_filter in entities:
    print(f"\nTesting Filter: {entity_filter}")
    
    if entity_filter != "전체":
        filtered_df = df[df['법인'] == entity_filter]
    else:
        filtered_df = df
        
    print(f"Filtered Rows: {len(filtered_df)}")
    
    # KPI Logic
    total_count = len(filtered_df)
    mismatch_df = filtered_df[filtered_df['결과'] == '❌ 불일치']
    mismatch_count = len(mismatch_df)
    total_diff = mismatch_df['차액'].abs().sum() if '차액' in mismatch_df.columns else 0
    
    print(f"Total: {total_count}, Mismatch: {mismatch_count}, Diff: {total_diff}")
    
    if entity_filter == "TFSS":
        assert total_count == 2
        assert mismatch_count == 1
        assert total_diff == 1000
    elif entity_filter == "TFSK":
        assert total_count == 1
        assert mismatch_count == 0
        assert total_diff == 0
    elif entity_filter == "FSK":
        assert total_count == 1
        assert mismatch_count == 1
        assert total_diff == 500
    elif entity_filter == "전체":
        assert total_count == 4
        assert mismatch_count == 2
        assert total_diff == 1500

print("\n✅ Verification Successful!")
