import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
import shutil
# 전역 경로 상수는 가져오지 않음.
# 경로는 verification_page() 내부에서 서비스 선택에 따라 동적으로 설정됩니다.
from verify_cost import load_rate_table, calculate_expected_cost

st.set_page_config(page_title="배송비 검증 시스템", layout="wide")
st.title("🚀 배송비 자동 검증 시스템")

# 공통 결과 표시 함수
def display_verification_results(final_df):
    col_actual_cost = '발송금액'
    
    # 요약 메트릭
    total_count = len(final_df)
    mismatch_df = final_df[final_df['결과'] == "❌ 불일치"]
    mismatch_count = len(mismatch_df)
    match_count = total_count - mismatch_count
    match_rate = (match_count / total_count) * 100 if total_count > 0 else 0

    # 1. 🚨 불일치 건 즉시 표시 (최상단)
    if mismatch_count > 0:
        st.error(f"🚨 **{mismatch_count}건**의 불일치가 발생했습니다! 아래 내역을 확인하세요.")
        with st.expander("🚨 불일치 내역 (자동 펼침)", expanded=True):
            # 불일치 데이터만 표시 (주요 컬럼 위주로)
            cols_to_show = ['운송장번호', '수취주소', '무게', '규격', '발송금액', '예상운임', '차액', '비고', '결과']
            # 존재하는 컬럼만 선택
            existing_cols = [c for c in cols_to_show if c in mismatch_df.columns]
            if not existing_cols: # 중요 컬럼이 없으면 전체 표시
                existing_cols = mismatch_df.columns.tolist()
            
            st.dataframe(
                mismatch_df[existing_cols].style.applymap(
                    lambda v: 'color: red; font-weight: bold;', subset=[c for c in ['차액', '결과'] if c in existing_cols]
                ).format("{:,}원", subset=[c for c in ['발송금액', '예상운임', '차액'] if c in existing_cols])
            )
    else:
        st.success("🎉 모든 배송비가 운임표와 정확히 일치합니다!")
        st.balloons()

    # 2. 메트릭 카드
    col1, col2, col3 = st.columns(3)
    col1.metric("총 건수", f"{total_count}건")
    col2.metric("일치 건수", f"{match_count}건", delta=f"{match_rate:.1f}%")
    col3.metric("불일치 건수", f"{mismatch_count}건", delta_color="inverse")

    st.divider()

    # 3. 전체 데이터 상세 목록 (복구됨)
    st.subheader("📋 검증 결과 상세 목록")
    
    # 필터 옵션
    show_mismatch_only = st.checkbox("❌ 불일치 건만 보기", value=False)
    
    if show_mismatch_only:
        display_df = mismatch_df
    else:
        display_df = final_df
        
    # 데이터프레임 표시 (스타일링 적용)
    # 주요 컬럼 위주로 표시하되, 사용자가 필요로 하는 '지역구분' 포함
    cols_to_display = [col for col in display_df.columns if col not in ['수취주소_원본', '발송주소_원본']] # 너무 긴 컬럼 제외 가능
    
    st.dataframe(
        display_df.style.applymap(
            lambda v: 'color: red; font-weight: bold;' if v == "❌ 불일치" else ('color: green; font-weight: bold;' if v == "✅ 일치" else ''),
            subset=['결과']
        ).format("{:,}원", subset=[col for col in [col_actual_cost, '예상운임', '차액'] if col in display_df.columns])
    )

    # 결과 다운로드
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False)
    st.download_button(
        label="📥 검증 결과 엑셀 다운로드",
        data=output.getvalue(),
        file_name="배송비_검증결과.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# 검증 로직 분리 (재사용을 위해)
def perform_verification(df, rate_map, selected_entity):
    results = []
    
    # 컬럼 매핑 (유연하게 처리)
    col_weight = '무게'
    col_address = '수취주소'
    col_actual_cost = '발송금액'
    col_sender_address = None
    
    # 컬럼 찾기
    for col in df.columns:
        if '발송' in col and '주소' in col:
            col_sender_address = col
        elif '수취' in col and '주소' in col:
            col_address = col
        elif '무게' in col:
            col_weight = col
        elif '발송' in col and '금액' in col:
            col_actual_cost = col

    # 필수 컬럼 검사
    missing_cols = []
    if col_weight not in df.columns: missing_cols.append('무게')
    if col_address not in df.columns: missing_cols.append('수취주소')
    if col_actual_cost not in df.columns: missing_cols.append('발송금액')
    
    if missing_cols:
        return None, f"필수 컬럼 누락: {', '.join(missing_cols)} (발견된 컬럼: {list(df.columns)})"

    # 로직 수행
    for index, row in df.iterrows():
        weight = row.get(col_weight, 0)
        address = row.get(col_address, '')
        actual = row.get(col_actual_cost, 0)
        
        sender_addr = None
        if col_sender_address:
            val = row.get(col_sender_address)
            if pd.notna(val) and str(val).strip() != '':
                sender_addr = str(val).strip()

        expected, region, remark = calculate_expected_cost(weight, address, rate_map, sender_address=sender_addr)
        diff = actual - expected
        status = "✅ 일치" if diff == 0 else "❌ 불일치"
        
        results.append({
            '법인': selected_entity,
            '운송장번호': row.get('운송장번호', ''),
            '수취주소': address,
            '무게': weight,
            '규격': row.get('규격', ''),
            '발송금액': actual,
            '예상운임': expected,
            '지역구분': region,
            '차액': diff,
            '결과': status,
            '비고': remark
        })

    final_df = df.copy()
    final_df['법인'] = selected_entity
    final_df['예상운임'] = [r['예상운임'] for r in results]
    final_df['지역구분'] = [r['지역구분'] for r in results]
    final_df['차액'] = [r['차액'] for r in results]
    final_df['결과'] = [r['결과'] for r in results]
    final_df['비고'] = [r['비고'] for r in results]
    
    return final_df, None

# === 설정 ===
# 기본 데이터 경로 (최상위 폴더)
BASE_DIR = r'C:\Users\yunh1\OneDrive - Thermo Fisher Scientific\비용 검증 프로그램'

# 1. 운임표 로드 (캐싱 적용 - 경로를 인자로 받음)
@st.cache_data
def get_rate_map(file_path, mtime):
    if not os.path.exists(file_path):
        return None
    return load_rate_table(file_path)

def verification_page():
    # === 운송 서비스 선택 ===
    service_options = ["택배", "직배송", "퀵서비스"]
    selected_service = st.sidebar.selectbox("운송 서비스 선택", service_options, index=0)
    
    # 선택된 서비스에 따른 데이터 경로 설정
    DATA_DIR = os.path.join(BASE_DIR, selected_service)
    RATE_FILE = os.path.join(DATA_DIR, '운송요금_운임표.xlsx')
    
    # 2. 운임표 로드
    rate_file_mtime = os.path.getmtime(RATE_FILE) if os.path.exists(RATE_FILE) else 0
    rate_map = get_rate_map(RATE_FILE, rate_file_mtime)

    st.markdown(f"### 🚛 {selected_service} 비용 검증 시스템")

    if rate_map is None:
        if selected_service == "택배":
            st.error(f"❌ '{selected_service}' 운임표 파일({RATE_FILE})을 찾을 수 없습니다.")
        else:
            st.warning(f"⚠️ '{selected_service}' 운임표가 없습니다. 운임표 파일이 준비되면 검증이 가능합니다.")
            st.caption(f"운임표 위치: {RATE_FILE}")
    else:
        st.success(f"✅ {selected_service} 운임표 로드 완료 ({len(rate_map)}개 구간)")
    
    st.sidebar.divider()
    st.sidebar.header("📁 데이터 업로드 (신규)")

    # 법인 선택 추가
    entity_options = ["TFSS", "TFSK", "FSK"]
    selected_entity = st.sidebar.radio("법인 선택", entity_options, horizontal=True, key="verify_entity_radio")

    # 입력 방식: 서버 폴더에서 파일 선택 (단일 방식)
    # DATA_DIR 하위에 법인 폴더가 있다고 가정
    folder_path = os.path.join(DATA_DIR, selected_entity)
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path) # 폴더가 없으면 생성
        except:
            pass
    
    # [UI 개선] 현재 작업 경로 명시
    st.sidebar.info(f"📂 **파일 위치 확인**\n\n`{folder_path}`\n\n위 폴더에 있는 파일을 수정하셔야 반영됩니다.")

    selected_files = []
    
    if os.path.exists(folder_path):
        files = [f for f in os.listdir(folder_path) if f.endswith('.xlsx') and not f.startswith('~$')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(folder_path, x)), reverse=True)
        
        # 검증 모드 선택 (단일 vs 다중)
        is_multi_mode = st.sidebar.checkbox("일괄 처리 모드 (여러 파일 한번에)", value=False)
        
        if is_multi_mode:
            # 다중 선택 모드
            selected_files = st.sidebar.multiselect(
                "검증할 파일 선택 (다중)",
                files,
                placeholder="파일을 선택하세요"
            )
            # 전체 선택 옵션
            if st.sidebar.checkbox("전체 선택", value=False):
                selected_files = files
        else:
            # 단일 선택 모드
            selected_file = st.sidebar.selectbox(
                "검증할 파일 선택 (단일)",
                options=["선택하세요"] + files,
                index=0
            )
            if selected_file != "선택하세요":
                selected_files = [selected_file]
    
    if not files:
        st.sidebar.warning(f"'{selected_entity}' 폴더에 엑셀 파일이 없습니다.")
        st.sidebar.caption(f"파일을 아래 경로에 넣어주세요:\n{folder_path}")
    elif selected_files:
        st.sidebar.info(f"{len(selected_files)}개 파일 선택됨")

    process_new = False
    
    # 여기서부터 검증 로직 시작
    if selected_files:
        if rate_map is None:
            st.sidebar.button("🔍 검증 시작", disabled=True, key="verify_btn_disabled", help="운임표 파일(data/운송요금_운임표.xlsx)이 필요합니다.")
            st.sidebar.error("❌ 운임표 파일이 없어 검증할 수 없습니다.")
        elif st.sidebar.button("🔍 선택한 파일 검증 시작"):
            # ✅ [핵심 수정] 검증 시작 즉시 이전 결과 초기화
            # 그렇지 않으면, 새 파일 검증이 끝나고 rerun되기 전에 이전 결과가 화면에 표시됨
            st.session_state['verification_result'] = None
            st.session_state['current_file_name'] = None
            
            process_new = True
            # 프로그레스 바
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            success_count = 0
            fail_count = 0
            moved_count = 0
            
            # 결과 저장용 리스트 (마지막 파일만 보여주거나, 요약만 보여주거나 선택 필요)
            # 여기서는 마지막 성공한 파일의 결과를 보여주는 것으로 유지하거나, 전체 요약만 보여주는 방식.
            # UX상 여러개 처리시에는 요약이 낫고, 상세는 이력에서 보는게 나을 수 있음.
            # 하지만 사용자는 바로 보고싶어 할 수 있으므로, 마지막 처리된 파일 정보를 세션에 저장.
            
            for i, selected_filename in enumerate(selected_files):
                status_text.text(f"처리 중 ({i+1}/{len(selected_files)}): {selected_filename}")
                selected_file_path = os.path.join(folder_path, selected_filename)
                
                # ✅ [수정] RESULTS_DIR 기반 중복 감지 로직 삭제
                # 이전 로직은 '(2025 10)' in '(2025 10_1)' 처럼 문자열 포함 관계로
                # 잘못된 중복을 감지하는 버그가 있었음.

                try:
                    file_name_for_save = os.path.basename(selected_file_path)
                    
                    try:
                        # [캐싱/잠금 방지] 임시 파일로 복사하여 읽기
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                            shutil.copy2(selected_file_path, tmp.name)
                            temp_path = tmp.name
                        
                        try:
                            with pd.ExcelFile(temp_path) as xls:
                                sheet_to_use = 0
                                if '세부내역' in xls.sheet_names:
                                    sheet_to_use = '세부내역'
                                
                                df = pd.read_excel(xls, sheet_name=sheet_to_use)
                            df.columns = df.columns.str.strip()
                        finally:
                            # 임시 파일 삭제
                            if os.path.exists(temp_path):
                                try:
                                    os.remove(temp_path)
                                except:
                                    pass
                    except Exception as e:
                        st.error(f"❌ 파일 읽기 실패: {e}")
                        fail_count += 1
                        continue 
                    
                    # [디버깅] 파일 정보 및 데이터 확인
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(selected_file_path)).strftime('%Y-%m-%d %H:%M:%S')
                    st.info(f"📂 **파일 읽기 성공**: `{selected_filename}`\n\n🕒 **마지막 수정 시간**: {file_mtime}")
                    
                    with st.expander("🔎 [디버깅] 읽어온 원본 데이터 확인 (상위 5행)"):
                        st.write(f"총 {len(df)}행, '발송금액' 합계: {df['발송금액'].sum() if '발송금액' in df.columns else 'N/A'}")
                        st.dataframe(df.head())

                    # === 검증 로직 수행 (함수 호출) ===
                    final_df, error_msg = perform_verification(df, rate_map, selected_entity)
                    
                    if error_msg:
                        st.error(f"❌ [{selected_filename}] {error_msg}")
                        fail_count += 1
                        continue

                    success_count += 1
                    
                    # 마지막 성공 결과를 세션에 저장 (화면 표시용)
                    st.session_state['verification_result'] = final_df
                    st.session_state['current_file_name'] = f"[{selected_entity}] {file_name_for_save} (최근 처리됨)"
                    st.session_state['current_file_path'] = None # 저장된 경로가 없으므로 None
                    
                    # === 파일 이동 로직 (Verified 폴더) ===
                    verified_dir = os.path.join(folder_path, "verified")
                    if not os.path.exists(verified_dir):
                        os.makedirs(verified_dir)
                    
                    target_path = os.path.join(verified_dir, selected_filename)
                    
                    # 중복 파일명 처리
                    if os.path.exists(target_path):
                        name, ext = os.path.splitext(selected_filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        target_path = os.path.join(verified_dir, f"{name}_{timestamp}{ext}")
                    
                    try:
                        shutil.move(selected_file_path, target_path)
                        moved_count += 1
                    except Exception as e:
                        st.error(f"❌ 파일 이동 실패: {e}")
                        
                except Exception as e:
                    st.error(f"❌ [{selected_filename}] 처리 중 오류: {e}")
                    fail_count += 1
                
                # 진행률 업데이트
                progress_bar.progress((i + 1) / len(selected_files))

            status_text.text("작업 완료!")
            st.success(f"✅ 총 {len(selected_files)}개 중 {success_count}개 검증 완료! (이동: {moved_count}건, 실패: {fail_count}건)")
            
            if moved_count > 0:
                st.info("🔄 목록 갱신을 위해 2초 후 새로고침됩니다...")
                import time
                time.sleep(2)
                st.rerun()

    # 3. 사이드바 설정 (Verified 이력 보기)
    st.sidebar.divider()
    st.sidebar.header("📜 완료된 이력 (Verified)")
    
    verified_dir = os.path.join(folder_path, "verified")
    if os.path.exists(verified_dir):
        verified_files = [f for f in os.listdir(verified_dir) if f.endswith('.xlsx')]
        verified_files.sort(key=lambda x: os.path.getmtime(os.path.join(verified_dir, x)), reverse=True)
        
        if verified_files:
            selected_history = st.sidebar.selectbox("완료된 파일 선택", verified_files)
            if st.sidebar.button("📂 결과 다시 보기"):
                if not process_new: # 새로운 파일 처리 중이 아닐 때만 이력 보기 실행
                    try:
                        history_path = os.path.join(verified_dir, selected_history)
                        
                        # [캐싱/잠금 방지] 임시 파일로 복사하여 읽기
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                            shutil.copy2(history_path, tmp.name)
                            temp_path = tmp.name
                        
                        try:
                            with pd.ExcelFile(temp_path) as xls:
                                sheet_to_use = 0
                                if '세부내역' in xls.sheet_names:
                                    sheet_to_use = '세부내역'
                                history_source_df = pd.read_excel(xls, sheet_name=sheet_to_use)
                            history_source_df.columns = history_source_df.columns.str.strip()
                        finally:
                            if os.path.exists(temp_path):
                                try:
                                    os.remove(temp_path)
                                except:
                                    pass
                        
                        # 재검증 수행
                        verified_df, error_msg = perform_verification(history_source_df, rate_map, selected_entity)
                        
                        if verified_df is not None:
                            st.info(f"📂 불러온 파일: {selected_history} (재검증 결과)")
                            st.session_state['verification_result'] = verified_df
                            st.session_state['current_file_name'] = f"📂 {selected_history} (완료 건)"
                            st.rerun() 
                        else:
                            st.error(f"검증 실패: {error_msg}")
                            
                    except Exception as e:
                        st.sidebar.error(f"파일 로드 실패: {e}")
        else:
            st.sidebar.info("완료된 파일이 없습니다.")
    else:
        st.sidebar.info("완료된 파일 폴더가 없습니다.")

def open_folder(path):
    import platform
    import subprocess
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])

# 메인 로직 실행
verification_page()

# 세션 스테이트에 저장된 결과가 있으면 표시 (리런 시에도 유지됨)
if 'verification_result' in st.session_state and st.session_state['verification_result'] is not None:
    st.divider()
    if 'current_file_name' in st.session_state:
        st.subheader(f"📊 현재 보기: {st.session_state['current_file_name']}")
    display_verification_results(st.session_state['verification_result'])