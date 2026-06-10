import os
import requests
from collections import defaultdict
from datetime import datetime

# GitHub Secrets로부터 API 키 로드
API_KEY = os.environ.get("ECOS_API_KEY")

if not API_KEY:
    raise ValueError("환경변수 ECOS_API_KEY를 찾을 수 없습니다. GitHub Secrets 설정을 확인하세요.")

# [조회 항목 정의]
# 통계표코드, 항목코드1, 항목코드2, 표시이름
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
    """ECOS API로부터 최근 데이터 여러 건을 가져오는 함수"""
    # 현재 연도를 반영하여 데이터 요청 (충넉히 최근 데이터를 받기 위해 20건 요청)
    current_year = datetime.now().year
    url = f"http://bok.or.kr{API_KEY}/json/kr/1/{num_records}/{stat_code}/D/{current_year}0101/{current_year}1231/{item_code1}/{item_code2}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
            return data["StatisticSearch"]["row"]
        return []
    except Exception as e:
        print(f"API 요청 중 오류 발생 ({stat_code}-{item_code1}): {e}")
        return []

def main():
    # 날짜별로 데이터를 모으기 위한 딕셔너리 (행: 날짜, 열: 지표)
    # { '20260601': { '원/달러': '1350.2', '국채 3년': '3.52' ... } }
    table_data = defaultdict(dict)
    
    # 1. 모든 지표 데이터 받아와서 재구조화
    for stat_code, item_code1, item_code2, name in TARGET_INDICATORS:
        rows = get_ecos_history(stat_code, item_code1, item_code2)
        for row in rows:
            date = row['TIME']       # YYYYMMDD 형태
            value = row['DATA_VALUE']
            table_data[date][name] = value

    # 2. 데이터가 있는 날짜들을 오름차순 정렬
    sorted_dates = sorted(table_data.keys())
    
    # 3. 최근 10영업일만 추출
    recent_10_dates = sorted_dates[-10:]

    # 4. 표 형태로 출력
    print("==========================================================================================")
    print("                      [최근 10 영업일 금융 지표 동향 (오름차순)]")
    print("==========================================================================================")
    
    # 헤더 출력 (가로축 지표 이름)
    header = f"{'날짜':<12}"
    for _, _, _, name in TARGET_INDICATORS:
        header += f"{name:>12}"
    print(header)
    print("-" * len(header) * 1)
    
    # 데이터 행 출력 (세로축 날짜)
    for date in recent_10_dates:
        # 날짜 포맷 변경 (YYYYMMDD -> YYYY-MM-DD)
        formatted_date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
        row_str = f"{formatted_date:<12}"
        
        for _, _, _, name in TARGET_INDICATORS:
            # 해당 날짜에 데이터가 없으면 '-' 표시
            val = table_data[date].get(name, "-")
            
            # 수치 데이터 형식 정렬
            try:
                row_str += f"{float(val):>12.2f}"
            except ValueError:
                row_str += f"{val:>12}"
                
        print(row_str)
        
    print("==========================================================================================")

if __name__ == "__main__":
    main()
