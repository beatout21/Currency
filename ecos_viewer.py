import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ==========================================
# ECOS API KEY
# ==========================================
API_KEY = st.secrets["ECOS_API_KEY"]

# ==========================================
# 조회할 항목 (국고채 10년의 신규 매핑 코드로 업데이트)
# ==========================================
ITEMS = {
  "USD": "0000001",
  "EUR": "0000003",
  "JPY100": "0000002",
  "CNY": "0000053",
  "KTB3Y": "010200000",
  "KTB10Y": "010200001",     # 817Y002 통계표용 신규 10년 국채 코드로 수정
  "CORP_AA3Y": "010300000"
}


def get_ecos_data(item_code):

  end_date = datetime.today()
  start_date = end_date - timedelta(days=30)

  start = start_date.strftime("%Y%m%d")
  end = end_date.strftime("%Y%m%d")

  # [핵심 수정 부분: get_ecos_data 함수 내 주소 빌더]
if item_code in ["010200000", "010210000", "010300000"]:
    target_stat_code = "817Y002"
    # 시장금리(817Y002)는 하위 분류 자리(/?)를 포함해야 데이터가 정상 반환됨
    url = (
      f"https://ecos.bok.or.kr/api/StatisticSearch/"
      f"{API_KEY}/json/kr/1/1000/"
      f"{target_stat_code}/D/"
      f"{start}/{end}/{item_code}/?"
    )
else:
    # 환율(731Y001)은 기존 구조 유지
    target_stat_code = "731Y001"
    url = (
      f"https://ecos.bok.or.kr/api/StatisticSearch/"
      f"{API_KEY}/json/kr/1/1000/"
      f"{target_stat_code}/D/"
      f"{start}/{end}/{item_code}"
    )

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

  merged["DATE"] = pd.to_datetime(merged["DATE"])

  merged = merged.sort_values(
    "DATE",
    ascending=False
  )

  merged = merged.head(10)

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
# 화면
# ==========================================
st.set_page_config(
  page_title="경제지표 조회",
  layout="wide"
)

st.title("환율 및 금리 현황")

# 통합 데이터 연산 수행
df = build_table()

# 1. 환율 표 출력 (수정 없음)
st.subheader("💱 환율 현황")
exchange_cols = ["날짜", "원/달러", "원/유로", "원/100엔", "원/위안"]
st.dataframe(
  df[exchange_cols],
  use_container_width=True,
  hide_index=True
)

# 2. 금리 표 출력 (안전 장치 포함 구조)
st.subheader("📊 금리 현황")

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
