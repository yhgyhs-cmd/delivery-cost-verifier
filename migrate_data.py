import os
import shutil

# 기존 데이터 경로 (현재 프로젝트 내 data 폴더)
SOURCE_DIR = os.path.join(os.getcwd(), 'data')

# 새 데이터 경로 (사용자 요청 경로)
DEST_DIR = r'C:\Users\yunh1\OneDrive - Thermo Fisher Scientific\비용 검증 프로그램\택배'

def migrate_data():
    print(f"Source: {SOURCE_DIR}")
    print(f"Destination: {DEST_DIR}")

    if not os.path.exists(SOURCE_DIR):
        print(f"Error: Source directory '{SOURCE_DIR}' does not exist.")
        return

    # 새 경로 생성
    if not os.path.exists(DEST_DIR):
        try:
            os.makedirs(DEST_DIR)
            print(f"Created destination directory: {DEST_DIR}")
        except Exception as e:
            print(f"Error creating destination directory: {e}")
            return

    # 파일 및 폴더 이동 (복사 후 원본 유지 - 안전을 위해 copytree 사용 권장하나, 여기서는 덮어쓰기 고려하여 copy2 사용)
    # shutil.copytree는 대상 폴더가 없어야만 동작하므로, 개별 복사 방식 사용
    
    for item in os.listdir(SOURCE_DIR):
        s = os.path.join(SOURCE_DIR, item)
        d = os.path.join(DEST_DIR, item)
        
        try:
            if os.path.isdir(s):
                # 폴더인 경우 (예: TFSS, TFSK 등)
                if os.path.exists(d):
                    # 이미 존재하면 내부 내용물 병합 (여기서는 간단히 덮어쓰기/스킵 정책 결정 필요. 
                    # shutil.copytree(dirs_exist_ok=True)는 파이썬 3.8+ 지원)
                    shutil.copytree(s, d, dirs_exist_ok=True)
                    print(f"Merged directory: {item}")
                else:
                    shutil.copytree(s, d)
                    print(f"Copied directory: {item}")
            else:
                # 파일인 경우 (예: 운송요금_운임표.xlsx)
                shutil.copy2(s, d)
                print(f"Copied file: {item}")
        except Exception as e:
            print(f"Error copying {item}: {e}")

    print("\nMigration completed successfully!")
    print(f"Data is now available at: {DEST_DIR}")

if __name__ == "__main__":
    migrate_data()
