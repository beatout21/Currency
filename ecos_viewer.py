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

  # [통계표별 주소 체계 조건 분기]
  if item_code in ["010200000", "010210000", "010300000"]:
    # 1. 금리 데이터 (개편된 시장금리 통계표 반영)
    target_stat_code = "817Y002"
    # 중요: 817Y002 통계표는 하위 분류가 없음을 뜻하는 /? 자리를 규격상 반드시 명시해야 합니다.
    url = (
      f"https://ecos.bok.or.kr/api/StatisticSearch/"
      f"{API_KEY}/json/kr/1/1000/"
      f"{target_stat_code}/D/"
      f"{start}/{end}/{item_code}/?"
    )
  else:
    # 2. 환율 데이터
    target_stat_code = "731Y001"
    url = (
      f"https://ecos.bok.or.kr/api/StatisticSearch/"
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

  merged = merged.sort_values(
    "DATE",
    ascending=False
  )

  merged = merged.head(10)

  # 날짜 표기 가독성 정리 (YYYY-MM-DD)
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


# ==========================================
# 화면 레이아웃 (환율 표 선배치 / 금리 표 후배치)
# ==========================================
st.set_page_config(
  page_title="경제지표 조회",
  layout="wide"
)

st.title("환율 및 금리 현황")
st.caption("한국은행 경제통계시스템(ECOS) API 연동 최근 10 영업일 데이터 동향")

# 통합 데이터 테이블 생성
df = build_table()

if not df.empty:
  # 1. 💱 환율 표 상단 출력
  st.subheader("💱 환율 현황")
  exchange_cols = ["날짜", "원/달러", "원/유로", "원/100엔", "원/위안"]
  st.dataframe(
    df[exchange_cols],
    use_container_width=True,
    hide_index=True
  )

  # 2. 📊 금리 표 하단 출력
  st.subheader("📊 금리 현황")
  
  # 데이터 누락에 대비한 안전장치 적용 구조
  existing_interest_cols = ["날짜"]
  interest_targets = ["국고채(3년)", "국고채(10년)", "회사채AA-(3년)"]

  for col in interest_targets:
      if col in df.columns:
          existing_interest_cols.append(col)
      else:
          df[col] = "-"
          existing_interest_cols.append(col)

  st.dataframe(
    df[existing_interest_cols],
    use_container_width=True,
    hide_index=True
  )
else:
  st.error("❌ 데이터를 가져오는 데 실패했습니다. Streamlit Secrets 보관함에 등록된 API 키 설정을 점검해 주세요.")
