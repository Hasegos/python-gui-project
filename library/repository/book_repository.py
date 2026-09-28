from library.repository import like_pattern

# 대출 가능 권수 = 보유 권수 - 미반납 대출 건수
_SELECT_BOOK = """
    SELECT b.book_id, b.isbn, b.title, b.author, b.publisher,
           b.published_year, b.category, b.quantity,
           b.quantity - COALESCE(l.on_loan, 0) AS available
    FROM book b
    LEFT JOIN (
        SELECT book_id, COUNT(*) AS on_loan
        FROM loan
        WHERE return_date IS NULL
        GROUP BY book_id
    ) l ON l.book_id = b.book_id
"""

# 검색 기준 → 컬럼 (화면에서 넘어온 값을 그대로 SQL 에 넣지 않도록 화이트리스트로 관리)
SEARCH_COLUMNS = {
    "title": "b.title",
    "author": "b.author",
    "isbn": "b.isbn",
    "publisher": "b.publisher",
    "category": "b.category",
}


# ─────────────────────────────────────
# 1. 도서 목록 조회 (검색)
# ─────────────────────────────────────
def find_all(cur, keyword: str = "", field: str = "all") -> list[dict]:
    """
    도서 목록을 대출 가능 권수와 함께 조회한다.

    Args:
        cur    : DB 커서
        keyword: 검색어. 비어 있으면 전체 조회.
        field  : 검색 기준 (title, author, isbn, publisher, category, all)
    Returns:
        도서 dict 리스트 (book_id 오름차순)
    """
    sql = _SELECT_BOOK
    params: list = []
    if keyword:
        columns = [SEARCH_COLUMNS[field]] if field in SEARCH_COLUMNS else SEARCH_COLUMNS.values()
        sql += " WHERE " + " OR ".join(f"{col} ILIKE %s" for col in columns)
        params = [like_pattern(keyword)] * len(columns)
    sql += " ORDER BY b.book_id"
    cur.execute(sql, params)
    return cur.fetchall()


# ─────────────────────────────────────
# 2. 도서 단건 조회
# ─────────────────────────────────────
def find_by_id(cur, book_id: int) -> dict | None:
    """
    book_id 로 도서를 조회한다.

    Args:
        cur    : DB 커서
        book_id: 조회할 도서 PK
    Returns:
        도서 dict. 없으면 None.
    """
    cur.execute(_SELECT_BOOK + " WHERE b.book_id = %s", (book_id,))
    return cur.fetchone()


# ─────────────────────────────────────
# 3. 도서 행 잠금
# ─────────────────────────────────────
def lock_by_id(cur, book_id: int) -> dict | None:
    """
    대출/수정/삭제 동시 처리를 막기 위해 도서 행에 배타 잠금(FOR UPDATE)을 건다.

    잠금은 트랜잭션이 끝날 때(commit/rollback) 해제된다.

    Args:
        cur    : DB 커서
        book_id: 잠글 도서 PK
    Returns:
        {book_id, title, quantity} dict. 없으면 None.
    """
    cur.execute("SELECT book_id, title, quantity FROM book WHERE book_id = %s FOR UPDATE", (book_id,))
    return cur.fetchone()


# ─────────────────────────────────────
# 4. 대출중 권수 조회
# ─────────────────────────────────────
def count_on_loan(cur, book_id: int) -> int:
    """
    도서의 미반납 대출 건수를 조회한다.

    Args:
        cur    : DB 커서
        book_id: 도서 PK
    Returns:
        대출중 권수
    """
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM loan WHERE book_id = %s AND return_date IS NULL",
        (book_id,),
    )
    return cur.fetchone()["cnt"]


# ─────────────────────────────────────
# 5. 도서 등록
# ─────────────────────────────────────
def insert(cur, data: dict) -> int:
    """
    도서를 등록한다.

    Args:
        cur : DB 커서
        data: 검증된 도서 정보 dict
    Returns:
        생성된 book_id
    """
    cur.execute(
        """
        INSERT INTO book (isbn, title, author, publisher, published_year, category, quantity)
        VALUES (%(isbn)s, %(title)s, %(author)s, %(publisher)s,
                %(published_year)s, %(category)s, %(quantity)s)
        RETURNING book_id
        """,
        data,
    )
    return cur.fetchone()["book_id"]


# ─────────────────────────────────────
# 6. 도서 수정
# ─────────────────────────────────────
def update(cur, book_id: int, data: dict) -> None:
    """
    도서 정보를 수정하고 updated_at 을 갱신한다.

    Args:
        cur    : DB 커서
        book_id: 수정할 도서 PK
        data   : 검증된 도서 정보 dict
    """
    cur.execute(
        """
        UPDATE book
        SET isbn = %(isbn)s, title = %(title)s, author = %(author)s,
            publisher = %(publisher)s, published_year = %(published_year)s,
            category = %(category)s, quantity = %(quantity)s,
            updated_at = CURRENT_TIMESTAMP
        WHERE book_id = %(book_id)s
        """,
        {**data, "book_id": book_id},
    )


# ─────────────────────────────────────
# 7. 도서 삭제
# ─────────────────────────────────────
def delete(cur, book_id: int) -> None:
    """
    도서를 삭제한다. 대출 이력은 FK(ON DELETE CASCADE)로 함께 삭제된다.

    Args:
        cur    : DB 커서
        book_id: 삭제할 도서 PK
    """
    cur.execute("DELETE FROM book WHERE book_id = %s", (book_id,))


# ─────────────────────────────────────
# 8. 분류 목록 조회
# ─────────────────────────────────────
def find_categories(cur) -> list[str]:
    """
    등록된 도서의 분류 목록을 중복 없이 조회한다. (입력 폼 Combobox 용)

    Args:
        cur: DB 커서
    Returns:
        분류 문자열 리스트 (가나다순)
    """
    cur.execute(
        "SELECT DISTINCT category FROM book WHERE category IS NOT NULL ORDER BY category"
    )
    return [row["category"] for row in cur.fetchall()]
