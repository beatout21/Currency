import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# ==========================================
# ECOS API KEY
# ==========================================
API_KEY = st.secrets["ECOS_API_KEY"]

# ==========================================
# 시장금리 통계표 코드 및 세부 항목 정의
# ==========================================
STAT_CODE = "817Y002"

ITEMS = {
  "KTB3Y": "010200000",      # 국고채(3년)
  "KTB10Y": "010210000",     # 국고채(10년)
  "CORP_AA3Y": "010300000"   # 회사채AA-(3년)
}


def get_ecos_interest_data(item_code):
  """시장금리 통계표 규격에 맞추어 데이터를 호출합니다."""
  end_date = datetime.today()
  start_date = end_date - timedelta(days=30)

  start = start_date.strftime("%Y%m%d")
  end = end_date.strftime("%Y%m%d")

  # 817Y002 통계표는 뒤에 /? 처리를 명확히 해주어야 서버 오류가 발생하지 않습니다.
  url = (
    f"https://ecos.bok.or.kr/api/StatisticSearch/"
    f"{API_KEY}/json/kr/1/1000/"
    f"{STAT_CODE}/D/"
    f"{start}/{end}/{item_code}/?"
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
    
    # 필요한 컬럼 정제 [날짜, 금리값]
    df = df[["TIME", "DATA_VALUE"]]
    df.columns = ["DATE", item_code]
    return df
  except Exception:
    return None


@st.cache_data
def build_interest_table():
  """금리 데이터를 순회 수집하여 하나의 테이블로 완성합니다."""
  merged = None

  for name, code in ITEMS.items():
    df = get_ecos_interest_data(code)

    if df is None:
      continue

    # 컬럼명을 직관적인 이름으로 임시 변환하여 결합 준비
    df.columns = ["DATE", name]

    if merged is None:
      merged = df
    else:
      merged = merged.merge(df, on="DATE", how="outer")

  if merged is None:
    return pd.DataFrame()

  # 날짜형 정렬 및 최근 10영업일 슬라이싱
  merged["DATE"] = pd.to_datetime(merged["DATE"], format="%Y%m%d")
  merged = merged.sort_values("DATE", ascending=False)
  merged = merged.head(10)

  # 날짜 표기 가독성 확보 (YYYY-MM-DD)
  merged["DATE"] = merged["DATE"].dt.strftime("%Y-%m-%d")

  # 최종 한글 컬럼명 변환 매핑
  merged = merged.rename(
    columns={
      "DATE": "날짜",
      "KTB3Y": "국고채(3년)",
      "KTB10Y": "국고채(10년)",
      "CORP_AA3Y": "회사채AA-(3년)"
    }
  )

  return merged


# ==========================================
# Streamlit 화면 레이아웃 정의 (그래프 제외)
# ==========================================
st.set_page_config(
  page_title="국내 금리 조회",
  layout="wide"
)

st.title("📊 국내 주요 채권 금리 현황")
st.caption("한국은행 경제통계시스템(ECOS) API 연동 최근 10 영업일 동향")

# 테이블 연산 및 화면 렌더링
df = build_interest_table()

if not df.empty:
  st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
  )
else:
  st.error("❌ 금리 데이터를 호출하는 데 실패했습니다. Streamlit Secrets 보관함에 등록된 API 키가 정상적인지 확인해 주세요.")
