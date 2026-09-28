from dataclasses import dataclass


# ─────────────────────────────────────
# 1. 대출자 (member 테이블)
# ─────────────────────────────────────
@dataclass
class Member:
    """
    member 테이블 한 행을 표현하는 모델.

    Args:
        member_id : 대출자 PK
        student_no: 학번
        name      : 이름
        department: 학과
        phone     : 연락처
        email     : 이메일
        on_loan   : 미반납 권수 (조회 시 계산, 테이블 컬럼 아님)
        overdue   : 연체 권수 (조회 시 계산, 테이블 컬럼 아님)
    """
    member_id  : int
    student_no : str
    name       : str
    department : str | None = None
    phone      : str | None = None
    email      : str | None = None
    on_loan    : int = 0
    overdue    : int = 0
