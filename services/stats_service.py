from core.constants.loan import STATS_MONTHS, STATS_TOP_N
from crud import stats_crud
from db.session import transaction
from schemas.stats_schema import StatsDashboard


# ─────────────────────────────────────
# 1. 통계 대시보드 조회
# ─────────────────────────────────────
def get_dashboard(months: int = STATS_MONTHS, top: int = STATS_TOP_N) -> StatsDashboard:
    """
    통계 화면에 필요한 집계를 한 번에 조회한다.

    여러 집계 쿼리가 같은 시점의 데이터를 보도록 REPEATABLE READ 읽기 전용 트랜잭션으로 실행한다.

    Args:
        months: 월별 추이 개월 수
        top   : 인기 도서/다독 대출자 순위 개수
    Returns:
        StatsDashboard 객체
    """
    with transaction() as cur:
        # 트랜잭션의 첫 쿼리여야 격리 수준이 적용된다.
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        return StatsDashboard(
            summary=stats_crud.get_summary(cur),
            monthly=stats_crud.get_monthly_counts(cur, months),
            top_books=stats_crud.get_top_books(cur, top),
            top_members=stats_crud.get_top_members(cur, top),
            categories=stats_crud.get_category_stats(cur),
        )
