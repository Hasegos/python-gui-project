import re
from dataclasses import dataclass

from core.exceptions import ValidationError
from schemas.common_schema import clean_text, parse_int

# ISBN-10 (마지막 자리 X 허용) 또는 ISBN-13
ISBN_PATTERN = re.compile(r"\d{9}[\dX]|\d{13}")


# ─────────────────────────────────────
# 1. 도서 등록/수정 요청 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class BookRequest:
    """
    도서 등록/수정 요청 스키마. 검증을 통과한 값만 담는다.

    Args:
        title         : 제목 (필수, 200자 이하)
        author        : 저자 (필수, 100자 이하)
        isbn          : ISBN 10/13자리 (하이픈 제거)
        publisher     : 출판사
        published_year: 출판연도 (1000~9999)
        category      : 분류
        quantity      : 보유 권수 (1~999, 기본 1)
    """
    title          : str
    author         : str
    isbn           : str | None = None
    publisher      : str | None = None
    published_year : int | None = None
    category       : str | None = None
    quantity       : int = 1

    @classmethod
    def from_form(cls, form: dict) -> "BookRequest":
        """
        화면 입력값(문자열 dict)을 검증하여 요청 스키마로 변환한다.

        Args:
            form: 화면 입력값 dict
        Returns:
            BookRequest 객체
        Raises:
            ValidationError: 입력값 오류 시
        """
        # ISBN 은 하이픈/공백을 제거하고 대문자(X)로 통일
        isbn = (form.get("isbn") or "").replace("-", "").replace(" ", "").upper()
        if isbn and not ISBN_PATTERN.fullmatch(isbn):
            raise ValidationError("ISBN 은 10자리 또는 13자리로 입력해 주세요. (하이픈 제외)")

        quantity = parse_int(form.get("quantity"), "보유 권수", minimum=1, maximum=999)
        return cls(
            title=clean_text(form.get("title"), "제목", 200, required=True),
            author=clean_text(form.get("author"), "저자", 100, required=True),
            isbn=isbn or None,
            publisher=clean_text(form.get("publisher"), "출판사", 100),
            published_year=parse_int(form.get("published_year"), "출판연도", 1000, 9999),
            category=clean_text(form.get("category"), "분류", 50),
            quantity=quantity if quantity is not None else 1,
        )
