from dataclasses import dataclass


# ─────────────────────────────────────
# 1. 도서 (book 테이블)
# ─────────────────────────────────────
@dataclass
class Book:
    """
    book 테이블 한 행을 표현하는 모델.

    Args:
        book_id       : 도서 PK
        title         : 제목
        author        : 저자
        isbn          : ISBN (10/13자리, 선택)
        publisher     : 출판사
        published_year: 출판연도
        category      : 분류
        quantity      : 보유 권수
        available     : 대출 가능 권수 (조회 시 계산, 테이블 컬럼 아님)
    """
    book_id        : int
    title          : str
    author         : str
    isbn           : str | None = None
    publisher      : str | None = None
    published_year : int | None = None
    category       : str | None = None
    quantity       : int = 1
    available      : int = 0
