import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
=========================
설정
=========================
API_KEY = "여기에_ECOS_API_KEY_입력"
한국은행 ECOS 일일환율 통계표
STAT_CODE = "731Y001"
환율 항목코드
ITEM_CODES = {
"USD": "0000001",   # 원/달러
"EUR": "0000003",   # 원/유로
"JPY": "0000002",   # 원/100엔
"CNY": "0000053"    # 원/위안
}
def get_exchange_rate(item_code):
"""
ECOS에서 일별 환율 조회
"""
end_date = datetime.today()
start_date = end_date - timedelta(days=30)
start_str = start_date.strftime("%Y%m%d")
end_str = end_date.strftime("%Y%m%d")

url = (
    f"https://ecos.bok.or.kr/api/StatisticSearch/"
    f"{API_KEY}/json/kr/1/1000/"
    f"{STAT_CODE}/D/"
    f"{start_str}/{end_str}/{item_code}"
)

response = requests.get(url)

if response.status_code != 200:
    return pd.DataFrame()

data = response.json()

if "StatisticSearch" not in data:
    return pd.DataFrame()

rows = data["StatisticSearch"]["row"]

df = pd.DataFrame(rows)

df = df[["TIME", "DATA_VALUE"]]
df.columns = ["날짜", "환율"]

df["날짜"] = pd.to_datetime(df["날짜"])
df["환율"] = pd.to_numeric(df["환율"])

df = df.sort_values("날짜", ascending=False)

# 최근 10개 영업일
df = df.head(10)

return df.sort_values("날짜") 
=========================
Streamlit 화면
=========================
st.set_page_config(
page_title="ECOS 환율 조회",
layout="wide"
)
st.title("최근 10영업일 환율 조회")
st.caption("출처 : 한국은행 ECOS")
tabs = st.tabs(["달러", "유로", "100엔", "위안"])
currencies = [
("USD", tabs[0]),
("EUR", tabs[1]),
("JPY", tabs[2]),
("CNY", tabs[3]),
]
for currency, tab in currencies:
with tab:
df = get_exchange_rate(ITEM_CODES[currency])
    if len(df) == 0:
        st.error("데이터를 가져오지 못했습니다.")
        continue

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    st.line_chart(
        data=df.set_index("날짜")["환율"]
    ) 
