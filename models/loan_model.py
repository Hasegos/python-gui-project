from dataclasses import dataclass
from datetime import date


# ─────────────────────────────────────
# 1. 대출 기록 (loan 테이블)
# ─────────────────────────────────────
@dataclass
class Loan:
    """
    loan 테이블 한 행 + 조회 시 JOIN/계산한 값을 표현하는 모델.

    Args:
        loan_id     : 대출 기록 PK
        book_id     : 도서 FK
        member_id   : 대출자 FK
        loan_date   : 대출일
        due_date    : 반납 예정일
        return_date : 반납일 (None 이면 미반납)
        title       : 도서 제목 (book JOIN)
        author      : 저자 (book JOIN)
        student_no  : 학번 (member JOIN)
        name        : 이름 (member JOIN)
        status      : 대출중 / 연체 / 반납완료 (조회 시 계산)
        overdue_days: 연체일수 (조회 시 계산)
    """
    loan_id      : int
    book_id      : int
    member_id    : int
    loan_date    : date
    due_date     : date
    return_date  : date | None = None
    title        : str = ""
    author       : str = ""
    student_no   : str = ""
    name         : str = ""
    status       : str = ""
    overdue_days : int = 0

    @property
    def is_returned(self) -> bool:
        """반납 처리된 기록인지 여부."""
        return self.return_date is not None
