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
    """현재 날짜를 기준으로 한국은행 공식 주소(ecos.bok.or.kr)로 데이터를 요청합니다."""
    today = datetime.now().strftime("%Y%m%d")
    start_date = f"{datetime.now().year}0101"
    
    # 한국은행 공식 도메인을 명확하게 분리하여 주소 조립
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
        # 에러 발생 시 주소가 어떻게 조립되었는지 눈으로 확인할 수 있도록 출력 (보안 처리)
        safe_url = url.replace(str(API_KEY), "YOUR_SECRET_KEY")
        print(f"⚠️ 데이터 요청 실패 ({stat_code}-{item_code1})")
        print(f"🔗 요청 주소 확인: {safe_url}")
        print(f"❌ 에러 메시지: {e}\n")
        return []

def main():
    print("🔄 한국은행 API로부터 데이터를 가져오는 중입니다...\n")
    table_data = defaultdict(dict)
    
    # 1. 모든 지표 데이터 받아와서 재구조화
    for stat_code, item_code1, item_code2, name in TARGET_INDICATORS:
        rows = get_ecos_history(stat_code, item_code1, item_code2)
        for row in rows:
            date = row['TIME']       
            value = row['DATA_VALUE']
            table_data[date][name] = value

    if not table_data:
        print("❌ [최종 실패] 가져온 데이터가 전혀 없습니다.")
        print("💡 원인 1: 파이썬 파일이 정상적으로 커밋(저장)되지 않아 예전 오류 코드가 실행됨")
        print("💡 원인 2: GitHub Secrets에 저장된 API 키 값에 공백이나 잘못된 문자가 포함됨")
        return

    # 2. 데이터가 있는 날짜들을 오름차순 정렬
    sorted_dates = sorted(table_data.keys())
    recent_10_dates = sorted_dates[-10:]

    # 3. 표 형태로 출력
    print("==========================================================================================")
    print("                      [최근 10 영업일 금융 지표 동향 (오름차순)]")
    print("==========================================================================================")
    
    header = f"{'날짜':<12}"
    for _, _, _, name in TARGET_INDICATORS:
        header += f"{name:>12}"
    print(header)
    print("-" * len(header))
    
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
