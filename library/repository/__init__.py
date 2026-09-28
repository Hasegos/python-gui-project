# Repository 계층: 테이블별 SQL 실행을 담당한다.
# 모든 함수는 transaction() 이 넘겨준 커서를 첫 인자로 받고,
# 트랜잭션 경계(commit/rollback)는 Service 계층에서 결정한다.


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
