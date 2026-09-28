from library.db import transaction
from library.repository import stats_repository


# ─────────────────────────────────────
# 1. 통계 대시보드 조회
# ─────────────────────────────────────
def get_dashboard(months: int = 6, top: int = 5) -> dict:
    """
    통계 화면에 필요한 집계를 한 번에 조회한다.

    여러 집계 쿼리가 같은 시점의 데이터를 보도록 REPEATABLE READ 읽기 전용 트랜잭션으로 실행한다.

    Args:
        months: 월별 추이 개월 수
        top   : 인기 도서/다독 대출자 순위 개수
    Returns:
        {summary, monthly, top_books, top_members, categories} dict
    """
    with transaction() as cur:
        # 트랜잭션의 첫 쿼리여야 격리 수준이 적용된다.
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return {
            "summary": stats_repository.summary(cur),
            "monthly": stats_repository.monthly_counts(cur, months),
            "top_books": stats_repository.top_books(cur, top),
            "top_members": stats_repository.top_members(cur, top),
            "categories": stats_repository.category_stats(cur),
        }
