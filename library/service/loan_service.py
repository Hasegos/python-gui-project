from library import config
from library.db import transaction
from library.exceptions import LibraryError, NotFoundError
from library.repository import book_repository, loan_repository, member_repository
from library.service import parse_int


# ─────────────────────────────────────
# 1. 대출 기록 검색
# ─────────────────────────────────────
def search_loans(status: str = "all", keyword: str = "") -> list[dict]:
    """
    대출 기록을 상태 필터와 검색어로 조회한다.

    Args:
        status : 상태 필터 (all, not_returned, on_loan, overdue, returned)
        keyword: 도서명/이름/학번 검색어
    Returns:
        대출 기록 dict 리스트
    """
    with transaction() as cur:
        return loan_repository.find_all(cur, status, keyword.strip())


# ─────────────────────────────────────
# 2. 상태별 건수 조회
# ─────────────────────────────────────
def get_status_counts() -> dict:
    """
    전체 대출 기록의 상태별 건수를 조회한다.

    Returns:
        {on_loan, overdue, returned} dict
    """
    with transaction() as cur:
        return loan_repository.count_by_status(cur)


# ─────────────────────────────────────
# 3. 대출 가능 도서 목록
# ─────────────────────────────────────
def get_borrowable_books() -> list[dict]:
    """
    대출 가능 권수가 남아 있는 도서 목록을 조회한다. (대출 도서 선택 Combobox 용)

    Returns:
        도서 dict 리스트
    """
    with transaction() as cur:
        return [book for book in book_repository.find_all(cur) if book["available"] > 0]


# ─────────────────────────────────────
# 4. 대출자 목록
# ─────────────────────────────────────
def get_members() -> list[dict]:
    """
    전체 대출자 목록을 조회한다. (대출자 선택 Combobox 용)

    Returns:
        대출자 dict 리스트
    """
    with transaction() as cur:
        return member_repository.find_all(cur)


# ─────────────────────────────────────
# 5. 대출 처리
# ─────────────────────────────────────
def borrow_book(book_id: int, member_id: int, loan_days=None) -> dict:
    """
    도서를 대출한다.

    하나의 트랜잭션 안에서 도서/대출자 행을 잠근 뒤 대출 가능 여부를 검사하고 기록을 남긴다.
    잠금 순서는 항상 book → member 로 고정하여 교착 상태(Deadlock)를 방지한다.

    Args:
        book_id  : 대출할 도서 PK
        member_id: 대출자 PK
        loan_days: 대출 기간 (일). 비어 있으면 config.LOAN_DAYS
    Returns:
        {loan_id, due_date, title, name} dict
    Raises:
        NotFoundError: 도서/대출자가 없을 때
        LibraryError : 연체 도서 보유, 대출 한도 초과, 중복 대출, 재고 부족 시
    """
    days = parse_int(loan_days, "대출 기간", minimum=1, maximum=90) or config.LOAN_DAYS

    with transaction() as cur:
        # ─────────────────────────────────
        # 5-1. 도서 → 대출자 순서로 행 잠금
        # ─────────────────────────────────
        book = book_repository.lock_by_id(cur, book_id)
        if book is None:
            raise NotFoundError("존재하지 않는 도서입니다. 목록을 새로고침해 주세요.")
        member = member_repository.lock_by_id(cur, member_id)
        if member is None:
            raise NotFoundError("존재하지 않는 대출자입니다. 목록을 새로고침해 주세요.")

        # ─────────────────────────────────
        # 5-2. 대출자 조건 검사 (연체, 한도, 중복)
        # ─────────────────────────────────
        member_loans = loan_repository.count_member_loans(cur, member_id)
        if member_loans["overdue"]:
            raise LibraryError(
                f"{member['name']} 님은 연체중인 도서가 {member_loans['overdue']}권 있어 대출할 수 없습니다.\n"
                "연체 도서를 먼저 반납해 주세요."
            )
        if member_loans["on_loan"] >= config.MAX_LOANS_PER_MEMBER:
            raise LibraryError(
                f"{member['name']} 님은 이미 최대 대출 권수({config.MAX_LOANS_PER_MEMBER}권)를 대출중입니다."
            )
        if loan_repository.exists_not_returned(cur, book_id, member_id):
            raise LibraryError(f"{member['name']} 님은 '{book['title']}' 을(를) 이미 대출중입니다.")

        # ─────────────────────────────────
        # 5-3. 재고 검사 후 대출 기록 등록
        # ─────────────────────────────────
        on_loan = book_repository.count_on_loan(cur, book_id)
        if on_loan >= book["quantity"]:
            raise LibraryError(f"'{book['title']}' 은(는) 대출 가능한 재고가 없습니다.")

        loan = loan_repository.insert(cur, book_id, member_id, days)

    return {**loan, "title": book["title"], "name": member["name"]}


# ─────────────────────────────────────
# 6. 반납 처리
# ─────────────────────────────────────
def return_book(loan_id: int) -> dict:
    """
    대출 기록을 반납 처리한다. 이미 반납된 기록은 다시 처리하지 않는다.

    Args:
        loan_id: 대출 기록 PK
    Returns:
        {return_date, overdue_days, title, name} dict
    Raises:
        NotFoundError: 대출 기록이 없을 때
        LibraryError : 이미 반납된 기록일 때
    """
    with transaction() as cur:
        loan = loan_repository.lock_by_id(cur, loan_id)
        if loan is None:
            raise NotFoundError("존재하지 않는 대출 기록입니다. 목록을 새로고침해 주세요.")
        if loan["return_date"] is not None:
            raise LibraryError(f"이미 반납 처리된 대출입니다. (반납일 {loan['return_date']})")
        result = loan_repository.mark_returned(cur, loan_id)

    return {**result, "title": loan["title"], "name": loan["name"]}
