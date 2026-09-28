# ─────────────────────────────────────
# 1. LIKE 검색 패턴 생성
# ─────────────────────────────────────
def like_pattern(keyword: str) -> str:
    """
    ILIKE 부분 일치 검색용 패턴을 만든다.

    검색어에 포함된 와일드카드 문자(%, _)는 이스케이프하여 문자 그대로 검색한다.

    Args:
        keyword: 사용자가 입력한 검색어
    Returns:
        '%검색어%' 형태의 패턴 문자열
    """
    escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


# ─────────────────────────────────────
# 2. 검색 조건 WHERE 절 생성
# ─────────────────────────────────────
def keyword_condition(keyword: str, field: str, columns: dict) -> tuple[str, list]:
    """
    검색어와 검색 기준으로 WHERE 조건식과 바인딩 파라미터를 만든다.

    컬럼명은 화이트리스트(columns)에서만 가져오므로 SQL Injection 위험이 없다.

    Args:
        keyword: 검색어. 비어 있으면 조건 없음.
        field  : 검색 기준 키. columns 에 없으면 전체 컬럼 OR 검색.
        columns: {검색 기준 키: 컬럼명} 화이트리스트
    Returns:
        (조건식 문자열, 파라미터 리스트). 검색어가 없으면 ("", []).
    """
    if not keyword:
        return "", []
    targets = [columns[field]] if field in columns else list(columns.values())
    condition = "(" + " OR ".join(f"{col} ILIKE %s" for col in targets) + ")"
    return condition, [like_pattern(keyword)] * len(targets)
