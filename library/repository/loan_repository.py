from library.repository import like_pattern

# 대출 상태는 저장하지 않고 조회 시점 기준으로 계산한다.
STATUS_SQL = """
    CASE
        WHEN l.return_date IS NOT NULL THEN '반납완료'
        WHEN l.due_date < CURRENT_DATE THEN '연체'
        ELSE '대출중'
    END
"""

# 상태 필터 → WHERE 조건 (화이트리스트)
STATUS_FILTERS = {
    "all": "TRUE",
    "not_returned": "l.return_date IS NULL",
    "on_loan": "l.return_date IS NULL AND l.due_date >= CURRENT_DATE",
    "overdue": "l.return_date IS NULL AND l.due_date < CURRENT_DATE",
    "returned": "l.return_date IS NOT NULL",
}

# 연체일수 = (반납일 또는 오늘) - 반납 예정일, 음수면 0
_SELECT_LOAN = f"""
    SELECT l.loan_id, l.book_id, b.title, b.author,
           l.member_id, m.student_no, m.name,
           l.loan_date, l.due_date, l.return_date,
           {STATUS_SQL} AS status,
           GREATEST(COALESCE(l.return_date, CURRENT_DATE) - l.due_date, 0) AS overdue_days
    FROM loan l
    JOIN book b ON b.book_id = l.book_id
    JOIN member m ON m.member_id = l.member_id
"""


# ─────────────────────────────────────
# 1. 대출 기록 조회 (상태 필터 + 검색)
# ─────────────────────────────────────
def find_all(cur, status: str = "all", keyword: str = "") -> list[dict]:
    """
    대출 기록을 상태/연체일수와 함께 조회한다.

    Args:
        cur    : DB 커서
        status : 상태 필터 (all, not_returned, on_loan, overdue, returned)
        keyword: 도서명/이름/학번 검색어. 비어 있으면 필터만 적용.
    Returns:
        대출 기록 dict 리스트 (미반납 우선, 반납 예정일 빠른 순)
    """
    sql = _SELECT_LOAN + " WHERE " + STATUS_FILTERS.get(status, "TRUE")
    params: list = []
    if keyword:
        sql += " AND (b.title ILIKE %s OR m.name ILIKE %s OR m.student_no ILIKE %s)"
        params = [like_pattern(keyword)] * 3
    sql += " ORDER BY (l.return_date IS NOT NULL), l.due_date, l.loan_id DESC"
    cur.execute(sql, params)
    return cur.fetchall()


# ─────────────────────────────────────
# 2. 상태별 건수 집계
# ─────────────────────────────────────
def count_by_status(cur) -> dict:
    """
    전체 대출 기록의 상태별 건수를 집계한다.

    Args:
        cur: DB 커서
    Returns:
        {on_loan, overdue, returned} dict
    """
    cur.execute(
        """
        SELECT COUNT(*) FILTER (WHERE return_date IS NULL AND due_date >= CURRENT_DATE) AS on_loan,
               COUNT(*) FILTER (WHERE return_date IS NULL AND due_date < CURRENT_DATE)  AS overdue,
               COUNT(*) FILTER (WHERE return_date IS NOT NULL)                          AS returned
        FROM loan
        """
    )
    return cur.fetchone()


# ─────────────────────────────────────
# 3. 대출자별 미반납/연체 권수
# ─────────────────────────────────────
def count_member_loans(cur, member_id: int) -> dict:
    """
    대출자의 미반납 권수와 그중 연체 권수를 조회한다. (대출 가능 여부 판단용)

    Args:
        cur      : DB 커서
        member_id: 대출자 PK
    Returns:
        {on_loan, overdue} dict
    """
    cur.execute(
        """
        SELECT COUNT(*) AS on_loan,
               COUNT(*) FILTER (WHERE due_date < CURRENT_DATE) AS overdue
        FROM loan
        WHERE member_id = %s AND return_date IS NULL
        """,
        (member_id,),
    )
    return cur.fetchone()


# ─────────────────────────────────────
# 4. 동일 도서 미반납 여부
# ─────────────────────────────────────
def exists_not_returned(cur, book_id: int, member_id: int) -> bool:
    """
    대출자가 같은 도서를 반납하지 않은 채 대출중인지 확인한다.

    Args:
        cur      : DB 커서
        book_id  : 도서 PK
        member_id: 대출자 PK
    Returns:
        미반납 대출이 있으면 True
    """
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM loan
            WHERE book_id = %s AND member_id = %s AND return_date IS NULL
        ) AS found
        """,
        (book_id, member_id),
    )
    return cur.fetchone()["found"]


# ─────────────────────────────────────
# 5. 대출 등록
# ─────────────────────────────────────
def insert(cur, book_id: int, member_id: int, loan_days: int) -> dict:
    """
    대출 기록을 등록한다. 대출일/반납 예정일은 DB 날짜(CURRENT_DATE) 기준으로 계산한다.

    Args:
        cur      : DB 커서
        book_id  : 도서 PK
        member_id: 대출자 PK
        loan_days: 대출 기간 (일)
    Returns:
        {loan_id, due_date} dict
    """
    cur.execute(
        """
        INSERT INTO loan (book_id, member_id, loan_date, due_date)
        VALUES (%s, %s, CURRENT_DATE, CURRENT_DATE + %s)
        RETURNING loan_id, due_date
        """,
        (book_id, member_id, loan_days),
    )
    return cur.fetchone()


# ─────────────────────────────────────
# 6. 대출 기록 행 잠금
# ─────────────────────────────────────
def lock_by_id(cur, loan_id: int) -> dict | None:
    """
    중복 반납 처리를 막기 위해 대출 기록 행에 배타 잠금(FOR UPDATE)을 건다.

    Args:
        cur    : DB 커서
        loan_id: 대출 기록 PK
    Returns:
        {loan_id, return_date, due_date, title, name} dict. 없으면 None.
    """
    cur.execute(
        """
        SELECT l.loan_id, l.return_date, l.due_date, b.title, m.name
        FROM loan l
        JOIN book b ON b.book_id = l.book_id
        JOIN member m ON m.member_id = l.member_id
        WHERE l.loan_id = %s
        FOR UPDATE OF l
        """,
        (loan_id,),
    )
    return cur.fetchone()


# ─────────────────────────────────────
# 7. 반납 처리
# ─────────────────────────────────────
def mark_returned(cur, loan_id: int) -> dict:
    """
    반납일을 오늘로 기록한다.

    Args:
        cur    : DB 커서
        loan_id: 대출 기록 PK
    Returns:
        {return_date, overdue_days} dict
    """
    cur.execute(
        """
        UPDATE loan
        SET return_date = CURRENT_DATE
        WHERE loan_id = %s
        RETURNING return_date, GREATEST(return_date - due_date, 0) AS overdue_days
        """,
        (loan_id,),
    )
    return cur.fetchone()
