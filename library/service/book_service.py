import re

from psycopg2 import errors

from library.db import transaction
from library.exceptions import LibraryError, NotFoundError, ValidationError
from library.repository import book_repository
from library.service import clean_text, parse_int

# ISBN-10 (마지막 자리 X 허용) 또는 ISBN-13
ISBN_PATTERN = re.compile(r"\d{9}[\dX]|\d{13}")


# ─────────────────────────────────────
# 1. 도서 검색
# ─────────────────────────────────────
def search_books(keyword: str = "", field: str = "all") -> list[dict]:
    """
    도서 목록을 검색한다.

    Args:
        keyword: 검색어
        field  : 검색 기준 (title, author, isbn, publisher, category, all)
    Returns:
        도서 dict 리스트
    """
    with transaction() as cur:
        return book_repository.find_all(cur, keyword.strip(), field)


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
        return book_repository.find_categories(cur)


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
    data = _validate(form)
    try:
        with transaction() as cur:
            return book_repository.insert(cur, data)
    except errors.UniqueViolation:
        raise ValidationError(f"이미 등록된 ISBN 입니다. ({data['isbn']})") from None


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
    data = _validate(form)
    try:
        with transaction() as cur:
            _lock_book(cur, book_id)
            on_loan = book_repository.count_on_loan(cur, book_id)
            if data["quantity"] < on_loan:
                raise LibraryError(
                    f"현재 대출중인 권수({on_loan}권)보다 보유 권수를 적게 설정할 수 없습니다."
                )
            book_repository.update(cur, book_id, data)
    except errors.UniqueViolation:
        raise ValidationError(f"이미 등록된 ISBN 입니다. ({data['isbn']})") from None


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
        on_loan = book_repository.count_on_loan(cur, book_id)
        if on_loan:
            raise LibraryError(
                f"'{book['title']}' 은(는) 대출중인 책이 {on_loan}권 있어 삭제할 수 없습니다.\n"
                "반납 처리 후 다시 시도해 주세요."
            )
        book_repository.delete(cur, book_id)


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
    book = book_repository.lock_by_id(cur, book_id)
    if book is None:
        raise NotFoundError("존재하지 않는 도서입니다. 목록을 새로고침해 주세요.")
    return book


# ─────────────────────────────────────
# 7. 입력값 검증
# ─────────────────────────────────────
def _validate(form: dict) -> dict:
    """
    화면 입력값을 검증하고 DB 에 저장할 형태로 변환한다.

    Args:
        form: 화면 입력값 dict (문자열)
    Returns:
        검증된 도서 정보 dict
    Raises:
        ValidationError: 입력값 오류 시
    """
    # ISBN 은 하이픈/공백을 제거하고 대문자(X)로 통일
    isbn = (form.get("isbn") or "").replace("-", "").replace(" ", "").upper()
    if isbn and not ISBN_PATTERN.fullmatch(isbn):
        raise ValidationError("ISBN 은 10자리 또는 13자리로 입력해 주세요. (하이픈 제외)")

    quantity = parse_int(form.get("quantity"), "보유 권수", minimum=1, maximum=999)
    return {
        "isbn": isbn or None,
        "title": clean_text(form.get("title"), "제목", 200, required=True),
        "author": clean_text(form.get("author"), "저자", 100, required=True),
        "publisher": clean_text(form.get("publisher"), "출판사", 100),
        "published_year": parse_int(form.get("published_year"), "출판연도", 1000, 9999),
        "category": clean_text(form.get("category"), "분류", 50),
        "quantity": quantity if quantity is not None else 1,
    }
