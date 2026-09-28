from dataclasses import dataclass
from datetime import date

from core.config import settings
from core.constants.loan import MAX_LOAN_DAYS, MIN_LOAN_DAYS
from core.exceptions import ValidationError
from schemas.common_schema import parse_int


# ─────────────────────────────────────
# 1. 대출 요청 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class LoanRequest:
    """
    대출 처리 요청 스키마.

    Args:
        book_id  : 대출할 도서 PK
        member_id: 대출자 PK
        loan_days: 대출 기간 (일)
    """
    book_id   : int
    member_id : int
    loan_days : int

    @classmethod
    def from_form(cls, book_id: int | None, member_id: int | None, loan_days) -> "LoanRequest":
        """
        화면에서 선택/입력한 값을 검증하여 요청 스키마로 변환한다.

        Args:
            book_id  : 선택한 도서 PK. 선택하지 않았으면 None.
            member_id: 선택한 대출자 PK. 선택하지 않았으면 None.
            loan_days: 대출 기간 입력값. 비어 있으면 기본 대출 기간.
        Returns:
            LoanRequest 객체
        Raises:
            ValidationError: 도서/대출자 미선택 또는 대출 기간 범위 오류 시
        """
        if book_id is None or member_id is None:
            raise ValidationError("목록에서 도서와 대출자를 선택해 주세요.")
        days = parse_int(loan_days, "대출 기간", MIN_LOAN_DAYS, MAX_LOAN_DAYS)
        return cls(book_id=book_id, member_id=member_id, loan_days=days or settings.LOAN_DAYS)


# ─────────────────────────────────────
# 2. 대출 처리 결과 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class LoanResult:
    """
    대출 처리 결과.

    Args:
        loan_id : 생성된 대출 기록 PK
        due_date: 반납 예정일
        title   : 도서 제목
        name    : 대출자 이름
    """
    loan_id  : int
    due_date : date
    title    : str
    name     : str


# ─────────────────────────────────────
# 3. 반납 처리 결과 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class ReturnResult:
    """
    반납 처리 결과.

    Args:
        return_date : 반납일
        overdue_days: 연체일수 (0 이면 정상 반납)
        title       : 도서 제목
        name        : 대출자 이름
    """
    return_date  : date
    overdue_days : int
    title        : str
    name         : str


# ─────────────────────────────────────
# 4. 상태별 건수 스키마
# ─────────────────────────────────────
@dataclass(frozen=True)
class LoanStatusCount:
    """
    전체 대출 기록의 상태별 건수.

    Args:
        on_loan : 대출중 (연체 제외)
        overdue : 연체
        returned: 반납완료
    """
    on_loan  : int
    overdue  : int
    returned : int
