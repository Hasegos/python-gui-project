from psycopg2 import errors

from core.exceptions import LibraryError, NotFoundError, ValidationError
from core.logger import get_logger
from crud import member_crud
from db.session import transaction
from models.member_model import Member
from schemas.member_schema import MemberRequest

logger = get_logger("member_service")


# ─────────────────────────────────────
# 1. 대출자 검색
# ─────────────────────────────────────
def search_members(keyword: str = "", field: str = "all") -> list[Member]:
    """
    대출자 목록을 검색한다.

    Args:
        keyword: 검색어
        field  : 검색 기준 (student_no, name, department, phone, all)
    Returns:
        Member 리스트
    """
    with transaction() as cur:
        return member_crud.get_members(cur, keyword.strip(), field)


# ─────────────────────────────────────
# 2. 학과 목록 조회
# ─────────────────────────────────────
def get_departments() -> list[str]:
    """
    입력 폼 Combobox 에 표시할 학과 목록을 조회한다.

    Returns:
        학과 문자열 리스트
    """
    with transaction() as cur:
        return member_crud.get_departments(cur)


# ─────────────────────────────────────
# 3. 대출자 등록
# ─────────────────────────────────────
def create_member(form: dict) -> int:
    """
    입력값을 검증한 뒤 대출자를 등록한다.

    Args:
        form: 화면 입력값 dict (문자열)
    Returns:
        생성된 member_id
    Raises:
        ValidationError: 입력값 오류 또는 학번 중복 시
    """
    request = MemberRequest.from_form(form)
    try:
        with transaction() as cur:
            member_id = member_crud.create_member(cur, request)
    except errors.UniqueViolation:
        raise ValidationError(f"이미 등록된 학번입니다. ({request.student_no})") from None
    logger.info("대출자 등록: id=%s student_no=%s", member_id, request.student_no)
    return member_id


# ─────────────────────────────────────
# 4. 대출자 수정
# ─────────────────────────────────────
def update_member(member_id: int, form: dict) -> None:
    """
    입력값을 검증한 뒤 대출자 정보를 수정한다.

    Args:
        member_id: 수정할 대출자 PK
        form     : 화면 입력값 dict (문자열)
    Raises:
        ValidationError: 입력값 오류 또는 학번 중복 시
    """
    request = MemberRequest.from_form(form)
    try:
        with transaction() as cur:
            _lock_member(cur, member_id)
            member_crud.update_member(cur, member_id, request)
    except errors.UniqueViolation:
        raise ValidationError(f"이미 등록된 학번입니다. ({request.student_no})") from None
    logger.info("대출자 수정: id=%s", member_id)


# ─────────────────────────────────────
# 5. 대출자 삭제
# ─────────────────────────────────────
def delete_member(member_id: int) -> None:
    """
    대출자를 삭제한다. 반납하지 않은 도서가 있으면 삭제하지 않는다.

    Args:
        member_id: 삭제할 대출자 PK
    Raises:
        LibraryError: 미반납 도서가 있을 때
    """
    with transaction() as cur:
        member = _lock_member(cur, member_id)
        on_loan = member_crud.count_on_loan(cur, member_id)
        if on_loan:
            raise LibraryError(
                f"{member['name']}({member['student_no']}) 님은 반납하지 않은 도서가 {on_loan}권 있어 "
                "삭제할 수 없습니다.\n반납 처리 후 다시 시도해 주세요."
            )
        member_crud.delete_member(cur, member_id)
    logger.info("대출자 삭제: id=%s", member_id)


# ─────────────────────────────────────
# 6. 대출자 잠금 + 존재 확인
# ─────────────────────────────────────
def _lock_member(cur, member_id: int) -> dict:
    """
    대출자 행을 잠그고, 없으면 NotFoundError 를 던진다.

    Args:
        cur      : DB 커서
        member_id: 대출자 PK
    Returns:
        잠근 대출자 dict
    """
    member = member_crud.lock_member(cur, member_id)
    if member is None:
        raise NotFoundError("존재하지 않는 대출자입니다. 목록을 새로고침해 주세요.")
    return member
