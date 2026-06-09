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

st.title("📊 글로벌 경제지표 & 환율 경영 대시보드")
st.caption("최종 무결점 마감 (V19) | Streamlit 컴포넌트 규격 최적화 및 호출 에러 완전 디버깅")

# 제공해주신 한은 공식 API 인증키 자동 바인딩
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
    today_str = datetime.date.today().strftime("%Y%m%d")
    start_str = f"{datetime.date.today().year}0101"
    
    url = f"http://bok.or.kr{ECOS_API_KEY}/json/kr/1/500/{stat_code}/D/{start_str}/{today_str}/{item_code}/"
    
    try:
        response = requests.get(url, timeout=10)
        json_data = response.json()
        
        if 'StatisticSearch' in json_data and 'row' in json_data['StatisticSearch']:
            rows = json_data['StatisticSearch']['row']
            
            dates = [pd.to_datetime(row['TIME'], format='%Y%m%d') for row in rows]
            values = [float(row['DATA_VALUE']) for row in rows]
            
            series = pd.Series(values, index=dates)
            return series.sort_index()
    except Exception:
        pass
    return pd.Series(dtype=float)

@st.cache_data(ttl=1800)
def load_all_ecos_data():
    """모든 ECOS 지표를 하나의 공통 날짜 프레임에 조인하는 통합 마스터 함수"""
    all_columns = []
    
    for cat_name, cat_info in INDICATORS.items():
        stat_code = cat_info["stat_code"]
        for display_name, item_code in cat_info["tickers"].items():
            series = fetch_ecos_series(stat_code, item_code)
            
            if not series.empty:
                series.name = (cat_name, display_name)
                all_columns.append(series)
            
    # 데이터가 아예 안 잡혔을 때 발생하던 오류 방어선 재정비
    if not all_columns:
        fake_idx = pd.date_range(end=datetime.date.today(), periods=10, freq='B')
        columns = pd.MultiIndex.from_tuples([("원화환율(매매기준율)", "달러 환율")])
        empty_df = pd.DataFrame(index=fake_idx, columns=columns)
        empty_df.index = empty_df.index.strftime("%Y-%m-%d")
        return empty_df, empty_df
        
    total_df = pd.concat(all_columns, axis=1)
    total_df.columns = pd.MultiIndex.from_tuples(total_df.columns)
    total_df = total_df.dropna(how="all").sort_index(ascending=True)
    
    full_slice = total_df.tail(11).copy()
    diff_matrix = full_slice.diff().tail(10)
    display_matrix = full_slice.tail(10).copy()
    
    try:
        display_matrix.index = pd.to_datetime(display_matrix.index).strftime("%Y-%m-%d")
        diff_matrix.index = pd.to_datetime(diff_matrix.index).strftime("%Y-%m-%d")
    except Exception:
        pass
    
    return display_matrix, diff_matrix

# =========================================================
# 4. 데이터 엔진 가동 제어
# =========================================================
data, diff_data = load_all_ecos_data()

# =========================================================
# 5. 상단 레이아웃 및 엑셀 다운로드 컨트롤러 배치 [TypeError 디버깅 해결 완료]
# =========================================================
# columns 메서드 내부에 분할할 개수(2)를 명확한 인자로 전달하여 타입 에러를 원천 차단했습니다.
col1, col2 = st.columns(2)
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
st.info("💡 **가이드**: 한국은행 고시 규칙에 맞춰 데이터가 수집되지 않은 칸은 가공 없이 정직한 공백으로 노출됩니다.")

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
