from core.config import settings
from core.exceptions import LibraryError, NotFoundError
from core.logger import get_logger
from crud import book_crud, loan_crud, member_crud
from db.session import transaction
from models.book_model import Book
from models.loan_model import Loan
from models.member_model import Member
from schemas.loan_schema import LoanRequest, LoanResult, LoanStatusCount, ReturnResult

logger = get_logger("loan_service")


# ─────────────────────────────────────
# 1. 대출 기록 검색
# ─────────────────────────────────────
def search_loans(status: str = "all", keyword: str = "") -> list[Loan]:
    """
    대출 기록을 상태 필터와 검색어로 조회한다.

    Args:
        status : 상태 필터 (all, not_returned, on_loan, overdue, returned)
        keyword: 도서명/이름/학번 검색어
    Returns:
        Loan 리스트
    """
    with transaction() as cur:
        return loan_crud.get_loans(cur, status, keyword.strip())


# ─────────────────────────────────────
# 2. 도서/대출자별 대출 이력
# ─────────────────────────────────────
def get_history(book_id: int | None = None, member_id: int | None = None) -> list[Loan]:
    """
    특정 도서 또는 대출자의 전체 대출 이력을 조회한다. (이력 팝업용)

    Args:
        book_id  : 도서 PK (도서 이력 조회 시)
        member_id: 대출자 PK (대출자 이력 조회 시)
    Returns:
        Loan 리스트
    """
    with transaction() as cur:
        return loan_crud.get_loans(cur, "all", book_id=book_id, member_id=member_id)


# ─────────────────────────────────────
# 3. 상태별 건수 조회
# ─────────────────────────────────────
def get_status_counts() -> LoanStatusCount:
    """
    전체 대출 기록의 상태별 건수를 조회한다.

    Returns:
        LoanStatusCount 객체
    """
    with transaction() as cur:
        return loan_crud.count_by_status(cur)


# ─────────────────────────────────────
# 4. 대출 선택지 조회
# ─────────────────────────────────────
def get_borrow_options() -> tuple[list[Book], list[Member]]:
    """
    대출 처리 화면의 선택지(대출 가능 도서, 전체 대출자)를 조회한다.

    Returns:
        (대출 가능 Book 리스트, Member 리스트)
    """
    with transaction() as cur:
        books = book_crud.get_books(cur, only_available=True)
        members = member_crud.get_members(cur)
    return books, members


# ─────────────────────────────────────
# 5. 대출 처리
# ─────────────────────────────────────
def borrow_book(book_id: int | None, member_id: int | None, loan_days=None) -> LoanResult:
    """
    도서를 대출한다.

    하나의 트랜잭션 안에서 도서/대출자 행을 잠근 뒤 대출 가능 여부를 검사하고 기록을 남긴다.
    잠금 순서는 항상 book → member 로 고정하여 교착 상태(Deadlock)를 방지한다.

    Args:
        book_id  : 대출할 도서 PK
        member_id: 대출자 PK
        loan_days: 대출 기간 (일). 비어 있으면 기본 대출 기간
    Returns:
        LoanResult 객체
    Raises:
        ValidationError: 도서/대출자 미선택, 대출 기간 오류 시
        NotFoundError  : 도서/대출자가 없을 때
        LibraryError   : 연체 도서 보유, 대출 한도 초과, 중복 대출, 재고 부족 시
    """
    request = LoanRequest.from_form(book_id, member_id, loan_days)

    with transaction() as cur:
        # ─────────────────────────────────
        # 5-1. 도서 → 대출자 순서로 행 잠금
        # ─────────────────────────────────
        book = book_crud.lock_book(cur, request.book_id)
        if book is None:
            raise NotFoundError("존재하지 않는 도서입니다. 목록을 새로고침해 주세요.")
        member = member_crud.lock_member(cur, request.member_id)
        if member is None:
            raise NotFoundError("존재하지 않는 대출자입니다. 목록을 새로고침해 주세요.")

        # ─────────────────────────────────
        # 5-2. 대출자 조건 검사 (연체, 한도, 중복)
        # ─────────────────────────────────
        member_loans = loan_crud.count_member_loans(cur, request.member_id)
        if member_loans["overdue"]:
            raise LibraryError(
                f"{member['name']} 님은 연체중인 도서가 {member_loans['overdue']}권 있어 대출할 수 없습니다.\n"
                "연체 도서를 먼저 반납해 주세요."
            )
        if member_loans["on_loan"] >= settings.MAX_LOANS_PER_MEMBER:
            raise LibraryError(
                f"{member['name']} 님은 이미 최대 대출 권수({settings.MAX_LOANS_PER_MEMBER}권)를 대출중입니다."
            )
        if loan_crud.exists_not_returned(cur, request.book_id, request.member_id):
            raise LibraryError(f"{member['name']} 님은 '{book['title']}' 을(를) 이미 대출중입니다.")

        # ─────────────────────────────────
        # 5-3. 재고 검사 후 대출 기록 등록
        # ─────────────────────────────────
        on_loan = book_crud.count_on_loan(cur, request.book_id)
        if on_loan >= book["quantity"]:
            raise LibraryError(f"'{book['title']}' 은(는) 대출 가능한 재고가 없습니다.")

        loan = loan_crud.create_loan(cur, request)

    logger.info("대출: loan=%s book=%s member=%s", loan["loan_id"], request.book_id, request.member_id)
    return LoanResult(loan_id=loan["loan_id"], due_date=loan["due_date"], title=book["title"], name=member["name"])


# ─────────────────────────────────────
# 6. 반납 처리
# ─────────────────────────────────────
def return_book(loan_id: int) -> ReturnResult:
    """
    대출 기록을 반납 처리한다. 이미 반납된 기록은 다시 처리하지 않는다.

    Args:
        loan_id: 대출 기록 PK
    Returns:
        ReturnResult 객체
    Raises:
        NotFoundError: 대출 기록이 없을 때
        LibraryError : 이미 반납된 기록일 때
    """
    with transaction() as cur:
        loan = loan_crud.lock_loan(cur, loan_id)
        if loan is None:
            raise NotFoundError("존재하지 않는 대출 기록입니다. 목록을 새로고침해 주세요.")
        if loan["return_date"] is not None:
            raise LibraryError(f"이미 반납 처리된 대출입니다. (반납일 {loan['return_date']})")
        result = loan_crud.mark_returned(cur, loan_id)

    logger.info("반납: loan=%s overdue_days=%s", loan_id, result["overdue_days"])
    return ReturnResult(
        return_date=result["return_date"],
        overdue_days=result["overdue_days"],
        title=loan["title"],
        name=loan["name"],
    )
