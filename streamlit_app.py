import streamlit as st
import pandas as pd
from data.fetch_exchange import get_recent_week_rates
from utils.helpers import format_number   # 필요 시 만든 포맷 함수

st.set_page_config(page_title="최근 1주일 원화 환율(시초가)", layout="wide")

st.title("💱 최근 1주일 원화 환율 (시초가)")

@st.cache_data(ttl=86400)   # 하루에 한 번만 API 호출
def load_data():
    return get_recent_week_rates()

df = load_data()

if df.empty:
    st.warning("데이터를 가져오지 못했습니다. API 키와 네트워크를 확인해 주세요.")
else:
    # 날짜를 인덱스로 설정해 차트에 바로 사용
    chart_df = df.set_index("DATE")
    st.line_chart(chart_df)

    # 테이블 표시 (값 포맷)
    st.subheader("표 형태")
    st.dataframe(
        df.assign(
            USD=lambda x: x["USD"].apply(format_number),
            EUR=lambda x: x["EUR"].apply(format_number),
            JPY=lambda x: x["JPY"].apply(format_number),
            CNY=lambda x: x["CNY"].apply(format_number)
        ),
        hide_index=False,
        use_container_width=True
    )

    # CSV 다운로드
    csv = df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="CSV 파일 다운로드",
        data=csv,
        file_name="krw_exchange_last_week.csv",
        mime="text/csv"
    )
