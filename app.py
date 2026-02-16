import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
from verify_cost import load_rate_table, calculate_expected_cost, RATE_FILE, RESULTS_DIR, DATA_DIR

st.set_page_config(page_title="배송비 검증 시스템", layout="wide")
st.title("🚀 배송비 자동 검증 시스템")

# 1. 운임표 로드 (캐싱 적용)
@st.cache_data
def get_rate_map():
    if not os.path.exists(RATE_FILE):
        return None
    return load_rate_table(RATE_FILE)

rate_map = get_rate_map()

if rate_map is None:
    st.error(f"❌ 운임표 파일({RATE_FILE})을 찾을 수 없습니다. 파일을 확인해주세요.")
else:
    st.success(f"✅ 운임표 로드 완료 ({len(rate_map)}개 구간)")

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

    # 3. 전체 데이터 상세 (하단)
    st.subheader("📋 검증 결과 상세")
    
    # 필터 옵션 (기존 기능 유지)
    show_mismatch_only = st.checkbox("❌ 불일치 건만 보기", value=False)
    
    if show_mismatch_only:
        display_df = mismatch_df
    else:
        display_df = final_df
        
    # 데이터프레임 표시 (스타일링 적용)
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

# 2. 사이드바 설정 (신규 검증)
# 페이지 모드 선택
mode = st.sidebar.radio("모드 선택", ["🏠 비용 검증", "📊 대시보드"])

import shutil

def load_all_results():
    if not os.path.exists(RESULTS_DIR):
        return pd.DataFrame()
    
    all_files = []
    # os.walk로 하위 폴더까지 검색
    for root, dirs, files in os.walk(RESULTS_DIR):
        for f in files:
            if f.endswith('.xlsx') and not f.startswith('~$'):
                all_files.append(os.path.join(root, f))
    
    if not all_files:
        return pd.DataFrame()
    
    df_list = []
    for f in all_files:
        try:
            temp_df = pd.read_excel(f)
             # 호환성 처리
            rename_map = {'예상요금': '예상운임', '검증결과': '결과', '비고_검증': '비고'}
            temp_df.rename(columns=rename_map, inplace=True)
            if '결과' in temp_df.columns:
                temp_df['결과'] = temp_df['결과'].replace({'Match': '✅ 일치', 'Mismatch': '❌ 불일치'})
            
            # 법인 정보 없으면 파일명에서 추측
            if '법인' not in temp_df.columns:
                # 파일명: verified_{date}_{time}_{entity}_{filename}
                parts = os.path.basename(f).split('_')
                if len(parts) >= 4 and parts[3] in ["TFSS", "TFSK", "FSK"]:
                    temp_df['법인'] = parts[3]
                else:
                    # 상위 폴더명이 법인명인 경우 체크
                    parent_dir = os.path.basename(os.path.dirname(f))
                    if parent_dir in ["TFSS", "TFSK", "FSK"]:
                        temp_df['법인'] = parent_dir
                    else:
                        temp_df['법인'] = '기타'
            
            # 파일 날짜 (파일명의 timestamp 사용)
            filename = os.path.basename(f)
            if filename.startswith("verified_"):
                try:
                    date_str = filename.split('_')[1]
                    temp_df['검증일시'] = datetime.strptime(date_str, "%Y%m%d").date()
                except:
                    temp_df['검증일시'] = datetime.fromtimestamp(os.path.getmtime(f)).date()
            else:
                temp_df['검증일시'] = datetime.fromtimestamp(os.path.getmtime(f)).date()

            df_list.append(temp_df)
        except Exception as e:
            continue
            
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    else:
        return pd.DataFrame()

# ... (중략) ...



def dashboard_page():
    st.header("📊 통합 대시보드")
    
    # 사이드바에 필터 및 초기화 추가
    st.sidebar.header("🔍 대시보드 옵션")
    entity_filter = st.sidebar.selectbox("법인 필터", ["전체", "TFSS", "TFSK", "FSK"], key="dashboard_entity_filter")
    
    st.sidebar.divider()
    if st.sidebar.button("🗑️ 대시보드 초기화", key="dashboard_reset_btn", help="지금까지 저장된 모든 검증 이력을 삭제합니다."):
        if os.path.exists(RESULTS_DIR):
            try:
                shutil.rmtree(RESULTS_DIR)
                os.makedirs(RESULTS_DIR)
                st.sidebar.success("✅ 초기화 완료. 잠시 후 새로고침 됩니다.")
                st.cache_data.clear() # 캐시 초기화
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"초기화 실패: {e}")
        else:
            st.sidebar.info("삭제할 데이터가 없습니다.")

    with st.spinner('데이터를 분석하고 있습니다...'):
        df = load_all_results()
        
    if df.empty:
        st.info("아직 검증된 데이터가 없습니다.")
        return

    # 필터링 적용
    if entity_filter != "전체":
        df = df[df['법인'] == entity_filter]
        st.subheader(f"📍 {entity_filter} 현황")
    else:
        st.subheader("📍 전체 현황")

    # 1. KPI 카드
    total_count = len(df)
    mismatch_df = df[df['결과'] == '❌ 불일치']
    mismatch_count = len(mismatch_df)
    match_rate = ((total_count - mismatch_count) / total_count * 100) if total_count > 0 else 0
    total_diff = mismatch_df['차액'].abs().sum() if '차액' in mismatch_df.columns else 0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("총 검증 건수", f"{total_count:,}건")
    kpi2.metric("불일치 건수", f"{mismatch_count:,}건", delta=f"{match_rate:.1f}% (일치율)")
    kpi3.metric("총 차액 (절대값)", f"{total_diff:,.0f}원")
    
    # 법인별 통계 (전체일 때만 의미 있음, 하지만 필터 후에도 하나만 보여주는 것도 나쁘지 않음)
    st.divider()
    
    # 필터가 '전체'일 때는 법인별 비교 차트 표시
    if entity_filter == "전체":
        st.subheader("🏢 법인별 현황")
        if '법인' in df.columns:
            entity_stats = df.groupby('법인').apply(
                lambda x: pd.Series({
                    '전체': len(x),
                    '불일치': len(x[x['결과'] == '❌ 불일치']),
                    '차액합계': x[x['결과'] == '❌ 불일치']['차액'].sum() if not x[x['결과'] == '❌ 불일치'].empty else 0
                })
            ).reset_index()
            
            c1, c2 = st.columns(2)
            with c1:
                st.caption("법인별 불일치 건수")
                st.bar_chart(entity_stats.set_index('법인')['불일치'], color="#FF4B4B")
            with c2:
                st.caption("법인별 검증 물량")
                st.bar_chart(entity_stats.set_index('법인')['전체'])
                
            st.dataframe(entity_stats.style.format("{:,.0f}", subset=['전체', '불일치', '차액합계']))
    
    # 일자별/월별 추세 분석
    st.divider()
    st.subheader("📈 기간별 분석")

    if '검증일시' in df.columns:
        # 날짜 형식 변환 보장
        df['검증일시'] = pd.to_datetime(df['검증일시'])
        df['월'] = df['검증일시'].dt.strftime('%Y-%m')

        tab1, tab2 = st.tabs(["📆 월별 통합 분석", "📅 일자별 상세 불일치"])

        with tab1:
            # 1. 월별 불일치 추세
            monthly_mismatch = df[df['결과'] == '❌ 불일치'].groupby('월').size()
            
            # 2. 월별 비용 통계
            monthly_stats = df.groupby('월').agg({
                '발송금액': ['sum', 'mean'],
                '예상운임': 'sum'
            })
            # 컬럼명 평탄화
            monthly_stats.columns = ['실제비용_합계', '실제비용_평균', '예상비용_합계']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 📉 월별 불일치 발생 추이")
                if not monthly_mismatch.empty:
                    st.line_chart(monthly_mismatch, color="#FF0000")
                else:
                    st.info("불일치 데이터가 없습니다.")

            with col2:
                st.markdown("##### 💳 월별 평균 발송비용 (1건당)")
                st.line_chart(monthly_stats['실제비용_평균'], color="#00AA00")

            st.markdown("##### 💰 월별 총 비용 비교 (실제 vs 예상)")
            st.bar_chart(monthly_stats[['실제비용_합계', '예상비용_합계']])

        with tab2:
            # 기존 일자별 추세 유지
            daily_trend = df[df['결과'] == '❌ 불일치'].groupby('검증일시').size()
            if not daily_trend.empty:
                st.bar_chart(daily_trend)
            else:
                st.info("해당 기간/조건에 불일치 데이터가 없습니다.")

def verification_page():
    st.sidebar.header("📁 데이터 업로드 (신규)")

    # 법인 선택 추가
    entity_options = ["TFSS", "TFSK", "FSK"]
    selected_entity = st.sidebar.radio("법인 선택", entity_options, horizontal=True, key="verify_entity_radio")

    # 입력 방식: 서버 폴더에서 파일 선택 (단일 방식)
    folder_path = os.path.join(DATA_DIR, selected_entity)
    if not os.path.exists(folder_path):
        try:
            os.makedirs(folder_path) # 폴더가 없으면 생성
        except:
            pass
    
    selected_file_path = None
    files = []
    if os.path.exists(folder_path):
        files = [f for f in os.listdir(folder_path) if f.endswith('.xlsx') and not f.startswith('~$')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(folder_path, x)), reverse=True)

    
    is_duplicate = False
    if files:
        selected_filename = st.sidebar.selectbox("검증할 파일 선택", files, key="verify_file_selector")
        selected_file_path = os.path.join(folder_path, selected_filename)
        st.sidebar.info(f"선택된 파일: {selected_filename}")
        
        # ⚠️ 중복 검증 확인 로직
        if os.path.exists(RESULTS_DIR):
            # 전체 검색 (하위 폴더 포함)
            past_results = []
            for root, dirs, files in os.walk(RESULTS_DIR):
                for f in files:
                    if selected_filename in f and f.endswith(".xlsx"):
                        # 파일명에 법인이 포함되어 있거나, 상위 폴더가 해당 법인이면
                        if selected_entity in f or os.path.basename(root) == selected_entity:
                            past_results.append(f)
                
            if past_results:
                is_duplicate = True
                past_results.sort(reverse=True) # 최신순 정렬
                last_verified = past_results[0]
                try:
                    # verified_YYYYMMDD... 형식에서 날짜 추출
                    parts = last_verified.split('_')
                    if len(parts) > 1:
                        date_str = parts[1] # YYYYMMDD
                        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                        st.sidebar.error(f"⛔ {formatted_date}에 이미 검증된 파일입니다.")
                        st.sidebar.caption("중복 검증이 제한됩니다.")
                    else:
                        st.sidebar.error("⛔ 이미 검증된 이력이 있는 파일입니다.")
                except:
                    st.sidebar.error("⛔ 이미 검증된 이력이 있는 파일입니다.")
    else:
        st.sidebar.warning(f"'{selected_entity}' 폴더에 엑셀 파일이 없습니다.")
        st.sidebar.caption(f"파일을 아래 경로에 넣어주세요:\n{folder_path}")

    process_new = False

    # 파일 로드 로직
    df = None
    file_name_for_save = ""
    xls = None

    if selected_file_path:
        file_name_for_save = os.path.basename(selected_file_path)
        try:
            xls = pd.ExcelFile(selected_file_path)
        except Exception as e:
            st.error(f"파일 로드 오류: {e}")

    if xls is not None and rate_map is not None:
        # 엑셀 시트 선택 및 데이터프레임 로드
        sheet_to_use = 0
        if '세부내역' in xls.sheet_names:
            sheet_to_use = '세부내역'
        
        df = pd.read_excel(selected_file_path, sheet_name=sheet_to_use)
            
        df.columns = df.columns.str.strip() # 제목 공백 제거
        # st.sidebar.success(f"파일 로드 성공! ('{sheet_to_use}' 시트 사용)") # 중복일 땐 가리는게 나을수도, 일단 유지

        # 필수 컬럼 확인
        col_weight = '무게' 
        col_address = '수취주소' 
        col_actual_cost = '발송금액'
        required_cols = [col_weight, col_address, col_actual_cost]
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            st.error(f"❌ 필수 컬럼이 누락되었습니다: {', '.join(missing_cols)}")
            st.info(f"현재 엑셀의 제목들: {', '.join(df.columns.tolist())}")
        else:
            if is_duplicate:
                st.warning(f"⚠️ 이미 검증이 완료된 파일입니다. ({selected_filename})")
                st.info("결과를 다시 보고 싶다면 '검증 이력' 메뉴를 이용해주세요.")
            else:
                st.sidebar.success(f"파일 로드 성공! ('{sheet_to_use}' 시트 사용)")
                if st.sidebar.button("🔍 검증 시작"):
                    with st.spinner('검증 중입니다...'):
                        try:
                            # 검증 로직 수행
                            results = []
                            for index, row in df.iterrows():
                                weight = row.get(col_weight, 0)
                                address = row.get(col_address, '')
                                actual = row.get(col_actual_cost, 0)

                                expected, region, remark = calculate_expected_cost(weight, address, rate_map)
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
                                    '차액': diff,
                                    '결과': status,
                                    '비고': remark
                                })

                            # 결과 데이터프레임 생성
                            result_df = pd.DataFrame(results)
                            
                            # 원본 데이터와 합치기 (필요한 컬럼만 or 전체)
                            # 간단하게 결과만 보여주거나, 원본에 추가하거나. 
                            # 여기서는 원본과 병합하지 않고 결과를 기반으로 생성 (또는 원본 + 결과)
                            # 기존 로직: final_df = pd.concat([df, result_df], axis=1) -> 인덱스 주의
                            
                            # 안전하게 병합하기 위해 리스트 사용했음.
                            # 원본 df에 컬럼 추가 방식이 더 안전함.
                            final_df = df.copy()
                            final_df['법인'] = selected_entity
                            final_df['예상운임'] = [r['예상운임'] for r in results]
                            final_df['차액'] = [r['차액'] for r in results]
                            final_df['결과'] = [r['결과'] for r in results]
                            final_df['비고'] = [r['비고'] for r in results]

                            # 파일 저장
                            entity_result_dir = os.path.join(RESULTS_DIR, selected_entity)
                            if not os.path.exists(entity_result_dir):
                                os.makedirs(entity_result_dir)
                            
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            save_filename = f"verified_{timestamp}_{selected_entity}_{file_name_for_save}"
                            save_path = os.path.join(entity_result_dir, save_filename)
                            
                            final_df.to_excel(save_path, index=False)
                            st.success(f"✅ [{selected_entity}] 검증 완료! 결과가 저장되었습니다: {save_path}")
                            
                            display_verification_results(final_df)
                            
                        except Exception as e:
                            st.error(f"검증 중 오류 발생: {e}")
                        
    # 3. 사이드바 설정 (이력 관리)
    st.sidebar.divider()
    st.sidebar.header("📜 검증 이력")

    if os.path.exists(RESULTS_DIR):
        history_files = []
        for root, dirs, files in os.walk(RESULTS_DIR):
             for f in files:
                if f.startswith("verified_") and f.endswith(".xlsx"):
                    # 상대 경로로 저장해서 나중에 로드할 때 사용
                    rel_path = os.path.relpath(os.path.join(root, f), RESULTS_DIR)
                    history_files.append(rel_path)

        # 최신순 정렬 (파일명에 타임스탬프가 있으므로 파일명 역순 정렬하면 됨)
        # 하지만 rel_path에는 폴더명이 포함되므로 파일명만 추출해서 비교하거나 전체 경로로 비교
        history_files.sort(key=lambda x: os.path.basename(x), reverse=True)
        
        if history_files:
            selected_history = st.sidebar.selectbox("이전 결과 선택", history_files)
            if st.sidebar.button("📂 불러오기"):
                if not process_new: # 신규 검증 결과가 떠있지 않을 때만 실행
                    try:
                        history_path = os.path.join(RESULTS_DIR, selected_history)
                        history_df = pd.read_excel(history_path)
                        
                        # 호환성 처리: 이전 버전의 컬럼명 매핑
                        rename_map = {
                            '예상요금': '예상운임',
                            '검증결과': '결과',
                            '비고_검증': '비고'
                        }
                        history_df.rename(columns=rename_map, inplace=True)
                        
                        # 호환성 처리: 결과 값 매핑 (Match/Mismatch -> ✅ 일치/❌ 불일치)
                        if '결과' in history_df.columns:
                            history_df['결과'] = history_df['결과'].replace({
                                'Match': '✅ 일치',
                                'Mismatch': '❌ 불일치'
                            })

                        st.info(f"📂 불러온 파일: {selected_history}")
                        display_verification_results(history_df)
                    except Exception as e:
                        st.sidebar.error(f"파일 로드 실패: {e}")
        else:
            st.sidebar.info("저장된 검증 이력이 없습니다.")
    else:
        st.sidebar.info("저장된 검증 이력이 없습니다.")

# 메인 로직 실행
if mode == "🏠 비용 검증":
    verification_page()
elif mode == "📊 대시보드":
    dashboard_page()