from library.repository import like_pattern

# 대출자별 현재 대출중 / 연체 권수를 함께 조회
_SELECT_MEMBER = """
    SELECT m.member_id, m.student_no, m.name, m.department, m.phone, m.email,
           COALESCE(l.on_loan, 0) AS on_loan,
           COALESCE(l.overdue, 0) AS overdue
    FROM member m
    LEFT JOIN (
        SELECT member_id,
               COUNT(*) AS on_loan,
               COUNT(*) FILTER (WHERE due_date < CURRENT_DATE) AS overdue
        FROM loan
        WHERE return_date IS NULL
        GROUP BY member_id
    ) l ON l.member_id = m.member_id
"""

# 검색 기준 → 컬럼 (화이트리스트)
SEARCH_COLUMNS = {
    "student_no": "m.student_no",
    "name": "m.name",
    "department": "m.department",
    "phone": "m.phone",
}


# ─────────────────────────────────────
# 1. 대출자 목록 조회 (검색)
# ─────────────────────────────────────
def find_all(cur, keyword: str = "", field: str = "all") -> list[dict]:
    """
    대출자 목록을 대출중/연체 권수와 함께 조회한다.

    Args:
        cur    : DB 커서
        keyword: 검색어. 비어 있으면 전체 조회.
        field  : 검색 기준 (student_no, name, department, phone, all)
    Returns:
        대출자 dict 리스트 (member_id 오름차순)
    """
    sql = _SELECT_MEMBER
    params: list = []
    if keyword:
        columns = [SEARCH_COLUMNS[field]] if field in SEARCH_COLUMNS else SEARCH_COLUMNS.values()
        sql += " WHERE " + " OR ".join(f"{col} ILIKE %s" for col in columns)
        params = [like_pattern(keyword)] * len(columns)
    sql += " ORDER BY m.member_id"
    cur.execute(sql, params)
    return cur.fetchall()


# ─────────────────────────────────────
# 2. 대출자 단건 조회
# ─────────────────────────────────────
def find_by_id(cur, member_id: int) -> dict | None:
    """
    member_id 로 대출자를 조회한다.

    Args:
        cur      : DB 커서
        member_id: 조회할 대출자 PK
    Returns:
        대출자 dict. 없으면 None.
    """
    cur.execute(_SELECT_MEMBER + " WHERE m.member_id = %s", (member_id,))
    return cur.fetchone()


# ─────────────────────────────────────
# 3. 대출자 행 잠금
# ─────────────────────────────────────
def lock_by_id(cur, member_id: int) -> dict | None:
    """
    대출/수정/삭제 동시 처리를 막기 위해 대출자 행에 배타 잠금(FOR UPDATE)을 건다.

    Args:
        cur      : DB 커서
        member_id: 잠글 대출자 PK
    Returns:
        {member_id, student_no, name} dict. 없으면 None.
    """
    cur.execute(
        "SELECT member_id, student_no, name FROM member WHERE member_id = %s FOR UPDATE",
        (member_id,),
    )
    return cur.fetchone()


# ─────────────────────────────────────
# 4. 대출중 권수 조회
# ─────────────────────────────────────
def count_on_loan(cur, member_id: int) -> int:
    """
    대출자의 미반납 대출 건수를 조회한다.

    Args:
        cur      : DB 커서
        member_id: 대출자 PK
    Returns:
        대출중 권수
    """
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM loan WHERE member_id = %s AND return_date IS NULL",
        (member_id,),
    )
    return cur.fetchone()["cnt"]


# ─────────────────────────────────────
# 5. 대출자 등록
# ─────────────────────────────────────
def insert(cur, data: dict) -> int:
    """
    대출자를 등록한다.

    Args:
        cur : DB 커서
        data: 검증된 대출자 정보 dict
    Returns:
        생성된 member_id
    """
    cur.execute(
        """
        INSERT INTO member (student_no, name, department, phone, email)
        VALUES (%(student_no)s, %(name)s, %(department)s, %(phone)s, %(email)s)
        RETURNING member_id
        """,
        data,
    )
    return cur.fetchone()["member_id"]


# ─────────────────────────────────────
# 6. 대출자 수정
# ─────────────────────────────────────
def update(cur, member_id: int, data: dict) -> None:
    """
    대출자 정보를 수정하고 updated_at 을 갱신한다.

    Args:
        cur      : DB 커서
        member_id: 수정할 대출자 PK
        data     : 검증된 대출자 정보 dict
    """
    cur.execute(
        """
        UPDATE member
        SET student_no = %(student_no)s, name = %(name)s, department = %(department)s,
            phone = %(phone)s, email = %(email)s, updated_at = CURRENT_TIMESTAMP
        WHERE member_id = %(member_id)s
        """,
        {**data, "member_id": member_id},
    )


# ─────────────────────────────────────
# 7. 대출자 삭제
# ─────────────────────────────────────
def delete(cur, member_id: int) -> None:
    """
    대출자를 삭제한다. 대출 이력은 FK(ON DELETE CASCADE)로 함께 삭제된다.

    Args:
        cur      : DB 커서
        member_id: 삭제할 대출자 PK
    """
    cur.execute("DELETE FROM member WHERE member_id = %s", (member_id,))


# ─────────────────────────────────────
# 8. 학과 목록 조회
# ─────────────────────────────────────
def find_departments(cur) -> list[str]:
    """
    등록된 대출자의 학과 목록을 중복 없이 조회한다. (입력 폼 Combobox 용)

    Args:
        cur: DB 커서
    Returns:
        학과 문자열 리스트 (가나다순)
    """
    cur.execute(
        "SELECT DISTINCT department FROM member WHERE department IS NOT NULL ORDER BY department"
    )
    return [row["department"] for row in cur.fetchall()]
