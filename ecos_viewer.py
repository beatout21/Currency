import os
import requests
import streamlit as st
from collections import defaultdict
from datetime import datetime
import pandas as pd

# 1. 스트림릿 전용 보안 금고에서 API 키 로드
if "ECOS_API_KEY" in st.secrets:
    API_KEY = st.secrets["ECOS_API_KEY"]
else:
    # 로컬이나 다른 환경을 위한 백업 로직
    API_KEY = os.environ.get("ECOS_API_KEY")

if not API_KEY:
    st.error("❌ ECOS_API_KEY를 찾을 수 없습니다. Streamlit Cloud 설정의 Secrets를 확인해주세요.")
    st.stop()

# [조회 항목 정의]
TARGET_INDICATORS = [
    ("022Y013", "0000001", "?", "원/달러"),
    ("022Y013", "0000002", "?", "원/엔(100)"),
    ("022Y013", "0000003", "?", "원/유로"),
    ("022Y013", "0000013", "?", "원/위안"),
    ("021Y002", "010200000", "?", "국채 3년"),
    ("021Y002", "010400000", "?", "국채 10년"),
    ("021Y002", "010300000", "?", "회사채(AA-) 3년")
]

def get_ecos_history(stat_code, item_code1, item_code2="?", num_records=20):
    """현재 날짜 기준으로 한국은행 API에서 데이터를 가져오는 함수"""
    today = datetime.now().strftime("%Y%m%d")
    start_date = f"{datetime.now().year}0101"
    
    base_url = "http://bok.or.kr"
    url = f"{base_url}/{API_KEY}/json/kr/1/{num_records}/{stat_code}/D/{start_date}/{today}/{item_code1}/{item_code2}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
            return data["StatisticSearch"]["row"]
        return []
    except Exception as e:
        return []

def main():
    st.title("📊 한국은행 금융 지표 대시보드")
    st.subheader("최근 10 영업일 환율 및 금리 동향 (오름차순)")
    
    with st.spinner("한국은행 API로부터 데이터를 가져오는 중입니다..."):
        table_data = defaultdict(dict)
        
        # 데이터 수집
        for stat_code, item_code1, item_code2, name in TARGET_INDICATORS:
            rows = get_ecos_history(stat_code, item_code1, item_code2)
            for row in rows:
                date = row['TIME']       
                value = row['DATA_VALUE']
                table_data[date][name] = value

        if not table_data:
            st.error("❌ 가져온 데이터가 없습니다. API 키 상태나 한국은행 서버 상황을 확인해 주세요.")
            return

        # 데이터 정렬 및 최근 10일 필터링
        sorted_dates = sorted(table_data.keys())
        recent_10_dates = sorted_dates[-10:]

        # 판다스 데이터프레임 구조 생성
        report_list = []
        for date in recent_10_dates:
            formatted_date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
            row_dict = {"날짜": formatted_date}
            
            for _, _, _, name in TARGET_INDICATORS:
                val = table_data[date].get(name, None)
                if val is not None:
                    try:
                        row_dict[name] = float(val)
                    except ValueError:
                        row_dict[name] = val
                else:
                    row_dict[name] = "-"
            report_list.append(row_dict)
            
        df = pd.DataFrame(report_list)
        df.set_index("날짜", inplace=True)
        
        # 스트림릿 화면에 예쁜 웹 표로 출력
        st.dataframe(df, use_container_width=True)
        st.success("✅ 조회가 완료되었습니다.")

if __name__ == "__main__":
    main()
