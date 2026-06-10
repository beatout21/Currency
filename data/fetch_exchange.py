import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .env 로드 → 환경변수에 API 키 저장
load_dotenv()
API_KEY = os.getenv("KB_API_KEY")
if not API_KEY:
    raise ValueError("KB_API_KEY 가 .env 에 정의되지 않았습니다.")

# --------------------------------------------------------------
# 1) 한국은행 환율 통계코드·항목코드
# --------------------------------------------------------------
# 한국은행 통계검색 페이지에서 확인한 코드
STAT_CODE = "200Y001"          # “외환시세(시초가·종가·고가·저가)” 통계코드
# 항목코드(통화별) – 001 은 시초가(시작가) 를 의미합니다.
# 100엔은 “JPY(100엔)” 로 별도 항목코드가 존재합니다.
ITEM_CODES = {
    "USD": "001",   # 미국 달러 시초가
    "EUR": "002",   # 유로 시초가
    "JPY": "003",   # 엔화(100엔) 시초가
    "CNY": "004",   # 위안화 시초가
}
# --------------------------------------------------------------

def _build_url(item_code: str, start_date: str, end_date: str) -> str:
    """
    한국은행 StatisticSearch API URL 생성
    - format : json
    - period : D (일별)
    """
    base = "https://ecos.bok.or.kr/api/StatisticSearch"
    # 일별(D) → period 파라미터에 “D” 를 넣는다.
    return f"{base}/{API_KEY}/json/{start_date}/{end_date}/{STAT_CODE}/{item_code}/D"

def _request(url: str) -> pd.DataFrame:
    """API 호출 → JSON 파싱 → DataFrame 반환"""
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # JSON 구조: {"StatisticSearch": {"row": [{...}, {...}]}}
    rows = data.get("StatisticSearch", {}).get("row", [])
    if not rows:
        return pd.DataFrame()   # 빈 DataFrame 반환

    df = pd.DataFrame(rows)

    # 컬럼명 통일 (API마다 다소 차이)
    #   TIME   : 일자 (YYYYMMDD)
    #   DATA_VALUE : 시초가(숫자)
    df = df.rename(columns={"TIME": "DATE", "DATA_VALUE": "RATE"})
    df["DATE"] = pd.to_datetime(df["DATE"], format="%Y%m%d")
    df["RATE"] = pd.to_numeric(df["RATE"], errors="coerce")
    return df[["DATE", "RATE"]]

def get_recent_week_rates() -> pd.DataFrame:
    """
    최근 7일(오늘 포함) 동안 USD/EUR/JPY(100엔)/CNY 의 원화 대비 시초가를
    하나의 DataFrame 으로 반환.
    반환 형태:
        DATE   | USD | EUR | JPY | CNY
    """
    today = datetime.now().date()
    start = today - timedelta(days=6)   # 7일 구간 (오늘 포함)
    start_str = start.strftime("%Y%m%d")
    end_str   = today.strftime("%Y%m%d")

    # 각 통화별 DataFrame을 받아서 피벗(pivot) 형태로 합침
    dfs = []
    for cur, item_code in ITEM_CODES.items():
        url = _build_url(item_code, start_str, end_str)
        df = _request(url)
        df = df.rename(columns={"RATE": cur})
        dfs.append(df)

    # 날짜를 기준으로 외부 조인
    merged = dfs[0]
    for df in dfs[1:]:
        merged = pd.merge(merged, df, on="DATE", how="outer")

    merged = merged.sort_values("DATE").reset_index(drop=True)
    return merged

# -----------------------------------------------------------------
# 테스트용 실행 (스크립트 직접 실행 시)
# -----------------------------------------------------------------
if __name__ == "__main__":
    df_week = get_recent_week_rates()
    print(df_week)
