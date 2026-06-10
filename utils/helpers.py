def format_number(x):
    """소수점 4자리까지 표시하고, 천 단위 구분 기호 삽입"""
    if pd.isna(x):
        return "-"
    return f"{x:,.4f}"
