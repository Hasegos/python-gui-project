from schemas.stats_schema import (
    CategoryStat,
    MonthlyCount,
    StatsSummary,
    TopBook,
    TopMember,
)


# ─────────────────────────────────────
# 1. 요약 지표
# ─────────────────────────────────────
def get_summary(cur) -> StatsSummary:
    """
    통계 화면 상단 요약 카드에 필요한 지표를 한 번에 집계한다.

    Args:
        cur: DB 커서
    Returns:
        StatsSummary 객체
    """
    cur.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM book)                                   AS book_titles,
            (SELECT COALESCE(SUM(quantity), 0) FROM book)                 AS book_copies,
            (SELECT COUNT(*) FROM member)                                 AS members,
            (SELECT COUNT(*) FROM loan)                                   AS total_loans,
            (SELECT COUNT(*) FROM loan WHERE return_date IS NULL)         AS not_returned,
            (SELECT COUNT(*) FROM loan
              WHERE return_date IS NULL AND due_date < CURRENT_DATE)      AS overdue,
            (SELECT COUNT(*) FROM loan
              WHERE return_date IS NOT NULL AND return_date > due_date)   AS late_returns,
            (SELECT COUNT(*) FROM loan WHERE return_date IS NOT NULL)     AS returned
        """
    )
    return StatsSummary(**cur.fetchone())


# ─────────────────────────────────────
# 2. 월별 대출/반납 건수
# ─────────────────────────────────────
def get_monthly_counts(cur, months: int) -> list[MonthlyCount]:
    """
    최근 N개월(이번 달 포함) 월별 대출/반납 건수를 집계한다.

    generate_series 로 월 목록을 먼저 만들어 기록이 없는 달도 0건으로 채운다.

    Args:
        cur   : DB 커서
        months: 집계할 개월 수
    Returns:
        MonthlyCount 리스트 (오래된 달부터)
    """
    cur.execute(
        """
        WITH month_range AS (
            SELECT generate_series(
                date_trunc('month', CURRENT_DATE) - make_interval(months => %(months)s - 1),
                date_trunc('month', CURRENT_DATE),
                interval '1 month'
            )::date AS month
        )
        SELECT to_char(r.month, 'YYYY-MM') AS month,
               (SELECT COUNT(*) FROM loan
                 WHERE date_trunc('month', loan_date) = r.month)   AS loans,
               (SELECT COUNT(*) FROM loan
                 WHERE date_trunc('month', return_date) = r.month) AS returns
        FROM month_range r
        ORDER BY r.month
        """,
        {"months": months},
    )
    return [MonthlyCount(**row) for row in cur.fetchall()]


# ─────────────────────────────────────
# 3. 인기 도서 순위
# ─────────────────────────────────────
def get_top_books(cur, limit: int) -> list[TopBook]:
    """
    누적 대출 건수가 많은 도서 순위를 조회한다. (동점은 같은 순위)

    Args:
        cur  : DB 커서
        limit: 조회할 개수
    Returns:
        TopBook 리스트
    """
    cur.execute(
        """
        SELECT RANK() OVER (ORDER BY COUNT(*) DESC) AS rank,
               b.title, b.author, COUNT(*) AS loan_count
        FROM loan l
        JOIN book b ON b.book_id = l.book_id
        GROUP BY b.book_id, b.title, b.author
        ORDER BY loan_count DESC, b.title
        LIMIT %s
        """,
        (limit,),
    )
    return [TopBook(**row) for row in cur.fetchall()]


# ─────────────────────────────────────
# 4. 다독 대출자 순위
# ─────────────────────────────────────
def get_top_members(cur, limit: int) -> list[TopMember]:
    """
    누적 대출 건수가 많은 대출자 순위를 조회한다. (동점은 같은 순위)

    Args:
        cur  : DB 커서
        limit: 조회할 개수
    Returns:
        TopMember 리스트
    """
    cur.execute(
        """
        SELECT RANK() OVER (ORDER BY COUNT(*) DESC) AS rank,
               m.student_no, m.name, m.department, COUNT(*) AS loan_count
        FROM loan l
        JOIN member m ON m.member_id = l.member_id
        GROUP BY m.member_id, m.student_no, m.name, m.department
        ORDER BY loan_count DESC, m.name
        LIMIT %s
        """,
        (limit,),
    )
    return [TopMember(**row) for row in cur.fetchall()]


# ─────────────────────────────────────
# 5. 분류별 통계
# ─────────────────────────────────────
def get_category_stats(cur) -> list[CategoryStat]:
    """
    분류별 도서 종수와 누적 대출 건수를 집계한다. 분류가 없으면 '미분류'로 묶는다.

    Args:
        cur: DB 커서
    Returns:
        CategoryStat 리스트 (대출 많은 순)
    """
    cur.execute(
        """
        SELECT COALESCE(b.category, '미분류') AS category,
               COUNT(DISTINCT b.book_id)   AS book_titles,
               COUNT(l.loan_id)            AS loan_count
        FROM book b
        LEFT JOIN loan l ON l.book_id = b.book_id
        GROUP BY COALESCE(b.category, '미분류')
        ORDER BY loan_count DESC, category
        """
    )
    return [CategoryStat(**row) for row in cur.fetchall()]
