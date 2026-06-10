import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ==========================================
# ECOS API KEY
# ==========================================
API_KEY = st.secrets["ECOS_API_KEY"]

# ==========================================
# 통계표 코드 (환율/주요금리가 통합되어 있는 일별 통계표)
# ==========================================
STAT_CODE = "731Y001"

# ==========================================
# 조회할 항목 (원래 정의해주신 순서와 분류 그대로 유지)
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

  url = (
    f"https://bok.or.kr"
    f"{API_KEY}/json/kr/1/1000/"
    f"{STAT_CODE}/D/"
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

  # 날짜 형식 변환 및 정렬 (가장 최신 날짜가 위로 오도록 내림차순 정렬 후 10개 추출)
  merged["DATE"] = pd.to_datetime(merged["DATE"], format="%Y%m%d")
  merged = merged.sort_values("DATE", ascending=False)
  merged = merged.head(10)
  
  # 표에 표시할 최종 날짜 포맷 정리 (YYYY-MM-DD)
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
# 화면 구성 (요청에 따라 환율 차트 완전 제거)
# ==========================================
st.set_page_config(
  page_title="경제지표 조회",
  layout="wide"
)

st.title("환율 및 금리 현황")

df = build_table()

if not df.empty:
  st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
  )
else:
  st.error("❌ 데이터를 가져오지 못했습니다. Streamlit Cloud의 Secrets 설정과 API 키를 다시 한 번 확인해 주세요.")
