import os
import requests
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict

# ==========================================
# ECOS API KEY (Streamlit Secrets 활용)
# ==========================================
API_KEY = st.secrets["ECOS_API_KEY"]

# ==========================================
# 조회할 항목 및 고유 통계표 코드 정의
# ==========================================
# 각 지표가 속한 [통계표 코드, 항목 코드, 표시될 한글 이름]을 묶어서 관리합니다.
ITEMS_CONFIG = {
    "USD":       {"stat_code": "022Y013", "item_code": "0000001", "name": "원/달러"},
    "EUR":       {"stat_code": "022Y013", "item_code": "0000002", "name": "원/유로"},
    "JPY100":    {"stat_code": "022Y013", "item_code": "0000003", "name": "원/100엔"},
    "CNY":       {"stat_code": "022Y013", "item_code": "0000013", "name": "원/위안"},
    "KTB3Y":     {"stat_code": "021Y002", "item_code": "010200000", "name": "국고채(3년)"},
    "KTB10Y":    {"stat_code": "021Y002", "item_code": "010400000", "name": "국고채(10년)"},
    "CORP_AA3Y": {"stat_code": "021Y002", "item_code": "010300000", "name": "회사채AA-(3년)"}
}

def get_ecos_data(stat_code, item_code, key_name):
    """
    각 지표의 고유 통계표 코드와 항목 코드를 매개변수로 받아 
    최근 30일간의 데이터를 안전하게 수집하는 함수입니다.
    """
    end_date = datetime.today()
    start_date = end_date - timedelta(days=30)

    start = start_date.strftime("%Y%m%d")
    end = end_date.strftime("%Y%m%d")

    # 통계표 코드(stat_code)가 주소 중간에 동적으로 배치되도록 수정
    url = (
        f"https://bok.or.kr"
        f"{API_KEY}/json/kr/1/1000/"
        f"{stat_code}/D/{start}/{end}/{item_code}/?"
    )

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        if "StatisticSearch" not in data or "row" not in data["StatisticSearch"]:
            return None

        rows = data["StatisticSearch"]["row"]
        df = pd.DataFrame(rows)
        
        # 필요한 컬럼만 추출 및 정제
        df = df[["TIME", "DATA_VALUE"]].copy()
        df.columns = ["DATE", key_name]
        
        # 문자열 숫자를 연산 및 정렬이 가능한 실수형(float)으로 변환
        df[key_name] = pd.to_numeric(df[key_name], errors='coerce')
        
        return df
    except Exception:
        return None

@st.cache_data
def build_table():
    """
    수집된 환율 및 금리 데이터를 날짜 기준으로 완전 외부 조인(Outer Merge)하여
    하나의 통합 데이터프레임으로 구축합니다.
    """
    merged = None

    # 지표 설정을 순회하면서 데이터를 수집하고 결합
    for key_name, config in ITEMS_CONFIG.items():
        df = get_ecos_data(config["stat_code"], config["item_code"], key_name)

        if df is None:
            continue

        if merged is None:
            merged = df
        else:
            merged = merged.merge(df, on="DATE", how="outer")

    if merged is None:
        return pd.DataFrame()

    # 날짜 컬럼 형식 변환 및 정렬 환경 구축
    merged["DATE"] = pd.to_datetime(merged["DATE"], format="%Y%m%d")
    
    # 시간 순서대로 정렬 (오름차순) 후 최근 10일 필터링
    merged = merged.sort_values("DATE", ascending=True)
    merged = merged.tail(10)

    # 날짜 표시 포맷 변경 (예: 2026-06-10)
    merged["DATE"] = merged["DATE"].dt.strftime("%Y-%m-%d")

    # 영문 컬럼명을 직관적인 한글 이름으로 일괄 매핑
    rename_mapping = {"DATE": "날짜"}
    for key_name, config in ITEMS_CONFIG.items():
        rename_mapping[key_name] = config["name"]
        
    merged = merged.rename(columns=rename_mapping)

    return merged

# ==========================================
# Streamlit 화면 구성 (웹 인터페이스)
# ==========================================
st.set_page_config(
    page_title="경제지표 조회",
    layout="wide"
)

st.title("환율 및 금리 현황")
st.caption("한국은행 API 기반 최근 10 영업일 데이터 동향 (오름차순)")

with st.spinner("한국은행 API로부터 실시간 데이터를 가져오는 중입니다..."):
    df = build_table()

if not df.empty:
    # 소수점 둘째 자리까지 깔끔하게 포맷팅하여 데이터프레임 출력
    st.dataframe(
        df.style.format(num_format="{:.2f}", na_rep="-"),
        use_container_width=True,
        hide_index=True
    )
else:
    st.error("❌ 데이터를 가져오지 못했습니다. Streamlit Secrets에 등록된 ECOS_API_KEY를 확인해 주세요.")
