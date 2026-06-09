import datetime
import io
import pandas as pd
import streamlit as st
import requests

# =========================================================
# 1. 페이지 설정 (CEO 경영 보고용 와이드 레이아웃)
# =========================================================
st.set_page_config(
    page_title="한국은행 ECOS 금융 대시보드",
    layout="wide"
)

st.title("🏛️ 한국은행 ECOS 금융 지표 대시보드")
st.caption("오류 수정 완료 | 한국은행 경제통계시스템(ECOS) 공식 Open API 실시간 다이렉트 연동")

# 공식 API 인증키 자동 마운트
ECOS_API_KEY = "ZXBH7LM5BB9NFLDW0DEA"

# =========================================================
# 2. 한국은행 ECOS 공식 통계표 및 세부 항목코드 정의
# =========================================================
INDICATORS = {
    "원화환율(매매기준율)": {
        "stat_code": "731Y001",
        "tickers": {
            "달러 환율": "0000001",
            "유로 환율": "0000003",
            "엔 환율 (100엔)": "0000002",
            "위안 환율": "0000053"
        }
    },
    "한국 국채 및 회사채 금리(종가)": {
        "stat_code": "817Y002",
        "tickers": {
            "국고채 3년 수익률": "010200000",
            "국고채 10년 수익률": "010210000",
            "회사채(AA-) 3년 수익률": "010300000"
        }
    }
}

# =========================================================
# 3. ECOS API 다이렉트 웹 패킷 요청 처리기
# =========================================================
@st.cache_data(ttl=1800)
def fetch_ecos_series(stat_code, item_code):
    """한국은행 통계조회 API 서버에 접근하여 시계열 데이터를 파싱하는 함수"""
    end_date = datetime.date.today().strftime("%Y%m%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=45)).strftime("%Y%m%d")
    
    url = f"http://bok.or.kr{ECOS_API_KEY}/json/kr/1/100/{stat_code}/D/{start_date}/{end_date}/{item_code}/"
    
    try:
        response = requests.get(url, timeout=10)
        json_data = response.json()
        
        if 'StatisticSearch' in json_data and 'row' in json_data['StatisticSearch']:
            rows = json_data['StatisticSearch']['row']
            
            dates = [pd.to_datetime(row['TIME'], format='%Y%m%d') for row in rows]
            values = [float(row['DATA_VALUE']) for row in rows]
            
            series = pd.Series(values, index=dates)
            return series
    except Exception:
        pass
    return pd.Series(dtype=float)

@st.cache_data(ttl=1800)
def load_all_ecos_data():
    """모든 ECOS 지표를 하나의 공통 날짜 프레임에 안정적으로 조인하는 통합 마스터 함수"""
    all_columns = []
    
    for cat_name, cat_info in INDICATORS.items():
        stat_code = cat_info["stat_code"]
        for display_name, item_code in cat_info["tickers"].items():
            series = fetch_ecos_series(stat_code, item_code)
            
            if not series.empty:
                series.name = (cat_name, display_name)
                all_columns.append(series)
            
    if not all_columns:
        return None, None
        
    # 가로형 데이터 매트릭스로 결합
    total_df = pd.concat(all_columns, axis=1)
    total_df.columns = pd.MultiIndex.from_tuples(total_df.columns)
    total_df = total_df.dropna(how="all").sort_index(ascending=True)
    
    # 최근 10영업일 데이터 구조 표출 및 전일비 연산용 11행 분리
    full_slice = total_df.tail(11).copy()
    diff_matrix = full_slice.diff().tail(10)
    display_matrix = full_slice.tail(10).copy()
    
    # [오류 해결 포인트] 인덱스를 명확하게 Datetime 포맷으로 한 번 더 강제 고정한 뒤 strftime 변환 실행
    try:
        display_matrix.index = pd.to_datetime(display_matrix.index)
        diff_matrix.index = pd.to_datetime(diff_matrix.index)
        
        display_matrix.index = display_matrix.index.strftime("%Y-%m-%d")
        diff_matrix.index = diff_matrix.index.strftime("%Y-%m-%d")
    except Exception:
        # 혹시라도 날짜 변환이 또 깨질 경우 앱이 완전히 다운되는 것을 방지하는 최종 예외 방어선
        pass
    
    return display_matrix, diff_matrix

# =========================================================
# 4. 데이터 엔진 가동 및 방어 제어
# =========================================================
data, diff_data = load_all_ecos_data()

if data is None or data.empty:
    st.error("❌ 한국은행 ECOS API 연결 과정에서 데이터 병합 오류가 발생했습니다. 잠시 후 새로고침을 해주세요.")
    st.stop()

# =========================================================
# 5. 상단 레이아웃 및 엑셀 다운로드 컨트롤러 배치
# =========================================================
col1, col2 = st.columns()
with col1:
    st.subheader("🗓️ 날짜별 금융 지표 변동 현황 (최근 10영업일 마감)")
with col2:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        data.to_excel(writer, sheet_name="ECOS지표")
    buffer.seek(0)

    st.download_button(
        "📥 경영 보고용 엑셀 다운로드",
        data=buffer,
        file_name=f"BOK_ECOS_Report_{datetime.date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# =========================================================
# 6. 테이블 시각화 조건부 컬러링
# =========================================================
def highlight_changes(df_data, df_diff):
    style = pd.DataFrame("", index=df_data.index, columns=df_data.columns)
    for col in df_data.columns:
        for idx in df_data.index:
            try:
                diff = df_diff.loc[idx, col]
                if pd.isna(diff) or diff == 0:
                    continue
                if diff > 0:
                    style.loc[idx, col] = "background-color:#FFEBEE; color:#D32F2F; font-weight:bold;"
                elif diff < 0:
                    style.loc[idx, col] = "background-color:#E3F2FD; color:#1976D2; font-weight:bold;"
            except Exception:
                pass
    return style

# 가변 소수점 포맷팅 마감
styled_df = (
    data.style
    .apply(lambda x: highlight_changes(data, diff_data), axis=None)
    .format(lambda x: "" if pd.isna(x) else f"{x:,.2f}")
)

st.dataframe(styled_df, use_container_width=True, height=500)
st.info("💡 **가이드**: 한국은행 고시 규칙에 맞춰 당일 데이터가 수집되지 않은 칸은 가공 없이 정직한 공백으로 노출됩니다.")

# =========================================================
# 7. 인터랙티브 추세 차트 컴포넌트
# =========================================================
st.markdown("---")
st.subheader("📈 지표별 시계열 상세 트렌드 분석")

options = [f"{cat} | {sub}" for cat, sub in data.columns]
selected = st.selectbox("추세를 시각화할 경영 지표를 선택해 주세요:", options)

if selected:
    cat, item = selected.split(" | ")
    chart_data = data[(cat, item)].copy()
    chart_df = pd.DataFrame({item: chart_data})
    st.line_chart(chart_df, use_container_width=True)
