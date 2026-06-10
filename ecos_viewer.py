import os
import requests
from collections import defaultdict
from datetime import datetime

# GitHub Secrets로부터 API 키 로드
API_KEY = os.environ.get("ECOS_API_KEY")

if not API_KEY:
    raise ValueError("환경변수 ECOS_API_KEY를 찾을 수 없습니다. GitHub Secrets 설정을 확인하세요.")

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
    """현재 날짜를 기준으로 안전하게 데이터를 가져오는 함수"""
    # 현재 날짜를 YYYYMMDD 형식으로 가져옵니다 (미래 날짜 요청 방지)
    today = datetime.now().strftime("%Y%m%d")
    # 최근 20영업일 데이터를 확보하기 위해 시작일은 올해 1월 1일로 설정
    start_date = f"{datetime.now().year}0101"
    
    # 한국은행 API 표준 주소 규격에 맞춰 정확히 조립
    url = f"http://bok.or.kr{API_KEY}/json/kr/1/{num_records}/{stat_code}/D/{start_date}/{today}/{item_code1}/{item_code2}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
            return data["StatisticSearch"]["row"]
        return []
    except Exception as e:
        # 에러 발생 시 API 키가 로그에 노출되지 않도록 처리
        print(f"⚠️ {stat_code}-{item_code1} 지표 데이터 요청 중 오류가 발생했습니다.")
        return []

def main():
    table_data = defaultdict(dict)
    
    # 1. 모든 지표 데이터 받아와서 재구조화
    for stat_code, item_code1, item_code2, name in TARGET_INDICATORS:
        rows = get_ecos_history(stat_code, item_code1, item_code2)
        for row in rows:
            date = row['TIME']       # YYYYMMDD 형태
            value = row['DATA_VALUE']
            table_data[date][name] = value

    if not table_data:
        print("❌ 가져온 데이터가 전혀 없습니다. GitHub Secrets에 등록된 API 키가 올바른지 확인해 주세요.")
        return

    # 2. 데이터가 있는 날짜들을 오름차순 정렬
    sorted_dates = sorted(table_data.keys())
    
    # 3. 최근 10영업일만 추출
    recent_10_dates = sorted_dates[-10:]

    # 4. 표 형태로 출력
    print("==========================================================================================")
    print("                      [최근 10 영업일 금융 지표 동향 (오름차순)]")
    print("==========================================================================================")
    
    # 헤더 출력
    header = f"{'날짜':<12}"
    for _, _, _, name in TARGET_INDICATORS:
        header += f"{name:>12}"
    print(header)
    print("-" * len(header))
    
    # 데이터 행 출력
    for date in recent_10_dates:
        formatted_date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
        row_str = f"{formatted_date:<12}"
        
        for _, _, _, name in TARGET_INDICATORS:
            val = table_data[date].get(name, "-")
            try:
                row_str += f"{float(val):>12.2f}"
            except ValueError:
                row_str += f"{val:>12}"
                
        print(row_str)
        
    print("==========================================================================================")

if __name__ == "__main__":
    main()
