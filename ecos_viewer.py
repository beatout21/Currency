import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ==========================================
# ECOS API KEY
# ==========================================
API_KEY = st.secrets["ECOS_API_KEY"]

# ==========================================
# 조회할 항목 (원본 분류 코드 유지)
# ==========================================
ITEMS = {
  "USD": "0000001",
  "EUR": "0000003",
  "JPY100": "0000002",
  "CNY": "0000053",
  "KTB3Y": "010200000",
  "KTB10Y": "010210000",
  "CORP_AA3Y": "010300000"
}


def get_ecos_data(item_code):

  end_date = datetime.today()
  start_date = end_date - timedelta(days=30)

  start = start_date.strftime("%Y%m%d")
  end = end_date.strftime("%Y%m%d")

  if item_code in ["010200000", "010210000", "010300000"]:
    target_stat_code = "817Y002"
    url = (
      f"https://bok.or.kr"
      f"{API_KEY}/json/kr/1/1000/"
      f"{target_stat_code}/D/"
      f"{start}/{end}/{item_code}/?"
    )
  else:
    target_stat_code = "731Y001"
    url = (
      f"https://bok.or.kr"
      f"{API_KEY}/json/kr/1/1000/"
      f"{target_stat_code}/D/"
      f"{start}/{end}/{item_code}"
    )

  try:
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
      return None

    data = response.json()
    if "StatisticSearch" not in data:
      return None

    rows = data["StatisticSearch"]["row"]
    df = pd.DataFrame(rows)
    df = df[["TIME", "DATA_VALUE"]]
    df.columns = ["DATE", item_code]
    return df
  except Exception:
    return None


@st.cache_data
def build_table():

  merged = None

  for name, code in ITEMS.items():

    df = get_ecos_data(code)

    if df is None:
      continue

    df.columns = ["DATE", name]

    if merged is None:
      merged = df
    else:
      merged = merged.merge(
        df,
        on="DATE",
        how="outer"
      )

  if merged is None:
    return pd.DataFrame()

  merged["DATE"] = pd.to_datetime(merged["DATE"], format="%Y%m%d")

  # 원본 작동 확인 완료 로직 유지 (내림차순 정렬 후 최근 10일)
  merged = merged.sort_values("DATE", ascending=False)
  merged = merged.head(10)

  merged["DATE"] = merged["DATE"].dt.strftime("%Y-%m-%d")

  merged = merged.rename(
    columns={
      "DATE": "날짜",
      "USD": "원/달러",
      "EUR": "원/유로",
      "JPY100": "원/100엔",
      "CNY": "원/위안",
      "KTB3Y": "국고채(3년)",
      "KTB10Y": "국고채(10년)",
      "CORP_AA3Y": "회사채AA-(3년)"
    }
  )

  return merged


@st.cache_data
def get_opinet_10day_oil():
    """오피넷 웹사이트 주소에서 국제유가 표를 읽어와 최근 10영업일의 3대 원유 가격만 정제합니다."""
    # 오피넷 일간 국제유가 변동 표가 위치한 내부 도메인 주소 활용
    url = "https://opinet.co.kr"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            tables = pd.read_html(response.text)
            oil_raw = tables[0]  # 오피넷 국제유가 첫 번째 데이터프레임 로드
            
            # 컬럼명의 문자열 좌우 공백 일괄 정리
            oil_raw.columns = [str(col).strip() for col in oil_raw.columns]
            
            # 오피넷 표 표준 컬럼 구조 매핑 (구조 변경 대응을 위해 첫 번째 열을 날짜로 지정)
            date_col = oil_raw.columns[0]
            
            # 요구사항 반영: [날짜], [두바이유], [브렌트유], [WTI] 관련 데이터 컬럼만 동적 선별
            oil_filtered = oil_raw[[date_col, "두바이유", "브렌트유", "WTI"]].copy()
            oil_filtered = oil_filtered.rename(columns={date_col: "날짜"})
            
            # 웹 표 상단에 위치한 가장 최근 10 영업일 데이터 행(Rows)만 추출
            oil_10day = oil_filtered.head(10)
            return oil_10day
        return None
    except Exception:
        return None


# ==========================================
# 화면 레이아웃 정의 (환율 -> 금리 -> 유종 순서)
# ==========================================
st.set_page_config(
  page_title="경제 및 유가 지표 조회",
  layout="wide"
)

st.title("💱 환율, 금리 및 국제유가 현황")
st.caption("한국은행 오픈 API 및 오피넷 실시간 연동 (그래프 제외)")

# 한국은행 원본 빌드 테이블 호출
df = build_table()

if not df.empty:
  # 1. 💵 환율 표 출력
  st.subheader("💵 환율 현황 (최근 10일)")
  exchange_cols = ["날짜", "원/달러", "원/유로", "원/100엔", "원/위안"]
  st.dataframe(df[exchange_cols], use_container_width=True, hide_index=True)

  # 2. 📈 금리 표 출력
  st.subheader("📈 금리 현황 (최근 10일)")
  existing_interest_cols = ["날짜"]
  interest_targets = ["국고채(3년)", "국고채(10년)", "회사채AA-(3년)"]

  for col in interest_targets:
      if col in df.columns:
          existing_interest_cols.append(col)
      else:
          df[col] = "-"
          existing_interest_cols.append(col)

  st.dataframe(df[existing_interest_cols], use_container_width=True, hide_index=True)
else:
  st.error("❌ 한국은행 금융 데이터를 로드하지 못했습니다.")

# 3. 🛢️ 오피넷 국제유가 필터링 표 출력
st.write("---")
st.subheader("🛢️ 국제 유가 동향 (최근 10일 - Dubai, Brent, WTI)")

oil_10day_df = get_opinet_10day_oil()

if oil_10day_df is not None and not oil_10day_df.empty:
    st.dataframe(
        oil_10day_df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("⚠️ 오피넷 웹사이트 보안 설정 및 구조적 문제로 유가 표 데이터를 연동할 수 없습니다.")
