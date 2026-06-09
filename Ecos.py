import streamlit as st
import pandas as pd
import requests
import io
import datetime

# 페이지 설정
st.set_page_config(page_title="ECOS 금융 대시보드", layout="wide")
st.title("🏛️ 한국은행 ECOS 금융 지표")

# ECOS API 설정 (731Y001: 환율, 817Y002: 금리)
API_KEY = st.sidebar.text_input("ECOS API 인증키", type="password")

@st.cache_data(ttl=3600)
def get_ecos_data(key, stat_code, item_code):
    url = f"http://ecos.bok.or.kr/api/StatisticSearch/{key}/json/kr/1/100/{stat_code}/D/20230101/{datetime.date.today().strftime('%Y%m%d')}/{item_code}/"
    try:
        response = requests.get(url)
        df = pd.DataFrame(response.json()['StatisticSearch']['row'])
        df['TIME'] = pd.to_datetime(df['TIME'], format='%Y%m%d')
        return df.set_index('TIME')['DATA_VALUE'].astype(float)
    except: return None

# 데이터 수집 (예시: 환율 및 3년 국고채)
if API_KEY:
    ex_rate = get_ecos_data(API_KEY, "731Y001", "0000001")
    bond_3y = get_ecos_data(API_KEY, "817Y002", "010200000")
    
    if ex_rate is not None and bond_3y is not None:
        df = pd.concat([ex_rate, bond_3y], axis=1)
        df.columns = ['원/달러 환율', '국고채 3년(%)']
        df = df.ffill().dropna()
        
        st.subheader("최근 데이터 및 차트")
        st.line_chart(df.tail(30))
        st.dataframe(df.tail(10))
    else: st.error("데이터를 불러올 수 없습니다.")
else: st.info("사이드바에 API Key를 입력하세요.")
