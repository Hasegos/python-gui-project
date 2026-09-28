from psycopg2 import errors

from core.exceptions import LibraryError, NotFoundError, ValidationError
from core.logger import get_logger
from crud import book_crud
from db.session import transaction
from models.book_model import Book
from schemas.book_schema import BookRequest

logger = get_logger("book_service")


# ─────────────────────────────────────
# 1. 도서 검색
# ─────────────────────────────────────
def search_books(keyword: str = "", field: str = "all") -> list[Book]:
    """
    도서 목록을 검색한다.

    Args:
        keyword: 검색어
        field  : 검색 기준 (title, author, isbn, publisher, category, all)
    Returns:
        Book 리스트
    """
    with transaction() as cur:
        return book_crud.get_books(cur, keyword.strip(), field)


# ─────────────────────────────────────
# 2. 분류 목록 조회
# ─────────────────────────────────────
def get_categories() -> list[str]:
    """
    입력 폼 Combobox 에 표시할 분류 목록을 조회한다.

    Returns:
        분류 문자열 리스트
    """
    with transaction() as cur:
        return book_crud.get_categories(cur)


# ─────────────────────────────────────
# 3. 도서 등록
# ─────────────────────────────────────
def create_book(form: dict) -> int:
    """
    입력값을 검증한 뒤 도서를 등록한다.

    Args:
        form: 화면 입력값 dict (문자열)
    Returns:
        생성된 book_id
    Raises:
        ValidationError: 입력값 오류 또는 ISBN 중복 시
    """
    request = BookRequest.from_form(form)
    try:
        with transaction() as cur:
            book_id = book_crud.create_book(cur, request)
    except errors.UniqueViolation:
        raise ValidationError(f"이미 등록된 ISBN 입니다. ({request.isbn})") from None
    logger.info("도서 등록: id=%s title=%s", book_id, request.title)
    return book_id


# ─────────────────────────────────────
# 4. 도서 수정
# ─────────────────────────────────────
def update_book(book_id: int, form: dict) -> None:
    """
    입력값을 검증한 뒤 도서 정보를 수정한다.

    대출중인 권수보다 보유 권수를 적게 바꾸는 것은 허용하지 않는다.

    Args:
        book_id: 수정할 도서 PK
        form   : 화면 입력값 dict (문자열)
    Raises:
        ValidationError: 입력값 오류 또는 ISBN 중복 시
        LibraryError   : 보유 권수가 대출중 권수보다 적을 때
    """
    request = BookRequest.from_form(form)
    try:
        with transaction() as cur:
            _lock_book(cur, book_id)
            on_loan = book_crud.count_on_loan(cur, book_id)
            if request.quantity < on_loan:
                raise LibraryError(
                    f"현재 대출중인 권수({on_loan}권)보다 보유 권수를 적게 설정할 수 없습니다."
                )
            book_crud.update_book(cur, book_id, request)
    except errors.UniqueViolation:
        raise ValidationError(f"이미 등록된 ISBN 입니다. ({request.isbn})") from None
    logger.info("도서 수정: id=%s", book_id)


# ─────────────────────────────────────
# 5. 도서 삭제
# ─────────────────────────────────────
def delete_book(book_id: int) -> None:
    """
    도서를 삭제한다. 대출중인 책이 있으면 삭제하지 않는다.

    Args:
        book_id: 삭제할 도서 PK
    Raises:
        LibraryError: 대출중인 책이 있을 때
    """
    with transaction() as cur:
        book = _lock_book(cur, book_id)
        on_loan = book_crud.count_on_loan(cur, book_id)
        if on_loan:
            raise LibraryError(
                f"'{book['title']}' 은(는) 대출중인 책이 {on_loan}권 있어 삭제할 수 없습니다.\n"
                "반납 처리 후 다시 시도해 주세요."
            )
        book_crud.delete_book(cur, book_id)
    logger.info("도서 삭제: id=%s", book_id)


# ─────────────────────────────────────
# 6. 도서 잠금 + 존재 확인
# ─────────────────────────────────────
def _lock_book(cur, book_id: int) -> dict:
    """
    도서 행을 잠그고, 없으면 NotFoundError 를 던진다.

    Args:
        cur    : DB 커서
        book_id: 도서 PK
    Returns:
        잠근 도서 dict
    """
    book = book_crud.lock_book(cur, book_id)
    if book is None:
        raise NotFoundError("존재하지 않는 도서입니다. 목록을 새로고침해 주세요.")
    return book
