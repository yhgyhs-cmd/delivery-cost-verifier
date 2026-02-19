import pandas as pd
import numpy as np
import os
import math

# === 설정 ===
# 사용자 요청에 따라 데이터 경로 변경 (2025-02-19)
DATA_DIR = r'C:\Users\yunh1\OneDrive - Thermo Fisher Scientific\비용 검증 프로그램\택배'
RESULTS_DIR = 'results' # (사용 안함)
RATE_FILE = os.path.join(DATA_DIR, '운송요금_운임표.xlsx')

def load_rate_table(file_path=RATE_FILE):
    """Parses the rate table to extract bracket limits and prices."""
    # Load with header at row 1 (0-indexed)
    df = pd.read_excel(file_path, header=1)
    
    # Extract relevant rows (those with weight info)
    # Looking for rows where '무게,세변의 합' is not null and contains 'kg'
    rate_map = []
    
    for index, row in df.iterrows():
        weight_str = str(row['무게,세변의 합'])
        if 'kg' in weight_str:
            # Extract weight limit (e.g., "5kg / 80cm" -> 5)
            try:
                limit = int(weight_str.split('kg')[0].strip())
                national_price = int(row['운임'])
                jeju_price = int(row['Unnamed: 3'])
                rate_map.append({
                    'limit': limit,
                    'national': national_price,
                    'jeju': jeju_price
                })
            except (ValueError, IndexError):
                continue
                
    return sorted(rate_map, key=lambda x: x['limit'])

def calculate_expected_cost(weight, address, rate_map, sender_address=None):
    """Calculates expected cost based on weight and address.
    
    If address (receiver) is a logistics center (Incheon Jung-gu),
    use sender_address to determine if it's Jeju/Remote.
    """
    # 1. Determine Region
    target_address = str(address)
    region_source = "Receiver"
    
    # Check if receiver is logistics center (Incheon Jung-gu)
    # Remove spaces for robust matching
    target_addr_clean = target_address.replace(' ', '')
    if '인천' in target_addr_clean and '중구' in target_addr_clean and sender_address:
        print(f"DEBUG: Logistics Center Detected. Receiver: {target_address}, Sender: {sender_address}")
        target_address = str(sender_address)
        region_source = "Sender (Return)"
    else:
        if '인천' in target_address:
            print(f"DEBUG: Incheon detected but criteria not met. Addr: {target_address}, Sender: {bool(sender_address)}")

    is_jeju = '제주' in target_address
    region_type = '제주' if is_jeju else '전국'
    if region_source == "Sender (Return)":
        region_type += " (반품)"
        print(f"DEBUG: Region set to Return. Type: {region_type}")
    
    # 2. Base Cost Calculation
    base_cost = 0
    
    # Find the applicable bracket
    applicable_bracket = None
    for bracket in rate_map:
        if weight <= bracket['limit']:
            applicable_bracket = bracket
            break
            
    # If explicitly found in brackets (<= 30kg usually)
    if applicable_bracket:
        base_cost = applicable_bracket['jeju'] if is_jeju else applicable_bracket['national']
        return base_cost, region_type, "Normal"
        
    # 3. Surcharge Calculation (> 30kg)
    # Use the largest bracket as base (should be 30kg)
    max_bracket = rate_map[-1]
    base_cost = max_bracket['jeju'] if is_jeju else max_bracket['national']
    
    extra_weight = weight - max_bracket['limit']
    if extra_weight > 0:
        # Per 5kg chunk
        unit_5kg = 2000 if not is_jeju else 3000
        extra_units = math.ceil(extra_weight / 5)
        surcharge = extra_units * unit_5kg
        total_cost = base_cost + surcharge
        return total_cost, region_type, f"Surcharge (+{surcharge})"
    
    return base_cost, region_type, "MaxBracket"

def process_file(file_path, rate_map):
    """Processes a single data file and saves the verification result."""
    filename = os.path.basename(file_path)
    print(f"Processing {filename}...")
    
    try:
        # Check sheet names
        xls = pd.ExcelFile(file_path)
        sheet_to_use = 0
        
        if '세부내역' in xls.sheet_names:
            sheet_to_use = '세부내역'
            print(f"  - Found '세부내역' sheet. Using it.")
        else:
            print(f"  - '세부내역' sheet not found. Using first sheet.")
            
        df = pd.read_excel(file_path, sheet_name=sheet_to_use)
        
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return

    # Verification Columns
    expected_costs = []
    region_types = []
    remarks = []
    diffs = []
    statuses = []
    
    for index, row in df.iterrows():
        weight = row.get('무게', 0)
        address = row.get('수취주소', '')
        actual_cost = row.get('발송금액', 0)
        
        # Calculate
        expected, region, remark = calculate_expected_cost(weight, address, rate_map)
        
        # Compare
        diff = actual_cost - expected
        status = '✅ 일치' if diff == 0 else '❌ 불일치'
        
        expected_costs.append(expected)
        region_types.append(region)
        remarks.append(remark)
        diffs.append(diff)
        statuses.append(status)
        
    # Add columns to DataFrame
    df['예상운임'] = expected_costs
    df['지역구분'] = region_types
    df['비고'] = remarks
    df['차액'] = diffs
    df['결과'] = statuses
    
    # Save Result
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
        
    result_file = os.path.join(RESULTS_DIR, f"verified_{filename}")
    df.to_excel(result_file, index=False)
    print(f"Saved results to {result_file}")

def main():
    print("Loading rate table...")
    if not os.path.exists(RATE_FILE):
        print(f"Error: Rate file not found at {RATE_FILE}")
        return

    # Load Rate Table
    try:
        rate_map = load_rate_table(RATE_FILE)
        print(f"Loaded {len(rate_map)} rate brackets.")
    except Exception as e:
        print(f"Error loading rate table: {e}")
        return
    
    # Process all files in data directory
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory not found at {DATA_DIR}")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.xlsx')]
    count = 0
    
    for filename in files:
        file_path = os.path.join(DATA_DIR, filename)
        
        # Skip rate table
        if os.path.abspath(file_path) == os.path.abspath(RATE_FILE):
            continue
            
        process_file(file_path, rate_map)
        count += 1
        
    print(f"Done! Processed {count} files.")

if __name__ == "__main__":
    main()
